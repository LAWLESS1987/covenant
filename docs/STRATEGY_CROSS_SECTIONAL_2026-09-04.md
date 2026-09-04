# A different hypothesis, the same answer

**2026-09-04.** Asked for: "steadily refining crypto trading strategy... profit
while still staying green is the goal, max yield".

**Nothing survived.** Again, and this time from a hypothesis class the earlier
search never touched. Reproduce with:

```bash
python strategy_cross_sectional.py --out docs/results/CROSS_SECTIONAL_2026-09-04.txt
```

## Why a new hypothesis rather than more variants

Yesterday's search ran ~800 variants of **one idea**: predict an asset's next
move from its own past prices — SMA crossovers, mean reversion, breakouts,
trend-filtered reversion. Nothing cleared deflation, walk-forward and PBO
together.

Searching more variants of that idea is how you find noise, not edge. So this
asks a different mechanism: **cross-sectional momentum**. Not "will XRP go up"
but "of these twelve, which have been strongest, and does holding those beat
holding all of them". It is a relative-strength claim rather than a timing
claim, it is the most replicated anomaly outside equities, and a weekly or
monthly rebalance turns over only a fraction of the book — so the 100 bps round
trip this account pays bites far less than it does on a daily timing rule.

Then a second version with **dual momentum**: the same ranking plus a cash
option, dropping any pick whose own trailing return is negative. That matters
here because equal-weight buy-and-hold over this window returned **−63.27%** — a
rule with no cash option is *required* to hold the best loser.

## The bar, unchanged

The same three tests strategy_validate.py used, all of them or it does not
count. 12 verified Kraken daily series, 611 bars, 2025-01-01 to 2026-09-03, at
40 bps taker + 5 spread + 5 slippage each way.

| test | threshold | 144 variants | 288 with cash filter |
|---|---|---|---|
| deflated Sharpe | ≥ 0.95 | **0.0000** FAIL | **0.0000** FAIL |
| walk-forward | majority of folds AND p ≤ 0.05 | 3 of 5, p = 0.500 FAIL | 3 of 5, p = 0.500 FAIL |
| PBO (CSCV) | < 0.5 | **0.914** FAIL | **0.986** FAIL |

The best variant in sample returned −50.6% with a Sharpe of −0.04. The expected
best Sharpe from 144 **no-edge** trials is 2.66. It is not close.

## The part that looks like the opposite

Two of the five walk-forward folds chose the cash filter and both were positive,
+13.44% and +2.40%, and the mean out-of-sample return across folds was **+2.85%**.
Read alone that looks like an edge.

It is not, and the framework exists to say so. Three of five folds positive
carries a binomial p of 0.500 — a coin does that half the time. And **PBO rose
from 0.914 to 0.986 when the cash filter was added**: giving the search another
dimension made the selection procedure *less* reliable, not more. A PBO of 0.986
means the in-sample winner lands below the out-of-sample median 98.6% of the
time. The procedure is worse than picking at random.

This project's own random-walk control produced 4 of 5 positive folds and +9.76%
mean out-of-sample on data with no edge in it at all. A tally of positive folds
is not a test.

## What this does not say

It does not say crypto momentum has never worked. It says **no variant of it
cleared this bar on these twelve assets over this window at these costs** — and
the window is one in which the whole basket fell 63%, which is a hard place for
a long-only relative-strength rule to earn anything.

## Where that leaves the money

Where it is. The trader stays disarmed, for a measured reason rather than a
cautious one — and arming remains a change the account holder makes, not one
this program can make for itself.

The cost floor is the thing worth carrying away: at 100 bps round trip, a rule
must be right by more than 1% per trade before it breaks even. Nothing tested
over two days on 1,088 variants across two hypothesis classes has been.
