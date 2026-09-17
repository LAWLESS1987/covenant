#!/usr/bin/env python3
"""Short-only 200d regime rule: does it beat simply being short the whole time?

WHY THIS ONE. The operator, 2026-09-17: "Some short trading is fine if it covers
fees." The backfill ledger agrees on its face -- 66 shorts, +0.583% mean AFTER
the 130 bps round trip, against 68 longs at -8.185%.

THE CONFOUND THAT DECIDES IT. Equal-weight buy-and-hold over this window is
about -63%. In a market that falls that hard, ANY short wins. So "shorts made
money" is not a finding. The only question that matters:

    does the rule's shorting beat being short the whole time?

If it does not, the rule is charging 130 bps a round trip for drift that costs
nothing to hold. That is the benchmark this script scores against, and it is the
only one that can tell an edge from a direction.

Stupidly simple on purpose: one rule, one benchmark, one walk-forward split.
"""
import csv
import glob
import math
import os
import statistics as st

COST = 130 / 10_000.0
WIN = 200
DATA = os.path.join("private", "data")


def closes(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [float(r["close"]) for r in csv.DictReader(fh) if r.get("close")]


def sma(c, w=WIN):
    out, run = [None] * len(c), 0.0
    for i, x in enumerate(c):
        run += x
        if i >= w:
            run -= c[i - w]
        if i >= w - 1:
            out[i] = run / w
    return out


def short_only(c):
    """Short while close < 200d line. Flat otherwise. Returns net per trade."""
    ma = sma(c)
    entry = None
    rets = []
    for i, x in enumerate(c):
        m = ma[i]
        if m is None:
            continue
        if entry is None and x < m:
            entry = x
        elif entry is not None and x > m:
            rets.append(-(x - entry) / entry - COST)
            entry = None
    return rets


def always_short(c):
    """The benchmark: short from the first day the line exists to the last."""
    ma = sma(c)
    idx = [i for i, m in enumerate(ma) if m is not None]
    if len(idx) < 2:
        return None
    a, b = c[idx[0]], c[idx[-1]]
    return -(b - a) / a - COST          # one round trip, not many


def days_short(c):
    ma = sma(c)
    live = [i for i, m in enumerate(ma) if m is not None]
    if not live:
        return 0.0
    n = sum(1 for i in live if c[i] < ma[i])
    return n / len(live)


def score(rets):
    if not rets:
        return (0, 0.0, 0.0, 0.0)
    n, m = len(rets), st.mean(rets)
    sd = st.pstdev(rets) if n > 1 else 0.0
    t = m / (sd / math.sqrt(n)) if sd else 0.0
    return (n, 100 * m, 100 * sum(1 for x in rets if x > 0) / n, t)


def total(rets):
    """Compounded, because 40 trades at +0.5% is not the same as one at +0.5%."""
    eq = 1.0
    for r in rets:
        eq *= (1 + r)
    return 100 * (eq - 1)


def report(label, series):
    rule, bench, exposure = [], [], []
    per = []
    for sym, c in series.items():
        r = short_only(c)
        b = always_short(c)
        if b is None:
            continue
        rule += r
        bench.append(b)
        exposure.append(days_short(c))
        per.append((sym, total(r), 100 * b))
    n, m, w, t = score(rule)
    print("  %s" % label)
    print("    rule   : n=%3d  mean %+6.3f%%  win %5.1f%%  t %+5.2f  compounded %+8.2f%%"
          % (n, m, w, t, total(rule)))
    print("    always : n=%3d  mean %+6.3f%%  %28s compounded %+8.2f%%"
          % (len(bench), st.mean(bench) * 100, "", total(bench)))
    print("    rule is short %.0f%% of days -- it forgoes %.0f%% of the fall by being flat"
          % (100 * st.mean(exposure), 100 * (1 - st.mean(exposure))))
    beat = sum(1 for s, rt, bt in per if rt > bt)
    print("    beats always-short on %d of %d symbols" % (beat, len(per)))
    return per


def main():
    series = {}
    for f in sorted(glob.glob(os.path.join(DATA, "*_daily.csv"))):
        c = closes(f)
        if len(c) > WIN + 30:
            series[os.path.basename(f).replace("_daily.csv", "")] = c
    print("symbols: %d\n" % len(series))

    print("=== FULL SAMPLE ===")
    per = report("all history", series)

    print("\n=== WALK-FORWARD: second half only, never seen when the idea was formed ===")
    second = {s: c[len(c) // 2:] for s, c in series.items()}
    second = {s: c for s, c in second.items() if len(c) > WIN + 10}
    if second:
        report("held out", second)
    else:
        print("  UNDETERMINED: no symbol has 200+30 bars in its second half")

    print("\n=== per symbol, full sample (compounded) ===")
    print("  %-8s %10s %10s  %s" % ("sym", "rule", "always", "verdict"))
    for sym, rt, bt in sorted(per, key=lambda x: -(x[1] - x[2])):
        print("  %-8s %+9.2f%% %+9.2f%%  %s"
              % (sym, rt, bt, "rule" if rt > bt else "always-short"))


if __name__ == "__main__":
    main()
