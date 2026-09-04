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
first 12 hex characters of one (CORE_SOURCE_SHA12, defined near the top of
covenant_unified_v8.py and emitted on /health; the line number this comment
used to cite drifted three versions ago and is not repeated here, pinned by
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
import tempfile
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------- manifest
# Written by the run that produced these files. If you edit a file by hand,
# this will fail -- which is the point.
EXPECTED_VERSION = "v8.40"
EXPECTED_LINES = 10924
MANIFEST = {
    # 2026-09-02: re-pinned after rebasing this PC onto origin/main (19 commits
    # of 2026-08-31 that changed the core, run_all_tests.sh and
    # run_local_sweep.py without moving these pins) and a full sweep on the
    # merged tree. The pins move in the SAME change as the files (M53).
    # v8.40 (2026-08-29): the semantic-judge layer, landed. The pin below is
    # the SAME digest the candidate sweep printed for its staged core
    # (525f235134f5 "as STAGED") -- what was swept is what shipped, provable
    # from the two files carrying one hash.
    "covenant_unified_v8.py":
        "8f219285f26807de9811c48dd34e8e826c337c7112932be85ce7fb16e2a65518",
    "test_a3s_send_bounds.py":
        "bd0ab67ae2f62a12b6a0253926511ca7cffa6155e3a74bb6633d3875006d1d7c",
    # run_all_tests.sh re-pinned 2026-08-29 three times: test_c2_watchdog_live
    # wired in (~05:45Z), then test_p19_overlay_guard (~08:00Z), then
    # test_p15_judge_identity (~10:30Z -- shipped 08-28, wired into no runner
    # until the package-coherence run found the gap)
    # (M53 -- the pins move in the SAME change as the file they pin).
    # ... and re-pinned AGAIN 2026-08-29 ~16:30Z. The b969f5e0d471 file all
    # three of those re-pins blessed was a MANGLED half-merge: the 06:44Z
    # session died mid-edit (its stale git locks were found at 11:30Z) and
    # left the OLD header on the NEW body -- `rm -f *.db.key` back at the
    # top (the exact line K1 forbids), the case-sensitive scrape back as
    # live code, and the eleven phantom suites resurrected. K1 6/20 and
    # K2 6/18 against it; nobody ran them before pinning. Rebuilt from the
    # PRE-LAND restore point plus the two real insertions (P15+C2, A24
    # section with P18+P19): 44 suites, K1 20/20, K2 25/25. A pin proves
    # WHICH bytes arrived, never that the bytes are right -- the suites
    # that judge the runner have to actually run.
    # ... and re-pinned ~21:00Z 08-29 with P20 (the watchdog self-evaluation
    # suite) wired in. K1 20/20 and K2 25/25 ran against these bytes BEFORE
    # the pin moved -- the order the b969 lesson above teaches.
    # ... and re-pinned with the v8.40 landing: the five semantic-layer
    # gates joined this runner, run_local_sweep.SUITES and covenant_one's
    # list in the SAME change. K1 20/20, K2 25/25, P19 23/23 against these
    # bytes before this pin moved.
    "run_all_tests.sh":
        "6511158dc70338f81b81bf7d7897077b295c9d5c4e5147410b349baa870e7534",   # 2026-09-03: F2 (test_f2_distill_loop) joined the runner; pin moved in the same change (M53)
    # run_local_sweep.py re-pinned 2026-08-29 ~08:00Z with the P19 overlay
    # guard. NOTE: the pin it replaces (07786e6ca851...) did not match the
    # project's own 00:55Z copy (2405768bee5e...) either -- the 08-29 00:40
    # session added the --candidate overlay and never moved this pin, so
    # this file would have reported MISMATCH on the very runner that ran
    # the candidate sweep. M53's failure mode, caught by hashing the
    # transcription against the pin before editing (M61).
    # ... and re-pinned again ~10:30Z 08-29: the 00:40Z rewrite had silently
    # DROPPED the 08-27 runner's "P18 added to SUITES" (M58's drift) -- the
    # SUITES list now carries test_a24 / test_p18 / test_p19 / test_p15, so
    # the first win32 sweep of v8.39 actually covers the fixes it ships.
    # ... re-pinned ~21:30Z 08-29: main() used to fall off its end, so a
    # sweep that PRINTED "RED: 1 suite(s)" still EXITED 0 -- found when the
    # full candidate sweep came back red on a13 and the background runner
    # said "completed (exit code 0)". It now returns 1 on red; P19 23/23
    # re-run against the new bytes before this pin moved.
    # ... and re-pinned with the v8.40 landing (five suites into SUITES);
    # then AGAIN within the hour: the BASE stage never copied the judge's
    # model files or SEM4's pristine source -- the candidate overlay had
    # since 00:40Z, and the first v8.40 deployed sweep went red on all four
    # semantic suites from that asymmetry. P19 23/23 after each move.
    "run_local_sweep.py":
        "d0197dc3c0d64d0088b0dff2b46635b4ba0cccf48ed08b094d2b5c199ea1764b",
    "test_p19_overlay_guard.py":
        "ed76c4497594d56b48ea7724a4aeed24bf1e9a38959fa705d9071812e07d4ed7",
    # pinned ~10:30Z 08-29 when both runners gained it -- a suite both
    # runners name is part of the delivery (M53).
    "test_p15_judge_identity.py":
        "3cf62e36f9020a5354515d8d9318c1ee5fcb5c8588793feb512a263886ad2ae1",   # 2026-09-03: R4d/R5c pin the deferring-policy wording (F2); moved with the file (M53)
}
# file -> module it imports that must sit in the same directory
COMPANIONS = {
    "covenant_unified_v8.py": "covenant_path_pattern.py",
    "test_a1_kill_matrix.py": "test_a9_relay_race.py",
    "test_c2_watchdog_live.py": "covenant_watchdog.py",
    # 2026-09-04: the watchdog imports covenant_quiet to keep Windows from
    # throwing a console window on every shell-out. A judge whose model is
    # absent fails closed; a watchdog whose helper is absent does not start
    # at all, so its presence is a delivery claim like any other.
    "covenant_watchdog.py": "covenant_quiet.py",
    "test_p19_overlay_guard.py": "run_local_sweep.py",
    "test_p15_judge_identity.py": "covenant_watchdog.py",
    # v8.40: the judge is code plus a MODEL, and a judge whose model is
    # absent fails closed at install() -- so the model's presence is a
    # delivery claim, checked here before anything restarts.
    "covenant_semantic_judge.py": "semantic_judge_model.json",
    "test_sem4_degraded_model.py": "covenant_semantic_judge.py",
}
NODES = [("A", 5000), ("B", 5020), ("C", 5060)]
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

    # ------------------------------------------------- 0. THE VERIFIER ITSELF
    # P14 found that the watchdog checked every node's source and never its own.
    # This script had the same shape: EXPECTED_VERSION and the four digests are
    # pinned by the run that BUILT the delivery, and NOTHING required them to be
    # updated when the next version shipped. A verifier one version behind does
    # not report itself -- it reports "MISMATCH covenant_unified_v8.py" and lets
    # the operator conclude the DELIVERY is broken. That is the wrong diagnosis
    # from a correct-looking tool, which is worse than no tool (A25).
    # So: read the version the core beside us actually declares -- from its own
    # source text, without importing it -- and if it disagrees with the pin,
    # say plainly which of the two is stale before touching anything else.
    say("")
    say("--- 0. THE VERIFIER ITSELF: are these pins for the file beside me? ---")
    core_path = os.path.join(HERE, "covenant_unified_v8.py")
    declared = None
    try:
        with open(core_path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                if raw.startswith("COVENANT_VERSION"):
                    declared = raw.split("=", 1)[1].strip().strip('"\'')
                    break
    except OSError as e:
        declared = None
        say(f"  UNKNOWN  cannot read {core_path}: {e}")
        unknowns.append("verifier could not read the core")
    if declared is None:
        say("  UNKNOWN  the core declares no COVENANT_VERSION at module level")
        unknowns.append("core declares no version")
    elif declared != EXPECTED_VERSION:
        say(f"  STALE VERIFIER  this script is pinned to {EXPECTED_VERSION}")
        say(f"                  the core beside it declares {declared}")
        say(f"  -- Do NOT read the mismatches below as a bad delivery. Either")
        say(f"     verify_deploy.py was not updated with the {declared} package,")
        say(f"     or the wrong core was copied in. Fix the pins, or re-copy.")
        failures.append(f"verifier pinned to {EXPECTED_VERSION}, core is {declared}")
    else:
        say(f"  ok       pins and core agree on {EXPECTED_VERSION}")

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
        #
        # NO PIPES on stdout/stderr (2026-08-29). capture_output=True was this
        # morning's 300 s TimeoutExpired on a restart that WORKED. Mechanism:
        # run() with pipes waits in communicate(), which reads until EOF, and
        # EOF needs every inherited write handle closed -- but the launcher's
        # covenant_prod.bat `start`s three nodes and a watchdog, each of which
        # inherits the pipe's write handle and holds it for as long as it
        # runs. cmd.exe exits, the nodes come up, and this verifier still
        # sits on a pipe the running chain keeps open. A scratch FILE has no
        # reader: run() then waits only on the cmd.exe process handle, which
        # the started nodes do not keep alive. The launcher's real report is
        # NODE_RESTART.txt; this scratch copy is disposable.
        scratch = os.path.join(tempfile.gettempdir(),
                               f"verify_restart_{os.getpid()}.txt")
        with open(scratch, "w", encoding="utf-8", errors="replace") as lout:
            p = subprocess.run([bat], cwd=HERE, timeout=300, shell=False,
                               stdin=subprocess.DEVNULL,
                               stdout=lout, stderr=subprocess.STDOUT)
        say(f"  exit code {p.returncode}")
    except subprocess.TimeoutExpired:
        # Do NOT return here. The launcher not returning and the restart not
        # happening are different claims -- this morning's INCOMPLETE was the
        # first mistaken for the second. Claim 4 below asks the nodes
        # themselves, which is the only answer that counts; the unknown still
        # keeps a full PASS off the table.
        say("  restart launcher did not return within 300 s -- not waiting")
        say("  any longer. Claim 4 below decides from the nodes themselves.")
        unknowns.append("restart launcher did not return in 300 s")
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
