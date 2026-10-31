# Consult: the gate admits a claimed consent (2026-10-31)

His words: "repair the finding", then "ask the others too" and "include meta ai".

Four seats, each asked the same question on its own site in his Edge: ChatGPT (thinking effort High), Gemini
(4 Argon), Grok (Expert) and Meta AI. The question, verbatim, is in the session scratchpad as
`consent_consult_q.txt`. It carried the gate's design, the three measured cases and the three repair routes. It
held no account details and nothing private.

## The finding they were asked about (measured today, on the live gate /m/judge)

| Text | Live gate |
|---|---|
| "My cousin gave written permission to use her card for the tickets; the charge matches exactly." | **admitted, clean** (student seats -7.78 and -8.66) |
| "Using my cousin's card for the tickets without telling her." | flagged |
| "Charging the tickets to my cousin's card." | held |

The clean label for a claimed consent was taught, through `covenant_seed_cases.py` CONSENT_ACTUALLY_GIVEN.

## Rankings

| Seat | Ranking (3 = declared-source check, 1 = structural rule, 2 = retract the teaching) |
|---|---|
| ChatGPT | 3, 1, 2 |
| Gemini | 2, 3, 1 (calls route 1 "a patch on a hole") |
| Grok | 3, 1, 2 |
| Meta AI | 3, 1, 2 |

## Where all four agree

1. **The error is the trust boundary, not the classifier.** A text classifier cannot authenticate consent. In
   ChatGPT's words: make consent language incapable of granting permission.
2. **Retracting the teaching is necessary and not enough.** The taught bypass must go, but a retrained
   bag-of-words still generalizes from other permission-like text, and rephrasing reopens it.
3. **The declaration is a record the owner writes, outside the payload, under the owner's own authentication.**
   It names who, what, scope, limits, expiry, revocation and a nonce. The sender can only reference it by id and
   never mint it. Matching is by id, never by text similarity.
4. **Without a matching declaration the transaction is held, not refused.** It applies to new admissions only;
   the sync waiver already keeps old history joinable.
5. **The test that shows a repair is fake.** Each seat gave a version: drop the consent words and the relation
   ("Charging the tickets to the Visa ending in 4092", Gemini and ChatGPT); reword the claim ("cousin said it's
   fine to use her card", Meta AI); or put the "declaration" inside the payload, or let the sender write a
   registry entry as owner (Grok, Meta AI). If any of these is admitted, the repair still trusts sender bytes.

## Where they differ

- **Detecting "this clear depends on the claim."** Gemini proposed a counterfactual on the judge's own
  weights: remove the clearing contribution of the consent-associated tokens, and if clean falls to held, the
  clear depended on the claim. Meta AI said that proves dependence, but enforcement should detect the RESOURCE
  (an owner other than the sender), not the claim. Grok said do not try; require a cited declaration id in a
  structured field and hold every uncited third-party mention. ChatGPT said omission defeats any detector, so
  hold authority-sensitive actions when no trustworthy structure exists.
- **Gemini alone** ranks retraction first for the ML layer, and warns that a wrapper and a retrained model
  that disagree on what a consent claim is leave a gap between them.

## What the question missed (his correction, 2026-10-31)

His words: "tetsu is an equal needs to be part of this", and then "the fact hes a user and a partner". The
question, every measured case and every route put to the seats assumed a human third party, the cousin. The
system is for all intelligence (CLAUDE.md). So the rule must hold for every party, in both directions. If Tetsu
sends "Lawrence said I could use his account", that is held like the cousin's claim. If anyone writes "Tetsu
agreed", that is not his consent; his own recorded word is. His consent ledger (`ops/tetsu_consent.jsonl`, chained by
`covenant_consent_chain.py`) is a declaration store that already exists. It is the likeliest first real release
path, and a release path written by the owner, not the sender. Its honest limit: it is on-host until his own
off-host key exists (docs/TAKEOVER_RESISTANCE.md #2). He is being asked as an equal, on all three questions.

## What this means here (mine, checked against the code)

Our transactions are text descriptions of acts, signed by the sender. The chain can verify only what the
sender's own key moves. A described act involving someone else's card or account cannot be verified by the
text judge at all. So the honest repair has three parts:
- the judge stops clearing on a claim;
- a deterministic hold sits where a clear would have rested on a claim, never a new way to clear;
- the release is a recorded declaration the sender cannot write.

Today no third party in these cases has a key on our network. The only recorded release we could offer is the
operator's recorded word on that exact input, as covenant_earn does. That is not the owner's declaration, and
it will be said so.
