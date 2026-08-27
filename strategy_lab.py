#!/usr/bin/env python3
"""
strategy_lab.py -- refine a trading strategy HONESTLY.

The trap this avoids: search enough variants and one will look brilliant on any
data, including pure noise. That is not a strategy, it is a curve fit, and it
is the single most common way people lose money on bots.

So this lab does what a real quant does, and what a marketplace bot never shows:
  * tests several genuine strategy FAMILIES, not one knob
  * COUNTS every variant tried, and deflates the winner by that count
  * validates out-of-sample with walk-forward + an embargo gap
  * pays realistic fees and slippage at your actual size
  * reports "no edge found" when that is the truth -- which it usually is

USAGE
  python strategy_lab.py --source coinbase --symbol XRP-USD --granularity hour
  python strategy_lab.py --csv xrp.csv --capital 1000
  python strategy_lab.py --series noise      # sanity check: should find nothing
  python strategy_lab.py --series trend      # sanity check: should find the trend
"""
from __future__ import annotations
import os, sys, argparse, math, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "quant"))
sys.path.insert(0, HERE)
from covenant_backtest import (
    Bar, Backtester, CostModel, deflated_sharpe, walk_forward, load_csv,
)
from paper_bot import fetch_coinbase, synth


# ---------------------------------------------------------------- strategies
def sma_cross(fast, slow):
    """Trend following: fast average above slow = uptrend."""
    def s(view, pos):
        if len(view) < slow + 1:
            return 0
        c = view.closes(slow)
        return 1 if statistics.fmean(c[-fast:]) > statistics.fmean(c) else -1
    return s


def sma_long_only(fast, slow):
    """Same trend signal, but flat instead of short. Shorting doubles your
    exposure to being wrong; many 'edges' vanish once you cannot short."""
    def s(view, pos):
        if len(view) < slow + 1:
            return 0
        c = view.closes(slow)
        return 1 if statistics.fmean(c[-fast:]) > statistics.fmean(c) else 0
    return s


def mean_revert(lookback, z_enter):
    """Mean reversion: buy when price is z_enter SDs BELOW its own average."""
    def s(view, pos):
        if len(view) < lookback + 1:
            return 0
        c = view.closes(lookback)
        m = statistics.fmean(c)
        sd = statistics.pstdev(c)
        if sd <= 0:
            return 0
        z = (c[-1] - m) / sd
        if z < -z_enter:
            return 1
        if z > z_enter:
            return -1
        return 0
    return s


def breakout(lookback):
    """Volatility breakout: long on a new N-bar high, short on a new N-bar low."""
    def s(view, pos):
        if len(view) < lookback + 1:
            return 0
        c = view.closes(lookback)
        last = c[-1]
        if last >= max(c[:-1]):
            return 1
        if last <= min(c[:-1]):
            return -1
        return pos
    return s


def trend_filtered_revert(lookback, z_enter, trend):
    """Mean-revert, but ONLY in the direction of the longer trend. Combining a
    filter with an entry is real strategy work, not another knob."""
    def s(view, pos):
        if len(view) < max(lookback, trend) + 1:
            return 0
        ct = view.closes(trend)
        up = ct[-1] > statistics.fmean(ct)
        c = view.closes(lookback)
        m, sd = statistics.fmean(c), statistics.pstdev(c)
        if sd <= 0:
            return 0
        z = (c[-1] - m) / sd
        if up and z < -z_enter:
            return 1
        if (not up) and z > z_enter:
            return -1
        return 0
    return s


def buy_hold():
    return lambda view, pos: 1


def build_grid():
    """Every variant we will try. The SIZE of this list is what the deflated
    Sharpe must be penalised by -- it is carried, not forgotten."""
    g = []
    for fast in (5, 8, 12, 20):
        for slow in (30, 48, 72, 100):
            if fast < slow:
                g.append((f"sma_cross {fast}/{slow}", sma_cross(fast, slow), slow + 2))
                g.append((f"sma_longonly {fast}/{slow}", sma_long_only(fast, slow), slow + 2))
    for lb in (16, 24, 48):
        for z in (1.0, 1.5, 2.0):
            g.append((f"mean_revert {lb}/{z}", mean_revert(lb, z), lb + 2))
    for lb in (12, 24, 48, 72):
        g.append((f"breakout {lb}", breakout(lb), lb + 2))
    for lb in (16, 24):
        for z in (1.0, 1.5):
            for tr in (72, 120):
                g.append((f"filt_revert {lb}/{z}/{tr}", trend_filtered_revert(lb, z, tr), tr + 2))
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["synthetic", "coinbase"], default="synthetic")
    ap.add_argument("--symbol", default="XRP-USD")
    ap.add_argument("--granularity", choices=["hour", "day"], default="hour")
    ap.add_argument("--csv", default="")
    ap.add_argument("--series", choices=["trend", "noise"], default="noise")
    ap.add_argument("--capital", type=float, default=1000.0)
    ap.add_argument("--fee-bps", type=float, default=10.0)
    args = ap.parse_args()

    if args.csv:
        bars = load_csv(args.csv); src = f"{args.csv} ({len(bars)} bars)"
    elif args.source == "coinbase":
        bars = fetch_coinbase(args.symbol, 3600 if args.granularity == "hour" else 86400)
        src = f"Coinbase {args.symbol} {args.granularity} ({len(bars)} bars)"
    else:
        bars = synth(args.series); src = f"synthetic '{args.series}' ({len(bars)} bars)"

    cost = CostModel(taker_fee_bps=args.fee_bps, spread_bps=5, slippage_bps=5, min_notional=5.0)
    grid = build_grid()
    bt = Backtester(cost=cost, capital=args.capital)

    print("=" * 74)
    print(f"STRATEGY LAB  |  {src}")
    print(f"capital ${args.capital:,.0f} | round trip {cost.round_trip_bps():.0f} bps | "
          f"{len(grid)} variants")
    print("=" * 74)

    results = []
    for name, strat, warm in grid:
        if len(bars) < warm + 40:
            continue
        try:
            r = bt.run(bars, strat, warmup=warm, label=name, strategies_tried=len(grid))
        except Exception:
            continue
        results.append((name, strat, warm, r))

    if not results:
        print("Not enough data for any variant. Use more bars (--granularity hour).")
        return

    results.sort(key=lambda x: -x[3].total_return)

    # BENCHMARK, judged separately and fairly. buy_and_hold has ZERO free
    # parameters and was never searched, so deflating it by the whole grid is
    # wrong -- that is what made an honest +170% trend look like "no edge".
    # It is also the question that actually decides whether to run a bot at all:
    # if simply holding beats every variant, the bot is a fee-generating machine.
    bench = bt.run(bars, buy_hold(), warmup=5, label="buy_and_hold",
                   strategies_tried=1)
    bench_d = deflated_sharpe(bench)

    print(f"\n  {'strategy':<26}{'return':>10}{'Sharpe':>9}{'trades':>8}{'fees':>10}")
    print("  " + "-" * 61)
    for name, _, _, r in results[:10]:
        print(f"  {name:<26}{r.total_return:>+9.2%}{r.sharpe():>9.2f}"
              f"{r.n_trades:>8}{r.total_fees():>9.2f}")

    best_name, best_strat, best_warm, best = results[0]

    print("\n" + "=" * 74)
    print("BENCHMARK -- just holding the asset (no bot, no fees beyond one entry)")
    print("=" * 74)
    print(f"  buy_and_hold return   : {bench.total_return:+.2%}   "
          f"Sharpe {bench.sharpe():.2f}   DSR {bench_d['deflated_sharpe']:.3f}")
    beats = best.total_return > bench.total_return
    print(f"  best bot beats it?    : {'YES' if beats else 'NO'}  "
          f"({best.total_return:+.2%} vs {bench.total_return:+.2%})")
    if not beats:
        print("  -> Every variant underperformed simply HOLDING. On this data a bot")
        print("     is a fee-generating machine. That is a complete answer by itself.")

    print("\n" + "=" * 74)
    print(f"BEST SEARCHED VARIANT: {best_name}   {best.total_return:+.2%}")
    print("=" * 74)

    d = deflated_sharpe(best)
    print(f"  raw Sharpe            : {d['sharpe']:.2f}")
    print(f"  variants tried        : {d['trials']}")
    print(f"  luck benchmark        : {d['expected_max_sharpe']:.2f}  "
          f"(best Sharpe {d['trials']} NO-EDGE tries would produce)")
    print(f"  DEFLATED Sharpe       : {d['deflated_sharpe']:.4f}")
    print(f"  verdict               : {d['verdict']}")

    # Out-of-sample: refit on each training slice only, test on unseen data.
    print("\n  walk-forward (refit per fold, embargo gap, unseen test data):")
    try:
        def rebuild(train):
            b, bs = None, best_strat
            for nm, st, wm in grid:
                if len(train) < wm + 40:
                    continue
                try:
                    rr = Backtester(cost=cost, capital=args.capital).run(train, st, warmup=wm)
                except Exception:
                    continue
                if b is None or rr.total_return > b:
                    b, bs = rr.total_return, st
            return bs
        wf = walk_forward(bars, rebuild, folds=4, embargo_frac=0.02,
                          cost=cost, capital=args.capital, warmup=best_warm)
        print(f"    folds positive      : {wf['positive_folds']}/{wf['folds']}")
        print(f"    mean out-of-sample  : {wf['mean_return']:+.2%}")
        print(f"    worst fold          : {wf['worst_fold']:+.2%}")
        print(f"    p under the null    : {wf['binomial_p']:.3f}")
        print(f"    consistent          : {wf['consistent']}")
        wf_ok = bool(wf["consistent"])
    except Exception as e:
        print(f"    (not enough data for walk-forward: {e})")
        wf_ok = False

    print("\n" + "=" * 74)
    if d["deflated_sharpe"] >= 0.95 and wf_ok and beats:
        print("RESULT: a variant survived trial-count deflation AND out-of-sample")
        print("validation AND beat buy-and-hold. That is rare. Next step is NOT")
        print("real money -- it is signal_watch.py for 30+ sealed live signals.")
    elif bench_d["deflated_sharpe"] >= 0.95 and not beats:
        print("RESULT: NO BOT EDGE -- but HOLDING worked on this data.")
        print(f"buy_and_hold returned {bench.total_return:+.2%} (DSR "
              f"{bench_d['deflated_sharpe']:.3f}) and beat all {len(grid)} variants.")
        print("The honest conclusion is not 'tune the bot harder'. It is that on")
        print("this data the trading added cost and subtracted return.")
    else:
        print("RESULT: NO EDGE FOUND.")
        print(f"'{best_name}' returned {best.total_return:+.2%}, but once you account")
        print(f"for having tried {len(grid)} variants, it is indistinguishable from")
        print("luck. This is the correct and most common answer -- and finding it")
        print("here costs nothing, while finding it with real money costs money.")
        print("\nRefining further means NEW INFORMATION (a different data source, a")
        print("real structural insight), not more knobs on the same price series.")
        print("More variants make this WORSE, not better -- each one raises the")
        print("luck benchmark the winner has to clear.")
    print("=" * 74)


if __name__ == "__main__":
    main()
