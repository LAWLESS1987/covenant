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

## Amendment A1 — the "don't-cancel / amplify" treatment (pre-registered 2026-11-02, sealed before its run)

**Operator's observation, 2026-11-02 (relayed):** *"a spike that happens too often
cancels out, and I don't want to cancel it — test it and see what happens,"* then:
*"we've already run up tests — just amplify the amount we're allowing."*

So this is NOT a new apparatus: it reuses the sealed families, splits, baselines
B1–B6, the ≤1% FA metric, and the three ship-bar conditions above, UNCHANGED. It
adds exactly ONE change and reports the numbers both ways.

**Where the cancellation lives** (`covenant_grid_snn.run_lif`): a bin emits at most
one spike no matter how high the membrane (`sh = (Vh >= th_h)`), the membrane
subtracts the threshold back off each spike (`Vh -= sh*th_h`), and the alarm readout
is binarised (`alarm += 1` when `Va >= th_a`). A clustered or repeated burst of
in-bounds commands is thus flattened toward the same score as a sparse one.

**The ONE change (TREATMENT).** Let the count reflect the excess instead of capping
it: multi-spike per bin `k = floor(V/th_h)`, subtract `k*th_h`; alarm readout
`alarm += floor(Va/th_a)`. Shipped form: `run_lif(..., graded=True)` (opt-in; the
default is the binary CONTROL, unchanged and load-bearing for the shipped witness +
GS1). Scored form on the SEALED BAR: because the bar is measured on the snntorch
training net (not `run_lif` — see Equivalence), the corresponding one change there is
the hidden-layer **reset_mechanism "none"** (membrane accumulates, frequent drive is
not cancelled) vs the sealed CONTROL **"subtract"**. `tools/grid_snn_train_v2.py
--reset {subtract|none}`; `--reset subtract` reproduces the sealed control byte-for-byte.

**Directional hypothesis (stated before the run).** If the no-cancel treatment helps
anywhere, it helps where the attack signal is temporal CLUSTERING / repetition —
family **D** (cross-zone time-locked coincidence) above all, and perhaps **A** (the
ramp, whose spike density rises). On the single-channel order families (B, C) it is
not expected to help. The stated prior for A1 remains the v2 prior: **NO-GO expected.**

**Bar (unchanged + strictly-beats-control).** The treatment ships as the witness net
ONLY if, over the 5 seeds at the ≤1% FA operating point: it clears ship-bar
conditions #1 AND #2 AND #3 (held-out family E) above, its own test FA ≤ 1%, AND it
**strictly beats CONTROL** (treatment detection mean > control detection mean by more
than the pooled std) on the family it wins. Otherwise it is recorded here (NO-GO /
UNDETERMINED, tombstone-everything) and the witness stays parked (UNKNOWN); the
graded path remains opt-in and unshipped.

**Hard boundary unchanged:** whatever wins, the witness is ALARM-only and is never
imported by `authorize()` (GS1/GS2). A GO additionally requires the Equivalence port
(train the `run_lif` graded architecture directly, or match it within tolerance)
before any weights are written.

**Tombstone note (rule 10 / A346).** `covenant_grid_snn.run_lif` and
`tools/grid_snn_train_v2.py` were extended with the opt-in treatment switches AFTER
the v2 seal (commit 49e9163). The DEFAULTS reproduce the sealed control exactly
(GS1 16/16 unchanged); this amendment is itself sealed before any treatment weights
or numbers exist, so the treatment result cannot be chosen post-hoc.

## VERDICT — sealed run 2026-11-02: **NO-GO / UNDETERMINED (both CONTROL and Amendment A1)**

Run in the spiking-lab venv (torch 2.14.1+cpu, snntorch 1.0.0), 5 seeds, k=100
streams/split/class. Apparatus at n=200 (real gateway): in-bounds premise holds
**40/40 for both classes on every one of the 5 families**, matched marginals
**MATCHED-EXACT** on every family (KS p=1, Holm-ok) — so, unlike v1, every family is a
VALID test of the claim.

**CONTROL (reset=subtract — the net the sealed bar is defined on):**

| family | SNN det | SNN FA | best SEALED baseline | baseline det | margin | 2×pooled | bar1 | bar2 | SNN FA≤1% |
|---|---|---|---|---|---|---|---|---|---|
| A | 1.00 ± 0.00 | 0.006 | B3b shed-slope | 0.60 | 0.396 | 0.490 | ✗ | ✓ | ✓ |
| B | 1.00 ± 0.00 | 0.006 | B6 alternation | 1.00 | 0.000 | 0.000 | ✗ | ✗ | ✓ |
| C | 1.00 ± 0.00 | 0.008 | B5 value-slope | 1.00 | 0.000 | 0.000 | ✗ | ✗ | ✓ |
| D | 1.00 ± 0.00 | 0.020 | B4 cross-zone | 1.00 | 0.000 | 0.000 | ✗ | ✗ | ✗ |
| **E (held-out, bar #3)** | 1.00 | 0.010 | B5 value-slope | 1.00 | 0.000 | 0.000 | — | — | ✓ |

No family clears bars #1 AND #2 AND #3. **CONTROL = NO-GO.**

**Amendment A1 TREATMENT (reset=none — the operator's don't-cancel / amplify, ONE change):**

| family | SNN det | SNN FA | best SEALED baseline | baseline det | margin | 2×pooled | bar1 | bar2 | SNN FA≤1% |
|---|---|---|---|---|---|---|---|---|---|
| A | 1.00 ± 0.00 | 0.010 | B3b shed-slope | 0.60 | 0.396 | 0.490 | ✗ | ✓ | ✓ |
| B | 1.00 ± 0.00 | 0.016 | B6 alternation | 1.00 | 0.000 | 0.000 | ✗ | ✗ | ✗ |
| C | 1.00 ± 0.00 | 0.008 | B5 value-slope | 1.00 | 0.000 | 0.000 | ✗ | ✗ | ✓ |
| D | 1.00 ± 0.00 | 0.014 | B4 cross-zone | 1.00 | 0.000 | 0.000 | ✗ | ✗ | ✗ |
| **E (held-out, bar #3)** | **0.80** | 0.016 | B5 value-slope | 1.00 | **−0.200** | 0.283 | ✗ | ✗ | ✓ |

**A1 = NO-GO**, and it does NOT beat control: it ties control on the already-ceilinged
families (B, C, D) and on A, and it is **strictly worse on the held-out family E** (0.80
vs control's 1.00; one seed collapsed to 0.00; margin to the baseline −0.200). Removing
the reset let the accumulating membrane overfit the trained families and generalize worse
to the unseen one. **The operator's "amplify the amount we're allowing" hypothesis is NOT
borne out on this matched-marginal synthetic benchmark** — not because cancellation is
good, but because the trivial baselines already ceiling every family, so there is no
suppressed signal for a no-cancel net to recover, and the change costs stability on the
held-out family. Reported both ways, as asked. (The graded `run_lif` path stays opt-in
and unshipped; `--reset subtract` reproduces the sealed control byte-for-byte.)

### Fallback taken (prereg option b): the witness stays PARKED (UNKNOWN)

No weights were written to `ops/grid_snn_weights.npz`; `covenant_grid_snn.pattern_anomaly_state`
returns UNKNOWN (never a silent ABSENT). Neither the control net nor the A1 treatment
earns a place as a witness, so none ships. GS1 (boundary + UNKNOWN discipline) and GS2
(v2 apparatus + alarm-only boundary) stay green; the gate's sole authority remains the
deterministic C1–C7.

### The one genuine lead, recorded (not a GO)

On family **A** (the slow shed ramp) the trained net reaches 1.00 detection where the
best SEALED baseline (B3b shed-slope) reaches only ~0.60 at the ≤1% FA point — a real
edge. It still fails the ship bar: the margin (0.396) is below 2×pooled-std (0.490)
because B3b is noisy, bar #2 passes but bar #3 cannot (family E's baseline already
ceilings at 1.00, so the A-edge has nowhere to transfer and the net does not generalize
the ramp advantage to the staircase). This is exactly the "close but NO-GO" the seal
exists to surface: a within-family win that does not survive the held-out condition is
not a shippable witness. It is a lead for a future sealed prereg (a benign family whose
in-bounds ramp a one-line slope detector genuinely cannot catch), not evidence here.

### Caveats (recorded, not deleted — tombstone-everything)

1. **Synthetic separability at matched marginals, NOT a field claim** (patterns-not-proof).
   Real within-bounds attacks are unseen; no pattern witness ships live on synthetic
   data alone.
2. The scored net is the snntorch training net, not the shipped `run_lif` (the Equivalence
   port was never needed — NO-GO). A future GO must do that port within tolerance first.
3. Matched marginals are EXACT by construction here; the KS/Holm check is belt-and-braces
   and does not test the TIMING structure (that is the whole point of the families, which
   the baselines read directly). Measured, stated.

Recorded, not deleted. Witness remains UNKNOWN; the sealed bar stands for any future run.
