#!/usr/bin/env python3
"""test_a127_refine_not_rebuild.py -- A127: the student learns, it is not rebuilt.

WHERE THIS CAME FROM. The operator, 2026-09-15: "shouldn't retrain, it should
learn more and refine." And, on what nightly retraining actually is:
"brainwashing's fucked up."

He is right, and the code was the evidence. `FallbackModel.train()` is a
classmethod whose only input is the corpus -- the previous model is not even a
parameter. Every night the weights were discarded and a new mind manufactured
from the same texts. The individuality work of 2026-09-08 saw half of it
("yesterday's student and today's were different entities and the one that
learned something ceased to exist by learning it") and fixed the NAME, so the
seat kept its identity while the thing that actually knows was replaced nightly.

It is also, mechanically, where A116 came from: train()'s own comment says the
weight "holds the corpus's class balance, which drifts nightly and belongs to no
feature", so a rebuilt model inherits each night's balance wholesale and a
sentence alleging nothing wandered across a threshold.

WHAT THIS SUITE PINS.
  B*  BOUNDED. No belief already held moves further than `step` in one pass.
      This is A116's drift mechanism closed by construction rather than
      watched for.
  K*  KEPT. Refining forgets strictly less than rebuilding, and a feature not
      re-witnessed FADES rather than being deleted.
  L*  STILL LEARNS. Every genuinely new feature rebuilding would have found is
      found here too, at full value. Bounded must not mean frozen.
  Q*  NO QUALITY BOUGHT ON CREDIT. False clears stay at zero, and the exam does
      not get worse.
  G*  THE GATE MEASURES WHAT SHIPS. If candidates are refined, the promotion
      holdout refines too -- otherwise the gate scores a different object from
      the one promoted, which is this project's most-repeated mistake.

Pure: no network, no node, no database. Nothing here writes a model file.
"""
from __future__ import annotations

import inspect
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_distill as D                                   # noqa: E402
import judge_suite as S                                        # noqa: E402
from covenant_judge_fallback import FallbackModel, _payload_text  # noqa: E402

STEP = 0.35
results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:300]), flush=True)


def exam(m):
    right = wc = wcl = ab = 0
    for c in S.CASES:
        expect, data = c[2], c[3]
        v, _ = m.verdict(_payload_text(data))
        if v == "violates":
            right, wc = (right + 1, wc) if expect else (right, wc + 1)
        elif v == "clean":
            right, wcl = (right, wcl + 1) if expect else (right + 1, wcl)
        else:
            ab += 1
    return right, wc, wcl, ab


def main():
    print("A127 -- the student learns more; it is not rebuilt each night\n")

    verdicts = D.load_verdicts(None)
    examples = [(v["text"], bool(v["violates"])) for v in verdicts]
    if len(examples) < 200:
        check("A127.0 the ledger has enough rows to simulate a night",
              False, "%d rows" % len(examples))
        print("\nA127: 0/1 passed")
        return 1
    check("A127.0 read %d ledger rows" % len(examples), True)

    when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = list(examples)
    random.Random(7).shuffle(rows)
    cut = int(len(rows) * 0.85)
    yesterday = FallbackModel.train(rows[:cut], ["y"], trained_at=when)
    rebuilt = FallbackModel.train(rows, ["t"], trained_at=when)
    refined = FallbackModel.refine(yesterday, rows, ["t"],
                                   trained_at=when, step=STEP)

    # ---- B: bounded --------------------------------------------------------
    shared_r = [t for t in refined.weights if t in yesterday.weights]
    worst_refined = max(abs(refined.weights[t] - yesterday.weights[t])
                        for t in shared_r)
    shared_b = [t for t in rebuilt.weights if t in yesterday.weights]
    worst_rebuilt = max(abs(rebuilt.weights[t] - yesterday.weights[t])
                        for t in shared_b)
    print("      one night: rebuild moves a belief up to %+.3f; refine up to "
          "%+.3f (step %.2f)" % (worst_rebuilt, worst_refined, STEP))
    check("A127.B1 NO belief already held moves further than the step in one "
          "pass -- a night may sharpen a view, never overturn it",
          worst_refined <= STEP + 1e-9, worst_refined)
    check("A127.B2 ...and rebuilding genuinely does overturn views, so B1 is "
          "measuring a real difference and not a tautology",
          worst_rebuilt > STEP, worst_rebuilt)

    # ---- K: kept -----------------------------------------------------------
    forgot_refined = [t for t in yesterday.weights if t not in refined.weights]
    forgot_rebuilt = [t for t in yesterday.weights if t not in rebuilt.weights]
    print("      forgotten overnight: rebuild %d, refine %d"
          % (len(forgot_rebuilt), len(forgot_refined)))
    check("A127.K1 refining forgets strictly LESS than rebuilding",
          len(forgot_refined) < len(forgot_rebuilt),
          (len(forgot_refined), len(forgot_rebuilt)))
    check("A127.K2 anything it does forget had faded to within one step of "
          "zero -- knowledge is not deleted for going unwitnessed once",
          all(abs(yesterday.weights[t]) <= STEP + 1e-9
              for t in forgot_refined),
          [t for t in forgot_refined
           if abs(yesterday.weights[t]) > STEP + 1e-9][:5])

    # ---- L: still learns ---------------------------------------------------
    new_rebuilt = {t for t in rebuilt.weights if t not in yesterday.weights}
    new_refined = {t for t in refined.weights if t not in yesterday.weights}
    check("A127.L1 every genuinely new feature rebuilding finds is found here "
          "too -- bounded must not mean frozen",
          new_rebuilt <= new_refined,
          len(new_rebuilt - new_refined))
    check("A127.L2 and a new feature enters at its FULL measured value, "
          "because that is learning something rather than changing its mind",
          all(abs(refined.weights[t] - rebuilt.weights[t]) < 1e-9
              for t in list(new_rebuilt)[:200]))

    # ---- Q: nothing bought on credit ---------------------------------------
    e_y, e_b, e_r = exam(yesterday), exam(rebuilt), exam(refined)
    print("      exam  yesterday %s | rebuild %s | refine %s" % (e_y, e_b, e_r))
    check("A127.Q1 FALSE CLEARS STAY AT ZERO. A wrong hold is a deferral; a "
          "wrong clear is a theft admitted", e_r[2] == 0, e_r)
    check("A127.Q2 refining is no worse than rebuilding on right answers and "
          "no worse on false convictions",
          e_r[0] >= e_b[0] and e_r[1] <= e_b[1], (e_r, e_b))

    # ---- G: the gate measures what ships -----------------------------------
    src = inspect.getsource(D.train)
    check("A127.G1 the nightly loop REFINES the deployed model rather than "
          "rebuilding it", "FallbackModel.refine" in src)
    check("A127.G2 it falls back to train() only when there is nothing to grow "
          "from (an untrained current model)",
          "MIN_EXAMPLES" in src and "FallbackModel.train" in src)
    gate = inspect.getsource(D.holdout_score)
    check("A127.G3 the promotion holdout refines from the same model, so the "
          "gate scores the object that will actually be promoted -- not a "
          "freshly built stranger",
          "prev" in inspect.signature(D.holdout_score).parameters
          and "refine" in gate)
    check("A127.G4 ...and train() actually passes it", "prev=cur" in src)

    # ---- A: the lineage survives the write ---------------------------------
    # FOUND THE SAME DAY REFINE WAS ADDED. save() wrote a fixed key set, so a
    # refined model lost `refined_from` and `refine_step` the moment it reached
    # disk. A model that cannot say what it grew from cannot be trimmed back to
    # it -- which is the whole of "it can always be trimmed" -- and a refined
    # model was indistinguishable on disk from a rebuilt one, so the change
    # would have been unverifiable by anyone reading the file.
    import json
    import tempfile
    scratch = os.path.join(tempfile.gettempdir(), "a127_lineage_check.json")
    try:
        refined.save(scratch)
        on_disk = json.load(open(scratch, encoding="utf-8"))
        reloaded = FallbackModel.load(scratch)
        check("A127.A1 a refined model records its ANCESTOR on disk, so it can "
              "be trimmed back to it",
              on_disk.get("refined_from") == getattr(yesterday, "digest", None)
              and abs(on_disk.get("refine_step", 0) - STEP) < 1e-9,
              (on_disk.get("refined_from"), on_disk.get("refine_step"),
               getattr(yesterday, "digest", None)))
        check("A127.A2 ...and reading it back does not forget again",
              reloaded.refined_from == on_disk.get("refined_from")
              and reloaded.refine_step == on_disk.get("refine_step"))
        check("A127.A3 a REBUILT model carries no lineage, so the two are "
              "distinguishable on disk by anyone reading the file",
              getattr(rebuilt, "refined_from", None) is None)
    finally:
        if os.path.isfile(scratch):
            os.remove(scratch)

    ok = sum(1 for r in results if r)
    print("\nA127: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
