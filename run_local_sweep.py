#!/usr/bin/env python3
"""
run_local_sweep.py (v2) -- run the verification sweep ON THIS MACHINE, against
the deployed covenant_unified_v8.py, in a scratch directory.

v1 hung. It used subprocess.run(capture_output=True, timeout=...), and on Windows
a suite that spawns node processes leaves grandchildren holding the stdout pipe:
communicate() kills the child on timeout and then blocks forever waiting for that
pipe to drain. Fifty-five minutes, not one result line. v2 fixes the two things
that caused it and the one that made it invisible:

  * every suite writes to its own LOG FILE -- no pipes, nothing to drain;
  * a suite over its budget is killed with `taskkill /F /T` (whole tree);
  * each result is appended to SWEEP_RESULTS.txt and flushed AS IT HAPPENS, so a
    watcher can see progress instead of waiting for the end.

It also kills leftovers from a previous sweep first, matched on the scratch path
in their command line, so it can never touch the production nodes in this folder.

Scratch dir: %TEMP%\\covenant_sweep. Nothing in the covenant folder is written
except SWEEP_RESULTS.txt.
"""
import os, re, shutil, subprocess, sys, tempfile, time

SRC   = os.path.dirname(os.path.abspath(__file__))
WORK  = os.path.join(tempfile.gettempdir(), "covenant_sweep")
OUT   = os.path.join(SRC, "SWEEP_RESULTS.txt")
BUDGET_TOTAL_S = 45 * 60          # hard ceiling for the whole sweep

SUITES = [
    ("test_a1a_a2.py", 180), ("test_a3_bounded_reads.py", 120),
    ("test_a5_size_coherence.py", 180), ("test_a11_gossip_scale.py", 120),
    ("test_a12_dead_peer_backoff.py", 180), ("test_a13_one_way_sync.py", 180),
    ("test_a14_boot_probe.py", 150), ("test_a15_exchange_deadline.py", 150),
    ("test_a17_oneway_peer_sync.py", 150), ("test_b1_judge_parser.py", 180),
    ("test_b2_quorum_diversity.py", 180),
    ("test_p14_watchdog_self_drift.py", 120),
    ("test_y1_stake_divergence.py", 120), ("test_w1_wsgi.py", 150),
    ("test_p11_version_identity.py", 180),
    ("test_p12_substrate_sensing.py", 180),
    ("test_a20_peer_version.py", 300),
    ("test_a22_topology_vigilance.py", 180),
    ("test_a23_ack_health.py", 180), ("test_a3s_send_bounds.py", 240),
    ("test_w2_sandbox_platform.py", 180),
    ("test_d3_daily_guards.py", 150), ("test_adversarial_suite.py", 240),
    ("test_b5_mine_latency.py", 240), ("test_security_audit.py", 300),
    ("test_e2e_gift.py", 180), ("test_a9_relay_race.py", 300),
    ("test_a1_kill_matrix.py", 360), ("test_a4_block_injection.py", 420),
    ("test_multinode_live.py", 300), ("sim_order_independence.py", 120),
    ("sim_yield_safety.py", 240), ("probe_final_pass.py", 120),
    # ADDED 2026-08-27. These four shipped in MANIFEST.sha256 and ran in
    # NEITHER runner, which is a worse state than a red check: a suite nobody
    # runs is a switched-off check that still reads as coverage in a file
    # count. Found by diffing the test files on disk against this list.
    # Measured standalone on win32 before being wired, because wiring a suite
    # that does not pass turns the sweep red for a reason that is not the
    # node's: r1_lora 58/58, backtest_guardrails 16/16, 3node_config 11/11,
    # covenant_app 54/54 (the last only after the A19 fix below -- until
    # 2026-08-27 it died on a KeyError against a console from the night
    # before, which is why it is listed last and staged specially).
    ("test_r1_lora_frame.py", 120), ("test_backtest_guardrails.py", 180),
    ("test_3node_config.py", 120),
]
# test_covenant_app.py (54 checks) is the fourth orphan and is DELIBERATELY
# NOT in that list. It binds the real production ports -- 5000/5020/5060 for
# its stubs and 5199 for the console -- because the console under test reads
# its own NODES table from source and there is no env var that moves it, by
# design: "a console that can restart nodes must not be one env var from the
# LAN". So the suite can only run with the chain STOPPED, while this sweep is
# meant to run with it up. Wired here it would report UNKNOWN on every normal
# sweep, and a check that is structurally always UNKNOWN teaches people to
# skip the line it prints. It is switched off honestly instead of noisily.
#
#   stop the nodes, then:  python test_covenant_app.py     (expects 54/54)
#
# Moving it into the sweep means giving covenant_app.py an overridable NODES
# table. That is a real change to a security-sensitive file and it is L's
# call, not a wiring decision. Recorded here so the next diff of disk against
# this list finds an answer rather than an omission.
TALLY = re.compile(r"(\d+\s*/\s*\d+\s*(?:checks|passed)|\d+ passed[^\n]*|ALL PASS[^\n]*|"
                   r"ALL INVARIANTS HELD|RESULTS:[^\n]*|A23: \d+/\d+ passed)", re.I)

def kill_leftovers():
    """DISABLED 2026-08-22, deliberately.

    The first version ran a PowerShell one-liner that matched processes by
    CommandLine. The powershell.exe process's OWN command line contains those
    patterns as literal text, so the filter matched the shell running it -- and
    the sweep died inside this function twice, in under a second, with no
    traceback. A cleanup routine that can kill its own caller is worse than no
    cleanup: leftovers cost a few failed suites, this cost the whole run.

    If leftovers ever need killing, write the filter to a .ps1 FILE and run the
    file (the command line is then just the path), or kill by PID from
    `netstat -ano` on the specific ports -- and never match on a pattern that
    appears in the matcher itself."""
    return

def stage():
    global WORK
    if os.path.isdir(WORK):
        shutil.rmtree(WORK, ignore_errors=True)
    if os.path.isdir(WORK) and os.listdir(WORK):
        n = 2
        while os.path.isdir(WORK + str(n)):
            n += 1
        WORK = WORK + str(n)
    os.makedirs(os.path.join(WORK, "logs"), exist_ok=True)
    # .bat and .html joined .py on 2026-08-27, for suites that read the
    # DEPLOYMENT rather than the code. test_3node_config.py asserts that
    # covenant_prod.bat, AB_RESTART_NODES.bat and covenant_watchdog.py agree
    # about the three nodes; covenant_app.py serves covenant_app_page.html
    # from disk and renders a "page is missing" stub without it. Staged from
    # a .py-only tree both suites fail on absent files and say so, which
    # reads exactly like a real defect. Copying is not executing: nothing in
    # the sweep runs a .bat except through the console's own allowlist.
    for n in os.listdir(SRC):
        p = os.path.join(SRC, n)
        if os.path.isfile(p) and (n.endswith(".py") or n.endswith(".bat")
                                  or n.endswith(".html") or n == "genesis.json"):
            shutil.copy2(p, WORK)
    for d in ("realdata", "quant", "ops"):
        s = os.path.join(SRC, d)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(WORK, d), dirs_exist_ok=True)

def clean_dbs():
    """Remove databases between suites, as run_all_tests.sh does.

    BUG FIXED 2026-08-22: this used to delete anything starting with
    "covenant_unified_" -- which is the SOURCE FILE, covenant_unified_v8.py.
    It deleted the module under test before the first suite ran, and 23 of 24
    suites reported ModuleNotFoundError in 0.2 s each. A cleanup rule written
    from a glob (`rm -f covenant_unified_*.db*`) lost the `.db` half in
    translation. Match on the database extension, never on the prefix."""
    for n in os.listdir(WORK):
        if ".db" in n:
            try: os.remove(os.path.join(WORK, n))
            except OSError: pass

def say(fh, line):
    print(line, flush=True)
    fh.write(line + "\n"); fh.flush(); os.fsync(fh.fileno())

def parse_argv():
    """Optional: run only some suites, and/or run them more than once.

      run_local_sweep.py                          -> the whole sweep, once
      run_local_sweep.py --repeat 2 test_b5_...   -> just those, twice each

    The repeat exists because of M18/M20: a suite that fails while 23 others
    and two nodes share the CPU has not failed yet. It fails when it fails
    alone, twice."""
    global OUT
    argv, repeat, only = sys.argv[1:], 1, []
    i = 0
    while i < len(argv):
        if argv[i] == "--repeat":
            repeat = int(argv[i + 1]); i += 2
        elif argv[i] == "--out":
            OUT = os.path.join(SRC, argv[i + 1]); i += 2
        else:
            only.append(argv[i]); i += 1
    return only, repeat


def main():
    only, repeat = parse_argv()
    fh = open(OUT, "w", encoding="utf8")
    say(fh, "covenant local sweep -- %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    say(fh, "python %s  pid %d" % (sys.version.split()[0], os.getpid()))
    try:
        say(fh, "leftover cleanup is disabled by design -- see kill_leftovers()")
        kill_leftovers()
        say(fh, "staging into %s ..." % WORK)
        stage()
        say(fh, "staged.")
    except Exception as e:
        import traceback
        say(fh, "SETUP FAILED: %r" % (e,))
        say(fh, traceback.format_exc())
        fh.close()
        return 1
    env = dict(os.environ)
    env.update(COVENANT_INSECURE_MOCK_JUDGE="1", COVENANT_JUDGE_PROVIDERS="mock",
               PYTHONUNBUFFERED="1")
    env.pop("COVENANT_WSGI", None)
    t_start = time.time()
    absent, skipped = [], []
    if True:
        say(fh, "core   %s bytes" % os.path.getsize(os.path.join(SRC, "covenant_unified_v8.py")))
        say(fh, "")
        plan = [(n, t) for (n, t) in SUITES if not only or n in only]
        if only:
            missing = [n for n in only if n not in [x[0] for x in SUITES]]
            plan += [(n, 300) for n in missing]          # not in the default list
            plan = [x for x in plan for _ in range(repeat)]
            say(fh, "running %d run(s) of %d suite(s), alone" % (repeat, len(set(n for n, _ in plan))))
            say(fh, "")
        for suite, tmo in plan:
            if not os.path.exists(os.path.join(WORK, suite)):
                absent.append(suite); continue
            if time.time() - t_start > BUDGET_TOTAL_S:
                skipped.append(suite); continue
            clean_dbs()
            log = os.path.join(WORK, "logs", suite + ".log")
            t0 = time.time()
            with open(log, "w", encoding="utf8") as lf:
                p = subprocess.Popen([sys.executable, suite], cwd=WORK, env=env,
                                     stdout=lf, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL)
                try:
                    rc = p.wait(timeout=tmo)
                except subprocess.TimeoutExpired:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try: p.wait(timeout=30)
                    except Exception: pass
                    rc = 124
            dt = time.time() - t0
            try:
                out = open(log, encoding="utf8", errors="replace").read()
            except OSError:
                out = ""
            m = TALLY.findall(out)
            if m:
                tally = m[-1].strip()
            elif out.strip():
                tally = "<no tally> " + out.strip().splitlines()[-1][:60]
            else:
                tally = "<no output>"
            say(fh, "%-32s rc=%-4s %6.1fs  %s" % (suite, rc, dt, tally[:80]))
        say(fh, "")
        say(fh, "total %.1f min" % ((time.time() - t_start) / 60.0))
        if skipped:
            say(fh, "not run, %d-minute budget spent: %s" % (BUDGET_TOTAL_S // 60, ", ".join(skipped)))
        if absent:
            say(fh, "referenced by run_all_tests.sh but not present on this machine: %s" % ", ".join(absent))
        say(fh, "per-suite logs: %s" % os.path.join(WORK, "logs"))
        fh.close()

if __name__ == "__main__":
    sys.exit(main())
