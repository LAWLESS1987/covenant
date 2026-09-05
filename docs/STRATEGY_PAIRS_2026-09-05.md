# A third hypothesis, the same answer

**2026-09-05.** Asked for: "need to get the trading profitable prior" — before a
second operator joins on Sunday.

**Nothing survived.** Third mechanism, third time. Reproduce with:

```bash
python strategy_pairs.py --out docs/results/PAIRS_2026-09-05.txt
```

## Why pairs, and why long-only

The two classes already measured were *timing* (predict an asset from its own
past — `strategy_validate.py`, ~800 variants) and *relative strength* (rank the
basket, hold the leaders — `strategy_cross_sectional.py`, 288 variants). Both
failed all three tests. Searching either harder is how noise gets found.

Pairs relative value is a different claim: two assets that usually move
together have a spread that tends to revert, and the cheap leg tends to
recover. This account cannot short, so the rule is long-only — hold whichever
leg the z-score says is cheap, cash in between. That is a rotation, which
`guards.py` permits within a day's sale proceeds, at the same 100 bps a round
trip.

Sixty-six pairs times eighteen settings is **1,188 trials**, and the grid is
carried into the deflation. The hedge ratio is fitted on the first 40% of
dates and the rule scored only on the rest; in walk-forward the entire search
— pair, setting, and beta — happens inside each training fold.

## The bar, unchanged

| test | threshold | result |
|---|---|---|
| deflated Sharpe | ≥ 0.95 | **0.0000** — best 1.33 against 3.30 expected from 1,188 no-edge trials |
| walk-forward | majority of folds AND p ≤ 0.05 | **1 of 5** positive, p = 0.969, mean out-of-sample **−6.14%** |
| PBO (CSCV) | < 0.5 | **0.386** — pass |

PBO passing is worth a sentence because it is the first time any test has. It
says the in-sample winner lands above the out-of-sample median more often
than not — the *selection* is not worthless. But the thing selected still
loses money out of sample in four folds of five, and its Sharpe is
indistinguishable from the best of a thousand coin flips. One test of three
is not a survival, and the framework was built so that it cannot be read as
one.

## What this means for Sunday

The constitution, rule 2 (`docs/CONSTITUTION.md`): **"No claim of profit
edge."** `docs/PARTNER.md` tells the prospective second operator that the
constitution forbids one. After three mechanisms and 2,276 variants, none
has been measured. Making the second operator wait on a profit edge would
mean either making a claim the constitution forbids, or waiting for a result
that has not appeared in any class tried.

The second operator needs the ledger, the judge, the install and the
peering to work. None of those depends on a trade. The trader stays
disarmed, for a measured reason.
