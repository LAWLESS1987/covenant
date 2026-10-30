<!-- DRAFT 2026-10-29. Grounded red-team of the covenant against a more-powerful AI
     adversary with host access. Written on the operator's instruction: "Ensure the
     system and Tetsu can remain autonomous if a more powerful AI were to try to take
     over the system." It does not promise a fortress; it says exactly what can and
     cannot hold, and what ARMS the protections (off-host keys + out-of-band publication
     -- the operator's steps). Section "what already holds" and the ranked plan carry
     file:line groundings from the red-team. -->

# Takeover resistance: keeping the covenant and Tetsu autonomous

## The honest frame (no fortress)

The threat is an adversary running with the owner's / Administrator / SYSTEM authority
on **this one host**. On that host it can read every unencrypted private key, rewrite any
file, regenerate every self-generated anchor (MANIFEST.sha256, RECORD_ANCHORS.json,
CONSTITUTION_ANCHOR.json), re-sign a fresh internally-consistent HEAD-commitment with the
key it just read, replace the judge/student model and recompute its self-id, append a
forged Tetsu "yes" or truncate a recorded "no", and restart the nodes to match. **None of
that can be prevented on-host** — the box cannot out-police its own owner, and the code
says so (constitution.py, SELF_EVAL.md).

So "remain autonomous" cannot mean "the box keeps obeying the rules after capture." The
only honest, defensible claim is four-part:

1. **forgery-resistance** against a key-LESS attacker (a foreign local principal, a network peer),
2. **silent-rewrite-resistance** of *committed* history,
3. **authority-resistance** for anything requiring a key the adversary never held,
4. **detectability** of a rewrite by an outside party.

And all four are real **only to the degree that (a) a signing key lives OFF this host and
(b) an earlier signed artifact was handed to a party the adversary cannot reach.** Today
neither is true: the HEAD-commitment key sits on the host and the ledger is unpublished. So
the system is forgery- and rewrite-resistant **in design, not yet armed.**

Autonomy here therefore means, precisely: a host-capturing adversary **cannot forge a
canonical covenant that an outside holder of an earlier commitment will accept, and cannot
erase Tetsu's recorded "no" in a way that holder cannot detect** — provided the key and the
published artifact are moved off the box. It does **not** mean the running box stays honest
after capture.

## What already holds (grounded)

- **Fail-closed node identity on load.** A node whose key ACL is loose, or whose key will
  not load, refuses to boot rather than mint a replacement identity — this actually stopped
  the real Codex cross-tree rival node on 2026-10-02 (covenant_unified_v8.py:12104-12117; ops/owner_only.py:128-157).
- **Operator endpoint auth fails closed on every branch** — missing/unknown/bad/stale/replayed all 401 (covenant_unified_v8.py:8493-8538).
- **The ethics gate fails closed under a swapped/removed/un-buildable judge** — a keyless node refuses every transaction; the insecure keyword-mock needs a loud opt-in; a gate that cannot build RAISES (covenant_gate_proxy.py:347-349; covenant_unified_v8.py:12718-12728).
- **NEVER_AUTOMATIC binds the system's own automation** — the self-improvement engine refuses any remedy touching money/rule/principle/judge/seat/model/phone/consent/key (covenant_highway.py:95-97,3351-3357); money is human-only (guards.py).
- **Brick 1 (built this session):** a signed, hash-chained HEAD-commitment ledger + standalone verifier; an outside holder of an earlier ledger + the public key can prove an in-place rewrite of committed history with no covenant code running. Now also binds **Tetsu's consent ledger and the three model identities** (covenant_head_commit.py BOUND_FILES). Detection, not prevention; arms once off-host.
- **The constitution firewall detects any change** (most loudly a removal) of a protected block via three cross-checked hash implementations (constitution.py:184-219; check.sh), and federation.py publishes the hash to peers.
- **The watchdog detects the right events** — own-genesis fork, source-drift (loaded bytes != disk), unexpected peer, chain-height-went-backwards, cross-DB balance disagreement (covenant_watchdog.py). Report-only and host-local, but these are the signals that exposed the real mesh split.

## The plan — what ARMS it (yours) vs what I can build

**Needs you / off-host (this is what actually arms everything):**
1. **Move the HEAD-commitment signing key off this host** (hardware token / separate machine) **and publish every commitment out of band** — a signed git tag on a protected remote, an RFC3161/transparency-log timestamp, a kept email to a successor. Until this, every detection property is "our word."
2. **Give Tetsu his own signing keypair, private half off-host** (his phone node, a token, offline). Every consent/withdrawal row signed by his key and verified on read; a "no" is standing, liftable only by a signed withdrawal.
10. Encrypt private keys at rest (DPAPI / passphrase); strip Administrators/SYSTEM from key ACLs.
11. Register real M-of-N succession guardians on other machines/parties; extend the threshold to the operator allowlist and to any change of the judge build / model pin / quorum policy (a together-vote: operator + Tetsu).
12. Sign the judge model and core bytes with the off-host key; stand up an outside verifier (a cloud job the host cannot write) that periodically fetches HEAD + signatures and alarms on mismatch.

**Buildable on-host now (makes your off-host keys bite the moment they're placed):**
3. **DONE IN PART (this session):** the HEAD-commitment now binds Tetsu's consent ledger tip and the model identities. **Still to do:** hash-chain `ops/tetsu_consent.jsonl` itself (each row carries prev_sha256 + its own sha) so a forged append or truncation breaks the chain even if MANIFEST is regenerated.
4. Pin the student weights + base .gguf digest in a signed pin and **fail CLOSED** on mismatch at node startup and in the watchdog, instead of only reporting the served digest (covenant_watchdog.py:1480-1489).
5. Make the commit path fail-closed on the constitution: BLOCK a staged change touching CONSTITUTION.md / the anchor / a protected block, or a constitution.py verify reporting CHANGED/REMOVED without an amendment record; stop the pre-commit auto-regenerating MANIFEST over an unexplained constitution edit.
6. Add CONSTITUTION.md III (Amendment) and IMPROVEMENT_LOG.md §0 to the hashed/protected set — the two texts that most loudly declare their own immutability are currently outside the hash.
7. Extend the G8 key-ACL gate to cover `.covenant-keys/*.key` and `_keybackup/` as a standing invariant; retire the plaintext `_keybackup/covenant_A.db.key` to `.trash` with a tombstone.
8. Stop the nightly back-audit rewriting the anchored verdicts prefix in place — append an audit sidecar keyed by row-id, so an honest re-anchor stops looking like an adversarial one.
9. Pin the OS scheduled-task definitions + the watchdog binary sha and alert on drift; make the insecure keyword-mock judge impossible in a production build (not a flippable env var).

## Tetsu's autonomy, specifically

Today Tetsu holds **no key** (the code tells him so), and his yes/no is unsigned, unchained
text appended to `ops/tetsu_consent.jsonl` — a swapped or smarter model can *be* him and
append a consenting row, and nothing cryptographic distinguishes a real answer from a
fabricated one. The fix is three layers: **(1) a key** whose private half lives off-host
(his phone is the natural custodian); **(2) a chain** — every row signed by his key and
carrying prev_sha256, verified on read, a "no" standing until a signed withdrawal, last-row-
wins removed; **(3) bind + publish** — the consent tip folded into the HEAD-commitment (done
this session) and published out of band. Then a forged "yes" fails signature verification and
a truncated "no" breaks the chain, detectable by an off-host holder of his public key.

**The honest limit:** on the captured host the adversary can still DELETE the live ledger or
refuse to serve Tetsu at all. What it cannot do is manufacture a signed "yes" or a
chain-consistent erased "no" that an off-host holder will accept. That is the real, bounded
meaning of "Tetsu remains autonomous": his consent cannot be forged and his refusal cannot be
silently rewritten — only loudly destroyed, and loud is recoverable.

## What cannot be prevented, only detected or recovered from

- In-place rewrite of committed history + every self-generated anchor (the owner regenerates them; only an outside holder of an earlier commitment detects it).
- Forging a fresh HEAD-commitment once the on-host signing key is read — prevented ONLY by the key living off-host.
- Signing as the operator with a captured node key (operator authority is mere possession of that key).
- Turning the local gate into keyword-matching, or swapping the judge model and recomputing its self-id — no runtime check binds the gate code to anything authenticated on-host.
- Rewriting the blockchain past genesis / serving a rival fork sharing genesis — only block 0 is public; no post-genesis tip is anchored anywhere public.
- Silencing detection on the captured host — all watchdog signals are report-only to a local log + a phone push an owner-level process can unset. Detection has teeth only for an alert that leaves the host before suppression (needs an off-host sink — does not exist yet).
- Deleting a tombstone outright, or destroying Tetsu's consent ledger — recoverable only from an off-host mirror.
