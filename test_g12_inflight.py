#!/usr/bin/env python3
"""test_g12_inflight.py -- G12 must not read the sweep's own half-written
transcript as evidence, and must say why it is UNKNOWN.

WHY (2026-09-05)
  The first full sweep after the A1 core fix ran 73 suites with 0 failed and
  still could not be green: G12 ("when did the suites last run?") reads the
  newest sweep transcript, and in phase 3 the newest transcript was the one
  that sweep was writing -- truncated at start, no tally yet -- while every
  older transcript named the core from before the fix. So the first sweep
  after ANY change to the core read UNKNOWN by its own gate, with a reason
  that pointed the wrong way ("a --check transcript?").

  Two halves fixed it. covenant_one names its transcript to launch_check in
  COVENANT_ONE_TRANSCRIPT and G12 leaves that file out; and covenant_one
  asks the gates a second time once its tally is on disk, which is the
  moment the proof exists. This file pins the first half by measurement and
  the second half by reading the runner's source, so that a future edit that
  drops either one fails here rather than in someone's first sweep.
LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import io
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import launch_check as LC  # noqa: E402

NL = chr(10)
FAILS = []
N = 0


def ok(tag, name, cond, detail=""):
    global N
    N += 1
    print("   %s  %s %s  %s" % ("PASS" if cond else "FAIL", tag, name, detail))
    if not cond:
        FAILS.append(tag)


def fake_tree(tmp, with_green=False):
    """A folder that looks like the project to G12: a core file, an in-flight
    transcript that has identity lines but no tally, and optionally an older,
    complete green transcript for the same core."""
    core = os.path.join(tmp, "covenant_unified_v8.py")
    io.open(core, "w", encoding="utf-8").write("VERSION = 'v8.99'" + NL)
    sha = hashlib.sha256(open(core, "rb").read()).hexdigest()[:12]
    plat = "Windows-11" if sys.platform.startswith("win") else "Linux-6"
    head = "core sha256 %s" % sha + NL + "platform %s" % plat + NL
    green = os.path.join(tmp, "ONE_RUN.txt")
    if with_green:
        io.open(green, "w", encoding="utf-8").write(
            head + "suites run 5" + NL + "checks failed 0" + NL)
        t = time.time() - 60
        os.utime(green, (t, t))
    inflight = os.path.join(tmp, "ONE_SWEEP.txt")
    io.open(inflight, "w", encoding="utf-8").write(head)  # no tally: the sweep is running
    return inflight


def run_g12(tmp, inflight_env):
    old_here, old_env = LC.HERE, os.environ.get("COVENANT_ONE_TRANSCRIPT")
    LC.HERE = tmp
    if inflight_env is None:
        os.environ.pop("COVENANT_ONE_TRANSCRIPT", None)
    else:
        os.environ["COVENANT_ONE_TRANSCRIPT"] = inflight_env
    try:
        # R() appends to LC.results and returns None; the gate's answer is
        # the last record.
        del LC.results[:]
        LC.g12()
        return LC.results[-1]
    finally:
        LC.HERE = old_here
        if old_env is None:
            os.environ.pop("COVENANT_ONE_TRANSCRIPT", None)
        else:
            os.environ["COVENANT_ONE_TRANSCRIPT"] = old_env


def main():
    print("G12 in-flight transcript -- the sweep's own transcript is the question, not the answer")

    with tempfile.TemporaryDirectory() as tmp:
        inflight = fake_tree(tmp, with_green=False)
        r = run_g12(tmp, inflight)
        ok("I1", "only the in-flight transcript exists: UNKNOWN, never PASS",
           r["state"] == LC.UNKNOWN, r["state"])
        ok("I2", "the reason names the sweep's own transcript as not-yet-evidence",
           "not evidence until its tally is written" in r["detail"]
           and os.path.basename(inflight) in r["detail"], r["detail"][:120])
        ok("I3", "the reason does not blame it as a --check transcript",
           "--check transcript" not in r["detail"], r["detail"][:120])

    with tempfile.TemporaryDirectory() as tmp:
        inflight = fake_tree(tmp, with_green=True)
        r = run_g12(tmp, inflight)
        ok("I4", "an older complete green transcript of the same core still proves it: PASS",
           r["state"] == LC.PASS and "ONE_RUN.txt" in r["detail"], r["detail"][:120])

    with tempfile.TemporaryDirectory() as tmp:
        fake_tree(tmp, with_green=True)
        r = run_g12(tmp, None)
        ok("I5", "with no in-flight name given, behaviour is unchanged: PASS on the green one",
           r["state"] == LC.PASS, r["detail"][:120])

    # The second half is the sweep's: after the tally it asks the gates again.
    src = io.open(os.path.join(HERE, "covenant_one.py"), encoding="utf-8").read()
    ok("I6", "covenant_one names its transcript to the gates (COVENANT_ONE_TRANSCRIPT)",
       "env.update(COVENANT_ONE_TRANSCRIPT=os.path.abspath(say.path))" in src)
    i_guard = src.find("    if not again:" + NL + "        env.update(COVENANT_ONE_TRANSCRIPT")
    ok("I9", "but only on the first ask: the second ask reads this sweep's transcript, tally and all",
       i_guard > 0 and 'env.pop("COVENANT_ONE_TRANSCRIPT", None)' in src)
    ok("I7", "covenant_one asks the gates again after the tally, only on a finished sweep",
       "gates = phase_gates(say, again=True)" in src
       and "if gates == 2 and results and not args.quick and not interrupted:" in src)
    i_tally = src.find('say("  checks failed       %d" % fails)')
    i_again = src.find("gates = phase_gates(say, again=True)")
    i_verdict = src.find('say("  gates               %s"')
    ok("I8", "and it asks AFTER the tally lines are written and BEFORE the gates verdict line",
       0 < i_tally < i_again < i_verdict, "%d < %d < %d" % (i_tally, i_again, i_verdict))

    print("G12-inflight: %d/%d passed" % (N - len(FAILS), N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
