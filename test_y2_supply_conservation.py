#!/usr/bin/env python3
"""test_y2_supply_conservation.py -- Y2: the ledger mints exactly what it means to.

WHY THIS IS THE FIRST THING ANY MONETARY GOAL NEEDS.

A supply cap, a burn, a halving, deflation -- every one of them is a claim
about a TOTAL. None of them means anything unless issuance is exact, because a
cap on a number the system cannot compute is decoration.

This ledger could not compute it until v8.12. total_staked was a hand-kept
counter that stake() and unstake() updated and that claim_rewards() and
distribute_block_rewards() did not, while both of those compounded rewards into
stake.amount. Each block split by stake.amount / total_staked, so rewards
raised the numerators and never the denominator; the shares summed to more than
1.0; that minted more than block_reward; that raised the numerators further.
A feedback loop, not a rounding error -- every block widened the gap that
caused it.

    10 stakers, 50 per block, 5000 blocks
    intended mint      250,000
    actual mint        676,563,839,999,194        (270 billion per cent over)
    cached counter still reading 10,000 against a true sum of 676 trillion

Fixing it introduced its own mirror-image bug, which is the more instructive
half: with total_staked DERIVED, reading it inside the credit loop recomputes
it after each staker is paid, so the denominator grows mid-iteration, the
shares sum to 0.9978, and the ledger quietly UNDER-issues by 0.2%. A
proportional split is only proportional against a FIXED total.

WHAT Y2 PINS.

  C*  CONSERVATION. One block mints exactly block_reward -- not approximately,
      and not "close enough at this scale", because the original defect was
      invisible at small scale and catastrophic at large.
  D*  total_staked is DERIVED and cannot be assigned. The defect was possible
      only because a second definition of one quantity existed; the fix is that
      there is now only one.
  S*  the denominator is SNAPSHOT before the credit loop, which is what stops
      the mirror-image under-issue.
  R*  refusal: a non-finite or negative reward is rejected before it touches a
      single stake, because stake.amount is cumulative and one NaN poisons the
      whole pool permanently.

Pure: no node, no network, scratch database only.
"""
import ast
import inspect
import math
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def pool_with(n=10, each=100.0):
    db = C.Database(os.path.join(tempfile.mkdtemp(), "y2.db"))
    p = C.StakingPool(db)
    now = time.time()
    for i in range(n):
        p.stakes["k%d" % i] = C.Stake(pubkey="k%d" % i, amount=each,
                                      start_time=now, duration=86400 * 30)
    return p


def main():
    print("Y2 -- the ledger mints exactly what it means to\n")

    # ---- C: conservation ---------------------------------------------------
    p = pool_with()
    before = p.total_staked
    p.distribute_block_rewards(50.0)
    check("C1 ONE block mints exactly its reward",
          abs((p.total_staked - before) - 50.0) < 1e-9,
          p.total_staked - before)

    p = pool_with()
    before = p.total_staked
    for _ in range(5000):
        p.distribute_block_rewards(50.0)
    minted = p.total_staked - before
    check("C2 FIVE THOUSAND blocks mint exactly 250,000. This is the exact "
          "scenario that produced 676,563,839,999,194 before v8.12 -- a "
          "feedback loop, so it is invisible at small scale and catastrophic "
          "at large, and only a long run can tell the two apart",
          abs(minted - 250000.0) < 1e-6, minted)
    check("C3 ...and the books balance: the sum of the stakes IS the total",
          abs(sum(s.amount for s in p.stakes.values()) - p.total_staked) < 1e-6)

    p = pool_with(n=3, each=1.0)
    for _ in range(200):
        p.distribute_block_rewards(7.5)
    check("C4 conservation holds with uneven, compounding stakes too -- the "
          "defect was a RATIO problem, so equal stakes could have hidden it",
          abs((p.total_staked - 3.0) - 1500.0) < 1e-6, p.total_staked - 3.0)

    p = pool_with()
    before = p.total_staked
    p.distribute_block_rewards(0.0)
    check("C5 a zero reward mints nothing and raises nothing",
          abs(p.total_staked - before) < 1e-12)

    # ---- D: one definition, derived --------------------------------------
    check("D1 total_staked is a PROPERTY, not a stored counter. The defect was "
          "possible only because one quantity had two definitions that could "
          "disagree; the fix is that there is now only one",
          isinstance(type(p).total_staked, property))
    try:
        p.total_staked = 999.0
        assigned = True
    except AttributeError:
        assigned = False
    check("D2 ...and it CANNOT be assigned, so no future call site can "
          "reintroduce a second definition by accident", not assigned)
    # BY AST. The first version searched the source TEXT for
    # "self.total_staked +=" and failed -- because the property's own docstring
    # contains that string while explaining what was REMOVED.
    #
    # Fourth time today a check matched a string where it should have parsed a
    # tree, and by now the pattern is worth naming rather than just fixing: in
    # THIS codebase every docstring describes the defect it repaired, so a grep
    # for a defect pattern reliably matches the documentation of its own fix.
    # Good commenting discipline makes text-matching assertions systematically
    # wrong here. Parse, always.
    pool_tree = ast.parse(inspect.getsource(C.StakingPool).lstrip())
    aug = [n for n in ast.walk(pool_tree)
           if isinstance(n, ast.AugAssign)
           and isinstance(n.target, ast.Attribute)
           and n.target.attr == "total_staked"]
    plain = [n for n in ast.walk(pool_tree)
             if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Attribute) and t.attr == "total_staked"
                     for t in n.targets)]
    check("D3 by AST: nothing in the pool ASSIGNS to total_staked, augmented "
          "or otherwise. The old counter was mutated in two places and not in "
          "two others, which is the whole defect -- a quantity with two "
          "definitions that were allowed to disagree",
          not aug and not plain, (len(aug), len(plain)))

    # ---- S: the snapshot that prevents the mirror-image bug ---------------
    fn = inspect.getsource(C.StakingPool.distribute_block_rewards)
    tree = ast.parse(fn.lstrip())
    loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)]
    reads_inside = 0
    for lp in loops:
        for n in ast.walk(lp):
            if isinstance(n, ast.Attribute) and n.attr == "total_staked":
                reads_inside += 1
    check("S1 the denominator is read OUTSIDE the credit loop. Reading a "
          "DERIVED total inside it recomputes after each staker is paid, the "
          "denominator grows mid-iteration, shares sum to 0.9978, and the "
          "ledger under-issues by 0.2% -- the mirror image of the bug this "
          "fixes, and introduced by fixing it. A proportional split is only "
          "proportional against a FIXED total",
          reads_inside == 0, reads_inside)

    # ---- R: refusal before contact ----------------------------------------
    for bad, name in ((float("nan"), "NaN"), (float("inf"), "+Inf"),
                      (float("-inf"), "-Inf"), (-1.0, "negative")):
        p = pool_with()
        before = sum(s.amount for s in p.stakes.values())
        try:
            p.distribute_block_rewards(bad)
        except Exception:                                    # noqa: BLE001
            pass
        after = sum(s.amount for s in p.stakes.values())
        clean = (abs(after - before) < 1e-12) and not math.isnan(after)
        check("R:%-8s is refused BEFORE it touches a stake. stake.amount is "
              "cumulative, so one NaN makes that stake NaN forever, and since "
              "the total is derived by summing them, one poisoned stake makes "
              "the WHOLE POOL NaN -- every share, every later block" % name,
              clean, after)

    n, ok = len(results), sum(results)
    print(f"\nY2: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
