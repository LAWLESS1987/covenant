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

**Send it as a response to an open consultation, not as correspondence.** An
RFI response is filed, read and catalogued because a process exists to receive
it. The identical text arriving as unsolicited mail reaches a duty officer whose
job is to route or discard, and who has no category for it. That difference
matters more than any wording.

### The channel this was aimed at is CLOSED. Checked 2026-08-31.

This draft was written for CAISI's January 2026 Request for Information on
securing AI agent systems. **That RFI closed on 9 March 2026**, and NIST has
since published a summary analysis of the responses — so it is not merely shut,
it is concluded. Two adjacent doors closed with it: the AI agent identity and
authorization concept paper (2 April 2026) and the sector listening sessions,
whose expressions of interest closed 31 March 2026.

The draft's own instruction was to check before sending. Checking is what found
this. Left unchecked for five months, a letter would have arrived quoting a
consultation that no longer existed — which does not merely fail, it marks the
sender as someone who did not look.

### The channel that IS open, and is a better fit

**NIST's AI Standards "Zero Drafts" pilot**, page last updated 14 August 2026,
accepting input by email and open to individuals rather than organisations only.
It runs several drafts, and one of them is squarely this subject:

- **TEVV — AI testing, evaluation, verification and validation.** A draft
  outline exists; input goes to `ai-standards+tevvzd [at] nist.gov`. Scope, in
  NIST's words, is a general framework for approaching TEVV "based on clear
  concepts and conceptual relationships" rather than specific methods. No
  deadline is stated for this one.
- **Public-facing AI documentation**, initial public draft July 2026 — NIST
  "will consider input received by **September 16, 2026**". A near deadline, but
  a worse fit: this project's contribution is a verification mechanism, not a
  documentation template.

TEVV is the better target and it is the more honest one. Conformance proved by
behaviour is a verification method; addressing it to a verification framework is
the whole of the argument, and needs no stretching to make the case.

**Submissions become part of the public record.** That is an advantage here, not
a risk — the repository is public domain and the point is to be checked — but it
should be a decision made knowingly rather than discovered afterwards.

**Verify all of this on nist.gov on the day of sending.** Everything above was
true on 31 August 2026 and the closed RFI is the standing demonstration of what
five months does to a fact like this.

> **Subject:** Input to the TEVV zero draft — verifying that two implementations compute the same thing, without either running the other's code

To the NIST AI Standards Zero Drafts team:

This is input to the TEVV zero draft. It addresses one narrow problem within
that scope: **how two systems, run by different parties, can each demonstrate to
the other that they follow the same rules — without either having to run the
other's code.**

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
is the mechanism most directly relevant to a TEVV framework that must apply to
systems its authors did not write.

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

**To check any of it — one command, no dependencies, no account:**

```
git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh
```

On Windows, `powershell -ExecutionPolicy Bypass -File check.ps1`. Neither needs
Python; with no Python installed the constitution still verifies and the checker
names exactly what went unchecked, because a skipped check is not a passed one.

It will report that the structure is capped at one operator. That is the true
state, and I would rather you learn it from the tool than from me.

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

**Recipient order, corrected 2026-08-31 by the reasoning in
`OUTREACH_STRATEGY.md` section 6.** This first listed the ministry, which was
backwards. A ministry has no technical evaluation function, so it cannot act on
a mechanism however good it is — and a first approach spent there is spent: the
second attempt reads as persistence rather than progress.

  1. **A NAMED ACADEMIC** at Hebrew University, the Technion or Tel Aviv
     University, chosen because their published work touches verification,
     distributed systems or AI governance. A researcher can run the vectors the
     same afternoon and needs nobody's approval to do it.
  2. The Israel Innovation Authority — only after (1) has produced something.
  3. The Ministry of Innovation, Science and Technology — last, and carrying
     whatever (1) and (2) yielded.

All to be confirmed on their own current sites on the day.

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

**To check any of it — one command:**

```
git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh
```

(`powershell -ExecutionPolicy Bypass -File check.ps1` on Windows. Neither needs
Python, and both name what they could not check.)

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

**One route was checked on 2026-08-31 and one was not.** The Zero Drafts pilot
page, its TEVV address and the 16 September 2026 documentation deadline were
read on nist.gov that day. No Israeli address has been checked at all, and none
is asserted below.

Every address must be confirmed on the organisation's own current site on the
day of sending. Two demonstrations of why, both from this file:

- The January 2026 CAISI RFI this draft was built around **closed on 9 March
  2026** and was still being cited here five months later. Nothing announced
  that; it simply stopped being true.
- An office renamed between one year and the next is common enough that the
  UN's technology envoy did exactly that on 1 January 2025, leaving its old
  published address attached to an office that no longer exists under that name.

A wrong address does not merely fail to arrive. It marks the sender as someone
who did not check, and mail from someone who did not check is filtered by both
machines and people. **Checked facts decay silently, so the check belongs on
the day, not in the draft.**

**Prefer a named person to an institutional inbox**, and prefer an open
consultation to either. The earlier letters in `docs/OUTREACH.md` are that shape
and remain the better model.

**Neither letter mentions the author's history, and that is deliberate.** A
message carrying both a technical mechanism and a personal claim is routed by
the personal claim, and the mechanism never reaches anyone who could evaluate
it. The mechanisms are strong enough alone. Keep them alone.
