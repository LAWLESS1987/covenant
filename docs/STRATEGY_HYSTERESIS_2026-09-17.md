# Hypothesis class 5: a confirmation band on the 200-day regime rule

**Nothing survived.** Fifth mechanism, fifth time. Reproduce with:

```
python tools/strategy_hysteresis.py
```

This one is recorded more fully than the previous four, because unlike them it
began from a real defect in how the live rule is measured, and that defect is
still open.

---

## Where the hypothesis came from

Not from a screen of ideas. From `ops/rule5_backfill_ledger.jsonl`, which holds
**134 settled outcomes** across 10 symbols and 411 read days (2025-07-19 →
2026-09-02) — 27 times the evidence in the 5 settled signals the live Rule 5
gate reports.

Bucketed by holding period, the ledger says something very loud:

| held | n | win | mean after costs |
|---|---|---|---|
| 1-2d | 55 | 0.0% | -5.348% |
| 3-7d | 35 | 0.0% | -7.251% |
| 8-30d | 28 | 7.1% | -8.206% |
| **31d+** | **16** | **50.0%** | **+16.226%** |

118 of 134 round trips lasted a month or less **on a 200-day signal**, and they
lost almost without exception. The rule turns over 11.9 times per symbol per
year on an indicator with a 200-day memory.

**That slice is lookahead-biased and is not a strategy.** Holding period is not
knowable at entry — it is set by when the regime next flips, which is in the
future. "Trade only the ones that last 31 days" cannot be executed. It is a
diagnosis, not a rule.

The causal form of the same idea *is* executable: only flip when the close is
more than k% past the line. That is decidable at entry, so it can be tested.

## What was tested

Settle-on-flip with a hysteresis band of k, on all 19 daily series in
`private/data/`, 130 bps round trip — the same cost figure the ledger uses.

Two controls, because a rule that improves on everything has found nothing:

1. a per-symbol random walk with matched drift and daily volatility;
2. a walk-forward split — choose k on the first half, score on the second.

## Result

```
band      n     mean%    win%       t      random-walk control
0%      130    -2.238    10.0   -1.45    n=510 mean  -4.186%  t -4.61
1%       92    -2.052    14.1   -0.94    n=389 mean  -5.182%  t -4.39
2%       76    -1.851    15.8   -0.71    n=310 mean  -6.422%  t -4.36
3%       53    -2.990    17.0   -0.91    n=261 mean  -7.051%  t -3.98
5%       35    -2.612    22.9   -0.55    n=190 mean  -9.702%  t -4.45
7%       20    -1.060    35.0   -0.15    n=145 mean -12.087%  t -4.17
10%      16    -1.356    43.8   -0.16    n= 95 mean -13.451%  t -3.03

WALK-FORWARD: band chosen on first half -> 0% (all bands negative in train)
  TEST (held out): n=27  mean -6.809%  win 0.0%  t -9.87
  TEST baseline  : n=27  mean -6.809%  win 0.0%  t -9.87
```

The diagnosis was right about the mechanism and **wrong about the remedy**. The
band does what whipsaw theory predicts — win rate climbs from 10% to 43.8% as it
widens — and the mean never crosses zero. Widening the band removes the bad
trades and the good ones with them. Walk-forward selects no band at all.

## The one positive result, held as suggestive and not as a finding

The rule loses substantially **less** on the real series than on random walks
with matched drift and volatility: -2.2% against -4.2% at band 0, widening to a
12-point gap at band 10%. The 200-day line does carry information about these
series. It never carries enough to clear 130 bps.

**Why this is not claimed as a finding.** The controls inherit the same negative
drift as the real series, so a trend rule is penalised in both and the
comparison is confounded by drift rather than clean of it. A zero-drift control
would separate the two. That has not been run.

## The measurement defect this uncovered, which is still open

**The first call recorded for each symbol is an initialisation, not a signal.**
No flip generated it; the ledger simply opens a call at whatever regime holds
when the symbol first appears, at whatever price it happens to sit. ADA's first
long opened at 0.858816 against a 200-day line of 0.746721 — **15% above the
line** — and was then exited at the boundary, surrendering the whole descent as
arithmetic rather than as market direction. Those 10 calls average **-17.190%**.

This matters because the exit has a condition and the entry does not. Every call
exits at the 200-day boundary; it opens wherever price stands inside a regime.
Whichever side is entered far from the line gives that distance up by
construction.

**It is recorded and not fixed, deliberately.** Excluding those 10 calls
improves the mean from -3.866% to **-2.792%**, and the record they gate is the
record that decides whether money moves. A cleanup that improves a number
guarding a decision is indistinguishable from moving a check to make it pass,
and the operator's standing rule forbids it. It is written here so the decision
is his, made knowingly.

**It changes no conclusion either way.** With the 10 removed, the remaining 124
chained calls still run **-2.792% mean at an 8.1% win rate**. Nothing is
rescued; only the size of the loss moves.

## Standing position after this

Five hypothesis classes tested, five refuted:

| class | recorded |
|---|---|
| trend / regime | `strategy-validation-2026-09-03` |
| cross-sectional | `docs/STRATEGY_CROSS_SECTIONAL_2026-09-04.md` |
| pairs | `docs/STRATEGY_PAIRS_2026-09-05.md` |
| Fibonacci (+ random-walk and placebo controls) | 2026-09-10 |
| **hysteresis on the regime rule** | **this document** |

The trader stays disarmed. Rule 5 stands at 5 settled of 30 required, 0 wins,
p = 1.000 — and the 134-outcome backfill says the shortfall is not a lack of
data. It is that the thing being counted has no edge to find.

**What "better trading" can honestly mean here.** Not a better strategy: five
classes have now been put down, and the deepest evidence base in the repository
argues against the one that is wired up. It can mean better *measurement* — the
initialisation defect above, a zero-drift control, and a signal ledger whose
entries carry a condition rather than only its exits. Those are repairs, and
they are what readiness looks like while the gate is correctly shut.

---

## Addendum, same day: "some short trading is fine if it covers fees"

The operator's reading of the ledger was right about the data. Shorts are the
only positive line in it: 66 shorts at **+0.583% mean after the 130 bps**,
against 68 longs at -8.185%.

Tested with `python tools/strategy_shortonly.py`. One rule, one benchmark.

**The benchmark is what decides it.** These assets fell hard over the window, so
any short wins and "shorts made money" is not a finding. The only question that
separates an edge from a direction: *does the rule's shorting beat simply being
short the whole time?*

```
FULL SAMPLE    rule n=71  mean +3.149%  win 21.1%  t +1.17
               beats always-short on 0 of 19 symbols

HELD-OUT HALF  rule n=22  mean -6.293%  win 18.2%  t -2.89
               always-short there: +3.620% mean
```

**Zero of nineteen.** Being short throughout beat the rule on every asset. The
rule is short 83% of days, so it forgoes 17% of the fall sitting flat and pays
130 bps to re-enter.

The held-out half is the decisive part. Always-short returns only +3.620% there,
so the second half was **not** a strong bear market -- and in it the rule's
shorts ran **-6.293% at t = -2.89**. When the downward drift stopped, the shorts
stopped covering fees and began losing significantly.

So the +0.583% was not the rule covering its fees. It was the bear market paying
them, in-sample, in a window that has ended.

**Stated in fairness:** always-short is a yardstick, not a proposal. It is not
investable on spot alts -- borrow and funding are not free and the loss is
unbounded. It is here only to tell an edge from a direction, which is the one
thing the ledger's +0.583% could not do on its own.
