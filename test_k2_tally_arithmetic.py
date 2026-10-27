#!/usr/bin/env python3
"""K2 (2026-08-27): the sweep's tally must not count a failure as a pass.

No node, no socket, no key. Every check feeds one result line to the parsing
block extracted from run_all_tests.sh itself and reads back what it scored.

THE DEFECT. The scrape was:

    p=$(echo "$line" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
    f=$(echo "$line" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+')

Two faults, compounding in the same direction -- upward.

  1. On "28/30 passed, 2 FAILED" the pattern `[0-9]+ passed` matches the
     substring "30 passed". 30 is the TOTAL. The two failures were added to
     the pass count.
  2. Both inner greps are case-SENSITIVE while the line-selecting grep is -i,
     so a suite printing "2 FAILED" in caps scored f=0.

Measured on the win32 sweep of 2026-08-27, whose 36 result lines are the
fixtures below: reported "1152 checks, 2 failed"; actually 1147 passed and 7
failed across 1154 checks. Five real failures were reported as five passes.

  A  THE MUTATION (§7): the original two lines, run verbatim, misread three of
     the five lines that carried a failure -- the two written plainly as
     "N passed, 1 failed" it read correctly -- and those three account for all
     five lost failures and all five phantom passes. The first draft of this
     check claimed all five and was wrong (§4).
  B  The shipped parser reads each of those five correctly.
  C  Whole-sweep arithmetic over all 36 real lines: 1147 / 7 / 1154.
  D  A suite that ran and printed nothing is UNSCORED, never a silent zero.
  E  THE SHIPPED SOURCE (§2): the fix is in the file, the old pattern is not
     executable anywhere in it, and UNSCORED is wired into the exit status.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "run_all_tests.sh")
PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def bash():
    for c in ("bash", r"C:\Program Files\Git\bin\bash.exe",
              r"C:\Program Files\Git\usr\bin\bash.exe"):
        p = shutil.which(c) if os.sep not in c else (c if os.path.exists(c) else None)
        if p:
            return p
    return None


BASH = bash()
src = open(RUNNER, encoding="utf-8", errors="replace").read()

# The real parsing block, lifted from the runner (§2).
m = re.search(r'^  n=""; f="".*?^  n=\$\{n:-0\}; f=\$\{f:-0\}', src, re.S | re.M)
SHIPPED = m.group(0) if m else None

OLD = (
    "p=$(echo \"$line\" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')\n"
    "f=$(echo \"$line\" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+')\n"
    "n=${p:-0}; f=${f:-0}\n"
)


def score(line, block):
    """Return (n, f) as the given shell block scores this result line."""
    script = f'line={sh_quote(line)}\n{block}\necho "$n $f"\n'
    r = subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=30)
    out = r.stdout.strip().split()
    return (int(out[0]), int(out[1])) if len(out) == 2 else (None, None)


def sh_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"


# The 36 result lines from the 2026-08-27 win32 sweep, verbatim.
SWEEP = [
    ("test_security_audit.py", "128 passed, 1 failed", 128, 1),
    ("test_adversarial_suite.py", "21 passed, 0 failed", 21, 0),
    ("test_e2e_gift.py", "11 passed, 0 failed", 11, 0),
    ("test_a1a_a2.py", "15/15 passed", 15, 0),
    ("test_a3_bounded_reads.py", "7 passed, 0 failed", 7, 0),
    ("test_a5_size_coherence.py", "20 passed, 0 failed", 20, 0),
    ("test_a4_block_injection.py", "60/60 passed", 60, 0),
    ("test_a9_relay_race.py", "18/18 passed", 18, 0),
    ("test_a1_kill_matrix.py", "28/30 passed, 2 FAILED", 28, 2),
    ("test_a11_gossip_scale.py", "23/23 passed", 23, 0),
    ("test_a12_dead_peer_backoff.py", "21/21 passed", 21, 0),
    ("test_a13_one_way_sync.py", "24/25 passed, 1 FAILED", 24, 1),
    ("test_a14_boot_probe.py", "15/15 passed", 15, 0),
    ("test_a15_exchange_deadline.py", "14/14 passed", 14, 0),
    ("test_a17_oneway_peer_sync.py", "6/6 passed", 6, 0),
    ("test_p11_version_identity.py", "29/29 passed", 29, 0),
    ("test_p12_substrate_sensing.py", "41/41 passed", 41, 0),
    ("test_p14_watchdog_self_drift.py", "33/33 passed", 33, 0),
    ("test_a20_peer_version.py", "27/27 passed", 27, 0),
    ("test_a22_topology_vigilance.py", "21/21 passed", 21, 0),
    ("test_a23_ack_health.py", "A23: 22/24 passed", 22, 2),
    ("test_a3s_send_bounds.py", "49/49 checks passed", 49, 0),
    ("test_b1_judge_parser.py", "162/162 passed in 28.1s", 162, 0),
    ("test_b2_quorum_diversity.py", "73/73 passed in 2.1s", 73, 0),
    ("test_b5_mine_latency.py", "31/31 passed in 20.9s", 31, 0),
    ("test_w1_wsgi.py", "24/24 passed", 24, 0),
    ("test_d3_daily_guards.py", "77/77 passed", 77, 0),
    ("test_multinode_live.py", "21 passed, 0 failed", 21, 0),
    ("test_r1_lora_frame.py", "R1 LoRa frame codec: 58 passed, 0 failed", 58, 0),
    ("test_backtest_guardrails.py", "16 passed, 0 failed", 16, 0),
    ("test_3node_config.py", "11/11 passed", 11, 0),
    ("test_k1_runner_key_preservation.py", "20/20 passed", 20, 0),
    ("test_xrp_signer.py", "21 passed, 1 failed", 21, 1),
]
WITH_FAILURES = [r for r in SWEEP if r[3]]


print("== A. THE MUTATION: the original scrape misread 3 of the 5 failing lines (§7) ==")
if BASH:
    wrong = 0
    for suite, line, want_n, want_f in WITH_FAILURES:
        got_n, got_f = score(line, OLD)
        if (got_n, got_f) != (want_n, want_f):
            wrong += 1
        if "FAILED" in line:
            check(f"A1 old scrape mis-scores {suite}",
                  (got_n, got_f) != (want_n, want_f),
                  f"scored {got_n}/{got_f}, truth {want_n}/{want_f}")
    # Precision matters here, and my first version of this check overstated it
    # (§4/§10). The old scrape was NOT wrong on all five failing lines: the two
    # written "N passed, 1 failed" -- lowercase, no A/B form -- it read
    # correctly. It was wrong on exactly the three that used an A/B form or
    # capitalised FAILED, and those three account for all five lost failures.
    check("A2 the old scrape was wrong on exactly 3 of the 5 failing lines",
          wrong == 3, f"{wrong} wrong, {len(WITH_FAILURES) - wrong} read correctly")
    lost = 0
    for _, line, want_n, want_f in WITH_FAILURES:
        got_n, got_f = score(line, OLD)
        lost += want_f - got_f
    check("A3 and those three account for all 5 missing failures",
          lost == 5, f"failures lost: {lost}")
    gained = 0
    for _, line, want_n, _ in WITH_FAILURES:
        got_n, _ = score(line, OLD)
        gained += got_n - want_n
    check("A4 which were counted as 5 extra passes -- 1152 vs 1147",
          gained == 5, f"passes over-counted: {gained}")
else:
    check("A SKIPPED-AS-FAILURE: no bash found, so this did NOT run (§5)", False)

print("\n== B. the shipped parser reads the failing lines correctly ==")
if BASH and SHIPPED:
    for suite, line, want_n, want_f in WITH_FAILURES:
        got = score(line, SHIPPED)
        check(f"B {suite}", got == (want_n, want_f),
              f"scored {got[0]}/{got[1]}, want {want_n}/{want_f}")
else:
    check("B SKIPPED-AS-FAILURE: no bash, or parser not found in source",
          False, f"bash={bool(BASH)} parser={bool(SHIPPED)}")

print("\n== C. whole-sweep arithmetic over all 36 real lines ==")
if BASH and SHIPPED:
    tp = tf = 0
    for _, line, _, _ in SWEEP:
        n, f = score(line, SHIPPED)
        tp += n; tf += f
    check("C1 passed == 1147", tp == 1147, str(tp))
    check("C2 failed == 7", tf == 7, str(tf))
    check("C3 checks == 1154", tp + tf == 1154, str(tp + tf))
    check("C4 and this is NOT what the runner reported that day",
          (tp + tf, tf) != (1152, 2), "reported 1152 checks / 2 failed")
else:
    check("C SKIPPED-AS-FAILURE: no bash available", False)

print("\n== D. a suite that printed nothing is UNSCORED, not zero ==")
check("D1 an empty line increments UNSCORED",
      re.search(r'if \[ -z "\$line" \]; then\s*\n\s*UNSCORED=\$\(\(UNSCORED\+1\)\)', src) is not None)
check("D2 and does NOT reach the TOTAL/FAILED accumulation",
      re.search(r'UNSCORED=\$\(\(UNSCORED\+1\)\).*?else.*?TOTAL=\$\(\(TOTAL\+n\)\)', src, re.S) is not None)
check("D3 UNSCORED is initialised", "UNSCORED=0" in src)
check("D4 UNSCORED is reported in the summary", "$UNSCORED suite(s) UNSCORED" in src)
check("D5 UNSCORED forces a non-zero exit",
      '[ "$FAILED" -eq 0 ] && [ "$UNSCORED" -eq 0 ] || exit 1' in src)

print("\n== E. THE SHIPPED SOURCE, not a retyped copy (§2) ==")
check("E1 run_all_tests.sh exists", os.path.exists(RUNNER))
check("E2 the parsing block is present", SHIPPED is not None)
check("E3 the A/B form is parsed as passes/total", "cut -d/ -f2" in (SHIPPED or ""))
check("E4 the failed grep is case-insensitive now",
      re.search(r"grep -oiE '\[0-9\]\+ \+failed'", src) is not None)
old_exec = [ln for ln in src.splitlines()
            if re.search(r"grep -oE '\[0-9\]\+ (passed|failed)'", ln)
            and not ln.lstrip().startswith("#")]
check("E5 the original case-sensitive scrape is not executable anywhere",
      old_exec == [], str(old_exec)[:90])
check("E6 the defect stays described in the file, so it is not relearned",
      "counted as a pass" in src.lower())

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
