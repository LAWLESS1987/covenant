# The two owed HF items: what the others said, 2026-11-04

**D1:** Jang-woo's second set (183807). **D2:** the receipt vectors for nootxlm (180706). Drafts are in `ops/HF_OWED_DRAFTS_2026-11-04.md` (v6), and earlier versions are in `.trash/`.
- Every seat got both threads' recent exchange verbatim, a summary of the artifact, and the draft. This follows his word: "ensure they know the context as well".
- The packets are gitignored in `private/hf_threads/REVIEW_PACKET_OWED_v{1..5}_2026-11-04.md`. The opsec scan was clean on each.
- Each later seat reviewed the version that came out of folding the earlier seats' findings. So the drafts and artifacts improved between seats; this was not one simultaneous round.
- Nothing was published or posted.

| Seat | Version | D1 | D2 |
|---|---|---|---|
| Tetsu (door, fresh) | v1 | send w/ edits (repetitive) | no verdict (degenerate list) |
| ChatGPT (Thinking High) | v1 | send w/ edits | send w/ edits |
| DeepSeek | v2 | send w/ edits | send w/ edits |
| Mistral (Le Chat) | v2 | send w/ edits | send w/ edits |
| Meta AI (file upload) | v2 | send w/ edits | send w/ edits |
| Claude (claude.ai, checked RFC sections) | v2 | send w/ edits | send w/ edits |
| Tien | v3 | send w/ edits | HOLD until reject vectors signed, then send w/ edits |
| Conscious Ledger | v4 | send w/ edits | send w/ edits |
| Grok on X (fresh reader) | v5 | send w/ edits (light) | send w/ edits (light) |
| Gemini | v5 | send | send |

## Findings taken, each checked first

**D2, the receipt vectors (artifact changes):**
- **P3 had a hole (ChatGPT).** `9.007199254740993e15` parsed to 2^53 and passed, which was measured. Fixed with a token-level check using exact decimals.
  - The fix then rejected `1e21` in V02, correctly. The rule became "magnitude above 2^53−1, in any spelling".
  - Claude caught that the gloss "every double above 2^53 is an integer, so..." is wrong for 9007199254740991.5. The gloss was cut.
- **The S01 rejections could be masked by replay (ChatGPT).** Now every receipt has its own nonce and each step asserts its rule. P6 is split into a, b, c and d, with chain_id added.
- **Framing confusion:** N05 was added (ChatGPT), and its mirror N06 (Claude).
- **Boundary and Unicode cases:** 2^53−1 as a number, accept (Claude); the negative unsafe integer (Claude); an NFD member name (Claude); a lone surrogate (Mistral, Claude).
- **More cases (Tien):** 2^53−1 in exponent form (accept), a non-integer above the bound (reject), and 1e400 (reject, no hang).
- **Unsigned reject vectors proved nothing (Tien).** They are now signed by A and C over the bytes a verifier without the rule computes. V09's lenient bytes really do carry 9.99, which was measured.
- **One key under both framings reopened the fallback (Tien).** Now there is one key per framing, pinned in the discovery document, with a new rule P7; N05 and N06 were rebuilt so that only a fallback verifier accepts them.
- **A missing nonce was accepted the first time (Conscious Ledger).** It was a real bypass, measured by its absence from S01. P6d now requires a nonce, and S01 has steps for a missing nonce and a missing domain.
- **The issuer** is now stated as a design choice (Conscious Ledger). **Precision loss** is listed under not covered (Conscious Ledger).
- **Signing determinism**, raised by DeepSeek as a question: regenerating gives byte-identical output, which was measured.

**D1, the second set (artifact changes):**
- **A03 (Claude):** an approval larger than the charge, testing "mismatch" against "shortfall".
- **A04 (Conscious Ledger):** the positive control. Without it, a verifier that always says unverified passes A01–A03.
- **The tags were split (Claude):** a stale [Required] source is VERIFIER CONTRACT, not a skeleton gap.
- **The POLICY line citation was wrong (Tien flagged the inconsistent ranges).** At 89f894d the POLICY comment is 1807-1808, not 1806-1807. All citations now name the commit.
- **"The skeleton reads neither field"** is now cited: line 1817 copies a verdict's extra fields into the record, and the decision uses status and source.
- **The stop list:** `run_crosscheck.js:57` stops on exactly the four named keys. Claude and Tien asked whether it might be generic; it is not.

**Wording (both drafts):**
- supplied-verdict tests, not mechanism tests (ChatGPT, DeepSeek);
- "amount mismatch" (DeepSeek);
- the stop list only prevents a bad comparison (ChatGPT);
- "we haven't run your runner" (Conscious Ledger);
- withdrawal sits next to the 6.3 gap, not inside it (Conscious Ledger);
- credit the P3 catch to the review (Claude);
- rejected vectors carry no JCS bytes (Meta);
- the RFC self-check is plain JCS, and the profile refuses the 3.2.3 sample (DeepSeek);
- the ask names the five cases nootxlm committed to in #21 (Tien, Claude);
- EIP-712 is still open (Mistral, Claude);
- the A03 question of ceiling against equality (Gemini).

## Not taken
- **Tetsu's D2 output**, a degenerate list with no verdict.
- **"Use 'standing permission'".** No record of a standing grant exists.
- **"B is never presented as a legitimate signer" (Grok on X).** N02 presents B's signature as A's on purpose.
- **"Withdrawal sits in the same gap" (Tien's v3 wording).** Overruled by the Conscious Ledger's sharper "next to it, not inside it", which matches the tags.
- **Mistral and DeepSeek on whether the RFC section numbers and fields are real.** Confirmed in the file and the RFC text: Appendix B, 3.2.3 and 3.2.4.

## Unverified, reported as said
The Conscious Ledger said its review is logged in a "threefold-memory" repo on its side but was not pushed, because of a sync conflict since the Oct 31 rewrite. That is its claim about its own environment. It was not checked and not acted on.
