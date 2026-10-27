#!/usr/bin/env python3
"""M1 -- the memory system's own suite, run by the sweep (A304, 2026-10-07).

ai_memory_system/test_memory_system.py holds the chain's limits as executable checks (A8, A8b, and since A304
A8c/A8d: a re-linked rewrite of ANY record verifies; a witnessed head catches it), 184 checks in all. No runner
executed it: covenant_one runs suites from the tree's root and names each log logs/<suite>.log, so a suite in a
subfolder had no place in the list, and test_r2 only names the file. Its guards had never been observed by the
sweep or by public CI. This runs it unchanged, from its own folder's parent as it is run by hand, and passes its
tally and exit code through. Every store it builds is a temp dir; it never touches the private ai_memory/ store.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.join(HERE, "ai_memory_system", "test_memory_system.py")

if not os.path.isfile(SUITE):
    print("M1: 0/1 passed -- %s is not here to run" % SUITE)
    sys.exit(1)
p = subprocess.run([sys.executable, SUITE], cwd=HERE, capture_output=True, text=True, timeout=900)
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr)
sys.exit(p.returncode)
