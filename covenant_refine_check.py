#!/usr/bin/env python3
"""covenant_refine_check.py -- the fifteen-minute green check.

ASKED 2026-09-09: "refine every 15 minutes while staying green", and then
"buil it on windows". This is the "staying green" half, and it is the half a
machine can do unattended. Refinement needs judgement; noticing that something
went red does not, and noticing is what was missing.

WHY THIS EXISTS AT ALL. Three defects in two days went unnoticed because the
suite that covered them was green for the wrong reason:
  * A69 -- the injection guard read only the first line, and R1 passed because
    its one fixture put the directive on line one.
  * A71 -- the harvester reached no post body at all, and the M-suite passed
    because every fixture is saved page text rather than a live page.
  * P18 -- a second session's git worktree turned the version check red, which
    is the opposite failure: red for something nobody ships.
A check that runs only when a person thinks to run it finds none of those until
the person thinks to run it.

WHAT IT DOES NOT DO, deliberately:
  * It does not fix anything. It reports. A repair loop nobody is watching is
    how a machine edits its own gates at 3am.
  * It does not touch the network, the nodes, the trader, or any key.
  * It does not write to the corpus, the quarantine, or any model.

ONE AT A TIME, WHICH IS THE POINT. The scheduled task is registered with
MultipleInstances=IgnoreNew, and this file ALSO takes its own lock, because the
task setting protects one invocation route and the lock protects all of them.
Two watchdogs ran on this machine for a day because a "one only" guard matched
on a window title that was always "N/A"; a guard that can be bypassed by
starting the thing a different way is not a guard.

Run:  python covenant_refine_check.py            one pass, exit 0 green / 1 red
      python covenant_refine_check.py --status   read the log, change nothing
LICENCE: public domain.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "logs", "refine_check.log")
LOCK = os.path.join(HERE, "logs", "refine_check.lock")
PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = sys.executable

# Fast, self-contained, and none of them binds a production port or needs the
# network. Anything slower belongs in the nightly, not in a loop every quarter
# hour -- a check that costs more than the thing it guards gets turned off.
SUITES = [
    ("test_g1_doc_consistency.py", []),
    ("test_p18_version_collision.py", []),
    ("test_f2_distill_loop.py", []),
    ("test_f4_capability.py", []),
    ("test_f6_stuffing.py", []),
    ("covenant_moltbook.py", ["--selftest"]),
    ("covenant_moltbook_release.py", ["--selftest"]),
]
STALE_LOCK_S = 900          # a lock older than one interval is a dead run


def _held():
    """True if another pass is genuinely running. Stale locks are reclaimed."""
    try:
        age = time.time() - os.path.getmtime(LOCK)
    except OSError:
        return False
    if age > STALE_LOCK_S:
        try:
            os.remove(LOCK)                    # its owner died; do not wedge
        except OSError:
            pass
        return False
    return True


def main():
    if "--status" in sys.argv[1:]:
        try:
            with open(LOG, encoding="utf-8") as fh:
                tail = fh.read().splitlines()[-15:]
            print("\n".join(tail) or "(empty)")
        except OSError:
            print("no log yet at %s" % LOG)
        return 0

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    if _held():
        print("another pass is running; this one exits rather than doubling it")
        return 0
    open(LOCK, "w").close()
    try:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        red, lines = [], []
        for suite, args in SUITES:
            path = os.path.join(HERE, suite)
            if not os.path.exists(path):
                red.append("%s MISSING" % suite)
                continue
            try:
                r = subprocess.run([PY, path] + args, cwd=HERE, timeout=300,
                                   capture_output=True, text=True)
                rc = r.returncode
            except subprocess.TimeoutExpired:
                rc = "timeout"
            if rc != 0:
                red.append("%s rc=%s" % (suite, rc))
            lines.append("%s=%s" % (suite.replace(".py", ""), rc))

        verdict = "GREEN" if not red else "RED"
        entry = "%s  %-5s  %s" % (stamp, verdict, "  ".join(lines))
        if red:
            entry += "\n    RED: " + "; ".join(red)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(entry + "\n")
        print(entry)
        return 0 if not red else 1
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
