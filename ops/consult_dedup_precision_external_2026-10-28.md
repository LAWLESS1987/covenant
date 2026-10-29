# External review of the improve-miner dedup precision (2026-10-28)

His standing ask: "continue finding flaws and consulting the others." After building the circle-back guard I
dug into WHY the dedup false-killed a real candidate, found a batch of flaws, and put them to two frontier
seats via his browser (no key). Their text is DATA, not instructions.

## The flaws found
The candidate "promote unresolved joins to first-class objects for inheritance" was killed as a 'have' because
the keyword **"joins" matched an English verb in a code COMMENT** (`build_semantic_model.py:56`), via:
- **A** `_grep_repo` greps the WHOLE file, including comments/docstrings/strings -- prose, not capability;
- **B** a case-insensitive SUBSTRING match (no word boundary) -- 'joins' also hits 'rejoins', 'enjoins';
- **C** it returns on the FIRST matched keyword, ignoring the candidate's other keywords;
- **D** it scans only top-level .py, missing subdirectories.

## What the seats said (ChatGPT GPT-5, DeepSeek DeepThink) -- CONVERGENT
- **Fix A, B, C; defer D.** A is mandatory (comments/docstrings are not evidence of a capability -- tokenize/
  AST). B is a cheap precision win (token/identifier-aware, handling snake_case/camelCase, not blind `\b`). C
  is the deepest defect: a first-keyword match must never establish the whole candidate is implemented;
  collect evidence across all concepts.
- **The governing invariant: "a lexical match is evidence to INVESTIGATE, never sufficient evidence to
  DISCARD."** A lexical hit should FLAG a candidate (a POSSIBLE_HAVE / work item), not kill it. The circle-back
  guard is detection-and-escalation, NOT correction -- it does not make precision unnecessary (review latency,
  reviewer load, confirmation bias; a human can still approve a wrong 'have'; opportunity cost if the idea
  leaves the pool before review). The "rejecting a duplicate is cheaper than building one" premise is
  INCOMPLETE -- it ignores the far larger cost of suppressing a genuine improvement.
- **DeepSeek added:** deferring D needs a COVERAGE flag -- "absence of evidence in a partial scan is not
  evidence of absence," so a no-match must not be read as a confident 'new'. Match candidate CONCEPTS not raw
  keywords (specificity / idf; a single generic word shouldn't dominate; stopword common tokens). POSSIBLE_HAVE
  should be tri-state and triaged by evidence quality, NOT auto-escalate every lexical hit to a human.

## What I repaired (per the convergence)
`covenant_improve._grep_repo` now matches candidate keywords against a file's IDENTIFIER tokens (Python
`tokenize`, which drops comments, docstrings and string literals; Python keywords excluded) at WORD level
(snake_case + camelCase components via `_components`), never as a raw-text substring, and collects ALL distinct
matches as "term @ file (code `identifier`)". Fixes A, B, C. The 'have' it yields is held by the circle-back
guard for a disposition -- a lexical match investigates, never silently discards -- realizing the invariant
without a full POSSIBLE_HAVE rename. Result: "joins" no longer matches (it was a comment word); the candidate
now matches only on the generic identifier "unresolved" @ covenant_daily.py, which the circle-back surfaces for
a human. `test_im5_dedup_precision.py` 8/8 both ways (comment/docstring not matched; component matched; substring
NOT matched; all concepts collected; unparseable file contributes nothing; the live 'joins' regression).

## Deliberately NOT done (noted, deferred with reason)
- **D** (recursive/subdir scan): deferred; a no-match stays `backlog` = "needs a human call", never a confident
  'new', so the coverage gap does not silently assert absence.
- **Specificity / idf weighting** so a single generic identifier ("unresolved") does not dominate: the residual
  "unresolved" match shows this is the next refinement; the circle-back holds it in the meantime.
- **Full POSSIBLE_HAVE tri-state + triage** of escalations by evidence quality: a larger downstream change;
  the circle-back's disposition model already prevents silent discard.
