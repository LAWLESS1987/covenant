"""D6: re-do the HBAR analysis of REAL_DATA_FINDINGS.md on the CLEAN series.

Original HBAR findings were computed on the corrupted series that silently
ended 2026-06-10 (70 days stale, see PRICE_DATA_INTEGRITY.md). This re-runs the
same test battery on realdata/deep/HBAR_2025Jul_2026Aug.csv — 408 verified
Kraken bars 2025-07-10 -> 2026-08-21, rebuilt this run directly from
api.kraken.com and byte-identical to the project artifact
(sha256 42c2894efb2c1298224c111c72ba05872bb7a8963292471b2df9a7ec721d99a6).

METHOD, pinned so a future run can check rather than repeat (M40):
- engine: covenant_backtest.py (project copy, sha256
  176c9bf454af963e8d84da049bf4377087d2df408fc4e2e75d6924a1ac970007),
  default CostModel (10 bps taker, 5 spread, 5 slippage), capital 12,
  warmup 74 (the original run's warmup: slowest lookback 72 + margin).
- variants: 53, long-only, fully enumerated below (the original run's exact
  53-variant list was never preserved — REAL_DATA_FINDINGS.md names only five
  of them; all five are in this grid). Signals computed on bar t fill at open
  of t+1 (engine rule).
- holdout: 70/30 by bars (train 286 / test 122), winner and top-10 chosen on
  train only. Same design as the original (349 bars could not support
  walk-forward folds at warmup 74; 408 still cannot: (4+1)*(74+30)=520 > 408).
- p under the null: the null is "train rank carries no information about test
  performance". Resample 10 of the 53 variants uniformly at random 100,000
  times; p = fraction of draws whose mean test return >= the observed
  top-10-by-train mean. Two seeds.
- deflated Sharpe: Bailey & Lopez de Prado via covenant_backtest.deflated_sharpe
  on the best-by-train variant's FULL-period result, trials=53.
"""
import statistics, random, json
import covenant_backtest as cb

BARS = cb.load_csv("HBAR_rebuilt.csv")
WARMUP = 74
CAPITAL = 12.0

# ---- the 53 variants -------------------------------------------------------
def breakout(n):
    def strat(view, pos):
        closes = view.closes(n + 1)
        if len(closes) < n + 1:
            return pos
        now, prior = closes[-1], closes[:-1]
        if now > max(prior):
            return 1
        if now < min(prior):
            return 0
        return pos
    return strat

def sma_cross(f, s):
    def strat(view, pos):
        closes = view.closes(s)
        if len(closes) < s:
            return pos
        fast = statistics.fmean(closes[-f:])
        slow = statistics.fmean(closes)
        return 1 if fast > slow else 0
    return strat

def momentum(n):
    def strat(view, pos):
        closes = view.closes(n + 1)
        if len(closes) < n + 1:
            return pos
        return 1 if closes[-1] > closes[0] else 0
    return strat

VARIANTS = []
for n in (10, 15, 20, 24, 30, 36, 48, 60, 72, 96):
    VARIANTS.append((f"breakout {n}", breakout(n)))
for s in (20, 30, 48, 72, 96):
    for f in (5, 8, 10, 12, 15, 20, 25, 30):
        if f <= s // 2:
            VARIANTS.append((f"sma_cross {f}/{s}", sma_cross(f, s)))
for n in (10, 15, 20, 24, 30, 36, 48, 60, 72, 96, 120, 144, 168):
    VARIANTS.append((f"momentum {n}", momentum(n)))
assert len(VARIANTS) == 53, len(VARIANTS)
NAMED = {"breakout 72", "sma_cross 20/72", "sma_cross 12/72", "sma_cross 5/30",
         "sma_cross 20/48"}
assert NAMED <= {n for n, _ in VARIANTS}

hold = lambda view, pos: 1

# ---- runs -------------------------------------------------------------------
bt = cb.Backtester(capital=CAPITAL)
split = int(len(BARS) * 0.7)          # 285 -> train 285 bars, test 123
train, test = BARS[:split], BARS[split:]

def run(bars, strat, label, tried=1):
    return bt.run(bars, strat, warmup=WARMUP, label=label, strategies_tried=tried)

full = {name: run(BARS, s, name, tried=53) for name, s in VARIANTS}
tr   = {name: run(train, s, name) for name, s in VARIANTS}
te   = {name: run(test, s, name) for name, s in VARIANTS}
hold_full, hold_test = run(BARS, hold, "hold"), run(test, hold, "hold")

rank_train = sorted(tr, key=lambda n: tr[n].total_return, reverse=True)
top10 = rank_train[:10]
top10_test = [te[n].total_return for n in top10]
obs_mean = statistics.fmean(top10_test)
all_test = [te[n].total_return for n, _ in VARIANTS]

def null_p(seed, draws=100_000):
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        if statistics.fmean(rng.sample(all_test, 10)) >= obs_mean:
            hits += 1
    return hits / draws

best_full = max(full, key=lambda n: full[n].total_return)
best_train = rank_train[0]
dsr = cb.deflated_sharpe(full[best_train])

out = {
    "bars": len(BARS),
    "window": "2025-07-10 -> 2026-08-21",
    "split": {"train_bars": len(train), "test_bars": len(test),
              "train_window": "2025-07-10 -> " + str(int(train[-1].ts)),
              "test_start_ts": int(test[0].ts)},
    "buy_and_hold": {"full_return": hold_full.total_return,
                     "full_maxDD": hold_full.max_drawdown(),
                     "test_return": hold_test.total_return},
    "best_full_period": {"name": best_full,
                         "return": full[best_full].total_return,
                         "maxDD": full[best_full].max_drawdown(),
                         "trades": full[best_full].n_trades},
    "best_by_train": {"name": best_train,
                      "train_return": tr[best_train].total_return,
                      "test_return": te[best_train].total_return,
                      "test_trades": te[best_train].n_trades,
                      "full_return": full[best_train].total_return,
                      "full_maxDD": full[best_train].max_drawdown(),
                      "deflated_sharpe": dsr},
    "top10_by_train": [
        {"name": n, "train": tr[n].total_return, "test": te[n].total_return,
         "test_trades": te[n].n_trades} for n in top10],
    "top10_test_mean": obs_mean,
    "top10_profitable_oos": sum(1 for r in top10_test if r > 0),
    "null_p_seed1": null_p(1),
    "null_p_seed2": null_p(2),
    "dd_reduction_best_full": (hold_full.max_drawdown()
                               / full[best_full].max_drawdown()
                               if full[best_full].max_drawdown() > 0 else None),
    "dd_reduction_best_train": (hold_full.max_drawdown()
                                / full[best_train].max_drawdown()
                                if full[best_train].max_drawdown() > 0 else None),
}
print(json.dumps(out, indent=1, default=str))
