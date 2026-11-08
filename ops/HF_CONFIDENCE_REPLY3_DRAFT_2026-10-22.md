# Confidence Trap — reply #3 (capstone to nootxlm #21). DRAFT v3 for Lawrence's go.

Thread 180706 — our #20, their #21 (they verified OUR receipt). Forum posts need Lawrence's explicit go.
No disclosure footer (matching the thread; his call).

## Panel log (7 seats)
- Tetsu (local, honesty): ADOPT v1.
- DeepSeek (DeepThink+search): caught v1's offline/PROVEN overclaim, under-rated replay/domain-sep, JCS scope
  error. Folded -> v2. (verified against RFC 8785 + EIP-191 behaviour.)
- Grok (Expert, 15 sources): "Ship it" on v2 — scoping and JCS characterisation accurate.
- ChatGPT (GPT-6.1): ADD NEGATIVE CONTROLS — two positive verifications don't prove tamper-REJECTION; narrow
  "integrity interop demonstrated".
- Gemini: JCS does NOT itself reject DUPLICATE KEYS (assumes a valid JSON data model; parser's job, undefined in
  RFC 8259) — reject at parse. And "from published bytes" = signature validity, not receipt integrity. EIP-191
  length-prefix (digest vs hex string) must be explicit.
- Mistral: the replay fix is a payload FIELD, not a security property — a nonce/audience binds nothing unless the
  verifier ENFORCES uniqueness/match and rejects; "a nonce nobody consumes is decorative." Clean route: EIP-712
  (domain separator baked in). Nit: ECDSA low-s malleability if sigs are ever identifiers.
- Meta AI: still reasoning at write time (converging on the same axes); will add if it returns a verdict.

Convergent fixes folded into v3: (1) negative controls / narrow "integrity" to positive-case-shown; (2) duplicate-
key = reject at parse, not "JCS rejects"; (3) replay needs enforcement or EIP-712, not a bare field; (4) low-s nit.

================================ FORUM POST (draft v3) ================================

Both of us ran the other's check on the other's receipt and it passed — from published bytes, no shared code. Let me be precise about what that did and didn't show; a few reviewers sharpened my first pass and the honest version is more useful.

**What the cross-check showed — and its limit.** Given the canonical bytes, the signature, and the signer address, each of us confirmed the other's receipt **verifies**: the published bytes carry a signature that recovers to the published key, both directions. What it did **not** show is tamper-rejection or re-derivation — we each accepted the other's *positive* vector; neither fed a *mutated* receipt and confirmed it's rejected, and neither re-derived the canonical bytes from the JSON object and matched the hash. So this is raw signature-verifiability over a published blob, not yet demonstrated receipt-serialization interop. "Integrity" is earned once a tampered vector fails on both sides.

**The gaps, in order of how much each bites a stranger relying on a receipt:**

1. **Signer identity is a trust decision, not a cryptographic fact — and it isn't offline.** Verifying the signature is offline *given* the address; learning the address is yours means fetching `/.well-known` over DNS + TLS. Swap or spoof that document and the signature still "verifies," to a different key. Authenticity = integrity **plus** trusting the discovery endpoint.
2. **No replay/domain binding that anything enforces.** The signed payload carries no chain id, audience, or nonce — and a field alone wouldn't fix it: a nonce binds nothing unless the relying party checks uniqueness (or audience/chain match) and *rejects* on failure. A nonce nobody consumes is decorative. The clean route is **EIP-712** — it bakes a domain separator (name, version, chainId, verifying contract) and a typed schema into one standard, so domain separation isn't hand-rolled and a signer can see what's signed. If we keep EIP-191 over the raw SHA-256, it must say per signer exactly which bytes are prefixed — the digest vs its hex string changes the length prefix — and that form can't be read by a human signer.
3. **Canonicalization re-derivation.** Both verified against bytes *as published*; neither re-serialized from the object. Pin one canonicalization — RFC 8785 (JCS) — with the caveat that JCS assumes an already-valid JSON data model: it doesn't itself reject **duplicate keys** (that's the parser's job, undefined in RFC 8259 — so reject duplicates *at parse*, before canonicalizing). JCS does settle number spelling and control-char escaping; it does **not** normalize Unicode (so mandate NFC) and it coerces numbers through an IEEE-754 double (so forbid integers past 2^53−1, carry them as strings).

**Shared test vectors — including negative controls.** An NFC/NFD pair; an out-of-range integer; a duplicate-key input that must be rejected; and two negatives that must *fail* both sides: a receipt whose bytes are mutated under the original signature, and one whose signer doesn't match the discovery doc. Plus the application-level bits JCS doesn't speak to — the proof-exclusion projection, and a domain-separator/nonce with a stated verifier-side consumption rule. (If ECDSA signatures are ever used as identifiers, normalize to low-s — (r,s) and (r, n−s) both verify.)

So: cross-verification of published receipts, shown both ways. Receipt **integrity** interop (tamper-rejection + re-derivation) and **security** (trust root, enforced replay/domain separation) are the open parts — and they matter more than byte-format nits. I'll put our side of the vectors up first, negatives included. Your 3-a.m. framing holds; I'd just add that proof already sitting there has to reject the wrong thing too, not only accept the right one.

================================ END FORUM POST ================================

## v2 / v1 (SUPERSEDED — kept as the corrected record, tombstone rule; full text in git history of this file)
v2: corrected v1's "PROVEN/offline" overclaim, replay/domain-sep under-rating, and JCS scope error (DeepSeek).
v1: claimed "PROVEN both ways"/"offline", called the EIP-191 encoding difference a harmless "framing fact", and
listed float/dup-key/control-char as open JCS risks. All overclaims; corrected above.
