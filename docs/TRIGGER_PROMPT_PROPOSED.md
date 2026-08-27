# APPLIED 2026-08-22 ~14:20 — this file is now a record, not a request

`update_trigger` on `trig_01JuqmnfpaxphVvShDch2GJa` **works in an attended,
L-started session** and was used to install the prompt below (plus this
session's additions). DE2 is narrowed, not deleted: it still fails in an
unattended scheduled run, so a scheduled run should keep writing proposals here
rather than attempting the call.

**Do not re-propose the changes listed below — they are live.** Added at apply
time, beyond the 00:15 proposal:

- M25: delivery is not `project_write`. The PC ran a pre-v8.15 source for
  fourteen versions while the log recorded them all as shipped. Read
  `claude/PC_SYNC_LOOP.md` before shipping anything.
- M26: if you replace an implementation, re-run every check whose RULE was
  derived from the old one's behaviour (the WSGI swap silently disarmed
  preflight's HTTP-vs-P2P probe).
- The corrected suite list: `test_a12_dead_peer_backoff` (not
  `test_a12_dead_peers`), plus `test_b5_mine_latency`, `test_a13_one_way_sync`,
  `test_a14_boot_probe`, `test_a15_exchange_deadline`, `test_y1_stake_divergence`,
  `test_a17_oneway_peer_sync`, `test_w1_wsgi`, `test_d3_daily_guards`.
- Batch sizes: <= 7 fast, <= 5 slow (M20/M21).
- A16 added to the decision-for-L list.
- The v8.27 and v8.29 import assertions.
- DATA: `api.kraken.com` and `api.exchange.coinbase.com` both answer plain
  `urllib` from the sandbox (HTTP 200, re-measured 2026-08-22). Run
  `pc/daily.py` rather than re-deriving prices; never use WebFetch for them;
  never `project_read` a CSV inline.
- Step 6: fetch the log FRESH at write-back and edit by anchor (M15/M23).

The next run that wants to change these instructions should edit this file with
its proposal and say so in its run-log entry, exactly as before.

---

# PROPOSED 2026-08-23 ~08:30 — not applied (unattended run, DE2)

Three changes, all small, all because the prompt now describes work that is
finished or an environment fact that is wrong.

### 1. The Android block at the end of the prompt is DONE. Replace it.

The trigger prompt currently ends with a long standalone brief: *"Build an
Android privacy/security layer app in Kotlin, based on VpnService…"*. That was
carried out on 2026-08-23 ~08:30 and closed as **C5**. Left as-is, every future
scheduled run re-reads it as a live instruction and may rebuild it.

**Replace the whole Android block with:**

> C5 (the Android on-device privacy/security layer) is BUILT and delivered —
> see `claude/ANDROID_GUARD.md` for the design record, the measured-vs-not
> table, and the eleven flagged assumptions. Do NOT rebuild it. The next move
> on C5 is L's: try the APK, answer README §7, and decide the C3 question
> (one VpnService at a time — the phone can be a covenant node over Tailscale
> or a filtered phone, not both). If L asks for changes, the source is
> `covenant-guard-src.tar.gz`, delivered by SendUserFile; ask L for it rather
> than assuming a copy is in the project.

### 2. Add the environment fact to the "known traps" paragraph.

One line, because it changes what a run believes it can do:

> BUILD TOOLS: this sandbox has JDK 21 and Gradle pre-installed, and
> `dl.google.com`, `repo1.maven.org` and `plugins.gradle.org` all answer 200,
> so the Android SDK installs and Android/Kotlin/JVM projects genuinely
> COMPILE here (`sdkmanager` → platform 37 + build-tools 37.0.0, ~956 MB,
> ~8 min). Measure what the sandbox can build before deciding a deliverable
> can only be described (M35). Note AGP 9.x has Kotlin built in — applying
> `org.jetbrains.kotlin.android` beside it is a hard error — and only JDK 21
> is present, so `jvmToolchain(17)` fails; set `sourceCompatibility` /
> `targetCompatibility` / `compilerOptions.jvmTarget` instead.

### 3. Sharpen step 2's verification rule for non-Python deliverables.

Step 2 currently names the Python suites only. Add:

> For a compiled deliverable, "it builds" is the compiler's opinion. Read the
> ARTEFACT: `aapt2 dump xmltree` on the APK for what the manifest actually
> declares, `apkanalyzer dex packages` on the R8 output for what survived
> shrinking. An extension point nothing statically calls is exactly what R8
> removes, and the build log says nothing about it.

**Apply these in an attended, L-started session** (`update_trigger` on
`trig_01JuqmnfpaxphVvShDch2GJa`), then mark this section APPLIED as the
2026-08-22 section above was.

---

# PROPOSED 2026-08-24 ~02:00 — not applied (unattended run, DE2)

The 2026-08-23 ~08:30 proposals above are **still unapplied**; apply them at the
same time. Four more, all because the prompt now names a stale set or is missing
a fact that cost this run time.

### 4. The suite list in step 2 is missing six suites that touch the file.

The prompt names 20 suites. `run_all_tests.sh` now calls 35, and six of the
missing ones test the node source directly, so a run following the prompt
literally ships without them. Add to the list:

> `test_b2_quorum_diversity` (~10 s), `test_w2_sandbox_platform` (~10 s),
> `test_p11_version_identity` (~10 s), `test_p12_substrate_sensing` (~50 s),
> `test_a20_peer_version` (~15 s), `test_a22_topology_vigilance` (~15 s).

MEASURED in this sandbox, twice, on 2026-08-24. The full green sweep is
**26 suites / 926 checks**; a run reporting fewer suites has skipped something.

### 5. Add the staging line to "known traps" — two suites fail as REGRESSIONS without it.

A fresh cloud sandbox holds only what the run staged, and the sweep's dependency
set is bigger than its suite list. This cost two re-runs:

> BEFORE the first sweep, stage `covenant_path_pattern.py`,
> `covenant_trading_bridge.py`, `guards.py`, `daily.py`, `covenant_watchdog.py`
> and `trace_runner.py` beside the suites, and run
> `pip install waitress --break-system-packages`. Without the bridge module
> `test_security_audit` dies on an import after printing three cryptic
> `'NoneType' has no attribute report_realized_profit` failures; without
> waitress `test_w1_wsgi` raises. **Both look exactly like regressions against
> the source you just changed, and neither is** — read a failure's FIRST line,
> not its verdict (M37).

### 6. Point step 1 at the OPEN-ITEMS INDEX, not the whole of §4.

§4 is ~890 lines and holds ~14 open items. It now opens with an index. Change
step 1's wording to:

> Pick from the **OPEN-ITEMS INDEX** at the head of §4 — one line per open item
> with its blocking state — and read the full entry only for the item you pick.
> Section A outranks D unless A is blocked (it is: every remaining A item is
> L's decision).

### 7. Say that `claude/LOOP_HEADER_ARCHIVE.md` exists, so a run does not read a shrink as a loss.

One line in step 6, because a future run that notices the banner got shorter has
no way to tell shrinkage from the 08-22 write-back accident:

> The STALL WATCH banner carries only the stall count and the last close. Nine
> runs of narrative that used to live there are in
> `claude/LOOP_HEADER_ARCHIVE.md`, moved verbatim on 2026-08-24 (M36). An index
> may be regenerated; §0 and §5 may never be edited.

**Apply in an attended, L-started session** (`update_trigger` on
`trig_01JuqmnfpaxphVvShDch2GJa`), then mark APPLIED as the 2026-08-22 section is.

---

# PROPOSED 2026-08-26 ~01:30 — not applied (unattended run, DE2)

The 08-23 and 08-24 proposals above are **still unapplied**; apply them at the
same time. Three more.

### 8. "Needs one Windows run" is not a blocking state — say so in step 1.

A23 sat in the backlog marked *needs one Windows run* while a scheduled run,
which by definition has no Windows, read that as blocked. Two of its three
findings needed no Windows at all: the Windows *symptom* (a peer whose port
completes the handshake and never answers) is fifteen lines of local listener
and reproduces on any platform. Add to step 1:

> An item filed as "needs a Windows run" is blocked only for the part that is
> genuinely platform-specific. Before skipping it, ask what SHAPE the platform
> produces and whether that shape can be built here — a killed Windows node
> presents as a socket that accepts and never answers; NTFS ACL semantics do
> not reproduce at all. Reproduce the shape, then say plainly which half of the
> item is still untested and on which platform (M29/M41).

### 9. The suite list in step 2 is stale again, and the green number moved.

Add `test_a23_ack_health` (~15 s) to the list in step 2. The full green sweep in
this sandbox is now **31 suites / 994 checks**, measured twice on 2026-08-26
(the 26/926 figure in proposal 4 predates a23, p14, w2, e2e_gift and the two
sims being run together). A run reporting fewer suites has skipped something.

### 10. Add M41's grep rule to step 2's verification paragraph.

> When an existing fix "does not fire", the branch is a claim you can measure —
> reproduce the shape in-process and print the state either side of it. And
> `grep` for EVERY writer of the counter your conclusion rests on, not only the
> one you are reading: A23's fix was firing correctly and a line three above it
> was clearing the counter it set, so the measurement that proved "the fix
> never ran" was reading a variable with a second author (M41).

**Apply in an attended, L-started session** (`update_trigger` on
`trig_01JuqmnfpaxphVvShDch2GJa`), then mark APPLIED as the 2026-08-22 section is.


---

# PROPOSED 2026-08-26 ~09:30 — not applied (unattended run, DE2)

The 08-23, 08-24 and 08-26 01:30 proposals above are **still unapplied**; apply
them at the same time. Three more, and the first one supersedes a number.

### 11. Stop enumerating the suite list. Name the runner instead.

Proposals 4 and 9 both exist because step 2 hard-codes a list of suite names
that goes stale every time a run adds one — three amendments in three days, and
each stale list is a run shipping without a suite that touches the file. The
list is also the wrong shape: `run_all_tests.sh` already IS the list, it lives
beside the code, and it is delivered with it. Replace the enumerated list in
step 2 with:

> Run **every suite `run_all_tests.sh` calls**, not a list quoted from these
> instructions — the runner is delivered with the source and this prompt is
> not. Read the measured time in each suite's comment block in the runner; the
> `timeout` values are ceilings, not estimates. The full green sweep in this
> sandbox was **31 suites / 1,043 checks** on 2026-08-26 (Linux). A run
> reporting materially fewer suites has skipped something; say which and why.

Keep the individually-measured slow ones called out by name, because they are
the ones runs have skipped on a wrong quoted figure: `test_security_audit`
(~90 s), `test_b1_judge_parser` (~30 s), `test_a12_dead_peer_backoff` (~30 s),
`test_a4_block_injection` (~60 s), `test_a1_kill_matrix` (~50 s),
`test_multinode_live` (~80 s), `test_b5_mine_latency` (~50 s).

### 12. Batch width is a ratio to vCPUs, not the constant 5.

Step 2 says "≤ 7 fast / ≤ 5 slow". On a **2-vCPU** box a 5-wide mining batch
produced two reds — `test_a1_kill_matrix` (a `/mine` HTTP call timed out) and
`test_b5_mine_latency` (`Invalid registration proof`) — both green 2/2 alone.
Replace with:

> Batch ≤ 7 fast suites in parallel, and ≤ **`nproc` + 1** slow (mining) ones —
> read `nproc` rather than assuming; this sandbox has been 2 vCPUs. A failure
> inside a batch is not a failure until it fails alone twice (M20). Note that
> CPU starvation does not always look like a timeout: anything with a freshness
> window (registration PoW, nonces, timestamps) fails as an **authentication
> error** when the box is oversubscribed.

### 13. Add the round-trip rule to step 3, and the data-flow rule to step 2.

Step 3 says deliver with SendUserFile AND `project_write`. Add what makes that
verifiable, and one line to step 2:

> A `project_write` returning `replaced: true` is not proof the bytes you
> intended are what landed. Verify with a **fresh** subagent that reads each
> path back with `project_read` and compares sha256 against the local file —
> and require it to say WHERE the bytes came from, because this session's
> transcript also contains the `Write` inputs that created the local copies,
> and comparing against those matches by construction and proves nothing
> (M43).

> And when you write a comment claiming that one thing reaches another, write
> the check for that flow in the same session. A data-flow claim can be wrong
> at the moment it is typed, not only stale: this run shipped a guard whose
> comment said a peer's index is echoed into the request we build, and the
> check written to prove it disproved it (M42). Pin source-level rules against
> **tokenized code**, not raw source text — a comment that mentions the symbol
> you are forbidding will satisfy a naive `in` test.

**Apply in an attended, L-started session** (`update_trigger` on
`trig_01JuqmnfpaxphVvShDch2GJa`), then mark APPLIED as the 2026-08-22 section is.
