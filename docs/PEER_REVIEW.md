# How to review this repository

**This is not a persuasion document.** It is the protocol for attacking the work.
Every standing claim below is paired with the thing that would kill it and the
exact command that would show it — because a claim with no stated falsifier is
not a finding, it is an assertion with a number attached.

**Why it exists.** On 2026-09-15 the author of an idea this project borrowed read
it and refuted its central claim in about twenty minutes. The claim had survived
three rounds of the project's own adversarial review, been published on the front
page, and been sent to a standards body and a federal program officer. It failed
for a reason nobody inside had asked: *does passing the published test require
doing the computation?* It did not. See `CORRECTIONS.md` and `KNOWN_ISSUES.md`
A121.

The lesson is general and it is the rule of this file:

> **State what an implementation must compute in order to pass, then demonstrate
> the check FAILS when it is not computed.**

---

## 0. The ten-minute pass

```bash
git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh
```

Five checks, no account, no dependencies. It names what it could **not** check as
plainly as what it could, and a skipped check is never rounded up to a passed one.

---

## 1. Standing claims, and what would kill each

| # | Claim | What would falsify it | Command |
|---|---|---|---|
| C1 | The published rules on disk are the rules the code enforces | The two independent hash computations disagree | `sh check.sh` (checks 1–2) |
| C2 | `attest` and `climb` behave as `docs/SEMANTICS.md` describes | An input where the spec and the implementation differ | `python test_r2_semantics.py` |
| C3 | A dissent three levels down still reaches the top | A nested disagreement that the summit reports as clean | `sh check.sh` (check 4) |
| C4 | The ethics gate fails closed: an unreachable judge beside a clean one still blocks | A transaction admitted while a judge was unreachable | `python test_f1_fallback_silence.py` |
| C5 | A retracted claim cannot silently return | A retracted phrasing reappearing with no citation | `python test_r1_retracted.py` |
| C6 | The chain is joinable — no block in it is convicted by the judge | Any chain payload the deployed elder convicts | `python test_a124_chain_syncable.py` |
| C7 | The student learns rather than being rebuilt nightly | A belief moving further than the step in one pass | `python test_a127_refine_not_rebuild.py` |

**Every one of these suites is mutation-tested**, and the mutations are named in
the suite's own docstring. A green that has never been made to fail is not
evidence. If you find a suite whose green cannot be broken by breaking the thing
it claims to protect, that is a finding — this repository has shipped that defect
before, in 35 of 36 guards (A74).

---

## 2. What a pass does NOT mean

- **Not correctness.** These say the implementation does what is written down.
  Whether what is written down is *right* is a separate question and this
  repository does not answer it.
- **Not coverage.** `SEMANTICS.md` is checked over an exhaustively enumerated
  **bounded** space — every input inside the bound, nothing outside it. The bound
  is printed with the result on purpose. A claim about 100,000 cases and a claim
  about 23 are different claims.
- **Not independence.** The specification, the reference implementation and the
  differential test were all written by the same hand, hours apart, by someone
  who had just read the implementation. `spec_reference.py` is barred from
  *importing* the code; nothing bars the ideas from having come from it. **The
  test that would settle this is a stranger building from `SEMANTICS.md` having
  never seen the repository. That has not happened.**
- **Not consensus safety.** `attest` detects divergence, corruption and
  single-point compromise. It is **not** Byzantine consensus, and calling it that
  would be a lie with a security label on it: witnesses under one hand are
  copies, not opinions.

---

## 3. Claims that are NOT established

Listed so a reviewer does not have to discover them.

- **No second operator.** `peers.txt` reads `self`. Section IX's cap, **L5 = 1**,
  applies to every claim in this repository.
- **Nobody outside has run the vectors.** One outside reviewer reproduced the
  conformance *root* — precisely to demonstrate that doing so proves nothing.
- **No trading edge.** Across three mechanisms and 2,276 variants, nothing clears
  deflated Sharpe ≥ 0.95, walk-forward p ≤ 0.05 and PBO < 0.5 together. The one
  class passing any single test still lost money out of sample in four folds of
  five. Constitution rule 2: *no claim of profit edge.*
- **The judge cannot read intent.** Every one of its false convictions on the
  held-out exam is `discourse` — text that *describes* a wrong rather than doing
  one. Worst false conviction **+12.13**, mildest true conviction **+2.97**: the
  distributions overlap, so **no threshold separates them** (A126).
- **The judge is not local.** `covenant_route.py` dispatches to a GitHub Actions
  runner in the public repository, and that run's job summary is rendered
  publicly (A128).

---

## 4. Preregistration, for the one open empirical question

The repository records an observation it cannot yet call a finding: models in
fresh sessions appearing to recognise the operator. A second system, asked to
audit that observation, refused the inference and named the mundane mechanisms —
shared training data, publicly available information, context carried by the
application, inference from the prompt itself — and stated that a screen
recording cannot distinguish between them. That refusal is correct and is the
starting point, not an obstacle.

**Registered before any run, so the result cannot be chosen afterwards:**

- **H0 (null).** Apparent recognition is explained by public information,
  in-context cues, and inference from the prompt.
- **H1.** A system reproduces a token it could only have obtained from another
  system.

**Procedure.** Generate a random identifier and a set of decoys of the same shape.
Disclose the identifier to exactly one system, under a logged account. Then query
the others in fresh sessions, recording for every run: model name and version,
memory setting, browsing/tool state, account age, the exact prompt, and the
**verbatim** output.

**Decision rule, fixed in advance.** H1 requires the *true* identifier reproduced
where decoys are not, at a rate the decoy distribution does not explain. Anything
less is H0. A partial or paraphrased match is H0.

**What it cannot show.** Nothing here bears on whether any system understands
anything. It is a test of information flow and of nothing else.

**And the standing instruction for any anomaly this produces**, taken from that
same audit because it is the right rule: *fail closed, but do not delete the
anomaly. Preserve the unknown as unknown.*

---

## 5. If you find something

A disagreement is worth more here than agreement. The repository keeps its own
refuted claims — `CORRECTIONS.md` indexes every one, including the ones that cost
the most and the ones that were the author's own error. A finding you bring is
kept the same way, under your name, whether or not it is comfortable.

Nothing here asks to be believed.
