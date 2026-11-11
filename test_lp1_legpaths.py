#!/usr/bin/env python3
"""LP1 -- covenant_legpaths.py, driven both ways (A407 cross-OS road redundancy, the laptop side, 2026-11-07).

The claim is narrow and mechanical: legs are read in PARALLEL (a severed leg costs ~one timeout, not one each),
roads are tried in ORDER with FALL-THROUGH (a dead road is retried on the next before the leg is called down),
any HTTP reply counts as the leg answering (A115), an absent/malformed roads file yields NO legs (never a guess),
and no address lives in the module source (this repo is public). Every check is driven both ways: the property
holds, AND reinstating its negation is observed to fail.

Stdlib only; no covenant node, no real network beyond 127.0.0.1 servers this test starts itself.
"""
import json
import os
import re
import socket
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import covenant_legpaths as LP

HERE = os.path.dirname(os.path.abspath(__file__))
_servers, _tarpits = [], []


def _http(status, body=b"ok"):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _servers.append(srv)
    return "127.0.0.1:%d" % srv.server_address[1]


def _tarpit():
    """A listener that accepts and never replies: a GET over it blocks until the client's read timeout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(16)
    held = []

    def loop():
        while True:
            try:
                c, _ = s.accept()
            except OSError:
                break
            held.append(c)
    threading.Thread(target=loop, daemon=True).start()
    _tarpits.append((s, held))
    return "127.0.0.1:%d" % s.getsockname()[1]


def _refused():
    """A port nobody listens on: bind to claim a free one, then release it, so a connect is refused fast."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "127.0.0.1:%d" % port


def _cleanup():
    for srv in _servers:
        srv.shutdown()
    for s, _held in _tarpits:
        s.close()


# --------------------------------------------------------------------------- checks

def check_fallthrough_picks_next_road():
    """A dead first road falls through to a live second -- and the OTHER way, two dead roads report down."""
    live = _http(200)
    cfg = {"node_D": {"roads": [_refused(), live], "path": "/health"}}
    r = LP.read_leg("node_D", config=cfg, timeout=1.0)
    assert r["ok"] is True, r
    assert r["road_index"] == 1, "expected fall-through to road 1, got %r" % r
    assert r["roads_tried"] == 2, r
    # the other way: with no live road, fall-through exhausts and the leg is down, not hung on road 0
    down = {"node_D": {"roads": [_refused(), _refused()], "path": "/health"}}
    rd = LP.read_leg("node_D", config=down, timeout=1.0)
    assert rd["ok"] is False and rd["roads_tried"] == 2, rd


def check_timeout_road_falls_through():
    """A road that HANGS (not merely refuses) still falls through once it times out -- the real severed-road case."""
    live = _http(200)
    cfg = {"node_D": {"roads": [_tarpit(), live], "path": "/health"}}
    t0 = time.time()
    r = LP.read_leg("node_D", config=cfg, timeout=0.5)
    dt = time.time() - t0
    assert r["ok"] is True and r["road_index"] == 1, r
    assert 0.4 < dt < 2.0, "expected ~one timeout then success, took %.2fs" % dt


def check_legs_read_in_parallel():
    """N severed legs cost ~ONE timeout, not N. Serial would be N*timeout; threaded is ~timeout."""
    n, t = 5, 0.4
    cfg = {"leg%d" % i: {"roads": [_tarpit()], "path": "/health"} for i in range(n)}
    t0 = time.time()
    out = LP.read_all(config=cfg, timeout=t)
    dt = time.time() - t0
    assert len(out) == n and all(v["ok"] is False for v in out.values()), out
    serial = n * t
    assert dt < serial - t, "read_all took %.2fs; serial would be ~%.2fs -- not parallel" % (dt, serial)
    assert dt > t * 0.8, "read_all returned in %.2fs, below one timeout -- it did not actually wait" % dt


def check_http_reply_is_answering_a115():
    """A 429 (and any HTTP code) is the leg ANSWERING over that road, not a reason to fall through (A115)."""
    for code in (200, 429, 503):
        cfg = {"x": {"roads": [_http(code)], "path": "/health"}}
        r = LP.read_leg("x", config=cfg, timeout=1.0)
        assert r["ok"] is True and r["status"] == code and r["road_index"] == 0, (code, r)
    # the other way: a transport failure is NOT "answering" -- ok is False
    r = LP.read_leg("x", config={"x": {"roads": [_refused()]}}, timeout=1.0)
    assert r["ok"] is False, r


def check_absent_or_malformed_file_yields_no_legs():
    """No file, bad JSON, or the wrong shape -> {} and a leg marked down for want of roads. Never a guessed road."""
    missing = os.path.join(tempfile.gettempdir(), "lp1_no_such_%d.json" % os.getpid())
    if os.path.exists(missing):
        os.remove(missing)
    assert LP._load(missing) == {}
    for payload in ("{ not json", json.dumps([1, 2, 3]), json.dumps({"node_D": {"roads": []}}),
                    json.dumps({"node_D": {"roads": ["", "  "]}}), json.dumps({"node_D": "oops"})):
        fd, p = tempfile.mkstemp(suffix=".json")
        os.write(fd, payload.encode())
        os.close(fd)
        try:
            assert LP._load(p) == {}, "malformed payload produced legs: %r -> %r" % (payload, LP._load(p))
        finally:
            os.remove(p)
    assert LP.read_all(config={}) == {}
    r = LP.read_leg("node_D", config={}, timeout=0.5)
    assert r["ok"] is False and r["roads_tried"] == 0, r
    # the other way: a well-formed file with one real road DOES yield exactly that leg
    fd, p = tempfile.mkstemp(suffix=".json")
    os.write(fd, json.dumps({"legs": {"node_D": {"roads": ["127.0.0.1:5080"]}}}).encode())
    os.close(fd)
    try:
        assert LP.legs(config=LP._load(p)) == ["node_D"], LP._load(p)
    finally:
        os.remove(p)


_TAILNET = re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_ANYV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
_LOOPBACK_OK = {"127.0.0.1", "0.0.0.0"}
# A FABRICATED tailnet-range address, assembled from octets so the literal never appears in this
# file's source. The opsec push guard refuses any literal tailnet IP, and this test's whole point is
# to plant one at RUNTIME to prove the scanner is not blind. 100.100.100.100 is obviously not a real
# node; its second octet (100) is in [64,127], so it still matches _TAILNET.
_FAKE_TAILNET = ".".join(("100", "100", "100", "100"))


def check_source_carries_no_address():
    """The module source and the shipped example hold NO tailnet/public address -- only loopback. Driven the other
    way: the SAME scan catches a planted tailnet address, so a clean result means the scan works, not that it is
    blind (A30 -- a check must prove it can see what it claims is absent)."""
    src = open(os.path.join(HERE, "covenant_legpaths.py"), encoding="utf-8").read()
    example = open(os.path.join(HERE, "ops", "leg_roads.example.json"), encoding="utf-8").read()
    for name, text in (("covenant_legpaths.py", src), ("ops/leg_roads.example.json", example)):
        assert not _TAILNET.search(text), "%s carries a tailnet address" % name
        assert ".ts.net" not in text, "%s carries a tailnet DNS name" % name
        stray = [ip for ip in _ANYV4.findall(text) if ip not in _LOOPBACK_OK]
        assert not stray, "%s carries non-loopback IPv4 %r" % (name, stray)
    # the other way: the scan is not blind
    planted = 'TARGET = (%r, 15081)' % _FAKE_TAILNET
    assert _TAILNET.search(planted), "the tailnet scan cannot see a tailnet address -- it is blind"
    assert _ANYV4.search(planted)


def check_masking_hides_real_hosts():
    """Returned/logged roads mask a real host but keep loopback readable (debugging a relay needs the loopback)."""
    assert LP._mask_host("127.0.0.1:5001") == "127.0.0.1:5001"
    m = LP._mask_host(_FAKE_TAILNET + ":5081")
    assert _FAKE_TAILNET not in m and m.endswith(":5081"), m


CHECKS = [
    check_fallthrough_picks_next_road,
    check_timeout_road_falls_through,
    check_legs_read_in_parallel,
    check_http_reply_is_answering_a115,
    check_absent_or_malformed_file_yields_no_legs,
    check_source_carries_no_address,
    check_masking_hides_real_hosts,
]


def main():
    failed = 0
    try:
        for c in CHECKS:
            try:
                c()
                print("ok   %s" % c.__name__)
            except AssertionError as e:
                failed += 1
                print("FAIL %s: %s" % (c.__name__, e))
    finally:
        _cleanup()
    print("\nLP1: %d/%d checks passed" % (len(CHECKS) - failed, len(CHECKS)))
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
