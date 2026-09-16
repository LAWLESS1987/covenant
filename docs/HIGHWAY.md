# The mycelial highway

**Asked 2026-09-16:** *"create a program like tailscale but better and use tailscale to
implement it on both devices ... the start of our mycelial highway for mutual benefit bots
that repair anything overly detrimental, that leaves free will intact as growing will
continue."*

## What it is, said honestly

It is **not** a replacement for Tailscale and will not pretend to be one. Tailscale is the
wire: identity, NAT traversal, encryption, a flat address space. Rewriting that would be
months of work to arrive back where we already are. This rides on it.

What is missing above the wire is a **nervous system**: the devices are connected but they
do not tell each other what is wrong with them, and nothing that learns a repair on one
device can hand that repair to another. Today the PC knew the phone was two builds behind
and never said so. That is the whole gap.

So: **hypha** — one module, `covenant_highway.py`, that gives every node three organs.

| organ | what it does | how it is not vapour |
|---|---|---|
| **sense** | a fixed set of detectors that MEASURE a condition (source drift, build gap, dead peer, height lag, disk, clock skew, judge unavailable) | each returns numbers it read this second; a detector that cannot measure returns UNKNOWN, never OK |
| **repair** | a fixed set of remedies, each with a class, a bound, and an `undo` | the undo is exercised in the test, not described |
| **share** | signed condition+remedy reports gossiped over the tailnet to peers | reuses the node's existing signer scheme; no new crypto |

## Mutual benefit propagation

A node that repairs something publishes what the condition looked like (a fingerprint:
detector id + measured shape, never file contents, never money, never anything personal)
and whether the remedy **measurably** fixed it — before and after, from the same detector.

A peer that sees that report does three things and no more:

1. runs the same detector **locally**. No peer's word is ever taken for a local fact.
2. if the condition is genuinely present here too, and the remedy is `AUTO_REVERSIBLE`,
   applies it, then measures again.
3. records the outcome and shares that. A remedy that fails to fix twice is **quarantined**
   — the mesh stops recommending it. That is the "bot that learns", and it is one counter,
   not a claim.

Nothing commands anything. A report is an offer. Every node may refuse, and a refusal is
recorded with its reason, because a silent refusal is indistinguishable from a bug.

## Free will, in code rather than in a promise

These are invariants with tests, not paragraphs:

1. **Two classes only.** `AUTO_REVERSIBLE` (restart a node that is down, re-fetch a build,
   re-sync a lagging chain, rotate a log that is eating the disk) and `PROPOSE_ONLY`
   (everything else). Anything that changes a config, installs software, touches money,
   edits a rule, or narrows what a person can do is `PROPOSE_ONLY` by construction — the
   engine refuses to execute that class at all, and the test flips a remedy's class to
   prove the refusal is real.
2. **An operator's explicit choice is untouchable.** A125's lesson cost a full sweep to
   find: a fix of mine silently overrode a scope he had chosen. Choices are registered in
   `ops/OPERATOR_CHOICES.json`; a remedy whose target appears there refuses and says so.
3. **Stateless, or an undo on record.** A remedy that changes persistent state with no
   recorded way back is not a repair, it is a decision taken on someone else's behalf. (The
   first draft of this document said "every remedy carries an undo"; a restart has no undo
   and needs none, because it changes no file and no database. The code says stateless OR
   undoable, and H1c refuses anything else.)
4. **No node may be commanded.** Reports are data. The receiving node re-measures locally
   and decides. Sovereignty per node is what makes a branch a branch and not a puppet.
5. **The phone is asked, never pushed.** Android asks the person holding it to confirm an
   install, and the highway never tries to route around that. Per your instruction:
   nothing reaches the phone until you have read this.

## Phase 1, as built 2026-09-16

- `covenant_highway.py` — five detectors (`node_down`, `source_drift`, `height_lag`,
  `app_build_gap`, `log_bloat`), four remedies, the effectiveness ledger
  (`ops/highway.jsonl`), dry run as the **default**. Measured on this machine the first
  time it ran:

```
SENSE
  app_build_gap    PRESENT  the phone is on 0.1.421+70c6200, 6953f6d is here
  height_lag       ABSENT   {"A": 27, "B": 27, "C": 27}, gap 0
  log_bloat        ABSENT
  node_down        ABSENT   asked A, B, C
  source_drift     ABSENT   disk 3fb031657a8c == A == B == C
REPAIR  (dry run)
  app_build_gap    fetch_build       dry run    would run covenant_app_update.fetch()
  app_build_gap    install_on_phone  proposed   a person decides
```

- `test_h1_highway.py` — 25 checks, the five invariants plus three registry audits, every
  refusal mutation-tested. Registered in `covenant_one.py`; it passes from the staged copy,
  which is where the runner runs it.
- **The refusal is a referral.** Your "when 1 happens, refer to the covenant or meta data in
  it and mutual benefit": a `PROPOSE_ONLY` remedy does not dead-end at "refused". The row
  carries what was measured, the declared mutual benefit **including the cost**, and what
  the covenant's own running seat said when the action was put to it against the principles
  — quoted, named, with HELD reported as held rather than as a No.
- Not yet built: the two node routes (`POST /hwy/report`, `GET /hwy/state`). The engine's
  `report()` and `ingest()` are written and tested; putting them on the wire is the next
  step, and it is the step that first touches another device — so it waits for you.

**Not in phase 1:** the phone, anything that writes money state, anything that edits a rule
file, and any remedy that is not reversible in one step.

## The one thing I want you to decide

Phase 1 remedies are safe by construction, which also makes them small: restart a node that
is down, re-fetch a build, rotate a log. The interesting cases — "the judge is unavailable",
"a seat has drifted", "a node's disposition disagrees with the trunk" — are all
`PROPOSE_ONLY` under the rules above, so the highway will raise them and wait for you.

That is the right default. Say the word if you want any class of them auto-applied, and
name which; I will not widen it on my own judgement.
