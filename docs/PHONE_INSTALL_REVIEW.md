# C1 — phone/node-install.sh, node-install-v2.sh, covenant-doctor.sh: static Termux review (2026-08-22)

**Status of C1 before this:** blocked since 2026-08-20 — "`phone/node-install.sh` has never run; Termux uses Bionic libc, not glibc. Verify or mark clearly as untested." The scripts were on L's PC and not in the project, so no scheduled run could read them. They were pulled in over the device bridge this run.

**Nothing here has been run on hardware.** The phone has not arrived. This is a static review against the shipped core (`covenant_unified_v8.py` v8.28, 8609 lines) and `requirements.txt`; every claim is either a quoted line or a documented Termux behaviour, and where a claim needed measuring it says so.

# Termux static review — `node-install.sh`, `node-install-v2.sh`, `covenant-doctor.sh`

Verified against the shipped core (`covenant_unified_v8.py`, v8.28, 8609 lines, read from the project) and `requirements.txt`. Line numbers in the core are cited where a script's assumption contradicts it.

---

## BLOCKER — install cannot work

**1. `node-install.sh:30,35` — Flask/Werkzeug are never installed. The node cannot import.**
```
pkg install -y python openssl libffi rust binutils >/dev/null 2>&1
python -c "import cryptography" 2>/dev/null && ok "cryptography already present" || {
```
v1 installs and verifies `cryptography` only. `covenant_unified_v8.py:223-225` are unconditional top-level imports: `from flask import Flask, request, jsonify`, `from werkzeug.serving import run_simple`, `from werkzeug.exceptions import RequestEntityTooLarge`. `requests` is lazy (`:8068`) so it survives, Flask does not. Install prints five green `ok`s, then `node-run.sh` dies with `ModuleNotFoundError: No module named 'flask'` into `state/node.log`, which nothing reads.
Fix: add `pip install --no-cache-dir flask requests` and gate on `python -c "from werkzeug.serving import run_simple; import flask, requests"` (v2 does half of this — see #12).

**2. `node-install.sh:46` — `covenant_path_pattern.py` is not copied. Hard import at core line 216.**
```
for f in covenant_unified_v8.py covenant_client.py genesis.json; do
```
`covenant_unified_v8.py:216` is `import covenant_path_pattern`, top-level, unguarded (used at `:3465`, `:3493`). `ANDROID_VPN_SYNC.md` already states the PC needs it "beside the core". Same silent death as #1.
Fix: add `covenant_path_pattern.py` to the loop. v2 fixed this.

**3. `node-install.sh:47` / `node-install-v2.sh:78` — `~/storage/` does not exist until `termux-setup-storage` is run, and neither script runs or checks for it.**
```
    if [ -f "$HOME/storage/downloads/$f" ]; then cp "$HOME/storage/downloads/$f" "$HERE/$f"; ok "$f"
```
On a fresh Termux `$HOME/storage` is absent (the symlink farm is created only by `termux-setup-storage`, which raises the runtime storage permission dialog). Every test is false, every file reports `X f missing from Downloads`, and the script exits 1 blaming the user for not downloading files they did download. This is the first thing that will happen on the real phone.
Fix: before the loop, `[ -d "$HOME/storage" ] || { warn "run: termux-setup-storage (grant the permission), then re-run"; exit 1; }`.

**4. `node-install.sh:30,37` / `node-install-v2.sh:53,60` — no compiler, and Termux pip cannot use any prebuilt aarch64 wheel.**
```
pkg install -y python openssl libffi rust binutils curl >/dev/null 2>&1
    pip install --no-cache-dir cryptography >/dev/null 2>&1 \
```
Termux's pip rejects `manylinux*` wheels — they are glibc-linked and would fault against Bionic — so *every* extension package is built from source, not just `cryptography`. `binutils` is a linker, not a compiler: the `python` package does not depend on `clang`, so `pip install` of any sdist fails at `clang: command not found`. `cryptography` ≥42 also needs `maturin`/`setuptools-rust` (themselves manylinux-only on PyPI → also built from source) and `pkg-config` to locate OpenSSL. `rust` alone is not a toolchain here.
Fix: `pkg install -y python clang make pkg-config openssl libffi binutils rust`, and try the prebuilt first — `pkg install -y python-cryptography` *before* falling back to pip. The advice to do that is already in the script at `:40`/`:62`, but only printed after the 15-minute build has already failed.

**5. `node-install.sh:30` / `node-install-v2.sh:53` — package install output and exit status both discarded, and no `pkg update`.**
```
pkg install -y python openssl libffi rust binutils curl >/dev/null 2>&1
```
Termux mirrors rotate; a Termux installed more than a few weeks ago 404s on every `pkg install` until `pkg update` runs. With `2>&1` to `/dev/null` and no `||`, a total install failure is invisible and the script proceeds to `pip install cryptography` with no python at all.
Fix: `pkg update -y || { bad "pkg update failed — pick a mirror: termux-change-repo"; exit 1; }` then `pkg install -y … || { bad "pkg install failed"; exit 1; }`, without the redirect.

**6. `node-install-v2.sh:115` — `COVENANT_JUDGE_PROVIDERS=local` is not a registered provider. The node raises at construction.**
```
COVENANT_JUDGE_PROVIDERS=local
```
`node-run.sh:182` sources `node.env` under `set -a`, so this reaches the node process. `covenant_unified_v8.py:8160-8194` registers exactly `claude`, `openai`, `google`, `mock`. `build_semantic_quorum` (`:8228`) calls `JudgeProviderRegistry.build(name, i)`, which at `:8149` raises `ValueError: unknown judge provider: 'local' (known: ['claude','google','mock','openai'])`. That call sits in `CovenantUnifiedMaster.__init__` (`:6655`), so the node dies before binding a port — unless `run_with_ollama_judge.py` calls `JudgeProviderRegistry.register("local", …)` before constructing the master. That file is not in the bundle (see #7), so this is unverifiable and the smoke test at `:155` never exercises it.
Fix: have the installer prove it, not assume it — `python -c "import run_with_ollama_judge, covenant_unified_v8 as c; c.JudgeProviderRegistry.build('local',0)"` as a gate, or set `COVENANT_JUDGE_PROVIDERS` to whatever name that module actually registers.

**7. `node-install-v2.sh:75-77` — five of the seven required files do not exist in the shipped bundle.**
```
for f in covenant_unified_v8.py covenant_client.py covenant_path_pattern.py \
         covenant_judge_local.py covenant_judge_ollama.py \
         run_with_ollama_judge.py genesis.json; do
```
`MANIFEST.json` and the project tree contain `covenant_unified_v8.py`, `covenant_path_pattern.py`, `preflight.py`, the test suites — and no `covenant_judge_local.py`, `covenant_judge_ollama.py`, `run_with_ollama_judge.py`, `judge_suite.py`, `judge_bench.py`. If they only exist on the PC they must be added to the manifest and hashed; if they do not exist, v2 is unrunnable by construction (`:85` exits 1) and every judge finding below is moot.
Fix: resolve before the phone arrives; add them to `MANIFEST.json` so `verify_bundle.py` covers them.

**8. `covenant-doctor.sh:13,19-24` — the doctor measures an artifact neither installer creates.**
```
LOG="$STATE/runs.log"
...
    echo "  No run log at all. The job has NEVER run."
    echo "  -> run ./covenant-run.sh by hand once to prove it works,"
```
Neither installer writes `runs.log` or `last_run_epoch`, creates `covenant-run.sh`, or installs a crontab — grep across both is empty. They produce `state/node.log` and `node-run.sh`. So after either install the doctor takes the first branch every time, says "the job has NEVER run", and points at a script that does not exist. It is a health check for a different (daily-cron) artifact, wired to the node's state directory by coincidence of path.
Fix: point it at `state/node.log` and `node-run.sh`, or ship the cron job it was written for. Full answer to question 5 below.

---

## DEGRADED — runs, but wrong

**9. `node-install.sh:35` / `node-install-v2.sh:58` — `import cryptography` is the wrong probe; it passes on a broken build.**
```
python -c "import cryptography" 2>/dev/null && ok "cryptography present" || {
```
The top-level `cryptography` package is pure Python. The node needs `cryptography.hazmat.bindings._rust` (`covenant_unified_v8.py:220-222` → `rsa`, `padding`, `serialization`). A half-finished Rust build, or a `cryptography` left behind by a failed earlier attempt, imports clean here and raises at node boot.
Fix: `python -c "from cryptography.hazmat.primitives.asymmetric import rsa; rsa.generate_private_key(65537,2048)"`.

**10. `node-install-v2.sh:152` — `curl -s` exits 0 on HTTP 404. "Ollama reachable" passes against anything answering HTTP.**
```
    if curl -s -m 10 "$BASE/api/tags" >/dev/null 2>&1; then
```
Verified: `curl -s` on a 404 returns exit 0; `curl -fsS` returns 22. A router admin page, an unrelated service, or an Ollama with zero models pulled all report `ok Ollama reachable at …`.
Fix: `curl -fsS -m 10 "$BASE/api/tags" | grep -q '"models"'`.

**11. `node-install-v2.sh:151` — the URL suffix strip fails on a trailing slash or a CR, and #10 then converts the failure into a PASS.**
```
    BASE="${COVENANT_LOCAL_JUDGE_URL%/v1/chat/completions}"
```
Verified expansions: clean → `http://h:11434`; with a trailing `\r` (the file arrives via Windows/Downloads) → unchanged, so `BASE` keeps the whole path; trailing slash → likewise. curl then requests `…/v1/chat/completions/api/tags`, gets 404, and exits 0. A CR also rides into the node's `COVENANT_LOCAL_JUDGE_URL`.
Fix: strip CR when sourcing (`tr -d '\r'` on read, or `sed -i 's/\r$//' node.env`) and derive `BASE` by scheme+authority, not by suffix removal.

**12. `node-install-v2.sh:155` — the smoke test's stderr is discarded, so every failure is misreported as a judge failure.**
```
        if python - <<'PY' 2>/dev/null
```
A missing `flask`, a broken `_rust.so`, an absent `covenant_judge_ollama.py`, or the `ValueError` from #6 all land on the `else` branch at `:168`: `judge reachable but its verdict was wrong or it errored`, plus advice to run `judge_bench.py`. The one diagnostic that would name the cause is thrown away.
Fix: drop `2>/dev/null`, or capture to `$HERE/state/smoke.log` and print the tail on failure.

**13. `node-install-v2.sh:155-166` vs `:192` — the gate tests a different code path from the one that runs.**
```
r = O.OllamaJudge(judge_id="local:1").evaluate(
...
exec python run_with_ollama_judge.py --port 5041 --node-id PHONE \
```
The smoke test constructs `OllamaJudge` directly. It never runs `run_with_ollama_judge.py`, never calls `build_semantic_quorum()`, never sees `COVENANT_JUDGE_PROVIDERS=local`, and never boots a node. A green smoke test is therefore compatible with a node that cannot construct its sentinel at all (#6). The whole design of v2 rests on this gate.
Fix: make the gate `python run_with_ollama_judge.py --export-genesis /dev/null --node-id SMOKE` (or an equivalent boot-and-exit) and assert `/health` reports `judge_keyless: false`.

**14. `node-install-v2.sh:114` — `COVENANT_JUDGE_TIMEOUT` is not a variable the core reads, and the correct name would refuse to boot at this value.**
```
COVENANT_JUDGE_TIMEOUT=900
```
`covenant_unified_v8.py:7886` reads `COVENANT_JUDGE_TIMEOUT_S` (default `30`), and `:7887` is a module-level `assert 1.0 <= JUDGE_TIMEOUT_S <= 600.0`. So as written the setting does nothing and the phone judges at 30 s — the exact silent-rejection failure the header warns about. Renaming it to `COVENANT_JUDGE_TIMEOUT_S=900` makes the node die at *import* with `AssertionError: COVENANT_JUDGE_TIMEOUT_S=900.0 out of range [1, 600]`. `COVENANT_LOCAL_JUDGE_TIMEOUT`, `COVENANT_LOCAL_JUDGE_URL/MODEL`, `COVENANT_OLLAMA_NUM_CTX/NUM_PREDICT/KEEP_ALIVE` (`:109,113,116-118`) appear nowhere in the core either — they can only be read by the unshipped judge modules.
Fix: `COVENANT_JUDGE_TIMEOUT_S=600` (the asserted ceiling), and delete or verify the rest against the judge modules.

**15. `node-install-v2.sh:113-114` — a 600–900 s judge timeout is ~30–45 min of held `chain_lock` per transaction.**
Core `:8082` passes `JUDGE_TIMEOUT_S` into the request; `_retry_with_backoff(..., max_retries=2, base_delay_s=0.5)` (`:7895`) makes 3 attempts plus ~1.3 s backoff. `IMPROVEMENT_LOG` B5 measured the default as 91.3 s per tx per judge; at 600 s that is ~1801 s, at 900 s ~2701 s, sequential, **after** the PoW and **under `chain_lock`** — blocking `/chain`, peer block accept, tx fetch and tip gossip. On a phone whose link drops in Doze this reads as a hung node.
Fix: keep the phone at or near the default and let a timeout fail fast; the "generous" setting converts a slow link into a wedged node rather than a rejecting one.

**16. `node-install.sh:91` / `node-install-v2.sh:217` — the documented start command has no `nohup`/`setsid`/`disown`.**
```
echo "  start   :  ~/covenant/node-run.sh &"
```
Backgrounded from an interactive Termux shell, the node is a job of that shell and takes SIGHUP when the session is torn down (app swiped away, terminal closed). `termux-wake-lock` (`:184`) keeps the CPU awake; it does not keep the session alive. The node dies the first time the user closes Termux, and only the absence of new log lines records it.
Fix: `nohup ~/covenant/node-run.sh >/dev/null 2>&1 & disown`, or install it under `termux-services` (`pkg install termux-services`, `sv up covenant`).

**17. `node-install.sh:80-87` / `node-install-v2.sh:200-208` — the boot script is written and reported `ok` without checking that Termux:Boot exists.**
```
    chmod +x "$HOME/.termux/boot/start-covenant-node"
    ok "boot script installed"
```
`~/.termux/boot/` is inert unless the separate **Termux:Boot** app is installed *and opened once*. Creating the directory succeeds regardless. v2 goes to real trouble to refuse this step when the judge is unproven, then claims success for a step that may be a no-op.
Fix: `pm list packages 2>/dev/null | grep -q com.termux.boot || warn "Termux:Boot is NOT installed — nothing will restart after a reboot"`; downgrade the message to "boot script written".

**18. `node-install.sh:54-63` / `node-install-v2.sh:126-139` — the generated peers file is 100% comments, and nothing gates on it.**
Both write a peers file with every peer line commented out, then tell the user to start the node. `${PEERS:+--peers "$PEERS"}` expands to nothing, the node boots with zero peers, `/health` sets `"no peers configured -- this node is isolated"` in `warnings` (core `:6548`) — and neither script ever reads `/health`. v1's closing check (`:92`, `curl … /chain`) returns a height-1 chain and looks correct. A node that is a backup of nothing.
Fix: mirror the judge gate — if `PEERS` is empty after parsing, refuse to install the boot script and say why.

**19. `node-install.sh:27` / `node-install-v2.sh:50` — the Termux detection hardcodes the primary-user data path.**
```
[ -d "/data/data/com.termux" ] || { bad "not Termux -- get Termux from F-Droid, not Play Store"; exit 1; }
```
Under a work profile or secondary Android user the prefix is `/data/user/<N>/com.termux/files/usr`, and `/data/data/com.termux` does not resolve. The install refuses to run on a correct Termux. The same assumption is baked into all four shebangs.
Fix: `[ -n "${TERMUX_VERSION:-}" ] && [ -d "${PREFIX:-}" ] || { … }`.

**20. Both installers — `COVENANT_TIP_GOSSIP_INTERVAL` is never set.**
Core `:523` defaults to 120 s. `IMPROVEMENT_LOG` C4 and `ANDROID_VPN_SYNC.md` both conclude the phone's cost is radio wake-ups (~720/peer/day, est. ~3 %/day on cellular) and name `COVENANT_TIP_GOSSIP_INTERVAL=600` as the lever. Neither script applies it; v2's `node.env` — the natural place — omits it.
Fix: add `COVENANT_TIP_GOSSIP_INTERVAL=600` to `node.env`.

**21. `node-install-v2.sh:199` — the judge gate is one-shot at install time; nothing re-checks it, ever.**
```
if [ "${JUDGE_OK:-0}" = "1" ]; then
```
The failure v2 exists to prevent — a node that boots, peers, serves `/chain`, and silently rejects everything — is prevented only at t=0. The PC going down, Ollama unbound, the tailnet dropping, or the model being deleted all reinstate it, with the boot script now installed and firing daily. `/health` would show it (`judge_keyless`, `degraded`, and the `judge_unavailable` anomaly kind added in v8.24); nothing polls `/health`, and the doctor does not know the node exists.
Fix: a periodic check that curls `localhost:5041/health` and alerts on `degraded: true` or a rising `judge_unavailable` count — that is what `covenant-doctor.sh` should have been.

**22. `covenant-doctor.sh:68-77` — even with a correct log, the verdict is a timestamp, not a liveness check.**
```
if [ "$AGE_H" -gt 30 ]; then
...
    echo "  VERDICT: alive. Last run ${AGE_H}h ago."
```
No `pgrep` of the node, no port check, no HTTP request. A node that wrote its last line and then crashed, or whose listener thread died while Flask kept answering (a failure the core's own `/health` docstring at `:6519` says has already happened), reports **alive**. The doctor's stated purpose — "a missed morning looks identical to a quiet morning" — is exactly what it fails to distinguish for the node.
Fix: add `curl -fsS -m 5 localhost:5041/health` and assert `degraded == false`, `chain_height` advancing, `dead_peers == 0`.

**23. `covenant-doctor.sh:22,70` — the remedy it prints is `crond`, which Termux does not have.**
```
    echo "    1. is cron alive?          pgrep crond || crond"
```
No cron in Termux by default (`pkg install cronie`, or `termux-services`); neither installer installs one; `pgrep` needs `procps`, also not guaranteed. So the fix instruction is `command not found` twice over, and there is nothing scheduled to be alive.
Fix: replace with `sv status covenant` (termux-services) or a `pgrep -f covenant_unified_v8` against the node that is actually installed.

---

## NOTE

**24. `node-install.sh:33` / `node-install-v2.sh:56` — `$(uname -m)` is not a Rust target triple on 32-bit ARM.**
```
export CARGO_BUILD_TARGET="$(uname -m)-linux-android"
```
`aarch64` → `aarch64-linux-android` ✓, `x86_64` ✓; `armv7l`/`armv8l` → `armv7l-linux-android`, which is not a target Rust knows (`armv7-linux-androideabi` is), and cargo aborts. Also, setting `CARGO_BUILD_TARGET` at all puts cargo into cross-compile mode and stops `RUSTFLAGS` applying to build scripts.
Fix: map explicitly, or simply omit both vars and let Termux's cargo use its host default, which is already correct.

**25. `node-install.sh:34` / `node-install-v2.sh:57` — `RUSTFLAGS` does not reach the C half of the build.**
```
export RUSTFLAGS="-C link-arg=-Wl,-z,max-page-size=16384"
```
The 16 KB-page link arg is right for Android 15, but `cryptography` also compiles/links C against OpenSSL; that path reads `CFLAGS`/`LDFLAGS`, not `RUSTFLAGS`, and `openssl-sys` needs `OPENSSL_DIR` or `pkg-config` to find `$PREFIX`.
Fix: also `export LDFLAGS="-Wl,-z,max-page-size=16384 -L$PREFIX/lib" CFLAGS="-I$PREFIX/include" OPENSSL_DIR="$PREFIX"`, and install `pkg-config`.

**26. `node-install-v2.sh:91,144,182` — `node.env` is executed as bash and never mode-restricted.**
```
cat > "$HERE/node.env" <<'ENV'
set -a; . "$HERE/node.env" 2>/dev/null; set +a
```
It is documented as a settings file but is `source`d, so anything pasted into it runs as shell in the installer *and* in `node-run.sh`. It is created under the default umask (0644). It is the file where a judge credential would end up.
Fix: `chmod 600 "$HERE/node.env"` after writing; parse with a `while read` + `export` loop rather than `.` if arbitrary values are expected.

**27. `node-install-v2.sh:188` — the judge URL is appended to `node.log` on every start.**
```
echo "$(date '+%F %T') node starting (peers: ${PEERS:-NONE}) judge: ${COVENANT_LOCAL_JUDGE_URL:-UNSET}" >> "$HERE/state/node.log"
```
Harmless for a bare `http://100.x:11434/…`; a cleartext credential if anyone ever uses `http://user:token@host/…`, and it accumulates one copy per start in an unrotated file.
Fix: log the host:port only — `${COVENANT_LOCAL_JUDGE_URL#*://}` truncated at the first `/`, with any `user:pass@` stripped.

**28. Key material — correctly placed, undocumented, and one copy step from leaving the device.**
`node-run.sh` sets `COVENANT_DB_PATH="$HERE/phone.db"` (`v1:71`, `v2:185`), so the core writes the node identity to `$HOME/covenant/phone.db.key` at mode 0600 (core `:6633`, `_load_or_create_identity`). That is Termux app-private storage — not synced, not world-readable. Good. But `DEPLOYMENT.md` is explicit that this file *is* the operator credential for `/mine`, `/crisis/clear`, `POST /peers` and the genesis mint key, and neither installer mentions it, backs it up, or warns against the obvious backup route.
Fix: print one line after install naming `~/covenant/phone.db.key` as the credential, and state explicitly that copying it through `~/storage/downloads` publishes it.

**29. `~/storage/downloads` is off-device-syncing shared storage, and it is the install's delivery channel.**
`$HOME/storage/downloads` resolves to `/storage/emulated/0/Download`: readable by every app holding storage permission, and the default target of Google Drive / "Files by Google" / OneDrive backup. Both scripts `cp` from it (`v1:47`, `v2:78,83`) and never remove the staged originals, so `covenant_unified_v8.py`, `genesis.json` and the judge modules persist there. Nothing secret is staged today; the risk is that the documented way to move files onto the phone is a synced folder, and the operator credential lives one `cp` away from it.
Fix: `rm -f "$HOME/storage/downloads/$f"` after a successful copy, and state that the key file must never transit that directory.

**30. `node-install.sh:73` / `node-install-v2.sh:192` — the port is hardcoded inside the quoted heredoc while the installer computes it.**
```
exec python run_with_ollama_judge.py --port 5041 --node-id PHONE \
```
`API_PORT=5041` at `:39` is used for the banners; `node-run.sh` carries a literal `5041`. Changing `API_PORT` changes what the installer prints and not what runs.
Fix: unquote just that value, or `--port ${COVENANT_API_PORT:-5041}` in the generated script.

**31. Neither script runs `preflight.py`,** which `DEPLOYMENT.md` says to run before every launch ("ALWAYS run this first", exit 0/1/2) and which checks precisely these silent conditions — keyless judge, self-minted genesis, world-readable identity key. It is in the bundle. `preflight_port_check` inside the core (`:8447`) covers the port trio and the API-vs-P2P peer-port confusion automatically, so that part is safe without it.

**32. `node-install-v2.sh:154` — `cd "$HERE"` runs in the main shell inside one branch,** so the installer's cwd depends on which judge path was taken. Everything after uses absolute paths, so it is currently harmless; it will not stay harmless. Fix: `( cd "$HERE" && python - <<'PY' … )`.

**33. `rust` is a ~600 MB install and the build is 5–15 min on a phone; no free-space or battery check.** A device that runs out of space mid-build leaves a partial `cryptography` that satisfies the probe in #9.

---

## Question 4 — what v2 fixed, and what it still gets wrong

**Genuinely fixed:**
- `covenant_path_pattern.py` added to the copy list (`:75`) — fixes the core's hard import at `:216`.
- `flask` + `requests` installed and probed (`:64-67`).
- `curl` added to the package list (`:53`) — v1 used no curl but told the user to (`v1:92`).
- `mkdir -p "$HERE/state"` moved into `node-run.sh` (`:187`), so the runner no longer depends on install-time ordering.
- Idempotence: `node.env` and `node-peers.conf` are not clobbered on re-run (`:88`, `:123`).
- The boot script is gated on evidence (`:199`) instead of installed unconditionally — the right instinct, and the single best idea in either file.
- Closing check changed from `/chain` to `/health` (`:218`) — `/chain` returns 200 on a node rejecting 100% of traffic; `/health` carries `degraded` and `warnings` (core `:6514-6581`).
- `unset COVENANT_INSECURE_MOCK_JUDGE` in the runner (`:186`) so the smoke test's mock flag cannot leak into the node.
- F-Droid-not-Play-Store named in the failure message (`:50`).

**Still wrong in v2:** #3 (storage), #4 (toolchain), #5 (swallowed `pkg` errors), #6 (`providers=local`), #7 (missing judge modules), #9 (`import cryptography`), #10–13 (the judge gate: 404-passes, CR/slash strip, hidden stderr, wrong code path), #14–15 (timeout name/range/lock), #16 (no `nohup`), #17 (Termux:Boot unverified), #18 (empty peer list ungated), #19 (data path), #20 (gossip interval), #21 (one-shot gate), #26–27, #30.

Net: v2 fixes v1's two import-level blockers and adds a real gate, but the gate validates a code path the node does not use, and passes against a 404.

## Question 5 — would `covenant-doctor.sh` detect a broken install?

No. It cannot detect anything about this node, in either direction.

- Against either install it always takes the `[ ! -f "$LOG" ]` branch (#8) — the file `runs.log` is never created by anything in this bundle — prints "the job has NEVER run", and exits 1 pointing at `covenant-run.sh`, which does not exist. That is its behaviour for a perfectly healthy node.
- If `runs.log` did exist but `last_run_epoch` did not, `LAST_EPOCH=0` (`:26`) makes `AGE_H` ≈ 490,000 and the verdict **STALE** — wrong, but at least it fails safe.
- The "reports healthy on a node that is not running" case is real once both files exist: whatever writes `last_run_epoch` is a *wrapper*, not the node. The verdict at `:76` is derived purely from that timestamp plus the day-gap scan (`:39-65`). No process check, no port check, no HTTP request (#22). A node killed by Android's battery manager five minutes after its wrapper stamped the file reports `VERDICT: alive`.
- Its three remedies (`:70-74`) are `crond` (absent, #23), Termux battery exemption (correct and the most valuable line in the file), and Termux:Boot (correct, and the only place in the whole bundle where the Termux:Boot requirement is stated — the installers that create the boot script do not, #17).

Minimum viable rewrite: read `state/node.log`, `pgrep -f covenant_unified_v8`, and `curl -fsS -m 5 localhost:5041/health`, then assert `degraded == false`, `judge_keyless == false`, `own_genesis == false`, `peers > 0`, and `chain_height` strictly greater than the value recorded on the previous run. Every one of those fields already exists in the core's `/health` payload (`:6553-6581`).

## Question 6 — keys, secrets, and off-device folders

- Nothing in any of the three scripts prints, echoes, or copies a private key. The identity key is created by the core, not by the scripts, at `~/covenant/phone.db.key`, mode 0600, inside Termux app-private storage — the right place, not synced, not readable by other apps (#28). The gap is documentation, not placement.
- `node.log` records the judge URL verbatim on every start (#27) — the only path by which a script writes a potential credential to disk.
- `node.env` is created world-readable-by-default and is `source`d as shell (#26) — the file most likely to hold a token, with the weakest handling.
- `~/storage/downloads` = `/storage/emulated/0/Download` is the install's staging area (#29): shared, world-readable to any app with storage permission, and backed up off-device by default on most phones. The scripts read from it and never clean it, so `covenant_unified_v8.py`, `genesis.json` and the judge modules persist there. Nothing secret is staged today; the risk is that the documented way to move files onto the phone is a synced folder, and the operator credential lives one `cp` away from it.
