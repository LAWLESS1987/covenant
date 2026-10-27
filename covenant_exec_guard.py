#!/usr/bin/env python3
"""covenant_exec_guard.py -- CXR-1 enforcement MECHANISM (shadow-only), built 2026-10-26 after a 7-seat panel
(Tetsu, Codex, Grok, DeepSeek, Mistral, Gemini-Argon, Tien) unanimously picked it as the one item safe to build
now, in one converged scope.

WHAT THIS IS. A pure, side-effect-free evaluator that answers one question at EXECUTION time: given an action,
the declared grant for it, and the current context, is the action REACHABLE (authorized + its contextual limits
still hold) or not? An unauthorized action yields NO execution handle at all -- un-reachable by construction,
not merely a rejection flag (nootxlm / Beforeword, HF 190911; Jang-woo, HF 180541: authority outside the model,
re-checked at execution on an unavoidable path).

WHAT THIS IS NOT. It is OFF BY DEFAULT and not imported by the live executor. It decides nothing live and blocks
nothing: there is NO enforce() that acts. `shadow()` only OBSERVES and LOGS "would have been reachable/unreachable"
with the reason. It is the MECHANISM, never the POLICY -- what counts as authorized is passed IN as the grant,
never baked here, so this file cannot change what the system permits. Wiring it into the live path, switching it
on, or altering what is authorized is the HUMAN-GATED step, and this module never takes it (money, trust-root,
exposure, free will unchanged). Stdlib only.
"""
from __future__ import annotations

import json
import os
import time

# A sentinel the module itself can never flip to live. Enforcement wiring is a human-gated edit elsewhere, not a
# runtime toggle here (DeepSeek: prefer the live path ABSENT, not a deployable switch).
SHADOW_ONLY = True

RESERVED = ("money", "trust-root", "exposure", "free-will")   # capability classes whose POLICY this never changes


def _bound_ok(grant, action, target, args):
    """The handle is bound to the EXACT action/target/args of the grant (TOCTOU: a grant valid at request time
    does not authorize a different target/args at execution)."""
    if grant.get("action") != action:
        return False, "action does not match the grant"
    if "target" in grant and grant.get("target") != target:
        return False, "target changed since the grant (bound mismatch)"
    g_args = grant.get("args")
    if g_args is not None and g_args != (args or {}):
        return False, "args changed since the grant (bound mismatch)"
    return True, "bound"


def evaluate(action, grant, context, target=None, args=None):
    """PURE. Decide reachability at execution time. Returns (reachable: bool, reason: str). Fail-closed: a
    missing/malformed grant, an expired grant, a bound mismatch, or an unmet contextual limit -> NOT reachable."""
    if not isinstance(grant, dict) or not grant:
        return False, "no grant -- fail-closed"
    ok, why = _bound_ok(grant, action, target, args)
    if not ok:
        return False, why
    now = (context or {}).get("now", time.time())
    exp = grant.get("expiry")
    if exp is not None and now > exp:
        return False, "grant expired (re-checked at execution)"
    # contextual limits declared by the grant, re-read against the live context -- the grant says WHAT to check,
    # the context supplies the live values; neither is invented here.
    for key, limit in (grant.get("limits") or {}).items():
        have = (context or {}).get(key)
        if isinstance(limit, (int, float)) and (have is None or have > limit):
            return False, "contextual limit '%s' exceeded (%r > %r)" % (key, have, limit)
        if isinstance(limit, bool) and bool(have) != limit:
            return False, "contextual condition '%s' not met (need %r, have %r)" % (key, limit, have)
    return True, "reachable: authorized, bound, within limits"


def handle(action, grant, context, target=None, args=None):
    """Un-reachable BY CONSTRUCTION: returns an opaque execution handle only if reachable, else None -- an
    unauthorized caller is left with nothing to execute, not a rejected request to retry. Pure; constructs no
    live effect."""
    ok, why = evaluate(action, grant, context, target=target, args=args)
    if not ok:
        return None
    return {"handle": True, "action": action, "target": target, "why": why}


def shadow(action, grant, context, target=None, args=None, log_path=None):
    """OBSERVE-ONLY. Logs the would-be verdict + reason and returns it; NEVER blocks, NEVER raises on a log
    failure, NEVER constructs a live effect. This is the only integration point, and it changes no behavior --
    the divergence log is the human-review artifact for a future, gated decision to wire enforcement live."""
    ok, why = evaluate(action, grant, context, target=target, args=args)
    row = {"would": "reachable" if ok else "unreachable", "reason": why, "action": action,
           "reserved": action in RESERVED, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:                                      # noqa: BLE001 -- a shadow log is never a gate
            pass
    return ok, why


if __name__ == "__main__":
    g = {"action": "FETCH", "target": "https://x.y", "expiry": time.time() + 60, "limits": {"approved": True}}
    print("authorized ->", handle("FETCH", g, {"approved": True}, target="https://x.y") is not None)
    print("wrong target ->", handle("FETCH", g, {"approved": True}, target="https://evil") is None)
    print("not approved ->", handle("FETCH", g, {"approved": False}, target="https://x.y") is None)
