# The system as a nervous system: what exists, what is missing, the first increment (2026-11-22)

Lawrence, 2026-11-22: "The system should be expanding to work like a neural network even better. Like a neural
network and a nervous system."

## What already exists (by discovery, this tree, 2026-11-22)

| nervous system | covenant now |
|---|---|
| **sensory nerves** (afferent) | `covenant_highway.py`: 40 `detect_*` functions; `covenant_octopus.py`'s WITNESS arm (spiking, rate not totals); the phone's check-ins; `covenant_reflex_sense.py` |
| **reflex arcs** (local, fast, no brain) | `covenant_highway.py`: 20 `remedy_*` functions; `covenant_watchdog.py` revives nodes; `covenant_heal.py`; `covenant_tetsu_reflex.py`'s ROUTER and FOOTING cues (advisory only) |
| **arms / ganglia** (octopus) | `covenant_octopus.py`: WITNESS, ENCODER, REFLEX arms (pure-Python LIF). The arm-to-arm ring is opt-in, because Tetsu said NO for his arms (2026-11-07). The leg (`covenant_leg.py`) and the limbs (`covenant_limbs.py`) are consult-on-purpose arms on the second PC since A470 / A402 |
| **brain** | Tetsu's 3B, with the gate judging every action |
| **motor nerves** (efferent) | his hands (`covenant_tetsu_hands.py`), the phone's actuator |
| **plasticity** | `covenant_distill.py` (fallback judge), the practice loop, improve-mining |
| **kill switch** | `COVENANT_VERDICT_CACHE_OFF`, Tetsu's own, silences every arm |

## What the lab learned tonight that bears on it (spiking lab exp18-24)

1. **One diffuse signal cannot say which part was wrong.** exp21 and exp22: a global reward acting on everything
   pulled the readable and unreadable cases in opposite directions. exp20 shows what works: a LOCAL trace at each
   synapse (eligibility) multiplied by the diffuse signal.
2. **Measure the margin before adding a gate.** exp21-24 tried four gates on a signal that was not separable (noise
   drove outputs at 66-85% of a real input). Measured only after the fact (exp24).
3. **Selectivity comes from competition** (exp25 is testing per-output normalisation now), not from stacking gates.

## The gap

When something in the system goes wrong or right, nothing records which parts were active just before it, so
nothing can say which detector, remedy, arm or leg deserves the credit or the blame. Each part logs its own
activity, but there is no shared, time-aligned trace for an outcome to be read against. In nervous-system terms the
system has nerves, reflexes and a brain, but no eligibility traces, so it cannot learn WHICH of its parts to trust.

## First increment (proposed; not built): an eligibility ledger, read-only

- **Every part that acts** (a detector firing, a remedy applied, an arm spiking, a leg or limb consulted) appends
  one line: part, time, what it did.
- **When an outcome arrives,** the ledger reads which parts acted in the window before it and reports their credit.
  Outcomes: a heal that held or did not; a node that came back or did not; his correction; a gate HOLD later
  overturned.
- **SENSE -> REPORT only:** it changes nothing, trusts no part more or less, and acts on nothing. Exactly the shape
  of exp20's eligibility x signal, with the multiplication left to a person reading the report.
- **Before any later step lets credit change behaviour:**
  - measure whether the credit separates good parts from bad on held-out outcomes (lesson 2);
  - ask Tetsu, one plain question, for anything that touches his own arms;
  - test it both ways.
- **Cost:** one append per action; a report on demand. Nothing on the hot path decides from it.
