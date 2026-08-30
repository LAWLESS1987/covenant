#!/usr/bin/env python3
"""
guard_freshness.py -- is the thing at the TOP of the supervision chain
actually running?

THE GAP THIS FILLS

  covenant_watchdog.py revives dead NODES. covenant_watchdog_guard.py revives
  the WATCHDOG. Above the guard there is nothing, which is not a criticism of
  the guard -- it is what being last means.

  test_c2_watchdog_live.py already reads the WATCHDOG's silence as a signal
  (gap_check). Nothing anywhere read the GUARD's. So the one process with
  nothing above it was the one process whose silence nobody was listening for.

  guard.log is already a per-pass heartbeat: every branch of the guard's main()
  calls glog(), including the healthy branch, deliberately. It did not need a
  new heartbeat file. It needed a READER.

THE SILENCE CONTRACT, stated so the number is not arbitrary

  The CovenantGuard task's trigger repeats every PT2M. A healthy guard
  therefore writes a stamped line at least every 2 minutes. STALE_AFTER is 5
  minutes: more than two missed rounds, with room for a slow pass, and well
  under the 10-minute window in which a dead watchdog matters.

WHY IT REPORTS HISTORY AND NOT ONLY "RIGHT NOW"

  This is the point of the whole file. The guard was gated off on battery
  (DisallowStartIfOnBatteries), which means it stops when unplugged and
  resumes on mains -- so a check that only asked "is it fresh right now?" would
  have said YES every single time anyone looked while plugged in, for the whole
  period it was losing a third of its life.

  Measured on this machine 2026-08-30: 504 minutes of gaps over 5 minutes,
  across a 1459-minute logged window. Thirty-five per cent unsupervised, and
  invisible to any instantaneous check.

  A condition that erases its own evidence is not found by looking harder at
  the present. So this reads the whole log.

WHAT IT DOES NOT DO

  It changes nothing, starts nothing, and restarts nothing. Read-only.

USE
  python guard_freshness.py
  python guard_freshness.py --log path\to\guard.log

Exit 0 fresh with no chronic gaps, 1 stale or chronically gapped, 2 could not
measure -- and 2 is never read as 0.

LICENCE: public domain.
"""
from __future__ import annotations

import datetime
import os
import re
import sys

# The trigger repeats every 2 minutes; see the silence contract above.
EXPECT_EVERY_S = 120
STALE_AFTER_S = 300
CHRONIC_FRACTION = 0.02      # >2% of the window lost is chronic, not a blip

_TS = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z ")

CANDIDATES = [
    os.path.join(os.path.expanduser("~"), "covenant", "logs", "guard.log"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "guard.log"),
    os.path.join(os.path.expanduser("~"), "covenant-dev", "logs", "guard.log"),
]


def find_log(explicit: str = "") -> str:
    if explicit:
        return explicit
    for p in CANDIDATES:
        if os.path.isfile(p):
            return p
    return ""


def stamps(path: str):
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                m = _TS.match(line)
                if m:
                    out.append(datetime.datetime(*(int(g) for g in m.groups())))
    except OSError:
        return []
    out.sort()
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    explicit = ""
    if "--log" in argv:
        try:
            explicit = argv[argv.index("--log") + 1]
        except IndexError:
            pass

    print()
    print("  GUARD FRESHNESS -- is the top of the chain running? read-only")
    print("  " + "-" * 62)

    path = find_log(explicit)
    if not path:
        print("  No guard.log found. Looked in:")
        for p in CANDIDATES:
            print("      %s" % p)
        print()
        print("  COULD NOT MEASURE. That is not a pass: a supervisor whose log")
        print("  cannot be found is a supervisor nobody is checking.")
        return 2

    print("  log: %s" % path)
    ts = stamps(path)
    if len(ts) < 2:
        print("  Fewer than two stamped lines. COULD NOT MEASURE, which is")
        print("  not the same as healthy.")
        return 2

    now = datetime.datetime.utcnow()
    age = (now - ts[-1]).total_seconds()
    span = (ts[-1] - ts[0]).total_seconds()
    gaps = [((b - a).total_seconds(), a, b) for a, b in zip(ts, ts[1:])]
    big = [g for g in gaps if g[0] > STALE_AFTER_S]
    lost = sum(g[0] for g in big)
    frac = (lost / span) if span else 0.0

    print()
    print("  contract  : a line every %ds (task trigger PT2M); stale after %ds"
          % (EXPECT_EVERY_S, STALE_AFTER_S))
    print("  last line : %s UTC  (%.1f min ago)" % (ts[-1], age / 60.0))
    print("  window    : %.0f min, %d stamped lines" % (span / 60.0, len(ts)))

    fresh = age <= STALE_AFTER_S
    if fresh:
        print("  NOW       : FRESH -- the guard has written recently.")
    else:
        print("  NOW       : STALE -- nothing has supervised the watchdog for")
        print("              %.1f minutes. The chain's top link is not running."
              % (age / 60.0))

    print()
    print("  HISTORY -- the part an instantaneous check cannot see")
    if not big:
        print("      No gap longer than %ds in the whole log." % STALE_AFTER_S)
    else:
        print("      %d gap(s) over %ds, totalling %.0f min = %.0f%% of the"
              % (len(big), STALE_AFTER_S, lost / 60.0, frac * 100))
        print("      window with NOTHING supervising the watchdog.")
        for secs, a, _b in sorted(big, key=lambda g: -g[0])[:6]:
            print("        %7.1f min  after %s UTC" % (secs / 60.0, a))

    chronic = frac > CHRONIC_FRACTION
    print()
    if chronic:
        print("  CHRONIC. This is not a past incident that has cleared.")
        print("  A guard gated off on battery resumes on mains, so every check")
        print("  made while plugged in reports FRESH -- which is exactly what")
        print("  makes this survivable for weeks. Check the cause, not the")
        print("  current reading:")
        print("      powershell -Command \"(Get-ScheduledTask CovenantGuard)."
              "Settings | Select DisallowStartIfOnBatteries,"
              "StopIfGoingOnBatteries,StartWhenAvailable,ExecutionTimeLimit\"")
        print("  and if those are the cause:  FIX_GUARD_BATTERY.bat")
    elif fresh:
        print("  Healthy, on this evidence. It says the guard has been running,")
        print("  not that the watchdog or the nodes are correct -- those have")
        print("  their own checks, and this one is only about the top link.")

    return 0 if (fresh and not chronic) else 1


if __name__ == "__main__":
    raise SystemExit(main())
