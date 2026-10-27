# Your strategy — rules, not predictions

Built from what actually survived testing on YOUR assets (349 real daily bars
each, XRP and HBAR). Everything here is a rule you apply to whatever you hold.
No account access required. No prediction required.

---

## The evidence this is built on

| tested | result |
|---|---|
| ~800 strategy variants across 16 assets | no profit edge survived deflation |
| top-10 winners, XRP, out-of-sample | **-2.70%** (p=0.656) |
| top-10 winners, HBAR, out-of-sample | **-7.06%** (p=0.891) |
| drawdown reduction, XRP | 68.2% -> 22.5% (**3.0x**) |
| drawdown reduction, HBAR | 73.3% -> 21.3% (**3.4x**) |

**Read that twice.** Nothing predicted returns. One thing replicated cleanly on
two independent assets: **trend-following cut the worst loss by about 3x.**

So this strategy does not try to make money by timing. It manages how much you
can lose. That is the only effect the evidence supports.

> **Retested 2026-09-03 on twelve assets, data extended to that day.** The
> direction holds and is now measured on twelve series instead of two: a 150-day
> trend filter cut the worst drawdown on **12 of 12**. The size does not hold —
> the median cut is **1.5x, not 3x**. And the retest surfaced a confound this
> table cannot see: the filter is in the market only 13–24% of the time, and
> every asset in the window fell 30–94%, so "the trend filter works" and "being
> in cash works during a crash" predict the same measurement. Separating them
> needs a window with a sustained rise in it, which 2025-01 to 2026-09 does not
> contain. Read the 3x above as two assets in a one-directional market, not as a
> property of the rule. Full numbers and method:
> [docs/STRATEGY_VALIDATION_2026-09-03.md](docs/STRATEGY_VALIDATION_2026-09-03.md).

---

## RULE 1 — Size by volatility, not by conviction

Your assets move 62%-78% annualised (3.3%-4.1% per day). At that volatility, how
much you hold decides your outcome far more than when you buy.

- No single coin above **20%** of your crypto total.
- Crypto total no more than an amount you could see fall **70%** without it
  changing your life. Both your assets have already done ~65-73% peak-to-now.
- Keep a cash sleeve. It is the only asset that does not fall with the others.

**Why this rule is first:** it is the only lever in this document with a
guaranteed, arithmetic effect. Everything else is probabilistic.

---

## RULE 2 — The 200-day line is the regime switch

Not a buy signal. A statement about which regime you are in.

- Price **BELOW** its 200-day average = downtrend regime. Do not add. This is
  where trend-following earns its 3x drawdown reduction.
- Price **ABOVE** its 200-day average = uptrend regime. Normal position sizing
  applies.

Current state (from verified data):
- **XRP $1.105 — BELOW 200d by 13.5%.** Downtrend regime. Above its 20d and 48d,
  so this is a bounce inside a downtrend, not a reversal.
- **HBAR $0.0776 — BELOW everything, sitting at its 52-week low.** (data through
  2026-06-10, needs refresh)

---

## RULE 3 — Act on regime CHANGES, never on daily moves

The daily alert tells you the regime. You act only when it flips, and flips are
rare — a handful of times a year, not weekly.

- Flip DOWN through the 200d -> reduce that position toward your floor.
- Flip UP through the 200d -> may return to normal size.
- Everything in between -> **do nothing.** Doing nothing is a position.

A +10% week (XRP just had one) is NOT a regime change. Our testing found
reacting to moves like that averaged -2.7%.

---

## RULE 4 — Never add to a loser to "average down"

Both your assets fell 46-64% this year. Adding on the way down is the single
fastest way that becomes unrecoverable. If Rule 2 says downtrend regime, the
position does not grow. Full stop.

---

## RULE 5 — Prove it before it costs anything

`signal_watch.py --record` seals every signal BEFORE the outcome and scores it
with a p-value. Run it for **30+ signals** before letting any of this change
real money.

If it comes back "not distinguishable from luck," that is the answer, and you
paid nothing to learn it.

Since 2026-09-06 the auto-trader keeps this record itself: `signal_ledger.py`
seals each asset's 200-day regime call and settles it when the regime flips,
and `covenant_trader.py` will not place a live order until 30 flips have
settled AND the record beats the coin-flip test (p <= 0.05, positive mean
after fees). `python signal_ledger.py` prints where it stands. Before that
date the counter was read and never written -- see docs/KNOWN_ISSUES.md A47.

---

## RULE 6 — Contribute on a schedule, never on a signal (added 2026-09-06)

Asked: "a budget of 100 a week". No timing edge replicated, so this rule never
asks *when*. Each week's money is placed by rules that already exist:

1. **Cash floor first.** Nothing is put to work while cash is under 10% of the
   book. The week's money stays as USDC and the run says so.
2. **Then equal shares** into held assets that are under the 20% concentration
   cap and above their 200-day line (Rule 4 said forwards). Hold-only assets
   (XRP) never receive a dollar.
3. **Under the caps:** $25 per order, at most the day's remaining order count,
   maker-only, and the week's total within `weekly_fiat_budget_usd`, which
   `guards.WeeklyBudget` enforces as a backstop from the trader's own record.

Shipped off (`allow_fiat_buys` false, budget 0). The operator's own
`trader_config.json` turns it on with a number. Pinned by
`test_r6_contribution.py`.

**Rule 5 gates Rule 6, and that was not stated when Rule 6 was written.**
Measured 2026-09-06: `preconditions()` applies the Rule 5 gate to every order,
buys included, so a contribution order is refused with "0 sealed signals on
record, need 30" even once the cash floor is met. That is defensible rather
than accidental -- step 2 of Rule 6 only adds to assets **above their 200-day
line**, which is precisely the signal Rule 5 is still scoring -- but it means
the weekly budget accumulates as cash until Rule 5 clears. Removing the regime
filter to escape the gate is not a fix: it would put money into assets below
their line, which Rule 4 forbids. Whether to exempt a pure schedule from Rule 5
is the operator's decision and has not been taken. See docs/KNOWN_ISSUES.md A58.

---

## What this strategy explicitly does NOT do

- It does not predict price. Nothing tested here could.
- It does not promise profit. Both assets are in severe downtrends.
- It does not require an exchange link, an API key, or a seed phrase. Anything
  asking for those is not part of this strategy.
- It does not trade automatically. You place every order yourself.

---

## Your daily loop, in full

1. 8:00am ET — alert arrives on your phone with each asset's regime state.
2. If no regime flip: **do nothing.** (This is most days.)
3. If a flip: check Rule 2 and 3, decide, place it yourself in Kraken.
4. Weekly: `python signal_watch.py --record` to see if the signals are earning
   their keep.

---

## The one number to fill in

Everything above is complete except your position sizes, which need one input
from you: **what you actually hold.** Approximate is fine — "5000 XRP, 20000
HBAR, $400 cash". With that, Rule 1 becomes specific numbers instead of
percentages.
