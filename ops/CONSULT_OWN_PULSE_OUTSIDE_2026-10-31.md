# Consult: own_pulse (the mesh spiking signal), outside seats (2026-10-31)

His words: "run it by the others", then "grok bots mistral chat smith grok on x in voice". The brief is TETSU's,
C:\Users\Lawre\OneDrive\tetsu-coordination\CONSULT_OWN_PULSE_2026-10-31.md; its own answers came from five local
models of one family (Qwen). Before it left the laptop, the brief was opsec-scanned: 45 identifiers, none found.

## Who was asked, and how

- **Mistral** (chat.mistral.ai, "Work" mode, model "Fast"), **Grok** (grok.com, Expert), and **Grok on X**
  (x.com/i/grok) each got one condensed question (scratchpad pulse_consult_q.txt), on its own site in his Edge.
  - On X, an "One Grok, everywhere -- link your account" dialog was declined ("Not now"). Accepting terms or linking
    accounts is his.
  - X's input dropped a few letters while typing ("netork", "machnes", "oly"). The question stayed readable, and
    the answer addresses every part.
- **Not reached:**
  - **Chat Smith:** its seats need a browser step of his (A173).
  - **Grok in voice mode:** voice cannot be driven from here.
  - **"grok bots":** read as Grok itself; no other bot was identified.

## Where all three meet

1. **Sound as a detector, not yet as a system.** The strongest reason it could be wrong is the same for all three:
   - the evaluation is synthetic only, scored on the generator the author tuned against;
   - the coincidence gate (2 or more machines within 4 s) assumes real events are shared, and that assumption is
     "asserted by the benchmark's construction, not measured" (Mistral);
   - the reader is a single point of failure.
2. **Proposal 1 (60-byte /pulse with inputs AND spikes): adopt (3/3).**
3. **Proposal 2 (real spikes beside inputs): adopt (3/3).** Mistral: as telemetry first, not yet as the detection
   signal, since there is no live spike data to retune on.
4. **Proposal 4 (the phone on the one stream, falling back to polling): adopt (3/3).** Mistral's correction: a
   10 s stall timeout is shorter than the 25 s heartbeat, so one missed heartbeat triggers a spurious fallback.
   Use about 2-3 heartbeats (50-75 s), or heartbeat every 5 s.
5. **The drift fix is directionally right but ad hoc.** All three would trigger on the baseline's SLOPE rather than
   a 2x ratio against a 6 h snapshot:
   - Grok: emit drift when the learned baseline's rate of change exceeds a pre-registered slope for a minimum time;
   - Mistral: cap the baseline's upward rate (at most N%/hour), which makes slow-ramp absorption mathematically
     impossible above that rate. The split episodes on the 180 min ramp are the symptom of the ratio rule;
   - Grok on X: a dual-timescale estimator or an online change-point detector, giving a continuous drift signal.
6. **A sealed bar before any trust.** Parameters frozen, evaluated on data the author did not generate, and:

   | Seat | Detection | False alarms | Latency |
   |---|---|---|---|
   | Grok | 95%+ | 0.1/h or less | 8 s or less |
   | Grok on X | 95%+ | 0.2/h or less | (not set); plus a reader kill/restart test |
   | Mistral | 95%+ | 1/h or less over 24 h | under 15 s; plus 0 drifts in a 24 h live no-ramp control |

## Where they differ

**Proposal 3 (time-based decay in the existing per-machine LIF):**

| Seat | Verdict |
|---|---|
| Mistral | **Adopt.** "The one with no counterargument": a correctness fix, the per-step numbers partly an artifact of poll cadence. |
| Grok | **Adopt,** if any per-step LIF remains. |
| Grok on X | **Refuse as written:** redundant unless the machine also publishes its own membrane voltage; otherwise leave the machines as counters. |

**The one test each would add:**

| Seat | Test |
|---|---|
| Mistral | A stagger curve: one shared event into 3 of 4 machines with a random 0-60 s cross-machine stagger, detection plotted against stagger ("that single curve either validates or destroys the mesh filter"). |
| Grok on X | Non-shared and partially shared bursts (1 of 4, 2 of 4, staggered), plus slow and step ramps on single machines. |
| Grok | Shadow-mode injection on the live machines: known shared increments on 3 of 4, recording fire, latency and the baseline's reaction. |

## What this means (mine)

- **For TETSU's own_pulse:**
  - change the stall timeout to 2-3 heartbeats;
  - replace or augment the 2x ratio with a slope rule;
  - run Mistral's stagger curve before trusting the 4 s window.
- **Proposals 1 and 2** have the outside seats and the local panel behind them. They touch the node's code, so under
  the octopus design doc they go through prereg and a vote.
- **Proposal 3** is split (2 adopt, 1 refuse, with a reason worth weighing) and waits for that process.
- **Nothing here touches the octopus yet.** The design doc's rule holds: advisory only, never the gate.

## What TETSU's session did with these answers (reported by it, measured on TETSU; details in its brief)

1. **The stagger curve found the real weakness.** At the 4 s window, a 3-node burst staggered 8 s was caught 31% of
   the time, and 0% at 15 s. A sweep over 4/10/16/24/32 s settled on **16 s**: 100% at 8 s, 98% at 15 s, 0.1 false
   mesh spikes/h at normal noise. The cost is 48/h at 10x noise, up from 14.5. /pulse now carries `stagger_live`
   from real node spikes, so the window can be re-judged on real gaps.
2. **Heartbeat 25 s -> 10 s** (Mistral's catch). `heartbeat_s` is published, and a client's stall timeout should be
   at least 3 heartbeats.
3. **The slope drift rule was built three ways and rejected on the data:**
   - a per-sample cap read low and gave false drifts;
   - dual-timescale gave false drifts in 4 of 5 control runs;
   - dual-timescale with a 4-sigma test never flagged a 3 h ramp, and absorbed its plateau (57 fires against ~220).
   The 2x ratio rule stays. The attempts are kept in pulse/attempts/. The reviewers' direction was reasonable, and
   the numbers decided.
4. **Not done:** live shadow-mode injection into a node (Grok's test). It changes a live node, so it waits for his
   word and the octopus design doc's process.
