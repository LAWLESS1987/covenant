#!/usr/bin/env python3
"""test_nv1_nightly_verify.py -- NV1: the nightly's green check names the gate that is not PASS.

WHY. The 2026-10-17 pass read "gates: 11 PASS 1 BLOCKED 0 UNKNOWN" and NOT GREEN, with every one of its 47 suites
green, and nothing in the report said which gate. Run again after the working tree was committed, every gate passed.
The cause was most likely uncommitted edits read by G1 as changed files, but the report could not show it, and the
direct line told him only "NOT GREEN". Tetsu's own practice choice that night was "Review the machine's health checks".

WHAT IT PINS, by running verify_green with launch_check and the suites stubbed (no gate or suite is really run):
  NV1.1  a BLOCKED gate is named in the report with its detail line
  NV1.2  an UNKNOWN gate is named too
  NV1.3  an all-PASS run names no gate and stays green
  NV1.4  a blocked gate still makes the pass NOT green (naming it does not excuse it)
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_nightly as N  # noqa: E402
import covenant_quiet as Q  # noqa: E402

PASSED, FAILED = [], []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("  %s %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -- %s" % (str(detail)[:300],)))


def run_with(gate_stdout):
    said = []
    real_run, real_suites = Q.run, N.GREEN_SUITES

    def fake(cmd, **kw):
        out = gate_stdout if "launch_check.py" in " ".join(map(str, cmd)) else "STUB: 1/1 passed"
        return types.SimpleNamespace(stdout=out, stderr="", returncode=0)
    try:
        Q.run, N.GREEN_SUITES = fake, ["stub_suite.py"]
        ok = N.verify_green(said.append)
    finally:
        Q.run, N.GREEN_SUITES = real_run, real_suites
    return ok, said


def main():
    print("NV1 -- the nightly names the gate that is not PASS")
    blocked = ("   G1   BLOCKED Bundle integrity -- every shipped file hashes to the manifest\n"
               "          853 checked; 2 changed; 0 missing. changed: tools/outside_eval.py, test_x.py\n"
               "   G2   PASS    Companion imports\n"
               "   11 PASS   1 BLOCKED   0 UNKNOWN\n")
    ok, said = run_with(blocked)
    named = [s for s in said if s.strip().startswith("gate G1 BLOCKED")]
    check("NV1.1 a BLOCKED gate is named with its detail line", named and "tools/outside_eval.py" in named[0], said)
    check("NV1.4 a blocked gate still makes the pass NOT green", ok is False, ok)
    unknown = "   G5   UNKNOWN The ethics judge is reachable\n          no answer in 30 s\n   11 PASS   0 BLOCKED   1 UNKNOWN\n"
    ok2, said2 = run_with(unknown)
    check("NV1.2 an UNKNOWN gate is named too", any(s.strip().startswith("gate G5 UNKNOWN") for s in said2) and ok2 is False, said2)
    clean = "   G1   PASS Bundle integrity\n   12 PASS   0 BLOCKED   0 UNKNOWN\n"
    ok3, said3 = run_with(clean)
    check("NV1.3 an all-PASS run names no gate and stays green",
          ok3 is True and not any(s.strip().startswith("gate ") for s in said3), (ok3, said3))
    print("\nNV1: %d/%d passed" % (len(PASSED), len(PASSED) + len(FAILED)))
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
