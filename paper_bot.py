#!/usr/bin/env python3
"""
paper_bot.py -- a Cryptohopper-style automated trading bot, but PAPER ONLY.

It runs a strategy over price data, "executes" trades on a simulated feed with
realistic fees and slippage, prints a live activity log like a real bot would,
and -- unlike a marketplace bot -- ends with an HONEST verdict on whether the
strategy actually has an edge or is just fitting noise.

NO exchange, NO API keys, NO real money, NO wallet. Nothing here can move a
real cent. It exists so you can see how a bot behaves and learn to tell a real
edge from an illusion before you ever risk anything.

USAGE
  python paper_bot.py                         # demo on a synthetic series
  python paper_bot.py --series trend          # a genuinely trending market
  python paper_bot.py --series noise          # a pure random walk (no edge)
  python paper_bot.py --csv myprices.csv       # your own OHLCV export
  python paper_bot.py --fast 10 --slow 40 --capital 1000
"""
from __future__ import annotations
import os, sys, argparse, math, random, statistics, json, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "quant"))
sys.path.insert(0, HERE)
from covenant_backtest import (
    Bar, Backtester, CostModel, deflated_sharpe, walk_forward, evaluate,
    EdgeMonitor, PaperTrader, load_csv,
)


def synth(kind: str, n: int = 1200, seed: int = 7):
    rng = random.Random(seed)
    drift = 0.0009 if kind == "trend" else 0.0
    vol = 0.015
    bars, px = [], 100.0
    for i in range(n):
        r = rng.gauss(drift, vol)
        o = px
        px = px * math.exp(r)
        hi = max(o, px) * (1 + abs(rng.gauss(0, vol / 4)))
        lo = min(o, px) * (1 - abs(rng.gauss(0, vol / 4)))
        bars.append(Bar(float(i), o, hi, lo, px, 1000.0))
    return bars


def fetch_coinbase(product: str = "XRP-USD", granularity: int = 86400):
    """Fetch REAL recent OHLCV candles from Coinbase's public API (no key, no
    account). Runs on YOUR machine, on YOUR network. Returns oldest-first Bars.

    Coinbase returns up to 300 candles as arrays in the order
    [time, low, high, open, close, volume], newest first.
    """
    url = (f"https://api.exchange.coinbase.com/products/{product}/candles"
           f"?granularity={granularity}")
    req = urllib.request.Request(url, headers={"User-Agent": "covenant-paperbot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            rows = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Coinbase API HTTP {e.code}: {e.reason}. "
                         f"Check the symbol (e.g. XRP-USD, BTC-USD).")
    except Exception as e:
        raise SystemExit(f"Could not reach Coinbase ({type(e).__name__}: {e}). "
                         f"Check your internet, or use --csv with a downloaded file.")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"Coinbase returned no candles for {product}.")
    rows = sorted(rows, key=lambda x: x[0])  # oldest first
    bars = []
    for t, low, high, opn, close, vol in rows:
        # guard against an occasional malformed row
        if not (low <= opn <= high and low <= close <= high):
            continue
        bars.append(Bar(float(t), float(opn), float(high), float(low),
                        float(close), float(vol)))
    if len(bars) < 60:
        raise SystemExit(f"Only {len(bars)} usable candles from Coinbase; "
                         f"not enough to test. Try a smaller --granularity.")
    return bars


def sma_cross(fast: int, slow: int):
    def strat(view, pos):
        if len(view) < slow + 1:
            return 0
        c = view.closes(slow)
        return 1 if statistics.fmean(c[-fast:]) > statistics.fmean(c) else -1
    return strat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["synthetic", "coinbase"], default="synthetic",
                    help="where prices come from (default: synthetic)")
    ap.add_argument("--symbol", default="XRP-USD", help="Coinbase product, e.g. XRP-USD, BTC-USD")
    ap.add_argument("--granularity", choices=["hour", "day"], default="day",
                    help="candle size for --source coinbase")
    ap.add_argument("--csv", default="", help="OHLCV CSV (timestamp,open,high,low,close,volume)")
    ap.add_argument("--series", choices=["trend", "noise"], default="noise",
                    help="synthetic market if no --csv/--source (default: noise)")
    ap.add_argument("--fast", type=int, default=10)
    ap.add_argument("--slow", type=int, default=40)
    ap.add_argument("--capital", type=float, default=1000.0)
    args = ap.parse_args()

    if args.csv:
        bars = load_csv(args.csv)
        src = f"your data ({args.csv}, {len(bars)} bars)"
    elif args.source == "coinbase":
        gran = 3600 if args.granularity == "hour" else 86400
        bars = fetch_coinbase(args.symbol, gran)
        src = f"LIVE Coinbase {args.symbol} {args.granularity} candles ({len(bars)} bars)"
    else:
        bars = synth(args.series)
        src = f"synthetic '{args.series}' market ({len(bars)} bars)"

    cost = CostModel(taker_fee_bps=10, spread_bps=5, slippage_bps=5, min_notional=5.0)
    strat = sma_cross(args.fast, args.slow)
    warmup = args.slow + 2

    print("=" * 66)
    print(f"PAPER BOT  |  SMA {args.fast}/{args.slow}  |  {src}")
    print(f"capital ${args.capital:,.0f}  |  round-trip cost {cost.round_trip_bps():.0f} bps  |  PAPER MONEY")
    print("=" * 66)

    # -- live-style paper run: decide on each bar, fill at the next open --
    trader = PaperTrader(cost=cost, capital=args.capital,
                         monitor=EdgeMonitor(expected_mean=0.0, expected_sd=0.02,
                                             window=30, max_consecutive_losses=15))
    from covenant_backtest import PointInTimeView
    pos, entry_px, open_idx = 0, 0.0, None
    trades = 0
    for i in range(warmup, len(bars) - 1):
        view = PointInTimeView(bars, i)
        want = strat(view, pos)
        fill = bars[i + 1].open
        if want != pos:
            if pos != 0 and open_idx is not None:
                idx = trader.seal(ts=bars[open_idx].ts, target=pos, ref_px=entry_px)
                rec = trader.settle(idx, exit_px=fill)
                trades += 1
                side = "LONG" if pos > 0 else "SHORT"
                mon = rec.get("monitor", {})
                tag = "  <<< EDGE DECAY, bot would STOP" if mon.get("killed") else ""
                print(f"  bar {i:>4}  close {side:<5} @ {fill:8.2f}  "
                      f"pnl {rec['pnl']:+8.2f}  equity {trader.equity:9.2f}{tag}")
                if mon.get("killed"):
                    print("  [BOT] kill-switch tripped -- a real bot should halt here.")
                    break
            pos = want
            if pos != 0:
                entry_px, open_idx = fill, i + 1
                print(f"  bar {i:>4}  open  {'LONG' if pos>0 else 'SHORT':<5} @ {fill:8.2f}")

    # -- backtest the same strategy for the honest guardrail verdict --
    res = Backtester(cost=cost, capital=args.capital).run(
        bars, strat, warmup=warmup, strategies_tried=1)
    d = deflated_sharpe(res)

    print("-" * 66)
    print(f"paper result: {trades} closed trades, equity ${trader.equity:,.2f} "
          f"({(trader.equity/args.capital-1):+.2%})")
    print(f"fees paid (backtest of same): ${res.total_fees():,.2f} "
          f"({res.total_fees()/args.capital:.1%} of capital)")
    print(f"raw Sharpe {res.sharpe():.2f}  ->  DEFLATED Sharpe {d['deflated_sharpe']:.3f}")
    print("-" * 66)
    if d["deflated_sharpe"] >= 0.95:
        print("VERDICT: this looks like a REAL edge (survives the deflated-Sharpe test).")
        print("         Still: paper-trade it live for weeks before risking a cent.")
    else:
        print("VERDICT: NOT distinguishable from luck. This is what a 'winning' bot")
        print("         usually is -- a curve fit to noise. On real money, the fees")
        print("         above are the only guaranteed part.")
    print("=" * 66)


if __name__ == "__main__":
    main()
