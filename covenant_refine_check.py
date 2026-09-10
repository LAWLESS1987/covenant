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
# EIGHT BLACK WINDOWS EVERY FIFTEEN MINUTES, and the fix already existed.
#
# Asked 2026-09-09: "why do black screens keep popping up?" -- measured: this
# task, 8 suites per run, every 15 minutes, about 32 consoles an hour.
#
# The task itself is silent: Task Scheduler runs it under pythonw.exe, which is
# the GUI-subsystem interpreter and never allocates a console. But pythonw has
# no console to lend, and PY below is python.exe, a CONSOLE binary -- so every
# child got a brand new console window of its own. capture_output=True does not
# prevent that: redirecting the handles is not the same as suppressing the
# console, and Windows allocates one before the redirection matters.
#
# ops/hidden_task.py solved exactly this on 2026-09-03 ("stop letting it pop up
# while I'm typing") for CovenantGuard and CovenantTrader. This file was written
# afterwards and reintroduced the bug one level down -- the wrapper was applied
# to the TASK and never to the eight processes the task spawns. A fix that is
# not applied where the work moved to is not a fix that holds.
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0      # CREATE_NO_WINDOW

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
    ("test_g3_behavioural_guards.py", []),
    ("covenant_moltbook.py", ["--selftest"]),
    ("covenant_moltbook_release.py", ["--selftest"]),
    # ADDED 2026-09-09. The ambassador is the largest surface written this week
    # and the loop that exists to catch regressions was not watching it at all.
    # Measured before adding: 2 seconds, against the 300s timeout each suite
    # gets -- well inside the rule above that a check costing more than the
    # thing it guards gets turned off. It is offline: no key, no post, and its
    # one network-touching check runs with live_repo_check=False.
    ("covenant_ambassador.py", ["--selftest"]),
    ("covenant_notify.py", ["--selftest"]),
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
                                   capture_output=True, text=True,
                                   creationflags=_NO_WINDOW)
                rc = r.returncode
            except subprocess.TimeoutExpired:
                rc = "timeout"
            if rc != 0:
                red.append("%s rc=%s" % (suite, rc))
            lines.append("%s=%s" % (suite.replace(".py", ""), rc))

        # A LIVE MUTATION WAS LEFT IN THE TREE ONCE, AND IT DISARMED THE MONEY.
        #
        # A73, 2026-09-09. A mutation audit ran 30+ agents against one shared
        # working tree. When it ended, covenant_trader.py was still sitting there
        # with its two `qty = sellable` clamps replaced by `pass` -- the ONLY
        # enforcement of the 50% reserve and of the frozen HOLD_ONLY floor, gone,
        # while the trader was armed. Nothing was committed and no trader ran in
        # that window, so no harm followed. That was luck. It was found by
        # someone thinking to look, which is exactly the thing that must not be
        # the control.
        #
        # Mutation testing is the right method and will be run again. So the
        # check is not "never mutate" -- it is "never leave one behind". Any
        # source file still carrying a mutation marker, and any .mutbak left in
        # the tree, is an unfinished run, and an unfinished run on this codebase
        # can be a disarmed guard on the money path.
        #
        # The needle is assembled at runtime so this file does not match itself.
        #
        # THE FIRST VERSION OF THIS CHECK HAD THE SAME SHAPE AS THE BUG IT
        # GUARDS. Written and committed an hour earlier, it scanned
        # os.listdir(HERE) -- the top level only. Measured straight afterwards:
        # 268 tracked .py files, 48 of them in subdirectories, including all
        # four in ops/ and both in quant/. A mutation left in any of those would
        # have passed a check whose whole purpose is to notice it, and the log
        # line would have read no_stray_mutation=0 while one sat there. That is
        # A73 again one level down, and the same shape as the A76 skip that
        # counted nine unread videos as done: a negative result that cannot tell
        # "clean" from "never looked".
        #
        # Enumerating through git is what makes the scope honest rather than
        # guessed. It is exactly the tracked set at any depth -- .venv, the
        # throwaway mutation worktrees under .claude/, and private/ are excluded
        # because git already knows they are not source. The listdir fallback is
        # narrower and SAYS SO in the log, because a check that silently
        # degrades to a smaller scope is the bug above wearing a different hat.
        needle = "MUT" + "ANT"
        me = os.path.abspath(__file__)
        files, how = [], ""
        try:
            r = subprocess.run(["git", "ls-files", "*.py"], cwd=HERE, timeout=30,
                               capture_output=True, text=True,
                               creationflags=_NO_WINDOW)
            if r.returncode != 0 or not r.stdout.strip():
                raise OSError("git listed nothing")
            files = [x.strip() for x in r.stdout.splitlines() if x.strip()]
        except Exception:                                        # noqa: BLE001
            how = "-listdir"       # git absent or broken; scope shrinks, say so
            files = [n for n in os.listdir(HERE) if n.endswith(".py")]
        stray = []
        for rel in files:
            full = os.path.join(HERE, rel)
            if os.path.abspath(full) == me:
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    if needle in fh.read():
                        stray.append(rel)
            except OSError:
                continue
        # A .mutbak backup is untracked by definition, so git cannot list it.
        # Look in every directory that holds tracked python, which is where a
        # mutation tool writes the backup it means to restore from.
        for d in sorted({os.path.dirname(f) for f in files}):
            try:
                for n in os.listdir(os.path.join(HERE, d) if d else HERE):
                    if ".mutbak" in n:
                        stray.append(os.path.join(d, n) if d else n)
            except OSError:
                continue
        if stray:
            red.append("MUTATION LEFT IN TREE: " + ", ".join(sorted(stray)[:6]))
        lines.append("no_stray_mutation=%d" % (1 if stray else 0))
        lines.append("scanned=%d%s" % (len(files), how))

        verdict = "GREEN" if not red else "RED"
        # WAS THE TREE MID-EDIT? At 19:03 on 2026-09-09 this task logged
        #   RED: covenant_moltbook_release.py rc=1
        # and nothing was wrong with the committed code. The file was being
        # edited at that moment -- reverted to its old coercion for one minute
        # to prove a new check could catch it. The task reads the WORKING TREE,
        # which is right (uncommitted breakage is still breakage a person should
        # see), but it leaves a red line in a permanent log that a reader will
        # later investigate and find nothing behind.
        #
        # So the entry says which it was. This does NOT change the verdict or
        # the exit code -- suppressing a red because the tree is dirty is how a
        # check learns to excuse the thing it exists to notice. It only records
        # that a person was editing, so tomorrow's reader can tell a regression
        # from someone's hands being on the keys.
        dirty = ""
        try:
            r = subprocess.run(["git", "status", "--porcelain"], cwd=HERE,
                               timeout=20, capture_output=True, text=True,
                               creationflags=_NO_WINDOW)
            if r.returncode == 0 and r.stdout.strip():
                n = len([x for x in r.stdout.splitlines() if x.strip()])
                dirty = "  (tree dirty: %d file%s uncommitted)" % (n, "" if n == 1 else "s")
        except Exception:
            dirty = ""          # git absent or slow is not this check's business
        entry = "%s  %-5s  %s%s" % (stamp, verdict, "  ".join(lines), dirty)
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
