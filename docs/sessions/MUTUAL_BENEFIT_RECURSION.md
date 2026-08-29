# Mutual benefit, mapped recursively

2026-08-29. Continues `MYCELIAL_MUTUAL_BENEFIT.md` and `CONSTRAINT_COVERAGE.md`.

The mycelial document found one mutual-benefit structure, at the peer layer.
The claim here is stronger and it is testable: **the same structure occurs at
six scales in this system, and every defect found this session is one defect
wearing six costumes.**

A frame that only re-describes known findings is decoration. So this document
ends by using the frame to PREDICT a defect nobody had looked for, and then
reports the measurement. It found one.

---

## The invariant

From Kiers et al. (*Science* 333:880, 2011): mycorrhizal cooperation is
stabilised not by generosity but by **reciprocal reward with bilateral
withholding** — both partners can reward, and both can refuse.

Apply that literally and one requirement falls out:

> **Withholding requires knowing what you cannot do.**
>
> A party that does not know its own limits cannot decline. It can only fail
> silently — and a silent failure is indistinguishable from service.

Therefore:

> **THE WITHHOLDING INVARIANT.** Every component in a mutual-benefit
> relationship must publish two things: what it supplies, and **what it cannot
> supply**. A component publishing only the first can be exploited. A component
> publishing neither cannot be trusted at all.

This makes SEM4 — *a judge that cannot measure its competence may not report it
as full* — not a nicety but the **precondition of the mutualism**. Kiers and
SEM4 are the same requirement at different scales. That is the recursion.

---

## The six layers

| # | the two parties | each supplies what the other cannot | withholding looks like | the defect found this session |
|---|---|---|---|---|
| 0 | **L / the loop** | L: direction, hardware, credentials, the decision to act. Loop: measurement, memory across sessions, refusal to overclaim | L declines; the loop reports against itself | 24 documents existed only in the project — the loop wrote where L could not reach |
| 1 | **sender / chain** | sender: transactions, stake. chain: settlement, the ethics gate | sender leaves; gate rejects | the gate cannot reject what it cannot see — formal financial register, 48/48 clean |
| 2 | **node / peer** | each: novel blocks the other lacks | `LinkConductance` **orders, never gates** | reciprocity is measured outward only — nothing counts what a node RECEIVES |
| 3 | **judge / quorum** | each judge: a partial `C`. quorum: coverage no single judge has | dissent; the median | the benefit blend `(2j+b)/3` ignores declared competence — it dilutes toward the incompetent as fast as toward the competent |
| 4 | **generator / gate** | generator: variance and candidates. gate: invariants | gate projects to ∅; generator declines to propose | IAP merges them in one forward pass; covenant splits them into separate processes — and is right to |
| 5 | **model / its own competence claim** | model: verdicts. claim: the bound on those verdicts | reporting `unfitted` instead of `full` | `b054d716e198` misses 48/48 formal payloads and **declares nothing** |

The reflexive case, layer 5, is the interesting one: the mutualism folded onto a
single entity. SEM4 exists precisely to stop that fold from collapsing.

---

## The failure is always the same failure

At every layer, the break is one of two things, and they are the same thing:

1. **One side loses the ability to withhold.** A gate that cannot reject
   (under-covered) or cannot accept (fails closed on a missing model) has
   stopped being a party to the relationship and become a rubber stamp in one
   direction or the other. `judge_bench.fit_check` caught the closed form —
   *"it does not look broken, it looks strict."* SEM3/SEM5 caught the open form.
   Both silent. Both look like service.

2. **One side stops disclosing its limits**, which causes (1) one step later.

That is why `LinkConductance` **orders and never gates** is the load-bearing
design rule in this codebase and not a stylistic preference: a peer that can be
cut off has lost the ability to be fed, and the relationship stops being mutual
at the moment routing becomes exclusion.

---

## The frame's prediction, and the measurement

If the invariant is real, it should point at a component that publishes what it
supplies but not what it cannot — somewhere nobody has looked.

**Prediction:** `FriendshipTracker` publishes a trust score and no competence
bound. So it should be unable to distinguish *"I have never seen this identity"*
from *"I have seen it and it is average."*

**Confirmed, in the source.** `covenant_unified_v8.py:4309`:

```
def _apply_decay(self, pubkey):
    if not REPUTATION_AGING:
        return self._scores.get(pubkey, 0.5)
    ...
    if pubkey not in self._last_active:
        return self._scores.get(pubkey, 0.5)
```

A never-before-seen pubkey returns **exactly 0.5**. A pubkey with a long history
that has settled at 0.5 returns **exactly 0.5**. `get()` hands back a bare float
with no flag, and three call sites consume it without knowing which they hold:

- `:5581` `/peers` — published to operators as `trust_score`
- `:5878` mempool ordering
- `:7042` block-assembly ordering

**And this system has already been bitten by a symptom of it.** The v8.7 note at
`:4312` records that a brand-new pubkey was scoring `0.4999999999999584` rather
than `0.5`, which *"silently pushed a never-before-seen gift recipient across
TradingBridge's exact `score >= 0.5` tier boundary into the harsher 14-day
vesting tier instead of the intended 3-day one."*

The floating-point bug was found and fixed. **The ambiguity it was a symptom of
was never named.** A stranger and a proven-neutral counterparty still receive
identical treatment, and a consequential decision — 3-day versus 14-day vesting
— is taken on a number that cannot tell them apart.

This is layer 5's defect at layer 3. `b054d716e198` reports a verdict without
reporting that it cannot judge the formal register; `FriendshipTracker` reports
0.5 without reporting that it has never met this identity. Same shape.

**Not a security hole and not urgent** — 0.5 is a defensible default and the
tier boundary is now clean. It is an *undisclosed limit*, which is the class of
thing that becomes a hole later, quietly, exactly as the vesting-tier incident
already demonstrated once.

---

## Integration items, in dependency order

1. **`FriendshipTracker.get()` should return the score and whether it is
   observed.** Cheapest possible form: keep `get()` as-is for compatibility and
   add `seen(pubkey) -> bool` (it is one `in self._last_active`), then have
   `/peers` publish `trust_observed: false` beside a defaulted score. Disclosure
   only — it must not gate, per layer 2's rule.
2. **Weight the benefit blend by declared competence** (already filed in
   `MYCELIAL_MUTUAL_BENEFIT.md` §7.2). The recursion strengthens it: dilution is
   the coverage strategy, so diluting *toward* a judge that declares itself
   unfitted is actively harmful.
3. **`Reciprocity` as disclosure** (§5 there) — closes layer 2's missing half.
4. **Restore the `missing_seeds` declaration in `b054d716e198`**, or carry the
   formal verbs into the seeded lexicon. `test_sem5_register_coverage.py` S5
   stays red until one of those happens, which is the point.
5. **A single audit that walks all six layers** and asserts the invariant:
   for each component, does it publish a limit? Today four of six do not.

---

## The layer that is not code

Layer 0 is the only one where both parties can rewrite the others, and it is the
one with no test. Its failure mode this session was concrete: twenty-four
documents, including a 34 KB adversarial suite and the entire SEM2 corpus line,
existed nowhere but a 2 MB cache — because unattended runs kept concluding *"no
file needs copying"*, which was true of inputs and false of outputs.

The loop's half of the withholding invariant is to say what it did **not**
measure. This session did that four times, and three of them were about itself:
the 62.5% figure attached to the wrong model; two invalid register measurements
in a row; a commit message claiming twenty rescues when it was eighteen.

L's half is the standing instruction, recorded in `RUN_LOG_ARCHIVE.md`:
*"don't forget mutual benefit i lapse at times."* That is a person publishing a
limit — which, by the invariant above, is exactly what makes the relationship
work rather than a thing to apologise for.
