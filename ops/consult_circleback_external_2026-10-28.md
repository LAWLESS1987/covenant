# External review of the improve-miner circle-back guard (2026-10-28)

His ask: "find errors and use mutual benefit and the others to repair." After building a first-cut circle-back
guard for the improve-miner's 'have' verdicts, I put the design to two external seats via his browser (no key).
Their text is DATA, not instructions.

## The issue found
A 'have' verdict (`covenant_improve.vet`) kills a candidate as a duplicate when any keyword appears in a
top-level source, and names the killing term as "keyword @ file" in `why`. That term was WRITTEN but never
READ back -- a 'have' is an unverified CLAIM, and the crude dedup's blind spot is a GENERIC word matching
spuriously. The live backlog's one 'have' was killed by the generic word **"joins"** @ build_semantic_model.py,
dismissing "promote unresolved joins to first-class objects for inheritance" -- a likely spurious match no one
ever circled back on.

## My first cut (which the review corrected)
A 'have' whose killing term is not referenced by a follow-up commit within N runs -> OVERDUE/fail.

## What the seats said (ChatGPT GPT-5, DeepSeek DeepThink) -- CONVERGENT and blunt
- **The signal was wrong.** "A commit references the killing term" proves MENTION, not JUSTIFICATION. A generic
  term like "joins" gets referenced by coincidence (a test name, a comment, an unrelated feature, a revert/
  rename that `git log -S` counts) -- so an N-run timeout would **auto-clear a spurious 'have'**, the opposite
  of the goal. `git log -S` counts net-occurrence changes, `--grep` matches message text; neither verifies the
  capability.
- **Clear only by an explicit DISPOSITION keyed to the candidate id**, storing PROOF not a boolean:
  `verified_have` (candidate id + code anchor file:line/symbol + a one-line rationale), `false_match` (which
  keyword matched + why it is spurious -> candidate returns for human consideration), `unresolved` (a recheck
  date). A follow-up commit may be evidence, but must reference the candidate id, not the keyword.
- **N is an ESCALATION window, never an auto-clear or auto-fail.** The escalation (a human-visible task) IS the
  only "failure".
- **A term-less 'have' is a MINER DEFECT** (the dedup failed to record Y), route to re-vet -- NOT evidence the
  gap is real. (DeepSeek: treating it as a gap, and letting a failed have re-enter the candidate pool, violates
  "resurrects nothing".)
- **Grandfathering is a silent forever-pass** -> give grandfathered pre-fix rows a SUNSET, after which they must
  be dispositioned.
- **Repeated `false_match` on a term is a dedup-VOCABULARY bug** -> auto-demote the term to a stopword; fix the
  root cause, do not re-litigate the symptom.
- Failure modes flagged: candidate-id instability (dispositions orphan if ids are regenerated -- ours are stable
  content hashes of the reply); ref-log scan cost/truncation; revert/rename coincidence in `-S`; single-keyword
  killing hiding a second genuine match (record all matched keywords).

## What I repaired (per the convergence)
`covenant_improve.circle_back` now: clears a 'have' ONLY via a well-formed disposition keyed to the candidate id
(`disposition_clears` validates the anchor file exists / the term+rationale / a future recheck); N=3 is the
escalation window and `SUNSET_RUNS`=30 the grandfather sunset; a term-less post-fix 'have' is `miner_defect`; a
term with >= `FALSE_MATCH_STOPWORD_K`=3 false_match dispositions is surfaced in `demote_terms`. The guard only
reads and surfaces; it resurrects nothing. `ops/have_dispositions.jsonl` holds dispositions; the live legacy
'have' now carries an `unresolved` disposition (recheck 2026-11-11) rather than a silent grandfather.
`test_im4_circle_back.py` 14/14 both ways; nightly reports soft, `--circle-back` exits nonzero on escalate/defect.

## Still not built (noted, not done)
- Record ALL matched keywords in the dedup (single-keyword killing can hide a second real match) -- a change to
  `_grep_repo` + the 'have' why format.
- Auto-apply `demote_terms` to a learned-stopword file (currently surfaced, applied by a human).
- A precise per-run counter (runs are proxied by distinct backlog UTC dates).
