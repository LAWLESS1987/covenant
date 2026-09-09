# "Make it 7 seconds." Done — and the fast answer contradicted the slow one. 2026-09-07

**Asked:** compress the 7-month forward test to 7 hours, 7 minutes, 7 seconds.

**What happened:** the 7-second version was run. It **refuted** the finding it
was meant to accelerate, and it is a correction against this loop's own
document from earlier the same day.

---

## 1. The correction, first

`BREAKOUT_GAUNTLET_2026-09-07.md` reported breakout-100 as *"the only thing in
this project's history that has cleanly separated from its own null"* — beating
shuffled data by +123 to +160 points, DSR 0.7855, on **33 assets over 5.7
years**.

Re-run on **275 assets over a recent 10-month window** (2025-11-12 → 2026-09-06,
every live OKX USDT pair with ≥160 daily bars, recent listings included so the
survivorship filter is far weaker):

| | trades | mean/trade | 95% bootstrap CI |
|---|---|---|---|
| **real data** | 355 | **−2.351%** | **[−3.567%, −1.080%]** |
| shuffled null, seed 0 | 573 | −1.768% | [−2.292%, −1.193%] |
| shuffled null, seed 1 | 489 | −1.852% | [−2.359%, −1.282%] |
| shuffled null, seed 2 | 541 | −1.643% | [−2.277%, −0.972%] |

**The real data is significantly negative, and it is WORSE than its own
shuffled null.** Win rate fell from 33.1% to 23.4%; the median trade from
−2.28% to −3.12%. On the 5-year survivor set the top five trades supplied +36%
of the return; here the extreme trades subtract.

**The most likely reading, stated plainly:** the 5-year result was
**2021 plus survivorship**. Thirty-six percent of its return came from five
trades, and those trades were in the alt season. Take 2021 out and widen the
universe to include the coins that were not selected for having survived, and
the separation from noise disappears — and inverts.

For context on the window: buy-and-hold across those same 275 assets had a
**median of −11.9%**, with only 37% of assets up. It was a bad market, and
breakout's *smaller* loss is the risk-control property showing again. But
per-trade it is negative, and it is below its own null. That is not an edge
having a bad quarter. That is an edge that was not there.

## 2. So: 7 hours, 7 minutes, 7 seconds?

**7 seconds already existed.** It is called a backtest, and this project has run
several thousand variants of them. The trouble is not that they are slow. It is
that this afternoon two backtests of the same rule, on the same asset class,
gave opposite answers — +1.55% per trade on one universe, −2.35% on another.
A method that can be re-cut until it agrees with you is not evidence.

The three ways to actually compress a forward test, and what each costs:

| lever | speed-up | what it costs |
|---|---|---|
| **more assets** | sub-linear | OKX lists ~395 live USDT pairs *in total*, and they are heavily correlated. 275 assets is not 275 independent draws — the same correction that took the Friday effect from t = 5.33 to t = 2.57. Realistically 7 months → 3–4, not seconds. |
| **faster bars** | ~24× on hourly | already measured: 848 intraday variants, **DSR 0.0000 on 16 of 16**, and 130 bps against ~1% moves is fatal arithmetic. You would be validating a different and worse rule quickly. |
| **lower the bar** | instant | the cheat. `signal_ledger.py` names it: the gate *"could not clear on evidence, only by someone lowering the number."* |

**You cannot buy statistical power with impatience.** 863 observations of a
1:10 signal-to-noise process is a rate limit set by the world, not by the code.

## 3. What CAN be fast, and it is not nothing

- **The operational loop.** `breakout_ledger.py --record` is seconds a day.
- **The decision.** The timeline is now a computable date, not a vibe: the
  ledger recomputes the required n from live data every run.
- **Refutation.** This document took about twenty minutes and it killed a
  finding. Fast evidence is excellent at *destroying* claims and poor at
  *establishing* them, and that asymmetry is the whole reason the forward test
  is slow.

## 4. Where the breakout ledger stands now

Unchanged and still worth having — arguably more so. Its job was never to
confirm the rule; it was to settle it. The backtest evidence has now failed to
replicate, so the forward record is the only instrument left that cannot be
re-cut. If breakout is real it will show up; if it was 2021, it will not.

What changes is the expectation. An hour ago this was "the one survivor, worth
sealing forward." It is now "a candidate whose historical support did not
survive a wider, more recent universe." The gate (DSR ≥ 0.95, and 0.7855 was
already short) does not move.

---

Nothing was traded, armed, sized or wired. Data and analysis off-machine.
