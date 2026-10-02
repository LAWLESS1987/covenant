# The mycelial highway

**2026-10-02 correction:** an unavailable post-repair measurement is now
reported as unverified. One remedy exception does not stop unrelated repairs.
See [the unattended-recovery verification record](RECOVERY_CONVERSATION_2026-10-02.md).

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
## Built the same day, on his "just do it"

- **The wire.** `GET /hwy/state` — tailnet-gated like `/m`, returns what this node senses
  and a narrow view of its ledger. `POST /hwy/report` — takes a peer's **signed** offer and
  runs `ingest()` with `dry_run` forced **true**, not as a parameter. An inbound request can
  make this node measure and answer; it cannot make it act. H1d already says a node repairs
  only what it measured itself, and this is the stronger form: "a packet arrived and the
  machine did something" is the hazard that has cost the industry more than any other, and
  the scheduled local pass loses nothing by being the only thing that acts.
- **It runs by itself.** `run_once()` is called by the watchdog every round: sense, repair
  what is reversible, and raise the rest as alerts carrying the covenant's reading and the
  cost beside the gain. Its own restart is excluded there — a remedy that kills its caller
  mid-round is not a repair — so P14 stays the way a stale watchdog is reported.
- **Two more detectors, two more remedies**, both chores that were being done by hand and
  forgotten: `held_core_drift` → `resync_held_core` (P18 V3 went red on thirty-seven commits
  in a row once), and `watchdog_stale` → `restart_watchdog` (P14).
- **The line that does not move.** `NEVER_AUTOMATIC` is matched against what a remedy
  *touches*, not the class it claims: money and the machinery that decides money, the rules
  and the seats that judge by them, keys, and the phone. Flip `install_on_phone` to
  `AUTO_REVERSIBLE` and make it stateless — it still refuses, and H1i proves it by doing
  exactly that. An engine that can quietly widen its own remit is not repairing the system,
  it is replacing the person in it.

`test_h1_highway.py` is now 38 checks.

**Not in phase 1:** the phone, anything that writes money state, anything that edits a rule
file, and any remedy that is not reversible in one step.

## The one thing I want you to decide

Phase 1 remedies are safe by construction, which also makes them small: restart a node that
is down, re-fetch a build, rotate a log. The interesting cases — "the judge is unavailable",
"a seat has drifted", "a node's disposition disagrees with the trunk" — are all
`PROPOSE_ONLY` under the rules above, so the highway will raise them and wait for you.

That is the right default. Say the word if you want any class of them auto-applied, and
name which; I will not widen it on my own judgement.

## What the first live hour taught it

The watchdog started running the pass every ~66 seconds at 06:44. Inside the hour it
fetched a build by itself — and then produced three faults of mine, which is the point of
running a thing rather than describing it.

1. **A remedy graded against a condition it cannot clear.** `fetch_build` was paired with
   `app_build_gap` ("the phone is behind"), which fetching does not fix, so two correct runs
   were recorded "did not fix" and the remedy **quarantined itself**. The counter was right;
   the pairing was wrong. `fetch_build` now answers `build_stale_on_pc`, and a quarantine is
   cleared only by `recalibrate()`, which writes *why* into the ledger and leaves the
   failures above it. Never by deleting history.
2. **An asynchronous remedy cannot be graded a second after it starts.** A CI build takes
   ten minutes. Remedies marked `async` record `started`, and `quarantined()` does not count
   that as a failure — a later pass measures the condition and tells the truth.

   **Corrected 2026-09-27, on his instruction "get … self healing right". The second half of
   that sentence was not true for six weeks.** Nothing implemented the later pass. Measured
   from `ops/highway.jsonl` that morning, unit LEDGER ROWS: `dispatch_phone_build` 11 started
   / 0 graded, `fetch_build` 177 / 8, `schedule_watchdog_restart` 64 / 0 — **252 starts with
   no outcome**, while `--standing` printed UNPROVEN beside each and explained, accurately,
   that "nothing checks what they started". It cost five days of phone builds: dispatches were
   told "accepted (HTTP 204)", every build failed on a full artifact store, and the highway
   went on dispatching into it with a remedy that looked busy.

   `grade_started()` now keeps it. It waits out each remedy's own declared window
   (`grade_after_s` — 30 min for a build dispatch, 15 for a scheduled restart, an hour for a
   fetch) and only then measures: PRESENT then and ABSENT now is `fixed`, still PRESENT is
   `did not fix`. UNKNOWN now is left ungraded, because a read that failed is not a verdict
   and calling it one would quarantine a remedy for the reader's blindness. Rows before a
   `recalibrated` row are never graded, or a re-grade would silently put back the failures the
   recalibration set aside. The original caution is kept rather than discarded: a start inside
   its window is still not touched.

   **What it found in its first pass, which is the argument for it.** 36 rows graded.
   `schedule_watchdog_restart` went from UNPROVEN to **EARNED, 16 fixed / 0 missed** — it had
   been working all along and nothing had ever said so. And two bugs surfaced that only
   grading could expose: the async branch **ignored `ran=False`**, so a remedy that declined
   was filed as `started` (the synchronous branch had honoured it since 2026-09-19); and
   `remedy_fetch_build` returned true whenever *any* build was on disk (`or bool(after)`), so
   "already have build 2ab1ba5" reported as a remedy that had acted. Together those turned 16
   correct declines into 16 failures and quarantined it. Both fixed: a decline is now `held`
   with its reason, and fetch reports true only when a different build actually arrived.
   `fetch_build` and `dispatch_phone_build` were then recalibrated — the reasons are in the
   ledger and the failures stay above them.

   Fault 1 above is also why `standing()` changed: `quarantined()` has always honoured
   `recalibrated`, and `standing()` did not, so the same record produced two verdicts and the
   harsher one was printed. `rehash_bundle` read **FAILING** off two rows its own
   recalibration had set aside; it now reads UNPROVEN, which is the honest answer.

   Driven both ways in `test_h1_highway.py` as **H1o2**, twelve checks: graded past the window
   in each direction, *not* graded inside it (and graded once the window is shrunk, so the
   check is the window and not the fixture), UNKNOWN left alone, the recalibration barrier
   honoured in both directions, `dry_run` writing nothing and then writing one, and a
   declining async remedy recorded `held` where the same remedy returning ok records `started`.
3. **A guard that measured itself.** The first `watchdog_stale` imported the watchdog and
   compared *that* to disk; a fresh import always matches, so it would have said ABSENT every
   time, including twice today when the running watchdog really was stale. It now asks the
   only question answerable from outside — was the file written after the process started —
   and immediately reported PRESENT by 1702 seconds.

It was also writing an identical proposal row every 66 seconds, re-loading the judge each
time to re-ask a question whose answer had not changed. There is now an hourly cooldown,
bypassed by `--repair` typed by a person, because the suppressor is for the scheduled pass.

## The delivery gap it closed

`covenant-phone` builds on a push to **itself**, and the APK it produces is a checkout of
the **public core at main**. So every core change left the app build behind and nothing ever
rebuilt: today's work would have sat here while the phone auto-updated faithfully to a build
made before it. `phone_build_behind_core` measures that (main's last commit against the
build's timestamp) and `dispatch_phone_build` asks the runner for one — the credential on
this PC carries `workflow` scope. It touches a build server, not a device: no install, no
money, and Android still asks the person holding the phone. First live dispatch: HTTP 204,
133 minutes behind.

`test_h1_highway.py` is 47 checks.
