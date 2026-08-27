"""verify_deploy.py -- close the three-claims gap in one command (M38).

WHY THIS EXISTS.  `project_write` is not delivery (M25), a file on disk is not
the running process (P11), and the three drift INDEPENDENTLY: a delivery moves
disk without moving running, a restart moves running without moving disk. This
project has been caught by that repeatedly -- fourteen node versions delivered
to a machine that ran none of them, and a v8.35 restart that sat one
double-click away for two days while the log recorded it as shipped.

So this asks all three questions in one run and refuses to report success
unless all three agree:

  1. DISK      -- do the delivered files hash to what the run that built them
                  says they should?
  2. COMPANIONS-- are the imports each one needs actually beside it?
  3. RUNNING   -- after the restart, does each node's own /health report the
                  version and source hash that are ON DISK?

NOTE ON THE HASH COMPARISON, because the field name misleads.  /health's
`source_sha256` does NOT contain a sha256; it contains CORE_SOURCE_SHA12, the
first 12 hex characters of one (covenant_unified_v8.py line 7362, pinned by
test_p11 V6b). So claim 3 is compared over 12 characters -- 48 bits -- which is
ample for detecting "nobody restarted the node" and is NOT a tamper check.
Claim 1 compares the full 64. The first draft of this script compared /health's
12 against a full 64 and reported MISMATCH on a perfectly correct deployment;
a verifier that cries wolf is worse than none, because it teaches its operator
to skip it.

It fails CLOSED and it is honest about what it could not determine: a node it
cannot reach is reported as UNKNOWN, never as OK.

Usage:
    python verify_deploy.py              # verify, restart, verify running
    python verify_deploy.py --no-restart # verify disk only, touch nothing
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------- manifest
# Written by the run that produced these files. If you edit a file by hand,
# this will fail -- which is the point.
EXPECTED_VERSION = "v8.37"
EXPECTED_LINES = 9846
MANIFEST = {
    "covenant_unified_v8.py":
        "07e097f3e37f51bf1c53df1873cc32e980da5f8146035cd98dbf780386e85cb2",
    "test_a3s_send_bounds.py":
        "bd0ab67ae2f62a12b6a0253926511ca7cffa6155e3a74bb6633d3875006d1d7c",
    "run_all_tests.sh":
        "5727b42d1ed8542e383588b33668fea5e5ef3cf679f23da84c445224ea21cd37",
    "run_local_sweep.py":
        "309053b11edac861a54bb4218411bc5b3245dae8b590dc66fb4ba302f8de8c0f",
}
# file -> module it imports that must sit in the same directory
COMPANIONS = {
    "covenant_unified_v8.py": "covenant_path_pattern.py",
    "test_a1_kill_matrix.py": "test_a9_relay_race.py",
}
NODES = [("A", 5000), ("B", 5020)]
RESTART_BAT = "AB_RESTART_NODES.bat"
OLLAMA_URL = "http://127.0.0.1:11434"

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
lines_out = []


def say(s=""):
    print(s, flush=True)
    lines_out.append(s)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def health(port, timeout=4.0):
    """/health or None. Never raises -- an unreachable node is UNKNOWN."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health",
                                     headers={"User-Agent": "verify-deploy/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main():
    restart = "--no-restart" not in sys.argv
    say("=" * 68)
    say(f"verify_deploy  {time.strftime('%Y-%m-%d %H:%M:%S')}  expecting "
        f"{EXPECTED_VERSION}")
    say(f"folder: {HERE}")
    say("=" * 68)

    failures = []
    unknowns = []

    # ------------------------------------------------------- 1. DISK
    say("")
    say("--- 1. DISK: do the delivered files hash to what was built? ---")
    disk_sha = None
    for name, want in sorted(MANIFEST.items()):
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            say(f"  MISSING  {name}  -- not copied into this folder")
            failures.append(f"{name} missing")
            continue
        got = sha256_of(path)
        if name == "covenant_unified_v8.py":
            disk_sha = got
        if got == want:
            say(f"  ok       {name}  {got[:12]}")
        else:
            say(f"  MISMATCH {name}")
            say(f"           on disk  {got[:12]}")
            say(f"           expected {want[:12]}")
            say(f"           -- an OLD copy, a partial copy, or a hand edit")
            failures.append(f"{name} hash mismatch")

    # ------------------------------------------------------- 2. COMPANIONS
    say("")
    say("--- 2. COMPANIONS: are the sibling imports present? ---")
    for owner, needed in sorted(COMPANIONS.items()):
        if not os.path.exists(os.path.join(HERE, owner)):
            say(f"  skip     {owner} is not here, so {needed} is not required")
            continue
        if os.path.exists(os.path.join(HERE, needed)):
            say(f"  ok       {needed}  (needed by {owner})")
        else:
            say(f"  MISSING  {needed}  -- {owner} will not import without it")
            failures.append(f"{needed} missing")

    if failures:
        say("")
        say("STOPPING BEFORE RESTART: the files on disk are not the files that")
        say("were built and tested. Restarting now would run something nobody")
        say("has verified. Fix the copy, then run this again.")
        return finish(failures, unknowns)

    if not restart:
        say("")
        say("--no-restart given: disk verified, nothing was started or stopped.")
        say("The RUNNING processes are therefore UNVERIFIED by this run.")
        unknowns.append("running version not checked (--no-restart)")
        return finish(failures, unknowns)

    # --------------------------------------------- 2b. THE JUDGE IS UP
    # AB_RESTART_NODES.bat kills the nodes and THEN calls covenant_prod.bat,
    # which aborts before starting anything if Ollama does not answer on
    # 11434 ("a judge that cannot be reached fails CLOSED"). Those two facts
    # compose into a restart that can take the chain down and leave it down:
    # stop succeeds, start refuses, and the operator is looking at a console
    # that scrolled past. So ask first, and refuse to touch a running node
    # over a judge that is not there.
    say("")
    say("--- 2b. JUDGE: is Ollama answering before we stop anything? ---")
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags",
                                     headers={"User-Agent": "verify-deploy/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            tags = json.loads(r.read().decode())
        models = [m.get("name") for m in tags.get("models", []) if m.get("name")]
        say(f"  ok       ollama answering, {len(models)} model(s): "
            f"{', '.join(models[:6]) or '(none listed)'}")
        if not models:
            say("  WARNING  ollama is up but reports no models -- "
                "covenant_prod.bat's fit_check will abort the start")
            failures.append("ollama reports no models")
    except Exception as e:
        say(f"  DOWN     {OLLAMA_URL} did not answer ({type(e).__name__})")
        say("           NOT restarting. The launcher would stop the nodes and")
        say("           then covenant_prod.bat would abort before starting")
        say("           them, leaving this machine running nothing at all.")
        say("           Start Ollama, then run this again.")
        failures.append("ollama unreachable -- restart refused")

    if failures:
        say("")
        say("STOPPING BEFORE RESTART: see above. Nothing was stopped or")
        say("started; the nodes are still running whatever they were running.")
        return finish(failures, unknowns)

    # ------------------------------------------------------- 3. RESTART
    say("")
    say("--- 3. RESTART ---")
    bat = os.path.join(HERE, RESTART_BAT)
    if not os.path.exists(bat):
        say(f"  {RESTART_BAT} is not here -- restart the nodes by hand, then")
        say(f"  re-run:  python verify_deploy.py --no-restart")
        unknowns.append(f"{RESTART_BAT} absent, nodes not restarted")
        return finish(failures, unknowns)
    say(f"  running {RESTART_BAT} ...")
    try:
        # stdin=DEVNULL, and it is load-bearing. AB_RESTART_NODES.bat ends in
        # `pause`, which is correct for a human double-click and fatal for a
        # caller: capture_output redirects stdout/stderr but NOT stdin, so the
        # launcher would sit waiting for a keypress whose prompt went into the
        # captured pipe -- an invisible hang until the 300 s timeout, reported
        # as "restart launcher failed" on a restart that actually worked.
        # Under a redirected stdin `pause` returns at once. So do the `timeout
        # /t N` waits inside the launcher ("Input redirection is not
        # supported"), which is why claim 4 below polls /health for 90 s on its
        # own account rather than trusting the launcher to have waited.
        p = subprocess.run([bat], cwd=HERE, capture_output=True, text=True,
                           timeout=300, shell=False,
                           stdin=subprocess.DEVNULL)
        say(f"  exit code {p.returncode}")
    except Exception as e:
        say(f"  restart launcher failed: {type(e).__name__}: {e}")
        unknowns.append("restart launcher failed")
        return finish(failures, unknowns)

    # ------------------------------------------------------- 4. RUNNING
    say("")
    say("--- 4. RUNNING: does each node report the source that is on disk? ---")
    say("    (/health is rate-limited 20/60s per node -- polling every 3 s)")
    for label, port in NODES:
        got = None
        deadline = time.time() + 90
        while time.time() < deadline:
            got = health(port)
            if got is not None:
                break
            time.sleep(3)
        if got is None:
            say(f"  UNKNOWN  node {label} :{port} did not answer within 90 s")
            say(f"           -- NOT reported as ok. Check its console window.")
            unknowns.append(f"node {label} unreachable")
            continue
        ver = got.get("version")
        src = str(got.get("source_sha256") or "")     # 12 chars, see NOTE above
        ln = got.get("source_lines")
        want12 = (disk_sha or "")[:12]
        agree = (ver == EXPECTED_VERSION and src == want12
                 and ln == EXPECTED_LINES)
        if agree:
            say(f"  ok       node {label} :{port}  {ver}  {src}  "
                f"{ln} lines  == disk (first 12 of the digest)")
        else:
            say(f"  MISMATCH node {label} :{port}")
            say(f"           running {ver} {src[:12] or '(no version field)'} "
                f"{ln} lines")
            say(f"           on disk {EXPECTED_VERSION} {want12} "
                f"{EXPECTED_LINES} lines")
            if not src:
                say(f"           no source_sha256 at all: this process predates")
                say(f"           v8.31, so it is older than anything delivered.")
            failures.append(f"node {label} running != disk")
    return finish(failures, unknowns)


def finish(failures, unknowns):
    say("")
    say("=" * 68)
    if failures:
        say(f"RESULT: FAIL -- {len(failures)} problem(s)")
        for f in failures:
            say(f"  - {f}")
    elif unknowns:
        say(f"RESULT: INCOMPLETE -- nothing failed, but {len(unknowns)} thing(s)")
        say("        could not be determined. This is NOT a pass.")
        for u in unknowns:
            say(f"  - {u}")
    else:
        say("RESULT: PASS -- project, disk and running process all agree.")
    say("=" * 68)
    try:
        with open(os.path.join(HERE, "DEPLOY_VERIFY.txt"), "w",
                  encoding="utf-8") as fh:
            fh.write("\n".join(lines_out) + "\n")
        say("written to DEPLOY_VERIFY.txt")
    except Exception as e:
        say(f"(could not write DEPLOY_VERIFY.txt: {type(e).__name__})")
    return 1 if failures else (2 if unknowns else 0)


if __name__ == "__main__":
    sys.exit(main())
