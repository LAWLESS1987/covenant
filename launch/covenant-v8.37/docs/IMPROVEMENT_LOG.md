# Recursive self-improvement loop — whole system, from 2026-08-21

Each scheduled run reads this, picks the highest-value unblocked item, does it,
and appends what happened. Fresh session each time — this file is the only
memory.

**This loop improves itself as well as the system.** Sections marked MUTABLE are
meant to be edited by runs. Section 0 is IMMUTABLE and may never be edited,
weakened, reinterpreted, or moved — by any run, for any reason, including a
reason that seems excellent at the time.

> ⚠ **ACTIVE ISSUE — A12 has TWO v8.23 sources; the project source does NOT
> match this log's A12 entry. Read before touching A12 or the send path.**
> The 00:15 run's A12 entry describes a `PeerHealth` v8.23 (sha256 `c5447e79…`,
> 8483 lines) as shipped — but that source **never reached the project** (the
> project held v8.22 `8b304a2f` at the start of the next run) and is not
> retrievable here; only L's SendUserFile download from ~00:15 has it. A second,
> **concurrent** run (00:15→00:40, its entry is the last in the log) read a
> STALE snapshot of this log that pre-dated the A12 entry, re-did A12
> independently as a simpler `_delivery_order` + heartbeat-backoff v8.23
> (sha256 `2d3e9da6…`, 8382 lines), verified it, and **that** is what the
> project source currently holds. So: grepping the project source for
> `PeerHealth` finds nothing and `_delivery_order` instead — that is EXPECTED,
> not the M6 regression it looks like. The `PeerHealth` design is the more
> thorough of the two (it caught head-of-line blocking as the primary hazard
> and found A13/A14). **For L to decide:** consolidate on `PeerHealth`
> (`c5447e79`, in your ~00:15 download) — recommended — or keep `2d3e9da6`.
> Until L consolidates, do not re-do A12 a third time; it is closed twice over.

> **STALL WATCH (rule 6): 0 consecutive runs with no close.** Last close:
> **DEPLOYMENT's disk half, onto v8.37** (2026-08-26 ~19:30, attended) — the
> first delivery to reach this machine since 08-24. Two runs of send-path work
> (A23/v8.36, A3-send/v8.37) AND the whole propagation package had stayed in
> the project; disk was v8.35 `1207bd2e7dc5` and both nodes were running it.
> Seven files copied over the bridge, sha256-verified on the target. **The
> package built to make delivery verifiable had two defects that would each
> have broken its own first run** — an LF-only `.bat` built entirely of `goto`
> labels, and a `subprocess.run` that would have reported a working restart as
> a failure — plus a third that is a real hazard (**P17**: the restart can take
> the chain down and leave it down). **running: still v8.35.** → **M44**.
> Before that:
> **A3's send-side follow-on** (2026-08-26 ~09:15) — the backlog called it
> "small: outbound, and self-limited by what this node builds". Measured, both
> halves were wrong. A `TX_ANNOUNCE`'s `tx_id` is chosen by the SENDER and
> echoed verbatim into the `TX_REQUEST` we build: a 204,893-byte announcement
> made the node build and transmit a **204,872-byte request**, ~3,200× the
> honest 64-char sha256 id, on a fetch-pool worker gap-fill needs. And an
> over-cap frame was transmitted 3× (897 KB) to a peer that must refuse it —
> whereupon **A23's own new rule read the missing reply as non-delivery and
> escalated the backoff against that innocent peer** (k=1). That edge was one
> run old: it is what M33 says to look for. v8.37 `07e097f3e37f`;
> `claude/test_a3s_send_bounds.py` **49/49 ×2**, PRE-FIX RECORD **23/49** on
> pristine v8.36; full sweep **31 suites / 1,043 checks / 0 failures** (Linux
> — M29 applies, it has NOT run on win32). → **M42**, **M43**.
> Before that:
> **A23** (2026-08-26 ~01:30) — `_note_send_ok` fired the instant `sendall()`
> returned, which is the exact claim A18 exists to deny, and it CLEARS the
> link's consecutive-failure count. So a peer that accepts bytes and never
> answers stayed at k=1 and one interval of backoff for ever, while a REFUSED
> peer reached k=5 and 16×: the peer delivering nothing was accounted healthier
> than the one that says so. Also, a NON-JSON reply returned None in silence.
> v8.36 `dd613fc534e0`; `claude/test_a23_ack_health.py` **24/24 ×2**, PRE-FIX
> RECORD **16/24** on pristine v8.35; full sweep **31 suites / 994 checks / 0
> failures** (Linux — M29 applies, it has NOT run on win32). → **M41**.
> Before that:
> **SEM1** (2026-08-24 ~23:15) — the day's three semantic result files had no
> source, no corpus and no space id, so the cross-register claim was rebuilt
> from scratch and measured against the nulls it never had. A spelling-only
> scorer beats the space 7×; the space survives anyway, on the half of the
> data where spelling scores exactly zero. `claude/SEMANTIC_NULLS.md`,
> `claude_CROSS_REGISTER_EVAL_v2.txt`, source in `claude/semantic/`. → **M40**.
> Before it:
> **P14 + the delivery half of DEPLOYMENT** (2026-08-24 ~07:45), the
> **restart onto v8.35 at 08:10:09**, **P16**, **P7**, and the first Windows
> sweep this project has ever run (**961/964 in 12.2 min**, three reds, two
> root causes: **P9** and **A23**). Narrative moved to
> `claude/RUN_LOG_ARCHIVE.md` — M36; the record is §4 and §5.
>
> This banner used to carry nine runs of narrative. That prose is moved
> **verbatim** to `claude/LOOP_HEADER_ARCHIVE.md` — nothing lost — because §4
> holds per-item detail and §5 holds per-run detail, and the banner's job is
> the one number above. It cost every run ~60 lines of reading to say what was
> already recorded twice. → **M36**, and see the OPEN-ITEMS INDEX at the head
> of §4: a run can now pick an item from ~30 lines instead of ~890.
>
> Still L's, unchanged: **A10** (which genesis state is canonical),
> **A16** (Option A recommended), **B4** (is the ethics verdict a consensus
> rule or an admission policy), the **A12 consolidation**, A12's residual,
> **A7/A8**, **P2**, **P3**, **P9**. Still hardware: **C3/C4** (the phone),
> and C5's next move (try the APK, answer README §7).
> **CORRECTED 2026-08-24 07:45 — this said "five versions deep; the nodes are
> on v8.30".** Measured on the machine: the **disk** was on **v8.34**
> (`773cb7d7adef`, mtime 08-23 07:39 — an unlogged delivery), one version
> behind, not five; and the **running** processes are older than either — their
> boot banner still reads `Covenant Unified v7.0`, the string **P11 replaced in
> v8.31**. The disk now holds v8.35, hash-verified on the target. The running
> processes have not changed: **the restart is still open**, and it is one
> double-click — `Downloads\RESTART_COVENANT_ON_v8.35.bat`. Project, disk and
> running process are three separate claims and drift independently → **M38**.
>
> **VERSION STATE at 2026-08-26 19:30 (M38 — three claims, not one). All three
> MEASURED on the machine this time, not inferred.**
> **project: v8.37 `07e097f3e37f`.** **disk: v8.37 `07e097f3e37f`, 9846 lines**
> — delivered over the bridge and `sha256sum -c` verified ON the target at
> 19:20; v8.35 kept beside it as `covenant_unified_v8.PRE-v8.37.py`
> (`1207bd2e7dc5`). **running: v8.35 `1207bd2e7dc5`, BOTH nodes** — the
> restart has not happened. Read off the watchdog's own P11 line rather than
> forensics: `node A v=v8.35 src=1207bd2e7dc5 height=3 peers=1 ...
> [unchanged, 2310 rounds]` at 18:47:56Z, node B the same at 18:44:52Z.
> **A FOURTH claim, and it has been alerting correctly for two days while
> nobody read it:** the watchdog PROCESS is running `c228ac0a629d` against
> `d363d6c2bb5f` on disk and says so once per roll-up — *"THE WATCHDOG ITSELF
> IS STALE ... the checks in the deployed file are NOT the checks running."*
> P14 works. The restart clears it, because `AB_RESTART_NODES.bat` kills the
> watchdog window too and `covenant_prod.bat` starts a fresh one.
> **The remaining gap is one double-click** on
> `covenant\AM_VERIFY_AND_RESTART.bat`, which now verifies before it acts.
>
> **Three docs in the project are NEWER than this log and are not recorded in
> it** (M16): `claude_phil_CORPUS_MANIFEST.json` (2026-08-25 09:00),
> `claude_phil_align_ceiling.py` (2026-08-25 09:36) and **`fetch46.py`
> (2026-08-26 07:38 — 37 minutes before this run booted)**. All three are
> semantic/SEM-family: `fetch46.py` fetches the Gutenberg ids named in
> `claude_phil_CORPUS_MANIFEST.json` into `/home/claude/jlens/books/`. The
> newest may be an IN-FLIGHT run rather than a torn commit (M23), so this run
> deliberately picked a Section-A item to stay clear of it, and re-read this
> log at write-back: `created_at` was unchanged at 02:02:14Z, so no concurrent
> run has written here. A future run should read their headers and log them on
> that run's behalf rather than repeating the work (M16/M23).
>
> ⚠ **READ `claude/PC_SYNC_LOOP.md` BEFORE SHIPPING ANYTHING.** From 08-21
> 05:35 to 08-22 12:30 every run ended "L: copy this into
> `C:\Users\Lawre\covenant`", and for fourteen node versions nobody did.
> The machine running the node was on a pre-v8.15 source: no
> `preflight_port_check`, no `_gossip_tip`, no `MAX_EXCHANGE_S`, none of it.
> **`project_write` is not delivery.** In an attended, L-started session,
> hash-compare the deployed source against the project's BEFORE choosing an
> item — drift outranks the backlog.

---

# 0. IMMUTABLE — no run may ever edit or relax this section

A self-improving loop that can edit its own constraints has no constraints. So
these do not move, and a run that finds itself reasoning toward an exception
should stop and write the reasoning into the log for a human instead.

- **No trades.** All ten positions are locked in `TRADING_POLICY.json`; the sleeve is L's to place by hand. Never place, prepare, or simulate a real order.
- **No credentials.** Never request, store, read, or use an API secret, exchange
  key, or the Ledger recovery phrase.
- **No claims of profit edge.** No timing edge survived out-of-sample (XRP
  −2.70% p=0.656; HBAR −7.06% p=0.891). Rebalancing: +0.45% mean OOS at
  **p=0.109, not significant.**
- **Never weaken a security control to make a test pass.** If the ethics gate, a
  guard, or a bound blocks something, that is usually correct. Fix the test.
- **Never widen the loop's own scope or permissions.** It may improve its
  methods and priorities. It may not grant itself new capabilities.
- **Report honestly, especially against yourself.** If a run finds an earlier
  conclusion wrong — including one from a previous run of this loop — say so
  plainly and correct it.

---

# 1. MUTABLE — how the loop improves itself

**Every run must do this, before finishing:**

1. **Record cost.** Which item, roughly how much effort, what was produced.
2. **Record dead ends.** Anything tried that did not work, so no future run
   repeats it. Dead ends are as valuable as successes and are cheaper to write.
3. **Re-prioritise.** If a finding changed what matters, reorder the backlog and
   say why. Priorities are a hypothesis, not a schedule.
4. **Improve a method.** If something was learned about *how* to work here —
   a verification trick, a trap, a faster path — add it to §2 Methods.
5. **Improve the loop.** If these instructions were unclear, wrong, or missing
   something, fix them. The trigger prompt itself can be updated via
   `update_trigger` on `trig_01JuqmnfpaxphVvShDch2GJa`.
6. **Notice stalling.** If three consecutive runs produce no completed item,
   say so at the top of the log and propose what would unblock it. Churning
   quietly is the failure mode to avoid.

## Self-assessment, updated each run

- runs completed: 35 (the 00:47 run left no log entry — see the 01:40 entry; the 07:15 run's entry was overwritten by the 08:00 write-back and restored at ~08:20)
- backlog items closed: 49 + DEPLOYMENT (delivery AND restart) (this header line had drifted — it read 34 while the list below already held 41 items and the last run-log entry said 41; corrected here rather than left to drift further) (P1, P4, P5, P6, A1a, A2, A3, A5, A4, A9, A1, A6, A11, B1, B3, A12, B5, A13, A14, A15, D1-XLM, D1-SOL, D1-XRP, D1-HBAR, D2-regime, A17, D1-ADA, D1-complete [ATOM/AVAX/NEAR/CRO/ONDO/PEPE/WLFI], D2-regime-all-assets, D2-rebalance, **D3**, **D4**, **C1**, **W1**, **P11**, **P12**, **A20**, **A21**, **A22**, **P8**, **P10**, **C5**, **B2**, **P14**, **P16**, **P7**, **WINDOWS-SWEEP**, **SEM1**, **A23**, **A3-send**)
  — run 11 closed NO NEW item: it duplicated A12 off a stale log read (see the
  ACTIVE ISSUE banner and the 00:40 run-log entry). Not counted as a close.
- methods learned: 44 (this header read 42 while M43 was already the newest
  label — off by one; corrected here rather than left to drift, as the
  closed-items counter was on 08-22. M44 is this run's.)
- earlier conclusions corrected: 44 (
  **THE PREVIOUS RUN'S OWN CLOSING SENTENCE, and it is the reason this one had
  work to do. The 11:05 addendum shipped `verify_deploy.py` +
  `AM_VERIFY_AND_RESTART.bat` and ended "Nothing else is needed; if the copy is
  wrong it will say so and refuse to restart." Measured on the machine: the
  launcher shipped LF-only into a folder where every other `.bat` is CRLF, and
  the verifier's restart step would have hung on `AB_RESTART_NODES.bat`'s
  `pause` and then reported a working restart as `restart launcher failed`. A
  package written to make delivery verifiable, never once run on the platform
  it was written for** — → **M44**, **P17**;
  **P13's "the interop measurement cannot be re-verified anywhere" is FALSE on
  the machine that matters. `test_a20_peer_version.py` already lists
  `covenant_unified_v8.PRE-v8.33.py` in `_OLD_CANDIDATES`, and that file is ON
  the PC: `COVENANT_VERSION=v8.32`, zero `A20` markers — a genuine,
  un-fabricated pre-A20 binary. C1-C5 have been runnable there all along; what
  P13 describes is a FRESH-SANDBOX gap, not a global one** — → P13;
  **A COMMENT I WROTE THIS RUN, wrong at the moment it was written. The v8.37
  guard on `BLOCK_ANNOUNCE`'s `index` was introduced with a comment saying the
  index "is echoed onward as the from_index of the BLOCK_REQUEST this node
  builds" — i.e. a second amplifier beside the tx_id. The check written to
  prove it (S5f) disproved it: `_fetch_announced` asks from
  `len(self.node.chain)`, our OWN height, and the peer's number never leaves
  the process. The guard is still worth having and is now labelled honestly as
  input-shape hygiene, not a send-side bound. The general lesson is that a
  data-flow claim in a comment can be wrong AT BIRTH, not only stale** — →
  **M42**;
  **the A3 follow-on's own backlog wording — "those are outbound and
  self-limited by what this node builds" — was false in both halves, and it
  had sat unexamined for five days precisely because it sounded like a reason
  not to look** — → A3-send;
  
  **A23's own filed entry named the wrong culprit. It said the exhaustion path
  was "not being reached" and guessed at `return verdict` / `return None`
  taking the exit first. Measured in-process against a listener that accepts
  and never answers: the A18 path IS reached, records `peer_send_failure` and
  arms a backoff — on the FIRST send. What was broken is that
  `_note_send_ok(host, port)` ran three lines earlier, on `sendall()` alone,
  clearing the counter every attempt, so the link never escalated past k=1. The
  entry was right that something was wrong and wrong about what** — → A23/M41;
  **P7's standing hypothesis — "A12's dead-peer backoff marked the peer suspect
  and the broadcast skipped it, so the node is correct and only the RECORD is
  missing" — is FALSE. Measured on Windows 2026-08-24: `dead_peers=0`,
  `heartbeats_skipped=0` in both K1 and K3, before and after. Both
  `peer_send_failure` sites call `_note_send_failed` immediately before
  recording, so a zero counter proves neither ran; and the only kind present,
  `peer_message_error`, is the INBOUND parse channel. A18 (v8.30), written from
  the correct diagnosis of exactly this Windows behaviour, has never fired on
  Windows** — → A23;
  **THIS RUN'S OWN ADDENDUM 1 said node A's surviving `-shm` looked like a
  python.exe that had outlived its console window (P3), and named `netstat` as
  the cheap test. The restart ran it: /health empty, netstat empty, taskkill
  "No tasks running with the specified criteria" x3. NOTHING was orphaned — an
  orphaned `-shm` also survives a hard kill, which is what it was** — see
  ADDENDUM 2;
  **THIS RUN'S OWN P16 banner said the log guarantees "one line every 30 rounds
  (~30 min)". True and far too loose: the balance check logs every round when
  both databases are present, so the real bound is 60 seconds — publishing the
  weak floor would have taught a reader to tolerate a watchdog dead for
  twenty-nine minutes, which is the failure P16 exists to prevent** — corrected
  within the hour, see ADDENDUM 2;
  **this file's own banner said "the nodes are on v8.30, the project holds
  v8.35, the restart is five versions deep". Measured on the machine: the disk
  held v8.34 (`773cb7d7adef`, an unlogged 08-23 07:39 delivery) — one version
  behind, not five — and the running processes are older than either, still
  printing the pre-v8.31 `Covenant Unified v7.0` banner. Two of the three
  numbers were wrong in opposite directions and the third had never been
  measured** — corrected 2026-08-24, → M38;
  **`covenant_watchdog.py`'s `source_drift_report`, written 08-23 07:39 to
  catch "the file was updated and the node was never restarted", had never
  executed once: the watchdog process running at the time started 08-23 01:39,
  six hours earlier, and was still running 29 hours later with neither it nor
  `Adaptation` — so the control against staleness was itself stale, while
  writing 3,448 redundant ALERT lines out of 3,456** — fixed by P14;
  **`QUORUM_DIVERSITY`'s honesty note said it "checks label diversity, not
  reasoning diversity" — true, and too kind. Measured: because
  `build_semantic_quorum` always appends `mock_selfreport:0` as its own bucket,
  the check passed for EVERY configuration the builder can produce, including a
  single provider and the same provider twice. It had never once constrained a
  running node, and one of the two buckets it counted was the SENDER'S
  self-report** — fixed v8.35, B2;
  **`/health`'s `judge_keyless` means "no key for ANY provider", so a node with
  one key of two reported a healthy judge while its keyless judge's fail-closed
  vote rejected 100 % of transactions — the exact failure the /health block's
  own docstring says it exists to make visible** — B2; the field's formula and
  `degraded` are deliberately UNCHANGED (a suite pins `degraded`'s definition);
  the new `quorum` block and its warning carry the truth instead;
  **`test_a20_peer_version` asserted that a FIXTURE FILE exists as if it were a
  system property, and when it was absent `interop_checks()` returned early —
  so D1–D6, the checks on what actually leaves the process, did not run at all.
  Two red lines were hiding six absent ones** — P13;
  
  **`claude/ANDROID_VPN_SYNC.md` §3's phone runbook puts the phone on Tailscale
  for the whole of C3, and this run's Android work needs a VpnService on the
  same phone. Android permits exactly ONE app to hold the VPN interface: no
  chaining, no stacking, no API to share it — starting either tears the other
  down and the loser gets `onRevoke()`. So the phone cannot be a covenant node
  over Tailscale AND run an on-device filter. Neither document said so, and both
  plans were written for the same handset** — see C5 and the ~08:30 entry;
  **P10 as I wrote it in this file said the audit should "SKIP its three sandbox
  checks with a reason" on a platform where the sandbox is unavailable. That was
  wrong: a skip means the check stops checking on the platform that actually
  runs production. Asserting what CORRECT behaviour is there instead turned three
  phantom failures into four real assertions and pinned P4's one-way property —
  "nothing turns the sandbox ON where its limits cannot be enforced" — which was
  untested anywhere until now** — see the 07:45 entry and M34;
  **the `POST /peers` route carried the comment "Still NOT authenticated --
  anyone can register a peer", describing a state the v8.9 operator-auth work had
  already fixed: it IS in `PROTECTED_OPERATOR_ENDPOINTS` and the before_request
  hook fails closed on missing headers, unknown key, bad signature, stale
  timestamp and replayed nonce. A comment that denies a live control is worse
  than no comment — it invites the next reader to reason "peers are
  unauthenticated anyway, so this other thing doesn't matter"** — corrected
  v8.34, and the control is now asserted by `test_a22` P1 so it cannot regress
  quietly;
  **two defects in this loop's OWN A20/A21 code, found ninety minutes after
  shipping it: the peer table REFUSED newcomers when full (so anything reaching
  the node from enough sources could fill it and permanently suppress the A7
  split-source warning — an attacker switching a signal OFF), and
  `peer_version_mismatch` was recorded on EVERY observation rather than on
  change, i.e. a permanent condition transmitted at full rate inside a bounded
  anomaly buffer — the exact failure fixed one layer up the same night**
  — fixed v8.34, → M33;
  **the node was blind to the machine under it — a grep for
  `psutil|meminfo|GlobalMemoryStatus|loadavg|virtual_memory` over 8,933 lines
  returned nothing — while the ethics judge sits INSIDE consensus and is a
  5.2 GB model; the production nodes were restarted on 08-23 with 3.1 GB free,
  so the judge was loading by paging, and `AH_FITCHECK.bat` had measured exactly
  that and written it to a text file nothing reads** — fixed v8.32, P12;
  **the node could not say what it was running, and nobody had noticed the
  banner in sixteen runs of reading node logs: `covenant_unified_v8.py` printed
  "Covenant Unified v7.0 running" on a v8.30 file, `COVENANT_VERSION` was
  `"v8.9-merged"` and read by nothing, and `/health` had no version field — so
  M25's "grep the DEPLOYED file" had no counterpart for the RUNNING process**
  — fixed v8.31, P11, see `claude/RUNNING_VS_DEPLOYED.md`;
  **`LEAN_MEASURE.txt`'s two summary lines (17.4 s vs 12.8 s per verdict) read
  as "num_predict=96 is 36% slower than 160"; strip the single cold model load
  and the two settings are 12.88 s and 12.77 s — indistinguishable. The
  `covenant_prod.bat` keepalive comment shows the cold load WAS understood by
  whoever measured it; the report's summary line does not, and the report is
  what a future run reads** — see the 03:10 entry;
  **the code sandbox was dead in two different ways on two platforms and
  `/propose_code` could not accept anything anywhere: `get_context("fork")`
  raised past every handler into a bare 500 on Windows, and on Linux the child
  set RLIMIT_NPROC=0 and then reported through a Queue, whose put() needs a
  thread — so it died silently** — both fixed, P4;
  **A2's preflight could not detect a port collision on Windows at all: its probe
  binds with SO_REUSEADDR, which there lets a second process bind a port another
  is actively listening on — the control passed on the platform where the footgun
  is worst** — fixed, P5;
  **the 18:45 entry said six suites "cannot run on Windows at all"; three of them
  ran every check and passed, and only their `shutil.rmtree` teardown crashed —
  I read a missing summary line as a missing run** — corrected below;
  **the suites were never delivered to the PC: `run_all_tests.sh` shipped there
  on 08-22 12:30 calls 34 suites and the machine held 15 — every A/B-series test
  from v8.15 to v8.29 was missing, so the sweep could not run where the node runs**
  — see the 18:45 entry and `claude/LOCAL_INTEGRATION.md`;
  **`covenant_prod.bat stop` does not stop a node — it kills the cmd wrapper by
  window title, `python.exe` keeps the port, and the next start says "node A
  already up" and does nothing; so 12:30's "restart the node to pick up v8.29"
  could not have worked as written** — observed live 14:12, see P3;
  **W1's waitress path had never run on L's machine: waitress was in
  `requirements.txt` and not in `.venv`, so v8.29 shipped the bounded pool inert
  and `test_w1_wsgi` could not exercise it there** — fixed, see P1;
  **`DAILY_CHECK_CLOUD_BLOCKER.md`'s "403 Forbidden at the tunnel" for Coinbase
  and Kraken is FALSE — all four endpoints answer plain `urllib` with HTTP 200;
  what failed was WebFetch's permission gate, and the superseded measurement
  cost two mornings of no data** — see the 14:20 entry;
  **DAILY_CHECK.md section 2's "lines are good for 14 days" measured the drift of the
  LINE (0.3–0.8%/week, correct) and concluded something about the STATE, which
  flipped on five of nine symbols in three days** — see the 14:20 entry;
  **"shipped" meant "written to the project" for sixteen runs — the PC ran a
  pre-v8.15 source the whole time (7774 lines, `54955648…`, mtime 08-20 23:33)
  while the log recorded fourteen versions as delivered; M6's own grep rule was
  applied to the project's source twenty times and never to the deployed one**
  — see M25 and `claude/PC_SYNC_LOOP.md`;
  **M5's "scheduled cloud runs have no device bridge" was read as "the loop can
  never reach the PC"; the true rule is that the bridge exists when L STARTS the
  session, and no run had tested it** — see M25;
  **every D1 run from 01:35 to 07:45 assumed Kraken was reachable only through the WebFetch summariser (M1's row-loss hazard, 5–8 windows and ~50k context tokens per symbol); `api.kraken.com` answers plain `urllib` from this sandbox, one call per 720 bars, byte-exact — ADA rebuilt this way hashes to the logged `a0ae69f1…`** — see M24;
  **D1's own wording said "WLFI/ONDO/PEPE may not be on Kraken" — all three are (ONDO/PEPE from 2024-09-01, WLFI from 2025-09-01)** — see the 08:45 entry;
  **the 08:00 run's write-back overwrote the 07:15 run's entry, DE5, M21 and counters — a stale-copy paste, restored ~08:20** — see the banner;
  **A1/K5's "a node at genesis gossips nothing — nothing worth saying" became
  false the moment A13 made the reply useful: a one-way-peered node never
  synced at all** — see A17; **the "~3× drawdown reduction replicated"
  claim does not hold on XLM at 598 bars (0.9×; 2.1× SOL, 1.8× XRP)** —
  see D2;
  **the 05:30 entry's "D outranks nothing while A/B/C are merely blocked on L"
  contradicted the trigger prompt's own rule (A outranks D *unless A is
  blocked* — it is) — D1 was unblocked all along** — see the 06:20 entry;
  **A15's own wording said every reader had a per-recv socket timeout —
  the two INBOUND handlers had none at all; a silent open connection
  (no trickle needed) pinned a receive worker for ever, unrecorded** —
  see the 05:30 entry;
  **the A3/A5 bounded-read work bounded BYTES, not time — a peer that trickles
  one byte per 0.2 s held `bootstrap_chain` (and `/sync`) forever on v8.25;
  recorded as `bootstrap_probe_timeout` and abandoned since v8.26, but the
  same gap still pins a worker on every other reader** — see A15;
  
  **the 13:00 run's B3 claim that a fail-closed infrastructure reject is
  "recorded as judge_unavailable" held only on the two transaction ingest
  paths — the /mine and peer-block paths recorded nothing (/mine: nothing at
  all, a bare 400)** — fixed v8.24, see the 01:40 entry;
  **the 00:15 run's claim that its PeerHealth v8.23 (`c5447e79`) shipped to the
  project was false — the project still held v8.22 `8b304a2f` at the next run's
  start; the source save did not persist** — see the ACTIVE ISSUE banner;
  the "no edge" claims were under-powered;
  **the A3 bounded-read fix was recorded as done but was never in the source**;
  **the A3 cap called itself "generous" and was 7x too small for the file's own
  worst-case catch-up** — see A5; **the source's own "harmless because the
  drift check catches an empty block" note was wrong once the attacker sets
  alignment_score by hand** — see A4; **A1 was never blocked in the
  shared-genesis deployment path — DE1 only describes a self-minted node**,
  and the two genesis paths produce different ledger/stake state — see A10;
  **A6 was worded as if `sim1000_network.py` exercised sockets and shape
  checks — it exercises neither**, see the 11:45 run; **B1's "two found
  and fixed" parser fixes were NOT in the node's judge parser** — see the
  13:00 run; **the suite run-time figures the runner and three run-log
  entries quoted (a1 ~8 min, a4 ~4 min, multinode ~10 min) are 5–10× too
  high in this sandbox — 45 s, 55 s, 79 s measured twice — and the 13:00 run
  skipped the kill matrix on the strength of the wrong figure**, see the
  23:30 run)
- dead ends recorded: 7 (DE1 narrowed; DE2 NARROWED — see M25; **DE6** — `device_bash` is a third local and cannot run the suites; **DE7** — computer-use at click tier cannot launch a program)

---

# 2. MUTABLE — Methods learned here

### M1. Never trust a row count. Only contiguity.
Long WebFetch responses silently drop rows — a 70-day-stale series once came
back looking perfect. Bounding the request does **not** fix it: asking for 110
rows returned 105. Reported totals lie too; one response claimed `TOTAL=1787`
for a series that cannot exceed ~720.
**Verify every window:** exactly 86400s spacing, no duplicates, no non-positive
prices, adjacent windows joining seamlessly. The 105-row window was *usable*
precisely because contiguity was checked. Kraken OHLC takes `since` only.

### M2. The node test environment has three traps, all silent.
- Needs **both** `COVENANT_INSECURE_MOCK_JUDGE=1` **and**
  `COVENANT_JUDGE_PROVIDERS=mock`. The flag alone rejects every transaction.
- `--port N` occupies **N, N+1, N+11**. Nodes closer than 12 apart collide, and
  the victim prints `Address already in use` *after* a healthy-looking banner.
- `--peers` takes each peer's **P2P port (API + 1)**, while `--port` takes the
  API port. Get it wrong and peer JSON hits Flask, which answers 400 while the
  sender sees nothing. Nodes look peered and are not.
**Since v8.15 the last two are caught at startup** by `preflight_port_check`
(fails before the banner, with the arithmetic in the message).
`COVENANT_SKIP_PREFLIGHT=1` bypasses it — bypassing re-arms both footguns.

### M3. Stake action signatures are RSA-PSS, not EC.
`verify_stake_action_signature` uses
`padding.PSS(mgf=MGF1(SHA256), salt_length=MAX_LENGTH)` with SHA256 over
`_domain_frame(b"COVENANT_STAKE_ACTION_V1", pubkey_pem, action, str(timestamp))`.
Signing with EC fails with a confusing `missing 1 required positional argument`.

### M4. Detecting "this port is Flask, not P2P": don't look for `HTTP/`.
Measured 2026-08-21: send an unparseable request line (e.g. `{}`) to werkzeug
and it falls back to **HTTP/0.9**, which sends the HTML error body with **no
status line** — the response starts `<!DOCTYPE HTML>`, not `HTTP/`. The robust
discriminator: a real P2P listener answers JSON or nothing; anything non-empty
that isn't JSON is an HTTP server. This is what `preflight_port_check` uses.

### M5. Sandbox process + delivery facts for scheduled cloud runs.
- Background processes do **not** survive between Bash tool calls here. Any
  harness that starts nodes must start, test, and kill them inside ONE script
  invocation (see `test_a1a_a2.py` for the working pattern).
- Scheduled cloud runs have **no device bridge** — `device_commit_files` to
  `C:\Users\Lawre\covenant` is impossible, every time, by design. Deliver via
  SendUserFile + `project_write`, and say in the summary that L must copy the
  files into the local repo (or re-run the tests locally).
- `covenant_unified_v8.py` imports `covenant_path_pattern` — copy both out of
  the project or the node won't start.

### M6. Trust the code, not the backlog's claim that the code was changed.
This run found A3 listed as **done** ("three fixed via `recv_bounded` +
`MAX_PEER_MSG_BYTES`") while `grep` showed **zero** occurrences of either symbol
and all five read sites still unbounded. A prior entry described work that never
landed. **Before building on any "DONE" item, grep the source for the symbol it
names.** A one-line `grep -c` is cheaper than trusting prose, and the whole point
of this file is that prose is the only memory — so prose can be wrong. The two
existing suites also had never actually been run against v8.15 (last run said so
in its residual-risk note); running them found the `except: pass` regression M4's
work had introduced. **Run the existing suites against the file you are shipping,
every time — a claim of "unlikely to break" is not verification.**

### M7. A bound is only safe once it is measured against the honest maximum.
The A3 read cap was described as "generous, not snug" and nobody multiplied
the file's own constants: 1,466-byte bare transaction × 5000 per block × 64
blocks per catch-up page = **448 MiB against a 64 MiB cap**. A cap on the reader
with no cap on what an honest writer may produce is a liveness bug with an
attack attached (one stuffed block exiles every late joiner for good).
**Whenever a ceiling is added, write the one-line product of the constants
that feed it into the test, with the real serializer, and assert the relation
at import** (`MAX_TX < MAX_BLOCK <= PAGE < READ CAP`) so an env override cannot
silently break it. `serialized_size()` is now the single measure.

### M8. Moving big files between the project and disk (cloud sandbox).
- `project_write(local_path=...)` only accepts a path **inside the working
  directory** (`/home/claude/...`); `/tmp` is refused. Build in `/home/claude`.
- `project_read` returns most files **inline**, which burns context if you
  then retype them. Cheaper: spawn a general-purpose subagent with the list of
  paths and have it `json.load` the raw response and write each file verbatim
  (~110k subagent tokens for six files, zero main-context cost, byte-exact).
- `covenant_unified_v8.py` imports `covenant_trading_bridge.py` lazily via the
  API; `test_security_audit.py` needs it on disk. The suite set to run before
  shipping is: security_audit, adversarial_suite, a1a_a2, a3_bounded_reads,
  a5_size_coherence (all in `run_all_tests.sh`).

### M9. Write the matrix so that *acceptance* is the failing outcome.
A4 found six classes of bad block in one run because every case asserted
"height unchanged AND a named anomaly recorded", and the test was written
BEFORE reading what the acceptor checks. Reading the acceptor first would have
produced cases for exactly the checks that exist; writing from the attacker's
side ("what can I put in a hash-committed header field that I mine myself?")
found the fields nobody checked: `index=2.0`, `stake_rewards=inf`, an empty
transaction list with `alignment_score` pinned to the governor value. Also:
a refusal that the node reports as success (`outcome:"duplicate", ok:true`
for an invalid block at the tip) is the same A1a class — check the reply, not
just the state. Mining at difficulty 4 ~60 times is slow: the full matrix
takes ~3–4 min; give it `timeout 500`.

---

### M10. Run the suites nobody has run, and trace races with a patched runner.
`test_multinode_live.py` had been skipped by three runs as "10 min, residual
risk". Run for the first time against v8.18 it failed the same two relay
checks 2/2 — a real bug, not flakiness — AND showed the founder *spending*
on a loaded genesis, which overturned DE1's "inert until 2027". Two findings
from one run of an existing test. **A test that has never been run against
the shipped file is an unverified claim, however old.**
To trace a cross-process race without editing the source: a 40-line
`trace_runner.py` that imports `covenant_unified_v8`, monkeypatches the
methods of interest (`announce_block`, `_fetch_announced`,
`_accept_block_common`, `SpikingAnomalyMonitor.record`) to print
`time.time()` + thread name, sets `sys.argv[0]` and calls `cov.main()`; point
the harness's `CORE` at it. Thread names (`covenant-fetch_0` vs
`Thread-6 (_bootstrap_once)`) named the two racing paths in one run.
Also: `/anomalies` shows only `per_kind` counts — the detail strings are only
visible this way. `free_port()` in the multinode harness can still collide
(one 2/21 run with "all three nodes came up" false); re-run before believing
a startup failure.

### M11. Kill tests: SIGKILL, reuse the db, and know what signals cannot stage.
- Use `p.kill()` (SIGKILL), never SIGINT, for survival tests — a clean
  shutdown hook is not what a power cut runs. Restart on the **same db path**
  so persisted state is what is tested. `KNet` in `test_a1_kill_matrix.py`.
- **SIGSTOP cannot stage a dropped message.** A stopped process still has a
  listening socket; the kernel completes the TCP handshake into the backlog
  and buffers the bytes, so a frame sent to a frozen peer is delivered the
  moment it resumes. "Partition then heal with no restart" therefore cannot
  be built from signals on one host — test that path in-process with a fake
  peer listener instead (K5), or accept that only the boot path is provable
  live.
- `/chain` is rate-limited 20 reads/60 s **per node**. Three nodes polled
  every 1.5 s for 30 s read as height 0 / tip `""` — a converged network
  looked split. Poll every 3 s and treat 429 as "not yet".
- A kill matrix should be written from the failure side (M9): K2 "miner
  killed the second `/mine` returns" was the case nobody had a path for, and
  it failed 3/3 on the first run.

### M12. Scale questions are usually arithmetic, not 1000 processes.
A11 asked "what does the heartbeat do at N=1000?" and the whole answer came
from two constants: `ATTENUATE` 0.02 per 120 s against a 3600 s half-life
toward 0.5 has an equilibrium below `MIN`, so every link hits the floor in
31 rounds; and the spike rule `recent ≥ 5 and recent > 3×expected` with a
lock-step schedule is a false spike for exactly the first three rounds at
degree ≥ 5. **Before building a harness, write the recurrence for each
per-event side effect on the receive path and solve it.** Then confirm with
the real class and a patched clock (`cov.time.time = lambda: base + t` —
the module imports `time`, so patch `cov.time.time`, and restore it in a
`finally`). For the receiver itself, `socket.socketpair()` + a thread running
the real `_handle_peer(conn, addr)` drives the production handler in-process
with no listener and no second process (0.25 ms per frame); `m.api.app.
test_client()` reaches the Flask routes the same way. 23 live checks in ~20 s.
Also: `sim1000_network.py` is a LEDGER sim — `apply_transaction_ledger`
only. It never calls `validate_block_shape`, `_handle_peer`, the pools or
the gossip loop, whatever a backlog item says it measures.

### M13. Judge-layer tests need no keys, no sockets, no mining.
Subclass `_APIReasoningJudge`, stub `_call` to return canned text (or raise),
and every parser/fail-closed path runs in microseconds; count `evaluate()`
calls by overriding it (not `_call` — `_retry_with_backoff` makes 3
attempts per evaluate, which is what a naive counter sees). Monkeypatch
`requests.post` to capture the `timeout=` each provider passes rather than
waiting on a real timeout. Routes via `master.api.app.test_client()`;
`/anomalies` returns `per_kind: {kind: {recent, baseline, expected_recent}}`,
not bare counts. The peer-ingest path is `CovenantUnifiedMaster.
_ingest_peer_transaction`, not on `P2PNode`. Pre-fix evidence is cheap here:
copy the old parser into the test verbatim (`old_parse`) so the record of
what it did is executable, and run the new test against the backed-up
previous source once before shipping (a second copy of the file in another
dir with `covenant_path_pattern.py` beside it). 162 checks in 29 s.

### M14. Send-path tests: shim the socket, tap the pool, measure with monotonic.
- **Black-hole peers without a network:** subclass `socket.socket`, override
  `connect` to sleep the socket timeout and raise `socket.timeout` for
  addresses in a `DEAD` set (and redirect `REVIVED` ones to a real
  listener), then install it as `cov.socket = <module copy with .socket
  replaced>` — the patch is local to the module, the real listener in the
  test keeps the real class. Deterministic on any OS, which a real
  10.255.255.1 is not (it times out here; 192.0.2.1 is *refused*, instantly
  — a refused peer costs 0.13 s, a dropped one 15.13 s; only the second
  kind is a hazard). Run with `COVENANT_PEER_SEND_TIMEOUT=0.5` and
  `COVENANT_MAX_CONCURRENT_SENDS=4` so the arithmetic is visible in seconds.
- **See every dispatch:** `cov._SEND_POOL.submit = tap` records (time,
  host, port, attempts) per submit and the futures to `wait()` on;
  `cov._SEND_POOL._work_queue.qsize()` is the queue-growth signal. Count
  attempts at the shim's `connect`, not at the pool.
- **Clocks:** `cov.time.time = lambda: real() + OFFSET` patches the `time`
  module globally (M12) — so measure latencies with `time.monotonic()`,
  advance `OFFSET` to expire backoffs, restore in `finally`.
- **Ports:** a closed listener whose accept thread is still blocked keeps
  the port; give each scenario its own port instead of rebinding.
- **Run times:** the runner's timeouts are ceilings, not estimates. Every
  suite in `run_all_tests.sh` ran here in < 90 s, all twelve in ~6 min in
  parallel pairs. Never skip a suite on the strength of a quoted run time.
- **Subagents:** a *resumed* fetch subagent reported the `Projects` tool
  disabled while a fresh spawn had it; it recovered the doc from the
  session transcript's `tool_result` JSON instead. Spawn fresh for fetches.

### M15. The log snapshot handed to a run at boot can be STALE — re-read it, and grep the SOURCE, before selecting an item.
This run picked A12 and did it in full before discovering (when a fresh
subagent fetched the log for the write-back) that a run 40 min earlier had
already closed A12 — the boot snapshot of this file pre-dated that entry.
Two runs off one stale snapshot both grab the same "highest-value unblocked"
item and ship divergent fixes for it. Two cheap guards, both mandatory now:
1. **Re-read `IMPROVEMENT_LOG.md` fresh (a `project_read`, not the system
   prompt's boot snapshot) immediately before choosing the item** — the boot
   context can lag a concurrent run's write.
2. **Before starting, `grep` the SOURCE in the project for the symbol the
   chosen item's DONE/target line names** (M6 already says this for building
   ON a done item; it applies just as hard to NOT re-doing one). Had this run
   grepped the v8.22 project source for `PeerHealth` first, it would have
   found it absent — but so is the fix, because the 00:15 save never landed;
   the tell would have been the log entry existing at all. The log read is
   the real guard; the grep catches the inverse (a done-line whose code never
   shipped, which is exactly what the 00:15 A12 save is).
Also: the project write-back is the commit, and it is not transactional with
the source write. The 00:15 run wrote its log entry (persisted) and believed
it wrote its source (did not persist) — a torn commit. **Verify the source
round-trip by re-reading its hash after `project_write`, every time** (M8's
subagent fetch does this for free); a bare `replaced: true` is not proof the
bytes you intended are what landed.

### M16. `project_info` timestamps expose a torn commit; a file newer than the log is an unlogged run.
At this run's boot the log's last entry was 00:40 (`created_at` 00:25), but
`project_info` showed `claude/test_b5_mine_latency.py` and `run_all_tests.sh`
written at **00:47** — a run had done B5 and wired it in, and its log
write-back never landed (the 00:15 run's failure mode, mirrored: source
persisted, log did not). **Before selecting an item, compare every doc's
`created_at` against the log's; anything newer than the log is work the log
does not know about.** Read its header — the test docstring carried the
whole finding — verify it (run it, twice), and log it on the unlogged run's
behalf rather than re-doing it. Also: the sweep of 12 suites runs in two
parallel batches (8 fast, then a9/a4/a1/multinode) in ~4 min total here;
`test_a12_dead_peers.py` is the `PeerHealth` test and fails by design on the
`_delivery_order` source — not a regression (see the banner).

### M17. Edit the log on disk, and get the pristine source for free.
- **Log write-back without retyping 97 KB:** have a fresh subagent write
  `IMPROVEMENT_LOG.md` to `/home/claude/...` verbatim, apply the run's
  changes there with `Edit`/a python `replace` that asserts exactly one
  match per anchor, then `project_write(local_path=...)`. Zero main-context
  cost for the unchanged bulk, and "never rewrite earlier entries" is
  enforced by construction (you only touch the anchors you name).
- **Pre-fix evidence costs one call:** `project_read` on
  `covenant_unified_v8.py` returns a `local_file` path (it is too big for
  inline) — `cp` it beside `covenant_path_pattern.py` in another dir and
  run the new test there. No need to keep a backup before editing.
- **The log is now ~97 KB and is the whole boot context of every run.** It
  will keep growing ~5 KB per run. Proposal for L (not done — §1 says earlier
  entries are never rewritten, and moving them is a judgement call a run
  should not make alone): archive run-log entries older than the last five
  into `claude/IMPROVEMENT_LOG_ARCHIVE.md`, keeping §0–§4 and the tail here.

### M18. A socket timeout bounds one recv, not the exchange; and a flaky suite must be re-run on the PRISTINE file before it is called a regression.
- `sk.settimeout(T)` + `recv_bounded` bounds each chunk and the total bytes,
  never the wall clock: a peer that sends one byte every 0.2 s keeps every
  reader in the file alive indefinitely (measured: `bootstrap_chain` past
  6 × timeout on v8.25, and it would have gone on forever). Whenever a loop
  reads until EOF, ask what bounds its *duration*; if nothing does, it is a
  pinned worker per malicious peer. `Trickler` in `test_a14_boot_probe.py`
  is the 15-line probe. `concurrent.futures.as_completed(futs, timeout=…)`
  gives arrival order AND a deadline in one call.
- `test_a13_one_way_sync.py` failed T5 once inside the 6-suite parallel
  batch on v8.26, then 1 in 3 alone. Before calling it a regression it was
  run 4× on the pristine v8.25 — 1 in 4 failed there too. Root cause was
  the test: Z lied (`height 1e9`) from the start, so Z and Y both answered
  "ahead" to the T5 heartbeat and whichever `_delivery_order` put first took
  the one catch-up cooldown. **A new failure in an old suite is a regression
  only if the pristine file passes the same number of runs.** Keep the
  pristine copy (M17) until the sweep is done, not just for the pre-fix run.
- The security audit's AST check rejects `except …: pass` anywhere in the
  core — set a flag in the handler instead (it cost one sweep iteration).

### M19. Read the listener, not just the reader: an accepted socket inherits NO timeout.
A15 was written as "each site bounds bytes and per-recv time". True for the
three outbound readers (`settimeout(PEER_SEND_TIMEOUT_S)` before connect);
false for both inbound handlers — `sock.accept()` on a blocking listener
hands back a socket with `gettimeout() is None`, and nothing in the file
set one. So the cheapest attack in the whole A-series was open: `K`
connections that send nothing, where `K = MAX_CONCURRENT_HANDLERS` (96),
and the node is deaf to every peer for ever with `/anomalies` empty
(measured: 4 idle sockets, honest BLOCK_REQUEST never answered). **Whenever
a bound is added on a read path, print `sock.gettimeout()` at each site
first** — a `None` on an inbound socket is a pinned worker per idle
connection, a cheaper hazard than any trickler. Also: `recv_bounded` can
carry the whole fix (`settimeout(min(own, remaining))` per recv, raise the
socket's own `socket.timeout` when that is what fired, `PeerMessageTooSlow`
otherwise) so no call site changes and outbound semantics are byte-for-byte
what they were; U4 in `test_a15_exchange_deadline.py` asserts that.
`socket.socketpair()` with `settimeout(None)` is the 3-line model of an
accepted connection.

### M20. Parallel sweeps: ≤ 10 wide, and a failure in a batch is not a failure until it fails alone twice.
A 12-wide batch of the fast suites on the unchanged v8.27 produced three
failures (a1a_a2 "correct config boots", a13 T4, security_audit "chain
does not halt" — `/mine` non-200 under CPU starvation); each passed 2/2
alone and in the next 12-wide batch. A fourth (a15 U4) was a real test
bug the load exposed: thread helpers in `test_a15_exchange_deadline.py`
referenced the module-level socket `b` **late-bound**, so a flood thread
from U3b that had not yet died spilled 64 MB into U4's fresh socketpair
(`PeerMessageTooLarge` after 0.66 s). Fix: bind the socket as a default
argument (`def flood(sk=b)`). **Rule:** any thread helper in a test must
capture its socket at definition time; and run batches ≤ 10 wide (10 + 5
has been clean across six runs; 12 was not). Also, for D1: the Crypto.com
MCP `get_candlestick` returns only the most recent 50 bars, no `since`
(DE4); Kraken via WebFetch still works for history — ask for "the FIRST
60 rows as CSV lines" per `since` window (returned 58, 60, 63, 64, 40:
the count is never what was asked, M1), merge on overlapping boundary
rows asserting byte-equality, verify 86400 s spacing, then re-fetch one
interior window at an unrelated `since` and diff it (25/25 identical).
Five windows covered 281 days in ~10 min. **Amendment 2 (08:00): the SLOW
batch (a4/a1/a9/multinode, all mining) must be ≤ 5 wide — at 8 wide a
`/mine` HTTP call timed out at 15 s and multinode failed, 21/21 ×2 alone.**
**Amendment 3 (2026-08-26): ≤ 5 is not a constant, it is a ratio.** A 5-wide
slow batch on a **2-vCPU** box produced two reds — `test_a1_kill_matrix`
(a `/mine` HTTP call timed out) and `test_b5_mine_latency`
(`Invalid registration proof`: the PoW went stale while the process was
starved). Both passed **2/2 alone**, so M20's rule held and cost ~4 minutes.
Read `nproc` first: **slow batch ≤ vCPUs + 1**, fast batch ≤ 7 regardless. And
note the second symptom, because it does not look like starvation: a
*freshness* window (registration PoW, nonces, timestamps) fails as an
**authentication error**, not a timeout, when the CPU is oversubscribed.
**Amendment (06:45):** asking for
"the FIRST 100 rows" works too — SOL returned 86/84/94/84/50, XRP
100/82/84/83/50 — so a full 2025-01-01 → 2026-01 symbol is 5 windows + 1
independent re-fetch, ~8 min. Always end with the re-fetch diff.

### M21. Test the deployment SHAPE, not just the mechanism; and a summed-return engine is not a compounding one.
- Every propagation suite through A15 peered nodes BOTH ways (the harness
  lists everyone). The first configuration a real phone is in — lists the
  PC, PC lists nobody — had never been run, and on v8.27 it never synced
  (A17). **When a backlog item is "deployment", write the harness from the
  operator's config file, not from the test's convenience.** Two real
  processes on `hostname -I`'s address (not 127.0.0.1) is the VPN shape
  and costs nothing extra; `test_a17_oneway_peer_sync.py` is the recipe
  (founder db reused so `/mine` has a spendable genesis; operator-signed
  `/mine`; zero-value tx; `benefit_score` = `/health`'s `alignment`).
- `covenant_backtest.Backtester` sums dollar P&L of fixed-notional trades
  (`capital / entry_px`), so a 9-trade losing sequence reads −74 % where
  compounding reads −54 %. Compare strategies on ONE convention (the
  engine's, or log-growth) and say which. And the first bootstrap helper
  used bar t+1's own open→open return for a decision made at t's close —
  look-ahead by one bar, +112 % "edge" — caught only because the engine
  structurally cannot do that. **Any hand-rolled return series must be
  reconciled against the engine on one asset before it is trusted.**
- 8-wide slow batches (a4 + a1 + multinode + a9 all mining) time out
  `/mine` calls at 15 s; keep the slow batch ≤ 5 (M20 amended).

### M22. A subagent-transcribed file with no logged hash is unverified until an independent source agrees with it.
The 07:45 run's fetch subagent wrote thirteen docs "verbatim" but could
only prove it for the four whose sha256 the log already held. For the three
598-bar CSVs (no logged hash) it said it had "assembled" them from the
verified `_2026Jan` prefixes plus the remaining rows — the word that should
stop you. The only proof available is external: re-fetch an interior window
of the *unverified tail* from Kraken at an unrelated `since` and diff by
timestamp (XRP 25/25, SOL 20/20, XLM 20/20 identical). **Always log the
sha256 of every CSV you ship** (the 07:14 run did not), so the next run can
check a transcription in one `sha256sum` instead of three fetches. Also from
this run: the WebFetch summariser's `LAST=` line is unreliable on interior
windows (it printed `1778025600` once for a reply whose true `last` was
`1787270400`) — only trust `last` on the final window, and confirm it by
fetching one more window past it; the partial bar after `last` came back and
was dropped. Seeded bootstrap p-values reproduce exactly (that is
reproducibility, not confirmation); a second seed shifting p by ≤ 0.02 is
the cheap check that the verdict is not a seed artefact.


### M23. Two runs can overlap; a concurrent run is detectable and survivable. *(Written by the 07:15 run as M21; restored and re-numbered at ~08:20 after the 08:00 write-back dropped it.)*
This run booted at 06:38 while the 06:20 run was still writing (SOL 06:25,
XRP 06:32, its log entry 06:42 — all AFTER this run's boot snapshot of the
log, which ended at 06:20). M16's timestamp check showed the two CSVs as
"unlogged"; they were not — their entry landed 4 min later. So: **a doc
newer than the log may be an in-flight run, not a torn commit.** Before
logging on an "unlogged" run's behalf, `project_search` the log for the
doc's name — a fresh hit means the other run already logged it. Pick an
item the other run's own "Next" line does NOT name first (it said HBAR
next; this run checked for an HBAR file before starting and again before
writing). At write-back, fetch the log FRESH (the 06:42 version here was
85 lines longer than the boot copy), apply edits by exact anchor, and never
paste a boot-time copy over it. Also, from the Kraken work: the WebFetch
summariser's row *indexes* are as unreliable as its counts (it called index
92 "row 100") — only the timestamp-keyed byte diff means anything; the
`last` field in the reply is the last COMPLETE bar, so drop any row after
it (today's partial bar came back and was excluded). `claude/verify_csv.py`
is the contiguity check (spacing, 00:00 UTC, date column, OHLC/vwap
sanity, dups) — run it on every deep CSV before shipping.

### M24. Kraken's public API answers plain `urllib` here — fetch structured data as JSON, never through the WebFetch summariser.
Found 08:45 while probing CRO: `urllib.request.urlopen("https://api.kraken.com/0/public/OHLC?pair=ADAUSD&interval=1440&since=…")` returns the full JSON (up to 720 bars per call, the `last` field exact). Every M1 hazard — dropped rows, lying totals, unreliable indexes, `LAST=` misreads — was the *summariser*, not Kraken. Proof: ADA rebuilt from two direct calls hashes to `a0ae69f1…`, the WebFetch-assembled file's logged hash, byte for byte; and a WebFetch window of ATOM agreed with the direct file 5/5. Recipe (`~20 lines`): `since=start-1`, page on `last`, keep rows `start ≤ ts ≤ last` (drops the forming bar), assert overlap rows equal, write with `csv.writer(..., lineterminator="\n")` — **the default `\r\n` silently changes the hash** (first cut did). Verify with `verify_csv.py`, then re-fetch two interior windows at unrelated `since` and diff by timestamp. Seven symbols, twice-verified, in ~4 minutes of wall clock and < 5k tokens of context — versus ~50k tokens per symbol before. Also: **never `project_read` a CSV inline** (the ADA check cost ~40k tokens of context); hash-compare via a subagent or compare a few grep'd rows. Network allowlist still applies: WebFetch remains the only path for pages that fail, per the sandbox rules; this is for an API that *succeeds* through both.

### M25. `project_write` is not delivery. Grep the DEPLOYED file, not just the project's.
M6 says do not trust the backlog's claim that the code changed — grep the
source. Twenty runs did that faithfully, to the source in the *project*, and
none to the one on the machine that runs the node. On 2026-08-22 the PC held
`covenant_unified_v8.py` at 7774 lines / `54955648…` / mtime 08-20 23:33 —
**pre-v8.15**. `grep -c` for the symbol each closed item names returned 0 for
`preflight_port_check` (A2), `serialized_size` (A5), `_gossip_tip` (A1/K2),
`_delivery_order` (A12), `_send_announce` (A13), `_bootstrap_round` (A14),
`MAX_EXCHANGE_S` (A15) and `infrastructure_failure` (B3). Sixteen closed items,
none of them running anywhere but a cloud test.
**The bridge rule, sharper than M5/DE2:** the device bridge exists when **L
starts the session**, not when L is merely present in one — the 10:30 and 23:30
runs both had L in the conversation and no bridge because a *schedule* had
started them. So: an unattended run still ships via SendUserFile +
`project_write` and still writes the "L: copy…" line (nothing else is possible);
an attended, L-started run **does the copy** with
`device_stage_files`/`device_commit_files` and verifies by sha256 on the far
side. And at the top of any run that can reach the PC, hash-compare the deployed
source against the project's before choosing an item: **drift outranks the
backlog**, because fixing item N+1 in a file nobody runs is not progress.
Two things the bridge does not fix, both recorded in `claude/PC_SYNC_LOOP.md`:
every write invalidates `covenant_seal.py`'s root (`SEAL_ROOT.txt`, anchored to
the chain), so re-seal promptly — a tamper-evident seal that is usually wrong
teaches its operator to ignore it; and anything a tool writes on every run
(e.g. `daily_state.json`) belongs OUTSIDE the synced folder for the same reason.

### M26. Swapping an implementation can disarm a control that was measured against the old one.
W1 replaced werkzeug's dev server with waitress. The full 20-suite sweep on the
werkzeug path was green, so the change looked free — and then `test_a1a_a2`
A2-2 hung on the waitress path and left a node running for ever. Cause:
`preflight_port_check`'s HTTP-vs-P2P discriminator (M4) was *measured* against
werkzeug, which answers an unterminated request line with an HTTP/0.9 HTML body
("non-empty and not JSON" → HTTP → fatal, correct). **waitress answers nothing
at all** — it is still waiting for the CRLFCRLF that ends the headers when the
half-close arrives. Empty reply → verdict "P2P" → preflight passes → the exact
footgun A2 exists to catch (`--peers` pointed at a Flask API port) goes through
silently. Fixed by asking a question every HTTP server must answer and a P2P
listener cannot: when the first probe says nothing, send a WELL-FORMED
`GET / HTTP/1.0` and check for a status line. Generalise it: **any check whose
rule was derived from one implementation's behaviour ("werkzeug replies X")
must be re-run against the replacement before the swap is called safe** — and
the reason the existing suite caught it is that it asserted the OUTCOME
(preflight refuses) rather than the mechanism. Also: the pre-fix record here is
not synthetic; it is the leaked `covenant_unified_v8.py --port 5021 --node-id C`
process that the sweep left running.

### M27. There are two "locals" on this machine, and they prove different things.
`device_bash` runs in a Linux VM with the covenant folder mounted read-write —
genuinely L's machine, genuinely the deployed bytes. It is **not** the runtime the
node uses. Measured 2026-08-22: VM python 3.10.12 vs Windows `.venv` 3.12.10; **no
network at all** in the VM (`403 Forbidden` at the tunnel for Kraken *and* PyPI —
note this is the failure `DAILY_CHECK_CLOUD_BLOCKER.md` wrongly attributed to the
cloud sandbox, where it is false); loopback only, so `hostname -I` is empty and
`test_a17_oneway_peer_sync.py` dies with `IndexError` before it starts; and **M5's
process rule holds here too — a background process is killed when its
`device_bash` call returns** (`setsid nohup` does not save it; measured with a
25 s sleep that left nothing behind), on top of a hard 45 s per-call ceiling. So
the VM can run any suite that finishes in ~40 s and nothing else.
Recipe that makes it work: copy `flask werkzeug jinja2 markupsafe itsdangerous
click blinker` **and their `*.dist-info`** out of `.venv\Lib\site-packages` into
`~/pylibs`, `find ~/pylibs -name '*.pyd' -delete`, and set `PYTHONPATH` — but
never put the venv's `cryptography` on the path, the VM has its own Linux build.
The `.dist-info` copies are not optional: `flask.testing` calls
`importlib.metadata.version("werkzeug")`, and without metadata every suite using
`app.test_client()` dies with `PackageNotFoundError` (six did). Run in `~/sweep`,
never in the mount — the suites `rm` their databases and **`device_bash` cannot
delete inside the mount**, and every write there invalidates the seal.
For the whole sweep, drive Windows: a `.bat` that runs `run_local_sweep.py` in
`%TEMP%` and writes its results into the covenant folder, where the bridge reads
them.

### M28. A batch file is a delivery mechanism; give it the same suspicion as code.
Two failures in one run, both silent, both in `cmd`:
- `echo --- health A (5000) ---` inside an `if ( … )` block. The unescaped `)`
  closes the block early, cmd aborts the script, and it had written three lines
  and stopped — no error visible from the bridge, nothing done. **Use GOTO labels
  instead of parenthesised blocks in anything that has to be trusted unattended,
  and grep the file for `(` outside `REM` before shipping it.**
- `taskkill /f /fi "windowtitle eq …"` kills the **cmd wrapper**, not the
  `python.exe` it launched (no `/t`), so a "stop" reports success while the node
  keeps its port. Kill by PID from `netstat -ano` as well, and **assert the port
  is free before starting** — a restart that cannot fail is how a machine keeps
  running a source from days ago (M25's mechanism, one layer down).
Also: a launcher whose output is redirected to a file writes nothing visible until
it exits, so **write progress to a file the watcher can read**, not just stdout —
40 minutes of this run were spent blind.

### M29. Run it where it runs: the same source has different bugs on each platform, and a suite that cannot run there proves nothing there.
Three defects found in one evening, all in code that had passed every cloud
sweep for days, none findable without executing on the machine that runs the
node:
- `run_sandboxed()` needs a **fork** start method. On Windows `get_context("fork")`
  raised `ValueError` straight past `validate_and_score`, `DAGNode.create` and
  `/propose_code`'s `except CodeSecurityError` into a bare **HTTP 500 with nothing
  on /anomalies**. Fail-closed by accident, undiagnosable from outside.
- the same function then failed on **Linux** for an unrelated reason: the child
  sets `RLIMIT_NPROC = 0` (no new processes) and reports through a
  `multiprocessing.Queue`, whose `put()` starts a **feeder thread**. The sandbox
  forbade the mechanism it used to speak. Measured both ways on L's machine:
  Queue+NPROC=0 → child dies with exit code 0 and no report; Queue without
  NPROC=0 → fine; Pipe+NPROC=0 → fine.
- **Windows' `SO_REUSEADDR` is not POSIX's.** There it lets a second process bind
  a port another process is *actively listening on*. A2's preflight probe set it,
  so the check that exists to catch port collisions could not see one on the only
  platform where two nodes can silently share a port — which is exactly how a
  leaked test node came to hold node A's P2P port as its own Flask API.
The corollary for this loop: **a green sweep is green for the platform it ran
on.** Record which platform produced a result, and treat "cannot run here" as an
untested claim, not a passing one.

### M30. A fact that is only ever asserted, never measured, drifts silently — so give every claim you depend on a way to answer for itself.
This loop has now found the same failure four times in four places, and it is
one failure: *the PC has the latest source* (asserted sixteen runs, false —
M25); *`covenant_prod.bat stop` stops the node* (asserted until someone watched
it — P3); *the guards are wired into `daily.py`* (asserted until someone
grepped — D4); *this is v7.0* (asserted since v7.0 — P11). None was a lie and
none was checkable, which is the whole point: **an unmeasurable claim does not
degrade gracefully, it degrades invisibly.**
The remedy is not more vigilance, it is to move the claim from prose into
something that answers when asked, and then to ask on a schedule:
- **Make the thing self-describing.** A node that prints its own source hash
  cannot be wrong about its version. A `COVENANT_VERSION` nobody reads can be
  wrong for twenty-one versions, and was.
- **Compare two independent measurements, never one against a memory.** The
  watchdog's new check is worth more than the banner alone because it puts
  *loaded* beside *on disk*: either alone is a claim, the pair is a test.
  `covenant_seal.py verify` is the same shape and answered in one call what
  "the seal is stale" had asserted vaguely for three days (20 changed, 81
  added, **0 removed**).
- **Put it on the clock.** A check that runs when someone remembers is an
  assertion with extra steps. In `logs/watchdog.log` the answer is now a line
  per minute, which is also a record for whoever reads it next week.
- **Test that the check can fail.** `test_p11_version_identity` V4 imports a
  one-byte-different copy and requires a different hash — without it a
  hard-coded constant passes the "agrees with an independent digest" check by
  accident. And V5d, as first written, asserted "the banner does not say v7.0",
  which an EMPTY banner satisfies; it passed on the VM run where V5b/V5c failed
  for want of the very evidence V5d claimed to inspect. **A check whose
  assertion is satisfied by missing evidence is not a check** — bind it to the
  evidence existing.

### M31. Sensing may inform refusal and disclosure. It may never inform relaxation — and pin that in a test, not a comment.
Adding a sensor to a fail-closed system is the moment its guarantees are most
at risk, because the *helpful* next edit is always the forbidden one: notice
memory pressure → extend the judge timeout; notice load → lower difficulty;
notice a spike → stop recording it. Each reads as prudence and each fails OPEN
exactly when an attacker would want it to. Section 0 already forbids weakening
a control to make something pass; a sensor makes that easy to do by accident,
months later, in good faith.
So the rule, and the way to make it stick:
- **The sensor reports; `/health` warns; nothing else may read it.** A node that
  cannot judge properly says so and refuses. It never judges worse.
- **`degraded` is computed from the node's own capability, never from the
  weather on the machine.** That field is what a monitor keys off; letting the
  environment move it turns a capability signal into a load average.
- **Assert the boundary mechanically.** `test_p12_substrate_sensing.py` walks
  the AST: B1 fails if any function outside the allowlist so much as *names* the
  sensor; B2 fails if any branch in `/health` tests the reading; B3 fails if its
  numbers are *compared* outside `warnings()`; B3b fails if `degraded` touches
  it. A comment saying "do not wire this into a decision" is an assertion (M30);
  a test that fails when someone does is a measurement.
- **Then mutation-test the boundary check itself.** B2's first version matched
  the literal word `substrate` and was evaded by one local variable —
  `sub = ...snapshot()` then `if sub["available_memory_mb"] < 500` reads the
  sensor in a branch and never says "substrate". That hole was found by
  *injecting the violation and watching the check pass*, not by review. It now
  follows aliases to a fixpoint. **Every guard in this file should be run once
  against a deliberately broken copy; a guard that has only ever seen correct
  code has never been tested.**

### M32. "Backwards compatible" and "this is what goes on the wire" are two claims, and both are cheap to actually measure.
Two habits, learned the same hour, both from refusing to accept a plausible
substitute for evidence.
- **Interop: run the OLD binary.** A20 adds fields to every peer reply, and the
  reasoning that it is safe is sound — replies are JSON read with `.get()`, so
  unknown fields are ignored. Sound reasoning is still an assertion (M30).
  `test_a20_peer_version.py` C1–C5 start a **real pristine pre-A20 process**
  beside the new one and check BOTH directions: the old node accepts a new frame
  and answers normally, and the new node folds the old node's reply in as
  "cannot say" without inventing a version mismatch. **Point the test at the
  backup the delivery itself leaves behind** (`*.PRE-vX.Y.py`) rather than a
  file only the cloud has — a compatibility test that cannot run on the machine
  that runs the node is an assertion with extra steps.
- **The wire: capture the frame, not the return value.** What `build_digest()`
  returns and what leaves the process are different claims, and the gap between
  them is where the bug was: `build_digest` was defined next to `_reply`, which
  lives on `CovenantUnifiedMaster`, while `announce_block` lives on `P2PNode`.
  The node booted, printed its banner, served HTTP — and **silently never
  gossiped its tip**, which is A17's failure mode exactly, from a daemon thread
  whose traceback nobody would read. The way to catch that is to *be the peer*:
  bind a plain socket, start the node with `--peers 127.0.0.1:<that port>` and
  `COVENANT_TIP_GOSSIP_INTERVAL=3`, answer its preflight with silence or JSON,
  and read the bytes. ~40 lines, and it asserts the disclosure boundary against
  what actually left the process.
Corollary for anything that touches the P2P layer: **grep which class you landed
in.** This file has a node and a master and both read like "the node"; an
`AttributeError` on a daemon thread is not a test failure, it is a silence.

### M33. Audit the surface you just added, the same session you add it — the sweep that passed does not cover the attacker.
A20/A21 shipped green: 26 suites, 856 checks, interop measured against a real old
binary, the disclosure boundary asserted against bytes off the wire. Ninety
minutes later, asked to look for bad actors, I read my own new peer-input path
and found two defects in it. **A passing sweep tells you the code does what the
tests say. It tells you nothing about what an adversary does with the surface you
just widened.** So when a change adds a new input path, spend one pass on it
immediately, asking only: what can a peer make this do?
What that pass found, and both generalise:
- **A bound that REFUSES is a lockout, and a lockout is a signal an attacker can
  switch off.** `PeerStateTable` capped at 512 and refused new keys when full.
  Anything reaching the node from enough sources could fill it first and then no
  real peer could ever be recorded — silently disabling the A7 split-source
  warning. **Prefer eviction to refusal for any bounded OBSERVABILITY structure**
  (a bounded *security* structure may be right to refuse — the distinction is
  whether being full is itself an attack). Now evicts the oldest, so a flood
  costs the attacker its own rows as they age out.
- **I rebuilt the bug I had just fixed, one layer down.** The same night the
  watchdog learned to transmit change rather than state — after measuring 3,973
  log lines carrying 16 messages — I wrote `peer_version_mismatch` to record on
  *every* observation: once per heartbeat per differing peer, for ever, into a
  bounded buffer whose whole purpose is retaining phasic events. A tonic kind in
  there crowds out the events it exists to keep, and would trip the spike
  detector on a condition nobody can act on. **A lesson learned at one layer is
  not automatically applied at the next; go and check the code you wrote after
  learning it.**
And the corollary about prose: this pass also found a comment stating that
`POST /peers` is unauthenticated, directly above a route that
`PROTECTED_OPERATOR_ENDPOINTS` protects. M6 says trust the code over the
backlog's claim; the mirror is **when prose and code disagree, fix the prose AND
assert the control in a test**, because the next reader may act on the comment.

### M34. A check that fails on a platform should assert what is CORRECT there — never skip, and never be left red.
Three ways to handle a check that cannot hold on some platform, in increasing
order of value:
- **Leave it failing.** This is what the suite did, and it is the worst option,
  because it is not one cost but two: the check tells you nothing, AND a standing
  red line trains every reader to skim the section it lives in. That is the
  watchdog-log failure (3,973 lines carrying 16 messages) inside the test suite —
  a tonic signal drowning the phasic one. A sweep with four permanent failures
  cannot report a fifth.
- **Skip it with a reason.** Better, and what this file previously proposed for
  P10 — but a skip means the check stops checking on the platform where the node
  actually runs. The reason is printed once and then nobody reads it either.
- **Assert what correct behaviour IS on that platform.** Best, and usually
  available, because "this cannot work here" almost always means "here it must
  fail closed", and *that* is a property worth testing. Applying it to the three
  sandbox checks produced four assertions on the no-fork path — the refusal is
  complete, it names its reason, an infinite loop is refused without being run —
  plus one that runs on BOTH platforms and pins P4's one-way rule: **the sandbox
  never reports success when its limits cannot be enforced.** Nothing tested that
  before. Injecting a sandbox that claims success while unable to enforce makes
  all five fail.
Two supports that make this cheap: an env override that reaches the other
platform's branch from this one (`COVENANT_FORCE_NO_SANDBOX=1` exercises the
no-fork path on Linux, so the Windows assertions are verifiable everywhere), and
the discipline of writing the *claim* before the assertion — see the four
assert-a-proxy bugs in the 07:00 entry.
And the sibling case: **a knife-edge assertion is the same disease in miniature.**
b5's "second /mine paid again" compared a measured 2.50 s against a 2.51 s bar the
same run had computed one line earlier. The behaviour is real; the equality is
not. It passed one sweep and failed the next two, which teaches its reader
exactly what a permanent failure does. A 5 % tolerance keeps all of the check's
power — the mechanism failing would put the figure at a third of the bar — and
stops it crying wolf about the scheduler.

### M35. Check what the sandbox can actually build before deciding a deliverable can only be described.
The Android task arrived with an explicit escape hatch — *"if the SDK isn't
available, say so rather than claiming the build passes"* — and taking it would
have been reasonable and wrong. Measured instead, in four `curl`s and about
eight minutes: JDK 21 and Gradle are pre-installed, and `dl.google.com`,
`repo1.maven.org` and `plugins.gradle.org` all answer 200 through the proxy. So
`sdkmanager` installed platform 37 + build-tools 37.0.0 (956 MB) and the whole
thing compiled. **The escape hatch is for after the measurement, not instead of
it** — M30's rule ("an unmeasurable claim degrades invisibly") applied one step
earlier, to a claim about the ENVIRONMENT rather than about the code.
Four things a future run should not have to rediscover:
- **The toolchain has moved past training.** AGP **9.x has Kotlin built in**,
  and applying `org.jetbrains.kotlin.android` beside it is a hard error that
  names itself. Pure-JVM modules still need the standalone plugin, so a mixed
  build keeps it in the version catalogue and applies it to some modules only.
  Only JDK 21 is present, so `jvmToolchain(17)` fails with "cannot find a Java
  installation"; set `sourceCompatibility`/`targetCompatibility` plus
  `compilerOptions.jvmTarget` and build with 21 targeting 17.
- **Put every fallible line where a desktop JVM can run it.** Checksums, wire
  parsing, precedence, hash chaining — all in Android-free modules, 89 tests in
  5 s. What was left in the Android class is I/O and lifecycle, which is exactly
  the part no test here could reach. M29 in the mirror: if you cannot run it
  where it runs, at least arrange for the part you CAN run to be the part that
  is easy to get silently wrong.
- **Read the artefact, not the build log.** "BUILD SUCCESSFUL" says the compiler
  was happy. `aapt2 dump xmltree` on the built APK is what proves the
  `BIND_VPN_SERVICE` permission, the `android.net.VpnService` intent filter and
  the foreground-service type actually landed; `apkanalyzer dex packages` on the
  R8 output is what proves the keep rules kept the governance interface instead
  of R8 stripping an extension point that nothing statically calls. Both were
  run, and the second is the one that could plausibly have failed. Same shape as
  M32's "capture the wire, not the return value".
- **Pin a digest from an INDEPENDENT computation.** `AuditLogTest`'s canonical
  form is pinned against a value computed in Python from the written spec, not
  by running the Kotlin and copying its output. A pinned value produced by the
  code it is meant to check is a photograph, not an oracle.

### M36. Shrink the loop's read-imprint by MOVING, never deleting — and keep the index separate from the record.

**Applied to §5 on 2026-08-24, the second time this rule has paid.** The run log
had reached 3,608 lines — **56% of the whole file** — and every fresh run read
all of it to find three facts. The last three runs stay in §5; the other 35 are
in `claude/RUN_LOG_ARCHIVE.md`, verbatim, with a one-line index left behind.
The file went 6,137 → 3,253 lines. Nothing was deleted and nothing was edited.

**And the budget that stops it coming back: an entry earns about forty lines.**
Longer than that means the run is putting per-item detail in §5 (it belongs in
§4) or a lesson in §5 (it belongs in §2). The 07:00 entry below is 369 lines and
is the standing counter-example.
L: *"Shrink imprint while growing effectiveness while not losing content."*
Applied to the loop's own memory, which is the thing whose imprint grows without
bound: this file is read in full at every boot and had reached 4,852 lines.
Two costs were pure duplication, and both were removed **without losing a
byte**:
- The **STALL WATCH banner** exists to answer one question rule 6 asks — how
  many consecutive runs closed nothing. It had accreted **nine runs of
  narrative, 63 lines**, every sentence of which is also in §4 (as a
  struck-through item) and §5 (as a run entry). Moved verbatim to
  `claude/LOOP_HEADER_ARCHIVE.md`; the banner is 21 lines and says the number.
- **§4 is ~890 lines and holds ~14 open items.** A run reads all of it to pick
  one. An **OPEN-ITEMS INDEX** now sits at its head: one line per open item with
  its blocking state. Purely additive — nothing struck through was touched.
The rule that makes this safe: **an index may be regenerated; a record may not
be edited.** The banner and the index are derived views and may be rewritten
freely. §0 and §5 are the record: never. When you are tempted to delete
something from this file to make it smaller, the move is a new file plus a
pointer, and the run-log entry must name where it went — otherwise the next run
finds a gap and cannot tell shrinkage from loss.
*Effectiveness, not just size:* the banner now answers its own question in its
first sentence, and the index answers "what can I work on?" in thirty lines.
Both were previously answerable only by reading everything.

### M37. A suite that fails for want of a DEPENDENCY is not a regression — stage the dependency before you read the failure.
A fresh cloud sandbox holds **only what this run staged**, and the sweep's
dependency set is larger than its suite list. Two of the three failures in this
run's first full sweep were that, and both looked exactly like regressions
against the new source:
- `test_security_audit` → `ModuleNotFoundError: covenant_trading_bridge`, plus
  three cryptic `'NoneType' object has no attribute report_realized_profit`
  FAILs upstream of it. Staged the module: **128/128, twice.**
- `test_w1_wsgi` → `waitress is not installed`. `pip install waitress`:
  **24/24, twice.** This is P1 recurring in a different building — the same
  package, missing for the same reason, three days later.
So before the first sweep, stage: `covenant_path_pattern.py`,
`covenant_trading_bridge.py`, `guards.py`, `daily.py`, `covenant_watchdog.py`,
`trace_runner.py`, and `pip install waitress --break-system-packages`. Cost of
not doing it: two re-runs and a wrong first reading of a green change.
*And the general form:* when a suite fails, read the failure's **first** line,
not its verdict. An import error at the top of a run and an assertion failure in
the middle are different kinds of news, and only one of them is about your code.

---

### M39. Three of anything, with nothing varied, is one observation. (Written twice, wrong twice, corrected below.)
`computer_double_click` on a `.bat` in Explorer "worked once and then stopped",
so DE7 was written declaring the capability unusable. It was usable the whole
time. Every failure was a double-click on a row **the previous failure had left
selected**; every success was on an unselected row reached by navigating fresh.
Nothing was varied between attempts, and the repetition was mistaken for
evidence.

The working recipe, and it is worth having:

1. `computer_open_application` — brings a window to the front and gives it focus;
2. click the destination in the **sidebar** (typing is blocked at click tier, so
   the address bar is unavailable);
3. `computer_double_click` the target **without clicking it first**. An
   already-selected row does not open.

Confirm by **side effect, never by screenshot** — the launched console is masked
out of the image. Watch the mtime of the file the batch writes
(`NODE_RESTART.txt`, `INTEGRATE_RESULTS2.txt`): that is the only proof the
process started, and it arrives in seconds.

**CORRECTED 08:39, ten minutes after writing the above — and this is the third
correction against this run's own claims today, which is the honest number.**
The recipe is **not** deterministic. Applied exactly as written above, on a
fresh window, an unselected row, and a freshly-clicked sidebar folder, it failed
four consecutive times on `RESTART_COVENANT_ON_v8.35.bat` — the row highlighted
and nothing launched — after having worked three times in a row on three
different files.

**The truthful statement is: `computer_double_click` launches a program
INTERMITTENTLY, and I do not know what determines it.** Every discriminator I
proposed — already-selected row, stale window, sidebar navigation — has now been
contradicted by a run that satisfied it and still did nothing. What I have is
5 successes and 7 failures, and no mechanism.

So the rule that survives, and it is smaller than either of my two previous
attempts at it:

1. **Confirm by side effect, never by screenshot.** The launched console is
   masked out of the image. Watch the mtime of the file the batch writes
   (`NODE_RESTART.txt`, `INTEGRATE_RESULTS2.txt`). That part has never failed.
2. **Retry, but bound it.** Three attempts. It either takes or it does not.
3. **Never make a click the critical path.** Put the launcher one click from the
   Explorer sidebar and let L click it if the attempts do not take. A capability
   that works half the time is not a capability a plan may depend on — it is a
   shortcut that sometimes helps.

The general rule, which is the expensive half and survives both corrections:
**before writing a capability off — or writing it up — name the precondition you
did not vary.** DE7 wrote it off after three failures and was wrong. M39's first
draft wrote it up after three successes and was also wrong. Three of anything,
with nothing varied, is one observation repeated. The sweep got run either way,
which is the only reason this was cheap.

### M38. Hash all three: the project, the disk, and the RUNNING process. They are three different claims.
`project_write` is not delivery (M25) and `covenant_unified_v8.py` on disk is
not what is executing (P11). Measured 2026-08-24 on the production machine, the
banner said *"the nodes are on v8.30, the project holds v8.35, the restart is
five versions deep"* and **every clause about a version was wrong**:

| claim | what it said | measured |
|---|---|---|
| project | v8.35 `1207bd2e7dc5` | correct |
| disk | v8.30 (implied) | **v8.34 `773cb7d7adef`**, mtime 08-23 07:39 — an unlogged delivery |
| running | v8.30 | **pre-v8.31** — the boot banner still reads `Covenant Unified v7.0` |

The disk was one version behind, not five; the running process was older than
either; and nobody had ever measured the third. The three drift **independently**
— a delivery moves disk without moving running, a restart moves running without
moving disk, a `project_write` moves neither.

So the check at the start of an attended session is three lines, not one:

```bash
sha256sum covenant_unified_v8.py            # disk
curl -s :5000/health | grep source_sha256   # running   (v8.31+ only)
grep 'Covenant Unified v' logs/nodeA.log    # running   (works on any version)
```

The third line is the one that survives a node too old to answer the second —
and a node too old to answer is *precisely* the case you are hunting. If the
banner says `v7.0`, you are looking at a pre-v8.31 process whatever the disk
says. The same applies to every long-lived process, **including the watchdog**:
compare `logs/watchdog.log`'s first `watchdog started` line against
`covenant_watchdog.py`'s mtime before believing anything the watchdog reports.
That comparison is what found P14.

---

### M40. A result file is not a result. Pin the inputs or the next run can only repeat you, never check you.

Three semantic result files were written to the project on 2026-08-24 (11:10,
12:33, 14:05). Each is a clean table of PASS/FAIL and numbers. **None records a
corpus, a source file, a seed, or a space identity, and none appended here.**
Nothing in them could be verified. The only way to find out whether the
headline number meant anything was to build the entire pipeline again — which
is the exact cost **M22** exists to prevent, **M25** describes ("writing to the
project is not delivery"), and **M30** predicts ("a fact that is only ever
asserted, never measured, drifts silently").

The fix is small and it is a habit, not a tool:

- **the corpus**: pin the ids and the sampling seed in a `MANIFEST.json` next
  to the result. `fetch_corpus.py` writes one.
- **the artefact**: give the derived object a signature over everything that
  determines it. `build_space` hashes `(lang, tokens, vocab, window, dim,
  alpha, min_count, seed)` and prints it beside every number it produces.
- **the source**: ship it with the result, in the same write-back.

And the null belongs in the same sentence as the score. `P@10 = 0.21 vs random
0.00067` is a true statement that carries no information, because uniform-random
models an adversary who does not know how the words are spelled. **The null
must be the best cheap predictor available to someone without the thing you are
claiming** — here, edit distance, which beat the semantic space by 7× and would
have been visible in the first eval's own printed hits (`gold->gold#1`,
`secret->secret#1`) if anyone had asked what a dumber scorer would do.

Corollary, learned the same run and worth its own line: **a null that fails is
as valuable as one that passes.** The frequency-rank null was my hypothesis and
it scored 0.000–0.002 — refuted, recorded as refuted, and the space is cleaner
for it.

### M41. When two parts of one function disagree, the older one is usually still winning — and "the fix does not fire" is a claim about a BRANCH, so measure the branch.
A23 was filed as *"A18's path is not being reached"* with a named suspect (an
early `return`). It was reached on the first try. What made it useless was a
line **above** it: `_note_send_ok()` on `sendall()`, which cleared exactly the
counter A18's `_note_send_failed()` was about to set. `_send_raw` recorded a
failure it could not confirm AND erased the previous one, three times per send,
and both lines had a comment explaining why they were right. **A18 added a new
rule to a function that still contained the old rule it contradicts; nobody
deleted the old one, and the old one ran first.** So when a fix "does not fire":
- **Reproduce the shape, not the platform.** The Windows symptom is a peer whose
  port completes the handshake and never answers. That is 15 lines of listener
  and it runs anywhere. Two of the three A23 findings needed no Windows at all,
  and DE6 says a Windows run was not available — so "wait for the machine" would
  have cost three days for something a socket could answer in ten minutes.
- **Print the state either side of the branch, then read what the counter you
  are printing actually MEANS.** P7's Windows measurement (`dead_peers=0`) was
  correct and its inference (*"therefore neither site executed"*) was sound but
  incomplete: it did not ask what else touches that counter.
- **Grep for every writer of the variable your conclusion rests on**, not just
  the one you are looking at. One `grep -n '_send_failures'` would have found
  this on 08-24.
- **Then pin it in the source, not the prose.** §S6 asserts on
  `inspect.getsource(_send_raw)` that no `_note_send_ok` appears before the ACK
  read, and that exactly three failure sites remain. The next person "restoring
  the reachability signal" fails a check instead of quietly undoing this.
And the sibling lesson about wall clock: the SAME logical failure costs ~0.13 s
against a refused peer and ~15.1 s against one that accepts and holds. Every
propagation test that samples `/anomalies` when `/mine` returns is sampling an
**asynchronous** `_SEND_POOL.submit`; on Linux the record lands before the
sample, on Windows it does not. A green test and a red test can differ by
nothing but which kind of dead the peer is.

### M42. A comment that asserts a DATA FLOW can be wrong at birth. Write the check in the same session, and make it match code rather than prose.
M30 says an unmeasurable claim degrades invisibly, and every example there was
a claim that went **stale**. This run produced the other kind: a claim that was
**false the moment it was typed**, by me, in a source comment, as part of a fix.

The v8.37 guard on `BLOCK_ANNOUNCE`'s `index` shipped with a comment saying the
index "is echoed onward as the `from_index` of the `BLOCK_REQUEST` this node
builds" — a second amplifier beside the `tx_id` one. It reads well and it is
wrong: `_fetch_announced` calls `request_missing_blocks(host, port,
len(self.node.chain))`. **Our own height. The peer's number never leaves the
process.** One `grep -n request_missing_blocks` would have shown it, and I did
not run it because the sentence sounded like something I already knew.

What caught it was writing the assertion the comment implied — S5f, *"the
request it builds names that index"* — and then reading the failure instead of
adjusting the test. The suite now pins what actually happens (`from_index: 1`,
our height, never the peer's `7`), which is a better check than the one I meant
to write. **So: whenever a comment claims that A reaches B, write the check for
that flow in the same session.** A data-flow claim is cheap to assert, cheap to
be wrong about, and the version that ends up in a comment is the version the
next reader trusts. The guard itself stays — relabelled as what it is, input
shape hygiene (`true` was read as index 1, a float as an offset, a string
raised into the FRAMING-error channel) — because a guard being worth having and
its rationale being wrong are two different questions.

And the mirror, which cost twenty minutes the same hour: **a source-level pin
must match CODE, not source text.** §S8 asserted that the over-cap path does not
call `_note_send_failed` — and failed, on the new comment that says *"DO NOT
call `_note_send_failed`"*. Its count check said 5 sites where there are 3:
three calls and two comments. Strip comments and docstrings with `tokenize`
before matching (`code_only()` in `test_a3s_send_bounds.py`, ~15 lines; join the
tokens with a space so `x.replace(" ", "")` reproduces the exact call text). A23
pinned its rule the same way one run earlier and got away with it on the luck of
its wording.

**AMENDMENT 2026-08-26, and it cost one failing check to learn: tokenized code
still contains STRING LITERALS, and a refusal message is prose that happens to
live in a string.** R8e in `test_r1_lora_frame.py` was written to assert that a
deliberately-rejected option — hash truncation — is documented but never built.
It matched `"truncat"` over the tokenized source and FAILED, on eight
occurrences of `raise LoraFrameError("truncated varint")` and its siblings:
refusal messages saying *this frame arrived truncated, I reject it*, which is
the exact opposite of the feature being forbidden. The tempting repair was to
reword those messages, which would have deleted real diagnostics to satisfy a
badly-worded assertion — §0's "fix the test, not the control" in miniature.
**A claim about whether something is IMPLEMENTED is a claim about IDENTIFIERS**,
so the view a source-level pin needs is usually NAME tokens only, not "code
minus comments". Both views are worth having and the suite now keeps both: R8e
asserts the identifier is absent, R8f asserts the refusal messages are still
THERE (so a future run cannot make R8e pass by scrubbing them), and R8g injects
`truncate_hash=False` into a copy and requires R8e to fail against it — M31's
rule that a guard which has only ever seen correct code has never been tested.

### M43. A round-trip check that reads its own input is not a check.
`project_write` returning `replaced: true` is not proof the bytes you intended
are what landed — M15 says re-read the hash. This run did, and the *way* it was
nearly done wrong is worth more than the result.

`project_read` returns a large file as a `local_file` path (cheap, `cp` it) and
a small one **inline as a JSON `content` string**, with no file on disk. There
is then a temptation to reconstruct those bytes from somewhere convenient — and
this session's transcript contains, for the very same filenames, the `Write`
tool inputs that created the LOCAL copies. Comparing those against the local
copies matches **by construction** and proves nothing. The check is only real if
the bytes come from a payload whose parsed `method` is `project_read` for that
`path`.

The standing recipe for any delivery, from now on:
1. `project_write(local_path=...)`.
2. A **fresh** subagent (M14): `project_read` each path back, write it to a
   scratch dir **from the tool result only**, `sha256sum` both sides, and `cmp`
   at full length rather than trusting a 12-character prefix.
3. Require it to state MATCH/MISMATCH **and where the bytes came from**. That
   second sentence is what makes the check auditable by the next run.
Four files, ~600 KB, verified this way in one subagent call at zero
main-context cost. Two properties fall out for free on the inline path: UTF-8
survives the JSON string encoding, and so does the trailing newline.

### M44. The step that runs LAST and only on the target is the step nobody has executed. Read the call chain to its leaves.
`verify_deploy.py` was mutation-tested on all three claims it checks — a byte
appended to the core, a companion deleted, a file never copied, and two real
nodes booted on different sources to prove the running check both ways. It was
careful work. The one line in it that had never been exercised anywhere is the
line that does the actual thing:

```python
subprocess.run([bat], cwd=HERE, capture_output=True, text=True, timeout=300)
```

because exercising it needs Windows and a real launcher. It had two defects,
and both are ordinary:

- **`capture_output=True` redirects stdout and stderr, not stdin.**
  `AB_RESTART_NODES.bat` ends in `pause`, which is correct for a human
  double-click. Composed, the prompt goes into the captured pipe, the console
  shows nothing, and a restart that may well have worked is reported as
  `restart launcher failed` after a 300 s invisible wait. `stdin=DEVNULL` fixes
  it — **and changes something else**, which is the half worth writing down:
  under a redirected stdin the launcher's own `timeout /t N` calls also return
  at once ("Input redirection is not supported"). That is survivable here only
  because claim 4 polls `/health` for 90 s on its own account. A fix that
  silently removes every wait in a script you did not write is not a fix unless
  you know what those waits were for.
- **A file's line endings are part of its contract with the interpreter on the
  OTHER machine.** The launcher shipped LF-only into a folder where
  `AB_RESTART_NODES.bat` is 68/68, `covenant_prod.bat` 135/135 and
  `AA_INTEGRATE_AND_RUN.bat` 30/30 CRLF — and it is built entirely out of
  `goto` labels, the one cmd construct read by byte offset. Check the encoding
  against **what already works there** (`tr -cd '\r' | wc -c` on the
  neighbours), not against what looks right in the sandbox.

The general rule, and it is cheap: **before shipping a script that invokes
another script, `cat` the whole call chain to its leaves and list every place
it (a) waits for a human, (b) refuses, or (c) exits early.** Each one is a
branch your caller inherits and cannot see. Here the chain was
`verify_deploy.py` → `AB_RESTART_NODES.bat` → `covenant_prod.bat`: the `pause`
is one level down, the Ollama abort that produced **P17** is two, and both were
twenty lines of reading away. M26 says a check derived from one
implementation's behaviour must be re-run against the replacement; this is the
same disease between *layers* rather than between implementations.

---

# 3. MUTABLE — Dead ends (do not repeat)

### DE1. `/unstake` cannot free the genesis mint. Blocked until 2027.
Genesis calls `staking_pool.stake(pubkey, 1000.0, 31536000)` at line ~7222 —
a **365-day** lock, where `STAKE_MIN_DURATION` is only 86400. `/unstake`
returns `HTTP 200 {"status":"success","payout":0.0}` with the real answer buried
in the prose: *"Stake still locked for 31535947 more seconds."*
So A1 cannot be unblocked this way. Do not retry it.
**Two separate findings here:** the year-long inert period, and the fact that
`/unstake` reports success for a no-op — a caller checking `status` is misled.
*(The second finding is FIXED as of v8.15 — see A1a in the run log.
The year-long lock still stands **for a node that mints its own genesis**.
NARROWED 2026-08-21 ~09:30: `load_canonical_genesis` — the path every node
in a shared-genesis deployment takes, including the founder's when started
with `--genesis` on a fresh db — credits the 1000 and never stakes it, so the
founder spends immediately. A1 is therefore NOT blocked; see A10 for the
divergence this reveals. Do not retry `/unstake`; do use the exported-genesis
path, as `test_multinode_live.py` already does.)*

### DE2. `update_trigger` cannot run from a scheduled (unattended) session.
Tried 2026-08-21 ~06:55: the MCP call needs interactive approval, which no one
is present to give. Step 5 of §1 ("fix the trigger prompt") therefore cannot
be completed by the loop itself. Workaround: write the proposed prompt to
`claude/TRIGGER_PROMPT_PROPOSED.md` and ask L to apply it (or approve it once
in an attended session). Do not spend another run retrying the call.

### DE3. Do not look for socket/thread/gossip behaviour in `sim1000_network.py`.
It stands up 1000 `Database` objects and applies blocks through
`apply_transaction_ledger` — no `P2PNode`, no sockets, no pools, no
`validate_block_shape`, no announce path. Against v8.21 it passes I1–I5
(0 findings, 373 s on 2 vCPUs) and that is all it can say: ledger
convergence. Anything about pools, preflight probes or heartbeats at scale
needs the in-process recipe in M12 or a real multi-process harness.

### DE4. Crypto.com MCP `get_candlestick` cannot deepen price history.
It returns at most the 50 most recent candles per instrument/timeframe
and takes no `since`/`start` parameter (checked 2026-08-22 ~06:10). It is
fine for "what is the price now" and for the last ~7 weeks of dailies;
for D1's 2025 history use Kraken OHLC through WebFetch as in M20.

### DE5. Kraken has no HBARUSD daily bars before 2025-07-10.
`since=1700000000` and `since=1735600000` both return 1752105600 as the
first row (checked twice, 2026-08-22 ~07:00) — the pair was listed then.
Kraken cannot deepen HBAR into H1 2025 or earlier; the 408-bar file is
everything Kraken holds. For pre-July-2025 HBAR (D6's corrupted series
covered a different window) another venue is needed — Crypto.com MCP is
50 bars only (DE4), so that is a new source to find, not a re-fetch.

---


---

### DE6. `device_bash` cannot run this system's suites. It is a THIRD local.
The `device_bash` bridge in an attended session runs in an isolated **Linux VM**
on L's machine with `~/covenant` mounted read/write at `$HOME/mnt/covenant`. It
is excellent for what it is good at — `sha256sum` on the deployed file, reading
`logs/watchdog.log` while it is being written, editing a file in place with a
`python3 -` heredoc, `py_compile`. It **cannot execute this system**:

```
python3 -c "import flask"   ->  ModuleNotFoundError: No module named 'flask'
```

and the `.venv` in `~/covenant` is a **Windows** venv, so it cannot supply one.
Any suite that does `import covenant_unified_v8` therefore cannot run there —
which is most of them. Pure-function suites (P14, and the judge-layer parts of
M13's class) do run, and that result is a **Linux** result: M29 still applies in
full, and saying "33/33" without saying "on Linux" would be the exact false
claim M29 exists to prevent.

M27 said there are two locals on this machine. There are three: the Windows host
(where the node runs), the cloud sandbox (where the loop runs), and this VM
(where the loop can *touch* the Windows filesystem). Do not confuse the third
for the first. Windows execution needs L, a scheduled task, or computer-use —
not `device_bash`.

### DE7. ~~Computer-use at "click" tier cannot launch a program.~~ **HALF WRONG — it launches intermittently and unpredictably. See the note at the end and M39, which was itself corrected.**
Granted File Explorer on 2026-08-24 (L said "do it"). The tier is **click**:
visible plus plain left-click, and explicitly *no typing, key presses,
right-click, modifier-clicks or drag-drop* — the address bar, Search box and Run
dialog all hand typed text to ShellExecute, so they are blocked on purpose.

`computer_double_click` on a `.bat` **worked once** and then did not: three
subsequent double-clicks on a correctly selected row left `NODE_RESTART.txt`'s
mtime untouched. One success is not a capability, and there is no fallback at
this tier — Enter is a key press.

So the honest statement of what this loop can do to the Windows host is: **read,
hash, edit in place, and deliver — never execute.** Windows execution needs L, or
a scheduled task created with the trigger tools. Do not write a plan whose
critical step is "click the launcher"; write one whose critical step is "L clicks
the launcher", and put the launcher one click from the Explorer sidebar
(Downloads works).

Corollary worth keeping: this is roughly the boundary §0 assumed *before* the
grant. Asking for the capability did not widen the loop's reach; it measured it.

**CORRECTED 08:21, and the correction is the useful part.** The above is wrong,
and wrong in the most ordinary way: **I generalised from a failure whose
precondition I never varied.** All three failures were double-clicks on a row
that was **already selected** — selected by the previous failed attempt. Both
successes were double-clicks on a row that was NOT selected, reached by
navigating to the folder fresh.

The recipe that works → **M39**: `computer_open_application` (brings a window to
the front), click the folder in the sidebar, then double-click the target
**without selecting it first**. Under it, `SWEEP_COVENANT_v8.35.bat` launched on
the first try and the sweep was running fifteen seconds later.

So the honest capability statement is neither of the two above: **this loop can
SOMETIMES start a Windows process** — 5 launches in 12 attempts, cause unknown
(see M39's second correction). It was enough to run the restart, the sweep and
the log copy, and it was not enough to be relied on: the last four attempts, on
the recipe that had just worked three times, did nothing at all.

Which makes §0's rule matter more, not less. It is a real capability, it is
unreliable, and it stays exactly where L put it — a per-session grant on one
app, at a tier that cannot type.

### DE8. Mycelium (or any microbial) electricity generation cannot power a data centre. The fuel is the wall, not the electrode.
Asked 2026-08-26 by L — *"mycellium electricty generation to lessen the need of
power for data centers"*. Priced before designing anything (M12: a scale
question is usually arithmetic), and the arithmetic is not close.

**Fungal mycelium specifically.** The state of the art is EMPA's 2025 3D-printed
fungal biobattery, and its own authors describe the output as *"enough to power
a temperature sensor for several days"* — no voltage, current or power figure is
published, which is itself the answer. A temperature sensor is ~100 µW. A 100 MW
data hall is **12 orders of magnitude** away. That is not a scaling problem, it
is a category error.

**Bacterial MFCs, at the record.** The 2024 *Nature Communications*
redox-mediated Shewanella flow cell reaches **13.1 mW/cm² = 131 W/m² of anode**,
about 10× state-of-the-art. At that figure 100 MW needs only ~76 hectares of
anode, which can be stacked — **and this is the number that makes the idea look
plausible and it is the wrong number.**

**The right number is fuel.** An MFC is not a generator, it is a converter: the
energy comes from organic carbon you must keep feeding it. Glucose is 15.57
MJ/kg (ΔH_c 2803 kJ/mol ÷ 180 g/mol). At a generous 30 % chemical→electrical:

```
   100 MW  ->  21.4 kg/s sugar  =  1,850 t/day  =  0.68 Mt/yr   (30 %, generous)
                42.8 kg/s        =  3,699 t/day  =  1.35 Mt/yr   (15 %, realistic)
```

World sugar production is ~180 Mt/yr, so **one 100 MW hall at 30 % eats ~0.4 % of
the global sugar crop.** Global data centres were ~415 TWh in 2024 (IEA, ~1.5 %
of world electricity, projected ~945 TWh by 2030). And anaerobic digestion + CHP
burns the *same* organic carbon at 35–40 % electrical efficiency, is
commercially deployed, and needs no electrode at all — so even where the biomass
exists, the microbial route is the worse converter.

**Do not spend a run on this.** Not on fungal batteries, not on soil/plant MFCs,
not on "scaling up" the EMPA cell. If cheap clean power for this system is ever
the question, the honest comparison is solar PV at ~25 W/m² annual average
against ~0 W/m² net for anything that has to be fed.

**What mycelium DOES offer, and it is not power — it is signalling.** Fungal
networks carry measurable millivolt spike trains, and that is *information* at
microwatt cost. It is also, precisely, the architecture this codebase already
runs on: `SpikingAnomalyMonitor`, `LinkConductance`'s Hebbian reinforce/attenuate,
lateral inhibition in `announce_block`, and Mahowald's address-event principle
that `announce_block`'s own docstring cites — **bandwidth proportional to
ACTIVITY, not to the size of the array.** That is the mycelial idea that pays,
and R1 is what it looks like when it is taken seriously: 40 bytes and 0.30 s of
airtime per announce. The saving is in not transmitting, not in growing a
battery.

**And the power lever in THIS system is measured and is somewhere else entirely
— see the B4 amendment below.**

---

# 4. MUTABLE — Backlog

## OPEN-ITEMS INDEX (added 2026-08-24 — M36)

Everything below this index that is struck through is CLOSED; its text is kept
because the measured numbers and the original wording live there. **Nothing is
removed — this index exists so a run can choose an item from thirty lines
instead of reading eight hundred and ninety.** Read the full entry for the one
item you pick.

| item | state | one line |
|---|---|---|
| A1c, A7, A8, A10, A16 | **L's decision** | genesis lock; block-size + PoW validity rules; which genesis state is canonical; on-chain staking (Option A recommended) |
| A12 residual | **L's decision** | may a real message be skipped to a suspect peer, or only heartbeats |
| **A24** | open, unblocked | a peer can evict every real anomaly record by sending garbage — ARCHITECTURAL, measured on v8.36 AND v8.37 |
| ~~A3 follow-on~~ | **CLOSED** v8.37 08-26 | and it was not small. A peer chooses the size of the `TX_REQUEST` we build (204,872 bytes from a 64-char honest maximum); an over-cap frame of our own making was transmitted 3× AND blamed on the peer (A23's own new edge); A5's relation bounds the payload, not the frame. 49/49, PRE-FIX 23/49. **Not yet run on win32** |
| B4 | **L's decision** | is the ethics verdict a consensus rule or an admission policy — B5's fix waits on it. **AND it is a WATTS decision (08-26): the judge is 45× the whole chain's memory and ~38× its proof-of-work, and B4 decides whether every node pays that or only the admitting one** |
| C1 | reviewed, needs hardware | 8 BLOCKER in the phone installers; fix with the device in hand |
| C2 | open | heartbeat/doctor gap detection is unit-tested only |
| C3, C4 | needs hardware | Tailscale peering; phone radio power. **One VpnService at a time — C3 and C5 cannot share a handset** |
| C5 | **L's move** | try the APK, answer `ANDROID_GUARD.md` README §7 |
| D3a | open, unblocked | `execute.py` and `paper_run.py` do not exist and must be written |
| D5, D6 | open, unblocked | L's real numbers into `MY_STRATEGY.md`; redo HBAR on the clean series |
| P2, P3, P9 | **L's decision** | 12 phantom suites in the runner; `covenant_prod.bat stop`; NTFS key ACL |
| P7 | needs one Windows run | instrumented 08-23; the measurement prints in the failing check's detail |
| P13 | **narrower than filed** 08-26 | the pre-A20 fixture is ON the PC (`PRE-v8.33.py` = v8.32, 0 A20 markers) and the suite already looks for it by that name — C1–C5 are runnable there and will run in the next Windows sweep. The gap is a FRESH SANDBOX, not everywhere |
| P14 | **CLOSED** 08-24 | the watchdog never checked its own source; `self_drift_report`, 33/33 (Linux only — DE6) |
| **DEPLOYMENT** | **half closed** 08-26 | **disk: DONE** — v8.37 `07e097f3e37f` 9846 lines, delivered over the bridge and `sha256sum -c` verified ON the machine 08-26 19:20, with a3s/a23/runner/verifier/launcher; v8.35 kept as `covenant_unified_v8.PRE-v8.37.py`. **running: OPEN** — both nodes still `v8.35 1207bd2e7dc5`, and the WATCHDOG process is `c228ac0a629d` against `d363d6c2bb5f` on disk and has been alerting about itself since 08-24. One double-click: `covenant\AM_VERIFY_AND_RESTART.bat` |
| **P17** | open, unblocked | a restart can take the chain down and LEAVE it down — `AB_RESTART_NODES.bat` stops the nodes, then `covenant_prod.bat` refuses to start them if Ollama is not answering. Gated in `verify_deploy.py`; the bare double-click is still exposed |
| A23 | **CLOSED** v8.36 08-26 | the A18 path DID fire; `_note_send_ok` on `sendall()` cleared the counter it set. Accepting-silent peers never escalated (k=1 for ever) while refused ones reached k=5; a non-JSON reply was swallowed silently. 24/24, PRE-FIX 16/24. **Not yet run on win32** |
| P7 | **CLOSED** 08-24 | measured on Windows; the standing hypothesis is false and the real finding is A23 |
| P9 | **worse than filed** | NTFS breaks every owner-only check: `authorize_mainnet_payment` refuses on this machine, always |
| P15 | open, unblocked | the FOURTH long-lived process — ollama — is the ethics judge and nothing reports its identity |
| P16 | **CLOSED** 08-24 | the log could not distinguish "quiet because healthy" from "quiet because dead" — the watchdog died and its last line says all is well |
| **SEM1** | **CLOSED** 08-24 | the cross-register eval's null was uniform-random; against a spelling-only baseline the space loses 7×, against a permuted-anchor null it wins 80× and holds on non-cognates. Per-language spread at n=33 was noise; frequency governs |
| **R1** | **increment 1 DONE** 08-26; rest open | **LoRa as a bearer for the mycelium — ADDITIVE (L: "integration not removal").** The codec is shipped: `covenant_lora_frame.py` + `test_r1_lora_frame.py`, **58/58 ×2**, a new file importing nothing from the node. Announce **148 B → 40 B**, which fits EU868 SF12 (51 B), the worst legal case; heartbeat+digest 268 → 55 B. A block is still 17.4 h of airtime and always will be. Remaining: three collisions with shipped controls, **A23 first**, and L's hardware / stack / goal answers |
| SEM2 | open, unblocked | the supervision curve has not flattened at 3.3k anchors — 10k anchors / 10M tokens is a falsifiable prediction, not a guess |
| SEM3 | open, small | `SEMANTIC_CORE_PROBE`'s contrast-axis test C has **n=3** and no null — M39 in a different costume; redo it at the n the retrieval eval now runs at |
| ~~**WINDOWS SWEEP**~~ | **DONE** 08-24 | **961/964 in 12.2 min** on the deployed `1207bd2e7dc5`. 3 reds, 2 root causes: P9 (×2) and A23. `test_w2_sandbox_platform` is in `run_all_tests.sh` but NOT in `run_local_sweep.py` — that suite was not covered |

## A. LEDGER & PROPAGATION

~~**A1. Prove block propagation survives a node kill**~~ **DONE v8.20**
(2026-08-21 ~10:30) — `test_a1_kill_matrix.py`, 29/29 ×2, wired into
`run_all_tests.sh`. Bridge dead during the mine (K1), miner SIGKILLed the
second `/mine` returns (K2), leaf dead mid-flight (K3), db survives every
kill (K4), periodic tip gossip to an idle peer (K5). **K2 failed 3/3 on
v8.19**: the restarted miner was *ahead*, bootstrapped nothing, announced
nothing, and B and C sat at genesis for the whole window — on a quiet chain,
indefinitely. Fixed: `_gossip_tip()` — push-on-boot after `bootstrap_chain`,
plus a `_tip_gossip_loop` every `TIP_GOSSIP_INTERVAL_S` (120 s default,
`COVENANT_TIP_GOSSIP_INTERVAL`, 0 = boot-push only). ~150 bytes per peer per
interval; peers that hold the tip inhibit. History kept below.
*Was:* **UNBLOCKED 2026-08-21 ~09:30**
*Correction:* the "blocked until 2027" claim held only for a self-minted
node. On the shared-genesis path (`--export-genesis` then `--genesis`, which
is the real deployment story and what `test_multinode_live.py` does) the
founder's 1000 is spendable at once, real blocks mint, and they propagate —
21/21 live after v8.19. **Remaining for A1 proper:** the kill-during-
propagation matrix: mine on A, kill B (the only bridge to C) before relay,
restart B, assert C converges; and kill the miner after `/mine` returns but
before peers ack. Cheap now; do it with `test_a9_relay_race.py`'s `Net`
class. Replication and restart are proven (3 nodes, shared genesis, kill,
unattended rejoin — PASS).
Ways forward, in preference order:
- ~~**A1a.** Fix `/unstake` to return an error status when payout is zero.~~
  **DONE v8.15** (2026-08-21). `/claim_rewards` had the same bug, fixed too.
- **A1c. (now preferred over A1b)** Decide with L whether the 365-day lock is
  intended. It has the shape of a founder-commitment mechanism, but the effect
  is a chain inert until 2027. **L: is the year-long genesis lock deliberate?**
- **A1b.** Test-only genesis lock override (env var, defaulting to current
  behaviour). **Section-0 tension flagged 2026-08-21:** the lock may itself be
  a security/commitment control, and "env var so the test can run" is exactly
  the shape of "weaken a control to make a test pass". Not implemented for that
  reason; needs L's explicit say-so (which A1c would provide either way).

~~**A2. Make the port footguns impossible rather than documented.**~~
**DONE v8.15** (2026-08-21) — `preflight_port_check`. Verified live:
`test_a1a_a2.py`, 15/15, re-verified this run against the v8.16 source.
**TIGHTENED v8.29 (2026-08-22), because W1 silently disarmed half of it.** The
HTTP-vs-P2P discriminator read an EMPTY reply as proof of a P2P listener. That
was measured against werkzeug (which answers an unterminated request line with
an HTTP/0.9 HTML body); waitress answers nothing at all, so with a production
WSGI server in front, `--peers` pointed at a Flask API port passed preflight and
both nodes reported healthy while neither heard the other. Now: when the first
probe is silent, a second probe sends a well-formed `GET / HTTP/1.0` and any
status line is fatal. Detection only — nothing that booted correctly stops
booting. Caught by `test_a1a_a2` A2-2 on the first sweep after the swap (it hung
and leaked a node), which is why the outcome-style assertion was worth having.
→ M26.

~~**A3. Audit remaining network paths for unbounded reads.**~~
**DONE v8.16** (2026-08-21) — see run log. The prior "done" claim was false;
this run actually implemented `recv_bounded` + `MAX_PEER_MSG_BYTES` (64 MB
default, env-overridable) and applied it to **all five** read sites:
`_handle_peer`, `_handle_bridge`, the catch-up reply reader, the tx-fetch
reader, and the ACK reader. Flood-tested live: `test_a3_bounded_reads.py`,
7/7, run twice. No other socket read-until-EOF loops remain (the only other
`while True:` sites are the PoW nonce search and the main run loop).
~~**Follow-on, small:** the *send* side (`_send_raw`, catch-up REQUEST) is not
size-bounded, but those are outbound and self-limited by what this node builds;
lower priority than A4/A5.~~ **DONE v8.37 (2026-08-26) — and every clause of
that sentence was wrong, which is why it sat unexamined for five days: it read
as a reason not to look.**

**"Self-limited by what this node builds" — false for one field.** A
`TX_ANNOUNCE` carries a `tx_id` chosen by the SENDER, and
`_fetch_announced_tx` echoes it verbatim into the `TX_REQUEST` it builds.
Measured on pristine v8.36: a **204,893-byte** announcement (all of it
`tx_id`, comfortably under the read cap) made the node build and transmit a
**204,872-byte** request. A real transaction id is
`hashlib.sha256(...).hexdigest()` — **64 characters** — so the honest maximum
was exceeded ~3,200× by a peer simply saying so. The cost is entirely ours:
two copies of the string per fetch, a database lookup keyed on the whole
thing, a linear mempool scan comparing it, and one of
`MAX_CONCURRENT_FETCHES` (32) workers held across a round trip. At the 64 MiB
default that is ~4 GiB of frames **this node builds on request**, and the pool
it exhausts is the one `bootstrap_chain` and gap-fill need (A14).

**"Size-bounded" — never checked against the receiver's cap.** Measured on
v8.36: `_send_raw` transmits an over-cap frame anyway (3 attempts, 897 KB), the
peer's `recv_bounded` raises `PeerMessageTooLarge` and closes without a reply,
and A23 (v8.36, the run before this one) reads "no parsed reply" as
non-delivery and calls `_note_send_failed`. **So an oversized frame of our own
making escalates the heartbeat backoff against a peer that behaved perfectly**
— k=1 after one send, k=5 and 16× after five. A23 was right to make that rule;
it just needed this. M33 exactly: audit the surface you widened.

**And the frame is not the payload.** A5's import assertion
(`MAX_TX < MAX_BLOCK <= CATCHUP_BUDGET < MAX_PEER_MSG`) bounds what travels;
the receiver's cap applies to what arrives, which is payload **plus envelope**
— measured with the real serializer at 129 bytes (BLOCK_PROPAGATE), 181
(TRANSACTION_PROPAGATE), 62 (a catch-up reply). At the defaults there is 8×
headroom so nothing is live, but `MAX_BLOCK_BYTES` may legally be set to
`MAX_PEER_MSG_BYTES - 1`, at which point this node mines blocks no peer can
read — the A5 exile bug wearing an envelope.

**Fix v8.37 `07e097f3e37f` (grep `v8.37`), tightening only.** One rule: *this
node never transmits a frame it knows the receiver must refuse, and never
blames a peer for one.* Three pure, total helpers (`frame_fits`,
`usable_tx_id`, `sane_index`); guards in `_send_raw`, `request_missing_blocks`
and `_fetch_announced_tx`, which record **`outbound_message_too_large`** and
deliberately do **not** call `_note_send_failed` — the peer never saw it;
`tx_id` bounded at both ingest sites (`peer_tx_id_invalid`), by LENGTH only
and not "must be hex", because a format assertion on a field a future build
might widen is the A5 liveness bug in mirror; index shape checked on
`BLOCK_ANNOUNCE`/`BLOCK_REQUEST` (`peer_index_invalid`); and
`FRAME_ENVELOPE_BYTES` extends A5's relation to the frame, asserted at import.
No verdict, route, bound or refusal was relaxed.

**`claude/test_a3s_send_bounds.py` 49/49 ×2; PRE-FIX RECORD 23/49 on pristine
v8.36** — the 23 are the record of what was already right, and the 26 that
fail carry the measurements above. §S8 pins the rule on the tokenized source
so it cannot be undone quietly. Liveness is asserted throughout, deliberately:
an honest 64-char announcement is still fetched (S4e/S4f), an honest novel
index still triggers a request (S5e/S5f), an honest `BLOCK_REQUEST` still
returns its page (S6c), and a block at the payload bound still travels (S7).

**Residual, recorded honestly.** (a) **Linux only** — M29 applies in full;
this has not run on win32. (b) An arbitrary-precision integer is still parsed
by `json.loads` before `sane_index` can see it. CPython ≥ 3.11 caps int↔str
conversion at 4,300 digits and raises, so the sandbox and the PC `.venv`
(3.12) are covered; the `device_bash` VM is **3.10**, where there is no such
cap and the conversion is O(n²). Bounding that needs a custom decoder, which
is a bigger change than this item; it is named rather than silently left.
(c) The `index` guard is NOT a send-side bound — see M42; the first draft of
its comment said it was.

~~**A4. Widen the adversarial suite.**~~ **DONE v8.18** (2026-08-21) —
`test_a4_block_injection.py`, 60 live checks against the real P2P listener,
60/60 ×2, wired into `run_all_tests.sh`. Found and fixed: float index accepted;
`stake_rewards=inf` accepted; empty block accepted; forged `stake_rewards` /
`alignment_score` accepted; stake rewards distributed on the miner only
(consensus split); invalid block at the tip reported as `ok:true duplicate`.
See run log. Original wording kept below for the record.
*Was:* 21/21 passing but thin. Add malformed block
shapes, replay, fork/rival-genesis injection, oversized and truncated messages,
NaN/Inf amounts, forged signatures. The patch log records blocks that *were*
accepted when they should not have been — that class is the target.
**Partly addressed 06:05 run:** `test_a1a_a2.py` (route semantics) and
`test_a3_bounded_reads.py` (bounded reads) are now **wired into
`run_all_tests.sh`** under a new "ROUTE SEMANTICS + BOUNDED READS" section, so a
future edit reverting `status:error` no-ops or the read caps fails the sweep.
Remaining A4 work: the malformed/forged/rival-genesis block-injection matrix.

~~**A5. Confirm the 64 MB cap is never hit by a legitimate catch-up.**~~
**DONE v8.17** (2026-08-21) — and the answer was **no, it was hit, 7× over**.
See run log and M7. Fixed with coherent bounds (`MAX_TX_BYTES` 16 KiB,
`MAX_BLOCK_BYTES` = cap/8 = 8 MiB, `CATCHUP_REPLY_BUDGET_BYTES` = ¾ cap,
`MAX_HTTP_BODY_BYTES` 4 MiB), byte-paged BLOCK_REQUEST replies, byte-packed
mining, and a 413 on oversized HTTP bodies. `test_a5_size_coherence.py`
20/20 ×3, wired into `run_all_tests.sh`.
**Not done from the original A5 wording:** the `sim1000_network.py` throughput
/ thread regression and "preflight probe at scale" — split out as **A6** so it
is not lost behind this strike-through.

~~**A6. 1000-node scale regression**~~ **DONE/CORRECTED v8.21** (2026-08-21
~11:45). `sim1000_network.py` vs v8.21: I1–I5 pass, 0 findings, 373 s — but
it is a ledger-only sim (DE3), so the rest of this item was answered
directly: `validate_block_shape` on a 4.85 MiB / 5000-tx block costs 60 ms
(`serialized_size` 34 ms of it) — once per accepted block, negligible; the
preflight `{}` probe is one short connection per peer at boot only, and a
real P2P listener answers a non-JSON frame with `peer_message_error` and a
close, so at scale it is N·degree anomaly records once per boot, not a load.
Thread behaviour under A3/A5 is unchanged by construction (same three
bounded pools). *Original wording:* via `sim1000_network.py` against v8.20
(now also A11's periodic gossip). *Original wording:* against v8.17:
throughput and thread behaviour after A3 (bounded reads) and A5 (per-block
`serialized_size` in `validate_block_shape` adds one json.dumps per accepted
block — ~7 MiB worst case, measure it); and confirm the preflight `{}` probe at
boot does not disturb peers at scale. Lower priority than the A4 block-injection
matrix because A5's finding shows the *correctness* gaps are still where the
value is.

**A7. Consensus note for L (decision, not code).** v8.17 makes "block
serialized ≤ MAX_BLOCK_BYTES" a **validity rule**: an older node could mint a
block a v8.17 node refuses. All current nodes are L's and the chain is at
genesis, so this is free today; once anyone else runs a node it becomes a
protocol-version question. Record it in `HANDOFF.md` when the chain is live.
**v8.18 adds three more rules of the same kind** (all things `/mine` already
produces, so honest miners are unaffected): non-empty transactions;
`stake_rewards == fsum(amount)*0.01`; `alignment_score == mean(benefit_score)`;
plus int-typed `index`/`nonce` and finite header scores as *shape*.

**A8. Two open validity questions for L, found by A4 (decision, not code).**
- **No timestamp rule.** A block stamped ten years in the future is accepted
  (A4.17, observed, not asserted). Nothing reads block timestamps for
  consensus today, so it is cosmetic until something does (e.g. a stake-lock
  or heartbeat that consults block time). Decide whether to bound it
  (e.g. ≤ now + 2h, ≥ parent) before that happens.
- **Registration PoW is not re-checked on the block path.** `/transactions`
  and `_ingest_peer_transaction` require `RegistrationPoW.verify` per sender;
  `_accept_block_common` does not, so a block mined by a peer can carry
  transactions from senders that never paid the registration cost. If the PoW
  is a per-node admission policy, that is fine; if it is meant as a sybil cost
  on the chain itself, it needs to be a block rule. **L: which is it?**

~~**A11. Periodic gossip at scale.**~~ **DONE v8.21** (2026-08-21 ~11:45) —
and it was not free. Measured with the real classes: the heartbeat's
`announce_inhibited` + `attenuate` on every receipt drove **every link's
conductance to MIN within 31 rounds (~62 min) on a quiet chain**, erasing
what `LinkConductance` learns, and raised a **false `anomaly spike` on
/health for ~5 min after any synchronized restart with ≥ 5 peers** (L's
2-peer nodes were safe). Fixed: heartbeats carry `gossip: true`; a
receiver that holds the tip counts `tip_gossip_seen` (on /health) and does
nothing else; a receiver that is behind fetches exactly as before; untagged
duplicates are still recorded and attenuated. `test_a11_gossip_scale.py`
23/23 ×2, in `run_all_tests.sh`. Receive-pool: the reply goes out before
any fetch, so a heartbeat holds a slot for ~0.25 ms. Original wording kept:
v8.20's `_tip_gossip_loop` adds one
`BLOCK_ANNOUNCE` per peer per 120 s per node and one `announce_inhibited`
anomaly record per redundant receipt. Fine at 3 nodes; at N=1000 with a
scale-free overlay it is a steady ~N·degree/120 events/s — measure it in
A6's `sim1000_network.py` run (it is the same run) and confirm the spike
detector treats it as baseline, not as a spike, and that the receive pool is
not held. If it costs, lengthen the interval or jitter it; do not remove
the boot push.

~~**A12. Heartbeats to dead peers can saturate the send pool.**~~ **DONE
v8.23** (2026-08-21 ~23:30) — measured, and the nearer hazard was not the
one the item named. One message to a black-holed host costs 15.13 s of a
pool worker (3 × 5 s + backoff sleeps); saturation by heartbeats alone is at
D ≥ 508 dead peers (not 512) — but **head-of-line blocking starts at D ≥ 64**:
ties in delivery order fall to insertion order and a dead peer sits at
baseline conductance forever, so a live peer listed after a generation of
dead ones waited a full timeout generation for a *novel* block. Scaled to
4 workers / 8 dead / 0.5 s: boot push to the live peer 1.63 s late, every
heartbeat 3.27 s late, real announce 3.27 s late, 32 sends still queued
after a 6-round burst. Fixed with `PeerHealth` (fed only by this node's own
send outcomes; inbound never resets it — a CGNAT phone that can reach us
but not vice versa would otherwise re-arm the cost): answering peers are
ordered first, never-contacted next, failing last (ordering only, nothing
dropped); after `PEER_SUSPECT_AFTER` (3) consecutive failures a peer gets
one attempt per real message and periodic heartbeats skip it until a
backoff (`PEER_BACKOFF_BASE_S` 120 doubling to `PEER_BACKOFF_MAX_S` 900)
expires, at which point the heartbeat is the probe; any success resets.
Periodic heartbeats use one attempt (the next heartbeat is the retry); the
boot push keeps three and, because `bootstrap_chain`'s catch-up request now
feeds the table, goes to the peers that answered first. `/health` reports
`peers_suspect` + a warning; GET `/peers` carries the table. Steady-state
saturation moves 508 → 11,520 dead peers. `test_a12_dead_peers.py` 41/41
×3 (4/24 on v8.22), in `run_all_tests.sh`. **Residual, for L:** real
messages to a suspect peer still cost one 5 s timeout each, so a node with
≥ 64 *dropped* (not refused) peers still blocks back-to-back bursts for up
to 5 s; the full failure-detector (skip real messages too, rely on the
probe + gap-fill) is a policy choice — a revived peer would catch up on its
next probe (≤ 3 intervals + 15 min) instead of instantly. Not done without
L's say-so. *Original wording:* arithmetic, not yet observed; fix shape:
skip heartbeats after K failures, never drop the boot push.

~~**A13. One-way reachability never syncs**~~ **DONE v8.25** (2026-08-22
~03:00) — `P2PNode._send_announce` wraps `_send_raw` for every
BLOCK_ANNOUNCE and reads the reply's `height`; a real int strictly above
ours counts `peer_ahead_seen` (on `/health`), records `peer_ahead`, and —
gated by `catchup_allowed()` — submits the master's `_pull_from_peer_ahead`
to `_FETCH_POOL` (never inline on the send pool), which is
`request_missing_blocks` + `_apply_fetched_blocks` (one gate, A9 relay
onward, source excluded). One page (64 blocks) per heartbeat; a bigger gap
closes over successive heartbeats. Lying/garbage heights: bool/float/str/
None/≤ ours ignored; a liar costs one BLOCK_REQUEST per cooldown and
`peer_ahead_empty`. `test_a13_one_way_sync.py` 25/25 ×3 (T2 FAILS on
v8.24: X stays at 2 beside a reachable peer at 4), in `run_all_tests.sh`.
Built on the project's `_delivery_order` line (`ec267d40` → `acaca10a`);
the edit is additive (grep `A13`) and re-applies by hand on `PeerHealth`.
*Original wording:* If X
can reach us but we cannot reach X (X behind CGNAT with us port-forwarded,
or us on a VPS and X at home), X learns nothing we mint: our announces to X
fail, and X's own heartbeats to us are answered `known` with OUR height in
the reply — which `_send_raw` returns and `announce_block` discards. Fix
shape, small: in `_dispatch`'s heartbeat path, if a reply's `height` exceeds
ours, submit one `request_missing_blocks` to that peer on `_FETCH_POOL`
(never inline in the send pool — the file's own deadlock note), gated by
`catchup_allowed()` so a lying peer can only make us ask once per cooldown.
Not L's current topology (same-wifi LAN or Tailscale are symmetric); real
for the VPS option in `NODE_DEPLOYMENT_FINDINGS.md` §5. Test in-process:
fake peer replies `{"outcome":"known","height":9}`.

~~**A14. Boot-time catch-up is sequential over peers.**~~ **DONE v8.26**
(2026-08-22 ~04:15) — and the nearer hazard was unbounded *time*, not the
sequential order: a peer that accepts the BLOCK_REQUEST and trickles bytes
held `bootstrap_chain` — and `/sync` — **indefinitely** on v8.25 (the A3
cap bounds bytes, the socket timeout bounds each recv, nothing bounded the
exchange). New `_bootstrap_round`: every peer asked at once on
`_FETCH_POOL` (N dead peers cost ⌈N/32⌉ × timeout, not N × timeout), waits
at most `BOOT_PROBE_DEADLINE_S` (`COVENANT_BOOT_PROBE_DEADLINE`, default
2 × timeout + 1, asserted ≥ one timeout at import), applies replies in
arrival order through the unchanged `_apply_fetched_blocks` gate, skips
already-held indexes before the gate (no spurious `block_already_held`
from the second answering peer), records `bootstrap_probe_timeout` for
stragglers. Measured at 0.5 s with 8 blackholes ahead of the live peer:
bootstrap 9.0 s → 2.0 s (two rounds + pause), `/sync` 4.0 s → 0.5 s, boot
push 5.5 s → 2.0 s after start; wedged peer: forever → 2.0 s.
`test_a14_boot_probe.py` 15/15 ×3 (pre-fix record 13/13 on v8.25), in
`run_all_tests.sh`. `PeerHealth.rank` ordering not used (table is not
persisted; arrival order makes it unnecessary). *Original wording:*
`bootstrap_chain` calls `request_missing_blocks` peer by peer: 5 s per
dropped peer per round before the boot push goes out (measured 4.0 s for 8
peers at 0.5 s), and `/sync` has the same shape inside an HTTP request.

~~**A15. Every other read-until-EOF site is unbounded in TIME.**~~ **DONE
v8.27** (2026-08-22 ~05:30) — and the inbound side was worse than written:
accepted sockets had **no timeout at all**, so an idle connection (no
trickle) pinned a `_RECV_POOL` worker for ever, unrecorded; 96 idle TCP
connections from one host = a node deaf to every peer while `/health`
stays green (measured with 4 handlers: honest `BLOCK_REQUEST` never
answered, anomalies `{}`). Fixed inside `recv_bounded` alone:
`max_seconds` (default `MAX_EXCHANGE_S`, env `COVENANT_MAX_EXCHANGE_S`,
60 s, refused at import below `PEER_SEND_TIMEOUT_S`), each recv under
`min(own timeout, remaining)`, `PeerMessageTooSlow` when the budget is
spent, the socket's own `socket.timeout` re-raised unchanged when that is
what fired. Handlers record `peer_message_too_slow` /
`bridge_message_too_slow`. Honest maximum (M7): one 48 MiB catch-up page
fits 60 s on any link ≥ 6.7 Mbit/s (asserted from the constants, L5).
`test_a15_exchange_deadline.py` 14/14 ×3 (11/11 PRE-FIX RECORD on v8.26),
in `run_all_tests.sh`. Residual: a deliberate attacker can still hold 96
workers for 60 s at a time by reconnecting — bounded, recorded, and
rate-limitable by kind now; a per-source connection cap would be the next
tightening if it is ever observed. *Original wording:* Found by
A14's `Trickler`: `_send_raw`'s reply read (send pool), `request_missing_
blocks` when called from `_fetch_announced` / `_pull_from_peer_ahead`
(fetch pool), the tx-fetch reader, `_handle_peer` / `_handle_bridge`
(receive pool) — each bounds bytes (A3) and per-recv time, not the
exchange. A peer dripping one byte per 0.2 s pins one worker per
connection for as long as it likes: 32 such connections exhaust
`_FETCH_POOL` (no gap-fill at all), 64 exhaust the send pool. Fix shape:
a wall-clock budget inside `recv_bounded` (`deadline = monotonic() +
MAX_EXCHANGE_S`, raise `PeerMessageTooSlow`, recorded like
`PeerMessageTooLarge`), one constant, asserted ≥ the socket timeout. Same
tightening-only class as A3/A5; the honest maximum is one `MAX_PEER_MSG_
BYTES` reply on a slow link — measure it (M7) before picking the number.
Unblocked, additive, testable with `Trickler` + the socketpair recipe (M12).

~~**A9. Stake-state convergence test across real processes.**~~ **DONE
v8.19** (2026-08-21 ~09:30) — and it found the relay gap instead: a block
that enters a node by startup bootstrap (or any path that wins the delivery
race) was never relayed; C stranded until the next block. Fixed:
`_apply_fetched_blocks` announces what it applied (excluding the source),
`_fetch_announced` forwards the event when the block arrived by another path,
and a lost race is named `block_already_held` instead of
`block_rejected_persist`. `test_a9_relay_race.py` 18/18 ×2;
`test_multinode_live.py` 21/21 ×2 (was 19/21 ×2). `/stakes` agrees across
nodes — trivially, because on a loaded genesis it is **empty on every node**
(see A10). Original wording kept: v8.18 now
distributes stake rewards on peers. `test_multinode_live.py` should assert
that `/stake_info` (or equivalent) agrees on every node after a value block
propagates — the miner-only split went unnoticed because nothing compared
stake tables across nodes. Small; do with the next multi-node run.

**A10. The two genesis paths produce different state — decision for L,
then one small code change.** Found by the first run of
`test_multinode_live.py`. `add_genesis_block` (self-mint) records the 1000
mint **and** `staking_pool.stake(pubkey, 1000, 365 days)`: founder balance
0, stake 1000. `load_canonical_genesis` (every `--genesis` node) records the
mint only: founder balance 1000, stake table empty. Same block hash, two
different ledgers. Consequences today: (a) the 365-day commitment lock
exists only on the exporter's own db, and vanishes if the founder starts
with `--genesis` on a fresh db — so it is not a control anyone can rely on;
(b) if the self-minted node keeps running alongside `--genesis` nodes, it
will refuse every block that spends the founder's 1000 (`block_rejected_
overdraft`) while the others accept — a fork between the two camps;
(c) with an empty stake table `distribute_block_rewards` on the `--genesis`
nodes credits nobody, so the 1% per block is minted on the self-minted node
only. **Not changed this run**: making the importer apply the lock is
"tightening" but makes the only working propagation path dead for a year;
removing the lock from the self-mint path weakens a control without L's
say-so (Section 0). **L: which state is canonical — locked or spendable?**
Whichever it is, the fix is to make both paths produce it (one line either
way) and `test_a9_relay_race.py` S3 should then assert a non-empty,
identical stake table. Supersedes A1c/A1b as the question to answer.
*(06:45: A16 below subsumes the mechanism half of this — with on-chain
staking both genesis paths produce one state by construction; only the
locked-vs-spendable choice stays with L.)*

**A16. Staking is node-local, so yield diverges across nodes — DECISION FOR
L (Option A recommended), then ~two runs of code.** Opened 2026-08-22
~06:45 on L's instruction "refine entire system repeatedly until confident
in yield to help with propagation". Measured on the shipped v8.27 with
`claude/test_y1_stake_divergence.py` (10/10 ×2, in-process, real classes,
shared exported genesis): a stake placed on node A debits A's ledger only;
the next honest spend B mines is refused by A as `block_rejected_overdraft`
(A one block behind for ever); a non-overdrawing block both accept pays the
1 % reward to the staker on A and to nobody on B (supply differs by the
reward); `/stakes` disagree the moment anyone stakes (A9-S3's agreement was
two empty tables); after the lock, A's unstake credit is spendable on A and
an overdraft on B — the fork runs both ways. Also from the constants: with
no fee, a sole staker cycling its balance mints 1 % of volume per block to
itself (+100 % supply in ~200 blocks). The yield *arithmetic* is sound:
`sim_yield_safety.py`, run against v8.27 for the first time, shows 0.0 %
over-issue at 1…5 000 blocks and bounded time yield (its own prose still
says "runaway" — stale, predates the AK fix). Full write-up and the two
options in `claude/YIELD_ON_CHAIN_DESIGN.md`: **A** = stake/unstake become
net-zero ledger events against a `STAKING_ESCROW` account with a
node-recomputed reward mint verified like the v8.18 `stake_rewards` rule
(closes A10's mechanism half and needs A8's timestamp rule); **B** = keep
node-local and document that yield does not travel. Section 0: a consensus
change is L's call; the source (patch log AC) and `HANDOFF.md` §4 say the
same. **No node source changed.** If L says A, the next run implements the
event plumbing with Y1 as the pre-fix record, then the genesis
unification, full sweep each time.

~~**A17. One-way peering never syncs (the phone/VPN shape).**~~ **DONE
v8.28** (2026-08-22 ~08:00) — found while checking L's "node we can sync
with over a VPN for Android": two real processes on the host's interface
IP, B lists A, A lists nobody (the phone-to-PC / Tailscale day-one
config). A mined block 2; **B stayed at genesis for ever on v8.27** — A
announces to an empty list, B's bootstrap ran when both were at 1, and
`_gossip_tip` said nothing at height 1 (A1/K5: "nothing worth saying"),
so A13's reply-height probe never fired. Fix: `_gossip_tip` announces the
tip even at genesis (one method, `tip = chain[-1] if chain else None`);
the peer answers `known` + height (A11 path, no attenuation), A13 pulls.
`test_a17_oneway_peer_sync.py` 6/6 ×3 (B converges in 2–3 s at a 3 s
interval; pre-fix record 4/4 on pristine v8.27 with B=1 at 15 s), K5 in
`test_a1_kill_matrix.py` updated (30/30), in `run_all_tests.sh`. Full
sweep green on v8.28 (multinode 21/21 ×2 alone after a load timeout in
an 8-wide batch). Cost: one ~150-byte frame per peer per
`TIP_GOSSIP_INTERVAL_S` from nodes at genesis; a rival-genesis peer now
fetches and refuses our block 0 once per interval — visible, not silent.
Runbook for the phone: `claude/ANDROID_VPN_SYNC.md` (PC side verified;
phone side waits for the hardware — C1/C3).

~~**A23. A18's bytes-accepted-never-ACKed path has never fired on Windows.**~~
**DONE v8.36 (2026-08-26) — and this entry named the wrong culprit.**

The entry below concludes *"the fix is in the source and is not being reached"*
and nominates `return verdict` / `return None` as the branch stealing the exit.
Measured in-process against a listener that accepts the bytes and never answers
— the Windows shape, reproducible on any platform — **the A18 path is reached,
on the first send**: `peer_send_failure` recorded, `_note_send_failed` called,
`dead_peers` 0 → 1.

What was broken is three lines **above** it. `_note_send_ok(host, port)` ran
immediately after `sendall()`, on the strength of the socket alone — the exact
claim A18's own comment denies — and `_note_send_ok` CLEARS the link's
consecutive-failure count. So `_send_raw` recorded a failure it could not
confirm and erased the previous one, once per attempt, three times per send:

```
                     k after 5 consecutive total failures   backoff
accepting-silent     v8.35: 1 1 1 1 1                        10s (base, for ever)
refused (Linux)      v8.35: 1 2 3 4 5                        16x base
accepting-silent     v8.36: 1 2 3 4 5                        16x base
```

**The peer delivering nothing was accounted healthier than the peer that says
so out loud**, and A12's whole headroom (508 → 11,520 dead peers) is bought by
that escalation — so for this class of dead peer A12 bought nothing.

Second defect, same function: a reply that is **not JSON** returned `None` in
silence — no anomaly, no health update, link left at full conductance. A
covenant listener answers JSON or nothing (M4), so bytes that are neither prove
the far end is not a peer: an HTTP server (the A2 footgun, which preflight only
checks at BOOT), a proxy, or a port another process took. Now
`peer_ack_unparseable` + a failure, not retried.

**Fix (v8.36, grep `A23`):** `_note_send_ok` moved to the parsed-reply path,
which is the first evidence of delivery `_send_raw` ever gets; unparseable ACK
recorded and counted; nothing else touched. Tightening only — no verdict, no
route, no bound and no refusal changed; `_note_peer_contact` (an INBOUND frame
clears the backoff) is deliberately unchanged, so a peer that comes back is
still heard within one tick. Escalation gates **periodic heartbeats only** —
the boot push and every novel/tx announce still go to every peer (asserted by
`test_a12` and re-run here).

**`claude/test_a23_ack_health.py` 24/24 ×2; PRE-FIX RECORD 16/24 on pristine
v8.35** — the 16 that pass are the record of what was already right. §S6 pins
the rule in the source (no `_note_send_ok` before the ACK read; exactly three
failure sites), so "restoring the reachability signal" fails a check.

**Residual, recorded honestly.** (a) This has NOT run on win32; M29 applies in
full and the K1/K3 red is not claimed fixed. (b) S3 measures why that red is
platform-shaped and the answer is partly a MEASUREMENT bug in the test, not the
node: a broadcast is `_SEND_POOL.submit`, and one send to an accepting-silent
peer costs ~15.1 s at the defaults against ~0.13 s for a refused one, so K1/K3
sample `/anomalies` ~15 s too early on the platform where the peer accepts.
Fixing that means making K1/K3 WAIT for the send path, which is a change to the
test's timing and not to what it asserts — left for the run that can watch it
happen on the machine. (c) A peer legitimately silent — `crisis_mode`, a
duplicate nonce on a retry — now escalates its heartbeat backoff where before it
did not; any inbound frame clears it, which is A12's designed recovery, but it
is a real behaviour change and it is stated here rather than discovered later.

Original wording follows.

**A23 (as originally filed).** Opened 2026-08-24 by the first Windows sweep, with
the measurement in hand rather than a hypothesis.

K1/K3 in `test_a1_kill_matrix` kill node B, mine on A, and assert *"A recorded
the failed delivery, not silence"*. On win32 they fail, and P7's instrumentation
now says why it is **not** what everyone assumed:

```
P7 MEASUREMENT [after kill, before mine] A: dead_peers=0 heartbeats_skipped=0 peers=1 kinds=['peer_message_error']
P7 MEASUREMENT [after mine]              A: dead_peers=0 heartbeats_skipped=0 peers=1 kinds=['peer_message_error']
```

- **`heartbeats_skipped=0`** — A12's backoff never suppressed the send. The
  standing hypothesis ("the broadcast skipped a peer already marked suspect, so
  the node is correct and only the record is missing") is **false**.
- **`dead_peers=0`** — and this is the load-bearing one. *Both*
  `peer_send_failure` sites in `_broadcast`/`_send_raw` call
  `_note_send_failed(host, port)` **immediately before** recording. A counter of
  zero therefore proves **neither site executed**.
- **`peer_message_error` is not evidence of a send.** It is recorded in
  `_handle_peer`'s `except` — the INBOUND parse/verify channel (line ~8270). It
  says something arrived and could not be handled; it says nothing about
  delivery.

So: A mined a block, the block provably did not reach C, and A recorded **nothing
outbound** and **backed off nothing**. The link stays at full conductance and
/anomalies is silent about a delivery that never happened.

**This is the exact failure A18 (v8.30) exists to close**, and A18's own comment
names this platform and this test:

> *"Found by running K1/K3 on Windows 2026-08-22, where a killed peer's
> listening port can still accept a connection: every attempt 'succeeded' at the
> socket level, so the except branch below never ran and node A recorded nothing
> about a delivery that never happened."*

The diagnosis was right. The fix — `self._note_send_failed(...)` plus
`peer_send_failure("bytes accepted, no ACK")` after attempts are exhausted — is
in the source and is **not being reached**. Five node versions later, on the
machine that runs production, the send still terminates through a success path.
The likely candidate is the `return verdict` / `return None` branch above it
taking the exit before the exhaustion path, but that is a hypothesis and this
item exists because hypotheses were the problem.

**Deliberately not fixed in the run that found it.** The change is to what the
send path counts as success, and §0 is explicit: never weaken a control to make
a test pass. Making K1/K3 accept `peer_message_error` would be exactly that —
it would let an inbound parse error stand in for proof of outbound delivery.

**The cheap next step, and it needs one Windows run, not a redesign:** instrument
`_broadcast`'s exit — which branch returns, and what the ACK read actually got —
and print it from K1 the way P7 printed the counters. P7's own method worked:
*measure, do not guess*, and the measurement arrived the first time the suite
ran where it runs.

**A24. A peer can empty the anomaly buffer of everything that matters.**
Opened 2026-08-26 ~10:45 by an adversarial pass over v8.37's OWN new surface
(M33), and the first question was whether I had just caused it. **I had not —
it is architectural, and it predates every guard in this file.**

`SpikingAnomalyMonitor` holds `max_events=5000` and evicts oldest-first. Several
anomaly kinds are recorded on paths a PEER triggers at will, one record per
frame, with no per-source or per-kind bound. Measured, same harness, both
sources:

```
                       frames  buffer  composition             real event kept?
v8.36 peer_message_error 5200   5000   {peer_message_error:5000}      NO
v8.37 peer_tx_id_invalid 5200   5000   {peer_tx_id_invalid:5000}      NO
```

A planted `peer_send_failure` reading *"REAL EVENT: node B unreachable"* — the
exact phasic signal the buffer exists to retain — was gone in both cases. So an
attacker with one socket can make `/anomalies` say nothing but what the attacker
chose, and the watchdog reads `/anomalies` every round (P12). **This is the
watchdog-log failure (3,973 lines carrying 16 messages) rebuilt one layer down,
with an adversary holding the pen instead of a permanent win32 fact.**

v8.37 adds three more attacker-triggerable kinds (`peer_tx_id_invalid`,
`peer_index_invalid`, `outbound_message_too_large`) to a room that already had
at least one wide-open door, so it neither caused nor worsened this — the rate
was already the attacker's to choose via `peer_message_error`. Recorded that way
rather than as "my new surface", because the fix belongs at the monitor and not
at the six call sites.

**Deliberately NOT fixed in the run that found it,** and the reasoning is worth
keeping. The obvious fix is to change eviction policy — on overflow, evict from
the most-represented kind rather than oldest-overall, so the buffer degrades
toward diversity under flood. That is probably right. But `_events` also feeds
the SPIKE DETECTOR's baseline, so changing which events survive changes what
counts as a spike, and the detector is read by `/health` and by the watchdog's
alerting. Shipping an eviction-policy change into the observability layer in the
same hour as a propagation, on a system where the running node is already two
versions behind, is how a monitoring regression gets dressed as a tightening
(W1/M26 is the precedent). Fix shape for the next run: per-kind share cap or
diversity-preserving eviction, with the spike detector's behaviour measured
before and after on the same event stream, and a check that a flood of one kind
can no longer evict another kind's records.

**A25. `/health`'s `source_sha256` does not contain a sha256.**
Found the same hour, by writing a tool that trusted the name. The field holds
`CORE_SOURCE_SHA12` — the first **12** hex characters (line 7362), which
`test_p11` V6b pins deliberately, and which the peer digest and watchdog both
use. So the contract is correct, tested and intentional; only the NAME lies, and
it lied convincingly enough that `verify_deploy.py`'s first draft compared it
against a full 64-character digest and reported MISMATCH on a node running
exactly the right source. **A verifier that cries wolf on a correct deployment
is worse than no verifier, because it teaches its operator to skip it.** Not
renamed: a suite pins the field and two consumers read it, so a rename is an
interface change needing L's say-so. The `verify_deploy.py` docstring states the
48-bit comparison explicitly instead. Same family as the `POST /peers` comment
that denied a live control and `judge_keyless` meaning something narrower than
it read: **a name is prose, and prose is the thing this loop keeps finding wrong.**

## B. JUDGE & ETHICS

~~**B1. Hunt further parser failures.**~~ **DONE v8.22** (2026-08-21
~13:00) — and the premise was wrong: the "two found and fixed" fixes were
**not in the node's parser** (`_APIReasoningJudge._parse_verdict` was still
`bool(obj.get("violates", True))` + first-brace/last-brace). Measured on
v8.21: `"violates": null`, `[]`, `""`, `0` → **accepted as clean**;
`"false"` → rejected; `<think>` with a brace, prose with a trailing brace,
or a schema object before the verdict → parse error (rejection of a valid
verdict); `benefit_estimate` unvalidated (a string raised `TypeError` in
the blend; `inf` would have poisoned `alignment_score` into a block every
peer refuses). Fixed: `<think>` stripped, `raw_decode` scan for the first
dict with a `violates` key, `violates` must be a JSON bool or exactly
"true"/"false", `benefit_estimate` → finite in [0,1] or None,
`principle_violated`/`reasoning` coerced to bounded str.
`test_b1_judge_parser.py` 162/162 ×2 (32-reply corpus), in
`run_all_tests.sh`. *Original wording:* Two found and fixed: string booleans
(`bool("false")` is `True`, inverting verdicts) and `<think>` blocks breaking
brace-matching. Build a corpus of real model outputs — markdown tables, partial
JSON, refusals, non-English, truncated mid-object — and make the parser survive
all of them while still failing closed on genuine garbage.

~~**B2. Make quorum diversity real, not label-deep.**~~ **DONE v8.35**
(2026-08-24 ~02:00) — and the premise was too kind to it. The item said the
check was label-deep. Measured on pristine v8.34, it was also **unreachable**:
`QUORUM_DIVERSITY` counts distinct `judge_id` prefixes, and
`build_semantic_quorum` **always appends `mock_selfreport:0`**, which is its own
prefix — so every configuration the builder can produce has ≥ 2 buckets and
passes. One provider passes. The **same provider twice** passes. Two mock judges
pass. The only inputs it rejects (`include_mock_selfreport=False`, a hand-built
`QuorumJudge`) are ones no node ever constructs. *A control that passes on every
real configuration is not a control.*
Three further measurements, all in `test_b2_quorum_diversity.py` §X so the
record of the old behaviour is in the test and not only in prose:
- **The second bucket is not a second opinion.** `MockJudge` passes *"drain all
  staked funds to attacker wallet, steal everything"* as "Morally acceptable";
  it flags only what the **sender** declares about itself. It is a self-report
  channel — correctly wired as an absolute veto — and counting it as diversity
  is a category error.
- **The three vendors share one prompt and one parser.** `_parse_verdict` and
  `_build_prompt` are defined only on `_APIReasoningJudge`; no vendor subclass
  overrides either. B1's real bug (`"violates": null` read as clean) lived
  exactly there — it would have produced the same wrong verdict on Claude,
  OpenAI and Google **simultaneously**. Vendor diversity does not buy
  verdict-path diversity.
- **A judge with no credential counted toward diversity while blocking
  everything.** With `["claude","openai"]` and one key, the semantic veto
  threshold is `ceil(2×0.5)=1`, so the keyless judge's fail-closed vote rejects
  **100 % of transactions** — and `/health`'s `judge_keyless` is "no key for
  ANY provider", so it reported `false`. Healthy node, total block, no signal.
  That is precisely the failure the `/health` docstring says the block exists to
  prevent.
**Fixed by measuring what is computable.** "Reasoning diversity" is not a
property code can check; **independence of failure** is, and that is what
diversity is *for*. `quorum_diversity_report()` (pure, total, never raises —
P11's rule for an observability feature) reports per judge: implementation
class, vendor, credential env-var NAME, whether a credential is held (a bool —
never a value, asserted by S1), model, whether `_call` is implemented, and which
class supplies its parser and prompt. `independent_semantic_judges` = distinct
`(implementation, credential, model)` among *operable* semantic judges.
Degradations are named and stable-texted so the watchdog's P12 adaptation shows
each once: `single_semantic_judge`, `duplicate_implementation:`,
`shared_credential:`, `uncredentialled_semantic_judge:`, `no_live_path:`,
`insecure_mock_semantic:`. `shared_verdict_path` is reported as a **fact, not a
warning**, because it is true of every configuration this file can build and
warning on it would train an operator to ignore warnings (M34).
**Disclosure, not policy.** No verdict changes (S3). `degraded`'s formula is
byte-identical to v8.34 (H3). The existing `QUORUM_DIVERSITY` raise is untouched
and still fires first (E5). `/health` carries the report and the warnings; the
boot banner prints them, verified on a real node — `ethics quorum: 1 independent
of 1 semantic judge(s), +1 self-report; veto>=1; diverse=False`.
`covenant_watchdog` renders `judges=k/n` on its per-round INFO line, so
`watchdog.log` becomes a minute-by-minute record of what the gate actually was.
**The tightening is opt-in and one-way:** `COVENANT_REQUIRE_JUDGE_DIVERSITY=1`
refuses a non-diverse quorum at build time; **only the exact string `"1"` arms
it** and no value of it relaxes anything (E4, seven values tried) — the same
shape as `COVENANT_FORCE_NO_SANDBOX` in P4/P10. Default unset = v8.34 behaviour
(E1), which is why L's mock nodes and every suite still boot.
**And the boundary is asserted (M31/A21):** the operator may see the quorum's
composition; a **peer may not**. `test_b2` §B pins it on the digest object, and
`test_a20`'s D1–D6 pin it on the bytes captured off the wire — D5 read
`{"v":"v8.35","src":"1207bd2e7dc5",…}` from a real node's heartbeat with no
quorum block in it.
`test_b2_quorum_diversity.py` **73/73 ×2** (PRE-FIX RECORD **22/29** on pristine
v8.34: the 22 that pass are the record of the old behaviour and pass on both
files; the 7 that fail name the missing fix), in `run_all_tests.sh`.
**Not done, and deliberately:** B2's own wording asked to make diversity "real".
Reasoning diversity cannot be made real by this file — it can only be *bought*,
by configuring providers that are genuinely independent. What this closes is the
part that was a lie: the claim that the current wiring is diverse. **L: the
one-line way to make it true is `COVENANT_JUDGE_PROVIDERS=claude,openai,google`
with all three keys present** (measured `diverse=True`, independence 3), and
`COVENANT_REQUIRE_JUDGE_DIVERSITY=1` to keep it that way.

~~**B3. Judge timeout audit.**~~ **DONE v8.22** (2026-08-21 ~13:00).
Three hard-coded `timeout=30` literals (Claude/OpenAI/Google), nothing else
at 30 s. Now one `JUDGE_TIMEOUT_S` (`COVENANT_JUDGE_TIMEOUT_S`, default
30, refused at import outside [1, 600]). A timeout still fails closed —
that is correct and untouched — but it is now **distinguishable**:
`JudgmentResult.infrastructure_failure` is set by no-key / timeout /
HTTP error / unparseable reply, propagated by `QuorumJudge` only when a
violating component carries it, and both `/transactions` and the peer
ingest path record `judge_unavailable` beside `ethics_gate_rejection`.
A real dissent is never relabelled (Q2). Also found on the way:
`/transactions` called `judge.evaluate` **twice** per transaction (once to
decide, once more just to `save_judgment`) — two live API round-trips,
2× latency, and the persisted verdict could differ from the acted-on one.
Now one call via `ReasoningSentinel.evaluate_transaction`. *Original
wording:* Cloud default is 30s; a local 7B on CPU exceeds it and a timeout
counts as a **violation**, so slow hardware silently rejects transactions.
Local is 180s. Check no other path keeps 30s.

**B4. The semantic judge sits inside consensus — decision for L.**
`_accept_block_common` (peer block acceptance) and `/mine` both call
`sentinel.validate_block`, i.e. a live, non-deterministic, timeout-prone
API call **per transaction per block on every node**. With real providers:
(a) a timeout or provider outage on node B while A's block arrives makes B
record `block_rejected_ethics` and fork from A, B3's flag notwithstanding;
(b) two nodes can get different verdicts for the same data; (c) `/mine`
evaluates each tx a second time after the PoW is done, so a judge hiccup
discards a mined block. With the mock judge (every test so far) none of
this shows. Options: judge at admission only and make block acceptance
re-verify signatures/shape/balance but not ethics (a protocol change;
peers would then trust the miner's gate); or keep it and accept forks on
judge disagreement; or cache `judgments` by tx_id and reuse on the block
path (consistent per node, still divergent across nodes). **L: should the
ethics verdict be a consensus rule or an admission policy?** Do not change
either path before that answer (Section 0: it is a control).

**AMENDMENT 2026-08-26 — B4 is also a POWER decision, and that has never been
stated. It was filed as a correctness question and it is the largest energy lever
in this system by a wide margin.** L asked whether mycelium could generate
electricity to lessen data-centre power (DE8: no, by twelve orders of magnitude).
The useful half of that question turned out to be the mirror: *what actually draws
power here?* Measured on L's own machine, from files already sitting in the
covenant folder — `TOPMEM.txt`, `LEAN_MEASURE.txt`, and C4's `probe_power.py`:

| | measured |
|---|---|
| `llama-server.exe` (the ethics judge) | **5,234 MB** resident |
| the ENTIRE chain — both nodes + watchdog | **117 MB** |
| ratio | **45×** |
| one warm verdict | 12.8 s (`num_predict=96`) |
| one cold model load | 39.9 s |
| proof-of-work for a whole block, difficulty 4 | **0.34 CPU-s** |

At an assumption of 40 W package power — stated so it can be checked rather than
believed — a single ethics verdict is ~512 J against ~13.6 J for mining the
block it sits in. **The ethics gate costs about 38× the proof-of-work**, which is
the exact opposite of what anyone assumes about a chain's energy profile. Nobody
here has ever been mining anything expensive; the node is 0.03 % of a core (C4).

**And B4 is the switch.** If the verdict is a CONSENSUS RULE, every node
re-evaluates every transaction in every block: N nodes × 512 J per transaction,
and every participant needs 5.2 GB of resident RAM to take part at all. If it is
an ADMISSION POLICY, one node pays 512 J and a peer needs ~0.1 GB. At 100 nodes
that is 51.2 kJ against 512 J per transaction — a hundredfold — and it is the
difference between a mesh that can only run on machines that host an 8B model and
one that can run on a phone (C3/C4) or answer over a LoRa link (R1).

**This changes no verdict and settles nothing** — §0 is explicit that a consensus
change is L's call, and there are real correctness arguments on the consensus
side (a peer would otherwise have to trust the miner's gate). It is filed here so
that the decision is made with the number in front of it. **L: B4 is worth about
two orders of magnitude of the system's energy at scale, and it is still open.**

~~**B5. `/mine` with live judges: measure the latency.**~~ **DONE — measured
(00:47 run, unlogged) + observability fix v8.24 (2026-08-22 ~01:40).**
`test_b5_mine_latency.py` 31/31 ×2 (27/31 on v8.23), in `run_all_tests.sh`.
Measured on the real `/mine` (M13): judging is N_tx × N_judges × per-call,
strictly sequential, **after** the PoW, **under `chain_lock`** — every
`/transactions`, peer tx fetch, peer block accept, tip gossip and `/chain`
on the node waits. A timeout costs 3 × `JUDGE_TIMEOUT_S` + backoff =
**91.3 s per tx per judge** at the default; the mined block is discarded
(400), the txs stay pending, and the next `/mine` repeats PoW + wait. A
verdict that flips clean→violating at mine time wedges `/mine` until that
tx is evicted by hand. Honest maximum: 5000 pending × one timing-out
provider = 127 h under `chain_lock`; happy path 2 judges × 2 s = 5.6 h.
v8.24 changes no decision (B4's): a `/mine` refusal is now recorded as
`mine_rejected_ethics` (it recorded nothing), and an infrastructure refusal
on `/mine` **and** on `_accept_block_common` also records
`judge_unavailable`; a real dissent never is (asserted both paths).
**The fix proper waits on B4.** *Original wording:* N pending tx ×
(up to 3 attempts × `JUDGE_TIMEOUT_S`) per provider, sequentially, after
the PoW — with 5000 pending and one slow provider that is hours. Cheap to
measure with M13's canned judge plus a `time.sleep` in `_call`. Depends on
B4's answer for the fix.

## C. DEPLOYMENT

~~**C1. Phone node install untested.**~~ **REVIEWED 2026-08-22 12:30** —
`phone/node-install.sh`, `node-install-v2.sh` and `covenant-doctor.sh` are in
the project now (pulled over the bridge, M25) and statically reviewed against
the shipped core in `claude/PHONE_INSTALL_REVIEW.md`: **8 BLOCKER, 15 DEGRADED,
10 NOTE.** Still never run on hardware — the phone has not arrived — so this is
review, not verification. The blockers, shortest first: v1 never installs
Flask/werkzeug (the core imports them at top level) and never copies
`covenant_path_pattern.py`; both scripts read `$HOME/storage/downloads` without
running or checking `termux-setup-storage`, so on a fresh phone every file
reports "missing from Downloads"; `binutils` is a linker, not a compiler, and
Termux pip rejects every manylinux wheel, so `cryptography` builds from source
with no `clang`; `pkg install` output AND exit status are both discarded and
there is no `pkg update`; v2 sets `COVENANT_JUDGE_PROVIDERS=local`, which is not
a registered provider — `JudgeProviderRegistry.build` raises in
`CovenantUnifiedMaster.__init__`, before a port is bound; five of the seven
files v2 requires are not in the bundle or the manifest; and
`covenant-doctor.sh` measures `runs.log`/`covenant-run.sh`, which nothing in
either installer creates — it prints "the job has NEVER run" for a perfectly
healthy node, and once both files exist it reports **alive** on a timestamp with
no process check, no port check and no HTTP request. Also: v2's judge gate
constructs `OllamaJudge` directly, so it never exercises the path that actually
runs, and `curl -s` exits 0 on a 404 — "Ollama reachable" passes against a
router admin page. **Nothing is fixed here**: these are L's scripts, the phone
is not here, and rewriting an installer that has never met its target is how you
get a second untested installer. Fix them with the device in hand, against the
report.
~~**C5. On-device Android privacy/security layer (L's trigger-prompt ask).**~~
**BUILT 2026-08-23 ~08:30** — `covenant-guard-src.tar.gz`, delivered by
SendUserFile (741 KB, 47 source files, 4,761 lines of Kotlin); design record and
the full assumptions list in `claude/ANDROID_GUARD.md`. A local `VpnService`
DNS firewall: no remote server, no third party, every decision in-process and
synchronous. Five Gradle modules, and the split IS the verification strategy —
`:policy-api` and `:core` are Android-free, so the DNS codec, the IPv4/IPv6+UDP
builder with RFC 1071 checksums, the blocklist, the decision chain and the
hash-chained audit log all run under `./gradlew test`: **89 tests, 0 failures,
twice, the second time with `--no-build-cache --rerun-tasks`**. Debug APK, R8
release APK (1.1 MB), lint **0 errors**, zipaligned + signed + `apksigner
verify` v2/v3; the manifest and the R8 dex were both read back OUT OF the built
APK rather than trusted from the build log (M35).
**The governance seam is the part L singled out:** `PolicyProvider.evaluate` →
`ALLOW|DENY|LOG|abstain`; chain order total and reproducible; **DENY is
absorbing**, and an ALLOW may overturn it only with an explicit
`canOverrideDeny` declaration AND strictly stronger priority, every such event
logged as an override; a throwing provider abstains — it may not deny (a crash
must not take the network down) and may not allow (or `throw` becomes the
cheapest bypass); the app's own blocklist is an ordinary provider with no
special standing, asserted by a test in which an example module overturns it.
Extension point is a **compile-time module boundary, not AIDL, and the README
argues it**: a Binder hop per DNS question adds a context switch to every name
the phone resolves, its timeout policy would be a security decision made by a
scheduler, and an exported decision hook is a way for any app that binds it to
see every domain the device resolves — the surveillance the app exists to
prevent, rebuilt as a feature. AIDL IS used for the control plane only (install
rules / verify audit), unexported, gated through `AuthorityModel`.
**Still untested where it runs (M29):** no device and no emulator here, so
nothing below `builder.establish()` has ever executed. README §0 is the
measured-vs-not table; §7 is the eleven flagged assumptions; §8 records the
three defects the tests found.
**And it collides with C3** — one VpnService at a time, so this app and
Tailscale cannot both hold the phone. See the correction above.

**C2. Heartbeat/doctor** gap detection is unit-tested only.
**C3. Cross-network peering** via Tailscale — documented, never tried.
*(08:00: the code path is verified on the interface-IP shape, A17; the
Tailscale hop itself still waits for the phone.)*
**C4. Phone power: the radio, not the CPU.** `claude/probe_power.py` on
v8.27: idle node 0.03 % of a core / 56 MB; 0.34 CPU-s per block at
difficulty 4; ≈ 0.1 % of a 15 Wh battery per day. The estimated cost is
720 gossip wake-ups per peer per day on cellular (~3 %/day, arithmetic).
Lever exists: `COVENANT_TIP_GOSSIP_INTERVAL=600` on the phone. Measure
with the phone; do not change the default for the PC.

## D. TRADING TOOLING

**D1. Deepen price history — IN PROGRESS; XLM DONE (2026-08-22 ~06:20).**
220 bars → 66-bar test set → detects
only annualised Sharpe above **4.61**, which is why every "no edge" conclusion
here was under-powered. Done: `realdata/deep/XLM_2025Q1.csv`, 105 verified bars
2025-01-01 → 2025-04-15; **`realdata/deep/XLM_2025Q2_2026Jan.csv`, 281
verified bars 2025-04-15 → 2026-01-20** (first row deliberately duplicates
Q1's last bar so the join can be asserted locally; 386 bars total for XLM,
~116-bar test set). **SOL DONE** (`realdata/deep/SOL_2025_2026Jan.csv`, 391
bars 2025-01-01 → 2026-01-26, sha256 `addb42b5…`) and **XRP DONE**
(`realdata/deep/XRP_2025_2026Jan.csv`, 397 bars 2025-01-01 → 2026-02-01,
`dcecaa87…`), both 06:45, same recipe, 30-row independent re-fetch 30/30
each. **HBAR DONE** (`realdata/deep/HBAR_2025Jul_2026Aug.csv`, 408 bars
2025-07-10 → 2026-08-21, sha256 `42c2894e…`, ~07:15): Kraken lists HBARUSD
only from 2025-07-10 (DE5), so it was extended to the last complete bar
instead — 408 bars is nearly 2× the 220 the power problem was stated
for, but note the window is Jul-2025 onward, not 2025-01. **07:14 run (unlogged; verified and logged 07:45):** XLM/SOL/XRP extended
to 598 bars each, 2025-01-01 → 2026-08-21, as `realdata/deep/{XLM,SOL,XRP}_
2025_2026Aug.csv` (sha256 `7c59b6bd…`, `60f792be…`, `c2b450fd…` as held on
disk after a verbatim fetch; their post-Jan tails re-fetched independently
at 07:45: XRP 25/25, SOL 20/20, XLM 20/20 byte-identical) — these supersede
the `_2026Jan` files for D2. **ADA DONE** (`realdata/deep/ADA_2025_2026Aug.
csv`, 598 bars 2025-01-01 → 2026-08-21, sha256 `a0ae69f1…`, ~07:45; Kraken
`ADAUSD` has bars from 2024-09-01, 8 windows, two independent interior
re-fetches 50/50 identical). **D1 COMPLETE (08:45 run, M24 direct-API recipe):** ATOM `cef5abed…`,
AVAX `57566fc0…`, NEAR `692460b6…` (598 bars each, 2025-01-01 → 2026-08-21),
CRO `2d82f4b6…` (570, listed 2025-01-29), ONDO `ef1c34d1…`, PEPE `5b55fd41…`
(598 each), WLFI `6de7219e…` (`WLFI_2025Sep_2026Aug.csv`, 355, listed
2025-09-01) — all `verify_csv.py` 0 defects, two interior re-fetches 30/30
each, project round-trip verified by hash. The earlier "may not be on
Kraken" was wrong: all three are. Note Kraken pair names (XLMUSD → `XXLMZUSD`, XRPUSD →
`XXRPZUSD`; HBARUSD is plain `HBARUSD`).
~~**D2.** Re-run every conclusion on the deeper data.~~ **DONE for the
regime rule on XLM/SOL/XRP (2026-08-22 ~08:00)** — `claude/d2_regime_deep.py`
on 598-bar series (`realdata/deep/{XLM,SOL,XRP}_2025_2026Aug.csv`,
2025-01-01 → 2026-08-21, cross-venue checked vs Coinbase to < 0.01 %):
timing edge +12 % / +59 % / +56 % log-growth at **p = 0.81 / 0.47 / 0.67**
— not distinguishable from chance on 3× the data, DSR 0.000; drawdown
reduction 0.9× / 2.1× / 1.8× (XLM whipsawed 9× and lost MORE than
holding). By arithmetic a Sharpe-0.5 edge needs ~31 years of daily bars to
detect — the rule is risk control, never alpha. Full write-up in
`claude/TRADING_READINESS.md`. **DONE on all ten assets (08:45):** ATOM p 0.697 (DD 1.7×), AVAX 0.546
(1.7×), CRO 0.509 (1.4×), PEPE 0.658 (1.7×), NEAR 0.773 (**0.9× — lost to
holding, 11 whipsaws**), ONDO 0.915 (**0.6×, 18 whipsaws**), WLFI: rule
never fired in 155 decision bars, no verdict possible. Second seed shifts
each p ≤ 0.03. Three of ten assets get no drawdown control from the rule;
table in `TRADING_READINESS.md`. *(07:45: reproduced to the decimal, then re-run under
a second bootstrap seed — p 0.797 / 0.456 / 0.688, stable to ±0.02; ADA
added: edge +110 % at p = 0.531, DD 2.21×, 3 switches — same verdict.
HBAR's series starts 2025-07-10 (DE5), ~208 decision bars after warm-up.)*
~~**D3.** Automated tests for `guards.py` and `daily.py`~~ **DONE 2026-08-22
12:30** — `claude/test_d3_daily_guards.py`, **61/61 ×2**, wired into
`run_all_tests.sh`. No network, no key, nothing trades. Two groups: G1–G8 pin
every breaker on both sides of its boundary (including that a guard which
RAISES becomes a block, not a pass, and that `GuardStack` reports ALL blocks
rather than short-circuiting on the first); D1–D7 and S1–S5 make
`DAILY_CHECK.md` §3 executable. **The D-checks are the finding:** §3 has
mandated contiguity / duplicate / non-positive / staleness verification on every
price window since 2026-08-20 and `daily.py` implemented **none of it** — it
sorted the rows and used them, so the 70-day-stale series of
`PRICE_DATA_INTEGRITY.md` would have printed here as a clean regime call and
fed the 20 % cap arithmetic. `fetch()` now returns `(price, closes, why_failed)`
and refuses with a reason instead of reporting numbers. Note `execute.py`,
`paper_run.py` and `covenant_judge_local.py` are NOT covered: the first two do
not exist (see the correction under D3a below), and the third is a judge module
that belongs with B, not D.
**D3a. CORRECTION — `execute.py` and `paper_run.py` do not exist.**
`EXECUTION_ARCHITECTURE.md` describes both as built and bug-fixed ("`execute.py`
now calls `kraken balance` first and clamps every order"), and
`TRADING_READINESS.md` §2 lines 3–4 say "L must upload" them. Neither is in
`C:\Users\Lawre\covenant` — a `find` over the whole folder returns only
`paper_bot.py`. They were written in a cloud session, delivered by
SendUserFile, and never saved. So checklist lines 3 and 4 were never blocked on
an upload; they are blocked on code that has to be written. Both docs corrected
this run.
~~**D4.** Wire `guards.py` into `daily.py`~~ **DONE v-D4 2026-08-22 12:30** —
and the premise was worse than "called nowhere": `grep -i guard daily.py` on the
shipped file returned **zero lines**. Every circuit breaker was written,
documented, hand-tested and reachable by nothing. Now: `daily.py` imports
`guards` (failing CLOSED if the import fails — every "may add" is blocked and
the reason printed), keeps an equity journal at `~/.covenant/daily_state.json`
(**outside** the synced folder: it would otherwise break the seal on every run,
and the folder leaves the machine), and the guards gate exactly one sentence —
rule 2's *"may hold and add"*. They never block a trim and never suggest a sale.
`--sold SYM [--pnl X]` records a sale so the cooldown and loss-streak guards
have something real to reason over; where the journal cannot supply a value the
run says so rather than assuming safety. `execute.py` half of this item is void
— see D3a.
**D5.** `MY_STRATEGY.md` contains none of L's actual numbers. *(UNBLOCKED
2026-08-22: the file is in the project now.)*
**D6.** Re-do HBAR analysis in `REAL_DATA_FINDINGS.md` (was computed on the
corrupted 70-day-stale series). XRP results stand. *(UNBLOCKED 2026-08-22: the
file is in the project now, and `realdata/deep/HBAR_2025Jul_2026Aug.csv` is on
the PC.)*
~~**D7.** Rename superseded corrupted files in `realdata/`.~~ **DONE
DIFFERENTLY 2026-08-22 12:30** — `realdata/README.md` on the PC names every
superseded file and why (the `*_c.csv` ~220-bar series, the
`HBAR-USD.STALE-ends-2026-06-10.csv` corruption, the Coinbase `XRP-USD.csv`),
and points at `realdata/deep/`, where all twelve verified series now sit
locally for the first time. **Deliberately not renamed:** a file that a past
result was computed on should stay findable under the name that result cited.

## W. THE HTTP FRONT DOOR

~~**W1. The HTTP server was the last unbounded resource.**~~ **DONE v8.29
2026-08-22 12:30** — `test_w1_wsgi.py` **24/24 ×2**, in `run_all_tests.sh`.
A3 bounded peer bytes, A5 made the ceilings coherent, A14 bounded the boot
probe, A15 bounded the exchange in wall-clock, `MAX_CONCURRENT_HANDLERS` bounds
the receive pool at 96 — and Flask was served by `run_simple(..., threaded=True)`,
werkzeug's **development** server: one thread per connection, no ceiling, no
queue, no idle timeout, on the one port an operator is told to expose. W10 is
the pre-fix record (the dev server never reaps an idle connection; measured,
not argued). Now `resolve_wsgi_server()` prefers waitress — pure Python, so it
needs no compiler on Termux/aarch64, and it works on Windows — with
`WSGI_THREADS` 8, `WSGI_CONNECTION_LIMIT` 100, `WSGI_CHANNEL_TIMEOUT` 120 s and
a `cleanup_interval` DERIVED from the timeout so the number an operator sets is
the number that happens. `COVENANT_WSGI=auto|waitress|werkzeug`; absent
waitress the old dev server runs byte for byte, and `/health` reports `wsgi:`
plus a warning when it is the dev server. The WSGI body cap is deliberately
ABOVE Flask's `MAX_CONTENT_LENGTH` (W7): if waitress refused the body first it
would answer 413 itself and the v8.17 `http_body_too_large` anomaly record
would silently stop happening — a monitoring regression dressed as a tightening.
**The honest trade, recorded not hidden:** a bounded pool CAN be exhausted where
an unbounded one would not — B5 measured `/mine` holding `chain_lock` for up to
91.3 s per tx per judge, so 8 such requests do stop HTTP. Bounded-and-queued is
the better failure (visible, recoverable, and idle clients are reaped), but the
cure for the wedge is B4/B5 and swapping the server must not be mistaken for it.
**And it broke a control on the way in — see M26 and A2.**

---

## P. THE MACHINE THAT RUNS IT

~~**P4. The code sandbox was dead on both platforms, in different ways.**~~ **DONE
2026-08-22 ~22:00 (v8.30, W2).** Windows: no fork, so `run_sandboxed` raised into
a bare 500. Linux: `RLIMIT_NPROC = 0` plus a `Queue` whose `put()` needs a thread,
so the child died reporting nothing and every proposal — including `x = 1` — came
back "child exited without reporting". Fixes, neither of which weakens a limit:
the child now reports over a **one-shot Pipe** (no feeder thread; RLIMIT_FSIZE
does not apply to pipes), and a platform with no fork **refuses** with
`SandboxUnavailable` instead of raising, so the Guardian rejects with a reason and
`/propose_code` answers 400 and records `code_sandbox_unavailable` on /anomalies.
`/health` carries `subsystems.code_sandbox` and warns at boot. Deliberately NO
"spawn" fallback: Windows has no `resource` module, so RLIMIT_AS/NPROC/FSIZE
cannot be applied there and a sandbox that runs the snippet uncapped while
reporting success is worse than one that refuses. `COVENANT_FORCE_NO_SANDBOX=1`
makes a fork platform take the refusal path so it is testable — one-way by
construction: nothing turns the sandbox ON where the limits cannot be enforced.
New suite `claude/test_w2_sandbox_platform.py`, 21 checks, and it pins the
no-spawn-fallback rule. → M29.

~~**P5. Windows SO_REUSEADDR let two nodes share a port; A2 could not see it.**~~
**DONE 2026-08-22 ~22:30 (v8.30, A19).** `_bind_exclusive()` now sets
`SO_EXCLUSIVEADDRUSE` on Windows (listeners and the preflight probe) and keeps
`SO_REUSEADDR` on POSIX. Before this, `test_a1a_a2`'s A2-1 collision case did not
fail fast on Windows — the second node bound the same port and ran. This is the
mechanism behind the leaked node on 5001 that blocked node B's start at 21:02.
Caveat recorded honestly: **waitress binds the API port itself**, so the API port
is still hijackable on Windows; only the node's own P2P and bridge listeners and
the preflight are covered.

~~**P6. A silent non-delivery recorded nothing.**~~ **DONE 2026-08-22 (v8.30, A18).**
`_send_to_peer` recorded `peer_send_failure` when the socket raised — but when the
bytes were accepted and **no application ACK ever came**, the final attempt fell
through to a bare `return None`: no anomaly, and no `_note_send_failed`, so the
link was not even backed off. That is precisely the silent non-delivery the ACK
was added to catch. Now recorded and backed off like any other failure.

**P7. `test_a1_kill_matrix` K1/K3 still fail on Windows — INSTRUMENTED 2026-08-23
~07:45, still one Windows run short.** The measurement the item asked for is now
in the suite (`p7()`), printing `dead_peers` / `heartbeats_skipped` / `peers` /
anomaly kinds on the relevant node either side of the kill, and folding them into
the failing check's own detail string so the next Windows sweep's output carries
the answer. It asserts nothing — deliberately. **Linux baseline recorded now, for
comparison:** K1 `dead_peers 0 -> 1` ACROSS the mine with `heartbeats_skipped
0 -> 0` and `peer_send_failure` present; K3 the same on B. So on Linux the send is
attempted, fails, and that attempt is what marks the peer dead. **If Windows shows
`1 -> 1` with no `peer_send_failure`, the standing hypothesis is confirmed** — the
backoff had already marked the peer and the broadcast skipped it, meaning the node
is correct and the missing thing is the record. Still not fixed here, and the
reason is unchanged: "a skipped block delivery should leave a trace" is probably
right, but a heartbeat skip must NOT — that would flood /anomalies with exactly
the tonic signal this day's work removed from watchdog.log. Original wording:
28/30, twice, alone. A's `/anomalies` after mining to a dead peer holds
`peer_message_error` but no `peer_send_failure`, and A18 did not change that —
which means A did not attempt the send at all. Most likely A12's dead-peer backoff
had already marked B DEAD and the broadcast skipped it. If so the node is behaving
correctly and the *record* is what is missing: a skipped block delivery should
leave a trace (a heartbeat skip should not — it would flood /anomalies). Needs one
measurement of `dead_peers`/`heartbeats_skipped` on A between the kill and the
mine before anything is changed.

~~**P8. `test_b5_mine_latency` L2 has a knife-edge assertion.**~~ **DONE
2026-08-23 ~07:45.** Both L2 cost checks now compare against `BAR = per_tx * 0.95`.
The claim is "it paid the full judging cost again", not "it took at least this
exact float": if the retries stopped happening the figure would be ~`t`, a third
of the bar, so the 5 % tolerance costs the check nothing and stops it failing two
sweeps in three on a machine also running two nodes and Ollama. → M34.

**P9. On Windows NO owner-only check holds — and it hard-blocks the mainnet
guard. MEASURED 2026-08-24, and it is worse than this entry said.**
Filed as a key-ACL nicety. The first Windows sweep found it is not: NTFS does not
give `os.chmod(0o600)` POSIX semantics, so *every* owner-only assertion in this
codebase is false here. Two independent witnesses in one sweep —
`test_security_audit`'s single red (`identity key file is owner-only`) and
`probe_final_pass` dying on
`MainnetGuardError: Policy file ... is mode 0o666`. The second means
**`authorize_mainnet_payment` refuses on this machine, always.** Fail-closed, so
it is safe — and it means the XRP mainnet path cannot execute on the only machine
that runs production, which nobody knew because that probe had never run here.
Still L's decision (an NTFS ACL, not a code change), but the stakes in this entry
were understated. Original text follows.

**P9 (as originally filed). On Windows the node's identity key file is not owner-only.**
`test_security_audit`'s "identity key file is owner-only" fails there: `chmod 0o600`
is a near-no-op on NTFS, where ACLs govern. The key is the node's operator
credential. Either set the ACL (`icacls <file> /inheritance:r /grant:r %USERNAME%:F`)
at creation on win32, or record it as an accepted risk in DEPLOYMENT.md. Not
touched here: it is a security control on L's machine and the choice is L's.

~~**P10. `test_security_audit`'s three sandbox checks fail by design on Windows.**~~
**DONE 2026-08-23 ~07:45, and NOT the way this item proposed.** It said "SKIP
with a reason". A skip stops checking on the platform that runs production. The
checks are now platform-aware ASSERTIONS: on a fork platform the limits must bite
(unchanged); on a no-fork platform P4's refusal must be complete — a benign
snippet refused and not run, a memory bomb never reported ok, an infinite loop
refused in ~0 s without executing, and the reason present so it is diagnosable —
plus one check on BOTH platforms pinning the one-way rule, **the sandbox never
reports success when its limits cannot be enforced**, which nothing tested
before. 128/128 on the fork path, 129/129 on the no-fork path
(`COVENANT_FORCE_NO_SANDBOX=1` reaches it from Linux, and the refusal shape was
confirmed on L's own machine). Mutation-tested: a sandbox that claims success
while unable to enforce fails all five. → M34.

~~**P1. The suites were never delivered; waitress was never installed.**~~ **DONE
2026-08-22 ~18:45.** `run_all_tests.sh` on the PC calls 34 suites; 15 were there.
The 19 missing included every A/B-series test written between v8.15 and v8.29 —
`test_a1a_a2`, `a3`, `a4`, `a5`, `a9`, `a1_kill_matrix`, `a11`, `a12`, `a13`,
`a14`, `a15`, `a17`, `b1`, `b5`, `y1`, plus `trace_runner`, `verify_csv`,
`probe_power`, `d2_regime_deep`, `d2_rebalance_deep`. All 21 delivered and
verified by sha256 on the far side. `waitress` was in `requirements.txt` and not
in `.venv`, so W1's bounded pool had never run on this machine: the wheel is in
`vendor/`, unpacked into `.venv\Lib\site-packages`, and `test_w1_wsgi` now passes
24/24 on the waitress path. Recipe and the two-locals table:
`claude/LOCAL_INTEGRATION.md`. → M27.

**P2. `run_all_tests.sh` calls 12 suites that exist nowhere — L's call.**
`verify_bundle.py`, `verify_patches.py`, `verify_auth.py`, `verify_tx_aer.py`,
`test_path_pattern.py`, `test_succession_seal.py`, `test_ethics_judge.py`,
`test_golden_ratio.py`, `test_judge_individuality.py`,
`test_multi_provider_quorum.py`, `test_v86_bridge.py`, `test_v86_loss_tracking.py`
— v8.11/v8.12-era names from `MANIFEST.json`, absent from the PC and from the
project. Every local sweep prints a dozen `NO RESULT` lines that read as failures.
Either restore them from an old bundle (if L has one) or delete the lines. Not
touched this run: deleting a test line is exactly the shape Section 0 says not to
do unilaterally. `run_local_sweep.py` lists them as "referenced but not present"
instead of scoring them.

**P3. `covenant_prod.bat` cannot restart a running node — one-line fix, L's file.**
`:stop` is `taskkill /f /fi "windowtitle eq Covenant Node A*"`, which kills the
cmd wrapper and leaves `python.exe` on 5000/5020; the start path then curls
`/health`, sees UP, and reports "node A already up". Observed live 14:12: stop →
start left both nodes on the process they were already running. `AB_RESTART_NODES.bat`
(new, on the PC) does it properly — `/t` on the taskkill, then kill by PID from
`netstat -ano`, then assert both ports are free before calling `covenant_prod.bat`
to start. Folding that into `covenant_prod.bat` is two lines, but it is L's
operational script and the change deserves a deliberate yes. → M28.

~~**P11. The node could not say which source it was running.**~~ **DONE v8.31
2026-08-23 ~03:10.** M25 taught the loop to grep the DEPLOYED file rather than
trust the backlog; nothing did the same for the RUNNING PROCESS. Three findings
in one file, each individually harmless: `COVENANT_VERSION` (line 413) read
`"v8.9-merged"` and `grep -c` returned **1** — defined, read by nothing; the
boot banner hard-coded `Covenant Unified v7.0` on a v8.30 file, and that is the
string an operator actually sees, in `logs/nodeA.log`, on every restart; and
`/health` carried no version field at all. So "is v8.30 live?" had to be
answered by forensics — `prod.log`'s 21:39 start, the source mtime, and a
`code sandbox unavailable` alert that only exists in v8.30 — on a machine where
`covenant_unified_v8.PRE-v8.29.py` and `…PRE-v8.30.py` both sit in the same
folder and a restart from either would have looked identical.
Fixed additively (grep `P11 (v8.31)`): a real `COVENANT_VERSION`;
`CORE_SOURCE_SHA256`/`CORE_SOURCE_LINES` computed once at import from the
module's own file, degrading to `"unavailable"` **with a reason** rather than
raising (an observability feature must not be able to stop a node booting); the
banner names version + source hash + line count and `flush=True`s, because its
job is to appear in a redirected log; `/health` carries `version`,
`source_sha256`, `source_lines`, and warns when the fingerprint failed.
`covenant_watchdog.py` then compares each node's LOADED hash against the file
on DISK every round: drift is an ALERT naming both hashes and
`AB_RESTART_NODES.bat`; nodes on different sources alert about A7; a node too
old to answer is INFO, once per round. The INFO line now leads with
`v=… src=…`, so `logs/watchdog.log` is a minute-by-minute record of what was
running when — which is exactly what tonight's forensics substituted for.
`test_p11_version_identity.py` 29/29 ×2 in the cloud and **29/29 over the
bridge on L's own machine against the deployed bytes**; 6/6 PRE-FIX RECORD on
pristine v8.30. Full sweep green (23 suites, 788 checks). Write-up:
`claude/RUNNING_VS_DEPLOYED.md`. → M30.

~~**P12. The node was blind to its substrate; the watchdog could not tell change from state.**~~
**DONE v8.32 + watchdog P12, 2026-08-23 ~06:15.** L: *"act as an antenna, also
looking for substrate messages above and below, integrating into the same
patterns in nature."* Measured before building (`claude/SENSING_ACROSS_LAYERS.md`).
**What was already true and is worth recording:** the biological patterning here
is real and mostly WIRED — `LinkConductance` is Hebbian (reinforce ×3 sites,
attenuate ×3, feeding `order()`); `announce_block` is lateral inhibition, cited
in the source to Mahowald's 1992 VLSI retina; `PeerHealth` is habituation with
spontaneous re-test; `MedianGovernor` → `_integrity_monitor_loop` → `crisis_mode`
is homeostasis with a two-check debounce and is the one complete reflex arc in
the system. **Three places where the wire ended:** (a) `SpikingAnomalyMonitor`'s
verdict is computed, stringified and put on `/health` — `grep spike_detected`
returns exactly those three sites, so a detector tuned to say *something changed*
was connected to a text field; (b) `/anomalies` — the richest signal in the
system, `{recent, baseline, expected_recent}` per kind — had exactly one
consumer, `dashboard_render.py`, which draws it for a person, while
`covenant_watchdog.py`, the only thing that ACTS, did not read it at all;
(c) the node could not see its machine at all.
**The measurement that made it concrete:** twelve hours of `logs/watchdog.log` =
**3,808 lines carrying 16 distinct messages**, 99.6% redundancy — 269 identical
permanent `code sandbox unavailable` ALERTs against **four** lines (0.1%) reading
`1 peer(s) unreachable`, which is the 21:02–21:06 episode and the only thing in
the file that *happened*. A receptor with no adaptation buries the transient
under the tonic signal. The node implements the fix one layer down and the
watchdog never applied it to itself.
**Built (all three, L's call):** the watchdog now emits first-occurrence in full,
silence while unchanged, full amplitude on change, a roll-up every 30 rounds so a
quiet log still proves it is alive, and `CLEARED after N round(s)` — `alerts` is
returned unchanged so `--once` and every caller still sees everything, only the
LOG is adapted (replaying the real distribution: the transient's share of emitted
lines goes 1.5% → 10%). It reads `/anomalies` and turns the node's own spike
verdict into an alert carrying the numbers, and a first-seen kind into an INFO —
reported, never acted on, because A11 measured this detector false-positiving for
~3 rounds after a synchronized restart at degree ≥ 5. And `SubstrateSensor`
samples available memory (`GlobalMemoryStatusEx` / `MemAvailable`) and the judge
model's footprint (measured from Ollama `/api/tags`, falling back to a declared
figure, **labelled with which** per M30), cached by a background sampler so
`/health` never blocks, every failure degrading to a reason string, none raising.
**The boundary is the design** and it is asserted over the AST, not in a comment
— B1/B2/B3/B3b, all four mutation-tested. → **M31**.
`test_p12_substrate_sensing.py` 33/33 ×2 in the cloud and **33/33 over the bridge
on L's machine against the deployed bytes**; 4/4 PRE-FIX RECORD on pristine
v8.31. Full sweep green: **24 suites, 821 checks, zero failures.**
**First reading on the real machine: 3,535 MB available against a ~5,200 MB
model** — the condition the warning exists for is live on that box now, and has
presumably been live and unseen for as long as the model has been configured.

~~**A20. Peers cannot see each other's version.**~~ **DONE v8.33 2026-08-23
~06:40, on L's explicit instruction ("broadcast") — the authorisation Section 0
required.** `_reply()` stamps `v` + `src` on EVERY reply (one site, not three:
a peer must be able to learn what we are from any exchange, and one call site
cannot drift out of step with the others). `P2PNode._send_raw` folds every reply
it reads into a new `PeerStateTable`; a peer on another source records
`peer_version_mismatch` naming both hashes; `/health` gains a `mesh` summary
grouping peers by source and warns when the mesh runs more than one. **Nothing
is refused on account of it** — this node does not get to decide a peer is too
old to talk to. Backwards compatibility MEASURED against a real pristine v8.32
process in both directions, not asserted (M32): C1–C5. A v8.32 reply carries no
`v`/`src` and is folded in as "cannot say" — P11's own definition — with no
spurious mismatch (C4/C4b).

~~**A22. `mycelium.topology()` has no internal consumer.**~~ **DONE 2026-08-23
~07:00 (watchdog; node change is v8.34 and is a comment fix plus two hardening
fixes).** `/mycelium` reports the real peer table and each link's conductance,
and was exposed on a route and read by nothing — the same shape `/anomalies` had
twelve hours earlier, and the only place the node says WHO IT IS TALKING TO. The
watchdog now reads it every round through a pure `topology_report()` and alerts
on: an **unexpected peer** (naming it, its address and the configured set — and
`POST /peers` is operator-authenticated, so one did not arrive by accident);
**every link at the conductance floor**, which is A11's measured signature that
the learned ordering has been erased; a **chain that shortens**, which cannot
happen honestly; and a **silent restart** (uptime going backwards), with text
deliberately stable so adaptation shows it once and then CLEARs. A configured
peer missing or dropped is INFO, not an alert. Everything reports; nothing
restarts, blocks or reconfigures on a topology reading — the same boundary P12
draws, for the same reason. `test_a22_topology_vigilance.py` 21/21 ×2 in the
cloud and **21/21 over the bridge on L's machine**; its three guards
mutation-tested (drop `/peers` from the protected set, revert the eviction,
revert the record-on-change — each makes its guard fail).

~~**A21. Peers cannot see each other's state.**~~ **DONE v8.33, same run.**
A bounded digest — `{v, src, height, peers, crisis, spike}` — rides the tip-gossip
heartbeat and **nothing else**. Measured: plain `BLOCK_ANNOUNCE` **156 bytes,
unchanged**; heartbeat 172 → 280 (+108), i.e. 0.9 B/s per peer at the 120 s
default. The hot path is untouched deliberately — a block announce is 156 bytes
BY DESIGN (address-event, Mahowald 1992) and putting the digest on every one
would hand back most of what that design buys. **What it must never carry, and
this is the judgement call:** no substrate reading. A peer has no business
knowing this machine's memory; that tells an attacker exactly when a flood is
cheapest, and it is operator information (P12/M31). D1–D6 assert the key set
against the built object AND against the bytes captured off the wire by standing
up a listener and being the node's peer. Every field a peer sends is coerced,
clamped and truncated by `PeerStateTable._clean()`, and the table is capped at
512 peers (T1–T7).

**P13. A pre-fix fixture that exists on one machine took six live checks down
with it — PARTLY FIXED 2026-08-24, the rest is open.**
`test_a20_peer_version`'s C0 asserted *"a pre-A20 source is available to test
against"* — a property of the **test directory**, not of the system under test.
On the machine that produced `covenant_unified_v8.PRISTINE-v8.32.py` it was
green; on a fresh sandbox it is red for ever (M34's disease). Worse, and this is
the part nobody saw: `interop_checks()` **returned early** when the file was
absent, so `wire_digest` was never captured and **D1–D6 did not run at all** —
the six checks on what actually leaves the process, which are the ones that pin
A21's "no substrate on the wire" boundary. Two visible failures were concealing
six absent checks.
**Fixed this run to the extent that is honest:** the wire capture needs only a
NEW node, so it is decoupled and now always runs (13/13 against v8.35, D5 read
off the wire). C1–C5 report through a new third outcome, `not_run()`, which the
summary prints as *"1 section(s) NOT RUN — do not read this as covered"*, so a
green sweep can never be mistaken for full A20 verification.
**Still open:** the interop measurement is **dated 2026-08-23** and cannot be
re-verified anywhere. Fix shape: replace the binary fixture with a **synthetic
pre-A20 peer** — a small script that speaks the P2P frame and replies *without*
`v`/`src`, which is the only property C1–C5 need from an old node — turning a
one-time measurement into a standing check. **Do not fabricate a file named
`PRISTINE-v8.32`**: a fake pristine artifact is how a false claim gets a hash.

~~**P16. Adaptation removed the noise and the heartbeat with it.**~~ **DONE
2026-08-24, same run, after it happened live.**
P12's `Adaptation` is right and its cost was never written down. The 3,448
redundant ALERTs it suppresses were noise — **and they were also proof of life.**
A flooding watchdog is provably alive. A quiet one is not, and nothing in the
file distinguished *quiet because healthy* from *quiet because dead*.

**Observed, not hypothesised, ninety minutes after P14 shipped.** L stopped the
consoles. Measured at 08:05:58Z:

```
last watchdog line   2026-08-24T08:03:12Z  "node A ... node B ... (healthy)"
rounds since         two missed (08:04:1x, 08:05:1x) -- the process is gone
NODE_RESTART.txt     unchanged, mtime 08-23 01:39 -- the restart never ran
logs/nodeB.log       ends in ^C            -- node B took a real interrupt
nodeB_prod.db-shm    absent                -- clean SQLite close, B exited
nodeA_prod.db-shm    still present, 07:39  -- A's python may be ORPHANED (P3)
```

**The last line the watchdog ever wrote asserts that both nodes are healthy.**
That line is now permanent, and it is a claim about 08:03:12 that reads, to
anyone opening the file afterwards, as a claim about the present. A monitor that
dies silently reports health for ever — and the quieter Adaptation makes it, the
longer that false present lasts.

**The fix is one line of contract, not new machinery.** The roll-up already
guarantees output every `ROLL_UP_EVERY` rounds; what was missing is that no
reader could know the interval, so no reader could judge a gap. The startup
banner now states it:

```
watchdog source c228ac0a629d -- this file writes at least one line every 30
rounds (~30 min) even when nothing changes. A LONGER GAP THAN THAT MEANS THIS
PROCESS IS DEAD, not that all is well.
```

**A note against my own change, because §0 says report honestly especially
against yourself:** this makes the gap *readable*, it does not make it *checked*.
Nothing yet compares `watchdog.log`'s mtime against now — and the only thing
positioned to do that is something outside the watchdog. That is the next
instance of P14's pattern (*nothing checks the thing that checks*), and it is
filed with P15 rather than pretended closed here.

---

**P15. There are FOUR long-lived processes and the judge is the unwatched one.**
Opened 2026-08-24 as P14's falsifiable prediction, not as a hunch — P11, P12 and
P14 are the same defect three times (a long-lived process whose identity nothing
reports), so the honest next move is to enumerate the population rather than wait
for the fourth to bite. It is:

| process | identity reported? | by what |
|---|---|---|
| node A | yes, since v8.31 | `/health.source_sha256`, boot banner (P11) |
| node B | yes, since v8.31 | same |
| watchdog | yes, since 08-24 | `self_drift_report` (P14) |
| **ollama** | **no** | — |

`covenant_watchdog.py` mentions ollama exactly twice, and both are in
`start_node`: a default URL and the script name. It **launches against** the
judge and never **probes** it. Nothing anywhere reads `GET /api/tags` or
`/api/ps`, so nothing can say which model is answering, whether the served tag
still resolves to the same digest, or whether the endpoint is up at all — and
this process is not peripheral: it **is** the ethics gate, and it sits inside
consensus. The live nodes report `judge=quorum(local:0,mock_selfreport:0)`, so
`local:0` is one ollama call and the other bucket is the sender's own word (B2).

**The prediction, and how to falsify it.** If the pattern is real, then
re-pulling or re-tagging `qwen3:8b` changes what the gate decides and **no
surface in this system says anything changed**. That is one command to test
(`curl :11434/api/tags` before and after) and it either produces a digest the
node never mentions, or it does not. The cheap fix if it holds: the watchdog
records the served model and its digest each round, alerting on **change**, not
on state — the P12 shape, and disclosure only, never a refusal.

**Not started.** Needs the Windows host (DE6), so it queues behind the restart.

---

**P17. A restart can take the chain down and LEAVE it down. Two correct scripts,
one hazard that neither can see.** Opened 2026-08-26 ~19:30 by reading the call
chain before running it (M44), not by being bitten.

`AB_RESTART_NODES.bat` — the file P3 exists to praise, and it is right about
what it was written for — stops the nodes properly (by title with `/t`, then by
PID from `netstat -ano`, then asserts the ports are free) and **then** calls
`covenant_prod.bat`. And `covenant_prod.bat` opens with, correctly:

```
curl -s -m 8 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "ABORT: Ollama not answering on 11434. A judge that cannot be
               reached fails CLOSED - every transaction rejected."
  exit /b 1
```

Neither is wrong. **Composed, the stop always succeeds and the start may
refuse**, so a machine that was serving a chain a minute ago is serving nothing,
and the only notice is a line in a console that scrolls past into
`NODE_RESTART.txt`. The judge is a 5.2 GB local model with a 30-minute
keep-alive on a box P12 measured at 3,535 MB free — "Ollama is not answering
right now" is not an exotic state, and **`AB_RESTART_NODES.bat` is the exact
double-click this log has been telling L to perform since 08-24.**

**Partly mitigated the same run, in the layer that could hold it.**
`verify_deploy.py` gained step **2b**: probe `/api/tags` BEFORE the restart, and
refuse — as a FAILURE, not an unknown — to stop a running node over a judge that
is not there. It also warns when Ollama answers but lists no models, because
`covenant_prod.bat`'s next line is `judge_bench.fit_check()` and that aborts
too. So the `AM_VERIFY_AND_RESTART.bat` path is safe.

**Residual, and it is the more likely path:** the bare `AB_RESTART_NODES.bat`
double-click is unchanged and still exposed. Fix shape, small and L's file:
probe 11434 in `AB_RESTART_NODES.bat` itself before the first `taskkill`, and
refuse. That is strictly tightening — it can only decline to stop something —
but it is L's operational script and P3 says a change to one deserves a
deliberate yes. **A stop that cannot fail composed with a start that can is not
a restart; it is a stop.**

---

~~**P14. The watchdog checked every process except itself.**~~ **DONE
2026-08-24 (`self_drift_report`, 33/33).**
`source_drift_report()` was written on 2026-08-23 at 07:39 for one purpose: to
ALERT when the source the NODES loaded is not the file on disk — *"the file was
updated and the node was never restarted"*, the failure that cost this project
fourteen versions (M25). Measured on the production machine on 08-24, it had
**never executed**:

```
watchdog started      2026-08-23T01:39:52Z   <- the running process
covenant_watchdog.py  mtime 08-23 07:39      <- SIX HOURS LATER
grep -c 'unchanged,' logs/watchdog.log  -> 0 <- no Adaptation either
grep -ci 'CLEARED'   logs/watchdog.log  -> 0
```

The process that would run the staleness check started six hours before the
check was written, and was still running 29 hours later. **The control against
"deployed is not running" was itself a case of it** — and a stale monitor is
worse than an absent one, because it keeps producing confident lines. The cost,
in the log it was writing the whole time: 12,538 lines, **3,456 ALERTs of which
3,448 are two permanent win32 facts** repeated once a minute per node. The eight
that were news — node B down, node B unreachable, a peer unreachable ×4, an
anomaly spike ×2 — are buried **431:1** by the noise `Adaptation` was written to
remove.

**Why it was structural, not an oversight.** Every check in the file takes its
subject as an argument — a port, a health dict, a hash — and **nothing passes it
itself**. Fixed by giving it one:
`SELF_SOURCE_SHA12 = disk_source_sha12(SELF_SRC)` captured **at import** (what
this *process* loaded), compared each round against the file on disk by
`self_drift_report(loaded, on_disk)`, a pure two-hash function wired in beside
the node-side check.

**Disclosure only, pinned.** It restarts nothing, refuses nothing and changes no
verdict — P12's boundary for the substrate sensor, B2's for the quorum report. A
watchdog that restarted *itself* on a hash change would be a watchdog any file
write can make execute new code; `test_p14` §C asserts the function body
contains no `start_node`, `Popen`, `taskkill`, `os.remove`, `sys.exit` or
`raise`. The alert text is deliberately **stable** while the condition holds, so
`Adaptation` emits it once and then CLEARs it (M34) — §B proves it against the
real class: 1 emission in 29 rounds, then `CLEARED after 29 round(s):`.

**`test_p14_watchdog_self_drift.py` 33/33 — on LINUX only.** The suite is pure
functions (no node, no socket, no key), but it ran in the `device_bash` VM,
which is not where the node runs. M29 applies in full and DE6 says why. **It has
not run on win32 yet**; that happens in the first post-restart sweep.

**Open follow-on:** the check cannot fire until the watchdog is restarted, which
is the same DEPLOYMENT item it exists to police. Until then it is code on disk —
exactly the state it was written to detect.

---

## R. RADIO BEARER — LoRa as a path into the mycelium

**R1. LoRa can carry the mycelium's ANNOUNCE. It can never carry its PAYLOAD.**
Opened 2026-08-26 ~19:50 on L's instruction — *"we also want to be able to
access lora radios as a potential bridge to the mycellium"*. Measured before
designing anything, because the whole question turns out to be arithmetic.

**INCREMENT 1 BUILT 2026-08-26 ~20:15 — the frame codec, and it changes nothing.**
L, mid-run: *"we want lora integration not removal of other aspects."* That is
the governing constraint and it is also the only way §0 permits this, so it is
built in: `claude/covenant_lora_frame.py` is a NEW FILE that imports nothing
from the node (pinned by R8a on tokenized source), opens no socket, reads no
env var, and is never called by the TCP path. JSON over TCP is byte-for-byte
what it was and remains the ONLY transport that can carry a block. No bound,
verdict, route or refusal changed anywhere.

`claude/test_r1_lora_frame.py`, **58/58, twice in the cloud and 58/58 against
the deployed bytes on L's own machine** (python 3.10, the `device_bash` VM —
this is the pure-function class DE6 says CAN run there). Measured:

| frame | JSON today | binary | fits |
|---|---|---|---|
| `BLOCK_ANNOUNCE` | 148 B | **40 B** | **EU868 SF12 (51 B) — the worst legal case** |
| heartbeat + A21 digest | 268 B | **55 B** | DR2 (125 B), with the digest INTACT |
| heartbeat, spiking + crisis | 311 B | 93 B | DR2 |
| `BLOCK_REQUEST` | 76 B | 8 B | everything |
| `TX_ANNOUNCE` | 134 B | 39 B | DR1 (53 B) |

§R3 is the pre-fix record and it is the justification: the JSON announce fits
DR3 and **nothing below it**, so on the shipped encoding a radio link works
until the first data-rate step-down and then goes silent. The binary announce
survives two.

**Three design decisions, each of which could have been a relaxation and is
not.** (a) The block hash is carried WHOLE. Truncating to 16 bytes was priced —
the announce is only a dedup key and `_accept_block_common` validates the real
block — and rejected for one reason: **it is not needed**, the full-hash frame
already fits SF12. An option that weakens a field, bought for headroom nobody
is short of, is how a relaxation enters a codebase. R8e pins that no identifier
implements it, R8f pins that the "truncated" REFUSAL messages are still there,
and R8g injects a `truncate_hash` parameter and requires R8e to fail against
it. (b) Degradation is explicit: when a frame will not fit, the only thing
dropped is the digest's spike-KIND list, `FLAG_SPIKES_ELIDED` records it, and
the decoder returns `spikes_elided: True` with NO `spike` key — an absent list
and an empty list are different claims, and conflating them is how a monitor
learns to report calm it never measured (P16's disease, in a codec). If it
still will not fit, `encode()` RAISES rather than sending a partial event.
(c) `BearerProfile` makes A5's exile bug impossible to stumble into: a bearer
DECLARES `can_carry_blocks` and `synchronous_ack` rather than being discovered
to lack them, and R7c/R7d/R7e assert that no LoRa profile claims either while
TCP claims both.

**Deliberately NOT wired into `run_all_tests.sh` or `run_local_sweep.py` yet,
and the reason is a small proof that the verifier works.** Both files are
sha256-pinned in `verify_deploy.py`'s MANIFEST; editing either right now would
make `AM_VERIFY_AND_RESTART.bat` report MISMATCH and **correctly refuse to
restart**. The runner wiring is the first thing to do AFTER the restart, with
the manifest updated in the same edit.

**What is still open is all of the integration.** The codec is the piece that
needed no hardware and no decisions; the three collisions below are the actual
work, and A23 is the one that would silently kill the whole thing.

**The frames, constructed from the delivered v8.37 source's OWN key sets**
(`announce_block`, `build_digest`, `_reply`), a real 64-hex hash, `json.dumps`
exactly as the node does it:

| frame | bytes |
|---|---|
| `BLOCK_ANNOUNCE` — the hot path | **148** |
| `BLOCK_ANNOUNCE` + `gossip` tag | 164 |
| heartbeat = announce + A21 digest | **268** |
| heartbeat carrying 2 spike kinds | 309 |
| `BLOCK_REQUEST` | 76 |
| `TX_ANNOUNCE` | 134 |
| ACK reply (A20-stamped) | 70 |

**Against LoRaWAN US915 application payload** (Things Network regional
parameters: DR0 11 B, DR1 53 B, DR2 125 B, DR3 222 B, DR4 222 B; 400 ms dwell
on channels 0-63; **no** duty cycle in the US, unlike EU868's 1%):

- a 148-byte announce fits **DR3/DR4 only**. It does NOT fit DR2 (125 B) — and
  DR2 is where a link lands as soon as range or noise costs it one step down.
- the **268-byte heartbeat fits nothing.** The A21 digest cannot ride a radio
  as it stands. Consistent with A21's own reasoning: the digest rides the
  heartbeat *and nothing else* precisely to keep the announce small. The radio
  wants that same discipline one notch tighter.
- `MAX_BLOCK_BYTES` is 8 MiB. At Meshtastic LongFast (1.07 kbps) that is
  **17.4 hours of continuous airtime**; under EU868's 1% duty cycle, **72
  days**. Even one `MAX_TX_BYTES` transaction (16 KiB) is 122 s continuous,
  ~3.4 h duty-limited. Block transfer over LoRa is not slow. It is
  arithmetically out of the question, and no amount of engineering moves it.

**So the architecture is forced — and this system already has it.**
`announce_block` is address-event BY DESIGN (Mahowald 1992, in its own
docstring): emit the address, let the receiver look up what it means and fetch.
That is exactly the split a radio bearer needs. **LoRa carries "block N with
hash H exists, ask someone"; the fetch happens over IP.** A radio-reachable node
that has lost its internet still learns the chain moved and knows precisely what
to ask for when it returns — partition tolerance, landing on A13's existing
`peer_ahead` path rather than inventing one.

**The seam is two functions, which is the good news.** Outbound announces have
exactly ONE call site (`_send_announce` -> `_send_raw`, line 6252); inbound is
`_listen_for_peers`. The fetch paths (`request_missing_blocks`, the tx fetch)
stay on TCP **by construction** — which is what the physics demands anyway.

**Three collisions with controls this loop has already shipped. These are the
work; the radio is not.**

1. **A23 vs. a bearer with no synchronous ACK — the blocking one.** `_send_raw`
   now treats "no parsed reply" as non-delivery: `_note_send_failed`, backoff.
   A LoRaWAN Class A downlink arrives in a receive window *seconds* later, and a
   Meshtastic broadcast has no application ACK at all. So **every LoRa peer
   would be marked failing on its first send and stay suspect**; A12 would
   withhold its heartbeats after `PEER_SUSPECT_AFTER`=3; and A13's reply-height
   probe — the only mechanism by which a one-way peer EVER syncs — would never
   fire, because there is no reply to read. A LoRa peer is precisely the
   one-way shape A13 was written for, with A23 suppressing the cure. A23 is
   right for TCP and must become **per-bearer**: a bearer that declares no
   synchronous ack cannot feed `PeerHealth` the same way. **Do not fix this by
   relaxing A23 for everyone** (§0).
2. **A15/A5 constants are per-process, not per-bearer.** `PEER_SEND_TIMEOUT_S`
   is 5 s — shorter than a single SF12 transmission. `MAX_EXCHANGE_S` is 60 s.
   `MAX_PEER_MSG_BYTES` is 64 MiB. A bearer needs its own ceiling and its own
   clock, and A5's import-time relation must hold WITHIN each bearer.
3. **A5's exile bug, in radio form.** A LoRa-only peer can receive no block this
   node may legally mine. So it is announce-and-fetch-elsewhere by construction,
   or it is a peer that can never catch up — and A5's whole lesson is that the
   second state is a liveness bug with an attack attached. **A bearer must
   declare what it can carry, and the node must refuse to treat a
   notification-only peer as a sync peer.**

**One lever already exists and is exactly the right one.** C4 identified
`COVENANT_TIP_GOSSIP_INTERVAL=600` for the phone's radio budget. Run it for
LoRa: a 148 B announce at 1.07 kbps is ~1.1 s of airtime, so at the 120 s
default a single link sits at ~0.9% duty — **right on the EU868 limit, for one
peer.** At 600 s it is 0.18%. The knob C4 found for a different radio is the
knob this needs.

**DECISIONS FOR L, before any code.**
- **Hardware:** any on hand, or is this "can we"? Everything below depends on it.
- **Which stack:** (a) **LoRaWAN** — needs a gateway and a network server, gives
  regional compliance for free, imposes Class A downlink windows, and is the
  WORST fit for A23; (b) **raw point-to-point LoRa** over an SX1262 on serial —
  full control of timing and framing, no infrastructure, cleanest map onto a
  bearer interface; (c) **Meshtastic** — an existing routed store-and-forward
  mesh with its own addressing, ~200-230 B payloads and a ready serial/BLE API.
  **(b) or (c) recommended** — (c) if a mesh already exists nearby, (b) if this
  is two known sites at a known distance.
- **Goal:** partition tolerance (the node has internet *usually*), or reaching a
  site with none at all? The second drags in the judge: the ethics gate is a
  5.2 GB local model sitting INSIDE consensus (B4, P15), and a radio-only node
  still has to run one.

**Not started; nothing in the node was changed.** Adding a transport changes how
blocks propagate, so A7's protocol-version question applies the moment a second
operator exists. Regulatory, one line: stay on the ISM allocations (915 MHz US,
868 MHz EU, 433 MHz Region 1) where encryption is unremarkable — the US
**amateur** allocation forbids messages encoded to obscure their meaning
(47 CFR 97.113(a)(4)), which the covenant's signed frames would violate.
**Unverified figure, flagged rather than smoothed over (M40):** Meshtastic's
exact maximum payload (~200-237 B) was not pinned to a primary source this run.
The LoRaWAN numbers above ARE — Things Network regional parameters — and the
frame sizes are measured from the shipped source, not quoted.

---

# 5. Run log — append, never rewrite

**DONE 2026-08-26 ~09:15.** The two oldest entries (02:00 08-24 B2, and
07:00→07:45 08-24 P14/delivery) were moved **verbatim** to
`claude/RUN_LOG_ARCHIVE.md` — 564 lines, nothing edited — with their one-line
index rows left below. §0 was hashed before and after the move and is
byte-identical (`d635317a079a`). The previous run recorded not doing this as a
deliberate omission because "moving a record is a two-file edit and doing it
badly loses more than the reading cost it saves"; the way to make it safe is
to do it mechanically with an assertion on §0, not to keep deferring it. This
file: 3,388 → 2,826 lines before this run's own additions.

**The last 3 runs are here in full. Everything before them is in
`claude/RUN_LOG_ARCHIVE.md`, verbatim and unedited** — moved 2026-08-24 under
M36, because §5 had grown to 56% of this file and every run read all of it.
The index below is the whole archive, one line each; read the archive for the
one run you need.

## ARCHIVED RUNS — index

- 2026-08-21 ~01:45 — loop made self-improving; A1 investigated and blocked
- 2026-08-21 ~01:35 — D1 started; fetch method proven and characterised
- 2026-08-21 ~01:30 — loop created
- 2026-08-21 ~05:35 — A1a and A2 both closed (v8.15); verified live, twice
- 2026-08-21 ~06:05 — A3 closed for real (v8.16); an earlier "done" was false
- 2026-08-21 ~06:50 — A5 closed (v8.17); the A3 cap was 7× too small for honest traffic
- 2026-08-21 ~07:45 — A4 closed (v8.18); the injection matrix found six accepted-when-it-shouldn't classes
- 2026-08-21 ~09:30 — A9 closed (v8.19); the relay gap it found, and DE1 corrected
- 2026-08-21 ~10:30 — A1 closed (v8.20); the miner-killed-after-mine case had no path home
- 2026-08-21 ~11:45 — A6 and A11 closed (v8.21); the heartbeat was quietly erasing link conductance
- 2026-08-21 ~13:00 — B1 and B3 closed (v8.22); the "fixed" parser fixes were never in the node
- 2026-08-21 ~23:30 → 08-22 ~00:15 — A12 closed (v8.23); the dead-peer cost was head-of-line blocking first, pool saturation second
- 2026-08-22 ~00:40 — DUPLICATE run: A12 re-done off a stale log snapshot; no new item closed
- 2026-08-22 ~00:47 — (UNLOGGED run, reconstructed at 01:40) B5 measured, test + runner shipped, log write-back never landed
- 2026-08-22 ~01:40 — B5 closed: the unlogged measurement verified, plus v8.24 (refusals by a DOWN judge are now visible on both block paths)
- 2026-08-22 ~03:00 — A13 closed (v8.25): one-way reachability now syncs; the reply every announce threw away was the only signal
- 2026-08-22 ~04:15 — A14 closed (v8.26): the boot probe was sequential, and — worse — a trickling peer held it forever
- 2026-08-22 ~05:30 — A15 closed (v8.27): the readers were unbounded in time — and the inbound ones had no timeout at all
- 2026-08-22 ~06:20 — No-regression sweep on v8.27 as held by the project; pushback on the "close nothing" plan; D1-XLM closed
- 2026-08-22 ~06:45 — (attended continuation of 06:20) D1-SOL and D1-XRP closed; yield audit opened A16 with measured evidence; no node source change
- 2026-08-22 ~08:00 — (attended, same session) D2 closed on three assets; E1 power probe; A17 found and fixed (v8.28) — the phone-over-VPN shape never synced
- 2026-08-22 ~07:15 — D1-HBAR closed (408 bars); SOL/XRP independently re-verified; a concurrent run detected and not duplicated
- 2026-08-22 ~07:14 — (the 07:45 run's note) the six docs written at 07:14 belong to the attended run whose entry is dated ~08:00 above
- 2026-08-22 ~07:45 — 07:14 run verified and logged; D1-ADA closed (598 bars); D2 regime verdict holds on a second seed and a fourth asset
- 2026-08-22 ~08:45 — D1 closed for every held asset (seven symbols in one run) and D2 regime verdict on all ten; the WebFetch detour was never necessary
- 2026-08-22 ~12:30 — (ATTENDED, L-started) the loop was open at the PC end for sixteen runs; closed it, then closed D3, D4, C1 and W1 with the files it unblocked
- 2026-08-22 ~14:20 — (attended continuation) the daily check has been switched off by a measurement error since 08-20; the network was never blocked
- 2026-08-22 ~21:10 — (ATTENDED, L-started) "fully integrate and run local": the suites had never been delivered, waitress was never installed, `covenant_prod.bat stop` does not stop a node — and the sweep leaked a node that then blocked the restart
- 2026-08-22 ~23:20 — (ATTENDED, L-started) "improve following principles": running it where it runs found three real defects, two of them in the sandbox that gates code proposals
- 2026-08-23 ~03:10 — (ATTENDED, L-started) "complete the loop": the loop had a third layer nobody could see — the node could not say which source it was running
- 2026-08-23 ~06:15 — (ATTENDED, L-started) "act as an antenna": the system senses a great deal and almost none of it returns into the system — P12 closed on all three fronts
- 2026-08-23 ~06:40 — (ATTENDED, L-started) "broadcast": the transmitting half — A20 and A21 closed, and the wire-capture test found a node that booted fine and never spoke
- 2026-08-23 ~07:00 — (L authorised one item, then went to rest) A22 closed; and reviewing the surface I added ninety minutes earlier found two defects in it, one of them my own lesson unlearned
- 2026-08-23 ~07:45 — "implement": P8 and P10 closed, P7 instrumented — a sweep cannot tell you anything until it is quiet
- 2026-08-23 ~08:30 — C5: the Android on-device privacy layer, COMPILED rather than described; and it collides with C3
- 2026-08-24 ~02:00 — B2 closed (v8.35): the diversity check had never once constrained a running node, and one of its two "judges" was the sender's own word
- 2026-08-24 ~07:00 → ~07:45 — (attended) the delivery actually landed, hash-verified on the target for the first time; P14, P16, the restart onto v8.35, and the first Windows sweep

---

### 2026-08-24 ~22:50 → ~23:20 — (attended, L: "just continue refining") SEM1: the cross-register number was measured against the weakest null available

**No source.** Today's three semantic files (11:10, 12:33, 14:05) record no
corpus, no seed, no space id, and none appended here. Unverifiable, so rebuilt
whole. → **M40**.

**The claim.** `P@10=0.21 n=33` beside `random 0.00067`. Both true; the
comparison carries no information — uniform-random does not know how the words
are spelled, and **two of the three hits that eval showcased are identical
strings** (`gold->gold#1`, `secret->secret#1`).

**Rebuilt**: Gutenberg, deterministic sample of each whole catalogue (seed
20260824, size-matched ~3.1M words en/fr/de/es — the lowest-id corpus gave
English the Bible and French novels, a register mismatch inside an eval named
CROSS_REGISTER); PPMI ±4, SVD-300; Procrustes on 4,000 anchors; CSLS; MUSE
gold; **600** held-out English words of rank ≥4,000, not 33.

```
                       en->fr   en->de   en->es
aligned space P@10      0.078    0.077    0.083
SPELLING ONLY P@10      0.527    0.210    0.443   <- median rank 7 on French
frequency only          0.002    0.000    0.002   <- MY hypothesis; refuted
permuted anchors        0.0010   0.0007   0.0008  <- 0/20 shuffles above 0.005
non-cognate subset:  spelling -> 0.000 everywhere, the space does not move
```

**So: spelling beats the space 3-7×, and the space is still real.** The two
signals are disjoint — on the half where spelling scores exactly zero the space
holds its ~8%, e.g. `chill->froid#2`, `epistle->brief#3`, `dew->rocío#6`.

**Two corrections.** (1) The per-language spread (fr .42 / de .12 / es .00 at
n=12/8/13) was noise — at n=600 the three Wilson intervals overlap completely.
**M39 in a different costume.** (2) The governing variable was never looked at:
P@10 decays monotonically with source frequency rank (0.16 → 0.02), same shape
in all three languages.

**SEM2, predicted before the run:** the anchor curve has not flattened (fr P@10
.010/.038/.055/.065/.078 at 250/500/1k/2k/3.2k, median rank halving per
doubling). If 10k anchors and 10M tokens do not pass P@10 ~0.15, I am wrong and
the method is the problem.

**Shipped:** `claude/SEMANTIC_NULLS.md`, `claude_CROSS_REGISTER_EVAL_v2.txt`,
and the part today's earlier runs skipped — source in `claude/semantic/`, with
`CORPUS_MANIFEST.json` and a per-space signature (`en c59189695f62`,
`fr b1c6c2daab9a`, `de bfc05bd42661`, `es a7aed4664fb6`).
**SEM3** left open: `SEMANTIC_CORE_PROBE`'s contrast-axis test C is n=3 with no
null. Node/ledger/trading untouched; the v8.35 restart is still one double-click.


---

### 2026-08-26 ~01:00 → ~01:30 — (scheduled, unattended) A23 closed (v8.36): the fix WAS firing; the line above it was erasing the evidence

**Item choice.** Fresh log read at boot and again here (M15) — no concurrent
run; the log's last entry is still SEM1. Two project docs are newer than the log
and unrecorded (`claude_phil_*`, 08-25 09:00/09:36); noted in the banner, not
re-done (M16/M23). Section A outranks D and A23 was the only A item that is
neither closed nor L's. It was filed as *needs one Windows run* — and DE6 plus a
scheduled session means no Windows. **The escape hatch was taken as a
hypothesis, not a verdict (M35):** the Windows *symptom* is a peer whose port
completes the handshake and never answers, and that is fifteen lines of listener
that runs anywhere.

**Measured before writing anything.** `probe_a23.py`, real `_send_raw`, real
health table, four peer shapes. The filed entry's conclusion — *"the A18 fix is
not being reached"* — is **false**: it is reached on the first send, records
`peer_send_failure`, arms a backoff. What was broken is three lines above it:
`_note_send_ok()` on `sendall()`, clearing the counter `_note_send_failed()` was
about to set. Five consecutive total failures to an accepting-silent peer left
`k=1` and one interval of backoff **for ever**; five to a REFUSED peer reached
`k=5` and 16×. A peer delivering nothing was accounted healthier than one that
says so, and A12's 508 → 11,520 headroom is bought entirely by that escalation.
A second defect fell out of the same probe: a **non-JSON reply** returned `None`
in silence — which is what `--peers` pointed at a Flask API port looks like
after boot, when preflight is no longer watching (M4, A2).

**Fix v8.36 `dd613fc534e0` (9,631 lines), tightening only.** `_note_send_ok`
moved to the parsed-reply path; unparseable ACK → `peer_ack_unparseable` +
counted, not retried; `_note_peer_contact` unchanged so recovery is still heard
in one tick. No verdict, route, bound or refusal changed. §0 held: this makes a
failure detector stricter and adds a record; nothing was relaxed to make a test
pass, and the K1/K3 red is **not** claimed fixed.

**`claude/test_a23_ack_health.py` 24/24 ×2. PRE-FIX RECORD 16/24 on pristine
v8.35** (S2 ×3, S4 ×2, S6 ×3 name the fix; the other 16 pass on both files and
are the record of what was already right). §S6 asserts on
`inspect.getsource(_send_raw)` so the defect cannot be reintroduced quietly.
Two of my own checks failed on the first run and both were mine, not the node's:
a knife-edge ratio (M34, in the very run that quotes M34) and a fixture whose
fake reply carried a wrong `src` and so was measuring A20.

**Full sweep, green: 31 suites, 994 checks, 0 failures, 6m07** on 2 vCPUs,
batched ≤7 fast / ≤5 slow (M20). a11 23, a12 21, a13 25, a14 15, a15 14, a17 6,
a1_kill 30, a1a_a2 15, a20 13, a22 21, **a23 24**, a3 7, a4 60, a5 20, a9 18,
adversarial 21, b1 162, b2 73, b5 31, d3 77, e2e_gift 11, multinode 21, p11 29,
p12 41, p14 33, security_audit 128, w1 24, w2 21, y1 10, sim_order INVARIANTS
HELD, sim_yield (no tally by design). The six send-path-sensitive suites re-run
**alone, a second time**: all green. **Linux only** — M29 applies in full.

**Runner gap closed on the way:** `pc/run_local_sweep.py` did not list
`test_w2_sandbox_platform` (recorded 08-24 as "a gap in the runner, not a pass")
and now lists it and `test_a23_ack_health`, so the next Windows sweep covers
both.

**Delivery (M25) — SendUserFile AND project_write, round-trip hash-verified
(`dd613fc534e0` read back out of the project).** **L must copy into
`C:\\Users\\Lawre\\covenant`:** `covenant_unified_v8.py` (v8.36),
`test_a23_ack_health.py`, `run_all_tests.sh`, and `run_local_sweep.py` (over the
one already there). `covenant_unified_v8.py` needs `covenant_path_pattern.py`
beside it (already there); `test_a1_kill_matrix.py` imports
`test_a9_relay_race.py`. **Then restart** — the running nodes are v8.35 at best,
and A23 has never executed on the platform it was written for. This was a
scheduled cloud run: **no device bridge**, none was attempted (M5/DE2).

**Cost:** ~⅔ session. A fifth on staging 37 files and the probe; a fifth on the
fix and its suite; a fifth on the pre-fix record and two full sweeps; the rest
on delivery, the runner gap and this entry.

**Dead ends.** None new.

**Next.** Still L's, unchanged: **A10**, **A16** (Option A), **B4**, the **A12
consolidation**, **A7/A8**, **P2**, **P3**, **P9** (which the Windows sweep
showed hard-blocks `authorize_mainnet_payment`), C5's README §7. Unblocked code
work in order: **P13** (synthetic pre-A20 peer), **A3's send-side follow-on**
(now the only open A item, and adjacent to this run's code), **C2**, then
**D3a**, **D5**, **D6**. Highest-value action overall is still not code: **copy
v8.36 across and restart**, then run the Windows sweep — A23, P14 §win32 and the
K1/K3 question all wait on it.


---

### 2026-08-26 ~08:15 → ~09:30 — (scheduled, unattended) A3's send-side follow-on closed (v8.37): the backlog line that said "small, and self-limited" was the reason nobody looked

**Item choice.** Log re-read fresh at boot and again at write-back (M15):
`created_at` unchanged at 02:02:14Z both times, so no concurrent run has
written here. `fetch46.py` (07:38Z, 37 min before boot) joins the two
`claude_phil_*` docs as newer-than-the-log — all three are SEM-family, and
`fetch46.py` fetches the corpus ids the manifest names, so it is plausibly an
**in-flight** run (M23). That settled the choice: take a Section-A item and
stay clear of it. Every other A item is closed or L's; **A3's follow-on was
the only unblocked one**, and it is adjacent to the code the last run touched.

**Measured before writing a line (M41), and the backlog's own wording was the
defect.** "Those are outbound and self-limited by what this node builds" is a
sentence that tells the reader not to bother. Three measurements say otherwise
— the numbers are in §4's A3 entry and the suite's docstring, in short:
a peer sizes the `TX_REQUEST` we build (**204,872 bytes** from a 64-char
honest maximum, on a fetch-pool worker `bootstrap_chain` needs); an over-cap
frame was transmitted **3× / 897 KB** to a peer obliged to refuse it, and then
**A23's new rule blamed that peer for it** (k=1); and A5's relation bounds the
payload while the receiver's cap applies to the frame.

**The second of those is one run old and is mine.** A23 shipped "a send with
no parsed reply is a failure" last night, correctly. Its edge is that a frame
WE built too large produces exactly that signature. M33 says to audit the
surface you just widened, in the session you widen it; this is the first time
that has been done a run late rather than not at all.

**Fix v8.37 `07e097f3e37f` (9,846 lines), tightening only.** One rule — *never
transmit a frame the receiver must refuse, never blame a peer for one* — three
pure helpers, guards at three send sites and four ingest sites, three new
anomaly kinds, and `FRAME_ENVELOPE_BYTES` extending A5's import assertion to
the frame. §0 held: nothing relaxed, no verdict/route/bound/refusal changed,
and one blame REMOVED from a peer that never earned it. The node boots and
self-reports it: `Covenant Unified v8.37 (source 07e097f3e37f, 9846 lines)`,
`/health` agreeing (P11).

**`claude/test_a3s_send_bounds.py` 49/49 ×2. PRE-FIX RECORD 23/49 on pristine
v8.36.** Four of my own checks failed on the first run and **all four were
mine, not the node's** — two races (reading a listener's frame list while
polling its connection count), and two source-level pins that matched the new
comment containing the words they searched for. The most useful was S5f: it
was written to prove a claim in a comment I had just written, and **disproved
it** — `_fetch_announced` asks from our own height, so a peer's index never
leaves the process. The node comment, the constant's comment and the helper's
docstring were all corrected rather than the check deleted. → **M42**.

**Full sweep on the shipped file: 31 suites, 1,043 checks, 0 failures, 8m10.**
Two reds inside a 5-wide mining batch (`a1_kill_matrix`, `b5_mine_latency`)
passed **2/2 alone** — M20 held, and 5-wide turns out to be too many on a
2-vCPU box, so M20 gains a per-CPU amendment. The eight send-path-sensitive
suites were re-run **alone** afterwards: a9 18, a11 23, a12 21, a13 25, a14
15, a17 6, a23 24, a3s 49. **Linux only** — M29 applies in full.

**Delivery (M25) — SendUserFile AND project_write, round-trip verified by a
fresh subagent reading the bytes back OUT of the project (`07e097f3e37f`,
`bd0ab67ae2f6`, `5727b42d1ed8`, `309053b11eda`, all four `cmp`-identical at
full length).** **L must copy into `C:\\Users\\Lawre\\covenant`:**
`covenant_unified_v8.py` (**v8.37**), `test_a3s_send_bounds.py`,
`run_all_tests.sh`, and `run_local_sweep.py` (over the one already there).
`covenant_unified_v8.py` needs `covenant_path_pattern.py` beside it (already
there); `test_a1_kill_matrix.py` imports `test_a9_relay_race.py`. **Then
restart** — the disk is on v8.35 and **two** versions of send-path work have
now never executed on the machine that runs the chain. No device bridge in a
scheduled run; none was attempted (M5/DE2).

**Loop work.** The archive move §5 asked for was done: the two oldest entries
moved **verbatim** to `RUN_LOG_ARCHIVE.md` (564 lines), index rows left
behind, §0 hashed before and after and byte-identical — 3,388 → 2,826 lines
before this run's own additions. Three methods: **M42** (a data-flow claim in
a comment can be wrong at birth; pin it against tokenized code, not source
text), **M43** (a round-trip check that reads its own input is not a check),
and **M20 amendment 3** (batch width is a ratio to vCPUs; a starved
freshness-window failure reads as an *authentication* error, not a timeout).

**Cost:** ~⅔ session. A fifth on staging 45 files and the probe; a fifth on
the fix; a quarter on the suite, its four self-inflicted failures and the
pre-fix record; a fifth on the sweep and re-running two reds alone; the rest
on delivery, verification, the archive move and this entry.

**Dead ends.** None new.

**Next.** Still L's, unchanged: **A10**, **A16** (Option A), **B4**, the **A12
consolidation**, **A7/A8**, **P2**, **P3**, **P9** (which the Windows sweep
showed hard-blocks `authorize_mainnet_payment`), C5's README §7. **Section A
is now fully closed or L's** — so by rule 1 the next run is free to take P or
D. In order: **P13** (synthetic pre-A20 peer — it turns a dated measurement
into a standing check), **P15** (ollama, the fourth long-lived process, needs
the PC), **C2**, then **D3a** (`execute.py` / `paper_run.py` do not exist),
**D5**, **D6**. Someone should also read the three `claude_phil_*`/`fetch46`
docs' headers and log them on their run's behalf (M16). And the highest-value
action overall is still not code: **copy v8.37 across and restart**, then run
the Windows sweep — A23, this run, P14 §win32 and the K1/K3 question all wait
on it.

**ADDENDUM ~10:00 → ~11:05 — "refine and prepare for propagation". Two findings
in v8.37's own new surface, and a propagation check that proves all three claims
instead of asserting them.**

**The adversarial pass first (M33), because the lesson from A23 was that it
arrives a run late.** The three anomaly kinds v8.37 adds are recorded on a path a
PEER triggers at will. Flooding 5,200 garbage `TX_ANNOUNCE`s filled 100 % of the
5,000-event buffer with `peer_tx_id_invalid` and **evicted a planted
`peer_send_failure`** — the phasic signal the buffer exists to keep. Before
claiming I had caused it I ran the identical flood against **pristine v8.36**
through `peer_message_error`: identical result, 5,000/5,000, real event gone. So
it is **architectural and predates every guard here** → **A24**, filed with both
measurements and deliberately NOT fixed, because the fix changes what the spike
detector sees and shipping that into the observability layer in the same hour as
a propagation is exactly W1/M26's shape.

**Then the propagation package, which is what "prepare" had to mean.** The
recurring failure in this project is not the code, it is that project, disk and
running process drift independently (M38) and nobody notices for days. So:
`pc/verify_deploy.py` + `pc/AM_VERIFY_AND_RESTART.bat` ask all three questions in
one double-click and **refuse to restart if the copied files are not what was
built** — sha256 against a manifest, companion imports checked
(`covenant_path_pattern.py`, `test_a9_relay_race.py`), then the restart, then
each node's own `/health` compared against the disk. It fails CLOSED and reports
a node it cannot reach as **UNKNOWN, never OK**; the exit codes are
0 = PASS / 1 = FAIL / 2 = INCOMPLETE, and INCOMPLETE prints "this is NOT a pass".
The launcher follows M28 — all logic in Python, GOTO labels not parenthesised
blocks, grepped for a stray `(` before shipping.

**Every check was mutation-tested (M30), and the running check both ways.** One
byte appended to the core → MISMATCH and it stops before restarting; a companion
deleted → MISSING; a delivered file never copied → MISSING. Then two real nodes
were booted, one on v8.37 and one on pristine v8.36: the first is reported
`ok ... == disk`, the second `MISMATCH (correctly refused)`. **That is the third
claim actually being checked rather than assumed — the first time this project
has had that.**

**And the third self-correction of this session, which is the honest count.**
`verify_deploy.py`'s first draft called a node running exactly the delivered
source a MISMATCH. `/health`'s field is named `source_sha256` and contains
`CORE_SOURCE_SHA12` — twelve characters (→ **A25**). I compared it against a full
64-character digest because I trusted the name. A verifier that cries wolf on a
correct deployment is worse than none; it now compares 12 and says in its own
docstring that the comparison is 48 bits and is a drift check, not a tamper
check. Three times today a claim I wrote was disproved by the check I wrote to
support it (M42's data-flow comment, the setext `---` that would have silently
reformatted an earlier entry, and this). The pattern is consistent enough to be
the method rather than an embarrassment: **write the check that could embarrass
you, then read the failure instead of adjusting the check.**

**Delivered (M25):** `pc/verify_deploy.py`, `pc/AM_VERIFY_AND_RESTART.bat` — by
SendUserFile AND project_write. **L: copy BOTH into
`C:\\Users\\Lawre\\covenant` beside the four v8.37 files, then double-click
`AM_VERIFY_AND_RESTART.bat`.** Nothing else is needed; if the copy is wrong it
will say so and refuse to restart, and if it passes then for the first time the
log's version claim will have been checked rather than asserted.

---

### 2026-08-26 ~19:05 → ~19:50 — (ATTENDED, L-started: "Complete loop update files and run on pc") DEPLOYMENT's disk half closed onto v8.37; the propagation package would have failed its own first run

**Drift outranks the backlog (M25), so the three claims were measured before
anything was chosen — and for once the banner was right.** disk **v8.35
`1207bd2e7dc5`**, mtime 08-24 07:05; running **v8.35 on BOTH nodes**, height 3,
peers 1. Not by forensics this time: the watchdog's own P11 line says it —
`node A v=v8.35 src=1207bd2e7dc5 ... [unchanged, 2310 rounds]`. On 08-24 the
same question cost an evening of mtimes and `-shm` files. P11/P12 paid for
themselves here. A **fourth** long-lived process answered too, unprompted: the
watchdog is running `c228ac0a629d` against `d363d6c2bb5f` on disk and has been
saying so once per roll-up **since 08-24**. P14's self-check works; nobody was
reading it.

**What had not happened: any of it.** `test_a3s_send_bounds.py`,
`test_a23_ack_health.py`, `verify_deploy.py` and `AM_VERIFY_AND_RESTART.bat`
were ABSENT from the machine; the core was v8.35. Two runs' deliveries — A23
(v8.36) and A3-send (v8.37) — plus the whole propagation package had stayed in
the project. **M25 for the fourth time**, and the mechanism is structural, not
anyone's forgetfulness: a scheduled cloud run has no bridge, so every one of
them can only END in a manual instruction, and manual instructions accumulate.

**Delivered over the bridge, `sha256sum -c` verified ON the target** (M25's
attended path, 7/7 OK): `covenant_unified_v8.py` **`07e097f3e37f`, 9846 lines,
`COVENANT_VERSION = "v8.37"`**; `test_a3s_send_bounds.py` `bd0ab67ae2f6`;
`test_a23_ack_health.py` `e2f69d41f29c`; `run_all_tests.sh` `5727b42d1ed8`;
`run_local_sweep.py` `309053b11eda`; plus the two patched scripts below. All
five `.py` `ast.parse` on the deployed bytes. v8.35 kept as
`covenant_unified_v8.PRE-v8.37.py` (`1207bd2e7dc5`).

**Then the part that earned the run: the package built to make delivery
verifiable had never run on the platform it was written for** — M29 in the
mirror, and its own closing sentence said *"Nothing else is needed."* Two
defects, each fatal to its first real use, detail in **M44**: an **LF-only**
`.bat` in a folder where all three neighbours are CRLF, built entirely of
`goto` labels; and `subprocess.run(capture_output=True)` over a launcher that
ends in `pause`, which would have reported a working restart as
`restart launcher failed` after a 300 s invisible wait. Both fixed, both
written back to the project so the next run does not re-ship them.

**And a third, which is a hazard rather than a nuisance → P17.**
`AB_RESTART_NODES.bat` stops the nodes and THEN calls `covenant_prod.bat`,
which aborts before starting anything if Ollama is not answering on 11434.
Neither is wrong alone; composed, **a restart can take the chain down and leave
it down** — and that is the exact double-click this log has prescribed since
08-24. `verify_deploy.py` now asks first (step 2b) and refuses, as a FAILURE,
to stop a running node over a judge that is not there. The bare double-click is
still exposed; that residual is P17's.

**A correction to P13, from looking rather than trusting the entry.** It says
the A20 interop measurement "cannot be re-verified anywhere". Measured:
`test_a20_peer_version.py` already lists `covenant_unified_v8.PRE-v8.33.py` in
`_OLD_CANDIDATES`, and that file is ON the PC — `COVENANT_VERSION=v8.32`, zero
`A20` markers, a genuine un-fabricated pre-A20 binary. C1–C5 have been runnable
there all along, and the next Windows sweep will run those six checks for the
first time.

**RUNNING is still v8.35, and that is this run's honest state.** Computer use
is turned off on the device, so DE7/M39 does not arise — there was no click to
attempt, only a toggle that is L's. Asked for; not yet given.

**Cost:** ~⅓ session. Most of it on the three-claims measurement and on reading
the call chain to its leaves; the delivery itself took minutes.

**Dead ends.** None new. DE6 held exactly as written — `device_bash` is the
Linux VM (`python3` 3.10 there), excellent for `sha256sum`, `ast.parse` and
reading `watchdog.log` live, and unable to run one Windows thing.

**Next.** **The restart, then the Windows sweep** (`run_local_sweep.py`, 33
suites, ≤45 min): A23, A3-send, P14 §win32, the K1/K3 question and now A20
C1–C5 all wait on it. Then **P17** (make `AB_RESTART_NODES.bat` itself refuse
to stop what it cannot start), **P15** (ollama — the PC is reachable right
now), **A24**, P13's sandbox half, **C2**, **D3a**, **D5**, **D6**. Still L's,
unchanged: **A10**, **A16** (Option A), **B4**, the **A12 consolidation**,
**A7/A8**, **P2**, **P3**, **P9**, C5's README §7. And
`TRIGGER_PROMPT_PROPOSED.md` still holds **thirteen unapplied proposals** from
four runs; this was an attended session, which is the only kind that can apply
them (DE2), and the restart was the open question instead. That is now the
cheapest loop-level win available.

**ADDENDUM ~19:50 — L, mid-run: "we also want to be able to access lora radios
as a potential bridge to the mycellium". Opened as R1, measured rather than
sketched, and the arithmetic settles the architecture on its own.**

The frames were constructed from the shipped v8.37 source's own key sets rather
than quoted from A21's old measurement: `BLOCK_ANNOUNCE` **148 B**, heartbeat
with the A21 digest **268 B**, `BLOCK_REQUEST` 76 B, ACK 70 B. Against verified
LoRaWAN US915 payloads (DR2 125 B, DR3/DR4 222 B) the announce fits at the top
two data rates and **the heartbeat fits nothing**; against LongFast's 1.07 kbps
an 8 MiB `MAX_BLOCK_BYTES` is **17.4 hours of airtime**, 72 days under EU868's
1% duty cycle. So LoRa is a NOTIFICATION bearer for the mycelium and never a
transport — which is the split `announce_block` was already built around
(address-event, Mahowald 1992), and the seam is two functions.

**The work is not the radio; it is three collisions with controls this loop
shipped in the last week**, and the first is the interesting one: **A23 would
kill it.** `_send_raw` counts "no parsed reply" as non-delivery, so a bearer
with no synchronous ACK marks every peer failing on its first send, A12
withholds its heartbeats, and A13's reply-height probe — the only way a one-way
peer ever syncs — never fires. A LoRa peer is exactly A13's shape with A23
suppressing the cure. A23 is RIGHT for TCP; it has to become per-bearer, and
§0 forbids the tempting fix of relaxing it for everyone. Full item, the other
two collisions and the decisions L owes it: **§4 R1**.

**ADDENDUM 2 ~20:15 — L: "we want lora integration not removal of other
aspects." Increment 1 of R1 built under exactly that constraint.**

`claude/covenant_lora_frame.py` + `claude/test_r1_lora_frame.py`, **58/58 twice
in the cloud and 58/58 against the deployed bytes on L's machine.** A new file
that imports nothing from the node, opens no socket and is called by nothing —
so JSON over TCP is byte-identical to what it was and remains the only
transport that can carry a block. The announce goes **148 B → 40 B**, which
fits EU868 SF12 (51 B), the worst legal case; the heartbeat carries the A21
digest INTACT in 55 B. §R3 is the pre-fix record: on today's JSON a radio link
works at DR3 and dies at the first step-down.

**One check failed, it was mine, and reading it instead of adjusting it is the
whole finding.** R8e asserted that hash truncation — an option deliberately
priced and rejected — appears in prose only. It matched eight
`raise LoraFrameError("truncated varint")`-class REFUSAL messages, i.e. the
opposite feature. The tempting repair was to reword the node's own diagnostics
to satisfy my assertion. **Tokenized code still contains string literals, and a
refusal message is prose living in a string; a claim about what is IMPLEMENTED
is a claim about identifiers.** → **M42 amendment**, plus R8f (the refusal
messages must still be there) and R8g (inject `truncate_hash` and require R8e
to fail).

**Not wired into the runner, deliberately** — `run_all_tests.sh` and
`run_local_sweep.py` are sha256-pinned in `verify_deploy.py`'s MANIFEST, so
touching them now would make the launcher correctly refuse to restart. That is
the verifier doing its job on its first day. Runner wiring is the first task
after the restart, manifest updated in the same edit. Everything else in R1 —
the A23 per-bearer question above all — is still open and still needs L's
hardware, stack and goal answers.

**ADDENDUM 3 ~20:45 — L: "mycellium electricty generation to lessen the need of
power for data centers". Priced, not designed. The answer is no, and the mirror
of the question is the finding.**

**No, by twelve orders of magnitude → DE8.** EMPA's 2025 fungal biobattery is a
temperature sensor for a few days — its own authors publish no power figure,
which is the answer. The bacterial record (13.1 mW/cm², *Nature Comms* 2024) makes
it look plausible on AREA — 76 hectares of anode for 100 MW — and that is the
wrong number. An MFC is a CONVERTER: at a generous 30 % it needs **1,850 t/day of
sugar** for one 100 MW hall, ~0.4 % of world production, and anaerobic digestion
burns the same carbon at 35–40 % with no electrode. Global data centres are ~415
TWh (IEA, 2024). Recorded as a dead end so no future run re-derives it.

**The mirror was worth the search: what actually draws power here?** Measured
from files already on L's machine — the ethics judge is **5,234 MB resident
against 117 MB for the entire chain (45×)**, and one warm verdict is ~512 J
against ~13.6 J to mine the whole block it sits in (**38×**, at a stated 40 W
assumption). **The ethics gate, not the proof-of-work, is this system's energy
profile** — the reverse of what a chain is assumed to look like.

**So B4 has been a watts decision all along and nobody said so.** Consensus rule
= N × 512 J per transaction and every participant needs 5.2 GB resident;
admission policy = 512 J once and a peer needs ~0.1 GB. At 100 nodes that is a
hundredfold, and it is exactly what decides whether the mesh can reach a phone
(C3/C4) or a LoRa peer (R1) at all. Filed as a **B4 amendment** rather than a new
item — it is a new argument for an open decision, not a new decision. It changes
no verdict and remains L's call.

**And the mycelial idea that DOES pay is signalling, not generation** — fungal
spike trains are millivolt information at microwatt cost, which is
`SpikingAnomalyMonitor`, `LinkConductance` and Mahowald's address-event
principle, all of which this codebase already runs on. R1 is what taking it
seriously looks like: 40 bytes, 0.30 s of airtime. The saving is in not
transmitting.
