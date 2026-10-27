#!/usr/bin/env python3
"""strategy_cross_sectional.py -- a DIFFERENT hypothesis, at the same bar.

WHY (asked 2026-09-04: "steadily refining crypto trading strategy... profit
while still staying green is the goal, max yield")

  strategy_validate.py searched ~800 variants of one idea: predict an asset's
  next move from its OWN past prices. SMA crossovers, mean reversion,
  breakouts, trend-filtered reversion. Nothing survived deflation,
  walk-forward and PBO together, and the honest conclusion was recorded:
  no rule, on no asset, cleared all three.

  Searching more variants of the same idea is how you find noise. This asks a
  hypothesis with a DIFFERENT MECHANISM: cross-sectional momentum. Do not ask
  "will XRP go up"; ask "of these twelve, which have been strongest, and does
  holding those beat holding all of them". It is a relative-strength claim,
  not a timing claim, it is the most replicated anomaly outside equities, and
  it is cheap to trade because a weekly or monthly rebalance turns over a
  fraction of the book.

  It is tested at exactly the bar strategy_validate.py used, and the grid size
  is carried into the deflation, because a search is a search.

WHAT IT REFUSES TO DO
  It never touches an exchange, a key, holdings.txt or trader_config.json. It
  cannot arm anything. If nothing survives it says so, which is an answer.

USE
  python strategy_cross_sectional.py
  python strategy_cross_sectional.py --out docs/results/CROSS_SECTIONAL.txt
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import csv
import glob
import itertools
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from covenant_backtest import deflated_sharpe                              # noqa: E402

DEEP = os.path.join(HERE, "realdata", "deep")

# The same costs strategy_validate.py charges: Kraken Pro's lowest tier plus
# adverse spread and slippage on both sides. A round trip is 100 bps.
FEE_BPS, SPREAD_BPS, SLIP_BPS = 40.0, 5.0, 5.0
ONE_WAY = (FEE_BPS + SPREAD_BPS + SLIP_BPS) / 10000.0

PPY = 365.0


class Result:
    """The shape deflated_sharpe() reads. Duck-typed on purpose: the statistic
    should not care who computed the returns."""

    def __init__(self, returns, strategies_tried):
        self.returns = list(returns)
        self.strategies_tried = strategies_tried

    def sharpe(self, periods_per_year=PPY):
        if len(self.returns) < 2:
            return 0.0
        sd = statistics.pstdev(self.returns)
        if sd <= 0:
            return 0.0
        return (statistics.fmean(self.returns) / sd) * math.sqrt(periods_per_year)


# ------------------------------------------------------------------- the data
def load_series():
    """{symbol: {date: close}} from the verified Kraken dailies."""
    out = {}
    for path in sorted(glob.glob(os.path.join(DEEP, "*.csv"))):
        name = os.path.basename(path)
        if "STALE" in name:
            continue
        sym = name.split("_")[0]
        rows = {}
        with open(path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    rows[r["date"]] = float(r["close"])
                except (KeyError, ValueError):
                    continue
        if len(rows) > 120:
            out[sym] = rows
    return out


def calendar(series, min_assets=6):
    """Dates where enough assets are listed to rank at all."""
    counts = {}
    for rows in series.values():
        for d in rows:
            counts[d] = counts.get(d, 0) + 1
    return sorted(d for d, n in counts.items() if n >= min_assets)


# ------------------------------------------------------------------ the rule
def run(series, dates, lookback, top_k, rebal, skip, cash_filter=False):
    """Equal-weight the top_k trailing performers, rebalanced every `rebal`
    days, ranked on the return from t-lookback-skip to t-skip.

    NO FORWARD DATA. The ranking at date index i uses closes at or before
    dates[i]; the position it implies earns the return from dates[i] to
    dates[i+1]. Costs are charged on the fraction of the book that changes.
    """
    held, rets, turn = set(), [], []
    need = lookback + skip + 1
    for i in range(need, len(dates) - 1):
        d, nxt = dates[i], dates[i + 1]
        if (i - need) % rebal == 0:
            scored = []
            for sym, rows in series.items():
                a = dates[i - skip - lookback]
                b = dates[i - skip]
                if a in rows and b in rows and rows[a] > 0:
                    scored.append((rows[b] / rows[a] - 1.0, sym))
            scored.sort(reverse=True)
            picked = scored[:top_k]
            if cash_filter:
                # DUAL MOMENTUM. Relative strength says which of these twelve
                # is strongest; it cannot say that any of them is worth owning.
                # Over this window equal-weight buy-and-hold returned -63%, so
                # a rule with no cash option is required to hold the best
                # loser. This drops any pick whose own trailing return is
                # negative, and holds nothing when none is positive.
                picked = [(r, sym) for r, sym in picked if r > 0]
            new = {sym for _r, sym in picked}
            if True:
                changed = len(new ^ held) / float(max(len(new), 1))
                turn.append(changed)
                held = new
        if not held:
            rets.append(0.0)
            continue
        day = []
        for sym in held:
            rows = series[sym]
            if d in rows and nxt in rows and rows[d] > 0:
                day.append(rows[nxt] / rows[d] - 1.0)
        r = statistics.fmean(day) if day else 0.0
        # charge the rebalance on the day it happens
        if turn and (i - need) % rebal == 0:
            r -= turn[-1] * ONE_WAY * 2.0
        rets.append(r)
    return rets


def equal_weight_hold(series, dates):
    rets = []
    for i in range(len(dates) - 1):
        d, nxt = dates[i], dates[i + 1]
        day = [rows[nxt] / rows[d] - 1.0
               for rows in series.values()
               if d in rows and nxt in rows and rows[d] > 0]
        rets.append(statistics.fmean(day) if day else 0.0)
    return rets


def grid():
    """Every variant tried. Its SIZE is carried into the deflation."""
    return [(lb, k, rb, sk, cf)
            for lb in (7, 14, 21, 30, 60, 90)
            for k in (1, 2, 3, 4)
            for rb in (7, 14, 30)
            for sk in (0, 7)
            for cf in (False, True)]


# ------------------------------------------------------------------- the tests
def total_return(rets):
    eq = 1.0
    for r in rets:
        eq *= (1.0 + r)
    return eq - 1.0


def max_drawdown(rets):
    eq, peak, worst = 1.0, 1.0, 0.0
    for r in rets:
        eq *= (1.0 + r)
        peak = max(peak, eq)
        worst = min(worst, eq / peak - 1.0)
    return worst


def binom_p(wins, n):
    """P(at least `wins` of n fair coin flips). A tally of positive folds is
    not a test without this: QUANT_README measured 4 of 5 positive folds on a
    series with no edge in it."""
    if n == 0:
        return 1.0
    tot = 0.0
    for k in range(wins, n + 1):
        tot += math.comb(n, k)
    return tot / float(2 ** n)


def walk_forward(series, dates, folds=5, embargo=0.02):
    """Pick the best variant on each training block, score it on the block
    after. The search happens INSIDE the fold, which is the whole point: a
    variant chosen on all the data and then 'validated' on part of it has
    already seen the answer."""
    n = len(dates)
    size = n // (folds + 1)
    emb = int(n * embargo)
    out = []
    for f in range(folds):
        tr_end = size * (f + 1)
        te_start = min(n - 2, tr_end + emb)
        te_end = min(n, te_start + size)
        if te_end - te_start < 20:
            continue
        train, test = dates[:tr_end], dates[te_start:te_end]
        best, best_sh = None, -9e9
        for v in grid():
            r = run(series, train, *v)
            sh = Result(r, 1).sharpe()
            if sh > best_sh:
                best, best_sh = v, sh
        te = run(series, test, *best)
        out.append({"fold": f + 1, "variant": best, "train_sharpe": best_sh,
                    "test_return": total_return(te), "test_sharpe": Result(te, 1).sharpe(),
                    "bars": len(te)})
    return out


def pbo(returns_by_variant, n_blocks=8):
    """CSCV. Split into S contiguous blocks, take every half as in-sample, and
    count how often the in-sample winner lands below the out-of-sample median.
    >= 0.5 means the selection procedure is worth nothing."""
    names = list(returns_by_variant)
    if len(names) < 2:
        return None
    n = min(len(returns_by_variant[k]) for k in names)
    if n < n_blocks * 4:
        return None
    edges = [round(i * n / n_blocks) for i in range(n_blocks + 1)]
    blocks = [list(range(edges[i], edges[i + 1])) for i in range(n_blocks)]

    def sharpe(name, idx):
        r = [returns_by_variant[name][i] for i in idx]
        if len(r) < 2:
            return 0.0
        sd = statistics.pstdev(r)
        return (statistics.fmean(r) / sd) * math.sqrt(PPY) if sd > 0 else 0.0

    worse = trials = 0
    for combo in itertools.combinations(range(n_blocks), n_blocks // 2):
        ins = [i for b in combo for i in blocks[b]]
        outs = [i for b in range(n_blocks) if b not in combo for i in blocks[b]]
        champ = max(names, key=lambda nm: sharpe(nm, ins))
        oos = sorted(sharpe(nm, outs) for nm in names)
        med = oos[len(oos) // 2]
        trials += 1
        if sharpe(champ, outs) < med:
            worse += 1
    return worse / float(trials) if trials else None


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args()

    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    series = load_series()
    dates = calendar(series)
    say("# Cross-sectional momentum: a different hypothesis, the same bar")
    say("")
    say("%d series, %d dates from %s to %s; costs %d bps one way (%d round trip)"
        % (len(series), len(dates), dates[0], dates[-1],
           FEE_BPS + SPREAD_BPS + SLIP_BPS, 2 * (FEE_BPS + SPREAD_BPS + SLIP_BPS)))
    say("assets: %s" % ", ".join(sorted(series)))
    say("")

    variants = grid()
    bench = equal_weight_hold(series, dates)
    say("benchmark, equal-weight buy and hold: total %+.2f%%  Sharpe %.2f  max drawdown %.1f%%"
        % (100 * total_return(bench), Result(bench, 1).sharpe(), 100 * max_drawdown(bench)))
    say("")

    by_variant = {}
    rows = []
    for v in variants:
        r = run(series, dates, *v)
        by_variant["lb%d k%d rb%d sk%d cf%d" % (v[0], v[1], v[2], v[3], int(v[4]))] = r
        rows.append((Result(r, len(variants)).sharpe(), v, r))
    rows.sort(reverse=True, key=lambda x: x[0])

    say("## The five best of %d variants, in sample" % len(variants))
    say("")
    say("| lookback | top k | rebalance | skip | cash filter | total | Sharpe | max DD |")
    say("|---|---|---|---|---|---|---|---|")
    for sh, v, r in rows[:5]:
        say("| %d | %d | %d | %d | %s | %+.1f%% | %.2f | %.1f%% |"
            % (v[0], v[1], v[2], v[3], "yes" if v[4] else "no",
               100 * total_return(r), sh, 100 * max_drawdown(r)))
    say("")

    best_sh, best_v, best_r = rows[0]
    d = deflated_sharpe(Result(best_r, len(variants)))
    say("## Test 1 -- deflation")
    say("")
    say("The best variant is `lb%d k%d rb%d sk%d cash=%s`, Sharpe %.2f over %d bars."
        % (best_v[0], best_v[1], best_v[2], best_v[3], best_v[4], best_sh, len(best_r)))
    say("Expected best Sharpe from %d NO-EDGE trials: %.2f. Deflated Sharpe **%.4f** (needs >= 0.95): %s"
        % (len(variants), d["expected_max_sharpe"], d["deflated_sharpe"],
           "PASS" if d["deflated_sharpe"] >= 0.95 else "FAIL"))
    say("")

    say("## Test 2 -- walk-forward, the search inside each fold")
    say("")
    wf = walk_forward(series, dates, folds=args.folds)
    say("| fold | variant chosen on train | train Sharpe | test return | test Sharpe | bars |")
    say("|---|---|---|---|---|---|")
    for f in wf:
        say("| %d | lb%d k%d rb%d sk%d cf%d | %.2f | %+.2f%% | %.2f | %d |"
            % (f["fold"], f["variant"][0], f["variant"][1], f["variant"][2], f["variant"][3],
               int(f["variant"][4]),
               f["train_sharpe"], 100 * f["test_return"], f["test_sharpe"], f["bars"]))
    wins = sum(1 for f in wf if f["test_return"] > 0)
    p = binom_p(wins, len(wf))
    say("")
    say("%d of %d folds positive, binomial p = %.3f (needs majority AND p <= 0.05): %s"
        % (wins, len(wf), p, "PASS" if (wins * 2 > len(wf) and p <= 0.05) else "FAIL"))
    if wf:
        say("mean out-of-sample return %+.2f%%" % (100 * statistics.fmean(f["test_return"] for f in wf)))
    say("")

    say("## Test 3 -- PBO by CSCV")
    say("")
    pb = pbo(by_variant)
    say("PBO = %s (needs < 0.5): %s"
        % ("n/a" if pb is None else "%.3f" % pb,
           "n/a" if pb is None else ("PASS" if pb < 0.5 else "FAIL")))
    say("")

    passed = (d["deflated_sharpe"] >= 0.95
              and wf and wins * 2 > len(wf) and p <= 0.05
              and pb is not None and pb < 0.5)
    say("## Verdict")
    say("")
    say("**%s** -- all three tests are required, and %s."
        % ("A rule survived" if passed else "Nothing survived",
           "all three passed" if passed else "at least one failed"))
    if not passed:
        say("")
        say("This is the same answer the per-asset search gave on 2026-09-03, from a")
        say("different hypothesis class. It is a result, not a failure: the money stays")
        say("where it is, and the trader stays disarmed, for a measured reason.")

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print("\nwrote %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
