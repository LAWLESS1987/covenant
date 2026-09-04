#!/usr/bin/env python3
"""covenant_quiet.py -- run a child process without throwing a window at him.

WHY (asked three times now: "stop letting it pop up while I'm typing", then
"covenant needs to not pop up and cover the screen", then "fix the pop up
glitch")

  The first fix was the Windows tasks: CovenantGuard ran python.exe, a console
  binary, every two minutes under an interactive logon, so Windows allocated a
  console and put it in front of whatever he was typing into. Those now run
  under pythonw.exe and are silent.

  That was not all of it, and the rest is in the code. On Windows a console
  process launched from a parent that has NO console gets a BRAND NEW ONE, and
  redirecting its output does not stop that -- the window still appears, and
  for a short command it appears and vanishes, which is exactly the flicker he
  kept seeing. Every unattended path that shells out was doing this:

    covenant_github_judge   `git remote get-url` and `git credential fill`,
                            TWICE PER CALL to the runner, and a learning pass
                            makes several calls
    covenant_watchdog       every round, forever
    covenant_chat           powershell, for speech and for the microphone
    covenant_scenarios      a subprocess per scenario, from the daily task

  So the flag lives here, once, and the modules call this instead of
  subprocess directly. A helper is not the interesting part; not having to
  remember the flag at twenty call sites is.

WHAT IT DOES NOT DO
  It does not hide output -- every caller still captures or logs exactly what
  it did before. It suppresses the WINDOW, not the record. And it leaves
  DETACHED_PROCESS launches alone: a detached child (the watchdog reviving a
  node) already has no console, and the two flags do not combine.

USE
  from covenant_quiet import run, popen        # drop-in for subprocess.*
  run(["git", "status"], capture_output=True, text=True)
LICENCE: public domain.
"""
from __future__ import annotations

import os
import subprocess

# CREATE_NO_WINDOW. Present on Python 3.7+ for Windows; zero elsewhere, so the
# same call is correct on Linux where none of this applies.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0


def _flags(kw):
    if os.name != "nt":
        return kw
    kw["creationflags"] = int(kw.get("creationflags", 0)) | NO_WINDOW
    return kw


def run(cmd, **kw):
    """subprocess.run, with no console window on Windows."""
    return subprocess.run(cmd, **_flags(kw))


def popen(cmd, **kw):
    """subprocess.Popen, with no console window on Windows."""
    return subprocess.Popen(cmd, **_flags(kw))


def selftest():
    ok = []

    def check(name, cond):
        ok.append(bool(cond))
        print("%s  %s" % ("ok  " if cond else "FAIL", name))

    check("Q1 the flag is set on Windows and zero elsewhere",
          (NO_WINDOW == 0x08000000) if os.name == "nt" else (NO_WINDOW == 0))
    kw = _flags({})
    check("Q2 a call with no creationflags gets the flag",
          (kw.get("creationflags") == NO_WINDOW) if os.name == "nt" else ("creationflags" not in kw))
    kw = _flags({"creationflags": 0x00000008})
    check("Q3 an existing flag is kept, not replaced",
          (kw["creationflags"] & 0x00000008) if os.name == "nt" else True)
    r = run([__import__("sys").executable, "-c", "print('quiet')"],
            capture_output=True, text=True, timeout=60)
    check("Q4 output still comes back -- it hides the window, not the record",
          r.returncode == 0 and "quiet" in r.stdout)
    print("\ncovenant_quiet selftest: %d/%d" % (sum(ok), len(ok)))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
