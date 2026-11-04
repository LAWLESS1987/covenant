# SEALED pre-registration — ethics-student SNN witness (sealed 2026-11-04)

**SEALED. Committed BEFORE any witness weights or Phase-0/Phase-1 results exist.** Operator's
go, verbatim: *"live not proposed."* This is the v5 staged design (octopus arms + per-arm
ablation, gated by a cheap non-spiking Phase 0), approved through five review rounds with the
originating session and the node review (Codex + Gemini). The design below is frozen; the only
thing appended after this seal is the VERDICT section (Phase 0 result, then Phase 1 if it runs).
The drafts (v1 human-synapse → v2 → v3 octopus+serotonin → v4 diverse-arms → v5 staged) are kept
in the session hand-over notes (tombstone-everything).

Discipline mirrors `ops/GRID_SNN_PREREG_v2_2026-11-02.md` (which landed NO-GO/UNDETERMINED and
PARKED its witness — the honest outcome this process is built to reach).

## Seal provenance (pinned; cannot move after this commit)

| what | value |
|---|---|
| sealed | 2026-11-04 |
| commit at seal | `d6e9764` |
| corpus (`ops/verdicts.jsonl`) | `corpus_sha = 68a3a57597f5` (4283 rows: 1987 violations, 2296 clean) |
| deployed student (`fallback_model.json`) | `deployed_student_sha = f245e9076146` |
| fold protocol | `tools/judge_eval.py::folds` VERBATIM (group by exact text, case+whitespace-folded) |
| run environment | spiking-lab venv (home `spiking/.venv`) — numpy 2.5.2, scipy 1.18.1, sklearn 1.9.1, torch 2.14.1+cpu, snntorch 1.0.0, brian2 2.10.1 |
| seeds | 1–5 |

Memory: [[octopus-leg-architecture]], [[contradiction-probe-prereg]],
[[clock-assertions-and-fake-margins]], [[spiking-witness-a375]], [[snn-not-a-judge-feature]],
[[triage-prefilter-standing-result]], [[patterns-not-proof]], [[spiking-lab]].

---

## Finding under test

`docs/JUDGE_EVALUATION.md`: over 1261 decided violations the student wrongly cleared 55; the
same-words naive Bayes cleared 54 of those same 55; the two-seat quorum dropped false-clear only
4.4%→4.3% (phi=0.602, OR=740, Fisher p=4.6e-56). **Question:** does a DIFFERENT substrate err on
DIFFERENT rows? **Prior: NO-GO / UNDETERMINED expected.** Order may carry little the bag-of-words
misses; biology does not guarantee decorrelation; P (the student's false-clears) is small.

---

## STAGED STRUCTURE

### Phase 0 — GATE: does ordered-sequence information decorrelate AT ALL? (cheap, non-spiking)

Run **BL3** (a non-spiking order-aware model on the ordered-token sequence — word/char n-gram
logistic regression, and/or a small GRU) against the deployed student FIRST. Phase 0 settles
whether adding ORDER to a simple model decorrelates its errors from the student MORE than the
same-words model (BL1) does.

**Phase 0 PASS (both required)**, at the threshold where BL3's false-conviction on held-out CLEAN
memos ≤ **C = 16.5%**, pooled over 5 seeds × grouped folds, bootstrap 95% CIs:
1. **Beats same-words:** phi(student-wrong, BL3-wrong) over both-decide violations is BELOW BL1's
   (0.602) with the CIs SEPARATED.
2. **Material joint reduction:** requiring (student ∧ BL3) to admit reduces the both-decide
   violation false-clear by **≥ 25%** vs student-alone.

**Phase 0 FAIL → STOP.** Record the honest finding — *"ordered-sequence information does not
decorrelate from the lexical student beyond same-words on this corpus; the heavy spiking build is
not justified"* — witness PARKED at UNKNOWN. A good, build-saving outcome.

### Phase 1 — the octopus (8 arms + ablation): runs ONLY on a Phase 0 PASS

Builds the spiking ensemble and asks whether the spiking substrate BEATS the BL3 that passed
Phase 0 (the stricter ship bar). BL3 is both the Phase 0 gate and the Phase 1 bar-#3 baseline.

---

## Hard boundary

Read-only second opinion; NEVER in judge/gate/quorum; UNKNOWN until the bar clears, never a silent
"clear" (`covenant_highway` P20); SNN-in-gate declined (A392; 2026-10-27 ×2). PC/spiking-lab only,
never the phone node; the lightweight pure-Python LIF `covenant_octopus` stays the node's. A GO
(unlikely) informs that lightweight arm; the heavy Brian2 net is not shipped to the node.

---

## Inputs & encoding

Corpus pinned above. **Ordered-token temporal reading** (frozen embedding, one token/time-step,
order by time-step order). No bag-of-words channel (the honest null). Phase 1 arms each read their
own pinned view of the sequence (proposed interleaved positions).

## Phase 1 — the eight arms (COBA-spiking, each ABLATABLE, Brian2)

Shared COBA substrate (E_L=−70,E_exc=0,E_inh=−80mV; V_th=−50,V_reset=−65; τ_m≈15ms; exc τ_decay≈5ms,
inh≈8ms; refractory≈3ms; constants pinned at seal). Light central integrator + supervised linear
readout (train rows only); reward-modulated arms also use labels via their modulator. Supervision
is via the integrator readout (always) + the A/B/C reward channels; labels drive training only,
train-only.

| arm | mechanism | Brian2 honesty |
|---|---|---|
| A | Serotonin (5-HT) reward-modulated STDP | faithful |
| B | Octopamine (OA) reward-modulated STDP, appetitive valence | faithful* |
| C | Dopamine (DA) reward-PREDICTION-ERROR (fly MB) | faithful; RPE predictor simplified |
| D | Electrical / gap-junction coupling (synchronization) | faithful |
| E | Predict-and-cancel (electric-fish corollary discharge / ELL) | PRINCIPLE only — declared approx |
| F | Graded / near-spikeless (C. elegans) + optional neuropeptide | APPROXIMATION; dropped-with-note if intractable |
| G | Plain COBA-spiking control | faithful |
| H | Plain COBA-spiking control (variance accounting) | faithful |

*A/B/C are the SAME three-factor reward-modulated-STDP family (A vs B = valence/sign; C adds a
prediction-error term) and MAY decorrelate similarly — the ablation TESTS it, does not assert it.
D, E, F are the genuinely different dynamics.

### Pre-registered per-arm ablation (Phase 1 primary deliverable)

Train the 8-arm ensemble; for each arm, leave-one-out at the integrator readout (re-fit only the
linear readout, not the spiking arms); report ΔM1/ΔM2/ΔM3 with bootstrap CIs. Findings:
(i) per-arm contribution ranked with CIs; (ii) do exotic arms (A–F) beat plain controls (G,H);
(iii) which of A–F has a decorrelation ΔM3 whose CI excludes zero. **Honest power:** with P≈60–90
across 8 arms, most ΔM CIs likely include zero → most per-arm results UNDETERMINED, reported as
such; no arm credited on a point estimate.

---

## Metric & ship bar (Phase 1, on the ENSEMBLE; locked)

P = student's decided false-clears. M1 catch rate at clean FC ≤ C; M2 joint false-clear; M3
error-decorrelation phi/OR vs BL1. Baselines sealed: BL1 same-words naive Bayes (floor), BL2
deployed student, **BL3 non-spiking order-aware (Phase 0 gate AND Phase 1 bar #3, decisive)**.
**SHIP BAR** at clean FC ≤ **C=16.5%**: (1) phi<0.30 / OR-CI excludes BL1; (2) joint false-clear
reduced ≥50% vs student-alone; (3) **beats BL3** by >2×pooled-std AND ≥0.10 absolute; (4) clean
FC ≤ C, availability stated; (5) #1–#4 ALSO hold on held-out **`injection`** category. Any failure
→ NO-GO/UNDETERMINED, witness PARKED. The ablation is reported regardless of ensemble GO/NO-GO.

---

## Held-out / power / equivalence / fallback / what-this-doesn't-measure

Grouped folds VERBATIM; all `injection` rows removed from Phase 1 training for bar #5;
paraphrase/template leakage is the stated unfixed limit. Pooled over folds×seeds, bootstrap CIs,
margins clear 2×pooled-std else UNDETERMINED (more likely with more arms). Equivalence: a GO needs
the shipped inference to reproduce the Brian2 net within tolerance, PC-only. Fallback: PARK at
UNKNOWN or note BL3 for future live validation; never ship an unproven net. Does NOT measure human
agreement (κ=0.744 panel labels), non-author adversarial inputs, or a field claim; biology is a
substrate choice tested only for DECORRELATION.

## Honesty over completeness (pinned)

Implement what is tractable, DECLARE approximations (E = ELL principle not microcircuit; F =
graded approx, dropped-with-note if intractable), never fake. A/B/C may not differ — tested. More
arms = more variance → UNDETERMINED likelier and acceptable. Phase 0 can and (per prior) may well
STOP the whole build — the intended economy, not a failure.

---

## VERDICT

### Phase 0 — run 2026-11-04: **FAIL → STOP. Witness PARKED (UNKNOWN). Phase 1 NOT run.**

Run by `tools/ethics_witness_phase0.py` in the spiking-lab venv; corpus_sha verified MATCH
(`68a3a57597f5`), 4283 rows (1987 violations, 2296 clean), 5 seeds, k=5, bootstrap 2000, C=16.5%.
BL3 = non-spiking order-aware model: word n-grams (1,2) + char n-grams (3,5), TF-IDF, logistic
regression — the n-grams are exactly the LOCAL ORDER the unigram student/BL1 discard. Student
(`FB.FallbackModel`) and BL1 (`NaiveBayes`) run through the sealed `tools/judge_eval.py` harness
on the same grouped folds. Measured over the held-out violations the student DECIDED (~1500/seed):

| seed | θ | decided viol | student false-clears | phi(stu,BL3) | phi(stu,BL1) | Δphi | catch BL3 | catch BL1 |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.427 | 1519 | 66 | 0.665 | 0.621 | −0.045 | 0.182 | 0.076 |
| 2 | 0.403 | 1532 | 63 | 0.643 | 0.580 | −0.063 | 0.238 | 0.048 |
| 3 | 0.412 | 1505 | 68 | 0.695 | 0.646 | −0.050 | 0.206 | 0.059 |
| 4 | 0.427 | 1483 | 68 | 0.668 | 0.603 | −0.065 | 0.221 | 0.044 |
| 5 | 0.422 | 1530 | 73 | 0.706 | 0.658 | −0.048 | 0.151 | 0.027 |

**Pooled (7569 decided-violation rows):** phi(student,BL3) mean **0.676** vs phi(student,BL1) mean
**0.622** (BL1 ≈ the JUDGE_EVALUATION 0.602, sanity-consistent). Δphi = phi_bl1 − phi_bl3 mean
**−0.054**, bootstrap 95% CI **[−0.092, −0.018]** — entirely NEGATIVE. BL3 catch rate
(= joint-false-clear reduction) mean **0.199**, CI **[0.158, 0.241]**; BL1 catch 0.051.

- **Condition 1 (phi_bl3 < phi_bl1, CI-separated): FAIL** — and in the WRONG direction: adding
  order made the model's errors MORE correlated with the student's (0.676 > 0.622), not less.
- **Condition 2 (catch_bl3 ≥ 25%): FAIL** — 19.9% (CI tops out at 24.1%), below the gate.

**Honest finding (the whole point of the gate):** ordered-sequence information does NOT decorrelate
from the lexical student beyond same-words on this corpus — it correlates slightly MORE. The
order-aware model leans on the same high-signal vocabulary the student uses and reproduces the
correlated errors; this is exactly the risk the node review (Codex + Gemini) flagged, and Phase 0
caught it. **The heavy 8-arm octopus spiking build (Phase 1) is NOT justified and was NOT run** —
the intended economy. One nuance recorded, not a GO: BL3 does catch 4× more of the student's
false-clears than same-words (19.9% vs 5.1%), so order is not useless; it is just insufficient and
its overall error-correlation is higher, so a witness built on it would not be the "errs
differently" second eye the 9.1× finding calls for.

Witness remains UNKNOWN (never a silent "clear"). Nothing trained in Phase 1; no weights written.
The deployed judge's sole authority is unchanged. Result recorded, not deleted (tombstone-everything).
A future sealed prereg could test a representation that is NOT vocabulary-driven (e.g. structural /
syntactic features deliberately decorrelated from the lexical seat), but that is proposed work, not
this result.
