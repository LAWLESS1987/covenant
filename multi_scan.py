#!/usr/bin/env python3
"""
multi_scan.py -- scan a watchlist of coins for a real edge, honestly.

THE TRAP THIS EXISTS TO AVOID
  Scanning many assets multiplies the search. 14 coins x 53 variants = 742
  tries. The best of 742 no-edge tries looks spectacular -- guaranteed, on pure
  noise. A scanner that reports "best coin: +180%!" without deflating by the
  TOTAL number of tries is a machine for manufacturing false winners, and that
  is what most "AI crypto scanners" are.

  So: every variant on every asset counts toward one shared trial budget, and
  the winner is judged against the luck benchmark for that whole budget.

ALSO REPORTED, because they decide more than the strategy does:
  * HOLD benchmark per asset -- if simply holding beats every bot, the bot is
    a fee machine and that is the answer.
  * Watchlist bias -- a list chosen today, knowing which coins already ran, is
    not a fair sample. This project's own quant README flags exactly that.

USAGE
  python multi_scan.py                                   # the default watchlist
  python multi_scan.py --symbols XLM-USD,LINK-USD,DOGE-USD
  python multi_scan.py --granularity day --capital 1000
"""
from __future__ import annotations
import os, sys, argparse, statistics, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "quant"))
sys.path.insert(0, HERE)
from covenant_backtest import Backtester, CostModel, deflated_sharpe, _norm_ppf
from paper_bot import fetch_coinbase
from strategy_lab import build_grid, buy_hold
import math

# friendly name -> Coinbase product id
ALIASES = {
    "xlm": "XLM-USD", "stellar": "XLM-USD",
    "chainlink": "LINK-USD", "link": "LINK-USD",
    "hbar": "HBAR-USD", "hedera": "HBAR-USD",
    "worldcoin": "WLD-USD", "wld": "WLD-USD",
    "jasmy": "JASMY-USD", "jasymy": "JASMY-USD",
    "wlfi": "WLFI-USD",
    "ada": "ADA-USD", "cardano": "ADA-USD",
    "toshi": "TOSHI-USD",
    "onyxcoin": "XCN-USD", "xcn": "XCN-USD",
    "cronos": "CRO-USD", "cro": "CRO-USD",
    "eos": "EOS-USD",
    "vechain": "VET-USD", "vet": "VET-USD",
    "pepe": "PEPE-USD",
    "doge": "DOGE-USD", "dogecoin": "DOGE-USD",
    "ondo": "ONDO-USD",
    "canton": "CC-USD", "cantonnetwork": "CC-USD", "canton network": "CC-USD",
    "xrp": "XRP-USD", "btc": "BTC-USD", "eth": "ETH-USD",
}

DEFAULT = ["XLM-USD", "LINK-USD", "HBAR-USD", "WLD-USD", "JASMY-USD", "WLFI-USD",
           "ADA-USD", "TOSHI-USD", "XCN-USD", "CRO-USD", "EOS-USD", "VET-USD",
           "PEPE-USD", "DOGE-USD", "ONDO-USD", "CC-USD"]


def resolve(s: str) -> str:
    s = s.strip()
    return ALIASES.get(s.lower(), s.upper() if "-" in s else f"{s.upper()}-USD")


def luck_benchmark(trials: int) -> float:
    """Expected best Sharpe from `trials` independent NO-EDGE tries."""
    if trials <= 1:
        return 0.0
    e = 0.5772156649
    return (1 - e) * _norm_ppf(1 - 1.0 / trials) + e * _norm_ppf(1 - 1.0 / (trials * math.e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(DEFAULT))
    ap.add_argument("--granularity", choices=["hour", "day"], default="hour")
    ap.add_argument("--capital", type=float, default=1000.0)
    ap.add_argument("--fee-bps", type=float, default=10.0)
    args = ap.parse_args()

    symbols = [resolve(s) for s in args.symbols.split(",") if s.strip()]
    cost = CostModel(taker_fee_bps=args.fee_bps, spread_bps=5, slippage_bps=5, min_notional=5.0)
    grid = build_grid()
    bt = Backtester(cost=cost, capital=args.capital)
    gran = 3600 if args.granularity == "hour" else 86400

    print("=" * 78)
    print(f"MULTI-ASSET SCAN  |  {len(symbols)} symbols x {len(grid)} variants  "
          f"|  {args.granularity} candles")
    print("=" * 78)

    rows, missing, total_trials = [], [], 0
    for sym in symbols:
        try:
            bars = fetch_coinbase(sym, gran)
        except SystemExit as e:
            missing.append((sym, str(e)[:60]))
            print(f"  {sym:<12} unavailable ({str(e)[:44]})")
            continue
        except Exception as e:
            missing.append((sym, f"{type(e).__name__}"))
            print(f"  {sym:<12} error {type(e).__name__}")
            continue

        bench = bt.run(bars, buy_hold(), warmup=5, strategies_tried=1)

        # HOLD-OUT VALIDATION -- the same standard XRP got, applied per asset.
        # Choosing the winner on ALL the data is the in-sample illusion: the
        # winner is picked BECAUSE it fits that data. So search only the first
        # 70%, then score that winner on the last 30% it has never seen. A real
        # edge keeps working; a curve fit falls apart. This is the single most
        # informative number in the whole scan.
        split = int(len(bars) * 0.70)
        train, test = bars[:split], bars[split:]

        best = None            # winner chosen on TRAIN only
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
        if best is None:
            missing.append((sym, "not enough bars"))
            continue

        name, strat, warm, tr_res = best
        oos = None
        if len(test) >= warm + 20:
            try:
                oos = bt.run(test, strat, warmup=warm, label=f"{name}@oos")
            except Exception:
                oos = None

        rows.append({"sym": sym, "bench": bench, "best_name": name,
                     "best": tr_res, "oos": oos, "bars": len(bars)})
        beat = "yes" if tr_res.total_return > bench.total_return else "no"
        oos_s = f"{oos.total_return:>+8.2%}" if oos else "    n/a "
        print(f"  {sym:<12} hold {bench.total_return:>+8.2%}  train "
              f"{tr_res.total_return:>+8.2%}  OUT-OF-SAMPLE {oos_s}  ({name})")
        time.sleep(0.25)   # be polite to the public API

    if not rows:
        print("\nNo usable symbols. Check names, or try --granularity day.")
        return

    bench_ok = luck_benchmark(total_trials)
    print("\n" + "=" * 78)
    print("HONEST SCORING")
    print("=" * 78)
    print(f"  total variants tried across all assets : {total_trials}")
    print(f"  luck benchmark for {total_trials} tries        : Sharpe "
          f"{bench_ok:.2f} -- the best a NO-EDGE search returns")

    rows.sort(key=lambda r: -r["best"].total_return)
    top = rows[0]
    d = deflated_sharpe(top["best"])          # per-asset trial count
    top["best"].strategies_tried = total_trials
    d_all = deflated_sharpe(top["best"])      # deflated by the WHOLE search

    print(f"\n  headline winner : {top['sym']} / {top['best_name']}  "
          f"{top['best'].total_return:+.2%}")
    print(f"  raw Sharpe                        : {d['sharpe']:.2f}")
    print(f"  deflated by this asset alone      : {d['deflated_sharpe']:.4f}")
    print(f"  deflated by ALL {total_trials} tries        : {d_all['deflated_sharpe']:.4f}   <-- the honest one")

    beat_hold = [r for r in rows if r["best"].total_return > r["bench"].total_return]
    hold_winners = sorted(rows, key=lambda r: -r["bench"].total_return)[:3]
    print(f"\n  assets where ANY bot beat simply holding : {len(beat_hold)}/{len(rows)}")
    print("  best HOLD performers (no bot, no fees):")
    for r in hold_winners:
        print(f"    {r['sym']:<12} {r['bench'].total_return:>+8.2%}")

    # THE DECISIVE TEST: did winners chosen on training data survive unseen data?
    scored = [r for r in rows if r.get("oos")]
    survivors = [r for r in scored if r["oos"].total_return > 0]
    print(f"\n  OUT-OF-SAMPLE SURVIVAL (the number that matters):")
    print(f"    winners still profitable on unseen data : {len(survivors)}/{len(scored)}")
    if scored:
        mean_oos = statistics.fmean(r["oos"].total_return for r in scored)
        print(f"    mean out-of-sample return               : {mean_oos:+.2%}")
        n, k = len(scored), len(survivors)
        p_oos = sum(math.comb(n, i) for i in range(k, n + 1)) / (2 ** n)
        print(f"    p under the null (coin flips)           : {p_oos:.3f}")
        if mean_oos <= 0:
            print("    -> The winners LOST on data they were not fitted to.")
            print("       That is the curve fit revealing itself. Definitive.")
        elif p_oos > 0.05:
            print("    -> Positive but not significant; consistent with luck.")
        else:
            print("    -> Survived unseen data at p<=0.05. Worth live paper-testing.")

    print("\n" + "=" * 78)
    if d_all["deflated_sharpe"] >= 0.95:
        print("RESULT: something survived deflation by the FULL search. That is rare.")
        print("Next step is signal_watch.py for 30+ sealed live signals -- not money.")
    else:
        print("RESULT: NO EDGE SURVIVES THE FULL SEARCH.")
        print(f"{top['sym']} looks like {top['best'].total_return:+.2%}, but it is the best of")
        print(f"{total_trials} tries. A no-edge search of that size is EXPECTED to produce a")
        print(f"winner around Sharpe {bench_ok:.2f}. This one does not clear that bar.")
    print("\nTWO BIASES THIS CANNOT FIX FOR YOU:")
    print("  1. WATCHLIST BIAS. You chose these coins today, already knowing which")
    print("     ones ran. A fair test picks the list BEFORE the period it is tested")
    print("     on. Backtests on a hindsight watchlist flatter themselves.")
    print("  2. COST REALISM. Small/meme coins have wider spreads and thinner books")
    print("     than the 40 bps modelled here. Real costs on those are often far")
    print("     worse, which eats exactly the edge a scanner claims to find.")
    if missing:
        print(f"\nUNAVAILABLE ({len(missing)}): " + ", ".join(s for s, _ in missing))
        print("  (not listed on Coinbase, or too new -- not a bug)")
    print("=" * 78)


if __name__ == "__main__":
    main()
