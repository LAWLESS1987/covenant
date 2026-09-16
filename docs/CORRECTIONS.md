# Corrections and missteps

One index for everything this project has got wrong and said so. It exists because the
record was scattered — some in `KNOWN_ISSUES.md` under an A-number, some in
`WHAT_WE_FOUND.md` §7, some in a roundtable transcript — and a record nobody can find
is a record that does not do its job.

**The rule this file follows.** A refuted claim is never deleted or quietly reworded.
The original text stays where it was published, a correction is written beside it, and
both stay. A document rewritten after it was refuted is not a record. Where a claim went
out by email, the correction goes back to the same recipient, unprompted, before they
raise it.

*Standing direction, 2026-09-05: keep it green and document the issues honestly —
perfection is not the goal, mutual benefit and honesty is.*

---

## The refutations that cost the most

| What was claimed | What is true | Where |
|---|---|---|
| **The conformance root proves two builds compute the same thing** — "NIR's move applied to governance" | The root is a hash over the expected outputs **printed in the same file that publishes it**. It reproduces in nine lines with no implementation at all. What survives is an ordinary test-vector suite: two builds matched all 23 vectors *per vector*, which pins the computation only where it samples. Refuted by **Jens Egholm Pedersen (DTU)**, author of the borrowed idea, on 2026-09-15 — the first outside review this project ever had | [A121](KNOWN_ISSUES.md) |
| **The 11→23 vector history shows the method catching and curing its own flaw** | Underdetermination is what a sample-based suite does. Twelve more samples is still a sample. No vector count converts a suite into a semantic specification | [A121](KNOWN_ISSUES.md), [SPEC_SUFFICIENCY](SPEC_SUFFICIENCY_2026-08-31.md) |
| **"Someone independent reproduces the conformance root" is the one event that changes the project's standing** | That target could be hit by reading a file. Sixteen days of outreach were aimed at it. The real and still-unmet event is computing all 23 vectors from their **inputs** and matching every answer | [A121b](KNOWN_ISSUES.md), [OUTREACH_STRATEGY §5](OUTREACH_STRATEGY.md) |
| **The project has drawn contributions from outside institutions** | The "outside implementers" were AI agents run inside the project. Corrected to NSF by the author, unprompted, 2026-09-11 — before the refutation, and reinforced by it | [A121b](KNOWN_ISSUES.md) |
| **The trading rules have a measurable edge** | Across three mechanisms and **2,276 variants**, nothing clears deflated Sharpe ≥ 0.95, walk-forward p ≤ 0.05 and PBO < 0.5 together. The one class that passed any single test still lost money out of sample in four folds of five. Equal-weight buy-and-hold over the same window lost 63%. The trader stays disarmed, and Constitution rule 2 is *"no claim of profit edge"* | [KNOWN_ISSUES](KNOWN_ISSUES.md) |
| **35 of 36 "guards" protected what they named** | Confirmed fake by mutation: the dominant mechanism is a check that **greps the source text** instead of running it. A guard that passes without the property holding is not a guard | [A74](KNOWN_ISSUES.md) |
| **A node earns something by running the chain** | Zero, measured. The only reward is 1% of value *moved*, paid exclusively to stakers; nothing has ever been staked, so all 0.12 tokens ever computed were discarded. Supply is still the 1000-token genesis mint | [PARTNER.md](PARTNER.md) |
| Two further claims of the author's that did not survive checking | Written out in full | [WHAT_WE_FOUND §7](WHAT_WE_FOUND.md) |

## Missteps of conduct, not of code

| | Where |
|---|---|
| The outreach tiering rule was broken **sixteen hours after it was written**, by a bulk send to foreign defence ministries, government press desks and MIT lists with nothing from Stage 1 to carry. Uncorrectable — no live correspondent | [A122](KNOWN_ISSUES.md) |
| August letters into the neuromorphic community — the same small field the one good September result came from | [A122](KNOWN_ISSUES.md) |
| Every emailed `git clone` line arrived wrapped by Gmail and clones an **empty repository**. Present in every letter until 2026-09-15, including the one whose notes claimed the links were safe | [A122](KNOWN_ISSUES.md) |
| An affiliation verified against a page that was real and not current: Pedersen is at **DTU**, not KTH | [A121](KNOWN_ISSUES.md) |

## What the pattern is

Three separate findings here are the same shape, and it is worth naming once:

> **A check that confirms a claim is *stated consistently* is not a check that the claim
> is *true*.**

The fake guards grepped source text instead of running it (A74). Three rounds of
adversarial review passed the conformance claim by verifying that the root reproduced —
which it did — and never asking whether reproducing it required doing the computation
(A121). And the suite's own test X2 was labelled **"THE CLAIM"** while passing by
reading `expected` and never `input`, so the test that was supposed to defend the claim
demonstrated the defect instead.

**The standing question that follows, for any conformance artifact here:** state what an
implementation must compute in order to pass, then demonstrate the check **fails** when
it is not computed. Breaking a green on purpose is the only proof the green was earned.

## What has not been corrected

- **The bulk sends of 2026-08-31** stand wrong in other people's inboxes. There is no
  correspondent in those threads to write back to.
- **Pedersen's prescription** — write the specification of `climb` and `attest` as
  semantics independent of any implementation — is recorded and **not done**. It is new
  structure, and new structure waits for more than one operator.
- **`peers.txt` still reads `self`.** No second party has run the vectors. The federation
  is one node, and section IX's cap, L5 = 1, applies to every claim in this repository.
