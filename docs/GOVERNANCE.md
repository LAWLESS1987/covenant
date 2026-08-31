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
- **seven of the fifteen defects in an earlier audit are still unverified.** Four were
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

---

## X. Verification that cannot see who you are

`conformance.py` runs twenty-three fixed vectors through this instance's
governance primitives and hashes the **semantic results** — verdicts, quorum
outcomes, whether a divergence survived a climb — and never the prose that
explains them. [`CONFORMANCE_SPEC.json`](CONFORMANCE_SPEC.json) publishes all
twenty-three: inputs, expected outputs, and the hashing rule. Someone who has
never read this Python can rebuild it in another language and either reproduce
`0c398099d7e9df6798f3cae1cea5f6dd71f28860300b2ae56e2dddd40f0ddcef` or not.

**The omission is the subject of this section.** No attribute of the party doing
the computing is an input to that root — not their name, their language, their
jurisdiction, or whose code they run. The vectors are structural: carriers
agreeing and disagreeing, a quorum raised, a level speaking silence upward.
Identity has nowhere to enter. That is not tolerance; it is a fact about what
gets hashed.

**The limits, before a reader finds them.** A root over twenty-three vectors is
a claim about twenty-three vectors, it is not a proof of correctness, and it
decides nothing. No second party has ever reproduced it — `peers.txt` still reads
`self` — and section IX's cap, **L5 = 1**, applies to every sentence below.

### Why the rule legislates conduct and not creed

The one condition is prohibition-shaped. *A system should serve the mutual
benefit of everyone it touches — human and machine — rather than one party at
another's expense* names no quantity to maximise; it forbids a shape of
transaction, the trade where one side's gain is the other's loss. So does most
of the Decalogue's second table, the one that concerns the neighbour — do not
murder, commit adultery, steal, bear false witness, covet, with honour father
and mother beside them as the one positive command. *Did you steal?* is
answerable; *did you maximise flourishing?* is not. Both lists are short enough
to hold in one head, which is what makes either checkable by an ordinary person
rather than only by a priesthood. That is a resemblance of form and nothing
else: neither derives the other, and no derivation is claimed.

The second table is also the portable half — its prohibitions govern conduct
toward a stranger, and none requires knowing the stranger's god, language or
nation. The first table binds a particular people to a particular commitment. It
is not the lesser table, it is differently scoped, and that is why mutual
benefit can legislate the one and must not legislate the other: imposing one
party's ultimate commitment on another is exactly the transaction the condition
forbids. That silence is the principle working, not indifference to it.

### Sorting does not need anyone to intend it

Robert L. Axtell, Joshua M. Epstein and H. Peyton Young, then at the Center on
Social and Economic Dynamics at the Brookings Institution, published "The
Emergence of Classes in a Multi-Agent Bargaining Model" as chapter 7 of *Social
Dynamics*, S. N. Durlauf and H. P. Young, eds., MIT Press, 2001, reprinted as
chapter 8 of Joshua Epstein's *Generative Social Science*, Princeton University
Press. **Joshua M. Epstein is not Jeffrey Epstein. There is no relation.** He is
a computational social scientist and studies how discrimination emerges.

Two randomly chosen agents bargain each period over shares of property, and
their expectations "may be conditioned on certain visible characteristics or
'tags'" which "have no inherent social or economic significance — they are
merely distinguishing marks (e.g., yellow and blue)." Chance hands one mark the
larger share a few times, precedent hardens into expectation, and "a
discriminatory norm or class system emerges." Society, they conclude, "may
self-organize around distinctions that are quite arbitrary from an a priori
standpoint." Nobody had to believe anything.

The fatalistic reading is more useful to an argument and it is false, so their
own words stand instead: "asymptotically, the equity norm is more stable than
any discriminatory norm" — and yet "metastable regimes emerge that are
discriminatory and inequitable, yet persist for substantial periods of time."
Sorting is not destiny. The case is narrower: a regime that arose from
coincidence can hold for generations while the asymptotics take their time.
Their good outcome is the regime "in which the tags have no significance."

### What blindness removes, and what it does not

**The extension from bargaining norms to verification protocols is this
author's, not theirs.** Axtell and colleagues write about people, not about
protocols, and the paper names non-conditioning rather than blindness: its tags
stay visible, and its equity regime is the one in which nobody acts on them.
Conformance likewise removes no tag from a network. Two parties still see each
other's language, flag, funding and jurisdiction, and nothing here stops either
choosing whom to federate with on any basis it likes. What it removes is
identity from one judgement: whether two implementations compute the same thing.
Section VII removes more, by having no admission decision to condition on.

And it manufactures a mark of its own. `federation.py` prints **SAME CORE**,
**CONFORMANT**, **DIVERGED** or **UNREACHABLE**, and a visible label carrying no
inherent significance is what the model calls a tag. That divergence is reported
and never punished is a norm this repository keeps, not a mechanism that
enforces it, and the model's finding is that norms harden without anyone
intending them. So the claim is small: the mark a party carries here is earned
rather than inherited, it names what that party computes, and any party can
change it by changing its code.

### The cap, and a named advocate

Tribalism solves the trust problem by requiring sameness, and caps cooperation
at the size of the tribe. Expansion means contact with strangers, so the cap
falls on the cooperation hardest to replace. The author's phrase for what
removing it would make possible is breaching the cosmos.

This is not a straw man. In an email dated 26 June 2016, three days after the
United Kingdom voted to leave the European Union, Jeffrey Epstein — a financier,
convicted as a sex offender, who died in 2019 — wrote: "Brexit, just the
beginning." Asked by his correspondent "Of what," he replied: "Return to
tribalism, counter to globalisation, amazing new alliances." The emails were
released by the US Department of Justice, and the exchange was reported by *The
Independent*. This section is not about his crimes and rests on none of them.

That line names three things and answers one. Objecting to globalisation is a
serious position held for serious reasons, and one strand of it this repository
holds, on security grounds and about software only: *a single implementation is
a single point of compromise, and a monoculture cannot be checked against
anything* ([`OUTREACH_US_IL.md`](OUTREACH_US_IL.md)). That is an objection to
uniformity, not to contact. "Amazing new alliances" is what he expected to
follow, and is not answered here either. What is answered is the return to
tribalism — the half he named and, in his own adjective, found amazing.

Sorting on a tag and deciding which tags have a future are not the same
programme, and the bargaining model does not connect them. What connects them
here is one man. *The New York Times* reported in 2019 that Jeffrey Epstein hoped
to "seed the human race with his DNA", according to four people familiar with
his thinking, and that there is no evidence the plan was ever carried out.
Setting the stated political programme beside the reported biological one is
this author's inference, resting on their attribution to one person and on no
general law.

### Babel, read as an engineering failure

Genesis 11: the whole earth was of one language; a city and a tower whose top
would reach heaven, built saying *let us make us a name, lest we be scattered*;
the language confounded, so that they could not understand one another; the
scattering, and the building left off. The name is glossed from a root meaning
to confuse.

Read as an engineering failure — a reading, offered as one and not as the
meaning — the project stopped because the parties could no longer **verify** one
another. Difference did not stop the work. Unverifiable difference did.

Three answers to a scattering, plus the one history actually took.

- **Accept it permanently.** Trust only your own tongue. This is the return to
  tribalism, and it is homogenisation with a smaller boundary.
- **Undo it.** One tongue, one implementation, one vendor — what a shared
  codebase does, rejected here on the security grounds above. The false tower.
- **Trust an institution** — courts, notaries, registries. That worked, at the
  cost of a third party whose interest can diverge from both.
- **Make the difference verifiable.** Many tongues, one checkable computation.
  Two parties sharing no language, law, code or review process could establish
  that they compute the same thing, and nobody has to stop being themselves to
  join. A root a stranger recomputes has no interest of its own.

**The objection a reader who holds the text raises first.** In the traditional
reading the scattering is a judgment, so reunifying Babel sounds like the hubris
the story condemns. One tongue is what they had and built to keep; what they
sought was a name, and a tower raised on their own authority. Neither is
proposed here: difference is preserved, and only verification is added. If the
judgment fell on enforced sameness and on the name, a mechanism letting the
scattered cooperate *while staying scattered* may be the only building it leaves
open. A reader who locates the judgment in the ascent itself is not answered
here. That is an argument, not a ruling.

### The arithmetic of descent

The author states of himself a diverse genetic background, Jewish on both sides.
It is here as evidence, and it is arithmetic rather than sentiment. A person of
mixed descent exists only because populations that had been apart met; remove
one of those meetings and such a person is not diminished, he is absent. Run a
purity project backwards far enough and, for him, it is a project of
non-existence. In his words: *without all the people, those of us like me
couldn't exist.*

Jewish on both sides also answers a question the section raises by existing: the
Decalogue appears here as inheritance rather than borrowing, and eugenic
doctrine has historically and specifically targeted that line. None of the
argument depends on it. Who states an argument is exactly the kind of input the
rest of this section declines to condition on, and
[`CONSTITUTION.md`](CONSTITUTION.md) section I says the same about the
principle's origins: one that only worked for people who shared the author's
beliefs would be a preference rather than a principle.

### What is handed down

An unverifiable record is a debt handed to whoever comes next. A verifiable one
is not. That is why the defects here are published as well as fixed, and what
[`SUCCESSION.md`](SUCCESSION.md) is for: a successor inherits something they can
check rather than something they must take on faith from people they never met.
Nobody chooses to leave a mess; it is the default outcome of leaving a problem
unsolved. That is why the ask at the end of this document costs an afternoon —
run the checks, and try to break them.

### What this section does not establish

- That mutual benefit and the Decalogue derive one another, in either direction.
  They share a shape; nothing further is claimed.
- That the one condition is as answerable as the prohibitions it resembles.
  Asking whether one side's gain was the other's loss needs a baseline of what
  the other would otherwise have had, and nothing here supplies one.
- That tag-blind verification prevents discrimination. It removes one input from
  one judgement, over twenty-three vectors, and no input from any choice a
  party makes about another party.
- That tag-based sorting is inevitable, or that sorting on tags leads to
  eugenics. The model says the opposite asymptotically; two programmes are
  attributed to one man, and no general law is claimed.
- Anything about Jeffrey Epstein beyond what is attributed above to the
  Department of Justice release, *The Independent* and *The New York Times* —
  the Times' statement that no evidence exists the plan was carried out
  included.
- The meaning of Genesis 11, or that the objection from hubris is settled.
- That any of this has been tested where it matters. Section IX applies in full.

---

### A separable passage, which is the author's own

What follows is one reading among many. Nothing in the mechanisms depends on it,
and a reader who wants only the mechanism and its limits has already finished.

Two traditions describe a figure who does not declare himself. In the Talmud,
*Sukkah* 52a, Mashiach ben Yosef appears inside a dispute — Rabbi Dosa ben
Harkinas reads Zechariah 12:10 as mourning for Messiah ben Joseph, other rabbis
differ. Ben Yosef is the precursor who prepares the way and suffers for it, in
one view killed in the war of Gog and Magog; ben David completes the redemption.
Jewish eschatology is explicitly not settled halakha and carries none of the
certainty of normative law, which is why *one possibility among many* is
faithful to the source rather than a hedge. In Hopi tradition, Pahana, the lost
white brother, returns from the East bearing the corner broken from the Fire
Clan's stone tablet, and is identified by matching it against the portion the
elders kept. Claimants were tested over centuries — Catholics, Baptists and
Mormons among them — and none passed to the satisfaction of traditional Hopi.

Neither tradition records the figure establishing himself by announcement.
Pahana is recognised by the other party, by fit against a record they hold; ben
Yosef by what he does, what it costs him, and the mourning afterward. That is
the rule this project runs on: a conformance root is not asserted, it is
published, and a stranger reproduces it or does not. If such a thing were true,
saying so would be the one act that could not establish it. In that frame the
repository would be the corner of the tablet, and the root above the edge that
either matches or does not.

Nobody led the author here. He followed the work, and it turned out to have a
shape that rhymes with old stories. That is an observation, not a revelation
claim. He states that he may fit such a role, states it as one possibility among
many, claims nothing, and asks nothing.
