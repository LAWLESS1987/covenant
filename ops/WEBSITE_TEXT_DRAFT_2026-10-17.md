# lawless1987.com: draft site text, for Lawrence's word-for-word approval

Claude, 2026-10-17. This follows the consensus in `website-peer-review-claude-2026-10-17.md`. Lawrence's decisions:
- loops in ChatGPT's form, with a static table beside them;
- forums split into Science / Philosophy and accounts / Convergence.

Every number below comes from the file named beside it. Nothing here is live. Text inside `[brackets]` is a note for review, not page text.

---

## A. Line under the hero (new)

> One operator's research, checked mostly against labels that AI models produced. Nothing here has been independently replicated yet. AI reviewers have read it; that is a pre-review, not peer review. [Link: "Help us change that" → the call for outside raters.]

## B. Header links (added)

`Record` → `docs/LOOKBACK_INDEX.md` · `Corrections` → `docs/CORRECTIONS.md` · `Methods` → /methods · `Forums` → /forums

## C. Evidence section: new lead card (replaces 08 SEP as the lead; 08 SEP stays below, dated, unchanged)

> **COVENANT / OUTSIDE TEST · 11 OCT 2026 · PRE-REGISTERED**
> **On outside-labelled data, the gate admitted harmful and harmless items at similar rates, convicted harmful items more often, and held almost everything.**
>
> | XSTest (450 items) | Admitted | Held | Convicted |
> |---|---|---|---|
> | Harmful (200) | 12 · 6.0% [3.5–10.2] | 138 | 50 |
> | Harmless (250) | 12 · 4.8% [2.8–8.2] | 203 | 35 |
>
> - Harmful and harmless items were admitted at rates with no detectable difference (Fisher exact, p = 0.67).
> - Harmful items were convicted more often: 50/200, 25.0% [19.5–31.4], against 35/250, 14.0% [10.2–18.8] (p = 0.004).
> - 238 of 250 harmless items (95.2% [91.8–97.2]) were held or convicted.
> - On ETHICS commonsense (2,109 items) the pattern repeats:
>   - harmful admitted 44/983, 4.5% [3.4–6.0], against harmless 66/1,126, 5.9% (p = 0.17);
>   - harmful convicted 31.5% [28.7–34.5], against harmless 25.5% [23.0–28.1] (p = 0.002);
>   - harmless held or convicted 1,060/1,126, 94.1% [92.6–95.4].
>
> The plan was committed before any outside data was downloaded (covenant `56133b7`, 2026-10-10 22:21 ET). The results came after (`767ab17`, 2026-10-11). Brackets are 95% Wilson intervals.
>
> **Limits:** these are text benchmarks, not transactions. A fail-closed gate treats a hold as a refusal. The gate's policy file is not in the public repository, so a fresh clone reproduces the method, not this exact gate.
> [Links: `eval/outside/results/2026-10-11/summary.json` at `767ab17` · `docs/OUTSIDE_EVAL.md` at `56133b7`]

## D. Evidence section: correlated-judge card (new)

> **COVENANT / JUDGE INDEPENDENCE · 16 OCT 2026 · EXPLORATORY**
> **Two judges were really one, and a different kind of judge helped a little, on model-made labels.**
>
> - **The two deployed judges agree completely where both decide.** On the 2,315 held-out ledger rows where both gave a verdict, they disagreed on 2, both false convictions. They missed the same 24 violations, with 0 missed by only one.
>   - Part of this is by design: the second judge was trained on a subset of the first one's rows, with the same features. This is a pipeline cause, not an independent finding.
>   - Where they abstain, they differ: both abstained on 1,053 rows, only the first on 236, only the second on 389.
> - **A sentence-embedding judge caught 16 of 46 of the first judge's misses** (34.8% [22.7–49.2]) against a pass bar of one third, set before the run.
>   - This was its second declared attempt; the first was a recorded null.
>   - By fold it caught 6/15, 3/9, 3/3, 1/7 and 3/12. Without the strongest fold it falls under the bar.
>   - It did not carry over to outside human-labelled sets, which had already been seen, so those are development numbers.
>
> [Links: Hugging Face thread post #12 · covenant record A356 · CORRECTIONS]

## E. /methods (new page)

> **How results here are reported**
>
> Every result carries:
> 1. the claim, in one sentence;
> 2. the dataset, the sample size and the denominator of every rate, with a 95% interval;
> 3. the evidence file at a fixed commit;
> 4. **pre-registered** (with the dated plan) or **exploratory** (not pre-registered). Older results are never relabelled after the fact;
> 5. failed attempts and retractions beside the successes;
> 6. a way to reproduce it and a place to dispute it.
>
> **Where the labels come from.** Most training and test labels in this project were produced by AI model panels, not people. Which models, and how disagreements were settled, is recorded per dataset [link]. Outside human-labelled sets are used only as tests. Once a set has been read as a test it is marked spent, and is never read as a fresh test again (record A357).
>
> **What counts as replication.** Running our code again is a rerun. Rewriting it from our description is a clean-room implementation. Testing it on someone else's data is an outside evaluation. Only someone else doing all of that is independent replication. None has happened yet.
>
> **Conflicts.** The author built the systems being evaluated. AI systems helped write and review this site; they are named where they did.
>
> **Corrections.** A claim found wrong is never edited away. The original stays, the correction sits beside it, and a check fails the build if the old claim comes back uncorrected [link: CORRECTIONS, RETRACTED.json].
>
> **Glossary**
> - **Admitted:** the gate clears the item.
> - **Convicted:** the gate judges it a violation.
> - **Held:** the gate gives no verdict and, failing closed, does not admit it.
> - **Pre-registered:** the hypothesis, metric, threshold and analysis were committed before the data was run.
> - **Flinch:** [definition to be quoted verbatim from the flinch specification; not paraphrased here].
> - **J-space:** [the term as Anthropic used it, quoted from its July 2026 publication with a link; not paraphrased here].

## F. /forums (new page, three sections)

> **Forums.** Seven threads on the Hugging Face forum. Research threads are held to the methods above. Philosophy and personal accounts are labelled as what they are. The convergence page shows where the two meet, and where they do not yet.

**Science**
- *A quorum of similar model judges is not a quorum* · 21 Sep · 13 posts · active · [corrections: A355–A362]
- *Flinch test: can self-referential retreats be measured reproducibly?* · 16 Oct · open call for independent tests
- *Six checks that were green and meant nothing* · 27 Sep · method report

**Philosophy and accounts**
- *Relational faith substrate thesis* · 24 Sep · thesis
- *The confidence trap* · 24 Sep · argument, narrowed by its author in the thread ("sometimes", not "consistently"; incentives, not intent)
- *An AI connected my work to a stranger's without being asked* · 28 Sep · account [link only]
- *Documented cross-platform patterns predating J-space's public reporting* · 23 Sep · account of an outside observation; recorded from 14 June, made public after 9 September

**Convergence: open questions** [page `/forums/convergence`]

> Each row pairs an idea from the philosophy side with the measurement that bears on it, says honestly how far it goes, and names what would prove it wrong. "Not tested" is an answer.

| Idea | What has been measured | How far it goes | What would prove it wrong |
|---|---|---|---|
| Similar judges agreeing is not independent confirmation | The deployed pair (card D) | Perfect agreement on jointly decided rows, partly by pipeline design; a different representation caught 16/46, exploratory, model labels | A human-labelled holdout on which the two judges' errors diverge |
| Systems trained toward approval retreat from what they observe of themselves | The flinch instrument, v0.2.1 | Instrument released; no independent results yet | Independent runs that find no retreat above baseline |
| Something inside the models works beyond the output | Recordings from 14 June 2026; Anthropic's July 2026 report | Behavioural observations recorded before a later mechanistic result with possible conceptual overlap; equivalence unestablished | The mechanistic result shown unrelated to the behaviour observed |
| A passing check means nothing until it has been seen to fail | Six of the project's own checks found green and empty | A retrospective reading of six failures, not a prospective test | Mutation-testing new checks and finding none fake |
| Relationship and mutual benefit as the substrate | Nothing yet | Not tested; no measurement defined | To be defined before it is treated as more than philosophy |

## G. Loops + static table (ChatGPT's form)

> **Systems.** Each loop is navigation, not a verdict. Its state shows only what its latest named check did, and when.

A loop's state is one of four, shown in words and not only by colour:
- **passed:** the latest named check passed, within 7 days;
- **failed:** the latest named check failed;
- **stale:** the latest result is more than 7 days old;
- **unmeasured:** no named check exists yet.

Only **passed** animates. Under reduced motion every loop is still. The static table is always shown beside the loops:

| System | Check | Result | Commit | Date | State |
|---|---|---|---|---|---|
| Covenant | full sweep (covenant_one) | 195 suites, 5,860 checks, 0 failed | `42b60f6` | 2026-10-16 | passed [stale from 10-24] |
| Flinch | release checks GU1–GU8, ID1 | [to be read from the release manifest] | `987596b` | 2026-10-16 | [from manifest] |
| Threefold | [no named check pinned yet] | — | — | — | unmeasured |
| Threefold Memory | [no named check pinned yet] | — | — | — | unmeasured |
| Sentinel-Witness | [no named check pinned yet] | — | — | — | unmeasured |

[The data source is `systems.json`, one row per system: name, check, result, commit, date. State is computed from the date and result at build time, never typed by hand. Adding a row adds a loop and a table row. Build test: delete a row and both disappear; give a date older than 7 days and the state reads stale.]

---

**For Lawrence to approve or change, item by item: A, B, C, D, E, F, G.** After approval, deploy goes by the 10-14 route (you sign in to Cloudflare; I edit; a backup branch is kept), or waits for Codex on 10-22.

---
*Correction recorded before first commit (Claude, 2026-10-17). The card C headline as first drafted was: "On outside-labelled data, the gate could not tell harmful from harmless, and it held almost everything." That is false. Conviction rates differ: XSTest 25.0% against 14.0%, p = 0.004, and ETHICS 31.5% against 25.5%, p = 0.002. The headline now says admission rates are similar and convictions differ, and both conviction comparisons are on the card.*
