#!/usr/bin/env python3
"""JE1 -- the correlated-judge figure carries its own significance, computed in closed form.

2026-09-26: a reader of docs/JUDGE_EVALUATION.md asked for the significance of the
student / naive-Bayes pair itself, not only the 7.7x ratio -- the raw 2x2, a chi-square
test of independence with phi, and Fisher's exact test, because the expected joint count
(~7) is small. tools/judge_eval.table_tests() computes all of it with the standard library
only, so it can be checked by hand; this suite pins it.

  JE1a  Fisher's exact test reproduces the textbook tea-tasting table exactly.
  JE1b  the published table (53 / 5 / 92 / 1076) gives the values scipy gives
        (computed once with scipy 1.18 and written here; scipy is not needed to run this).
  JE1c  driven the other way: an exactly independent table is NOT significant
        (chi2 0, phi 0, Fisher p 1) -- the test can say no.
  JE1d  error_overlap() builds the table from predictions correctly, abstentions excluded.
  JE1e  the report's prose takes its figures from the run (the live-repository run of 2026-09-26
        found two written in from the first dataset).
  JE1f  driven the other way: a table that is not significant is not called 'not noise'.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
import judge_eval as J  # noqa: E402

PASSED, FAILED = [0], []


def check(label, ok, detail=""):
    print("  %-74s %s" % (label[:74], "ok" if ok else "FAIL  %s" % detail))
    if ok:
        PASSED[0] += 1
    else:
        FAILED.append(label)


def close(x, y, rel=1e-6):
    return abs(x - y) <= rel * max(abs(x), abs(y))


def main():
    t = J.table_tests(3, 1, 1, 3)
    check("JE1a tea tasting: Fisher two-sided 0.485714, one-sided 0.242857",
          close(t["fisher_p_two_sided"], 0.4857142857) and close(t["fisher_p_greater"], 0.2428571429), t)

    r = J.table_tests(53, 5, 92, 1076)
    want = {"expected_both_wrong": 6.859706362153344, "chi2": 369.4599, "chi2_p": 2.45324e-82,
            "chi2_yates": 361.4963, "chi2_yates_p": 1.32982e-80, "phi": 0.548957, "odds_ratio": 123.9739,
            "fisher_p_two_sided": 1.26769e-47, "fisher_p_greater": 1.26769e-47}
    bad = {k: (r[k], v) for k, v in want.items() if not close(r[k], v, rel=1e-4)}
    check("JE1b the published table matches scipy: chi2, Yates, phi, odds ratio, Fisher", not bad, bad)

    z = J.table_tests(1, 9, 9, 81)          # 1/10 x 1/10 = 1/100: exactly independent
    check("JE1c an independent table is not significant: chi2 0, phi 0, Fisher p 1",
          close(z["chi2"] + 1, 1) and close(z["phi"] + 1, 1) and close(z["fisher_p_two_sided"], 1.0), z)

    pa = ["clean", "clean", "violates", "violates", "abstain", "clean"]
    pb = ["clean", "violates", "clean", "violates", "clean", "clean"]
    gold = [True, True, True, True, True, False]
    o = J.error_overlap(pa, pb, gold)
    check("JE1d the table is built from predictions; abstentions and clean rows are excluded",
          o["n"] == 4 and o["table"] == {"both_wrong": 1, "a_only_wrong": 1, "b_only_wrong": 1, "both_right": 1}, o)

    # JE1e/f (2026-09-26): the report's prose carried two figures written in from the first dataset ('3.4% vs 23.9%',
    # 'the 7.7x is not noise'); a run on a second corpus printed them beside tables that said 3.2% vs 25.4% and 9.1x.
    def judge(fc, decided):
        return {"false_clear": fc, "ci_false_clear": (fc, fc), "false_hold": 0.2, "ci_false_hold": (0.2, 0.2),
                "false_conviction": 0.1, "abstain": 1 - decided, "decided": decided, "accuracy_when_deciding": 0.9}
    res = {"student (distilled, 5-fold)": judge(0.032, 0.648), "naive Bayes, same words, must decide": judge(0.254, 1.0)}

    def overlap_of(bw, ao, bo, br):
        a = ["clean"] * (bw + ao) + ["violates"] * (bo + br)
        b = ["clean"] * bw + ["violates"] * ao + ["clean"] * bo + ["violates"] * br
        return J.error_overlap(a, b, [True] * len(a))
    strong, flat_ = overlap_of(54, 1, 82, 1124), overlap_of(1, 9, 9, 81)
    text = J.render(res, 10, None, [{}] * 10, 5, 10, 7, overlap=strong)
    check("JE1e the report's prose takes the gap and the ratio from the run, not from the first dataset",
          "3.2% vs 25.4%" in text and "3.4% vs 23.9%" not in text and ("the %.1fx is not noise" % strong["ratio"]) in text
          and "7.7x" not in text, [ln[:120] for ln in text.splitlines() if "vs" in ln or "noise" in ln][:3])
    weak = J.render(res, 10, None, [{}] * 10, 5, 10, 7, overlap=flat_)
    check("JE1f driven the other way: an independent table's report does NOT say the ratio is not noise",
          "is not noise" not in weak and "not established at the 0.001 level" in weak,
          [ln[:160] for ln in weak.splitlines() if "noise" in ln or "established" in ln][:2])

    total = PASSED[0] + len(FAILED)
    print("JE1: %d/%d passed" % (PASSED[0], total))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
