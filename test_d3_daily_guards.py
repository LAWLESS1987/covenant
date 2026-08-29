#!/usr/bin/env python3
"""
test_d3_daily_guards.py -- D3 + D4.

WHY THIS EXISTS
  `guards.py` and `daily.py` were the two files on the live-trading checklist
  (TRADING_READINESS.md section 2, lines 3 and 4) that had never had a single
  automated test. They were also the two the loop could not reach, because they
  live on L's machine and every scheduled run is a cloud session with no device
  bridge. Both facts stopped being true today.

  The first thing this suite found is not a subtle one: `grep -i guard daily.py`
  on the shipped file returned NOTHING. Every circuit breaker in guards.py was
  written, documented, hand-tested -- and called by nothing. D4 wires them in;
  the G-checks below pin what they do and the W/D-checks pin the wiring.

  The second is that DAILY_CHECK.md section 3 has mandated four verification
  checks on every price window since 2026-08-20 -- contiguity, duplicates,
  non-positive prices, staleness -- and daily.py implemented none of them. A
  70-day-stale series would have printed as a clean regime call. The D-checks
  are the executable version of that section.

  No network. No key. Nothing here trades.
"""
from __future__ import annotations
import contextlib
import io as _io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guards                      # noqa: E402
import daily                       # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail and not ok else ""))


def st(**kw):
    base = dict(equity_now=100.0, equity_peak=100.0, equity_start_of_day=100.0,
                closed_trades=[], last_sold={}, positions={"XLM": 50.0}, cash=50.0,
                now=1_800_000_000.0)
    base.update(kw)
    return guards.State(**base)


# =========================================================== G: the breakers
print("\nG  guards.py -- every breaker, both sides of its boundary")

g = guards.MaxDrawdown(0.25)
check("G1a drawdown under limit allowed", g.check(st(equity_now=80, equity_peak=100)).allowed)
check("G1b drawdown AT limit blocks", not g.check(st(equity_now=75, equity_peak=100)).allowed)
check("G1c no peak recorded -> BLOCKS (fail closed)",
      not g.check(st(equity_peak=0)).allowed)
check("G1d the blocking reason carries the number",
      "25.0%" in g.check(st(equity_now=75, equity_peak=100)).reason,
      g.check(st(equity_now=75, equity_peak=100)).reason)

g = guards.DailyLossLimit(0.08)
check("G2a small daily loss allowed",
      g.check(st(equity_now=95, equity_start_of_day=100)).allowed)
check("G2b loss at the limit blocks",
      not g.check(st(equity_now=92, equity_start_of_day=100)).allowed)
check("G2c no start-of-day equity -> BLOCKS (fail closed)",
      not g.check(st(equity_start_of_day=0)).allowed)

g = guards.CooldownPeriod(7)
now = 1_800_000_000.0
check("G3a inside cooldown blocks",
      not g.check(st(now=now, last_sold={"XLM": now - 3 * 86400}), "XLM").allowed)
check("G3b outside cooldown allowed",
      g.check(st(now=now, last_sold={"XLM": now - 8 * 86400}), "XLM").allowed)
check("G3c never sold -> allowed", g.check(st(now=now), "SOL").allowed)
check("G3d no symbol -> not asset-specific", g.check(st(now=now)).allowed)

g = guards.LossStreak(4, 30)
recent = [{"sym": "X", "pnl": -1, "closed_at": now - i * 86400} for i in range(4)]
old = [{"sym": "X", "pnl": -1, "closed_at": now - (40 + i) * 86400} for i in range(9)]
check("G4a four losses in the window blocks",
      not g.check(st(now=now, closed_trades=recent)).allowed)
check("G4b nine losses OUTSIDE the window do not",
      g.check(st(now=now, closed_trades=old)).allowed)
check("G4c wins do not count",
      g.check(st(now=now, closed_trades=[dict(t, pnl=1) for t in recent])).allowed)

g = guards.ConcentrationCap(0.20)
check("G5a under the cap allowed",
      g.check(st(positions={"XLM": 10.0}, cash=90.0), "XLM").allowed)
check("G5b at the cap blocks",
      not g.check(st(positions={"XLM": 20.0}, cash=80.0), "XLM").allowed)
check("G5c zero portfolio -> BLOCKS (fail closed)",
      not g.check(st(positions={}, cash=0.0), "XLM").allowed)

g = guards.CashFloor(0.10)
check("G6a cash at the floor allowed", g.check(st(positions={"X": 90.0}, cash=10.0)).allowed)
check("G6b cash under the floor blocks", not g.check(st(positions={"X": 95.0}, cash=5.0)).allowed)

stack = guards.GuardStack()
# cash 4/50 = 8% is UNDER the 10% floor -- at exactly 10% CashFloor allows, as
# G6a asserts, so the fixture has to be under it for this to test what it says.
bad = st(equity_now=50, equity_peak=100, equity_start_of_day=100,
         positions={"XLM": 46.0}, cash=4.0, now=now, last_sold={"XLM": now - 3600})
verdicts = stack.evaluate(bad, "XLM")
blocked = {v.guard for v in verdicts if not v.allowed}
check("G7 evaluate() reports ALL blocks, not just the first",
      {"max_drawdown", "daily_loss", "cooldown", "concentration", "cash_floor"} <= blocked,
      sorted(blocked))
ok, blocks, _ = stack.may_buy(bad, "XLM")
check("G7b may_buy is False and returns every block", (not ok) and len(blocks) >= 5, len(blocks))


class Exploding(guards.Guard):
    name = "exploding"

    def check(self, s, sym=None):
        raise ZeroDivisionError("boom")


v = guards.GuardStack([Exploding()]).evaluate(st())
check("G8 a guard that RAISES becomes a BLOCK, not a crash and not a pass",
      len(v) == 1 and not v[0].allowed and "ZeroDivisionError" in v[0].reason,
      v[0].reason if v else "no verdict")

# ================================================ D: daily.py candle checks
print("\nD  daily.py -- DAILY_CHECK.md section 3, made executable")

DAY = 86400
NOW = int(time.time()) // DAY * DAY


def rows(n=210, step=DAY, start=None, close=1.0, mutate=None):
    """Coinbase candle rows: [time, low, high, open, close, volume], any order."""
    start = NOW - DAY if start is None else start
    out = [[start - i * step, close, close, close, close, 1.0] for i in range(n)]
    if mutate:
        mutate(out)
    return out


def with_rows(r):
    """Run daily.fetch("XLM") against a canned candle response."""
    class _R:
        def __init__(self, payload):
            self._p = payload

        def read(self):
            return json.dumps(self._p).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    real = daily.urllib.request.urlopen
    daily.urllib.request.urlopen = lambda *a, **k: _R(r)
    try:
        return daily.fetch_coinbase("XLM")     # the venue reader, not the dispatcher
    finally:
        daily.urllib.request.urlopen = real


px, closes, why = with_rows(rows())
check("D1 a clean contiguous window is accepted", px is not None and why is None, why)
check("D1b 200 settled closes are returned", closes is not None and len(closes) == 200,
      None if closes is None else len(closes))

r = rows()
r[5] = list(r[4])                       # duplicate timestamp
px, _, why = with_rows(r)
check("D2 duplicate timestamps refused", px is None and "duplicate" in (why or ""), why)

r = rows()
del r[7]                                # a hole -> a 2-day gap
px, _, why = with_rows(r)
check("D3 non-contiguous bars refused", px is None and "non-contiguous" in (why or ""), why)

r = rows()
r[9][4] = 0.0
px, _, why = with_rows(r)
check("D4 non-positive close refused", px is None and "non-positive" in (why or ""), why)

px, _, why = with_rows(rows(start=NOW - 70 * DAY))
check("D5 a 70-day-stale series is refused, not reported",
      px is None and "read is broken" in (why or ""), why)

px, _, why = with_rows(rows(n=20))
check("D6 too few settled bars refused", px is None and "need 30" in (why or ""), why)

# today's forming bar: used as the live price, kept OUT of the mean
r = rows(n=210, start=NOW)              # newest bar is today
for row in r:
    row[4] = 2.0
r[0][4] = 99.0                          # today's bar is wild
px, closes, why = with_rows(r)
check("D7 today's forming bar IS the live price", px == 99.0, px)
check("D7b today's forming bar is NOT in the regime mean",
      closes is not None and 99.0 not in closes and set(closes) == {2.0},
      None if closes is None else sorted(set(closes))[:3])

# ==================================================== S: state + guard_state
print("\nS  daily.py state journal -- what makes the breakers real")

tmp = tempfile.mkdtemp()
daily.STATE_PATH = os.path.join(tmp, "daily_state.json")
s0 = daily.load_state()
check("S1 a missing state file loads as empty, not an exception",
      s0["equity"] == [] and s0["last_sold"] == {} and s0["closed_trades"] == [])
s0["equity"] = [[float(i), 100.0 + i] for i in range(500)]
daily.save_state(s0)
s1 = daily.load_state()
check("S2 equity history is trimmed to 400 entries", len(s1["equity"]) == 400, len(s1["equity"]))
check("S2b it keeps the NEWEST 400", s1["equity"][-1][1] == 599.0, s1["equity"][-1])

# A FIXED midday clock. With time.time() the "is this reading from today?"
# branch depends on what hour the suite happens to run at -- the test would
# pass for the wrong reason before midnight and fail after it.
NOON = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 12:00:00",
                                 "%Y-%m-%d %H:%M:%S"))
hist = {"equity": [[NOON - 5 * 86400, 200.0], [NOON - 4 * 3600, 120.0]],
        "last_sold": {}, "closed_trades": []}
gs, notes = daily.guard_state(hist, 100.0, 10.0, {"XLM": 90.0}, now=NOON)
check("S3 peak comes from history, not from today", gs.equity_peak == 200.0, gs.equity_peak)
check("S3b a reading from TODAY is the start-of-day", gs.equity_start_of_day == 120.0,
      gs.equity_start_of_day)
check("S3c no fallback note when today's own reading was used",
      not any("48h" in n for n in notes), notes)

# nothing from today, but yesterday evening is inside 48h -> fall back, and SAY so
hist = {"equity": [[NOON - 20 * 3600, 111.0]], "last_sold": {}, "closed_trades": []}
gs, notes = daily.guard_state(hist, 100.0, 10.0, {"XLM": 90.0}, now=NOON)
check("S3d start-of-day falls back to a <48h reading", gs.equity_start_of_day == 111.0,
      gs.equity_start_of_day)
check("S3e the fallback is stated, not hidden",
      any("48h old" in n for n in notes), notes)
now = time.time()

stale = {"equity": [[now - 5 * 86400, 200.0]], "last_sold": {}, "closed_trades": []}
gs, notes = daily.guard_state(stale, 100.0, 10.0, {"XLM": 90.0}, now=now)
check("S4 no reading inside 48h -> start-of-day 0 so the guard FAILS CLOSED",
      gs.equity_start_of_day == 0.0 and
      not guards.DailyLossLimit().check(gs).allowed, gs.equity_start_of_day)
check("S4b and it says WHY it cannot evaluate", any("48h" in n for n in notes), notes)
check("S5 an empty trade log is called out rather than read as 'no losses'",
      any("loss-streak" in n for n in notes), notes)

# ======================================================= E: end to end (D4)
print("\nE  end to end: the breakers actually gate 'may add'")

HOLD = [{"sym": "XLM", "qty": 100.0, "avg": 1.0, "manual": None},
        {"sym": "SOL", "qty": 10.0, "avg": 1.0, "manual": None},
        {"sym": "CC", "qty": 10.0, "avg": 1.0, "manual": 0.5},
        {"sym": "CASH", "qty": 1.0, "avg": 1.0, "manual": None}]


KEEP = object()      # leave daily_state.json exactly as the previous run left it


def run_main(argv, prices, state=None):
    """Run daily.main() with fetch stubbed. prices: {sym: (px, closes, why)}
    state=None resets the journal, state=KEEP leaves it, a dict installs it."""
    real_fetch, real_hold, real_argv = daily.fetch, daily.load_holdings, sys.argv
    # *a/**k: daily.fetch grew (source=, notes=, divs=) on 2026-08-28 and the
    # old one-arg stub then broke every path through one() with a TypeError
    # scored as NO RESULT. The stub ignores them, as it ignored source before.
    daily.fetch = lambda s, *a, **k: prices.get(s, (None, None, "not stubbed"))
    daily.load_holdings = lambda *a, **k: [dict(h) for h in HOLD]
    sys.argv = ["daily.py"] + argv
    if state is KEEP:
        pass
    elif state is not None:
        with open(daily.STATE_PATH, "w") as f:
            json.dump(state, f)
    elif os.path.exists(daily.STATE_PATH):
        os.remove(daily.STATE_PATH)
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            daily.main()
    finally:
        daily.fetch, daily.load_holdings, sys.argv = real_fetch, real_hold, real_argv
    return buf.getvalue()


up = (2.0, [1.0] * 200, None)            # price above its own mean -> UP
down = (0.5, [1.0] * 200, None)          # below -> DOWN
out = run_main([], {"XLM": up, "SOL": down})
check("E1 the guards section is printed at all", "CIRCUIT BREAKERS" in out)
check("E2 an over-cap position is still trimmed", "TRIM XLM" in out, out[-400:])
check("E3 the cash floor is still flagged", "CASH: you hold" in out)
check("E4 a hand-entered price is labelled as hand-entered", "hand-entered price" in out)
check("E5 rule 4 still names the below-line assets", "do NOT add to SOL" in out)
check("E6 concentration blocks adding to the over-cap asset",
      "[BLOCK] XLM" in out, [l for l in out.splitlines() if "XLM" in l and "BLOCK" in l])
check("E7 the permitted-to-add line is present and empty",
      "adding is permitted by the guards only for: NONE" in out,
      [l for l in out.splitlines() if "permitted" in l])
check("E8 a run with no history says so instead of implying safety",
      "first run" in out or "48h" in out)

# a clean, diversified book where nothing is blocked
HOLD = [{"sym": "XLM", "qty": 5.0, "avg": 1.0, "manual": None},
        {"sym": "SOL", "qty": 5.0, "avg": 1.0, "manual": None},
        {"sym": "ADA", "qty": 5.0, "avg": 1.0, "manual": None},
        {"sym": "XRP", "qty": 5.0, "avg": 1.0, "manual": None},
        {"sym": "HBAR", "qty": 5.0, "avg": 1.0, "manual": None},
        {"sym": "CASH", "qty": 20.0, "avg": 1.0, "manual": None}]
now = time.time()
good_state = {"equity": [[now - 3600, 44.0]], "last_sold": {}, "closed_trades": []}
out = run_main([], {s: up for s in ("XLM", "SOL", "ADA", "XRP", "HBAR")}, state=good_state)
check("E9 a healthy book is allowed to add",
      "adding is permitted by the guards only for: XLM, SOL, ADA, XRP, HBAR" in out,
      [l for l in out.splitlines() if "permitted" in l])
check("E10 no action is reported when the rules are satisfied",
      "all rules satisfied" in out)

# a drawdown that should stop every add
dd_state = {"equity": [[now - 30 * 86400, 200.0], [now - 3600, 44.0]],
            "last_sold": {}, "closed_trades": []}
out = run_main([], {s: up for s in ("XLM", "SOL", "ADA", "XRP", "HBAR")}, state=dd_state)
check("E11 a 78% drawdown blocks every add",
      "adding is permitted by the guards only for: NONE" in out and "max_drawdown" in out,
      [l for l in out.splitlines() if "drawdown" in l])

# cooldown, recorded through --sold, is honoured on the next run
out = run_main(["--sold", "XLM"], {s: up for s in ("XLM", "SOL", "ADA", "XRP", "HBAR")},
               state=good_state)
check("E12 --sold is recorded", "recorded: sold XLM" in out)
out = run_main([], {s: up for s in ("XLM", "SOL", "ADA", "XRP", "HBAR")}, state=KEEP)
check("E13 the recorded sale blocks re-buying it tomorrow",
      "[BLOCK] XLM" in out and "cooldown" in out,
      [l for l in out.splitlines() if "XLM" in l and "BLOCK" in l])
check("E13b and every OTHER asset is still addable",
      "permitted by the guards only for: SOL, ADA, XRP, HBAR" in out,
      [l for l in out.splitlines() if "permitted" in l])
check("E13c the block names the cooldown, not the portfolio guards",
      any("cooldown" in l for l in out.splitlines() if "[BLOCK] XLM" in l),
      [l for l in out.splitlines() if "[BLOCK] XLM" in l])

# state persists across runs
s2 = daily.load_state()
check("E14 each run appends its equity reading", len(s2["equity"]) >= 2, len(s2["equity"]))

# fail closed when guards.py is not importable
real = daily._guards
daily._guards, daily.GUARDS_ERR = None, "ImportError: simulated"
try:
    out = run_main([], {s: up for s in ("XLM", "SOL", "ADA", "XRP", "HBAR")}, state=good_state)
finally:
    daily._guards = real
check("E15 guards.py missing -> every add BLOCKED, loudly",
      "did NOT load" in out and "permitted by the guards only for: NONE" in out,
      [l for l in out.splitlines() if "did NOT" in l])

# an unpriced asset must never be invented into the total
HOLD = [{"sym": "XLM", "qty": 10.0, "avg": 1.0, "manual": None},
        {"sym": "SOL", "qty": 10.0, "avg": 5.0, "manual": None},
        {"sym": "CASH", "qty": 10.0, "avg": 1.0, "manual": None}]
out = run_main([], {"XLM": (2.0, [1.0] * 200, None), "SOL": (None, None, "fetch failed: URLError")})
check("E16 an unpriced holding is excluded and the reason is printed",
      "NO PRICE" in out and "fetch failed" in out and "HELD BUT NOT PRICED" in out,
      [l for l in out.splitlines() if "NO PRICE" in l])
check("E17 the total is 30.00 (10x2 + 10 cash), not inflated by a guessed SOL price",
      "TOTAL" in out and "30.00" in out,
      [l for l in out.splitlines() if "TOTAL" in l])

# ======================================= X: the second venue and the cross-check
print("\nX  Kraken as an independent read, and what happens when they disagree")


def with_kraken(payload):
    class _R:
        def read(self):
            return json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    real = daily.urllib.request.urlopen
    daily.urllib.request.urlopen = lambda *a, **k: _R()
    try:
        return daily.fetch_kraken("XLM")
    finally:
        daily.urllib.request.urlopen = real


def krows(n=210, start=None, close=1.0, step=DAY):
    """Kraken OHLC rows: [time, open, high, low, close, vwap, volume, count].
    Note close is index 4 and LOW is index 3 -- the layout differs from
    Coinbase's [time, low, high, open, close, volume] everywhere except the
    index of close, which is a coincidence, not a shared convention."""
    start = NOW - DAY if start is None else start
    return [[start - i * step, str(close), str(close), str(close), str(close),
             str(close), "1.0", 1] for i in range(n)]


px, closes, why = with_kraken({"error": [], "result": {"XXLMZUSD": krows(close=3.0),
                                                       "last": NOW}})
check("X1 a clean Kraken window is accepted", px == 3.0 and why is None, (px, why))
check("X1b and yields 200 settled closes", closes is not None and len(closes) == 200,
      None if closes is None else len(closes))

px, _, why = with_kraken({"error": ["EGeneral:Invalid arguments"], "result": {}})
check("X2 a Kraken error array is refused, not parsed",
      px is None and "kraken error" in (why or ""), why)

px, _, why = with_kraken({"error": [], "result": {"XXLMZUSD": krows(start=NOW - 70 * DAY),
                                                  "last": NOW}})
check("X3 the SAME staleness check applies to Kraken",
      px is None and "read is broken" in (why or ""), why)

px, _, why = with_kraken({"error": [], "result": {"last": NOW}})
check("X3b an empty Kraken result is refused", px is None and "no series" in (why or ""), why)


def with_venues(cb, kr, source="both"):
    """Stub the two venue readers directly and run the dispatcher."""
    rc, rk = daily.fetch_coinbase, daily.fetch_kraken
    daily.fetch_coinbase = lambda s: cb
    daily.fetch_kraken = lambda s: kr
    daily.XVENUE_NOTES.clear()
    daily.XVENUE_MAXDIV.clear()
    try:
        return daily.fetch("XLM", source=source)
    finally:
        daily.fetch_coinbase, daily.fetch_kraken = rc, rk


agree_cb = (2.0, [1.000, 0.9, 0.8], None)
agree_kr = (2.01, [1.003, 0.9, 0.8], None)          # 0.30% apart, the worst seen live
px, closes, why = with_venues(agree_cb, agree_kr)
check("X4 venues that agree -> the COINBASE read is the one used",
      px == 2.0 and closes[0] == 1.000 and why is None, (px, why))
check("X4b and the agreement is recorded, not assumed",
      len(daily.XVENUE_MAXDIV) == 1 and abs(daily.XVENUE_MAXDIV[0][1] - 0.003) < 1e-9,
      daily.XVENUE_MAXDIV)

px, _, why = with_venues(agree_cb, (2.1, [1.05, 0.9, 0.8], None))     # 5% apart
check("X5 a 5% disagreement REFUSES the symbol rather than picking one",
      px is None and "venues disagree" in (why or ""), why)
check("X5b and the refusal quotes both numbers and the tolerance",
      "Coinbase 1" in (why or "") and "Kraken 1.05" in (why or "")
      and "1.00%" in (why or ""), why)

px, _, why = with_venues((None, None, "fetch failed: URLError"), agree_kr)
check("X6 Coinbase down -> priced on Kraken alone, not dropped",
      px == 2.01 and why is None, (px, why))
check("X6b and the single-venue read is called out",
      any("Kraken alone" in n for n in daily.XVENUE_NOTES), daily.XVENUE_NOTES)

px, _, why = with_venues(agree_cb, (None, None, None))               # not listed on Kraken
check("X7 no Kraken listing -> still priced, cross-check skipped", px == 2.0 and why is None,
      (px, why))
check("X7b and the MISSING check is reported, so it cannot be mistaken for a passed one",
      any("no Kraken cross-check" in n for n in daily.XVENUE_NOTES), daily.XVENUE_NOTES)

px, _, why = with_venues((None, None, "cb down"), (None, None, "kr down"))
check("X8 both venues down -> refused with a reason", px is None and why, why)

px, _, why = with_venues((9.0, [9.0], None), (1.0, [1.0], None), source="kraken")
check("X9 --source kraken uses Kraken alone and does NOT cross-check",
      px == 1.0 and why is None and not daily.XVENUE_MAXDIV, (px, why))
px, _, why = with_venues((9.0, [9.0], None), (1.0, [1.0], None), source="coinbase")
check("X9b --source coinbase likewise", px == 9.0 and not daily.XVENUE_MAXDIV, (px, why))

passed = sum(1 for _, ok in results if ok)
print(f"\n  {passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
