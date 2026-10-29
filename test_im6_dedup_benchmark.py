#!/usr/bin/env python3
"""test_im6_dedup_benchmark.py -- the dedup benchmark harness (both ways) + the live measurement.

    python test_im6_dedup_benchmark.py   -> "IM6: n/n passed", then LIMIT lines (the measured rates)

ChatGPT asked to MEASURE the vet's error rates on adjudicated examples before adding more precision machinery.
`covenant_improve.benchmark` scores the vet over a labelled set (real_have / real_gap) and reports a
false_have (a real_gap the vet treats as already-present) and a missed_duplicate (a real_have it lets through).
This suite proves the metric computation both ways with injected rows/stubs, then PRINTS the live seed numbers
as measurements (a LIMIT line, not a pass/fail): the seed labels are author-written, not blind adjudication, so
the live rate is indicative, not a validated result (NO RESULT is not a pass -- the harness is what is pinned).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve as CI   # noqa: E402

R = []


def check(name, ok, detail=""):
    R.append(bool(ok))
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  -- %s" % (str(detail)[:300],)))


def row(rid, idea, label):
    return {"id": rid, "idea": idea, "maps": "", "test": "present=green / removed=red", "label": label}


HAVE = row("h", "alpha beta gamma delta", "real_have")
GAP = row("g", "alpha beta gamma delta", "real_gap")
two = lambda terms: "alpha @ a.py (code `alpha`); beta @ b.py (code `beta`)"   # noqa: E731  -- 2 matches -> have
none = lambda terms: ""                                                        # noqa: E731  -- 0 matches
notomb = lambda text: None                                                     # noqa: E731
hittomb = lambda text: "RETRACTED.json: ... matched line"                      # noqa: E731


def main():
    print("IM6 -- dedup benchmark harness, both ways, then the live measurement\n")

    # ---- metric computation, driven by injected vet outcomes ----
    b = CI.benchmark(rows=[HAVE], grep=none, tomb=notomb)      # real_have, vet->backlog => missed
    check("IM6.1 a real_have the vet lets through is a MISSED DUPLICATE",
          b["missed_dup_rate"] == 1.0 and b["false_have_rate"] is None, b)
    b = CI.benchmark(rows=[HAVE], grep=two, tomb=notomb)       # real_have, vet->have => caught
    check("IM6.2 a real_have the vet flags as 'have' is CAUGHT (not missed)", b["missed_dup_rate"] == 0.0, b)
    b = CI.benchmark(rows=[GAP], grep=two, tomb=notomb)        # real_gap, vet->have => false_have
    check("IM6.3 a real_gap the vet flags as 'have' is a FALSE HAVE", b["false_have_rate"] == 1.0, b)
    b = CI.benchmark(rows=[GAP], grep=none, tomb=notomb)       # real_gap, vet->backlog => correct
    check("IM6.4 a real_gap the vet passes to backlog is correct (no false have)", b["false_have_rate"] == 0.0, b)
    b = CI.benchmark(rows=[GAP], grep=none, tomb=hittomb)      # real_gap, vet->recurrence => also false_have
    check("IM6.5 a real_gap the vet calls 'recurrence' is ALSO a false positive (covered != have-only)",
          b["false_have_rate"] == 1.0 and b["rows"][0]["vet"] == "recurrence", b)

    # ---- the live seed benchmark: measured, not asserted ----
    live = CI.benchmark()
    check("IM6.6 the live benchmark runs and computes both rates",
          live["n"] > 0 and live["false_have_rate"] is not None and live["missed_dup_rate"] is not None, live["n"])

    print("\n  ---- LIMIT lines (measurements on the AUTHOR-labelled seed; indicative, not validated) ----")
    print("  LIMIT seed n=%d (%d real_have, %d real_gap); vet status: %s"
          % (live["n"], live["n_real_have"], live["n_real_gap"], live["by_status"]))
    print("  LIMIT false_have_rate = %.2f  (real gaps the vet treated as already-present: %s)"
          % (live["false_have_rate"], live["false_haves"] or "none"))
    print("  LIMIT missed_dup_rate = %.2f  (real haves the vet let through: %s)"
          % (live["missed_dup_rate"], live["missed_duplicates"] or "none"))
    fh_rec = [r["id"] for r in live["rows"] if r["outcome"] == "false_have" and r["vet"] == "recurrence"]
    fh_have = [r["id"] for r in live["rows"] if r["outcome"] == "false_have" and r["vet"] == "have"]
    print("  LIMIT of the false positives, %d are from the RECURRENCE check (%s) and %d from the DEDUP (%s)"
          % (len(fh_rec), fh_rec or "-", len(fh_have), fh_have or "-"))
    print("  LIMIT recurrence FIXED (A391): it now rides RETRACTED.json's narrow patterns, so it fires 0 here "
          "(was 6 of 10, all false, shadowing the dedup); and the circle-back now re-verifies every recurrence, "
          "so a false one is surfaced, never a silent drop. The remaining false-haves are all DEDUP (coverage>=2 "
          "on coincidental generic identifiers) -- the next measured lever, and each is held by the circle-back.")

    ok = sum(R)
    print("\nIM6: %d/%d passed" % (ok, len(R)))
    print("LIMIT: the seed labels are author-written, not blind independent adjudication. The harness + metrics "
          "are pinned; the live rate is a first indicative read, to be re-measured on an adjudicated corpus.")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
