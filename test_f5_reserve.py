#!/usr/bin/env python3
"""test_f5_reserve.py -- F5: half of every coin is not for sale, and the
program cannot move money off the exchange.

WHY (asked 2026-09-04: "50% of every current coin should be off limits",
"only with 50% of current holdings on coinbase", "can buy but can't withdraw
from my bank")

  Three separate promises, and a promise that is not pinned is a comment.

  THE RATCHET is the one that matters, and it is why the baseline is stored
  rather than recomputed. Read the rule as "half of what I hold right now" and
  check it per order, and it permits selling everything: half of 100 leaves
  50, half of 50 leaves 25, and eight orders later the position is 0.4 units
  with no single order ever breaking the rule. A floor that moves down with
  the balance it protects is not a floor. R* pins that eight rounds of selling
  everything permitted leaves exactly half.

  WHERE IT IS ENFORCED matters too. covenant_trader's guard stack is consulted
  for buys only -- "a guard never stops a sale" -- and every order that
  planner can produce is a sell. A reserve enforced in the guard stack alone
  would never run. P* pins that the PLANNER clamps the quantity, before an
  order exists.

  AND WHAT THE PROGRAM CANNOT DO AT ALL. W* reads the trading sources and
  asserts there is no withdrawal, bank, ACH, wire or payment-method path in
  any of them. The venue adapters read balances, list pairs and place orders.
  Money can move between assets on the exchange; it cannot leave.

  A* pins that the trader ships disarmed and that nothing in the repository
  turns arming on. Arming is an operator's edit with an operator's key, and
  the program says so in its own docstring.

Run:  python test_f5_reserve.py     (offline; no exchange, no keys, no network)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import guards as G                                                       # noqa: E402

OK = []


def check(name, cond, detail=""):
    OK.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name,
                        ("  " + str(detail)[:160]) if (detail and not cond) else ""))


def state(held, base, sym="XLM"):
    return G.State(equity_now=1000.0, equity_peak=1000.0, equity_start_of_day=1000.0,
                   closed_trades=[], last_sold={}, positions={sym: held * 5.0},
                   cash=500.0, quantities={sym: held}, reserve_baseline={sym: base})


def main():
    print("F5 -- the reserved half, and what the program cannot do\n")
    g = G.ReserveFloor(0.50)

    # ---- H: hold-only -----------------------------------------------------
    # Asked 2026-09-04: "50 percent of current holdings excluding xrp can be
    # sold and rebought". XRP is not half-reserved, it is wholly reserved, and
    # the R* tests below therefore use XLM -- a suite that demonstrated the
    # fifty-percent rule on the one symbol exempt from it would be measuring
    # nothing. That substitution is the reason these checks exist: to make sure
    # the exemption is real and not an artefact of changing the example.
    check("H1 at the frozen floor nothing of a hold-only asset is sellable "
          "(100 held against a 100 baseline)",
          G.ReserveFloor.sellable(state(100.0, 100.0, "XRP"), "XRP") == 0.0)
    # H1b IS THE 2026-09-07 RULE. "hold the current amount able to add and use
    # for trading": the floor is the whole baseline rather than half of it, so
    # what is bought ABOVE the floor is tradeable like any other asset. Before
    # this date sellable_units returned a flat 0.0 for these symbols and the
    # 40 units below would have been locked on arrival.
    check("H1b ...but what is held ABOVE that floor is sellable (140 held "
          "against a frozen 100 baseline leaves 40)",
          G.ReserveFloor.sellable(state(140.0, 100.0, "XRP"), "XRP") == 40.0)
    check("H1c a hold-only asset with NO recorded baseline fails closed at 0, "
          "not None -- with no floor there is no 'above the floor'",
          G.sellable_units(140.0, None, "XRP") == 0.0)
    check("H1d ...while a 50%-reserved asset with no baseline still makes no "
          "claim either way, so a caller cannot mistake one for the other",
          G.sellable_units(140.0, None, "XLM") is None)
    check("H2 ...and at the floor the guard refuses rather than trimming",
          not g.check(state(100.0, 100.0, "XRP"), "XRP").allowed
          and "hold-only" in g.check(state(100.0, 100.0, "XRP"), "XRP").reason)
    check("H2b ...and above the floor it ALLOWS, because a rule that refused "
          "here would make 'able to add and use for trading' unreachable",
          g.check(state(140.0, 100.0, "XRP"), "XRP").allowed)
    check("H3 zero sellable is KNOWN, not unknown -- None means 'no baseline "
          "recorded' and would let a caller fall through to its own default",
          G.ReserveFloor.sellable(state(100.0, 100.0, "XRP"), "XRP") is not None)
    check("H3b the reserved fraction is 1.0 for a hold-only symbol and 0.50 "
          "for every other, from one function rather than two branches",
          G.reserved_pct("XRP") == 1.0 and G.reserved_pct("HBAR") == 1.0
          and G.reserved_pct("LINK") == 1.0 and G.reserved_pct("XLM") == 0.50)
    check("H4 XRP, HBAR and LINK are the hold-only set (HBAR and LINK added "
          "2026-09-07), and nothing in the program adds to it",
          G.HOLD_ONLY == ("XRP", "HBAR", "LINK"))
    src_g = io.open(os.path.join(HERE, "guards.py"), encoding="utf-8").read()
    check("H5 HOLD_ONLY is assigned exactly once -- a second assignment anywhere "
          "would mean a rule that can be widened at runtime",
          src_g.count("HOLD_ONLY = ") == 1, src_g.count("HOLD_ONLY = "))
    check("H6a HOLD-ONLY IS ABOUT SELLING, NOT BUYING. may_buy() must not refuse "
          "to add XRP just because none of it may be sold -- the two are "
          "different questions and conflating them is a rule nobody asked for",
          G.GuardStack([G.ReserveFloor(0.50)]).may_buy(
              state(100.0, 100.0, "XRP"), "XRP")[0])
    check("H6b ...and the reserve still refuses the SALE it is there to refuse",
          not G.ReserveFloor(0.50).check(state(100.0, 100.0, "XRP"), "XRP").allowed)
    check("H6c the reserve declares itself sell-side, which is what makes the "
          "distinction executable rather than a comment",
          G.ReserveFloor(0.50).side == "sell"
          and G.PerDayCap().side == "both"
          and G.MaxDrawdown().side == "buy")
    check("H6d ...and evaluate() still REPORTS it, so the operator sees the "
          "reserve line whether or not it bears on the question asked",
          any(v.guard == "reserve_floor" for v in
              G.GuardStack([G.ReserveFloor(0.50)]).evaluate(
                  state(100.0, 100.0, "XRP"), "XRP")))
    check("H6 an asset that is NOT hold-only still gets the half rule",
          G.ReserveFloor.sellable(state(100.0, 100.0, "XLM"), "XLM") == 50.0)
    src_t = io.open(os.path.join(HERE, "covenant_trader.py"), encoding="utf-8").read()
    check("H7 the planner clamps through guards.sellable_units rather than its own "
          "copy of the arithmetic, so the hold-only rule reaches the order it plans",
          "sellable_units(" in src_t)

    # ---- R: the ratchet ---------------------------------------------------
    held = 100.0
    for _ in range(8):
        held -= G.ReserveFloor.sellable(state(held, 100.0), "XLM")
    check("R1 eight rounds of selling everything permitted leaves exactly half, not "
          "nothing (%.4f units of a 100 baseline)" % held, abs(held - 50.0) < 1e-9, held)
    check("R2 a sell is refused once the holding is at the floor",
          not g.check(state(50.0, 100.0), "XLM").allowed)
    check("R3 ...and below it", not g.check(state(49.0, 100.0), "XLM").allowed)
    check("R4 above the floor it allows, and says how much is sellable",
          g.check(state(100.0, 100.0), "XLM").allowed
          and "50 sellable" in g.check(state(100.0, 100.0), "XLM").reason)
    check("R5 buying more raises what half means",
          G.ReserveFloor.sellable(state(120.0, 100.0), "XLM") == 70.0)
    check("R6 an asset with no baseline recorded gets no claim either way, rather than "
          "a silent pass", "no baseline recorded" in
          g.check(G.State(equity_now=1.0, equity_peak=1.0, equity_start_of_day=1.0,
                          closed_trades=[], last_sold={}, positions={}, cash=1.0), "XLM").reason)
    check("R7 the floor is in the default stack, so it is on unless someone removes it",
          any(isinstance(x, G.ReserveFloor) for x in G.DEFAULTS))

    # ---- P: enforced where the orders are made ---------------------------
    src = io.open(os.path.join(HERE, "covenant_trader.py"), encoding="utf-8").read()
    check("P1 the planner reads a stored baseline rather than recomputing half of the "
          "current balance", "def reserve_baseline(" in src and "RESERVE_PATH" in src)
    check("P2 the planner clamps the sell quantity itself, not just the guard stack "
          "(which is consulted for buys only)",
          "sell trimmed" in src and "sellable" in src)
    check("P3 a sell that starts at the floor is DROPPED, not sent at zero size",
          "sell DROPPED" in src)
    check("P4 the baseline is written under private/, because a per-asset quantity is "
          "the portfolio (CONSTITUTION II.4)", '"private", "RESERVE.json"' in src)

    # ---- P2b/H7b: THE SAME CLAIMS, RUN RATHER THAN READ --------------------
    # P1-P4 and H7 above are greps. Measured 2026-09-09 by mutation, in an
    # isolated worktree: delete both `qty = sellable` clamps in
    # covenant_trader.plan() and this suite stayed at 35/35, fully green.
    #
    # Those two lines are the ONLY enforcement of the 50% reserve and of the
    # frozen HOLD_ONLY floor. guards.py gates BUYS only -- "a guard never stops
    # a risk-reducing sale" -- so nothing downstream re-checks the quantity.
    # With them gone the planner emits a 75-unit sell of a 100-unit position
    # against a 50-unit floor, and a 75-unit sell of XRP, which must never be
    # sellable at all. The trader is armed.
    #
    # It is worse than a silent break: the notes.append() lines survive the
    # mutation, so the planner PRINTS "reserve: XLM sell trimmed 75 -> 50
    # units ... no rule may cross it" and then attaches a 75-unit order. The
    # operator's own audit trail would report the floor honoured while it was
    # being crossed.
    #
    # The lesson was already in this file, eleven lines below, at P5: "a test
    # that reads the prose instead of running the code". It was applied to one
    # check and not to its neighbours. So: run the code.
    import covenant_trader as T

    def _planned_sell(sym):
        """Units of `sym` the planner actually attaches to a plan.

        Baselines are stubbed to 100 so the reserve is a known 50, and the
        position is built over the concentration cap so a sale is wanted at
        all: the cap asks for 75, the reserve permits 50, hold-only permits 0.
        """
        real = T.reserve_baseline
        T.reserve_baseline = lambda pf, path=None: (
            {p["sym"]: 100.0 for p in pf["positions"]},
            {p["sym"]: 100.0 for p in pf["positions"]}, [])
        try:
            out = T.plan(dict(T.DEFAULT_CONFIG),
                         {"positions": [{"sym": sym, "val": 200.0, "px": 2.0,
                                         "qty": 100.0, "at": "t", "regime": "UP"}],
                          "total": 250.0, "cash": 50.0})
        finally:
            T.reserve_baseline = real
        orders = out[0] if isinstance(out, tuple) else out
        return sum(o["qty"] for o in orders if o.get("side") == "sell")

    _xlm = _planned_sell("XLM")
    check("P2b the planner CLAMPS the quantity it plans -- the concentration cap wants "
          "75 units of a 100-unit position sold and the reserve permits 50",
          abs(_xlm - 50.0) < 1e-9, _xlm)
    _xrp = _planned_sell("XRP")
    check("H7b a hold-only asset at its frozen floor is planned for NO sale at all, "
          "not merely a trimmed one", abs(_xrp) < 1e-9, _xrp)
    # P5 is BEHAVIOURAL. The first version of this check grepped the function
    # body for the word "lower" and failed on the docstring that explains why
    # it never lowers -- a test that reads the prose instead of running the
    # code. Run the code: hand it a SMALLER holding and see whether the stored
    # number follows it down. That is the ratchet, and it is the whole point.
    import tempfile
    import covenant_trader as T
    tmp = os.path.join(tempfile.mkdtemp(), "RESERVE.json")

    def pf(units, sym="XLM"):
        return {"positions": [{"sym": sym, "val": units * 2.0, "px": 2.0, "at": "test"}],
                "total": units * 2.0, "cash": 0.0}

    base1, _held, _r = T.reserve_baseline(pf(100.0), path=tmp)
    base2, _held, _r = T.reserve_baseline(pf(40.0), path=tmp)     # sold most of it
    base3, _held, _r = T.reserve_baseline(pf(160.0), path=tmp)    # then bought more
    check("P5 a baseline never follows a holding DOWN (100 -> sold to 40 -> baseline still %.8g)"
          % base2.get("XLM", -1), base1["XLM"] == 100.0 and base2["XLM"] == 100.0, base2)
    check("P6 ...and for a 50%%-reserved asset it does follow a holding UP, because new coin "
          "changes what half means (bought to 160 -> baseline %.8g)"
          % base3.get("XLM", -1), base3["XLM"] == 160.0, base3)

    # P7 IS THE OTHER HALF OF THE 2026-09-07 RULE, and it is the one that is
    # easy to get backwards. For a hold-only symbol the floor must NOT follow a
    # purchase up: raising it would lift the floor above the coin that was just
    # bought and lock it on arrival, which is the exact opposite of "able to
    # add and use for trading".
    tmp2 = os.path.join(tempfile.mkdtemp(), "RESERVE.json")
    h1, _hh, _hr = T.reserve_baseline(pf(100.0, "XRP"), path=tmp2)
    h2, _hh, _hr = T.reserve_baseline(pf(160.0, "XRP"), path=tmp2)   # bought more
    check("P7 a hold-only baseline is FROZEN and does not follow a purchase up "
          "(100 -> bought to 160 -> floor still %.8g)" % h2.get("XRP", -1),
          h1["XRP"] == 100.0 and h2["XRP"] == 100.0, h2)
    check("P8 ...so the 60 units bought above that frozen floor are tradeable",
          G.sellable_units(160.0, h2["XRP"], "XRP") == 60.0)

    # P9: reserve_baseline MERGES rather than rebuilding. guards.set_starting_total
    # writes starting_total_usd into this same file; a fresh dict deleted it, and
    # the next cycle then re-anchored the buy budget to that day's book -- the
    # ratchet set_starting_total exists to prevent.
    import json as _json
    tmp3 = os.path.join(tempfile.mkdtemp(), "RESERVE.json")
    T.reserve_baseline(pf(100.0), path=tmp3)
    d = _json.loads(io.open(tmp3, encoding="utf-8").read())
    d["starting_total_usd"] = 6899.82
    io.open(tmp3, "w", encoding="utf-8").write(_json.dumps(d))
    T.reserve_baseline(pf(100.0, "ADA"), path=tmp3)                  # a new asset: writes
    d2 = _json.loads(io.open(tmp3, encoding="utf-8").read())
    check("P9 a later write keeps starting_total_usd instead of erasing it "
          "(found %r)" % d2.get("starting_total_usd"),
          d2.get("starting_total_usd") == 6899.82, d2)

    # ---- W: what it cannot do at all -------------------------------------
    BANK = re.compile(r"\b(withdraw\w*|payment_method\w*|ach_transfer|wire_transfer|"
                      r"bank_account|cash_out)\b", re.I)
    offenders = []
    for f in ("covenant_trader.py", "venues.py", "covenant_trading_bridge.py"):
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        for i, line in enumerate(io.open(p, encoding="utf-8"), 1):
            if BANK.search(line) and not line.lstrip().startswith("#"):
                offenders.append("%s:%d" % (f, i))
    check("W1 no withdrawal, bank, ACH, wire or payment-method path exists in the "
          "trading sources -- value can move between assets, it cannot leave",
          not offenders, offenders[:4])

    # ---- A: it ships disarmed --------------------------------------------
    import json
    # trader_config.json is the OPERATOR's file and is deliberately not shipped
    # -- it holds their caps and their arming decision. On a clean checkout it
    # does not exist, and the first version of this check crashed there, which
    # is how CI found it. Absent is the correct state for a fresh clone, so the
    # property is checked against whichever one is authoritative: the file when
    # an operator has one, the code's default when nobody does.
    cfg_path = os.path.join(HERE, "trader_config.json")
    if os.path.exists(cfg_path):
        cfg = json.load(io.open(cfg_path, encoding="utf-8"))
        # 2026-09-06: the operator armed the trader himself (future.bat, "your
        # click is the arming"). The check is now provenance, not posture: an
        # explicit boolean; and if it is true, the arming must be traceable to
        # a one-click run in trader_log.txt -- nothing else may flip it.
        armed = cfg.get("armed")
        # PROVENANCE FROM THE CONFIG ITSELF, not from trader_log.txt. The first
        # version of this check read the log for a FUTURE run, which passed
        # standalone and failed inside covenant_one -- a shared mutable file
        # that another suite can move while this one reads it. Evidence that
        # races is not evidence. FUTURE.bat now writes armed_by and armed_at
        # beside the flag it sets, so the claim and its provenance live or die
        # together in one file.
        check("A1 this operator's config states armed explicitly, and if armed it records who armed it (FUTURE.bat writes armed_by beside the flag)",
              armed is False or (armed is True and bool(cfg.get("armed_by"))))
    else:
        tsrc = io.open(os.path.join(HERE, "covenant_trader.py"), encoding="utf-8").read()
        check("A1 no config here (a clean checkout), and the default the trader would "
              "write is disarmed", re.search(r'"armed"\s*:\s*False', tsrc) is not None)
    arming = []
    for f in ("covenant_trader.py", "covenant_trading_bridge.py", "trade_daily.py",
              "daily.py", "covenant_nightly.py"):
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        for i, line in enumerate(io.open(p, encoding="utf-8"), 1):
            t = line.strip()
            if t.startswith("#"):
                continue
            if re.search(r'["\']armed["\']\s*\]?\s*=\s*True', t) or re.search(r'armed\s*=\s*True', t):
                arming.append("%s:%d" % (f, i))
    check("A2 nothing in the repository sets armed=True -- arming is an operator's edit "
          "with an operator's key, and the trader says so itself", not arming, arming[:4])

    n = sum(OK)
    print("\nF5: %d/%d passed" % (n, len(OK)))
    return 0 if n == len(OK) else 1


if __name__ == "__main__":
    raise SystemExit(main())
