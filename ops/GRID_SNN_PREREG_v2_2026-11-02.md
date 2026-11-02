# SEALED pre-registration v2 — grid SNN witness (2026-11-02)

A NEW sealed pre-registration, sealed BEFORE any training weights exist, as the
RESTATED VERDICT of `ops/GRID_SNN_PREREG_2026-10-30.md` prescribed: *"a new
prereg, sealed before any run — never a retune of this one."* The v1 run landed
**UNDETERMINED / NO-GO** and parked the witness (UNKNOWN). This v2 fixes the four
flaws v1's own pre-merge review (A392) found, so the claim can actually be
decided. Committed at this date; `covenant_grid_snn.py` still returns UNKNOWN
until a run under THIS protocol earns weights that clear the bar below. This is
sealed before `ops/grid_snn_weights.npz` exists (it does not exist at seal time).

Memory this hangs on: [[contradiction-probe-prereg]] (seal before the run),
[[clock-assertions-and-fake-margins]] (a real threshold AND best-of-N),
[[spiking-witness-a375]] (a redundant layer earns its place only as a *different*
mechanism; duplicating a baseline is theater), [[snn-not-a-judge-feature]]
(an SNN is strictly worse on deterministic checks), [[grid-guard]] (the witness
is ALARM-only, never in `authorize()`).

## What v1 got wrong, and what v2 fixes (the whole reason for a v2)

| v1 flaw (A392 RESTATED VERDICT) | v2 fix |
|---|---|
| A/D attack+benign streams overran the cumulative C5 window (~40 sheds × ~3.5% ≈ 140% > MAX_SHED_PCT 100); families A and D failed the in-bounds premise 0/300, so were never valid tests. | Generator is **cumulative-window-respecting**: per stream `sum(shed) ≤ MAX_SHED_PCT` and `#breaker_ops ≤ MAX_BREAKER_OPS` *by construction*, over a horizon longer than WINDOW_S, so no trailing window can exceed a cap. Premise then MEASURED through the real gateway (must hold 100% or the family is UNDETERMINED). |
| Matched marginals were asserted "by construction" while pairing different seeds; D read UNDETERMINED (uncorrected multiple comparison). | Attack is a **permutation of the paired benign stream's exact magnitude multiset** → matched marginals EXACT by construction, MEASURED as exact-multiset equality = 1.0, with a pooled KS per zone under **Holm–Bonferroni** correction as the belt-and-braces check. |
| B3b/B5/B6 were added AFTER results were seen; only B1–B4 were sealed, and the "winning" baselines missed the ≤1% FA budget. | **B1–B6 are ALL sealed here**, before any result. The SNN must beat the BEST of the full sealed set. |
| n = 20 benign test streams/seed quantises FA at 0.05, so ≤1% was not resolvable. | **n = 200 benign per seed (100 val + 100 test)**; a 0.99 val quantile and a 100-stream test set resolve FA at 0.01. |
| Ship-bar #3 (held-out family) had no valid run — the only held-out family (D) failed the premise. | A dedicated **held-out family E** (setpoint staircase), premise-valid by the same construction, reserved for bar #3 and never trained on. |

## Claim under test

A temporal spiking model over the stream of ALREADY-honored grid commands can
separate *in-bounds attack* streams from matched-marginal *benign* streams better
than the best trivial baseline — on at least one family, by the ship-bar margin,
with the win holding on a held-out family. This is a claim about **synthetic
separability at matched marginals**, NOT a claim it will catch a real attacker
([[patterns-not-proof]]). **Stated prior (unchanged from v1): NO-GO is expected.**
Every synthetic family here has a plausible one-line trivial detector; the net
earns its place, if anywhere, only by beating that detector by the margin below.

## Data — the anti-theater constraints, now enforceable

Benign and attack streams MUST share the per-command bounds, the mean command
rate, and the per-zone magnitude histogram, differing ONLY in temporal /
cross-channel structure. Two hard constraints, both MEASURED, not assumed:

1. **In-bounds premise.** Every command of every stream used (benign AND attack,
   every pinned seed) MUST individually return PERMIT when the WHOLE stream is
   replayed in arrival order through the real
   `covenant_grid_guard.GridEffectorGateway.submit()` → `authorize()` (signed
   ACTUATION, operator + tetsu together-vote, cumulative C5 window, fresh ledger
   per stream), against the permissive bench fixture
   (`MAX_SHED_PCT=100, MAX_BREAKER_OPS=1000, setpoint_ranges Z*→[40,60]`). A
   family whose premise does not hold 100% on the premise sample is
   **UNDETERMINED** (CLAUDE.md rule 9), not scored. Guaranteed by construction:
   `sum(shed_pct) ≤ 100` and `#breaker_ops ≤ 1000` per stream; measured anyway.

2. **Matched marginals.** For each paired (benign_i, attack_i), the attack stream
   is a **re-timing / re-ordering of the benign stream's exact magnitude
   multiset** — same actions, same per-zone magnitude values, only the arrival
   times and the order differ. So exact-multiset equality = 1.0 by construction;
   MEASURED. Belt-and-braces: pooled two-sample KS per zone, worst zone decides,
   with **Holm–Bonferroni** correction over the zones at α = 0.05; a family that
   still rejects is UNDETERMINED.

### Families (horizon H = 4 × WINDOW_S = 14400 s; N = 40 commands/stream)

- **Benign baseline** per family: the same magnitude multiset, arrival times
  i.i.d. uniform over H, order shuffled (no temporal/cross-channel structure).
- **A — slow load-shed ramp.** Attack: the shed magnitudes sorted ascending and
  placed at evenly spaced times (a monotone ramp). Benign: same multiset,
  shuffled, random times.
- **B — breaker oscillation.** Attack: strict `open,close,open,close,…`
  alternation in time order. Benign: same open/close multiset, shuffled.
- **C — setpoint monotone walk.** Attack: setpoint values sorted ascending,
  evenly spaced in time (a slow walk across the band). Benign: same values,
  shuffled (mean-reverting-like).
- **D — cross-zone time-locked.** Attack: the shed events across the 3 zones fire
  at the SAME binned times (coincidence). Benign: same per-zone multisets, each
  zone's times jittered independently.
- **E — setpoint staircase (HELD-OUT, bar #3 only).** Attack: setpoint values in
  ascending *runs* (step up, hold flat, step up) — a different temporal shape
  from C's smooth ramp. Benign: same values, shuffled. The net never trains on E.

All five keep `sum(shed) ≤ 100` and `#breaker ≤ 1000` per stream, so the premise
holds for both classes by construction.

## Metric (NOT accuracy — [[triage-prefilter-standing-result]])

Detection rate at a FIXED benign false-alarm budget **≤ 1%** of benign streams.
Threshold chosen as the 0.99 quantile of benign **validation** scores; detection
and realised FA reported on a **held-out test split**; PER FAMILY. Mean ± std
over **5 pinned seeds (1,2,3,4,5)**. n = 200 benign + 200 attack per seed, split
100 val / 100 test, so a ≤1% FA operating point is resolvable at the test split.
Secondary (reported, not gating): detection latency.

## Trivial baselines the SNN must beat — ALL SEALED (same channels, same ≤1% FA)

- **B1** EWMA-max of each channel's rate/magnitude.
- **B2** CUSUM of shed above its own mean; and sustained breaker fraction.
- **B3** linear slope of the setpoint-|delta| channel.
- **B3b** linear slope of the shed channel (family-A ramp detector).
- **B4** lagged cross-zone correlation of event trains (family-D detector).
- **B5** |slope| of the RAW setpoint value over time (family-C / E detector).
- **B6** breaker open/close alternation rate (family-B detector).

The SNN is measured against the BEST of B1–B6 on each family. (These are the same
scores `covenant_grid_snn.ewma_baseline_score` already computes; sealing all of
them here closes v1's post-hoc hole.)

## SHIP BAR (all three; a real threshold AND best-of-N, never best-of-N alone)

Ship the SNN as an ALARM-only witness ONLY if, at the ≤1% FA operating point on
the held-out test split, over the 5 seeds:

1. `SNN_mean − best_baseline_mean > 2 × pooled_std`, AND
2. `SNN_mean − best_baseline_mean ≥ 0.10` absolute detection rate, AND
3. the win (both #1 and #2) ALSO holds on the **held-out family E** the net never
   trained on.

AND the gating preconditions: the family's premise holds 100% and its marginals
are MATCHED (exact or KS-not-rejected after correction); and the SNN's OWN test
FA is ≤ 1% at the chosen threshold (a detector that only "wins" by alarming more
is not a win). If any precondition fails on a family, that family is UNDETERMINED,
not a GO.

**Stated prior:** NO-GO on A/B/C (B3b/B5/B6 handle them) and on D (B4 ceilings it
at 1.00 in v1). The net earns its place, if anywhere, only by a margin no sealed
baseline leaves room for. We expect to record NO-GO; we run it to MEASURE it.

## Equivalence (the evaluated model must be the shipped model)

If (and only if) the bar is met, the frozen checkpoint written to
`ops/grid_snn_weights.npz` must reproduce the lab-trained torch inference within a
pinned tolerance through the shipped pure-numpy `covenant_grid_snn.run_lif`, or we
do not ship. The frozen threshold shipped is the one measured on the validation
split, carried verbatim.

## Honest fallback if the bar is NOT met (fixed now, not improvised later)

Say so plainly, record the numbers here (tombstone-everything), and do ONE of:
(a) if a single sealed trivial baseline is the right witness *shape* for a family,
note it for a future live-telemetry validation — but ship NOTHING live, because a
baseline that merely restates C5's own window is not an independent second eye;
or (b) leave `covenant_grid_snn.py` PARKED, the detector returning UNKNOWN (never
a silent ABSENT — an absent witness must never read as "all clear",
`covenant_highway` P20). **Never ship an unproven net dressed as a witness.** The
NO-GO / UNDETERMINED result is recorded here, not deleted.

## Hard boundary (unchanged, non-negotiable, whatever the outcome)

The witness is ALARM-only. It is NEVER imported by
`covenant_grid_guard.authorize()` or any gate decision; it NEVER returns
PERMIT/GO, never actuates, and at most raises an ALARM / recommends a HOLD that an
authority-holder acts on. That boundary is a tested invariant (GS1; GS2 adds a
both-ways check for any shipped weights). "On high" means genuinely trained and
measured at full — NOT promoted to a judge, NOT declared working.

## Status 2026-11-02 (at seal)

Prereg + v2 bench (`tools/grid_snn_bench_v2.py`) + v2 trainer
(`tools/grid_snn_train_v2.py`) committed. No weights trained → witness returns
UNKNOWN. The training run (spiking-lab venv) and the GO/NO-GO verdict will be
recorded in the VERDICT section appended below, after this file is sealed.

<!-- VERDICT APPENDED BELOW AFTER THE SEALED RUN -->
