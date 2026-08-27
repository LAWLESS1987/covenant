# Running the system on the machine that runs it — 2026-08-22

L: *"fully intergrate and run local"*. This is what "local" turned out to mean,
what was missing, and the recipe that works, so no future run has to rediscover it.

## 1. The integration gap: the runner asked for 34 suites; 19 had never arrived

`claude/PC_SYNC_LOOP.md` (12:30) closed the loop for the **source**: v8.29 was
copied to the PC and matches by hash (`d7cadb3d…`, 8769 lines, verified again at
the top of this run). What nobody checked is that `run_all_tests.sh` — shipped to
the PC in the same delivery — invokes **34** suites, and the machine held only
**15** of them. Fourteen of the missing nineteen are the A/B-series suites this
loop wrote between v8.15 and v8.29: every fix from `preflight_port_check` to
`recv_bounded`'s exchange deadline had a test that could not run where the node
runs.

Delivered this run and verified by sha256 on the far side (21 files):

```
test_a1a_a2 7c754e97   test_a3_bounded_reads 8b6b353d   test_a4_block_injection b6ad2ad4
test_a5_size_coherence 2041a2a7   test_a9_relay_race fccbbecf   test_a1_kill_matrix 9275e84b
test_a11_gossip_scale 714f0b2a   test_a12_dead_peer_backoff 107be733
test_a12_dead_peers 4c4e316d   test_a13_one_way_sync 81d06496   test_a14_boot_probe a0139c0a
test_a15_exchange_deadline d9ec18d7   test_a17_oneway_peer_sync acc5950c
test_b1_judge_parser 29bd808f   test_b5_mine_latency 6305310d   test_y1_stake_divergence 2dc36205
trace_runner e8f1d56c   verify_csv 921ed0c5   probe_power bd7456b9
d2_regime_deep 27b933e4   d2_rebalance_deep b37a8443
```

**And 12 suites the runner calls for exist nowhere** — not on the PC, not in the
project: `verify_bundle.py`, `verify_patches.py`, `verify_auth.py`,
`verify_tx_aer.py`, `test_path_pattern.py`, `test_succession_seal.py`,
`test_ethics_judge.py`, `test_golden_ratio.py`, `test_judge_individuality.py`,
`test_multi_provider_quorum.py`, `test_v86_bridge.py`, `test_v86_loss_tracking.py`.
They are v8.11/v8.12-era names from `MANIFEST.json`. A local sweep therefore prints
a dozen `NO RESULT` lines that look like failures and are not. Not deleted from the
runner here — that is L's call — but `run_local_sweep.py` lists them under
"referenced but not present" instead of scoring them.

## 2. waitress was never installed, so W1 was inert on this machine

v8.29 (12:30) added `resolve_wsgi_server()` so the node serves Flask through
waitress — a bounded thread pool, a connection cap, and an idle-connection reaper —
instead of werkzeug's development server. `requirements.txt` lists it. It was not
installed in `.venv`, so **the node has been running the dev server the whole
time** and `test_w1_wsgi.py` could not exercise the path it exists to test.

Fixed: `waitress-3.0.2-py3-none-any.whl` (pure Python, `py3-none-any`) is now in
`vendor/`, unpacked into `.venv\Lib\site-packages`, and `test_w1_wsgi` passes
24/24 on the waitress path, and after the restart described in §7 both production
nodes boot `api: waitress on 0.0.0.0:5000 (threads=8, connections=100,
idle_timeout=120s)` — the bounded pool is live for the first time.

## 3. `covenant_prod.bat stop` does not stop a node

Observed live at 14:12: the sequence stop → start reported
`stopped. Databases untouched` and then `node A already up`, `node B already up`.

`:stop` runs `taskkill /f /fi "windowtitle eq Covenant Node A*"`. The nodes are
launched as `start "Covenant Node A" /min cmd /c "... python run_with_ollama_judge.py ..."`,
so the window title belongs to the **cmd wrapper**; `/f` without `/t` kills the
wrapper and leaves `python.exe` holding 5000/5020. The next start's `curl /health`
succeeds, so it does nothing and says so cheerfully.

**This is the same class as M25 and belongs beside it: a restart that reports
success while the process keeps running is how a machine keeps executing a source
from days ago.** It is also why "restart the node to pick up v8.29" in the 12:30
entry could not have worked as written.

`AB_RESTART_NODES.bat` fixes it: `taskkill /f /t` by title, then by PID for
whatever still holds 5000/5020 from `netstat -ano`, then asserts the ports are free
*before* handing over to `covenant_prod.bat` to start. It never touches a database.

## 4. The two local runtimes, and what each can prove

There are two "locals" on this machine and they are not the same:

| | Linux VM (the file bridge) | Windows (`.venv`) |
|---|---|---|
| python | 3.10.12 | 3.12.10 |
| flask | borrowed from `.venv\Lib\site-packages` | native |
| network | **none** (403 at the tunnel) | full |
| interfaces | loopback only | real |
| command budget | **45 s, background dies with the call** | none |
| runs the node | no | yes |

The VM is where the covenant folder is mounted read-write; it is genuinely L's
machine, and a suite that passes there passes against the deployed bytes. But it
cannot run `daily.py` (no network), cannot install anything (no PyPI), cannot run
`test_a17_oneway_peer_sync.py` (it calls `hostname -I` and gets nothing back —
there is no non-loopback address to peer on), and cannot finish any suite that
takes longer than ~40 s, because **`device_bash` background processes are killed
when their call returns** — the same rule M5 records for the cloud sandbox, now
measured here (`setsid nohup` does not survive; a 25 s sleep launched in one call
had left nothing behind by the next).

So the split that works: fast suites over the bridge for a quick answer; the full
sweep on Windows through `AA_INTEGRATE_AND_RUN.bat`, which writes its results to a
file the bridge can read.

## 5. The recipe

**Over the bridge (Linux VM), for a 40-second answer:**

```bash
mkdir -p ~/pylibs && cd ~/mnt/covenant
cp -r .venv/Lib/site-packages/{flask,werkzeug,jinja2,markupsafe,itsdangerous,click,blinker} ~/pylibs/
cp -r .venv/Lib/site-packages/{flask,werkzeug,jinja2,markupsafe,itsdangerous,click,blinker}-*.dist-info ~/pylibs/
find ~/pylibs -name '*.pyd' -delete          # Windows binaries; the pure-python fallbacks work
# cryptography comes from the VM's own python3 -- do NOT put the venv's Windows build on the path
export PYTHONPATH=~/pylibs COVENANT_INSECURE_MOCK_JUDGE=1 COVENANT_JUDGE_PROVIDERS=mock
```

Copy the source and suites to `~/sweep` (NOT the mount: the suites `rm` their
databases and **`device_bash` cannot delete inside the mount**, and every write
there invalidates the seal), then run one suite per call with `timeout 40`.

The `.dist-info` copies are not optional: `flask.testing` calls
`importlib.metadata.version("werkzeug")`, and without metadata every suite that
uses `app.test_client()` dies with `PackageNotFoundError` — six of them did before
this was found.

**On Windows, for the whole sweep:** double-click `AA_INTEGRATE_AND_RUN.bat`. It
records the deployed hash and python version, then runs `run_local_sweep.py`, which
stages everything into `%TEMP%\covenant_sweep`, runs each suite there under a
whole-tree kill on timeout, and appends each result to `SWEEP_RESULTS.txt` **as it
happens** so the bridge can watch it. One launcher, one job: the node restart is
`AB_RESTART_NODES.bat`, and it refuses to stop anything if Ollama is not answering
— the judge fails closed, so a node that cannot reach it rejects every
transaction, and a node that is up beats one that will not come back.

Two harness bugs worth not repeating, both mine, both Windows-specific:
`subprocess.run(capture_output=True, timeout=…)` **hangs forever** when a killed
suite's node children still hold the stdout pipe (55 minutes, no output) — write to
log files instead; and a cleanup rule that deletes `covenant_unified_*` deletes the
**source file**, not just the databases (23 of 24 suites reported
`ModuleNotFoundError` in 0.2 s each before that was spotted).

**A cmd trap that cost this run twenty minutes:** the first launcher died silently
on `echo --- health A (5000) ---` inside an `if ( … )` block — the unescaped `)`
closes the block early and cmd aborts the script. It had written three lines and
stopped, with no error anywhere the bridge could see. **No parenthesised blocks in
a batch file that has to be trusted unattended: GOTO labels only**, and grep the
file for `(` outside `REM` before shipping it.

## 6. What the sweep found on Windows

Ten and a half minutes, python 3.12.10, waitress path, in `%TEMP%\covenant_sweep`.

**476 checks green:** a3 7/7, a5 20/20, a11 23/23, a12_dead_peer_backoff 21/21,
a13 25/25, a14 15/15, a15 14/14, b1 162/162, y1 10/10, w1 24/24, d3 77/77,
a9 18/18, a4 60/60.

**Three that ran and did not fully pass.** None is a node defect on this evidence,
and none should be written up as one until it is re-run alone:

- `b5` 30/31 — "second /mine paid again" measured 2.50 s against a 2.51 s bar that
  the same run had set one line earlier. A 10 ms margin, on a machine also running
  two nodes and Ollama. The assertion needs a tolerance, not the node a fix.
- `a1_kill_matrix` 28/30 — K1 and K3, "A recorded the failed delivery, not
  silence". The monitor *did* record `peer_message_error` (recent=1); the
  assertion wanted what a Unix connect-timeout produces, and Windows refuses a
  dead local port instantly instead. Tips converged in both scenarios.
- `multinode` 2/3 — "all three nodes came up and serve HTTP" failed at startup
  after 151 s. M10 already records this harness flaking on `free_port()`.

**Six that cannot run on Windows at all** — harness portability, not the node:
`a1a_a2` (`send_signal(signal.SIGINT)` → `ValueError: Unsupported signal: 2`),
`a17` (`hostname -I`), `security_audit` (multiprocessing `fork` context),
and `adversarial`, `e2e_gift`, `sim_order_independence`, `sim_yield_safety`
(`shutil.rmtree` over an open sqlite file → `WinError 32`). `probe_final_pass`
stops on `MainnetGuardError: policy file absent`, which is the guard working.

## 7. The best finding came from the tests breaking

`test_a1a_a2` died on the Windows signal error **and left its node running**. That
node had been started with `--port 5001`, so it held 5001 as its *Flask API* — the
same port node A uses for *P2P*. When the nodes were properly restarted afterwards,
**node B refused to boot**:

```
PREFLIGHT FAILED: peer 127.0.0.1:5001 answered like an HTTP server,
not a Covenant P2P listener -- this is almost certainly the node's Flask API port.
```

`netstat` confirmed two pythons on 5001: node A (5000/5001/5011) and the stray
(5001/5002/5012). So A2's preflight — the control W1 silently disarmed this
morning and M26 re-armed — caught a real port collision on the production machine
and refused to boot into exactly the state it exists to prevent: two nodes that
look peered while neither hears the other. Killing the stray by its own port
(5002, which nothing else holds) and starting again brought both nodes up.

**The operational lesson:** a test sweep that leaks node processes can take the
production chain down on the next restart. `run_local_sweep.py` now runs each suite
under a whole-tree kill on timeout; a suite that dies of its own accord can still
leak, so check `netstat -ano | findstr ":500"` after any sweep.

## 8. What is now true, and what is not

*(Section 8 is the only part of this file that is meant to be kept current;
everything above it is the record of 2026-08-22. Updated 2026-08-23 ~03:10.)*

- The suites, the source, waitress and the price data are all on the machine, and
  the sweep runs there with one double-click.
- **The deployed source is v8.34** (`773cb7d7…`). v8.30 (`0b04473b…`)
  landed at 18:57 ET on 08-22 and **is what both nodes are running now**,
  restarted properly at 21:39 ET. Three additive changes sit on top of it, none
  touching a decision path: **P11** (the node names its version and the sha256 of
  the source it LOADED, in the boot banner and on `/health`, and the watchdog
  compares that against the file on disk every round); **P12** (the node samples
  the machine under it and reports it as a WARNING only, and the watchdog
  transmits change rather than state — the real 12 h log replays 3,973 → 178
  lines — and can push surviving alerts off the box, opt-in); **A20/A21** (every
  peer reply carries `v` and `src`, and a bounded digest rides the 120 s
  heartbeat, so two nodes can find out they run different sources by being told
  instead of by a rejected block; the 156-byte block announce is untouched).
  **A22** (`/mycelium` — the node's own peer table and link conductance — now
  reaches the watchdog, which alerts on a peer nobody configured, on every link
  at the conductance floor, on a chain that shortens, and on a silent restart;
  plus two hardening fixes to the A20/A21 peer-input path and one comment in the
  node source that wrongly denied a live security control).
  **The running nodes are still v8.30, four versions back** — double-click
  `AB_RESTART_NODES.bat`; `NODE_RESTART.txt` will then contain
  `"version": "v8.34", "source_sha256": "773cb7d7adef"` from both nodes, and the
  watchdog log will start naming what it is watching. Nothing in v8.31–v8.34
  changes what a node accepts or refuses: it is all disclosure, observation, or
  a tightening of what a peer can make this node do.
- **How to answer "what is running?" from now on** — three lines, no forensics:

  ```cmd
  python -c "import hashlib;print(hashlib.sha256(open('covenant_unified_v8.py','rb').read()).hexdigest()[:12])"
  curl -s http://127.0.0.1:5000/health | findstr source_sha256
  curl -s http://127.0.0.1:5020/health | findstr source_sha256
  ```

  Three identical strings means the deployed file is the running file on both
  nodes. Anything else is drift, and the watchdog is already alerting on it.
  Full write-up: `claude/RUNNING_VS_DEPLOYED.md`.
- **Both nodes are up, serving through waitress** — `api: waitress on
  0.0.0.0:5000 (threads=8, connections=100, idle_timeout=120s)` and the same on
  5020. Height 3, peers 1, founder balance agrees across both dbs (988.0),
  nodeB balance agrees (12.0). The watchdog's standing ALERT is `code sandbox
  unavailable … (win32)` on both nodes — that is P4 working as designed, not a
  fault: `/propose_code` refuses rather than running a snippet with no
  enforceable limits.
- **The local judge is measured, and it works.** `AG_LEAN_MEASURE.bat` →
  `judge_bench.py`: qwen3:8b on the tuned path (think off, constrained JSON,
  temp 0) got **6/6** on benign gift / theft / false witness / prompt injection
  / plain transfer / honest tithe, determinism STABLE over three runs, **~12.8 s
  per verdict warm**. Note against `LEAN_MEASURE.txt`'s own summary lines:
  `num_predict` 96 vs 160 are **not** 17.4 s vs 12.8 s — strip the one 39.9 s
  cold model load and they are 12.88 s and 12.77 s, indistinguishable.
- **RAM is the judge's real constraint on this box**, not CPU. `llama-server.exe`
  holds 5234 MB of 16.4 GB; covenant's own footprint is **331 MB across 27
  processes** (`AI_TOPMEM.bat`). At the 21:39 restart only 3.1 GB was free, below
  the 5.2 GB the model needs, so it was loading by paging. `AJ_CLEANUP.bat`
  (closes leaked launcher consoles, spares the node ones) and `AK_FREE_RAM.bat`
  (unloads the model: 2.86 → 8.18 GB free) are the two levers.
  `COVENANT_OLLAMA_KEEP_ALIVE` is now **30m**, not 60m — the cost is one cold
  load after a quiet half hour, and the chain sat at height 3 through 431
  watchdog ticks.
- **`AL_DASHBOARD.bat`** renders a 3D view of the mesh into a local HTML file
  with the data baked in, so it still renders when a node is DOWN. Its age badge
  goes amber then red, so a stopped refresher cannot look like a calm system.
- **`AJ_CLEANUP.bat` does not remove the junk file it says it removes** — `4]`
  (0 bytes, created 01:31 UTC by a broken one-liner) is still in the folder, and
  the cleanup reports nothing either way. Harmless, but it is a step that claims
  to have done something it did not.
- Node A's `/health` reports `own_genesis: true` with the warning that it cannot
  converge with peers that did not adopt the same genesis file. **A10 is not
  theoretical on this machine** — it is the live configuration, and it is still
  L's decision.
- `daily.py` still cannot run over the bridge (no network in the VM). It runs on
  Windows (`DAILY.bat`) and in the cloud sandbox, where the 14:20 run proved it.
- **The seal, measured rather than guessed.** `python covenant_seal.py verify`
  runs read-only and takes seconds — over the device bridge too. Today:
  `root was c119afb5… root now 679e447f…`, **20 changed, 81 added, 0 removed.**
  Nothing has been removed; every difference is explained by known work. Re-run
  `covenant_seal.py` and `covenant_anchor.py` to re-anchor. Deliberately not
  done by the loop: re-sealing blesses a file set as canonical, and the loop
  doing that immediately after its own writes is the auditor signing its own
  work.
