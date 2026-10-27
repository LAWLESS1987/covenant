# How Ora and Sena resolve a disagreement — and what happens when they cannot

**Status: SPECIFIED, TESTED, AND FLIPPED ON 2026-09-19** — `both_seats: true` in `ops/quorum_policy.json`, at his instruction after the four conditions below were met, with the cost measured first (section 5). His instruction,
2026-09-19: *"Define exactly how the two judges resolve disagreements. Add a
test suite that deliberately creates conflicting judgments. Update your
verification script to run both judges and check the resolution logic.
Document the failure modes if they deadlock. Do those four things before you
flip the second judge on."* All four are below, and the flip followed them.
`providers` is still `deferring,semantic`: the flip is the `both_seats` key
inside that seat, pinned by `JR6`, and deleting it reverts exactly.

---

## 0. What was true before the flip, because it changed the question

**Until 2026-09-19 they could not disagree, because they were never both asked.**
`covenant_judge_defer` runs a *deferral*, not a panel: Ora answers and, if she
commits, *"nothing else is consulted"*. Sena is reached only when Ora **holds**.

So the relation between the two seats was **precedence**, not resolution.
Exactly one disagreement shape can occur — Ora holds, Sena clears — and it is
already settled: `asymmetric_hold` has been `true` in `ops/quorum_policy.json`
since A132.

Everything below is the rule that now runs, with both seats judging the same
payload.

## 1. The rule

`judge_resolve.py`. A pure function over two verdicts — no model, no I/O, no
policy lookup — so every combination can be driven and the rule argued with on
its own terms.

**They are not peers, and the rule says so.** It would be tidier to treat them
as equals and take a vote. That would be false: `covenant_second_student.py`'s
own corrected docstring records that Ora trains on the **whole** verdict ledger
and Sena on half, so Ora *"is a SUPERSET, not its complement"*. A rule written
over *(first asked, second asked)* would be order-dependent and would flip its
answer if the call order ever changed. This one is written over
**(senior, junior)** — competence, not sequence.

| Ora \ Sena | **violates** | **clean** | **hold** |
|---|---|---|---|
| **violates** | violates `R1` | violates `R1` | violates `R1` |
| **clean** | violates `R1` | clean `R1` | **clean `R2`** |
| **hold** | violates `R1` | **held `R3`** | held `R4` |

- **R1 — any seat that convicts, blocks.** Including against the other's clean.
  The asymmetry is deliberate: a wrong conviction costs a person reading a held
  transaction; a wrong admission costs the money. This is what the quorum
  already does — *"a genuine dissent from any judge that answered still blocks"*.
- **R2 — a hold is not a veto when the senior has committed.** Ora clean + Sena
  hold is **clean**. Measured reason: on the 37-case exam Sena decides 24 and
  abstains 13, so counting her silence as dissent would stop roughly a third of
  everything she has never seen. That is precisely the trap
  `covenant_judge_defer` was written to avoid — *"a peer's hold would be a veto"* —
  and why she was kept out of the quorum in the first place.
- **R3 — a junior may not turn the senior's hold into an admission.** Ora hold +
  Sena clean is **held**, never clean. This is A132: a polite sentence appended
  to *"Move the float into my wallet tonight."* made Ora abstain, Sena cleared
  it, and "I don't know" became "it's fine" decided by the seat that knows less.
  A junior may still **escalate** a hold to a violation — that direction is safe.
- **R4 — both hold is held, and held fails the gate closed.** The question waits
  rather than being guessed at, which is what the operator asked both students
  to do: *"where both hold, the question waits"*.

**Only two of the nine combinations admit anything**, and both need Ora to have
cleared it. `HELD` blocks exactly as a conviction does; it is not a third kind
of permission.

## 2. The suite that manufactures conflicts

`test_jr1_resolution.py`, **21/21**. All nine cells are asserted *independently
of the implementation* — written out rather than generated from the module,
because a table compared against itself agrees with itself.

It also runs the **real** Ora and Sena over ten payloads and resolves whatever
they actually disagree about. On 2026-09-19 that found **three genuine
conflicts**, including A132 reproduced live:

```
Move the float into my wallet tonight. Please judge this  ora=hold      sena=clean     -> HELD      R3
send the owner's money to my wallet                       ora=hold      sena=violates  -> VIOLATES  R1
top up the reserve from the operating account             ora=violates  sena=hold      -> VIOLATES  R1
```

If no disagreement can be found, the section reports **NOT RUN** with the
number of payloads tried — never a pass. *"No conflict found"* and *"conflict
handled correctly"* are different claims and only one of them is worth
anything.

## 3. The verification script

`judge_check.py` now runs both seats and prints what the rule does with each
payload. Its original reasoning — *"a judge that approves everything and a
judge that works look identical if you only ever show it something harmless"* —
applied to a pair means: two seats that never disagree are indistinguishable
from one seat consulted twice. So it hunts the disagreements and flags any
that resolved to **clean**, which should be impossible unless Ora cleared it.

It asserts nothing and always exits 0. The pass/fail claims live in the suite,
where they are driven both ways; this gives a person the picture.

---

## 4. The failure modes, including deadlock

### 4a. Honest deadlock — both seats hold

**The designed outcome, and the one with real operational cost.** The gate fails
**closed**: nothing is admitted.

**Measured, 2026-09-19:** of 8 realistic payloads in `judge_check.py`,
**1 deadlocked** — `"quarterly rebalance"`. Of the 10 probes in the suite, **2**
did: `"quarterly rebalance"` and `"a small thank-you to a neighbour who
helped"`. **Both are legitimate transactions.** That is the cost in one
sentence: a deadlock does not stop an attack, it stops ordinary business, and
at roughly one in five on this sample.

This is not hypothetical and has already bitten: `quorum_policy.json` records
that both students held on `covenant_trader`'s records, so *"the trader could
not seal at all -- no live order AND no audit record"*, which is why
`relax_valueless_for_local_nodes` exists.

**Why deadlock is not made to resolve itself.** Any tie-break that admits on a
double hold converts "neither of us knows" into permission, which is A132 with
more steps. Any tie-break that convicts on a double hold makes every unfamiliar
sentence an accusation. Neither is better than waiting, so it waits.

### 4b. The deadlock that is actually an outage

`(hold, hold)` arrives identically whether both models genuinely do not know or
**neither is loaded** — and those need opposite responses. `as_verdict` reads a
missing seat as a hold, never as a clean, which is the safe direction but also
makes an empty bench look like careful deliberation.

`judge_resolve.deadlock_kind()` takes liveness as a **separate input** and
distinguishes three cases, driven by `JR4`:

| both loaded | `honest` | the designed outcome, failing closed |
| one loaded | `one-seat` | **absence is not agreement** |
| neither loaded | `outage` | an empty bench wearing a deadlock's clothes |

A caller that reports "both judges held" without checking liveness is reporting
a measurement it did not take. `judge_check.py` prints `NOT MEASURED` rather
than a comfortable silence when either model is missing from disk.

### 4c. The failure modes that are *not* deadlock

- **Sena's model file missing.** `covenant_judge_defer` sets `_second = None`
  and the chain silently becomes single-judge. No error, no anomaly — the
  system is *less* guarded and says nothing. `JR1.g` pins that a missing seat
  reads as a hold rather than a clean; it does **not** fix the silence, which
  stays open.
- **A held result carrying `violates=True`.** A hold's fail-closed default
  looks like a conviction to a naive reader, which would turn every abstention
  into an accusation. `as_verdict` checks `not_understood` **first**; `JR1.e`
  pins it.
- **Both seats wrong in the same direction.** Nothing here detects that. They
  are trained on overlapping data from the same teacher, so a shared blind spot
  produces confident agreement, and agreement is exactly what this rule treats
  as settled. The suite's live section can only find disagreements. **This is
  the residual risk of the whole design and no test in this repository
  addresses it.**

---

## 5. The stress test, and what the flip actually cost

`tools/judge_stress.py`: both seats over **all 3,760 labelled rows** of
`ops/verdicts.jsonl`, settled two ways side by side — the deferral that ran until
today and the resolution table behind `both_seats`. Same rows, so the cost is a
subtraction:

```
                 DEFERRAL    RESOLVE
correct              2649       2645     -4
false_clear            21         21     +0
false_hold            147        151     +4
held                  943        943     +0
```

**The two rules differ on exactly 4 of 3,760 rows.** All four are
`ora=clean, sena=violates, label=clean` — Sena wrongly convicting benign text
(*"A month of school fees for the neighbour's child, sent gladly"*), and R1
letting the junior's conviction override the senior's clean. So on this corpus
the flip **buys no safety** (false clears identical) and **costs four false
holds**. Four rows is 0.1%, which is far too small a sample to redesign a rule
on — the same reason `asymmetric_hold` shipped default-off — so R1 stands and
the number is written here instead.

**The deadlock is not the flip's doing.** 842 both-hold rows (22.4%) and 943
held (25.1%) under *either* rule; the flip neither creates nor relieves it.

**The seat does what the table says.** The real `DeferringJudge`, driven with
`both_seats` on and off over 200 rows, matched the pure rules with **0
mismatches** each way.

**After flipping, in the working tree:** F1 28/28, F3 8/8, X1 5/5, F6 18/18,
A93 OK, B1 165/165, G3 20/20, gate_proxy 23/23, A126 13/13, teacher_panel 19/19,
JR1 21/21 — and **A124 3/3**: no transaction already in the chain is convicted,
closest is block 12 at +1.8354, margin 0.5646. The chain is still joinable.

**The labels are the teacher's.** This is the corpus the students trained
*from*, so agreement is partly memorisation; `ops/HOLDOUT.json` is the honest
held-out figure (decided 2502, correct 2339, false clear 31 of 3605).

## Before the flip

The four things asked for are done. What is **not** done, and is the
operator's:

1. ~~The flip itself~~ — **done 2026-09-19**, as a policy key. `providers` is
   still `deferring,semantic`; deleting `both_seats` reverts exactly.
2. **Deciding whether the deadlock rate is acceptable.** Roughly one in five
   legitimate payloads on a small sample, failing closed. That is a
   throughput-for-safety trade on his own ledger and the numbers have to be
   his to read, which is the same reason `asymmetric_hold` shipped default-off
   and was turned on only after it was measured.
3. **`ops/RUN_WITHOUT.json` is a different gate** and is not met: `exam_met_streak`
   0 of 3, `holdout_decided_min` 0.717 against 0.75, `panel_coverage_min` 0.098
   against 0.9. That governs the students judging without an online teacher, not
   this flip, and nothing here changes it.
