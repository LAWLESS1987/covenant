# Federation

**Outside the core, on purpose.** Delete `federation.py` and `peers.txt` and
everything else behaves identically — verified by removing them and re-running
the core's own tests. An instance offline, firewalled, or under sanctions loses
nothing. Federation is something you may do, never something you must.

---

## The question it answers

Two instances, run by people who have no reason to trust each other, want to
know one thing:

> **Do we still mean the same thing by the rules we both claim to follow?**

Every instance publishes a **constitution hash** — one number over the rules
that bind its operator (`docs/CONSTITUTION_ANCHOR.json`). Anyone can fetch
anyone's, and compare, block by block.

```
python federation.py mine     # this instance's hash, to publish
python federation.py check    # read peers.txt and compare
```

Output is one of four words per peer: `SAME CORE`, `DIVERGED` (with the exact
blocks amended, missing or added), `UNREACHABLE`, or nothing at all if you list
no peers.

## What it deliberately is not

**Not a registry.** There is no list anyone maintains. `peers.txt` is yours,
local, and nobody can add to it or be removed from it.

**Not a membership.** Nothing is conferred. There is no status to lose, which
means there is no lever, which means there is nobody who can pull one.

**Not a standard body.** No committee, no version authority, no certification.
Publishing a hash is the whole of participation and there is nobody to ask.

**Not a scoring system.** No compliance rating, no percentage, no ranking. Each
of those would be a way to reward and punish, and whoever defined the metric
would quietly be in charge.

## Why divergence is reported and never punished

A federation that expels members for diverging is a hierarchy in costume, and
whoever decides what counts as divergence is simply the government.

An instance that amends a core rule is **not defective**. It may have found
something the original got wrong — which is the single most valuable thing a
fork can do, and this project's record is built to keep refutations rather than
argue them away. If a fork's amendment is better, the right outcome is that
this instance adopts it, not that the fork is corrected.

What matters is only that the change is **visible**, so that anyone relying on
a shared rule can see when it stopped being shared.

## Forks, not branches

A branch in someone's repository is that person's property. They can rewrite
it, rename it, or delete it. A "governance branch" the owner can erase is a
folder with ceremony — the same flaw as a single-operator network, moved one
layer up.

A **fork** lives on an account its owner controls completely. It cannot be
deleted, rewritten, or overruled from here. That is sovereignty rather than
delegated shelf space.

It also happens to solve the largest problem this project has. `CONSTITUTION.md`
section V names it: *every node is run by one person, and a single-operator
network is not governed, it is owned.* **Every genuine fork is a second
independent operator.** The federation is not a nice addition to governance
here; it is the only route to it that does not run through trusting one man.

## On nations

Adoption will not follow borders. It follows whoever has the problem.

Adapting to a jurisdiction — data protection, liability, evidentiary rules — is
a legal question, and legal questions are answered by lawyers in that
jurisdiction, not by a hash. What this offers a national or institutional
adopter is narrower and more useful than a "national branch": **fork it, amend
what your law requires, publish your hash, and everyone can see exactly which
rules you kept and which you changed.**

No permission is sought and none is granted. A regulator can verify a claim
about a deployment without trusting its operator and without contacting anyone
here. That is the property worth having, and it survives its author.

## Honest limits

- **Verification only helps parties who want to be verified.** Anyone who
  prefers not to be checked simply does not publish, and nothing here can
  compel them. This lowers the cost of cooperation between willing parties; it
  does nothing to the unwilling.
- **A published hash proves what the rules say, not what the code does.** An
  operator can publish an honest constitution and run something else. Pairing
  it with `SUCCESSION_ANCHORS.md` and a reproducible build would narrow that
  gap. Neither is done.
- **`UNREACHABLE` is a fact about the network, not about the peer.** It says
  nothing about their rules and must never be read as though it did. That is
  the same discipline as everywhere else here: an access failure is not an
  adverse finding.
- **This has never run between two genuinely independent instances.** Until it
  does, it is a mechanism that works in test, not a federation.
