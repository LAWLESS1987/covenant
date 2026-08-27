# Real-data test: XRP, 349 verified daily bars (2025-09-05 -> 2026-08-19)

## Data provenance (why you can trust these numbers)

Fetched from Coinbase's public API, then verified three ways before use:

| check | result |
|---|---|
| timestamp spacing | every gap exactly 86400s -> PASS |
| OHLC coherence | 0 incoherent bars -> PASS |
| chain continuity (`open[i]` vs `close[i+1]`) | worst diff 0.0005, avg 0.0001 -> PASS |
| independent cross-source (Kraken) | 5/6 settled bars agree to **0.02%** |
| in-progress candle | detected (8.9% disagreement on newest bar) and **dropped** |

The chain-continuity check is the strong one: fabricated numbers cannot keep
`open[i] == close[i+1]` across 350 consecutive rows.

**Market context: XRP fell $2.79 -> $1.11 over this period. Buy-and-hold was -63.22%.**

## Headline result, and why it is not what it looks like

| | return | trades | max drawdown |
|---|---|---|---|
| buy_and_hold | **-63.22%** | 1 | 68.2% |
| best variant (`breakout 72`) | **+47.24%** | **1** | 22.5% |

A +110 percentage-point swing versus holding. It looks spectacular.

**It came from ONE trade.**

That is the whole finding. `breakout 72` made a single position decision across
an entire year, and that year happened to be a one-directional crash. A single
correct bet is n=1. There is no statistical content in n=1 — it is one coin flip
that landed, and no amount of backtesting makes it more than that.

## The out-of-sample test (winner chosen on train only, scored on unseen data)

TRAIN 2025-09-05 -> 2026-05-07 ($2.79 -> $1.42) | TEST 2026-05-07 -> 2026-08-19 ($1.42 -> $1.11)

| rank | strategy | TRAIN | TEST (unseen) | test trades |
|---|---|---|---|---|
| 1 | breakout 72 | +32.05% | **-7.31%** | 1 |
| 2 | sma_cross 20/72 | +29.10% | +0.14% | 1 |
| 7 | sma_cross 12/72 | +21.29% | +0.14% | 1 |
| 9 | sma_cross 5/30 | +18.33% | -8.67% | 5 |
| -- | buy_and_hold | -52.54% | -23.42% | 1 |

- profitable out-of-sample: **3/6**
- mean out-of-sample return: **-2.70%**
- p under the null: **0.656** (a coin-flipper does this well 2 times in 3)
- deflated Sharpe over 53 variants: **0.0005** ("not distinguishable from selection luck")

Strategies that returned +32% in training averaged **-2.70%** on data they had
not seen. The apparent edge did not survive.

## What IS defensible here

The strategies lost far less than holding (-2.70% vs -23.42% on test; 22.5% vs
68.2% max drawdown over the year). That is consistent with the documented
benefit of trend-following: it is **drawdown reduction in a persistent trend**,
not return generation. But with 1 trade per strategy, this specific test cannot
establish even that. It is a hypothesis, not a result.

## Honest conclusion

**No tradeable edge was found on real XRP data.** The winner is one lucky bet
during a crash. Deploying it forward would be betting that the next year is also
a one-directional decline — which is a market call, not a strategy.

The one durable, real number in this whole exercise: **XRP is down 63% over the
year.** Any plan involving it should start from that, not from a backtest.

## Method note (what changed during this run)

1. Walk-forward could not run (349 bars cannot support 4 folds at warmup 74) ->
   switched to a 70/30 train/test holdout.
2. Three strategies showed an identical +0.14% -> investigated rather than
   reported. Cause: they made exactly one trade. That discovery is what turned a
   "+47% winner" into "n=1, no statistical content."

---

# SECOND ASSET: HBAR (349 verified daily bars, 2025-06-27 -> 2026-06-10)

Same fetch, same three integrity checks, same test. The one incoherent bar was
the in-progress candle (open 0.0776 vs low 0.07763) and was dropped, not hidden.

## Side by side

| | XRP | HBAR |
|---|---|---|
| buy & hold, full year | **-63.22%** | **-50.35%** |
| hold max drawdown | 68.2% | 73.3% |
| best variant | breakout 72 | sma_cross 20/48 |
| its full-period return | +47.24% | +52.30% |
| **its max drawdown** | **22.5%** | **21.3%** |
| trades | 1 | 8 |
| out-of-sample return | -7.31% | +6.07% |
| deflated Sharpe (53 tries) | 0.0001 | 0.0749 |
| top-10 out-of-sample mean | **-2.70%** | **-7.06%** |
| top-10 OOS p-value | 0.656 | 0.891 |

## What replicated, and what did not

**DID NOT replicate: any return edge.** On both assets the top-10 train winners
averaged NEGATIVE out-of-sample (-2.70%, -7.06%) at p=0.656 and p=0.891. Neither
survived deflation by the 53-variant search (0.0001, 0.0749 -- both far under the
0.95 bar). Two independent assets, same verdict: **the profit is selection luck.**

Note HBAR's single best variant WAS +6.07% out-of-sample. That is exactly the
cherry-pick trap: pick the winner after the fact and it looks real; look at all
ten and the average is -7.06%.

**DID replicate, and this is the interesting part: drawdown reduction.**

| | hold maxDD | strategy maxDD | reduction |
|---|---|---|---|
| XRP | 68.2% | 22.5% | **3.0x** |
| HBAR | 73.3% | 21.3% | **3.4x** |

Two different assets, two different winning strategies, two different periods --
and both cut max drawdown by roughly 3x. That consistency is what a real effect
looks like, as opposed to the returns, which did not replicate at all.

This matches the trend-following literature exactly: it is a **risk-management
tool, not an alpha generator.** It does not make money; it loses less when a
trend runs against you. Both assets fell ~50-63% and the strategies sat out most
of it.

## The honest bottom line, on real data, twice

1. **No tradeable return edge exists in this search.** Confirmed independently
   on two assets. More variants would make this worse, not better.
2. **The drawdown effect is real and replicated**, but it is a defensive
   property, not a profit engine -- and n=1 to 8 trades is still a small sample.
3. **Both assets lost roughly half their value this year.** That is the dominant
   fact. No amount of strategy tuning changes the fact that the watchlist is in
   a severe downtrend.

If you want to act on anything here, the defensible version is: *trend-following
as a drawdown control on a position you already intend to hold* -- not as a way
to generate returns. And that should be paper-traded live for 30+ sealed signals
before a cent moves, because everything above is still backtest.
