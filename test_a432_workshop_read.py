#!/usr/bin/env python3
"""A432: the workshop read door -- POST /m/workshop/read hands back one workshop file's exact bytes and their sha256,
to a request signed by a registered operator key and to nobody else.

Offline. A real node object (temp database and key) and its real Flask app, driven by the test client; real
signatures over the real core scheme; a fixture signer registry, workshop, hands ledger and mycelium ledger in a
retained temp folder. Nothing binds a port, and the real workshop, ledgers and registries are never touched. The
spore check runs the production wrapper and admission path with an in-memory sealer and relay (as A430S does).

    python test_a432_workshop_read.py
"""
import base64
import builtins
import hashlib
import json
import os
import sys
import tempfile
import types
from unittest.mock import patch

import covenant_daily_plan as DP
import covenant_mycelium as MY
import covenant_spore as S
import covenant_tetsu_hands as H
import covenant_unified_v8 as cov

PATH = "/m/workshop/read"
OFF_TAILNET = "192.0.2.41"                  # TEST-NET-1: neither loopback nor the tailnet
LOOPBACK = "127.0.0.1"
TAILNET = str(cov.TAILNET_CGNAT[4097])      # an address inside the tailnet range, taken from the core's own constant
REFUSED_403 = "reading a workshop file needs a request signed by a registered operator key"
CASES = []


def case(fn):
    CASES.append(fn)
    return fn


class Door:
    """One node, one fixture workshop and registry. Each case gets a fresh one."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="a432_")      # retained, never removed (nothing erased)
        self.shop = os.path.join(self.root, "workshop")
        os.makedirs(self.shop)
        self.outside = os.path.join(self.root, "outside")
        os.makedirs(self.outside)
        with open(os.path.join(self.outside, "secret.txt"), "wb") as fh:
            fh.write(b"OUTSIDE-THE-WORKSHOP")
        self.ledger = os.path.join(self.root, "hands.jsonl")
        self.key, self.pem = cov.sig_keygen()
        self.stranger, _ = cov.sig_keygen()
        signers = os.path.join(self.root, "signers.json")
        with open(signers, "w", encoding="utf-8") as fh:
            json.dump({"fixture": self.pem}, fh)
        self.patches = [patch.object(t, a, v) for t, a, v in (
            (H, "WORKSHOP", self.shop), (H, "LEDGER", self.ledger),
            (DP, "SIGNERS", signers), (DP, "_seen_nonces", set()),
            (MY, "PEERS", os.path.join(self.root, "no_allies.json")),
            (MY, "LEDGER", os.path.join(self.root, "mycelium.jsonl")))]
        for p in self.patches:
            p.start()
        self.m = cov.CovenantUnifiedMaster("a432", host="127.0.0.1", port=15432, p2p_port=15433,
                                           db_path=os.path.join(self.root, "node.db"))
        self.client = self.m.api.app.test_client()
        self.sent = 0

    def close(self):
        for p in reversed(self.patches):
            p.stop()

    def put(self, name, raw):
        p = os.path.join(self.shop, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(raw)
        return p

    def signed(self, payload, key=None):
        return DP.sign_json_request(key or self.key, "POST", PATH, payload)

    def post(self, body, headers=None, addr=OFF_TAILNET):
        self.m.node.rate_limiter._hits.clear()   # many asks from one address in a second; the limiter is not under test
        self.sent += 1
        h = dict(headers or {})
        h.setdefault("Content-Type", "application/json")
        r = self.client.post(PATH, data=body, headers=h, environ_base={"REMOTE_ADDR": addr})
        try:
            js = json.loads(r.get_data())
        except ValueError:
            js = None
        return r.status_code, js

    def read(self, name, addr=OFF_TAILNET):
        body, headers = self.signed({"name": name})
        return self.post(body, headers, addr)

    def rows(self):
        return H._rows(self.ledger)


def with_door(fn):
    def run():
        d = Door()
        try:
            fn(d)
        finally:
            d.close()
    run.__name__ = fn.__name__
    return run


RAW = b"print('exact')\r\n\x00\xff\xfe not utf-8 \xe9\n# no newline at the end"


@case
@with_door
def signed_read_returns_exact_bytes_and_their_sha256(d):
    d.put("probe.py", RAW)
    code, js = d.read("probe.py")
    assert code == 200, (code, js)
    assert set(js) == {"name", "size", "sha256", "bytes_b64"}, js
    got = base64.b64decode(js["bytes_b64"], validate=True)
    assert got == RAW, got
    assert js["sha256"] == hashlib.sha256(RAW).hexdigest() and js["size"] == len(RAW) and js["name"] == "probe.py", js


@case
@with_door
def a_file_in_a_workshop_folder_is_read_by_the_hands_rule(d):
    d.put("tasks/t1.py", b"x = 1\n")
    code, js = d.read("tasks/t1.py")
    assert code == 200 and base64.b64decode(js["bytes_b64"]) == b"x = 1\n", (code, js)


@case
@with_door
def the_file_is_opened_once_as_bytes(d):
    target = os.path.realpath(d.put("once.py", RAW))
    opened, real_open = [], builtins.open

    def counting(file, mode="r", *a, **k):
        if isinstance(file, (str, bytes, os.PathLike)) and os.path.realpath(file) == target:
            opened.append(mode)
        return real_open(file, mode, *a, **k)

    with patch.object(builtins, "open", counting):
        code, js = d.read("once.py")
    assert code == 200, (code, js)
    assert opened == ["rb"], opened


@case
@with_door
def unsigned_is_refused_403_and_nothing_is_read(d):
    d.put("probe.py", RAW)
    calls = []
    with patch.object(H, "read_exact", side_effect=lambda *a, **k: calls.append(a) or (200, {})):
        code, js = d.post(json.dumps({"name": "probe.py"}).encode())
    assert code == 403 and js == {"error": REFUSED_403}, (code, js)
    assert calls == [], calls


@case
@with_door
def loopback_alone_is_refused_403(d):
    d.put("probe.py", RAW)
    code, js = d.post(json.dumps({"name": "probe.py"}).encode(), addr=LOOPBACK)
    assert code == 403 and js == {"error": REFUSED_403}, (code, js)


@case
@with_door
def tailnet_alone_is_refused_403(d):
    assert cov.tailnet_ok(TAILNET), TAILNET          # the address really is one the /m doors admit
    d.put("probe.py", RAW)
    code, js = d.post(json.dumps({"name": "probe.py"}).encode(), addr=TAILNET)
    assert code == 403 and js == {"error": REFUSED_403}, (code, js)


@case
@with_door
def a_signed_request_is_read_on_every_road(d):
    d.put("probe.py", RAW)
    for addr in (OFF_TAILNET, LOOPBACK, TAILNET):
        code, js = d.read("probe.py", addr=addr)
        assert code == 200 and base64.b64decode(js["bytes_b64"]) == RAW, (addr, code, js)


@case
@with_door
def an_unregistered_key_is_refused_403(d):
    d.put("probe.py", RAW)
    body, headers = d.signed({"name": "probe.py"}, key=d.stranger)
    code, js = d.post(body, headers, addr=LOOPBACK)
    assert code == 403 and js == {"error": REFUSED_403}, (code, js)


@case
@with_door
def a_signature_for_another_door_or_body_is_refused_403(d):
    d.put("probe.py", RAW)
    d.put("other.py", b"other\n")
    body = json.dumps({"name": "probe.py"}).encode()
    other = DP.sign_headers(d.key, "POST", "/m/agent", body)
    other["Content-Type"] = "application/json"
    code, js = d.post(body, other)
    assert code == 403, (code, js)
    body, headers = d.signed({"name": "probe.py"})
    code, js = d.post(json.dumps({"name": "other.py"}).encode(), headers)
    assert code == 403, (code, js)


@case
@with_door
def a_replayed_request_is_refused_403(d):
    d.put("probe.py", RAW)
    body, headers = d.signed({"name": "probe.py"})
    first, _ = d.post(body, headers)
    again, js = d.post(body, headers)
    assert first == 200 and again == 403, (first, again, js)


@case
@with_door
def a_bad_name_is_refused_400(d):
    d.put("probe.py", RAW)
    for payload in ({}, {"name": ""}, {"name": None}, {"name": 7}, {"name": ["probe.py"]}, {"name": "/probe.py"},
                    {"name": ".hidden"}, {"name": "a b.py"}, {"name": "probe.py\x00"},
                    {"name": "x" * 121}, {"file": "probe.py"}):
        body, headers = d.signed(payload)
        code, js = d.post(body, headers)
        assert code == 400 and isinstance(js, dict) and set(js) == {"error"}, (payload, code, js)


@case
@with_door
def a_name_that_leaves_the_workshop_is_refused_400(d):
    d.put("probe.py", RAW)
    for name in ("../outside/secret.txt", "tasks/../../outside/secret.txt", "..\\outside\\secret.txt",
                 os.path.join(d.outside, "secret.txt")):
        code, js = d.read(name)
        assert code == 400, (name, code, js)
        assert "OUTSIDE" not in json.dumps(js), js


def _links_out(d):
    """Make what links out of the workshop this platform allows: a file link, and a folder link (a symbolic link, or
    a junction on Windows, which needs no privilege). Returns the names that reach secret.txt through a link."""
    made = []
    try:
        os.symlink(os.path.join(d.outside, "secret.txt"), os.path.join(d.shop, "link.txt"))
        made.append("link.txt")
    except (OSError, NotImplementedError):
        pass
    linkdir = os.path.join(d.shop, "linkdir")
    try:
        os.symlink(d.outside, linkdir, target_is_directory=True)
    except (OSError, NotImplementedError):
        if sys.platform == "win32":
            import _winapi
            _winapi.CreateJunction(d.outside, linkdir)
    if os.path.isfile(os.path.join(linkdir, "secret.txt")):
        made.append("linkdir/secret.txt")
    return made


@case
@with_door
def a_link_pointing_out_is_refused_400(d):
    names = _links_out(d)
    assert names, "no link out of the workshop could be made here, so the refusal was not observed"
    for name in names:
        with open(os.path.join(d.shop, name), "rb") as fh:
            assert fh.read() == b"OUTSIDE-THE-WORKSHOP"     # the link really reaches the file outside
        code, js = d.read(name)
        assert code == 400 and "OUTSIDE" not in json.dumps(js), (name, code, js)


@case
@with_door
def a_link_inside_the_workshop_is_read(d):
    d.put("realdir/real.py", RAW)
    names = []
    try:
        os.symlink(os.path.join(d.shop, "realdir", "real.py"), os.path.join(d.shop, "alias.py"))
        names.append("alias.py")
    except (OSError, NotImplementedError):
        pass
    try:
        os.symlink(os.path.join(d.shop, "realdir"), os.path.join(d.shop, "aliasdir"), target_is_directory=True)
    except (OSError, NotImplementedError):
        if sys.platform == "win32":
            import _winapi
            _winapi.CreateJunction(os.path.join(d.shop, "realdir"), os.path.join(d.shop, "aliasdir"))
    if os.path.isfile(os.path.join(d.shop, "aliasdir", "real.py")):
        names.append("aliasdir/real.py")
    assert names, "no link inside the workshop could be made here, so the read was not observed"
    for name in names:
        code, js = d.read(name)
        assert code == 200 and base64.b64decode(js["bytes_b64"]) == RAW, (name, code, js)


@case
@with_door
def a_missing_file_is_refused_404(d):
    os.makedirs(os.path.join(d.shop, "afolder"))
    for name in ("nothere.py", "afolder", "tasks/nothere.py"):
        code, js = d.read(name)
        assert code == 404 and set(js) == {"error"}, (name, code, js)


@case
@with_door
def an_oversized_file_is_refused_413_and_the_limit_is_read(d):
    d.put("big.txt", b"a" * (H.MAX_FILE + 1))
    d.put("full.txt", b"b" * H.MAX_FILE)
    code, js = d.read("big.txt")
    assert code == 413 and set(js) == {"error"}, (code, js)
    code, js = d.read("full.txt")
    assert code == 200 and js["size"] == H.MAX_FILE and base64.b64decode(js["bytes_b64"]) == b"b" * H.MAX_FILE, code


@case
@with_door
def every_answer_is_one_ledger_row_and_no_row_holds_content(d):
    marker = b"CONTENT-MARKER-7f3a"
    d.put("probe.py", marker + RAW)
    d.put("big.txt", marker * (H.MAX_FILE // len(marker) + 1))
    d.read("probe.py")                                                          # 200
    d.post(json.dumps({"name": "probe.py"}).encode(), addr=LOOPBACK)          # 403
    d.read("../outside/secret.txt")                                             # 400
    d.read("nothere.py")                                                        # 404
    d.read("big.txt")                                                           # 413
    rows = d.rows()
    assert len(rows) == d.sent, (len(rows), d.sent, rows)
    assert [r.get("status") for r in rows] == [200, 403, 400, 404, 413], rows
    assert all(r.get("kind") == "operator_read" for r in rows), rows
    text = json.dumps(rows)
    for leak in (marker.decode(), base64.b64encode(marker + RAW).decode()[:24], "OUTSIDE-THE-WORKSHOP", "bytes_b64"):
        assert leak not in text, leak
    ok = rows[0]
    assert ok["outcome"] == "read" and ok["name"] == "probe.py" and ok["size"] == len(marker + RAW), ok
    assert ok["sha256"] == hashlib.sha256(marker + RAW).hexdigest() and ok["who"].startswith("key:"), ok
    assert all(r["outcome"] == "refused" and r.get("sha256") is None for r in rows[1:]), rows
    assert rows[1]["who"] == "" and rows[1]["name"] is None, rows[1]


@case
def the_spore_relay_allows_the_door_and_carries_the_signed_bytes(_=None):
    assert S.door_ok(PATH), S.SPORE_DOORS
    assert PATH in S.SPORE_DOORS
    key, pem = cov.sig_keygen()
    body, headers = DP.sign_json_request(key, "POST", PATH, {"name": "probe.py"})
    sealer = types.SimpleNamespace(
        seal=lambda kind, obj, *args: obj, blocks=lambda obj: [obj],
        open_env=lambda obj, *args: ({"kind": S.KIND_REQ}, obj, pem),
        fingerprint=lambda ignored: "box", error=ValueError)
    _, block = S.wrap_request(sealer, "POST", PATH, body, headers, key, pem, pem)
    relay = types.SimpleNamespace(take=lambda *a, **k: [("block", block)], put=lambda *a: None)
    forwarded = []

    def forward(method, path, raw, signed):
        forwarded.append((method, path, raw, signed))
        return 200, b"{}", {}

    with patch.object(DP, "signer_name", return_value="operator"), patch.object(MY, "_record"):
        rows = S.pc_pass(relay, key, pem, forward=forward, sealer=sealer, seen=set())
    assert rows and rows[-1]["kind"] == "answered", rows
    assert len(forwarded) == 1 and forwarded[0][:3] == ("POST", PATH, body), forwarded
    # the largest answer the door gives (a MAX_FILE file) fits what the spore road carries
    biggest = json.dumps({"name": "x" * 120, "size": H.MAX_FILE, "sha256": "0" * 64,
                          "bytes_b64": base64.b64encode(b"\xff" * H.MAX_FILE).decode()}).encode()
    assert len(biggest) <= S.MAX_BODY, (len(biggest), S.MAX_BODY)


def main():
    passed = 0
    for fn in CASES:
        try:
            fn()
        except Exception as exc:                                  # noqa: BLE001 -- each case reports on its own
            print("FAIL %s: %s: %s" % (fn.__name__, type(exc).__name__, str(exc)[:240]), flush=True)
        else:
            passed += 1
            print("ok   " + fn.__name__, flush=True)
    print("A432: %d/%d passed" % (passed, len(CASES)))
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
