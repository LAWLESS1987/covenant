"""TC1 -- both-ways test for covenant_tetsu_client's door fallthrough.

Hermetic: a local stub HTTP door on 127.0.0.1 plus a dead port, no TETSU, no SOCKS, no
outside network. Every guard is driven in the direction that PASSES and the direction
that must FAIL/raise, so a green is earned:
  * a later door answers when an earlier one is down (fallthrough), and the down door is
    recorded;
  * a consult POST round-trips and comes back labelled;
  * max_tokens is OMITTED by default (the operator's no-cap rule) and SENT only when set;
  * all doors down -> AllDoorsDown, not a hang or a crash.
Run:  python test_tc1_tetsu_client.py
"""
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import covenant_tetsu_client as tc

checks = []
UNICODE_ANSWER = "Luna’s “lead” — 0.8 → too close ≤ 1"


def check(name, cond):
    checks.append(bool(cond))
    print(("ok   " if cond else "FAIL ") + name)


class Stub(BaseHTTPRequestHandler):
    last_post = None

    def log_message(self, *a):
        pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/panel":
            self._send({"panel": {"leg-qwen3.5-2b": True, "qwen3.8-27b-uncensored": True}})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_raw(self, b):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        Stub.last_post = json.loads(self.rfile.read(n) or b"{}")
        q = Stub.last_post.get("question")
        if q == "unicode":
            # what the real door sends: raw UTF-8, NOT \u-escaped (ensure_ascii=False). The 27B's answer on
            # 2026-11-05 carried a right double quote (bytes E2 80 9D); 0x9D has no cp1252 mapping.
            self._send_raw(json.dumps({"question": q, "answers": [{"model": "m", "answer": UNICODE_ANSWER}]},
                                      ensure_ascii=False).encode("utf-8"))
            return
        if q == "badbytes":
            self._send_raw(b'{"answers": [{"answer": "\xff\xfe"}]}')         # not valid UTF-8
            return
        self._send({"question": Stub.last_post.get("question"),
                    "answers": [{"model": "leg-qwen3.5-2b", "answer": "READY",
                                 "seconds": 0.0, "tokens": 1, "error": None}]})


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


good_port = free_port()
srv = HTTPServer(("127.0.0.1", good_port), Stub)
threading.Thread(target=srv.serve_forever, daemon=True).start()

GOOD = {"name": "good", "base": "http://127.0.0.1:%d" % good_port, "socks": None}
BAD = {"name": "bad", "base": "http://127.0.0.1:%d" % free_port(), "socks": None}   # nothing listens
BAD2 = {"name": "bad2", "base": "http://127.0.0.1:%d" % free_port(), "socks": None}

try:
    # --- PASS: bad first, good second -> fall through to good ---
    r = tc.panel(timeout=4, doors=[BAD, GOOD])
    check("panel falls through a down door to a working one", r["door"] == "good")
    check("panel returns the panel map", r["panel"].get("leg-qwen3.5-2b") is True)
    check("the down door is recorded in attempts", any(a["door"] == "bad" for a in r["attempts"]))

    # --- PASS: consult POST round-trips through the working door, labelled ---
    c = tc.consult("say READY", models=["leg-qwen3.5-2b"], timeout=4, doors=[BAD, GOOD])
    check("consult reaches the working door", c["door"] == "good")
    check("consult returns labelled answers", c["result"]["answers"][0]["answer"] == "READY")

    # --- no-cap rule, both ways: omitted by default, present only when set ---
    Stub.last_post = None
    tc.consult("q", timeout=4, doors=[GOOD])
    check("max_tokens OMITTED by default (uncapped)", "max_tokens" not in (Stub.last_post or {}))
    check("thinking defaults to false", Stub.last_post.get("thinking") is False)
    Stub.last_post = None
    tc.consult("q", max_tokens=50, timeout=4, doors=[GOOD])
    check("max_tokens SENT when explicitly set", (Stub.last_post or {}).get("max_tokens") == 50)

    # --- UTF-8, both ways (2026-11-05). A non-ASCII answer from a WORKING door must come back intact;
    #     an undecodable one must be named a decode error, never "no response" (which reads as a down door). ---
    u = None
    try:
        u = tc.consult("unicode", timeout=4, doors=[GOOD])
    except tc.AllDoorsDown as e:
        u = e
    check("a raw-UTF-8 answer comes back intact (not 'all doors down')",
          isinstance(u, dict) and u["result"]["answers"][0]["answer"] == UNICODE_ANSWER)
    bad = None
    try:
        tc.consult("badbytes", timeout=4, doors=[GOOD])
    except tc.AllDoorsDown as e:
        bad = e
    check("undecodable bytes are reported as a decode error, not as a down door",
          bad is not None and "decode" in str(bad).lower())

    # --- FAIL direction: every door down -> AllDoorsDown, no hang/crash ---
    err = None
    try:
        tc.panel(timeout=3, doors=[BAD, BAD2])
    except tc.AllDoorsDown as e:
        err = e
    check("all doors down raises AllDoorsDown (no hang)", err is not None)
    check("AllDoorsDown names the down doors", err is not None and "bad" in str(err))

    # --- config loading from a gitignored JSON file (addresses live there, not in source) ---
    import json as _json
    import os as _os
    import tempfile
    fd, cfg = tempfile.mkstemp(suffix=".json")
    with _os.fdopen(fd, "w", encoding="utf-8") as fh:
        _json.dump([{"name": "d1", "base": "http://127.0.0.1:1", "socks": None},
                    {"name": "d2", "base": "http://127.0.0.1:2", "socks": "127.0.0.1:9"}], fh)
    loaded = tc.load_doors(cfg)
    check("load_doors reads the config list", [d["name"] for d in loaded] == ["d1", "d2"])
    check("load_doors keeps socks per door", loaded[1]["socks"] == "127.0.0.1:9")
    check("load_doors on a missing file returns []", tc.load_doors(cfg + ".nope") == [])
    _os.remove(cfg)

    # --- no doors configured -> NoDoorsConfigured (clear error, not a crash) ---
    nd = None
    try:
        tc.panel(timeout=2, doors=[])
    except tc.NoDoorsConfigured as e:
        nd = e
    check("empty door list raises NoDoorsConfigured", nd is not None)
finally:
    srv.shutdown()

passed = sum(checks)
total = len(checks)
print("\nTC1: %d/%d passed" % (passed, total))
sys.exit(0 if passed == total else 1)
