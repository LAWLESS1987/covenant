#!/usr/bin/env python3
"""covenant_one.py -- ONE command. Every task. Both platforms. Nothing hidden.

WHY THIS EXISTS
---------------
There were twenty-two launchers in this folder (AA..AP, RUN, DAILY, JUDGE,
PROBE, start_*), two sweep runners that disagreed with each other, and a shell
script that named eleven suites which are NOT ON DISK. The runner's helper
swallowed stderr and printed "NO RESULT" for each of them while adding 0 to
TOTAL and 0 to FAILED -- so run_all_tests.sh could exit 0 having never
executed a fifth of what it lists. That is this project's own named failure
mode (M30, P14): a check that stopped checking still reads as coverage.

This file is the single entry point, and it obeys three rules:

  1. NOTHING IS SILENT. A suite that is absent, over budget, deliberately
     switched off, or on disk but in no runner, gets a LOUD line of its own.
     Absent and orphaned are first-class outcomes; neither is ever folded
     into a pass.
  2. NOTHING IS TOUCHED unless you ask. The default run is read-only plus the
     test sweep in a scratch copy. Restarting nodes, serving the console,
     writing the dashboard and running the daily job are behind explicit
     flags. A stop that always succeeds composed with a start that can refuse
     is not a restart (P17), so gates run BEFORE any action.
  3. IT SAYS WHAT IT IS. Like the node (P11) and the tree (P18), this runner
     prints its own version and the sha256 of its own source at the top of
     every run, so a transcript identifies the bytes that produced it.

USAGE
-----
    python covenant_one.py                 identity, integrity, gates, sweep,
                                           live state.  Touches nothing.
    python covenant_one.py --quick         everything except the long sweep
    python covenant_one.py --check         gates only (nothing else runs)
    python covenant_one.py --only test_a23_ack_health.py [--repeat 2]
    python covenant_one.py --restart       ...then verify_deploy.py (hash,
                                           restart nodes, confirm running src)
    python covenant_one.py --dashboard     ...then write+open dashboard.html
    python covenant_one.py --daily         ...then daily.py
    python covenant_one.py --console       ...then serve the console (blocks)
    python covenant_one.py --all           sweep + dashboard + daily
    python covenant_one.py --verbose       stream every suite log, not just
                                           the result line

EXIT CODES
----------
    0   everything measured, everything correct
    1   something FAILED or is BLOCKED   -- do not launch
    2   nothing failed, something could not be measured -- NOT a pass
"""
import argparse
import glob
import hashlib
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ONE_VERSION = "one-1.0"
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
WIN = sys.platform.startswith("win")
NODES = [("A", 5000), ("B", 5020), ("C", 5060)]
CONSOLE_PORT = int(os.environ.get("COVENANT_APP_PORT", "5199"))
CORE = "covenant_unified_v8.py"

# --------------------------------------------------------------------------
# THE SUITE TABLE. This is the union of run_all_tests.sh and run_local_sweep.py
# -- the two lists had drifted apart in BOTH directions. Budgets are the
# larger of the two where they disagreed.
# --------------------------------------------------------------------------
SUITES = [
    # (file, seconds, section)
    # NB verify_bundle.py and test_p18_version_collision.py are NOT here on
    # purpose. Both are claims about THE FOLDER -- the delivery hashes, and
    # which files under the tree declare which version -- so running them in
    # the sweep's scratch copy measures the scratch copy. The first draft of
    # this runner did exactly that and reported "55 changed or missing"
    # against a PC that has 6: a check moved to a copy answers about the copy.
    # They run in phase_integrity, in the live folder, before anything else.
    ("test_security_audit.py",           300,  "SECURITY"),
    ("test_k1_runner_key_preservation.py",120, "SECURITY"),
    ("test_k3_p9_owner_only_guard.py",   120,  "SECURITY"),
    # Arrived on main 2026-08-27 from fix/tally-counts-failures-as-passes,
    # where it had been sitting unmerged. It pins the sweep's own arithmetic:
    # a runner that counts a failure as a pass reports coverage it does not
    # have, which is this project's whole disease in one function. Measured
    # 25/25 before wiring, so it is not turning the sweep red on arrival.
    ("test_k2_tally_arithmetic.py",      120,  "SECURITY"),
    # D1 (2026-08-30). Same family as K2 above: a claim about the RUNNER
    # rather than about the node. K2 pins that a failure is not counted as a
    # pass; D1 pins that a MISSING DECLARED DEPENDENCY names itself instead of
    # surfacing as four unrelated failures in three sections -- which is what
    # it did on the run that produced this line, with a SECURITY suite reading
    # 14/16 and no regression anywhere near it. Pure: no network, no install.
    # 21/21 before wiring, so it is not turning the sweep red on arrival.
    ("test_d1_preflight_deps.py",        120,  "SECURITY"),
    # R2 (2026-08-30). Pins redundancy.py, which asks one question at every
    # scale: how many independent carriers, and what survives the first loss.
    # Its whole value is being believed, so R2 pins the ways it could lie --
    # chiefly the SUBSTRING bug it shipped with, which flagged twelve files
    # under ai_memory_system/ (the public software) for containing the string
    # "ai_memory" (the private record). Same error as the ignore rule that
    # swallowed test_e1_secret_egress.py and held CI red for a day: a pattern
    # that cannot tell a thing from a thing ABOUT it. 17/17 before wiring.
    ("test_r2_redundancy.py",            120,  "SECURITY"),
    # S1 (2026-08-30). scale.py makes a level's verdict usable as a witness one
    # level up, so governance composes to any depth AND any shape with no new
    # machinery -- the thing "the same function at every scale" has to mean if
    # it means anything. S1 pins the invariant that makes it safe: divergence
    # never disappears as you climb. A diverged level goes SILENT upward
    # instead of passing its majority root along, because the obvious
    # implementation launders disagreement into consensus one level at a time.
    # It also pins the two wrong versions that shipped before it, both caught
    # by these tests. 23/23 before wiring.
    ("test_s1_scale.py",                 120,  "SECURITY"),
    # N1 (2026-08-30). From the 2025 Misha Mahowald Prize shortlist, read for
    # what it implies rather than what it builds: Pedersen's Neuromorphic
    # Intermediate Representation stops comparing IMPLEMENTATIONS and compares
    # a canonical description of the COMPUTATION. federation.py had the same
    # bug NIR exists to fix -- it decided agreement by hashing the TEXT of the
    # rules, so a faithful reimplementation read DIVERGED while an instance
    # that copied the text and changed the code read SAME CORE. N1 pins a
    # behaviour root that is blind to prose and mutation-tested against two
    # real semantic breaks. 14/14 before wiring.
    ("test_n1_conformance.py",           120,  "SECURITY"),
    ("test_adversarial_suite.py",        300,  "ADVERSARIAL"),
    ("test_e2e_gift.py",                 180,  "ADVERSARIAL"),
    ("test_a1a_a2.py",                   240,  "ROUTES + BOUNDS"),
    ("test_a3_bounded_reads.py",         120,  "ROUTES + BOUNDS"),
    ("test_a5_size_coherence.py",        180,  "ROUTES + BOUNDS"),
    ("test_a3s_send_bounds.py",          240,  "ROUTES + BOUNDS"),
    ("test_a4_block_injection.py",       600,  "P2P"),
    ("test_a9_relay_race.py",            420,  "P2P"),
    ("test_a1_kill_matrix.py",           560,  "P2P"),
    ("test_a11_gossip_scale.py",         120,  "P2P"),
    ("test_a12_dead_peer_backoff.py",    240,  "P2P"),
    ("test_a13_one_way_sync.py",         180,  "P2P"),
    ("test_a14_boot_probe.py",           180,  "P2P"),
    ("test_a15_exchange_deadline.py",    180,  "P2P"),
    ("test_a17_oneway_peer_sync.py",     180,  "P2P"),
    ("test_a20_peer_version.py",         300,  "P2P"),
    ("test_a22_topology_vigilance.py",   180,  "P2P"),
    ("test_a23_ack_health.py",           180,  "P2P"),
    ("test_multinode_live.py",           600,  "P2P"),
    ("test_p11_version_identity.py",     180,  "IDENTITY"),
    ("test_p12_substrate_sensing.py",    180,  "IDENTITY"),
    ("test_p14_watchdog_self_drift.py",  120,  "IDENTITY"),
    # P15 (2026-08-28): the watchdog's ollama identity probe -- canned
    # responses, no socket, no keys. 29/29 here 2026-08-29; shipped 08-28 and
    # wired into NO runner until now, which is exactly the orphan class this
    # coverage phase exists to catch.
    ("test_p15_judge_identity.py",       120,  "IDENTITY"),
    # P20 (2026-08-29): the watchdog's self-evaluation ledger -- every layer
    # it senses, one PASS/WARN/FAIL block, report-only by AST. 23/23.
    ("test_p20_watchdog_self_eval.py",   120,  "IDENTITY"),
    # C3 (2026-08-29): the guard that heals the watchdog -- pure
    # decide(), report-only by AST, no process started. 21/21.
    ("test_c3_guard.py",                 120,  "IDENTITY"),
    # M2 (2026-08-29): merkle proofs over the seal -- prove one file,
    # disclose nothing else. 21/21, pure hashing.
    ("test_m2_merkle_seal.py",           120,  "SECURITY"),
    # T1 (2026-08-29): three witnesses, one root each, and the refusals
    # that keep the comparison honest. Pure. 20/20.
    ("test_t1_triangulate.py",           120,  "SECURITY"),
    # E1 (2026-08-29): no secret survives an error message. The
    # regression for the Google key-in-URL disclosure. 15/15.
    ("test_e1_secret_egress.py",         120,  "SECURITY"),
    # A24, moved here from DELIBERATELY_OFF 2026-08-29 exactly as that
    # entry's own REMEDY clause instructed ("propagate the v8.38+ core,
    # then move this line into SUITES") -- the v8.40 core at root carries
    # the fair-share buffer. 70/70, measured repeatedly today.
    ("test_a24_anomaly_eviction.py",     300,  "IDENTITY"),
    # P19 (2026-08-29): the sweep's own overlay guard -- a candidate folder
    # must not supply the checks that judge it. Subprocess-drives the real
    # run_local_sweep.py in a scratch tree; no node, no socket. 23/23.
    ("test_p19_overlay_guard.py",        180,  "GATE INTEGRITY"),
    # F1 (2026-08-30). Pins the line between availability and permissiveness.
    # Deployed wiring is COVENANT_JUDGE_PROVIDERS="local,semantic" with a veto
    # threshold of 1, and an UNREACHABLE judge fails closed -- so its
    # violates=True was counted as dissent, one stopped Ollama refused every
    # transaction, and _accept_block_common refused peer blocks too, which the
    # code there already calls "a fork in the making". Silence read as dissent,
    # in the one place that decides whether the chain moves.
    # The fix is OFF BY DEFAULT: the first attempt made it unconditional and
    # broke five checks in B1/B2/J1 that turned out to be deliberate. F1 pins
    # BOTH modes -- the untouched default, and that relaxed mode still blocks a
    # genuine dissent and still admits nothing when nothing answered.
    ("test_f1_fallback_silence.py",      120,  "JUDGE"),
    ("test_b1_judge_parser.py",          180,  "JUDGE"),
    ("test_b2_quorum_diversity.py",      180,  "JUDGE"),
    # The semantic-judge layer's own gates, joined 2026-08-29 when v8.40
    # landed the layer at root. Their DELIBERATELY_OFF entries ("joins the
    # sweep when the candidate lands") are honored and removed in the same
    # change. Candidate-sweep tallies on admission: 34/34, 28/28, 56/56,
    # 26/26, 6/6.
    ("test_j1_judge_paths.py",           120,  "JUDGE"),
    ("test_sem4_degraded_model.py",      120,  "JUDGE"),
    ("test_competence.py",               120,  "JUDGE"),
    ("test_semantic_judge.py",           120,  "JUDGE"),
    ("test_sem5_register_coverage.py",   120,  "JUDGE"),
    ("test_b5_mine_latency.py",          300,  "JUDGE"),
    ("test_r1_lora_frame.py",            120,  "JUDGE"),
    ("test_w1_wsgi.py",                  300,  "HTTP"),
    ("test_w2_sandbox_platform.py",      180,  "HTTP"),
    ("test_d3_daily_guards.py",          180,  "DAILY + GUARDS"),
    ("test_backtest_guardrails.py",      180,  "DAILY + GUARDS"),
    ("test_3node_config.py",             120,  "DEPLOYMENT"),
    ("test_y1_stake_divergence.py",      120,  "LEDGER"),
    ("sim_order_independence.py",        600,  "LEDGER"),
    ("sim_yield_safety.py",              240,  "LEDGER"),
    ("probe_final_pass.py",              120,  "XRP OFFLINE"),
    ("test_xrp_signer.py",               120,  "XRP OFFLINE"),
    ("test_xrp_mainnet.py",              180,  "XRP OFFLINE"),
]

# Switched off HONESTLY, with the reason, instead of quietly. Printed every
# run so a reader is never told coverage they do not have.
DELIBERATELY_OFF = {
    "test_covenant_app.py":
        "binds the REAL production ports (5000/5020/5060/5199) by design -- "
        "run it with the chain STOPPED: python test_covenant_app.py (expects 54/54)",
    "test_xrp_live.py":
        "needs a FUNDED XRP testnet account. Mainnet stays BLOCKED until this "
        "has run once.",
    "test_c2_watchdog_live.py":
        "boots the watchdog's REAL topology (5000/5020/5060) on nodes it "
        "starts itself -- same class as test_covenant_app: run it with the "
        "chain STOPPED. 27/27 x2 on Linux 2026-08-29 (run_all_tests.sh runs "
        "it in the sandbox sweep, where there is no chain to collide with).",
    "probe_block_hash.py":  "one-off investigation probe, not a pass/fail suite",
    "probe_mainnet_review.py": "one-off investigation probe, not a pass/fail suite",
    "probe_power.py":       "one-off investigation probe, not a pass/fail suite",
    "probe_scaling.py":     "one-off investigation probe, not a pass/fail suite",
    "probe_win_connect.py":
        "a MEASUREMENT, not a pass/fail suite -- it reports what a refused and "
        "a dead TCP connect cost on THIS machine (Linux ~0.0 ms, win32 ~2045 ms). "
        "Run it by hand, or ONE_PROBE.bat, when A12/A23 backoff numbers are in "
        "question. Nothing about it can fail.",
    "verify_csv.py":        "data utility, run against realdata by hand",
    "verify_deploy.py":     "an ACTION (restarts nodes) -- runs under --restart",
    "trace_runner.py":      "helper, not a suite",
    # NOT a wiring oversight. run_all_tests.sh names this suite; it exists
    # NOWHERE on the production PC, and the fix it tests exists nowhere either:
    # grep for _fair_share / _compact_locked / last_eviction_age_seconds in the
    # deployed covenant_unified_v8.py (v8.37) returns ZERO. A24 landed in the
    # project as v8.38 and A24b as v8.39; neither was ever propagated. Wiring
    # it here would make the sweep permanently red for a reason that is not a
    # defect in the sweep, and a permanent red is not one cost but two (M34).
    # It is on the record instead, with its remedy.
}

TALLY = re.compile(
    r"(\d+\s*/\s*\d+\s*(?:checks|passed)|\d+ passed[^\n]*|ALL PASS[^\n]*|"
    r"ALL INVARIANTS HELD|RESULTS:[^\n]*|FINDINGS:\s*\d+[^\n]*|"
    r"[A-Z]\d+: \d+/\d+ passed)", re.I)

# INFORMATIONAL by design: these print curves/notes, not a pass/fail tally.
# run_all_tests.sh treated sim_yield_safety.py this way in prose ("ran clean --
# see output for curves") and then let the generic parser call it NO RESULT.
# Naming them here keeps the distinction: an informational suite that exits 0
# is `info`, which is neither a pass to be counted nor a failure to be chased.
INFORMATIONAL = {
    "sim_yield_safety.py":
        "reports yield curves; read it before changing YIELD_RATE. A clean run "
        "is NOT approval of any particular rate.",
}

BUDGET_TOTAL_S = int(os.environ.get("COVENANT_ONE_BUDGET_S", 75 * 60))

# --------------------------------------------------------------------------
# output: everything to the screen AND to one transcript, always both
# --------------------------------------------------------------------------
class Tee:
    def __init__(self, path):
        self.fh = open(path, "w", encoding="utf8", errors="replace")
        self.path = path

    def __call__(self, line=""):
        print(line, flush=True)
        self.fh.write(line + "\n")
        self.fh.flush()
        try:
            os.fsync(self.fh.fileno())
        except OSError:
            pass

    def close(self):
        try:
            self.fh.close()
        except Exception:
            pass


def rule(say, title):
    say("")
    say("=" * 74)
    say("  " + title)
    say("=" * 74)


def sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def http_json(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            import json
            return json.loads(r.read(1 << 20).decode("utf8", "replace"))
    except Exception:
        return None


def port_open(host, port, timeout=0.6):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def kill_tree(proc):
    """Kill the whole tree. A suite that spawns node processes leaves
    grandchildren holding the handle; killing the child alone hangs."""
    if WIN:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    try:
        proc.wait(timeout=30)
    except Exception:
        pass


def run_open(say, cmd, cwd=None, env=None, timeout=None, label=None):
    """Run a command with its output STREAMED to the screen and transcript.
    Used for the short read-only phases, where seeing it happen is the point."""
    label = label or " ".join(cmd)
    say("")
    say("$ " + " ".join(str(c) for c in cmd))
    t0 = time.time()
    try:
        p = subprocess.Popen(cmd, cwd=cwd or HERE, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, text=True,
                             encoding="utf8", errors="replace", bufsize=1,
                             start_new_session=not WIN)
    except FileNotFoundError:
        say("   ABSENT -- %s is not on this machine" % cmd[0])
        return None
    deadline = time.time() + timeout if timeout else None
    try:
        for line in p.stdout:
            say("   " + line.rstrip())
            if deadline and time.time() > deadline:
                say("   OVER BUDGET (%ss) -- killing the tree" % timeout)
                kill_tree(p)
                return 124
    finally:
        try:
            p.stdout.close()
        except Exception:
            pass
    rc = p.wait()
    say("   -> exit %s in %.1fs" % (rc, time.time() - t0))
    return rc


# --------------------------------------------------------------------------
# scratch staging: the sweep NEVER runs in the live folder. It copies the
# tree to scratch, so a suite that deletes a database, binds a port or kills a
# process tree cannot reach the production nodes or the node identity keys.
# --------------------------------------------------------------------------
def stage(say):
    # ONE SCRATCH DIRECTORY PER RUN, keyed by pid.
    #
    # What this replaces, and the two false reports it produced on 2026-08-30.
    # The previous version took the fixed path .../covenant_one, DELETED it,
    # and only then looped looking for a free name:
    #
    #     work = .../"covenant_one"
    #     if os.path.isdir(work): shutil.rmtree(work)      # <- destroys it
    #     while os.path.isdir(work) and os.listdir(work):  # <- now always False
    #         work = .../"covenant_one%d" % n
    #
    # The collision check was written and then made unreachable by the rmtree
    # two lines above it. So a second run on the same machine did not pick a
    # new directory; it deleted the first run's staged copy mid-flight. The
    # first run then failed suite after suite with "can't open file", and
    # reported 45 and then 39 suites unclean -- dozens of alarming failures,
    # none of them real, in a tool whose entire job is to be believed.
    #
    # A pid is unique among live processes by definition, so two runs cannot
    # collide at all rather than being trusted to notice each other.
    work = os.path.join(tempfile.gettempdir(), "covenant_one_%d" % os.getpid())
    if os.path.isdir(work):
        shutil.rmtree(work, ignore_errors=True)

    # Sweep scratch left by runs that are long over. By AGE, never by name:
    # deleting a sibling because it looks like ours is exactly the mistake
    # above. Anything younger than a day might still be running, and disk is
    # cheaper than another day of false failures.
    try:
        cutoff = time.time() - 24 * 3600
        for name in os.listdir(tempfile.gettempdir()):
            if not name.startswith("covenant_one"):
                continue
            old = os.path.join(tempfile.gettempdir(), name)
            if old == work or not os.path.isdir(old):
                continue
            try:
                if os.path.getmtime(old) < cutoff:
                    shutil.rmtree(old, ignore_errors=True)
            except OSError:
                pass
    except OSError:
        pass

    os.makedirs(os.path.join(work, "logs"), exist_ok=True)
    for name in os.listdir(HERE):
        p = os.path.join(HERE, name)
        if os.path.isfile(p) and (name.endswith(".py") or name.endswith(".bat")
                                  or name.endswith(".html")
                                  or name.endswith(".json")
                                  or name.endswith(".sh")
                                  or name == "MANIFEST.sha256"):
            try:
                shutil.copy2(p, work)
            except OSError:
                pass
    for d in ("realdata", "quant", "ops", "semantic", "pending-v8.38", "docs"):
        s = os.path.join(HERE, d)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(work, d), dirs_exist_ok=True)
    say("   staged into %s" % work)
    return work


def clean_dbs(work):
    """Match on the DATABASE EXTENSION, never on the prefix: a rule written
    from `rm -f covenant_unified_*.db*` once deleted covenant_unified_v8.py
    itself and 23 of 24 suites reported ModuleNotFoundError in 0.2s each."""
    for n in os.listdir(work):
        if ".db" in n or n.endswith(".db.key"):
            try:
                os.remove(os.path.join(work, n))
            except OSError:
                pass


# --------------------------------------------------------------------------
# phases
# --------------------------------------------------------------------------
def phase_identity(say):
    rule(say, "0. IDENTITY -- what is running, and from which bytes")
    me = os.path.abspath(__file__)
    say("  runner        %s  %s" % (ONE_VERSION, (sha256_file(me) or "?")[:12]))
    say("  when          %s" % time.strftime("%Y-%m-%d %H:%M:%S %z"))
    say("  platform      %s %s (%s)" % (platform.system(), platform.release(),
                                        platform.machine()))
    say("  python        %s" % sys.version.split()[0])
    say("  folder        %s" % HERE)
    core = os.path.join(HERE, CORE)
    if os.path.isfile(core):
        say("  core          %s  %d bytes  sha256 %s"
            % (CORE, os.path.getsize(core), (sha256_file(core) or "?")[:16]))
        ver = None
        try:
            with open(core, "r", encoding="utf8", errors="replace") as f:
                for line in f:
                    m = re.match(r'\s*COVENANT_VERSION\s*=\s*["\']([^"\']+)', line)
                    if m:
                        ver = m.group(1)
                        break
        except OSError:
            pass
        say("  version       %s" % (ver or "NOT DECLARED IN SOURCE"))
    else:
        say("  core          ABSENT -- %s is not in this folder" % CORE)
    try:
        out = subprocess.run(["git", "log", "--oneline", "-1"], cwd=HERE,
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            say("  git HEAD      %s" % out.stdout.strip())
        # --no-optional-locks, and it is load-bearing. Plain `git status`
        # REFRESHES THE INDEX, which takes .git/index.lock -- so a run of this
        # runner that is killed mid-status leaves a stale lock behind and every
        # later git command in the repo fails with "Another git process seems to
        # be running". That happened here on 2026-08-27: an aborted run left a
        # zero-byte lock that blocked `git rm` two hours later. The Linux kernel
        # uses this flag in scripts/setlocalversion for exactly this reason --
        # "This script must avoid any write attempt to the source tree." A
        # read-only check has no business taking a write lock.
        dirty = subprocess.run(["git", "--no-optional-locks", "status",
                                "--porcelain"], cwd=HERE,
                               capture_output=True, text=True, timeout=15)
        if dirty.returncode == 0:
            k = len([l for l in dirty.stdout.splitlines() if l.strip()])
            say("  git worktree  %s" % ("clean" if k == 0 else "%d file(s) modified" % k))
    except Exception:
        say("  git           not available here")


def phase_coverage(say):
    """The check that run_all_tests.sh could not do for itself: does the list
    match the disk? Both directions. Loudly."""
    rule(say, "1. COVERAGE -- does the runner's list match what is on disk?")
    # IN_PLACE counts as listed: those suites are RUN, just not from the
    # scratch copy. Leaving them out made the runner call its own integrity
    # phase an orphan -- a coverage report that miscounts is the thing this
    # phase exists to prevent.
    listed = [s for s, _, _ in SUITES] + [n for n, _, _ in IN_PLACE]
    absent = [s for s in listed if not os.path.isfile(os.path.join(HERE, s))]
    on_disk = set()
    for pat in ("test_*.py", "sim_*.py", "probe_*.py", "verify_*.py"):
        for p in glob.glob(os.path.join(HERE, pat)):
            n = os.path.basename(p)
            if ".PRE-" not in n:
                on_disk.add(n)
    orphans = sorted(on_disk - set(listed) - set(DELIBERATELY_OFF))

    say("  listed in this runner   %d suites (%d in the sweep, %d in place)"
        % (len(listed), len(SUITES), len(IN_PLACE)))
    say("  present on disk         %d" % (len(listed) - len(absent)))
    say("  switched off, on record %d" % len(DELIBERATELY_OFF))
    say("")
    if absent:
        say("  ABSENT -- named by the runner, NOT ON DISK. These contribute")
        say("  nothing and must never be read as coverage:")
        for s in absent:
            say("      ABSENT   %s" % s)
    else:
        say("  ABSENT   none. Every suite this runner names exists.")
    say("")
    if orphans:
        say("  ORPHANED -- on disk, in no runner and on no off-record. A suite")
        say("  nobody runs is a switched-off check that still reads as coverage:")
        for s in orphans:
            say("      ORPHAN   %s" % s)
    else:
        say("  ORPHAN   none. Every suite on disk is either run or on record.")
    say("")
    say("  SWITCHED OFF ON PURPOSE (reason on record, never silent):")
    for s, why in sorted(DELIBERATELY_OFF.items()):
        mark = "" if os.path.isfile(os.path.join(HERE, s)) else "   [not on disk]"
        say("      OFF      %-34s %s%s" % (s, why, mark))

    # A suite list that matches the disk is only half of "can this run". The
    # other half is whether what those suites IMPORT is installed, and nothing
    # here asked until 2026-08-30, when xrpl-py -- DECLARED in requirements.txt,
    # absent from the machine -- produced four failures across three sections,
    # one of them a SECURITY suite reading 14/16. Four symptoms named, the one
    # cause named nowhere. It is the same disease as the orphan check above:
    # the runner already knew, and never said.
    # ON DISK HERE is not IN THE DELIVERY, and the difference is the whole
    # reason CI was red from 2026-08-29 to 2026-08-30. .gitignore's `*_secret*`
    # swallowed test_e1_secret_egress.py, `git add` declined it without a word,
    # and this phase -- the phase that exists to catch a runner naming a suite
    # that is not there -- reported it present, because os.path.isfile asks
    # "is this on THIS disk" and never "is this in what I am about to ship".
    #
    # So the check written to stop exactly this could not fire on the machine
    # where the mistake was made. It could only fire on a clean checkout, in a
    # CI log the operator gets a 403 on. That is the same blind spot one level
    # up, and this closes it.
    say("")
    say("  SHIPPED -- is every listed suite actually IN the delivery, not just")
    say("  on this disk?")
    unshipped, ignored_by = [], {}
    if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                      cwd=HERE, capture_output=True,
                      text=True).returncode != 0:
        # A tarball delivery, a transported copy, a PRE-LAND snapshot. Without
        # this gate every listed suite reports UNSHIPPED and the run is
        # permanently INCOMPLETE for a reason that is true of the folder rather
        # than of the code -- M34, a check that is always red.
        say("      NOT MEASURED -- not a git work tree. This is not a pass;")
        say("      it means the question could not be asked here.")
    else:
        # ls-files and check-ignore only. NEVER `git status`: this file already
        # records (see phase_identity) that a plain status refreshes the index,
        # takes .git/index.lock, and once blocked a git rm for two hours.
        tracked = set()
        out = subprocess.run(["git", "ls-files"], cwd=HERE,
                             capture_output=True, text=True)
        if out.returncode == 0:
            tracked = {os.path.basename(l.strip()) for l in
                       out.stdout.splitlines() if l.strip()}
        unshipped = sorted(s for s in listed
                           if s not in tracked
                           and os.path.isfile(os.path.join(HERE, s)))
        for s in unshipped:
            ci = subprocess.run(["git", "check-ignore", "-v", s], cwd=HERE,
                                capture_output=True, text=True)
            if ci.returncode == 0 and ci.stdout.strip():
                ignored_by[s] = ci.stdout.strip().split("\t")[0]
        if not unshipped:
            say("      SHIPPED  every listed suite is in the delivery.")
        for s in unshipped:
            if s in ignored_by:
                say("      IGNORED  %s" % s)
                say("               on disk here, and an ignore rule keeps it")
                say("               OUT of the delivery: %s" % ignored_by[s])
                say("               CI will call this ABSENT. A suite the")
                say("               runner names has no legitimate reason to")
                say("               be ignored. Fix the RULE, not the list.")
            else:
                say("      UNSHIPPED %s -- on disk, not yet committed." % s)
                say("               Fix: git add %s" % s)

    say("")
    say("  DECLARED DEPENDENCIES -- requirements.txt against what is installed:")
    missing_deps = 0
    try:
        import preflight_deps
        missing_deps = preflight_deps.report(say, HERE)
    except Exception as e:                                   # noqa: BLE001
        # A preflight must never be the thing that takes down the run it
        # precedes. Report the miss and carry on: unmeasured, loudly, is the
        # one outcome this project always allows -- unmeasured and quiet is not.
        say("      COULD NOT CHECK -- %s: %s" % (type(e).__name__, e))
        say("      Treat dependencies as UNVERIFIED for this run.")
        missing_deps = 0
    return absent, orphans, missing_deps, sorted(ignored_by)


IN_PLACE = [
    # (file, seconds, why it may not be run from a scratch copy)
    ("verify_bundle.py", 120,
     "hashes the DELIVERY against MANIFEST.sha256 -- a copy is not the delivery"),
    ("test_p18_version_collision.py", 180,
     "walks the tree for other copies of the core -- a copy has a different tree"),
]


def phase_integrity(say, transported=False):
    """Claims about THE FOLDER, measured in the folder. Read-only."""
    rule(say, "2. INTEGRITY -- claims about this folder, measured here")
    out = []
    if transported:
        say("")
        say("  --transported was passed: this tree is a COPY of the delivery,")
        say("  not the delivery. MANIFEST.sha256 is a claim about the machine")
        say("  the bundle was built on, so measuring it here answers about the")
        say("  copy -- reported N/A, never as a pass and never as a failure.")
        for name, _, why in IN_PLACE:
            if name == "verify_bundle.py":
                out.append((name, "N/A (transported copy)"))
        say("")
    for name, tmo, why in IN_PLACE:
        if any(n == name for n, _ in out):
            continue
        say("")
        say("  %s -- %s" % (name, why))
        if not os.path.isfile(os.path.join(HERE, name)):
            say("    ABSENT -- not on disk. NOT measured, and not a pass.")
            out.append((name, "ABSENT"))
            continue
        rc = run_open(say, [sys.executable, name], timeout=tmo)
        out.append((name, "ok" if rc == 0 else "FAIL rc=%s" % rc))
    return out


def phase_gates(say):
    rule(say, "3. GATES -- asked out loud, changes nothing")
    lc = os.path.join(HERE, "launch_check.py")
    if not os.path.isfile(lc):
        say("  ABSENT -- launch_check.py is not here. Gates NOT measured.")
        return None
    rc = run_open(say, [sys.executable, "launch_check.py"], timeout=300)
    subprocess.run([sys.executable, "launch_check.py", "--json"], cwd=HERE,
                   stdout=open(os.path.join(HERE, "LAUNCH_CHECK.json"), "w"),
                   stderr=subprocess.DEVNULL)
    if rc == 0:
        say("  GATES PASS -- every gate measured and correct.")
    elif rc == 1:
        say("  GATES BLOCKED -- read the BLOCKED lines above; each carries its fix.")
    elif rc == 2:
        say("  GATES INCOMPLETE -- nothing blocked, something unmeasured. NOT a pass.")
    return rc


def phase_sweep(say, only=None, repeat=1, verbose=False):
    rule(say, "4. SWEEP -- every suite, in a scratch copy, live")
    say("  The live folder is never the working directory: a suite that binds a")
    say("  port, deletes a db or kills a tree must not be able to reach the")
    say("  production nodes or the node identity keys.")
    work = stage(say)
    env = dict(os.environ)
    env.update(COVENANT_INSECURE_MOCK_JUDGE="1", COVENANT_JUDGE_PROVIDERS="mock",
               PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf8")
    env.pop("COVENANT_WSGI", None)

    plan = [(s, t, sec) for (s, t, sec) in SUITES if not only or s in only]
    if only:
        known = {s for s, _, _ in SUITES}
        plan += [(s, 300, "AD HOC") for s in only if s not in known]
    plan = [x for x in plan for _ in range(max(1, repeat))]

    results, section, t_start = [], None, time.time()
    say("")
    for suite, tmo, sec in plan:
        if sec != section:
            section = sec
            say("")
            say("  --- %s ---" % section)
        src = os.path.join(HERE, suite)
        if not os.path.isfile(src):
            say("    %-34s ABSENT (not on disk)" % suite)
            results.append((suite, "ABSENT", 0, None, None))
            continue
        if time.time() - t_start > BUDGET_TOTAL_S:
            say("    %-34s NOT RUN (total budget %ds spent)" % (suite, BUDGET_TOTAL_S))
            results.append((suite, "NOTRUN", 0, None, None))
            continue
        clean_dbs(work)
        log = os.path.join(work, "logs", suite + ".log")
        t0 = time.time()
        with open(log, "w", encoding="utf8", errors="replace") as lf:
            p = subprocess.Popen([sys.executable, suite], cwd=work, env=env,
                                 stdout=lf, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL,
                                 start_new_session=not WIN)
            try:
                rc = p.wait(timeout=tmo)
            except subprocess.TimeoutExpired:
                kill_tree(p)
                rc = 124
        dt = time.time() - t0
        try:
            with open(log, "r", encoding="utf8", errors="replace") as lf:
                body = lf.read()
        except OSError:
            body = ""
        hits = TALLY.findall(body)
        line = (hits[-1] if hits else "").strip()
        if isinstance(line, tuple):
            line = line[0]
        passed = failed = None
        m = re.search(r"(\d+)\s*/\s*(\d+)", line)
        if m:
            passed, total = int(m.group(1)), int(m.group(2))
            failed = total - passed
        else:
            mp = re.search(r"(\d+) passed", line, re.I)
            mf = re.search(r"(\d+) failed", line, re.I)
            if mp:
                passed = int(mp.group(1))
                failed = int(mf.group(1)) if mf else 0
        mfind = re.search(r"FINDINGS:\s*(\d+)", line, re.I)
        if mfind:
            failed = int(mfind.group(1))
            passed = 0 if failed else 1

        if rc == 124:
            state = "TIMEOUT"
        elif suite in INFORMATIONAL:
            state = "info" if rc == 0 else "ERROR rc=%s" % rc
            line = line or INFORMATIONAL[suite]
            passed = failed = None
        elif not line:
            state = "NO RESULT"
        elif failed:
            state = "FAIL"
        elif rc != 0 and passed is None:
            state = "ERROR rc=%s" % rc
        else:
            state = "ok"
        say("    %-34s %-9s %6.1fs  %s" % (suite, state, dt, line or "(no tally line)"))
        results.append((suite, state, dt, passed, failed))
        if verbose or state in ("FAIL", "TIMEOUT", "NO RESULT") or state.startswith("ERROR"):
            lines = [l for l in body.splitlines() if l.strip()]
            # The FAILING lines first, then the tail. The first draft printed
            # only the last 18 lines and a suite whose failures were early
            # showed 18 PASS lines under the word FAIL -- a report that hides
            # the thing it is reporting.
            bad_lines = [l for l in lines
                         if re.search(r"\bFAIL\b|\bERROR\b|Traceback|Exception", l)]
            if bad_lines and not verbose:
                say("        | -- the %d failing line(s):" % len(bad_lines))
                for l in bad_lines[:20]:
                    say("        | " + l[:200])
                if len(bad_lines) > 20:
                    say("        | ... %d more" % (len(bad_lines) - 20))
                say("        | -- tail:")
            for l in (lines if verbose else lines[-12:]):
                say("        | " + l[:200])
    say("")
    say("  suite logs: %s" % os.path.join(work, "logs"))
    return results


def phase_live(say, title="5. LIVE STATE -- what is actually up right now (read-only)"):
    rule(say, title)
    any_up = False
    for name, port in NODES:
        up = port_open("127.0.0.1", port)
        h = http_json("http://127.0.0.1:%d/health" % port) if up else None
        if h:
            any_up = True
            say("  node %s :%-5d UP    height=%s version=%s src=%s peers=%s"
                % (name, port, h.get("height", h.get("chain_height", "?")),
                   h.get("version", "?"), str(h.get("source_sha256", "?"))[:12],
                   h.get("peer_count", h.get("peers", "?"))))
            warn = h.get("warnings") or h.get("warning")
            if warn:
                say("             warnings: %s" % warn)
        elif up:
            say("  node %s :%-5d port open, /health did not answer JSON" % (name, port))
        else:
            say("  node %s :%-5d down" % (name, port))
    say("  console :%-5d %s" % (CONSOLE_PORT,
        "UP" if port_open("127.0.0.1", CONSOLE_PORT) else "not running"))
    say("  ollama  :11434 %s" % ("UP" if port_open("127.0.0.1", 11434) else "not running"))
    wd = os.path.join(HERE, "logs", "watchdog.log")
    if os.path.isfile(wd):
        age = time.time() - os.path.getmtime(wd)
        say("  watchdog      last wrote %.0f min ago (%s)" % (age / 60,
            "alive" if age < 900 else "STALE -- the control that catches drift is drifting"))
        try:
            with open(wd, "r", encoding="utf8", errors="replace") as f:
                tail = f.readlines()[-5:]
            for l in tail:
                say("             | " + l.rstrip()[:150])
        except OSError:
            pass
    else:
        say("  watchdog      no logs/watchdog.log here")
    if not any_up:
        say("")
        say("  No node answered. That is a fact, not a failure: this runner does")
        say("  not start them. Use --restart (gated) or AN_LAUNCH.bat on Windows.")
    return any_up


def phase_actions(say, args, gates=None):
    did = []
    if args.restart and gates == 1:
        rule(say, "6. RESTART -- REFUSED")
        say("  A gate is BLOCKED, so nothing is stopped and nothing is started.")
        say("  P17: a stop that always succeeds composed with a start that can")
        say("  refuse is not a restart, it is a stop -- so the refusal happens")
        say("  BEFORE the stop, not after it. Read the BLOCKED lines above;")
        say("  each carries its own fix. Re-run with the gate cleared.")
        return [("verify_deploy.py", "REFUSED (gate BLOCKED)")]
    if args.restart and gates is None:
        rule(say, "6. RESTART -- REFUSED")
        say("  The gates were NOT MEASURED, and an unmeasured gate is not a")
        say("  passed gate. Nothing was stopped and nothing was started.")
        return [("verify_deploy.py", "REFUSED (gates not measured)")]
    if args.restart:
        rule(say, "6. RESTART -- hash the delivery, restart, confirm running source")
        rc = run_open(say, [sys.executable, "verify_deploy.py"], timeout=900)
        did.append(("verify_deploy.py", rc))
    if args.dashboard:
        rule(say, "6. DASHBOARD")
        rc = run_open(say, [sys.executable, "dashboard_render.py"], timeout=300)
        did.append(("dashboard_render.py", rc))
    if args.daily:
        rule(say, "6. DAILY CHECK + CIRCUIT BREAKERS")
        rc = run_open(say, [sys.executable, "daily.py"], timeout=900)
        did.append(("daily.py", rc))
    if args.console:
        rule(say, "6. CONSOLE -- serving on 127.0.0.1:%d (blocks; ctrl-c to stop)" % CONSOLE_PORT)
        rc = run_open(say, [sys.executable, "covenant_app.py"])
        did.append(("covenant_app.py", rc))
    return did


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="skip the long sweep")
    ap.add_argument("--check", action="store_true", help="gates only")
    ap.add_argument("--only", nargs="+", default=None, help="run only these suites")
    ap.add_argument("--repeat", type=int, default=1, help="run each suite N times, alone")
    ap.add_argument("--verbose", action="store_true", help="stream every suite log")
    ap.add_argument("--restart", action="store_true", help="ACTION: verify + restart nodes")
    ap.add_argument("--dashboard", action="store_true", help="ACTION: write dashboard.html")
    ap.add_argument("--daily", action="store_true", help="ACTION: run daily.py")
    ap.add_argument("--console", action="store_true", help="ACTION: serve the console")
    ap.add_argument("--all", action="store_true", help="sweep + dashboard + daily")
    ap.add_argument("--ci", action="store_true",
                    help="continuous integration: implies --transported, and "
                         "the gates are REPORTED but do not decide the exit "
                         "code (a CI runner is not a launch host)")
    ap.add_argument("--transported", action="store_true",
                    help="this tree is a COPY of the delivery (e.g. the cloud "
                         "mirror): report the manifest check N/A instead of red")
    ap.add_argument("--out", default="ONE_RUN.txt", help="transcript file")
    args = ap.parse_args()
    if args.all:
        args.dashboard = args.daily = True
    if args.ci:
        # A CI runner has no ethics judge, no nodes, no identity keys and no
        # manifest of its own -- so G1/G5/G8/G9/G10 CANNOT pass there, ever.
        # Wiring the exit code to them would make every CI run red for reasons
        # that are true of the runner rather than of the code, and a check that
        # is always red is one people learn to skim past (M34). The gates are
        # still ASKED and still PRINTED in full: reported, not gating. What
        # decides the exit code is the suites, which is the thing CI can
        # actually observe.
        args.transported = True

    say = Tee(os.path.join(HERE, args.out))
    t0 = time.time()
    say("#" * 74)
    say("#  COVENANT -- ONE COMMAND.  Nothing hidden, nothing silent.")
    say("#  transcript: %s" % say.path)
    say("#" * 74)

    absent = orphans = []
    inplace = []
    gates = None
    results = []
    actions = []
    missing_deps = 0
    ignored = []
    try:
        phase_identity(say)
        absent, orphans, missing_deps, ignored = phase_coverage(say)
        inplace = phase_integrity(say, transported=args.transported)
        gates = phase_gates(say)
        if args.check:
            say("")
            say("--check was passed. Stopping here. Nothing else ran, nothing touched.")
        else:
            if not args.quick:
                results = phase_sweep(say, only=args.only, repeat=args.repeat,
                                      verbose=args.verbose)
            else:
                rule(say, "4. SWEEP -- SKIPPED (--quick). This is NOT a pass.")
            phase_live(say)
            actions = phase_actions(say, args, gates=gates)
            if actions and any(r not in ("REFUSED (gate BLOCKED)",
                                         "REFUSED (gates not measured)")
                               for _, r in actions):
                # Measure AFTER, not only before. "It restarted" is a claim
                # about a process, and the only way to check a claim about a
                # process is to ask the process (M30).
                phase_live(say, "7. LIVE STATE AFTER -- ask the processes, "
                                "do not assume the restart worked")
    except KeyboardInterrupt:
        say("")
        say("INTERRUPTED by ctrl-c. Partial run -- do not read it as a result.")
    finally:
        # ------------------------------------------------------------------
        rule(say, "VERDICT")
        checks = sum(p for _, _, _, p, _ in results if p)
        fails = sum(f for _, _, _, _, f in results if f)
        bad = [r for r in results if r[1] in ("FAIL", "TIMEOUT", "NO RESULT")
               or r[1].startswith("ERROR")]
        unmeasured = [r for r in results if r[1] in ("ABSENT", "NOTRUN")]
        say("  suites run          %d" % len([r for r in results
                                              if r[1] not in ("ABSENT", "NOTRUN")]))
        say("  checks passed       %d" % checks)
        say("  checks failed       %d" % fails)
        say("  suites not clean    %d%s" % (len(bad),
            ("  -> " + ", ".join(r[0] for r in bad)) if bad else ""))
        say("  suites unmeasured   %d%s" % (len(unmeasured),
            ("  -> " + ", ".join(r[0] for r in unmeasured)) if unmeasured else ""))
        say("  runner list absent  %d%s" % (len(absent),
            ("  -> " + ", ".join(absent)) if absent else ""))
        say("  orphaned on disk    %d%s" % (len(orphans),
            ("  -> " + ", ".join(orphans)) if orphans else ""))
        say("  listed but NOT SHIPPED %d%s"
            % (len(ignored),
               ("  -> " + ", ".join(ignored)
                + "   <- an ignore rule keeps these OUT of the delivery;"
                  " CI will call them ABSENT")
               if ignored else ""))
        say("  declared deps missing %d%s"
            % (missing_deps,
               "   <- suites needing them are UNMEASURED, not failing"
               if missing_deps else ""))
        bad_inplace = [n for n, st in inplace if st != "ok"]  # noqa: F841
        say("  folder integrity    %s" % (", ".join("%s=%s" % (n, st)
                                                    for n, st in inplace) or "NOT MEASURED"))
        if actions:
            say("  actions             %s" % ", ".join("%s=%s" % (n, r)
                                                       for n, r in actions))
        say("  gates               %s" % {0: "PASS", 1: "BLOCKED", 2: "INCOMPLETE",
                                          None: "NOT MEASURED"}.get(gates, gates))
        say("  elapsed             %.1f min" % ((time.time() - t0) / 60))
        say("")
        gate_blocks = (gates == 1) and not args.ci
        inplace_fail = [n for n, st in inplace if st.startswith("FAIL")] \
            if not args.ci else []
        if args.ci:
            say("  ci mode             gates are REPORTED above, not gating --")
            say("                      this runner has no judge, no nodes and no")
            say("                      keys, so those gates cannot pass here. The")
            say("                      suites decide the exit code.")
        if bad or fails or gate_blocks or inplace_fail:
            say("  RESULT: FAIL. Something is wrong and it is named above.")
            code = 1
        elif (unmeasured or absent or orphans or args.quick or missing_deps
              or ignored
              or (gates in (2, None) and not args.ci)
              or [n for n, st in inplace
                  if st == "ABSENT" or (st.startswith("N/A") and not args.ci)]):
            say("  RESULT: INCOMPLETE. Nothing failed; something was not measured.")
            say("          This is NOT a pass. Every unmeasured item is named above.")
            code = 2
        else:
            say("  RESULT: PASS. Everything this runner names was measured and correct.")
            code = 0
        say("")
        say("  transcript: %s" % say.path)
        say("")
        say("  NOT COVERED BY THIS RUN, and never read a green run as covering them:")
        say("    test_xrp_live.py   XRP autofill/submit against a FUNDED testnet")
        say("                       account. Mainnet stays BLOCKED until it runs once.")
        say("    test_covenant_app.py  needs the chain STOPPED (binds real ports).")
        say("")
        say.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
