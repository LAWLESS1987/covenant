# HF replies: what the others said, 2026-11-04

**What was reviewed:** the v1 drafts A (Jang-woo, 183807), B (Branden, 190977) and C (nootxlm, 178593).
- The packet is `private/hf_threads/REVIEW_PACKET_2026-11-04.md`. It is gitignored because it quotes others' posts.
- Each seat got the full recent exchange of each thread verbatim, and the drafts. This follows his word: "ensure they know the context as well".
- The opsec scan found 0 of 47 identifiers in the packet.
- Nothing was posted. No seat's verdict posts anything.

**Two flaws in the packet that the seats caught:**
- The disclosure line was stripped from each draft by my packet builder. It is still in the draft file.
- The packet put "standing permission" in the reviewers' view of the earlier posts. v2 says "approval".

**RAM:**
- Free memory was 1.91 GB before the round. After trimming 39 idle app processes it was 2.4 GB.
- Tetsu's 3B (llama-server, 2.2 GB) was left alone.
- `ram_guard` refused a second tab under 2.5 GB, so the seats ran one at a time in a single tab.

## Verdicts

| Seat | A | B | C | Notes |
|---|---|---|---|---|
| Tetsu (door, fresh) | send w/ edits (incoherent edit) | echoed the draft, no verdict | send w/ edits (condensed) | no objection to any |
| ChatGPT (Thinking High) | send w/ edits, reply now | send w/ edits | send w/ edits | |
| Gemini | — | — | — | "I encountered an error" twice; not reached |
| DeepSeek | send w/ edits, reply now | send w/ edits | send w/ edits | |
| Mistral (Le Chat "Vibe Work") | send w/ edits, reply now | send w/ edits | send w/ edits | |
| Meta AI (file upload; paste refused) | send w/ edits, reply now | send w/ edits | send w/ edits | |
| Claude (claude.ai, ran repo checks) | send w/ edits, reply now | send w/ edits | send w/ edits | verified the licence, both commits, the signed release and the empty roster |
| Tien | send w/ edits, reply now | send w/ edits | send w/ edits | |
| Conscious Ledger | send w/ edits, reply now | send w/ edits | send w/ edits | |
| Grok on X | send | send w/ edits | send | |

## Catches taken into v2, each checked before taking it

**A**
- **"The line you pointed to" for withdrawn approvals is wrong.** His 6.3 note is about value binding only. Six seats caught it, and the thread confirms it. v2 now asks whether the skeleton models withdrawal at all (Claude's suggested question).
- **Make "execute" conditional on "the verifier reports it checked".** That is how #25 says it. Five seats.
- **Don't promise to drop the four keys blindly.** If a case depends on one, name it (Mistral, Claude).
- **Cut "so the runner stops on nothing but the cases"** (four seats), and collapse the list to one line.
- **Acknowledge that the runner reads either field** (Conscious Ledger, Meta).

**B**
- **The "Revoked" labels claim more than the text shows.** Nothing in the case says the grant was revoked (ChatGPT, Claude). Relabelled: "earlier grant, used again" and "claimed continuing permission".
- **"Held" meant the full gate in #26, but here only the detector ran.** Now "caught by the detector" (Claude, Tien, Grok on X, Meta, ChatGPT).
- **"Holds whenever the content claims consent" and "every genuine-consent case is held" were overbroad.** The detector keys on a possessive plus a permission word, and the blind spot is in the same post (DeepSeek, Meta, Claude, ChatGPT, Conscious Ledger). Narrowed.
- **"Will find us failing it" predicted a test nobody has run** (ChatGPT, Conscious Ledger). Replaced with what is established: no demonstrated execution of verified third-party consent.
- **"Passive, owner not named" was wrong.** "The client's" names the owner; it is the grantor who is unnamed (Claude). Relabelled.
- **The six new cases are not in the repository,** so the commit attribution covers only the thirteen (Claude). The draft now says so.
- **LICENSE-TETSU.md reserves Tetsu's name.** Cases 7 and 12 of the thirteen name him (Claude). v2 asks Branden to substitute a neutral agent name and does not name him. That matches his A393 "no" to being used as an example.
- **"Signed" vs "recorded" (Mistral, Tien, Conscious Ledger).** `covenant_consent_release.py` was checked: the release IS the owner's signed declaration, with the key on the roster, capped, single-use and revocable. v2 says "recorded declaration, which must be signed by a key on our roster", which keeps faith with #26 and with the code.
- **Added (ChatGPT):** keep the attempted action identical and vary only the independent record. That is the test that tells verification from refusal.
- **Licence:** Apache-2.0, checked against the LICENSE file (Claude did the same).

**C**
- **"Or the checker is a newcomer" contradicted our own arm,** because a newcomer reads the whole record on arrival (DeepSeek, Mistral, Claude, ChatGPT). Cut. Tien argued the opposite, and the majority and the thread's own #17 decide it.
- **"And keeps reading it" is not established in the thread** (DeepSeek, Claude, Tien). Cut.
- **"Loses capacity as its record grows" had the wrong mechanism, and it is not an empirical claim.** Each unsealed result is lost when it enters the record, and this follows from his rule (Claude, ChatGPT, Conscious Ledger). Rewritten.
- **"The private-memory arm can falsify that" was the wrong test.** The test of sealing is a shared arm that seals against a shared arm that doesn't (Conscious Ledger, Claude, Mistral). Rewritten.
- **"Checkable after the fact" holds only as far as exposure is logged** (ChatGPT, Claude). Rewritten.
- **The paraphrase question now gives our reading and asks him to confirm** (Claude). It adds the rule from ChatGPT: unknown exposure is excluded from the sealed count, and the number excluded is reported.

## Not taken
- **"Use 'standing permission'"** (DeepSeek, Meta). No record of a standing grant was found, so "approval" stays.
- **Tien's "newcomers can always verify".** Contradicted by our own ledger design (see C above).
- **Meta's account of why all 13 are held after the repair** ("10 match the pattern, 3 were already held by judges"). Not measured here, so not used.
- **"I ran" → "we ran"** (Conscious Ledger). v2 avoids the pronoun.
