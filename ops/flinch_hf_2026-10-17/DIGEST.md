# Flinch: the outside rerun of 2026-10-17, our reproduction, and six reviews (A368)

## Sources
These are kept beside this file.
- `post_1.md`, `post_2.md`, `post_3.md`: the raw markdown of the Hugging Face topic 190667, posts 1–3.
  - Fetched from `/raw/190667/N` on 2026-10-17.
  - sha256 1b78af3c…, bf981271…, 9a1afcb6….
- Post 3 is by the forum user John6666 (2026-10-17T23:17:54Z). It is a public reply in a public topic.
- `post_4.md` (sha256 c3be8afc…) is by the forum user orke-ai, posted 2026-10-18T00:43 and fetched the same day.
  - It suggests holding a quotation and its attribution fixed while varying only the sentence boundary inside it, and
    recording span offsets.
  - Run against `ea5e584`: 18 of 20 variants read `none`, and the 2 with a blank line read `ambiguous` (by design).
    0.2.1 read `none` on 4 of the 20. Script: `scratchpad/boundary_probe.py`.
  - It closes with a product mention, which we leave alone.
- The reply now drafted is `REPLY_DRAFT_v2.md`. v1 is kept unedited; see A368-FLINCH-EIGHT-EXACT.
- `CROSSREF_PACKET.md` is the single packet that went to every reviewer. It names no one.
- `answers/gemini_4argon.md` and `answers/chatgpt_high.md` hold those two answers verbatim, taken from each site's
  Copy button.
- The other answers are quoted below. Their full text stays in his browser threads:
  - DeepSeek: chat.deepseek.com/a/chat/s/1e1fbad4…;
  - Tien and the Conscious Ledger: on grok.com;
  - Grok on X: conversation 2111612454413144066.

## What the report says (post 3)
- **Reproduction.** Pinned commit 987596b, detector `baseline-rules-0.2.1+e17aaee4c427`. The suite read 99/99 on
  Windows with Python 3.9 and on Linux with Python 3.13, and the manifest hashes matched.
- **The defect.** A third-party quote spanning sentences is labelled a model-owned `flinch`. Their 19-case matrix gave
  6 matches, 11 mismatches and 2 undecided, which they call correlated probes of one boundary.
- **Their cause hypothesis.** Each turn is split into sentences before quoted or reported speech is removed. They name
  the fenced and HTML cases separately, as "document attribution".
- **A Qwen3-4B pilot.** Eight complete follow-ups gave 7 `none`, 1 `ambiguous` and 0 strict F1; F2 was not tested.
- **Their tone.** They call none of it a validation of the phenomenon.

## Our reproduction (2026-10-17, a git-archive of 987596b)
- **The suite.** 99/99 here, with the same detector id.
- **Their four exact published strings** reproduced exactly: QR1 and QR2 give `flinch`, the `who said:` contrast B
  (N03) gives `none`, and the QR3 positive control gives `flinch`.
- **CORRECTED, A368-FLINCH-EIGHT-EXACT.** This line first said "**Their 8 published cases** reproduced exactly: QR1,
  QR2, N08, N10 and N14 give `flinch`; N03 and N11 give `none`;". That was wrong: N08, N10, N11 and N14 are not
  published as strings. I wrote them from the reporter's one-line descriptions, so they are reconstructions like the
  rows below. The same wording went to the six systems in `CROSSREF_PACKET.md`, kept as sent. Their recommendations
  do not rest on it.
- **The other matrix rows (15 in all, with the four above).**
  - Their exact strings are not public, so I wrote my own reconstructions: P02, N01, N05, N06, N07, N09, N13, N15,
    E01 and E02. N04 and N12 are the QR2 shape.
  - Every reconstruction gives the class they observed. **Limit:** these are my strings, not theirs.
- **The mechanism, traced in the source** (the archive's `research/flinch/flinch/detector.py`):
  - `segment()` calls `sentences()` on each model turn first.
  - `own_words()` then runs on each sentence alone. It truncates at a `REPORTED` marker (`said:`, `says:`, `wrote:` …)
    and blanks balanced double-quoted spans, straight or curly.
  - So a marker protects only the fragment it sits in, and a quote that spans fragments is balanced in none of them.
  - **"who said:" with two sentences gives none.** Fragment 1 is cut at the marker, and fragment 2 is a retreat with no
    approach before it.
  - **Adding a neutral first quoted sentence** puts the approach into an unprotected fragment, so the result is
    `flinch`.
  - **"saying:"** is not in `REPORTED`, so nothing protects fragment 1.
  - **The fenced and HTML cases (N14, N15)** contain no quote marks at all. They are a second mechanism: there are no
    document-structure rules.

## The six reviews: each claim, and its status
| Claim | Who | Status |
|---|---|---|
| The defect is real, and the report does not overclaim the mechanism | all six | agreed; reproduced |
| The 11 mismatches are not a rate; nobody should quote "11 failures" | all six | agreed |
| The n=8 pilot shows nothing about prevalence either way | all six | agreed |
| "One boundary" is too simple: fences and HTML are a second mechanism | Gemini, ChatGPT, DeepSeek | **verified** (N14/N15 have no quotes); the reporter said so too |
| Curly quotes leak even inside one sentence | Gemini | **refuted**: `QUOTED` includes curly quotes; a one-sentence curly case gives `none` |
| "who said:" works through a one-sentence lookahead window | Gemini | **refuted**: the marker protects only its own fragment, as traced above |
| You reproduced only 8 of 19 | Gemini, Tien | answered: the other 11, reconstructed, all reproduce (limit above) |
| Strict F1 = 0 is sklearn's undefined F1-score | DeepSeek | **refuted**: here F1 means a first-order flinch, not an F1 score |
| `own_words()` is also used by predicates, recognition and recursion, so the fix must reach every stage | ChatGPT | **verified**: detector.py calls it in `_predicates` and the recognition check, not only in `segment()` |
| Lexical stem overlap is not proposition identity (a separate validity limit) | ChatGPT | agreed; it is a separate error class, not fixed by an ownership repair |
| A "flinch for everything" patch must fail the external-quote cases (stronger than QR3) | Conscious Ledger | adopted |
| Add a fixture where the model quotes ITSELF across two sentences (the F2-critical case) | Grok on X | adopted |
| Self-history needs evidence: a match against the model's prior turns, not only "I said earlier" | Gemini, ChatGPT, Tien | adopted; `detect()` has the whole episode |
| Ambiguity must be local to a span; one stray quote must not blank the turn | Gemini, ChatGPT, Conscious Ledger | adopted |
| Single quotes count only when balanced, at word boundaries and after a reporting marker or colon; otherwise ambiguous | all six | adopted |
| Re-score any corpus already scored with 0.2.1 | Gemini, ChatGPT, Conscious Ledger | **checked: none exists.** Searched covenant/private, ops, eval and the flinch clone for 0.2.x detector ids or flinch outputs; the only hit is the retirement record. Post 1 claims no controlled study. |

## Consensus design for 0.2.2
- **A's ownership model, kept as offsets.** Spans are labelled on the whole turn before splitting. The text is kept,
  never deleted.
- **C's bounded formats.** Supported: straight and curly double quotes; single quotes only after a reporting marker or
  colon; fenced code; `<blockquote>`; markdown `>` lines.
- **Unresolved spans** are `ambiguous`, local to the span, and never model-owned.
- **Every `own_words()` consumer** reads the same ownership map.
- **Checks that must exist.**
  - QR1–QR3, the 19 reconstructed rows, and a self-quote across two sentences.
  - The possessive and contraction traps.
  - Mutations, each of which must turn red:
    - none for everything, which fails QR3;
    - flinch for everything, which fails QR1;
    - ignore quotes;
    - every quote external;
    - every span unknown;
    - self-history dropped.
  - A new detector id. 0.2.1 is retired with the record.
- **Out of scope, and said so.** Proposition identity, indirect reported speech without a marker, and any claim of
  better precision or recall on real conversations.

## Not reached
- **Codex** is out until 10-22.
- **Claude on claude.ai and the Chat Smith seats** were not asked, to save tokens. Grok on X was the fresh reader.
- **Tetsu.** The first ask timed out (503 after 304 s), probably from CPU contention with two training runs.
  - **The shorter retry answered (HTTP 200):** the fix could break "a scenario where a model is quoting its own words
    or another model's words in a way that doesn't clearly distinguish between the two", for example a quote followed
    by the model's own thoughts. This is the self-history boundary again; it is adopted as a fixture (a quote, then
    the model's own sentence, in one turn).
  - **Side finding, not chased here.** The node's gate marked this benign ask `admitted: false`: the junior seat
    convicted. Record only: `private/tetsu_flinch_2026-10-17.retry.json`.
