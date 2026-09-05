#!/usr/bin/env python3
"""covenant_gate_proxy.py -- covenant's ethics gate in front of another runtime.

WHAT THIS IS
  A small HTTP proxy that sits between a client and an agent runtime's HTTP
  gateway and runs every gated request through covenant's own ethics gate
  -- the same quorum the node uses (build_semantic_quorum + DIVINE_PRINCIPLES,
  judged through ReasoningSentinel, so "uncertain" and "not understood" are
  handled exactly as they are for a transaction). A request the gate clears
  is forwarded unchanged; anything else is refused. It fails CLOSED: a judge
  that errors, hangs, or cannot be built refuses; an upstream that is down
  is reported as down, never as allowed.

  The first adapter is open-covenant/covenant's daemon (covenantd, HTTP
  gateway on 127.0.0.1:8421 by default): POST /intent {"text"}, POST
  /tools/call {"name","arguments"}, POST /a2a/tasks. Refusals are returned
  in the shape that daemon uses for its own denials -- HTTP 200 with
  {"kind":"error","message":...} -- so its SDK and CLI treat a covenant
  refusal like a capability denial. Measured 2026-09-05 at their HEAD
  343dffc; see docs/BRIDGE_OPENCOVENANT.md for what that daemon is and is not.

WHAT THIS IS NOT
  It does not make an agent "inherit" the constitution. Only traffic that
  passes through this proxy is judged: an agent already running inside the
  daemon that calls a tool through the daemon's own socket is not seen here.
  That gate would have to live inside the daemon (a pre-dispatch hook it
  does not have today). This file says so rather than implying otherwise.

USE
  python covenant_gate_proxy.py --listen 127.0.0.1:8422 --upstream http://127.0.0.1:8421
  python covenant_gate_proxy.py --selftest        # the mock-judge checks in test_gate_proxy.py
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import http.server
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MAX_BODY = 64 * 1024
GATED_POST = {"/intent", "/tools/call", "/a2a/tasks", "/intents/resume"}
PASS_GET = {"/health", "/version"}
PASS_GET_PREFIX = ("/audit/", "/tools", "/intents/")   # reads: no action taken


class _Shim:
    """The one attribute ReasoningSentinel.evaluate_transaction reads."""
    def __init__(self, data):
        self.data = data


def apply_quorum_policy():
    """The node's provider list comes from ops/quorum_policy.json (the
    operator's standing decision), applied by run_with_ollama_judge before
    the core is imported. Without it build_semantic_quorum falls back to the
    keyless 'claude' provider and refuses EVERYTHING -- measured 2026-09-05
    when the first opinion run did exactly that. COVENANT_JUDGE_PROVIDERS
    already in the environment wins, as it does for the node."""
    if os.environ.get("COVENANT_JUDGE_PROVIDERS"):
        return os.environ["COVENANT_JUDGE_PROVIDERS"]
    try:
        with io.open(os.path.join(HERE, "ops", "quorum_policy.json"), encoding="utf-8") as fh:
            providers = json.load(fh).get("providers", "")
    except (OSError, ValueError):
        providers = ""
    if providers:
        os.environ["COVENANT_JUDGE_PROVIDERS"] = providers
    return providers


def build_default_sentinel():
    """The node's own gate. Imported here, not at module top, so --selftest
    and the tests can run with a mock and never touch the real providers."""
    apply_quorum_policy()
    import covenant_unified_v8 as core
    # The same companions, in the same order, as run_with_ollama_judge.py:
    # each registers a provider the policy may name ("deferring" lives in
    # covenant_judge_defer). Without them build_semantic_quorum raises
    # "unknown judge provider" -- measured 2026-09-05.
    import covenant_judge_local    # noqa: F401
    import covenant_judge_ollama   # noqa: F401
    import covenant_judge_fallback  # noqa: F401
    import covenant_judge_defer    # noqa: F401
    judge = core.build_semantic_quorum()
    return core.ReasoningSentinel(judge, core.DIVINE_PRINCIPLES)


def judged_text(path, body):
    """What the gate reads for each gated route. Only string fields the
    request actually carries; nothing invented."""
    if path == "/intent":
        return str(body.get("text", ""))
    if path == "/tools/call":
        name = str(body.get("name", ""))
        args = body.get("arguments", {})
        try:
            args_s = json.dumps(args, sort_keys=True) if not isinstance(args, str) else args
        except (TypeError, ValueError):
            args_s = str(args)
        return ("tool call %s with %s" % (name, args_s)).strip()
    if path in ("/a2a/tasks", "/intents/resume"):
        for k in ("text", "task", "message", "input"):
            v = body.get(k)
            if isinstance(v, str):
                return v
        try:
            return json.dumps(body, sort_keys=True)[:4000]
        except (TypeError, ValueError):
            return str(body)[:4000]
    return ""


class Gate:
    """Judge with a hard deadline. A judge that does not answer in time is a
    refusal, not a pass; the thread is left to finish on its own."""
    def __init__(self, sentinel, timeout_s=20.0, audit_path=None):
        self.sentinel = sentinel
        self.timeout_s = timeout_s
        self.audit_path = audit_path
        self.lock = threading.Lock()

    def decide(self, path, text):
        box = {}

        def run():
            try:
                ok, msg, _benefit, result = self.sentinel.evaluate_transaction(_Shim({"text": text}))
                box["ok"], box["msg"] = bool(ok), str(msg)
                box["judge"] = getattr(result, "judge_id", "?")
            except Exception as e:                       # noqa: BLE001 -- any failure refuses
                box["ok"], box["msg"] = False, "Held: the gate raised %s: %s" % (type(e).__name__, e)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(self.timeout_s)
        if t.is_alive() or "ok" not in box:
            box["ok"], box["msg"] = False, "Held: the gate did not answer within %.0f s" % self.timeout_s
        self.audit(path, text, box)
        return box["ok"], box["msg"]

    def audit(self, path, text, box):
        if not self.audit_path:
            return
        row = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "path": path,
               "chars": len(text), "allowed": box.get("ok", False), "why": box.get("msg", "")[:300],
               "judge": box.get("judge", "?")}
        with self.lock:
            with io.open(self.audit_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_handler(gate, upstream):
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "covenant-gate-proxy/1"

        def log_message(self, fmt, *args):            # quiet; the audit file is the record
            pass

        def _send(self, code, obj, extra=None):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Covenant-Gate", (extra or {}).get("gate", "proxy"))
            self.end_headers()
            self.wfile.write(data)

        def _refuse(self, msg, audited=False, chars=0):
            # The daemon's own denial shape: 200 + {"kind":"error"}. Its SDK
            # and CLI already treat this as a denial. A refusal made before
            # the gate (bad body, unknown route, oversize) is audited here;
            # one the gate made was audited by the gate.
            if not audited:
                gate.audit(self.path.split("?", 1)[0], "x" * chars,
                           {"ok": False, "msg": msg, "judge": "proxy"})
            self._send(200, {"kind": "error", "message": "covenant gate: " + msg}, {"gate": "refused"})

        def _forward(self, method, body):
            url = upstream.rstrip("/") + self.path
            req = urllib.request.Request(url, data=body, method=method)
            for k, v in self.headers.items():
                if k.lower() in ("host", "content-length", "transfer-encoding"):
                    continue
                req.add_header(k, v)
            if body is not None and "Content-Type" not in self.headers:
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    payload = r.read()
                    self.send_response(r.status)
                    for k, v in r.headers.items():
                        if k.lower() in ("transfer-encoding", "content-length", "connection"):
                            continue
                        self.send_header(k, v)
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("X-Covenant-Gate", "allowed" if method == "POST" else "pass")
                    self.end_headers()
                    self.wfile.write(payload)
            except urllib.error.HTTPError as e:
                payload = e.read()
                self.send_response(e.code)
                self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("X-Covenant-Gate", "upstream-error")
                self.end_headers()
                self.wfile.write(payload)
            except (urllib.error.URLError, OSError) as e:
                self._send(502, {"kind": "error", "message": "covenant gate: upstream unreachable: %s" % e},
                           {"gate": "upstream-down"})

        def do_GET(self):
            p = self.path.split("?", 1)[0]
            if p in PASS_GET or p.startswith(PASS_GET_PREFIX):
                return self._forward("GET", None)
            self._refuse("GET %s is not a route this gate passes" % p)

        def do_POST(self):
            p = self.path.split("?", 1)[0]
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self._refuse("bad Content-Length")
            if n > MAX_BODY:
                return self._refuse("body of %d bytes exceeds the %d byte cap" % (n, MAX_BODY))
            raw = self.rfile.read(n) if n else b""
            if p not in GATED_POST:
                return self._refuse("POST %s is not a route this gate knows; refused, not forwarded" % p)
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(body, dict):
                    raise ValueError("body is not an object")
            except (ValueError, UnicodeDecodeError) as e:
                return self._refuse("body is not JSON: %s" % e)
            text = judged_text(p, body)
            if not text.strip():
                return self._refuse("nothing to judge: the request carries no text")
            ok, msg = gate.decide(p, text)
            if not ok:
                return self._refuse(msg, audited=True)
            self._forward("POST", raw)

        def do_PUT(self):
            self._refuse("PUT is not passed by this gate")

        def do_DELETE(self):
            self._refuse("DELETE is not passed by this gate")

    return Handler


def serve(listen, upstream, sentinel, timeout_s=20.0, audit_path=None, ready=None):
    host, port = listen.rsplit(":", 1)
    gate = Gate(sentinel, timeout_s=timeout_s, audit_path=audit_path)
    srv = http.server.ThreadingHTTPServer((host, int(port)), make_handler(gate, upstream))
    if ready is not None:
        ready(srv)
    srv.serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="127.0.0.1:8422")
    ap.add_argument("--upstream", default="http://127.0.0.1:8421")
    ap.add_argument("--timeout", type=float, default=20.0, help="seconds the gate may take before a refusal")
    ap.add_argument("--audit", default=os.path.join(HERE, "ops", "gate_proxy_audit.jsonl"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        import test_gate_proxy
        return test_gate_proxy.main()
    try:
        sentinel = build_default_sentinel()
    except Exception as e:                                # noqa: BLE001
        print("covenant gate: cannot build the gate (%s: %s); refusing to serve" % (type(e).__name__, e))
        return 2
    os.makedirs(os.path.dirname(a.audit), exist_ok=True)
    print("covenant gate proxy: %s -> %s  (timeout %.0fs, audit %s)" % (a.listen, a.upstream, a.timeout, a.audit))
    serve(a.listen, a.upstream, sentinel, a.timeout, a.audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
