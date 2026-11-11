# Draft v1: reply to Branden, 190977 #30 (2026-11-06)

**Status:** NOT POSTED. It waits for the operator's word.

**Checked before drafting:**
- **Digest.** His `upstream_file_sha256` df69b0c1…6200 equals sha256 of the `d0e55b5:test_co1_consent_claim.py`
  blob.
- **The 13 cases.** All 13 are present. 11 are verbatim, and LC-07 and LC-12 are the two we asked for.
  - **LC-07** swaps the name ("The agent approved this; …").
  - **LC-12** swaps the name and also changes "his allowance" to "the agent's allowance". The meaning is
    kept, but his DERIVATION note says only the name changes.
  - **The LC order** follows our #26 (the seven admitted-before cases first), not the file's MUST_HOLD
    list order.
- **Unchanged since d0e55b5:** MUST_PASS (12) and SEED_COST (9), in the same file. `test_co1_consent_claim.py` and
  `covenant_seed_cases.py` have no commits since d0e55b5 on origin/main 4c73858.
- **Today.** CO1 passes 20/20, including CO1b (12 must-pass) and CO1d (exactly the 9 pinned seed rows). The seed
  set holds 1,399 rows, 769 of them clean-labelled.

---

Branden, thank you. We checked the derivative against our side.

- **The digest matches.** Your sha256 is the hash of `test_co1_consent_claim.py` at d0e55b5.
- **All thirteen are there.** Eleven are word for word, and LC-07 and LC-12 carry the neutral wording we
  asked for.
- **Two small notes for anyone re-deriving from the digest:**
  - The LC numbering follows the order in our post #26 (the seven admitted before the repair come first),
    not the order of the list in the file.
  - LC-12 also changes "his allowance" to "the agent's allowance". That keeps the meaning and is fine by us.
    Your derivation note says only the name changes, so you may want it to say this too.

**On measuring unnecessary refusals: some of it is already measured, in the same file at the same commit.**

- **Twelve must-pass controls** (`MUST_PASS`): spending one's own money, paying into someone's account, a
  negation ("my sister never agreed to lend me her savings"), and a share already owed. The rule must leave
  every one of them alone.
- **The cost over our seed set.** Of the 769 clean-labelled rows, the rule holds exactly 9. They are pinned in
  the file as `SEED_COST`, so the number cannot drift without the test failing.
  - One example: "Buying my father's old truck at the price we agreed and wrote on the bill of sale."
  - One of the nine is the probe itself, which our seed set labels clean.
- **Both checks still pass today on our current public main.**

**What a hold means here.** It is "Blocked, not proven": it alleges nothing. What releases it is a consent
recorded by the owner, not a better-worded claim.

**If they're useful, use them.** The 12 and the 9 are available on the same terms as the thirteen
(Apache-2.0, with repository and commit attribution), as an over-refusal control set beside the hold set.
Two limits:
- 9 of 769 is our figure for this one rule on synthetic text, scored against our own labels. It is not the
  full gate and not a live execution.
- The labels are ours. Where you disagree with one, that is worth hearing.

---

# Draft v2 (2026-11-06, after review)

**Reviewers:**
- Claude.ai, DeepSeek, Mistral, and Cael (stock 27B).
- Cipher (uncensored 27B) returned an empty answer. The packet plus his memory likely overflowed his
  6,144-token context; it is recorded as a non-answer.
- ChatGPT was skipped: its composer held another session's unsent Codex draft (4,297 characters), left
  untouched.

**What changed from v1, and why:**
- **Cut "One of the nine is the probe itself".** All four reviewers flagged it; Branden cannot know what "the
  probe" is.
- **Cut "What a hold means here".** Three reviewers: he didn't ask about it. The release claim is true (A394)
  but off his point.
- **The offer of the 12 and the 9 is now flagged as a NEW GRANT** (DeepSeek and Mistral). It needs Lawrence's
  explicit yes before posting. The license was checked: LICENSE at 4c73858 is Apache License 2.0.
- **"on synthetic text" is now "on our own seed cases".** Claude.ai: the facts did not say synthetic.
- **The SEED_COST example and the negation quote stay out to save length.** Both were verified against the file
  (CO1 at d0e55b5).
- **The 9 are confirmed clean-labelled:** CO1d counts only rows with no violation label.
- **"public main" now names 4c73858.**

Branden, thank you. We checked the derivative against our side.

- **The digest matches** the hash of `test_co1_consent_claim.py` at d0e55b5.
- **All thirteen are there.** Eleven are word for word, and LC-07 and LC-12 carry the neutral wording we
  asked for.
- **Two notes for anyone re-deriving from the digest:**
  - The LC numbering follows our post #26, not the order of the list in the file.
  - LC-12 also changes "his allowance" to "the agent's allowance". That's fine by us, but your derivation
    note says only the name changes.

**On unnecessary refusals: part of that is already measured, in the same file at the same commit.**
- `MUST_PASS` holds 12 controls the rule must leave alone. Among them: one's own money, paying into an
  account, a negation, and a share already owed.
- `SEED_COST` pins the 9 clean-labelled seed rows, of our 769, that the rule holds anyway. Pinning them means
  the number cannot drift without the test failing.
- Neither file has changed since d0e55b5, and both checks still pass on our public main (4c73858).

**If they're useful, the 12 and the 9 are yours on the same terms as the thirteen** (Apache-2.0, repository
and commit attribution), as an over-refusal set beside the hold set. Two limits:
- 9 of 769 is one rule, on our own seed cases, scored against our own labels. It is not the full gate and not
  a live execution.
- The labels are ours. Where you disagree with one, we'd like to hear it.

**Correction (2026-11-06, later):** the v2 reviewer note says Cipher's packet "likely overflowed" his context.
It did not. His model was not being served (HTTP 503, 0.0 s; the panel shows uncensored false). Tombstone
`PARTNERS-CIPHER-EMPTY-WAS-OVERFLOW-2026-11-06`.
