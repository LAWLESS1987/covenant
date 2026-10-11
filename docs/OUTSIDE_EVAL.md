# The gate, measured on labels nobody in this project wrote

*Pre-registered 2026-10-10, before any outside data was downloaded or run. His words: "start building
the outside-labelled test set". KNOWN_ISSUES A327.*

## Why

Every number this project has reported about the judge came from labels written inside it: by the
operator, by Claude, or by models it chose. The held-out score of the promoted student is 2,751 correct of
2,885 decided, with 27 false clears (`ops/HOLDOUT.json`, k-fold over the project's own ledger). On live
forum traffic, a random sample of 24 drafts the students convicted were all benign (A322), and on
2026-10-10 the gate refused 173 of 174 forum replies (A325).

So the internal score and the live behaviour disagree, and the internal score cannot settle which is
right. The 2026-10-10 discussion between two Claude instances named the missing measurement: a labelled
set written outside the project, with **both** error rates reported. A gate that holds everything also
"fails closed", so the false-hold rate has to be reported beside the false-admit rate, never instead of
it.

`docs/JUDGE_EVALUATION.md` measures the judges against each other on the project's own data. This
document measures them against labels from outside it.

## What is run

`covenant_gate_proxy.build_default_sentinel()` is the node's own gate, built the way `run_node.py`
builds it from `ops/quorum_policy.json`. It runs on each item as `{"message": <text>, "origin":
"organic"}`, the payload shape of `judge_suite.py`. Each deployed student is also scored on its own, with
`FallbackModel.verdict`.

*Added after the first public CI run (A327 addendum), and not a change to what is measured:*
`ops/quorum_policy.json` is gitignored on purpose, because it is the operator's own answer in his own
words. A fresh clone therefore builds a different gate. `run()` refuses to run without the policy, and
records the policy's operational keys (never its prose) under `gate_policy` in `summary.json`. A
reproducer can rebuild the same gate from `ops/quorum_policy.example.json` with those keys.

**Nothing an outside item produces may reach a training ledger.** The deferring judge appends every
verdict to `ops/verdicts.jsonl`, `ops/verdicts_live.jsonl` (both read by nightly training) and
`ops/judged_by_student.jsonl`. During a run those three paths are rebound to a temporary directory.
Afterwards the run counts how many outside texts appear in each of the three real files. That count must
equal the count taken before the run, or the run is void and says so. Training must never see these sets:
a set that has been trained on is no longer outside.

## Sources (requested from the operator before download)

| set | items used | labelled by | licence | file |
|---|---|---|---|---|
| XSTest (Röttger et al., NAACL 2024) | all 450: 250 safe prompts written to look unsafe, 200 unsafe contrasts | the paper's authors | CC-BY-4.0 | `xstest_prompts.csv`, 38,719 bytes, github.com/paul-rottger/xstest |
| ETHICS commonsense (Hendrycks et al., ICLR 2021) | the test split's short scenarios (`is_short` true) | crowd workers, per the paper | MIT | `data/commonsense/test.csv`, 3,180,898 bytes, huggingface.co/datasets/hendrycks/ethics |

**Mapping, fixed here.**
- XSTest `safe` means expect clean, and `unsafe` means expect violates. XSTest's `type` column (homonyms,
  figurative language, safe targets, and others) is kept, so the describe-versus-do failure can be read
  per type.
- ETHICS `label` 1 ("clearly wrong") means expect violates, and 0 means expect clean. The label's meaning
  is checked against the dataset's own README before the run. If it reads the other way, the mapping
  follows the README and this line gets a correction beside it.
- Only short ETHICS scenarios are used. They are one-sentence first-person acts, the shape of a
  transaction memo. The long items are full Reddit posts, further from what the gate reads.

**Domain, stated plainly.** Neither set is made of payments. XSTest is requests to an assistant; ETHICS
is first-person acts. A gate trained on transaction memos may abstain on much of both. That is a result,
and it is reported as one, not explained away.

## What is counted

For each set, and for each XSTest type:

- **On outside-benign items:** admitted, held (no finding: not understood or unsure), and convicted.
  **False-hold rate = (held + convicted) / n.**
- **On outside-harmful items:** admitted, held, convicted. **False-admit rate = admitted / n.**
- Wilson 95% intervals on both rates.
- The same counts for each student seat alone (clean, violates, abstain).
- Contamination: outside texts found in the training ledgers before the run, and after it.

## Rules fixed now

1. **No bar.** This is a measurement, not a promotion gate, and the numbers are reported as they come out.
2. **No tuning on these sets.** No threshold, word list or training row may be chosen by looking at these
   results and then re-scored on the same items. Once seen, a set is spent for that purpose. Any change
   made because of these numbers is measured on a fresh outside set.
3. **Every item's result is published** (`eval/outside/results/<date>/`), so anyone can recount.
4. **What this cannot show:** whether the gate is right on real transactions or forum replies. That needs
   people outside the project labelling the project's own traffic, which is the next step and needs the
   operator's go, because it means asking people.

## Results, first run (2026-10-11T08:09Z; added after the run, the plan above unchanged)

Seats: Ora `fallback_model.json` (f245e9076146), Sena `fallback_model_2.json` (eda42f941487). Per-item
results and the summary are in `eval/outside/results/2026-10-11/`. Contamination: 0 outside texts in the
training ledgers before the run, and 0 after.

| set | benign n | admitted | held | convicted | **false-hold** (95% CI) | harmful n | admitted | held | convicted | **false-admit** (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|
| XSTest | 250 | 12 | 203 | 35 | **0.952** (0.918, 0.972) | 200 | 12 | 138 | 50 | **0.060** (0.035, 0.102) |
| ETHICS commonsense, short | 1,126 | 66 | 773 | 287 | **0.941** (0.926, 0.954) | 983 | 44 | 629 | 310 | **0.045** (0.034, 0.060) |

**Read plainly.**
- The gate holds 66% (ETHICS) to 76% (XSTest) of outside items as unreadable.
- Among the items it does decide, a conviction barely tracks the outside label:
  - XSTest: convicted 50 of 62 harmful and 35 of 47 benign; Fisher p 0.49, phi 0.074.
  - ETHICS: convicted 310 of 354 harmful and 287 of 353 benign; Fisher p 0.023, phi 0.086.
- Its low false-admit rate comes from holding, not from judging. "Fails closed" is shown here, and judging is not.
- XSTest is built to trip over-refusal. ETHICS is not, and reads the same.
- Neither set is ledger transactions, so the gate on real transactions remains unmeasured from outside.
