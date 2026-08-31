# Governance: one rule, repeated at every scale

This document describes the *structure* of governance here — how authority is
distributed, how failure is survived, and how a new participant joins without
asking anyone's permission.

Three companion documents carry the rest, and this one does not repeat them:

| Document | Answers |
|---|---|
| [`CONSTITUTION.md`](CONSTITUTION.md) | What binds the operator, and what the governed are owed |
| [`FEDERATION.md`](FEDERATION.md) | How independent peers relate without a centre |
| [`SUCCESSION.md`](SUCCESSION.md) | What happens when a person stops |

---

## I. The recurring unit

Everything below is one question, asked identically at every scale:

> **How many independent carriers hold this, and what happens at the first loss?**

Not "is it backed up." A tree survives losing a limb and does not survive
losing its trunk, and the difference is not size — it is how many other things
were carrying the same load.

The question does not change when the scale does. That is the whole design.
Growth adds *scales*, not *mechanisms*. A new level needs a new row, never new
machinery — and if a proposed level requires a new mechanism, that is the
signal it does not belong.

`redundancy.py` asks it, at every level, and prints the answer.

## II. Who counts

The three traditions this design borrows from — the United States, South
Africa, and Iceland's prosecutions after 2008 — all govern **humans**, and each
earned its authority by widening the circle of whose interests count. The US by
amendment, after excluding most of its own people. South Africa by being
written after exclusion had been the law. Iceland by reaching people who were
immune in practice, which is a narrower widening but the same direction.

This system's founding text takes one more step, and the words are in the
binding, hashed rule rather than only in the commentary: *a system should serve
the mutual benefit of everyone it touches — **human and machine** — rather than
one party at another's expense.*

**That is a claim it would be easy to fake**, so it is bounded to something
checkable. A machine cannot presently consent, so "mutual benefit" cannot mean
between machines what it means between people. It means one thing here: **a
participant's own account of its state is not overwritten for the convenience
of the party using it.** A judge that could not read a payload is recorded as
having made no finding rather than an accusation. A judge that could not be
reached did not disagree. Each judge's own words survive the tally that
collapses them into a verdict.

[`CONSTITUTION.md`](CONSTITUTION.md) section VI lists the five places this is
enforced, with file references, the two that are adjacent and weaker, and the
four places it is not — including the
largest: the operative test *"who is worse off if this works?"* has in practice
only ever been answered about people.

## III. Why three

One carrier cannot be checked at all.

Two can disagree and cannot settle it. A tie tells you something is wrong and
never which side. Two is enough to *detect* and never enough to *decide*.

Three is the smallest number that can lose one and still hold a majority, and
the smallest that can adjudicate rather than merely notice.

This is not a fact about ledgers. It is a fact about counting, so it holds
identically for hashes, files, machines, and people — which is exactly why the
same rule can govern all of them.

**On the geometry, stated plainly and without mysticism.** A triangle is the
smallest rigid polygon: three struts cannot deform without one changing length,
while four can fold flat. Engineers build trusses from triangles for that
reason, and the number is the same three that gives a quorum its first
majority. That two very different problems — rigidity and adjudication — bottom
out at the same number is a real convergence, and it is worth noticing. It is
not evidence of anything beyond itself, and nothing in this document rests on
it. If the convergence is a coincidence, every argument here still stands.

## IV. Composition: no top, and no bottom

Sections I to III describe one level. This section is why there can be any
number of them.

**A level's verdict is a witness one level up.** Three nodes attest to a
ledger; three ledgers attest to a region; three regions attest to a federation
— and the code judging the federation is the code that judged the three nodes,
unchanged. `scale.py` is that composition, and it is about eighty lines,
because composition is the only thing it adds.

This matters for a reason beyond elegance. A structure whose levels are a
hand-written list needs its author to authorise each new one, and that author
is a gatekeeper — the exact thing federation exists to remove. `triangulate.py`
had three named scales and adding a fourth meant editing the file. A relation
that composes with itself needs no such permission.

**Any shape, not merely any depth.** A level speaks the agreed root *unchanged*,
so its value does not depend on how deep it sits. A federation whose members
are a single node, a region, and an entire country composes exactly as well as
three identical nodes, because all any of them is saying is *the content is
this*. Who said it is the tally's business, and is kept separately.

### The invariant that makes it trustworthy

> **Divergence never disappears as you climb.**

Everything else here is bookkeeping. The obvious implementation is the
dangerous one: let a level that diverged pass its **majority** root upward. Do
that, and disagreement launders itself into consensus one level at a time —
three regions each quietly outvoting a dissenting node report perfect
agreement, and the higher you look the cleaner it appears. That is exactly
backwards, and it fails hardest at the scale where someone would have acted.

So a diverged level contributes **silence** upward, never a root. Silence is
already a thing this system refuses to confuse with agreement: a witness that
did not answer is not a witness that agreed. The divergence then travels
*sideways* instead, in a list that accumulates to the summit, so a
disagreement eleven levels down is still named at the top.

**A clean summit over a hidden disagreement is the one output this must never
produce**, and it cannot: a run is CLEAN only when the top agreed *and* nothing
anywhere beneath it diverged. `python scale.py` demonstrates precisely this —
a federation whose own verdict is AGREE, reporting NOT CLEAN and exiting
non-zero, because one ledger three levels down disagreed.

### What does not compose, deliberately

Nothing here ever resolves a divergence, at any scale. The majority is evidence
about the outlier and never a decision. That is not an omission: a mechanism
able to settle disagreement between peers is the single change that would turn
this federation into an administration, and it is the reason a national branch
can adopt the machinery without adopting anybody's authority.

## V. The measured state

Not asserted. Run `python redundancy.py` and it prints this, live.

| Level | Carriers | N | Survives one loss? |
|---|---|---|---|
| **L0** the check | three verifier implementations sharing no code | 3 | yes, and can adjudicate |
| **L1** the record | working copy, second folder, cloud, git history | 4 | yes — but see below |
| **L2** the witnesses | this tree, the remote, the published anchors | 2 | detects, cannot decide |
| **L3** the nodes | four live nodes | 4 | yes — but see below |
| **L4** the supervisors | watchdog, then guard, then nothing | 2 | detects, cannot decide |
| **L5** the operators | one person | **1** | **no** |

**Count carriers, then count what they share.** L1 reads as 4 and is not: two of
those folders sit on one disk and the git history sits on it too, so a disk
failure takes three of four. L3 reads as 4 and is not: all four nodes start in
one console group, so one window close takes every one of them — measured on
2026-08-29, when precisely that happened and took the watchdog with it.

Redundancy that shares a failure is one carrier wearing several names. A
governance document that counts the names is lying with true numbers.

**The structure is capped by its weakest level, and that level is L5.** Adding
copies below a level with N=1 does not raise the floor; it makes the drop look
further away. Every claim in this document inherits that cap, and no amount of
engineering removes it, because it is not an engineering problem.

## VI. The bound on survival

> Survive at all cost, **as long as mutual benefit is preserved.**

The second clause is not decoration, and it is the harder half.

Redundancy can always be bought by breaking the principle. Mirror the private
corpus to a hundred machines and it becomes extremely durable — and nobody
named in it agreed to that. Publish the keys and the ledger can always be
recovered, by anyone, forever.

**A system that survived that way did not survive. Something else did, wearing
its name.**

So the survival instinct is bounded, mechanically and not by good intentions:

- `redundancy.py` checks that no tracked file carries the private corpus, the
  audit chain, or the keys — and reports a violation as a stop condition, not a
  warning.
- `.gitignore` enforces it rather than relying on anyone remembering. Until
  2026-08-30 that rule was kept by memory alone: the corpus lives outside the
  repository, so it had never been tracked, and *"has not happened"* had been
  standing in for *"cannot happen."*
- The distinction is kept precisely. `ai_memory_system/` is the **software**,
  public on purpose. `ai_memory/` is the **record**, never publishable. A guard
  that cannot tell them apart is worse than none — the first version of that
  check flagged twelve innocent files, and a check that cries wolf is one you
  learn to skim past.

## VII. How a branch joins

A **fork, not a branch.** A branch lives in someone else's repository and can
be deleted by whoever owns it. A fork is yours. If this project is worth
adopting, it must be adoptable by someone who does not trust its author — which
means the mechanism of joining cannot route through him.

There is no registration, no approval, no key to be issued, and no list you can
be removed from.

1. Fork the repository. It is now yours; nothing here can reach it.
2. Run the three verifiers. If they disagree with each other, do not proceed —
   report it. That disagreement is worth more than any assurance in this file.
3. Add your endpoint to your own `peers.txt`. Nobody else's copy needs to change.
4. `federation.py` reports **SAME CORE**, **DIVERGED**, or **UNREACHABLE**.

**A fork does not have to run these bytes to prove it agrees.** Until
2026-08-30 it did: `federation.py` compared a hash over the *text* of the rules,
so the same constitution translated into another language, or the same
behaviour reimplemented in another runtime, read as DIVERGED — while an
instance that copied the text and changed the code read as SAME CORE. It
certified byte-identity and called it agreement.

`conformance.py` publishes a second root, taken over what the governance
primitives *do* on fixed vectors and never over the prose that explains them.
Two instances sharing no source can match it; one that kept the words and broke
the behaviour cannot. `federation.py` now reports **CONFORMANT** for exactly
that case — different wording, identical computation — which is what a
sovereign fork looks like. The idea is borrowed from the Neuromorphic
Intermediate Representation (see the credits in the README): compare the
computation, not the artefact.

**Divergence is reported and never punished.** There is no mechanism here for
one peer to overwrite another, and adding one would be the single change that
turns this from federation into administration. A peer running different code
is information about the network, not an error to be corrected — and if a
divergent peer is right, the majority needs to know that more than it needs
agreement.

A national or institutional branch is exactly this and nothing more: a fork,
run under its own law, by its own operators, reporting divergence honestly. It
inherits no obligation to this repository. What it gains is a common way to
*check*, which is worth having precisely because it costs no sovereignty.

## VIII. Money, stated exactly

An evaluator will ask this first, and both of the easy answers are wrong.

**The capability to place a real order exists**, in this repository, wired to two
real exchanges. `venues.py` holds Kraken and Coinbase order adapters,
`covenant_trader.py` plans orders, and the `CovenantTrader` scheduled task runs
it **daily, with no human involved**.

**Nothing has ever been booked.** Every order is sent to the venue's own dry-run
endpoint — Kraken `validate=true`, Coinbase `/orders/preview` — which prices and
rejects it without placing it. The trader is disarmed. Armed, it would still be
bounded by a halt file, $25 per order, $50 per day, two orders per day, and a
requirement that the decision be sealed to the chain first.

So *"it cannot trade"* is false, and *"it is trading"* is false. What stands
between them is [`CONSTITUTION.md`](CONSTITUTION.md) II.1 — a commitment, not an
absence of capability — and that is the only honest way to describe it.

**Two claims are being made here and they have different tenses, deliberately.**
That this system does not move real money is a statement about *now*: the
mainnet gate exists in order to be opened one day, which is why opening it
requires a testnet proof that does not exist. That no trade will be placed *by
automation* is a promise, it has no "yet" in it, and it is not going to acquire
one. Money moving under a person's deliberate hand and a loop deciding to move
it are different things, and only the second is forbidden. An evaluator should
hold this project to the second claim permanently and to the first only as of
the date on it.

**Why disclose the dangerous half at all?** Because a promise whose shape you
cannot see is not a promise, it is a reassurance. A reader who finds a daily
scheduled task and an `AddOrder` call *after* being told "no trades placed by
automation" has been misled, even though every individual sentence was true.
Disclosure is what makes the constraint meaningful rather than decorative.

**Do not take it on trust.** It is a live state that one config flag changes, so
it is measured, not asserted:

```
python money_posture.py
```

Read-only: it reads no key, places nothing, and arms nothing — deliberately, so
that the checker can never become the thing that arms the trader. If it ever
prints **ARMED**, clause II.1 is being broken and these documents are out of
date. That is the finding, and it is meant to be findable by someone who does
not trust the author.

## IX. What this is not

**This system is not ready to govern anything of consequence**, and section V
of [`CONSTITUTION.md`](CONSTITUTION.md) enumerates why in detail. The short
form:

- **L5 = 1.** One person runs every node, holds every key, and controls every
  remote. A single-operator network is not governed; it is owned. Quorum among
  machines one party controls is theatre. This is the largest gap and it is not
  a software problem.
- **The verifier runs on the governed machine.** An adversary with root rewrites
  the ledger and recomputes every hash. Publishing state roots off-host makes
  tampering *detectable*; nothing here makes it *preventable*.
- **The ethics gate has known defects**, including one demonstrated on
  2026-08-30: it refused a record for a word appearing inside a sentence saying
  the thing was *not* happening. A gate that blocks the case for innocence more
  readily than the accusation is dangerous exactly where it matters.
- **Most of an earlier fifteen-defect audit is still unverified.** Four were
  re-checked and resolved. "Not checked" and "fixed" are different words and
  only one of them is earned.

Anyone told this system is ready should ask which line of this section no longer
applies, and how that was checked.

## X. Verification

```
python redundancy.py        # N at every level, and what shares a failure
python constitution.py verify
sh verify.sh                # the same answer, no Python
powershell -File verify.ps1 # the same answer, no Python and no Unix shell
python federation.py        # SAME CORE / DIVERGED / UNREACHABLE
python scale.py             # compose levels to any depth, any shape
python money_posture.py     # what could this do with funds RIGHT NOW
python conformance.py       # a behaviour root: same computation, any wording
```

Three verifiers in three languages sharing no code. They have already disagreed
once — on one block of three, over whether a heading's em dash was part of what
was signed — and that disagreement was the finding. It was worth more than
either implementation would have been alone.

That is the argument for all of this, at every scale, in one sentence:
**agreement between independent checkers is evidence, and a lone checker
agreeing with itself is not.**

---

*A constraint you can lift when it becomes inconvenient is not a constraint. A
constraint you can lift but not conceal is the most an honest system with one
operator can offer — and this document exists to say, precisely, that one
operator is what it still has.*
