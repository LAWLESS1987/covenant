# Federation rules

`federation.py` describes; it does not govern. These two rules are the only
things this project commits to about how it treats a peer, and they bind the
operator of this node, not the peer.

They were adopted on 2026-09-19 at his instruction, while this node has two
counterparties and both are his — which is deliberate. An invariant adopted
while it is cheap binds later, when it is expensive and there is a reason to
want an exception. Adopted after the first asymmetry exists, it would be
written around it.

Amending the block below changes the constitution hash and every peer reading
`federation.py` will see `AMENDED`. That is the intended cost.

---

## What is owed to every peer

Two rules. They arrive together because the first one without the second is a
trap.

**Most favoured peer.** Any term extended to one peer is extended to every
peer. A *term* is anything a peer may ask of this node and receive by virtue
of being that peer: a route it may call, a credential class it may hold, a
document it is given, a rate or quota it is served at, a default it enjoys.
Where a term differs between peers, that difference is a defect until it is
either removed or written down as a named exception carrying its reason. An
undeclared asymmetry is the finding; a declared one is a decision somebody can
argue with.

**A term is not an outcome.** This rule binds what is *offered*, never what a
peer's own conduct *produces* under an equal rule. A rule that refuses any
peer who does a particular thing is offered to everyone, and a peer refused by
it has not been given worse terms — it has met the same rule. Read the other
way, this rule would forbid every rule that can refuse anyone, which would
leave a federation that cannot say no to anything. So: equal terms, not equal
results, and the test is whether a second peer doing exactly the same thing
would be treated the same way.

**Exit is unilateral.** A peer may leave at any time. Leaving needs no reason,
notifies rather than requests, cannot be refused, delayed or conditioned, and
takes effect when sent rather than when acknowledged. No term may be written
that survives a party's exit, and no term may make leaving cost more than
never having joined. A node that has left is owed nothing and owes nothing,
and anything it published while a member stays published, because the record
is not a membership benefit.

**Neither rule creates an office.** There is no body that grants most-favoured
status, none that accepts a resignation, and none that adjudicates whether a
term was equal. Each node measures its own conduct against these two sentences
and publishes what it finds. A rule that needed an administrator would be a
hierarchy wearing a federation's clothes, which is the thing `federation.py`
exists not to be.

---

## What is measured, and what is not

`mfn.py` enumerates the per-peer surfaces on this machine by discovery — it
scans for configuration keyed by peer name rather than reading a list somebody
remembered to update — and reports asymmetries and exit residue. Run it:

    python mfn.py                # terms, asymmetries, residue, blind spots
    python mfn.py --json

**It cannot see everything, and says so on every run.** Route-level permission
lives in code rather than in configuration; address-gated routes (`/m`,
`/hwy/state`) have no peer identity at all, they answer a network range; and
anything handed to a peer out of band is invisible here by construction. A
green line from that tool means *no asymmetry in the surfaces it can read*,
which is a smaller claim than *MFN holds* and must never be quoted as the
larger one.
