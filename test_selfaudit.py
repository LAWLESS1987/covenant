#!/usr/bin/env python3
"""
test_selfaudit.py -- the self-audit's own checks, as a suite the loop runs.

Same shape as test_sentinels.py and test_xrpl_record.py: the bare module runs
a LIVE audit whose result depends on the state of this machine's records,
which is a different question from "is the auditor correct". This wrapper runs
the offline selftest and carries its exit code. The live audit is
`python covenant_selfaudit.py`, and the nightly runs it every pass.

Run:  python test_selfaudit.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_selfaudit as SA          # noqa: E402

if __name__ == "__main__":
    raise SystemExit(SA._self_test())
