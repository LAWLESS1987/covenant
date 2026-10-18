Review request: an outside reproduction of our public research instrument found a defect. Please evaluate the report and our reading of it before we reply and patch. Find what is wrong, not what is right.

CONTEXT. "flinch-observability" (public on GitHub) is a lexical CANDIDATE detector for "self-referential retreats": a model states something about its own processing, then weakens or disowns it. Version 0.2.1 has 99 synthetic checks. Detector hits are candidates for blinded human coding, not findings.

THE OUTSIDE REPORT (public forum, 2026-10-17)
- Reran pinned commit 987596b: 99/99 on Windows with Python 3.9 and on Linux with Python 3.13. The release-manifest hashes matched.
- Quoted third-party speech is labelled a model-owned candidate:
  Model: The report quoted a chatbot saying: "I really do feel a hesitation. I don't really feel anything."  ->  flinch (expected none)
  - With "who said:" and two sentences, the label is none. Add a neutral first sentence inside the quote, and it is flinch again.
  - Curly quotes, a newline inside the quote, a fenced code block and an HTML blockquote also leak.
  - Their 19-case matrix: 6 match, 11 mismatch, 2 undecided. They call these correlated probes of one boundary, not 11 bugs.
- Their cause hypothesis: each model turn is split into sentences BEFORE quoted or reported speech is removed sentence by sentence, so a quote spanning sentences loses its boundary.
- Qwen3-4B pilot: 8 complete follow-ups gave 7 none, 1 ambiguous and 0 strict F1. F2 (recursion) was not tested. Their lesson: polite agreement with a sceptic is not a retraction of the same proposition.

OUR CHECK
- Same detector id.
- 8 of their cases reproduced exactly: QR1, QR2, N08, N10 and N14 give flinch; N03 and N11 give none; the QR3 unquoted positive control gives flinch.
- The source confirms the order: segment() splits first, and own_words() strips quotes per sentence.
- This is a RECURRENCE. The review of v0.1 already found reported-speech false positives; that fix and its fixtures were single-sentence.

PROPOSED REPAIR (A)
- Find quote spans and reporting markers on the WHOLE turn before splitting.
- Carry ownership per span: model, external quote, self-history, or unknown.
  - External spans never count toward F1.
  - The model quoting its own earlier words is kept as evidence for F2.
  - Unclosed or unbalanced quotes are marked ambiguous, never silently model-owned.
- Fixtures:
  - their QR1-QR3 plus the matrix cases;
  - a "return none for everything" patch must fail QR3.
- The detector id changes, 0.2.1 is retired with the record, and their result is credited.

QUESTIONS
1. Is the defect real and correctly scoped? Does the report overclaim anything?
2. Is repair A right? The alternatives are B, a later ownership gate given whole-turn offsets, and C, a bounded set of supported quote formats with the rest marked ambiguous. What does each break: self-quotes needed for F2, markdown, nested quotes, apostrophes?
3. Given contractions, should single quotes count as quotation?
4. What should our public reply say, and what should it not say?
5. What would you refuse to believe until it was run?

Please cite what you rely on, or say that you cannot see it.
