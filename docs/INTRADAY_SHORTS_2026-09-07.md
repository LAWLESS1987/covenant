# Intraday and shorts, measured. 2026-09-07

**Asked:** *"should be looking at day trading trends also shorts etc"* — then
*"do it"*. So it was done, in `strategy_lab.py`, at the cost this account
actually pays, before anything touched the trader.

**Answer: no on both, and the reason is not the one anyone expects.**

---

## What was run

Real Kraken OHLC pulled 2026-09-07: **8 assets × 2 intraday timeframes** —
hourly (721 bars, 30 days) and 4-hourly (721 bars, 120 days). SOL, XRP, XLM,
ADA, ATOM, AVAX, HBAR, CRO.

`strategy_lab.py`, 53 variants per run across four families (sma_cross,
sma_longonly, mean_revert, breakout), each with walk-forward refitting, an
embargo gap, and a deflated Sharpe that raises the bar for every variant tried.
**848 variants.** Costs at `--fee-bps 55`, which is `2 × (55 + 5 + 5)` =
**130 bps round trip** — the same number `signal_ledger.py` charges.

**The instrument was checked first.** On pure noise it reported NO EDGE FOUND.
On a synthetic trend it reported no *bot* edge but correctly identified that
buy-and-hold captured it (+169.58%, DSR 1.000). It finds what is there and not
what is not.

## Result 1 — no edge, on any asset, at either timeframe

**Deflated Sharpe = 0.0000 on 16 of 16 runs.** Raw Sharpes ran up to 1.82 and
every one of them fell to zero once deflated by the number of variants tried.
Walk-forward means ran −7.64% to +6.31%, folds positive 0/4 to 3/4 — noise.

## Result 2 — it is NOT the fees. There is nothing under them.

The obvious hypothesis was that 130 bps eats an intraday edge that would exist
at a better fee tier. It was tested by driving costs to **zero**, which is
impossible in the world and useful in the lab:

| data | 130 bps (real) | 40 bps | **zero cost** |
|---|---|---|---|
| SOL 1h | DSR 0.0000 | DSR 0.0000 | **DSR 0.0000** |
| ADA 4h | DSR 0.0000 | DSR 0.0019 | **DSR 0.0001** |

**At zero cost the deflated Sharpe is still zero.** Fees are not hiding an
edge; there is no edge underneath them. That closes the fee-tier argument as a
route to profitability — it would matter if there were something to protect,
and there is not.

## Result 3 — shorting made every single variant worse

The lab runs the same signal two ways: `sma_cross` shorts when the signal is
down, `sma_longonly` goes flat instead. Same data, same costs, SOL hourly:

| variant | return | Sharpe |
|---|---|---|
| sma_longonly 20/100 | **+29.69%** | **1.42** |
| sma_cross 20/100 (shorts) | +23.70% | 1.11 |
| sma_longonly 12/100 | **+29.60%** | **1.41** |
| sma_cross 12/100 (shorts) | +23.24% | 1.10 |

Shorting cost roughly **6 percentage points and 0.3 Sharpe on every matched
pair**. The lab's own docstring said why before the run: *"Shorting doubles
your exposure to being wrong; many 'edges' vanish once you cannot short."*

And shorts are not wired anyway — `venues.py` is spot only, no margin, no
perps, no borrow. Adding them means a different product, liquidation risk, and
a risk frame (position cap, cash floor, never-average-down) built for a world
where the worst case is zero.

## Result 4 — the only thing on the board with a real DSR is doing nothing

On SOL hourly: **buy_and_hold +34.64%, Sharpe 1.34, DSR 1.000** — and it beat
all 53 variants. The best bot variant made +29.69%. The trading subtracted
about five points and added turnover, timing risk and 130 bps a round trip.

That is the same verdict `d2_regime_deep.py` reached on daily bars, reached
again two timeframes down.

## Where this leaves the search

| mechanism class | variants | verdict |
|---|---|---|
| per-asset timing, daily (`strategy_validate.py`) | ~800 | nothing survived |
| cross-sectional momentum (`strategy_cross_sectional.py`) | 288 | PBO 0.986 |
| pairs / relative value (`strategy_pairs.py`) | — | measured, no survivor |
| 200-day regime (`d2_regime_deep.py`) | 10 assets | p 0.47–0.92, DSR 0.000 |
| **intraday 1h + 4h, long and short (this run)** | **848** | **DSR 0.0000 × 16** |

Five mechanism classes. Well over 1,900 variants. No surviving edge at any
timeframe, with or without shorting, at any cost level including zero.

**Nothing here says the market is unbeatable. It says this account, on these
assets, with this data, has not found a way to beat it — and that going faster
or adding shorts moves away from an answer, not toward one.** The one strategy
that has produced a positive deflated Sharpe in any test run in this project is
holding.

---

Read-only with respect to the trader: no config, cap, gate or credential was
touched, and nothing was placed. Data and lab runs were done off-machine; only
this document was written.
