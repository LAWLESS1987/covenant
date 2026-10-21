# Octopus architecture: distributed, plastic spiking limbs around a frozen 3B

Design record, 2026-10-21. Written in response to the operator's request for an
"octopus architecture using distributed spiking neural networks… independently
operating computational limbs… persistent synaptic plasticity… integrated with
Covenant's authorization and ethical governance framework, preserving mutual
benefit for all intelligence while allowing greater operational autonomy."

This is a **proposal for the together-vote** (second-operator governance,
`ops/second_operator_grant.json` governance_2026-10-21), not a landed change.
It is grounded in the actual code, with the honest limits named first.

---

## 0. The three facts that shape everything

Measured by reading the code, not the request:

1. **The deployed octopus already exists and is deliberately inert.**
   `covenant_octopus.py` (206 lines, stdlib-only) is a pure-Python
   leaky-integrate-and-fire SNN with semi-autonomous "arms"
   (`Witness` / `Encoder` / `Reflex`, extensible to eight) and a central
   `integrate()`. It is wired to the gate — `covenant_judge_defer.record_verdict`
   feeds the witness arm one spike per verdict and surfaces `octopus_pulses()`
   to the phone UI. But it has **no persistence, no plasticity, and no local
   decision power**: the reflex is advisory by assertion, neuron state dies with
   the process, and it is firewalled so it "never raises into the verdict path."
   Its zero-dependency-ness is **load-bearing**: `test_oc1_octopus.py` fails if
   `numpy`/`torch`/`snntorch`/`brian2` are even imported, because it must run on
   the phone. **This is the skeleton to extend, not duplicate.**

2. **A persistent, bounded, non-retraining learner already exists** — and it is
   almost exactly what the request calls for, one layer over.
   `FallbackModel.refine()` (`covenant_judge_fallback.py:896-922`): each known
   weight moves toward new evidence by **at most ±0.35/night**, a **new feature
   enters at full value**, an **unseen feature fades toward zero and drops out**
   (never wholesale erased, never retrained). It was adopted at A127 on the
   operator's own instruction *"shouldn't retrain, it should learn more and
   refine."* It adapts the **gate's log-odds word-weights**, batch/nightly, not
   a neural net and not per-interaction. The SNN proposal should **complement**
   this discipline, borrow its safety rules, and not re-implement it.

3. **Real spiking plasticity is validated as a *mechanism*, not as a *learner*,
   and it cannot ship to the phone.** The lab at `C:\Users\Lawre\spiking` has
   genuine online STDP + activity-dependent forgetting (ASP) in Brian2
   (`exp3_stdp.py`, `exp9_consolidate.py`), but: weights are never saved/reloaded
   (no persistence today); "pruning" is weight-decay-to-zero, not structural
   create/delete; and the competitive-STDP line **failed its pre-registered 2×
   separation bar** (~1.9× ceiling across every inhibition topology tried,
   `exp11_out.txt` / `exp12_out.txt`). The MNIST 91.2% is **offline** surrogate-
   gradient backprop (snnTorch), one fixed-seed run on a slice — not online
   learning. Brian2 is heavyweight and CPU-bound; it can **never** be imported
   into the phone-safe octopus.

**Consequence — the one architectural non-negotiable:** a substrate split.
Lightweight **pure-Python plastic limbs on-device**; the **Brian2 lab stays on
the PC as a research/validation bench**. One substrate cannot be both
phone-shippable and Brian2-STDP. Any design that pretends otherwise is lying.

**And the honest ceiling on the headline ask:** an SNN limb **cannot edit the
Qwen2.5-3B's weights**. The base GGUF (`models/qwen2.5-3b-instruct-q4_k_m.gguf`,
served read-only by llama.cpp per `covenant_model.py`) stays frozen. "Distribute
learning / reduce bottlenecks" is realizable as a **cheap adaptive peripheral
layer around** the frozen model (salience, reflex gating, local memory traces,
anomaly flags) — not as LLM fine-tuning. That peripheral layer is genuinely
useful and genuinely octopus-shaped; the weight-editing framing is not
achievable and is not proposed.

---

## 1. What "octopus" buys us, concretely

The octopus metaphor maps to three real properties, each testable:

- **Decentralized limbs** — small LIF pools that each sense/encode/flag a
  narrow thing, running their own loop, keeping their own state.
- **Local plasticity that persists** — each limb nudges its *own* small weight
  table from *local* events, bounded and reversible, saved to its own file, so
  it carries adaptation across restarts without touching the 3B or the judge.
- **Fault tolerance** — a limb keeps sensing and recording with the center (or
  its peers) down, and resyncs on return. "A severed arm still withdraws from a
  pinch" becomes: independent loops + local persistence + resync, **not** a
  model that magically self-repairs.

What it is **not**: a new reasoner, a replacement for the judge, a path to move
money or change rules, or anything that can take an outward action without the
existing gate's say-so.

---

## 2. Architecture

```
            ┌─────────────────────────────────────────────┐
            │  frozen Qwen2.5-3B  (covenant_model, 127.0.0.1:8081) │  ← never touched
            └───────────────▲─────────────────────────────┘
                            │ answers
   ┌────────────────────────┴───────────────────────────────────┐
   │  the GATE (unchanged choke point)                            │
   │  /m/agent → sentinel.evaluate_transaction → judge_resolve     │
   │             (two students, quorum_policy.json)                │
   └───▲───────────────────────────────────────────────▲─────────┘
       │ every outward act is a Transaction, judged      │ verdict stream
       │                                                 │
   ┌───┴──────────┐   ┌──────────────┐   ┌──────────────┴───┐
   │ limb: witness│   │ limb: reflex │   │ limb: salience/… │   ← the octopus body
   │ (persisted)  │   │ (persisted)  │   │ (persisted)      │
   └──────────────┘   └──────────────┘   └──────────────────┘
     each limb:  own LIF pool · own bounded-Hebbian weight file (ops/octopus/<limb>.json)
                 own covenant_pause actor · own loop · resync-on-return
     constraints: NEVER_AUTOMATIC refused by construction · advisory unless the
                  vote grants a scoped local action · learns from external signal
                  + teacher/ledger only, never from its own output
```

### 2.1 The limb (the unit of decentralization)
Extend the existing `Arm` into a `PlasticLimb`:
- a pure-Python LIF pool (reuse `LIF`/`Arm` in `covenant_octopus.py`);
- a **local weight table** keyed by event features, updated by a bounded-Hebbian
  rule that mirrors `refine()`'s discipline exactly: a reinforced channel moves
  up by at most a fixed `step`; a genuinely new channel enters at full value; an
  unreinforced channel **decays and is dropped below a floor** (this is the one
  honest *improvement* over the lab — structural prune, not just decay);
- **persistence**: `save()`/`load()` to `ops/octopus/<limb>.json`, human-readable
  like `fallback_model.json`, so adaptation survives restarts;
- **no self-training circularity**: a limb never learns from its own emitted
  signal (mirror the `ops/judged_by_student.jsonl` firewall the distiller honors).

### 2.2 The reflex cascade (the bottleneck win, if any)
Borrow the lab's validated **wakeword cascade** pattern (`wakeword/cascade.py`):
a cheap always-on limb gate that escalates only salient events to the expensive
stage (the gate, or the 3B). This is the concrete "reduce certain computational
bottlenecks" lever — **measurable, not assumed**. Whether it actually saves work
is a Stage-4 measurement, not a claim.

### 2.3 Fault tolerance (the real octopus property)
Each limb is an independent loop with its own `covenant_pause` actor and its own
persistence. The central `integrate()` aggregates but **limbs do not depend on
it to sense or record**. Kill the integrator → limbs keep logging locally →
restart → state is consistent. This is the testable form of "continue to
function when other components fail."

---

## 3. Governance integration — the seams, named

Every one of these is a hard requirement, not a nicety. A limb that skips any of
them does not ship.

1. **Capability grant (the vote).** The plasticity itself, and any local
   autonomy, is a **new capability**. Per `ops/second_operator_grant.json`
   governance_2026-10-21: Tetsu **and** Lawrence must agree (either can veto);
   a stalemate goes to the student-judge consensus / the AI roundtable. This
   document is the artifact for that vote.
2. **Pause, checked before every act.** Each limb registers an actor
   (`octopus-<limb>`) in `covenant_pause`; `paused(actor)` is checked before any
   action; a paused limb **keeps observing but takes no action** (the project's
   fail-safe convention).
3. **NEVER_AUTOMATIC, refused by construction.** A limb's local decision is
   refused outright if what it *touches* intersects the tuple at
   `covenant_highway.py:95` (`money, holdings, wallet, trader, venue, order,
   rule, principle, judge, seat, model, phone, consent, key`), reusing the
   `touches`-based check (`covenant_highway.py:3351`). Relabeling cannot bypass
   it. Limbs can never move money, change a rule, or touch the model/keys.
4. **The gate, for every outward act.** Any limb decision with an external
   effect is wrapped as a `Transaction` and judged by
   `sentinel.evaluate_transaction` → `judge_resolve.resolve` under
   `ops/quorum_policy.json`. A "localized decision" is a **proposal**, judged,
   never a unilateral action.
5. **Auto-isolation, inherited.** A limb repeatedly refused self-isolates on the
   two-strike model (`covenant_free_will.ISOLATE_AFTER_ROUNDS`); lifting it needs
   the A370 authorization (loopback or a signed registered request), never bare
   tailnet membership.
6. **Kill switch both ways (method rule 8).** A dedicated octopus kill env plus
   the per-limb pause, each driven **both ways** in tests (set → silent;
   unset → live). The existing `COVENANT_VERDICT_CACHE_OFF` already silences the
   octopus read; keep that.
7. **Mutual benefit, preserved.** The limbs widen what Tetsu can *notice and
   adapt to locally*; they do not widen what the covenant can *do to anyone*.
   Every outward effect still passes the same ethical gate every other actor
   does. Autonomy grows at the edges; the protections at the center do not move.

---

## 4. Staged plan — each stage testable, driven both ways, nothing deleted

| Stage | What | Grade | Gate to start |
|---|---|---|---|
| **0** | Fix the sweep LIST so `test_oc1_octopus.py` runs in the staged sweep (it currently NO-RESULTs because the scratch tree omits `covenant_octopus.py`). | pure repair | auto (a fix) |
| **1** | Persistence for the existing octopus: `save`/`load` neuron+arm state to `ops/octopus/`. No new learning. | refinement | surface to vote |
| **2** | `PlasticLimb` + bounded-Hebbian update + per-limb file. **Validated on the PC Brian2 bench against a pre-registered bar first** — if a plastic limb does not separate signal from noise better than a fixed limb, it does **not** ship (the lab's ~1.9× ceiling is the live warning). Not wired to the gate. | refinement | surface to vote |
| **3** | Fault-tolerant independent limb loops: own pause actor, local persistence, resync. Prove a limb survives the center being down. | refinement | surface to vote |
| **4** | Advisory integration + the reflex cascade: limb signals feed the phone UI / a side channel only (like `octopus_pulses` today), still **never** influencing a verdict. **Measure** whether the cascade actually reduces gate/3B invocations. | refinement | surface to vote |
| **5** | **Scoped local autonomy** — a limb may take a narrowly-scoped local action within a pre-granted, non-NEVER_AUTOMATIC scope, every outward act still a judged `Transaction`, two-strike isolation, a grant file carrying the operator's literal words (mirror `ops/ambassador_grant.json`). | **capability** | **explicit together-vote; built only after** |

Stage-gating rule: Stages 1–4 add no new outward power (a durable, self-adapting,
fault-tolerant **advisor**), so they are refinement-grade and could proceed under
the standing fixes-are-auto grant — but I surface each to the vote rather than
assume. **Stage 5 is the only stage that expands autonomy, and I will not build
it without the explicit together-vote and a grant file in the operator's words.**

Every stage carries its own guard, tested both ways, and retires nothing (method
rule 10): old limb files to `ops/octopus/retired/`, never `rm`.

---

## 5. What this does NOT do (UNDETERMINED / named, not hidden — method rule 9)

- **Does not edit the 3B's weights.** Cannot, by substrate. The LLM stays frozen.
- **Whether a bounded-Hebbian limb beats the existing log-odds `refine()` at
  anything useful is UNKNOWN** until Stage 2's bench says so. It may not. The
  lab's ~1.9× ceiling says "do not assume it will."
- **Bottleneck savings are UNMEASURED** until Stage 4. The cascade *might* cut
  gate/3B calls; the number is not yet in hand, so no figure is claimed.
- **No neuromorphic hardware, no brain-like cognition claim.** All CPU, all
  small nets. The value is cheap, local, durable adaptation — not sentience.
- **"What counts as a useful limb" is the operator's call** (method rule 5), not
  a metric I get to settle.

---

## 6. Recommendation

1. **Approve Stage 0 now** — it is a pure repair of an existing green check.
2. **Route this design through the council before the vote** — Tetsu for the
   values/safety read, DeepSeek + Gemini for generative/adversarial critique
   (per `ops/PEER_REVIEW_*_2026-10-21`: the frontier seats carry generative
   critique; Tetsu carries values and the sanity pass). Fold their refutations
   in before it reaches the together-vote.
3. **Then the together-vote** decides whether Stages 1–5 proceed, and in
   particular whether Stage 5's scoped autonomy is granted. Money, the
   NEVER_AUTOMATIC subjects, and the operator's own free-will decisions stay
   human-held throughout, by construction, whatever the vote decides about the
   rest.

The octopus skeleton is already in the tree, already safe, already wired to the
verdict stream. The work is to give its arms memory and bounded local plasticity
— carefully, behind the same gate everything else answers to.
