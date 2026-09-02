#!/usr/bin/env python3
"""trader_freshness.py -- did the scheduled trader actually run today?

WHY IT EXISTS (2026-09-02)

  The laptop slept 07:26-14:42 across the 09:00 trigger. On resume the Task
  Scheduler stamped \\CovenantTrader with LastRunTime 14:48:55 and result
  0x800710E0 -- a refusal, because "run as soon as possible after a missed
  start" is off for that task. Nothing ran. NumberOfMissedRuns stayed 0.
  money_posture.py printed "last run 09/02/2026 14:48:55" and every other
  reader (watchdog, guard, the scheduled self-eval) had no code path that
  could say "the trader did not run today". Four of five due runs had
  happened; the fifth was skipped in silence.

  So this answers exactly one question with an exit code something can alarm
  on: after the trigger time, is there a run header in trader_log.txt dated
  today? It reads the log the run itself writes, not the scheduler's opinion
  of what it attempted.

WHAT IT REPORTS

  exit 0  RAN    a header dated today exists (or the trigger is not yet due)
  exit 1  MISSED the trigger time has passed and no header dated today exists
  exit 2  UNKNOWN the log cannot be read or its headers cannot be dated --
                  never read as 0

USE
  python trader_freshness.py                 # today, trigger 09:00, grace 5 min
  python trader_freshness.py --due 09:00 --grace 5
  python trader_freshness.py --selftest      # the logic, mutation-tested

Read-only. Opens trader_log.txt and nothing else. Places nothing, arms nothing.
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "trader_log.txt")

_HEADER = re.compile(r"^==== (.*?) ====\s*$", re.M)
_US_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def run_dates(text):
    """Every dated run header in the log, as (y, m, d), in file order. A header
    that carries no US date is skipped and counted, so 'no dated header' can be
    told apart from 'no header'."""
    dated, undated = [], 0
    for h in _HEADER.findall(text or ""):
        m = _US_DATE.search(h)
        if m:
            mo, d, y = (int(g) for g in m.groups())
            dated.append((y, mo, d))
        else:
            undated += 1
    return dated, undated


def verdict(text, today, now_hm, due_hm=(9, 0), grace_min=5):
    """(code, sentence). today is (y, m, d); now_hm and due_hm are (h, m)."""
    if text is None:
        return 2, "UNKNOWN: trader_log.txt could not be read."
    dated, undated = run_dates(text)
    if today in dated:
        return 0, "RAN: a run header dated %04d-%02d-%02d is in trader_log.txt." % today
    due_min = due_hm[0] * 60 + due_hm[1] + grace_min
    now_min = now_hm[0] * 60 + now_hm[1]
    if now_min < due_min:
        return 0, ("NOT YET DUE: trigger %02d:%02d plus %d min grace has not passed."
                   % (due_hm[0], due_hm[1], grace_min))
    if not dated and undated:
        return 2, ("UNKNOWN: %d run header(s) carry no readable date, so today's "
                   "run cannot be told from an older one." % undated)
    last = ("%04d-%02d-%02d" % dated[-1]) if dated else "none"
    return 1, ("MISSED: trigger %02d:%02d passed %d+ min ago and trader_log.txt has "
               "no run dated today. Last run in the log: %s. The scheduler's "
               "missed-run counter does not count this; only this line does."
               % (due_hm[0], due_hm[1], grace_min, last))


def selftest():
    ok = 0
    n = 0

    def check(label, cond):
        nonlocal ok, n
        n += 1
        ok += bool(cond)
        print("%s  %s" % ("ok  " if cond else "FAIL", label))

    log = ("junk\n==== Mon 09/01/2026  9:00:01.76 ====\n  PLAN\n"
           "==== Tue 09/02/2026  9:00:02.10 ====\n  Disarmed.\n")
    check("dated headers parse in file order",
          run_dates(log)[0] == [(2026, 9, 1), (2026, 9, 2)])
    check("a run dated today is RAN", verdict(log, (2026, 9, 2), (14, 48))[0] == 0)
    check("no run today, before the trigger, is NOT YET DUE",
          verdict(log, (2026, 9, 3), (8, 30))[0] == 0)
    check("no run today, inside the grace window, is NOT YET DUE",
          verdict(log, (2026, 9, 3), (9, 4))[0] == 0)
    check("no run today, after trigger + grace, is MISSED (exit 1)",
          verdict(log, (2026, 9, 3), (9, 6))[0] == 1)
    code, msg = verdict(log, (2026, 9, 3), (14, 48))
    check("...and the sentence names the last real run", "2026-09-02" in msg)
    check("THE 2026-09-02 CASE: log ends 09-01, it is 14:48 on 09-02 -> MISSED",
          verdict("==== Tue 09/01/2026  9:00:01.76 ====\n", (2026, 9, 2), (14, 48))[0] == 1)
    check("an unreadable log is UNKNOWN (exit 2), never 0",
          verdict(None, (2026, 9, 2), (14, 48))[0] == 2)
    check("headers with no date are UNKNOWN after the trigger, not MISSED and "
          "not RAN", verdict("==== run ====\n", (2026, 9, 2), (14, 48))[0] == 2)
    check("an empty log after the trigger is MISSED with last run 'none'",
          verdict("", (2026, 9, 2), (14, 48)) == (1, verdict("", (2026, 9, 2), (14, 48))[1])
          and "none" in verdict("", (2026, 9, 2), (14, 48))[1])
    check("MUTATION: a header dated YESTERDAY does not satisfy today",
          verdict("==== Tue 09/01/2026  9:00:01.76 ====\n", (2026, 9, 2), (23, 59))[0] == 1)
    print("\ntrader_freshness selftest: %d/%d passed" % (ok, n))
    return 0 if ok == n else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", default="09:00", help="trigger time, local, HH:MM")
    ap.add_argument("--grace", type=int, default=5, help="minutes after the trigger")
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        with open(a.log, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        text = None
    now = dt.datetime.now()
    h, m = (int(x) for x in a.due.split(":"))
    code, msg = verdict(text, (now.year, now.month, now.day), (now.hour, now.minute),
                        (h, m), a.grace)
    print("  TRADER FRESHNESS  %s local, trigger %s" % (now.strftime("%Y-%m-%d %H:%M"), a.due))
    print("  " + msg)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
