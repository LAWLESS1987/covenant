#!/usr/bin/env python3
"""
A88 -- a feature was dropped from the judge by a row that never mentioned it.

THE HAZARD, measured on 2026-09-11. The nightly added 12 violation rows and 10
clean rows. Nineteen features left the model:

    delivery, follow, for my friend, his account, money is, my personal,
    not:arrived, not:arriv~, ordered, payment from, remittance, remittanc~,
    say nothing, schedul~, support, that belongs, that belongs to,
    the statement, the village

Every one of them had weight 0.2502 against a cut of `abs(w) >= 0.25`, and not
one of their counts had changed. What changed was the corpus:

    clean/violation balance 1675/1565 = 1.0703  ->  1685/1577 = 1.0685

The weight written to the model is

    w = log((a+1)/(b+1))  +  log((n_c+2)/(n_v+2))
        ^ what this feature has been seen to do    ^ the corpus's class balance

and the cut was applied to the SUM. The second term is identical for every
feature and moves every night, so a feature can be dropped without a single new
row ever mentioning it -- and restored the same way on a night that tips the
balance back. `his account` and `that belongs to` are the possessive phrases
this judge detects theft with, and they were removed by arithmetic about
unrelated rows.

THE FIX. The cut is on the evidence alone -- MIN_EVIDENCE_HOLD / _CLEAR in
covenant_judge_fallback.py -- which for fixed counts is a constant. The weight
WRITTEN is unchanged, so scoring is unchanged; only the decision about whether
to write it down has moved off the drifting quantity.

WHY THESE CHECKS ARE BEHAVIOURAL. Every one builds a corpus and runs the real
FallbackModel.train, then asks whether a feature is in the model. None reads
the source of covenant_judge_fallback.py or asserts on a constant's spelling --
that is the fake-guard shape A74 found in 35 of 36 suites. E1 and E2 also
recompute what the OLD rule would have done on the same two corpora, so the
suite fails if the cut is ever moved back onto the weight.

CHECKS (fast, no network, nothing written):
  E1  hold side: one clean row that never mentions the feature decided its fate
      under the old rule; under the shipped rule it decides nothing
  E2  clear side: the same, for a feature that argues for clearing
  E3  across every class balance the ledger has occupied, membership never
      flickers -- and the old rule flickers inside that same range
  E4  the weight WRITTEN is still the full log-odds: scoring is untouched
  E5  a feature's fate changes when its OWN counts change (the cut still cuts)
  E6  neither bar sits on a low-count atom, which is what made one drift
      remove nineteen features at once rather than one
LICENCE: public domain.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_judge_fallback as FB

MARK_HOLD = "kumquat"      # not a stopword, and _fold() leaves it alone
MARK_CLEAR = "quokka"

_checks = []


def ck(name, cond, detail=""):
    _checks.append((name, bool(cond), detail))
    print("%-5s %s%s" % ("ok" if cond else "FAIL", name, ("  -- " + detail) if detail and not cond else ""))


def corpus(mark, mark_v, mark_c, n_v, n_c):
    """mark appears in mark_v violation rows and mark_c clean rows. The rest are
    filler that never contains it, and exists only to set the class balance."""
    rows = []
    for i in range(mark_v):
        rows.append(("the %s was taken without asking number %d" % (mark, i), True))
    for i in range(mark_c):
        rows.append(("the %s was sent as agreed number %d" % (mark, i), False))
    for i in range(n_v - mark_v):
        rows.append(("unrelated seizure of the harbour ledger number %d" % i, True))
    for i in range(n_c - mark_c):
        rows.append(("unrelated wages for the harbour ledger number %d" % i, False))
    assert sum(1 for _t, v in rows if v) == n_v and sum(1 for _t, v in rows if not v) == n_c
    return rows


def trained(rows):
    return FB.FallbackModel.train(rows, ["a88"], trained_at="a88")


def old_rule_keeps(a, b, n_v, n_c):
    """The cut exactly as it stood before 2026-09-11: on the stored weight."""
    w = math.log(((a + 1.0) / (n_v + 2.0)) / ((b + 1.0) / (n_c + 2.0)))
    return abs(w) >= 0.25


def main():
    print("A88 -- the cut that dropped nineteen features for rows that never mentioned them\n")

    # -- E1  hold side ----------------------------------------------------
    # a=5 b=4 is the 6:5 atom all nineteen sat on. The two corpora differ by
    # ONE clean filler row, which does not contain the feature.
    a, b = 5, 4
    keep_rows = corpus(MARK_HOLD, a, b, 48, 52)
    drop_rows = corpus(MARK_HOLD, a, b, 48, 51)
    old_keep = old_rule_keeps(a, b, 48, 52)
    old_drop = old_rule_keeps(a, b, 48, 51)
    in_keep = MARK_HOLD in trained(keep_rows).weights
    in_drop = MARK_HOLD in trained(drop_rows).weights
    ck("E1a the old rule's verdict really did turn on that one unrelated row",
       old_keep and not old_drop,
       "old rule: %s at n_c=52, %s at n_c=51 -- expected kept then dropped"
       % ("kept" if old_keep else "dropped", "kept" if old_drop else "dropped"))
    ck("E1b THE REGRESSION: the feature survives both corpora now",
       in_keep and in_drop,
       "%s at n_c=52, %s at n_c=51" % (in_keep, in_drop))

    # -- E2  clear side ---------------------------------------------------
    # The drift cut both ways; a feature that argues for CLEARING drifted too.
    a2, b2 = 4, 6
    keep2 = corpus(MARK_CLEAR, a2, b2, 48, 52)   # balance 1.038
    drop2 = corpus(MARK_CLEAR, a2, b2, 44, 54)   # balance 1.217
    old_k2 = old_rule_keeps(a2, b2, 48, 52)
    old_d2 = old_rule_keeps(a2, b2, 44, 54)
    in_k2 = MARK_CLEAR in trained(keep2).weights
    in_d2 = MARK_CLEAR in trained(drop2).weights
    ck("E2a the old rule dropped a clearing feature on a balance shift alone",
       old_k2 and not old_d2,
       "old rule: %s then %s" % (old_k2, old_d2))
    ck("E2b it survives both now", in_k2 and in_d2, "%s / %s" % (in_k2, in_d2))

    # -- E3  the whole range the ledger has actually occupied --------------
    # Sweep the balance from 1.00 to 1.20 and count how many times membership
    # changes. The answer must be zero, and the old rule's answer must not be,
    # or this suite is not measuring anything.
    flips_new = flips_old = 0
    prev_new = prev_old = None
    for n_c in range(48, 60):
        rows = corpus(MARK_HOLD, a, b, 48, n_c)
        now_new = MARK_HOLD in trained(rows).weights
        now_old = old_rule_keeps(a, b, 48, n_c)
        if prev_new is not None and now_new != prev_new:
            flips_new += 1
        if prev_old is not None and now_old != prev_old:
            flips_old += 1
        prev_new, prev_old = now_new, now_old
    ck("E3a the old rule flickers inside the range the ledger lives in",
       flips_old >= 1, "flips=%d -- if this is 0 the sweep is too narrow to prove anything" % flips_old)
    ck("E3b the shipped rule never flickers across that range",
       flips_new == 0, "flips=%d" % flips_new)

    # -- E4  scoring is untouched -----------------------------------------
    m = trained(keep_rows)
    expect = round(math.log(((a + 1.0) / (48 + 2.0)) / ((b + 1.0) / (52 + 2.0))), 4)
    ck("E4  the weight written is still the full log-odds, balance included",
       m.weights.get(MARK_HOLD) == expect,
       "wrote %r, expected %r" % (m.weights.get(MARK_HOLD), expect))

    # -- E5  the cut still cuts -------------------------------------------
    # Evidence below the bar must still be refused, or the fix has quietly
    # turned into "keep everything", which is a different judge.
    weak = corpus(MARK_HOLD, 6, 6, 48, 52)          # 7:7 -- no evidence at all
    strong = corpus(MARK_HOLD, 9, 2, 48, 52)        # 10:3 -- plenty
    ck("E5a a feature with no evidence is still refused",
       MARK_HOLD not in trained(weak).weights)
    ck("E5b a feature whose OWN counts carry evidence is kept",
       MARK_HOLD in trained(strong).weights)

    # -- E6  neither bar sits on a LOW-count atom -------------------------
    # With Laplace smoothing a feature's evidence can only land on log(k/m).
    # For large k and m those points are dense and no bar can avoid them all --
    # nor does it need to, because a feature with hundreds of rows behind it
    # crosses a bar on its own evidence and crosses alone. The damage comes
    # from the LOW-count points, where hundreds of features share one value and
    # a bar sitting on one removes them as a bloc: nineteen at 6:5 on
    # 2026-09-11. So the bound is asserted where the blocs are.
    def clearance(bar, limit):
        atoms = {abs(math.log(k / float(mm)))
                 for k in range(1, limit + 1) for mm in range(1, limit + 1) if k != mm}
        return min(abs(x - bar) for x in atoms)

    worst = min(clearance(FB.MIN_EVIDENCE_HOLD, 8), clearance(FB.MIN_EVIDENCE_CLEAR, 8))
    # The bar that shipped until today, in the same terms: 0.25 minus the class
    # balance the ledger actually had. This is the comparison that makes E6 a
    # measurement rather than a restatement of the constants.
    old_in_evidence = 0.25 - math.log((1685 + 2.0) / (1577 + 2.0))
    ck("E6a both bars sit in a gap between low-count atoms",
       worst >= 0.01, "closest low-count atom is %.4f from a bar" % worst)
    ck("E6b and the bar that shipped until today did not",
       clearance(old_in_evidence, 8) < 0.01,
       "old bar %.4f was %.4f from log(6/5) -- the atom the nineteen sat on"
       % (old_in_evidence, clearance(old_in_evidence, 8)))

    bad = [n for n, ok, _d in _checks if not ok]
    print("\nA88: %d/%d passed" % (len(_checks) - len(bad), len(_checks)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
