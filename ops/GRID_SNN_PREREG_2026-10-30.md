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
