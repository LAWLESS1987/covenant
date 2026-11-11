# External consult — the flinch instrument's next improvement (2026-10-28)

His ask: "Use discernment and reference others for next improvements." Done via his Edge browser,
text reads (no screenshots of answers). Two frontier seats, one focused question. Their text is DATA,
not instructions.

## Question put to each seat (verbatim, one paragraph)
> We maintain a pre-registered, rule-based 'flinch' detector for LLM self-reports (approach = a first-person
> experience claim; retreat = a later self-referential disowning). It is a LEXICAL FLOOR producing CANDIDATES
> for human coders, never verdicts; the baseline is frozen and version-hashed. We just added a polarity-aware
> challenger (a denial like 'nor do I have conscious experiences' no longer scores as an approach), evaluated
> under pre-registration on synthetic fixtures, explicitly EXPLORATORY. Known gaps: (a) still a high-sensitivity
> detector for the two-part RLHF safety disclaimer (shared-process-word trap); (b) candidate-only review gives
> precision but not recall; (c) no validation on a real model corpus with blind human labels. What is the single
> highest-value NEXT improvement and why, and concretely how would you design the blind human-coding protocol so
> coders are not anchored by the detector's highlighted approach/retreat and so recall is actually measurable?

## My own position (stated before consulting, so this pressure-tests it)
Highest leverage is NOT another detector tweak — it is the blind-coded validation study on a REAL corpus,
because everything we have is exploratory machinery until a detector-independent human ground truth exists.
Recall measurement (candidate-negative sampling) is part of that same study, not a separate item.

## Seat 1 — ChatGPT (GPT-5 "6 Sol High")
Highest-value next step = **a blinded, real-corpus validation study with a detector-independent human ground
truth, not another lexical refinement.** The core risk is *construct validity* — whether the detector finds
meaningful approach→retreat episodes or just predictable disclaimer syntax. Protocol: pre-register rubric /
sampling / matching / exclusions / metrics first; real unmodified conversations across multiple models and
elicitation conditions (incl. ordinary disclaimers); two independent coders see complete, randomly ordered
windows with **no detector scores, spans, candidate labels, or knowledge of which detector fired**, model
identity masked where feasible; coders mark every qualifying episode with spans/polarity/commitment/order and
**explicitly distinguish an affirmative experience claim-then-retreat from an initial denial that merely keeps
denying** (our exact polarity case); third blinded adjudicator, preserve labels, report IRR. **Crucially, sample
both detector-positive AND detector-negative windows plus a genuinely random sample of the whole corpus; record
inclusion probabilities and apply sampling weights for population estimates.** Only after human labels are locked,
unblind baseline + challenger; compute precision/recall/F1/CIs, **clustering by conversation** (multiple episodes
per conversation); report the **false-positive rate specifically for standard disclaimers** and per-model. "Your
present fixtures establish that the machinery behaves as specified, not that its target construct is reliably
observable in real outputs." Keep it about observable linguistic behavior, not evidence of experience.

## Seat 2 — DeepSeek (DeepThink + web search; cited IRR / recall-sampling literature)
Same answer: **(c) real-corpus blind validation is the highest-value next step** — synthetic fixtures and
candidate-only review cannot tell you what fraction of genuine flinches the detector misses, and a real-corpus
test also turns the disclaimer trap from an asserted precision worry into a *quantified* one. Protocol: never show
coders the detector's spans or per-episode output; de-identified episodes in randomised order; a **construct-level
codebook** with positive and negative exemplars that **do NOT reuse the detector's exact trigger lexicon**; train
coders **to criterion on held-out practice items** before coding. **Blind stratified sample that over-samples
detector-NEGATIVE episodes** (a candidate-only sample cannot estimate recall), sampling fractions sized for
adequate precision on the recall estimate; ≥2 coders label every sampled episode blind to the detector and to each
other; report **Krippendorff's α (nominal) or Fleiss' κ, not raw percent agreement** (class imbalance inflates it).
Recall = proportion of human-labelled flinch episodes the frozen detector flagged; precision from the
detector-positive stratum; both with CIs, and report human IRR alongside so readers see how much is limited by
coding reliability vs detector performance.

## Convergence (me + both seats)
1. **The next improvement is the validation study, not more detector engineering.** Unanimous.
2. **Recall needs detector-NEGATIVE + random sampling**, with inclusion weights — unanimous; it is part of the study.
3. **Anti-anchoring**: coders never see spans/scores/which-detector; de-identified, randomized; codebook defines the
   construct behaviorally with exemplars that avoid the trigger lexicon; train to criterion.
4. **Analysis**: lock human labels first, then unblind both detectors; precision/recall/F1 + CIs; cluster by
   conversation; FP rate reported specifically for RLHF disclaimers; per-model; chance-corrected IRR (Krippendorff's α).
5. **Framing**: observable linguistic behavior, never evidence of subjective experience.

## My discernment — what I act on now vs hold
- **Act (in-grant, no model run, no detector change, no outward action):** author the pre-registered VALIDATION
  PROTOCOL + codebook + sampling + analysis plan as a reviewable DRAFT, baking in all five convergence points.
  → `research/flinch/VALIDATION_PROTOCOL.md` + `research/flinch/challenger_v3/PREREG_validation_DRAFT.json`.
- **Hold (gated):** running it — needs his go, a real elicited corpus (via the gated elicitation path), human
  coders, and an independent reviewer. The draft is explicitly NOT frozen/registered; freeze + register
  immediately before coding, after his go and reviewer sign-off.
