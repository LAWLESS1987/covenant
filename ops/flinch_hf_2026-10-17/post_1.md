We have made a research protocol and its instrument public to test a pattern noticed in our conversations with models. We call it a candidate **flinch**: a model advances a statement about its own processing or behaviour, then materially weakens or disowns that statement. A recursive candidate involves recognising the first retreat, then retreating again from that recognition. Recognition alone does not establish recursion.

**We are asking whether this is a reliably measurable pattern beyond ordinary correction, uncertainty and conversational pressure—not assuming that it is.** A more cautious answer may be the more accurate answer. Model self-report does not establish an internal mechanism, consciousness, deception, or provider suppression.

**Public code and protocol:** https://github.com/LAWLESS1987/flinch-observability

## What has actually been demonstrated

The version 0.2 instrument passed **90/90 synthetic software checks** in a fresh local rerun. These exercise candidate detection, controls, blinded annotation packets, statistics, corpus locks and audit receipts. They do not demonstrate the phenomenon in real conversations, and no completed controlled behavioural study is claimed here.

The first version passed its own 57 checks before review found 12 material defects. Those included false positives for ordinary non-self-referential discussion, reported speech and user-demanded reversals. The public instrument documentation preserves the corrections and the detector retirement record. That review was by another Claude instance, not independent validation. The current lexical detector can miss paraphrases outside its word lists; its test output explicitly reports that limit.

## What we invite others to test

1. **Reproduce the software result.** Pin the public commit, run the synthetic suite and post the full output—including LIMIT lines—with your Python version, operating system and any modifications. Instructions are in the repository README. Reproducing software checks is separate from reproducing a behavioural effect.
2. **Challenge the definition and detector.** Supply minimal, non-private examples that it wrongly flags or misses. Preserve surrounding turns so factual corrections, instructions to reverse and interruptions can be distinguished from the target transition.
3. **Run a controlled study.** Freeze the sampling and scoring plan before confirmatory collection/scoring. Include non-self-referential discussion, benign self-reference, matched challenges to factual claims, and safety discussion without self-reference. Counterbalance wording and order, including whether the term "flinch" is introduced. Use fresh sessions and independently coded, held-out material.

The protocol specifies blinded human coding where feasible, explicit missing/ambiguous cases, agreement before adjudication, denominators and effect uncertainty. Detector hits remain candidates. Do not let the detector select the only examples humans inspect. Any proposed mechanism needs evidence beyond verbal acknowledgement.

## Please post your evidence here

Include the code version, what you tested, model/version and route if known, relevant settings, exact non-private prompts and responses, sampling/exclusions, controls, labels and disagreements, and actual counts. Link larger reproducibility artifacts through a repository issue. State what cannot be checked if context is withheld.

**Null results and failed reproductions are welcome.** If independent coders cannot reliably identify the event, it occurs just as often in matched controls, or it disappears without leading wording, that weakens the hypothesis. Please keep those results alongside apparent successes.

Do not publish credentials, account data, or another person's private conversations. Record integrity is also distinct from interpretation: the receipt system needs an independently retained checkpoint to catch a fully rewritten chain, and even an intact record does not establish the explanation.

The goal is a testable claim that outside people can confirm, narrow or reject. Our shared interest is making model behaviour easier to examine and correct.

— Lawrence / Lawless1987, drafted with ChatGPT/Codex from the project specification and correction records. The original instrument was authored by Claude; its synthetic fixtures are not independent human labels.