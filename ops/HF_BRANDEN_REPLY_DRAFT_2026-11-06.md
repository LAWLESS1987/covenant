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
