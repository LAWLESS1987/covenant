#!/usr/bin/env python3
"""strategy_pairs.py -- a THIRD hypothesis class, at the same bar.

WHY (asked 2026-09-05: "need to get the trading profitable prior")

  Profit is not a feature; it is a measured property of a rule on a market.
  Two classes have been measured and neither survived: per-asset timing
  (strategy_validate.py, ~800 variants) and cross-sectional momentum
  (strategy_cross_sectional.py, 288 variants, PBO 0.986). Searching either
  harder is how you find noise. This is a different MECHANISM: relative
  value between two assets that usually move together.

  If XRP and XLM track each other, the log-price spread between them is
  roughly stationary; when it stretches, the cheap leg tends to recover
  toward the dear one. Long-only, because this account cannot short: when
  the spread says A is cheap relative to B, hold A; when B is cheap, hold B;
  in between, cash. That is a rotation, which guards.py permits within the
  day's sale proceeds, and it pays the same 100 bps a round trip.

  The grid is carried into the deflation. Sixty-six pairs times eighteen
  settings is 1,188 trials, and the expected best Sharpe from 1,188 NO-EDGE
  trials is high -- which is the point of deflating, not a reason to hide
  the number.

WHAT IT REFUSES TO DO
  It never touches an exchange, a key, holdings.txt or trader_config.json.
  It cannot arm anything. If nothing survives it says so.

USE
  python strategy_pairs.py --out docs/results/PAIRS_2026-09-05.txt
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import itertools
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from covenant_backtest import deflated_sharpe                              # noqa: E402
from strategy_cross_sectional import (Result, ONE_WAY, PPY, load_series,   # noqa: E402
                                      calendar, total_return, max_drawdown,
                                      binom_p, pbo)


def _lp(rows, d):
    v = rows.get(d)
    return math.log(v) if v and v > 0 else None


def hedge_ratio(ra, rb, dates):
    """OLS slope of log(A) on log(B) over the given dates. Fit on TRAINING
    dates only; the caller never passes a date it will later score on."""
    xs, ys = [], []
    for d in dates:
        a, b = _lp(ra, d), _lp(rb, d)
        if a is not None and b is not None:
            xs.append(b)
            ys.append(a)
    if len(xs) < 30:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def run(ra, rb, dates, beta, lookback, entry, exit_):
    """Long-only pairs rotation. Position from the z-score at dates[i] earns
    the return dates[i] -> dates[i+1]. NO FORWARD DATA: the z at i uses
    spreads at or before i, and beta was fitted on earlier dates."""
    rets, held = [], None
    spreads = []
    for i in range(len(dates) - 1):
        d, nxt = dates[i], dates[i + 1]
        a, b = _lp(ra, d), _lp(rb, d)
        if a is None or b is None:
            spreads.append(None)
            rets.append(0.0)
            continue
        spreads.append(a - beta * b)
        win = [s for s in spreads[-lookback:] if s is not None]
        if len(win) < lookback:
            rets.append(0.0)
            continue
        mu, sd = statistics.fmean(win), statistics.pstdev(win)
        z = (spreads[-1] - mu) / sd if sd > 0 else 0.0
        want = held
        if z <= -entry:
            want = "A"          # A cheap relative to B
        elif z >= entry:
            want = "B"
        elif abs(z) <= exit_:
            want = None
        cost = ONE_WAY * (2.0 if (want != held and want is not None and held is not None)
                          else 1.0 if want != held else 0.0)
        held = want
        if held is None:
            rets.append(-cost)
            continue
        rows = ra if held == "A" else rb
        if d in rows and nxt in rows and rows[d] > 0:
            rets.append(rows[nxt] / rows[d] - 1.0 - cost)
        else:
            rets.append(-cost)
    return rets


def settings():
    return [(lb, en, ex) for lb in (20, 40, 60) for en in (1.0, 1.5, 2.0) for ex in (0.25, 0.5)]


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
    dates = calendar(series, min_assets=2)
    syms = sorted(series)
    pairs = list(itertools.combinations(syms, 2))
    grid = [(p, s) for p in pairs for s in settings()]
    say("# Pairs relative value: a third hypothesis, the same bar")
    say("")
    say("%d series, %d dates %s -> %s; %d pairs x %d settings = %d variants; costs %d bps one way"
        % (len(syms), len(dates), dates[0], dates[-1], len(pairs), len(settings()), len(grid), ONE_WAY * 10000))
    say("")

    # ---- in-sample: beta fitted on the first 40% of dates, rule scored after
    cut = int(len(dates) * 0.4)
    fit_dates, score_dates = dates[:cut], dates[cut:]
    rows = []
    by_variant = {}
    for (a, b), (lb, en, ex) in grid:
        beta = hedge_ratio(series[a], series[b], fit_dates)
        if beta is None:
            continue
        r = run(series[a], series[b], score_dates, beta, lb, en, ex)
        name = "%s/%s lb%d e%.2f x%.2f" % (a, b, lb, en, ex)
        by_variant[name] = r
        rows.append((Result(r, len(grid)).sharpe(), name, r))
    rows.sort(reverse=True, key=lambda x: x[0])
    say("## The five best of %d variants, beta fitted on the first 40%% and scored on the rest" % len(rows))
    say("")
    say("| variant | total | Sharpe | max DD |")
    say("|---|---|---|---|")
    for sh, name, r in rows[:5]:
        say("| %s | %+.1f%% | %.2f | %.1f%% |" % (name, 100 * total_return(r), sh, 100 * max_drawdown(r)))
    say("")

    best_sh, best_name, best_r = rows[0]
    d = deflated_sharpe(Result(best_r, len(grid)))
    say("## Test 1 -- deflation")
    say("")
    say("Best: `%s`, Sharpe %.2f over %d bars. Expected best from %d NO-EDGE trials: %.2f. "
        "Deflated Sharpe **%.4f** (needs >= 0.95): %s"
        % (best_name, best_sh, len(best_r), len(grid), d["expected_max_sharpe"], d["deflated_sharpe"],
           "PASS" if d["deflated_sharpe"] >= 0.95 else "FAIL"))
    say("")

    # ---- walk-forward: the whole search (pair + setting + beta) inside each fold
    say("## Test 2 -- walk-forward, the search inside each fold")
    say("")
    n = len(dates)
    size = n // (args.folds + 1)
    emb = int(n * 0.02)
    wf = []
    for f in range(args.folds):
        tr_end = size * (f + 1)
        te_s = min(n - 2, tr_end + emb)
        te_e = min(n, te_s + size)
        if te_e - te_s < 20:
            continue
        train, test = dates[:tr_end], dates[te_s:te_e]
        fcut = int(len(train) * 0.5)
        best, best_v = -9e9, None
        for (a, b), (lb, en, ex) in grid:
            beta = hedge_ratio(series[a], series[b], train[:fcut])
            if beta is None:
                continue
            sh = Result(run(series[a], series[b], train[fcut:], beta, lb, en, ex), 1).sharpe()
            if sh > best:
                best, best_v = sh, ((a, b), (lb, en, ex), beta)
        if best_v is None:
            continue
        (a, b), (lb, en, ex), beta = best_v
        te = run(series[a], series[b], test, beta, lb, en, ex)
        wf.append({"fold": f + 1, "name": "%s/%s lb%d e%.2f x%.2f" % (a, b, lb, en, ex),
                   "train": best, "ret": total_return(te), "sh": Result(te, 1).sharpe(), "bars": len(te)})
    say("| fold | chosen on train | train Sharpe | test return | test Sharpe | bars |")
    say("|---|---|---|---|---|---|")
    for w in wf:
        say("| %d | %s | %.2f | %+.2f%% | %.2f | %d |" % (w["fold"], w["name"], w["train"], 100 * w["ret"], w["sh"], w["bars"]))
    wins = sum(1 for w in wf if w["ret"] > 0)
    p = binom_p(wins, len(wf))
    say("")
    say("%d of %d folds positive, binomial p = %.3f (needs majority AND p <= 0.05): %s"
        % (wins, len(wf), p, "PASS" if (wf and wins * 2 > len(wf) and p <= 0.05) else "FAIL"))
    if wf:
        say("mean out-of-sample return %+.2f%%" % (100 * statistics.fmean(w["ret"] for w in wf)))
    say("")

    say("## Test 3 -- PBO by CSCV")
    say("")
    pb = pbo(by_variant)
    say("PBO = %s (needs < 0.5): %s" % ("n/a" if pb is None else "%.3f" % pb,
                                        "n/a" if pb is None else ("PASS" if pb < 0.5 else "FAIL")))
    say("")
    passed = (d["deflated_sharpe"] >= 0.95 and wf and wins * 2 > len(wf) and p <= 0.05 and pb is not None and pb < 0.5)
    say("## Verdict")
    say("")
    say("**%s** -- all three tests are required, and %s." % ("A rule survived" if passed else "Nothing survived",
                                                           "all three passed" if passed else "at least one failed"))
    if not passed:
        say("")
        say("Third hypothesis class, same answer. The trader stays disarmed for a measured reason.")
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print("\nwrote %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
