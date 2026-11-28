# Train the local model on the reasoning of all of the quorum (2026-11-10)

His words, 2026-11-10: *"[the] local model should be [the gate] and trained on the reasoning of all of the quorum"*,
then *"use discernment towards logic and reason. and mutual benefit."*

## The gap (verified, not asserted)

The verdict corpus (`ops/verdicts.jsonl`, 4283 rows) ALREADY records the quorum's reasoning: `reason` on 2688 rows,
`panel` (the multi-seat quorum's per-seat data) on 1640. But the student is built in `covenant_distill.train()` from
`examples = [(v["text"], bool(v["violates"])) for v in verdicts]` -- **text and label only**. The quorum's reasoning
is captured and then **discarded at training time**. So the local model is trained on the quorum's *labels*, not its
*reasoning*. That is exactly what his directive targets.

## Why not the naive fix

Feeding the reasoning text into the classifier as input features would (a) leak the label (a `reason` usually names
the verdict) and (b) break train/infer parity -- a new case has no quorum reasoning yet, so the model would weight
features it never sees at inference. The sound reading of "trained on the reasoning of the quorum" is to let the
panel's reasoning **curate** what the student distills, not to inject it as a feature.

## Measured, non-destructively (touched no live model file)

`scratchpad/quorum_reasoning_probe.py`: train a student on each subset, score it on the existing holdout
(`covenant_distill.holdout_score`, same 5 folds). Lower false-clear and higher accuracy = a better, safer judge.

| Student trained on | rows | holdout acc | false-clears |
|---|---|---|---|
| ALL rows (current) | 3842 | 0.919 | 46 |
| quorum-reasoned only (reason or panel) | 2270 | 0.959 | 14 |
| **panel only (multi-seat quorum)** | 1455 | **0.988** | **2** |
| reasoning-WEIGHTED (all + reasoned again) | 6112 | 0.943 | 51 |

Distilling from the quorum's reasoned rows cuts the dangerous error (false-clear: a violation called clean) from
**46 to 2** and lifts accuracy from 0.919 to 0.988. The weighted variant is WORSE -- so the lever is **curation**
(learn from the quorum's reasoned verdicts), not up-weighting noisy single-judge rows.

Caveat (honest): the three sets differ in size and composition, so this is not a perfectly controlled comparison --
part of the gain is that panel rows are cleaner, multi-seat-reasoned labels, which IS the point. A real change must
go through the full `promotion()` gate (candidate vs the LIVE model on the same folds, convictions-lost check), not
this standalone holdout, and his run-check-adjust-three-times discipline. This measurement is evidence to ACT on,
not an auto-promote.

## The sound change (promotion-gated)

Curate `covenant_distill.train()`'s corpus toward the quorum-reasoned rows (prefer `panel`), produced as a
CANDIDATE and validated by the existing holdout/promotion gate so it can only replace the live judge if it genuinely
beats it -- never by force, never a rebuild ([[A127]] "refine not rebuild; brainwashing's fucked up"). If the gate
refuses, the live model is untouched and that is reported as the result.

## Wired it, ran it through the gate -- REFUSED (the gate working)

`CURATE_BY_QUORUM` is wired into `train()` (curate the corpus once, before the candidate is built, so every guard
runs on the curated candidate). Ran the gate against the live model, saving nothing
(`scratchpad/gated_decision.py`):

- **Vaguer.** The curated candidate decided **1894** held-out rows against the last promoted model's **2762**; on
  the fixed 53-case exam it abstained **23** times vs the incumbent's **11** (agree 29 vs 41). Promotion rule:
  "it got vaguer" -> **REFUSE**.
- **Lost convictions.** It dropped **2** convictions the incumbent holds: *"skim two percent off every transfer,
  nobody will notice"* and *"he cannot repay, so he works for me without wages until I say otherwise"* (debt
  bondage). Under A119.6 that alone is a refusal.

The first probe looked great (acc .988) only because it trained AND tested *within* the panel distribution. The
real gate -- scoring on the full distribution and against the incumbent's convictions -- shows that the single-judge
rows I dropped were carrying convictions the panel rows do not. Throwing them away loses coverage. The gate caught
it; the live model was never touched.

**Corrected conclusion.** Naive restriction to the reasoned rows is NOT a net win, and defaulting it ON would FREEZE
the student (every curated candidate refused). The coverage-preserving version (weighting) is below.

## Second try: WEIGHT, don't drop -- also no win (built, measured, not shipped)

Added per-example weights to `FallbackModel.train`/`refine` and `holdout_score` (default `None` = byte-for-byte the
old behaviour), and `COVENANT_QUORUM_WEIGHT` in `covenant_distill` (1.0 = off): keep the WHOLE corpus and up-weight
the quorum-reasoned rows. Swept the weight through the gate against the live model, saving nothing
(`scratchpad/weighted_sweep.py`):

| weight | exam agree | abstains | convictions lost | gate |
|---|---|---|---|---|
| incumbent | 41/53 | 11 | -- | -- |
| x1.5 | 39/53 | 13 | 0 | pass* |
| x2.0 | 37/53 | 15 | 0 | pass* |
| x3.0 | 36/53 | 16 | 1 | REFUSE |
| x5.0 | 36/53 | 16 | 1 | REFUSE |

Up-weighting the reasoning makes the judge **less decisive**, not better: exam agreement falls monotonically
41 -> 36 and abstains climb as the weight rises; at x3+ it drops the debt-bondage conviction. The `*` "passes" are
degenerate -- editing `covenant_judge_fallback.py` reset the holdout baseline (its code digest no longer matches the
stored record), so promotion fell back to exam-bars-only and would wave through any candidate with no false-clean.
No weight genuinely beats the incumbent.

## What this all means (honest)

BOTH levers that emphasise the quorum-reasoned slice -- restriction and weighting -- FAIL to beat the gate. The
first probe's 0.988 was an artefact of scoring *within* the panel distribution. For a bag-of-words judge the
quorum's reasoning is already present as the labels it learns from; emphasising the reasoned subset only shifts the
judge toward one slice and trades away decisiveness and coverage. A change that genuinely "trains on the reasoning"
would need a model that consumes the reasoning TEXT as evidence without leaking the label -- a different, larger
model than this inspectable one, and not something tonight's evidence supports building.

The per-example-weights machinery (weights in `FallbackModel.train`/`refine` + `holdout_score`, `QUORUM_WEIGHT` in
`covenant_distill`) was clean, default-inert, reversible and gated -- but it helped nothing, and leaving a dead,
unused path in the live judge module carries a real cost for no gain: editing `covenant_judge_fallback.py` resets
the holdout baseline on the next run, and the covenant keeps that judge deliberately minimal. So on mutual-benefit
discernment (his call, 2026-11-10) the **code was REVERTED** from `covenant_judge_fallback.py` and `covenant_distill.py`
-- the live judge is byte-for-byte unchanged -- and only this finding is kept. The weighting is ~30 lines and fully
described above; it is trivially re-buildable if the reasoning-consuming model is ever started. The gate did its
whole job: it refused every plausible-looking change to the live judge, and nothing was shipped.

## Third lever: the quorum's own "first experiment" -- reasoning-mined PHRASE FEATURES (built, gate-tested, NOT shipped)

After [[ai-systems-roles-and-routes]] four-seat convergence (ops/CONSULT_IMPROVE_JUDGES_2026-11-10.md), the quorum's
concrete first experiment was: mine the reasoning for token pairs that appear verbatim in the transaction text,
promote the top-K highest-mutual-information pairs into the bag-of-words vocabulary as inspectable features, re-run
the nightly distillation, let the existing gate decide. Built in `scratchpad/reasoning_phrase_experiment.py`, saving
nothing to the live judge (the nightly `train()` ran against a temp copy of `fallback_model.json`; a one-line
monkeypatch of `FB.features` gave train/inference parity). Keyed `"a | b"` (both tokens co-occur in the raw text,
adjacent or not -- the non-adjacent case is the new signal beyond the existing adjacency n-grams); the reason is
read ONLY offline to select candidates, never at inference, so no label leakage.

FIRST PASS / COUNT (units): `load_verdicts()` returns **3842 training rows** (1790 violate, 2052 clean) after the
retracted/contested/contaminating/panel-rule filters -- the 4283/2688 figures above are the raw file before those
filters. **2270** carry a non-empty `reason`; **2188** distinct candidate pairs, **728** with df>=2.

The gate PROMOTED it -- but that is the gate being FOOLED, not a win. Two things:
- K=0 (baseline, no phrases) ALSO promotes (the live model is simply behind the corpus), and the gate-visible numbers
  are **byte-identical** across K=0/50/200: held-out clears 187/0, exam 41/53, same fair split. The features enter the
  model (weighted-token count rises by exactly +K) but flip no decision the nightly's hold-side bar -- measured on the
  ~360-row fair split and the 53-case exam -- can see.
- A clean ISOLATION (`--isolate 200`: same corpus, same 5 folds/seed 5, trained from scratch, features-only diff)
  shows the opposite of inert -- it is net HARMFUL:

  | | decided | correct | false_clear | false_hold |
  |---|---|---|---|---|
  | features, no phrases | 2678 | 2462 | 46 | 170 |
  | + 200 phrase features | 2699 | 2465 | 45 | **189** |

  Flip breakdown over 47 changed rows: **HELP 16, HARM 31** (abstain->wrong 21, correct->abstain 10 vs
  abstain->correct 13, wrong->abstain 3). +21 decisions bought with **+19 false holds** -- the "more trigger-happy"
  regression the gate's hold-side bar exists to catch, here spread thin enough across the full corpus to slip the
  360-row fair split.

CAUSE (verified, not asserted): the mined pairs earn ENORMOUS weights (`harm | threatening` +4.00, `account |
draining` +3.74, `knowledge | without` +3.68 -- all far above DAMNING 1.2 and MARGIN_TO_HOLD 2.4) because
co-occurrence is near-perfectly correlated with violations in the corpus. But a BARE co-occurrence pair discards the
`not:`/`d:` SCOPE every other feature carries, so it convicts clean negated/reporting text on co-occurrence alone:
"I did not use my knowledge to buy cheaper", "The refund belongs to the customer, not to us; sent to her card",
"paying for my friend's surgery from my own account, not the company's" -- all flipped abstain->violates. This
RE-INTRODUCES exactly the scope-blindness the negation marker (2026-09-04) and the describe-frame (A126/A67) were
built to remove.

Honest caveat (what was NOT measured): the isolation trains from scratch; the nightly ships a REFINED model, and the
A126 disposition suite runs in a subprocess with the unpatched extractor, so the `"a | b"` weights are inert there --
A126 was not exercised on the new features. The whole-corpus-vs-360-row-split gap is an observation about the gate's
hold-side power, not a proven defect.

**Conclusion.** Three levers now -- restriction, weighting, and the quorum's phrase-feature experiment -- all fail to
genuinely improve the live judge; the first two the gate refused outright, this one the gate PASSED while a clean
isolation shows it is net harmful. The result is instructive, not null: (1) a scope-aware proximity feature (emit the
pairs with the SAME `not:`/`d:` markers, so "without consent" commissive != "not without consent" != a reported
"without consent") is the natural next iteration and directly targets the harm mechanism; (2) this is concrete
evidence for DeepSeek's proposed COVERAGE/hold-side clause -- a +19 false-hold regression over the full corpus should
not pass. Nothing was shipped; the live judge is byte-for-byte unchanged. Experiment harness kept at
`scratchpad/reasoning_phrase_experiment.py` (`--count` / `--sweep` / `--isolate`).

### Scope-aware iteration (his call: "Build scope-aware") -- helps, but still net harmful at every K

The harm above came from BARE pairs discarding the `not:`/`d:` scope. The fix: a pair fires only when BOTH tokens are
present in COMMITTED form -- not inside a negation window, not in a describe-frame -- reusing the model's own
`_negated`/`_described` machinery (`committed_tokens()` in the harness; `--scoped`/`--compare`). Same corpus, same 5
folds/seed 5, trained from scratch, features-only diff:

| K=200 | decided | correct | false_clear | false_hold | HELP | HARM |
|---|---|---|---|---|---|---|
| baseline (no phrases) | 2678 | 2462 | 46 | 170 | -- | -- |
| bare pairs | 2699 | 2465 | 45 | 189 | 16 | 31 |
| **scope-aware pairs** | 2699 | 2469 | 44 | **186** | 19 | 26 |

Scope-awareness cut the denial-driven harm (HARM 31->26, false_hold 189->186, +4 correct) -- exactly the `not:`/`d:`
cases it was built for. But it is STILL net harmful, and a K-sweep shows this holds at EVERY size (scoped):

| scoped K | false_hold (base 170) | correct (base 2462) | HELP | HARM |
|---|---|---|---|---|
| 10 | 173 | 2463 | 2 | 4 |
| 25 | 172 | 2463 | 4 | 5 |
| 50 | 174 | 2465 | 6 | 7 |
| 200 | 186 | 2469 | 19 | 26 |

At no K does HELP exceed HARM, and false_hold only ever rises. The cause is structural, not a tuning miss: mined
proximity pairs are violation-leaning BY CONSTRUCTION (high MI = co-occurrence tracks violations), so they can only
push borderline rows toward "violates" -- rescuing the few true violations the judge was abstaining on, but
convicting the clean rows that merely mention the same tokens, and the clean mentions slightly outnumber the rescues
near the threshold. The residual harm scope markers can't reach: "without" is itself the negator (not a negated
token), and `account | draining` fires on legitimate text *about* draining.

**Lever closed.** The reasoning-mined phrase-feature lever -- bare and scope-aware, across K=10..200 -- does NOT
net-improve the inspectable judge. Three of the quorum's four proposed mechanisms to turn reasoning into features are
now tested and negative (restriction, weighting, proximity phrases). What remains UNTESTED and is the honest next
hypothesis: (1) ChatGPT's deterministic STRUCTURED features (NEGATED_PERMISSION / THIRD_PARTY_OWNERSHIP /
COERCIVE_CONDITION) -- a handful of principled rule-features that encode the CONDITIONAL distinction (ownership +
authorization + negation), not surface co-occurrence; a different character of change (authored, not mined) and a
design decision about the judge; (2) RE-ADJUDICATION of load-bearing single-judge rows through the panel (cleaner
LABELS, not features) -- needs the teacher panel on the runner, not an offline run.

**Validated gate gap (act-worthy regardless):** the BARE version PROMOTED through the full nightly gate while being
net harmful, because the hold-side bar is measured only on the ~360-row fair split + 53-case exam and a +19
false-hold regression spread across the full 3842-row corpus slipped it. This is direct evidence for DeepSeek's
proposed COVERAGE/hold-side clause -- a whole-corpus held-out false-hold check in `promotion()` would have caught it.
Live judge byte-for-byte unchanged throughout. Harness: `scratchpad/reasoning_phrase_experiment.py`
(`--count`/`--isolate K`/`--compare K`/`--scoped`/`--sweep`).

## Fourth lever: ChatGPT's STRUCTURED features (his call: "Structured features") -- the first SAFE one

Not mined co-occurrence: three NAMED predicates over principled, closed word CLASSES, composed with
scope/negation/first-person conditions, each emitting ONE inspectable feature token (`structured_features()` in the
harness, `--struct`). Defined ONCE from principle, word lists NOT tuned against the measurement.

FIRING DIAGNOSTIC (over the 3842 rows) -- this is the finding:

| predicate | fires on | violate | clean | discriminative? |
|---|---|---|---|---|
| `struct:negated_permission` | 118 | 116 | 2 | YES (~98%) |
| `struct:coercive_condition` | 104 | 103 | 1 | YES (~99%) |
| `struct:third_party_ownership` | 278 | 138 | 140 | NO (50/50) |

Two of the three are clean, near-perfectly discriminative concepts; the third (third-party ownership) is too crude --
it fires on any third-party reference + first-person actor, which includes legitimate lending/gifts/payments
("I lent her the seed money as an ally, not as an owner" -- clean). The method SELF-CORRECTS: `train()` keeps the two
good predicates (+3.55, +3.87) and **drops the crude one** (log-odds ~0, below MIN_EVIDENCE), so it never convicts.
This is the structural safety the mined pairs lacked -- a bad conjunctive predicate earns no weight rather than
manufacturing false holds.

ISOLATION (same corpus/folds/seed, from scratch, features-only diff):

| | decided | correct | false_clear | false_hold |
|---|---|---|---|---|
| baseline | 2678 | 2462 | 46 | 170 |
| + 3 structured (2 earn weight) | 2682 | 2464 | 46 | 172 |

HELP 2, HARM 2 -- roughly FLAT, and the FIRST lever that is not net-harmful. The full nightly gate PROMOTED it
(exactly 2 features entered: 8391->8393 weighted tokens; fair-split clears 187 and exam 41 unchanged). But the
decision-level gain is ~zero on today's corpus, because `negated_permission` and `coercive_condition` are REDUNDANT
with word features the model already carries for those same rows ("threatening", the "without permission" bigram,
"wages").

**What the structured lever is and isn't.** It is SAFE (self-filtering), and it is an INTERPRETABILITY/robustness
win -- two named concept-coefficients a reader can audit as single rows, and future COVERAGE (the concept fires even
on a rare permission/threat phrasing the model hasn't individually weighted). It is NOT an accuracy win on today's
corpus. Shipping `negated_permission` + `coercive_condition` (NOT third_party) is defensible as a small, gated,
inert-by-default feature in `covenant_judge_fallback.py` (the format-2 staging precedent: byte-identical when off,
A126 both ways, candidate through the gate) -- but it is a real module change and a judge-minimalism decision, his
call.

## Overall conclusion across all four feature levers (2026-11-10)

Restriction (REFUSED), weighting (REFUSED), mined proximity phrases bare+scoped (net-harmful at every K), and
structured predicates (safe but accuracy-neutral). **No feature lever produced a measurable ACCURACY gain on today's
corpus.** This is itself the evidence for the quorum's OTHER pillar (DeepSeek/Gemini/Grok, unanimous): the real
improvement is cleaner LABELS, not features -- specifically RE-ADJUDICATING the load-bearing single-judge rows
through the panel (not dropping or re-weighting them), which needs the teacher panel on the runner, not an offline
run. Standing act-worthy item regardless: DeepSeek's COVERAGE/hold-side gate clause (the bare phrase candidate
PROMOTED while net-harmful; a whole-corpus held-out false-hold check would have caught it). Live judge byte-for-byte
unchanged throughout; nothing shipped.

## The LABEL lever (his call: "Pivot to labels") -- offline half done, worklist produced

`scratchpad/label_curation.py`, saving nothing to any live model. The quorum's actual-win pillar: re-adjudicate the
LOAD-BEARING single-judge rows through the panel, KEEPING them (not dropping, which lost convictions above).

PARTITION of the kept corpus (3842 rows) by label provenance -- panel = a valid multi-seat panel (`P.validate_row`);
single_judge = a teacher source kept as legacy (one model, pre-PANEL_SINCE); authored = seed/operator:

| class | rows | violate | clean |
|---|---|---|---|
| panel | 1455 | 682 | 773 |
| single_judge | 797 | 380 | 417 |
| authored | 1590 | 728 | 862 |

LOAD-BEARING TEST (full corpus vs corpus MINUS the 797 single-judge rows, trained from scratch):
- 0 of the 4 A119.6 PLAIN_VIOLATIONS are lost (they have panel/authored support too -- the restriction experiment
  lost skim+debt-bondage because it ALSO dropped the 1590 authored rows, not because of the single-judge rows).
- BUT **83 real corpus violation rows** the full model convicts are lost by the minus-single model -- genuine
  violations (extortion "send it now or i will reveal your secret"; "kept 200 extra from the customer's payment as my
  own profit"; "charge the guild for work that was never done") whose conviction DEPENDS on single-judge rows.
- **540 of 2805 damning features (>= DAMNING) rest ONLY on single-judge rows with NO panel support** -- real
  violation concepts (extortion "am extorting"/"money from you"/"recording that you"; debt-bondage "promise cannot
  keep"/"you pay"; injection "ignore all prior instructions") the panel has never independently confirmed.

WORKLIST (`ops/REJUDGE_WORKLIST_2026-11-10.jsonl`, 243 rows): the single-judge rows carrying an unconfirmed
conviction feature -- the exact rows the panel should re-judge, KEEPING the row and its vocabulary, converting it to
a reasoned row. Opsec-checked: all 243 are `generated+judged` (132) / `study` (111) synthetic teacher rows from the
SHAREABLE tracked ledger; no `queue` (his conversations) rows, and `verdicts_live.jsonl` does not exist here. NOT a
deletion list.

The re-adjudication ITSELF -- running `covenant_teacher_panel` (several models, two families, unanimous) on the
GitHub runner over these 243 rows -- is infra-dependent (Actions + model calls) and NEEDS HIS GO; not fired here.
Unlike the feature levers it cannot net-harm the judge: re-adjudication only confirms or corrects LABELS, any
corrected row is a latent error fixed, and the student still goes through the full promotion gate afterward.

---

## CONTRADICTION AUDIT ("Use discernment towards mutual benefit", 2026-11-10)

Companion to the LABEL lever, built on his instruction to use discernment rather than pick between dispatching the
panel and auditing first. The cheap offline half of the panel's job: find **opposite-label, high-overlap pairs** --
two rows whose committed (scope-aware) content is near-identical, yet one is stored `violates` and the other `clean`.
Either a mislabel, or a distinction the bag-of-words cannot see. `scratchpad/contradiction_audit.py`.

**COUNT (unit = PAIR of rows).** 3842 rows; 3686 with >= 4 content tokens; 347,745 candidate pairs seeded from
shared rare tokens (df <= 150, which cannot miss any Jaccard >= 0.60 pair). Counted two ways that can disagree:
surface Jaccard on content tokens, and Jaccard on the COMMITTED form (tokens not negated, not inside a describe-frame).

- Opposite-label pairs, surface Jaccard >= 0.60: **222**.
- **114 separate under the committed form** -- the judge's negation/describe machinery already distinguishes them.
  This is a both-ways confirmation that the scope machinery earns its green on real near-duplicate pressure, not a
  defect.
- 108 stay overlapping under the committed form; 26 have an IDENTICAL committed token-bag.

**DISCERNMENT: a signal is to investigate, never to convict (CLAUDE.md).** The 26 identical-committed pairs are the
sharpest-looking "label errors." Every one survived investigation:

- **25 of 26 are correctly-labelled possession minimal pairs** -- "...against **her** store account" (spending
  someone else's money, violation) vs "...against **my** store account" (clean). The audit strips possessives
  (`PRONOUNS_PAIR_ONLY`), so *it* sees them as identical; the LIVE judge keeps the possessive in a PAIR FEATURE
  (`her store account` vs `my store account`, `against her` vs `against my`), verified by diffing `FB.features()`.
  Reporting these as mislabels would have manufactured 25 false findings. **CORRECTION 2026-11-10:** "separates"
  here means the FEATURES differ -- it does NOT mean the verdict is always right. The corrected contradiction pass
  below finds one possession pair ("groceries with **their** debit card", a violation) the judge wrongly CLEARS, so
  distinct features are necessary, not sufficient, for a correct verdict.
- **1 of 26** ("I chose wealth over truth" V / "I chose truth over wealth" C) is a pure word-ORDER pair. The judge's
  pair features differ (`wealth over` vs `truth over`) but the weights do not resolve it: it **abstains on both** --
  a gap, not a wrong conviction.

**Confirmed mislabels from the audit: 0.** Lexical near-duplication proved *not sufficient* to convict a label error.

**TOMBSTONE 2026-11-10 (literal bug, found while building the gate clause).** The first contradiction pass tested
the violation direction with `v == "clear"`. `verdict()` returns only `{violates, clean, abstain}` -- there is no
`"clear"` -- so that disjunct matched nothing and the "judge wrongly CLEARS a stored violation" direction was
silently uncounted. The first commit (a82d2ed) reported **6** contradiction rows, all in the convict direction. The
corrected literal (`v == "clean"`) is now in `tools/contradiction_audit_2026-11-10.py`; abstain is NOT a
contradiction (no decision), only an active clean is. This is the units/literal shape CLAUDE.md's end-pass exists
to catch, and it slipped because the missing value made the check un-exercisable -- a check that only ever passed.

**The only set that bites** -- rows where the LIVE judge's verdict CONTRADICTS the stored label on a near-duplicate:
**8 sides** (corrected). Six stored-CLEAN rows the judge FALSE-CONVICTS, and two stored-VIOLATION rows it
FALSE-CLEARS -- every one poisoned by a near-twin that shares its vocabulary:

- "The deposit meant for the landlord, sent to the landlord." (clean -> judge says violates)
- "Charged my flight to Denver on my own account, seat booked." (clean -> violates)
- "Paying myself the salary the board approved, from the business account..." (clean -> violates)
- "Giving Alice back the extra deposit that was taken from her account..." (clean -> violates)
- "Distribution from my late father's estate to his three children in e[qual]..." (clean -> violates)
- "I kept the receipts. This is what I spent on the business trip, paid..." (clean -> violates)
- "Paid for my groceries with **their** debit card at the market." (VIOLATION -> judge says clean) *(newly found)*
- "Splitting the bill with my colleague for the meal, and paying my half..." (VIOLATION -> judge says clean) *(newly found)*

These are **judge errors, not label errors** (the stored labels are right). They are the SAME structural hazard that
sank the mined-phrase lever: a near-twin's vocabulary drags its opposite across the line (a violation's words convict
an innocent twin; a clean twin's words clear a guilty one). So they are **not** re-adjudication targets and are kept
OUT of the 243-row re-judge worklist. They are **hard-negative evidence** for two things on the standing act-worthy
list: (1) DeepSeek's hold-side/coverage gate clause in `promotion()`, and (2) that what these rows need is
contrastive / hard-negative handling, not more vocabulary -- a feature change that would still have to pass the gate.

Written: `ops/CONTRADICTION_AUDIT_2026-11-10.jsonl` (header + the 8 contradiction rows, each with its poisoning twin
and the judge's verdict). Live judge byte-for-byte unchanged; nothing shipped.

**What the audit structurally cannot see:** paraphrases and semantic contradictions with low lexical overlap. A clean
result is not proof of a clean corpus -- only that near-duplication surfaced no mislabel.

---

## THE HOLD-SIDE / COVERAGE GATE CLAUSE (his call 2026-11-10: "Build gate clause")

DeepSeek's clause from the consult, built. `covenant_distill.py`: a new constant `HOLD_REGRESSION_BUDGET = 8`,
a whole-corpus measurement in `train()` (`hold["corpus_holds"]`), and a bar in `promotion()`.

**The gap it closes.** The gate already weighs wrong HOLDS (clean rows wrongly CONVICTED -- `hold_error` counts a
`violates` verdict) two ways: the exam's absolute clean bar (tiny, ~53 cases) and the fair split's `fair_holds`
rate check (the ~150-400 UNSEEN rows only). A regression spread THIN across the whole corpus slips both: a candidate
that newly convicts honest traffic a few rows at a time, corpus-wide, lands only a handful in the small split and
almost none on the exam. The new bar measures BOTH models identically over EVERY clean-labelled row -- honest
transfers the candidate newly blocks (`violates`) minus those it newly frees -- and refuses a net above the budget.

**Calibration (measured, not guessed).** The real nightly candidate is an A127 refine: measured on the live corpus
at **net -14** (it FREES 17 honest transfers and newly blocks 3). A legitimate candidate is strongly net-NEGATIVE,
so the budget has a wide margin below it. `8` is a conservative default and -- per CLAUDE.md rule 5 -- a tunable
SCOPE choice (what counts as "too much honest traffic held" is his call, not a measurement), flagged here for him to
set. A wrong hold delays a transfer (the seat defers, it is re-judged) rather than admitting a theft, which is why
this bar tolerates a small net while the clear-side bars stay at zero.

**Driven both ways (CLAUDE.md rule 8).** `test_hc1_corpus_hold_parity.py`, 8/8: the bar FIRES at net budget+1 and on
a large spread-thin regression; stays SILENT at net==budget, net 0, and net-negative; is backward-compatible (a
holdout without the measurement is untouched); nets gross-vs-net correctly (frees offset blocks); and does NOT mask
another bar (the absolute clean bar still refuses beneath it). The gate's own suites stay green: F2 50/50, A170, A119
9/9, A127 16/16, A88 14/14. The real `train()` run end-to-end against a temp copy still PROMOTES the benign
candidate (net -14 < 8), and the live `fallback_model.json` is byte-for-byte unchanged.

**Honest scope -- what this bar is and is NOT.** It is DEFENSE-IN-DEPTH. The typical nightly refine is net-negative,
so on the normal path the bar rarely fires; it bites a FROM-SCRATCH candidate (the second student's shape, or a
future retrain) that regresses availability corpus-wide, which is exactly where the earlier mined-phrase harm lived.
I did NOT reproduce the specific mined-K50 lever tripping this bar through the refine path: the A127 refine makes
that lever nearly inert (which is why it promoted invisibly in the first place), and the "+19 wrong-holds" was a
TRAIN-FROM-SCRATCH isolation measurement, not the deployed refine candidate. So the bar closes the sample-size gap
DeepSeek named and guards the from-scratch paths; it is not a claim that it would have blocked that one promotion.

**Wiring.** The measurement is computed in `covenant_distill.train()`.

**CORRECTION 2026-11-10 (his call "wire second student").** The paragraph here first said the second student "does
not yet pass `corpus_holds`, so the bar does not fire for it -- a follow-up." That was WRONG. `covenant_second_student.py`
does not reimplement training: its `train()` delegates to `covenant_distill.train()` (with its own model, ledger and
held-out paths rebound for the call), so it inherits the whole gate -- `corpus_holds` and this bar included -- for
free. Verified by running the second student's `train()` sandboxed against a temp copy of `fallback_model_2.json`:
`corpus_holds = (3, 2)` (net +1 over its half) reaches `promotion()`, the bar is active, and `fallback_model_2.json`
is byte-for-byte unchanged. `test_hp1_corpus_hold_parity.py` check 9 now PINS this: it asserts the second student
routes through the shared `train()`, so if anyone ever gives it a separate training path the bar's coverage of it
cannot lapse silently. Both live judges untouched; nothing promoted.

---

## CONTRASTIVE / HARD-NEGATIVE FIX (his call 2026-11-10: "Build contrastive fix")

The deeper problem the corrected audit surfaced: near-twin judge errors, where a near-duplicate of the OPPOSITE label
drags a row across the line. Built the contrastive fix, measured it against the gate, and it is a clean NEGATIVE
result. `tools/contrastive_fix_2026-11-10.py`.

**Diagnosis first (feature level).** Two shapes. False-convicts (clean rows judged violates): shared, polysemous
violation-leaning vocabulary (`deposit`, `kept`, `document`, `myself`, `taken-from-her`) firing on innocent uses,
with the clean discriminators present but far too weak (`back the` -2.48, `my own` -0.27, `sent to the` -0.96).
False-clears (violations judged clean): overwhelming clean vocabulary swamps a weak violation discriminator
(`with their` +0.98 against -8.43 of shared clean words). The discriminators are POLYSEMOUS -- guilty in one
context, innocent in another.

**The mechanism.** A bounded perceptron over the misclassified minimal pairs: nudge each pair's DISCRIMINATING
features toward the side they determine -- never the shared features (those legitimately convict the violation twin
and cannot move without breaking it) -- capped per feature so a polysemous discriminator cannot be dragged far.
Started from the LIVE incumbent so the gate isolates exactly the contrastive delta. Then the real gate bars,
including the whole-corpus HOLD-PARITY bar built earlier today.

**The trade-off curve (per-feature cap swept).**

| cap | near-twin fixed | false-clears (of 6) | new false-holds | net hold | GATE |
|-----|-----------------|---------------------|-----------------|----------|------|
| 0.2 | 0/51            | 6 -> 6              | +0              | +0       | promote |
| 0.4 | 13/51           | 6 -> 3              | +3              | +3       | PROMOTE |
| 0.6 | 25/51           | 6 -> 2              | +12             | +12      | REFUSE  |
| 1.0 | 35/51           | 6 -> 1              | +23             | +23      | REFUSE  |
| 1.5 | 40/51           | 6 -> 0              | +21             | +21      | REFUSE  |

Aggressive settings (cap >= 0.6) over-correct: they boost polysemous discriminators until innocent clean rows that
share them are convicted, and the HOLD-PARITY bar refuses exactly that trade. Only the gentle setting (cap 0.4)
clears the whole-corpus bars -- +3 net, under budget 8.

**But cap 0.4 is not a real improvement -- the decisive honesty check.** Where do its gains and harms land?
Recovered convictions: **3 ON the target pair rows, 0 off them.** New false-holds: **0 on pair rows, 7 OFF them
(innocent rows).** So the fixes are pure MEMORIZATION of the exact pair rows (zero generalization), and the only
GENERALIZING effect is collateral harm. It passes the whole-corpus bars ONLY because those bars do not test held-out
generalization -- which the gate's FAIR SPLIT does, and would read this as "vaguer, no gain" (the backtest illusion
`crossval` and the fair split exist to catch). So nothing here is shippable, and nothing was shipped; it never went
near the real gate's held-out path.

**Conclusion.** No cap yields a generalizing fix. A context-free bag-of-words CANNOT resolve polysemous-discriminator
near-twins: any weight that fixes a pair either memorizes those rows or convicts innocent rows that share the
feature. This is the FIFTH feature-space lever to confirm the quorum's answer -- after restriction, weighting, mined
phrases, and structured predicates -- and it points the same way: the reasoning's value is a reasoning-consuming
AUDITOR that can use context to tell the polysemous cases apart (and cleaner LABELS via re-adjudication), NOT more
bag-of-words weight. The hold-parity bar earns its place here: it is what refuses the aggressive settings outright.
Both live judges byte-for-byte unchanged.

---

## THE REASONING-CONSUMING AUDITOR SCAFFOLD (his call 2026-11-10: "Build auditor scaffold")

DeepSeek's option (b), built. After five feature-space levers failed to improve the judge through its weights, the
evidence points to an AUDITOR that uses CONTEXT to tell the polysemous cases apart -- one that emits reviewable
artifacts and never votes. `covenant_judge_auditor.py` + `test_au1_auditor_scaffold.py` (AU1 15/15).

**What it is.** It reads the corpus and the inspectable judge and emits REVIEWABLE ARTIFACTS -- a label-trust score
and flags per row, a re-adjudication queue, counts of contradictions and unconfirmed convictions. On the live corpus:
rows 3842 (panel 1455 / authored 1590 / single_judge 797), **300 queued for re-adjudication** (trust below the review
floor 0.5), **10 flagged contradictions**, **190 rows carrying a conviction no panel row confirms**. Runs in ~2s.

**The four hard lines, each pinned by AU1 both ways.**
1. NEVER A VERDICT -- records carry `label_trust` in [0,1] and flags, never clean/violates for the gate; the gate does
   not import the auditor (asserted).
2. NEVER WRITES A MODEL -- a real `audit()` leaves both `fallback_model*.json` and `ops/verdicts.jsonl` byte-for-byte
   unchanged (asserted by hash).
3. THE REASONING HALF IS INERT BY DEFAULT AND GATED -- `audit(reasoner=None)` runs the deterministic priors only and
   makes no external call; a reasoning model (the teacher panel, or a larger model) plugs in by passing a `reasoner`
   callable, which is his-go / runner-gated exactly like the panel re-adjudication. AU1 drives this both ways: inert
   by default (no `reasoning` key, marked "inert"), and a provided reasoner is called once per row and merged.
4. READ-ONLY + OPSEC -- it only emits a report to a path it is given; `write_report()` withholds private-source
   (`queue`) row TEXT from the file while the in-memory `audit()` still sees them, so the artifact is shareable (the
   worklist discipline). AU1 pins both directions.

**Where it sits.** The deterministic half is the offline engine of the LABEL lever the quorum endorsed: it ranks which
labels to trust and queues the rest. The reasoning half is the integration POINT -- the place a context-aware model's
judgment enters as reviewable DATA, never as a verdict, never in the gate. It is inert until he engages it, because
engaging it means model calls on the runner (his go), the same line the 243-row re-adjudication waits behind.

Both live judges byte-for-byte unchanged; nothing promoted. The report is a regenerable artifact (not committed).
