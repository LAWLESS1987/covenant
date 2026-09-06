#!/usr/bin/env python3
"""
test_xrpl_record.py -- covenant_xrpl_record's checks, as a suite the loop runs.

WHY THIS FILE EXISTS RATHER THAN A FLAG. The nightly's verify_green and the
covenant_one sweep both invoke a suite as `python <name>` with no arguments.
covenant_xrpl_record.py with no arguments prints its help and exits 0, so
listing it directly would have added a suite that passes without testing
anything -- a green light with nothing behind it, which is worse than no
light at all. This wrapper runs the real checks and carries their exit code.

Offline: no network, no key is created, nothing is submitted.

Run:  python test_xrpl_record.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_xrpl_record as X          # noqa: E402

if __name__ == "__main__":
    raise SystemExit(X._self_test())
