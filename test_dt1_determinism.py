#!/usr/bin/env python3
"""DT1 -- the determinism probe (tools/determinism_probe.py), driven BOTH ways (rule 8): a DECLARED filler
(identical every run) reads as 'declared' with no slot guessing; a GUESSING filler (one slot varies) reads as
'guessing' and names the varying slot while the stable slot stays stable. Plus: a failed run is RECORDED not
dropped, and an all-failed probe is NO-RESULT, never a silent pass. No model needed (the live leg helper is not
exercised here -- it needs the reasoning leg up). Stdlib only."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import determinism_probe as D

fails = []


def ok(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:160]))
    if not cond:
        fails.append(name)


# --- DECLARED: same slots every run -> 'declared', nothing guessing (the grounded direction)
def declared():
    return {"target": "/declared/path", "action": "read", "amount": 10}


rep_declared = D.probe(declared, reps=5)
ok("DT1.1 a declared (deterministic) fill reads as 'declared' with no guessed slot",
   rep_declared["verdict"] == "declared" and rep_declared["guessing"] == []
   and all(s["stable"] for s in rep_declared["slots"].values()), rep_declared)

# --- GUESSING: one slot varies each run -> 'guessing', that slot named, the declared slot still stable
_c = {"n": 0}


def guessing():
    _c["n"] += 1
    return {"target": "/declared/path", "action": "read", "amount": _c["n"]}   # amount is never pinned -> guessed


rep_guess = D.probe(guessing, reps=4)
ok("DT1.2 a guessed slot (varies run to run) is caught: verdict 'guessing', the slot named",
   rep_guess["verdict"] == "guessing" and "amount" in rep_guess["guessing"]
   and rep_guess["slots"]["amount"]["distinct"] == 4, rep_guess)
ok("DT1.3 ...and the declared slots beside it stay stable (the probe is specific, not 'everything varies')",
   rep_guess["slots"]["target"]["stable"] and rep_guess["slots"]["action"]["stable"]
   and "target" not in rep_guess["guessing"], rep_guess)

# --- a failed run is RECORDED, not dropped ('a log of only successes lies'); stability is over the good runs
_c2 = {"n": 0}


def flaky():
    _c2["n"] += 1
    if _c2["n"] == 2:
        raise ValueError("boom")
    return {"x": 1}


rep_flaky = D.probe(flaky, reps=3)
ok("DT1.4 a failed run is recorded (errors kept, reps counts it), not silently dropped",
   rep_flaky["reps"] == 3 and rep_flaky["ok_runs"] == 2 and rep_flaky["errors"] == ["ValueError"], rep_flaky)
ok("DT1.5 ...and stability is judged over the SUCCESSFUL runs (identical x=1 -> declared, error not a 'guess')",
   rep_flaky["verdict"] == "declared" and rep_flaky["guessing"] == [], rep_flaky)

# --- all runs fail -> NO-RESULT, never a silent pass and never mislabelled as guessing (A129 / rule 9)
rep_dead = D.probe(lambda: (_ for _ in ()).throw(RuntimeError("down")), reps=3)
ok("DT1.6 an all-failed probe is NO-RESULT, not a pass and not 'guessing'",
   rep_dead["verdict"] == "no-result" and rep_dead["ok_runs"] == 0 and len(rep_dead["errors"]) == 3, rep_dead)

# --- reps floor: reps<1 still runs once (a probe that runs zero times measures nothing)
rep_one = D.probe(declared, reps=0)
ok("DT1.7 reps<1 still runs once (never zero runs)", rep_one["reps"] == 1 and rep_one["ok_runs"] == 1, rep_one)

# --- a scalar (non-dict) fill is handled, not crashed
rep_scalar = D.probe(lambda: "same", reps=3)
ok("DT1.8 a scalar fill is wrapped and judged stable", rep_scalar["verdict"] == "declared"
   and rep_scalar["slots"].get("_value", {}).get("stable"), rep_scalar)

print("\nDT1: %d/8 passed" % (8 - len(fails)))
raise SystemExit(1 if fails else 0)
