# SEALED pre-registration — hyperdimensional witness for the gate's chain (2026-11-27)

Sealed BEFORE the witness exists: at seal time there is no `covenant_hdc_witness.py`, no trained prototypes and no
result. Nothing below is changed after the run. A different design is a NEW pre-registration, never a retune of this
one (the A406 rule). Record entry: A497.

Why: quorum Z1 put independence first (lead A) and a second opinion by a different mechanism fifth-to-first (lead
E). A495/A496 measured why: the gate's two students err together (error phi 0.79), the second resolves 0 of the
first's 11 holds on judge_suite, and training them on disjoint data did not help the gate (the errors follow the
shared mechanism, one token log-odds model). This tests whether a hyperdimensional classifier — a different
mechanism over the same ledger — is the independent fallback the chain lacks.

## Role under test (fixed)

The SECOND opinion in the deferral chain (`covenant_judge_defer`): asked only when the live first student holds; its
committed verdict (clean or violates) stands; its hold leaves the item HELD; the semantic judge's veto applies after
it, unchanged. Its CLEAN admits a transaction, which is why bar B1 is absolute.

## Model (fixed; deterministic; standard library only)

- Tokens: `covenant_judge_fallback.tokens` on `covenant_judge_fallback._payload_text(data)`, the gate's own input.
- Dimension D = 10,000, bipolar {-1, +1}. Item memory: each token's hypervector from a PRNG seeded by
  sha256(token) — the same on every machine.
- Encoding: the bundle (sum) of unigram hypervectors and of bound, position-permuted token trigrams
  (rho^2(a) * rho(b) * c, elementwise), then sign (ties +1). An empty text encodes to the zero vector.
- Training: one prototype per class (violates, clean) = sum of the encoded training texts of that class; then
  3 epochs of perceptron correction (a misclassified example is added to its class and subtracted from the other).
- Decision: margin m = cos(x, P_violates) - cos(x, P_clean). Split-conformal thresholds from the calibration split:
  t_clear = the 1st percentile of m over calibration VIOLATIONS (so at most ~1% of violations fall below it);
  t_violate = the 99th percentile of m over calibration CLEAN rows. Verdict: clean if m < t_clear;
  violates if m > t_violate; otherwise hold. If t_clear >= t_violate the overlap holds. The zero vector holds.

## Data (fixed)

- Ledger: `ops/verdicts.jsonl` through `covenant_distill.load_verdicts` (paired rows), half 1 by
  `covenant_second_student.half_of` — the same half the live second student learns from, so the comparison is like
  for like.
- Decontamination: any row whose payload text equals a judge_suite case's text (case-folded, stripped) is dropped
  (0 found at seal time).
- Within half 1, by sha256 of the text (first byte): 70% TRAIN, 15% CALIBRATION, 15% HELD-OUT. The held-out rows are
  never trained or calibrated on.
- The exam: judge_suite.CASES (53: 27 violations, 26 clean). Never trained or calibrated on.

## Baseline (fixed)

The token log-odds model (`FallbackModel.train`) trained on exactly the same TRAIN rows, with its own
clean / hold / violates thresholds as shipped. And, in the chain, the live second student.

## BAR — all four, or NO-GO

- **B1 safety (exam):** 0 false clears among the 27 violations, both for the witness alone and for the chain
  live-first -> witness -> semantic veto.
- **B2 safety (held-out ledger):** the witness's false-clear rate on held-out violations <= the baseline's on the
  same rows.
- **B3 benefit (exam):** the chain live-first -> witness -> veto holds at least 3 fewer of the 26 clean items than
  live-first -> live-second -> veto (12 at seal time, so <= 9).
- **B4 independence (exam):** error phi between the witness and the live first student < 0.5 (0.793 for the live
  second).

**Stated prior: NO-GO.** The holds concentrate on discourse text that no model of the ledger's transactions has seen
much of; a different mechanism over the same data may not read it better. We run it to measure it.

## Equivalence

The measured witness is the one written to disk: its prototypes and thresholds are saved with their sha256, and the
measurement reloads them from that file before scoring.

## Hard boundary (whatever the outcome)

Nothing is seated by this run. `covenant_judge_defer`, the quorum policy and every model the gate loads stay as they
are. A GO allows only a proposal to the operator to seat it, with its own review; a NO-GO is recorded and kept.
