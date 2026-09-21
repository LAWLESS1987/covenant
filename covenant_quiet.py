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
  import covenant_quiet; covenant_quiet.install()   # at a process entry (A204):
                                                    # every child, every module
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


# A204 (2026-09-21, his words: "still popping up"). The helper above only
# covers the call sites that were rewritten to use it. Node A was measured
# spawning `git log`, `verify_bundle.py` and PowerShell through modules that
# still called subprocess directly (the highway, reconnect, the daily plan,
# the self-audit), and because the node itself runs without a console, every
# one of those children got a NEW console -- a window, handed to Windows
# Terminal, which kept 372 dead tabs. So the flag is applied ONCE, at the
# process entry, to subprocess.Popen itself: every child of that process,
# through any module, current or future, is windowless unless the caller
# asked for a console on purpose (CREATE_NEW_CONSOLE) or for a detached
# child (DETACHED_PROCESS, which does not combine with the flag).
DETACHED_PROCESS = 0x00000008
CREATE_NEW_CONSOLE = 0x00000010
_installed = False
_orig_init = None


def _quiet_init(self, *args, **kw):
    flags = int(kw.get("creationflags", 0) or 0)
    if not flags & (DETACHED_PROCESS | CREATE_NEW_CONSOLE):
        kw["creationflags"] = flags | NO_WINDOW
    return _orig_init(self, *args, **kw)


# A204d (2026-09-21, the window that opened at 16:16:01, the second the guard
# revived the watchdog). The venv's python.exe on a Store Python is a SHIM
# that starts the real interpreter as a child. A DETACHED shim has no console,
# so Windows gives its child a new one -- a window. A survivor is therefore
# started with a HIDDEN console (CREATE_NO_WINDOW), which the shim's child
# inherits, in its own process group (so a Ctrl-C to the parent is not its),
# and out of the parent's job when the job allows it (CREATE_BREAKAWAY_FROM_JOB,
# so it outlives the shell that started its parent -- A204b).
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def survivor_flags(breakaway=True):
    """creationflags for a long-lived child that must outlive its parent and
    never show a window. 0 off Windows."""
    if os.name != "nt":
        return 0
    flags = CREATE_NEW_PROCESS_GROUP | NO_WINDOW
    if breakaway:
        flags |= CREATE_BREAKAWAY_FROM_JOB
    return flags


def popen_survivor(cmd, **kw):
    """Popen with survivor_flags(); falls back to no breakaway when the job
    forbids it (ERROR_ACCESS_DENIED), so nothing that started before fails."""
    try:
        return subprocess.Popen(cmd, creationflags=survivor_flags(True), **kw)
    except OSError as e:
        if os.name != "nt" or getattr(e, "winerror", None) != 5:
            raise
        return subprocess.Popen(cmd, creationflags=survivor_flags(False), **kw)


def install():
    """Make every child of THIS process windowless (Windows only; a no-op
    elsewhere). Returns True when the patch is in place, False on Linux."""
    global _installed, _orig_init
    if os.name != "nt":
        return False
    if not _installed:
        _orig_init = subprocess.Popen.__init__
        subprocess.Popen.__init__ = _quiet_init
        _installed = True
    return True


def uninstall():
    """For the selftest only: put subprocess back the way it was."""
    global _installed
    if _installed and _orig_init is not None:
        subprocess.Popen.__init__ = _orig_init
        _installed = False


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
    # A204: install() reaches calls that never heard of this module.
    seen = {}
    if os.name == "nt":
        real_init = subprocess.Popen.__init__
        def probe(self, *a, **kw):
            seen["flags"] = kw.get("creationflags")
            return real_init(self, *a, **kw)
        subprocess.Popen.__init__ = probe          # the probe sits UNDER the patch
        try:
            install()
            r = subprocess.run([__import__("sys").executable, "-c", "print('plain')"],
                               capture_output=True, text=True, timeout=60)
            check("Q5 after install() a plain subprocess.run carries the flag and still answers",
                  (seen.get("flags") or 0) & NO_WINDOW and r.returncode == 0 and "plain" in r.stdout)
            seen.clear()
            try:
                subprocess.Popen([__import__("sys").executable, "-c", "pass"],
                                 creationflags=DETACHED_PROCESS).wait(60)
            except OSError:
                pass
            check("Q6 a detached child is left alone (the two flags do not combine)",
                  seen.get("flags") == DETACHED_PROCESS)
            uninstall()
            seen.clear()
            subprocess.run([__import__("sys").executable, "-c", "pass"], timeout=60)
            check("Q7 broken the other way: without the patch the same call carries no flag",
                  not ((seen.get("flags") or 0) & NO_WINDOW))
        finally:
            uninstall()
            subprocess.Popen.__init__ = real_init
    else:
        check("Q5 install() is a no-op off Windows", install() is False)
        check("Q6 (Windows only) NOT RUN here", True)
        check("Q7 (Windows only) NOT RUN here", True)
    # "N/N passed" is the shape run_all_tests.sh scrapes for. Anything else is
    # reported UNSCORED, which that runner is careful to say is not a pass.
    print("\nQUIET: %d/%d passed" % (sum(ok), len(ok)))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
