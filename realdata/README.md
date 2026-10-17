# realdata/ -- which price files to trust

> **Read as an experiment.** *Added 2026-10-03 for clarity, at the operator's
> request ("reflect the scientific method while leaving the substance"). A map
> onto this page; nothing else on it was changed.*
>
> - **Question.** Which price series are sound enough to test a strategy on?
> - **Method.** Each series checked for daily contiguity, duplicate
>   timestamps, OHLC sanity and UTC alignment; interior windows re-fetched and
>   diffed byte for byte; every file's sha256 recorded.
> - **What was refuted.** The older, shorter series were too short to detect
>   anything below a very large edge, and one series that looked normal was 70
>   days stale ([SUPERSEDED](#superseded----do-not-run-a-backtest-on-these)).
>   They are kept so a result quoted from them can be traced.
> - **Use.** `realdata/deep/` only.

**Use `realdata/deep/` for everything.** Twelve Kraken daily series,
2025-01-01 -> 2026-08-21 (or the pair's listing date), each verified for
86 400 s contiguity, no duplicate timestamps, OHLC sanity and 00:00 UTC
alignment, with two interior windows independently re-fetched and diffed
byte-for-byte. sha256 of every file is recorded in `claude/IMPROVEMENT_LOG.md`
under D1.

*REALDATA-TWELVE-2026-10-15: `deep/` holds fifteen series, not twelve -- see
the note after the next.*

*A257-HASHLOC, 2026-10-04: the hashes are elsewhere, and the files have grown since.*
The D1 record is `docs/IMPROVEMENT_LOG.md` (there is no `claude/` here), as
8-hex prefixes of the 598-bar files. On 2026-09-04 `realdata/refresh_kraken.py`
appended 13 bars to each of the twelve, so the windows now end 2026-09-03 and
the table below is the D1 state; every overlapping bar agreed.
`realdata/deep/REFRESH_LOG.md` records each file's sha256 before and after, and
all twelve files on disk match their "after". The D1 prefixes still verify the
first 598 bars: ADA's first 599 lines hash to `a0ae69f1`.

*REALDATA-TWELVE-2026-10-15 (proposed tombstone), measured 2026-10-15 at
eeb2f18 by listing the directory.* `deep/` holds fifteen series, not twelve,
and has since 462887e, the commit that wrote "for everything": the twelve in
the table and three shorter ones the table does not name --
`SOL_2025_2026Jan.csv` (391 bars, 2025-01-01 -> 2026-01-26),
`XLM_2025Q2_2026Jan.csv` (281 bars, 2025-04-15 -> 2026-01-20) and
`XRP_2025_2026Jan.csv` (397 bars, 2025-01-01 -> 2026-02-01). They pass the
same four checks, but the D1 record says the 598-bar files supersede them for
D2, and `REFRESH_LOG.md` never extended them. "Everything" means the twelve in
the table. Re-measured the same day:
each of the twelve has 0 gaps other than 86 400 s, 0 duplicate timestamps,
0 bars off 00:00 UTC and 0 OHLC defects; each matches its "after" hash; and
each one's header and first D1 bars (598, or 570, 408 and 355 for CRO, HBAR
and WLFI) hash to its D1 prefix.

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
*(2026-10-15: two files here are not price series -- `series_issues.csv`, 28
rows of findings, 24 about the `_c` files and 4 about the two `-USD` files
below, and `refresh_kraken.py`, the script that extends `deep/`, added in
6f030af on 2026-09-03.)*

- `*_c.csv` (ADA, CRO, HBAR, ONDO, PEPE, SOL, WLFI, XLM) -- the ~220-bar
  series. After the 200-day warm-up that leaves roughly a 20-bar test set,
  which is why every "no edge" conclusion computed on them was under-powered:
  it could only ever have detected an annualised Sharpe above ~4.6.
  *REALDATA-C220-2026-10-15 and REALDATA-SHARPE20-2026-10-15, proposed
  tombstones; measured 2026-10-15 by counting rows (these files have no header
  and are unchanged since 462887e).* Six of the eight have 220 bars. `HBAR_c.csv`
  has 419 (2025-06-27 -> 2026-08-19) and `WLFI_c.csv` 110 (2026-05-02 ->
  2026-08-19), so a 200-bar warm-up leaves 20 bars on six of them, 219 on HBAR
  and none on WLFI. The ~4.6 is not the floor for 20 bars: the D1 record in
  `docs/IMPROVEMENT_LOG.md` ties 4.61 to a 66-bar test set ("220 bars →
  66-bar test set"), and 1.96 x sqrt(365/66) = 4.61 reproduces that number (a
  reconstruction; the record gives no formula); the same arithmetic on 20 bars
  gives 8.37. Two right numbers of different things were joined. The
  conclusion stands, and more strongly: on 20 bars the floor was higher, not
  lower.
- `HBAR-USD.STALE-ends-2026-06-10.csv` -- the corrupted series. It looked
  completely normal and was 70 days stale. It is the reason
  `PRICE_DATA_INTEGRITY.md` exists and the reason `daily.py` now refuses a
  window whose newest bar is more than two days old instead of reporting it.
- `XRP-USD.csv` -- Coinbase export, superseded by `deep/XRP_2025_2026Aug.csv`
  (the two agree to < 0.01 % on the overlapping 2026-08-19 close, which is
  the cross-venue check recorded in TRADING_READINESS.md).

Nothing here is deleted, and nothing is renamed: a file that a past result was
computed on should stay findable under the name that result cited.
