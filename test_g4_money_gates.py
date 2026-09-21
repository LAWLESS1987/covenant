#!/usr/bin/env python3
"""
test_g4_money_gates.py -- G4 (2026-09-16): every reason an order may be refused,
driven BOTH WAYS.

WHY THIS EXISTS. guards.preconditions() is the last thing between a decision and
a venue. It can refuse for eleven distinct reasons. Five suites call it
(DP1, F7, rule5, sentinel gate, V2) and each drives the reasons it cares about;
nothing asked the whole set whether each reason can be made to appear AND to go
away. A gate that always fires is not a gate -- it is a wall that will be
switched off the first time it is inconvenient. A gate that never fires is worse.

This suite constructs the condition in memory and asserts the exact reason
appears, then removes the condition and asserts that reason is gone. It writes
nothing: cfg, st, sealed_ok, guard_blocks, config_path, state_path and now are
all parameters, and the one file-backed check (TRADER_HALT) is driven by
pointing guards.HALT at a temp path. The real trader_config.json, the real
trader state and the real halt file are never read for a verdict and never
touched.

IT DOES NOT CHANGE A GUARD. If a reason here cannot be driven both ways, that is
a finding to report, not a thing to fix in the money path at the end of a long
session.

    python test_g4_money_gates.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import guards as G

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


# A configuration with every gate satisfied, so that each test can break exactly
# one thing. daily_plan_required is off here because the plan gate is DP1's
# subject and is driven separately below.
def clear_cfg(**over):
    cfg = {"armed": True, "daily_plan_required": False, "seal_required": True,
           "min_sealed_signals": 0, "rule5_require_significance": False,
           "min_order_usd": 10.0, "max_order_usd": 1000.0,
           "max_orders_per_day": 5, "max_daily_notional_usd": 5000.0}
    cfg.update(over)
    return cfg


def clear_st(**over):
    st = {"orders_today": [], "sealed_signals": 100,
          "rule5": {"clears": True, "why": "fixture"}}
    st.update(over)
    return st


ORDER = {"side": "buy", "usd": 100.0, "sym": "XRP-USD"}


def reasons(order=None, **kw):
    kw.setdefault("cfg", clear_cfg())
    kw.setdefault("st", clear_st())
    kw.setdefault("sealed_ok", True)
    return G.preconditions(order or ORDER, **kw)


def drives(label, on_kwargs, needle, off_kwargs=None):
    """The reason must appear under on_kwargs and be absent under off_kwargs."""
    on = reasons(**on_kwargs)
    off = reasons(**(off_kwargs or {}))
    hit = [r for r in on if needle.lower() in r.lower()]
    still = [r for r in off if needle.lower() in r.lower()]
    check(label, bool(hit) and not still,
          "on=%s | off=%s" % (str(hit)[:70], str(still)[:50]))


def main():
    # The baseline must be CLEAR. If this fails every "it went away" below is
    # meaningless, so it is asserted first and loudly.
    base = reasons()
    check("G4.0 the fixture configuration is clear -- no reason at all",
          base == [], str(base)[:150])

    # 1. armed
    drives("G4.1 armed=false refuses, and arming clears it",
           {"cfg": clear_cfg(armed=False)}, "armed=false")

    # 2. TRADER_HALT -- driven by the constant, never by writing the real file
    real_halt = G.HALT
    tmp_halt = tempfile.mktemp(suffix="_TRADER_HALT")
    try:
        with open(tmp_halt, "w", encoding="utf-8") as fh:
            fh.write("stop")
        G.HALT = tmp_halt
        with_halt = reasons()
        G.HALT = tmp_halt + ".absent"
        without = reasons()
        check("G4.2 a halt file refuses, and its absence clears it",
              any("TRADER_HALT" in r for r in with_halt) and not any("TRADER_HALT" in r for r in without),
              "%s | %s" % (str(with_halt)[:60], str(without)[:40]))
    finally:
        G.HALT = real_halt
        try:
            os.unlink(tmp_halt)
        except OSError:
            pass

    # 3. unparseable trader state -- a real temp file, never the real one
    bad_state = tempfile.mktemp(suffix="_state.json")
    good_state = tempfile.mktemp(suffix="_state.json")
    with open(bad_state, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    with open(good_state, "w", encoding="utf-8") as fh:
        json.dump({"orders_today": [], "sealed_signals": 100,
                   "rule5": {"clears": True}}, fh)
    try:
        on = G.preconditions(ORDER, cfg=clear_cfg(), st=None, sealed_ok=True, state_path=bad_state)
        off = G.preconditions(ORDER, cfg=clear_cfg(), st=None, sealed_ok=True, state_path=good_state)
        check("G4.3 a trader state that will not parse refuses, a good one clears",
              any("will not parse" in r for r in on) and not any("will not parse" in r for r in off),
              "%s | %s" % (str(on)[:70], str(off)[:50]))
    finally:
        for f in (bad_state, good_state):
            try:
                os.unlink(f)
            except OSError:
                pass

    # 4. the daily plan gate.
    #
    # MY FIRST VERSION OF THIS TEST WAS WRONG, and the way it was wrong is
    # worth keeping. It turned the gate on and asserted it would complain --
    # and it did not, because that day's plan was approved. Silence was the
    # correct answer and I had written the test as though the gate always
    # speaks. So it is driven by a DAY instead: a day with no approval must be
    # refused, an approved day must not.
    #
    # RETRACTED AND RESTATED 2026-09-19 -- retraction G4b, the second half of
    # that fix. It read "...today, which the operator approved from the phone,
    # is not", and asserted the gate stays silent on TODAY. That is not a
    # property of the gate. It is a property of whether the operator has
    # tapped approve yet this morning, and he approves between roughly 07:00
    # and 11:20. Measured: 17/17 in three sweeps on 2026-09-18 after the 07:10
    # approval, 16/17 in the 2026-09-19 sweep before it, with ops/daily_approvals.jsonl
    # holding approvals for the 15th through the 18th and none yet for the 19th.
    #
    # So the suite reported the operator's to-do list as a test failure, every
    # morning, on the money path -- which is A60's defect in its worst place: a
    # line that is red by routine is a line nobody reads on the day it means
    # something. The invariant the original author wanted is the one directly
    # above, and it is kept; what is restated is this half, which now drives an
    # APPROVED day from the ledger rather than hoping today is one.
    #
    # The claim as written is preserved on branch
    # `g4-daily-plan-check-as-written-2026-09-19` and in docs/RETRACTED.json.
    import time as _t
    import covenant_daily_plan as _dp
    no_plan_day = _t.time() - 86400 * 400          # long before any plan exists
    on = reasons(cfg=clear_cfg(daily_plan_required=True), now=no_plan_day)
    off_switch = reasons(cfg=clear_cfg(daily_plan_required=False), now=no_plan_day)
    check("G4.4 a day with no approved plan is refused",
          any("daily plan" in r.lower() for r in on), str(on)[:100])

    # An approved day, taken from the ledger rather than assumed. If nothing
    # has ever been approved on this machine there is nothing to measure and
    # the check says so instead of passing: a green that means "no data" is
    # the fake-guard shape this project has paid for twice (A65, A74).
    approved_days = []
    try:
        with open(_dp.APPROVALS, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("decision") == "approve" and r.get("date"):
                    approved_days.append(r["date"])
    except (OSError, ValueError):
        approved_days = []
    if approved_days:
        day = sorted(set(approved_days))[-1]
        ok_appr, why_appr = _dp.approved(day)
        stamp = _t.mktime(_t.strptime(day, "%Y-%m-%d")) + 43200
        off_appr = reasons(cfg=clear_cfg(daily_plan_required=True), now=stamp)
        check("G4.4b ...and a day the operator DID approve is not -- the gate "
              "reads the decision, it does not assume one",
              ok_appr and not any("daily plan" in r.lower() for r in off_appr),
              "%s: %s | %s" % (day, why_appr[:60], str(off_appr)[:50]))
    elif not os.path.exists(_dp.APPROVALS):
        # A fresh clone -- the public repository's Linux CI, a stranger's machine --
        # has no approvals ledger at all: the ledger is the operator's state, not the
        # tree's (gitignored). Measured 2026-09-21: 16/17 on every fresh Linux clone,
        # at 3455312 and at 67c8d12 alike, while this PC read 17/17. Nothing to drive
        # here, so it is said as NOT RUN and counted neither way; a ledger that EXISTS
        # and holds no approval still fails below, as designed (A65, A74).
        print("  [NOT RUN] G4.4b ...and a day the operator DID approve is not  -- no approvals ledger on this tree "
              "(%s): an operator's decision, not the code's" % os.path.basename(_dp.APPROVALS))
    else:
        check("G4.4b ...and a day the operator DID approve is not",
              False, "NOT MEASURED: no approval has ever been recorded in %s, so "
                     "there is no approved day to drive this with. This is not a "
                     "pass." % _dp.APPROVALS)
    check("G4.4c ...and the switch turns the gate off entirely",
          not any("daily plan" in r.lower() for r in off_switch), str(off_switch)[:80])

    # 5. under the minimum order size
    drives("G4.5 an order under min_order_usd refuses, a larger one clears",
           {"order": {"side": "buy", "usd": 1.0, "sym": "XRP-USD"}}, "under min_order_usd")

    # 6. over the room left today
    drives("G4.6 an order over the placeable room refuses, a smaller one clears",
           {"order": {"side": "buy", "usd": 900.0, "sym": "XRP-USD"},
            "cfg": clear_cfg(max_order_usd=200.0)}, "placeable now")

    # 7. the per-day cap.
    #
    # ALSO WRONG FIRST TIME, and for a reason the guard is right about:
    # orders_today_from() applies the trader's own day rollover, so a state
    # whose "day" is not today counts as zero orders -- my fixture had no day
    # at all, so five orders became none and the cap correctly said nothing.
    # The fixture now carries today's date, which is what a real state has.
    today = _t.strftime("%Y-%m-%d", _t.localtime())
    full = clear_st(day=today, orders_today=[{"usd": 10.0, "sym": "XRP-USD"}] * 5)
    empty = clear_st(day=today, orders_today=[])
    on = reasons(st=full)
    off = reasons(st=empty)
    check("G4.7 a day already at its order count refuses, an empty day clears",
          bool(on) and not off, "on=%s | off=%s" % (str(on)[:90], str(off)[:40]))
    check("G4.7b ...and yesterday's orders do not block this morning",
          not reasons(st=clear_st(day="2020-01-01", orders_today=[{"usd": 10.0}] * 9)),
          "rollover")

    # 8. sealing
    drives("G4.8 an unsealed decision refuses, a sealed one clears",
           {"sealed_ok": False}, "not sealed")
    check("G4.8b ...and seal_required=false makes sealing irrelevant",
          not any("not sealed" in r for r in reasons(cfg=clear_cfg(seal_required=False), sealed_ok=False)))

    # 9. Rule 5, the count
    drives("G4.9 too few sealed signals refuses, enough clears",
           {"cfg": clear_cfg(min_sealed_signals=30), "st": clear_st(sealed_signals=3)},
           "sealed signals on record")

    # 10. Rule 5, the significance -- the count met but the record meaning nothing
    drives("G4.10 a count met with an unclearing record still refuses",
           {"cfg": clear_cfg(min_sealed_signals=1, rule5_require_significance=True),
            "st": clear_st(sealed_signals=100, rule5={"clears": False, "why": "fixture: not significant"})},
           "Rule 5")

    # 11. a caller's own blocks are carried through
    drives("G4.11 a caller's guard_blocks are carried into the refusal",
           {"guard_blocks": ["freshness: prices are 3 h old"]}, "freshness")

    # AND THE WHOLE POINT: the refusals are additive, not first-wins. An order
    # that breaks four things must be told all four, or fixing one at a time
    # looks like progress while three remain.
    many = reasons(cfg=clear_cfg(armed=False, min_sealed_signals=30),
                   st=clear_st(sealed_signals=0), sealed_ok=False,
                   order={"side": "buy", "usd": 1.0, "sym": "XRP-USD"})
    check("G4.12 four broken conditions produce four reasons, not one",
          len(many) >= 4, "%d reasons: %s" % (len(many), str(many)[:120]))

    failed = [n for n, ok in results if not ok]
    print(f"\nG4: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
