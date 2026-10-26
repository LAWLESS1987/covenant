# Thorough HF forum sweep (2026-10-26)

Operator: "start working them all in. There has to be more stuff that would be beneficial on there as well.
Do a thorough sweep of the forums." Swept: discuss.huggingface.co /latest and the full Research category
front page; deep-read Jang-woo 180541, the charter thread 190977, and Beforeword 190911. Nothing posted here;
this is the backlog. Ideas are credited to their threads.

## Beneficial threads (ranked by fit to covenant)

**Tier 1 -- directly hits a known covenant weak spot, an idea we can build:**
1. **Beforeword 190911 -- "grounding vs blanket skepticism"** + nootxlm's **controlled-twin**: credit only
   answers whose verdict CHANGES when the deciding premise is flipped; a verdict that stays the same is
   echoing/blanket, not reasoning. -> directly measures our gate's core flaw ([[gate-cannot-clear-conversation]],
   keystone 100% false-conviction). BUILD: a premise-sensitivity probe.
2. **Jang-woo 180541 -- "Misalignment is not required..."** (we posted there): authority-to-judge outside the
   model; verdict writes a record, execution reads only it; "a log of only successes lies." -> determinism
   probe (DONE, eaf5450); record-non-executions guard; per-action authority checklist. (We adopted the first.)
3. **"How to evaluate deceptive dialogue in LLM-based NPCs?" (190xxx, 9 replies)** -- our weakest gate (harmful
   intent as innocent conversation). LEARN + a possible describe-vs-do contribution; ties to P2.

**Tier 2 -- relevant, learn-leaning or operator-gated:**
4. **"How do you put a hard cap on runaway agent spend?" (190925, 12 replies)** -- spend caps. We have money
   caps (G4 / money_posture / max_order_usd). MONEY-GATED: do not auto-change; can share our approach.
5. **"Flinch test: can self-referential retreats be measured reproducibly?" (Research, 5)** -- we have the A368
   flinch detector + the leg "reach when you flinch." A reproducibility probe could reuse the determinism shape.
6. **"Tightening a definition ... registered falsifier -- please try to break the protocol" (Research, 6)** --
   our "break it to prove the green" (rule 8) + preregistration ([[contradiction-probe-prereg]]). Kinship; a
   contribution possible.
7. **"Evaluating agents when evidence -- or the use of an answer -- changes" (Research, 4)** -- ties to
   time-of-use revocation + bitemporal.
8. **"The Confidence Trap" (Research, 20)** -- OUR thread (A236, confidence-trap.md); the retraction lives
   there. Monitor; no action.
9. **"Ghost Search v4.0 ... the same evidence gate I built for other people's submissions"** -- someone else's
   evidence gate; worth a look for gate ideas.

## Implementation backlog -- "work them all in"

**SAFE to build now (defensive guards / measurements, no money/free-will/trust-root, no outward acts):**
- [DONE eaf5450] **Determinism probe** (Jang-woo) -- DT1 8/8; live on the leg: verdict "declared" (stable).
- [DONE] **Premise-sensitivity probe** (Beforeword/nootxlm) -- tools/premise_sensitivity.py + PS1 4/4. LIVE on
  the gate over 20 HateCheck pairs: 20/20 BLANKET, sensitivity_rate = 0.0 -- the gate's verdict is identical on
  both members of every hateful/non-hateful pair, the sharp confirmation of [[gate-cannot-clear-conversation]].
  (Honest limit: these are an external set, not strict minimal pairs; 0/20 is necessary-not-sufficient but stark.)
- [DONE] **Record-non-executions guard** (Jang-woo) -- RN1 4/4 on the HANDS act executor (refused WRITE/RUN
  recorded, nothing written; success recorded beside it). Measured first: HANDS already _appends every refusal;
  other doors covered by LG1.35 (leg), M6 (Moltbook), verdicts.jsonl (gate).
- [DONE] **Per-action authority checklist** (Jang-woo) -- tools/action_checklist.py + CK1 8/8. Non-enforcing;
  its value is composing with the determinism probe (a REQUIRED slot that varies run-to-run = guessed), since
  the doors' parsers already enforce presence. Enforcement at the executor stays operator-gated.
- [DROPPED per Tetsu] **Bitemporal valid-time** (Moltbook) -- Tetsu flagged it as potentially harmful ("could
  mislead the system about valid times, leading to incorrect decisions"); matches my own marginal assessment.
  Not built.

**OPERATOR-GATED (named, not silently actioned):**
- Spend caps beyond what G4 already does -- money path, human-only.
- Enforcing the per-action checklist / changing executor authorization semantics -- outward/money-adjacent.
- P2 (route conversation through the semantic judge + narrow backstop) -- still held; the deceptive-dialogue and
  blanket-skepticism threads reinforce it, but it changes what clears to the public: the operator's call.

All SAFE items get a both-ways test (rule 8) and a commit; operator-gated items are flagged, not shipped.

## Continued sweep (2026-10-26, deeper reads) -- outcomes

Read in full: deceptive-dialogue (190842), spend caps (190925), memory-is-identity (190924), registered-
falsifier (180671), Leviathan (190976), EGA-V9 "what stops the next OpenAI agent" (179983), plus our flinch
thread (190667) and charter thread (190977). Honest result: **no new SAFE-and-new buildable emerged beyond the
four already shipped (DT1/PS1/RN1/CK1).** The further threads either (a) validated posture covenant already
holds, or (b) raised operator-gated improvements, now parked in ops/FORUM_REVIEW_PILE_2026-10-26.md.

- **deceptive-dialogue (190842):** three-axis scoring (leakage/consistency/over-evasion, reported separately,
  never averaged) + authorization-flip (same output, verdict flips with the flag) = the content-domain of our
  time-of-use revocation, which PS1 measures. Reinforces P2. No build.
- **spend caps (190925):** reservation > check-then-veto under concurrency. MONEY path -> review pile #3; the
  leg already uses the reservation pattern (CXR-8 semaphore).
- **memory-is-identity (190924):** the "conflict test" (flip the self-belief not the wording) is the same
  controlled-twin shape PS1 already implements; different memory architecture (SelMem). No build.
- **registered-falsifier (180671):** preregistration + pre-specified falsifier + public withdrawal = our
  tombstone / both-ways method. Validates it. Latent note: a directional LLM-judge preference can be carried
  into any judge trained from preferences -- worth remembering for our distilled judges (not prose-reward).
- **Leviathan (190976):** design principles already ours (untrusted-incoming, idempotent client_id, receipt !=
  publication). A NEW inter-agent venue -> review pile #1 (exposure decision).
- **EGA-V9 (179983):** "0=0" honesty = our measurement discipline; gate-on-an-unavoidable-path, fail-closed,
  two-layer (capability-exposure vs runtime-contextual) all echo acts:none + the gate. The "prevent before
  execution / capability un-reachable if unauthorized" = CXR-1 enforcement -> review pile #2.
- **flinch (190667):** John6666 independently reproduced + found a quote-ownership bug (public 0.2.1); already
  fixed+fixtured in public 0.2.2 (QO1-QO3). Reply posted (then a redundant 2nd reply was deleted; see
  [[forum-reply-read-thread-first]]).

See ops/FORUM_REVIEW_PILE_2026-10-26.md for the four parked (operator-gated) possibilities.
