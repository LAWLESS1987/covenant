# Best odds by condition — two periods, four pre-specified splits. 2026-09-07

**Asked:** best odds in seven minutes, using pattern recognition. Then: *"no
demands just trend observation."* That second sentence is the right frame, and
what follows is written to it — this is an observation, not a recommendation.

**The trap named first.** Slicing 355 trades by conditions until one looks good
is guaranteed to find something. So the conditions were fixed **before** looking,
each chosen for a mechanism rather than a shape, and every one was tested in
**two independent periods**. Anything that appears in only one is a slice.
Bonferroni for four tests: intervals below are 98.75%, not 95%.

---

## The two periods

- **Recent wide** — 275 assets, every live OKX USDT pair with enough history,
  2025-11-12 → 2026-09-06. 355 trades. Weak survivorship filtering.
- **Five-year survivors** — 33 assets, 2021-2026. 1,304 trades. Heavy
  survivorship, and dominated by 2021.

Different universes, different years, different biases. A pattern that holds in
both is the only kind worth naming.

| condition | recent (n, mean) | five-year (n, mean) | same sign? |
|---|---|---|---|
| **ALL** | 355, **−2.35%** | 1304, **+1.55%** | **no** |
| **BTC above its own 100d** | 226, **−1.18%** | 1221, **+1.69%** | — |
| **BTC below its own 100d** | 129, **−4.41%** | 83, **−0.51%** | **yes** |
| breadth > median | 307, −2.19% | 1304, +1.55% | degenerate |
| asset vol < median | 177, −0.75% | 652, +0.48% | — |
| asset vol >= median | 178, **−3.94%** | 652, **+2.61%** | **no — reversed** |

## What survived: one thing, and it is a filter, not an edge

**Market regime.** In both periods, breakouts do materially worse while BTC is
below its own 100-day line:

- recent: **−4.41%** below vs **−1.18%** above — a 3.2-point spread
- five-year: **−0.51%** below vs **+1.69%** above — a 2.2-point spread

Same direction, comparable magnitude, two universes, two eras. That is the only
conditioner of the four that replicated.

**And it does not make the rule profitable.** Conditioned on BTC being in an
uptrend, the recent period is still **−1.18%** per trade — it merely stops being
*significantly* negative. The condition turns a measurable loser into a coin
flip. What it genuinely does is identify the state to stay out of.

## What did not survive, and why it matters more than what did

**Asset volatility reversed.** In the five-year set, high-volatility assets were
the good ones (+2.61% vs +0.48%). In the recent set they were the bad ones
(−3.94% vs −0.75%). Opposite signs, same rule, same asset class.

Had only one period been run — the seven-minute version of this question — that
would have read as a clean finding: *"trade breakouts on high-volatility
assets."* It is the exact shape of a discovery, and it is noise. That is what a
second period costs and what it buys.

## What changed in the code

`breakout_ledger.py` now stamps `btc_up` and `breadth` onto every sealed call,
and carries them onto the settled record. **Recorded, never acted on.** The
point is pre-registration: the forward record can test this condition later
without *re-cutting* the data, which is the whole difference between a
hypothesis and a fishing trip. The split is reported in every summary and
**gates nothing** — the verdict remains the whole record.

61 checks, 61/61 ×2.

## The observation, since that is what was asked for

Across five mechanism classes, ~2,800 variants, two timeframes, three universes
and two eras, the only thing that has replicated is **negative**: a
trend-following rule is worse than useless while the market's own trend is
down. Nothing has replicated positive.

That is a real observation about crypto and it is worth having. It is also not
a strategy, and the honest thing is to keep calling it what it is.

---

Nothing traded, armed, sized or wired. Analysis off-machine.
