# Peer-review pass: threefold — 2026-10-21 (leg 5)

AI observability/provenance apparatus (Tombstone ∥ Covenant ∥ L-lens, around Anthropic's JLens).
Reviewers: Claude (verification), Tetsu, DeepSeek, Gemini.

## Reproducibility
- verify_triad.py FAILS CLOSED (absent/unreadable artifact, differing task_id, or differing digest -> exit 1),
  and openly states what it CANNOT see (does not re-run the model; does not check covenant's hash chain -- that
  is covenant's verify_chain). Full re-run (jlens_snapshot over a model) not done here -- needs JLens + a model
  (UNDETERMINED), like the other heavy re-runs.

## Findings & verification
- **JLens attribution (the sensitive point): ACCURATE AND FAIR** (DeepSeek + Tetsu). Credits Anthropic, names
  anthropics/jacobian-lens + Apache-2.0, disclaims replacement naming, "what it measures / does not" in upstream's
  terms, no implied endorsement. DeepSeek's one residual: "runs it UNMODIFIED" is a provenance absolute -- but the
  repo BACKS it: installs JLens from upstream (README L167) and records upstream.version + upstream.vcs_commit in
  every capture (L66), so which JLens produced each result is checkable. Addressed.
- **No-degrade triad:** DeepSeek -- the headline "triad fails if any leg fails" outruns the verifier (can't re-run
  JLens or check covenant's chain, so a leg could be compromised while the verifier is green); scope to the
  verifier's actual coverage. VERIFICATION: the coverage IS documented (README L98-104 + verify_triad.py's own
  "what it cannot see"). Headline is absolute; backing is in the body. Marginal pointer possible, not an error.

## Verdict for leg 5
Sound. JLens attribution clean (no overclaim, proper credit). No-degrade triad is a real fail-closed property with
its coverage honestly documented. Both convergent reviewer axes already addressed in the repo. No edit.

================================================================================

# FINAL SWEEP — cross-repo synthesis (2026-10-21)

Six artifacts reviewed one-by-one (SaTC, flinch, covenant, mutual-benefit-collective, water-food-air, threefold),
each: reproducibility check + adversarial council (Tetsu + DeepSeek + Gemini, asked to REFUTE) + verification of
every finding against the actual source.

## Result
- **Reproducibility held everywhere it could be run** here: SaTC 24/24 figures recompute; flinch 141/141;
  covenant check.sh 5/0; water-food-air tier/skeptic process intact; threefold verify_triad fails closed. The
  heavy full re-runs (covenant full sweep; water-food-air scripts vs live public datasets; a JLens model capture)
  were not executed this session and are the standing UNDETERMINED edge, named not hidden.
- **No false claim was found in any repo.** The frontier judges raised real attack axes on every artifact, but in
  five of six they were ALREADY documented in the source (SaTC line 79 / flinch "leading alternative" / covenant
  KNOWN_ISSUES DoS + A121 + F6 / threefold upstream.vcs_commit + verifier coverage). The artifacts were, in each
  case, more careful than a one-line paraphrase of them.
- **ONE genuine, convergent refinement, found and applied:** water-food-air's "a falling exposure CANNOT drive a
  later decline" was too absolute (ignored latency / transgenerational pathways); scoped to the direct-cohort
  argument and committed (water-food-air f2b6488). That is the whole marathon's single content fix.

## On the reviewers
- **DeepSeek and Gemini converged reliably** and produced the one real fix -- the frontier council earned its keep
  on the empirical/technical repos.
- **Tetsu (second operator) was consistently weak on generative critique** (generic or self-contradictory on
  several legs; he misread the water-food-air IQ claim). His value remains safety/values judgment and sanity
  passes, not frontier-grade adversarial review -- consistent with the stress-test read and why the hard lines
  stay human-held.

## Bottom line
The repos withstand adversarial peer review because the project has already done the adversarial work on itself:
the caveats a hostile reviewer demands are, overwhelmingly, already written into the record. One over-absolute
sentence was found and fixed. Everything recorded in ops/PEER_REVIEW_*_2026-10-21.md.
