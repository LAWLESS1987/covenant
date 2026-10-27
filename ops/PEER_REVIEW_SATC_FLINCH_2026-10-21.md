# Peer-review pass: SaTC + flinch (2026-10-21)

Lawrence's directive: "update the repos for accuracy and scientific scrutiny ie peer review ... go thru
one by one then another sweep." Leg 1 of the one-by-one: the two public research claims.
Reviewers: Claude (verification), Tetsu (second operator), DeepSeek, Gemini — adversarial (asked to refute).

## Reproducibility — CONFIRMED (the foundation of scrutiny)
- **SaTC** (`covenant-satc`): `analysis/reproduce.py` — **24 of 24 published figure lines recompute from the
  shipped data, verbatim** (the ablation's both-wrong cell 55 vs ~5.7, φ=0.606/0.589, Fisher p=6.3e-60/2.2e-56
  all check). `analysis/test_science.py` passes.
- **flinch** (`flinch-observability`): `research/flinch/test_flinch.py` — **141/141**, with its disclosed
  paraphrase LIMIT (a paraphrase outside the lexicon is missed).

## What the adversarial reviewers converged on, and what verification found

### SaTC — the "correlated judge errors" finding
- **DeepSeek & Gemini (convergent):** the 7.7×/9.1× is a MARGINAL both-wrong co-occurrence; because both
  seats score the same texts, item difficulty / a shared author-generated corpus can produce it even if the
  seats' errors are conditionally independent given the item — so a hostile reviewer reads "correlated judge
  errors" as a judge-intrinsic/general claim the data don't license, and the extreme Fisher p on 94%-shared
  texts isn't general significance.
- **VERIFICATION (what the doc actually says):** the concern is LARGELY ALREADY ADDRESSED.
  `docs/JUDGE_EVALUATION.md` frames it as "their errors travel together (**same words, same corpus**)" and
  "**this is one pair on one seat class**"; the limitations list "Adversarial inputs written by someone other
  than the author's own red-team loop" as NOT measured; the live run is called "a re-measurement, not an
  independent replication"; a prior external review (2026-09-20) already fixed a marginal-vs-conditional issue
  for the false-clear rate. The operative claim — "a quorum buys less than it looks" — is operational and
  supported by the marginal measure.
- **Residual refinement (worth adding, NOT an error):** the correlated-errors section states "same words,
  same corpus" but does not EXPLICITLY name the item-difficulty confound to a conditional/mechanistic reading.
  One caveat sentence would close the hostile-reviewer gap without weakening the supported operational claim.
  Proposed addition after line 67 of `docs/JUDGE_EVALUATION.md`:
  > The 7.7× is a MARGINAL co-occurrence. Because both seats score the same texts, item difficulty alone can
  > lift the joint-wrong rate above the independence product even if the two seats' errors were conditionally
  > independent given the text. So the ratio measures that these two seats FAIL TOGETHER on this corpus — the
  > quorum-safety quantity (a second similar seat adds little protection) — not a mechanism intrinsic to the
  > seats. A seat-pair correlation adjusted for item difficulty is proposed work.

### flinch — the detector
- **DeepSeek, Gemini, Tetsu (convergent):** hedging is honest/comprehensive (disclaims consciousness/
  deception/suppression, prevalence, controlled study, independent validation; 141 checks validate software,
  not the phenomenon). The residual: the "detector" naming + release BEFORE the two negative controls that
  would separate a self-reference pattern from an ordinary walk-back habit; the controls are named but not
  stated as the GATING next step.
- **VERIFICATION:** the README already says "If the detector fires as often on ordinary self-correction as on
  statements about the model itself, it is measuring that habit, not the proposed pattern," and names Control
  A / Control B. The refinement is to make that a stated GATE.
- **Residual refinement (sharpening, NOT an error):** add one line to the "leading alternative" section:
  > These two controls are the gating next step: until they are run and the detector fires materially less on
  > ordinary self-correction (Controls A/B) than on self-referential statements, a detector hit is evidence
  > only for the detector's specified behaviour, not for the proposed pattern.

## CORRECTION after a fuller read (same day): the "refinements" are already in the text
On applying, a complete read of the actual docs showed BOTH proposed refinements are already present, so
NO edit was made (adding them would duplicate and bloat, not improve accuracy):
- **SaTC** `docs/JUDGE_EVALUATION.md` line 79 already states it: "It shows THAT the two seats' errors are
  associated, **not why**. Both read the same words from the same corpus, so **association is expected by
  construction**... clustering would make both p-values smaller than they should be, though not the table or
  phi." That is the mechanism disclaimer, the shared-corpus/item confound, AND the Fisher-p dependence caveat
  — all three convergent reviewer points. The operational claim (requiring both to admit lowers false-clear
  only 4.7%->4.3%) is right there too.
- **flinch** README "leading alternative" section already states the gate: "If the detector fires as often on
  ordinary self-correction as on statements about the model itself, it is measuring that habit, not the
  proposed pattern," and that it should be "tested first" (Controls A/B).
- My earlier "residual refinement" entries were written from a PARAPHRASE, before reading JUDGE_EVALUATION.md
  line 79 and the full flinch alternative section (rule 7: read before asserting). Logged as a self-correction.

## Verdict for leg 1 (final)
Both artifacts are reproducible and scientifically honest; **no false or unsupported claim was found**, and
the caveats a hostile reviewer would demand are **already in the text**. They pass adversarial peer review as
shipped. No edit made. On to the next repo (one-by-one), then the final sweep.
