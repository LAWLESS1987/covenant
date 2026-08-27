"""d2_rebalance_deep.py -- D2: re-test the REBALANCING claim on the deep data.

WHY THIS ITEM EXISTS
  Section 0 of IMPROVEMENT_LOG.md carries one number computed on the 220-bar
  series: "Rebalancing: +0.45% mean OOS at p=0.109, not significant." Every
  other Section-0 figure has now been re-tested on 598-bar data; this is the
  last one whose power was inadequate. Section 0 is IMMUTABLE: whatever this
  script finds is reported in the run log for a human to read. It is not
  edited into Section 0 by any run, in either direction.

WHAT IS TESTED
  Periodic rebalancing back to a fixed target weight vector, against letting
  the same starting weights DRIFT (no trades after day one). Both worlds pay
  the same entry cost, so the spread is purely the cost and effect of the
  rebalancing trades.

TIMING AND COSTS (the engine's convention, so the two D2 halves agree)
  The decision is taken at the close of bar t and filled at the OPEN of bar
  t+1; returns between rebalances are open-to-open. Each rebalance trades
  sum|w_i - target_i| of notional and pays HALF the CostModel round trip on
  every unit traded (a sell and its matching buy are each one side).

THE FOUR FRAMINGS, because one number would hide the disagreement
  1. FULL SAMPLE   -- log-growth spread, net, per schedule.
  2. WALK-FORWARD  -- K non-overlapping folds; mean OOS spread and a sign
                      test. This is the framing the +0.45% / p=0.109 figure
                      came from, so it is the comparable one.
  3. BLOCK BOOTSTRAP -- stationary block bootstrap (mean block 10 d) over the
                      TIME index, resampling whole cross-sections so that
                      cross-asset correlation survives and only the time
                      structure is destroyed. NOTE the direction of this
                      test: under i.i.d. returns the rebalancing bonus is
                      POSITIVE BY CONSTRUCTION (it is the diversification
                      return, half the gap between mean asset variance and
                      portfolio variance). So a HIGH p here does NOT mean
                      "no bonus" -- it means the observed bonus is only the
                      mechanical one, with no extra help from the actual path.
                      A LOW p would mean this window mean-reverted more than
                      chance. Read it that way, not as a significance star.
  4. COST BREAKEVEN -- the round-trip cost at which the spread reaches zero.

  Plus the tension nobody has measured: L's rule 4 is NEVER AVERAGE DOWN, and
  rebalancing a falling portfolio is *definitionally* averaging down. The
  script counts how much of the turnover buys assets that have fallen since
  the last rebalance.

Section 0: no claim of profit edge is made here. Whatever the numbers say is
reported as it is, including against this loop's earlier conclusions.
"""
import datetime as dt
import math, os, random, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_backtest as cb

DEEP = os.path.join(HERE, "realdata", "deep")
FILE = {"WLFI": "WLFI_2025Sep_2026Aug.csv", "HBAR": "HBAR_2025Jul_2026Aug.csv"}
N_BOOT = 2000
SEED = 20260822

# Held per VERIFIED_BASELINE_2026-08-19 (CC has no series -- not tradable on
# Coinbase, so it cannot be in any panel).
HELD_LONG  = ["XLM", "SOL", "XRP", "ADA", "ONDO", "PEPE"]              # 598 bars
HELD_ALL   = HELD_LONG + ["CRO", "HBAR", "WLFI"]                        # 355 bars
WATCHLIST  = HELD_LONG + ["ATOM", "AVAX", "NEAR"]                       # 598 bars


def load_panel(symbols):
    """Aligned open prices on the intersection of all symbols' timestamps."""
    opens = {}
    for s in symbols:
        fn = FILE.get(s, f"{s}_2025_2026Aug.csv")
        opens[s] = {b.ts: b.open for b in cb.load_csv(os.path.join(DEEP, fn))}
    ts = sorted(set.intersection(*(set(v) for v in opens.values())))
    return ts, [[opens[s][t] for s in symbols] for t in ts]


def returns(prices):
    """Open-to-open simple returns, one row per step, one column per asset."""
    return [[prices[i + 1][j] / prices[i][j] - 1.0 for j in range(len(prices[0]))]
            for i in range(len(prices) - 1)]


def simulate(rets, target, schedule, cost_side, count_avg_down=False):
    """Log-growth of the rebalanced book. schedule: set of step indexes at whose
    OPEN the book is reset to `target`. Returns (log_growth, turnover, n_rb,
    equity_curve, avg_down_fraction)."""
    w = list(target)
    g, turn, n_rb, curve = 0.0, 0.0, 0, [1.0]
    down_bought = bought = 0.0
    since = [1.0] * len(target)          # cumulative price factor since last rebalance
    for i, r in enumerate(rets):
        if i in schedule and i > 0:
            traded = sum(abs(a - b) for a, b in zip(w, target))
            if traded:
                if count_avg_down:
                    for j in range(len(w)):
                        d = target[j] - w[j]
                        if d > 0:                    # buying asset j
                            bought += d
                            if since[j] < 1.0:       # ... and it has fallen
                                down_bought += d
                g += math.log1p(-traded * cost_side)
                turn += traded
                n_rb += 1
            w = list(target)
            since = [1.0] * len(target)
        step = sum(wi * (1.0 + ri) for wi, ri in zip(w, r))
        if step <= 0:
            raise ValueError("portfolio wiped out")
        g += math.log(step)
        curve.append(curve[-1] * step)
        w = [wi * (1.0 + ri) / step for wi, ri in zip(w, r)]
        since = [s * (1.0 + ri) for s, ri in zip(since, r)]
    return g, turn, n_rb, curve, (down_bought / bought if bought else 0.0)


def max_dd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst


def sched(n, every):
    return set(range(every, n, every)) if every else set()


def spread(rets, target, schedule, cost_side):
    reb = simulate(rets, target, schedule, cost_side)[0]
    drift = simulate(rets, target, set(), cost_side)[0]
    return reb - drift


def block_bootstrap_idx(n, rng, mean_block=10):
    out, i = [], rng.randrange(n)
    while len(out) < n:
        if rng.random() < 1.0 / mean_block:
            i = rng.randrange(n)
        out.append(i % n)
        i += 1
    return out


def walk_forward(rets, target, every, cost_side, folds=6):
    """Non-overlapping consecutive folds; the spread measured inside each."""
    n, k = len(rets), len(rets) // 6
    out = []
    for f in range(folds):
        seg = rets[f * k:(f + 1) * k]
        if len(seg) < every * 2:
            continue
        out.append(spread(seg, target, sched(len(seg), every), cost_side))
    return out


def binom_p(hits, n):
    """One-sided binomial P(X >= hits) at p=0.5 -- 'more folds positive than chance'."""
    return sum(math.comb(n, i) for i in range(hits, n + 1)) / 2 ** n


def run_panel(name, symbols, schedules, cost_rt_bps=None):
    rng = random.Random(SEED)
    ts, prices = load_panel(symbols)
    rets = returns(prices)
    cm = cb.CostModel()
    rt = cost_rt_bps if cost_rt_bps is not None else cm.round_trip_bps()
    cs = (rt / 10_000.0) / 2.0
    target = [1.0 / len(symbols)] * len(symbols)
    print(f"\n=== {name}: {len(symbols)} assets, {len(rets)} steps "
          f"({dt.datetime.fromtimestamp(ts[0], dt.UTC).date()} -> "
          f"{dt.datetime.fromtimestamp(ts[-1], dt.UTC).date()}), "
          f"equal weight, round trip {rt:.0f} bps")
    drift_g, _, _, drift_curve, _ = simulate(rets, target, set(), cs)
    print(f"    drift (no rebalance): log-growth {drift_g:+.4f} = {math.expm1(drift_g):+.2%}, "
          f"maxDD {max_dd(drift_curve):+.1%}")
    rows = []
    for label, every in schedules:
        sc = sched(len(rets), every)
        g, turn, n_rb, curve, adown = simulate(rets, target, sc, cs, count_avg_down=True)
        obs = g - drift_g
        boots = []
        for _ in range(N_BOOT):
            idx = block_bootstrap_idx(len(rets), rng)
            rs = [rets[i] for i in idx]
            boots.append(spread(rs, target, sc, cs))
        p = sum(1 for b in boots if b >= obs) / N_BOOT
        wf = walk_forward(rets, target, every, cs)
        pos = sum(1 for x in wf if x > 0)
        wf_mean = statistics.fmean(wf) if wf else float("nan")
        wf_p = binom_p(pos, len(wf)) if wf else float("nan")
        # cost at which the spread crosses zero
        lo, hi = 0.0, 2000.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if spread(rets, target, sc, (mid / 10_000.0) / 2) > 0:
                lo = mid
            else:
                hi = mid
        print(f"    {label:<12} rebalances {n_rb:>3}  turnover {turn:>5.2f}x  "
              f"spread {math.expm1(obs):+7.2%}  boot p={p:.3f}  "
              f"WF mean {math.expm1(wf_mean):+6.2%} {pos}/{len(wf)} folds+ (p={wf_p:.3f})  "
              f"maxDD {max_dd(curve):+.1%}  breakeven {lo:.0f}bps  "
              f"avg-down {adown:.0%} of buys")
        rows.append((name, label, obs, p, wf_mean, pos, len(wf), wf_p, lo, adown,
                     max_dd(curve), max_dd(drift_curve)))
    return rows


SCHEDULES = [("daily", 1), ("weekly", 7), ("monthly", 21), ("quarterly", 63)]

if __name__ == "__main__":
    all_rows = []
    all_rows += run_panel("HELD-6 (598 bars)", HELD_LONG, SCHEDULES)
    all_rows += run_panel("HELD-9 (355 bars)", HELD_ALL, SCHEDULES)
    all_rows += run_panel("WATCHLIST-9 (598 bars)", WATCHLIST, SCHEDULES)
    print("\n=== zero-cost control (is any spread just the cost model?) ===")
    run_panel("HELD-6 zero cost", HELD_LONG, SCHEDULES, cost_rt_bps=0.0)
    print("\n=== summary: monthly schedule, the one the policy implies ===")
    for r in all_rows:
        if r[1] == "monthly":
            print(f"    {r[0]:<24} spread {math.expm1(r[2]):+7.2%}  boot p={r[3]:.3f}  "
                  f"WF {math.expm1(r[4]):+6.2%} {r[5]}/{r[6]} (p={r[7]:.3f})  "
                  f"breakeven {r[8]:.0f}bps")


# ---------------------------------------------------------------------------
# The finding this script exists for (added after the first run)
# ---------------------------------------------------------------------------
def fold_resolution_probe():
    """Section 0's p=0.109 is not a measurement of the data. It is exactly
    binom_p(5, 6) = 7/64 -- 'five of six folds positive'. With six folds the
    p-value can only ever take seven values, and 5/6 is the second-best of
    them. So the 220-bar conclusion was never SAMPLE-limited; it was
    FOLD-limited, and adding bars cannot move it. Adding folds can."""
    print("\n=== fold resolution: the p-value the 6-fold test can even produce ===")
    for k in (6, 8, 12, 16):
        vals = [f"{i}/{k}:{binom_p(i, k):.3f}" for i in range(k, max(k - 4, -1), -1)]
        print(f"    {k:>2} folds -> best p {binom_p(k, k):.4f}   " + "  ".join(vals))


def deep_walk_forward(name, symbols, every=21, folds=12, seed=SEED):
    ts, prices = load_panel(symbols)
    rets = returns(prices)
    cs = (cb.CostModel().round_trip_bps() / 10_000.0) / 2.0
    target = [1.0 / len(symbols)] * len(symbols)
    k = len(rets) // folds
    xs = []
    for f in range(folds):
        seg = rets[f * k:(f + 1) * k]
        if len(seg) < every * 2:
            continue
        xs.append(spread(seg, target, sched(len(seg), every), cs))
    pos = sum(1 for x in xs if x > 0)
    m = statistics.fmean(xs)
    sd = statistics.pstdev(xs)
    t = m / (sd / math.sqrt(len(xs))) if sd else float("inf")
    print(f"    {name:<24} {folds:>2} folds of {k:>3} bars: mean {math.expm1(m):+6.2%}  "
          f"{pos}/{len(xs)} positive  binom p={binom_p(pos, len(xs)):.4f}  t={t:+.2f}")
    return xs


def threshold_schedule(rets, target, band):
    """L's policy is a BAND (trim at the 20% cap), not a calendar. Rebalance
    only when some weight has drifted more than `band` from target."""
    w, out = list(target), set()
    for i, r in enumerate(rets):
        if i and max(abs(a - b) for a, b in zip(w, target)) > band:
            out.add(i); w = list(target)
        step = sum(wi * (1 + ri) for wi, ri in zip(w, r))
        w = [wi * (1 + ri) / step for wi, ri in zip(w, r)]
    return out


def run_bands(name, symbols, bands=(0.02, 0.05, 0.10)):
    ts, prices = load_panel(symbols)
    rets = returns(prices)
    cs = (cb.CostModel().round_trip_bps() / 10_000.0) / 2.0
    target = [1.0 / len(symbols)] * len(symbols)
    drift_g = simulate(rets, target, set(), cs)[0]
    print(f"\n=== {name}: band-triggered rebalancing (the shape the policy uses) ===")
    for b in bands:
        sc = threshold_schedule(rets, target, b)
        g, turn, n_rb, curve, adown = simulate(rets, target, sc, cs, count_avg_down=True)
        print(f"    band {b:.0%}  rebalances {n_rb:>3}  turnover {turn:>5.2f}x  "
              f"spread {math.expm1(g - drift_g):+7.2%}  maxDD {max_dd(curve):+.1%}  "
              f"avg-down {adown:.0%} of buys")
