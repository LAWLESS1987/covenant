# Rule 5, replayed over history — 2026-09-10

**Asked:** *"expedite with historical data, september 15th is the absolute cut
off to begin."*

**Done.** The answer took a day instead of months, and it is not the answer we
were hoping for.

## What was run

`rule5_backfill.py` walks `realdata/deep/` forward one day at a time and feeds
each day's 200-day regimes through **`signal_ledger.record_cycle`** — the same
function the live trader uses — into a separate ledger, then scores it with
**`signal_ledger.summary`**, the same scorer the gate reads. Same 200d
definition, same entry/exit arithmetic, same 130 bps round trip, same binomial
test. Not a second implementation: this project's recurring defect is two code
paths to one answer where one of them is not enforcing the rule.

Data: the twelve Kraken daily series verified for contiguity, duplicate
timestamps, OHLC sanity and 00:00 UTC alignment, with interior windows
re-fetched and diffed byte for byte. The three shorter overlapping files are
excluded by name — they are subsets and would count the same flips twice.

    assets   12   ADA ATOM AVAX CRO HBAR NEAR ONDO PEPE SOL WLFI XLM XRP
    window   2024-12-31 -> 2026-09-02   (611 days, 411 after the 200-bar warmup)

## The result

    settled calls      134        (Rule 5 wants 30 — the COUNT is 4.5x satisfied)
    wins                10/134    (7.5%)
    mean per call      -3.866%    after 130 bps round trip
    median             -5.352%
    mean before costs  -2.566%    <- costs are not what breaks it
    best / worst       +63.7% / -32.6%

    P(>= 10 wins | fair coin)  = 1.0000     the test Rule 5 applies
    P(<= 10 wins | fair coin)  = 1.8e-26    how unlikely this is by bad luck

**This is not "no edge detected". It is a strongly negative edge detected.** A
coin flip would have won ~67 of 134. The rule won 10. The probability of doing
that badly by chance is about 2 in 100,000,000,000,000,000,000,000,000.

And it loses **before** fees. Trading it more cheaply would not fix it.

## It agrees with the live ledger

The live sealed ledger holds one settled call: **−3.79%**. The historical replay
of 134 calls: **−3.87%**. Two independent samples, one of them genuinely sealed
before its outcome, landing within 0.08 points of each other.

It also agrees with the standing validation result: 2 hypothesis classes, ~1088
variants, nothing cleared walk-forward, deflation or PBO, with PBO 0.986 on a
cash-filtered variant.

Three separate routes, same conclusion.

## Per asset

    ADA    n=8   wins=1   mean=+1.47%
    SOL    n=4   wins=1   mean=+6.67%
    PEPE   n=10  wins=1   mean=-1.42%
    ATOM   n=23  wins=2   mean=-1.64%
    XRP    n=6   wins=1   mean=-2.64%
    XLM    n=18  wins=1   mean=-4.58%
    ONDO   n=34  wins=2   mean=-5.70%
    NEAR   n=23  wins=1   mean=-5.75%
    AVAX   n=7   wins=0   mean=-9.22%
    CRO    n=1   wins=0   mean=-15.72%

Two are positive, on 8 and 4 calls. Picking those two after seeing the table is
the definition of the overfitting PBO 0.986 already warned about.

## What this means for 15 September

**Rule 5 is not a bureaucratic delay. It is working, and it is right.** The gate
was built so that money would not go live on a rule nobody had scored. It has
now been scored, and it loses.

Expediting did not open the gate. It closed the question — in a day.

### What "begin" can honestly mean

1. **Do not run this timing rule live.** The evidence is now three-way
   consistent. Turning it on is choosing a measured negative expectation.
2. **Holding is already being in.** The book exists; the reserve floor and the
   frozen hold-only floors protect it. Nothing needs to be switched on for that
   to continue.
3. **Find a rule that clears this bar first.** The harness now exists and runs
   in seconds, so candidate rules can be scored against 134 real flips instead
   of waiting months. That is the productive use of the days before the 15th —
   though the standing result says do not expect a winner.
4. **Lower the gate anyway.** `min_sealed_signals` in `trader_config.json` is
   one line. It is the operator's decision, it is reversible, and it leaves a
   mark — which is exactly why it is the honest lever, rather than backfilling
   the sealed ledger to make a counter say 30.

**What this file will not do:** write to the live ledger. Every call here was
settled from prices already known when it ran. A signal sealed after the outcome
is not a sealed signal, and mixing the two would make `sealed_signals`
permanently unreadable as evidence. `rule5_backfill.py` refuses if pointed at
the live path.

## Reproduce

```
python rule5_backfill.py --per-asset
```
