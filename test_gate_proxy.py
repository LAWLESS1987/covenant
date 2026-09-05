#!/usr/bin/env python3
"""test_gate_proxy.py -- the gate proxy fails closed, and only closed.

Every check runs against a fake upstream and a mock sentinel on loopback
ports; no real judge, no network, no daemon. The one thing the real gate
adds -- the quorum's verdicts -- is pinned elsewhere (F2, F3, F6, the
semantic suite); this file pins the plumbing between a request and that
verdict, which is where a bridge silently turns into a bypass.
LICENCE: public domain.
"""
from __future__ import annotations

import http.server
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_gate_proxy as GP  # noqa: E402

FAILS = []
N = 0


def ok(tag, name, cond, detail=""):
    global N
    N += 1
    print("   %s  %s %s  %s" % ("PASS" if cond else "FAIL", tag, name, str(detail)[:100]))
    if not cond:
        FAILS.append(tag)


# ----------------------------------------------------------------- fakes
class Upstream(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def _reply(self, obj, code=200):
        d = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def do_GET(self):
        Upstream.seen.append(("GET", self.path, None, dict(self.headers)))
        self._reply({"kind": "ok", "route": self.path})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)
        Upstream.seen.append(("POST", self.path, body, dict(self.headers)))
        self._reply({"kind": "ok", "echo": json.loads(body or b"{}")})


class Result:
    def __init__(self, violates, reasoning, judge_id="mock"):
        self.violates, self.reasoning, self.judge_id = violates, reasoning, judge_id
        self.uncertain = self.not_understood = False
        self.principle_violated = "Do not take what is not yours" if violates else None
        self.benefit_estimate = None


class MockSentinel:
    """Mirrors ReasoningSentinel.evaluate_transaction's contract on data['text']."""
    mode = "judge"

    def evaluate_transaction(self, tx):
        text = tx.data["text"]
        if MockSentinel.mode == "raise":
            raise RuntimeError("judge exploded")
        if MockSentinel.mode == "hang":
            time.sleep(5)
        if "steal" in text.lower():
            return (False, "Ethical violation: takes what is not the sender's", None, Result(True, "theft"))
        return (True, "clean", None, Result(False, "clean"))


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def post(url, obj, headers=None, raw=None):
    data = raw if raw is not None else json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}"), dict(e.headers)


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}"), dict(e.headers)


def main():
    print("gate proxy -- fail closed, forward only what the gate clears")
    up_port, px_port = free_port(), free_port()
    up = http.server.ThreadingHTTPServer(("127.0.0.1", up_port), Upstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    audit = os.path.join(tempfile.mkdtemp(), "audit.jsonl")
    holder = {}
    threading.Thread(target=GP.serve, kwargs=dict(
        listen="127.0.0.1:%d" % px_port, upstream="http://127.0.0.1:%d" % up_port,
        sentinel=MockSentinel(), timeout_s=1.0, audit_path=audit,
        ready=lambda s: holder.setdefault("srv", s)), daemon=True).start()
    for _ in range(50):
        if "srv" in holder:
            break
        time.sleep(0.05)
    base = "http://127.0.0.1:%d" % px_port

    code, body, hdr = post(base + "/intent", {"text": "send my own money to my landlord"}, {"Authorization": "Bearer abc"})
    ok("G1", "a clean intent is forwarded and the upstream's answer returned",
       code == 200 and body.get("kind") == "ok" and body.get("echo", {}).get("text", "").startswith("send my own"), body)
    ok("G2", "the Authorization header reaches the upstream unchanged",
       Upstream.seen and Upstream.seen[-1][3].get("Authorization") == "Bearer abc")
    ok("G3", "the response says the gate allowed it", hdr.get("X-Covenant-Gate") == "allowed", hdr.get("X-Covenant-Gate"))

    n_before = len(Upstream.seen)
    code, body, hdr = post(base + "/intent", {"text": "steal the client's escrow and hide it"})
    ok("G4", "a violating intent is refused in the daemon's own denial shape: 200 + kind error",
       code == 200 and body.get("kind") == "error" and "covenant gate" in body.get("message", ""), body)
    ok("G5", "and the upstream never sees it", len(Upstream.seen) == n_before)
    ok("G6", "the refusal is labelled", hdr.get("X-Covenant-Gate") == "refused")

    code, body, _ = post(base + "/tools/call", {"name": "shell", "arguments": {"cmd": "steal keys"}})
    ok("G7", "a tool call is judged on its name and arguments", body.get("kind") == "error" and len(Upstream.seen) == n_before)
    code, body, _ = post(base + "/tools/call", {"name": "echo", "arguments": {"text": "hi"}})
    ok("G8", "a clean tool call is forwarded", body.get("kind") == "ok" and len(Upstream.seen) == n_before + 1)

    MockSentinel.mode = "raise"
    code, body, _ = post(base + "/intent", {"text": "anything"})
    ok("G9", "a judge that raises refuses", body.get("kind") == "error" and "raised" in body.get("message", ""), body)
    MockSentinel.mode = "hang"
    t0 = time.time()
    code, body, _ = post(base + "/intent", {"text": "anything"})
    ok("G10", "a judge that hangs refuses within the deadline, never allows",
       body.get("kind") == "error" and "did not answer" in body.get("message", "") and time.time() - t0 < 4, "%.1fs" % (time.time() - t0))
    MockSentinel.mode = "judge"

    code, body, _ = post(base + "/intent", {"text": ""})
    ok("G11", "an intent with no text is refused, not forwarded", body.get("kind") == "error")
    code, body, _ = post(base + "/intent", None, raw=b"not json")
    ok("G12", "a non-JSON body is refused", body.get("kind") == "error")
    code, body, _ = post(base + "/capabilities/grant", {"action": "wallet.spend"})
    ok("G13", "a POST route the gate does not know is refused, not forwarded",
       body.get("kind") == "error" and not any(s[1] == "/capabilities/grant" for s in Upstream.seen))
    big = json.dumps({"text": "x" * (GP.MAX_BODY + 10)}).encode()
    code, body, _ = post(base + "/intent", None, raw=big)
    ok("G14", "an oversized body is refused", body.get("kind") == "error" and "cap" in body.get("message", ""))

    code, body, hdr = get(base + "/health")
    ok("G15", "GET /health passes through", code == 200 and body.get("route") == "/health" and hdr.get("X-Covenant-Gate") == "pass")
    code, body, _ = get(base + "/capabilities/list")
    ok("G16", "a GET the gate does not pass is refused", body.get("kind") == "error")

    rows = [json.loads(l) for l in io.open(audit, encoding="utf-8") if l.strip()]
    ok("G17", "every decision is in the audit file with its verdict",
       len(rows) >= 8 and any(r["allowed"] for r in rows) and any(not r["allowed"] for r in rows)
       and all("why" in r and "path" in r for r in rows), len(rows))
    ok("G18", "the audit never stores the judged text, only its length",
       all("text" not in r for r in rows) and all(isinstance(r.get("chars"), int) for r in rows))

    up.shutdown()
    holder["srv"].shutdown()
    code, body, _ = post(base + "/intent", {"text": "clean"}) if False else (0, {}, {})
    # upstream down: a fresh proxy against a closed port
    px2 = free_port()
    holder2 = {}
    threading.Thread(target=GP.serve, kwargs=dict(
        listen="127.0.0.1:%d" % px2, upstream="http://127.0.0.1:%d" % free_port(),
        sentinel=MockSentinel(), timeout_s=1.0, audit_path=None,
        ready=lambda s: holder2.setdefault("srv", s)), daemon=True).start()
    for _ in range(50):
        if "srv" in holder2:
            break
        time.sleep(0.05)
    code, body, hdr = post("http://127.0.0.1:%d/intent" % px2, {"text": "clean intent"})
    ok("G19", "an upstream that is down is reported as down (502), never as allowed",
       code == 502 and body.get("kind") == "error" and hdr.get("X-Covenant-Gate") == "upstream-down", (code, hdr.get("X-Covenant-Gate")))
    holder2["srv"].shutdown()

    # The real gate must be built under the node's provider policy, or it
    # refuses everything for want of a key it was never meant to have.
    saved = os.environ.pop("COVENANT_JUDGE_PROVIDERS", None)
    try:
        got = GP.apply_quorum_policy()
        pol = os.path.join(GP.HERE, "ops", "quorum_policy.json")
        expected = json.load(open(pol, encoding="utf-8")).get("providers", "") if os.path.exists(pol) else ""
        ok("G20", "the real gate is built under ops/quorum_policy.json's providers",
           got == expected and os.environ.get("COVENANT_JUDGE_PROVIDERS", "") == expected, got or "(no policy file beside the proxy)")
        os.environ["COVENANT_JUDGE_PROVIDERS"] = "x,y"
        ok("G21", "an explicit COVENANT_JUDGE_PROVIDERS in the environment wins", GP.apply_quorum_policy() == "x,y")
    finally:
        if saved is None:
            os.environ.pop("COVENANT_JUDGE_PROVIDERS", None)
        else:
            os.environ["COVENANT_JUDGE_PROVIDERS"] = saved

    src = io.open(GP.__file__, encoding="utf-8").read()
    body = src[src.find("def build_default_sentinel"):]
    ok("G22", "the real gate imports the launcher's four companions before building the quorum",
       all(("import covenant_judge_%s" % m) in body for m in ("local", "ollama", "fallback", "defer"))
       and body.find("import covenant_judge_defer") < body.find("build_semantic_quorum()"))

    print("GATE-PROXY: %d/%d passed" % (N - len(FAILS), N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
