#!/usr/bin/env python3
"""P22 -- the scheduled watchdog restart must verify a watchdog EXISTS after it,
not merely that the restarter launched.

WHY. On 2026-09-16 covenant_watchdog_guard.py logged four revivals, each
"gap 200-294s, no live watchdog PID" (attempts #8-#11). That is this remedy
killing the watchdog and leaving nothing running for three to five minutes,
with the nodes unwatched, while the remedy reported success. The old check --
rc of the PowerShell restarter after 0.5s -- proves the restarter started. It
cannot prove a watchdog is alive, because the restarter does its work five
seconds later, by which time the caller is gone.

This test NEVER spawns PowerShell and NEVER touches the running watchdog. It
intercepts subprocess.Popen to capture the exact script the remedy would run,
then checks that script for the properties that were missing, and hands it to
PowerShell's PARSER (parse only, no execution) to prove it is syntactically
real rather than a plausible-looking string.
"""
import os
import subprocess
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_highway as H  # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-62s %s%s" % (label, "OK" if ok else "*** FAIL ***",
                            ("  " + detail) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


class FakePopen(object):
    """Stands in for the spawn. Captures the argv and reports a live child,
    so the remedy takes its success path and we see what it WOULD have run."""
    captured = None

    def __init__(self, args, **kwargs):
        FakePopen.captured = args
        self.pid = 424242

    def poll(self):
        return None                       # still running -> remedy reports OK


# The final line must not read "<digits> PASSED": covenant_one parses a
# tally out of it, and "P21 PASSED" was recorded as 21 checks when the
# suite runs 16. P21-P24 inflated the sweep by ~38 checks that way.
def main():
    print("P22a -- dry run promises, and spawns nothing")
    FakePopen.captured = None
    real_popen = subprocess.Popen
    subprocess.Popen = FakePopen
    try:
        ok, detail = H.remedy_schedule_watchdog_restart({}, dry_run=True)
        check("dry_run returns True", ok is True)
        check("dry_run spawns nothing", FakePopen.captured is None,
              "captured=%r" % (FakePopen.captured,))

        print("P22b -- the real path builds a powershell command")
        ok, detail = H.remedy_schedule_watchdog_restart({}, dry_run=False)
        args = FakePopen.captured
        check("remedy reports success", ok is True, detail)
        check("spawned powershell -NoProfile -Command",
              isinstance(args, list) and args[:3] ==
              ["powershell", "-NoProfile", "-Command"],
              "args=%r" % (args[:3] if args else None,))
    finally:
        subprocess.Popen = real_popen

    script = FakePopen.captured[3]

    print("P22c -- the %-escaping survived (this bit broke a --repair run once)")
    check("WMI filter contains literal %python%", "%python%" in script)
    check("no doubled %%python%% leaked through", "%%python%%" not in script)

    print("P22d -- THE FIX: it verifies the effect, not the invocation")
    check("counts watchdogs AFTER starting one", script.count("$a") >= 3,
          "found %d references to $a" % script.count("$a"))
    check("has a fallback when none is alive", "$a.Count -eq 0" in script)
    check("fallback retries WITHOUT the redirects that fail",
          script.count("-RedirectStandardOutput") == 1
          and script.count("Start-Process") == 2,
          "redirects=%d starts=%d" % (script.count("-RedirectStandardOutput"),
                                      script.count("Start-Process")))
    check("records the outcome where it can be read",
          "watchdog_restart_last.json" in script and "alive=" in script)
    check("marks whether the fallback was needed", "fallback_used" in script)
    check("a failing Start-Process cannot abort the script",
          script.count("try {") == 2 and script.count("catch { }") == 2,
          "try=%d catch=%d" % (script.count("try {"), script.count("catch { }")))

    print("P22e -- it still kills before it starts, and waits first")
    check("sleeps before acting, so the calling round finishes",
          "Start-Sleep -Seconds 5" in script)
    check("stops the existing watchdog", "Stop-Process -Id $_.ProcessId -Force"
          in script)

    print("P22f -- PowerShell's own parser accepts it (parse only, no run)")
    tmp = os.path.join(tempfile.mkdtemp(), "inner.ps1")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(script)
    probe = ("$e=$null;"
             "[void][System.Management.Automation.Language.Parser]::ParseFile("
             "'%s',[ref]$null,[ref]$e);"
             "if ($e) { $e.Count } else { 0 }" % tmp.replace("\\", "\\\\"))
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                             capture_output=True, text=True, timeout=120)
        errs = (out.stdout or "").strip().splitlines()
        n = errs[-1].strip() if errs else "?"
        check("parses with 0 syntax errors", n == "0",
              "parser reported %r; stderr=%s" % (n, (out.stderr or "")[:300]))
    except Exception as e:                                    # noqa: BLE001
        check("parses with 0 syntax errors", False, "could not run parser: %r" % (e,))

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("P22 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("P22 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
