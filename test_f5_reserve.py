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
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import guards as G                                                       # noqa: E402
# Imported at module level since A84, because P4 now asks covenant_trader for
# the VALUE of RESERVE_PATH rather than grepping its source for a literal.
import covenant_trader as T                                              # noqa: E402

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
    # P4 ASKS THE CONSTANT, NOT THE BYTES. A84 (2026-09-10).
    #
    # It used to be `'"private", "RESERVE.json"' in src` -- a substring test over
    # the whole of covenant_trader.py, which pins the PRESENCE of that literal
    # somewhere in the file and not the VALUE of RESERVE_PATH. Measured by
    # mutation: redirect the path to ops/ and leave the original expression
    # behind as a trailing `# was ...` comment, and F5 reported 39/39, exit 0 --
    # while the per-asset baseline quantities, the hold-only list and
    # starting_total_usd were written to ops/RESERVE.json, which `git
    # check-ignore` does not cover and `git add -n` accepts. That is the
    # operator's portfolio staged for a public commit, with the guard green.
    #
    # An env-var or fallback wrapper around the original expression does the
    # same. Reading the imported module's constant cannot be fooled by any of
    # them, because it is the value the program will actually use.
    check("P4 the baseline is written under private/, because a per-asset quantity is "
          "the portfolio (CONSTITUTION II.4)",
          os.path.basename(os.path.dirname(T.RESERVE_PATH)) == "private",
          T.RESERVE_PATH)
    # P4b is the half that actually protects him and that nothing asserted: the
    # directory being named private/ is worthless if git will commit it.
    _ign = subprocess.run(["git", "check-ignore", "-q", T.RESERVE_PATH],
                          cwd=HERE, capture_output=True)
    check("P4b ...and git genuinely ignores that path -- the name private/ is a "
          "convention, the ignore rule is the mechanism",
          _ign.returncode == 0, "check-ignore rc=%d" % _ign.returncode)

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

    # P5b: THE SAME RATCHET, THROUGH THE SHAPE gather() ACTUALLY PRODUCES.
    # Measured 2026-09-09 by mutation, in an isolated worktree: neuter
    # `q = p.get("qty")` in covenant_trader.reserve_baseline (so the quantity
    # falls through to the deprecated val/px round trip the comment above it
    # calls wrong), and this suite stayed fully green. Halving what that line
    # returns -- which records every frozen hold-only floor at half the coin
    # held, making half of XRP, HBAR and LINK sellable -- was invisible too.
    #
    # The reason is pf() eleven lines up: it builds a position with no "qty"
    # key at all, while gather() puts qty on every position it emits. So P5-P9
    # exercise only the fallback, and the branch production actually runs is
    # executed by nothing in this repository. The checks were real; the INPUT
    # was a shape the program never sees.
    #
    # Making qty and val/px disagree is the whole fix: qty says 100 units,
    # val/px says 150, and the floor that gets written names which one the
    # code believed. pf() is left as it is -- it still pins the fallback, which
    # is live code for any venue that reports value without quantity.
    tmp1b = os.path.join(tempfile.mkdtemp(), "RESERVE.json")
    b1b, held1b, _r1b = T.reserve_baseline(
        {"positions": [{"sym": "XLM", "qty": 100.0, "val": 300.0, "px": 2.0,
                        "at": "test"}], "total": 300.0, "cash": 0.0}, path=tmp1b)
    check("P5b the floor is the QUANTITY held, not a round trip through the price -- "
          "given qty=100 where val/px says 150, both the baseline and the holding "
          "it reports back to the planner read 100",
          b1b.get("XLM") == 100.0 and held1b.get("XLM") == 100.0, (b1b, held1b))

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

    # P10: A TORN FLOOR FILE IS UNKNOWN, NOT ABSENT. A78 (2026-09-10).
    #
    # Found by mutation audit: line 462 used to answer a parse failure with
    # `data, base = {}, {}` -- byte-identical to the answer for a file that was
    # never written. From an empty baseline every held symbol is "not in base",
    # so every floor is re-set to TODAY'S quantity, hold-only symbols included,
    # and the MERGE-never-rebuild write then rebuilds from {} and takes
    # starting_total_usd with it. Measured before the fix: a frozen XRP floor
    # of 500 followed the holding down to 300, and the buy budget re-anchored
    # to that day's book, in ONE cycle, with a note list byte-identical to a
    # legitimate first-ever run.
    #
    # P5 above claims to pin exactly this ratchet ("a baseline never follows a
    # holding DOWN") and stayed green with the branch inverted, because every
    # fixture it uses starts from a file that parses. The ratchet was pinned on
    # the happy path only.
    tmp4 = os.path.join(tempfile.mkdtemp(), "RESERVE.json")
    T.reserve_baseline(pf(500.0, "XRP"), path=tmp4)          # frozen floor at 500
    _intact = io.open(tmp4, encoding="utf-8").read()
    io.open(tmp4, "w", encoding="utf-8").write(_intact[:40])  # torn: truncated
    _torn = io.open(tmp4, encoding="utf-8").read()
    try:
        _b, _h, _r = T.reserve_baseline(pf(300.0, "XRP"), path=tmp4)
        _raised, _got = False, _b
    except T.ReserveUnreadable as _e:
        _raised, _got = True, str(_e)
    check("P10 a RESERVE.json that exists and will not parse RAISES rather than "
          "rebuilding from an empty baseline -- unknown is not absent", _raised, _got)
    check("P10b ...so the frozen hold-only floor of 500 does NOT follow the holding "
          "down to 300 through the torn-file path (the measured harm)",
          _raised and (not isinstance(_got, dict) or _got.get("XRP") != 300.0), _got)
    check("P10c ...and the unreadable file is left EXACTLY as found: a program that "
          "cannot read a floor file must not overwrite it either",
          io.open(tmp4, encoding="utf-8").read() == _torn)

    # A list is valid JSON and then raises AttributeError on .get, which the
    # original `except (OSError, ValueError)` never caught -- so this shape
    # crashed the cycle instead of failing closed. guards.set_starting_total
    # already defended against it; this reader did not.
    tmp5 = os.path.join(tempfile.mkdtemp(), "RESERVE.json")
    io.open(tmp5, "w", encoding="utf-8").write("[]")
    try:
        T.reserve_baseline(pf(100.0), path=tmp5)
        _shape = "no exception"
    except T.ReserveUnreadable as _e:
        _shape = "ReserveUnreadable"
    except Exception as _e:                                   # noqa: BLE001
        _shape = "%s: %s" % (type(_e).__name__, _e)
    check("P10d valid JSON of the wrong SHAPE (a list) is refused the same way, not "
          "an uncaught AttributeError", _shape == "ReserveUnreadable", _shape)

    # P10e: the planner's side of it. Every order plan() can produce is a SELL,
    # so refusing to plan is the conservative answer when the floors are
    # unknown -- the position is simply held for a cycle. reserve_baseline is
    # stubbed here because plan() binds RESERVE_PATH as a default argument at
    # import; what is under test is plan's HANDLING, not the read.
    _real = T.reserve_baseline
    try:
        def _boom(_pf, path=None):
            raise T.ReserveUnreadable("planted")
        T.reserve_baseline = _boom
        _orders, _notes = T.plan({"max_position_pct": 0.25}, pf(500.0, "XRP"))
    finally:
        T.reserve_baseline = _real
    check("P10e plan() returns NO orders when the floors are unreadable -- every order "
          "it can emit is a sale, so refusing is the conservative direction",
          _orders == [], _orders)
    check("P10f ...and says so loudly enough for an operator to act on",
          any("UNREADABLE" in n and "RESERVE" in n for n in _notes), _notes)

    # P10g: the write that could create the torn file is atomic, so this
    # program cannot manufacture the emergency it now fails closed on.
    tmp6 = os.path.join(tempfile.mkdtemp(), "RESERVE.json")
    T.reserve_baseline(pf(100.0), path=tmp6)
    check("P10g the floor write leaves no .tmp behind and the result parses",
          not os.path.exists(tmp6 + ".tmp")
          and isinstance(_json.loads(io.open(tmp6, encoding="utf-8").read()), dict))

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
    # A2's label used to read "nothing in the repository sets armed=True". It
    # reads five hand-listed files, so that is not what it measures, and the
    # wider claim is false at HEAD: FUTURE.bat:40 sets it, which is the design
    # (A1's comment above says so -- "your click is the arming"). Narrowed to
    # what it does measure; the repository-wide claim is A2b's, below.
    check("A2 nothing on the scheduled trading path -- the trader, the bridge, the "
          "daily and nightly passes -- sets armed=True; arming is an operator's edit "
          "with an operator's key, and the trader says so itself", not arming, arming[:4])

    # A2b: THE SAME CLAIM, OVER THE WHOLE TREE. Measured 2026-09-09 by
    # mutation: add covenant_autoarm.py (a module that flips trader_config.json
    # to armed=true, armed_by, armed_at at import time) and one line --
    # `import covenant_autoarm` -- to covenant_nightly.py, which IS one of the
    # five files A2 reads. The suite stayed fully green, because the arming
    # statement lives one file over and an import line matches neither regex.
    # A scheduled unattended pass then armed the trader with no operator action
    # and no operator key, and covenant_selfaudit's C6 provenance check passes
    # on any non-empty armed_by, which the mutant supplies.
    #
    # So the scan region is the check, not the regexes. This walks every .py,
    # .bat and .ps1 in the tree and names FUTURE.bat as the ONE exception --
    # an exception nobody can see is not an exception, it is a hole. .claude/
    # is skipped because it holds worktrees, which are whole copies of the
    # repository; the walk is ~240 files and a sixth of a second.
    SKIP_DIRS = {".git", ".claude", "__pycache__", ".venv", "node_modules"}
    ARMS_IT = {"FUTURE.bat"}          # the operator's one click IS the arming
    elsewhere = []
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if (not f.endswith((".py", ".bat", ".ps1"))
                    or f.startswith("test_") or f in ARMS_IT):
                continue
            fp = os.path.join(root, f)
            try:
                body = io.open(fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for i, line in enumerate(body.splitlines(), 1):
                t = line.strip()
                if t.startswith("#") or t[:4].upper() == "REM ":
                    continue
                if (re.search(r'["\']armed["\']\s*\]?\s*=\s*True', t)
                        or re.search(r'armed\s*=\s*True', t)):
                    elsewhere.append("%s:%d" % (os.path.relpath(fp, HERE), i))
    check("A2b ...and no other file ANYWHERE in the tree arms it either -- FUTURE.bat, "
          "the operator's own click, is the only thing in this repository that can",
          not elsewhere, elsewhere[:4])

    n = sum(OK)
    print("\nF5: %d/%d passed" % (n, len(OK)))
    return 0 if n == len(OK) else 1


if __name__ == "__main__":
    raise SystemExit(main())
