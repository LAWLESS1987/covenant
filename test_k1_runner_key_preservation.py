#!/usr/bin/env python3
"""K1 (2026-08-27): run_all_tests.sh must never delete a node's identity key.

No node, no socket, no mining, no real key -- every check runs in a fresh
temporary directory in well under a second, on Windows and on Linux (M29/§8:
the node runs on Windows, so this runs there too).

THE DEFECT. The sweep's cleanup was:

    rm -f covenant_unified_*.db* *.db.key

The second glob is unanchored. The suites create short-named databases
(a.db, m.db, exporter.db ...) whose keys it was meant to reap, but it matches
EVERY *.db.key in the directory. On an operator's machine that set includes
covenant_A.db.key and the six node keys nodeA/B/C_{prod,run}. Those decrypt
the persisted ledger: deleting one does not fail a test, it strands an
encrypted database with no key and no error message.

It appeared twice -- once at the top of the script, once at the tail of `run`
-- so a full sweep executed it 47 times. The documented instruction is to run
this script before any launch and after any change.

  A  THE MUTATION (§7): the original line, run verbatim, destroys all six.
     A guard that has only ever seen correct input has never been tested, so
     this asserts the bug is real rather than assuming it.
  B  The fix preserves every key that existed before the sweep began.
  C  And still reaps the keys the suites create, which was the point.
  D  Idempotent: 47 invocations leave the six untouched.
  E  THE SHIPPED SOURCE (§2): the file on disk carries the fix, and the
     unanchored deletion is not executable anywhere in it.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "run_all_tests.sh")

PASS = FAIL = 0

PROD_KEYS = [
    "covenant_A.db.key",
    "nodeA_prod.db.key", "nodeA_run.db.key",
    "nodeB_prod.db.key", "nodeB_run.db.key",
    "nodeC_prod.db.key",
]
# Names the suites actually construct, harvested from the test files.
TEST_STEMS = ["a", "m", "b", "exporter", "p", "f", "b2", "a2", "t",
              "peer", "p11", "founder", "e2e", "NODE_A"]


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def bash():
    """Path to a bash, or None. Git for Windows ships one."""
    for c in ("bash", r"C:\Program Files\Git\bin\bash.exe",
              r"C:\Program Files\Git\usr\bin\bash.exe"):
        p = shutil.which(c) if os.sep not in c else (c if os.path.exists(c) else None)
        if p:
            return p
    return None


BASH = bash()


def seed(d):
    """An operator's directory: six real keys, present before any sweep."""
    for k in PROD_KEYS:
        with open(os.path.join(d, k), "w") as fh:
            fh.write("PRODUCTION-KEY-" + k + "\n")


def litter_sh():
    """Shell that creates what a suite leaves behind.

    ORDERING MATTERS, and getting it wrong is how this test first lied to me
    (§4). In the real sweep PRESERVE_KEYS is computed once at the top of the
    script, BEFORE any suite has run, so artefacts appear afterwards and are
    correctly outside the snapshot. A harness that creates them first has
    them snapshotted as protected and then reports that cleanup is broken
    when it is not. So the litter is emitted as shell, to be executed after
    PRESERVE_KEYS is set, exactly as a suite would.
    """
    names = [s + e for s in TEST_STEMS for e in (".db", ".db.key")]
    names += ["covenant_unified_X.db", "covenant_unified_X.db.key"]
    return "".join(f"echo artefact > '{n}'\n" for n in names)


def run_sh(script, cwd):
    return subprocess.run([BASH, "-c", script], cwd=cwd,
                          capture_output=True, text=True, timeout=60)


def survivors(d):
    return sorted(k for k in PROD_KEYS if os.path.exists(os.path.join(d, k)))


def stray_test_keys(d):
    return sorted(f for f in os.listdir(d)
                  if f.endswith(".db.key") and f not in PROD_KEYS)


# --- extract the real shipped logic, never a retyped copy (§2) --------------
src = open(RUNNER, encoding="utf-8", errors="replace").read()
m_fn = re.search(r"^clean_test_dbs \(\) \{.*?^\}", src, re.S | re.M)
m_pre = re.search(r'^PRESERVE_KEYS=.*$', src, re.M)
SHIPPED = (m_pre.group(0) + "\n" + m_fn.group(0)) if (m_fn and m_pre) else None


print("== A. THE MUTATION: the original line really did destroy them (§7) ==")
if BASH:
    with tempfile.TemporaryDirectory() as d:
        seed(d)
        check("A0 six keys present before the sweep", len(survivors(d)) == 6)
        run_sh("rm -f covenant_unified_*.db* *.db.key 2>/dev/null", d)
        gone = survivors(d)
        check("A1 ONE invocation of the original line destroys all six",
              gone == [], f"survivors={gone}")
else:
    check("A1 SKIPPED-AS-FAILURE: no bash found, so this did NOT run (§5)",
          False, "install Git for Windows or run on Linux")

print("\n== B. the fix preserves what was already there ==")
if BASH and SHIPPED:
    with tempfile.TemporaryDirectory() as d:
        seed(d)
        r = run_sh(SHIPPED + "\n" + litter_sh() + "clean_test_dbs\n", d)
        check("B1 clean_test_dbs exits 0", r.returncode == 0, r.stderr[:80])
        check("B2 all six node keys SURVIVE",
              survivors(d) == sorted(PROD_KEYS),
              f"{len(survivors(d))}/6")
        for k in PROD_KEYS:
            p = os.path.join(d, k)
            check(f"B3 {k} survives with its bytes intact",
                  os.path.exists(p) and "PRODUCTION-KEY-" in open(p).read())
else:
    check("B SKIPPED-AS-FAILURE: no bash, or the fix is not in the source",
          False, f"bash={bool(BASH)} shipped_fn={bool(SHIPPED)}")

print("\n== C. and still reaps the artefacts, which was the point ==")
if BASH and SHIPPED:
    with tempfile.TemporaryDirectory() as d:
        seed(d)
        run_sh(SHIPPED + "\n" + litter_sh() + "clean_test_dbs\n", d)
        check("C1 no suite-created *.db.key is left behind",
              stray_test_keys(d) == [], str(stray_test_keys(d))[:80])
        check("C2 covenant_unified_* databases are gone too",
              not any(f.startswith("covenant_unified_") for f in os.listdir(d)))
else:
    check("C SKIPPED-AS-FAILURE: no bash available", False)

print("\n== D. idempotent across a whole sweep ==")
if BASH and SHIPPED:
    with tempfile.TemporaryDirectory() as d:
        seed(d)
        # 47 = once at the top of the script, once per `run` call.
        run_sh(SHIPPED + "\nfor i in $(seq 1 47); do clean_test_dbs; done\n", d)
        check("D1 47 invocations leave all six keys",
              survivors(d) == sorted(PROD_KEYS), f"{len(survivors(d))}/6")
    with tempfile.TemporaryDirectory() as d:
        # No keys at all must not error: a fresh clone has none.
        r = run_sh(SHIPPED + "\nclean_test_dbs\n", d)
        check("D2 an empty directory is not an error", r.returncode == 0,
              r.stderr[:80])
else:
    check("D SKIPPED-AS-FAILURE: no bash available", False)

print("\n== E. THE SHIPPED SOURCE, not a retyped copy (§2) ==")
check("E1 run_all_tests.sh exists", os.path.exists(RUNNER))
check("E2 it defines clean_test_dbs", m_fn is not None)
check("E3 it snapshots the pre-existing keys", m_pre is not None)
check("E4 clean_test_dbs is actually CALLED, not merely defined",
      len(re.findall(r"^\s*clean_test_dbs\b", src, re.M)) >= 3,
      "definition + both former rm sites")

# The unanchored deletion must survive ONLY as commentary.
executable = [ln for ln in src.splitlines()
              if "*.db.key" in ln
              and ln.lstrip().startswith("rm ")]
check("E5 no executable line deletes an unanchored *.db.key",
      executable == [], str(executable)[:100])
check("E6 the defect is still described in the file, so it is not relearned",
      "unanchored" in src.lower())

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
