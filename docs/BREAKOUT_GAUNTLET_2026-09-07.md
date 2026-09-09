# The one survivor, put through the gauntlet. 2026-09-07

> **SUPERSEDED IN PART, SAME DAY.** The separation reported below does **not
> replicate** on 275 assets over a recent window: real data returns −2.35% per
> trade with a 95% CI of [−3.57%, −1.08%], which is *worse* than its own
> shuffled null (~−1.75%). The five-year result was most likely 2021 plus
> survivorship — 36% of its return came from five trades, all in the alt
> season. See `docs/SEVEN_SECONDS_2026-09-07.md`. Everything below stands as
> what was measured on the 33-asset five-year set; it is no longer a claim
> about the rule.

Breakout was the only rule in six years and ~2,800 tested variants that
separated from its own shuffled null (+123 to +160 points). That earned it a
test, not a promotion. Here is the test.

Universe: 33 assets, 2,086 daily bars, compounded, 130 bps round trip.

---

## Check 1 — risk-adjusted, not just total return

| | total | CAGR | max DD | Sharpe | Calmar | in market |
|---|---|---|---|---|---|---|
| BUY & HOLD | +639.6% | 42.0% | **−74.0%** | 0.92 | 0.57 | 100% |
| breakout 20d | +1.7% | 0.3% | −36.8% | 0.09 | 0.01 | 10.3% |
| breakout 55d | +45.0% | 6.7% | −23.2% | 0.61 | 0.29 | 5.7% |
| **breakout 100d** | +71.4% | 9.9% | **−12.8%** | **0.98** | **0.78** | **3.7%** |
| 50/50 hold + brk100 | +330.8% | 29.2% | −47.7% | **1.02** | 0.61 | 100% |

**The earlier verdict was too harsh.** Breakout 100d is not merely risk
control — it beats buy-and-hold on **Sharpe (0.98 vs 0.92)** and crushes it on
**Calmar (0.78 vs 0.57)** and drawdown (−12.8% vs −74.0%), while in the market
**3.7% of the time.** Correction filed against this loop's own wording of
2026-09-07: "risk control, not a return edge" understated it.

## Check 2 — deflated Sharpe: **0.7855**

The first non-zero deflated Sharpe in this project's history. Everything
previously tested returned 0.0000.

**It still fails.** The 0.95 bar is not cleared by 0.7855, and the gate does not
bend for the best result so far.

*(Corrected 2026-09-09: this cited `TRADING_POLICY.json` as the file holding the
bar. That file is not in the working tree and appears in zero commits of the
current history — it was removed in the 2026-09-05 redaction. The threshold the
conclusion rests on was therefore unreadable by anyone checking this document,
which is the one thing a gauntlet write-up cannot afford. The result is
unchanged; the citation was not.)*

## Check 3 — out of sample

| | 2021–23 | 2024–26 |
|---|---|---|
| breakout 100d | +47.8%, Sharpe 1.24 | +15.9%, Sharpe **0.64** |
| breakout 20d | +14.6%, Sharpe 0.35 | −11.3%, Sharpe **−0.32** |
| BUY & HOLD | +574.2%, Sharpe 1.30 | +9.7%, Sharpe **0.31** |

The long window degrades and survives; the short window dies. And in the recent
period breakout 100d's risk-adjusted return (0.64) **beat holding's (0.31)**.

## Check 4 — where the money actually comes from, and this is the one that decides it

1,304 trades, 33 assets, 5.7 years — a real sample, not a thin one:

- **win rate 33.1%** — it loses two trades out of three
- **median trade −2.28%** — the *typical* trade loses money
- mean trade +1.55%, mean hold **2.0 days**, ~229 trades/year
- best +220.2%, worst −35.8%
- **the top 5 trades supply 36% of the entire return**

That is the trend-follower's shape: lose small constantly, win enormous rarely.
It is a real structure — it is how managed futures has always worked — and it
carries a hard consequence. **The edge does not live in 1,304 observations. It
lives in about five.** No backtest can separate "this captures tail momentum"
from "the 2021 alt season produced five monsters", because it only has the one
history to look at.

### And at this account's size

The caps are $25 per order. Run at those caps: ~229 trades/year × $25 × mean
+1.55% ≈ **+$89 a year** on a $3,889 book — about **2.3%**, before any slippage
beyond what is modelled, and only if the tail recurs. A +220% winner at $25 adds
**$55**.

The edge may be real. At this size it is worth about ninety dollars a year, and
it is paid for by sitting through roughly 150 losing trades annually.

---

## What this changes, and what it does not

**Changes:** the honest summary of this project is no longer "nothing has ever
separated from noise." One thing has, it is long-window breakout momentum, and
it is better risk-adjusted than holding. That is a real finding and it should be
recorded as one.

**Does not change:** it fails the DSR gate (0.7855 < 0.95). It is not wired to
anything. Its return concentration means the backtest is weaker evidence than
its trade count suggests. And survivorship bias inflates the comparison —
though here it cuts *toward* breakout, since the dead coins that are missing
would have hurt buy-and-hold most.

## The counter, and what refining it found

`breakout_ledger.py` (433 lines) + `test_breakout_ledger.py` (**50 checks,
50/50 ×2** in the deployment folder), wired into `run_all_tests.sh` and verified
through the runner's own `run()` in both directions. Four findings from the
refinement pass, in the order they hurt:

**1. The file promised a flag it did not have.** Its USAGE block advertised
`python breakout_ledger.py --record`; the parser had only `--verify` and
`--json`. That is precisely the class `test_g2_promised_commands.py` exists to
catch — *"on 2026-09-02 the checker was found deleted from disk while four
documents went on promising it."* `--record` is now real: it pulls the most
liquid OKX spot pairs, fetches `WINDOW+2` daily bars each, drops the forming
bar, and runs a cycle. The suite now asserts that **every flag named in USAGE
exists in the parser**, so the promise cannot drift from the code again.

**2. Survivorship bias walks back in through the exit.** A forward record is
immune to the bias that ruins backtests — you record what exists at the time —
*only if you also close what stops existing*. An asset that is delisted or
halted is overwhelmingly one that collapsed; leaving its call open forever means
the loss never enters the record. So each cycle writes a small `marks` record
carrying the current price of every open call, and `settle_stale()` closes any
call whose asset has been unquoted for 7 days **at its last marked price**.
Settling at the entry price instead would score every collapse as exactly zero,
which is worse than either alternative. Stale settlements are counted and
reported separately.

**3. A partial universe is a biased universe.** If under 80% of the watchlist
answers, `fetch_quotes` raises and the day is not recorded at all — rather than
opening and settling calls on whichever subset happened to respond.

**4. The 863 floor was a point estimate, so it now adapts.** 863 came from one
historical sd/mean ratio. `summary()` recomputes the required n from the *live*
record and, if the live ratio is worse, reports the larger number and keeps
blocking. The bootstrap CI is also checked on two seeds: if they disagree about
whether zero is inside it, the verdict is "not yet".

**PRE-REFINEMENT RECORD: 27 passed / 2 failed, then abort** — the two failures
are the stale-settlement checks, which is the finding that mattered.

**Verified live:** `--record --watchlist 12` run from L's own machine reached
OKX, read 11 of 12 pairs (above the 80% floor), opened no calls (nothing at a
100-day high), and wrote a correctly chained record. First real network
execution of anything built in this session.

## The proceed that is actually available

**Seal it forward. Do not wire it.**

`signal_ledger.py` already exists and already does exactly this for the 200-day
regime rule. Breakout-100 is a different rule and would need its own counter,
but the machinery, the discipline and the gate are built. Record the calls live,
score them, and let the tail arrive or fail to. It costs nothing, it risks
nothing, and in a year it is either evidence or it is a closed question.

That is the same answer Rule 5 has been giving since 2026-09-06, now with
something worth pointing it at.
