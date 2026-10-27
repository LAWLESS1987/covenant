#!/usr/bin/env python3
"""Does a confirmation band around the 200d line rescue the regime rule?

ANSWER, measured 2026-09-17: NO. See docs/STRATEGY_HYSTERESIS_2026-09-17.md.

HYPOTHESIS, generated from ops/rule5_backfill_ledger.jsonl (134 settled
outcomes): the rule loses because it flips on a single daily close across the
200-day line. 118 of 134 round trips lasted <= 30 days on a 200-day signal and
lost; the 16 that lasted longer made +16.2% after costs.

That slice is LOOKAHEAD-BIASED -- holding period is not knowable at entry. The
causal form of the same idea is a hysteresis band: only flip when the close is
more than k% past the line. That is decidable at entry.

CONTROLS, because a rule that improves on everything has found nothing:
  1. a random-walk control per symbol (same length, same daily vol, no signal)
  2. a walk-forward split: choose k on the first half, score on the second

Costs: 130 bps round trip, the same figure the ledger uses.
"""
import csv
import glob
import math
import os
import random
import zlib
import statistics as st

COST = 130 / 10_000.0
WIN = 200
DATA = os.path.join("private", "data")


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [(r["date"], float(r["close"])) for r in rows if r.get("close")]


def sma(closes, w=WIN):
    out = [None] * len(closes)
    run = 0.0
    for i, c in enumerate(closes):
        run += c
        if i >= w:
            run -= closes[i - w]
        if i >= w - 1:
            out[i] = run / w
    return out


def run_rule(closes, k, skip_first=True):
    """Settle-on-flip with a k% confirmation band. Returns list of net returns.

    skip_first drops the initialisation call, which no flip generated.
    """
    ma = sma(closes)
    regime = None
    entry = None
    rets = []
    for i, c in enumerate(closes):
        m = ma[i]
        if m is None:
            continue
        if c > m * (1 + k):
            new = "UP"
        elif c < m * (1 - k):
            new = "DOWN"
        else:
            new = regime           # inside the band: the call stands
        if new is None:
            continue
        if regime is None:
            regime, entry = new, c
            continue
        if new != regime:
            side = 1 if regime == "UP" else -1
            rets.append(side * (c - entry) / entry - COST)
            regime, entry = new, c
    if skip_first and rets:
        rets = rets[1:]
    return rets


def stats(rets):
    if not rets:
        return (0, 0.0, 0.0, 0.0)
    n = len(rets)
    m = st.mean(rets)
    sd = st.pstdev(rets) if n > 1 else 0.0
    t = m / (sd / math.sqrt(n)) if sd else 0.0
    win = sum(1 for x in rets if x > 0) / n
    return (n, 100 * m, 100 * win, t)


def randomwalk(closes, seed):
    rnd = random.Random(seed)
    rel = [closes[i] / closes[i - 1] for i in range(1, len(closes))]
    lr = [math.log(x) for x in rel if x > 0]
    mu, sd = st.mean(lr), st.pstdev(lr)
    out = [closes[0]]
    for _ in range(len(closes) - 1):
        out.append(out[-1] * math.exp(rnd.gauss(mu, sd)))
    return out


def main():
    files = sorted(glob.glob(os.path.join(DATA, "*_daily.csv")))
    series = {}
    for f in files:
        sym = os.path.basename(f).replace("_daily.csv", "")
        cl = [c for _, c in load(f)]
        if len(cl) > WIN + 30:
            series[sym] = cl
    print("symbols with enough history: %d of %d\n" % (len(series), len(files)))

    bands = [0.0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10]

    print("=== FULL SAMPLE (in-sample -- read with suspicion) ===")
    print("%-6s %6s %10s %8s %8s   %s" % ("band", "n", "mean%", "win%", "t", "random-walk control"))
    for k in bands:
        real, ctrl = [], []
        for sym, cl in series.items():
            real += run_rule(cl, k)
            for s in range(3):
                ctrl += run_rule(randomwalk(cl, zlib.crc32((sym + ':' + str(s)).encode())), k)
        n, m, w, t = stats(real)
        cn, cm, cw, ct = stats(ctrl)
        print("%-6s %6d %+10.3f %8.1f %+8.2f   n=%d mean %+.3f%% t %+.2f"
              % ("%.0f%%" % (100*k), n, m, w, t, cn, cm, ct))

    print("\n=== WALK-FORWARD: band chosen on first half, scored on second ===")
    firsts, seconds = {}, {}
    for sym, cl in series.items():
        cut = len(cl) // 2
        firsts[sym] = cl[:cut + WIN] if cut + WIN <= len(cl) else cl[:cut]
        seconds[sym] = cl[cut:]
    best_k, best_m = None, -9e9
    for k in bands:
        r = []
        for sym, cl in firsts.items():
            r += run_rule(cl, k)
        n, m, w, t = stats(r)
        print("  train band %-5s n=%3d mean %+7.3f%% win %5.1f%%" % ("%.0f%%" % (100*k), n, m, w))
        if n >= 10 and m > best_m:
            best_k, best_m = k, m
    print("  -> chosen band: %s" % ("%.0f%%" % (100 * best_k) if best_k is not None else "none"))
    if best_k is not None:
        r = []
        for sym, cl in seconds.items():
            r += run_rule(cl, best_k)
        n, m, w, t = stats(r)
        print("  TEST (held out): n=%d  mean %+.3f%%  win %.1f%%  t %+.2f" % (n, m, w, t))
        base = []
        for sym, cl in seconds.items():
            base += run_rule(cl, 0.0)
        bn, bm, bw, bt = stats(base)
        print("  TEST baseline (no band): n=%d  mean %+.3f%%  win %.1f%%  t %+.2f"
              % (bn, bm, bw, bt))


if __name__ == "__main__":
    main()
