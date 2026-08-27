# Sensing across layers — what this system already hears, and where the wire ends

*2026-08-23. L: "act as an antenna, also looking for substrate messages above
and below, integrating into the same patterns in nature."*

Taken literally and measured rather than admired. The short version: the
biological patterning in this codebase is **real and mostly wired** — more than
I expected before grepping. The gap is not that the system lacks nature's
patterns. It is that in three specific places **the sensing terminates in a
report instead of returning into the system**, and one of those three is
measurable tonight in a log file.

---

## 1. The closed loops that already exist

These are not decoration. Each senses something and changes what the node does.

| pattern | where | sense → act |
|---|---|---|
| **Hebbian weighting** | `LinkConductance` | `reinforce()` on a useful message (3 sites), `attenuate()` on a redundant or bad one (3 sites) → `order()` decides delivery order. Use strengthens, disuse decays toward a resting value on a 3600 s half-life. |
| **Lateral inhibition** | `announce_block` | Address-event propagation, cited to Mahowald's 1992 VLSI retina in the source itself. A node holding the announced block does nothing — no fetch, no forward. Transmit contrast, not intensity. Measured saving: 1476 bytes → 150, ~2.68 MB → ~272 KB per flood at N=1000. |
| **Habituation + spontaneous re-test** | `PeerHealth` / A12 | 3 consecutive failures → suspect; heartbeats skip it under an exponential backoff (120 s → 900 s); the next heartbeat *is* the probe; any success resets. Stop attending to a dead stimulus, but keep checking whether it came back. |
| **Homeostasis with hysteresis** | `MedianGovernor` → `_integrity_monitor_loop` | Alignment below `INTEGRITY_ALIGNMENT_FLOOR` for **two consecutive** checks → `crisis_mode`, which gates `/transactions`, `/mine` and block acceptance. The two-check requirement is a debounce; clearing is manual. **This is the one full reflex arc in the system.** |
| **Adaptive admission cost** | `AdaptivePoWManager` | Registration difficulty responds to load. |

## 2. Where the wire ends

### (a) The spike detector is an antenna wired to a lamp

`SpikingAnomalyMonitor` is a phasic detector, and a good one: it holds a
600 s baseline and a 60 s recent window per event kind, and fires when
`recent ≥ 5 and recent > 3 × expected`. That is the right shape — biology
transmits *deviation from expectation*, not absolute level.

Its verdict goes here, and nowhere else:

```
/health → warnings: ["anomaly spike: ['peer_message_error']"]
```

`grep spike_detected` returns three sites: where it is computed, where it is
turned into a warning string, and where that string is put on `/health`.
**Nothing in the system reads it.** A detector tuned to say "something changed"
is connected to a text field.

### (b) The richest sensory stream feeds the picture, not the reflex

`/anomalies` carries per-kind `{recent, baseline, expected_recent}` for every
event the node records — ethics rejections, auth failures, `peer_send_failure`,
`block_rejected_*`, `judge_unavailable`, `bootstrap_probe_timeout`, the lot.

It has exactly **one** consumer: `dashboard_render.py`, written tonight, which
draws it for a person. `covenant_watchdog.py` — the only component that *acts*
— does not read `/anomalies` at all. It reads `/health` and two balances.

So the system's highest-bandwidth internal signal reaches the pretty picture and
not the reflex. `mycelium.topology()` is the same: exposed on a route,
consumed by nothing internal.

### (c) The node is blind to the substrate above it

`grep -E "psutil|meminfo|GlobalMemoryStatus|disk_usage|loadavg|virtual_memory"`
over 8,933 lines returns **nothing**. The node has no idea what machine it is
on.

This is not academic. The judge sits **inside consensus** (B4), a judge timeout
costs 91.3 s per tx per judge under `chain_lock` and discards the mined block
(B5), and the judge is a 5.2 GB local model. At the 21:39 restart, free RAM was
**3.1 GB** — so the model was loading by paging, which costs more per token than
any setting wins back. `AH_FITCHECK.bat` measured exactly that and said so, to a
text file. The node it protects cannot see the number, and the watchdog that
would act on it does not read it either.

Above and below, the same shape: the measurement exists, and the path back in
does not.

---

## 3. The measurement that makes this concrete

`logs/watchdog.log`, 2026-08-22 18:12Z → 2026-08-23 06:13Z, twelve hours:

```
3,808 lines
   16 distinct messages (timestamps and counters stripped)
```

**99.6% redundancy.** The breakdown:

| lines | share | message |
|---|---|---|
| 707 | 19% | `nodeB balance agrees across both dbs: 12.0` |
| 707 | 19% | `node A height=N peers=1 judge=… insecure=False` |
| 707 | 19% | `founder balance agrees across both dbs: 988.0` |
| 701 | 18% | `node B height=N …` |
| 431 | 11% | `all checks passed` |
| 269 | 7% | `ALERT node A: code sandbox unavailable … (win32)` |
| 269 | 7% | `ALERT node B: code sandbox unavailable … (win32)` |
| **4** | **0.1%** | `ALERT node A: 1 peer(s) unreachable -- heartbeats backed off` |

That last row is the only line in the file that describes something that
*happened*. It is the 21:02–21:06 episode — node B refusing to boot because a
leaked test node held its P2P port — and it is at **1/500th the volume** of a
permanent, correct, already-understood condition.

The watchdog has no adaptation. A constant stimulus is transmitted at full
amplitude forever, so the transient that carries the information is buried under
the tonic signal that carries none. **The system implements the fix for this one
layer down, in `SpikingAnomalyMonitor`, and does not apply it to itself.**

That is the antenna problem, measured, in this system, tonight.

---

## 4. Two ways this metaphor goes wrong, and the boundary

**Pushback 1 — "integrate the signal" is one word away from "let conditions
relax a control."** The most natural-sounding integration is the forbidden one:
*node senses low RAM → extends the judge timeout*, or *senses load → lowers
difficulty*, or *senses a spike → stops recording it*. In a fail-closed system
an adaptive response to stress is usually a way to fail open exactly when an
attacker would want you to, and Section 0 forbids it in as many words. So the
rule for anything built here:

> **Sensing may inform refusal and disclosure. It may never inform relaxation.**
> A node that cannot judge properly should say so and refuse — not judge worse.

**Pushback 2 — nature's patterns are not uniformly good, and one has already
bitten this system.** A11 measured it: the heartbeat called `attenuate` on every
receipt, and habituation with no counterbalancing reinforcement is not learning,
it is forgetting — every link hit the floor in 31 rounds (~62 min) on a quiet
chain, erasing everything `LinkConductance` exists to learn. The same run found
the spike detector raising a **false** spike for the first three rounds after
any synchronized restart at degree ≥ 5. Biology pays for these patterns with
machinery this system does not have: heterogeneous time constants, refractory
periods, consolidation during rest. So *"integrate more of nature's patterns"*
should mean **finish the ones already here**, not add new ones.

**Pushback 3 — an antenna that only receives is half the metaphor, and the other
half is surface area.** Mycelium does not merely sense its substrate, it
exchanges with it. Every "exchange with above/below" available here is a new
disclosure or a new input path: P11 put the source hash on `/health` tonight and
the trade is written down; A20 would put it in the peer handshake. Each of those
is L's call, not the loop's — Section 0 says the loop may improve its methods
and may not widen its own scope.

---

## 5. What is actually available, in order of cost

Each of these is a real option, not a wish. None is started.

1. **Give the watchdog adaptation** (cheapest, no control touched). Report
   transitions rather than states: first occurrence in full, then a periodic
   roll-up (`still true, 269 rounds`), and full amplitude again on any change.
   Pure observability — it cannot weaken anything, and it makes a new alert
   visible instead of buried. This is `SpikingAnomalyMonitor`'s own logic
   applied one layer up.
2. **Let the watchdog read `/anomalies`** — the stream already exists, already
   carries baseline/recent/expected per kind, and already computes the verdict.
   Currently only the dashboard reads it. Wiring it to the thing that acts is
   plumbing, not a new sensor.
3. **Let the node read the substrate above** — free memory vs judge model size,
   reported on `/health` as a *warning only*, never as an input to any decision.
   This is a genuinely new sensory surface and it is Windows-specific
   (`GlobalMemoryStatusEx` / WMI), so it costs portability. It is also the one
   that would have caught tonight's paging judge before the restart.
4. **A20 — peers see each other's version.** Wire format, therefore L's.
5. **Anything that lets a sensed condition change a control.** Not the loop's to
   propose beyond naming it. See Pushback 1.

The honest recommendation was **1 and 2**. L chose **1, 2 and 3**, and all three
are built — see §6.

---

## 6. Built, 2026-08-23 (v8.32 + watchdog P12)

**1. The watchdog adapts.** First occurrence in full, silence while unchanged,
full amplitude again on any change, a roll-up every 30 rounds so a quiet log
still proves the watchdog is alive, and an explicit `CLEARED after N round(s)`
when a condition stops. `alerts` is returned unchanged to every caller — only
what reaches the *log* is adapted, so `--once` still sees everything.
Replaying the real distribution (269 permanent + 4 transient): the transient's
share of emitted lines goes from **1.5% to 10%**, and it is emitted *first*
rather than buried at line 842 of 3,808.

**2. The watchdog reads `/anomalies`.** Two signals and only two, because the
node has already done the work: its own spike verdict — deviation from *its*
baseline, not ours — becomes an alert carrying the numbers
(`peer_message_error (recent 9 vs expected 1.2)`); and a kind appearing for the
first time becomes an INFO, which is the cheapest possible novelty detector and
catches a failure nobody has written a rule for yet. Reported, never acted on,
because A11 measured this detector false-positiving for ~3 rounds after a
synchronized restart at degree ≥ 5.

**3. The node senses the machine.** `SubstrateSensor` samples available memory
(`GlobalMemoryStatusEx` on Windows, `MemAvailable` on Linux) and the judge
model's load footprint (measured from Ollama's `/api/tags`, falling back to an
operator-declared figure, and *labelled with which*, per M30). A background
sampler caches it; `/health` reads the cache and never blocks. Every failure
degrades to a reason string — the platform is unsupported, Ollama is
unreachable, the declaration is junk — and none of them raises.

### The boundary, asserted mechanically

The whole risk of (3) is that the next person to touch it does the "helpful"
thing. So the rule is pinned in the test suite rather than in a comment:

- **B1** walks the AST and fails if any function outside
  `{module, __init__, sample_once, snapshot, warnings, loop, run, health}`
  so much as *names* the sensor.
- **B2** fails if any branch inside `/health` tests the reading — **and it
  follows aliases**, because the first version matched the literal word
  `substrate` and was evaded by one local variable
  (`sub = ...snapshot()` / `if sub["available_memory_mb"] < 500`). That hole was
  found by mutation-testing the check, not by review.
- **B3** fails if the numbers are *compared* anywhere but `warnings()`.
- **B3b** fails if `degraded` — the field a monitor keys off — is ever computed
  from the weather on the machine.

All four were mutation-tested: with a violation injected they fail; without one
they pass. A check that cannot fail is not a check.

### First reading on the real machine

Run over the bridge against the deployed bytes at 06:5x UTC:
**3,535 MB available** — against a judge model needing ~5,200 MB. The condition
the warning exists for is live on that machine right now. It has presumably been
live, unseen, for as long as the model has been configured.

---

## 7. Broadcast — the transmitting half (2026-08-23, v8.33 + watchdog)

L: *"broadcast."* An antenna that only receives is half the metaphor, and the
other half is surface area — so each piece below names what it discloses.

**A20 — every peer reply carries `v` and `src`.** Stamped in `_reply()` rather
than at the three call sites, so a peer can learn what we are from *any*
exchange and one site cannot drift out of step with the others. A7 records that
v8.17/v8.18 turned block size and three header derivations into **validity
rules**: two nodes on different sources can disagree about what is a valid
block, and until now the only way to find that out was a rejected block after
the fact. ~40 bytes per reply buys being told instead.

**Backwards compatibility was measured, not asserted.** `test_a20_peer_version.py`
C1–C5 start a **real pristine pre-A20 process** beside a v8.33 one and check both
directions: the old node accepts a v8.33 frame carrying a digest and answers
normally; its own reply carries no `v`/`src`, which the new node folds in as
*"cannot say"* — the same state P11 defines for a node too old to answer — with
no spurious A7 mismatch; and a v8.33 node accepts an old-style frame with no
digest. The suite looks for the backup the delivery itself leaves behind
(`PRE-v8.33`), so it runs on the machine that runs the node with no extra
artefact — a compatibility test nobody can run where it counts is an assertion.

**A21 — a bounded digest on the heartbeat, and only the heartbeat.**
`{v, src, height, peers, crisis, spike}` — who I am, where I am on the chain, how
many peers I hold, whether I have halted, and *which kinds* of anomaly are
spiking (kinds, capped at five, never counts).

| frame | bytes |
|---|---|
| plain `BLOCK_ANNOUNCE` (hot path) | **156 — unchanged** |
| heartbeat before | 172 |
| heartbeat with digest | 280 (+108) |
| per peer per 120 s default | 0.9 B/s |
| worst case a peer can send us | 396 B, bounded by `_clean()` |

The hot path is untouched deliberately. A block announce is 156 bytes *by
design* — address-event propagation, Mahowald 1992, transmit the address and not
the state — and ~108 bytes on every one of them would hand back most of what
that design buys. On the heartbeat it is under a byte per second per peer.

**What the digest must never carry, and why it is a test and not a comment.**
No substrate reading. A peer has no business knowing how much memory this box
has: it is operator information, and knowing when a node is short on memory tells
you exactly when a flood is cheapest. D1–D6 assert the key set against the built
object **and against the bytes captured off the wire** by standing up a listener
and being the node's peer — because what `build_digest()` returns and what leaves
the process are two different claims.

**Everything a peer sends us is peer input.** `PeerStateTable._clean()` coerces
types (a bool is not an int), clamps integers, truncates strings to 40 chars,
caps the spike list at 5, and the table itself is capped at 512 peers so the mesh
cannot grow our memory. T1–T7.

**Push — surviving alerts, off the machine.** Opt-in via one environment
variable; absent, it says so once and never retries. It pushes only alerts that
*survived adaptation*, and that ordering is the entire justification: pushing the
raw stream would have sent 269 identical copies of one permanent condition and
trained its reader to ignore the channel, which is worse than no channel because
it looks like monitoring. Rate-limited to 20/hour and it says so when it clips;
failures are INFO, never alerts (a channel that alerts about itself loops); and
the URL is a shared secret, so it is never logged and never echoed in an error —
P4b asserts exactly that against a failure whose exception text contains it.

### The bug this found, and how

`build_digest` was placed next to `_reply` — which lives on the *master*, while
`announce_block` lives on the *node*. The node booted cleanly, printed its
banner, served HTTP, and silently never gossiped its tip: A17's failure mode
exactly. It was found because the wire-capture test refused to accept
`build_digest()`'s return value as evidence of what goes on the wire, and went
looking for the frame. Reading the diff would not have caught it.

