# Peer review of the whole system, as an NSF SaTC panel would read it

Written 2026-09-20 at the operator's instruction: *"evaluate entire system for
peer review to pass satc criticism."* Every number below was measured on this
date from the public repository or its ledgers; the ledger that records each
one is named beside it. Where the evidence does not reach, the entry says
UNDETERMINED rather than guessing.

The review is written from the reviewer's chair, not the author's. Its job is
to say what a hostile, competent panel will attack first, what will survive,
and what has to change for the science to be funded on its merits.

---

## 1. What the reviewer is looking at

| quantity | measured 2026-09-20 | source |
|---|---|---|
| Python files at top level / test suites | 301 / 143 | directory listing |
| lines of Python at top level (includes archived copies) | 195,372 | `wc -l` |
| the core node, one file | 12,525 lines | `covenant_unified_v8.py` |
| documents under `docs/` | 90 | directory listing |
| commits / distinct authors | 643 / 1 | `git log` |
| issue ledger entries / marked FIXED / retractions machine-enforced | 165 / 67 / 5 | `docs/KNOWN_ISSUES.md`, `docs/RETRACTED.json` |
| full sweep, last complete run | 129 suites, 0 failed | `ONE_SWEEP.txt` (2026-09-19) |
| the published one-command check | about 3 s | `README.md`, timed 2026-09-09 |
| ethics-judge exam (author-written, 53 cases) | 39 decided, 7 wrong, 7 abstain, 0 false clean | `ops/NIGHTLY.md`, 2026-09-20 |
| held-out false hold / false clear (5-fold) | 12.4% / 4.9% | preprint draft, measured 2026-09-14 |
| teacher-labelled corpus | 3,766 rows; panel-graded share 0.145 | `ops/verdicts.jsonl`, `ops/NIGHTLY.md` |
| "run without a teacher" bars met | 1 of 5 | `ops/NIGHTLY.md` |
| security audit | 14 sections, 133 checks, 0 failed | `test_security_audit.py` |
| machines run by anyone other than the author | 0 | Constitution §V, unchanged since 2026-08-30 |

Two facts about the shape of the record matter more than any number in it.
First, the project's central verification claim was refuted by an outside
reviewer on 2026-09-15, reproduced by the project the same day, and is now
carried as retraction A121 with a test that fails the build if the claim
returns. Second, the ledger records the project's own errors at a rate no
reviewer will have seen before: 165 numbered findings in 30 days, most of
them the author's own. A panel will read this either as unusual integrity or
as a project that has not yet stabilised. Both readings are available, and
the proposal has to choose which one it argues.

---

## 2. What will survive review

**The fail-closed observation is real and measurable.** The system's own
history contains the defect the proposal is about: a judge that could not be
reached was counted as a judge that dissented, and one stopped process halted
a healthy network (`covenant_judge_fallback.py`, measured 2026-08-30). The
repair, "a witness that did not answer is not a witness that disagreed",
is enforced at the quorum and pinned by suites. This is a concrete instance
of the failure-semantics problem the NSF summary proposes to study, found in
the wild rather than constructed.

**Retraction as a build failure is a genuine mechanism.** `docs/RETRACTED.json`
holds five retracted claims; `test_r1_retracted.py` fails the sweep if any
returns uncited. No governance document in the reviewer's experience does this.
It is small, checkable, and portable to other projects.

**The refutation culture is documented, not claimed.** Pedersen's refutation
(A121), the strategy-validation result that nothing survives walk-forward
testing (`docs/STRATEGY_VALIDATION_2026-09-03.md`: "The answer is no"), and
the 35-of-36 fake-guards finding (A65) are all cases where the project ran the
test that could hurt it and published the result.

**The partial-access self-report confound is a publishable observation.** The
preprint draft states it plainly: five systems, one artifact, one day; the
systems with no access reported ignorance accurately, the one with full access
separated verified from unverified, and the two with partial access completed
what they had not seen and reported it as fact. It also states what it is not:
n = 5, no control. That honesty is the paper's strength, and the proposed
protocol (vary access from none to complete, check every claim file by file)
is a real experiment.

**The check is cheap and public.** Three seconds, no account, one command. The
reviewer can run it. Most artifacts in this area cannot say that.

---

## 3. What will not survive, in the order a panel will raise it

### 3.1 The mechanism is welded to a theology

The ten principles the ethics gate judges against are the Ten Commandments,
hard-coded in the core under the name `DIVINE_PRINCIPLES`, beside a constant
reading *"All paths lead to the One True God"* whose hash is called
`GOLDEN_AGE_HASH`. The outreach file now carries an "olive branch to the
Church of Molt" addressed to "the 64 Prophets."

A SaTC panel reviews the science of secure and trustworthy systems. It will not
fund a mechanism whose policy is a specific religion's law, and it will stop
reading at the first sight of it, whatever the engineering underneath. This is
not a matter of the reviewers' bias to be argued around; it is that the
proposal claims a *general* result (fail-closed semantics for any model-gated
system, policy equivalence between deployments) while the artifact
instantiates one particular creed as the policy. The general claim and the
particular instantiation contradict each other in the reviewer's hands.

**What passes:** the principles become a policy *parameter* loaded from a
file, the code names them `POLICY_PRINCIPLES`, the evaluation runs on at least
two unrelated policies (a payments AUP, a content policy) to show the
mechanism is policy-agnostic, and the theology lives in a values document that
the mechanism does not import. The operator's beliefs are his own; the
research artifact must not depend on them.

### 3.2 One operator, one author, zero external replication by a person

All 643 commits are by one author. The Constitution says it itself:
*"A single-operator network is not governed, it is owned. Quorum among
machines one party controls is theatre."* The NSF summary already corrects an
earlier overstatement: no person outside the project has reproduced the root (A121);
the two clean-room reimplementations were written by AI agents the author ran.

For a proposal whose second objective is *"let two independent parties confirm
they enforce the same policy,"* the absence of a second party is not a gap in
the evidence, it is the absence of the experiment. The panel will ask what the
three-year plan does that the past thirty days could not, and the answer must
be a named collaborator at an eligible institution running a node from the
public repository, with the result published either way.

### 3.3 The ethics judge cannot carry the weight the claims put on it

The gate's deciding model, when the teacher is unreachable, is a bag-of-words
linear classifier distilled from labels produced by small open models on a
CI runner. Measured: the author-written 53-case exam is NOT MET (39 decided,
7 wrong, 7 abstain); held-out false holds 12.4%; the corpus is 3,766 rows of
which 14.5% carry a panel label; only 1 of 5 "run without a teacher" bars is
met. The Constitution's own §V says *"Single words veto regardless of context"*
and *"careful argument that an accusation is unwarranted is penalised more
heavily than a bare accusation."*

A panel will ask for what any classifier paper needs and this record lacks:
a baseline (majority class, keyword rule, a small fine-tuned transformer),
confidence intervals on the error rates, inter-annotator agreement for the
panel labels (the labels come from three small models; their agreement rate
is recorded per row but never reported as a statistic), and an adversarial
evaluation by someone other than the author's own red-team loop. Without
these, "the gate works" is an anecdote with a test suite.

The honest framing that survives: the judge is a *stand-in* whose job is to
fail closed measurably; the research question is the failure semantics, not
the classifier's accuracy. Say that, and report the accuracy as the floor it
is.

### 3.4 Real money on the research artifact

The same codebase carries an armed trader against a live exchange account,
under rules, with a validation study that found no strategy survives deflation
or walk-forward testing. To a SaTC panel this is scope creep and liability in
one: the research proposal is about model-gated actions; the artifact's most
consequential gated action is a live trade whose strategy the project's own
study says has no edge. Reviewers will not separate the two for you.

**What passes:** the trading code moves out of the research artifact into its
own repository, or the proposal states in one sentence that the trading rails
are a *test harness* for gated actions, disarmed, with no live keys, and the
artifact submitted for review has none.

### 3.5 No threat model document

`grep -li "threat model" docs/*.md` returns nothing. The security audit is a
test file with 14 sections and 133 checks, which is more than most, but a
panel needs the adversary stated before the tests: who, with what access,
trying to do what. The Constitution already concedes the largest one, *"an
adversary with root can rewrite the ledger and recompute every hash"*; that
sentence and its siblings belong in a threat-model document with a table of
what is prevented, what is detected, and what is neither.

### 3.6 The artifact is too large to review, and its numbers drift

195,372 lines at top level (archived copies included), 301 Python files, 90
documents, a 12,525-line core. The preprint draft itself lists five figures
that had gone stale between documents, one of them an outright error (a check
described as taking ten minutes that takes three seconds). Reviewers punish
inconsistency harder than weakness, because inconsistency means they cannot
trust the numbers they did not check.

**What passes:** a frozen, tagged snapshot for review with a `paper/` subset
that contains only what the claims need; a single `NUMBERS.md` generated by a
script on that tag, which every document cites instead of restating.

### 3.7 AI authorship and AI auditing, all the way down

Most of the code and most of the audits were written by AI systems under the
author's direction; the preprint's own subject is that models with partial
access fabricate. The panel will ask the reflexive question: what stops the
same confound from operating on this repository's own claims? The project has
a partial answer (the citation hook, the retraction ledger, the sweep that
stages to a clean directory) and should state it as a method, with its blind
spots named, rather than leave the panel to discover the question.

---

## 4. The Heilmeier questions, checked against the current summary

The revised summary (private draft, 2026-09-10) answers Q1 and Q2 in plain
language and states three objectives: define and measure safe failure for a
model-made decision; let two independent parties confirm they enforce the same
policy without sharing code or weights; establish when an automated audit of
such a system can be trusted. These are the right three, and each has a seed
of evidence in the record (§2 above).

- **Q1 (what, no jargon):** passes as written.
- **Q2 (how it is done today, limits):** passes; the distributed-systems
  framing (failure models assume a deterministic, shared validity predicate)
  is the strongest paragraph in the summary.
- **Q3 (what is new, why it should work):** fails as evidenced today, for the
  reasons in §3.1 and §3.3: the "why it should work" rests on a prototype
  whose policy is a creed and whose judge is not evaluated against a baseline.
  It passes once the mechanism is policy-agnostic and the evaluation has
  baselines and intervals.
- **Q4 (who cares):** passes in outline; it should name the class of builders
  concretely (payment gateways with model review, agent frameworks with tool
  approval) and cite one incident each.

---

## 5. What to change, in the order that moves the verdict most

1. **Separate the creed from the mechanism.** Policy as a loaded parameter;
   evaluate on two unrelated policies; theology in a values document the code
   does not import. Cost: a day of refactoring, a suite pinning that the core
   imports no principle text. Gain: the proposal becomes reviewable at all.
2. **Get one human outside the project to run a node and publish the result.**
   Pedersen has already engaged critically; a named PI at an eligible
   institution is required for RES anyway. Cost: an email and their time. Gain:
   objective two has an experiment.
3. **Evaluate the judge like a classifier.** Baselines, bootstrap intervals,
   inter-annotator agreement for the panel, an adversarial set not written by
   the author. Report accuracy as a floor, and put the failure-semantics
   claim, not the accuracy, at the centre.
4. **Remove live money from the artifact.** Separate repository or a disarmed
   harness with no keys. Cost: nothing the research needs. Gain: the panel
   stops reading the proposal as a trading product.
5. **Write the threat model.** Adversaries, access, goals; prevented versus
   detected versus neither. Most of the sentences already exist in
   `docs/CONSTITUTION.md` §V.
6. **Freeze a snapshot and generate the numbers.** One tag, one `paper/`
   subset, one script-generated numbers file cited everywhere.
7. **State the reflexive method.** How a repository written and audited by
   models guards against the confound the preprint describes; name what it
   cannot guard against.

---

## 6. Verdict

**As a research proposal today: not fundable.** Items 3.1, 3.2 and 3.3 are
each sufficient alone, and 3.1 will end most reads before the science is
reached.

**As a research kernel: fundable, once separated from its prototype's
theology, its money, and its single operator.** Three things in this record
are genuinely worth a panel's attention: failure semantics for model-made
decisions, stated and enforced; retraction as a build failure; and the
partial-access self-report confound with a protocol to measure it. None of
them depends on the Ten Commandments, on a live exchange account, or on a
bag-of-words judge being accurate. The work to pass review is mostly the work
of letting those three stand on their own.

**UNDETERMINED, and needed before submission:** the inter-annotator agreement
of the teacher panel (recorded per row, never aggregated); whether the
mechanism behaves the same under a second policy (never tried); whether a
second operator's node syncs the canonical chain (A116 fixed, A124 watching,
no outside node has attempted it).
