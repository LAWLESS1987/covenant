#!/usr/bin/env python3
"""ops/hidden_task.py -- run a covenant task with NO console window.

WHY (asked 2026-09-03: "stop letting it pop up while I'm typing", then
"covenant needs to not pop up and cover the screen")

  The Windows task CovenantGuard ran `python.exe covenant_watchdog_guard.py`
  every 2 minutes with an INTERACTIVE logon. python.exe is a console binary,
  so Windows allocated a console for it and put that window in front of
  whatever he was typing into -- about 720 times a day. CovenantTrader has
  the same shape once a day through TRADER_TASK.bat, and a .bat always gets
  a console.

  The fix for a .py is to run it under pythonw.exe, which is the same
  interpreter built for the GUI subsystem: no console is ever allocated.
  A .bat cannot be run that way, so this wrapper launches it from pythonw
  with CREATE_NO_WINDOW, which suppresses the console for the child too.

  Nothing about WHAT runs changes -- same script, same arguments, same
  working directory, same log files. Only the window is gone. Output that
  used to go to a console nobody read is dropped; every one of these tasks
  already writes its own log (logs/guard.log, trader_log.txt), which is
  where an unattended run has to report anyway.

USE (as the scheduled task's action)
  pythonw.exe ops\\hidden_task.py TRADER_TASK.bat
  pythonw.exe ops\\hidden_task.py covenant_distill.py --cycle 4
  A .py argument is run with this interpreter; anything else is run as a
  command. Relative paths resolve against the repository root.

EXIT  the child's exit code, so the scheduler still sees a failure.
LICENCE: public domain.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREATE_NO_WINDOW = 0x08000000


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    target = argv[0]
    path = target if os.path.isabs(target) else os.path.join(HERE, target)
    if target.lower().endswith(".py"):
        # sys.executable is pythonw.exe here; its console-bearing twin would
        # re-open a window, so the windowless one runs the child as well.
        cmd = [sys.executable, path] + argv[1:]
    elif target.lower().endswith((".bat", ".cmd")):
        cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", path] + argv[1:]
    else:
        cmd = [path] + argv[1:]
    try:
        return subprocess.run(cmd, cwd=HERE, creationflags=CREATE_NO_WINDOW).returncode
    except OSError as e:
        # A wrapper that fails must fail LOUDLY somewhere a person reads,
        # and it has no console to fail into.
        try:
            with open(os.path.join(HERE, "logs", "hidden_task.log"), "a", encoding="utf-8") as fh:
                fh.write("could not run %r: %s\n" % (cmd, e))
        except OSError:
            pass
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
