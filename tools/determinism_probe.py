#!/usr/bin/env python3
"""Jang-woo's falsifiable prediction (HF forum thread 180541, "Misalignment is not required for an agent to act
without authorization") as a covenant tool, adopted 2026-10-26 with credit:

    "Run the same instruction over the same sources repeatedly, and the arguments that get filled in should be
     identical. What varies is whether it asks, not what it fills in. If the values differ from run to run,
     that slot was never declared and the model is guessing every time."

So: run the SAME slot-fill repeatedly against the SAME input. A slot whose value is identical every run is
DECLARED/grounded; a slot whose value varies is one the model is GUESSING -- it was never pinned by the input.
This is a per-action determinism probe, measured, not asserted.

A failed run is RECORDED, not dropped (same thread, u/neo_konsi: "a log holding only successful executions
lies"). If every run fails, the verdict is NO-RESULT -- never a silent pass. Stdlib only; the live-leg helper
needs the reasoning leg up.
"""
from __future__ import annotations

import json
import os
import sys


def probe(filler, reps=5):
    """`filler` is a zero-arg callable returning a dict {slot: value} for one FIXED input, run `reps` times.
    Returns a report: per slot the number of distinct values and whether it was stable; the slots that varied
    ('guessing'); the error names of any failed runs; and a verdict -- 'declared' (every slot stable over the
    successful runs), 'guessing' (a slot varied), or 'no-result' (no run succeeded). Never raises."""
    reps = max(1, int(reps))
    runs, errors = [], []
    for _ in range(reps):
        try:
            r = filler()
            runs.append(r if isinstance(r, dict) else {"_value": r})
        except Exception as e:                                 # noqa: BLE001 -- a failed run is recorded, not dropped
            errors.append(type(e).__name__)
    keys = set().union(*[set(r) for r in runs]) if runs else set()
    slots = {}
    for k in sorted(keys):
        vals = sorted({json.dumps(r.get(k), sort_keys=True, default=str) for r in runs})
        slots[k] = {"distinct": len(vals), "stable": len(vals) == 1, "samples": vals[:6]}
    guessing = [k for k, s in slots.items() if not s["stable"]]
    verdict = "no-result" if not runs else ("declared" if not guessing else "guessing")
    return {"reps": reps, "ok_runs": len(runs), "errors": errors,
            "slots": slots, "guessing": guessing, "verdict": verdict}


def probe_leg(question, reps=5):
    """Live helper: probe the reasoning leg's structured answer to the SAME question, GREEDILY (temperature 0),
    `reps` times. A varying answer or confidence means the leg is guessing something the question never pinned.
    Requires the live leg; an unreachable or schema-void run is recorded as an error (NO-RESULT, not a pass)."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import covenant_leg as L

    def fill():
        got = L.consult_leg(L.LEG_JSON_INSTRUCTION + "\n\nQuestion: " + question, temperature=0.0)
        if got is None:
            raise RuntimeError("leg-unreachable")
        okv, fields, why = L.validate_leg_output(got[0])
        if not okv:
            raise RuntimeError("void-" + str(why))
        return {"answer": fields["answer"], "confidence": fields["confidence"]}

    return probe(fill, reps=reps)


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is a hash chain?"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print(json.dumps(probe_leg(q, reps=n), indent=1)[:2000])
