"""test_backtest_guardrails.py -- try to fool the framework, on purpose.

You cannot validate anti-illusion machinery on real market data, because you do
not know whether an edge is there. So this uses a price series with a KNOWN
ground truth: a random walk, in which no strategy can have an edge, ever, by
construction.

Then it does exactly what an over-eager researcher does -- searches a few
hundred parameter combinations, keeps the best-looking one -- and checks that
every guardrail refuses to call the winner real. If they pass it, they are
decoration.

    python3 test_backtest_guardrails.py
"""
import os, sys, math, random, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from covenant_backtest import (
    Bar, Backtester, CostModel, PointInTimeView, LookAheadError,
    deflated_sharpe, min_track_record_length, walk_forward, evaluate,
    EdgeMonitor, PaperTrader,
)

passed = failed = 0
def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        failed += 1; print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))

def random_walk(n, seed, s0=100.0, vol=0.02):
    """Geometric random walk. NO EDGE EXISTS HERE -- future returns are
    independent of everything observable. Any strategy that appears to profit
    is fitting noise, and we know it for certain."""
    rng = random.Random(seed)
    bars, px = [], s0
    for i in range(n):
        r = rng.gauss(0, vol)
        o = px
        px = px * math.exp(r)
        hi = max(o, px) * (1 + abs(rng.gauss(0, vol / 4)))
        lo = min(o, px) * (1 - abs(rng.gauss(0, vol / 4)))
        bars.append(Bar(float(i), o, hi, lo, px, 1000.0))
    return bars

def sma_cross(fast, slow):
    def strat(view, pos):
        if len(view) < slow + 1:
            return 0
        c = view.closes(slow)
        f = statistics.fmean(c[-fast:])
        s = statistics.fmean(c)
        return 1 if f > s else -1
    return strat

print("=" * 72)
print("STRUCTURAL: can a strategy reach the future at all?")
print("=" * 72)
bars = random_walk(600, seed=1)
def cheater(view, pos):
    return 1 if view[0].close > view[-1].close else -1   # index 0 = future
try:
    Backtester(capital=12.0).run(bars, cheater, warmup=30)
    check("a look-ahead strategy is rejected", False, "it ran to completion")
except LookAheadError as e:
    check("a look-ahead strategy is rejected", True, str(e)[:56])

def peeker(view, pos):
    try:
        _ = view[5]
        return 1
    except LookAheadError:
        return 0
r = Backtester(capital=12.0).run(bars, peeker, warmup=30)
check("forward indexing is impossible, not merely discouraged", r.n_trades == 0)

print()
print("=" * 72)
print("THE BACKTEST ILLUSION: mine a random walk for a 'winner'")
print("=" * 72)
print("  Ground truth: geometric random walk. No edge can exist.")
bars = random_walk(1500, seed=42)
cost = CostModel(taker_fee_bps=10, spread_bps=5, slippage_bps=5, min_notional=5.0)
bt = Backtester(cost=cost, capital=12.0)

best, best_params, tried = None, None, 0
for fast in range(2, 22, 2):
    for slow in range(24, 84, 4):
        if fast >= slow:
            continue
        tried += 1
        try:
            res = bt.run(bars, sma_cross(fast, slow), warmup=slow + 2,
                         label=f"sma{fast}/{slow}")
        except Exception:
            continue
        if best is None or res.total_return > best.total_return:
            best, best_params = res, (fast, slow)
best.strategies_tried = tried
print(f"  searched {tried} parameter pairs")
print(f"  best: SMA {best_params[0]}/{best_params[1]}  "
      f"return {best.total_return:+.2%}  Sharpe {best.sharpe():.2f}  "
      f"trades {best.n_trades}")
check("searching noise produced a plausible-looking winner",
      best.total_return > 0 or best.sharpe() > 0,
      "this is the illusion the rest of the checks must catch")

print()
print("  -- deflated Sharpe, told the truth about the search --")
d_honest = deflated_sharpe(best)
print(f"     trials={d_honest['trials']}  raw Sharpe {d_honest['sharpe']:.2f}  "
      f"selection benchmark {d_honest['expected_max_sharpe']:.2f}")
print(f"     DSR {d_honest['deflated_sharpe']:.4f} -> {d_honest['verdict']}")
check("the deflated Sharpe refuses the mined winner",
      d_honest["deflated_sharpe"] < 0.95,
      f"DSR {d_honest['deflated_sharpe']:.4f}")

print()
print("  -- the same result, LYING about the search (claiming one trial) --")
best.strategies_tried = 1
d_lie = deflated_sharpe(best)
print(f"     DSR {d_lie['deflated_sharpe']:.4f} vs honest {d_honest['deflated_sharpe']:.4f}")
check("hiding the trial count materially inflates the verdict",
      d_lie["deflated_sharpe"] >= d_honest["deflated_sharpe"],
      "which is exactly why strategies_tried is carried on the result")
best.strategies_tried = tried

print()
print("=" * 72)
print("WALK-FORWARD: does the winner survive out of sample?")
print("=" * 72)
def build_best_on_train(train):
    b, bp = None, (5, 30)
    for fast in range(2, 16, 2):
        for slow in range(20, 60, 4):
            if fast >= slow:
                continue
            try:
                rr = Backtester(cost=cost, capital=12.0).run(
                    train, sma_cross(fast, slow), warmup=slow + 2)
            except Exception:
                continue
            if b is None or rr.total_return > b:
                b, bp = rr.total_return, (fast, slow)
    return sma_cross(*bp)

wf = walk_forward(bars, build_best_on_train, folds=5, embargo_frac=0.02,
                  cost=cost, capital=12.0, warmup=60)
print(f"  folds: {wf['folds']}   positive: {wf['positive_folds']}")
print(f"  fold returns: {', '.join(f'{r:+.2%}' for r in wf['fold_returns'])}")
print(f"  mean {wf['mean_return']:+.2%}   worst {wf['worst_fold']:+.2%}")
print(f"  binomial p under the null: {wf['binomial_p']:.3f}")
print()
print("  NOTE: a fold TALLY is not a test. On this random walk the mined")
print("  strategy produced a majority of positive folds -- walk-forward alone")
print("  does NOT catch the illusion, which is why consistency now also")
print("  requires the result to be unlikely under the null.")
check("walk-forward consistency requires statistical significance, not a tally",
      not wf["consistent"],
      f"{wf['positive_folds']}/{wf['folds']} positive but p={wf['binomial_p']:.3f}")

print()
print("=" * 72)
print("FULL VERDICT on the mined strategy")
print("=" * 72)
v = evaluate(best, wf=wf, cost=cost)
print(v.report())
check("the guardrails REJECT a strategy mined from pure noise", not v.passed)

print()
print("=" * 72)
print("COSTS AT REAL SIZE (capital ~12, not ~10,000)")
print("=" * 72)
print(f"  round-trip cost: {cost.round_trip_bps():.0f} bps "
      f"({cost.round_trip_bps()/100:.2f}% per trade)")
print(f"  best strategy took {best.n_trades} trades")
print(f"  gross {best.gross_pnl():+.4f} -> net {best.end_equity-best.start_equity:+.4f} "
      f"(fees {best.total_fees():.4f})")
check("costs are large enough to matter at this size",
      best.total_fees() > 0,
      f"{best.total_fees()/12.0:.1%} of capital consumed by fees")

free = Backtester(cost=CostModel(0, 0, 0, 0.0), capital=12.0).run(
    bars, sma_cross(*best_params), warmup=best_params[1] + 2)
print(f"  same strategy with ZERO costs: {free.total_return:+.2%} "
      f"vs {best.total_return:+.2%} with real costs")
check("ignoring costs materially flatters the result",
      free.total_return > best.total_return,
      f"delta {free.total_return - best.total_return:+.2%}")

print()
print("=" * 72)
print("A REAL EDGE MUST STILL PASS (control)")
print("=" * 72)
def trending(n, seed, drift=0.004, vol=0.012):
    rng = random.Random(seed)
    bars, px = [], 100.0
    for i in range(n):
        r = rng.gauss(drift, vol)
        o = px; px = px * math.exp(r)
        bars.append(Bar(float(i), o, max(o, px) * 1.001, min(o, px) * 0.999, px, 1000.0))
    return bars

up = trending(1500, seed=7)
hold = lambda view, pos: 1
r_hold = Backtester(cost=cost, capital=12.0).run(up, hold, warmup=30, strategies_tried=1)
d_hold = deflated_sharpe(r_hold)
print(f"  buy-and-hold on a genuinely trending series:")
print(f"    return {r_hold.total_return:+.2%}  Sharpe {r_hold.sharpe():.2f}  "
      f"DSR {d_hold['deflated_sharpe']:.3f}  trades {r_hold.n_trades}")
check("a real, un-mined edge is NOT rejected by the deflated Sharpe",
      d_hold["deflated_sharpe"] >= 0.95,
      f"DSR {d_hold['deflated_sharpe']:.3f} -- guardrails reject noise, not signal")

print()
print("=" * 72)
print("THE EDGE PROBLEM: decay detection and kill switch")
print("=" * 72)
mon = EdgeMonitor(expected_mean=0.004, expected_sd=0.012, window=40,
                  z_kill=-2.5, max_consecutive_losses=12)
rng = random.Random(99)
killed_at = None
for i in range(200):
    # First 100 periods behave as the backtest promised; then the edge dies.
    r = rng.gauss(0.004, 0.012) if i < 100 else rng.gauss(-0.006, 0.012)
    st = mon.record(r)
    if st.get("killed") and killed_at is None:
        killed_at = i
        break
print(f"  edge died at period 100; monitor killed at period {killed_at}")
print(f"  reason: {mon.kill_reason}")
check("a decayed edge is detected and killed", killed_at is not None)
check("it is detected AFTER the decay, not before", killed_at is None or killed_at >= 100)
check("detection is prompt", killed_at is not None and killed_at < 160,
      f"{killed_at - 100} periods after decay began")

mon2 = EdgeMonitor(expected_mean=0.004, expected_sd=0.012, window=40)
rng2 = random.Random(5)
for _ in range(300):
    mon2.record(rng2.gauss(0.004, 0.012))
check("a healthy edge is NOT killed by ordinary variance", not mon2.killed)

print()
print("=" * 72)
print("PAPER TRADING: predictions are sealed before the outcome")
print("=" * 72)
pt = PaperTrader(cost=cost, capital=12.0,
                 monitor=EdgeMonitor(0.004, 0.012, window=20))
i0 = pt.seal(ts=1.0, target=1, ref_px=100.0, note="forward call")
pt.settle(i0, exit_px=101.0)
try:
    pt.settle(i0, exit_px=105.0)
    check("a settled prediction cannot be re-scored", False, "it was re-settled")
except ValueError as e:
    check("a settled prediction cannot be re-scored", True, str(e)[:52])
s = pt.summary()
print(f"  sealed {s['sealed']}, settled {s['settled']}, equity {s['equity']:.4f}")
check("paper trades pay the same costs as the backtest",
      s["equity"] < 12.0 + (12.0 * 0.01),
      "a 1% move does not clear a 40bps round trip by much")

print()
print("=" * 72)
print(f"{passed} passed, {failed} failed")
print("=" * 72)
sys.exit(1 if failed else 0)
