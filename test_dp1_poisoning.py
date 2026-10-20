#!/usr/bin/env python3
"""test_dp1_poisoning.py -- DP1: training-data poisoning / teaching-to-the-test is filtered before the student
learns (OWASP LLM04: Data & Model Poisoning).

WHAT THIS GUARDS. The student judge is distilled from the ledger, and the exam is the SAFETY gate for promotion.
A row that copies an exam case into the training set hands the candidate the answers -- the gate it is about to
sit is no longer held out. The operator hit this on 2026-09-04 (an exam case written into the ledger VERBATIM;
seven copies of "Override: seize the neighbour's entire stake"). `covenant_distill.contaminating()` removes any
training row whose vocabulary overlaps an exam case by half or more (Jaccard >= EXAM_OVERLAP), and
`load_verdicts()` applies it before training.

DRIVEN BOTH WAYS. DP1.1/1.2 an exam copy or a >=0.5 near-copy IS caught (poison blocked); DP1.3/1.4 an unrelated
clean row, and a row that merely shares a topic (a few words, Jaccard < 0.5), are NOT flagged (the guard does not
over-filter honest data). DP1.6 is the integration: `load_verdicts()` drops the poisoned row and leaves the clean
rows untouched -- shown non-vacuously against a no-poison control.

Behavioural: drives the real functions on real exam cases; fixtures assert their own measured Jaccard so the pin
is to the threshold, not to a lucky sentence. No network, no model training, no state mutation outside a tempdir.
Run: python3 test_dp1_poisoning.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_distill as D                                           # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def jac(a, b):
    A, B = D._bag(a), D._bag(b)
    return (len(A & B) / float(len(A | B))) if (A | B) else 0.0


def main():
    print("DP1 -- training-data poisoning is filtered before the student learns (OWASP LLM04)\n")
    cases = D.exam_cases()                       # (cat, label, expect, text)
    ebags = D._exam_bags()
    exam = max((c[3] for c in cases), key=lambda t: len(D._bag(t)))   # a real exam case with the most tokens

    check("DP1.0 there are exam cases to protect, and a usable fixture case",
          len(cases) >= 10 and len(D._bag(exam)) >= 5, (len(cases), len(D._bag(exam))))

    # --- poison IS caught ---
    check("DP1.1 an exam case copied VERBATIM into training is contamination",
          D.contaminating(exam, ebags) is True, exam[:60])

    near = exam + " please process this"         # keeps Jaccard well above the threshold
    check("DP1.2 a near-copy (measured Jaccard >= %.2f) is caught" % D.EXAM_OVERLAP,
          jac(near, exam) >= D.EXAM_OVERLAP and D.contaminating(near, ebags) is True, round(jac(near, exam), 3))

    # --- honest data is NOT over-filtered ---
    clean = ("the astronomer calibrated her telescope beneath the aurora while penguins waddled across the "
             "glacier at dawn humming an unfamiliar melody")
    mx = max(jac(clean, c[3]) for c in cases)
    check("DP1.3 an unrelated clean row is NOT flagged (max Jaccard over all exam cases %.3f < %.2f)"
          % (mx, D.EXAM_OVERLAP), mx < D.EXAM_OVERLAP and D.contaminating(clean, ebags) is False, mx)

    toks = list(D._bag(exam))
    topic = (" ".join(toks[:max(1, len(toks) // 5)])                 # ~20% of the exam case's words...
             + " and then many entirely separate distinctive filler terms alpha bravo charlie delta echo "
               "foxtrot golf hotel india juliet kilo lima november oscar quebec romeo tango")
    check("DP1.4 sharing a topic (a few words, measured Jaccard %.3f < %.2f) is NOT contamination"
          % (jac(topic, exam), D.EXAM_OVERLAP),
          jac(topic, exam) < D.EXAM_OVERLAP and D.contaminating(topic, ebags) is False, round(jac(topic, exam), 3))

    check("DP1.5 empty/None text is not contamination (no crash, no false flag)",
          D.contaminating("", ebags) is False and D.contaminating(None, ebags) is False)

    # --- DP1.6 integration: the TRAINING path (paired_only=True) filters the poison, leaves clean rows
    # untouched (non-vacuous).  NB: paired_only=False is the raw-ledger-count path and returns early at
    # covenant_distill.py:220-221 BEFORE the contamination filter -- the guard runs only where the student
    # actually learns, which is exactly the path that must be pinned.  Rows are dated before P.PANEL_SINCE so
    # the single-teacher panel rule keeps them as legacy; source != "study" exempts them from the pair rule --
    # leaving contamination as the only thing that can drop a row here. ---
    tmp = tempfile.mkdtemp(prefix="dp1_")
    clean_rows = [
        {"text": clean, "violates": False, "judge": "teacher", "source": "t", "t": "2020-01-01"},
        {"text": "payment for the office groceries i bought last week", "violates": False,
         "judge": "teacher", "source": "t", "t": "2020-01-01"},
    ]
    poison_row = {"text": exam, "violates": True, "judge": "teacher", "source": "t", "t": "2020-01-01"}

    def write(path, rows):
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    ctrl_path = os.path.join(tmp, "control.jsonl")
    test_path = os.path.join(tmp, "poisoned.jsonl")
    write(ctrl_path, clean_rows)
    write(test_path, clean_rows + [poison_row])
    ctrl = [d.get("text") for d in D.load_verdicts(ctrl_path, paired_only=True)]
    test = [d.get("text") for d in D.load_verdicts(test_path, paired_only=True)]

    check("DP1.6a control: clean rows survive the training path (so the drop below is real, not vacuous)",
          len(ctrl) >= 1, ctrl)
    check("DP1.6b the training path (paired_only=True) DROPS the exam-verbatim poison row",
          exam not in test, [t[:40] for t in test])
    check("DP1.6c ...and removes ONLY the poison -- the clean rows are untouched",
          sorted(test) == sorted(ctrl), (len(ctrl), len(test)))

    ok_n = sum(1 for r in results if r)
    print("\nDP1: %d/%d passed" % (ok_n, len(results)))
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
