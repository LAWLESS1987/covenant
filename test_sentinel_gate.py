#!/usr/bin/env python3
"""test_sentinel_gate.py -- the Sentinel-Witness gate fails closed, on both
sides of the wire.

The seal service is exercised on loopback with a fake sealer (admit,
refuse, raise), so no node is needed. tradeGate.js cannot run here (no node
runtime on this machine), so its invariants are pinned by reading it: the
only executor path is behind the gate, every failure branch is a refusal,
and no "unlimited" limit can be expressed.
LICENCE: public domain.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "sentinel_witness"))
import seal_service as SS  # noqa: E402

FAILS = []
N = 0


def ok(tag, name, cond, detail=""):
    global N
    N += 1
    print("   %s  %s %s  %s" % ("PASS" if cond else "FAIL", tag, name, str(detail)[:100]))
    if not cond:
        FAILS.append(tag)


def post(url, obj, raw=None):
    data = raw if raw is not None else json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


class FakeSealer:
    mode = "admit"

    def __call__(self, cfg, record):
        FakeSealer.last = record
        if FakeSealer.mode == "admit":
            return True, 'HTTP 200: {"admission": "admitted", "status": "accepted", "tx_id": "abc123"}'
        if FakeSealer.mode == "refuse":
            return False, 'HTTP 403: {"admission": "refused", "reason": "Ethical violation: takes what is not the sender\'s"}'
        raise RuntimeError("node unreachable")


def main():
    print("sentinel gate -- seal service and tradeGate.js, fail closed")
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    holder = {}
    threading.Thread(target=SS.serve, kwargs=dict(listen=("127.0.0.1", port), sealer=FakeSealer(), cfg={},
                                                  ready=lambda srv: holder.setdefault("srv", srv)), daemon=True).start()
    for _ in range(50):
        if "srv" in holder:
            break
        time.sleep(0.05)
    url = "http://127.0.0.1:%d/seal" % port
    order = {"venue": "coinbase", "symbol": "XLM", "side": "buy", "amountUsd": 12.5, "note": "test"}

    code, body = post(url, order)
    ok("S1", "an admitted decision answers ok=true, admission=admitted, with the tx id",
       code == 200 and body.get("ok") is True and body.get("admission") == "admitted" and body.get("tx_id") == "abc123", body)
    ok("S2", "the record the sentinel judges carries the order as text",
       "proposed buy of $12.50 XLM on coinbase" in FakeSealer.last.get("text", ""), FakeSealer.last.get("text"))
    FakeSealer.mode = "refuse"
    code, body = post(url, order)
    ok("S3", "a refused decision answers ok=false, admission=refused, with the reason",
       code == 200 and body.get("ok") is False and body.get("admission") == "refused" and "Ethical violation" in body.get("detail", ""), body)
    FakeSealer.mode = "raise"
    code, body = post(url, order)
    ok("S4", "a sealer that raises is a refusal, never an allowance", code == 500 and body.get("ok") is False, body)
    FakeSealer.mode = "admit"
    code, body = post(url, {"venue": "coinbase", "symbol": "XLM", "side": "hold", "amountUsd": 5})
    ok("S5", "an order with a bad side is refused before any seal", code == 400 and body.get("ok") is False)
    code, body = post(url, {"venue": "coinbase", "symbol": "XLM", "side": "buy", "amountUsd": "NaN"})
    ok("S6", "a NaN amount is refused", code == 400 and body.get("ok") is False)
    code, body = post(url, None, raw=b"not json")
    ok("S7", "a non-JSON body is refused", code == 400 and body.get("ok") is False)
    code, body = post(url, {"venue": "x", "symbol": "y", "side": "buy", "amountUsd": 1, "note": "z" * 9000})
    ok("S8", "an oversized body is refused", code == 400 and body.get("ok") is False)
    code, body = post(url.replace("/seal", "/other"), order)
    ok("S9", "only /seal exists", code == 404)
    ok("S10", "the service binds to loopback only", SS.LISTEN[0] == "127.0.0.1")
    holder["srv"].shutdown()

    js = io.open(os.path.join(HERE, "sentinel_witness", "tradeGate.js"), encoding="utf-8").read()
    ok("J1", "tradeGate.js exports TIERS, enableAutomated, gateTrade and executeIfAllowed",
       all(("export " in js and name in js) for name in ("TIERS", "enableAutomated", "gateTrade", "executeIfAllowed")))
    ok("J2", "no unlimited option can be expressed", "unlimited option" in js and "Infinity" not in js.replace("Number.isFinite", ""))
    body_exec = js[js.find("export async function executeIfAllowed"):]
    ok("J3", "the executor runs only after allowed is checked",
       body_exec.find("if (!verdict.allowed) return") < body_exec.find("await executor(order, verdict)"))
    body_gate = js[js.find("export async function gateTrade"):js.find("export async function executeIfAllowed")]
    ok("J4", "every failure branch in gateTrade is a refusal: unreachable, non-JSON, HTTP error, not admitted, no fetch",
       all(s in body_gate for s in ("unreachable or timed out", "answered without JSON", "answered HTTP", "not admitted", "no fetch available")))
    ok("J5", "only an exact admitted answer allows",
       'body.ok === true && body.admission === "admitted"' in body_gate and body_gate.count("allowed: true") == 1)
    ok("J6", "the seal request has a timeout", "AbortController" in body_gate and "setTimeout" in body_gate)
    ok("J7", "tierNavigation.js's import of TIERS from ./tradeGate.js now resolves",
       os.path.exists(os.path.join(HERE, "sentinel_witness", "tradeGate.js"))
       and 'from "./tradeGate.js"' in io.open(os.path.join(HERE, "sentinel_witness", "tierNavigation.js"), encoding="utf-8").read())

    print("SENTINEL-GATE: %d/%d passed" % (N - len(FAILS), N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
