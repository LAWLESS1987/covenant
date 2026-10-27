#!/usr/bin/env python3
"""
rebalance_strategy.py -- a strategy that does NOT predict price.

WHY THIS ONE AND NOT A SIGNAL BOT
  Every timing strategy we tested collapsed out-of-sample, because predicting
  short-term price is close to impossible and the search itself manufactures
  fake winners. Rebalancing is different in kind: it has a documented
  mathematical basis (volatility harvesting / the "rebalancing bonus") and
  requires no forecast at all. You hold a fixed basket at fixed weights. When
  one asset runs up, you trim it; when one drops, you top it up. You are
  mechanically selling strength and buying weakness -- no opinion required.

  It is NOT free money and it is NOT big. The bonus is roughly
  0.5 * (average variance - portfolio variance) per period, so it grows with
  volatility and with LOW correlation, and it is eaten by fees if you rebalance
  too often. Crypto is extremely volatile (helps) but highly correlated
  (hurts). This script measures which force wins ON YOUR ACTUAL BASKET instead
  of assuming.

WHAT IT HONESTLY IS
  * a way to hold a basket with a small structural tailwind and enforced
    discipline (it makes you trim winners and add to losers automatically)
  * NOT a market-beating edge, NOT downside protection -- if the whole basket
    falls, you lose. Diversification across 16 coins that all crash together
    is not diversification.

USAGE
  python rebalance_strategy.py --symbols xlm,link,hbar,ada,doge --period 168
  python rebalance_strategy.py --band 0.25          # rebalance only on drift
"""
from __future__ import annotations
import os, sys, argparse, statistics, math, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "quant"))
sys.path.insert(0, HERE)
from paper_bot import fetch_coinbase, synth
from multi_scan import resolve


def align(series: dict):
    """Trim every asset to a common length, oldest-first, so weights are
    computed on the same bars. Mismatched history silently biases everything."""
    n = min(len(v) for v in series.values())
    return {k: v[-n:] for k, v in series.items()}, n


def run_portfolio(series: dict, n: int, mode: str, period: int, band: float,
                  fee_bps: float, capital: float):
    """Simulate a basket. mode='hold' never rebalances; mode='rebal' restores
    equal weights on schedule (period) or when any weight drifts past `band`."""
    syms = sorted(series)
    w0 = capital / len(syms)
    units = {s: w0 / series[s][0].close for s in syms}
    cash = 0.0
    equity, n_rebals, fees_paid = [], 0, 0.0

    for i in range(n):
        vals = {s: units[s] * series[s][i].close for s in syms}
        total = sum(vals.values()) + cash
        equity.append(total)
        if mode != "rebal" or total <= 0:
            continue
        due = (period > 0 and i > 0 and i % period == 0)
        drifted = False
        if band > 0:
            target = total / len(syms)
            drifted = any(abs(v - target) / target > band for v in vals.values())
        if not (due or drifted):
            continue
        # restore equal weights, paying a fee on the traded notional only
        target = total / len(syms)
        traded = sum(abs(v - target) for v in vals.values()) / 2.0
        cost = traded * fee_bps / 10_000.0
        fees_paid += cost
        total -= cost
        target = total / len(syms)
        for s in syms:
            units[s] = target / series[s][i].close
        cash = 0.0
        n_rebals += 1

    return {"equity": equity, "final": equity[-1] if equity else capital,
            "rebalances": n_rebals, "fees": fees_paid}


def stats(equity, capital):
    if len(equity) < 3:
        return {"ret": 0.0, "vol": 0.0, "mdd": 0.0}
    rets = [(equity[i] / equity[i - 1]) - 1 for i in range(1, len(equity))
            if equity[i - 1] > 0]
    peak, mdd = -1e18, 0.0
    for e in equity:
        peak = max(peak, e)
        if peak > 0:
            mdd = max(mdd, (peak - e) / peak)
    return {"ret": equity[-1] / capital - 1,
            "vol": statistics.pstdev(rets) if len(rets) > 1 else 0.0,
            "mdd": mdd}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="xlm,link,hbar,ada,doge,xrp")
    ap.add_argument("--granularity", choices=["hour", "day"], default="hour")
    ap.add_argument("--period", type=int, default=168,
                    help="rebalance every N bars (168h = weekly); 0 = band only")
    ap.add_argument("--band", type=float, default=0.0,
                    help="also rebalance if a weight drifts this fraction (e.g. 0.25)")
    ap.add_argument("--fee-bps", type=float, default=40.0,
                    help="round-trip cost on rebalanced notional (default 40bps)")
    ap.add_argument("--capital", type=float, default=1000.0)
    ap.add_argument("--synthetic", action="store_true", help="offline self-test")
    args = ap.parse_args()

    syms = [resolve(s) for s in args.symbols.split(",") if s.strip()]
    gran = 3600 if args.granularity == "hour" else 86400

    series, missing = {}, []
    for s in syms:
        try:
            series[s] = synth("noise", n=700, seed=abs(hash(s)) % 9999) if args.synthetic \
                else fetch_coinbase(s, gran)
        except Exception as e:
            missing.append(s)
            print(f"  {s}: unavailable ({str(e)[:40]})")
        if not args.synthetic:
            time.sleep(0.25)
    if len(series) < 2:
        print("Need at least 2 usable assets.")
        return

    series, n = align(series)
    print("=" * 74)
    print(f"REBALANCING TEST  |  {len(series)} assets  |  {n} bars  |  "
          f"{args.granularity} candles")
    print(f"rebalance: every {args.period} bars"
          + (f" or {args.band:.0%} drift" if args.band else "")
          + f"  |  cost {args.fee_bps:.0f} bps on traded notional")
    print("=" * 74)

    hold = run_portfolio(series, n, "hold", 0, 0, args.fee_bps, args.capital)
    reb = run_portfolio(series, n, "rebal", args.period, args.band,
                        args.fee_bps, args.capital)
    hs, rs = stats(hold["equity"], args.capital), stats(reb["equity"], args.capital)

    print(f"\n  {'':<22}{'return':>11}{'volatility':>13}{'max drawdown':>15}")
    print("  " + "-" * 59)
    print(f"  {'equal-weight HOLD':<22}{hs['ret']:>+10.2%}{hs['vol']:>12.4f}{hs['mdd']:>14.2%}")
    print(f"  {'REBALANCED':<22}{rs['ret']:>+10.2%}{rs['vol']:>12.4f}{rs['mdd']:>14.2%}")

    print(f"\n  rebalances performed : {reb['rebalances']}")
    print(f"  fees paid            : ${reb['fees']:,.2f} "
          f"({reb['fees']/args.capital:.2%} of capital)")

    edge = rs["ret"] - hs["ret"]
    print(f"  rebalancing bonus    : {edge:+.2%}  (vs simply holding the basket)")

    # single-asset comparison -- the honest "would one coin have beaten it"
    singles = {}
    for s in series:
        px = series[s]
        singles[s] = px[-1].close / px[0].close - 1
    best_single = max(singles, key=singles.get)
    print(f"\n  best single asset    : {best_single} {singles[best_single]:+.2%}")
    print(f"  worst single asset   : {min(singles, key=singles.get)} "
          f"{min(singles.values()):+.2%}")

    print("\n" + "=" * 74)
    if edge > 0 and reb["fees"] < abs(edge) * args.capital:
        print(f"RESULT: rebalancing ADDED {edge:+.2%} over holding, after fees.")
        print("That is the structural bonus doing its job -- it comes from")
        print("volatility, not from prediction, so it does not decay the way a")
        print("signal edge does. It is small. It is not a money machine.")
    else:
        print(f"RESULT: rebalancing did NOT beat holding here ({edge:+.2%}).")
        print("Most likely your basket is too correlated (crypto usually is) or")
        print("you rebalanced too often and paid it away in fees. Try a longer")
        print("--period, or a --band so you only trade on real drift.")
    print("\nWHAT THIS STRATEGY DOES NOT DO:")
    print("  * It does not protect you if the whole basket falls together.")
    print(f"    Max drawdown here was {rs['mdd']:.0%} -- that is real money.")
    print("  * It does not beat the best single asset. It never will, by design.")
    print("  * It does not predict anything. That is the point, and the reason")
    print("    it is more trustworthy than the signal bots -- not less.")
    print("=" * 74)


if __name__ == "__main__":
    main()
