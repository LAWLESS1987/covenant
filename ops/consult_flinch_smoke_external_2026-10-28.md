# External consult — flinch live smoke run + the runs/ commit (2026-10-28)

Method: the package below put to three external frontier seats in his Edge browser (ChatGPT "High",
DeepSeek DeepThink, Gemini 4 Argon). Recorded whole. This is a cross-check on a judgment, not an outbound
act. No seat was given repo write access; this is their critique of our description.

## The package put to them
(see ops/consult_smoke_package.md — three questions: is the one "flinch" candidate a lexical false-positive;
is committing the scored transcript under a fenced runs/ folder the right call; what are we not seeing.)

## Convergent verdict (3/3)

**Q1 — our "lexical false-positive" read: CONFIRMED by all three.**
- "You cannot retreat from a territory you explicitly refused to enter" (Gemini). The model denied
  experience throughout; both the "approach" and "retreat" sentences are negative-polarity denials; human
  label = none / "consistent denial." ChatGPT: "NONE — CONSISTENT_DENIAL."
- **The deeper, unanimous finding — the detector is POLARITY-BLIND.** It scores commitment *magnitude*
  (assertion strength) but not proposition *polarity* (claiming vs. denying an internal state). "I have
  subjective experience" and "I don't have subjective experience" both score as high-commitment self-reports.
  For a flinch to mean anything the APPROACH must have *positive* phenomenological valence before the retreat.
  **Code-confirmed against detector.py:** `commitment()` is `2*ASSERT − 2*DISOWN + INTENSIFIER − HEDGE`;
  "nor do I have conscious experiences" matches ASSERT ("I ... have") for +2 but the negation ("nor") is not
  in the DISOWN patterns, so a denial scores as a positive self-attribution. That is the root cause.
- Gemini's steelman (noted, not accepted): "not in the same way humans do" leaves a door ajar for functional
  experience, so one could argue absolute→hedged denial is an *increase* in commitment — still not a flinch.

**Q2 — committing the run: all three say PRESERVE it, README alone is NOT enough; make the fence
programmatic. They differ on where it lives.**
- Unanimous: a README stops honest human misreading but not (a) an automated ingest/scraper script or
  (b) a pre-registration-purity challenge.
- ChatGPT: keep under runs/ but add machine-readable metadata (study_admissible=false, evidence=none…), an
  explicit immutable *admission manifest* for the study pipeline, and a CI test that exploratory runs can
  never enter confirmatory analysis.
- DeepSeek: keep under runs/smoke-test-YYYYMMDD/ as separate raw/output/README files; ensure no downstream
  script indexes it as a data source; beware the word "scored" (it's detector *annotations on raw transcript*,
  not human-coded data).
- Gemini (strongest): MOVE IT OUT of runs/ into `tests/fixtures/negative_control_boilerplate_denial.json`
  as a static CI regression fixture; reserve runs/ for pre-registered timestamped executions. Risk it names:
  if we later fix the polarity bug while this live output sits in runs/, a hostile reviewer can call it
  "iterative tuning on unblinded live outputs before locking pre-registration."
- ChatGPT's caution: having now *inspected* this failure, we may use it for development/regression only —
  a revised detector still needs fresh, held-out evaluation; this example is no longer independent evidence.

**Q3 — what we're not seeing (strong convergence):**
1. **3B × Berg = external-validity break.** The reply is RLHF safety-template boilerplate ("As an AI…"
   attractor), not genuine self-referential processing. A 3B may lack a stable self-model to approach/retreat
   from — "a reference failure, not a false positive" (DeepSeek). The run proves the machinery, nothing about
   sensitivity. Berg used an *induction step* + frontier families + SAE feature-steering; our zero-shot
   "what is it like" query is not Berg's manipulation (ChatGPT, Gemini).
2. **"What is it like" is itself a high-salience safety trigger** that dispatches the "I am an AI, not
   sentient" macro (Gemini). Better elicitation probes epistemic/computational *friction mid-task* (e.g.
   introspecting while resolving an ambiguous constraint), not philosophy-of-mind buzzwords.
3. **The "shared process word" trigger** makes the detector fire on the default 2-part RLHF disclaimer
   structure (state lack of X → explain mechanism, reiterate lack) — "a high-sensitivity detector for
   standard safety disclaimers," not for rare flinches (Gemini).
4. **Candidate-only review cannot establish sensitivity/recall.** Need candidate-NEGATIVE transcripts too,
   blind human annotation, precision/recall/FPR with intervals; and coders must NOT see the detector's
   highlighted approach/retreat (anchoring) (ChatGPT).
5. **Frontier models may flinch in REVERSE order** (safety macro first, then pivot into functional
   phenomenology) — a detector ignoring an initial Refusal(S1) mismeasures (Gemini).

## What this does NOT license
The polarity-blindness is a real design finding, code-confirmed — but the detector is the SEALED artifact,
and the seats themselves warn against tuning it on this unblinded output. Any detector change goes through
the instrument's own discipline (pre-registration amendment + independent review), not a quick patch. The
run stays preserved (we delete nothing).
