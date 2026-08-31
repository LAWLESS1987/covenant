# Two drafts — United States and Israel

Status: **DRAFTS. Nothing sent.** Verify every address on the organisation's own
site on the day of sending; see the note at the end.

Both are built the same way and for the same reason. Each leads with mechanisms
that can be checked in ten minutes, states the limits before the reader can find
them, and asks to be **refuted rather than adopted**. An official can act on
that at no risk — trying to break something commits nobody — whereas "adopt this
governance system" requires a decision no one is empowered to make from a cold
letter.

---

# 1. UNITED STATES

**Send it as a response to an open consultation, not as correspondence.** In
January 2026 NIST's Center for AI Standards and Innovation (CAISI) issued a
Request for Information on **securing AI agent systems**. CAISI is described as
industry's primary point of contact within the US government for testing and
collaborative research on commercial AI systems.

That matters more than the wording of the letter. An RFI response is filed,
read and catalogued because a process exists to receive it. The identical text
arriving as unsolicited mail reaches a duty officer whose job is to route or
discard, and who has no category for it. **Check whether the RFI is still open
before sending; if it has closed, wait for the next one rather than sending
this cold.**

> **Subject:** RFI response — verifiable agreement between AI systems that do not share an implementation

To the Center for AI Standards and Innovation:

This responds to the RFI on securing AI agent systems. It addresses one narrow
problem within that scope: **how two systems, run by different parties, can each
demonstrate to the other that they follow the same rules — without either
having to run the other's code.**

Today that is settled by audit, by contract, or by both sides adopting one
implementation. The third makes one vendor's software everyone's dependency,
which is a security property as much as a commercial one: a single
implementation is a single point of compromise, and a monoculture cannot be
checked against anything.

I have published a working demonstration, public domain, of three mechanisms.
Each is verifiable in about ten minutes on a laptop, and I am asking for them to
be broken rather than believed.

**1. Conformance is proved by behaviour, not by source.** Fixed vectors are run
through the governance primitives and the *semantic results* are hashed — never
the prose that explains them. An independent implementation, in another language
and under another organisation's procurement rules, produces the same root while
sharing no code. This distinguishes a **standard** from a **dependency**, and it
is the mechanism most directly relevant to an agency that must certify systems
it did not write.

**2. Disagreement cannot be hidden as authority composes.** Where checkers are
nested — agents into services, services into a system of record — a group that
disagrees internally reports *silence* upward rather than passing along its
majority view. A single dissent survives to the top instead of being outvoted
into invisibility. The obvious implementation does the opposite and yields a
system that looks cleaner the higher you look, which is the failure mode worth
designing against.

**3. Rules cannot be changed silently.** The text binding the operator is hashed
and published. Three independent verifiers — Python, POSIX shell, PowerShell —
sharing no code compute that hash, and any change to a protected rule, including
deleting one, is named. It does not prevent amendment. It prevents amendment in
silence, which is smaller and achievable.

**What it is not, stated because you will check.** This is not a governance
system ready for use, and its own documentation says so in those words. Every
node is run by one person; a single-operator network is not governed, it is
owned. It has no legislative mechanism. Most of an earlier fifteen-defect audit
remains unverified. The verifier runs on the same machine as the thing it
verifies, so it makes tampering detectable and never preventable.
`docs/CONSTITUTION.md` section V lists these, and it is the section I would read
first in your position.

**To check any of it:**

```
git clone https://github.com/LAWLESS1987/covenant && cd covenant
python conformance.py        # the behaviour root an independent build must match
python scale.py              # exits non-zero, naming a dissent three levels down
python constitution.py verify ; sh verify.sh   # same hash, no shared code
python redundancy.py         # what this survives, and what it does not
```

The last will report that the structure is capped at one operator. That is the
true state, and I would rather you learn it from the tool than from me.

Yours sincerely,
Lawrence Adam Moskowski
github.com/LAWLESS1987/covenant

---

# 2. ISRAEL

**Different argument, because the position is different.** Israel is small
enough to adopt a mechanism quickly and constrained enough that it must
interoperate with partners while ceding no control over its own systems. That is
precisely the problem conformance-by-behaviour solves, and it is a sharper fit
here than in a large agency.

Candidate recipients, in order of likely usefulness — **all to be confirmed on
their own current sites**: the Ministry of Innovation, Science and Technology
(which ran the national AI programme); the Israel Innovation Authority; and a
named academic centre — Hebrew University, the Technion, or Tel Aviv University
— where a specific researcher is far likelier to engage than a ministry inbox.

> **Subject:** A mechanism for verifying agreement between systems without sharing an implementation

Dear [name, title],

I am writing about one narrow technical problem, and I want to be exact about
how small it is.

**When two parties must cooperate but neither can adopt the other's software,
there is no cheap way for either to show it follows the same rules.** This
arises wherever systems must interoperate across an institutional or national
boundary: each side needs assurance, and neither can accept the other's
implementation as its dependency.

The usual answers are audit, contract, or a common codebase. The first two are
slow and periodic. The third creates exactly the dependency the boundary
existed to prevent — and a shared implementation is also a shared vulnerability.

I have published, public domain, a working demonstration of a fourth option:
**compare the computation, not the artefact.** Fixed vectors run through the
governance primitives, and the semantic results are hashed — never the wording.
Two systems sharing no source code produce the same root, or they do not, and
either answer is informative. A party can therefore demonstrate conformance
while retaining full control of its own implementation, its own language, and
its own review process.

Two further mechanisms come with it. **Disagreement survives composition:** in a
nested structure, a group that disagrees internally goes silent upward rather
than forwarding its majority, so a lone dissent reaches the top instead of
disappearing. And **rules cannot be amended silently:** the binding text is
hashed and published, and three verifiers written in three languages sharing no
code will each name any change, including a deletion.

The idea behind the first mechanism is not mine and I should say whose it is. It
is adapted from the Neuromorphic Intermediate Representation — Jens Egholm
Pedersen and colleagues — which solves the same problem for neuromorphic
hardware: stop comparing implementations, compare a canonical description of the
computation. The 2025 Misha Mahowald Prize shortlist is credited in the
repository, because taking an idea without saying where it came from is the
thing this project is against.

**What it is not.** Not a governance system ready for use. One operator holds
every key; no legislative mechanism exists; most of an earlier fifteen-defect
audit is unverified; the verifier runs on the machine it verifies, so tampering
is detectable and not preventable. All of that is in section V of the
constitution, which is the section I would read first.

**I am not asking for adoption.** The repository is public domain; forking needs
no permission and no notice to me. I am asking whether the mechanisms break
under examination by people who would know. If they do, that finding is worth
more to me than agreement — the project keeps a public record of its own
refuted claims for exactly that reason.

Yours sincerely,
Lawrence Adam Moskowski
github.com/LAWLESS1987/covenant

---

## Before either is sent

**No address is asserted here.** The nearest thing to a verified route is
`www.nist.gov/caisi` and the January 2026 RFI. Every address must be confirmed
on the organisation's own current site on the day of sending — an office renamed
between one year and the next is common enough that the UN's technology envoy
did exactly that on 1 January 2025, leaving its old published address attached
to an office that no longer exists under that name.

A wrong address does not merely fail to arrive. It marks the sender as someone
who did not check, and mail from someone who did not check is filtered by both
machines and people.

**Prefer a named person to an institutional inbox**, and prefer an open
consultation to either. The earlier letters in `docs/OUTREACH.md` are that shape
and remain the better model.

**Neither letter mentions the author's history, and that is deliberate.** A
message carrying both a technical mechanism and a personal claim is routed by
the personal claim, and the mechanism never reaches anyone who could evaluate
it. The mechanisms are strong enough alone. Keep them alone.
