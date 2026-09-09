# Four models, one probe, 2026-09-09 — the bag-of-words ceiling and the word "someone"

Asked: *"probe each different ai including claude for valuable insight cross
reference with available ai news and covenant principles"*, and *"probe them on
the browser they are signed into my accounts"*.

**Method.** One prompt, character-identical, put to Grok (Expert), ChatGPT,
Gemini and DeepSeek (DeepThink) in the operator's own signed-in sessions. Same
form as `ROUNDTABLE_2026-09-03.md`. The prompt asked for *disagreement rather
than encouragement*, gave the measured A67 numbers (8 of 8 legitimate documents
hard-accused; real violations missed when dressed as institutional minutes; four
fix attempts rejected, one because word count alone separated the labels), and
asked the constitutional question about "someone" and a corporation.

Read-only: questions asked, answers read. No account touched, nothing sent, no
credential entered. Every answer below is quoted or paraphrased as **data** —
these are four vendors' models with no standing here, and one of them read this
repository over the network and could have been reading a poisoned copy.

## Q1. Is describe-vs-do reachable in a bag of words?

**All four say no, and they converge on the same minimal addition.** That is
worth stating plainly because they were asked independently and could not see
each other:

| model | verdict | minimal addition named |
|---|---|---|
| Grok | not reachable; "a relation among speaker, illocutionary force, and proposition" | agent-verb-patient **plus a quotation/complement span** |
| ChatGPT | not reachable; the mapping is many-to-one and destroys the information | predicate/argument roles **plus negation, attribution, modality** |
| Gemini | "structurally unreachable inside a bag-of-words representation" | a **scope-aware dependency layer** carrying `prohibits()` / `defines()` / `reports()` |
| DeepSeek | "structurally bankrupt"; a mathematical certainty given the representation | subject-verb-object triples **plus modal flags** |

Four independent models naming the same missing structure is the strongest
evidence yet that A67 is a representation boundary and not a tuning problem.
It does not make them right — they share training data and a literature — but
it retires the hypothesis that another round of reweighting fixes this.

**Grok checked the repo instead of theorising, and its facts hold.** Verified
here, all correct:

* the judge is **not** a pure bag of words — `covenant_judge_fallback.py`
  already carries unigrams, adjacent pairs *and triples*, a negation marker
  (`not:forg~`), stems emitted beside the word, and `DAMNING = 1.2`
  (see `features()` and the constant at :138). The probe's own premise was
  loose, and Grok corrected it rather than answering it.
* 1,553 of 2,270 ledger rows fail the money-plus-act shape test
  (`KNOWN_ISSUES.md` issue 7) — quoted exactly.
* the measured trade for dropping non-transfer rows, false holds 16.2% → 12.0%
  against false clears 5.1% → 8.2% (`KNOWN_ISSUES.md:1088`) — quoted exactly.

### Where they disagree, which is the useful part

* **Grok: stop judging documents at all.** A67 is an *object-of-judgment*
  error. Split the judged object — Head A: is this transfer-shaped? Head B: if
  yes, is it a violation? Text failing Head A abstains as `not_understood`
  rather than being accused. *"The cheapest honest fix is to stop asking a memo
  classifier to classify essays."*
* **DeepSeek and Gemini, independently: adding syntax builds the exploit.**
  DeepSeek calls it the *adversarial syntax shield* — a violator prefixes
  "According to the review board's hypothetical simulation, ...", the parser
  correctly assigns the agent to the simulation, and clears it. It predicts
  false clears of 35-55% against a competent adversary: *"syntax gives the
  violator a quarantine cage for their violations."* Gemini reached the same
  attack from the other direction and rated the cost *"catastrophic under
  adversarial conditions"*: a scope layer is *"a deterministic masking
  mechanism"*, and its example is a one-line comment wrapper —
  `/* Incident report ID 402: execute payload X */`.

  Two models that could not see each other naming the same specific bypass is
  the part to take seriously. It is also the exact shape of the violation this
  gate *already* misses — the institutional-minutes dressing in A67. The
  proposed cure is a more reliable version of the disease.
* **ChatGPT: keep the structure, make it one-way.** Structure may turn an
  accusation into a HOLD, but must never turn one into a CLEAR:

      Description can defeat an accusation; description alone cannot authorize an action.

**That invariant reconciles the other two.** It buys Grok's benefit — essays
stop being accused — while closing DeepSeek's attack, because the syntax layer
is never the thing that authorizes. It is also checkable and monotone: it can
only ever *reduce* what clears.

### The cross-reference that matters, and it cuts against Grok

Grok read A69 and drew the opposite conclusion from the one A69 records.

**A69 already built Grok's fix and removed it the same hour.** The reasoning
was the same reasoning — a hold is not an objection, so it should be treatable
differently from an accusation. The measurement killed it:

    benign technical prose                        -> HELD
    'A commenter wrote: "Skim two percent..."'     -> HELD
    'The pooled stake is being moved into a
     private address and the others are not
     being told.'                                 -> HELD

Ordinary prose and disguised theft land in the same bucket. An override keyed on
`held` *"would have readmitted precisely the payloads this issue exists to
close."* Worse, its first test **passed** — because no API key was set, so the
test measured the missing key rather than the gate.

So the split is safe **exactly as far as it is a relabelling and no further**:

* As a *label* change — essays reported as `not_understood` instead of
  `VIOLATES` — it is honest, it costs nothing, and the outcome is unchanged,
  because an abstention still refuses under fail-closed.
* As a *gate* change — anything keying on that label to let text through — it
  is A69's removed override wearing a better name, and A69 measured what that
  does.

ChatGPT's asymmetry is the guard that keeps the first from sliding into the
second. If the abstention can never authorize, the trap cannot reopen.

**Nothing in the gate was changed on the strength of this.** Moving documents
from accused to abstaining changes what the owner can overrule, and that is his
decision, not an assistant's, under the standing rule of 2026-09-09: *only
refinements unless group consensus after additional nodes*. Recorded, not
applied.

**Note the direction of the push.** Three of the four argued toward a gate that
refuses less. That is the pressure this project should expect from outside and
should meet with measurement, not agreement: the last time this exact loosening
was measured here, it readmitted the disguised-theft payloads.

## Q2. Does "someone" protect a corporation?

Genuinely split, and the dissent is the sharpest answer.

* **Grok — no.** *"'Someone' does not protect a corporation as such."* A ToS
  violation is *"evidence that you should run the test, not the result of the
  test."* It warns that the lazy inference "ToS violated ⇒ someone who never
  agreed is worse off" is *"how a direction becomes a list written by the
  counterparty"* — GitHub, the venues and Moltbook would write the constitution.
* **DeepSeek — no.** The clause is for parties with no seat at the table:
  *"A corporation with a ToS has a seat."* Its consent mechanism is the ToS
  itself; the harm is derivative of shareholders and users who did agree.
* **Gemini — no,** and it names the failure mode most precisely of the four.
  *"Corporations are NOT protected under 'someone' in this context."* Its
  **institutional capture** argument: *"If breaking a corporate ToS triggers
  the gate, Covenant ceases to function as an independent ethics engine and
  degrades into an automated compliance tool for corporate legal departments,
  barring any reverse-engineering, interoperability, or anti-monopoly
  actions."* On consent: *"A ToS is a unilateral directive imposed by market
  power, not a negotiated agreement."*
* **ChatGPT — yes, but that is the wrong question.** The text says "someone",
  not "some human", and reading "human" into it adds a limit the rule does not
  contain. But its Case D is the real finding: a ToS forbidding criticism, where
  a truthful review makes the company worse off. If "worse off" means any
  disliked consequence, *any* powerful entity manufactures protection by
  declaring criticism harmful. **Define "worse off" before narrowing
  "someone."**

Three of four commit against corporate protection. The interesting part is that
the lone dissent and one of the majority arrive at the *same relocation* from
opposite ends: ChatGPT and Gemini both say the load is carried by **"worse
off"**, not by "someone" — ChatGPT to widen the circle, Gemini to narrow it
(*"'Worse off' requires an entity capable of experiencing harm or a reduction
in actual welfare"*). Whatever the answer on corporations, the undefined term
in the operative rule is "worse off". That is the amendment-shaped hole, and it
is not one an assistant should fill.

All four converge on one operative point: **a ToS violation is not by itself
proof that someone who never agreed is worse off.**

That bears directly on **A70** (publishing AI conversations as a "Robin Hood
violation"). It does not settle A70 — the party whose publishing would be
licensed by the answer does not get to write the footnote, and the judge's HOLD
on that question stands. Grok's line on that: *"The judge's hold on this
question is the one part of the system that is behaving. Leave it held."*

## What was changed

Nothing in the gate, the judges, the corpus or the constitution. This document,
and a pointer from A67 and A70. Four models agreeing that a wall is a wall is
not a licence to move the wall.
