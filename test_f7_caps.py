#!/usr/bin/env python3
"""test_f7_caps.py -- F7: how much may go out in one order, and in one day.

WHY (asked 2026-09-04: "add the per-trade and per-day caps")

  The three numbers already existed. max_order_usd, max_daily_notional_usd and
  max_orders_per_day have been in trader_config.json since the trader was
  written, and covenant_trader.preconditions() has enforced them. What did not
  exist was enforcement anywhere else: daily.py runs the guard stack and prints
  "may add" every morning, and it had never heard of them. Two enforcement
  points, one blind, and the blind one is the one a person reads.

  So the caps are guards now, and this suite pins what that has to mean.

  C* -- THE ARITHMETIC, including the case the two caps only catch together:
  one order may be legal by size and still impossible because the day's
  notional has almost run out. largest_allowed() returns the minimum of both,
  which is what stops many small orders doing what one large order may not --
  the same shape of hole ReserveFloor exists to close, in the other direction.

  U* -- UNKNOWN IS NOT ZERO. State.orders_today is None when the day's orders
  could not be established, and both guards block on it, because guards.py's
  first design rule is that a guard which cannot evaluate blocks. A missing
  trader state file is NOT unknown: the trader has never run, so it has placed
  nothing, and treating that as unknown would mean the caps refuse every order
  until the caps had already been used once.

  D* -- THE DAY ROLLS OVER the same way covenant_trader.roll_day() rolls it. A
  reader that skips that counts yesterday's orders against this morning, which
  blocks rather than admits, so it is safe -- and still wrong, and it would
  block every morning until the trader next ran.

  S* -- ONE SOURCE OF TRUTH. guards.CAP_DEFAULTS must agree with
  covenant_trader.DEFAULT_CONFIG, and guards.TRADER_STATE must point where
  covenant_trader.STATE points. guards cannot import covenant_trader -- the
  trader imports daily and daily imports guards -- so the constants are
  repeated, and repeated constants drift unless something fails when they do.
  This is that something.

  B* -- THE BUY BUDGET (asked: "buys are allowed with 50% of starting amount").
  The same ratchet ReserveFloor exists to stop applies from this end too: half
  of what I have NOW is spendable, and half of what remains after that, and the
  budget never runs out. So the baseline is the STARTING book, fixed and
  stored, and the spend is cumulative and never forgotten.

  X* -- FIAT NEEDS PERMISSION (asked: "not from fiat without permission").
  Selling XLM and buying SOL with the proceeds moves value between assets
  already owned; buying SOL out of the dollar balance spends money. They look
  identical on a balance sheet, so covenant_trader records `side` on every
  booked order and the guard reads today's sale proceeds as the headroom. Past
  that, a buy waits for allow_fiat_buys -- an operator's edit, like `armed`.

  L* -- THE CAPS ARE NOT FROZEN AT IMPORT. DEFAULTS is a module-level list, so
  reading the config in a guard's constructor would fix the numbers at
  start-up -- and covenant_trader --loop runs for days. Tightening a cap is
  exactly the edit someone makes in a hurry, and it should apply on the next
  cycle rather than the next restart.

Run:  python test_f7_caps.py     (offline; no exchange, no keys, no network)
"""
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import guards as G                                                       # noqa: E402

OK = []


def check(name, cond, detail=""):
    OK.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name,
                        ("  " + str(detail)[:160]) if (detail and not cond) else ""))


def sum_spend(bb):
    """Spend everything the budget permits, eight times over. If the baseline
    were "half of what is left" this would converge on the whole book; with a
    fixed starting baseline it stops at exactly half."""
    start, spent = 6700.0, 0.0
    for _ in range(8):
        st = G.State(equity_now=1.0, equity_peak=1.0, equity_start_of_day=1.0,
                     closed_trades=[], last_sold={}, positions={}, cash=1.0,
                     orders_today=[], starting_total_usd=start,
                     bought_total_usd=spent)
        spent += bb.remaining(st)
    return spent


def state(orders):
    return G.State(equity_now=1000.0, equity_peak=1000.0, equity_start_of_day=1000.0,
                   closed_trades=[], last_sold={}, positions={"XRP": 500.0},
                   cash=500.0, orders_today=orders)


def main():
    print("F7 -- the per-trade and per-day caps\n")

    # Fixed numbers, not the operator's: this suite must read the same on any
    # machine, and trader_config.json is deliberately not shipped.
    pt = G.PerTradeCap(max_usd=25.0, min_usd=5.0, max_orders=2, max_notional=50.0)
    pd = G.PerDayCap(max_orders=2, max_notional=50.0)

    # ---- C: the arithmetic ------------------------------------------------
    check("C1 with nothing placed, the largest order is the per-order cap",
          pt.largest_allowed(state([])) == 25.0, pt.largest_allowed(state([])))
    check("C2 the day's notional shrinks the headroom below the per-order cap",
          pt.largest_allowed(state([{"usd": 40.0}])) == 10.0,
          pt.largest_allowed(state([{"usd": 40.0}])))
    check("C3 the order COUNT alone can exhaust the day with notional to spare",
          pd.check(state([{"usd": 1.0}, {"usd": 1.0}])).allowed is False
          and pt.largest_allowed(state([{"usd": 1.0}, {"usd": 1.0}])) == 0.0)
    check("C4 a headroom under the minimum order blocks, because nothing legal fits",
          not pt.check(state([{"usd": 48.0}])).allowed
          and "nothing legal" in pt.check(state([{"usd": 48.0}])).reason)
    check("C5 ...and the per-DAY guard is still content there, so it is the pair "
          "that catches it, not either alone",
          pd.check(state([{"usd": 48.0}])).allowed)
    check("C6 spending the notional exactly blocks the day",
          not pd.check(state([{"usd": 50.0}])).allowed)
    check("C7 many small orders cannot exceed what one large order may not: "
          "the headroom never goes above the notional that is left",
          all(pt.largest_allowed(state([{"usd": 5.0}] * n)) <= 50.0 - 5.0 * n + 1e-9
              for n in (0, 1, 2)))
    check("C8 a block names the number that triggered it",
          "$50.00" in pd.check(state([{"usd": 50.0}])).reason
          and "2" in pd.check(state([{"usd": 1.0}, {"usd": 1.0}])).reason)
    check("C9 an order whose amount cannot be read makes the day UNKNOWN rather "
          "than counting as zero -- it is an order that happened for an unknown "
          "amount, and zero is the one answer it certainly is not",
          pt.largest_allowed(state([{"usd": "twenty"}])) is None
          and not pd.check(state([{"usd": "twenty"}])).allowed
          and "readable" in pd.check(state([{"usd": "twenty"}])).reason)
    check("C10 ...and the count cap still fires first when it is the count that "
          "is exhausted, because that needs no amounts at all",
          "limit 2" in pd.check(state([{"usd": "?"}, {"usd": "?"}])).reason)

    # ---- U: unknown is not zero -------------------------------------------
    check("U1 orders_today=None blocks the per-day cap", not pd.check(state(None)).allowed)
    check("U2 ...and the per-trade cap", not pt.check(state(None)).allowed)
    check("U3 ...and largest_allowed() returns None rather than a number",
          pt.largest_allowed(state(None)) is None)
    check("U4 both say they could not evaluate, not that a limit was hit",
          "unknown" in pd.check(state(None)).reason
          and "blocking" in pt.check(state(None)).reason)
    check("U5 State defaults orders_today to None, so a caller that never heard "
          "of the caps blocks instead of silently passing",
          G.State(equity_now=1.0, equity_peak=1.0, equity_start_of_day=1.0,
                  closed_trades=[], last_sold={}, positions={}, cash=1.0
                  ).orders_today is None)
    check("U6 an empty list is NOT unknown -- it is a known zero and it allows",
          pd.check(state([])).allowed and pt.check(state([])).allowed)

    d = tempfile.mkdtemp()
    p = os.path.join(d, "trader_state.json")
    check("U7 a missing trader state file is a known zero, not unknown: the trader "
          "has never run, so it has placed nothing",
          G.orders_today_now(os.path.join(d, "absent.json")) == [])
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write("{not json at all")
    check("U8 a file that exists but will not parse IS unknown",
          G.orders_today_now(p) is None)

    # ---- D: the day rolls over --------------------------------------------
    today = time.strftime("%Y-%m-%d")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump({"day": today, "orders_today": [{"usd": 20.0}]}, fh)
    check("D1 today's orders are read", G.orders_today_now(p) == [{"usd": 20.0}])
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump({"day": "2020-01-01", "orders_today": [{"usd": 20.0}]}, fh)
    check("D2 a stale day rolls over to empty, as covenant_trader.roll_day does -- "
          "otherwise yesterday's orders block this morning",
          G.orders_today_now(p) == [])
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump({"day": today}, fh)
    check("D3 a state file with the right day but no orders_today key is unknown, "
          "not zero", G.orders_today_now(p) is None)

    # ---- S: one source of truth -------------------------------------------
    import covenant_trader as T
    same = {k: (G.CAP_DEFAULTS[k], T.DEFAULT_CONFIG.get(k))
            for k in G.CAP_DEFAULTS if G.CAP_DEFAULTS[k] != T.DEFAULT_CONFIG.get(k)}
    check("S1 guards.CAP_DEFAULTS matches covenant_trader.DEFAULT_CONFIG", not same, same)
    check("S2 guards.TRADER_STATE is the file covenant_trader writes",
          os.path.normcase(G.TRADER_STATE) == os.path.normcase(T.STATE),
          (G.TRADER_STATE, T.STATE))
    check("S3 both caps are in the default stack, so a caller that takes the "
          "defaults gets them",
          {"per_trade_cap", "per_day_cap"} <=
          {g.name for g in G.DEFAULTS})
    src = io.open(os.path.join(HERE, "covenant_trader.py"), encoding="utf-8").read()
    check("S4 preconditions() no longer does the cap arithmetic itself -- it asks "
          "the guards, so there is one implementation",
          "PerTradeCap(" in src and "largest_allowed(" in src
          and "spent + order[" not in src)
    check("S5 caps() survives a missing config file rather than raising",
          G.caps(os.path.join(d, "no_such_config.json")) == G.CAP_DEFAULTS)
    with io.open(os.path.join(d, "partial.json"), "w", encoding="utf-8") as fh:
        json.dump({"max_order_usd": 7.0}, fh)
    c = G.caps(os.path.join(d, "partial.json"))
    check("S6 a config that names one cap gets the shipped default for the rest",
          c["max_order_usd"] == 7.0
          and c["max_orders_per_day"] == G.CAP_DEFAULTS["max_orders_per_day"], c)

    # ---- B: the buy budget ------------------------------------------------
    res = os.path.join(d, "RESERVE.json")

    def bstate(start, spent, orders=None):
        return G.State(equity_now=1.0, equity_peak=1.0, equity_start_of_day=1.0,
                       closed_trades=[], last_sold={}, positions={}, cash=1.0,
                       orders_today=[] if orders is None else orders,
                       starting_total_usd=start, bought_total_usd=spent)

    bb = G.BuyBudget(0.50, reserve_path=res)
    check("B1 half the starting book is the budget, and it is stated in the reason",
          bb.remaining(bstate(6700.0, 0.0)) == 3350.0
          and "3,350.00" in bb.check(bstate(6700.0, 0.0)).reason)
    check("B2 spending draws it down cumulatively",
          bb.remaining(bstate(6700.0, 1000.0)) == 2350.0)
    check("B3 the budget can be exhausted, and then buying stops",
          not bb.check(bstate(6700.0, 3350.0)).allowed
          and bb.remaining(bstate(6700.0, 3350.0)) == 0.0)
    check("B4 THE RATCHET: the baseline is the STARTING book, so spending half "
          "does not make half of what is left spendable again -- eight rounds of "
          "spending everything permitted still totals half",
          abs(sum_spend(bb) - 3350.0) < 1e-6, sum_spend(bb))
    check("B5 an unknown starting book blocks rather than assuming one",
          not bb.check(bstate(None, 0.0)).allowed
          and bb.remaining(bstate(None, 0.0)) is None)
    check("B6 an unknown lifetime spend blocks rather than assuming zero -- "
          "assuming zero hands back a budget that may already be gone",
          not bb.check(bstate(6700.0, None)).allowed)
    check("B7 set_starting_total writes once and never overwrites",
          G.set_starting_total(6700.0, res) == 6700.0
          and G.set_starting_total(99.0, res) == 6700.0
          and G.starting_total(res) == 6700.0)
    check("B8 ...and it refuses a nonsense total rather than recording it",
          G.set_starting_total(0.0, os.path.join(d, "empty.json")) is None)

    check("B9 roll_day backfills the lifetime buy total to zero ONLY on evidence: "
          "a state with no closed trades, no orders and no equity peak has never "
          "seen a trade, so zero is a measurement",
          T.roll_day({"day": today, "closed_trades": [], "orders_today": [],
                      "equity_peak": 0.0}).get("bought_total_usd") == 0.0)
    check("B10 ...and a state that HAS traded keeps the figure absent, so the "
          "budget goes on blocking until someone who knows says what was spent",
          "bought_total_usd" not in
          T.roll_day({"day": today, "closed_trades": [{"sym": "X", "pnl": -1.0}],
                      "orders_today": [], "equity_peak": 900.0}))

    # ---- X: fiat needs permission -----------------------------------------
    nofiat = os.path.join(d, "nofiat.json")
    with io.open(nofiat, "w", encoding="utf-8") as fh:
        json.dump({"armed": False}, fh)
    yesfiat = os.path.join(d, "yesfiat.json")
    with io.open(yesfiat, "w", encoding="utf-8") as fh:
        json.dump({"allow_fiat_buys": True}, fh)
    fp = G.FiatBuyPermission(config_path=nofiat)
    check("X1 with nothing sold today, a buy would come out of dollars and blocks",
          not fp.check(bstate(1.0, 0.0, [])).allowed)
    check("X2 today's sale proceeds are buyable without permission",
          fp.check(bstate(1.0, 0.0, [{"usd": 40.0, "side": "sell"}])).allowed
          and fp.headroom(bstate(1.0, 0.0, [{"usd": 40.0, "side": "sell"}])) == 40.0)
    check("X3 ...and re-buying them uses the headroom up",
          not fp.check(bstate(1.0, 0.0, [{"usd": 40.0, "side": "sell"},
                                         {"usd": 40.0, "side": "buy"}])).allowed)
    check("X4 an order with no side recorded blocks, because proceeds cannot be "
          "separated from spending and guessing which is the whole question",
          not fp.check(bstate(1.0, 0.0, [{"usd": 40.0}])).allowed
          and "which side" in fp.check(bstate(1.0, 0.0, [{"usd": 40.0}])).reason)
    check("X5 an unknown day blocks", not fp.check(bstate(1.0, 0.0, None)).allowed)
    check("X6 permission in the config allows it outright, and says where it came from",
          G.FiatBuyPermission(config_path=yesfiat).check(bstate(1.0, 0.0, [])).allowed
          and "allow_fiat_buys" in
          G.FiatBuyPermission(config_path=yesfiat).check(bstate(1.0, 0.0, [])).reason)
    check("X7 a missing or malformed config is NOT permission",
          not G.allow_fiat_buys(os.path.join(d, "absent.json"))
          and not G.allow_fiat_buys(p))
    check("X8 covenant_trader records `side` on a booked order, without which "
          "this guard can never evaluate",
          '"side": o.get("side")' in src)
    check("X9 ...and accumulates the lifetime buy total the budget measures",
          'st["bought_total_usd"] = float(' in src)
    check("X10 both new guards are in the default stack",
          {"buy_budget", "fiat_permission"} <= {g.name for g in G.DEFAULTS})

    # ---- R: a rotation is not new money -----------------------------------
    # Settled 2026-09-04: "50 percent of current holdings excluding xrp can be
    # sold and rebought to gain yield and purchase other assets". Rotation IS
    # the mechanism, so charging it to the buy budget would switch the
    # mechanism off after roughly sixty-nine rotations at the $50 daily cap --
    # without a single dollar having entered the book. Only the part of a buy
    # that the day's sales did not cover is new money.
    check("R1 covenant_trader banks only the fiat portion of a buy, computed "
          "from the day's sale headroom BEFORE the order is appended -- "
          "appending first would count the order against itself",
          "fiat_part = max(0.0, float(o[\"usd\"]) - (room or 0.0))" in src
          and src.index("room = _guards.FiatBuyPermission().headroom(before)")
          < src.index('st.setdefault("orders_today", []).append'))
    check("R2 a fully-covered rotation banks nothing",
          "if o.get(\"side\") == \"buy\" and fiat_part > 0:" in src)
    check("R3 an unreadable day treats the whole order as new money, which is "
          "the safe direction", "(room or 0.0)" in src)

    # ---- L: the caps are read at every check, not frozen at import --------
    live = os.path.join(d, "live.json")
    with io.open(live, "w", encoding="utf-8") as fh:
        json.dump({"max_order_usd": 25.0, "max_daily_notional_usd": 50.0,
                   "max_orders_per_day": 2, "min_order_usd": 5.0}, fh)
    g = G.PerTradeCap(config_path=live)
    before = g.largest_allowed(state([]))
    with io.open(live, "w", encoding="utf-8") as fh:
        json.dump({"max_order_usd": 10.0, "max_daily_notional_usd": 50.0,
                   "max_orders_per_day": 2, "min_order_usd": 5.0}, fh)
    after = g.largest_allowed(state([]))
    check("L1 tightening a cap applies to the SAME guard object on the next check "
          "($%.2f -> $%.2f) -- DEFAULTS is built at import and covenant_trader "
          "--loop outlives it, so a frozen cap would need a restart to take effect"
          % (before, after), before == 25.0 and after == 10.0)
    check("L2 ...and an explicit argument still wins over the file",
          G.PerTradeCap(max_usd=99.0, config_path=live).max_usd == 99.0)

    n = sum(OK)
    print("\nF7: %d/%d passed" % (n, len(OK)))
    return 0 if n == len(OK) else 1


if __name__ == "__main__":
    raise SystemExit(main())
