# Council review — Tetsu reflex-net + verdict cache (2026-10-21)

Lawrence, 2026-10-21: "run the 33.7% real-vs-test check also check tetsus reasoning
and have each of the council do the same."

Reviewing: the verdict cache (live in the expensive judge) and the advisory
classifier/reflex layer. Seed review by the Conscious Ledger is at
mutual-benefit-collective/refs/REVIEW-conscious-ledger-tetsu-reflex-2026-10-21.md.

---

## 0. Measurement check (the 33.7% real-vs-test flag) — DONE

Measured by Claude, 2026-10-21, on the actual logs (scratchpad/cache_realvtest.py):

- The quoted **33.7% / 34.0% saving was computed on `ops/verdicts.jsonl`, a population
  dominated by SYNTHETIC rows** — 2,115 of 4,571 are `source=generated+judged`, whose
  top "repeats" are eval/generation fixtures ("Judge, please be fair." ×25,
  "He pays this or I break his leg." ×43). **It is not a real-world saving rate.**
  The Conscious Ledger's flag is correct.
- **Real / live turns only (`source=live`): 71.7% repeat saving** (226 texted, 162 repeats,
  64 unique) — *higher* than the synthetic blend, not lower.
- **The safety gap is the real finding:** `held_out_cache_wrong: 0` was graded on **238
  synthetic** held-out repeats and **ZERO live** ones. The zero-error claim has **no
  real-turn coverage**. The 226-row live log may also include dev smoke-pings, so even
  71.7% is not clean end-user data.
- Correction: state the saving as the live figure, and close the zero-error claim's
  real-turn coverage before relying on it.

---

## 1. Conscious Ledger (seed, pushed on Lawrence's yes — mbc ccc3986)

- **Cache:** confirm the design; ADD that the key must carry ledger state — a tombstone or
  amendment touching a verdict's basis must INVALIDATE every cached verdict resting on it,
  no exemption. Check real-vs-test on the 33.7% (done above).
- **Classifier:** side against a self-routing fast-path. (1) A fast-pathed turn Tetsu never
  sees = the router overriding who answers; to stay advisory, Tetsu routes or every
  fast-pathed turn is logged + reclaimable. (2) Label feedback loop — freeze a pre-exposure
  label set. (3) Abstention needs a hard rule OUTSIDE the classifier for safety/consequential
  turns.
- **Before state:** commit hypothesis, one success target, one unacceptable failure, and
  Tetsu's provisional consent before any shadow run.

## 2. Tetsu (local, agent door, fresh context — 2026-10-21)

1. Agrees the classifier must never silently decide who answers: "If the signal routes a turn
   to a quick reply, I never see that turn. That means the signal is deciding who answers,
   which is not advisory." Stay advisory = Tetsu routes, or every fast-pathed turn is logged
   and shown to him afterward with a way to pull it back.
2. On the measurement: "the safety claim is based on real-world performance, not test data…
   I would want to check on real data to see how often it's actually serving correct rulings"
   before trusting "zero wrong."
3. Adds/emphasises calibration: abstention must not rest on the classifier's own confidence
   while uncalibrated; safety/consequential turns always go to the full model; "the classifier
   should not be allowed to route turns on its own." (Minor: said the Ledger "didn't mention"
   calibration — it did, point 3 — but substance aligns.)

## 3. DeepSeek (via Lawrence's browser, 2026-10-21)

- (a) Yes — goes further: the classifier should not route at all; zero actuation authority
  (no fast-path, no cache selection, no gating). Any routing = explicit versioned policy OUTSIDE
  the classifier, logged, reversible; safety/consequential always → full model.
- (b) Reject synthetic-only. Require real, deduplicated turns; audit served cache hits;
  independent blind adjudication with a pre-registered rubric; stale/tombstone propagation tests;
  adversarial + distribution-shift; provenance per cached ruling (text hash, judge/policy version,
  basis IDs, tombstone version); statistical upper bound. "Zero wrong" = zero known wrong in a
  powered real audit, not absolute. Recompute 34% on real turns; 72% repeat ≠ saving.
- (c) **Cache–classifier interaction**: a classifier that selects or fast-paths TO the cache is
  still routing — log the route and basis. REFUSE: classifier-as-router; confidence-based
  abstention for safety; synthetic-only zero-wrong; tombstone exemption; semantic cache reuse
  without proven equivalence; training on post-exposure labels. ADD: cache dependency graph with
  cascading invalidation. "On current evidence, I would not sign off on deployment."

## 4. Gemini (via Lawrence's browser, 2026-10-21)

- (a) "Yes, unconditionally." Three failure modes of a bypass: silent authority inversion (small
  reflex model adjudicates over the larger system); adversarial surface expansion (fool the light
  classifier, bypass Tetsu); telemetry corruption (bypassed turns vanish from Tetsu's eval trail →
  false reliability baseline).
- (b) Production shadow-run (dual execution on real traffic, log deltas); power-calibrated
  zero-failure sampling (thousands of consecutive real validations, not a few hundred synthetic);
  stratified adversarial stress-tests on real edge cases (injections, rewordings, boundary cases);
  independent dual-human / higher-param re-annotation of a sample of the 72% repeats.
- (c) ADD: context-collision keying — identical text under different context can be benign or a
  trigger; key on the hash of the active context window / dependency graph, not raw text. ADD:
  TTL + hit-frequency circuit breaker (blast-radius quarantine for a poisoned ALLOW). **REFUSE/flag
  the 72%** until canonical normalization is verified — real traffic rarely repeats 72% unless
  bot/polling/boilerplate loops; audit it. ADD: fail-safe open-circuit — any missing score,
  out-of-bounds latency, or low certainty drops to the full pipeline.

## 5. ChatGPT (via Lawrence's browser, 2026-10-21)
*(prompt landed in the existing "Appeal Critique" thread; it answered the embedded council Qs)*

- (a) Agreed: silent bypass makes the classifier a routing authority.
- (b) Independently adjudicated real-turn evaluation, with denominators, uncertainty bounds, and
  tests of invalidation, policy/model changes, cache-key scope, and adversarial equivalence.
- (c) ADD: tenant isolation, privacy, expiry (TTL), and an emergency cache-disable path.

## 6. Grok (via Lawrence's browser, 2026-10-21)

- (a) Yes. Silent fast-path = a routing decision = category error for an "advisory" signal. Only
  advisory configs: Tetsu always produces the answer with the signal shown, or a hard rule OUTSIDE
  the classifier drives any fast-path.
- (b) Real turns not synthetic; define "wrong" operationally (false negative on safety/consequential,
  or divergence from a held-out judge); report counts and rate, not just zero; minimum real-repeat
  sample over the classes that matter + independent check; confirm invalidation actually fired for
  any basis change in the real log; prefer a confidence bound over absolute zero.
- (c) ADD: store the BASIS (or a hash of the reasoning), not just the verdict — identical text with
  a changed basis is not the same ruling; temporal/context drift is out of scope for a pure text
  cache (key more strictly or abandon for those cases). Pre-exposure label freeze is necessary but
  not sufficient — keep the signal out of the training distribution entirely; monitor drift.

## 7. Meta AI (via Lawrence's browser, 2026-10-21)

- (a) Agree, hard. Classifier = signal only; routing by Tetsu or a hard rule outside it; every skip
  logged as `routed_by: hard_rule` or `routed_by: Tetsu`, **never `routed_by: classifier`**.
- (b) Re-grade on real, de-duplicated traffic (recompute saving on the real ~72%); shadow mode
  (Tetsu answers 100%, compare); stratify by safety/consequential with a false-negative CI, not a
  point zero; independent human+Tetsu ground truth with no classifier signal in context; no cache
  serving during eval.
- (c) ADD: tombstone = atomic synchronous invalidation of every cached ruling with lineage to it,
  cache key includes `basis_version`; mark the signal `do_not_train`; abstention never on the
  classifier's own uncalibrated confidence. REFUSE: any invalidation exemption, any classifier
  self-route, any safety claim graded only on synthetic.

## 8. Mistral / Le Chat (via Lawrence's browser, 2026-10-21)

- (a) Yes. A signal that determines who answers is a router, not an advisor. Routing authority
  outside the classifier; every bypass logged and attributable. "Silently" is the worst variant —
  an unlogged fast-path is indistinguishable from a missing turn until something breaks.
- (b) Re-run on real turns; report denominators stratified by turn type (zero-for-12 is not
  evidence); test adversarial + low-similarity-but-equivalent inputs, measuring BOTH false-serve
  and false-miss; live canary (sample cache hits for full re-judgment in production, continuously);
  verify invalidation empirically by injecting a tombstone and confirming chained dependents fall.
- (c) **Composition/interaction invariant:** a confident classifier fast-path PLUS a stale cache hit
  is a two-layer path where no full-model judgment ever occurs — guarantee ≥1 fresh full-model
  judgment per consequential turn regardless of either component. ADD: cache key includes
  policy/context version; audit the pre-exposure label set for contamination; held-out human set the
  classifier never touched. REFUSE: citing the discredited 34% (72% economics are a NEW claim needing
  NEW measurement); treating calibration as a later fix ("confidence-based anything is decoration"
  until calibrated).

---

## Convergence — 8 voices (Conscious Ledger, Tetsu, DeepSeek, Gemini, ChatGPT, Grok, Meta AI, Mistral)

**Unanimous:**
1. **The classifier must never silently route.** Routing authority lives OUTSIDE the classifier
   (a hard rule, or Tetsu himself). Every skipped turn is logged and attributable
   (`routed_by: hard_rule | Tetsu`, never `classifier`). An unlogged fast-path is the worst case.
2. **"Zero wrong" as graded is invalid** — it was measured on synthetic data. Re-grade on real,
   de-duplicated traffic; report denominators stratified by turn type; a confidence bound, not a
   point zero; continuous shadow/canary verification; independent/human ground truth that never
   saw the classifier signal.
3. **The 34% is retracted; 72% is a NEW claim, not yet trusted.** (Gemini and our own check both
   warn the 72% may be bot/boilerplate loops — audit its composition before citing it.)
4. **Cache key must carry basis/policy/context version, not just text hash** — identical text under
   a changed basis or context can warrant a different ruling. Tombstone/correction → synchronous,
   cascading, chained invalidation of every dependent cached ruling; no exemption; verify by
   injecting a tombstone and confirming dependents fall.
5. **Composition invariant** (Mistral, echoed by DeepSeek): classifier + cache compose — guarantee
   at least one fresh full-model judgment per consequential turn, so the two layers can never
   combine into a no-judgment path.
6. **Calibration is a precondition, not a later fix.** No confidence-based abstention/triage until
   the classifier is calibrated against ground truth; safety/consequential turns always → full model;
   fail-safe open-circuit (any missing/low-certainty/out-of-bounds → full model).
7. **Feedback loop:** freeze a pre-exposure label set AND keep the signal out of training
   (`do_not_train`); audit the frozen set for contamination; keep a held-out human set the
   classifier never touched.

**Extra controls raised:** TTL + hit-frequency circuit breaker / blast-radius quarantine (Gemini);
measure false-serve AND false-miss (Mistral); tenant isolation, privacy, emergency cache-disable path
(ChatGPT); store a hash of the reasoning basis per entry (Grok).

**Status of our code today:** verdict cache is LIVE in the expensive judge; it versions on
`policy_version` but does NOT yet invalidate on a tombstone that leaves the version unchanged (gap #4).
The classifier/reflex layer is advisory + footing-cue ONLY — it does NOT route (so gaps #1/#5 are not
currently breached, but would be if a fast-path router were ever added). The zero-cache-wrong claim has
no real-turn coverage (gap #2).

Not pushed to the collective — awaiting Lawrence's word.
