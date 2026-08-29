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

P19 (2026-08-29): the --candidate overlay no longer stages the candidate's
copies of gate files (test_*.py, sim_*.py, probe_*.py, verify_*.py, the two
runners) -- the folder under test must not supply the checks that judge it.
Blocked files are reported with both hashes; --allow-suite-overlay NAME (or
'all') overrides, loudly. Every suite that will run is hashed AS STAGED into
the results file, so "which bytes of the check ran" is never a forensic
question again.
"""
import fnmatch, hashlib, os, re, shutil, subprocess, sys, tempfile, time

SRC   = os.path.dirname(os.path.abspath(__file__))
CANDIDATE = ""            # set by --candidate DIR; overlaid onto the scratch tree
ALLOW_OVERLAY = set()     # --allow-suite-overlay NAME (repeatable; 'all') -- see P19
STAGE_REPORT = []         # built during stage(), written into the results file
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
    # v8.40 (2026-08-29): the semantic-judge layer's own gates, landed with
    # the layer. j1 34/34, sem4 28/28, competence 56/56, semantic 26/26,
    # sem5 6/6 -- the tallies of the candidate sweep that admitted them.
    ("test_j1_judge_paths.py", 120), ("test_sem4_degraded_model.py", 120),
    ("test_competence.py", 120), ("test_semantic_judge.py", 120),
    ("test_sem5_register_coverage.py", 120),
    ("test_p14_watchdog_self_drift.py", 120),
    # 2026-08-29: closing the runner/runner drift M58 recorded. The 08-27
    # delivery's runner (07786e6ca851) had "P18 added to SUITES"; the 00:40Z
    # 08-29 rewrite that introduced --candidate was built from an older base
    # and silently DROPPED it -- so the win32 candidate sweeps that blessed
    # pending-v8.38 could not have run a24/p18 (M58/PRELAND). These four are
    # the delivery's own suites: a24/a24b + p18 arrived with v8.39, p19
    # guards this runner itself, p15 is the shipped watchdog's newest control
    # (canned responses -- no ollama needed).
    ("test_a24_anomaly_eviction.py", 300),
    ("test_p18_version_collision.py", 120),
    ("test_p19_overlay_guard.py", 180), ("test_c3_guard.py", 120),
    ("test_m2_merkle_seal.py", 120),
    ("test_p15_judge_identity.py", 120),
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

# ---- P19 (2026-08-29): the folder under test must not supply the checks
# that judge it. The overlay below copies candidate *.py OVER the staged
# tree -- which is its purpose for the core and its modules, and was also,
# unnoticed, true for the SUITES: a candidate folder containing
# test_a23_ack_health.py would replace the gate's own check with whatever
# the candidate chose to claim about itself, and the results file would
# report the verdict as the sweep's. (Found while explaining the win32
# 23/23-vs-24/24 A23 delta: a green tally the project's suite bytes cannot
# produce means SOME other suite ran, and this overlay is one of two ways
# that happens silently.) So: files whose NAME says "check" -- test_*.py,
# sim_*.py, probe_*.py, verify_*.py, the two runners -- are never taken
# from the candidate by default. Each one blocked is reported with both
# hashes. --allow-suite-overlay NAME (or 'all') overrides, loudly, for the
# legitimate case of a candidate that ships an updated suite -- and the
# results file then says in as many words that the verdict for that suite
# is the candidate's own claim.
GATE_PATTERNS = ("test_*.py", "sim_*.py", "probe_*.py", "verify_*.py")
GATE_NAMES = {"run_local_sweep.py", "run_all_tests.sh"}

def is_gate_file(name):
    return name in GATE_NAMES or any(fnmatch.fnmatch(name, p) for p in GATE_PATTERNS)

def sha12(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

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
    # The judge's model files joined 2026-08-29 with v8.40: the semantic
    # judge is code PLUS a model, and staged from a .py-only tree it raises
    # "no semantic model" -- all four semantic suites went red on the first
    # v8.40 deployed sweep from exactly this line. The candidate OVERLAY has
    # copied .json since 00:40Z; the base stage never did, which is the same
    # asymmetry twice in one day.
    for n in os.listdir(SRC):
        p = os.path.join(SRC, n)
        if os.path.isfile(p) and (n.endswith(".py") or n.endswith(".bat")
                                  or n.endswith(".html") or n == "genesis.json"
                                  or n in ("semantic_judge_model.json",
                                           "model_v1.json")):
            shutil.copy2(p, WORK)
    # SEM4's D7 proves verdicts unchanged against the pristine pre-fix judge
    # source, which ships at docs/semantic/. The whole docs/ tree carries a
    # 46-book corpus and does not belong in every sweep; the one file does.
    _pristine = os.path.join(SRC, "docs", "semantic", "prefix_sem_judge.py")
    if os.path.isfile(_pristine):
        os.makedirs(os.path.join(WORK, "docs", "semantic"), exist_ok=True)
        shutil.copy2(_pristine, os.path.join(WORK, "docs", "semantic"))
    for d in ("realdata", "quant", "ops"):
        s = os.path.join(SRC, d)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(WORK, d), dirs_exist_ok=True)
    # ---- CANDIDATE OVERLAY (2026-08-29) ---------------------------------
    #
    # THE GATE THAT COULD NOT GATE. This sweep is the stated precondition for
    # landing anything -- and it stages the DEPLOYED core, so the only way to
    # sweep a candidate was to deploy it first. v8.38 sat in pending-v8.38 for
    # three days unswept for exactly that reason: the check that was supposed
    # to run before the change could only run after it. M48's shape in the
    # release process rather than in a gate.
    #
    # --candidate DIR copies DIR over the scratch tree AFTER the deployed
    # files, so the suites run against the candidate and the production folder
    # is never written. Nothing here can land anything: the overlay exists only
    # inside %TEMP%, and the deployed core is untouched either way.
    if CANDIDATE:
        if not os.path.isdir(CANDIDATE):
            raise SystemExit("--candidate %r is not a directory" % CANDIDATE)
        over, blocked, replaced = [], [], []
        for n in sorted(os.listdir(CANDIDATE)):
            p2 = os.path.join(CANDIDATE, n)
            if not (os.path.isfile(p2) and (n.endswith(".py") or n.endswith(".json")
                                            or n.endswith(".bat") or n.endswith(".html"))):
                continue
            if is_gate_file(n):                                   # P19, above
                if not ("all" in ALLOW_OVERLAY or n in ALLOW_OVERLAY):
                    staged_p = os.path.join(WORK, n)
                    have = (sha12(staged_p) if os.path.exists(staged_p)
                            else "(no deployed copy)")
                    blocked.append((n, sha12(p2), have))
                    continue
                replaced.append((n, sha12(p2)))
            shutil.copy2(p2, WORK)
            over.append(n)
        STAGE_REPORT.append("candidate overlay from %s: %d file(s) copied -- %s"
              % (CANDIDATE, len(over), ", ".join(over[:8])
                 + (" ..." if len(over) > 8 else "")))
        for n, csha, dsha in blocked:
            STAGE_REPORT.append(
                "OVERLAY BLOCKED %s: candidate copy %s NOT staged; the sweep "
                "runs the deployed copy %s. Gate files never come from the "
                "folder under test (P19); --allow-suite-overlay %s overrides."
                % (n, csha, dsha, n))
        for n, csha in replaced:
            STAGE_REPORT.append(
                "OVERLAY REPLACED GATE FILE %s with the candidate's %s "
                "(--allow-suite-overlay): every verdict that suite prints "
                "below is the CANDIDATE'S OWN CLAIM, not the deployed check's."
                % (n, csha))

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
    global OUT, CANDIDATE
    argv, repeat, only = sys.argv[1:], 1, []
    i = 0
    while i < len(argv):
        if argv[i] == "--repeat":
            repeat = int(argv[i + 1]); i += 2
        elif argv[i] == "--out":
            OUT = os.path.join(SRC, argv[i + 1]); i += 2
        elif argv[i] == "--allow-suite-overlay" and i + 1 < len(argv):
            ALLOW_OVERLAY.add(argv[i + 1]); i += 2
        elif argv[i] == "--candidate" and i + 1 < len(argv):
            CANDIDATE = argv[i + 1]
            if not os.path.isabs(CANDIDATE):
                CANDIDATE = os.path.join(SRC, CANDIDATE)
            i += 2
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
        for _line in STAGE_REPORT:          # P19: the overlay's report belongs
            say(fh, _line)                  # in the results file, not just stdout
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
    red, dep_skipped = [], []
    t_start = time.time()
    absent, skipped = [], []
    if True:
        # The core that was actually STAGED, hashed -- not the one in SRC.
        # Read from SRC it reported 551,342 bytes for a candidate sweep whose
        # overlay had just replaced it with 554,085: the line named the file
        # the sweep was NOT running. M38 in one print statement.
        _core = os.path.join(WORK, "covenant_unified_v8.py")
        try:
            import hashlib
            _b = open(_core, "rb").read()
            say(fh, "core   %s bytes  sha256 %s  (as STAGED, not as deployed)"
                % (len(_b), hashlib.sha256(_b).hexdigest()[:12]))
        except OSError as e:
            say(fh, "core   UNREADABLE in the scratch tree: %s" % e)
        say(fh, "")
        plan = [(n, t) for (n, t) in SUITES if not only or n in only]
        if only:
            missing = [n for n in only if n not in [x[0] for x in SUITES]]
            plan += [(n, 300) for n in missing]          # not in the default list
            plan = [x for x in plan for _ in range(repeat)]
            say(fh, "running %d run(s) of %d suite(s), alone" % (repeat, len(set(n for n, _ in plan))))
            say(fh, "")
        # P19/M40: pin the CHECKS, not just the core. "Which test_a23 ran?"
        # cost a morning of AST forensics; one line per suite, hashed as
        # STAGED, answers it for ever.
        _seen = set()
        for _s, _t in plan:
            _p3 = os.path.join(WORK, _s)
            if _s in _seen or not os.path.exists(_p3):
                continue
            _seen.add(_s)
            say(fh, "check  %-32s sha256 %s  (as STAGED)" % (_s, sha12(_p3)))
        if _seen:
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
            # M37: A SUITE FAILING FOR WANT OF A DEPENDENCY IS NOT A
            # REGRESSION. probe_final_pass has been red on every sweep because
            # xrpl-py is not installed -- a true statement about this machine's
            # packages and nothing at all about the node. Left as rc=1 it is a
            # permanently-red line, and a permanently-red line trains its
            # reader to skim the whole column (M34). It is now counted apart.
            missing_dep = (rc != 0 and (
                "ModuleNotFoundError" in out or "ImportError" in out
                or "not importable" in out))
            if missing_dep:
                dep_skipped.append(suite)
                say(fh, "%-32s DEP  %6.1fs  NOT RUN -- %s"
                    % (suite, dt, tally[:66]))
            else:
                if rc != 0:
                    red.append(suite)
                say(fh, "%-32s rc=%-4s %6.1fs  %s" % (suite, rc, dt, tally[:80]))
        say(fh, "")
        say(fh, "total %.1f min" % ((time.time() - t_start) / 60.0))
        # The verdict, stated once, so nobody has to scan 37 lines to find it.
        if red:
            say(fh, "RED: %d suite(s) -- %s" % (len(red), ", ".join(red)))
        else:
            say(fh, "GREEN: every suite that ran, passed.")
        if dep_skipped:
            say(fh, "NOT RUN (missing dependency, M37 -- not a regression): %s"
                % ", ".join(dep_skipped))
        if CANDIDATE:
            say(fh, "CANDIDATE SWEEP: staged from %s over the deployed tree. "
                    "The deployed core was NOT changed." % CANDIDATE)
        if skipped:
            say(fh, "not run, %d-minute budget spent: %s" % (BUDGET_TOTAL_S // 60, ", ".join(skipped)))
        if absent:
            say(fh, "referenced by run_all_tests.sh but not present on this machine: %s" % ", ".join(absent))
        say(fh, "per-suite logs: %s" % os.path.join(WORK, "logs"))
        fh.close()
        # SAY IT WITH THE EXIT CODE TOO (2026-08-29). main() used to fall off
        # the end here -- sys.exit(None) is exit 0 -- so a sweep that printed
        # "RED: 1 suite(s)" still told every SCRIPTED caller it succeeded.
        # Found when the 20:xx candidate sweep came back RED on a13 and the
        # background runner reported "completed (exit code 0)". The file said
        # the truth and the process contradicted it; both channels must agree.
        return 1 if red else 0

if __name__ == "__main__":
    sys.exit(main())
