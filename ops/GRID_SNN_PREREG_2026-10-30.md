# SEALED pre-registration — grid SNN witness (2026-10-30)

Sealed BEFORE any training weights exist, so the metric, baselines, seeds, and
ship bar cannot be chosen after seeing results (memory: contradiction-probe-prereg,
clock-assertions-and-fake-margins). Committed at this date; `covenant_grid_snn.py`
returns UNKNOWN until a run under this protocol earns weights that clear the bar.

## Claim under test
A temporal spiking model over the stream of ALREADY-honored grid commands can
separate *in-bounds attack* streams from matched-marginal *benign* streams better
than trivial baselines — specifically on cross-zone coincidence (family D). This
is a claim about synthetic separability, **NOT** a claim it will catch a real
attacker (patterns-not-proof).

## Data (matched-marginal — the anti-theater constraint)
Benign and attack streams MUST share per-command bounds, mean command rate, and
per-zone magnitude histograms, differing ONLY in temporal / cross-channel
structure. Every synthesized command MUST individually return PERMIT through
`covenant_grid_guard.authorize()` against a permissive bench fixture (asserted in
the generator) — that is the whole "in-bounds" premise. If matched marginals
cannot be enforced, the result is **UNDETERMINED** (CLAUDE.md rule 9), not a number.
- Benign: mean-reverting setpoint walk, sparse uncorrelated shed, breaker ops
  under cap, independent zones.
- A: slow load-shed riding the window cap. B: breaker oscillation at the ops cap.
  C: monotone setpoint walk across the allowed range. D: multi-zone events
  time-locked (each zone benign alone).

## Metric (NOT accuracy — memory triage-prefilter)
Detection rate at a FIXED benign false-alarm budget **≤ 1%** of benign streams.
Threshold chosen on a validation split; reported on a HELD-OUT test split; PER
FAMILY. Secondary: detection latency. Report mean ± std over **≥ 5 pinned seeds**.

## Trivial baselines the SNN must beat (same channels, same ≤1% FA)
- B1 EWMA of each channel's rate/magnitude.
- B2 CUSUM / sustained fraction of window near cap (extends C5 `_window()`).
- B3 linear slope over last-N setpoints (family C).
- B4 lagged cross-zone correlation of event trains (family D — the one the SNN
  must beat, since cross-zone temporal coincidence is where a lateral-inhibition
  circuit has an edge a per-channel EWMA structurally lacks).

## SHIP BAR (all three; a real threshold AND best-of-N, never best-of-N alone)
Ship the SNN as a witness ONLY if, at the ≤1% FA operating point on the held-out
test split, over ≥5 seeds:
1. `SNN_mean − best_baseline_mean > 2 × pooled_std`, AND
2. `SNN_mean − best_baseline_mean ≥ 0.10` absolute detection rate, AND
3. the win holds on a HELD-OUT attack family the net never trained on.

**Stated prior:** NO-GO is expected on A/B/C (low-order single-channel stats
handle them). The net earns its place, if anywhere, only on **family D vs B4**.

## Honest fallback if the bar is NOT met (fixed now, not improvised later)
Say so plainly, and do ONE of: (a) ship the winning trivial baseline as the
witness instead (a net that merely duplicates EWMA is theater — spiking-witness-a375);
or (b) park `covenant_grid_snn.py` labeled UNPROVEN with the detector returning
UNKNOWN (never a silent ABSENT). Never ship an unproven net dressed as a witness.
The NO-GO result is recorded, not deleted (tombstone-everything).

## Equivalence
The shipped pure-numpy `run_lif` must reproduce the lab-trained torch inference
within a pinned tolerance, or we do not ship (the evaluated model must be the
shipped model).

## Status 2026-10-30
Scaffold + this prereg committed. No weights trained yet → witness returns
UNKNOWN. Benchmark harness `tools/grid_snn_bench.py` and the training run (spiking
lab venv) are the next step; their result — GO or NO-GO — will be recorded here.

**Preliminary baseline run (2026-10-30, `tools/grid_snn_bench.py`; single seed set,
no held-out split, crude features — NOT yet the full sealed protocol):** every
synthesized attack command is individually in-bounds (premise holds). The trivial
**B4 baseline (lagged cross-zone correlation) already detects family D at 1.00 @
~1% false-alarm** — i.e. the one niche the SNN was hoped to fill appears ALREADY
saturated by a trivial detector, which *strengthens the NO-GO prior*. A/B/C scored
0.00 under the current crude features (feature/generator refinement is a later
tick). This is a signal, not the verdict; the full ≥5-seed held-out protocol and
the trained-SNN comparison remain. Recorded, not deleted (tombstone-everything).
> SUPERSEDED (A392-SNN-PREMISE-HOLDS, 2026-10-30): "premise holds" was not measured.
> The bench's permits() checked each command alone and never the real cumulative C5
> window; through the real gateway, families A and D fail the premise on 300/300
> streams (benign AND attack). See "RESTATED VERDICT" at the end.

**5-seed held-out protocol (2026-10-30, `tools/grid_snn_bench.py` `protocol()`):**
over seeds 1–5, with a val/test split and each baseline's threshold set at ≤1%
benign false-alarm on val, the trivial **B4 cross-zone-correlation baseline detects
family D at 1.00 ± 0.00 on the held-out test split (test FA ≈ 0.013)** — this
forecloses the SNN's one pre-registered candidate niche. Families A/B/C score
0.00 ± 0.00 for the best trivial baseline (feature/generator tuning, or genuinely
low matched-marginal signal — open, a later tick). **Leading conclusion: NO-GO for
the SNN as framed** — a trivial detector already ceilings family D, and A/B/C were
pre-registered as baseline territory, not SNN territory. To be confirmed by the
trained-net comparison (spiking-lab venv) before the verdict is sealed; the witness
stays UNKNOWN until then. Recorded, not deleted.

**Baselines completed (2026-10-30, tick 5): added a CUSUM and a shed-slope detector**
so the SNN is measured against the baselines' best shot (it must beat the *best*
trivial detector). Re-run: **family A is now caught by the shed-slope baseline
(0.97 ± 0.04)** — though test FA ≈ 0.047, above the ≤1% budget (a small-n threshold
artifact at n=60, needs larger n). **Family D stays saturated by B4 (1.00).**
Families B and C remain 0.00 — **but this reflects MISSING trivial detectors**
(a breaker-alternation autocorrelation for B; a raw-setpoint-*value* slope for C,
which the current `|delta|` encoding drops), **not** evidence of an SNN niche.
Reading a baseline/encoding gap as an SNN win is exactly the theater this prereg
guards against. **Conclusion unchanged and strengthened: NO-GO leading** — no family
has been shown to need a different mechanism. Remaining before sealing: complete the
B/C trivial detectors (expected to catch them) or run the trained net. Witness stays
UNKNOWN. Recorded, not deleted.

## VERDICT — sealed 2026-10-30: **NO-GO for the SNN witness**

> SUPERSEDED (A392-SNN-NOGO-BASIS, 2026-10-30, pre-merge review). Kept verbatim below.
> Its basis breaks this prereg's own rules: B3b, B5 and B6 were added AFTER results
> were seen (line 4 forbids choosing baselines then; only B1–B4 are sealed), the
> "winning" baselines missed the sealed ≤1% FA budget, and families A and D were never
> in-bounds. The witness outcome (parked, UNKNOWN) is unchanged; the reasoning is
> restated in "RESTATED VERDICT" at the end.

With the trivial baselines completed (B5 raw-setpoint-value slope, B6 breaker
alternation added tick 7), **every synthetic attack family is caught by a one-line
trivial detector** on the ≥5-seed held-out protocol:

| family | best trivial baseline | test detection | test FA |
|---|---|---|---|
| A | B3b shed-slope | 0.97 ± 0.04 | ~0.047 |
| B | B6 breaker-alternation | 1.00 ± 0.00 | ~0.047 |
| C | B5 setpoint-value-slope | 1.00 ± 0.00 | ~0.020 |
| D | B4 cross-zone-correlation | 1.00 ± 0.00 | ~0.013 |

The best baseline is at or near the ceiling on every family, so the SNN **cannot
clear the pre-registered ship bar** (beat the best baseline by >2σ AND ≥0.10 absolute)
on any family — there is no headroom. The trained-net run is therefore **moot for a
GO** and is not needed to seal this.

**Fallback taken (prereg option b):** the SNN stays PARKED; `grid_pattern_anomaly`
returns UNKNOWN (never a silent ABSENT). We do NOT ship the net as a witness — a
redundant layer earns its place only as a *different* mechanism, and here a trivial
detector already does the job ([[spiking-witness-a375]], [[snn-not-a-judge-feature]]).

**Caveats recorded (not deleted):** (1) test FA is ~2–5% at n=60 — a small-sample
threshold artifact; a larger-n run would tighten the baselines' FA toward ≤1%, it
would not create SNN headroom. (2) This is **synthetic separability at matched
marginals, NOT a field claim** — real within-bounds attacks are unseen (theater-risk
#1). The trivial-baseline ensemble is the right witness *shape* if real telemetry
ever validates it; until then no pattern witness ships live, and the gate's sole
authority stays the deterministic C1–C7.

## Trained-net confirmation (2026-10-30 16:29, `tools/grid_snn_train.py`, spiking-lab venv: torch 2.14.1+cpu, snntorch 1.0.0)

Small LIF net (10→32→1 Leaky, BCE on mean membrane), 5 seeds, train/val/test split,
threshold at the 99th percentile of held-out benign val scores:

| family | trained SNN test detection | test FA | best trivial baseline |
|---|---|---|---|
| A | 1.00 ± 0.00 | 0.010 | B3b shed-slope 0.97 ± 0.04 (FA 0.047) |
| B | **0.06 ± 0.04** | 0.110 | B6 alternation 1.00 |
| C | 1.00 ± 0.00 | 0.020 | B5 value-slope 1.00 |
| D | 0.99 ± 0.02 | 0.030 | B4 cross-zone 1.00 (FA 0.013) |
| D held-out (trained on A,B,C) | 0.98 | **0.100** | — |

Against the ship bar: the largest gain over the best baseline is +0.03 (A) — below both
the 0.10 absolute floor and 2× pooled std; the net is far WORSE on B (the encoding drops
open/close ORDER, which the one-line alternation baseline reads directly), ties C,
trails D, and the held-out-family test fails the ≤1% FA operating point (10%).
**VERDICT stands, now measured: NO-GO.** The witness stays parked (UNKNOWN). Weights were
NOT saved to `ops/grid_snn_weights.npz` — an unproven net is not shipped as a witness.
Recorded, not deleted.

## RESTATED VERDICT (2026-10-30, A392 — pre-merge review; supersedes the two sections above)

**Under this prereg as sealed, the result is UNDETERMINED, and in no reading is it a GO.
The witness stays parked: `grid_pattern_anomaly` returns UNKNOWN, no weights ship.**
The "NO-GO because a trivial detector catches every family" reasoning is withdrawn
(A392-SNN-NOGO-BASIS). What was actually measured:

1. **The in-bounds premise (lines 18–21), measured through the REAL gateway**
   (`tools/grid_snn_bench.py` `permits()`, rebuilt 2026-10-30: each whole stream replayed
   through `GridEffectorGateway.submit()` → `authorize()`, signed ACTUATION with operator
   + tetsu tokens, cumulative C5 window; 5 seeds × 60 = 300 streams per class per family):

   | family | benign streams all-PERMIT | attack streams all-PERMIT | why |
   |---|---|---|---|
   | A | 0/300 | 0/300 | ~40 sheds × ~3.5% ≈ 140% per window > MAX_SHED_PCT 100; first refusal at command ~27–30 |
   | B | 300/300 | 300/300 | — |
   | C | 300/300 | 300/300 | — |
   | D | 0/300 | 0/300 | same cumulative shed overrun as A |

   So **A and D were never in-bounds attacks**, and the old `permits()` that said they
   were checked each command alone (A392-SNN-PREMISE-HOLDS). Per line 20, A and D are
   UNDETERMINED as tests of this claim. D — the one family the stated prior gave the net
   a chance on (line 48) — is therefore untested, not foreclosed.

2. **Matched marginals (line 20)**, now measured rather than asserted (the bench's old
   docstring said "matched marginals by construction" while pairing different seeds —
   A392-SNN-MATCHED-BY-CONSTRUCTION): pooled per-zone two-sample KS, worst zone decides,
   UNDETERMINED at p < 0.05. A: p = 0.111; B: p = 1; C: p = 0.311 — distributional match.
   D: worst zone p = 0.0229 → **UNDETERMINED** (both D streams draw from the same
   `uniform(1,6)`; three zones at α = 0.05 with no correction, so this may be a false
   rejection — recorded as measured, the test was not changed after seeing it).

3. **On the two families whose premise holds (B, C), sealed baselines only (B1–B4):**

   | family | best SEALED baseline | trained SNN (test) | SNN test FA | post-hoc (exploratory) |
   |---|---|---|---|---|
   | B | 0.00 ± 0.00 (FA 0.000) | 0.06 ± 0.04 | 0.110 | B6 alternation 1.00 (FA 0.047) |
   | C | 0.00 ± 0.00 (FA 0.000) | 1.00 ± 0.00 | 0.020 | B5 value-slope 1.00 (FA 0.020) |

   B: the net fails outright. C: the net beats every sealed baseline by 1.00, but its test
   FA (0.020) is above the sealed ≤1% budget, and **ship-bar #3** (the win must hold on a
   held-out family the net never trained on) has **no valid run**: the only held-out run
   used D, which fails the premise. Bars #1–#2 met on C at an over-budget FA, bar #3
   untested ⇒ not a GO; formally UNDETERMINED.

4. **What the post-hoc baselines DO tell us** (exploratory, outside the seal): a one-line
   detector (B5) matches the net on C and another (B6) catches B, so if a future run is
   sealed, B5/B6 belong in its baseline list *before* any result is seen. That is a lesson
   for the next prereg, not evidence in this one.

**To make this decidable** (a new prereg, sealed before any run — never a retune of this
one): a generator whose A/D streams respect the cumulative window, a matched-marginal test
fixed in advance (with its multiple-comparison rule), B1–B6 sealed as baselines, a larger
benign test split so the ≤1% FA budget is resolvable (n = 20 benign test streams per seed
quantises FA at 0.05), and a held-out family that passes the premise.
