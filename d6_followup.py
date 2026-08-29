"""D6 follow-up: tie-class structure of the train ranking, and the corrupted-series
winner re-scored on the clean series. Same engine, same grid, same windows."""
import statistics, json
import covenant_backtest as cb
from d6_hbar_clean import (VARIANTS, BARS, WARMUP, bt, train, test, run,
                           full, tr, te, hold_full)

# tie class: variants whose train return is exactly 0.0 (never traded in train)
zero_train = [n for n, _ in VARIANTS if tr[n].total_return == 0.0 and tr[n].n_trades == 0]
pos_train  = [n for n, _ in VARIANTS if tr[n].total_return > 0.0]
zero_test_returns = [te[n].total_return for n in zero_train]
traded_test = [n for n, _ in VARIANTS if te[n].n_trades > 0]

named = ["breakout 72", "sma_cross 20/48", "sma_cross 20/72",
         "sma_cross 12/72", "sma_cross 5/30", "momentum 36", "momentum 60"]
table = {}
for n in named:
    table[n] = {
        "full_return": full[n].total_return,
        "full_maxDD": full[n].max_drawdown(),
        "full_trades": full[n].n_trades,
        "train_return": tr[n].total_return,
        "test_return": te[n].total_return,
        "test_trades": te[n].n_trades,
    }

# every-variant summary for the record
all_rows = sorted(
    ({"name": n, "full": round(full[n].total_return, 4),
      "maxDD": round(full[n].max_drawdown(), 4), "trades": full[n].n_trades,
      "train": round(tr[n].total_return, 4), "test": round(te[n].total_return, 4)}
     for n, _ in VARIANTS), key=lambda r: -r["full"])

out = {
 "train_tie_class": {
   "never_traded_in_train": len(zero_train),
   "positive_train": pos_train,
   "tie_class_test_returns_nonzero": sum(1 for r in zero_test_returns if r != 0.0),
   "tie_class_test_mean": statistics.fmean(zero_test_returns) if zero_test_returns else None,
 },
 "variants_trading_in_test": len(traded_test),
 "named_variants": table,
 "n_full_positive": sum(1 for n, _ in VARIANTS if full[n].total_return > 0),
 "hold_full_return": hold_full.total_return,
 "hold_full_maxDD": hold_full.max_drawdown(),
 "all_variants_by_full_return_top15": all_rows[:15],
 "all_variants_bottom5": all_rows[-5:],
}
print(json.dumps(out, indent=1))
