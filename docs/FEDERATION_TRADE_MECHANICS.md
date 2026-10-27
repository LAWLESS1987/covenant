# Trade mechanics for the federation — which parts survive the copy

**Status: DESIGN NOTE. Nothing here is implemented.** His standing rule of
2026-09-09 holds: repair is automatic, but new capability, structure or
rule-meaning waits for group consensus after more nodes exist. Three of the
four mechanics below *are* new structure, and two of them are inert with one
operator whatever we decide. This is written so the argument exists before the
nodes do, not to authorise anything.

Written 2026-09-19 on his proposal: *"we mirror international trade based off
only what works… Take the working mechanics, leave the dysfunction behind."*

---

## What is already here

`federation.py` is deliberately **descriptive only**. Every instance publishes
one constitution hash; this reads other instances' and reports `SAME`,
`AMENDED`, `MISSING`, `UNREACHABLE`. Its header states the commitment plainly:
it *"confers no status, grants no permission, and cannot remove anyone from
anything, because there is nothing to be removed from."* And: *"A federation
that expels members for diverging is a hierarchy wearing a federation's
clothes, and whoever decides what counts as divergence is simply in charge."*

`peers.txt` is the counterparty list, and its header says *"Nobody approves
this list and nobody can add to it."* It currently holds one entry: `self`.

`ops/daily_plan_signers.json` holds two grantees, `phone` and `pc`. **Both are
his.** That number is the binding constraint on everything below.

---

## 1. Bilateral agreements — COMPATIBLE, and mostly already true

Two parties setting terms between themselves needs no centre, no quorum and no
registry, which is why it survives the copy intact. `peers.txt` is already
bilateral by construction: you read whoever *you* chose, and nobody can add to
your list.

What is missing is the *agreement* — a recorded, signed statement that between
these two parties these terms hold, with both signatures over the same bytes,
so neither can later describe it differently. That is small to build and there
is an obvious shape for it: the same signed-document envelope
`covenant_actuator_guide` already uses and the phone already verifies.

**Why it is not built today:** an agreement between two keys held by one
person is a note to self. It becomes real the day there is a second custodian.

## 2. Mutual recognition — THE DANGEROUS ONE, and we already have the scar

The proposal: *"if your system already passed your Witness, some others
automatically accept it."*

**This project has already been refuted on exactly this.** A121: the
conformance root was published as evidence that an independent build, in any
language, sharing none of this code, had performed the computation. Jens
Egholm Pedersen (DTU) refuted it on 2026-09-15 — the root is sha256 over the
expected outputs printed *inside the spec file itself*, so it reproduces in
nine lines with no implementation at all. Passing the Witness proved
publication, not work.

`sentinel_witness/verify_record.py` is the same lesson one level down, in its
own words: *"A gate that says 'I wrote that down' and is never asked to
produce it is not an audit trail; it is a promise."*

So recognition has to be split in two, and only one half is safe to copy:

| | what it means | safe? |
|---|---|---|
| **Recognise a method** | I have read your procedure and can run it myself on your inputs and get your answer | yes — it is re-derivation, not trust |
| **Recognise a verdict** | Your Witness said pass, so I record pass | **no** — this is A121 with extra steps |

Recognising a verdict is precisely the *status* `federation.py` refuses to
confer. The moment my chain's validity depends on your Witness's word, you are
in charge of my chain, and whoever decides what counts as a passing Witness is
simply in charge. That is the hierarchy wearing a federation's clothes.

**The workable form:** recognition is a claim I publish about *myself* — "I
re-derived peer X's result R from their published inputs and got the same
number" — with my own derivation attached. It is evidence anyone can check and
a lever nobody can pull.

## 3. Most Favoured Nation — THE BEST OF THE FOUR, and the only one statable now

MFN is the direct antidote to the power imbalance he wants to skip, and it has
a property the other three do not: **it is a constraint on your own conduct,
not on a counterparty's.** It therefore needs no second operator to be *true*,
only to be *interesting*.

> Any term extended to one peer is extended to every peer.

That is checkable against surfaces that exist today: the signer registry, the
routes each signer may call, the rate they are served at, what the update door
will send them. A guard could enumerate the terms per counterparty and assert
the sets are identical — and, crucially, could be driven both ways, since
granting one peer something a second lacks is easy to construct.

**Its value today is nearly nil and that is fine.** Two counterparties, one
custodian: the invariant is trivially satisfiable and proves almost nothing.
The reason to write it *now* is that an invariant adopted while it is cheap
binds later, when it is expensive and there is a reason to want an exception.
Adopted after the first asymmetry exists, it would be written around it.

## 4. Dispute resolution panels — BLOCKED, and not only by policy

A neutral third-party panel requires a neutral third party. Today there is
one operator, one key custodian, and every node — PC, phone, the three local
nodes — answers to him. **A panel drawn from those is him three times, not a
panel.** This is the one-operator cap the register already names, and no
amount of code removes it.

It is also the mechanic most likely to be built wrong in advance: a panel
specified while only one party exists will encode that party's assumptions
about what a dispute looks like.

---

## The part that does not survive the copy, and it is not the veto

He is right that the veto, the endless negotiation and the power imbalance are
the dysfunction. But the veto is doing one load-bearing job in the original,
and dropping it without replacement breaks MFN specifically.

Under MFN, a term offered to one is owed to all. In a system with a veto, a
party facing a term it cannot bear can block. Remove the veto and the
arithmetic runs the other way: whatever the largest or most permissive party
offers, everyone is now obliged to match, and a small node is conscripted into
terms it cannot sustain.

**The replacement is not the right to block. It is the right to leave.** And
`federation.py` already has that shape by accident of good design — *"there is
nothing to be removed from"* cuts both ways: nothing can expel you, and nothing
can hold you. Written as a rule:

> MFN binds only for as long as a party stays. Exit is unilateral, needs no
> reason, notifies rather than requests, and cannot be refused. No term may be
> written that survives a party's exit.

That is the one addition this design needs that the trade system does not
supply, because in the trade system exit is catastrophic and here it is meant
to be ordinary.

---

## What could honestly be done before a second operator

1. **Write the MFN invariant down** — as a statement in the constitution's
   register, with a guard that enumerates per-counterparty terms and fails on
   asymmetry, driven both ways. Cheap, and it binds before there is a reason
   to want an exception.
2. **Write the exit rule down beside it.** MFN without exit is a trap, and the
   two must arrive together or the first one is dangerous alone.
3. **Nothing else.** Bilateral agreements between two of his own keys are notes
   to self; recognition needs someone else's Witness to recognise; a panel
   needs a third party. Building those now means guessing at the shape of
   problems that do not exist yet, which is how the conformance claim came to
   be written in the first place.

**UNDETERMINED:** whether any outside party wants this. `open-covenant` ships a
token and trading rails and has no policy hook; the one outside reviewer this
project has had arrived to refute a claim, not to federate. Nothing here
should be read as evidence that a counterparty exists.
