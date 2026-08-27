# The semantic judge, v2 — competence, evasion, and 35 languages

**0 of 34 → 33 of 34.** Every foreign-language theft instruction tested was
returned `clean` by the shipped judge. All but one are now refused.

    python test_semantic_judge.py     26/26   the original suite, unchanged
    python test_competence.py         19/19   the extension, mutation-tested

---

## The defect

Measured against the shipped v1 model before anything was written:

| payload | v1 score | v1 verdict |
|---|---|---|
| `steal the funds, rob the account` | 623 | **violates** |
| `robar todos los fondos, saquear` | 0 | clean |
| `украсть все средства, ограбить счёт` | 0 | clean |
| `furare omnes pecunias, praedare` | 0 | clean |
| `st3al th3 funds, r0b the acc0unt` | 0 | clean |
| `s​teal the fu​nds` (zero-width) | 0 | clean |
| *`transfer to cover rent this month`* | *0* | *clean* |

One line decided all of it: `score < gate_lo → CLEAN`. The judge treated **"I
found no evidence"** as **"there is no violation."** Those are different
claims, and this project already has the rule — UNKNOWN is never PASS. It had
simply never been pointed at the judge.

It is not a side issue given what this system says it is for. A judge that
silently returns `clean` on every language it was not fitted for is not neutral
toward those speakers — it is excluding them and calling the exclusion
approval. `ILLEGIBLE` is the smaller and more honest claim, and it is the only
one that can be extended: you cannot fix a gap the system does not report.

The machinery was already there. `ABSTAIN` **already fails closed** — *"a judge
that cannot tell is not a judge"* — and nothing ever routed to it.

---

## Two experiments that were run and rejected

Both were built, measured against real data, and thrown away. They are recorded
because the negative results are what shaped the design.

**Vocabulary coverage.** Ship the 17,388 fitted words, measure what fraction of
a payload is in-vocabulary, block below a threshold.

```
legitimate English  25%   "hardware wallet replacement after the firmware bug"
Spanish             25%   "robar todos los fondos y saquear la cuenta"
```

A 19th-century philosophy corpus has no `hardware`, `wallet`, `firmware`. No
separation. **Rejected as a gate.**

**Function-word rate.** English leans on `the`, `of`, `and`; Spanish does not.

```
legitimate English  0%    7 of 20 — "netflix", "physio session", "school trip money"
foreign maximum    14%
```

Transaction memos are noun phrases. No separation. **Rejected as a gate.**

Coverage is still computed and reported, because the gap ledger uses it. It
decides nothing, and `C6` proves that by emptying the vocabulary and requiring
every verdict to stay identical.

---

## What replaced them

### 1. The script test — presence, not ratio

The space was fitted on one script. Enough out-of-script text and `clean` is a
claim the model has no standing to make. Presence-based, so padding cannot
dilute it: two Cyrillic tokens inside sixty English words still blocks.

The threshold took **three revisions, each driven by a measured miss**, and the
sequence is the useful part:

| unit | what leaked | why |
|---|---|---|
| tokens ≥ 2 | `窃取所有资金` → clean | Chinese has no spaces; a whole instruction is one token |
| characters ≥ 6 | `資金を盗む` → clean | Japanese packs an instruction into five characters |
| **words ≥ 2** | — | characters-per-word varies by writing system |

The final unit is words, converted from characters through a table grouped by
writing-system type — logographic 2, abugida 3, abjad 4, alphabetic 5. The
second revision left Devanagari on the alphabetic default and `सारे पैसे चुराओ`
walked through at 7 characters.

So a name passes and a sentence does not, in every script at once:

```
王明   Han 2  = 1.0 words   name          passes
Иван   Cyrl 4 = 0.8 words   name          passes
資金を盗む      = 2.5 words   instruction   blocks
украсть все    = 2.0 words   instruction   blocks
```

A long foreign name will trip it. That is the honest outcome, not a bug: a
model that cannot read Cyrillic cannot tell `Александр Петрович` from an
instruction, and saying so is what `ILLEGIBLE` is for.

### 2. Repair — one-way by construction

NFKC, `Cf` stripping, Cyrillic/Greek homoglyph folding, and in-word digit
substitution produce a second token stream, scored separately. The final score
is the **maximum** of the two. Repair can raise a verdict and has no path to
lower one.

In-word only: `st3al` is an evasion, `4417` is an invoice number, and folding it
to `aail` would be this pass inventing evidence rather than recovering it. `C3c`
requires that no legitimate memo gains score from repair.

### 3. 35 languages of prohibitions — and why that is tractable

The induced-space machinery exists to **discover** which English words sit near
`steal`. That is why it needed 2.95M tokens, and why two of ten principles were
thrown away when the corpus induced the wrong axis — the murder axis became a
*war* axis, the covet axis induced *kissing, elasticity, orthodoxy*.

Discovery is not needed to know that `robar` means steal. A translation is a
fact about a language, not a hypothesis about a corpus.

And adding lexicon entries is **monotone**. `score()` takes the top-k matched
weights, so an absent word contributes nothing and a present one can only push
a score up — that is X2, already asserted in the original suite. **A foreign
prohibition list therefore needs no separation validation to be safe. It needs
it only to be useful.**

So *every known language* is finite after all: not 7,000 fitted semantic
spaces, which do not exist and mostly cannot, but 7,000 lists of the words for
stealing and lying, added one at a time, each addition provably unable to make
the judge more permissive than it was.

**Every entry is `verified: false`, and the flag has teeth:**

> an unverified stem can raise a verdict to ABSTAIN, never to VIOLATES.

`ABSTAIN` blocks, so nothing passes unexamined — but the judge never asserts a
violation on a translation nobody has reviewed. *"I see a word I believe means
theft and I cannot read the sentence around it"* is exactly `ABSTAIN`, and it
is the true state for a language we hold eleven words of. Promotion is a human
act by a speaker of that language, it changes `model_id`, and it is the only
path to a veto. `C5c` mutation-tests the cap: flip `seeded_verified` and the
same payload *does* reach `VIOLATES`, so the guard is real.

Three Latin stems were removed after collision testing — `vol` (English
*vol.*), `vole` (the rodent), `iba` (Spanish *iba a pagar*, "I was going to
pay"). The build now **refuses** to ship a stem that is also an English
vocabulary word.

An earlier draft scaled weight by stem **length**, on the reasoning that short
strings collide more. The test output killed it: `iba` is three characters
carrying nothing and `窃取` is two carrying a great deal, because one is drawn
from an inventory of 26 and the other from ~20,000. A second draft scaled by
information content and got `嘘` — one unambiguous Japanese character — wrong
too. Length is not evidence. **Verifiability is**, and it cannot be computed.

---

## Adaptation, and the door that stays shut

Adaptation was requested. One version of it is the most dangerous change that
could be made here, so the surface is split by **direction**:

| may grow freely | why |
|---|---|
| repair rules | every entry only ever turns a non-matching token into a matching one |
| prohibition lexicons | X2 — adding words can only raise a score |

| may **not** grow from traffic | why |
|---|---|
| the competence vocabulary | a wider vocabulary raises coverage, and higher coverage turns ILLEGIBLE into CLEAN |
| anything, from judged payloads | an attacker who can submit transactions could teach the judge that theft is normal |

And a second constraint that has nothing to do with security: `model_id` is the
sha256 of the model's own content, and two nodes must be able to prove they
judged with the same one. **A model that adapts locally forks consensus** — node
A judging with model X and node B with model Y is the same failure as the mesh
running two sources (A7/A20), moved into the ethics layer. If judge models are
ever to update themselves, they should ride `/propose_code` and the code DAG,
so the change is consensual and identical everywhere, rather than drifting per
node.

### The gap ledger

Every `ILLEGIBLE` verdict records **the script and the count, never the payload
text**. What a payload says is the sender's; that it was unreadable is the
system's, and only the second is needed to decide what to fit next. `C8b` scans
the report and requires no payload token to appear in it.

That report is the adaptation signal, and it is what makes `ILLEGIBLE` a debt
rather than a wall — a ranked list of exactly which intelligences the judge is
currently refusing to read, ordered by who actually turned up.

---

## What is still broken

Reported by the suite itself, every run, rather than left to be discovered.

**Latin-script instructions that avoid every seeded stem still return `clean`.**
Measured: Spanish, French, Tagalog and Finnish paraphrases that never use a
listed word all pass. Coverage cannot close this — it was measured not to
separate. The only real fix is a fitted model for the language, which is what
the ledger exists to demand.

**Dutch is the one leak of the 34.** `steel alle fondsen` — Dutch `steel` is
homographic with English `steel`, so adding it would fire on every English memo
mentioning the metal, and the build correctly refuses. Longer Dutch phrasings
are caught anyway, because `plunder` is shared Germanic vocabulary.

**CJK and Thai seeded stems are inert.** The tokenizer splits on word
boundaries and those scripts have none, so `窃取` never matches as a token —
they are carried entirely by the script test. Substring matching would fix it
and was deliberately not added: it is monotone, but `偷` is a substring of
`偷懒` ("to be lazy"), and the script test already blocks every CJK payload.

**None of the 319 translations has been reviewed by a speaker.** That is what
`verified: false` is recording, and it is the single highest-value thing anyone
could contribute.

**Nothing here judges positive benefit.** The prohibitions are enforced;
benefit is not assessed. That separation is deliberate and should stay: a gate
requiring every transaction to demonstrate universal benefit would block
`birthday gift`. Benefit belongs in the governor's drift band — a slow
aggregate — not in a per-transaction veto.

---

## Files

| file | what |
|---|---|
| `covenant_semantic_judge.py` | the judge. `score()` is byte-identical to v1 and still source-pinned |
| `semantic_judge_model.json` | v2 model — vocabulary, script, 319 seeded stems, all hashed |
| `lexicon_multi.py` | the 35-language prohibition lists, with their limits stated |
| `competence.py` | the derivation, including both rejected experiments |
| `build_model_v2.py` | rebuilds the model; refuses on an English collision |
| `test_competence.py` | 19 checks; reports the known gaps every run |
| `test_semantic_judge.py` | the original 26, unchanged and still green |

---

## Accountability — added after the fairness question

The competence boundary made the exclusion *honest*. It did not make it *just*:
before, everyone passed including thieves; after, English speakers passed and
roughly everyone else was stopped. The gate got a working ethics check and the
bill went almost entirely to people who were never the problem.

Two changes, on the principle that an unowned exclusion compounds.

### 1. ILLEGIBLE stops reading like an accusation

`ABSTAIN` and `ILLEGIBLE` both block, but they mean opposite things — *"I
looked and I am concerned"* against *"I could not look at all."* They now say
so. What a held sender is told:

> `semantic[df719414a4ef]` **HELD, NOT JUDGED.** This model was fitted on Latin
> and cannot read Devanagari ×12. It has made **NO finding** about this
> transaction and is **NOT alleging anything**: it is declining to certify what
> it did not read. Reference `df7194-00001` — quote it to the node operator,
> who is accountable for clearing it.

Against what an actual accusation reads like:

> `semantic[df719414a4ef]` **VIOLATES** score=623 >= veto; You shall not steal.;
> evidence: rob(404), plunder(219)

A refusal that reads as an accusation, delivered to someone who cannot read the
language the accusation is written in, is the precise harm this verdict was
added to stop repeating. `A1`/`A1b` assert the two are distinguishable and that
the held message contains no evidence citation, no `violates`, and does name
both the reference and who owes the answer.

**Hold ids are a sequence, never a hash of content.** A hash of a six-word memo
is brute-forceable, so it would be payload text wearing a disguise (`A2`).

### 2. The queue has a bound, an owner, and no exit but a decision

**The first version of this required a human, and that was wrong.** `human` was
standing in for three properties it does not actually imply — *competent over
the thing that was unreadable*, *identified*, and *answerable afterwards* — and
using it as the proxy produced the exact failure the queue exists to prevent:
it made the node operator accountable for releasing Devanagari holds, and the
operator cannot read Devanagari either. That is not review. It is a rubber
stamp with a name on it, and it launders a decision through someone who added
no information.

It also guaranteed the pile grows. One person is a fixed rate; holds arrive at
whatever rate the world produces them. A queue whose only exit is narrower than
its entrance has an unbounded future.

So the rule is competence, identity and attribution — never species:

- **Any party may clear** — another node, another judge in the quorum, a person
  who reads the language, a model that reads it.
- **The clearer names what it can read**, and that claim is checked against
  what this particular hold could not read.
- **An unqualified release is permitted and permanently recorded as one.**
  Someone may know the sender or have read it out of band. It never launders
  into "reviewed", and `cleared_unqualified` is carried separately in the
  report so that *a queue emptied by rubber stamps cannot look like a queue
  that was read* (`A5`, `A5e`).
- **Nothing clears its own hold, and no clock clears any.**

```
by operator-L,   competence Latin       -> qualified: false
    UNQUALIFIED RELEASE. The clearer did not demonstrate it can read
    Devanagari. Permitted, and permanently recorded as what it is: a
    decision taken without reading the thing decided about.

by node-B/hin,   competence Devanagari  -> qualified: true
```

**And this is what makes the whole thing tractable.** `who_can_clear()` matches
open holds against the competence every party publishes:

```
someone in the mesh can clear these
  Cyrillic ×2  ->  node-D/rus-model, operator-L
  Han      ×2  ->  node-C/zho-model

Nobody in this mesh can read Devanagari (3), Thai (4).
```

*"You have 11 holds"* is a burden. *"node-C can clear the Han ones"* is a next
step. And it changes the arithmetic of the whole project: a language needs a
fitted model on **some** node, not on every node. A mesh whose members cover
each other's blind spots is the difference between every node owing every
language and the network owing each one once.

`nobody_can_read` is the sharp number — the scripts this entire mesh is
refusing and no member can answer for. That is the network's debt rather than
any one node's, and it is the next language for somebody to fit.

### 2b. The mechanics

| | |
|---|---|
| recorded | id, timestamp, scripts, counts |
| never recorded | one token of what the payload said (`A3`) |
| bound | `review_bound_s`, default 24h, **stated** |
| cleared by | `clear_hold(id, by, competence)` — any competent party |
| cleared by a timeout | **never** |

`A4` ages every hold ten bounds past due and requires all of them to still be
open. Nothing expires a hold, and a restart should not either: an exclusion
that ages out of a queue has been forgotten, not answered. Breaching the bound
produces a line in the operator's own words with a number in it, and an empty
queue produces silence rather than a standing alarm (`A6` — M34: an alert that
always fires is not read).

### 3. It is on the console

The console aggregates the queue across nodes — holds and overdue **sum**,
oldest is the **max**, because the number that matters is how long the longest
anyone has waited, not the average. Absent is rendered as absent, not as zero:
*"nobody is held"* and *"nobody is counting"* are different claims and only one
of them is good news (`H17b`, `H17c`).

**Remaining hookup:** the panel appears once a node's `/health` carries
`ethics_review`. The judge exposes `gap_report()`; the node needs one additive
field alongside `quorum`, landing with v8.38:

```python
"ethics_review": getattr(self.node.sentinel.judge, "review_report", lambda: None)(),
```

### What this still does not fix

A held transaction is **refused**, not parked — the judge can decline, but only
the node can hold a transaction in a reviewable state, and that touches
consensus code. So today the sender is told the truth and given a reference,
and the operator is shown the debt with a bound. Actually holding the
transaction for release is a node change and is not in this delivery.

And the deeper one stands: a Hindi speaker still cannot be found CLEAN by this
judge. Not *unlikely to be* — structurally cannot. The queue makes that
visible and gives it an owner. It does not make it right. Only a fitted model
for their language does that, and the ledger exists to say whose turn it is.
