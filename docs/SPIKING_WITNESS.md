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

### The phone-side witness of the PC (built, covenant-phone branch brain/witness, NOT pushed)

The independent OUTSIDE path -- the one reading neither the highway nor `covenant_witness` can make, because both
run on the PC and read the PC's own ledgers. A neuron on THE PHONE over the PC's answers to this phone's check-ins.
- `entry.pc_beat` keeps each beat `{t, ok}`; `entry.PcPacemaker` is a leaky integrate-and-fire neuron in BEAT space
  (not wall-clock: Android deep sleep stretches the interval to hours and must not decay a real outage). A miss
  adds more than an answer drains -- the asymmetry means it fires on a sustained outage AND on a flaky PC that
  answers occasionally, the blind spot of NodeService's fixed consecutive-count (144 = 24 h, which any single
  answer resets).
- `entry.pc_witness` returns the spiking reading beside the fixed count and whether they agree; a disagreement is
  the finding. It raises nothing and acts on nothing; NodeService keeps the authoritative reconnect notice.
- M5.80a-f, M5 312/312, five mutations each red. Commits db903f8 + 078d055 on brain/witness. Not pushed (phone main
  reaches his phone only on his yes).
- **Surfaced in the /pc display (PC side on main, dd48e47).** The phone sends its witness reading in the check-in
  (`entry.pc_witness_summary` + NodeService); `record_checkin` keeps a bounded, type-safe `pc_witness` block;
  `covenant_pc3d._last_checkin_witness` reads the newest one and hides a reading older than 6 h; the /pc Phone orb
  goes amber and says "the phone reports a degraded link: its witness has been missing my answers (N recent
  misses)" when the two readings disagree -- the finding the PC cannot see on its own. DP1 D19w/D19w2, three
  mutations. The PC side reads the field only when present, so it is inert until a phone build carries it.

### The forum-strike twin, built then RETIRED (Amendment 2, 2026-10-19)

**What I claimed, as written:** "Moltbook-strike leaky-burst twin ... KEPT: it fires over the 12-unsolved run on
record (a labelled incident). Real data: 114 challenges, 35 solved, 71 abstained, 8 failed." I built it
(`covenant_witness.strike_report`) and said it passed.

**Five models refuted that on review (cycle a32894190cdb: Gemini, Meta AI, Mistral, Chat Smith, DeepSeek), and they
were right:**
- It does **not beat the baseline.** The highway's consecutive-unsolved count also fires on the 12-run, so the twin
  is no improvement there (Meta AI).
- It reads the **same observation path** (the challenge stream), so it fails the independence rule -- a second
  mechanism, not a second reading (Meta AI).
- It **restates the base rate.** The account is unsolved 79 of 114, so any accumulator fires ~continuously; firing
  on 108 of 114 is a description, not a detection (Gemini, Mistral, Chat Smith).
- The deepest flaw, which is the bar's, not the twin's: the keep test had **no specificity.** "The whole layer is
  validated only on positives" (Mistral) -- it tested that a twin fires on a labelled incident, never its
  false-alarm rate on incident-free periods.

**Retired.** `strike_report` now returns `kept: False` with the reason; the code stays as a shadow, reusable only
for a stream with an independent path where the twin beats the baseline at a fixed false-alarm rate. WN1.17-19.

## Amendment 3 (2026-10-19, after "run it by the others": CUSUM first, spiking only where it provably wins)

He said "run it by the others" and "hammer them." Tetsu, Gemini, Mistral and Grok reviewed the plan to adopt the
external methods (NAB, OeSNN-UAD, Fast_BOCPD/CUSUM, ED-sKWS). The verdict was UNANIMOUS, and it corrects the
direction of this whole file:

1. **NAB is a poor fit, not a solution.** On streams of 114-4000 events with 2-3 incidents, NAB's window-reward
   scoring is "numerically degenerate" (Gemini), "statistically unidentifiable" (Mistral), "statistically
   meaningless" (Grok). Adopt only the PRINCIPLE -- a false positive lowers the score, reward only the earliest
   detection in a window -- never NAB's normed scores or profile cutoffs.
2. **CUSUM is the sufficient statistic here; spiking buys nothing provable.** "On ~200-event streams a CUSUM with
   recovery/hysteresis is the sufficient statistic; OeSNN-UAD adds variance without power" (Mistral). "An evolving
   SNN buys almost nothing a well-tuned CUSUM/BOCPD does not" (Grok). Tetsu: "just run CUSUM and stop calling it
   spiking." So: **build CUSUM/BOCPD as the actual monitoring detector**, with an explicit recovery/hysteresis
   spec. A spiking twin is added only if it is MEASURED to beat CUSUM at an equal false-alarm rate on a real
   negative set -- and that is unproven for every monitoring stream, so there is no spiking redundancy here yet.
3. **The twins already built are re-labelled.** The phone-silence pacemaker and the phone-side witness are a
   SECOND OPINION, not redundancy, until each is shown to beat CUSUM at equal FP rate on a held-out negative set.
   They remain read-only and act on nothing; nothing is deleted.
4. **The one thing worth building now is the negatives pipeline, not another neuron.** Get honest negatives by
   running the detectors read-only and logging alerts-but-ignoring them ("silent accumulation is free", Mistral),
   over months, treating only verified incident-free periods as negatives. NEVER manufacture an incident. Until
   that volume exists, "beat a baseline on a single missed incident" is a case study, not a test (Mistral).
5. **ED-sKWS is gated on a measurement, not adopted.** The deciding number is energy (mJ) per wake at equal
   keyword-miss and false-wake rates versus a simple energy/VAD gate, on real audio; the SNN must cut energy or
   latency by >30-40% while matching accuracy or the simpler gate wins (Grok, Gemini, Mistral). A future lab
   experiment, not a plan item yet.
6. **Dissenting depth (Gemini):** on 3 incidents, a Bayesian/survival view would not score discriminative detectors
   at all -- model the generative process and treat negatives as right-censored intervals. Kept on record as the
   stronger method if the event counts stay this small.

**Net:** stop expanding the spiking monitoring layer. Build CUSUM + the negatives pipeline; prove-or-retire each
spiking twin against it. Spiking stays where it is proven (the road neurons) or is about efficiency and measured
(ED-sKWS). Answers kept whole in the scratch record; the consult ledger's daily budget was spent, so they were not
recorded there.

**The foundation, BUILT (his "put the foundation through ... just do it", 2026-10-19), in `covenant_witness.py`:**
- `CusumDetector(k, h, recover)`: the one-sided CUSUM with reset and a recovery hold (hysteresis) -- the sufficient
  statistic a twin must beat.
- `extract_negatives(event_times, incidents)`: the honest negatives -- the incident-free spans of a real stream,
  nothing manufactured.
- `score_detector(fires, incidents, negatives)`: the NAB PRINCIPLE, not the benchmark -- caught incidents, and
  false alarms on the negatives with a per-day rate.
- `beats_baseline(twin, base, incidents, negatives)`: Amendment 3's keep test in code -- kept only if the twin
  catches an incident the baseline MISSED at a false-alarm rate no worse than the baseline's; otherwise the reason
  (restates the baseline / worse FP rate / misses incidents). This is prove-or-retire, mechanised.
- Read-only; acts on nothing. WN1.20-24 (5 checks), five mutations each red, restored byte-identical. The negatives
  pipeline (running the detectors read-only over months and logging alerts-but-ignoring) is the next build on top
  of this; the machinery to judge it now exists.

## Amendment 2 (2026-10-19, after the five-model review, before any further twin)

The keep test of Amendment 1 is strengthened. A twin is kept only if ALL hold:
1. **Independence:** it reads a genuinely different observation path, or it is labelled "second opinion" and never
   claimed as redundancy. (The phone-side witness passes -- it reads the PC from the phone. The forum-strike twin
   failed -- same ledger.)
2. **Beats the baseline on a labelled incident:** it must catch an incident the plain baseline (a consecutive count,
   a CUSUM, or an EWMA) MISSES, or catch it sooner -- not merely also catch what the baseline already catches.
3. **Specificity, measured on a held-out set of NEGATIVES:** its false-alarm rate on incident-free periods must be
   below a fixed bound (at most one told alert per twin per week, the bar Amendment 1 already set for the phone
   silence). A twin that fires at ~the base rate is retired, whatever it does on the positives.
4. **Hysteresis:** every twin must define its recovery/reset and a quiet period, so an accumulator cannot sit
   saturated (Gemini: "never defines recovery, reset, or quiet periods").

**And efficiency, named honestly (all five):** adding a monitor is a COST, not a saving. Spiking cuts compute only
where it GATES execution -- waking a dormant worker on a threshold crossing instead of polling. The only measured
cut so far is the road neurons (6 connect attempts over 20 calls instead of 40). The next efficiency work is to
find a dense polling loop a spike can gate, not another monitor. The pacemaker and the phone witness are
PROVISIONALLY kept, pending their specificity measurement under rule 3.

### Still to build

Node-height progress (the reviewers' pick: clear monotonic velocity, a baseline-missed stall is well defined) as the
next twin, under the Amendment 2 bar; a held-out negative set for each stream; and a dense polling loop for a real
efficiency cut. Tailscale's own view beside the check-in ledger and a per-ledger writer pacemaker remain. None wired
to act until each clears the Amendment 2 bar.
