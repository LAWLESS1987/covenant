# Does any rule survive? A walk-forward test before going live

**2026-09-03.** Asked for: "a real, walk-forward validated strategy that actually
works — otherwise you're just adding risk for no reason."

**The answer is no.** Nothing survived. Not one rule, on one asset, cleared the
three tests together. The trader stays disarmed. This document is the evidence,
including the numbers that look like the opposite of that conclusion.

Reproduce every line of it with:

```bash
python strategy_validate.py --out docs/results/STRATEGY_VALIDATION_2026-09-03.txt
```

## The bar a rule had to clear

Three tests, all of them, or it does not count.

| test | what it asks | threshold |
|---|---|---|
| deflated Sharpe | is this Sharpe better than the best of 720 coin flips? | ≥ 0.95 |
| walk-forward | does it work on data the search never saw, repeatably? | majority of folds positive **and** binomial p ≤ 0.05 |
| PBO | does the selection procedure beat picking at random? | < 0.5 |

The middle one is stricter than it looks, and deliberately. This framework's own
random-walk test produced 4 of 5 positive folds and +9.76% mean out-of-sample on
data with no edge in it at all. A tally of positive folds is not a test. It needs
a p-value beside it.

## Data and costs

Twelve Kraken daily series, 2025-01-01 (or the pair's listing) to **2026-09-03**,
368 to 611 bars each, extended today by `realdata/refresh_kraken.py` with every
overlapping bar re-checked against Kraken and the in-progress candle dropped.

Costs are the ones this account pays, not the framework's defaults. Kraken Pro's
lowest tier is 0.40% taker, and spread and slippage are charged adversely in both
directions:

| component | bps |
|---|---|
| taker fee | 40 |
| half-spread | 5 |
| slippage | 5 |
| **round trip** | **100** |

Price must move 1% before a trade breaks even. The framework's default of 10 bps
taker is a volume tier this account does not have, and using it would have
flattered every result below.

## What was tried

60 variants across 12 assets: **720 trials in one search.** That count is carried
into the deflated Sharpe rather than forgotten, because a Sharpe of 1.5 from one
attempt and a Sharpe of 1.5 from 720 are not the same claim.

## The results that look like success

| asset | buy & hold | best variant | in-sample | Sharpe | deflated | trades | PBO |
|---|---|---|---|---|---|---|---|
| CRO | −58.1% | sma_cross 8/30 | **+151.2%** | 1.20 | **0.0000** | 20 | 0.97 |
| AVAX | −78.9% | breakout 24 | **+106.3%** | 1.17 | **0.0000** | 14 | 0.80 |
| SOL | −45.0% | sma_cross 12/30 | +93.3% | 1.05 | 0.0000 | 21 | 0.89 |
| WLFI | −94.3% | sma_cross 5/30 | +80.8% | 1.53 | 0.0000 | 10 | 0.43 |
| ONDO | −73.0% | sma_cross 12/30 | +73.6% | 0.90 | 0.0000 | 21 | 0.74 |
| ATOM | −75.5% | mean_revert 48/1.5 | +69.6% | 1.31 | 0.0000 | 39 | 0.46 |
| HBAR | −62.0% | sma_cross 20/100 | +54.0% | 1.59 | 0.0000 | **1** | 0.39 |
| NEAR | −60.2% | vol_target 40% | +24.1% | 1.05 | 0.0000 | 2 | 0.60 |
| XRP | −30.2% | vol_target 30% | +12.9% | 0.82 | 0.0000 | 2 | 0.96 |
| ADA | −73.8% | sma_cross 20/100 | −9.7% | 1.05 | 0.0000 | 8 | 0.64 |
| PEPE | −81.4% | mean_revert 24/1.0 | −129.2% | 0.90 | 0.0000 | 55 | 0.91 |
| XLM | −44.5% | sma_cross 12/100 | −143.4% | 1.02 | 0.0000 | 9 | 0.71 |

Three things in that table matter more than the returns.

**The deflated Sharpe is 0.0000 on every single asset.** Not low. Zero to four
decimal places. Against 720 trials the expected best Sharpe from pure luck is
higher than anything actually achieved. Every headline number in the third column
is indistinguishable from the best of 720 coin flips.

**PBO is at or above 0.5 on nine of the twelve**, reaching 0.97 on CRO and 0.96 on
XRP. PBO is the rate at which the variant that won in-sample lands *below median*
out-of-sample. Above 0.5 the selection procedure is worse than choosing at random.

**HBAR's +54.0% is one trade.** That is n=1. It is a coin flip that landed, and
the same finding was made on older data and written down then.

Two results are worse than −100% (XLM, PEPE). Those variants short, and a fixed
notional short against a rising price loses more than the stake. He cannot short
crypto spot on either venue, so those are artefacts of the grid, not offers.

## Every asset fell

Buy and hold lost between 30% and 94% on all twelve. **The whole window is one
bear market.** That single fact explains most of the apparent success above: in a
market that only falls, any rule that spends most of its time in cash beats
holding, and it does so without containing any information about the future.

## Walk-forward: the honest version

The procedure is refit on each training slice — the grid is re-searched on train
only, and its winner is traded forward. That is what a person actually does, and
it carries the selection bias that freezing a winner chosen on the full history
hides.

| asset | positive folds | mean out-of-sample | worst fold | p |
|---|---|---|---|---|
| PEPE | 3/5 | +14.16% | −9.93% | 0.500 |
| AVAX | 2/5 | +7.60% | −7.86% | 0.812 |
| HBAR | 3/5 | +2.09% | −14.88% | 0.500 |
| ATOM | 3/5 | −2.50% | −20.74% | 0.500 |
| CRO | 2/5 | −2.77% | −14.76% | 0.812 |
| ONDO | 3/5 | −3.12% | −38.54% | 0.500 |
| WLFI | 1/5 | −7.59% | −25.65% | 0.969 |
| ADA | 1/5 | −10.30% | −18.91% | 0.969 |
| SOL | 1/5 | −10.90% | −34.43% | 0.969 |
| XRP | 1/5 | −11.28% | −28.30% | 0.969 |
| NEAR | 1/5 | −26.47% | −67.08% | 0.969 |
| XLM | 1/5 | −29.01% | −54.43% | 0.969 |

**Zero of twelve are consistent.** The best p-value in the column is 0.500, which
is the p-value of a fair coin. Mean out-of-sample return is negative on eight of
twelve. The rules that made +151% and +106% in the search lost money going
forward.

One limitation, stated rather than hidden: 611 daily bars at 5 folds leave room
for a look-back of 71 days and no more, so the long rules (every 100-day and
200-day variant) were **excluded** from the walk-forward and named in the
transcript. This data cannot validate a 200-day rule out of sample. That is a
statement about the data, not about the rule.

## The one prior claim, retested

`MY_STRATEGY.md` says trend-following cut the worst drawdown by about 3x, and
calls that the one effect that replicated. Retested on twelve assets:

| rule | drawdown fell on | median cut | vs hold | time in market |
|---|---|---|---|---|
| sma_filter 150 | **12/12** | 1.51x | +40.5 pp | 17% |
| sma_filter 100 | 10/12 | 1.49x | +29.3 pp | 24% |
| sma_filter 200 | 10/12 | 1.45x | +27.7 pp | 13% |
| sma_filter 50 | 7/12 | 1.11x | +13.5 pp | 30% |
| vol_target 20% | 12/12 | 52.98x | +68.0 pp | **0%** |
| vol_target 30% | 12/12 | 15.66x | +62.0 pp | 1% |
| vol_target 40% | 12/12 | 3.40x | +66.1 pp | 7% |

The direction replicates: a 150-day trend filter reduced the worst drawdown on
all twelve assets. **The size does not.** It is about 1.5x here, not 3x.

And the last column is the finding. The vol-target rule that "cuts drawdown 53x"
is **in the market 0% of the time**. It is cash. Cash has no drawdown, beats a
falling market by definition, and is not a strategy. The trend filters are barely
different in kind: 13% to 24% time invested across a window where everything
fell.

So this data cannot separate "the trend filter works" from "being in cash works
during a crash." Both predict exactly what was measured. Distinguishing them needs
a window containing a sustained rise, and there isn't one in 2025-01 to 2026-09.

`MY_STRATEGY.md`'s 3x figure should be read as measured on two assets in a
one-directional window, not as a property of the rule.

## Go / no-go

**No-go for return.** `trader_config.json` stays `armed: false`. Nothing here
earned a live order. Arming on this evidence would be adding risk for no measured
reason, which is the thing the question was asked to prevent.

What would change the answer, in the order it would have to happen:

1. **A window with a rise in it.** Every conclusion above is drawn from one bear
   market. Re-run this when the data holds a sustained uptrend, and the drawdown
   claim becomes separable from the cash claim.
2. **Paper trading with sealed signals.** `trader_config.json` already requires
   `min_sealed_signals: 30`. Thirty sealed daily signals, recorded before the
   outcome is known, are worth more than any backtest, because they cannot be
   searched over after the fact.
3. **A rule with fewer parameters than the data can support.** 720 trials against
   611 bars is why the deflated Sharpe is zero. Fewer variants, chosen for a
   stated reason before testing, is the only way that number moves.

## What is still missing

- **Cross-sectional rotation was not tested.** Ranking the eleven non-XRP assets
  by momentum and holding the top few is the obvious family this run does not
  cover, and the $25 order cap with 2 orders a day makes its execution delay a
  real modelling problem rather than a detail.
- **No block-bootstrap null.** The deflated Sharpe and PBO both answer the
  overfitting question analytically. An empirical p-value from resampling each
  series would answer it a second, independent way.
- **Coinbase fees are not modelled separately.** Everything above uses the Kraken
  tier. The Coinbase side is more expensive, so every result here is the
  optimistic one.
- **XRP is hold-only**, so roughly half the book is not addressable by any rule in
  this document regardless of what it measured.
