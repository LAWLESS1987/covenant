#!/usr/bin/env python3
"""
full_test.py -- one comprehensive run against REAL live data.

Runs the whole battery on your watchlist and writes a structured report to
covenant_test_report.txt, so it can be read and iterated on.

  1. per-asset HOLD benchmark (the thing every bot must beat)
  2. strategy search with TRAIN/TEST split (winners scored on unseen data)
  3. trial-count deflation across the entire search
  4. rebalancing test at several periods and drift bands
  5. correlation of the basket (decides whether rebalancing can work at all)

Nothing here trades, holds keys, or touches funds.

  python full_test.py
  python full_test.py --granularity day --symbols xlm,link,hbar,ada,ondo,xrp
"""
from __future__ import annotations
import os, sys, argparse, statistics, math, time, io, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "quant"))
sys.path.insert(0, HERE)
from covenant_backtest import Backtester, CostModel, deflated_sharpe
from paper_bot import fetch_coinbase, synth
from strategy_lab import build_grid, buy_hold
from multi_scan import resolve, luck_benchmark, DEFAULT
import rebalance_strategy as RB

REPORT = os.path.join(HERE, "covenant_test_report.txt")


class Tee:
    """Print to console AND capture for the report file."""
    def __init__(self):
        self.buf = io.StringIO()

    def __call__(self, *a):
        line = " ".join(str(x) for x in a)
        print(line)
        self.buf.write(line + "\n")


def corr(a, b):
    if len(a) != len(b) or len(a) < 3:
        return 0.0
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    na = sum((x - ma) ** 2 for x in a) ** 0.5
    nb = sum((y - mb) ** 2 for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (na * nb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(DEFAULT))
    ap.add_argument("--granularity", choices=["hour", "day"], default="hour")
    ap.add_argument("--capital", type=float, default=1000.0)
    ap.add_argument("--fee-bps", type=float, default=10.0)
    ap.add_argument("--synthetic", action="store_true", help="offline self-test")
    args = ap.parse_args()

    out = Tee()
    t0 = time.time()
    syms = [resolve(s) for s in args.symbols.split(",") if s.strip()]
    gran = 3600 if args.granularity == "hour" else 86400
    cost = CostModel(taker_fee_bps=args.fee_bps, spread_bps=5, slippage_bps=5,
                     min_notional=5.0)
    bt = Backtester(cost=cost, capital=args.capital)
    grid = build_grid()

    out("=" * 78)
    out(f"COVENANT FULL TEST   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    out(f"{len(syms)} symbols | {args.granularity} candles | {len(grid)} variants each")
    out(f"cost model: {cost.round_trip_bps():.0f} bps round trip | capital ${args.capital:,.0f}")
    out("=" * 78)

    # ---------------------------------------------------------------- fetch
    series, missing = {}, []
    out("\n[1] FETCHING REAL DATA")
    for s in syms:
        try:
            series[s] = (synth("noise", n=700, seed=abs(hash(s)) % 9999)
                         if args.synthetic else fetch_coinbase(s, gran))
            out(f"    {s:<12} {len(series[s])} bars  "
                f"last close {series[s][-1].close:.6f}")
        except Exception as e:
            missing.append(s)
            out(f"    {s:<12} UNAVAILABLE ({str(e)[:46]})")
        if not args.synthetic:
            time.sleep(0.25)
    if len(series) < 2:
        out("\nNot enough usable symbols. Try --granularity day.")
        open(REPORT, "w").write(out.buf.getvalue())
        return

    # ---------------------------------------------------------- scan + holdout
    out("\n[2] STRATEGY SEARCH WITH TRAIN/TEST SPLIT")
    out(f"    {'symbol':<12}{'HOLD':>10}{'train best':>12}{'OUT-OF-SAMPLE':>15}  strategy")
    rows, total_trials = [], 0
    for s, bars in series.items():
        try:
            bench = bt.run(bars, buy_hold(), warmup=5, strategies_tried=1)
        except Exception:
            continue
        split = int(len(bars) * 0.70)
        train, test = bars[:split], bars[split:]
        best = None
        for name, strat, warm in grid:
            if len(train) < warm + 40:
                continue
            try:
                r = bt.run(train, strat, warmup=warm, label=name)
            except Exception:
                continue
            total_trials += 1
            if best is None or r.total_return > best[3].total_return:
                best = (name, strat, warm, r)
        if not best:
            continue
        name, strat, warm, tr = best
        oos = None
        if len(test) >= warm + 20:
            try:
                oos = bt.run(test, strat, warmup=warm)
            except Exception:
                oos = None
        rows.append({"sym": s, "bench": bench, "name": name, "train": tr, "oos": oos})
        o = f"{oos.total_return:+.2%}" if oos else "n/a"
        out(f"    {s:<12}{bench.total_return:>+9.2%}{tr.total_return:>+11.2%}"
            f"{o:>15}  {name}")

    # ------------------------------------------------------------- scoring
    out("\n[3] HONEST SCORING")
    out(f"    total variants tried : {total_trials}")
    lb = luck_benchmark(total_trials)
    out(f"    luck benchmark       : Sharpe {lb:.2f} (best a NO-EDGE search returns)")
    if rows:
        rows.sort(key=lambda r: -r["train"].total_return)
        top = rows[0]
        top["train"].strategies_tried = total_trials
        d = deflated_sharpe(top["train"])
        out(f"    headline winner      : {top['sym']} / {top['name']} "
            f"{top['train'].total_return:+.2%}")
        out(f"    raw Sharpe           : {d['sharpe']:.2f}")
        out(f"    DEFLATED (all tries) : {d['deflated_sharpe']:.4f}  <-- the honest one")

        scored = [r for r in rows if r.get("oos")]
        surv = [r for r in scored if r["oos"].total_return > 0]
        if scored:
            mo = statistics.fmean(r["oos"].total_return for r in scored)
            n, k = len(scored), len(surv)
            p = sum(math.comb(n, i) for i in range(k, n + 1)) / (2 ** n)
            out(f"    OUT-OF-SAMPLE        : {k}/{n} winners still profitable, "
                f"mean {mo:+.2%}, p={p:.3f}")
            verdict = ("CURVE FIT -- winners lost on unseen data" if mo <= 0
                       else "positive but consistent with luck" if p > 0.05
                       else "SURVIVED unseen data at p<=0.05")
            out(f"    verdict              : {verdict}")
        beat = [r for r in rows if r["train"].total_return > r["bench"].total_return]
        out(f"    beat simple HOLD     : {len(beat)}/{len(rows)} assets")

    # --------------------------------------------------------- correlation
    out("\n[4] BASKET CORRELATION (decides if rebalancing can work)")
    aligned, n = RB.align(series)
    rets = {s: [(v[i].close / v[i-1].close - 1) for i in range(1, n)]
            for s, v in aligned.items()}
    ss = sorted(rets)
    pairs = [corr(rets[a], rets[b]) for i, a in enumerate(ss) for b in ss[i+1:]]
    if pairs:
        avg_c = statistics.fmean(pairs)
        out(f"    average pairwise correlation : {avg_c:+.3f}  "
            f"(min {min(pairs):+.3f}, max {max(pairs):+.3f})")
        out("    " + ("-> highly correlated: these move together, so diversification"
                      if avg_c > 0.6 else
                      "-> moderately correlated: some rebalancing benefit possible"
                      if avg_c > 0.3 else
                      "-> low correlation: good conditions for rebalancing"))
        if avg_c > 0.6:
            out("       and the rebalancing bonus are both WEAK here.")

    # --------------------------------------------------------- rebalancing
    out("\n[5] REBALANCING vs HOLDING (no prediction required)")
    hold = RB.run_portfolio(aligned, n, "hold", 0, 0, 40.0, args.capital)
    hs = RB.stats(hold["equity"], args.capital)
    out(f"    equal-weight HOLD : {hs['ret']:+.2%}  vol {hs['vol']:.4f}  "
        f"maxDD {hs['mdd']:.2%}")
    best_cfg = None
    for period, band, label in ((24, 0.0, "daily"), (168, 0.0, "weekly"),
                                (720, 0.0, "monthly"), (0, 0.20, "20% drift band"),
                                (0, 0.35, "35% drift band")):
        r = RB.run_portfolio(aligned, n, "rebal", period, band, 40.0, args.capital)
        st = RB.stats(r["equity"], args.capital)
        edge = st["ret"] - hs["ret"]
        note = "  (never fired = just holding)" if r["rebalances"] == 0 else ""
        out(f"    rebal {label:<16}: {st['ret']:+.2%}  vol {st['vol']:.4f}  "
            f"maxDD {st['mdd']:.2%}  bonus {edge:+.2%}  ({r['rebalances']} trades, "
            f"${r['fees']:.2f} fees){note}")
        # only count a config that ACTUALLY rebalanced -- a setting that never
        # fires is holding wearing a different label, and calling it the
        # "best rebalance setting" would be a ghost result.
        if r["rebalances"] > 0 and (best_cfg is None or edge > best_cfg[1]):
            best_cfg = (label, edge, st, r)
    if best_cfg:
        out(f"\n    best setting that actually traded : {best_cfg[0]} "
            f"({best_cfg[1]:+.2%} vs hold)")
        if best_cfg[1] <= 0:
            # WHY it lost matters more than that it lost. The dominant cause is
            # usually one asset trending hard: rebalancing trims the winner.
            spread = None
            try:
                perf = {s: v[-1].close / v[0].close - 1 for s, v in aligned.items()}
                win, lose = max(perf, key=perf.get), min(perf, key=perf.get)
                spread = perf[win] - perf[lose]
                fee_share = best_cfg[3]["fees"] / args.capital
                out(f"    -> NO rebalancing bonus. Holding won by "
                    f"{abs(best_cfg[1]):.2%}.")
                out(f"       fees explain only {fee_share:.2%} of that.")
                if spread > 0.8:
                    out(f"       MAIN CAUSE: {win} ran {perf[win]:+.1%} while {lose} did "
                        f"{perf[lose]:+.1%}.")
                    out(f"       Rebalancing repeatedly TRIMS the runaway winner. When one")
                    out(f"       asset dominates, holding beats rebalancing -- by design.")
                else:
                    out("       Cause is drag from trading, not a single dominant asset.")
            except Exception:
                out("    -> NO rebalancing bonus on this basket. Holding won.")
        else:
            out("    -> small structural gain, and it does not decay like a signal.")
    else:
        out("\n    no rebalance setting fired -- series too short for these periods.")

    # ------------------------------------------------------------- summary
    out("\n" + "=" * 78)
    out("BOTTOM LINE")
    out("=" * 78)
    if rows:
        holds = sorted(rows, key=lambda r: -r["bench"].total_return)
        out(f"  best asset by simply HOLDING : {holds[0]['sym']} "
            f"{holds[0]['bench'].total_return:+.2%}")
        out(f"  worst asset by holding       : {holds[-1]['sym']} "
            f"{holds[-1]['bench'].total_return:+.2%}")
    out(f"  runtime {time.time()-t0:.0f}s | report written to {os.path.basename(REPORT)}")
    if missing:
        out(f"  unavailable symbols: {', '.join(missing)}")
    out("=" * 78)

    try:
        open(REPORT, "w", encoding="utf-8").write(out.buf.getvalue())
    except Exception as e:
        print(f"could not write report: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
    except Exception:
        traceback.print_exc()
