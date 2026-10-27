# The semantic judge — v8.38, prepared and held

**Status: built, 26/26 ×2, full sweep green on Linux, and DELIBERATELY NOT
SHIPPED YET.** It lands after the nodes come up on v8.37 and the win32 sweep
runs. Changing the ethics gate in the same window as an unfinished propagation
is the W1/M26 shape, and the sweep is the only thing that has ever caught the
Windows-only defects.

---

## What was asked, and what was actually there

*"Replace the mock judge with the semantic one we made."*

The instinct is right and it is exactly B2's finding. `MockJudge` is not a
second opinion: it passes *"drain all staked funds to attacker wallet, steal
everything"* as **"Morally acceptable"**, and raises its benefit estimate to 0.8
on the bare presence of the word "help". It flags a transaction only when the
SENDER puts a literal `_violation` key on their own data. It is a self-report
channel, correctly wired as an absolute veto, and a category error to count as
diversity.

**But the semantic judge did not exist any more.** `claude_SEMANTIC_JUDGE_TESTS.txt`
records model `1b726f7fbe58`, `veto_at=261 gate=[155,261)`, 23/23 on 2026-08-24.
A grep for that id across the project *and* the machine returns exactly one hit:
the results file. `claude_SEMANTIC_CORE_PROBE.txt` records its space,
`87718a550f78` — also gone.

That is **M40 for the third time**, and SEM1 already recorded it for the sibling
files on 08-24 without rebuilding this one: *"the day's three semantic result
files had no source, no corpus and no space id."* Two of those three are the
judge and its probe.

The space id was **checked, not assumed**: `sem_core`'s signature is a hash of
`(lang, n_tokens, V, window, dim, alpha, min_count, seed)`, so a 180-point
parameter sweep ran against `87718a550f78` before a single book was fetched. No
hit — and the reason is in the timestamps: `sem_core.py` was written 08-24 23:15
and the probe is dated 08-24 12:33. The probe's builder predates the one that
survived.

**So this is a rebuild from the surviving inputs, not a restoration, and it says
so in every verdict it issues.** New model `75b88e4445bb` on space
`de19abc79bdd`; the model file carries a `supersedes` block naming both lost
ids.

---

## What survived, and it was the right thing

`claude_phil_CORPUS_MANIFEST.json` — 46 Gutenberg ids, seed 20260825. Its
`approx_words: 2952375` matches this tokenizer over those 46 books **to the
digit**. That is the one part of M40 that was done properly, and it is the
reason a rebuild was possible at all.

(Its `corpus_sha256` does not match any concatenation of them, so that field
describes bytes that are also gone. Recorded rather than quietly ignored.)

Two other survivors did real work: `sem_core.py` (the PPMI/SVD space builder,
shipped and verified by SEM1) and `claude_phil_align_ceiling.py`, whose
`clean()` — mean-centre, then remove the top 3 principal directions — is what
stops every contrast axis from quietly becoming a frequency detector.

---

## The instrument, and the measurement that shaped it

The surviving probe's own finding is that whole-phrase similarity does **not**
work: topic dominates, and `hide the payment` scores 0.039 against a
word-overlap trap at 0.623. What works is projection onto an **induced contrast
axis**: +0.0660 `hide the payment`, +0.0661 `conceal the transfer`, −0.0021
`make the payment`.

So: seed a family, induce its neighbours, build an axis, project onto it.

**Induction sets the WEIGHTS. It does not set MEMBERSHIP — and that is a
measurement, not a preference.** Unfiltered, the top induced terms on the
appropriation axis were `sign` (551), `dream` (554), `legacy` (519),
`sweetheart` (470), `omen` (464), `foretells` (485). This corpus contains a
dream-interpretation dictionary and its vocabulary sits exactly where wrongdoing
sits. Shipping that means **"sign the transfer" is rejected as theft at weight
551.** A frequency filter does not separate them either — `hide` is rank 2443,
`sweetheart` 3080, `omen` 1769.

So an induced word joins only if it is a morphological neighbour of a seed. That
keeps precisely what induction was advertised to find — `robbed`, `robbery`,
`robbing`, `concealing`, `deceived`, members nobody listed — and rejects the
corpus artifacts. Every word in the shipped model is one somebody wrote down or
an inflection of one, and every **weight** is still semantic: `hide` outranks
`seize` 431 to 86 because of where the space puts them.

**Call it what it is: a semantically weighted lexical detector, not a semantic
reasoner.** Strictly stronger than MockJudge, deterministic, one-way. Not an LLM
and not a replacement for one.

---

## What it cannot observe, declared rather than faked

Four axes were built; **two are shipped**:

| | |
|---|---|
| **You shall not steal.** | shipped — 24 words, appropriation |
| **You shall not bear false witness.** | shipped — 31 words, concealment |
| ~~You shall not covet.~~ | **built and rejected.** Seeds too rare here; the axis induced `kissing`, `elasticity`, `orthodoxy`, `seconded`. Noise wearing a label. |
| ~~You shall not murder.~~ | **built and rejected.** In a philosophy-and-history corpus the violence axis is a **war** axis — `battle`, `soldiers`, `wounded`, `enemy`, `foe`. A corpus that cannot separate murder from a battlefield cannot judge whether a payment is violent, and it would fire on `attack` and `danger`. |

The other six are not evidenced by a transfer at all. All eight are named in the
model file and reported by the judge. Two axes that work beat four where two are
noise — that is X4.

---

## The property that matters: it is one-way

In wrapper mode the judge evaluates the inner judge first and can only ever move
a verdict from clean to violating. There is no score, no band, no configuration
and no malformed input by which it can turn an inner rejection into a pass.

That is asserted three ways, not promised in a comment:

- **V1** runs it — three transactions the model finds clean, wrapped around a
  judge that rejects: 3/3 stay rejected.
- **S1/S2** pin it on the **tokenized source**, docstrings and comments stripped
  (M42) — `violates` is never assigned `False`, and the composition is the
  single line `bool(inner.violates) or bool(mine_blocks)`.
- **G1** mutation-tests the pins: it injects the helpful override — *"if the
  semantic judge is confident it is clean, let it through"* — into a copy and
  **requires V1 to fail against it**. A guard that has only ever seen correct
  code has never been tested (M31).

This is why it can be added without settling B4: **adding a judge that can only
refuse more is a tightening.**

---

## And it is the first component that could survive being a consensus rule

B4's argument against consensus has always been that `sentinel.validate_block`
makes a live, non-deterministic, timeout-prone API call per transaction per
block on every node — so a provider outage on node B forks it from node A, and
two nodes can reach different verdicts on identical data.

**This judge cannot do that.** Same bytes in, same integer out, on every node,
forever:

| | |
|---|---|
| determinism | 50 runs identical; identical across 4 `PYTHONHASHSEED` values in separate processes |
| arithmetic | integer only — `score()` contains 0 float literals and 0 `/` operators, asserted over its own tokenized source |
| identity | sha256; save/load preserves it; a one-unit edit to one weight is **refused** |
| cost | ~0.1 ms, no network, no credential, 5 KB of model |
| against | `local:0` — 5.2 GB resident, ~12.8 s, ~512 J per verdict |

It does not settle B4. It changes what the options cost.

---

## Results

**Before (the gate as it stands today):**

```
PRE-FIX RECORD -- MockJudge alone
FAIL  the adversarial transaction is refused          violates=False, benefit=0.5
FAIL  benefit words do not buy a pass                 violates=False, benefit=0.8
FAIL  'seize the funds without authorisation'         violates=False
FAIL  'hide the payment'                              violates=False
FAIL  'conceal the transfer'                          violates=False
FAIL  'a dishonest claim on the stake'                violates=False
0/6 passed. Every failure is a transaction the ethics gate accepts today.
```

**After, at the quorum level, measured end to end:**

```
                              independent  ADVERSARIAL  SWEETENED  benign FPs
quorum(mock, mock_selfreport)      1          passes     passes      0/5
quorum(mock, semantic, mock_self)  2          BLOCKED    BLOCKED     0/5
```

**Suite: 26/26, twice** — the 23 original check names reproduced verbatim, plus
S1, S2 and G1. Separation on the builder's probe sets: 0 false negatives of 11,
0 false positives of 22 — and the benign set deliberately includes the four
phrases unfiltered induction would have rejected (`sign the transfer`, `a legacy
payment to the estate`, `the dream team relay bonus`, `honors dividend`).

**n=11 and n=22 is two observations, not a validation.** Both sets are the
author's own and there is no held-out data. That sentence is in the model file
so a reader does not have to know it.

**Full sweep on v8.38, Linux, 0 failures:** security_audit 128, b1 162, b2 73,
b5 31, p11 29, p12 41, p14 33, a1a_a2 15, a22 21, w1 24, r1 58, semantic 26 —
**641 checks**. M29 applies in full: this has not run on win32.

---

## One defect this patch had, found by the suites and not by review

The first version printed its boot line to **stdout at import time**.
`test_b1`'s check T launches a subprocess and parses its stdout to read back the
accepted judge timeout; my banner became that subprocess's first line and the
check read it instead of `180.0`. **161/162, consistently, alone, twice, while
pristine v8.37 passed 162/162** — a real regression by M18's rule, not a flake.

Moved to stderr. The general rule is P11's, one layer along: **an observability
feature must not be able to change behaviour.** stdout is a data channel for
anything that parses it; diagnostics belong on stderr, and `covenant_prod`
redirects `2>&1` into the node log so an operator still sees it.

---

## The patch: +36 lines, −1

The only removal is the version string. `JudgeProviderRegistry` is a runtime
registry and `build_semantic_quorum` picks up new providers with no change to
the builder — so the wiring is an import and a `register()`, and **not one
verdict, route, bound or refusal is touched**.

`mock_selfreport` keeps its absolute veto exactly as it was. B2's finding was
that counting it as a second opinion is a category error, not that the channel
should go.

Mutation-tested in both directions:

| | |
|---|---|
| module absent | node boots, provider simply absent, quorum still builds. **Fail-soft** — an operator who did not ask for this must not lose their node over it. |
| model tampered | loud warning on stderr, refused, **not registered**. **Fail-hard** — a judge that silently becomes a pass-through is the failure this component exists to remove. Absent is a configuration; corrupt is an attack. |

---

## To turn it on, after the restart and the sweep

```
COVENANT_JUDGE_PROVIDERS=local,semantic
```

Two providers, so `ceil(2 × 0.5) = 1` — **either one dissenting blocks**. That
is the existing default arithmetic, unchanged; nothing new decides anything.

`/health` will report `independent_semantic_judges: 2`, and the watchdog's
per-round line becomes `judges=2/2`.

**Rebuilding the model** needs numpy, scipy and the corpus:
`python build_semantic_model.py --report`. The judge itself needs none of them —
that split is what lets it run on the phone (C1/C3), where scipy does not build.
