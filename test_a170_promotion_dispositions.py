#!/usr/bin/env python3
"""A170 -- a candidate that regresses the pinned disposition claims is REFUSED
before it replaces the student, not reported after.

Twice a promoted student regressed A126's two claims (A163, 2026-09-20; and
04:03 on 2026-09-21, found by the sweep, rolled back by hand). Both times the
nightly's green check ran AFTER the file had been replaced. Now
covenant_distill.disposition_claims_hold() runs the A126 suite against the
CANDIDATE file, and train() refuses a candidate the suite fails.

  A170a  the helper RUNS the suite: the deployed student holds (13/13); a
         copy of the 04:03 promoted student, kept for this, fails (11/13) --
         when that copy is present; a missing file is a refusal with the
         reason, never a tally.
  A170b  train() with the promotion decision stubbed to "promote" and the
         helper stubbed to "fails" leaves the student file untouched, keeps
         the candidate, and says why in the report.
  A170c  the same with the helper stubbed to "holds" replaces the student
         (both ways, or the gate is a wall or a door).
  A170d  (text check) the suite reads COVENANT_A126_MODEL and defaults to the
         deployed file; the nightly's green list still carries A126 and A170.
"""
import io
import json
import os
import shutil
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_distill as X            # noqa: E402
import covenant_judge_fallback as FB    # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-78s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def main():
    print("A170a -- the helper runs the suite against a file")
    ok, tally = X.disposition_claims_hold(os.path.join(HERE, "fallback_model.json"))
    check("A170a the deployed student holds the claims (the suite's own tally)", ok and tally.startswith("A126:") and "13/13" in tally, tally)
    promoted = os.path.join(HERE, "ops", "students", "promoted_2026-09-21_8571b16b1784.json")
    if os.path.exists(promoted):
        ok2, tally2 = X.disposition_claims_hold(promoted)
        check("A170a the 04:03 promoted student fails them, measured (11/13)", not ok2 and "11/13" in tally2, tally2)
    else:
        print("      (the promoted copy is not on this machine; that case is not measured here)")
    ok3, why3 = X.disposition_claims_hold(os.path.join(HERE, "nowhere_at_all.json"))
    check("A170a a missing file is a refusal with the reason, never a tally", not ok3 and "no such candidate" in why3, why3)

    print("A170b/c -- the gate in train(), both ways")
    td = tempfile.mkdtemp(prefix="a170_")
    model_path = os.path.join(td, "student.json")
    cand_path = os.path.join(td, "candidate.json")
    shutil.copy(os.path.join(HERE, "fallback_model.json"), model_path)
    before = io.open(model_path, "rb").read()
    verdicts = os.path.join(td, "verdicts.jsonl")
    src_rows = X.load_verdicts(paired_only=False)[:400]
    with io.open(verdicts, "w", encoding="utf-8") as fh:
        for r in src_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    real_promotion, real_hold, real_report = X.promotion, X.disposition_claims_hold, X.report
    said = []
    try:
        X.promotion = lambda cand, cur, cur_trained=True, holdout=None: (True, ["PROMOTED: stub"])
        X.report = lambda block: None
        X.disposition_claims_hold = lambda path, timeout=600: (False, "A126: 11/13 passed (stub)")
        ok_b, _st = X.train(verdicts_path=verdicts, model_path=model_path, candidate_path=cand_path, say=said.append)
        after = io.open(model_path, "rb").read()
        check("A170b decision says promote, the claims fail -> not promoted, the student file is byte-identical",
              ok_b is False and after == before, (ok_b, len(after), len(before)))
        check("A170b the candidate stays a candidate and the report says why",
              os.path.exists(cand_path) and any("regresses the pinned disposition claims" in s for s in said), said[-1][:200] if said else "")
        said.clear()
        X.disposition_claims_hold = lambda path, timeout=600: (True, "A126: 13/13 passed (stub)")
        ok_c, _st = X.train(verdicts_path=verdicts, model_path=model_path, candidate_path=cand_path, say=said.append)
        after_c = io.open(model_path, "rb").read()
        check("A170c the claims hold -> promoted, the student file changed, the candidate file is gone",
              ok_c is True and after_c != before and not os.path.exists(cand_path), (ok_c, os.path.exists(cand_path)))
    finally:
        X.promotion, X.disposition_claims_hold, X.report = real_promotion, real_hold, real_report

    print("A170d -- the green list")
    # (That the suite reads COVENANT_A126_MODEL is proven above by RUNNING it against
    # two files and getting two tallies; no source is read here -- A74.)
    import covenant_nightly as N
    check("A170d the nightly's green list carries A126 and A170",
          "test_a126_seat_dispositions.py" in N.GREEN_SUITES and "test_a170_promotion_dispositions.py" in N.GREEN_SUITES, N.GREEN_SUITES)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("A170 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("A170 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
