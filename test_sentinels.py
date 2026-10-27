#!/usr/bin/env python3
"""
test_sentinels.py -- the sentinels' own checks, as a suite the loop runs.

Same reason test_xrpl_record.py exists: both runners invoke a suite as
`python <name>` with no arguments, and `covenant_sentinels.py` with no
arguments runs a LIVE check whose result depends on whether a watchdog
process happens to be writing at that moment. A green light that swings on a
running process is not a green light for the code. This wrapper runs the
offline self-test and carries its exit code; the live check is
`python covenant_sentinels.py`, which is a different question and belongs on
a schedule, not in a test suite.

Offline: no anchor is written, nothing is repaired, no process is contacted.

Run:  python test_sentinels.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_sentinels as S          # noqa: E402

if __name__ == "__main__":
    raise SystemExit(S._self_test())
