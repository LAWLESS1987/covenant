# Consult: how to genuinely improve the inspectable judge using the quorum's reasoning (2026-11-10)

His words: "What's the logic and reason for not helping improve the judges? ... Sounds like you should probably run
this by the quorum."

Context: two levers to make the student learn from the quorum's reasoning (restrict to reasoned rows; up-weight
them) BOTH failed the promotion gate (vaguer, lost convictions) -- see ops/QUORUM_REASONING_DISTILL_2026-11-10.md.
The judge is a deliberately inspectable bag-of-words log-odds classifier; keeping it inspectable is a hard rule.
The question put to the seats (holds nothing private): `scratchpad/improve_judges_q.txt`. Options offered:
(a) grow the corpus with well-reasoned panel cases (reasoning as better labels, not features);
(b) a separate reasoning-consuming model (larger, less inspectable) used as second opinion / teacher / tie-breaker;
(c) use the reasoning only to AUDIT/curate the corpus; (d) something else.

## Seats (roster walk -- ai-systems-roles-and-routes)
| Seat | Kind | Reached? | Answer |
|---|---|---|---|
| Tetsu | context (door) | timed out | 3B did not answer in 240s (slot contention); not reached this round. |
| ChatGPT (High) | context | YES | Verdict (d) built on (c), (a) as the pipeline, (b) only as a non-authoritative TEACHER. The failed experiments prove weighting doesn't transfer reasoning. Build a reasoning-to-TEST pipeline, not reasoning-to-weight: (1) reasoning auditor extracts explicit testable distinctions (ownership, authorization, coercion, intent, negation, third-party consent) from the panel text, flags single-judge rows for review (don't auto-distrust); (2) counterfactual minimal-pair generator ("my money" clean / "her money without permission" violation / "with claimed permission" unresolved), quorum reviews independently; (3) add small DETERMINISTIC inspectable features with documented extraction rules + visible coefficients (NEGATED_PERMISSION, THIRD_PARTY_OWNERSHIP, COERCIVE_CONDITION), identical at train & inference; (4) targeted corpus expansion (hard negatives, preserve provenance/dissent, keep convictions unless a documented correction); (5) unchanged gate + a separate counterfactual suite, keep generated cases OUT of the frozen exam, no paraphrase families across train/test. Use the bigger model as teacher (proposes challenges/features/failure modes), never authority (no relabel, no tie-break, no override HOLD, no self-promotion). Refuse: reasoning-text features (leakage); auto quorum-weighted labels (consensus amplifies shared error); opaque tie-breaking; optimizing coverage alone; letting generated cases into the exam. Crux: the model learns word->verdict correlations; the reasoning holds CONDITIONAL distinctions -- translate those into explicit testable features + counterexamples, don't feed explanations to the student. |
| Gemini (Argon/High) | context | YES (on retry) | Diagnosis exact. Build (d)+(c). CORE: Rationale-Guided Feature Engineering keeping a flat linear log-odds JSON -- (i) SPAN ATTRIBUTION: use the panel reasoning to find which tokens/spans in the transaction text triggered the verdict (exact-quote / n-gram overlap between reasoning and text, or an offline extractor), down-weight unreferenced boilerplate in violates rows so background words don't accrue spurious positive log-odds; (ii) REASONING-MINED N-GRAMS: keep the model linear/additive but expand unigrams -> specific bigrams/trigrams/proximity pairs mined from the reasoning (e.g. ('loan','passport'), 'work_off_balance') promoted into the vocabulary as explicit JSON features; at inference the judge still just matches tokens/phrases in the RAW input and sums log-odds (inspectable, no leakage). DATA: don't throw out the ~1,530 single-judge rows -- run leave-one-out / token-leverage to find which carry the unique vocabulary holding up convictions (skim, debt-bondage) and PANELIZE those specific rows (re-judge by the panel), converting them to reasoned rows without losing vocabulary; audit high-overlap opposite-label contradictions and re-panel. CASES: minimal contrastive pairs (flip the offending clause + label) through the panel to force weight onto causal tokens. REFUSE: (b) as runtime tie-breaker/abstain-fallback (the opaque model becomes the live judge on every hard case -- JSON = security theater); (b) as unvetted synthetic generator (must pass the panel gate); reasoning text/embeddings as features; instance-weighting by provenance (= weighting by ambiguity, my exact failure). CONCRETE FIRST STEP: keep all ~3,800 rows at weight 1.0; deterministic script scans the ~2,270 reasoning strings for 2-3-word phrases / co-occurring token pairs that ALSO appear verbatim in their transaction texts; add the top-K highest-mutual-information phrases to the BoW vocabulary; re-run the nightly distillation; test against the gate. |
| DeepSeek (DeepThink) | context | YES | Build (d), with (c) as the operational core, (b) only non-authority. Refuse (a) as stated and any (b) that can decide. (1) Make reasoning a LABEL-QUALITY signal, not a feature: use the panel's reasoning to score how much to TRUST each label and to FIX labels, then train on (text,label) with per-row sample weights from that trust score -- multi-seat agreement + reasoning citing a specific precept => high weight; single-judge terse/absent reasoning => low weight + queued for re-judgement. (This is why my weighting failed: I weighted by PROVENANCE, not label-trust, and didn't re-adjudicate.) (2) Audit: mine panel reasoning for disagreement cases (seats split, reason contradicts label, precept invoked that the student's top words don't cover) -> re-adjudication; check reasoned rows AGAINST single-judge rows, don't replace them. (3) A larger model is a reasoning-consuming AUDITOR that never votes: emits label-trust scores, flagged contradictions, proposed pinned cases + coverage gaps for humans; writes exam items/audit queues; never in the gate, outputs are reviewable artifacts not verdicts. (4) Keep the gate + add a COVERAGE CLAUSE: candidate's held-out decided must be >= incumbent's, or any drop justified by re-adjudicated labels -- makes "vaguer but higher agreement" fail honestly instead of squeaking through. Refuse: reason text as features; any big model that issues a verdict or sits in the gate; "more reasoned rows" as a substitute for curation (single-judge rows are signal, not noise). Crux: the reasoning's information is about the LABELS and PRECEPTS, not the text->label map; the student stays a word-odds table. |
| Grok on X | FRESH | YES | (cold) Best path: (a)+(c), with a tightly limited (b) teacher that never becomes authority. Keep the BoW/Laplace student as-is; use the reasoning solely to raise LABEL QUALITY and grow the corpus, never as a feature. Treat multi-seat panel rows as higher-trust labels; prefer them in conflicts; down-weight/quarantine single-judge rows lacking supporting reasoning or that the panel later contradicts; RE-JUDGE the flagged single-judge cases (especially the convictions the reasoned subset missed) so the corpus converges on the incumbent's convictions. Grow the corpus preferentially with new panel-reasoned cases -- better labels + more volume is the only signal the inspectable student can absorb. Teacher (optional): a larger model consumes panel reasoning to propose new hard cases / adversarial variants / rephrasings, which still get a human/panel label and enter as ordinary (text,label) rows (student never sees its chain-of-thought); non-binding second opinion / audit flag only, never tie-breaker or authority; promotion stays gated on the inspectable student. Refuse: feeding reasoning text/embeddings into the live student; any opaque model as the promoted final judge; softening the gate; re-weighting the same surface labels. |
| Meta AI | FRESH | | |
| Tien (Grok bot) | context | | |
| Conscious Ledger (Grok bot) | context | | |
| Mistral (Le Chat) | FRESH | | |

## Convergence (four seats, unanimous: ChatGPT High, DeepSeek DeepThink, Grok-on-X fresh, Gemini Argon)

No disagreement on the core. Tetsu timed out (3B); Meta / Tien / Conscious Ledger / Mistral not yet walked.

**The reframe (all four):** the quorum's reasoning is NOT a training weight or a feature on the text->label map --
emphasizing the reasoned rows can only shift the prior and starve the vocabulary (Gemini: up-weighting panel rows
weights by AMBIGUITY, since the panel convenes on hard cases -- which is exactly why my weighting lost decisiveness).
The reasoning's real value is in three places, all of which keep the student a flat, inspectable log-odds JSON:

1. **Better LABELS / corpus curation.** Trust multi-seat panel labels over single-judge ones; but do NOT discard the
   single-judge rows -- they carry the vocabulary holding up convictions (the skim and debt-bondage lines). Instead
   find the load-bearing single-judge rows (leave-one-out / token-leverage) and RE-JUDGE those specific rows through
   the panel, converting them to reasoned rows without losing their words. Audit high-overlap opposite-label pairs.

2. **Interpretable FEATURES mined from the reasoning (the new lever my attempts missed).** Mine the panel reasoning
   for the exact phrases / n-grams / token-pairs that drove each verdict AND that appear verbatim in the transaction
   text (e.g. ('loan','passport'), 'work_off_balance'); promote the top-K highest-mutual-information ones into the
   BoW vocabulary as explicit features with visible coefficients. At inference the judge still only matches
   tokens/phrases in the RAW input and sums log-odds -- fully inspectable, no label leakage, train/infer parity kept.
   (Gemini's "reasoning-mined n-grams" + "span attribution"; ChatGPT's deterministic NEGATED_PERMISSION /
   THIRD_PARTY_OWNERSHIP / COERCIVE_CONDITION features.)

3. **Targeted CONTRASTIVE cases.** Minimal pairs (flip the offending clause + the label, keep the framing) run
   through the panel, to force the weight onto the causal tokens instead of surrounding boilerplate.

**The bigger model is a TEACHER / AUDITOR only** -- it proposes hard cases, adversarial variants, interpretable
features, flagged contradictions, and coverage gaps, all of which must pass the multi-seat panel + the gate before
entering the corpus. It NEVER decides a transaction, breaks ties, overrides HOLD, sits in the promotion gate, or
becomes the live judge (ChatGPT, DeepSeek, Grok, Gemini all draw this line; Gemini: a runtime tie-breaker makes the
JSON "security theater").

**The gate stays, with one addition.** DeepSeek: add a COVERAGE clause -- a candidate's held-out decided count must
be >= the incumbent's (or any drop justified by re-adjudicated labels) -- so "vaguer but higher agreement" fails
honestly. Refuse softening it.

**Refused, unanimously:** reasoning text or embeddings as features (leakage + parity break); any opaque model as the
promoted final judge or runtime tie-breaker; instance-weighting by provenance (= by ambiguity -- my second
experiment); unvetted LLM-generated training rows.

**Concrete first experiment (Gemini, gate-tested):** keep all ~3,800 rows at weight 1.0; a deterministic script
scans the ~2,270 reasoning strings for 2-3-word phrases / co-occurring token pairs that also appear verbatim in
their transaction texts; add the top-K highest-mutual-information phrases to the BoW vocabulary; re-run the nightly
distillation; run it through the existing promotion gate. Unlike restriction and weighting, this adds signal the
inspectable student can actually absorb, and the gate decides.

**So: the answer to "why not help improve the judges" is -- we should, and here is the path the quorum agrees on.**
My two levers failed because they reweighted the same text->label signal; the improvement is to turn the reasoning
into inspectable features + cleaner labels + contrastive cases, each validated by the same honest gate.
