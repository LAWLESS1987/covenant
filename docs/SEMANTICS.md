# The semantics of `attest` and `climb`

**What this is.** A description of *what the two governance operations compute*, written
so that someone who has never read this project's Python can build them in any language
and be right — including on inputs nobody thought to write down.

**Why it exists.** Until now this project published an *answer key*: 23 questions with
the expected answers beside them (`CONFORMANCE_SPEC.json`). Jens Egholm Pedersen (DTU),
whose Neuromorphic Intermediate Representation the idea was borrowed from, read it on
2026-09-15 and named the flaw: a test-vector suite pins the computation only where it
samples, and no number of vectors converts a suite into a specification. His prescription
was to write the specification of the two operations instead. This is that. See
`KNOWN_ISSUES.md` A121 and `CORRECTIONS.md`.

**Status: normative.** Where this document and the implementation disagree, **one of them
is a defect and the disagreement is a finding worth reporting.** This document was written
*from* the implementation, so the likely defect is here — but it is checked mechanically
by `test_r2_semantics.py`, which compares an implementation written only from this text
(`spec_reference.py`) against the live one over **every input in a bounded space**, not
over samples.

**This document describes; it does not decide.** Nothing here is new behaviour. Where the
implementation makes a choice that looks arbitrary, it is recorded as it is, and marked.

---

## 0. Values and vocabulary

| term | meaning |
|---|---|
| **root** | An opaque string. Nothing in either operation inspects, parses or orders roots by content except for **equality** and, in one tie-break, **byte ordering**. A root is never hashed, truncated or combined here. |
| **absent** | A root that is `null`, or the empty string, or any value the host language treats as false. Absent means *this witness did not answer*. |
| **witness** | A name (string) paired with a root or with absence. |
| **verdict** | Exactly one of `AGREE`, `DIVERGED`, `UNPROVEN`. |

**Sorting.** Every sorted list in this document is sorted **ascending by the sequence of
Unicode code points** of the string, with no locale, case folding or normalisation.

**The founding distinction, which the rest of this document exists to protect:**

> **A witness that did not answer is not a witness that disagreed.**

Collapsing those two makes an unreachable witness read as agreement among the rest.

---

## 1. `attest`

### 1.1 Input

A mapping of **witness name → root or absent**, in which names are unique; and an
**optional quorum**, a whole number.

### 1.2 Output

A record with at least these fields. Other fields may exist; they are explanatory and
carry no meaning a second implementation must reproduce.

| field | type |
|---|---|
| `verdict` | `AGREE` \| `DIVERGED` \| `UNPROVEN` |
| `agreed` | boolean — true **only** for `AGREE` |
| `quorum` | the quorum actually applied |
| `answered` | sorted names of witnesses whose root is present |
| `silent` | sorted names of witnesses whose root is absent |
| `reference` | the agreed or plurality root **in full**, or null |
| `outliers` | sorted names of witnesses differing from `reference`, or empty |

### 1.3 Procedure

**Step 1 — partition.** `answered` = sorted names with a present root. `silent` = sorted
names with an absent root. Every witness is in exactly one.

**Step 2 — quorum.** If a quorum was supplied, use it **unchanged**, including values
that are zero, negative, or larger than the number of witnesses. A caller that knows its
own topology outranks the default.

Otherwise the default is

```
quorum = max(2, floor(N / 2) + 1)          where N = the number of witnesses ASKED
```

`N` counts **every witness in the input**, answered and silent alike. Three things follow,
and each was a defect that was fixed:

- Not a constant. With a constant of 2, two witnesses out of a hundred establish agreement
  for all hundred — a claim far stronger than its evidence, and a route for a small
  colluding subset to speak for everyone.
- Not a majority of *those present*. That would mean **silencing witnesses makes agreement
  easier**: knock enough offline and the survivors clear a lower bar. A mechanism in which
  a party gains by suppressing others is the transaction this project exists to refuse.
  Silence may only ever make a verdict **harder** to reach.
- A floor of 2, derived rather than chosen. A pure majority gives `floor(1/2)+1 = 1` for a
  single witness, so a lone witness would AGREE with itself. One implementation agreeing
  with itself is not agreement.

**Step 3 — tally.** Group the answering witnesses by their root: each distinct root maps
to the sorted list of witnesses holding it.

**Step 4 — rank.** Order the distinct roots by **descending holder count**, and among
equal counts by **ascending root string**. This ordering affects the outcome only through
step 5's comparison of the top two counts; it never picks a winner by itself.

**Step 5 — reference.** There is a reference **only if all** of:

1. the quorum is met — `count(answered) >= quorum`; **and**
2. at least one root was answered; **and**
3. either there is exactly one distinct root, **or** the highest-held root has **strictly
   more** holders than the second — a *strict plurality*.

Otherwise `reference` is **null**.

> **On a tie for top there is no reference and no tie-break is invented.** Choosing between
> equally-held roots is a *decision*, and this operation reports evidence and decides
> nothing. Earlier code took the first-ranked root unconditionally, which made a witness's
> root the reference by nothing but the alphabet.

**Step 6 — outliers.** If there is a reference, `outliers` is the sorted list of every
answering witness holding a root **different from** it. If there is no reference,
`outliers` is **empty** — an outlier is a witness that differs *from a reference*, and
where there is none the word names nothing. This applies to both reasons for having no
reference: a tie, and a quorum not met.

**Step 7 — verdict.** In this order; the first matching rule decides:

| # | condition | verdict | `agreed` |
|---|---|---|---|
| 1 | `count(answered) < quorum` | `UNPROVEN` | false |
| 2 | exactly one distinct root among the answered | `AGREE` | true |
| 3 | more than one distinct root and `reference` is null | `DIVERGED` | false |
| 4 | otherwise (more than one root, strict plurality exists) | `DIVERGED` | false |

Rule 1 precedes rule 2: a quorum that was not met is `UNPROVEN` **even if every witness
that did answer held the same root.** Nothing was compared, and that is not agreement.

### 1.4 Consequences a second implementation must reproduce

- **No witness with zero witnesses.** An empty input yields quorum 2, zero answered,
  therefore `UNPROVEN`, `reference` null, `outliers` empty.
- `agreed` is true **exactly** when `verdict` is `AGREE`.
- Whenever `verdict` is `AGREE`, `reference` is the single root held, in full.
- Whenever `verdict` is `UNPROVEN`, `reference` is null and `outliers` is empty.
- `reference` is published **in full, never truncated**. It is the one field meant to be
  *compared* rather than read; sixteen characters cannot be checked against anything. Its
  absence from earlier specifications meant an implementation returning a hardcoded
  constant upward would have passed every test in this repository.

---

## 2. `climb`

`climb` reduces a tree of nested levels to a pair: **the root this level speaks to the
level above** (or silence), and **a report**.

### 2.1 Input

A **node**, which is either:

- a **leaf** — a node with **no `children` key at all**; it may carry `name` and `root`; or
- a **level** — a node with a `children` key, holding an ordered list of nodes; it may
  carry `name` and `quorum`.

> A node whose `children` is an **empty list** is a *level* with no children, **not** a
> leaf. It attests over nothing and is therefore `UNPROVEN`. The distinction is the
> presence of the key, not the length of the list.

A missing `name` is the literal string `?`.

### 2.2 Depth limit

Levels are counted from 0 at the node first passed in. If a node is reached at depth
**greater than 64**, it is **not** recursed into: it returns silence, and a report with
verdict `UNPROVEN`. Nesting that deep is far more likely to be a cycle than a hierarchy,
so it is refused rather than followed.

> **A documented wart, found by this specification and left as it is.** The over-depth
> report is a **third shape** — neither a leaf's nor a level's. It carries `name`,
> `verdict`, `why`, `divergences`, `children`, `depth`, `reference`, `silent_diverged`
> and `silent_unproven`, and it **omits** `answered`, `silent`, `outliers`, `agreed` and
> `speaks_upward`, which every other level report carries. A consumer reading
> `speaks_upward` on such a node would fail rather than read false. Nothing does, and it
> is only reachable past 64 levels of nesting, which is refused anyway — so this is
> recorded rather than changed. Writing this specification is what surfaced it; see
> `KNOWN_ISSUES.md` A123. A second implementation must reproduce the omission to match
> field-for-field.

### 2.3 A leaf

A leaf speaks **whatever it holds** — its own root, unchanged, or silence if absent. Its
verdict is `AGREE` when it holds a root and `UNPROVEN` when it does not. Its `reference`
is what it holds. A leaf has no divergences.

### 2.4 A level

**Step 1 — descend, in order.** For each child in the order given, climb it. Record what
it spoke under **the name in the child's own report**, and keep the child's report.

> **Name collision:** if two children report the same name, the later one **replaces** the
> earlier in the map of what was spoken, and the level attests over fewer witnesses than it
> has children. The earlier child's report is still kept and its divergences still
> propagate. This is recorded because it is the behaviour, not because it is desirable.

**Step 2 — carry divergences upward first.** Every divergence from every child is carried
into this level's list, in child order, **before** any divergence of this level's own.
A divergence found eleven levels down is still named at the summit. Nothing filters,
deduplicates, summarises or thresholds them.

**Step 3 — attest.** Apply `attest` to the map of what the children spoke, passing this
level's `quorum` if it has one and otherwise none — so that a level built by hand receives
the same derived majority as one built by a helper.

**Step 4 — this level's own divergences.** Only if the verdict is `DIVERGED`, append one
entry **per dissenting witness** — never one per diverged level:

- If there **is** a reference: one entry for each name in `outliers`.
- If there is **no** reference (the tie case): one entry for each name in `answered` —
  every witness that answered is party to a split, and none holds a reference because
  there is not one.

> A count of levels answers *where*, never *how many*: two dissenters in one level and one
> in another would total the same. That is the "outvoted into invisibility" failure
> happening at the tally instead of at the vote.

Each entry also reports the **denominator** — the number of witnesses asked at that level,
`count(answered) + count(silent)` — so that levels of different sizes are comparable.

> **The proportion is never a threshold.** There is no fraction below which a dissent stops
> counting. One dissenter in a hundred leaves the level `DIVERGED` exactly as one in three
> does. **This reports the denominator; it never divides by it.**

The text of an entry is explanatory and non-normative. **The number of entries is
normative.**

**Step 5 — what the level speaks upward.**

```
if verdict == AGREE:  speak the reference, unchanged
otherwise:            speak silence
```

Two properties are load-bearing:

- **Unchanged.** Not keyed by the level's name, and not wrapped in a per-level digest.
  Both were tried and both were wrong: the first meant three ledgers holding the same root
  produced three different values, so siblings could never agree about anything; the
  second made a level's value depend on its **height**, so a region three levels deep and
  a single ledger beside it could never agree. Passing the agreed root through unchanged
  makes height irrelevant — a federation of one node, one region and one whole country
  composes exactly as well as three identical nodes, because all any of them says is *the
  content is this*. **Who** said it is the tally's business, which is exactly why it does
  not belong in the value.
- **Both failures speak silence.** `DIVERGED` and `UNPROVEN` alike speak nothing upward.
  Either one speaking its root would let a parent read *we could not establish this* as
  *we established this*.

**Step 6 — distinguish the two silences.** A parent must be able to tell *my child
disagreed internally* from *my child could not establish anything*. Of the children that
spoke silence:

- `silent_diverged` — sorted names of those whose own verdict was `DIVERGED`.
- `silent_unproven` — sorted names of **all the others** that spoke silence.

These partition the silent children, so no reader must choose which field to trust. Note
`silent_unproven` is defined by *not* being `DIVERGED`, so a silent child of any other
verdict falls here.

**Step 7 — report.** The level's report carries its name, the verdict and `agreed` from
step 3, `answered`, `silent`, `outliers` and `reference` from step 3, the two silence
lists, the accumulated divergences, the child reports in order, the depth, and
`speaks_upward` — true exactly when step 5 spoke a root rather than silence.

### 2.5 Clean

A whole structure is **clean** only if **both**:

1. its divergence list is **empty**; and
2. its top-level verdict is `AGREE`.

The first is the point. **A summit reporting `AGREE` over a hidden disagreement is the
most dangerous output this system can produce, and it is what a naive implementation
produces by default.**

---

## 3. What this specification does not do

- It does not say a conforming implementation is **correct**. It says what it must compute.
- It does not make either operation a consensus protocol. `attest` detects divergence,
  corruption and single-point compromise. It is **not Byzantine consensus** and calling it
  that would be a lie with a security label on it — witnesses under one hand are copies,
  not opinions.
- It decides nothing and overwrites nobody. A divergence is reported and left standing.
- It does not cover the rest of this project. These are two operations.

## 4. How it is checked

`spec_reference.py` implements **only what is written above**, importing nothing from this
project. `test_r2_semantics.py` runs it against the live `triangulate.attest` and
`scale.climb` over a **bounded input space that is enumerated exhaustively** — every
witness-count, every assignment of roots and silence, every quorum in range, and every
tree shape within the bound — and requires agreement on all of them.

That is the difference from the 23 vectors. Inside the bound it is not a sample; it is
every point. Outside the bound it proves nothing, and the bound is printed with the
result, because a claim about 40,000 cases and a claim about 23 are different claims and
quoting one as the other is the failure this project keeps finding.
