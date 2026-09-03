# Institutional outreach — draft, and the honest constraints on it

Status: **DRAFT. Nothing here has been sent, and by the sequencing in
`OUTREACH_STRATEGY.md` section 6 nothing here should be sent yet.** This is a
stage-4 recipient: a body with no technical evaluation function, which cannot
act on a mechanism however good it is. Spending it now does not merely fail —
it uses up the one approach such an institution will read from a stranger, and
the second attempt reads as persistence rather than progress.

It is held until stage 1 produces the only event that changes anything: somebody
independent running `sh check.sh` and reporting what they got. Read the two
sections after the letter before sending anything; they are the reason this
draft says what it says.

---

## The letter

> **Subject:** A small verifiable mechanism for checking agreement between parties who do not trust each other

Dear [name, title],

I am writing about one narrow technical problem, and I want to be exact about
how small it is.

**The problem.** When two institutions each run their own system and each claim
to follow the same rules, there is no cheap way for either to demonstrate that
to the other. Today this is settled by audit, by treaty language, or by both
sides agreeing to run identical software — and the last of those means one
party's implementation becomes everyone's dependency.

**What I have built and published.** A working demonstration, Apache-2.0,
of three mechanisms that address that problem and can be checked in about ten
minutes by anyone with a laptop:

1. **Disagreement cannot be hidden as it composes.** When groups of checkers
   are nested — nodes into regions, regions into a federation — a group that
   disagrees internally reports *silence* upward rather than passing along its
   majority view. A single dissent survives to the top instead of being
   outvoted into invisibility. The obvious implementation does the opposite,
   and produces a system that looks cleaner the higher you look.

2. **A participant can prove it agrees without adopting anyone's code.** The
   check compares *behaviour* on fixed test vectors, not source text. An
   independent implementation — another language, another jurisdiction's
   procurement rules, the rules translated — can demonstrate it computes the
   same thing while sharing no code. That is the difference between a standard
   and a dependency.

3. **Rules cannot be changed silently.** The text that binds the operator is
   hashed and published. Three independent verifiers, written in three
   languages sharing no code, compute that hash; any change to a protected rule
   — including deleting one, which reports as the most serious result — is
   named. It does not prevent amendment. It prevents amendment *in silence*,
   which is a smaller and achievable thing.

**What it is not, stated plainly because you will check.** This is not a
governance system ready for use, and its own documentation says so in those
words. Every node is run by one person; a single-operator network is not
governed, it is owned. Amendment by quorum is an intention, not a mechanism. Most of an
earlier fifteen-defect audit remains unverified. The verifier runs on the same
machine as the thing it verifies, so it makes tampering *detectable* and never
*preventable*. `docs/CONSTITUTION.md` section V lists these and more, and it is
the section I would read first in your position.

**What I am asking for.** Not adoption. Take the mechanisms, or one of them,
and try to break them — the repository is Apache-2.0 and forking requires
no permission from me and no notice to me. If you find where they fail, that
finding is worth more to me than agreement, and the project keeps a public
record of its own refuted claims for exactly that reason.

**To check any of it yourself:**

```
git clone https://github.com/LAWLESS1987/covenant
cd covenant
python constitution.py verify     # the published rules, unchanged
sh verify.sh                      # the same answer, no Python
python conformance.py             # the behaviour root a fork must match
python redundancy.py              # what this survives, and what it does not
```

The last of those will tell you the structure is capped at one operator. That
is the true state, and I would rather you learn it from the tool than from me.

Yours sincerely,
Lawrence Adam Moskowski
[contact]
github.com/LAWLESS1987/covenant

---

## Why the letter does not say "this is the fair mechanism"

Because the repository says otherwise, in its own words, and the recipient will
find that within ninety seconds:

> **Therefore: this system is not ready to govern anything of consequence.**
> — `docs/CONSTITUTION.md` section V

An institutional reader who is told "this is the fair mechanism" and then reads
that line does not conclude the documentation is too modest. They conclude the
letter overstated, and every other claim in it is discounted at once. The
overstatement would cost precisely the audience it was written for.

The version above is stronger for the same reason it is more modest. It leads
with three things that are true and checkable in ten minutes, states the limits
before the reader can find them, and asks for refutation rather than adoption.
An official can act on that without risk — trying to break something costs
nothing and commits no one — whereas "adopt our governance system" requires a
decision nobody at any desk is empowered to make from a cold email.

Claims that are defensible today, each verifiable by the recipient:

| claim | evidence |
|---|---|
| three verifiers, three languages, one hash | `0f0b3162…5f`, agreeing; `test_v1` |
| a fork can prove agreement without your code | conformance root `0c398099…0f0ddcef` |
| dissent survives composition | `python scale.py` exits non-zero with the dissent named |
| the limits are published, not hidden | `CONSTITUTION.md` V, `GOVERNANCE.md` IX |
| the test suite is real | 66 suites, 1,913 checks, reproducible by `covenant_one.py --all` <!--TOTALS--> |

## Why there is no list of addresses attached

**I could not verify one.** The single closest candidate — `techenvoy@un.org`,
published on the UN Envoy on Technology contact page — is attached to an office
that was **renamed** on 1 January 2025 to the UN Office for Digital and
Emerging Technologies, whose current About page publishes no address at all. If
even that one is uncertain, a list of thirty would be mostly wrong.

A wrong address does not simply fail to arrive. It marks the sender as
someone who did not check, and mail from someone who did not check is filtered
by both machines and people. A fabricated address would be worse than either.

**The harder point, which matters more than the addresses.** Unsolicited mail
to a general government inbox is read by a duty officer whose job is to route
or discard it. Nothing in this letter survives that filter, however good it is,
because the officer has no category for it.

What does work is what has already been done here: a named person whose
published work touches the mechanism, addressed about the specific thing they
worked on. The earlier letters in `docs/OUTREACH.md` are that shape, and they
are the better model. If institutional contact is wanted, the realistic route
is:

1. a named researcher inside an institution, not the institution's front door;
2. an existing call for evidence or consultation, which creates the category a
   duty officer needs;
3. an introduction from someone already inside.

**Before any of this is sent**, each address must be confirmed on the
organisation's own current website, on the day of sending. I have not sent
anything and will not; that is the operator's act, taken knowingly.
