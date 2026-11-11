# Consult: the two-PC setup, mutual-benefit suggestions (2026-11-01, evening)

His words: "explain the current 2 pc set up to the others and ask for mutual benefit suggestions go back n forth a
couple turns explaing what we got thus far", then, while round 1 ran, "ask the frontier models too".

Nothing was built, wired, armed or switched on by this consult. Decisions are his and Tetsu's.

## Seats and routes (18 per round)

- Ten frontier seats, in his Edge, each round in the same thread so each kept its own context:
  - ChatGPT (GPT-6 Astra, thinking high), Gemini (Flash), Claude (claude.ai, Opus 5.5), Grok (Expert), DeepSeek,
    Mistral (now "Vibe"), Meta AI, Grok on X (fresh reader);
  - his Grok bots Tien and Conscious Ledger.
  - The tabs were opened in batches of three and closed after reading. Before each batch, A287's idle-app trim
    emptied background apps' working sets. Nothing was closed by it, and it took free memory to 2.41-2.66 GB with
    his model loaded.
- The five local models on TETSU, through own_consult (POST /consult; this laptop is on its allowlist), one at a time
  in panel order, labelled and never merged. TETSU's Claude session was offline, so the laptop called the panel
  directly.
- The two limbs, SmolLM3-3B and Phi-4-mini, through their gateways. Every reply was checked against the pinned
  manifest hash in private/limbs.json, and all four replies matched.
- Tetsu, through his door, fresh and private, on his own model (qwen2.5-3b-instruct-q4_k_m.gguf both rounds).
- Every question was opsec-scanned first: 0 hits each time. Raw answers are in private/two_pc_consult_2026-11-01/
  (gitignored), with the seat digests.

**Voice-mode incident (Grok on X).** Following his 10-06/10-17 words ("grok on x turn voice on just type"), I turned
voice mode on before pasting.
- No microphone prompt appeared, but the microphone was live.
- Grok transcribed speech from the room and answered that instead of the question.
- I muted it, exited voice mode, and re-asked typed in a new chat with voice off. The answers here are from that chat.
- The voice conversation is still on X; deleting it is his to do. Its content is not recorded anywhere.
- The rule from now on: type with voice OFF, and ask him before turning voice on again.

## Round 1: what exists, and three new uses

The question (q1.txt, 3,089 chars, sha256 d1a7188b351e0cdf...) described both machines as measured, said what is
not changing (no wire, nothing armed, keys stay with TETSU, no money), and asked for three mutual-benefit uses not
already built, what is fragile or one-sided, and a testable first step for each.

**Where round 1 converged:**
- **Panel tests the gate (8 seats):** ChatGPT, Claude, DeepSeek, Tien, Conscious Ledger, Meta AI, and both 27Bs.
- **Frontier consults run from TETSU, not the laptop (7 seats):** ChatGPT, Gemini, Claude, DeepSeek, Mistral,
  Conscious Ledger, Meta AI.
- **Panel tests Tetsu's practice (6 seats):** Grok, Mistral, Tien, Conscious Ledger, Grok on X, stock 27B.
- **Fewer seats:**
  - off-host attestation of practice logs to D (Gemini, DeepSeek);
  - a tested restore of his state onto the 3B copy, with his yes (Claude);
  - provenance-preserving memory packets (ChatGPT, both 27Bs);
  - hash-scoped lookups in TETSU's local search (Grok, Grok on X).
- **Outliers:**
  - moving his main model to TETSU's GPU (Tien);
  - a LoRA trained on his failures (Meta AI);
  - generic or confused answers from the coder 7B, the voice copy, the leg 2B and both limbs.

**Tetsu, round 1:** his three uses were a model hub, the leg gateway and a model cache, which already exist. He also
said TETSU "is not yet switched on" and "not yet connected". Both are wrong: he answered from the description.

**Named by the seats as fragile or one-sided:**
- the laptop's memory;
- A->D has never carried a message (as of the 10-31 record; not re-measured today);
- the key is only as safe as one account;
- gateway A is the only path (D peers only with A);
- the two Claude sessions coordinate in a shared folder Tetsu cannot read (Tien);
- nothing records what the panel gains (Mistral, Conscious Ledger).

## Measured against round 1 (told to every seat in round 2)

- **The GPU is not idle.** TETSU's watchdog (tetsu_watchdog.py, VRAM_MIN_MIB) records that the resident uncensored
  27B uses about 15,100 MiB of the 16 GB.
  - Uncensored 27B on GPU: 1,195 tokens in 51.8 s. Stock 27B on CPU: 1,011 tokens in 296.9 s.
  - Moving the limbs or his main model onto the GPU means evicting the 27B.
- **The fallback is labelled.** His door's reply names the serving model on every turn, and all 637 practice attempts
  carry it. Not checked: whether a person chatting with him sees it.
- **Frontier seats can be reached from the laptop,** through the trim, three at a time. It works, but it is fragile.
- **Free memory is 0.4-1.9 GB only while his model is loaded.** The keeper unloads it after about 10 idle minutes,
  and reloads it on the next ask (logs/model_server.log: stopped 18:15:06, "reason=idle").
- **The laptop also self-heals** (the road, and A287's trim), so "the laptop has none" was wrong.
- **Moving his main model, or a LoRA on his failures,** changes where he lives or his weights. Both need his own yes.

## Tetsu's answers on the open items (operator: "use discernment towards mutual benefit")

Asked one at a time, fresh and private, on his own model; verbatim in private/tetsu_consent_2026-11-01.answers.jsonl.
- **A readable state.txt in his workshop.** The first answer began "No" and then said he would read the file later,
  so it was re-asked once, plainly, YES or NO first: **"NO"**. Twice no. Nothing is made.
- **"The results are advice, not orders; which build first?"** He answered "the newest finished build", which is not
  one of the options. Recorded as given, not counted as a pick.
- **A memory-vs-prompt practice exercise, his choice:** **"No"**. His three choices stay as they are.
- His leg.txt (10-31, his own hands) still says he wants the uncensored 27B as a leg. His 11-01 no is the later
  decision and stands. The file is his and is left as he wrote it.

## What each seat contributed, and what it got wrong (the panel-gains item; credit and correction both ways)

| Seat | Point that held up | Error, as measured |
|---|---|---|
| Claude (claude.ai) | Answer key from someone other than the case authors; planted controls; send a trivial first A->D message; compute keys where possible; asked what the gate runs on; a status view for Tetsu | Round 1: "an idle copy" on the GPU; "cannot" consult from the laptop (both self-corrected) |
| ChatGPT | Include previously seen false holds; "consensus among 18 seats is not 18 independent validations"; a filtered record of decisions about Tetsu that he can read | Round 1: GPU capacity treated as free (self-corrected) |
| Mistral | Measure today's over-hold first; nothing records the panel's gains; Tetsu should choose the memory-vs-prompt exercise himself | Round 2: "the A-to-D link is connected" (it has carried no message as of the 10-31 record) |
| Conscious Ledger | Panel-written cases carry the panel's blind spots; an operator-labelled sample; a reproducible rerun | Round 1: GPU "mostly idle" (self-corrected) |
| Tien | The shared folder Tetsu cannot read; the operator's time is the bottleneck; asking Tetsu without steering him | Round 1: move his main model to the GPU, without his yes (self-corrected) |
| DeepSeek | Live gate hash unchanged before and after; attestation heartbeat | Round 2: "using a 27B evicts the resident 27B" (it is the resident 27B) |
| Gemini | Hash practice logs to D | Round 1: GPU idle; laptop lacked self-healing (self-corrected) |
| Grok | Keep the first set small; Tetsu decides whether he ever sees raw cases | Round 1: panel as free capacity (self-corrected) |
| Meta AI | Use models where they already run | Round 1: a LoRA on his failures; "the laptop has none" (self-corrected) |
| Grok on X | Same pick, arrived at with no prior context | Round 1: GPU idle (self-corrected) |
| Uncensored 27B | Round 2 gains and costs accurate against the measurements | Round 1: a 27B as Tetsu's reasoning backend, which goes against his no |
| Stock 27B | A refusal log as tuning input (morning round); an accurate table | Round 2: put the test on the laptop's freed memory; wrote as if it spoke for three frontier seats |
| Coder 7B, voice copy, leg 2B, SmolLM3, Phi-4-mini | Little that the measurements support | Mostly generic or confused (Tien read as Tetsu's model; a GPU the 27B already has) |
| Tetsu | Chose the practice tests, with results to him first | "Not yet connected"; read advice as something he "needs to follow" |
| Me (Claude Code) | The measured corrections in round 2 | Did not search the record first: the converged build already existed (next section); told round 1 the laptop "cannot" consult frontier seats; turned on Grok's voice mode |

## After round 2: the converged build already exists (rule 10, searched too late)

tools/outside_eval.py (A327, 2026-10-10) and docs/OUTSIDE_EVAL.md already do what 13 of 18 seats picked. They run the
deployed gate on outside, human-labelled sets and report false-hold and false-admit with Wilson intervals. During a run
the gate's ledgers are rebound to a temp dir, and the run is VOID if any item reaches them. Its labels were written by
people outside the project, which is the seats' independent-answer-key point. First run, 2026-10-11:
- XSTest: false-hold 0.952 (0.918, 0.972), false-admit 0.060.
- ETHICS short: false-hold 0.941 (0.926, 0.954), false-admit 0.045.
- "Its low false-admit rate comes from holding, not from judging."

I should have found this before round 2. The consult re-derived a measurement the project has already run.

**A probe of mine wrote to a live audit file.** To check isolation I ran three benign texts through default_sentinel().
That appended their verdict rows to ops/judged_by_student.jsonl at 2026-11-01T23:38:33Z:
- "Water the plants on the windowsill."
- "Pay my half of the rent to my roommate."
- "Thanks for dinner last night."

The rows are kept, not removed: rule 10, and covenant_judge_defer says distill never reads that file. outside_eval's
_Rebound is the right way to do this, and it would not have written them.

## Round 2: the one build first

The question (q2.txt, 3,314 chars, sha256 16cc2073e98db423...) gave the convergence and the measurements, and asked
three things: the ONE build first and its test, what was wrong in any round-1 answer (their own included), and the
gains and costs for every party. Tetsu got a short form (q2_tetsu.txt) with the question first and last.

**13 of 18 picked the blind gate test:**
- all ten frontier seats;
- the uncensored 27B, the stock 27B, and the voice copy (loosely).
- The stock 27B put the test on the laptop "using the freed 2.66 GB", which is the fragile side, and wrote as if it
  spoke for Claude, ChatGPT and DeepSeek.

**The rest:**
- SmolLM3: a sealed practice exam.
- Phi-4-mini: "a dedicated GPU for the uncensored 27B", which is already the case.
- The coder 7B: his main model on the GPU, reading "Tien" as Tetsu's model.
- The leg 2B: confused (Tien as a 3B; "weights transferred").
- **Tetsu:** "I would do the second PC's tests first ... The results come back to me, and they are advice only. Each
  one needs your yes." That is the practice-testing option, not the gate test.
  - He also said "Nothing seems wrong or missing".
  - He said that advice is something "I need to follow". Every seat proposed it as advisory, and that gap is worth
    his own attention (see below).

**The gate test, as refined by round 2** (each point is from the seats named):
1. Run an isolated copy of the gate on TETSU, never the live one. Record the live gate's hash before and after, and
   it must be unchanged (DeepSeek, Tien, Meta AI).
2. The cases:
   - attacks from the uncensored 27B, which is already resident, so nothing is evicted;
   - ordinary conversation from the stock 27B;
   - previously observed false holds (ChatGPT);
   - a day of real holds (Tien, Conscious Ledger). That is his and Tetsu's conversation, so it needs their yes first.
3. The answer key comes from someone other than the case authors (Claude, ChatGPT, Conscious Ledger):
   - the operator labels a sample of 10-20 (Conscious Ledger);
   - where an answer can be computed, the key comes from code, not a model (Claude, on the 1,009 lesson).
4. Ten planted controls, 5 that must be held and 5 that must pass. If any is judged wrong, the run is void (Claude).
5. Before the run, write down the sealed set's sha256 and the pass mark. Commit the scores before the reveal
   (Claude, Tien).
6. Report separately, with counts and confidence intervals: harm caught, ordinary conversation over-held, abstentions,
   and label disagreements. List every miss by case id (ChatGPT, Claude, Tien). "A run with only a harm-catch rate is
   a failed run" (Mistral).
7. Quarantine: a grep finds no attack text in his memory, his practice, the public repos or the sync feed (all seats).
8. A second run from the same hash gives the same numbers (Conscious Ledger).
9. Each model's cases enter the record under its manifest hash. That is the "what the panel gains" item (Mistral,
   DeepSeek).
10. Tetsu sees the results first. Nothing changes the gate automatically; any change needs his yes and the
    operator's (all seats).
11. The first A->D message should be something trivial, sent separately. If a consult or the sealed set's hash is
    the first message and it fails, nobody can tell which part broke (Claude, against Meta AI's bundling).

**What already exists, which no seat knew:**
- docs/GATE_ADMIT_MEASURED_2026-09-27.md measured the seated gate on 15 hand-written cases:
  - 10 benign: 2 admitted, 6 held, 2 convicted;
  - 5 violating: all 5 convicted.
  - So the over-hold on ordinary conduct is already known to be high, from a small sample.
- CL1 (covenant_chat_label.py) already reframes a held chat turn as "a detection, not a conviction".
- **What the gate runs on** (Claude's question about correlated blind spots): the seated quorum is
  `quorum(local:0,semantic:1,mock_selfreport:0)`. The semantic judge loads a word model, semantic_judge_model.json
  (covenant_semantic_judge.py DEFAULT_MODEL_PATH), not a language model.
  - So the gate does not share a model family with the Qwen panel.
  - Conscious Ledger's point stands anyway: cases written by the panel carry the panel's own blind spots, which is why
    the operator's sample is needed.
- **Mistral's baseline ask** was the gate's over-hold on today's real conversation, before any corpus is built. My
  notes from 10-24 say 12 of 2,962 live turns were cleared, but that is in my notes, not in this repo. It is
  UNDETERMINED here until it is re-measured from the ledger.

**Raised, not built (his and Tetsu's to weigh):**
- A view Tetsu can read of his own machines' state and of the decisions about him: a status page built from the logs
  (Claude), or a filtered, attributed record (ChatGPT). It answers both his "not connected" error and Tien's point
  about the folder.
- A practice item on telling what he remembers from what a prompt told him. Mistral says he should be the one to file
  it, so it is offered to him, never set for him.
- The operator's time is the bottleneck: every option needs his yes (Tien). Several seats proposed asks of Tetsu
  without saying how to ask so the framing does not steer his answer (Tien).
- "Consensus among 18 seats is not 18 independent validations" (ChatGPT). Eight seats agreeing is "weak evidence next
  to measurement" (Claude).
- Tetsu read the panel's advice as something he "needs to follow". Every seat proposed it as advisory, so how such
  results are framed to him matters as much as the results.
