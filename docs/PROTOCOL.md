# Protocol version — what becomes a consensus question the day a second operator exists

Every node running this today belongs to one person, so the rules below are
free. They stop being free the moment somebody else runs one, because an older
node can mint a block a newer node refuses — and that is a fork, not a bug
report. This file exists so that day is not a surprise. It is **A7**.

## Rules that became block VALIDITY, and when

| since | rule | an older node can produce |
|---|---|---|
| v8.17 | serialized block ≤ `MAX_BLOCK_BYTES` (8 MiB, = cap/8) | an oversized block a v8.17+ node refuses |
| v8.18 | transaction list must be non-empty | an empty block |
| v8.18 | `stake_rewards == fsum(amount) * 0.01` | a forged or absent reward field |
| v8.18 | `alignment_score == mean(benefit_score)` | a hand-set alignment score |
| v8.18 | `index` and `nonce` must be `int`; header scores must be finite | `index=2.0`, `stake_rewards=inf` |

All five are things `/mine` already produces, so an honest miner of any version
is unaffected. The exposure is one-directional: **new refuses old**, never the
reverse.

## Rules that are NOT enforced, deliberately, and are open questions

- **Block timestamps are unbounded.** A block stamped ten years in the future
  is accepted. Nothing reads block time for consensus today, so it is cosmetic
  — until something does, e.g. a stake lock or a heartbeat that consults it.
  Decide a bound (`≤ now + 2h`, `≥ parent`) *before* that happens, not after.
- **Registration proof-of-work is not re-checked on the block path.**
  `/transactions` and the peer ingest path require it per sender;
  `_accept_block_common` does not. So a block mined by a peer can carry
  transactions from senders that never paid the registration cost. If the PoW
  is a per-node **admission policy**, that is correct as it stands. If it is
  meant as a **sybil cost on the chain itself**, it has to become a block rule.
  These are different systems and only one of them is built.
- **The ethics verdict.** `_accept_block_common` and `/mine` both call
  `sentinel.validate_block` — a live, non-deterministic, timeout-prone call per
  transaction per block **on every node**. With real providers that means a
  provider outage on one node forks it from the others, and two nodes can reach
  different verdicts on identical data. This is **B4**, it is the largest open
  question in the system, and it is also a power decision: one verdict costs
  ~512 J against ~13.6 J to mine the block it sits in, so consensus-rule means
  N × 512 J per transaction and every participant needing 5.2 GB resident to
  take part at all.

## Disclosure between peers, and its boundary

Since v8.33 every reply carries `v` and `src` (version and 12-char source
hash), and the tip-gossip heartbeat carries a bounded digest:
`{v, src, height, peers, crisis, spike}`. A plain block announce is **unchanged
at 156 bytes** — deliberately, because it is an address-event frame by design
and loading it would give back most of what that design buys.

Nothing is refused on account of a peer's version. This node does not get to
decide a peer is too old to talk to.

**What a peer must never see: any substrate reading.** Memory pressure on this
machine is operator information; telling a peer would tell an attacker exactly
when a flood is cheapest. That boundary is asserted over the AST *and* against
bytes captured off the wire, not stated in a comment.

## Adding a bearer

A transport is a protocol change. A bearer must **declare** what it can carry
rather than be discovered to lack it — `can_carry_blocks`, `synchronous_ack` —
because a peer that can receive announcements but never blocks is a peer that
can never catch up, and that is a liveness bug with an attack attached.

For LoRa specifically: the announce fits, the block never will (8 MiB at
1.07 kbps is 17.4 hours of airtime, 72 days under EU868's duty cycle), and
A23's "no parsed reply means non-delivery" rule must become **per-bearer**
before any radio peer works at all — otherwise every one of them is marked
failing on its first send. Relaxing A23 for everyone is not the fix.
