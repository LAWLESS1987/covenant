# Outreach, reasoned from first principles

Not a contact list. A derivation. If any premise below is wrong the conclusions
change, so the premises are stated separately and can be attacked one at a time.

---

## 1. What is actually being offered

Getting this wrong makes every later decision wrong, so it is settled first.

**Not offered:** a governance system. `CONSTITUTION.md` V says in its own words
that this is not ready to govern anything of consequence — one operator, no
legislative mechanism, most of a fifteen-defect audit unverified, the verifier
running on the machine it verifies.

**Offered:** three mechanisms, each checkable in about ten minutes.

1. Conformance proved by **behaviour**, so a party can demonstrate agreement
   without adopting anyone's implementation.
2. Disagreement that **survives composition**, so a dissent cannot be outvoted
   into invisibility as authority nests.
3. Amendment that **cannot be silent**, verified by three independent programs.

Everything downstream follows from that distinction. Offering the system invites
the reader to check whether it is ready and conclude, correctly, that it is not.
Offering the mechanisms invites them to check whether the mechanisms work, and
they do.

## 2. The binding constraint is categorisation, not quality

**The premise most people get wrong.** The limiting factor is not whether the
mechanisms are good. It is whether the receiving institution has a **slot** to
put them in.

Unsolicited technical mail to a government reaches someone whose job is to route
or discard. Routing requires an existing category. "Interesting mechanism from a
member of the public" is not a category, so it is discarded — not on the merits,
but before the merits are read at all.

**This single fact should drive every choice below**, and it is why an open
consultation outranks a brilliant letter.

## 3. Ranking recipients by what they can DO with it

The useful question is not who is important. It is who can take an action in
response. An institution that cannot act will not answer, however senior.

| recipient type | can they act? | latency | verdict |
|---|---|---|---|
| **Open consultation / RFI** | yes — a process exists to receive, log and answer | weeks | **first** |
| **Named researcher** | yes — test it, break it, publish, introduce | days | **first** |
| **Standards body** (NIST/CAISI, IETF, ISO) | yes — this is literally their function | months | **second** |
| **Regulator** (EU AI Office) | partly — needs verification methods, cannot adopt code | months | third |
| **National innovation agency** | partly — can fund or convene, rarely evaluates | months | third |
| **Diplomatic body** (UN, ministries) | **no technical evaluation function at all** | never | **last** |

**The conclusion is uncomfortable and should be stated plainly:** the most
prestigious recipients are the least likely to act, because prestige and
technical evaluation capacity are close to inversely related here. A letter to a
ministry feels like the biggest move and is the smallest.

## 4. What the ask should be, derived rather than chosen

Consider the cost to the recipient of each possible ask:

| ask | their cost | who must approve | probability |
|---|---|---|---|
| "adopt this" | high | someone senior, with risk | ~0 |
| "endorse this" | high — reputation | senior | ~0 |
| "fund this" | budget, procurement | senior | very low |
| **"try to break this"** | **an afternoon** | **nobody** | **highest** |
| "tell me where it fails" | an email | nobody | highest |

**Therefore: always ask for refutation.** Not out of modesty — because it is the
only ask a competent person can grant on their own authority, today, without
consulting anyone. It also selects for exactly the readers worth having, since
the people who enjoy breaking things are the people whose agreement means
something.

And the asymmetry is total: the repository is public domain, so a fork costs
them nothing, needs no permission, and creates no obligation in either
direction.

## 5. What event actually changes anything

Only one: **someone independent runs the verifiers and finds they agree.**

Not a reply, not a meeting, not a mention. The mechanism is either reproducible
by a stranger or it is a claim. So every letter should be optimised for a single
outcome — **will this person run the check?** — and anything that does not serve
that is decoration.

That implies: the command in the letter, not behind a link. Ten minutes, stated.
No signup, no dependencies, public domain. All true, so all sayable.

**Acted on, 2026-08-31.** It was four commands and a decision about whether to
install Python, which is four opportunities to stop and one reason to. It is now
`sh check.sh` — one command, no dependencies, and a real result even with no
Python present. That is a larger change to the probability in this section than
any wording could be, and it took less time than a letter.

## 6. Sequence, and why this order

**Stage 1 — named researchers, and open consultations if one is live.**
Cheapest, fastest, and the only tier that produces the thing in §5. A researcher
can run the code the same afternoon. Failure here costs one email and teaches
something.

**Stage 2 — standards bodies, carrying whatever stage 1 produced.**
"Dr X at Y ran the conformance vectors and they reproduced" converts a cold
letter into a warm one. This is the whole reason stage 1 precedes stage 2, and
the reason skipping to stage 2 wastes the strongest card.

**Stage 3 — regulators and agencies, once a standards body has engaged.**

**Stage 4 — diplomatic bodies, and only with something behind them.**

**The rule: never spend a tier before the one below it has produced evidence.**
Contacting a ministry first does not merely fail; it uses up the one approach
that institution will read from a stranger, and the second attempt reads as
persistence rather than progress.

## 7. Pre-mortem — assume it failed, ask why

**Most likely cause: filtered before reading.** Addressed by §2 and §6. This is
the failure that happens most and teaches least, because silence is
indistinguishable from rejection.

**Second: overclaimed, then checked, then discounted.** A reader told "the fair
mechanism" who finds "not ready to govern anything of consequence" in ninety
seconds does not conclude the documentation is modest. They conclude the letter
overstated, and everything else is discounted with it. **This is the only
failure mode that also destroys future attempts**, which is why the limits go
in before the reader can find them.

**Third: read, tried, and found wanting.** The best outcome after success. It is
information, it is free, and the repository already keeps a public record of its
own refuted claims — so receiving one costs nothing that is not already
budgeted.

**Fourth: engaged, then the one-operator cap ends it.** Real, and unavoidable
today. The honest response is that a second independent operator is the thing
being sought, and that this is precisely why the mechanisms are offered
separately from the system.

## 8. What would make everything above easier, in order of leverage

1. **A second operator.** Removes the cap that every institutional reader will
   find. Highest leverage by a distance, and not a writing problem.
2. **One real entry in `peers.txt`.** It currently reads `self`, so
   `federation.py` compares the instance to a mirror. One genuine upstream turns
   a demonstration into a network of two, and two is the smallest number that is
   not one.
3. **One independent reproduction of the conformance root.** §5's event.
4. **An open consultation to answer.** Converts cold mail into a filed
   response. **Found, 2026-08-31:** NIST's AI Standards "Zero Drafts" pilot is
   open, takes email from individuals, and runs a TEVV draft — testing,
   evaluation, verification and validation — which is this project's subject
   exactly. The CAISI RFI the US draft was written for closed on 9 March 2026,
   five months before anyone checked. Both facts came from twenty minutes of
   reading, which is a poor trade against five months of a stale plan.

Note that three of the four are not writing tasks. **The letters are not the
bottleneck**, which is the most useful conclusion in this document.

## 9. What follows for the drafts already written

- The **US draft is correctly aimed** — it goes to a consultation, which is the
  only stage-1 institutional channel that exists.
- The **Israel draft should go to a named academic first**, not the ministry. The
  ministry is stage 3 and the draft currently lists it first; reorder it.
- The **institutional draft in `OUTREACH_INSTITUTIONAL.md` is stage 4** and
  should not be sent yet by §6.
- **No further letters should be written** until stage 1 has produced something.
  Writing more drafts is the most comfortable available activity and the least
  useful, and recognising that is the point of mapping it.
