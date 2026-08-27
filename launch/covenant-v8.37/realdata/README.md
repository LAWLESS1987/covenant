# realdata/ -- which price files to trust

**Use `realdata/deep/` for everything.** Twelve Kraken daily series,
2025-01-01 -> 2026-08-21 (or the pair's listing date), each verified for
86 400 s contiguity, no duplicate timestamps, OHLC sanity and 00:00 UTC
alignment, with two interior windows independently re-fetched and diffed
byte-for-byte. sha256 of every file is recorded in `claude/IMPROVEMENT_LOG.md`
under D1.

| file | bars | window |
|---|---|---|
| XLM_2025_2026Aug.csv  | 598 | 2025-01-01 -> 2026-08-21 |
| SOL_2025_2026Aug.csv  | 598 | 2025-01-01 -> 2026-08-21 |
| XRP_2025_2026Aug.csv  | 598 | 2025-01-01 -> 2026-08-21 |
| ADA_2025_2026Aug.csv  | 598 | 2025-01-01 -> 2026-08-21 |
| ATOM_2025_2026Aug.csv | 598 | 2025-01-01 -> 2026-08-21 |
| AVAX_2025_2026Aug.csv | 598 | 2025-01-01 -> 2026-08-21 |
| NEAR_2025_2026Aug.csv | 598 | 2025-01-01 -> 2026-08-21 |
| ONDO_2025_2026Aug.csv | 598 | 2025-01-01 -> 2026-08-21 |
| PEPE_2025_2026Aug.csv | 598 | 2025-01-01 -> 2026-08-21 |
| CRO_2025_2026Aug.csv  | 570 | 2025-01-29 (listing) -> 2026-08-21 |
| HBAR_2025Jul_2026Aug.csv | 408 | 2025-07-10 (listing) -> 2026-08-21 |
| WLFI_2025Sep_2026Aug.csv | 355 | 2025-09-01 (listing) -> 2026-08-21 |

## SUPERSEDED -- do not run a backtest on these

Everything directly in `realdata/` is older, shorter, or wrong. Kept only so
that a result quoted from them can be traced back.

- `*_c.csv` (ADA, CRO, HBAR, ONDO, PEPE, SOL, WLFI, XLM) -- the ~220-bar
  series. After the 200-day warm-up that leaves roughly a 20-bar test set,
  which is why every "no edge" conclusion computed on them was under-powered:
  it could only ever have detected an annualised Sharpe above ~4.6.
- `HBAR-USD.STALE-ends-2026-06-10.csv` -- the corrupted series. It looked
  completely normal and was 70 days stale. It is the reason
  `PRICE_DATA_INTEGRITY.md` exists and the reason `daily.py` now refuses a
  window whose newest bar is more than two days old instead of reporting it.
- `XRP-USD.csv` -- Coinbase export, superseded by `deep/XRP_2025_2026Aug.csv`
  (the two agree to < 0.01 % on the overlapping 2026-08-19 close, which is
  the cross-venue check recorded in TRADING_READINESS.md).

Nothing here is deleted, and nothing is renamed: a file that a past result was
computed on should stay findable under the name that result cited.
