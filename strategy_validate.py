#!/usr/bin/env python3
"""strategy_validate.py -- does any rule survive walk-forward, deflation and
PBO on the refreshed data, at the costs this account actually pays?

WHY (asked 2026-09-03: "need a real, walk-forward validated strategy that
actually works -- otherwise you're just adding risk for no reason")

  QUANT_README.md already proved the machinery honest on a random walk: a
  150-variant search there produced +144.70% and a Sharpe of 1.10 with an
  edge of exactly zero, and the deflated Sharpe said 0.0000. REAL_DATA_
  FINDINGS.md then ran ~800 variants over 16 assets and found no return edge
  that survived. This re-asks the question on data extended to the last
  settled bar (2026-09-03), at the fee an account this size really pays, and
  it asks the SECOND question too: does the one effect that did replicate --
  trend-following cutting the worst drawdown by about 3x -- still replicate?

WHAT IT DOES
  For each of the twelve verified Kraken daily series in realdata/deep:
    * runs every variant of strategy_lab.build_grid() plus a risk family
      (long-only SMA filter at 50/100/150/200, and volatility targeting at
      20/30/40% annualised) through covenant_backtest.Backtester, which
      executes a signal from bar t at the OPEN of bar t+1 and hands the
      strategy a PointInTimeView that RAISES on any forward index;
    * scores buy-and-hold over the same window as the benchmark;
    * carries strategies_tried as ONE search over every (asset, variant)
      pair, because that is what it was, and deflates the Sharpe by it;
    * walk-forwards the best variant per asset (5 folds, 2% embargo), where
      "consistent" needs a majority of positive folds AND a binomial p<=0.05,
      because a tally is not a test (QUANT_README measured a 4/5-fold winner
      on pure noise);
    * computes PBO by CSCV (the method pbo_hbar.py uses): split the return
      matrix into S contiguous blocks, take every half as in-sample, and
      measure how often the in-sample-best variant lands below median
      out-of-sample. PBO >= 0.5 means the selection procedure is worthless.

WHAT IT REFUSES TO DO
  It never touches an exchange, a key, holdings.txt or trader_config.json.
  It cannot arm anything. It reports what it measured, including the case
  where the honest answer is "nothing survived" -- which is a complete
  answer, not a failure.

USE
  python strategy_validate.py                # all twelve, full report
  python strategy_validate.py --assets XRP HBAR
  python strategy_validate.py --out docs/STRATEGY_VALIDATION.md
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import glob
import itertools
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from covenant_backtest import (Backtester, CostModel, deflated_sharpe,       # noqa: E402
                               load_csv, walk_forward)
import strategy_lab as L                                                     # noqa: E402

DEEP = os.path.join(HERE, "realdata", "deep")

# COSTS. The framework's default is taker_fee_bps=10 (0.10%), which is a
# volume tier this account does not have. Kraken Pro's lowest tier -- under
# $10k of 30-day volume, which is where a small book sits -- is 0.40% taker.
# Spread and slippage are charged adversely in both directions on top. So a
# round trip costs 2 * (40 + 5 + 5) = 100 bps: price must move 1% before a
# trade breaks even. Change these with --fee-bps if the tier changes.
FEE_BPS, SPREAD_BPS, SLIP_BPS = 40.0, 5.0, 5.0
CAPITAL = 25.0            # trader_config.json max_order_usd; the size actually traded
MIN_NOTIONAL = 5.0        # trader_config.json min_order_usd


# ---------------------------------------------------------------- the risk family
def sma_filter(n):
    """Long when the close is above its own n-day average, else flat. The rule
    MY_STRATEGY.md says cut the worst drawdown by ~3x. Long-only: shorting
    doubles the exposure to being wrong."""
    def s(view, pos):
        if len(view) < n + 1:
            return 0
        c = view.closes(n)
        return 1 if c[-1] > statistics.fmean(c) else 0
    return s


def vol_target(target_annual, lookback=20):
    """Binary approximation of volatility targeting: hold when realised
    volatility is at or below the target, stand aside when it is above. The
    framework sizes every position at one unit of capital, so the honest way
    to express 'size down in a storm' inside it is to be out of the storm."""
    def s(view, pos):
        if len(view) < lookback + 2:
            return 0
        c = view.closes(lookback + 1)
        rets = [(c[i] / c[i - 1]) - 1.0 for i in range(1, len(c)) if c[i - 1]]
        if len(rets) < 2:
            return 0
        vol = statistics.pstdev(rets) * math.sqrt(365.0)
        return 1 if vol <= target_annual else 0
    return s


def risk_grid():
    g = []
    for n in (50, 100, 150, 200):
        g.append(("risk:sma_filter %d" % n, sma_filter(n), n + 2))
    for t in (0.20, 0.30, 0.40):
        g.append(("risk:vol_target %.0f%%" % (t * 100), vol_target(t), 24))
    return g


def buy_hold_stats(bars):
    first, last = bars[0].open, bars[-1].close
    ret = (last / first) - 1.0
    peak, mdd, eq = first, 0.0, first
    for b in bars:
        eq = b.close
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / peak) if peak else mdd
    rets = [(bars[i].close / bars[i - 1].close) - 1.0 for i in range(1, len(bars)) if bars[i - 1].close]
    sd = statistics.pstdev(rets) if len(rets) > 1 else 0.0
    sharpe = (statistics.fmean(rets) / sd) * math.sqrt(365.0) if sd else 0.0
    return {"return": ret, "mdd": mdd, "sharpe": sharpe}


# ---------------------------------------------------------------- PBO (CSCV)
def pbo(returns_by_variant, n_blocks=8):
    """Bailey/Lopez de Prado combinatorially symmetric cross-validation.
    Returns (pbo, n_splits) -- the fraction of splits where the variant chosen
    on the in-sample half lands below the out-of-sample median."""
    names = [k for k, v in returns_by_variant.items() if v and statistics.pstdev(v) > 0]
    if len(names) < 3:
        return -1.0, 0
    T = min(len(returns_by_variant[n]) for n in names)
    bl = T // n_blocks
    if bl < 10:
        return -1.0, 0
    blocks = [list(range(i * bl, (i + 1) * bl)) for i in range(n_blocks)]
    M = {n: returns_by_variant[n][:bl * n_blocks] for n in names}

    def sharpe(name, idx):
        xs = [M[name][i] for i in idx]
        sd = statistics.pstdev(xs)
        return (statistics.fmean(xs) / sd) if sd else 0.0

    worse = total = 0
    for combo in itertools.combinations(range(n_blocks), n_blocks // 2):
        is_idx = [i for b in combo for i in blocks[b]]
        oos_idx = [i for b in range(n_blocks) if b not in combo for i in blocks[b]]
        best = max(names, key=lambda n: sharpe(n, is_idx))
        oos = sorted(sharpe(n, oos_idx) for n in names)
        med = statistics.median(oos)
        worse += 1 if sharpe(best, oos_idx) < med else 0
        total += 1
    return (worse / total if total else -1.0), total


# ---------------------------------------------------------------- run
def series_files(only=None):
    out = {}
    for f in sorted(glob.glob(os.path.join(DEEP, "*_20*.csv"))):
        sym = os.path.basename(f).split("_")[0]
        if only and sym not in only:
            continue
        n = sum(1 for _ in open(f, encoding="utf-8"))
        if sym not in out or n > out[sym][1]:
            out[sym] = (f, n)
    return {k: v[0] for k, v in sorted(out.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="*")
    ap.add_argument("--fee-bps", type=float, default=FEE_BPS)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--out")
    a = ap.parse_args()

    cost = CostModel(taker_fee_bps=a.fee_bps, spread_bps=SPREAD_BPS,
                     slippage_bps=SLIP_BPS, min_notional=MIN_NOTIONAL)
    bt = Backtester(cost=cost, capital=CAPITAL)
    files = series_files(a.assets)
    grid = L.build_grid() + risk_grid()
    tried = len(grid) * len(files)          # ONE search, honestly counted
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    say("strategy_validate -- %d variants x %d assets = %d trials in one search" % (len(grid), len(files), tried))
    say("costs: taker %.0f bps + spread %.0f + slippage %.0f, adverse both ways; "
        "round trip %.0f bps; size $%.0f; min notional $%.0f"
        % (a.fee_bps, SPREAD_BPS, SLIP_BPS, cost.round_trip_bps(), CAPITAL, MIN_NOTIONAL))
    say()

    per_asset, risk_rows, best_rows = {}, [], []
    for sym, path in files.items():
        bars = load_csv(path)
        bh = buy_hold_stats(bars)
        rets_by_variant, rows = {}, []
        for name, strat, warm in grid:
            try:
                r = bt.run(bars, strat, warmup=warm, label=name, strategies_tried=tried)
            except ValueError:
                continue
            rows.append((name, r))
            rets_by_variant[name] = r.returns
            if name.startswith("risk:"):
                held = sum(t.bars_held for t in r.trades)
                risk_rows.append({"asset": sym, "rule": name, "ret": r.total_return, "mdd": r.max_drawdown(),
                                  "bh_ret": bh["return"], "bh_mdd": bh["mdd"], "trades": r.n_trades,
                                  "in_market": held / float(max(1, r.n_bars))})
        if not rows:
            continue
        rows.sort(key=lambda x: x[1].sharpe(), reverse=True)
        name, best = rows[0]
        d = deflated_sharpe(best)
        p, nsplit = pbo(rets_by_variant)
        per_asset[sym] = {"bars": len(bars), "bh": bh, "best": name, "res": best, "dsr": d, "pbo": p, "splits": nsplit}
        say("%-5s %3d bars | buy&hold %+7.1f%% (mdd %4.1f%%) | best %-22s %+7.1f%% "
            "sharpe %5.2f dsr %.4f trades %3d mdd %4.1f%% | PBO %s"
            % (sym, len(bars), bh["return"] * 100, bh["mdd"] * 100, name, best.total_return * 100,
               best.sharpe(), d["deflated_sharpe"], best.n_trades, best.max_drawdown() * 100,
               ("%.2f" % p) if p >= 0 else "n/a"))
        best_rows.append((sym, name, best, d, p))

    # ---- walk-forward the per-asset winner -------------------------------
    say()
    say("walk-forward (%d folds, 2%% embargo). The PROCEDURE is refit on each training" % a.folds)
    say("slice -- the grid is re-searched on train only and its winner traded forward --")
    say("because that is what a person actually does, and it is what carries the")
    say("selection bias the fixed-parameter version hides:")
    survivors = []
    for sym, name, best, d, p in best_rows:
        bars = load_csv(files[sym])
        # A fold cannot validate a rule whose warm-up is longer than the fold.
        # 611 daily bars at 5 folds leave room for a 71-day look-back and no
        # more, so the long rules are EXCLUDED here and named, rather than
        # quietly validated on a window that cannot hold them.
        wf, folds_used, warm, dropped = None, a.folds, 0, []
        while folds_used >= 2 and wf is None:
            cap = len(bars) // (folds_used + 1) - 30
            fit = [(n, st, w) for n, st, w in grid if w <= cap]
            if cap < 25 or not fit:
                folds_used -= 1; continue
            warm = max(w for _, _, w in fit)
            dropped = [n for n, _, w in grid if w > cap]

            def build(train, _bt=bt, _fit=fit):
                """Re-run the search on the training slice and return its
                winner. It never sees the test slice."""
                bests, bestsh = None, -1e9
                for n, st, w in _fit:
                    try:
                        r = _bt.run(train, st, warmup=w, label=n)
                    except ValueError:
                        continue
                    sh = r.sharpe()
                    if sh > bestsh:
                        bests, bestsh = st, sh
                return bests if bests is not None else (lambda v, pos: 0)

            try:
                wf = walk_forward(bars, build, folds=folds_used, embargo_frac=0.02,
                                  cost=cost, capital=CAPITAL, warmup=warm)
            except ValueError:
                folds_used -= 1
        if wf is None:
            say("  %-5s walk-forward impossible: %d bars cannot support 2 folds"
                % (sym, len(bars))); continue
        if dropped:
            say("  %-5s excluded from the walk-forward (look-back longer than a fold): %s"
                % (sym, ", ".join(dropped[:6]) + (" +%d more" % (len(dropped) - 6) if len(dropped) > 6 else "")))
        ok = bool(wf["consistent"]) and d["deflated_sharpe"] >= 0.95 and 0 <= p < 0.5
        say("  %-5s refit-per-fold  folds +%d/%d  mean OOS %+6.2f%%  worst %+6.2f%%  p=%.3f  "
            "consistent=%s  (in-sample pick was %s)  -> %s"
            % (sym, wf["positive_folds"], wf["folds"], wf["mean_return"] * 100,
               wf["worst_fold"] * 100, wf["binomial_p"], wf["consistent"], name,
               "SURVIVES" if ok else "no"))
        if ok:
            survivors.append((sym, name))

    # ---- the drawdown claim ----------------------------------------------
    say()
    say("the one prior claim -- does a trend filter still cut the worst drawdown?")
    by_rule = {}
    for r in risk_rows:
        by_rule.setdefault(r["rule"], []).append(r)
    for rule, rs in sorted(by_rule.items()):
        cut = [x for x in rs if x["mdd"] < x["bh_mdd"]]
        ratio = [x["bh_mdd"] / x["mdd"] for x in rs if x["mdd"] > 0.001]
        drag = [x["ret"] - x["bh_ret"] for x in rs]
        tim = [x["in_market"] for x in rs]
        say("  %-22s drawdown fell on %2d/%2d assets | median cut %.2fx | median return vs hold %+6.1f pp"
            " | median time in market %3.0f%%"
            % (rule, len(cut), len(rs), statistics.median(ratio) if ratio else 0.0,
               statistics.median(drag) * 100, statistics.median(tim) * 100))

    say()
    if survivors:
        say("SURVIVORS (deflated Sharpe >= 0.95 AND walk-forward consistent AND PBO < 0.5): %s"
            % ", ".join("%s %s" % s for s in survivors))
    else:
        say("NO RULE SURVIVED. Not one variant on one asset cleared deflated Sharpe >= 0.95,")
        say("walk-forward consistency at p <= 0.05, and PBO < 0.5 together. On this evidence")
        say("arming the trader for RETURN would be adding risk for no measured reason.")

    if a.out:
        with open(os.path.join(HERE, a.out), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        say("\nwritten to %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
