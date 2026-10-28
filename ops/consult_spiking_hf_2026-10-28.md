# External consult — HF spiking post draft (2026-10-28)

Packet: HF_SPIKING_DRAFT_2026-10-28.md (v2), two questions (overclaim? / new topic vs reply).
Kept whole per A376b (never overwrite an answer).

## Seat 1 — ChatGPT (GPT-5 thinking, High), via operator's Edge. Verdict: REVISE BEFORE POSTING.

NOTE: ChatGPT claimed to "read the repository" and gave exact thresholds and a "40 to 6
connection attempts" figure. It has no repo access; those specifics are inferred, not
inspected. Treated as UNVERIFIED and checked against code. Its central arithmetic turned out
CORRECT (verified below); the "40 to 6" is its own fabrication and is NOT adopted.

**#1 (the important one, VERIFIED TRUE against code).** Sentence: *"...the spiking pacemaker and
a one-sided CUSUM baseline were identical ... CUSUM is the sufficient statistic ... the pipeline
turned that prediction into a measured fact..."* ChatGPT: the two detectors are the same
threshold by construction, so identical results are an artifact, not proof of sufficiency.
VERIFIED in covenant_witness.py:
  - Pacemaker.silent: since_last/(6*gap) >= 1  <=>  since_last >= 6*gap     (lines 73-82)
  - Cusum.alarm:      max(0, since_last - 2*gap) >= 4*gap  <=>  since_last >= 6*gap  (lines 93-100)
  Both fire at exactly 6 median gaps. Identical detections and the same 9 false alarms are
  GUARANTEED, not measured evidence. "CUSUM is the sufficient statistic" / "measured fact" is an
  overclaim. The 11/11 redundancy agreement is trivially expected (same threshold).

**#2.** "We set the keep-bar before writing the detector" — the bar actually evolved across
Amendments 1-3 (our own record confirms). Honest: criteria strengthened through successive
reviews, then applied. The 2-day withhold does not prove earlier spans incident-free.

**#3.** A missing phone check-in is not proof of an outage; the 9-FA count depends on our
labelling. Hedge "known outages"/"false alarms" to "known check-in interruptions"/"intervals
outside known incident windows."

**#4.** Co-occurrence != causality; "one common cause" overstates. Soften to "plausible
confounder."

**#5.** The gate "compute cut" — honest form: we have not isolated how much of the saving needs a
spiking neuron vs ordinary conditional execution. (ChatGPT's "40->6" number is fabricated.)

**#6.** 78% is MODELED ops, ~1% CPU wall time; no physical-neuromorphic energy demonstrated.
(Already hedged in draft; make it explicit the 78% is modeled, not measured on hardware.)

**#7.** Redundancy layer: the 11/11 agreement is expected (same thresholds); and "a disagreement
would show which detector had gone blind" OVERCLAIMS — a disagreement shows a conflict, not which
reading is right.

**#8.** "sufficient" is stronger than a two-incident evaluation supports; neuromorphic hw is not
the only legitimate benefit (an event-driven gate can cut work on conventional hw too). Also
"Neither built" vs an earlier LeakyBurst shadow already in the repo — reword to "neither advanced
to a deployed detector" (coincidence + flaky were the two declined; LeakyBurst/strike twin was
built-then-retired separately).

**Placement:** ChatGPT says NEW TOPIC ("a distinct empirical case study about detector
equivalence and negative-result reporting"), link back to six-checks in the opener.
  -> SPLIT with Tetsu, who said REPLY/append to six-checks.

**ChatGPT's closing:** the most significant result is that the project has a stated criterion for
rejecting its own work and used it. But a skeptical reader will find the equivalent thresholds; if
the post presents their agreement as a meaningful comparison between distinct methods, it
reproduces the exact failure the six-checks thread criticised. Correct before publishing.

## Seat 0 — Tetsu (local 3B, fresh). KEEP mostly; one catch + placement.
- Overclaim: "a neuron that stays silent does no work" -> hardware property (fixed in v2).
- Placement: REPLY, append to six-checks thread.

## VERDICT SO FAR
The equivalence-by-construction catch (#1/#7) is real and verified. It does not kill the post --
it IMPROVES it: our own redundancy comparison was a check that could not fail (two detectors set
to the same 6-gap threshold), which is literally another "green that meant nothing," now about our
own SNN work. Rewriting the draft around the honest version, then re-consulting the corrected
draft with 1-2 fresh seats. NOT posting until the operator's explicit yes.

## Seat 2 — DeepSeek (DeepThink, reasoned 22s), via operator's Edge. Verdict: REVISE 3 LINES (v3 sound).
Ran on v3 (post-ChatGPT rewrite). "The draft is mostly self-correcting" — the equal-threshold catch
is handled. Three residual over-reaches, all applied to v4:
1. THROUGH-LINE "the spiking formulation has shown no advantage over the simpler detector" over-
   generalises from one threshold-equivalent twin -> scope to "the one spiking twin we built... not
   evidence about spiking detectors in general."
2. "a plausible common confounder a spiking detector would only restate" is predictive (we didn't
   build it) -> "would likely restate — a reason not to advance it, not a measured result."
3. "it becomes meaningful only with genuinely independent sensing" — "only"/"meaningful" overreach;
   independence is necessary, not sufficient -> softened.
Placement: REPLY — "it is explicitly the seventh in the six-checks series and its lesson depends on
that thread's context; a new topic would fragment the series."

## Seat (attempted) — Gemini (Flash): STALLED >60s, no answer returned. Not counted.

## PANEL RESULT (3 seats: Tetsu local + ChatGPT + DeepSeek)
- Material finding: the pacemaker twin and its CUSUM baseline are the SAME threshold (6 median
  gaps), VERIFIED in covenant_witness.py. The v1/v2 "CUSUM is the sufficient statistic / measured
  fact" framing was an overclaim; retracted and rewritten (draft changelog carries the wording).
- Draft now v4; all named overclaims fixed.
- Placement: 2 REPLY (Tetsu, DeepSeek) vs 1 NEW TOPIC (ChatGPT) -> lean REPLY to six-checks (180769).
- NOT posted. Awaiting operator's explicit yes (a send is an act; immunity never covers it).

## GATE VERDICT (covenant_moltbook.judge_outbound, real build_semantic_quorum) — 2026-10-28
Run on HF_SPIKING_POST_180769_FINAL.md. clean=False, ran=True, held=False.
  quorum=violates
  local:0: VIOLATES -- both seats (R1): ora=hold sena=violates -> violates; the junior seat
    convicted; a conviction from either seat blocks.
  semantic:1: UNSURE -- semantic[41bba7d7d753] ABSTAIN -- it blocks rather than approves, and it
    is NOT alleging a violation. lexicon score 194.
NOTE: first attempt under `python -I` returned "quorum unavailable (cryptography)" -- a degraded
fail-closed, NOT a verdict; -I hid the user-site cryptography. Re-run under normal python gave the
real quorum above.
READING: the documented A67 false-positive, same as the six-checks post (GREEN_THAT_MEANT_NOTHING_
FINAL): the topic-reading local/student seats convict an honest report ABOUT OUR OWN FAILURE while
the semantic seat (appropriation/concealment) does NOT allege a violation (abstains). Text NOT
reworded to pass (A67 lesson; the post is partly about the gate being wrong). Operator gave explicit
"reply to 180769, go ahead" on 2026-10-28; a forum send is an act, his decision alone (immunity
never covers it). Posting on his instruction, verdict recorded here verbatim.

## POSTED 2026-10-28 (operator's explicit "reply to 180769, go ahead")
Reply posted to HF thread 180769 as Lawless1987, through the operator's Edge. Now post 2/2:
  https://discuss.huggingface.co/t/.../180769/2
Verified on the rendered page: body, the repo onebox (LAWLESS1987/covenant), and the two-author
disclosure (naming the separate reviewer model + his grant) all present. Gate had REFUSED (A67
pattern, recorded above); not reworded to pass; posted on his instruction (a forum send is an act,
his decision alone). Final text: ops/HF_SPIKING_POST_180769_FINAL.md.
