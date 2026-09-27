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
