#!/usr/bin/env python3
"""
signal_watch.py -- live signal watcher with PHONE CONFIRMATION and an honest
track record.

WHAT IT DOES
  * pulls live real prices (Coinbase public API, no key, no account)
  * runs your strategy on them
  * when the signal CHANGES, pushes an alert to your phone with the reasoning
  * SEALS the prediction before the outcome is known, and scores it later
  * builds a track record file so you learn whether this actually works

WHAT IT DELIBERATELY DOES NOT DO
  It holds no API keys and places no orders. It tells you what it would do;
  YOU decide and place the order yourself in your exchange's own app. That is
  not a missing feature -- if you are confirming every trade on your phone
  anyway, you are already holding the phone. Keeping execution out means a bug,
  a bad signal, or a stolen file can never move your money. The value here is
  the signal and the discipline, not the order plumbing.

  Run it for weeks and read the track record BEFORE any real money is involved.
  If the win rate and deflated Sharpe do not hold up on sealed live predictions,
  that is the answer -- and it cost you nothing to learn.

PHONE SETUP (free, no account)
  1. install the "ntfy" app (iOS/Android)
  2. subscribe to a private topic name you invent, e.g. covenant-lawre-8f3k2
     (anyone who knows the topic can read it -- make it random, not "xrp")
  3. run with:  --topic covenant-lawre-8f3k2

USAGE
  python signal_watch.py --symbol XRP-USD --topic covenant-lawre-8f3k2
  python signal_watch.py --symbol XRP-USD --topic mytopic --interval 900
  python signal_watch.py --once                 # single check, no loop
  python signal_watch.py --record               # print the track record and exit
"""
from __future__ import annotations
import os, sys, json, time, math, argparse, statistics, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "quant"))
sys.path.insert(0, HERE)
from covenant_backtest import (
    Bar, PointInTimeView, CostModel, Backtester, deflated_sharpe,
)
from paper_bot import fetch_coinbase, sma_cross

STATE = os.path.join(HERE, "signal_state.json")
RECORD = os.path.join(HERE, "signal_record.jsonl")


def push(topic: str, title: str, body: str, priority: str = "default") -> bool:
    """Send to your phone via ntfy.sh. Returns False if it could not deliver --
    never silently pretends it did."""
    if not topic:
        return False
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
        headers={"Title": title, "Priority": priority, "Tags": "chart_with_upwards_trend"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  [push failed: {type(e).__name__}: {e}]")
        return False


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def save_state(s):
    json.dump(s, open(STATE, "w"), indent=2)


def append_record(row):
    with open(RECORD, "a") as f:
        f.write(json.dumps(row) + "\n")


def read_records():
    out = []
    if os.path.exists(RECORD):
        for line in open(RECORD):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def show_record(capital: float, cost: CostModel):
    rows = read_records()
    settled = [r for r in rows if r.get("settled")]
    print("=" * 68)
    print(f"TRACK RECORD -- {len(rows)} sealed signals, {len(settled)} settled")
    print("=" * 68)
    if not settled:
        print("  Nothing settled yet. Each signal settles when the NEXT one fires.")
        print("  This is the honest part: predictions are sealed before the")
        print("  outcome exists, so the score cannot be rewritten after the fact.")
        return
    rets = [r["ret_after_costs"] for r in settled]
    wins = sum(1 for r in rets if r > 0)
    eq = capital
    for r in rets:
        eq *= (1 + r)
    print(f"  win rate      : {wins}/{len(rets)} ({wins/len(rets):.0%})")
    print(f"  mean return   : {statistics.fmean(rets):+.3%} per closed signal (after costs)")
    print(f"  paper equity  : ${capital:,.2f} -> ${eq:,.2f} ({eq/capital-1:+.2%})")
    print(f"  round-trip cost assumed: {cost.round_trip_bps():.0f} bps")
    # SIGNIFICANCE, not just a tally. A win rate is a score, not evidence.
    # Under the null (no edge) each signal is ~a coin flip, so ask how often
    # pure luck produces a run this good. Same correction this project applied
    # to walk-forward, where 4/5 positive folds looked convincing at p=0.188.
    n = len(rets)
    p_val = sum(math.comb(n, k) for k in range(wins, n + 1)) / (2 ** n)
    sd = statistics.pstdev(rets)
    sharpe = (statistics.fmean(rets) / sd * (n ** 0.5)) if sd else 0.0
    print(f"  crude Sharpe  : {sharpe:.2f} over {n} signals")
    print(f"  p-value       : {p_val:.3f}  (chance of a run this good with NO edge)")

    if statistics.fmean(rets) <= 0:
        print("\n  VERDICT: mean return is <= 0 after costs. On real money this")
        print("  strategy loses. That is a real finding, and it cost you nothing.")
    elif n < 30:
        print(f"\n  VERDICT: NOT EVIDENCE YET. {wins}/{n} looks good, but {n} signals")
        print("  cannot tell skill from luck -- you would need 30+ before the")
        print("  number means anything, and p<=0.05 before it means an edge.")
    elif p_val > 0.05:
        print(f"\n  VERDICT: NOT DISTINGUISHABLE FROM LUCK (p={p_val:.3f}). A no-edge")
        print("  coin-flipper produces a run this good more than 1 time in 20.")
        print("  This is what most 'winning' bots actually are.")
    else:
        print(f"\n  VERDICT: survives the significance test (p={p_val:.3f}) over {n}")
        print("  sealed live signals. That is the strongest evidence this tool can")
        print("  give -- and it is still not a promise about the future. Edges decay.")
    print("=" * 68)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XRP-USD")
    ap.add_argument("--granularity", choices=["hour", "day"], default="hour")
    ap.add_argument("--fast", type=int, default=12)
    ap.add_argument("--slow", type=int, default=48)
    ap.add_argument("--capital", type=float, default=1000.0)
    ap.add_argument("--topic", default=os.environ.get("NTFY_TOPIC", ""),
                    help="your private ntfy topic for phone alerts")
    ap.add_argument("--interval", type=int, default=900, help="seconds between checks")
    ap.add_argument("--once", action="store_true", help="check once and exit")
    ap.add_argument("--record", action="store_true", help="print track record and exit")
    ap.add_argument("--test-push", action="store_true", help="send a test alert and exit")
    args = ap.parse_args()

    cost = CostModel(taker_fee_bps=10, spread_bps=5, slippage_bps=5, min_notional=5.0)

    if args.record:
        show_record(args.capital, cost)
        return

    if args.test_push:
        ok = push(args.topic, "Covenant test",
                  "If you can read this on your phone, alerts are working.")
        print("test push:", "DELIVERED" if ok else "FAILED (check the topic / your network)")
        return

    if not args.topic:
        print("No --topic set, so alerts will only print here. Add --topic <name>")
        print("and subscribe to that name in the ntfy phone app to get them on your phone.\n")

    strat = sma_cross(args.fast, args.slow)

    def check():
        bars = fetch_coinbase(args.symbol, 3600 if args.granularity == "hour" else 86400)
        i = len(bars) - 1
        view = PointInTimeView(bars, i)
        sig = strat(view, 0)                    # -1 short, 0 flat, +1 long
        px = bars[i].close
        st = load_state()
        key = f"{args.symbol}:{args.fast}:{args.slow}:{args.granularity}"
        prev = st.get(key, {})
        prev_sig = prev.get("signal")
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(bars[i].ts))

        if prev_sig is None:
            st[key] = {"signal": sig, "px": px, "ts": bars[i].ts}
            save_state(st)
            print(f"[{stamp}] {args.symbol} {px:.4f} -- baseline set, signal="
                  f"{'LONG' if sig>0 else 'SHORT' if sig<0 else 'FLAT'} (no alert)")
            return

        if sig == prev_sig:
            print(f"[{stamp}] {args.symbol} {px:.4f} -- no change "
                  f"({'LONG' if sig>0 else 'SHORT' if sig<0 else 'FLAT'})")
            return

        # SIGNAL CHANGED -> settle the previous sealed prediction honestly
        entry = float(prev.get("px", px))
        side = int(prev_sig)
        gross = side * (px - entry) / entry if entry else 0.0
        ret = gross - cost.round_trip_bps() / 10_000.0
        append_record({
            "symbol": args.symbol, "sealed_at": prev.get("ts"), "settled_at": bars[i].ts,
            "side": side, "entry": entry, "exit": px,
            "ret_gross": gross, "ret_after_costs": ret, "settled": True,
        })

        st[key] = {"signal": sig, "px": px, "ts": bars[i].ts}
        save_state(st)

        name = "LONG" if sig > 0 else "SHORT" if sig < 0 else "FLAT"
        prevname = "LONG" if side > 0 else "SHORT" if side < 0 else "FLAT"
        title = f"{args.symbol}: {name} signal"
        body = (
            f"{args.symbol} @ {px:.4f}\n"
            f"signal: {prevname} -> {name}  (SMA {args.fast}/{args.slow}, {args.granularity})\n\n"
            f"previous {prevname} closed: {ret:+.2%} after costs\n\n"
            f"THIS IS A SUGGESTION, NOT AN ORDER.\n"
            f"Nothing has been traded. If you agree, place it yourself in your\n"
            f"exchange app. If you do not, do nothing -- the track record still\n"
            f"scores it, so you learn either way."
        )
        print(f"\n[{stamp}] *** SIGNAL CHANGE: {prevname} -> {name} @ {px:.4f} ***")
        print(f"    previous {prevname} closed {ret:+.2%} after costs")
        delivered = push(args.topic, title, body, priority="high")
        print(f"    phone alert: {'sent' if delivered else 'NOT sent'}")
        print(f"    (nothing traded -- you decide and place it yourself)\n")

    if args.once:
        check()
        return

    print(f"watching {args.symbol} ({args.granularity} candles, SMA {args.fast}/{args.slow}) "
          f"every {args.interval}s")
    print("nothing will ever be traded automatically. Ctrl+C to stop.\n")
    while True:
        try:
            check()
        except SystemExit as e:
            print(f"  data error: {e}")
        except Exception as e:
            print(f"  error: {type(e).__name__}: {e}")
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    main()
