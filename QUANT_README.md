# Backtesting, paper trading, and edge maintenance

> **Read as an experiment.** *Added 2026-10-04 for clarity, at the operator's
> request of 2026-10-03 ("reflect the scientific method while leaving the
> substance"); this page was missed that day (A257). A map onto the sections
> below; nothing below it was changed except one dated note under "Using real
> tick data".*
>
> - **Question.** Can a backtest's guardrails tell a mined illusion from a real
>   edge, before any money depends on the answer?
> - **Method.** Run them where the truth is known: a random walk, on which no
>   edge can exist, and a genuinely trending series as the control.
> - **Evidence.** [The headline result](#the-headline-result) and
>   [What each guardrail caught](#what-each-guardrail-caught); every figure on
>   this page reproduced on 2026-10-04 (16 passed, 0 failed).
> - **What would refute it.** A mined winner the deflated Sharpe lets through,
>   or the real trend it rejects.
> - **Known limits.** [Honest limits](#honest-limits): synthetic data proves the
>   machinery, not any strategy.
> - **Reproduce.** `python test_backtest_guardrails.py`.

**16/16 validation checks passing.** The framework is validated against data
with **known ground truth** — a random walk, where no edge can exist — because
you cannot verify anti-illusion machinery on real market data. On real data you
never learn whether the guardrails were right.

## The headline result

Searching **150 parameter pairs** on a provable random walk produced a "winner":

| metric | value |
|---|---|
| net return after real costs | **+144.70%** |
| Sharpe | 1.10 |
| trades | 51 |
| actual edge | **zero, by construction** |

That equity curve is real. The edge is not. Everything below exists to make
that distinction visible.

## What each guardrail caught

**Deflated Sharpe — the central number.** Told the truth about 150 trials:
**DSR 0.0000**, selection benchmark 2.67 against a raw Sharpe of 1.10. Told it
was a single trial: **DSR 1.0000**. Same returns, opposite verdict. This is why
`strategies_tried` is carried on the result object and not left to memory.

**Walk-forward alone was NOT enough — measured, not assumed.** The mined
strategy produced **4/5 positive folds and +9.76% mean out-of-sample on pure
noise**. A naive "≥60% of folds positive" rule passed it. Under the null, 4/5
has p=0.188 — unremarkable. Consistency now requires a majority *and*
significance. Walk-forward is widely treated as the gold standard; on its own
it is a tally, not a test.

**Look-ahead is structurally impossible.** Strategies get a `PointInTimeView`
that raises on any forward index. Not a convention to remember — an operation
you cannot perform.

**Costs at real size.** Modelled at ~$12 per position, not $10,000. Round trip
is 40 bps; the mined strategy burned **10.2% of capital in fees**, and zeroing
costs flattered it by **+20.6 percentage points**.

**Edge decay.** A simulated edge died at period 100; the monitor killed it at
**period 114** — and did not kill a healthy edge over 300 periods of ordinary
variance.

**Control: real signal is not rejected.** Buy-and-hold on a genuinely trending
series scored **DSR 1.000**. The guardrails reject noise, not profit.

## Files

- `covenant_backtest.py` — engine, cost model, guardrails, `EdgeMonitor`, `PaperTrader`, `load_csv`
- `test_backtest_guardrails.py` — the validation above; run it after any change

## Using real tick data

`load_csv(path, ...)` takes real OHLCV and **validates** it — a bar whose close
sits outside its own high/low is corrupt and raises rather than silently
distorting every downstream number. I could not fetch a verified crypto dataset
from this sandbox (the repo paths had moved and the GitHub API was rate-limited),
so no real-data result is claimed here. Drop your own CSV in; nothing else
changes.

*A257, 2026-10-04: verified real data exists now, and so does a real-data
result.* `realdata/deep/` holds twelve Kraken daily series with recorded hashes
(`realdata/README.md`), and `docs/TRADING_READINESS.md` reports what these
guardrails said on them: no timing edge distinguishable from chance. This page
still claims no real-data result of its own.

## Honest limits

- Validated on synthetic data. That proves the **machinery**, not any strategy.
- No survivorship-bias handling — that lives in how you choose the asset list,
  and the 13-asset watchlist was selected with hindsight.
- Bar data, not true tick: intrabar path is modelled, not observed. Stop-loss
  and intrabar fill realism will overstate results.
- `EdgeMonitor` needs an honest `expected_mean`/`expected_sd` from a backtest
  that already passed the guardrails. Feed it in-sample numbers and it will
  never fire.

## Before trusting any result

1. Record how many variants you tried. Every one. Set `strategies_tried`.
2. Run `evaluate(...)` with a walk-forward — in-sample-only fails by design.
3. Paper trade with sealed predictions before any capital moves.
4. Keep `EdgeMonitor` running. Edges expire; assume yours will.
