#!/usr/bin/env python3
"""
test_rule5_ledger.py -- Rule 5 has a writer now; pin what it writes.

Found 2026-09-06: covenant_trader.py read `sealed_signals`, initialised it to
0, and nothing ever incremented it. The gate could not clear on evidence.
These tests pin the scorer that fixes that, and the two things the gate must
keep doing: block on count, and block on a record that is only luck.

Run:  python test_rule5_ledger.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import signal_ledger as L          # noqa: E402

FAILS = []


def check(cond, label):
    print(("ok    " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


def pos(sym, px, regime):
    return {"sym": sym, "px": px, "regime": regime, "s200": px}


def fresh():
    d = tempfile.mkdtemp()
    return os.path.join(d, "ledger.jsonl")


# --- L1: a first sighting opens a call, settles nothing -----------------------
p = fresh()
s = L.record_cycle([pos("XLM", 1.0, "UP"), pos("LINK", 10.0, "DOWN")], now=1000, path=p)
check(s["open"] == 2 and s["settled"] == 0, "L1 first sighting opens one call per asset, settles none")
check(not s["clears"] and "need 30" in s["why"], "L1 ...and the verdict says why it does not clear")

# --- L7: one read per local day, and the guard arms on a FLAT day too --------
s = L.record_cycle([pos("XLM", 1.50, "DOWN")], now=1000 + 3600, path=p)
check(s["open"] == 2 and s["settled"] == 0,
      "L7 a re-run an hour later on the same day settles nothing: one read per daily bar")
p7 = fresh()
D = 86400
L.record_cycle([pos("ADA", 1.0, "UP")], now=100_000, path=p7)                 # day 1: opens
L.record_cycle([pos("ADA", 1.01, "UP")], now=100_000 + D, path=p7)            # day 2, first run: flat, changes nothing
s = L.record_cycle([pos("ADA", 0.90, "DOWN")], now=100_000 + D + 3600, path=p7)  # day 2, re-run an hour later: a flip
check(s["settled"] == 0,
      "L7 a flat first read still claims the day: a same-day re-run cannot settle a flip (the audit's case)")
s = L.record_cycle([pos("ADA", 0.90, "DOWN")], now=100_000 + 2 * D, path=p7)  # day 3: the flip counts
check(s["settled"] == 1, "L7 ...and the next day's read settles it")

# --- L2: an unchanged regime is the same call, not a new signal per day ------
for day in range(1, 20):
    s = L.record_cycle([pos("XLM", 1.0 + day * 0.01, "UP")], now=1000 + day * 86400, path=p)
check(s["open"] == 2 and s["settled"] == 0,
      "L2 nineteen daily re-reads of the same regime add zero signals (one call, not one per day)")

# --- L3: a flip settles the call at the flip price, minus costs ---------------
s = L.record_cycle([pos("XLM", 1.20, "DOWN")], now=1000 + 30 * 86400, path=p, cost_bps=100)
rows = [json.loads(l) for l in open(p)]
settled = [r for r in rows if r["kind"] == "settled"]
check(s["settled"] == 1 and len(settled) == 1, "L3 a regime flip settles exactly one signal")
r = settled[0]
check(r["sym"] == "XLM" and r["side"] == 1 and abs(r["ret_gross"] - 0.20) < 1e-9,
      "L3 an UP call settled 20% higher scores +20% gross")
check(abs(r["ret_after_costs"] - 0.19) < 1e-9, "L3 ...and 100 bps round trip comes off it")
check(r["held_days"] == 30.0 and r["sealed_at"] == 1000, "L3 the row keeps the seal time: the call preceded the outcome")
opens = L._open_calls(rows)
check(opens["XLM"]["regime"] == "DOWN" and opens["XLM"]["entry"] == 1.20,
      "L3 the flip opens the next call in the new regime at the flip price")

# --- L4: a DOWN call is scored as a short: it wins if the asset fell ----------
p = fresh()
L.record_cycle([pos("ADA", 2.0, "DOWN")], now=0, path=p)
s = L.record_cycle([pos("ADA", 1.0, "UP")], now=86400, path=p, cost_bps=0)
r = [json.loads(l) for l in open(p) if '"settled"' in l][0]
check(r["side"] == -1 and abs(r["ret_gross"] - 0.5) < 1e-9,
      "L4 a DOWN call that preceded a 50% fall scores +50%: 'do not add' was right")

# --- L5: regimes that are n/a (too few bars) are not calls --------------------
p = fresh()
s = L.record_cycle([pos("NEW", 5.0, "n/a")], now=0, path=p)
check(s["open"] == 0, "L5 an asset with no 200d line opens no call")

# --- L6: the verdict -- count is necessary, not sufficient --------------------
def ledger_with(rets, path):
    for i, ret in enumerate(rets):
        sym = f"S{i}"
        now = i * 2 * 86400            # each call on its own days: one read per day is the rule
        L.record_cycle([pos(sym, 1.0, "UP")], now=now, path=path, cost_bps=0)
        L.record_cycle([pos(sym, 1.0 + ret, "DOWN")], now=now + 86400, path=path, cost_bps=0)
    return L.summary(path)

s = ledger_with([0.01] * 29, fresh())
check(s["settled"] == 29 and not s["clears"] and "need 30" in s["why"],
      "L6 29 winning signals do not clear: the count is the floor")

s = ledger_with([0.01] * 30, fresh())
check(s["settled"] == 30 and s["clears"] and s["p_value"] < 1e-6,
      "L6 30/30 wins clears (p ~ 1e-9)")

s = ledger_with([0.02] * 15 + [-0.01] * 15, fresh())
check(s["settled"] == 30 and not s["clears"] and "luck" in s["why"] and s["p_value"] > 0.05,
      "L6 15/30 wins with a small positive mean does NOT clear: a coin flip is not evidence")

s = ledger_with([0.05] * 17 + [-0.10] * 13, fresh())
check(not s["clears"] and "loses" in s["why"],
      "L6 17/30 wins but a negative mean does NOT clear: on real money it loses")

s = ledger_with([0.02] * 21 + [-0.01] * 9, fresh())
check(s["clears"] and s["p_value"] <= 0.05,
      "L6 21/30 wins, positive mean, p=0.021 clears -- the same bar signal_watch.py sets")

# --- T: the trader applies both halves of the gate ---------------------------
import covenant_trader as T          # noqa: E402
cfg = dict(T.DEFAULT_CONFIG)
cfg.update({"armed": True, "seal_required": False, "rule5_require_significance": True, "daily_plan_required": False})   # Rule 5, not the plan gate (A106)
order = {"sym": "XLM", "side": "sell", "qty": 1, "usd": 10, "rule": "R1"}
pf = {"total": 1000, "cash": 500, "positions": []}

st = {"sealed_signals": 0, "orders_today": []}
bad = T.preconditions(cfg, st, pf, order, sealed_ok=True, guard_blocks=[])
check(any(b.startswith("Rule 5") and "need 30" in b for b in bad),
      "T1 0 settled -> preconditions() names Rule 5 with the count")

st = {"sealed_signals": 30, "orders_today": [], "rule5": {"clears": False, "why": "30 settled signals, 15 wins, p=0.572 > 0.05 -- not distinguishable from luck"}}
bad = T.preconditions(cfg, st, pf, order, sealed_ok=True, guard_blocks=[])
check(any(b.startswith("Rule 5") and "luck" in b for b in bad),
      "T2 30 settled but a luck-shaped record -> still blocked, and it says so")

st = {"sealed_signals": 30, "orders_today": [], "rule5": {"clears": True, "why": "survives"}}
bad = T.preconditions(cfg, st, pf, order, sealed_ok=True, guard_blocks=[])
check(not any(b.startswith("Rule 5") for b in bad),
      "T3 30 settled AND the record clears -> Rule 5 no longer blocks (other gates still apply)")

cfg2 = dict(cfg); cfg2["rule5_require_significance"] = False
st = {"sealed_signals": 30, "orders_today": [], "rule5": {"clears": False, "why": "luck"}}
bad = T.preconditions(cfg2, st, pf, order, sealed_ok=True, guard_blocks=[])
check(not any(b.startswith("Rule 5") for b in bad),
      "T4 with rule5_require_significance=false the old count-only gate is what runs (his call, on purpose)")

# --- E: a live order whose answer is lost is still on the books --------------
class _Stub:
    name = "stub"
    def __init__(self, behaviour): self.b = behaviour
    def has_credentials(self): return True
    def place(self, sym, side, qty, live=False, **kw):
        if isinstance(self.b, Exception):
            raise self.b
        return self.b

_saved = []
T.save_state = lambda st: _saved.append(json.dumps(st, sort_keys=True))
armed = dict(T.DEFAULT_CONFIG)
armed.update({"armed": True, "seal_required": False, "rule5_require_significance": False, "daily_plan_required": False})
def run(stub):
    T.venue_for = lambda o, lv: stub
    T.V.all_venues = lambda: [stub]
    st = {"sealed_signals": 30, "orders_today": [], "rule5": {"clears": True}, "day": "x"}
    res = T.execute(armed, st, [{"sym": "XLM", "side": "sell", "qty": 1, "usd": 10, "rule": "R1"}],
                    sealed_ok=True, guard_blocks=[])
    return res, st

res, st = run(_Stub(TimeoutError("read timed out")))
check(res[0]["status"] == "UNKNOWN" and len(st["orders_today"]) == 1
      and st["orders_today"][0]["status"].startswith("UNKNOWN") and _saved,
      "E1 a live order whose answer is lost stays in orders_today as UNKNOWN, and state was written")
res, st = run(_Stub(T.V.VenueError("HTTP 400: bad size")))
check(res[0]["status"] == "REFUSED" and st["orders_today"] == [],
      "E2 a definite 4xx refusal frees the row: nothing was booked, the caps are not charged")
res, st = run(_Stub({"descr": "ok", "txid": "abc"}))
check(res[0]["status"] == "PLACED" and st["orders_today"][0]["txid"] == "abc"
      and st["orders_today"][0]["status"] == "PLACED",
      "E3 a placed order completes the same row with its txid")
res, st = run(_Stub(T.V.VenueError("no response: TimeoutError: timed out")))
check(res[0]["status"] == "UNKNOWN" and len(st["orders_today"]) == 1,
      "E4 a 'no response' VenueError is unknown, not refused")

src = open(os.path.join(HERE, "covenant_trader.py"), encoding="utf-8").read()
check('st["sealed_signals"] = int(r5.get("settled", 0))' in src,
      "T5 covenant_trader.py writes sealed_signals from the ledger -- the counter has a writer")

# T5 reads the file's BYTES, and the bytes survive things the behaviour does
# not. Measured 2026-09-09: put a '#' in front of that one line and the literal
# is still in the file, so T5 still printed ok while the counter went back to
# having no writer -- which IS the 2026-09-06 defect this whole file exists to
# pin. So run the writer instead of grepping for it. run_once() is driven with
# everything it touches stubbed out (no venues, no nodes, no orders, state and
# the decision snapshot in a temp dir) except the ledger, which is made to
# report a settled count nobody could mistake for a default; then read the
# state that was handed to save_state(). Two different counts, because a
# writer that always writes 7 is not reading the ledger either.
def rule5_state(settled):
    tmp = tempfile.mkdtemp()
    saved = {}
    keep = {k: getattr(T, k) for k in ("STATE", "load_state", "node_status",
                                       "gather", "plan", "execute", "save_state")}
    keep_record_cycle = T.signal_ledger.record_cycle
    try:
        T.STATE = os.path.join(tmp, "trader_state.json")
        T.load_state = lambda: {"orders_today": [], "day": "", "equity_peak": 0.0,
                                "equity_start_of_day": 0.0, "closed_trades": [],
                                "last_sold": {}, "bought_total_usd": 0.0,
                                # -1 is a value no ledger can produce: if it
                                # survives the cycle, nothing wrote the counter.
                                "sealed_signals": -1}
        T.node_status = lambda ports, timeout=4: []
        T.gather = lambda cfg: {"positions": [], "unpriced": [], "venue_notes": [],
                                "total": 0.0, "cash": 0.0}
        T.plan = lambda cfg, pf, week_spent=0.0: ([], ["no orders (stub)"])
        T.execute = lambda *a, **kw: []
        T.save_state = lambda st: saved.update(st)
        T.signal_ledger.record_cycle = lambda positions, **kw: {
            "open": 2, "settled": settled, "wins": settled,
            "mean_after_costs": 0.02, "p_value": 0.001, "clears": False,
            "why": f"{settled} settled signals (stub)"}
        cfg = dict(T.DEFAULT_CONFIG)
        cfg.update({"armed": False, "seal_required": False, "node_ports": []})
        with contextlib.redirect_stdout(io.StringIO()):   # the cycle's own report
            T.run_once(cfg)
    finally:
        for k, v in keep.items():
            setattr(T, k, v)
        T.signal_ledger.record_cycle = keep_record_cycle
    return saved

a, b = rule5_state(7), rule5_state(12)
check(a.get("sealed_signals") == 7 and b.get("sealed_signals") == 12,
      "T5b a cycle actually run writes the ledger's settled count into state "
      "(comment the writer out and this goes red, T5 does not)")
check(a.get("rule5", {}).get("settled") == 7 and a.get("rule5", {}).get("why"),
      "T5b ...and the record beside it carries the same count and the ledger's reason")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("RULE 5 ledger: all passed")
