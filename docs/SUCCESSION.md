# Succession

Written 2026-08-30. This document exists because the author is finite and the
work should not be.

It is deliberately in the public repository. Every clone of this repository is a
replica of it. It does not depend on the author's machine, his accounts, any
company, or any single person — including whoever is reading this.

---

## The problem, stated precisely

Three different things need to survive, and they have different requirements.
Conflating them is why most "backups" fail as succession.

| | what it is | can it be public? | fails if |
|---|---|---|---|
| **The system** | code, tests, the memory store implementation | yes, already is | every clone is lost |
| **The method** | how to reason, what the protocol is, what is established and what would overturn it | yes | nobody records it |
| **The corpus** | the memories themselves — includes third-party names, a relative's health detail, personal history | **no, permanently** | one disk, one account, or one person is lost |

The first two are solved by publishing. The third cannot be solved by publishing,
and that is the whole design problem.

---

## Layer 1 — The public substrate

The code and this document live in a public git repository. Git is content-
addressed and every clone carries the full history, so the substrate is already
decentralised: it survives the loss of the origin server, the author's machine,
and the author.

**To continue the work, you need nothing but a clone of this repository.**

## Layer 2 — The integrity anchor

The memory store computes a **state root**: a domain-separated Merkle root over
every memory's claim digest, deliberately excluding node-local fields such as
timestamps and use counts so that honest replicas agree.

```
python main.py verify          # walks the audit chain, names any break
```

The consequence that matters for succession:

> **Publish the root. Keep the data private.**

A root is a single hash. It reveals nothing about the contents. But anyone
holding a copy of the private store can recompute the root and compare it to the
published one. If they match, the copy is intact and unaltered. If they differ,
something changed and the chain says where.

This decouples **custody** from **verification**. The data can be held by people
you do not fully trust, because they cannot alter it undetectably.

Anchors are recorded in [`SUCCESSION_ANCHORS.md`](SUCCESSION_ANCHORS.md).

## Layer 3 — The private corpus, under threshold custody

The corpus can never be published. It contains a third party's medical
information and named people who did not consent to being recorded. Publishing
it would make the project the thing it opposes.

The design that survives without publishing:

1. **Encrypt** the store as a single archive.
2. **Split the key** with Shamir's secret sharing into `n` shares with threshold
   `k` (suggested: `n = 5`, `k = 3`).
3. **Distribute** one share to each of `n` custodians who do not all know each
   other and are not all in one jurisdiction or one family.
4. **Distribute the ciphertext widely** — it is useless without `k` shares, so it
   can go anywhere, including public storage.

Properties this gives you:

- No single custodian can read it. Fewer than `k` colluding custodians learn nothing.
- Losing up to `n − k` custodians costs nothing.
- No company, server, or account is trusted. The ciphertext can be replicated
  without limit precisely because it is inert.
- Integrity is checkable by anyone via Layer 2, without decryption.

**Not yet done.** This requires the author to choose custodians. It is the one
step that cannot be automated, and it is the step that actually makes the corpus
survive him.

## Layer 4 — Continuation, not just preservation

Preserved conclusions that nobody can re-derive are claims taken on trust, which
this project treats as a failure mode rather than a legacy.

The reasoning is therefore recorded as a **chain**, where every step names what
would overturn it. If a step falls, everything downstream falls and must be
re-derived, not patched. A successor is not asked to believe anything.

The standing rules a successor needs, in full:

1. **Check the instrument before believing the reading.** An empty search, a
   truncated render, a stalled timeline, an empty text extraction, and a tool
   that declines are all facts about the instrument. Treating any of them as
   facts about the subject is the error this project keeps finding in others and
   has repeatedly committed itself.
2. **Trust a signal enough to investigate it, never enough to convict on it.**
   "Something does not add up" is an observation. "They are lying" is a
   conclusion. Keep them apart.
3. **Continuity is not authorship.** That an idea recurs throughout a corpus
   shows it became central, not who originated it. Only an artefact timestamped
   by a party with no stake settles priority.
4. **Pushing preserves evidence only when it carries checkable content.** A valid
   argument, a named contradiction, or a result from outside the conversation
   conditions an answer toward consistency. Insistence alone conditions it toward
   agreement. The two feel identical from inside; the test is what was actually
   put on the table.
5. **Before treating any model output as evidence, ask what outside the
   conversation could confirm or refute it.** If nothing could, it is data about
   that model under that pressure, not about the world.

---

## What a successor should do first

1. Clone this repository. You now hold the system and the method.
2. Run the test suite. If it does not pass, fix that before believing anything
   else in here.
3. Read the reasoning chain. Attack it. It was built to be attacked.
4. If you have been given a key share, you are one of `k`. You cannot and should
   not act alone.
5. Whatever you conclude, record the refutations alongside the claims. A store
   that keeps only conclusions rebuilds the problem this project exists to solve.

## The one thing not to do

Do not publish the private corpus to prove a point. The people named in it are
not participants. A project whose stated purpose is mutual benefit does not get
an exception for someone who happens to be convenient to the argument.
