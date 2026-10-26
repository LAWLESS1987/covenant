#!/usr/bin/env python3
"""EG1 -- covenant_exec_guard, the shadow-only CXR-1 enforcement mechanism, driven BOTH ways (rule 8): an
authorized, bound, in-limits action is REACHABLE (yields a handle); everything else is UN-REACHABLE (no handle)
-- action mismatch, no grant, a target/args changed since the grant (TOCTOU), an expired grant, an unmet
contextual limit, and malformed input (fail-closed). And: shadow() OBSERVES -- it logs the would-be verdict and
never blocks or raises. Mechanism only; no policy baked, nothing wired live. Stdlib only."""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_exec_guard as G

fails = []


def ok(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:160]))
    if not cond:
        fails.append(name)


GRANT = {"action": "FETCH", "target": "https://x.y", "args": {"depth": 1},
         "expiry": time.time() + 60, "limits": {"approved": True, "amount": 100}}
CTX = {"now": time.time(), "approved": True, "amount": 50}

# --- reachable (the authorized direction): a handle is returned
ok("EG1.1 authorized + bound + in-limits is REACHABLE (a handle is returned)",
   G.handle("FETCH", GRANT, CTX, target="https://x.y", args={"depth": 1}) is not None
   and G.evaluate("FETCH", GRANT, CTX, target="https://x.y", args={"depth": 1})[0] is True)

# --- unreachable (the other direction), one reason at a time: NO handle, with a reason
ok("EG1.2 a mismatched action is UN-REACHABLE (no handle)",
   G.handle("HANDS", GRANT, CTX, target="https://x.y", args={"depth": 1}) is None)
ok("EG1.3 no grant is fail-closed UN-REACHABLE",
   G.handle("FETCH", {}, CTX, target="https://x.y") is None
   and "fail-closed" in G.evaluate("FETCH", {}, CTX, target="https://x.y")[1])
ok("EG1.4 TOCTOU: a target changed since the grant is UN-REACHABLE (bound mismatch)",
   G.handle("FETCH", GRANT, CTX, target="https://evil", args={"depth": 1}) is None
   and "bound mismatch" in G.evaluate("FETCH", GRANT, CTX, target="https://evil", args={"depth": 1})[1])
ok("EG1.5 TOCTOU: args changed since the grant is UN-REACHABLE",
   G.handle("FETCH", GRANT, CTX, target="https://x.y", args={"depth": 9}) is None)
ok("EG1.6 an expired grant is UN-REACHABLE (re-checked at execution)",
   G.handle("FETCH", dict(GRANT, expiry=time.time() - 1), CTX, target="https://x.y", args={"depth": 1}) is None)
ok("EG1.7 an unmet contextual limit (amount over) is UN-REACHABLE",
   G.handle("FETCH", GRANT, dict(CTX, amount=500), target="https://x.y", args={"depth": 1}) is None)
ok("EG1.8 an unmet contextual condition (not approved) is UN-REACHABLE",
   G.handle("FETCH", GRANT, dict(CTX, approved=False), target="https://x.y", args={"depth": 1}) is None)
ok("EG1.9 malformed grant is fail-closed, not fail-open", G.handle("FETCH", None, CTX, target="https://x.y") is None)

# --- shadow() OBSERVES: logs the would-be verdict both ways, never blocks, never raises
d = tempfile.mkdtemp()
logp = os.path.join(d, "shadow.jsonl")
r_ok = G.shadow("FETCH", GRANT, CTX, target="https://x.y", args={"depth": 1}, log_path=logp)
r_no = G.shadow("FETCH", GRANT, CTX, target="https://evil", args={"depth": 1}, log_path=logp)
rows = [json.loads(x) for x in open(logp, encoding="utf-8")]
ok("EG1.10 shadow() logs BOTH a would-be-reachable and a would-be-unreachable, with reasons, and blocks nothing",
   r_ok[0] is True and r_no[0] is False and len(rows) == 2
   and rows[0]["would"] == "reachable" and rows[1]["would"] == "unreachable", rows)
ok("EG1.11 shadow() never raises on a bad log path (observe-only is never a gate)",
   isinstance(G.shadow("FETCH", GRANT, CTX, target="https://x.y", args={"depth": 1},
                       log_path=os.path.join(d, "nope", "x.jsonl")), tuple))

# --- mechanism-not-wired: there is NO live enforce() entry that acts; only evaluate/handle/shadow, and
#     SHADOW_ONLY stands. Pins that this file cannot switch itself live.
ok("EG1.12 no live-enforce entry exists; SHADOW_ONLY holds (activation is a human-gated edit elsewhere)",
   G.SHADOW_ONLY is True and not hasattr(G, "enforce") and callable(G.shadow) and callable(G.evaluate))

print("\nEG1: %d/12 passed" % (12 - len(fails)))
raise SystemExit(1 if fails else 0)
