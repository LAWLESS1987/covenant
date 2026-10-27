#!/usr/bin/env python3
"""Show the exec-guard SHADOW divergences: where the capability guard's would-be verdict disagreed with the
door's ACTUAL outcome on a live act. Re-runnable, read-only. Reads ops/exec_guard_shadow.jsonl, which the live
door appends to (observe-only) per act directive since the 2026-10-26 shadow wiring.

A DIVERGENCE (divergent=True) is a would-be mismatch: the guard would have ALLOWED an act the door refused/held,
or would have BLOCKED an act the door ran. Those are the cases to read before deciding whether to define grant
policy and flip enforcement live. Agreements (divergent=False) and ambiguous outcomes (None) are summarised but
not expanded. Usage: python tools/exec_guard_divergences.py [MAX_SHOWN]"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(HERE, "ops", "exec_guard_shadow.jsonl")


def run():
    if not os.path.exists(LOG):
        print("no shadow log yet -- no act directive (FETCH/WEB/HANDS/MOLTBOOK/HEAL/LEG) has fired on a live")
        print("node since the shadow wiring went live. Acts are sporadic; let it gather.")
        return 0
    rows = []
    for line in open(LOG, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    if not rows:
        print("shadow log present but empty.")
        return 0
    by_action = Counter(r.get("action") for r in rows)
    outcomes = Counter(r.get("door_outcome") for r in rows)
    div = [r for r in rows if r.get("divergent") is True]
    undet = [r for r in rows if r.get("divergent") is None]
    agree = [r for r in rows if r.get("divergent") is False]
    print("exec-guard SHADOW log: %d act(s) observed" % len(rows))
    print("  by action:    %s" % dict(by_action))
    print("  door outcome: %s" % dict(outcomes))
    print("  agree: %d  |  DIVERGENT: %d  |  undetermined: %d" % (len(agree), len(div), len(undet)))
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    if div:
        print("\n=== DIVERGENCES (guard would-be verdict != door's actual outcome) ===")
        for r in div[:cap]:
            print("  [%s] %-8s %s | guard=%s (%s) | door=%s"
                  % (r.get("at"), r.get("action"), str(r.get("target"))[:56],
                     r.get("guard_would"), str(r.get("guard_reason"))[:46], r.get("door_outcome")))
    else:
        print("\nNo divergences yet: the guard's verdict matched the door on every classified act.")
    if undet:
        print("\n(%d act(s) had an ambiguous door outcome -> divergence undetermined; raw door_record is in the log.)" % len(undet))
    return 0


if __name__ == "__main__":
    sys.exit(run())
