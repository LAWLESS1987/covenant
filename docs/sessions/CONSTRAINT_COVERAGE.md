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
