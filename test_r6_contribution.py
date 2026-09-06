#!/usr/bin/env python3
"""
test_r6_contribution.py -- the weekly contribution path, pinned.

Asked 2026-09-06: "a budget of 100 a week". R6 is not a timing rule. These
checks pin what it may and may not do: nothing under the cash floor, nothing
below the 200d line, nothing into a hold-only asset, nothing over the
per-order cap or the day's order count, nothing over the week's budget --
and that guards.WeeklyBudget blocks on its own when the record says the
week is spent or cannot be read. No network; no private files are touched.

Run:  python test_r6_contribution.py
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guards as G                 # noqa: E402
import covenant_trader as T        # noqa: E402

FAILS = []


def check(cond, label):
    print(("ok    " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


# plan() consults the reserve baseline file under private/; keep tests away from it.
T.reserve_baseline = lambda pf, path=None: ({}, {p["sym"]: p["qty"] for p in pf["positions"]}, [])

BASE_CFG = dict(T.DEFAULT_CONFIG)
BASE_CFG.update({"allow_fiat_buys": True, "weekly_fiat_budget_usd": 100.0,
                 "contribution_min_cash_pct": 0.10, "max_order_usd": 25.0,
                 "max_orders_per_day": 2, "min_order_usd": 5.0, "max_position_pct": 0.20})


def pos(sym, val, regime, px=1.0):
    return {"sym": sym, "qty": val / px, "px": px, "val": val, "regime": regime, "at": {"coinbase": val / px}}


def book(cash, *positions):
    total = cash + sum(p["val"] for p in positions)
    return {"positions": list(positions), "cash": cash, "total": total, "unpriced": [], "venue_notes": []}


def buys(orders):
    return [o for o in orders if o["side"] == "buy"]


# --- C1: under the cash floor, nothing is put to work ---------------------
pf = book(50.0, *[pos(f"A{i}", 95, "UP") for i in range(10)])           # cash 5%, ten assets at 9.5%
orders, notes = T.plan(BASE_CFG, pf)
check(not buys(orders) and any("stays as cash" in n for n in notes),
      "C1 cash under the floor: no buy, and the note says the money stays as cash")

# --- C2: above the floor, equal shares into eligible assets, capped ---------
pf = book(300.0, pos("XLM", 150, "UP"), pos("LINK", 150, "UP"), pos("ADA", 150, "DOWN"),
          *[pos(f"D{i}", 150, "DOWN") for i in range(5)])   # cash 20%, every position 10%
orders, notes = T.plan(BASE_CFG, pf)
b = buys(orders)
check(len(b) == 2 and {o["sym"] for o in b} == {"XLM", "LINK"},
      "C2 two eligible assets above the line get the two orders of the day")
check(all(abs(o["usd"] - 25.0) < 1e-9 for o in b),
      "C2 each share is the per-order cap ($25), not the whole room")
check(all(o["rule"] == "R6 contribution" for o in b), "C2 the orders carry the rule name")

# --- C3: below the line never receives a dollar; hold-only never -----------
pf = book(300.0, pos("ADA", 400, "DOWN"), pos("XRP", 400, "UP"))
orders, notes = T.plan(BASE_CFG, pf)
check(not buys(orders) and any("nothing qualifies" in n for n in notes),
      "C3 a below-line asset and a hold-only asset: nothing qualifies, and the note says so")

# --- C4: the week's spend shrinks the room; a spent week emits nothing -----
pf = book(300.0, pos("XLM", 150, "UP"), *[pos(f"D{i}", 150, "DOWN") for i in range(7)])
orders, notes = T.plan(BASE_CFG, pf, week_spent=90.0)
check(len(buys(orders)) == 1 and abs(buys(orders)[0]["usd"] - 10.0) < 1e-9,
      "C4 with $90 spent this week only $10 of room remains, and the order is $10")
orders, notes = T.plan(BASE_CFG, pf, week_spent=100.0)
check(not buys(orders) and any("already used" in n for n in notes),
      "C4 with the week spent, no buy and the note says the budget is used")

# --- C5: a share under the venue minimum waits --------------------------
pf = book(112.0, *[pos(f"A{i}", 100, "UP") for i in range(10)])          # cash 10.07%: $0.80 spare
orders, notes = T.plan(BASE_CFG, pf)
check(not buys(orders) and any("under the" in n and "minimum" in n for n in notes),
      "C5 spare cash below the minimum order: wait, do not place dust")

# --- C6: the day's order count is shared with sells ------------------------
pf = book(300.0, pos("BIG", 900, "UP"), pos("XLM", 100, "UP"), pos("LINK", 100, "UP"))   # BIG is 64%: a sell
cfg1 = dict(BASE_CFG); cfg1["max_orders_per_day"] = 1
orders, notes = T.plan(cfg1, pf)
check(not buys(orders) and any(o["side"] == "sell" for o in orders)
      and any("order count is used" in n for n in notes),
      "C6 when the sells use the day's count, R6 yields and says so")

# --- C7: shipped defaults are OFF ----------------------------------------
pf = book(300.0, pos("XLM", 150, "UP"), *[pos(f"D{i}", 150, "DOWN") for i in range(7)])
orders, notes = T.plan(dict(T.DEFAULT_CONFIG), pf)
check(not buys(orders) and not any("R6" in n for n in notes),
      "C7 with the shipped config (no permission, no budget) R6 does not exist")

# --- C8: contribution_symbols narrows the set ------------------------------
cfg8 = dict(BASE_CFG); cfg8["contribution_symbols"] = ["LINK"]
pf = book(300.0, pos("XLM", 150, "UP"), pos("LINK", 150, "UP"), *[pos(f"D{i}", 150, "DOWN") for i in range(6)])
orders, notes = T.plan(cfg8, pf)
check([o["sym"] for o in buys(orders)] == ["LINK"], "C8 contribution_symbols limits the targets")

# --- W: guards.WeeklyBudget ---------------------------------------------
now = time.time()
def st(fiat, budget=100.0):
    return G.State(equity_now=1000, equity_peak=1000, equity_start_of_day=1000, closed_trades=[],
                   last_sold={}, positions={}, cash=100, orders_today=[], fiat_buys_week=fiat, now=now)

w = G.WeeklyBudget(budget=100.0)
check(w.check(st([{"at": now - 86400, "usd": 40.0}])).allowed, "W1 $40 of $100 used this week: allowed")
check(not w.check(st([{"at": now - 86400, "usd": 60.0}, {"at": now - 3 * 86400, "usd": 40.0}])).allowed,
      "W2 $100 of $100 used: blocked")
check(w.check(st([{"at": now - 8 * 86400, "usd": 100.0}])).allowed,
      "W3 a buy eight days ago has rolled out of the window")
check(not w.check(st(None)).allowed, "W4 an unknown record blocks (None is not zero)")
check(G.WeeklyBudget(budget=0.0).check(st([])).allowed, "W5 a budget of 0 means R6 is off: the guard does not constrain hand-made buys")
check(abs(w.headroom(st([{"at": now, "usd": 30.0}])) - 70.0) < 1e-9, "W6 headroom is budget minus the week's spend")
check(any(isinstance(g, G.WeeklyBudget) for g in G.DEFAULTS), "W7 WeeklyBudget is in the default stack")
check(G.WeeklyBudget().budget == float(G.caps()["weekly_fiat_budget_usd"]),
      "W8 with no explicit number it reads the operator's config at check time")

# --- X: execute() records fiat-funded buys for the week ---------------------
class _Stub:
    name = "stub"
    def has_credentials(self): return True
    def place(self, sym, side, qty, live=False, **kw): return {"descr": "ok", "txid": "t1"}

_saved = []
T.save_state = lambda s: _saved.append(1)
T.venue_for = lambda o, lv: _Stub()
T.V.all_venues = lambda: [_Stub()]
armed = dict(BASE_CFG); armed.update({"armed": True, "seal_required": False, "rule5_require_significance": False})
state = {"sealed_signals": 30, "orders_today": [], "rule5": {"clears": True}, "day": "x", "fiat_buys": []}
res = T.execute(armed, state, [{"sym": "XLM", "side": "buy", "qty": 25.0, "usd": 25.0, "rule": "R6 contribution"}],
                sealed_ok=True, guard_blocks=[])
check(res and res[0]["status"] == "PLACED" and len(state["fiat_buys"]) == 1
      and abs(state["fiat_buys"][0]["usd"] - 25.0) < 1e-9,
      "X1 a placed fiat-funded buy is written to the week's record with its amount")
old = {"day": "y", "fiat_buys": [{"at": now - 9 * 86400, "usd": 25.0}, {"at": now - 86400, "usd": 25.0}]}
T.roll_day(old)
check(len(old["fiat_buys"]) == 1, "X2 roll_day prunes the week's record to seven days")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("R6 CONTRIBUTION: all passed")
