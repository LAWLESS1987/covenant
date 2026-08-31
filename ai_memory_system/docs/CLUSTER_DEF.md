# Nodes D, E, F — the memory layer's quorum

The chain runs A (5000), B (5020), C (5060) with a watchdog above them and a
guard above that. This is the same shape one layer down, for memory:

| | port | role |
|---|---|---|
| **D** | 5100 | memory node |
| **E** | 5120 | memory node |
| **F** | 5140 | memory node |
| memory watchdog | — | polls all three, revives dead ones, **never** repairs a split |

Quorum is **2 of 3**, a constant rather than `len(NODES)//2+1`: a quorum that
follows the node count becomes 1-of-1 the moment somebody runs a single node
for convenience, and a one-node quorum is a spelling of "no quorum".

---

## The consensus token, and the claim that was wrong first

The first version used each node's **audit chain head**, reasoning that
replicas accepting the same writes in the same order must hash identically.

Three real nodes were then given **one identical write** and produced **three
different heads**:

    state roots: D=… E=… F=…      (identical, after the fix)
    chain heads: 56acc421753a / 118f2888b5a7 / b18139610e24

Every ledger line carries `"at": _now()`, so the bytes differ by microseconds
per node and the chain commits to them. The head fingerprints one node's log
*including when it wrote* — exactly right for local tamper-evidence, useless
for agreement. The claim survived writing, review and a confident docstring.
It died the first time three nodes were actually run.

**What nodes compare instead: `state_root()`** — a domain-separated Merkle
root (`0x00` leaf, `0x01` internal, odd nodes carried not duplicated, per
CVE-2012-2459) over the **sorted set** of `(name, claim_digest)` pairs.

Three properties, each load-bearing:

- **Untimed** — no clock, nothing node-local, so honest replicas match exactly.
- **State, not sequence** — two nodes that accepted the same memories in
  opposite orders *hold* the same memories and agree. A sequence token would
  call ordinary concurrent traffic a split, and an alarm that fires on normal
  operation is one nobody keeps. Pinned by test **Q1**.
- **Content-sensitive** — edit one body on one node and that node's root moves
  alone. Pinned by **Q4**.

## Two digests, because there are two questions

| | covers | answers |
|---|---|---|
| `content_digest()` | claim **+ `created`** | did *this file* change since *this node* wrote it? |
| `claim_digest()` | claim only | do *two nodes* hold the same memory? |

`claim_digest` drops `created`, `uses`, `last_used`, `tier`, `review`,
`review_by`. It keeps name, description, body, type, agent and
**`superseded_by`** — a node that thinks a memory is superseded and one that
does not genuinely disagree, and that must surface.

Dropping `created` was forced by measurement, not taste: it is the taking
node's wall-clock, so a root built on `content_digest` split three ways on
honest replication — the same contamination as the chain head, one level down,
found the same way. Pinned by **Q3**.

**Known gap, recorded rather than hidden.** Because `review` is excluded, a
node holding an *unreviewed* copy of a memory that other nodes reviewed still
agrees on the root. That divergence is real and is visible only in each node's
own report. Surfacing it separately is open work.

---

## What this is, and what it is not

**Is:** replicated write plus divergence detection.

**Is not:** Raft, Paxos, Byzantine fault tolerance, or partition-tolerant
linearizability. No leader election, no log repair, no rollback of a write that
reached one node and not the others.

What it does give — the property that was actually asked for:

- **No single node can be quietly altered.** Edit a memory on D and D's root
  moves alone; E and F still hold the record. One machine cannot sway it.
- **A write that misses quorum is reported UNCOMMITTED**, with the node that
  took it named. There is no rollback, so the operator repairs a *known*
  inconsistency instead of discovering an unknown one. Pretending to undo what
  cannot be undone would be worse than saying where it landed.
- **Every node self-verifies both ways** — chain *and* content — so a node
  lying about its own history is visible without trusting its summary. A node
  failing its own self-check is excluded from the agreement count: "two nodes
  agree" is a lie if one of them cannot verify its own files (**Q8**).

## The watchdog will not heal a split

It revives a node that is **dead**. It refuses to repair one that
**disagrees**, and this is a design commitment, not an omission.

Healing a split means choosing which history is true and overwriting the
others. That is auto-resolution of a contradiction — precisely what
`reconcile()` refuses to do to two *memories*. Doing it to three *nodes*,
unattended, at 3am, with no record of what the losing nodes held, is the same
sin at a larger scale. So a split is reported with **both roots named**, and
the operator decides. Pinned by **Q10**, and **Q11** pins that a split
accompanied by a dead node is *still* not repaired — restarting F would look
like action while leaving the disagreement standing.

A restart is different: a process that is not running holds no opinion, and
starting it back up destroys nothing (**Q12**). Inside the cooldown it holds
instead, because a restart loop is worse than a down node (**Q13**).

---

## Operational caveat: write through the cluster, not to a node

`reconcile()` is **order-dependent** — whichever of two overlapping memories
arrives second supersedes the first. Measured directly:

    node D:  gam superseded_by del
    node E:  del superseded_by gam      <- opposite
    node F:  gam superseded_by del

Three nodes given the same two overlapping memories in different orders held
**opposite supersede relationships**, and the cluster correctly reported
`split`. That is the system working: it surfaced a genuine disagreement rather
than hiding it.

The consequence is operational. Writes go through `MemoryCluster.put()`, which
sends to all three in one order. Writing overlapping content directly to
individual nodes will split the cluster, legitimately.

## Running it

    python memory_watchdog.py --status          # report only, never acts
    python memory_watchdog.py --once            # one pass
    python memory_watchdog.py                   # supervise

`--status` exits 0 on `agree`/`degraded` and 1 otherwise, so it drops into a
cron or a health check without parsing anything.

Every branch of `assess()` and `decide()` is a pure function over reports and
is exercised in `test_memory_system.py` (**Q5**–**Q13**) with no ports, no
processes and no sleeping. A supervisor that can only be tested by breaking a
live deployment is a supervisor nobody tests.
