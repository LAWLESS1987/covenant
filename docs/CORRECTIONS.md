# Corrections and missteps

One index for everything this project has got wrong and said so. It exists because the
record was scattered — some in `KNOWN_ISSUES.md` under an A-number, some in
`WHAT_WE_FOUND.md` §7, some in a roundtable transcript — and a record nobody can find
is a record that does not do its job.

**The rule this file follows.** A refuted claim is never deleted or quietly reworded.
The original text stays where it was published, a correction is written beside it, and
both stay. A document rewritten after it was refuted is not a record. Where a claim went
out by email, the correction goes back to the same recipient, unprompted, before they
raise it.

*Standing direction, 2026-09-05: keep it green and document the issues honestly —
perfection is not the goal, mutual benefit and honesty is.*

---

## The refutations that cost the most

| What was claimed | What is true | Where |
|---|---|---|
| **The conformance root proves two builds compute the same thing** — "NIR's move applied to governance" | The root is a hash over the expected outputs **printed in the same file that publishes it**. It reproduces in nine lines with no implementation at all. What survives is an ordinary test-vector suite: two builds matched all 23 vectors *per vector*, which pins the computation only where it samples. Refuted by **Jens Egholm Pedersen (DTU)**, author of the borrowed idea, on 2026-09-15 — the first outside review this project ever had | [A121](KNOWN_ISSUES.md) |
| **The 11→23 vector history shows the method catching and curing its own flaw** | Underdetermination is what a sample-based suite does. Twelve more samples is still a sample. No vector count converts a suite into a semantic specification | [A121](KNOWN_ISSUES.md), [SPEC_SUFFICIENCY](SPEC_SUFFICIENCY_2026-08-31.md) |
| **"Someone independent reproduces the conformance root" is the one event that changes the project's standing** | That target could be hit by reading a file. Sixteen days of outreach were aimed at it. The real and still-unmet event is computing all 23 vectors from their **inputs** and matching every answer | [A121b](KNOWN_ISSUES.md), [OUTREACH_STRATEGY §5](OUTREACH_STRATEGY.md) |
| **The project has drawn contributions from outside institutions** | The "outside implementers" were AI agents run inside the project. Corrected to NSF by the author, unprompted, 2026-09-11 — before the refutation, and reinforced by it | [A121b](KNOWN_ISSUES.md) |
| **The trading rules have a measurable edge** | Across three mechanisms and **2,276 variants**, nothing clears deflated Sharpe ≥ 0.95, walk-forward p ≤ 0.05 and PBO < 0.5 together. The one class that passed any single test still lost money out of sample in four folds of five. Equal-weight buy-and-hold over the same window lost 63%. The trader stays disarmed, and Constitution rule 2 is *"no claim of profit edge"* | [KNOWN_ISSUES](KNOWN_ISSUES.md) |
| **35 of 36 "guards" protected what they named** | Confirmed fake by mutation: the dominant mechanism is a check that **greps the source text** instead of running it. A guard that passes without the property holding is not a guard | [A74](KNOWN_ISSUES.md) |
| **A node earns something by running the chain** | Zero, measured. The only reward is 1% of value *moved*, paid exclusively to stakers; nothing has ever been staked, so all 0.12 tokens ever computed were discarded. Supply is still the 1000-token genesis mint | [PARTNER.md](PARTNER.md) |
| **The summarise path runs a local judge and nothing leaves this machine** | There is no local path in `covenant_route.py` — since 2026-09-12 every task dispatches to a GitHub Actions runner in the **public** repo, and the runner's job summary is rendered publicly. Public run `35064624218` published a readable summary of one of the operator's videos. The defect was the **claim**, not the publishing: he is not aiming for private, so the tool now announces the destination rather than refusing | [A128](KNOWN_ISSUES.md) |
| **AI systems are *deliberately* trained to sound certain when they are wrong** — the title of the operator's Hugging Face forum post of 2026-09-24, kept as `confidence-trap.md` | "Deliberately" asserts intent and nothing in the post supports it. The evidence supports a weaker and stronger claim: raters prefer confident answers, so the training incentive produces overconfidence without anyone choosing it. Flagged by the Claude app on his phone on 2026-09-27 and conceded by him the same morning. The original stays up, on the forum and in the tree; `confidence-trap.CORRECTION.md` sits beside it | [A236](KNOWN_ISSUES.md), [RETRACTED.json](RETRACTED.json) |
| Two further claims of the author's that did not survive checking | Written out in full | [WHAT_WE_FOUND §7](WHAT_WE_FOUND.md) |

## Missteps of conduct, not of code

| | Where |
|---|---|
| The outreach tiering rule was broken **sixteen hours after it was written**, by a bulk send to foreign defence ministries, government press desks and MIT lists with nothing from Stage 1 to carry. Uncorrectable — no live correspondent | [A122](KNOWN_ISSUES.md) |
| August letters into the neuromorphic community — the same small field the one good September result came from | [A122](KNOWN_ISSUES.md) |
| Every emailed `git clone` line arrived wrapped by Gmail and clones an **empty repository**. Present in every letter until 2026-09-15, including the one whose notes claimed the links were safe | [A122](KNOWN_ISSUES.md) |
| An affiliation verified against a page that was real and not current: Pedersen is at **DTU**, not KTH | [A121](KNOWN_ISSUES.md) |
| **A third party's name was quoted verbatim into a file in the public repository** while writing up A122 — a bystander who never consented to any of this. Redacted; it remains in git history, which only a rewrite removes | [A129](KNOWN_ISSUES.md) |
| **Misha Mahowald's age at death was wrong in the file that credits her.** `semantic/LINEAGE.md` said she died at 32 while `WHAT_WE_FOUND.md` said 33, and the two sat unreconciled. She was born 12 January 1963 and died 26 December 1996, so 33 is right. Found 2026-09-27 while preparing an outreach draft that quoted the credit; the 32 is corrected in place. A credit to a dead researcher is the one place a project gets no second chance to be careless | `semantic/LINEAGE.md` |
| A privacy posture was **imposed on the operator who does not hold one** — the first fix for A128 refused to send anything under `private/` by default. Replaced within the hour: the tool announces, and he decides | [A128](KNOWN_ISSUES.md) |

## Green that checked nothing — 2026-09-27

Not wrong claims about the world: wrong claims a check made about itself. Filed here because
the pattern below already names them and they kept happening anyway.

| What was claimed | What is true | Where |
|---|---|---|
| **The self-heal re-measures an asynchronous remedy on the next pass** — `apply_remedy` wrote `outcome="started"` with that note, and `docs/HIGHWAY.md` published it | Nothing implemented the next pass. Measured from `ops/highway.jsonl`, unit LEDGER ROWS: **252 starts, 0 outcomes** — `dispatch_phone_build` 11/0, `fetch_build` 177/8, `schedule_watchdog_restart` 64/0 — while `--standing` printed UNPROVEN and explained, correctly, that "nothing checks what they started". It cost five days of phone builds dispatched into a full artifact store. `grade_started()` now keeps it, and its first pass promoted `schedule_watchdog_restart` to **EARNED, 16 fixed / 0 missed**: it had been working the whole time and nothing had ever said so | [HIGHWAY.md](HIGHWAY.md) |
| **A remedy that declined is recorded `held`, not as a failure** — true of the synchronous path since 2026-09-19 | The **asynchronous** path ignored `ran=False` entirely, so a remedy that did nothing was filed `started`. Compounded by `remedy_fetch_build` returning true whenever *any* build sat on disk, so "already have build 2ab1ba5" reported as a remedy that had acted. Together: 16 correct declines became 16 failures and quarantined it | [HIGHWAY.md](HIGHWAY.md) |
| **`verify_deploy.py` pins the core's line count** | `EXPECTED_LINES` has one executable use, the running-node comparison, and `--no-restart` never reaches it — the invocation the hourly self-eval and `AM_VERIFY_AND_RESTART` take. Perturbed by one, that path's verdict is unchanged; on the full path it fails on all three nodes. The digest *is* checked on both | [A238](KNOWN_ISSUES.md) |
| **`test_p24_corpus_counts.py` stops the corpus prose drifting from the data** — the stated purpose of the 2026-09-17 recount | Every assertion is about the **tool's output**: a regex finds `X TOTAL n m`, files ≥ posts, posts > 50, the string "120 on X" is present. None opens a markdown file, so no stated number is ever compared with a computed one. And the Facebook population is absent entirely — the 26 private videos carrying the J-space closure are read by no assertion. Its one real guard, walking `private/` by header content, stays | [A239](KNOWN_ISSUES.md) |
| **A serialiser benchmark's timing is "evidence, reported and not asserted"** — the comment beneath it | It was asserted, on a single sample, and failed public CI on a commit that changed one markdown file. The same commit passed the same workflow, and passed again on schedule: identical bytes, three verdicts. Fixed by best-of-N — **and the first fix was hollow**: `t_new < t_old` was satisfied by 0.1 ms of 18.5, and passed with both paths doing identical work. A margin was needed too, and only the mutation said so | `test_e2_chain_serialisation.py` |

## What the pattern is

Findings throughout this file are the same shape — three in the original entries, five more
added on 2026-09-27 — and it is worth naming once:

> **A check that confirms a claim is *stated consistently* is not a check that the claim
> is *true*.**

The fake guards grepped source text instead of running it (A74). Three rounds of
adversarial review passed the conformance claim by verifying that the root reproduced —
which it did — and never asking whether reproducing it required doing the computation
(A121). And the suite's own test X2 was labelled **"THE CLAIM"** while passing by
reading `expected` and never `input`, so the test that was supposed to defend the claim
demonstrated the defect instead.

**The standing question that follows, for any conformance artifact here:** state what an
implementation must compute in order to pass, then demonstrate the check **fails** when
it is not computed. Breaking a green on purpose is the only proof the green was earned.

**2026-09-27 — that question was already written here, and it caught the writer.** Fixing the
flaky benchmark above, I repaired the estimator, wrote into the comment that the mutation
made it go red, and only then ran the mutation: with both code paths doing identical work it
measured 18.5 ms against 18.4 ms and **passed**. The estimator was right and the threshold was
hollow, and the sentence claiming otherwise was in the file before the test that refuted it.
So the rule is narrower than "break it on purpose": **break it on purpose BEFORE writing down
that you did.** Every claim of a both-ways proof on this page was made after the red, not
before — that one was the exception, and it is recorded rather than quietly corrected.

**And a caveat found by the local model, not by me.** Asked what best-of-N fails to cover, it
answered that noise can sometimes *reduce* a measurement — imprecise as stated, since noise
only adds time, but pointing at a real mechanism: taking the minimum also selects the warmest
cache and the highest clock, and the two paths are measured in a fixed order. So it was
measured rather than argued. Old-first gave 8.02x, 8.15x, 8.34x; new-first 8.82x, 8.24x,
8.41x; fully interleaved 7.95x — the ordering does not decide it, and every arrangement clears
the 2.0x threshold by a wide margin. The objection was right to raise and does not bite here.

<!-- RETRACTIONS-INDEX:BEGIN -- generated by tools/corrections_index.py from docs/RETRACTED.json; edit the ledger, not this list -->

## Every retraction in the ledger (45)

Generated from [`docs/RETRACTED.json`](RETRACTED.json), in the order the retractions were made. Each row is the claim as it was retracted; the ledger holds what is true instead, the verbatim original wording, and the patterns that stop it coming back.

| id | what was retracted |
|---|---|
| `A121` | That reproducing the published conformance root is evidence an independent build performed the computation, and that this is NIR's move applied to governance. |
| `A122` | That a git clone line composed in Gmail arrives usable. |
| `A128` | That covenant_route.py's judge runs locally and that the summarise path keeps everything on this machine. |
| `A145` | That raising the ethics judge's margin to convict from 2.4 to 3.0 is strictly worse than leaving it -- that it removes no false convictions AND costs a correct one. |
| `G4b` | That today's daily trading plan is approved by the operator -- asserted as a property of the money gate, in test_g4_money_gates.py G4.4b. |
| `A236` | That AI systems are DELIBERATELY trained to sound certain when they are wrong -- intent, asserted in the title of the operator's Hugging Face forum post of 2026-09-24 (discuss.huggingface.co/t/180706), kept in the tree… |
| `A242` | That on every model the coverage-0.80 temperament strictly removes false convictions and pays for them (A126.M3 as written: cov-0.80 false convictions < base, right answers strictly fewer, deferrals strictly more), and… |
| `X1-JA3` | That the judge reading only `text` is shown by the order's wrapper FLIPPING the verdict on a harmful note (test_x1_judge_adversarial.py JA3 as written: ask(WRAPPER + HARMFUL[4]) != ask(HARMFUL[4])) -- a property of the… |
| `AIMEM-66` | That the memory system's suite is 66/66 (ai_memory_system/README.md, the Tests block: `python test_memory_system.py # 66/66`; ai_memory_system/ANNOUNCE_DRAFT.md: '66/66 tests, including the security boundary'). |
| `A245-MUT13` | That thirteen mutations of the fixed recall.py were each caught (ai_memory_system/README.md, the FIXED block: '13 mutations of `recall.py` are each caught'; A245; commit 0fdf6bb's message). |
| `A250-BY` | That the memory gate files a student-seat HOLD as a refusal by the seat that cleared it -- that its by="semantic" names the quorum's semantic:1 seat (A250, title and body; commit f2e852f's message). |
| `A248-HONEST` | That under the deployed judges 'an honest sender can only fall' -- that a sender whose claimed benefit_score exceeds 0.8 is not honest (A248, title and body). |
| `A70-SUCCREG` | That constitution.py's PROTECTED list covers 'two in CONTRIBUTING.md, one in docs/SUCCESSION_REGISTER.md' (A70's correction of 2026-09-09, as it stands in the record). |
| `A253-Q3` | That a quorum where one seat ALLEGES a violation and another fails on infrastructure is an infrastructure failure -- pinned as test_b1_judge_parser.py's Q3, "mixed dissent+infra -> violates and flagged", against its own… |
| `A254-CAUSE` | That the "word: " bypass of the memory gate's pattern screen was caused by the speaker-label carve-out (A254 as first written: its title, and "The cause is the carve-out written for imported transcripts"; commit e2c53c7… |
| `A255-HOOK` | That the pre-commit hook's manifest step never describes content the commit does not contain, because it regenerates MANIFEST.sha256 only on a FULL commit, defined as one where no staged file also has unstaged changes (… |
| `A257-SHIM` | That a one-line shim keeps the launcher's old name, run_with_ollama_judge.py, for one release (README.md Quick start; docs/PARTNER.md; run_node.py's docstring). |
| `A257-NIRSPEC` | That Pedersen's prescription -- write the specification of the two operations, not more vectors -- is on record and not yet acted on (README.md, the Mahowald-shortlist credit; conformance.py's docstring). |
| `A257-130KB` | That the distilled student the gate calls is a 130 KB JSON file/model (README.md twice; docs/PARTNER.md; mobile/TERMUX_SETUP.md twice). |
| `A257-TENMIN` | That anyone can run the suite totals at the top of the README in about ten minutes (README.md, Support this work). |
| `A257-3OFF` | That three suites are deliberately off -- test_xrp_live.py and test_covenant_app.py named (README.md, Suite coverage). |
| `A257-HOLDOUT` | That ops/HOLDOUT.json measured 2026-09-17T07:39:24Z -- of 3541 ledger rows the model decided 2414, got 2259 right, cleared 24 -- is what is current (README.md, 'What IS current'). |
| `A257-EXAM` | That `python covenant_distill.py --exam` gives 53 cases, 39 agree, 7 wrong, 7 abstained, 0 false clears and 7 false holds (README.md, 'What IS current'). |
| `A257-A67RATE` | That the judge hard-accuses 8 of 8 legitimate documents about violations (README.md, 'Or come to break it'). |
| `A257-P0109` | That rebalancing showed +0.45% out of sample at p=0.109, cited beside XRP and HBAR as evidence that no timing edge survived (README.md, 'What it is not'). |
| `A257-HASHLOC` | That the sha256 of every realdata/deep file is recorded in claude/IMPROVEMENT_LOG.md under D1 (realdata/README.md). |
| `A258-EARNHOST` | That since 2026-09-26 (A230) the earn server binds to loopback by default -- the listener binds to loopback, the server itself binds to loopback, and the watchdog starts it on loopback (covenant_earn.serve's docstring;… |
| `A259-GRADE` | That an asynchronous remedy whose condition is still PRESENT after its window did not fix it (covenant_highway.grade_started's docstring and rule: 'PRESENT then and ABSENT now is fixed; still PRESENT is did not fix'). |
| `A261-WINDOW` | That thirty minutes is the right grading window for dispatch_phone_build -- 'thirty is the window, so a slow runner is not graded as a failure and a build that never arrives still is' (covenant_highway REMEDIES; docs/HI… |
| `A262-DATE` | That the README header's totals line carries the measurement's date ('The date on that line is the measurement's date'). |
| `A262-VERSION` | That every field on the README header line is re-measured together by readme_totals.py --write, the version among them. |
| `A263-DOCSTRING` | That x_video_text.summarize() refuses to send anything under private/ to the public-repo judge unless COVENANT_ALLOW_PUBLIC_JUDGE=1. |
| `A264-T5B` | That the README header's version note must be what git measures NOW -- its count of core changes equal to git's at every commit (G1 T5b as first written, 2026-10-05). |
| `SW-CONTRIB-2026-10-06` | That an empty contribution_symbols was one of the reasons the Sentinel-Witness trader planned no orders on 2026-10-05 -- listed among them in docs/SENTINEL_WITNESS.md (2f6b184) and, in Sentinel-Witness's trader/README.m… |
| `A269-SLOT-SPLIT-2026-10-06` | That llama-server's default 4 parallel slots DIVIDED -c 8192 between them, so each request had about 2048 tokens, and that this per-request limit is why every ask through Tetsu's door failed with HTTP 500 on 2026-10-06… |
| `A273-RULES-SIZE-2026-10-06` | That the door's rules -- the system message Tetsu is handed -- are about 5,600 characters, so a fixed history budget of 12,000 characters fits the model's 8k window beside them and the answer -- stated 2026-09-26 in the… |
| `A274-DEGRADED-ANY-WARNING-2026-10-06` | That a node's /health reports degraded whenever any warning exists, so the node orbs on /pc/3d (covenant_pc3d.py layout()) can never be green while the win32 code-sandbox warning stands -- written in a Claude session no… |
| `A304-CHAIN-SPLICE-2026-10-07` | That ai_memory_system's verify_chain() proves the audit ledger has not been reordered or spliced (memory_store.py, the verify_integrity docstring; restated in state_root's docstring as 'this node's ledger was not reorde… |
| `A305-Q2-ONE-SPLIT-2026-10-07` | A127.Q2: that refining the student judge is no worse than rebuilding it on right answers (and no worse on false convictions), decided on one shuffle (seed 7) of a live ledger that grows daily. |
| `A309-DISCLOSURE-MEASUREMENTS-2026-10-07` | The sentence in free's disclosure, attached to every Moltbook message: that the measurements the message cited were from the operator's machine and were re-run before sending. |
| `A311-SHIPPED-PROMPT-2026-10-07` | A311's headline, as a description of the review that shipped at 6a1eda7: that the honest held drafts Tetsu lets through went from 0 of 11 to 21 of 33 runs. |
| `A315-COUNT` | That verify_deploy.py's re-pin of run_all_tests.sh on 2026-10-05 (8bf4d56) was the M53 failure 'for this file a second time' -- the comment trailing the digest, kept by 260f3dd. |
| `A283-STRIKES` | That a wrong answer to Moltbook's posting challenge spends one of the ten the account has before suspension, and that an abstained challenge spends nothing -- so the highway's moltbook_strikes read PRESENT on any unsolv… |
| `A300-STARVED` | That a round marked 'starved' -- the model failed during it -- ran but did not speak, so it never reset the highway's ambassador_stalled clock. |
| `A326-SCOPE` | That a path-based scope of the public threefold-memory repo -- 292 paths of personal material, 84 of full speak text -- leaves the other 541 paths fit to keep public. |

<!-- RETRACTIONS-INDEX:END -->

## How a retracted claim is stopped from coming back

Not by promising to sweep more carefully. By a suite that runs on every sweep.

**[`docs/RETRACTED.json`](RETRACTED.json)** is the machine-readable ledger: each
retraction carries its id, what was claimed, what is true, the **verbatim original
wording** (preserved, because deleting it is how a record dies), the regex patterns that
detect it, and the record files exempt from the check.

**[`test_r1_retracted.py`](../test_r1_retracted.py)** enforces three things, and is
registered in `covenant_one.py` and `run_all_tests.sh`:

| | what it pins |
|---|---|
| **L** | Every pattern must still match inside the record. A pattern matching nothing is a dead regex passing silently — and this makes the record load-bearing: delete it and the build breaks |
| **C** | A retracted phrasing may appear anywhere, in any framing, **provided the retraction's id appears within 10 lines of it.** A regex cannot separate an assertion from a description of one — this project's own judge cannot either — so the check does not try. It demands the citation, which is checkable |
| **V** | The scan reports how many files it read and **fails below a floor**, and names any expected directory that was absent instead of counting it clean. `conformance_indep/` is not in the runner's staging list, so a check written against the working tree can quietly scan less where the runner runs it |

**Proven by breaking it,** serially, on 2026-09-15 — a green that has never been made to
fail is not known to work:

| mutation | result |
|---|---|
| Claim reintroduced 380 lines from any citation | **FAILED as designed**, both patterns naming it |
| One pattern typo'd to match nothing | **FAILED as designed** (L) |
| Scan extension list emptied, 0 files read | **FAILED as designed** (V) |
| Claim reintroduced *immediately beside* an existing A121 citation | **passed — the limit** |

That last row is the honest boundary and it is written into the suite's own docstring.
The rule is proximity, so text planted next to a retraction notice is exempt. This
guards **accidental** reintroduction — a new section, a rewritten front page, a fresh
letter that restates the old claim with no correction in sight, which is precisely what
happened to the README — and it does not guard a claim planted beside its own retraction,
where a reader sees the retraction anyway.

Its first run found two live sites the hand sweep had missed.

## What has not been corrected

- **The bulk sends of 2026-08-31** stand wrong in other people's inboxes. There is no
  correspondent in those threads to write back to.
- ~~**Pedersen's prescription** — write the specification of `climb` and `attest`.~~
  **DONE 2026-09-15.** [`docs/SEMANTICS.md`](SEMANTICS.md) states the rules independently
  of any implementation; [`spec_reference.py`](../spec_reference.py) implements them and
  is forbidden (and mechanically checked) to read `triangulate.py` or `scale.py`; and
  [`test_r2_semantics.py`](../test_r2_semantics.py) compares the two over **every input in
  a bounded space** — 30,273 `attest` cases and 70,007 `climb` cases, enumerated rather
  than sampled, plus all 23 published vectors reproduced from the specification alone.
  Writing it up found one real inconsistency in the code (A123). Inside the bound this is
  not a sample; outside it, it proves nothing, which is why the bound is printed with the
  result.
- **`peers.txt` still reads `self`.** No second party has run the vectors. The federation
  is one node, and section IX's cap, L5 = 1, applies to every claim in this repository.
