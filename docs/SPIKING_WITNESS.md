# The spiking witness: a redundant layer, by a different mechanism

**Asked 2026-10-19:** *"improve the spiking system to expand / have it be a redundant layer of
everything weve developed and grew"*, then *"ensure continuity discuss with the others"*.

**Status: PROPOSED, REVIEWED, not built (A375).** This file is the plan, written before any
code, for the other models to review. Their answers, and Amendment 1 (what changed because of
them), are at the end. Nothing here acts.

## What "redundant" has to mean to be worth anything

A second copy of a check is not redundancy: it fails in the same places. A redundant layer earns
its keep only if it reaches the same verdict **by a different mechanism**. Then agreement is
confidence, and **disagreement is a finding**: one of the two is blind.

The record says why this matters here:
- **A329.** The road read every phone build and never the phone. It took 53 hours for the
  silence to be noticed.
- **A65.** 35 of 36 guards grepped source text instead of running anything.
- **A288.** "Highway green" was a reading of 7 detectors out of 25.

Each was a single witness with a blind spot nobody could see from inside it.

## What exists (counted 2026-10-19)

- **The highway** has 29 detectors defined and 28 registered. `public_email_exposure` was
  retired on his word.
- **Already spiking:**
  - the road neurons (A374): one leaky integrate-and-fire neuron per road to the PC;
  - the wake-word lab's spiking encoder E1, which is not deployed.
- **What a spiking layer can honestly watch.** A detector whose input is a **stream of timed
  events** can be twinned: check-ins, asks, rounds, answers, admissions. A detector whose input
  is a **comparison of states** cannot: hashes, builds, CI status, the manifest. A neuron there
  would be the same comparison wearing a costume.
- **By that rule, 6 of the 28 have an event stream:**

| highway detector | its stream (already written today) | spiking twin |
|---|---|---|
| `phone_silent` | `ops/phone_checkins.jsonl` (every ~600 s) | pacemaker: silence |
| `tetsu_asks_failing` | `ops/model_asks.jsonl` (ok / failed) | leaky burst: failures |
| `ambassador_stalled` | the ambassador's sends ledger (live rounds) | pacemaker: silence |
| `moltbook_strikes` | verification answers (solved / failed / abstained) | leaky burst: strikes |
| `height_lag` | node heights per poll | progress: a height that stops rising |
| `node_down` | health polls per node | leaky burst: failed polls |

- **New senses, with no highway detector today:**
  - the watchdog's own rounds stopping. `watchdog_stale` asks something else: whether the
    running watchdog is older than its code (file time against process start). The first draft
    of this table called that a twin; it is a state comparison.
  - bursts of off-tailnet refusals in `ops/mycelium.jsonl` (someone knocking);
  - the spore road's unanswered and refused blocks.
- **Not covered, said plainly.** The other 22 detectors are state comparisons. The spiking
  witness is redundant for about a fifth of the road (6 of 28), plus three new senses. It is not
  "a redundant layer of everything", and calling it that would be the A288 error again.

## The two neurons

Both are event-driven: the leak between events is solved exactly, `v * exp(-dt / tau)`, so
nothing runs between events. That is what spiking is actually good at.

1. **Pacemaker (silence).**
   - A constant drive raises the potential, and each event resets it.
   - If events stop, the potential crosses threshold and the neuron fires: *silent*.
   - The drive is set from the stream's own measured cadence (the median interval), so it
     learns what "normal" is per stream. The highway instead uses one fixed hour count
     (3 h for the phone).
2. **Leaky burst (failures).**
   - Each failure adds charge, each success removes some, and the charge leaks.
   - It fires on failures that come close together. Scattered ones never sum.
   - The highway instead counts failures in a fixed window.

Different math from the highway's, on the same stream. That is the point.

## How it runs, and what it may do

- **Read-only, always.** It reads the ledgers the system already writes. It has no remedy,
  sends nothing, and changes nothing.
- It runs beside `covenant_highway.sense()` in the watchdog's round, as the daemon only (A370's
  rule). Each twin's verdict is set next to its highway detector's.
- **Disagreement is the output.** A row goes to `ops/spiking_witness.jsonl` saying which side
  said what, with both sides' measurements. A disagreement that persists for N rounds is told
  once, and once again when it clears, the way an hourly FAIL is (A235).

## The bar, fixed now, before any code

Replay the last 30 days of the ledgers. For each twin:

1. **It must find the two known phone silences from the check-in ledger alone:** about 53 h from
   2026-10-08 (A329), and the drop from 2026-10-12 06:48. If it misses either, the twin is
   rejected.
2. **Agreement with the highway's recorded PRESENT/ABSENT transitions** for the same condition,
   within one round, reported as a percentage.
   - Every disagreement is opened and labelled: the highway blind, the witness blind, or a
     threshold difference.
   - No threshold is tuned on the replay that scores it. Tuning uses the first 15 days and
     scoring the last 15.
3. **The false-alarm rate** on the scored 15 days must be at most one told disagreement per
   twin per week. Above that, the twin is shadow-only: recorded, never told.

What the replay cannot show: a silence that happened while the ledger itself was not being
written. Both witnesses go blind together there, and only a third, outside one can see it.

## Questions for the reviewers

1. Is "same verdict by a different mechanism" sound redundancy here, or theatre? Where does it
   fail?
2. Is the 7-of-28 split right? Is any state comparison secretly an event stream, or the other
   way round?
3. Is the bar above strong enough, and is the 15/15 split honest?
4. Should the neurons stay hand-set from measured cadence, or learn (STDP)? What would learning
   cost in false alarms?
5. What is missing?

## Review (2026-10-19, cycle b8b66fb396ac)

Seven readers saw the plan above before any code: Tetsu, with a fresh ask; and six models with one packet through
his Edge.
- **Context readers:** Gemini, DeepSeek, Mistral and Meta AI.
- **Blank slate:** Grok on X and Chat Smith's GPT-6 Luna.

Their answers are in `ops/ai_consult.jsonl`, kept whole in `ops/ai_consult_answers/` (both gitignored). They are
opinions recorded as such.

**The finding all six named first: the witness shares the highway's input.**
- Different math on the same ledger catches a logic mistake. It cannot catch a missing, delayed or corrupted
  shared input.
- The plan's own "known blind spot" is the proof.
- In their words, this is algorithmic diversity, not independent sensing; "different algorithm is not different
  sensing".
- Claim 1's "agreement = confidence" is too strong as written.

**Also raised:**
- **Gemini:** a median that adapts online learns the very silence it should catch. A static one breaks when the
  phone legitimately slows down (battery saving).
- **Gemini:** two models with different time constants will disagree near every boundary, so "one told
  disagreement a week" is optimistic unless the comparison is damped.
- **Mistral and Meta AI:** two known silences, both on one stream, are thin ground truth. The bar is strong for the
  phone and weak elsewhere.
- **Chat Smith:** prove it with fault injection, not only with history.
- **Mistral:** monitor the ledger writer itself.
- **DeepSeek and Mistral (statistics and SRE views):** a plain change-point detector (CUSUM) or two threshold rules
  might do the same job with nothing to explain. The neurons must earn their place against that.
- **Grok:** the 6-of-28 split may undersell independent timing on state checks.
- **Chat Smith:** a state check can be turned into a stream of changes. That alone does not make it independent.
- **STDP:** Mistral and DeepSeek say not on non-stationary streams, which costs false alarms. Meta AI's ML view
  would try it and pay in false alarms on drift.
- **Tetsu:** watch the phone's check-ins first, and run a witness on the phone too, so the phone can tell when the
  PC goes quiet.

## Amendment 1 (2026-10-19, after the review, before any code)

The plan above is kept as written. These changes govern the build:

1. **A twin must read a different observation path than the detector it twins.** Same-ledger twins are recorded,
   but they are labelled "algorithmic second opinion", never "redundant".
2. **Independent paths, first build:**
   - **The phone witness (Tetsu's ask).** A pacemaker on the PHONE, over the PC's answers to its check-ins. It
     watches the PC from outside: the third, outside witness the plan said both PC-side layers lack. It goes on the
     covenant-phone branch beside the road neurons, and it ships only with his yes.
   - **Tailscale's own view of the phone** (its last-seen time and byte counters), next to the check-in ledger.
     That is a different sensor, read by a different program.
   - **A writer pacemaker per ledger.** It watches each ledger the highway reads by its write time, so "the ledger
     stopped" becomes its own condition instead of a shared blind spot.
3. **Cadence frozen from the tuning half, never adapted online** (Gemini's point). A legitimate change of cadence
   is a disagreement for a person to see, not something the neuron quietly learns.
4. **A third, non-spiking baseline on the same streams:** a one-sided CUSUM. The spiking twin is kept only where it
   catches at least what CUSUM catches, at no more false alarms. If it does not beat a plain detector, it is
   retired with the reason, which is what DeepSeek and Mistral's view asks.
5. **Fault injection beside history.** Synthetic silences and failure bursts of known start and length are injected
   into the replay. Detection delay is scored on every injected fault, and both real silences remain hard
   requirements.
6. **Hand-set, no STDP in this build.**
7. **Unchanged:** read-only, daemon only, disagreement told once, and the 15/15 tune/score split.

## Built so far (2026-10-19): the phone-silence twin

`covenant_witness.py`, read-only, nothing wired into the watchdog yet.
- **Pacemaker (spiking):** a leaky integrate-and-fire silence neuron. A constant drive raises its potential; each
  check-in resets it; it fires when the potential reaches 1, which is exactly `fire_gaps` median gaps after the last
  check-in. Set from the stream's own median gap (10 min on the real ledger), frozen from the tuning half.
- **CUSUM (the baseline it must beat):** a one-sided cumulative sum over the gaps. A plain change-point detector.
- **Measured on the real check-in ledger (4,028 check-ins, 09-13 to 10-19):** median gap 10 min; the pacemaker fires
  after 1 h; it finds both known silences (A329's 53 h from 10-08, A338's drop from 10-12) and covers every silence
  CUSUM catches. So by Amendment 1's keep test it is kept, not retired.
- **WN1 10/10**, three mutations red (the fire window, the silence math, the UNKNOWN path); the keep test is also
  checked independently of the report field (WN1.4). Fault injection: a synthetic 30 h silence is found where placed.
### The leaky-burst twin (built, SHADOW/UNKEPT): an honest null for now

`LeakyBurst` over the model-ask stream (`ops/model_asks.jsonl`): each failure adds charge, each success drains some,
the charge leaks, and it fires when failures cluster. The mechanism is checked both ways (WN1.11-13: a cluster
fires, the same failures spread wide do not, successes between them drain it).

- **But it has no validated bar, so it never acts.** Measured 2026-10-19: of 4,072 asks, 39 failed, 1-5 on most
  days. The known Tetsu-down incidents (A329 10-08, A282 10-06) show only 1-2 FAILED asks each -- because when
  Tetsu is DOWN, asks are not made, so there is no failure row. That silence is `tetsu_cannot_answer`'s (a
  readiness check), not this stream's. So there is no labelled failure-burst to score against, and Amendment 1's
  keep test cannot be met here (rule 5: what counts cannot be computed without the ground truth).
- It is kept in the code because the mechanism is correct and reusable for a stream that DOES have labelled
  incidents -- the forum-strike stream (A283/A324), the next candidate.

### Still to build (Amendment 1)

The phone-side witness of the PC (the independent outside path; phone branch, his yes), Tailscale's own view
beside the ledger, a writer pacemaker per ledger, and the leaky-burst over the forum-strike stream (which has
labelled incidents). None wired to act until the replay bar is met for each.
