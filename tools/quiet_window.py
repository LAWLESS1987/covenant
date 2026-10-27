#!/usr/bin/env python3
"""tools/quiet_window.py -- is now a safe time for heavy or live-tree work on this PC? (A361, 2026-10-17)

WHY. Twice on 2026-10-17 my own work turned the system's scheduled checks red:
  - the nightly's launch gates read "11 PASS 1 BLOCKED" while my edits were uncommitted in the live tree (A359);
  - the daily's full sweep failed test_b5_mine_latency.py while my llama-bench runs held the CPU. It passed 31/31,
    twice, on a quiet machine afterwards.
Both were noise I made, and both reached him as failures. This answers one question before heavy work starts: is a
scheduled check running, or about to?

WHAT IT READS.
  - The clock: the nightly (CovenantDistill) starts 03:30 local and runs about an hour. The daily follows from the
    watchdog's hourly self-eval (10-17: 04:49-05:18). So BUSY_FROM..BUSY_TO local is busy.
  - The processes: covenant_nightly.py, covenant_daily.py, covenant_one.py or launch_check.py running now is busy,
    at any hour.
Exit 0 = quiet, 1 = busy, with the reason printed. A reader of the window, not a lock: nothing is prevented.
LICENCE: public domain.
"""
from __future__ import annotations

import datetime as _dt
import subprocess
import sys

BUSY_FROM = (3, 20)       # local time, inclusive
BUSY_TO = (5, 45)         # local time, exclusive
WATCH = ("covenant_nightly.py", "covenant_daily.py", "covenant_one.py", "launch_check.py")


def in_window(now=None):
    now = now or _dt.datetime.now()
    t = (now.hour, now.minute)
    return BUSY_FROM <= t < BUSY_TO


def running(listing=None):
    """Names from WATCH found in the process command lines (Windows: wmic-free, via PowerShell CIM)."""
    if listing is None:
        try:
            listing = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | ForEach-Object { $_.CommandLine }"],
                capture_output=True, text=True, timeout=30, creationflags=0x08000000 if sys.platform == "win32" else 0).stdout
        except Exception:                                                # noqa: BLE001
            listing = ""
    return sorted({w for w in WATCH if w in (listing or "")})


def verdict(now=None, listing=None):
    why = []
    if in_window(now):
        why.append("inside the scheduled window %02d:%02d-%02d:%02d local (nightly 03:30, daily after it)" % (BUSY_FROM + BUSY_TO))
    run = running(listing)
    if run:
        why.append("running now: " + ", ".join(run))
    return (not why), why


def main():
    ok, why = verdict()
    print("QUIET -- heavy or live-tree work will not collide with a scheduled check" if ok else "BUSY -- " + "; ".join(why))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
