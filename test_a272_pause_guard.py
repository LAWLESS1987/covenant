#!/usr/bin/env python3
"""test_a272_pause_guard.py -- A272: a test suite never writes the LIVE pause switch.

WHY. 2026-10-06, the operator lifted free's isolation ("should be constant interaction on moltbook ...
figure it out"); three minutes later ops/pause/ambassador was back, written by test_fw1_free_will.py: its
new FW1r check drives three refusing rounds, the isolation rule fired, and FW1 had never redirected
COVENANT_PAUSE_DIR. A190 (2026-09-21) met the same shape with IM1 and fixed it per suite -- six suites
redirect, one did not, and nothing stopped it. covenant_pause now refuses pause() and resume() when the
running program is a test_*.py and the directory is the real one.

WHAT IT PINS (the live directory is never touched: the module's notion of "real" is pointed at a temp dir).
  P1  a test suite's pause() on the "real" switch is refused, says A272, and writes nothing
  P2  the same for resume(): an existing pause file survives
  P3  redirected (PAUSE_DIR != the real one), a suite pauses and resumes normally
  P4  a program that is not a test (the node, the nightly, the CLI) writes the real switch as before
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_pause as CP  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def main():
    print("A272 -- a test suite never writes the live pause switch")
    real = (CP.REAL_PAUSE_DIR, CP.PAUSE_DIR, list(sys.argv))
    try:
        with tempfile.TemporaryDirectory() as fake_real, tempfile.TemporaryDirectory() as other:
            CP.REAL_PAUSE_DIR = CP.PAUSE_DIR = fake_real
            sys.argv[0] = "test_something.py"
            ok, why = CP.pause("ambassador", "probe")
            check("P1 a suite's pause() on the real switch is refused, names A272, writes nothing",
                  ok is False and "A272" in why and not os.path.exists(os.path.join(fake_real, "ambassador")), (ok, why))
            with open(os.path.join(fake_real, "ambassador"), "w", encoding="utf-8") as fh:
                fh.write("a real isolation\n")
            ok, why = CP.resume("ambassador")
            check("P2 a suite's resume() on the real switch is refused, and the pause stands",
                  ok is False and "A272" in why and os.path.exists(os.path.join(fake_real, "ambassador")), (ok, why))
            CP.PAUSE_DIR = other
            ok1, _ = CP.pause("ambassador", "probe")
            here = os.path.exists(os.path.join(other, "ambassador"))
            ok2, _ = CP.resume("ambassador")
            check("P3 redirected, a suite pauses and resumes as before",
                  ok1 and here and ok2 and not os.path.exists(os.path.join(other, "ambassador")), (ok1, here, ok2))
            CP.PAUSE_DIR = fake_real
            sys.argv[0] = "covenant_free_will.py"
            os.remove(os.path.join(fake_real, "ambassador"))
            ok, why = CP.pause("ambassador", "isolated by the round")
            check("P4 a program that is not a test writes the real switch as before",
                  ok is True and os.path.exists(os.path.join(fake_real, "ambassador")), (ok, why))
    finally:
        CP.REAL_PAUSE_DIR, CP.PAUSE_DIR = real[0], real[1]
        sys.argv[:] = real[2]

    ok = sum(results)
    print("\nA272: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
