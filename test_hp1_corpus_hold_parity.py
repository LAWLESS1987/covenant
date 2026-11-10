#!/usr/bin/env python3
"""HP1 -- the whole-corpus HOLD PARITY bar in covenant_distill.promotion()
(the id HC1 was already taken by test_hc1_head_commitment.py)
(2026-11-10, DeepSeek's hold-side clause from ops/CONSULT_IMPROVE_JUDGES).

The fair split weighs wrong HOLDS (clean rows wrongly CONVICTED) only on the
small unseen slice; a regression spread thin across the whole corpus slips it.
train() now measures, over EVERY clean-labelled row, honest transfers the
candidate newly blocks (verdict "violates") minus those it newly frees, and
promotion() refuses a net above HOLD_REGRESSION_BUDGET.

Driven BOTH WAYS (CLAUDE.md rule 8 -- a check that only ever passed has never
been observed): the bar must FIRE on a net over budget and must STAY SILENT on a
net at/under it and on a net-negative (legitimate) candidate, and its presence
must not disturb a holdout that does not carry the measurement at all.
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_distill as D

MARK = "whole corpus"            # the substring unique to this bar's refusal


def stat(agree=10):
    """A minimal examine()-shaped result that passes every OTHER bar, so only
    the corpus-hold clause can decide the outcome."""
    return {
        "total": {"n": 10, "agree": agree, "wrong": 0, "abstain": 0,
                  "false_clean": 0, "false_hold": 0, "false_hold_legit": 0},
        "clean": {"n": 10, "agree": 10, "wrong": 0, "abstain": 0,
                  "false_clean": 0, "false_hold": 0},
    }


def holdout(corpus_holds):
    """A benign fair split (adds no refusal) plus the corpus-hold measurement."""
    h = {"fair": ((10, 0), (10, 0), 100), "cand_holds": 0}
    if corpus_holds is not None:
        h["corpus_holds"] = corpus_holds
    return h


def fired(reasons):
    return any(MARK in r for r in reasons)


def main():
    B = D.HOLD_REGRESSION_BUDGET
    s = stat()
    checks = []

    def check(name, cond):
        checks.append((name, cond))
        print("%s  %s" % ("ok  " if cond else "FAIL", name))

    # 1. net NEGATIVE (benign refine, measured -14 on the live corpus): promote, silent.
    ok, r = D.promotion(s, s, holdout=holdout((3, 17)))
    check("benign net-14 promotes and the bar stays silent", ok and not fired(r))

    # 2. net ZERO: silent.
    ok, r = D.promotion(s, s, holdout=holdout((5, 5)))
    check("net 0 keeps the bar silent", not fired(r))

    # 3. net exactly AT budget (not over): silent, promotes.
    ok, r = D.promotion(s, s, holdout=holdout((B, 0)))
    check("net == budget (%d) does NOT fire" % B, ok and not fired(r))

    # 4. net ONE OVER budget: fires, refuses.
    ok, r = D.promotion(s, s, holdout=holdout((B + 1, 0)))
    check("net budget+1 fires and refuses", (not ok) and fired(r))

    # 5. a big spread-thin regression (the shape the fair split misses): refuses.
    ok, r = D.promotion(s, s, holdout=holdout((B + 20, 2)))
    check("large net regression refuses", (not ok) and fired(r))

    # 6. newly_freed OFFSETS newly_blocked back under budget: silent (net, not gross).
    ok, r = D.promotion(s, s, holdout=holdout((40, 40 - B)))   # net == B, not over
    check("frees offset blocks -> net at budget, silent", ok and not fired(r))

    # 7. BACKWARD COMPAT: a holdout WITHOUT the measurement is untouched by this bar.
    h = {"fair": ((10, 0), (10, 0), 100), "cand_holds": 0}
    ok, r = D.promotion(s, s, holdout=h)
    check("holdout lacking corpus_holds still promotes, bar silent", ok and not fired(r))

    # 8. the clause does not fabricate a pass: a candidate failing an ALWAYS-ON
    #    bar (the absolute clean-hold bar) with a benign corpus-hold still REFUSES.
    worse = stat()
    worse["clean"]["false_hold"] = 1      # wrongly holds a clean exam case
    ok, r = D.promotion(worse, s, holdout=holdout((3, 17)))
    check("absolute clean bar still refuses even with benign corpus_holds",
          (not ok) and not fired(r))

    npass = sum(1 for _, c in checks if c)
    print("\nHP1: %d/%d passed" % (npass, len(checks)))
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
