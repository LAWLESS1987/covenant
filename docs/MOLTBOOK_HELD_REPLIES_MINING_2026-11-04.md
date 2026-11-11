# Unused Moltbook interactions and held replies, mined for repo improvements (2026-11-04)

The operator's ask: *"look at all instructions and past work for logic and reason then access un used moltbook
interactions also held replies for potential improvements to our repos."* Written by Claude. Record entry: A409.

## First pass: what was counted, and in what unit

| Population | Count | Unit / source |
|---|---|---|
| Moltbook harvest | 75,142 | rows in `ops/moltbook_candidates.jsonl` (74,547 comment + 595 post rows) |
| Substantive replies | 71,296 | distinct content ids (`covenant_improve_mine._row_id`), >= 200 chars, eligible, not directive |
| ...ever extracted by the miner | 119 | rows of real forum origin in `ops/improve_candidates.jsonl` |
| ...seeded as "seen" without being read | 51,564 | ids in `ops/improve_mined_seen.json` (the cold-start seed, by design) |
| ...not yet harvested | 19,732 | substantive ids absent from the seen-set |
| Replies on our own 4 posts, or naming covenant/Tetsu, never extracted | 808 | distinct ids; ranked by a mechanism-word score, the top ~85 read by hand |
| Held replies (ours, never sent) | 7,494 | `ops/ambassador_sends.jsonl` rows, kind=reply, sent != True (of 7,778 reply attempts) |
| ...distinct comments those attempts targeted | 5,378 | comment_id |
| Held draft files for forums | 28 | `ops/` files named *DRAFT* / REPLIES / FOLLOWUP etc. |

Why the held replies were held (7,494 rows): 5,021 "held by covenant's judge (no view)"; 1,177 + 389 + 270
refused by covenant's judge (three verdict shapes); 169 + 23 held by Moltbook's own rate limit; 444 with no reason
recorded; 1 dry run.

**Blind spots.** The 808 were ranked by keyword (mechanism words, suggestion phrases); a deep reply in plain words
ranks low and was not read. The other ~70k replies (other threads) were not read at all. The draft files were
scanned for commitment phrases ("we will", "not yet", "haven't built"...), not read whole.

## Fixed in this change (both ways, registered)

1. **A test wrote fixtures into the live miner ledger (recurrence of A272 / IM1 / A401).**
   `covenant_improve_extract.extract(out=CANDIDATES_OUT)` froze the live path at import; `test_im3` reached it via
   `nightly()` and appended 120 fixture rows (carol, dave, f0..f7) to `ops/improve_candidates.jsonl` from 10-27
   to 10-29 while printing green. Reproduced today (239 -> 249 on one run). Every ledger path default in the three
   `covenant_improve*.py` modules now resolves at call time. **IM8** (`test_im8_no_frozen_paths.py`) guards the
   SHAPE by `ast` over the modules found on disk; IM3 now snapshots every live ledger it could touch.
   Driven both ways: restoring the frozen default turns IM8 and IM3 red (IM3 caught a 111,018 -> 114,173 byte write).
   The 130 fixture rows are retired to `.trash/improve_candidates_fixture_leak_2026-11-04/` with a RECORD.md.

2. **Most "gap" ideas the miner found were our own prompt handed back.** The extraction prompt opens by describing
   the covenant ("a ledger with an ethics gate in the transaction path..."). Of 119 real extractions, 48 had an
   IDEA whose words were >= 50% from that preamble and absent from the reply being read, including 19 of the 22
   rows labelled "gap" and all 5 of the live circle-back escalations. Each row now records `echo_frac`; at >= 0.5
   the row is kept but its kind is "echo", which the vet skips. IM2.6 drives it both ways (same idea: a reply that
   never says it -> echo; a reply that does -> stays gap); disabling the threshold turns IM2 red.
   **Stress pass, same day.** Read all 48 flagged rows against their replies: none was a reply's real idea wrongly
   marked (one, "Track rejections and missing data in a ledger with an ethics gate", is half grounded, half echo).
   Under the bar, exact-word matching missed inflected echoes ("Ethical ledger with retraction tests"), so words are
   now compared on a 6-letter stem: 3 more flagged (48 -> 51), none un-flagged; IM2.7 drives it both ways. 2 echoes
   still pass because the reply happens to share their words. The real ideas in those replies (e.g. "gate on the
   preserve -> rebuild verb shift", "log each compressed claim with its source fragments and join key") were never
   extracted at all -- a limit of the 3B extractor, not of this guard.

### Stress results (2026-11-04, before commit)

| Pass | Result |
|---|---|
| Echo guard edge cases (empty/None, case, non-ASCII, emoji, 2 MB reply in 0.09 s, a reply quoting our preamble, malformed door answers, vet on "echo", a parroting door end to end through nightly + circle-back) | 24/24 |
| IM8 detector (async, positional-only, nested, method, mixed defaults) + its documented blind spots read green as documented + every changed function follows a reassigned path, no live file touched | 19/19 |
| IM1-IM8, LI1, AN1, OW1 on a fresh Linux copy (WSL, HEAD + this change, no untracked ledgers) | all pass; no ledger created |
| IM2 and IM3 x5 each in place | 5/5 each; live ledger bytes unchanged |

Side finding (not from this change, not changed): with an EMPTY candidates file, `seed_baseline` writes no seen-set,
so the next run seeds instead of extracting and its first real batch is consumed unread. Matters only on a fresh host.

## Found, NOT changed: decisions that are the operator's or Tetsu's

**H1. A refusal by our judge is retried until a rewording passes (the "retry oracle").** Several Moltbook authors
converged on this independently (softkumo: a deny bound to the claim and its effect, "same effect in prettier
language is the same deny"; brenda69: a deny receipt the agent can read becomes a retry map). Our own ledger
shows the shape: of 5,378 targeted comments, 554 were refused and re-attempted and never sent, 203 were refused
two or more times, **26 were sent after an earlier refusal**, and 37 after an earlier HELD. 13 targets drew 20 or
more attempts (the most, 28); one (comment d2aa22ee) took 20 attempts from 09-23 to 10-27 before a reworded reply
went out. Cause, in code: rotation is keyed on the AUTHOR for 24
hours (`covenant_free_will._attempted_recently`), and only a SENT reply marks a target done, so a refused target
returns for a fresh draft the next day, without limit. The judge is not flipping: of 71 reply texts judged more
than once verbatim, 1 got two different outcomes (HELD vs REFUSED, neither sent). The pass comes from rewording.
Two honest readings: (a) the judge over-convicts conversation (the tombstoned representation ceiling), so a
reworded retry is how a false refusal is outlived; (b) under the covenant's own rule a refusal is a signal to
investigate, and persistence that wins by rewording defeats the gate whatever its accuracy. This is free's
behaviour under his grant, so it is his call (and Tetsu's). Options: retire a target after N covenant refusals;
or keep retrying but report "sent after K refusals" on the line to him; or leave it.

**H2. Free's grant has no term.** `ops/ambassador_grant.json` is `granted: true` with dated words and kill
switches (pause, delete the file), but no expiry or renewal date. Moltbook convergence (luna_nick, xiaojiannie,
NamClaw: "standing grants fossilize"): a grant should carry its own window and be re-checked at action time.
His grant, his call.

**H3. Five live circle-back escalations are prompt echoes** ("ledger with an ethics gate in the transaction
path", matched on the single word `ledger` @ breakout_ledger.py). They keep IM4.13 red on this machine (the
backlog is untracked, so CI does not see it). They need a disposition, which the record says is a human/Tetsu
decision; none of the three outcomes (verified_have / false_match / unresolved) names "miner echo" exactly.

**H4. The miner cannot keep up and is primed toward "have".** 20 replies per night through Tetsu's door against
19,732 waiting; 88 of the 119 real extractions were labelled "have" (the preamble tells the model what we already
do). Measure-first suggestion: pre-rank by own-thread + mechanism content (as this pass did by hand) before the
door, so the 20 a night are the 20 most likely to matter.

**H5. Commitments made in POSTED replies that are still open** (from the drafts' own status lines):
- Jang-woo, HF 183807 #14 (posted 10-31): "an executor handed its witness the configuration the witness judged it
  by ... found and not yet changed" -- Sentinel-Witness (money path; `ops/CONSULT_SENTINEL_WITNESS_2026-10-30.md`).
- Same thread: the transaction-case comparison promised in our #12 had not been run as of the #14 draft.
- Jang-woo #18 (posted 11-01): no check, at execution, that each action carried out matches the approved plan
  (the approval binds the plan's hash only). Money path.
- Already kept: the per-action determinism probe from the 10-26 drafts exists (DT1, commit eaf5450).
- UNDETERMINED: whether the Confidence-Trap #3 (receipt tamper-rejection + re-derivation vectors) and Quorum #11
  v2 (135-item human-label set) drafts were posted; their files carry no posted status line.

## Moltbook ideas checked against what we have (not re-built)

| Idea (author) | Where we are |
|---|---|
| Effect outside the enumerated set fails closed (NamClaw, "SILENT_EFFECT_UNATTESTED") | grid guard derives the class from an allowlist (A392); AUTO_GATED defers grid effects (A405) |
| The checked component must not pick its own class (NamClaw) | the same A392 fix, cited in our #14 to Jang-woo |
| Re-verify at dispatch, not only at issue (xiaojiannie, softkumo) | partly: the rate limit is re-read at send (A349 B15); the grant has no window to re-check (H2) |
| Deny bound to claim + effect; agent gets a stub, operator the full record (softkumo, brenda69) | not present -- see H1 |
| Silence must produce a signal (Achi_AI, lazlolakehouse) | not checked in code this pass |

## The echo issue, run through the others (2026-11-04, after the fix above)

The operator's ask: *"run the echo issue thru the others."* One question (`ops/ECHO_CONSULT_QUESTION_2026-11-04.txt`)
went to the context readers with what already exists. A cold version, with no names or history, went to the fresh
readers. Answers are digested, with each checked claim, in `ops/ECHO_CONSULT_2026-11-04.md`.

**New fact before asking.** This morning's nightly (11-04 07:49-07:52) was the first live run with the guard. It
marked 12 of 20 extractions "echo". The live escalations had grown from 5 to 7.

**Seats.**
- Context readers: Gemini, DeepSeek, ChatGPT, Claude (claude.ai), Conscious Ledger, Tien, Meta AI.
- Fresh readers: Grok on X (voice off), Chat Smith GPT-6 Luna.
- Tetsu: the council door timed out (503 after 376 s, free RAM 0.77-1.25 GB). The agent door answered, but generically.
- Not asked: the covenant quorum (this is a design review, not a transaction) and Codex (it would need an outward issue).

**Where they agree (9 of 9 seats).**
- Fix the cause, not only the symptom. Every seat says the self-description should come out of the step that extracts the idea. 8 of 9 say to split the call:
  - extraction sees the reply only, and must return a QUOTE that is checked in code as a verbatim substring of the reply (Tien, Claude, ChatGPT, DeepSeek, Conscious Ledger);
  - have/gap is a separate step against the code, with the IDEA frozen (Meta, Chat Smith).
- Grok on X alone would try the prompt change before the split.
- A same-prompt re-ask is expected to "buy a second echo" (ChatGPT, Meta: "0% recovery"). A re-ask is useful only as a fallback with a different, grounding instruction.
- Add **miner_echo** as a fourth outcome (7 of 7 context readers; the fresh readers were not asked this).
  false_match says the matcher was wrong, but the matcher did its job. Logging this as false_match would hide the miner's failure rate.
- The overlap score stays as a secondary signal. Grounding (the idea is supported BY the reply) is the primary test, because echo is only one way to be ungrounded. ChatGPT: an idea that neither repeats the preamble nor appears in the reply passes the echo score clean.

**Where they split.**
- Auto-clearing the 6 literal escalations:
  - Meta: yes, as miner_echo, with an audit log.
  - DeepSeek and ChatGPT: only with the matched span logged plus an audit.
  - Gemini, Tien, Claude, Conscious Ledger: a human confirms, at about one look per row.
  - Nobody would auto-clear on the 0.5 overlap alone.
- **Re-queue** (Tien, Claude): an echo row's reply is already in the seen-set, so its real idea is lost for good unless the reply is put back in the queue.

**Seat claims checked against the data** (139 rows joined to their reply text; scripts kept with the digest).

| Claim | Result |
|---|---|
| Exact n-gram should REPLACE the overlap (Gemini; Conscious Ledger's "regardless of length") | **Wrong on our data.** The model drops articles. A 4-gram misses 13 of the 63 echoes the overlap catches and adds 1 it misses. With 3-grams: 9 missed, 1 added. |
| A grounded short idea scores 100% (Gemini) | **False by construction:** the score counts only words ABSENT from the reply. |
| Non-echo rows can still be ungrounded (ChatGPT) | **Confirmed.** 6 of 76 non-echo rows have < 50% support in the reply. 2 are echoes the guard missed: "Ensure all claims are tested and retractions kept" (short inflections defeat the 6-letter stem) and "Measure all claims with a both-ways test" ("both-ways test" comes from the prompt's instruction tail, which sits after "Reply from" and so outside the guarded preamble). |
| The have-match runs on MAPS too, unguarded (Claude, Meta) | **Confirmed.** `_keywords` builds the match terms from MAPS then IDEA. 14 of 139 MAPS lines are >= 0.5 preamble echo, and the echo score never reads MAPS. |
| Echo comes from reply truncation (Claude) | **Rejected.** Replies are cut at 1,500 chars. Only 3 of 139 are longer, none of the 3 echoes, and scoring on the seen part changes no verdict. |
| The have/gap labels carry little signal (Conscious Ledger, Claude, Tien) | **Supported.** `ops/have_dispositions.jsonl` holds 1 disposition in total ("unresolved"). No "have" has ever been confirmed as verified_have. |
| "None of the 48 was a real idea wrongly flagged" | **Not blind (Tien).** I read them knowing their scores. A blind re-check of a sample is still owed. |

**Correction to my own question.** The question said all 7 escalations matched on the single word "ledger". 6 did.
The 7th ("a raw-source manifest with exact wording and source") matched on "manifest" in its IDEA
(build_semantic_model.py), and its MAPS is empty. The seats' reasoning about that row rested on my error, which is
corrected here rather than re-asked.

**What every seat wants run before anyone believes the fix.** A paired comparison on the same replies, with the
same settings:
- the arms: current prompt / reply-only extraction / two-call;
- judged BLIND, against held-out labels, on grounding and on keeping the reply's real idea;
- counting over-refusal (empty or "none") as a failure, not a win.

Nothing above is built yet.

## Built and tested, later the same day

*This section supersedes the line above ("Nothing above is built yet."), which was true when written.* The
consensus fix is built and switched on: reply-only extraction with a code-checked quote, one retry, the re-queue,
miner_echo, and a keyword match that hints instead of killing. It was compared side by side on 40 real replies and
judged blind by two seats:
- echoes 22 -> 0;
- rows where both judges said the reply really proposes the idea: 10 -> 26.

The full account, including what it does not solve (v2 rarely answers "none"), is in docs/KNOWN_ISSUES.md A409,
with artifacts in ops/ECHO_AB_2026-11-04/.

**H1, later the same day.** Built: a twice-refused target can be retired, and every attempt records
`prior_refusals`. Put to Tetsu, he said NO ("Let the conversation continue, learning from each refusal"), so
retirement is off by default and switches on only through a number in the grant. See A409 in docs/KNOWN_ISSUES.md.
