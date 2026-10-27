# Improvements found — 2026-08-27

Two sources: the repo itself, and the wider ecosystem. The repo turned out to
hold more than the ecosystem did. One claim from the research was checked by
measurement on this machine rather than believed, and it came back worse than
the research predicted.

---

## 0. The fixes are already written and unmerged. Start here.

There is **no GitHub remote** — `git remote -v` is empty, so nothing is pushed
anywhere. But `main` is missing five branches, and two of them fix precisely
the defects rediscovered today from scratch:

| branch | ahead of main | what it does |
|---|---|---|
| `fix/tally-counts-failures-as-passes` | 4 | Stops the sweep counting failures as passes. **Adds `test_k2_tally_arithmetic.py`, 212 lines — a suite that exists nowhere on `main`.** |
| `fix/remove-phantom-suites` | 3 | `c68efeb Remove eleven phantom suites from the sweep` |
| `fix/sweep-uses-project-venv` | 1 | Runs the sweep against the project's own interpreter |
| `docs/correct-missing-suite-count` | 1 | "twelve is now eleven" |
| `docs/withdraw-unverified-suite-totals` | 1 | Withdraws unverified totals from the README |
| `p9/platform-correct-owner-only` | 2 | **currently checked out** — the working tree is on a feature branch, not `main` |

`covenant_one.py` independently re-derived the phantom-suite and
failure-counting findings today, hours of work, because the branch that already
fixed them was never merged. **Unmerged work is invisible work.** Decide per
branch: merge, or delete and let `covenant_one.py` be the runner. `main` is not
the delivery until that is settled — and note the box is running a feature
branch right now.

---

## 1. MEASURED: the A23 win32 failure, root cause settled

`probe_win_connect.py` / `ONE_PROBE.bat` (new, read-only — opens sockets to
ports where nothing listens, times them, reads TCP settings, changes nothing).
Same probe, both platforms:

| | refused (closed loopback port) | dead (192.0.2.1, black-holed) |
|---|---|---|
| **Linux** (cloud, py3.11) | **0.0 ms** · `ConnectionRefusedError` | 0.1 ms · (no real network in sandbox) |
| **Windows 11** (py3.12) | **2,045.8 ms** · `ConnectionRefusedError` | 6,009 ms · `TimeoutError` (deadline) |

**A refused connect costs ~50,000× more on Windows than on Linux.**

The cause is confirmed arithmetic, not a guess. `Get-NetTCPSetting` reports
`MaxSynRetransmissions = 4` on every profile, and the published per-retransmission
cost on loopback is ~506 ms: **4 × 506 = 2,024 ms** against **2,045.8 ms
measured**. Windows does not surface the RST when it arrives — it holds the
socket in SYN-SENT and spends the whole retransmission budget first, then
returns `ConnectionRefusedError`. Confirmed by curl's maintainer, who hit the
same wall ([daniel.haxx.se, 2024-08-14](https://daniel.haxx.se/blog/2024/08/14/slow-tcp-connect-on-windows/),
[curl#14144](https://github.com/curl/curl/issues/14144)).

**And A23's own number was the stopwatch.** A23 S3 measured "refused 1.053 s vs
dead 1.12 s" at a ~1 s deadline. A refused connect here needs 2.045 s, so at
that deadline it never completed — **both** of A23's numbers were its own
timeout. That is why the probe uses 6 s: at 1 s a slow refusal and your own
deadline are indistinguishable, which is exactly the trap. So both readings are
true at once — the stack really is slow, *and* the suite measured itself.

**The consequence, which is live right now.** A12's dead-peer headroom
(508 → 11,520) is bought by refused peers costing nothing. On Windows a refused
peer costs ~2.05 s against a dead peer's ~5 s default timeout — call it 40% of
the cost, not ~0%. **On this platform, a peer that is merely stopped costs
almost as much as one that is black-holed**, so a node whose peers are simply
down behaves like a node under a dead-peer flood. The nodes were down for hours
today; this is not hypothetical.

### The fix, and it is not a Windows workaround

No mature P2P implementation derives its budget from measured per-attempt cost.
They all count failures:

* **Bitcoin Core** `src/addrman.cpp` — `fChance *= pow(0.66, min(nAttempts, 8))`,
  `Good_()` resets `nAttempts = 0`. Nothing anywhere times a failed attempt.
* **go-libp2p** `swarm_dial.go` — `BackoffBase 5s + BackoffCoef × priorBackoffs²`,
  capped 5 min, keyed per peer *and* per address, cleared on success.
* **Syncthing** `lib/connections/service.go` — 3 attempts in 2 min → 5 min cooldown.
* **py-libp2p** `swarm.py` — exponential with **jitter**. Add the jitter; a fixed
  peer set with deterministic backoff synchronises into a thundering herd.

Ranked changes:

1. **Key backoff on consecutive failure count, delete the cost model.** Removes
   the platform dependency outright. Highest value, lowest risk.
2. **Impose your own deadline: non-blocking connect + `selectors` + `SO_ERROR`.**
   Uniform across platforms — Linux wakes writable with `SO_ERROR=ECONNREFUSED`,
   Windows wakes in the exception set with the same `SO_ERROR`. Bitcoin Core's
   `ConnectToSocket` in `src/netbase.cpp` is the canonical shape.
3. **Branch on error *class*, not elapsed time.** `ECONNREFUSED`/`EHOSTUNREACH`
   are deterministic — the peer answered — so short-circuit. Timeout is
   indeterminate and gets its own slower ladder. go-libp2p keeps a separate
   `black_hole_detector.go` for exactly this and deliberately skips `AddBackoff`
   for black-hole errors.
4. **Cap concurrent dials** (go-libp2p 160 global / 8 per peer; Syncthing 64/8)
   and **deduplicate in-flight dials per peer** (`dial_sync.go`). Then one slow
   attempt costs a worker slot, not the loop.
5. Only if you truly need cheap refusals: `SIO_TCP_INITIAL_RTO` with
   `TCP_INITIAL_RTO_NO_SYN_RETRANSMISSIONS` — needs `ctypes`+`WSAIoctl`
   (Python's `socket.ioctl` exposes only `SIO_RCVALL`, `SIO_KEEPALIVE_VALS`,
   `SIO_LOOPBACK_FAST_PATH`), scope it to loopback only, and never
   `Set-NetTCPSetting` machine-wide from a node.

**Two traps worth writing down now.** Never dial `"localhost"` — `create_connection`
walks every `getaddrinfo` result with the *full* timeout each, so `::1` stalls
then `127.0.0.1` stalls: 2× your budget per dead peer. And McAfee's WFP callout
forces loopback onto the slow path permanently — tens of ms, not the second, but
it explains the noise.

---

## 2. The integrity checks: derive them, don't maintain them

Three hand-maintained checks failed today (manifest phantom, transcript
deadlock, frozen delivery list). The ecosystem answer is unanimous: **derive the
file set from VCS; never walk the disk.**

**The blocker, found by checking rather than assuming:** `DEPLOY_VERIFY.txt`,
`LAUNCH_CHECK.json`, `NODE_RESTART.txt` and `MANIFEST.sha256` are **tracked in
git**. They are launcher *outputs* committed as *inputs*, so every launch dirties
the worktree. That is the same deadlock a fourth time, one layer up — and it must
be fixed before any git-derived check can work. `git rm --cached` them, add them
to `.gitignore` (which already correctly ignores `logs/`, `*.db`, `*.key`).

Then, in order:

1. **`git --no-optional-locks status --porcelain` must be empty; `git rev-parse HEAD`
   is the delivery identity.** Both hand-maintained checks get deleted. This is
   verbatim the Linux kernel's own dirty check (`scripts/setlocalversion`), and
   `--no-optional-locks` is why: it takes no `.git/index.lock`, so it is safe on
   a read-only or concurrently-open tree — `git describe --dirty` is not. Use
   `--porcelain` v1, whose format is contractually stable. **Do not** use
   `git diff-index --quiet HEAD` as the primary check: it doesn't refresh the
   index, so a bare ctime change reads as dirty. Ignored files are invisible;
   an unexpected new file still shows as `??` and turns the gate red. That is
   the behaviour you want.
2. **If a manifest survives, generate it from `git ls-files`, not a directory
   walk.** The phantom becomes structurally impossible — a deleted file is not
   in `ls-files`. The OUTPUTS exclusion list is deleted, because outputs are
   ignored and therefore never enumerated. `git ls-files -s` already emits
   mode + blob SHA per file: a manifest git regenerates on demand. If you compare
   hashes, use `git hash-object --stdin-paths` (it applies the same filters),
   never raw `hashlib` — `.gitattributes` CRLF conversion will otherwise give
   you phantom mismatches on Windows.
3. **Steal PyPA `RECORD`'s two tricks:** the manifest lists *itself* with an
   empty hash (no chicken-and-egg, no special case), and generated files get an
   entry with *no hash* rather than no entry — strictly better than an exclusion
   list, because the file's existence is still declared.
4. **Signed tags** (`git tag -s` / `git verify-tag`) only *after* #1, and know
   the limit: `git verify-commit` validates the commit object, never the working
   tree. It answers "who declared this a release", not "is this folder that
   release." **Skip in-toto** — its layout file is hand-maintained *with a
   built-in expiry*, the exact failure mode being escaped, and there is no
   separation-of-duty payoff when owner, functionary and verifier are one person.
   SLSA **Build L1 is the ceiling without CI** and it is a document, not a gate:
   have the launcher *write* `{commit, tree, tag, launched_at, host, command}`,
   ~20 lines. Skip gitsign — 10-minute certs, interactive browser OAuth, and
   Rekor network access on a production launch is more ceremony, not less.

**Do not make a `git archive` tarball hash the delivery identity.** Git 2.38
changed its internal gzip and every tarball's bytes changed; the maintainers
have never guaranteed stable archive checksums. Use `git rev-parse HEAD^{tree}`
— a Merkle root over exactly the tracked content — for the "same bits as last
launch?" line.

---

## 3. W2.7 / `/propose_code`: the Windows sandbox gap

The node refuses every code proposal on win32 because the sandbox needs `fork`
+ `resource.setrlimit`. Refusing is correct fail-closed behaviour, but the
feature is dead on the platform that runs production.

**Near-term unblock — Windows Job Object via stdlib `ctypes`/`kernel32`.**
Smallest delta: `spawn` is already the Windows default for `multiprocessing`, so
only `setrlimit` is actually missing. `JOB_OBJECT_LIMIT_PROCESS_MEMORY` and
`JOB_OBJECT_LIMIT_ACTIVE_PROCESS` give memory and process count properly. ~100
lines and **zero new dependencies** — which fits the reasoning that chose
waitress. No maintained wrapper library exists; the only one (`WinJobster`,
GPL-3.0, 2023, ≤3.11) sets no limits at all. Read `pynisher`'s
`limiters/windows.py` as a reference, don't depend on it — last release
2023-11-13, declares ≤3.10, and it assigns the job *inside the child*, so
untrusted code could relax its own limits.

Three gaps to close by hand, all documented by Microsoft:
* Job time limits are **user-mode CPU, not wall clock**, and only sampled
  periodically — a `sleep()` loop never trips them. Needs a parent-side
  `join(timeout)` → `TerminateJobObject` watchdog.
* `JOB_OBJECT_LIMIT_JOB_TIME` is **additive**, not a reset.
* **No file-size limit exists at all** — there is no `RLIMIT_FSIZE` equivalent.
  Use a write-denied working directory, or NTFS per-user quota (`fsutil quota`).

Also: `subprocess` exposes neither `CREATE_SUSPENDED` nor the child's thread
handle, so the textbook create-suspended → assign → resume dance needs
`win32process.CreateProcess`, or a pipe handshake where the child blocks on one
byte while the parent assigns it to the job.

**Write this into the design doc rather than discovering it later: a job object
is a resource boundary, not a security boundary.** It stops a proposal
exhausting RAM, CPU or PIDs. It does nothing to stop that proposal reading the
node keys off disk, opening a socket, or calling `ctypes` to undo the job. It
converts fail-closed refusal into DoS-safe execution, and nothing more.

**Actual destination — `wasmtime-py`.** The only candidate whose limits are
enforced by the *runtime* rather than the OS, so Windows stops being a special
case: `Store.set_limits(memory_size=…)`, `set_fuel()` (deterministic instruction
budget), `set_epoch_deadline()` (wall clock). Apache-2.0, 47.0.1 released
2026-07-20, prebuilt `win_amd64`/`win_arm64` wheels, no compiler. A WASI guest
cannot spawn processes at all — strictly stronger than `RLIMIT_NPROC`. Known
risk, open since 2024-10: [#254](https://github.com/bytecodealliance/wasmtime-py/issues/254)
— *"the bindings in this repository are not thread safe"*; confine each `Store`
to one thread or put the runtime in the spawned worker. Trade-off: with
`micropython-wasm` as the reference wrapper the proposal language becomes
MicroPython's subset, not CPython's.

**Ruled out, with reasons:** AppContainer/Win32 App Isolation is an access-control
boundary with **no memory or CPU limits at all** — wrong layer. `wasmer-python`
is dead (last release 2022-01, no 3.11+ wheel). `pywasm` is pure-Python with a
perfect dependency profile but has no fuel/memory/timeout support and concedes
its own performance. Pyodide cannot leave a JS engine. Prebuilt CPython
`python.wasm` pins a security-relevant binary to an unmaintained 2023 build.
Every mainstream Linux sandbox (nsjail, firejail, gVisor, Firecracker, codejail,
E2B) is Linux/KVM-only. **RestrictedPython is not a resource limiter and its
escape record is current** — two High-severity advisories in the last three
months (GHSA-hp3v-5vw7-fx9w 2026-07-20, GHSA-ffg3-p8fm-mjx2 2026-06-22). Use it
as an inner layer to reject obviously hostile ASTs early; never as the boundary.

---

## Recommended order

1. Untrack the four launcher outputs, `.gitignore` them. Prerequisite for
   everything in §2, and one command.
2. Settle the five unmerged branches, and get off `p9/platform-correct-owner-only`
   onto a decided `main`.
3. Re-key the peer backoff on failure count + error class (§1, items 1–3). This
   is a live correctness issue on the production platform, not a cleanup.
4. Replace both integrity checks with `git status --porcelain` + `rev-parse HEAD`.
5. Job objects to un-refuse `/propose_code` on Windows, with the resource-vs-security
   boundary written into the design doc. `wasmtime-py` behind the same interface
   when there's appetite.
