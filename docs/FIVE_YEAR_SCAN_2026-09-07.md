# "One that works every year", and "repeatable patterns". Both measured. 2026-09-07

**Asked:** *"look for one that would work each of the past 5 years"*, then
*"look for repeatable patterns"*. Same question, two framings. Both were run.

**Answer: the filter finds fewer survivors in the real market than it finds in
pure noise.**

---

## 0. A dataset was thrown away first

The first pull (binance.us, daily, 2020-09 → 2026-09) returned 1,614 bars for a
2,199-day span and every variant reported **exactly +0.0% for 2024** — the tell
that stopped the run. Cause: a **586-day hole** from 2023-07-14 to 2025-02-19 in
every symbol (binance.us suspended USD service in that window). Results on that
data were discarded unread.

Re-pulled from OKX: **8 assets × 2,200 daily bars, 2020-08-30 → 2026-09-07,
gaps > 1.5 days: zero.** BTC, ETH, SOL, ADA, XRP, XLM, ATOM, AVAX. Everything
below is on the verified series. (XRP, ONDO, PEPE and WLFI could not all be
tested: three of them do not have five years of history at all.)

## 1. Does anything win in all five years?

61 variants plus buy-and-hold — SMA cross (long/short), SMA long-only, mean
reversion, breakout — decision at the close of bar *t*, filled at the open of
*t+1*, **130 bps round trip**, equal-weighted across the eight assets.

**Real data: 2 of 62 were positive in every one of 2021–2025.**

| variant | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| cross 8/48 | +170.1% | +26.1% | +35.0% | +31.6% | +14.0% |
| cross 12/48 | +157.2% | +28.2% | +17.7% | +16.3% | +32.0% |

That looks like the answer. **It is not**, and the control says why.

## 2. The control: the same scan on shuffled returns

Same assets, same volatility, same drift, returns shuffled so that **no signal
exists by construction**. Identical scan:

| shuffle seed | variants positive in all 5 years |
|---|---|
| 0 | 0 |
| 1 | 2 |
| 2 | **17** |
| 3 | 1 |
| 4 | 6 |
| **mean** | **5.2** |

**Pure noise produces 5.2 five-for-five "strategies" on average. The real market
produced 2.** The observed count is *below* what randomness delivers, and the
null's spread (0 to 17) shows the count is dominated by luck, not by signal.

Two further tells on the "winners": both are from the `cross` family, which
**shorts** — and shorting was measured on 2026-09-07 to make every matched pair
worse by ~6 points and ~0.3 Sharpe. The survivors come from the family that is
worse on average. That is what selection looks like.

## 3. Repeatability, posed properly

Not "did one win five times" but "is the whole distribution of consistency
different from noise?"

| positive in k of 5 years | real | noise (avg) |
|---|---|---|
| 0 | 0 | 6.0 |
| 1 | 8 | 7.2 |
| 2 | 0 | 11.6 |
| 3 | **42** | 9.2 |
| 4 | 10 | 13.0 |
| **5** | **2** | **15.0** |

Noise generates **15** variants at five-for-five. The market generates **2**.
Real results pile up at k=3 — which is simply the shape of the years (2021 up,
2022 down, 2023–24 up, 2025 mixed) showing through a long-biased book. There is
no repeatability here that randomness does not supply more of.

## 4. The one pattern that looked real, and what happened to it

Day-of-week, all assets, six years, before costs:

| | Mon | Tue | Wed | Thu | **Fri** | Sat | Sun |
|---|---|---|---|---|---|---|---|
| mean/day | −0.067% | +0.257% | +0.237% | +0.056% | **+0.531%** | +0.047% | +0.158% |
| naive t | −0.67 | +2.44 | +2.38 | +0.54 | **+5.33** | +0.59 | +1.47 |

A t of 5.33 is the only statistic in this entire project's history that has ever
looked like something. Three checks, and it does not survive any of them:

1. **Eight correlated majors are not eight independent observations.** Collapse
   each date to one cross-asset mean — 2,199 independent dates, 314 Fridays —
   and **t falls from 5.33 to 2.57**. A permutation test that shuffles the
   weekday labels 5,000 times gives **p = 0.0442**.
2. **Seven days were tested.** The threshold for one finding among seven is
   0.05/7 = **0.0071**. p = 0.044 does not clear it.
3. **It costs 2.4× what it pays.** Harvesting it means 52 round trips a year:
   **+27.5% gross against 67.6% in costs = −40.1% a year.**

The most statistically impressive thing found in six years of data across eight
assets is a calendar effect that is not significant once counted honestly, and
that loses forty percent a year if you trade it.

## 5. What this closes

- **"Find one that worked every year" is not a test, it is a sort.** Applied to
  62 variants it returns survivors from noise at a *higher* rate than from the
  market. Anyone offering a strategy on this evidence — including a future run
  of this loop — is showing the output of a filter, not a finding.
- **Consistency and profitability are different claims.** Nothing here has both.
- The methodology is the deliverable: a control on shuffled returns, an
  independence correction, a multiple-comparison bar, and the cost of
  harvesting. Any future candidate gets all four before it gets any money.

---

Read-only with respect to the trader: no config, cap, gate or credential
touched, nothing placed. Data and analysis off-machine; only this file written.
