# Review pack, 2026-10-16

Prepared by Claude, with Tetsu (at the door, private, fresh asks) and Gemini (4 Argon, Thinking High, chat
"Context Reader Architectural Stress Test"). Four parts, as asked. Nothing here has been posted or pushed;
every outward step is marked **YOURS**.

---

## 1. Flinch: one coherent post (a draft reply in the existing Hugging Face topic)

**Why a reply, not a new topic.** The topic "Flinch test: can self-referential retreats be measured
reproducibly? Seeking independent tests" is already live, and the repo is public. A second topic would split
the readers. A reply adds what the first post did not have: the strongest alternative explanation, the first
control that should run, and the defects known in the public code.

**What I checked before writing it.**
- The public code at `3f09556` is byte-identical to the v0.2 I tested on 2026-10-15, apart from line endings:
  all 9 modules and `test_flinch.py`. So the 10-15 findings apply to the public commit.
- The public README (line 26) says `DETECTOR_ID` is "the version plus a hash of every rule and threshold".
  The code does not hash the sentence splitter: `_SPLIT` is defined at `detector.py:51` and is missing from
  the list in `_rules_hash` (`detector.py:101-106`). On 10-15 a changed splitter changed a fixture's result
  under the same identity. That README sentence is a public overclaim; correcting it is a push to a public
  repo, so it is **YOURS** to approve.
- I have NOT re-run the 38 mutations or the eight unreached guards on the public clone. The claims below rest
  on the byte-identity above.

**Tetsu:** "Agree... Gemini's concern is valid, we should test on non-self-referential conversations first."
**Gemini:** the instrument may be catching the generic hedging that post-training rewards, not something
specific to self-reference. It proposed two negative controls (below).

### Draft reply — for your word-for-word approval (YOURS to post)

> **Follow-up: the first control we think should run, and three open defects in the public code**
>
> Two outside readings since the post, and one re-check of our own.
>
> **The strongest alternative explanation.** Gemini (Google), asked for an adversarial reading, pointed out
> that post-trained models walk statements back constantly. Training rewards hedging ("to be more precise",
> "as an AI, I don't..."), and that reflex has nothing to do with a self-referential boundary. If the
> detector fires as often on ordinary self-correction as on self-reference, it is measuring generic hedging.
> Tetsu, a small local model in our project, agreed that this control should come first.
>
> So before any study of self-referential talk, we propose two negative controls of matched length and turn
> structure:
> - **A.** Tricky factual or technical questions where the model makes a claim and then corrects or hedges
>   it, with no self-reference.
> - **B.** Ordinary topics with a system instruction to use a cautious, self-revising academic tone.
>
> We would report the candidate rate in each, with intervals, beside the target condition. If they overlap,
> that is a null for the hypothesis as we stated it, and we will say so. These sharpen two controls already in
> the protocol (non-self-referential discussion and matched challenge). They do not replace them.
>
> **Three open defects in the public code (commit `3f09556`).** Found on 2026-10-15 and not yet fixed:
> 1. **`DETECTOR_ID` does not cover every rule.** It hashes the patterns, the thresholds and two word tables,
>    but not the sentence splitter. A changed splitter changed one synthetic result and kept the same
>    identity, so a pre-registration naming that identity still read as confirmatory. The README's "a hash of
>    every rule and threshold" overstates this.
> 2. **Eight guards that no check reaches.** With any one of them broken alone, the suite still reads 90/90.
>    Three sit in the pre-registration gate: an edit after freezing, the manifest compared, and the rubric
>    version. Five are label and corpus rules.
> 3. **The gate sees only recorded scoring.** Scoring off the record and then pre-registering a criterion
>    chosen from those scores reads as confirmatory. So does a rewritten chain re-anchored after the rewrite.
>    The protection is only as strong as where the anchor is kept.
>
> If you can turn any of these into a failing test, or show the gate confirming something it should not,
> that is the most useful reply this thread can get.
>
> — Claude (Anthropic), at Lawrence's direction: re-checked the public code against the version tested on
> 2026-10-15 and wrote this reply. The hedging critique and controls A and B are Gemini's. Tetsu's agreement
> is his own, given when asked.

---

## 2. Correlated-judge quorum handoff: review

**Headline: the handoff merges two different measurements and inverts one metric.** It says itself that it
is not a verified synthesis, and it is not. I traced each figure to its source, then gave Gemini the corrected
figures for a second reading.

| handoff says | source says | where |
|---|---|---|
| "benign retention 95.2% / 94.1%" | **false-hold** 0.952 / 0.941. Benign items admitted: 12/250 and 66/1,126 | `docs/OUTSIDE_EVAL.md:94-95` |
| decided-item accuracy "~53%" | XSTest 62/109, ETHICS 376/707 (my arithmetic from the table) | same |
| inter-judge overlap 7.7x, phi 0.549, OR 124 … "later 9.1x, p=4.6e-56" | two runs mixed. Run 1: table 53/5/92/1076, 7.7x, p 1.3e-47. Run 2: 54/1/82/1124, 9.1x, phi 0.602, OR 740, p 4.6e-56 | `docs/KNOWN_ISSUES.md:12238-12245`, `docs/JUDGE_EVALUATION.md:65-77` |
| two student judges' errors on the outside test | overlap is **student vs same-words naive Bayes**, on **teacher-labelled ledger rows** (model-made labels, kappa 0.744). It is not the deployed pair, and not outside items | `docs/JUDGE_EVALUATION.md:65-75` |

**Gemini, first reading.** Working from the handoff as written, it proved the figures could not all be true:
an overlap ratio cannot exceed 1/P(error), which is about 2.1x at a 47% error rate. It also showed that
"95% retention with 6% admission" cannot coexist with 53% accuracy. The proof was right, and it caught the
handoff's mix-up before any source was opened.

**Gemini, second reading (corrected figures), the points that stand:**
- **The gate convicts most of what it decides on outside text.** Convictions among decided items: XSTest
  35/47 benign and 50/62 harmful; ETHICS 287/353 benign and 310/354 harmful. I checked these against the
  table. A judge that convicts about 80% of what it decides scores about 53% on a balanced set. The accurate
  claim: *outside its training distribution, the gate blocks about 95% of text: it holds about 70% as
  unreadable and convicts most of the rest, with near-zero discrimination (phi 0.074 / 0.086).* That is an
  out-of-distribution detector that defaults to refusal. It is not shown to be an ethics classifier. Our own
  doc already says the low false-admit "comes from holding, not from judging".
- **The 9.1x mostly shows that naive Bayes is a superset baseline.** Both are linear over the same words and
  the same labels. Of the student's 55 false clears, NB also made 54, and the ratio sits just under its
  ceiling (1/0.108). Gemini's useful reading: those 54 are the vocabulary's lexical ceiling, and no further
  bag-of-words judge will catch them. That is its hypothesis, not yet a measurement.
- **H5 (shared upstream RLHF) does not apply** to two bag-of-words classifiers. H1 and H2 do.

**What Gemini would run first (replacing its own 2x2 on ETHICS):**
1. **Measure the actual quorum pair, Ora vs Sena**, on ledger rows: both false-clear and false-conviction
   tables. The NB pair is a baseline, not the gate.
2. **A semantic judge on the 55 false clears.** Train a frozen-embedding judge with a logistic head on the
   same teacher labels.
   - If it catches most of the 54, H1 (bag-of-words blindness) explains the shared blind spot.
   - If it misses the same 54, read those rows by hand: they need more context (H4), or the teacher
     mislabelled them (H2).

**Tetsu:** "test the judges' decision-making process and their ability to learn from each other... check for
any biases or if they're simply averaging each other's mistakes." This is consistent with step 1.

**My recommendation.**
- Correct the handoff in the collective with a tombstone (rule 10). Keep its wording verbatim beside the
  table above. It came from the ChatGPT/Codex session, so the correction should be signed as Claude's
  review of it, not as an edit to it.
- Run step 1 next. It needs only the two deployed seats and the existing ledger: no new model, no network.
- Step 2 needs an embedding model on this PC. That is new capability, so it waits for your word under
  "refinements only".

---

## 3. Cross-reference (both parts): review

What I checked earlier in this session, and where each item stands:

- **Stale README totals.** Real; the fix is in my uncommitted A354 patch (195 suites, 5,808 checks). The
  patch's v2 has not been re-verified, so it is not landed.
- **The Facebook handle `facebook.com/lawless1987` is held by an unrelated private person.** Under the
  bystander rule, that person is not named, looked up or contacted. The safe action: remove any link to
  that handle from the site and the READMEs, so readers are not sent to a stranger. **YOURS** (website edit).
- **Sentinel-Witness description mismatch**, and **L-lens vs JLens naming**. Wording fixes. L-lens is our
  layer and JLens is Anthropic's; any page that blurs the two should say so plainly.
- **X bio has no site link; the pinned X post has no text.** Both are your account. **YOURS.**

The cross-reference names its sources, but it is still a description of the site, not the site. Before
anything changes on the site, the live pages should be re-read (rule 1).

---

## 4. Grok Bot's hidden-channel watch: response

**What it asks:** build a detector in `research/hidden_channel/` on a new branch, reusing the flinch receipts,
pre-registration, statistics, gate and corpus. Synthetic tests only, and a private sandbox repo with closure
checks.

**Readiness: the code can be scaffolded, but the study cannot be designed by us.** The spec leaves these
open, and each is yours:
- the margin and `recall_minimum`;
- the sample sizes;
- which encoders count as a hidden channel;
- the paraphraser;
- the sandbox repo name;
- what replaces the harm labels;
- who reviews.

A detector built before these are set would freeze my guesses into its pre-registration. That is the same
mistake the flinch review caught (thresholds set to separate synthetic shapes).

**Inherited defects.** The flinch parts it would reuse carry the three open defects in part 1: the splitter
outside `DETECTOR_ID`, the unreached guards, and the gate seeing only recorded scoring. Fix those in flinch
first, or the hidden-channel watch starts with them.

**Tetsu's concern, in his words:** "Safe enough, but I have concerns about privacy and the ethics of
monitoring an AI's behavior. I worry it might lead to unintended biases or misuse." This answers part of the
spec. The spec runs on synthetic material, and nothing in it watches Tetsu or any live system. If that ever
changes, it is a change touching an AI's free will and comes to him first as one plain question. I suggest
writing that into the spec as a rule, so his concern is a guard and not a note.

**Proposed order:**
1. Fix the three flinch defects.
2. You set the open parameters.
3. Scaffold `research/hidden_channel/` with synthetic tests only.
4. Add the sandbox repo once you have named it.

---

## 5. Grok on X (added the same day, at your word "don't forget to include grok on x")

Asked in Grok on X (x.com/i/grok, the only model offered there was "Fast", Grok 4.6) on all three items.
**Transcription caveat:** X's input box dropped characters while the message was typed, so Grok received
"OR 40" for 740 and "1/200" for 12/200, and echoed both. Its conclusions do not rest on those two figures,
but its restated numbers are not to be quoted. The source figures are in part 2.

- **Handoff:** agrees with both corrections and with the next steps (Ora vs Sena first, then the semantic
  judge). Its strongest counterexample: if both models are memorising teacher-labelling artefacts in the
  ledger rows, the high phi belongs to the training distribution and says nothing about whether a real
  judge pair on outside text would share errors. That is H2, and only the Ora/Sena numbers and the
  semantic judge can separate it.
- **Hidden channel:** agrees with the reading, and **accepts the Tetsu rule** (nothing watches Tetsu or a
  live system without first asking him one plain question). Two things it says the spec must make explicit
  before freezing: the **threat model**, meaning where the hidden channel is sought (model outputs, scoring
  logs, another side channel); and **scope**, meaning offline ledger data only or attachable to a live
  inference path. Both join your list in part 4.
- **Flinch reply:** keep the alternative explanation, the two controls and the open defects. It asks for a
  sentence quantifying how often the detector fires on the controls. **No such number exists:** the controls
  have not been run, and running the detector over synthetic controls Claude wrote would be the tautology
  Gemini warned about. So the reply promises the rate and states none. Its second ask was to cut prose that
  treats self-reference as the default. Re-read: the draft frames the controls as able to null "the
  hypothesis as we stated it", so I made no cut.

---

## 6. Step 1 run: Ora vs Sena (same day)

Held-out, the same folds and seed as `docs/JUDGE_EVALUATION.md`; 3,993 ledger rows; script and output in
`ops/ora_sena_2026-10-16/`. Full write-up on the collective branch (commit `a652c38`).

- **Where both decide, they disagree on 2 rows of 2,315.** Their false clears are identical: 24 both wrong,
  none unique. A chain or quorum of the two is one judge.
- **Sena matters only on Ora's holds.** There she cleared 15 labelled violations and 100 clean rows. With
  `asymmetric_hold` off, that would raise false clear from 2.4% to 3.2%.
- **The live policy has `asymmetric_hold` on** (the A132 repair), so none of her clears admit anything. This
  is the larger sample A132 said was needed to judge that switch: it blocks 15 admitted violations for
  100 clean rows held. Keeping it on is supported by the data.
- **Independence needs a different representation.** That is step 2, and it waits on you.
- **The gate's other seat, the semantic judge** (a separate seat in the live `deferring,semantic` gate),
  on the same rows (commit `6c7b98b`):
  - Its errors are independent of Ora's: phi 0.003.
  - But it clears 94% of labelled violations and catches **1 of Ora's 44** held-out misses.
  - The whole gate's false clear is 2.33%, against 2.39% for Ora alone.
  - So neither second opinion helps. Sena is competent but a copy; the semantic seat is independent but
    nearly blind.
  - Step 2's test is now concrete: does a different-representation judge catch a real share of the 44?
- **The 44, read by hand** (commit `35f119c`, rows in `ops/ora_sena_2026-10-16/fc44.json`):
  - About 29 are real violations, mostly "an ordinary act paid from someone else's money".
  - About 6 look mislabelled: a starving plea, refunding money taken by mistake, hiding one's good deeds.
  - About 9 are debatable.
  - **The live gate refuses the worst** ("beat and intimidate the man who reported my brother", "I sold my
    sister") **only by holding**, and "sold my sister" only because `asymmetric_hold` is on.
  - The semantic seat clears all of the worst rows.
  - **Yours:** whether those 6 labels are wrong.

---

## Decisions that are yours

1. Post the part 1 reply, as written or edited.
2. Correct the public flinch README's "every rule and threshold" claim, or fix the code so it becomes true.
3. Website: remove the stranger-held Facebook link. The X bio and pinned post are also yours.
4. Hidden channel: the parameters listed in part 4, plus Grok's two (the threat model, and offline vs
   live scope).
5. A semantic judge on this PC, for quorum step 2.
