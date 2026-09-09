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
import covenant_one as C1  # noqa: E402

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


# --------------------------------------------------------------------------
# I6b/I9b/I7b/I8b/I7c/I7d: the same two halves, MEASURED.
#
# I6/I9/I7/I8 read covenant_one.py as text. Text is not behaviour, and three
# separate mutations proved it here on 2026-09-09: with every literal those
# four checks grep for left byte-for-byte intact, the suite stayed 9/9 while
# (a) run_open was handed env=None, so the transcript name never reached
# launch_check at all; (b) an `if again:` line put the exclusion back, so the
# second ask excluded this sweep's transcript again -- the exact second-cycle
# failure of 2026-09-05; (c) the second ask was moved under `if False:`, so it
# never ran. The checks below drive the real functions instead, so each of
# those three mutations turns one of them red.
# --------------------------------------------------------------------------
class Say(list):
    """Stands in for covenant_one.Tee: keeps the lines instead of printing
    them, and carries the .path the runner names to the gates."""

    def __init__(self, path):
        list.__init__(self)
        self.path = path

    def __call__(self, line=""):
        self.append(line)

    def close(self):
        pass


class NoSub(object):
    """subprocess with run() disarmed. phase_gates fires launch_check twice;
    neither run is the thing under test, and the --json one is handed an open
    file that Windows will not let the temp folder be removed around."""
    DEVNULL = None

    @staticmethod
    def run(*a, **kw):
        fh = kw.get("stdout")
        if hasattr(fh, "close"):
            fh.close()
        return None


def gates_env(tmp, again, stale=None):
    """Ask the real phase_gates for the environment it hands launch_check,
    without letting launch_check run. Returns (env, say)."""
    io.open(os.path.join(tmp, "launch_check.py"), "w", encoding="utf-8").close()
    seen = {}

    def fake_run_open(say, cmd, cwd=None, env=None, timeout=None, label=None):
        seen["env"] = env
        return 0

    say = Say(os.path.join(tmp, "ONE_SWEEP.txt"))
    old = (C1.HERE, C1.run_open, C1.subprocess,
           os.environ.get("COVENANT_ONE_TRANSCRIPT"))
    C1.HERE, C1.run_open, C1.subprocess = tmp, fake_run_open, NoSub
    if stale is None:
        os.environ.pop("COVENANT_ONE_TRANSCRIPT", None)
    else:
        os.environ["COVENANT_ONE_TRANSCRIPT"] = stale
    try:
        C1.phase_gates(say, again=again)
    finally:
        C1.HERE, C1.run_open, C1.subprocess = old[0], old[1], old[2]
        if old[3] is None:
            os.environ.pop("COVENANT_ONE_TRANSCRIPT", None)
        else:
            os.environ["COVENANT_ONE_TRANSCRIPT"] = old[3]
    return seen.get("env"), say


def run_main(tmp, argv, answers):
    """Run covenant_one.main() with every phase stubbed except the one under
    test -- the gate asks. `answers` are what the stubbed phase_gates returns,
    in order. Returns ([(again, transcript_length_at_the_ask), ...], say)."""
    asks = []

    def fake_gates(say, again=False):
        asks.append((again, len(say)))
        return answers[min(len(asks) - 1, len(answers) - 1)]

    say = Say(os.path.join(tmp, "ONE_RUN.txt"))
    names = ("Tee", "phase_identity", "phase_coverage", "phase_integrity",
             "phase_gates", "phase_sweep", "phase_live", "phase_actions")
    old = dict((n, getattr(C1, n)) for n in names)
    old_argv, old_here = sys.argv, C1.HERE
    C1.HERE = tmp
    C1.Tee = lambda path: say
    C1.phase_identity = lambda s: None
    C1.phase_coverage = lambda s: ([], [], 0, [])
    C1.phase_integrity = lambda s, transported=False: []
    C1.phase_gates = fake_gates
    C1.phase_sweep = lambda s, only=None, repeat=1, verbose=False: [
        ("test_x.py", "PASS", 1.0, 3, 0)]
    C1.phase_live = lambda s, title=None: None
    C1.phase_actions = lambda s, a, gates=None: []
    sys.argv = ["covenant_one.py"] + list(argv)
    try:
        C1.main()
    finally:
        for n in names:
            setattr(C1, n, old[n])
        sys.argv, C1.HERE = old_argv, old_here
    return asks, say


def line_at(say, prefix):
    """Index of the first transcript line with this prefix, or -1."""
    for i, l in enumerate(say):
        if l.startswith(prefix):
            return i
    return -1


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

    # Now the same two halves again, run rather than read.
    with tempfile.TemporaryDirectory() as tmp:
        env, say = gates_env(tmp, again=False)
        got = (env or {}).get("COVENANT_ONE_TRANSCRIPT")
        ok("I6b", "measured: the first ask really hands launch_check this sweep's transcript",
           got == os.path.abspath(say.path), str(got))

    with tempfile.TemporaryDirectory() as tmp:
        stale = os.path.join(tmp, "SOME_OTHER_SWEEP.txt")
        env, say = gates_env(tmp, again=True, stale=stale)
        # Stale on purpose: the second ask must clear an inherited exclusion,
        # not just refrain from adding one. Excluding it both times is what
        # kept the 2026-09-05 second cycle from being green.
        ok("I9b", "measured: the second ask excludes nothing, even with an exclusion inherited",
           env is not None and "COVENANT_ONE_TRANSCRIPT" not in env,
           str((env or {}).get("COVENANT_ONE_TRANSCRIPT")))

    with tempfile.TemporaryDirectory() as tmp:
        asks, say = run_main(tmp, [], [2, 0])
        ok("I7b", "measured: a finished sweep with INCOMPLETE gates asks a second time, again=True",
           [a for a, _ in asks] == [False, True], repr([a for a, _ in asks]))
        i_tally, i_verdict = line_at(say, "  checks failed"), line_at(say, "  gates ")
        ok("I8b", "measured: the second ask lands after the tally and before the gates verdict",
           len(asks) == 2 and 0 <= i_tally < asks[-1][1] <= i_verdict,
           "tally %d, ask at %d, verdict %d" % (i_tally, asks[-1][1] if asks else -1, i_verdict))

    with tempfile.TemporaryDirectory() as tmp:
        asks, _ = run_main(tmp, [], [0])
        ok("I7c", "measured: gates that already PASSed are not asked again",
           len(asks) == 1, repr(asks))

    with tempfile.TemporaryDirectory() as tmp:
        asks, _ = run_main(tmp, ["--quick"], [2, 0])
        ok("I7d", "measured: a sweep that never ran (--quick) proves nothing, so no second ask",
           len(asks) == 1, repr(asks))

    print("G12-inflight: %d/%d passed" % (N - len(FAILS), N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
