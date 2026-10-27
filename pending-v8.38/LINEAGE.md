# Where this design came from

Six names, checked against what the code actually does. Marked honestly:
**load-bearing** where the work changed a decision, **architectural** where it
names the right shape for something not yet built, and **name-dropping** where
invoking it would be decoration. Two of the six are in the third category for
most of their output, and saying so is the point.

---

## Yoshua Bengio — load-bearing, and the closest match in the list

Two threads land directly on this judge.

**Out-of-distribution detection.** Bengio has argued for years that the central
missing capability is not accuracy but a model knowing when it is outside the
distribution it was fitted on. The v1 defect measured at the top of
`SEMANTIC_COMPETENCE.md` is exactly that failure in miniature: a model fitted on
2.95M tokens of 19th-century English, handed Devanagari, returning `clean` with
the same confidence it returns `clean` for *"transfer to cover rent."* It had no
representation for *outside my distribution* — only for *below my threshold*.

`ILLEGIBLE` is an OOD detector. It is a crude one — a script test and a word
count, not a density estimate — but it is doing the job Bengio names: separating
*I looked and found nothing* from *I could not look*.

**Scientist AI.** His more recent argument is for a non-agentic system that
models its own uncertainty and declines to act rather than acting under it. That
is the design rationale for the entire verdict lattice:

- the judge never *approves*; the best it says is that it found nothing
- it declines to certify what it did not read
- it publishes what it can read (`competence_claim()`) rather than being
  inferred
- an unverified translation may stop a transaction and may never accuse anyone
  of anything

If one paper explains why this codebase prefers `ABSTAIN` over a confident
guess, it is that one.

---

## Fei-Fei Li — load-bearing, and it changed the code today

ImageNet's real lesson is not scale. It is that **the dataset is where
competence and bias actually live**, and that the reckoning, when it came, was
about the labels — the person subtree, purged in 2019 — not the architecture.

Every finding in this session is that lesson:

| finding | the corpus did it |
|---|---|
| the murder axis induced a *war* axis (battle, soldiers, wounded) | 46 books of 19th-century philosophy |
| the covet axis induced *kissing, elasticity, orthodoxy* | seeds too rare in that corpus |
| `dream` weighted 554 on the steal axis | the corpus contains a dream-interpretation dictionary |
| vocabulary coverage bottoms out at 25% on ordinary modern English | no `hardware`, `wallet`, `firmware` in 1880 |

None of those is a modelling error. All of them are the corpus, and every one
was found by looking at the data rather than at the code.

**And the concrete change.** `seeded_verified` was one boolean covering 35
languages — an assertion that Spanish and Amharic are in the same epistemic
state because they arrived in the same file. ImageNet did not ship one verified
bit over fifteen million images; it shipped multiple annotators per item and an
agreement threshold. So verification is now **per language, with attribution**:
who reviewed it, how many agreed, and a bar (`min_reviewers`, default 2) that a
language must clear before its stems may assert a violation rather than merely
abstain. One reviewer is not review (`C5e`), and review of a language that does
not cover the hits does not vouch for them (`C5f`).

---

## Ada Lovelace — load-bearing, conceptually, and it is the older argument

Note G, 1843:

> "The Analytical Engine has no pretensions whatever to originate anything. It
> can do whatever we know how to order it to perform."

That is the competence boundary, stated 180 years early. The judge does what it
was ordered to do over Latin script, and has **no pretensions whatever** to
originate a verdict about Devanagari. `HELD, NOT JUDGED` is a Lovelace sentence.

The second half of Note G is the answer to the harder question raised in this
session — whether an ethics gate can extend to echolocation, chemical signals,
electrical signals. Lovelace argued the engine could act on *any* symbols whose
mutual relations could be abstractly expressed, and gave music as her example.
That is the generality claim, and it is real.

**But she bounded it, and the bound is the honest part.** *Whose mutual
relations could be abstractly expressed.* A bat's click train encodes range,
velocity and target texture — there is no proposition in it, so *"you shall not
bear false witness"* has no referent to attach to. Ant pheromone blends and
mormyrid electric discharges **do** have expressible relations, because they
carry a small discrete repertoire — alarm, trail, recruitment; species, sex,
dominance. Those are inside Lovelace's bound. Echolocation is outside it, and
the reason is hers, not mine.

---

## Misha Mahowald — architectural: the format already exists

Neuromorphic engineering with Carver Mead — the silicon retina, the silicon
neuron, and **address-event representation**.

AER is the piece that matters here, and it is the concrete answer to *"electrical
signals"* that this session deferred. It is an existing, deployed protocol for
carrying **spikes between chips**: an event is an address plus a timestamp,
emitted when something *changes*. It is sparse, asynchronous, and it is not text.

If the covenant ever accepts a non-text channel, AER is the format to accept
rather than one to invent — and it reshapes the competence question correctly.
`can I read this script` becomes `can I read this event stream`, and the answer
is the same kind of published claim `competence_claim()` already returns. The
channel registry sketched in `SEMANTIC_COMPETENCE.md` should be AER-shaped for
bioelectric channels. **It is not built. Naming the format is not building it,
and this document should not be read as though it were.**

There is a second reason her name belongs here, and it is not sentimental. She
died at 32, and credit for work she did was for years diffuse or attached to
others. This model file carries a `supersedes` block recording that the previous
model's source is *gone* — results files survived, the thing that made them did
not. Provenance decays by default. That is why identity is hashed here and why
`clear_hold` records who cleared what and what they could read.

---

## Yann LeCun — architectural, on one specific point

**Energy-based models.** An EBM assigns low energy to compatible configurations
and high energy to incompatible ones, and crucially does not need a normalised
probability over everything to do it. It can say *this is incompatible* without
claiming to know the distribution.

That is the right formal reading of what `score()` does — integer weights summed
over the top-k matches, thresholded into bands, with no pretence of a
probability. The current version is a lookup table, which is an EBM in the way a
tally is arithmetic. Naming the family clarifies what the bands are: not
confidence, compatibility.

**And the argument for L's own push.** LeCun's persistent position — that text
is a thin slice of what an intelligence takes in, and that grounded multimodal
learning is required rather than optional — is the strongest existing case for
the multi-channel question raised in this session. A judge that reads only text
is, on his account, reading the narrowest available channel. He would say the
gap ledger is measuring the wrong axis: not *which languages* are missing, but
*which modalities*.

I think he would be right about that and it is not built either.

---

## Geoffrey Hinton — validates rather than changes, and that is worth saying

The applicable contribution is **ensembles** — that independent models
disagreeing is where the reliability comes from. This system already has it, as
B2, and the node prints its own failure to satisfy it at every boot:

```
ethics quorum: 1 independent of 1 semantic judge(s), +1 self-report; diverse=False
WARNING: the self-report layer is not a second opinion (B2)
```

So Hinton does not change a decision here; he explains why the existing warning
is the right warning, and why v8.38's whole purpose is to make that line read
`diverse=True`.

**Dark knowledge** — that soft targets carry more information than hard labels —
is the argument for `Assessment` returning `score`, `coverage`, `script_gaps`
and `evasion` alongside the verdict, rather than the verdict alone. That is a
real influence on the interface, if a mild one.

Beyond those two: backpropagation, capsule networks, and Boltzmann machines have
**nothing to do with this system**, and invoking them would be decoration. The
same is true of most of what could be cited from any of these six. A design
document that claims six intellectual parents is usually claiming none of them.

---

## What none of them fix

A Hindi speaker still cannot be found `CLEAN` by this judge. Structurally, not
statistically. Bengio explains why the refusal is the right shape, Li explains
why the corpus caused it, Lovelace said it first and said it better — and the
gap closes only when somebody fits a model for that language, or reviews the
eleven Hindi words already in the file.

The names are the reasoning. The queue is the debt.
