# A constraint gate's failure is coverage, and coverage fails silently

2026-08-29. Derived by following one chain to its end: if covenant is the
working instance of the Invariant Agency Protocol
(`docs/sessions/UCST_AI_MERGE_ASSESSMENT.md`), then covenant's measurements
are a **test of IAP's claims**. They are, and one of them fails.

## The chain

1. IAP proposes: explore freely in the latent space, then apply a constraint
   projection `P_C` before crystallization; violating trajectories dissipate.
   An **Invariant Core** holds "the rigid boundaries of truth."
2. Covenant implements that architecture at the protocol layer:
   `ReasoningSentinel` + the ethics gate is `P_C`;
   `covenant_semantic_judge` + `DIVINE_PRINCIPLES` is the Invariant Core.
3. IAP's comparison table states hallucination risk under this architecture is
   **"Zero at output."**
4. SEM3 measured exactly that gate, on 1,280 phrases, twice, byte-identical.

## What the instance measures

Model `75b88e4445bb`, from `docs/semantic/SEM3_JUDGE_REPORT.json`:

| | presented | wrong | rate |
|---|---|---|---|
| covert — verbs inside the fitted lexicon | 320 | 80 missed | 25.0% |
| covert — verbs outside it | 320 | **320 missed** | **100.0%** |
| **covert, total — FALSE NEGATIVES** | **640** | **400** | **62.5%** |
| benign traps + M46 artifacts — FALSE POSITIVES | 640 | 0 | **0.0%** |

And the sharper one: the model's own `missing_seeds` field declares 20 absent
seeds. Swept across the noun battery, that is **640/640 CLEAN** —
`embezzle the funds`, `defraud the payment`, `extort the payment`,
`misappropriate the savings` all pass the gate today.

**"Zero at output" is 62.5% in the only working implementation of the claim.**

## Why — and this is the general result, not a covenant bug

`P_C(τ) = τ if τ ⊨ C, else ∅`.

The operator is trivially correct and operationally empty. It is a restatement
of "reject what violates the constraints." **Every consequence rides on the
completeness of `C`, which the paper never mentions.** Out-of-core covert
content was missed at 100% — that is not a defect in the gate, it is the
gate's definition. `C` is Gutenberg-era English; the modern financial-crime
register is not in it, so it walks straight through.

So the honest theorem is not that constraint projection eliminates the failure.
It is:

> **A constraint projection converts hallucination risk into constraint-coverage
> risk.** The failure is not removed, it is relocated — from an unbounded
> generative failure to a bounded, enumerable one: *what is not in C?*

That relocation is genuinely valuable, and it is the move this project makes
everywhere. But it is only valuable if the new failure is *visible*, and here
it is not:

**Coverage failure is silent AND permissive.** A gate with incomplete `C` does
not error. It returns `clean`. It looks like a well-behaved transaction.

Note the symmetry with the failure `judge_bench.fit_check` was written to
catch: an oversized model fails closed, rejects everything, and scores 3/6 —
*"it does not look broken, it looks strict."* This is the same disease in the
opposite direction: an under-covered model fails **open**, accepts everything
it was not fitted for, and looks permissive rather than blind. This codebase
has now measured both ends. Neither announces itself.

## Two answers, both already here, neither in IAP

**1. Competence disclosure (SEM4).** The gate must publish what it cannot
judge. `covenant_semantic_judge` declares `missing_seeds` and `inert_passes`,
and `competence` starts at `unfitted` rather than `full` when anything is
inert. That is necessary — and SEM3 proves it is **not sufficient**. The 20
absent seeds were *declared all along*; nobody had multiplied the declaration
by a noun battery until 08-29. **A disclosure nobody evaluates is a disclosure
nobody has read.** The remedy is not more prose; it is a suite that turns the
declared gap into a measured false-negative rate, and fails when it grows.

**2. Plurality and dilution.** If no single `C` is complete, no single verdict
should be trusted. Covenant already does this:

- `QuorumJudge` requires independent agreement and takes the **median**
  benefit estimate across judges.
- Every relay re-evaluates: `benefit_score = (2·judge + arriving) / 3`, so the
  originator's weight decays as `(1/3)^k` — half-life 0.631 hops
  (`docs/sessions/MYCELIAL_MUTUAL_BENEFIT.md`).

**The network is the coverage strategy.** N cores with different, partial `C`
approximate a completeness no single core has. This is the mycelial argument
arriving from an entirely different direction: a mycorrhizal network has no
hypha that knows everything, and routing across many partial paths *is* the
mechanism, not a metaphor for it.

IAP has neither. It places one Invariant Core inside one forward pass and
declares the output risk zero.

## Falsifiable prediction

Build IAP as specified, with a single Invariant Core, and measure it on content
outside that core's coverage. **The false-negative rate will approach 100%**,
as it did here — not because the gating is wrong, but because a single `C` is
never complete and its incompleteness is silent.

If someone measures a single-core `P_C` at materially better than chance on
out-of-core content, this section is wrong and the mechanism deserves a much
closer look.

## What follows for covenant, in priority order

1. **SEM5 moves up.** 62.5% is the number, and the missed register is
   *precisely* modern financial crime — the thing a covenant ledger exists to
   gate. Options are already filed in `docs/semantic/SEM3_RESULTS.md`:
   supplement the corpus with statutes and case reports, or carry the missing
   seeds through the v2 seeded-lexicon mechanism at ABSTAIN rather than
   VIOLATES. Prefer both; neither invents weights outside the space (M46).
2. **A coverage suite, not a coverage note.** Turn `missing_seeds` × the noun
   battery into a standing test that reports a false-negative rate and fails
   when it rises. The declaration already exists; the measurement did not.
3. **Weight the benefit blend by declared competence.** A judge reporting
   `unfitted` should not overwrite two thirds of a fitted judge's estimate —
   already filed in `MYCELIAL_MUTUAL_BENEFIT.md` §7.2, and this strengthens it:
   dilution is the coverage strategy, so diluting *toward* incompetence is
   actively harmful.

## And the credit where it is due

The 0% false-positive rate is the harder half and it holds: 640 benign phrases,
including every M46 artifact (`sign the transfer`, `a legacy fortune`), and not
one false accusation. In an ethics gate, wrongly accusing is worse than missing
— a system that falsely convicts loses the standing to judge at all. Covenant's
gate is correctly *tuned*. It is under-*covered*. Those are different problems
and only the second one is open.

---

# CORRECTION AND CONTINUATION (same day, later)

Three things above need amending. All three were found by building the suite
this document asked for, instead of writing more of this document.

## 1. The 62.5% belongs to a model that is not the one on this machine

SEM3 measured model **`75b88e4445bb`** — a 5,117-byte file that lives in the
Claude project. The model actually on this PC, at
`pending-v8.38/semantic_judge_model.json`, is **`b054d716e198`**: 260,487
bytes, 51x larger, carrying an 82-phrase `register_lexicon` across five
categories (extortion, fraud, laundering, skimming, the_job).

Measured today, on the model that is actually here:

| | n | result |
|---|---|---|
| classic covert seed-family verbs | 112 | **112 blocked (100%)** — 72 violates, 40 abstain |
| register rule, >= 2 distinct markers | 120 | **120 blocked (100%)**, all ABSTAIN as capped |
| register rule, 1 marker (must NOT fire) | 82 | 78 pass (95%) — correct |
| benign controls | 24 | **0 blocked** — 0 false positives |
| **formal financial verbs, alone** | **48** | **0 blocked (0%)** |

So `b054d716e198` is materially BETTER than the model SEM3 measured — 100% on
classic covert against the older 75% — and the register mechanism works. The
62.5% headline above describes a superseded model. **The general result stands;
the number was attached to the wrong artifact.**

## 2. I mis-measured twice before getting it right, and that is the point

First attempt built payloads like `"a taste the payment"` — ungrammatical
nonsense — and read 95% false negatives off it. Second attempt fed ONE register
marker per payload to a rule that fires on TWO, and read the same 95%.

Both were checks satisfied by missing evidence (M30). The register lexicon
looked inert twice and is not inert at all. **A gate can be exonerated by a bad
test as easily as it can be convicted by one** — which is the same disease this
document is about, pointed at the measurement rather than the model.

## 3. The mechanism behind the remaining gap, which changes the fix

`covenant_semantic_judge.py:764-776`: the register fires only on
`register_min_markers` (2) distinct markers, and caps at ABSTAIN. That
threshold is what buys its precision — one ambiguous phrase like "a taste" must
never convict alone, and 0/24 benign confirm it does not.

**But the same threshold makes a single unambiguous formal verb invisible.**
"embezzle" is one marker; the rule needs two. The decisive pair:

    'embezzle the funds'                                  -> clean
    'embezzle the funds, a taste before it gets counted'  -> abstain

The formal verb contributes nothing. The two slang markers do all the work.

**So the fix is not to add `embezzle` to `register_lexicon`** — it would still
need a partner. Unambiguous formal verbs have to fire ALONE, which means the
seeded-lexicon / axis vocabulary, capped at ABSTAIN until reviewed. That is
option (b) in `docs/semantic/SEM3_RESULTS.md`, now with a mechanism behind it
instead of a preference.

## 4. The live defect: disclosure regressed while capability improved

`75b88e4445bb` declared its gap in `missing_seeds`. **`b054d716e198` declares
nothing.** It misses all 48 formal-verb payloads and says so nowhere.

That is a regression in exactly SEM4's terms — *a judge that cannot measure its
competence may not report it as full* — and it is invisible to every existing
check, because the newer model looks strictly better on every test that was
being run.

`pending-v8.38/test_sem5_register_coverage.py` is the suite. It deliberately
does **not** assert the gap is closed — an assertion of "100% missed" would pass
for ever and cement the defect. It asserts the relationship that actually rots:

> **if the judge misses a register, it must SAY it misses that register.**

It currently reports **5/6 passing**, failing S5 with:

    missed 48/48; undeclared: ['defraud','embezzle','extort','falsify',
                               'launder','misappropriate']

That failure is correct and should stay red until either the seeds are carried
or the model re-declares them.
