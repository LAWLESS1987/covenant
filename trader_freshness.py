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
  on: after the trigger time, did a cycle FINISH today?

CORRECTION 2026-09-09 -- IT WAS ANSWERING A WEAKER QUESTION THAN IT CLAIMED.

  These lines used to read "is there a run header dated today? It reads the log
  the run itself writes, not the scheduler's opinion of what it attempted."
  The second sentence was false. TRADER_TASK.bat:30 and FUTURE.bat:42 echo the
  `==== date time ====` header BEFORE python starts, unconditionally, so the
  header IS the scheduler's opinion of what it attempted. Measured against the
  shipped code:

      header + a completed cycle              -> exit 0 RAN
      header + ModuleNotFoundError traceback  -> exit 0 RAN
      header alone, nothing after it          -> exit 0 RAN

  The one monitor watching the money path could not tell a working trader from
  one that died on import. covenant_trader.main() now prints CYCLE COMPLETE
  after run_once returns -- printed by the cycle, not the wrapper, because a
  marker the launcher writes is bypassed by launching another way. A crash
  cannot print it: run_once raises straight past the line. A refusal DOES print
  it, because a cycle that ran and refused is a cycle that finished.

WHAT IT REPORTS

  exit 0  RAN     a CYCLE COMPLETE dated today (or the trigger is not yet due)
  exit 0  RAN/WEAK a header dated today, in a log that has never carried a
                  CYCLE COMPLETE -- says the launcher started, nothing more.
                  The first marker ever written arms the strict rule for good.
  exit 1  STARTED BUT DID NOT FINISH  a header today, no marker today, in a log
                  that does carry markers. This is the case that used to be 0.
  exit 1  MISSED  the trigger has passed and nothing is dated today
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
_DONE = re.compile(r"^---- CYCLE COMPLETE (.*?) ----\s*$", re.M)


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


def done_dates(text):
    """Every CYCLE COMPLETE marker, as (y, m, d), in file order.

    THE HEADER IS NOT WRITTEN BY THE RUN, found 2026-09-09. This file's own
    docstring said it "reads the log the run itself writes, not the scheduler's
    opinion of what it attempted". That was false. TRADER_TASK.bat:30 and
    FUTURE.bat:42 echo the `==== date time ====` header BEFORE python starts,
    unconditionally, so the header means the batch file began. Measured against
    the shipped verdict():

        header + a completed cycle              -> exit 0 RAN
        header + ModuleNotFoundError traceback  -> exit 0 RAN
        header alone, nothing after it          -> exit 0 RAN

    So the monitor on the money path could not tell a working trader from one
    that died on import. covenant_trader.main() now prints CYCLE COMPLETE after
    run_once returns -- from the cycle itself, not the wrapper, because a marker
    written by the launcher is bypassed by launching another way.
    """
    out = []
    for h in _DONE.findall(text or ""):
        m = _US_DATE.search(h)
        if m:
            mo, d, y = (int(g) for g in m.groups())
            out.append((y, mo, d))
    return out


def verdict(text, today, now_hm, due_hm=(9, 0), grace_min=5):
    """(code, sentence). today is (y, m, d); now_hm and due_hm are (h, m)."""
    if text is None:
        return 2, "UNKNOWN: trader_log.txt could not be read."
    dated, undated = run_dates(text)
    done = done_dates(text)
    # MIGRATION, AND WHY IT IS NOT A LOOPHOLE. A log written before the marker
    # existed contains none, and demanding one would report a failure every day
    # for a week over a change in this file rather than a change in the trader.
    # So the stricter question is asked only once the log proves the marker is
    # being written at all. That is a one-way door: the first CYCLE COMPLETE
    # ever written arms it permanently for that log, and it cannot be disarmed
    # by a trader that stops finishing -- which is the case it exists to catch.
    marker_live = bool(done)
    if today in done:
        return 0, ("RAN: a cycle dated %04d-%02d-%02d COMPLETED -- the trader "
                   "printed it, not the launcher." % today)
    if today in dated and not marker_live:
        return 0, ("RAN: a run header dated %04d-%02d-%02d is in trader_log.txt. "
                   "WEAK: this log has no CYCLE COMPLETE marker anywhere, so this "
                   "says the launcher started, not that a cycle finished." % today)
    if today in dated:
        return 1, ("STARTED BUT DID NOT FINISH: a run header dated "
                   "%04d-%02d-%02d is in trader_log.txt, but no CYCLE COMPLETE "
                   "for today, and this log carries them. The launcher wrote "
                   "that header before python began; something after it did not "
                   "return. Read the lines under the header." % today)
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
    # THE EXIT CODE ITSELF HAD NO COVERAGE (found 2026-09-09). Every check above
    # calls verdict() directly; nothing above ever ran the program. So the suite
    # stayed 11/11 green under two mutations that destroy the one contract this
    # file exists for -- an exit code something can alarm on:
    #   main(): `return code`                 -> `return 0`   (a stale log alarms at 0)
    #   main(): `except OSError: text = None` -> `text = ""`  (an unreadable log exits 1,
    #                                                          not the promised 2)
    # The line above that prints "an unreadable log is UNKNOWN (exit 2), never 0"
    # had never observed an exit code at all. These three run the file the way the
    # scheduler runs it, through `raise SystemExit(main())`, and read the code.
    import subprocess
    import tempfile

    def cli(log_path):
        # --due 00:00 --grace 0 so the trigger has always passed: the fixture,
        # not the clock, decides the verdict.
        return subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--log", log_path,
             "--due", "00:00", "--grace", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT).returncode

    with tempfile.TemporaryDirectory() as tmp:
        stale = os.path.join(tmp, "stale.txt")
        with open(stale, "w", encoding="utf-8") as fh:
            fh.write("==== Wed 01/01/2020  9:00:00.00 ====\n  PLAN\n")
        fresh = os.path.join(tmp, "fresh.txt")
        d = dt.date.today()
        with open(fresh, "w", encoding="utf-8") as fh:
            fh.write("==== x %d/%d/%d  9:00:00.00 ====\n  PLAN\n" % (d.month, d.day, d.year))
        check("EXIT CODE: the program exits 1 when the newest run in the log is "
              "not today", cli(stale) == 1)
        check("EXIT CODE: the program exits 2 when the log cannot be opened -- "
              "never 1 (which would read as a plain miss) and never 0",
              cli(os.path.join(tmp, "no-such-log.txt")) == 2)
        check("EXIT CODE: the program exits 0 on a log holding a header dated "
              "today, so the two lines above are not merely never-zero",
              cli(fresh) == 0)

    # ---- THE HEADER IS THE LAUNCHER'S, NOT THE RUN'S (2026-09-09) ----------
    # Every case below returned exit 0 RAN before the CYCLE COMPLETE marker
    # existed, including a log holding nothing but the header. The monitor on
    # the money path could not tell a working trader from one that died on
    # import, while its docstring claimed it read "the log the run itself
    # writes". These pin the distinction in both directions -- C4 is here so
    # that C1-C3 cannot be satisfied by a verdict() that has simply become
    # uniformly non-zero for logs carrying markers.
    HDR = "==== Tue 09/09/2026  9:00:01.76 ====\n"
    # The marker deliberately does NOT use the ==== delimiter: money_posture.py
    # compiles the identical `^==== (.*?) ====$` and would have counted every
    # completion as another run header, quietly inflating its run count. A new
    # marker that collides with an existing format is a bug in two files.
    DONE = "---- CYCLE COMPLETE 09/09/2026 ----\n"
    TODAY, LATE = (2026, 9, 9), (14, 48)
    check("C1 a header with a CRASH under it and no marker is STARTED BUT DID "
          "NOT FINISH (exit 1) once the log carries markers -- this returned 0",
          verdict("==== Mon 09/08/2026 9:00 ====\n" + DONE.replace("09/09", "09/08")
                  + HDR + "Traceback...\nModuleNotFoundError: coinbase\n",
                  TODAY, LATE)[0] == 1)
    check("C2 ...and a bare header with nothing at all under it, likewise",
          verdict("==== Mon 09/08/2026 9:00 ====\n" + DONE.replace("09/09", "09/08")
                  + HDR, TODAY, LATE)[0] == 1)
    check("C3 a cycle that COMPLETED is RAN, and the sentence says the trader "
          "printed it rather than the launcher",
          verdict(HDR + DONE, TODAY, LATE)[0] == 0
          and "not the launcher" in verdict(HDR + DONE, TODAY, LATE)[1])
    check("C4 a REFUSAL that completed is still RAN -- a cycle that ran and "
          "refused is the gate working, not a missed run",
          verdict(HDR + "  exit 3: a required seal failed\n" + DONE,
                  TODAY, LATE)[0] == 0)
    check("C5 MIGRATION: a log that has never carried a marker still reads RAN "
          "on the header alone, so this change cannot alarm on old logs...",
          verdict(HDR, TODAY, LATE)[0] == 0)
    check("C6 ...but it SAYS the signal is weak, rather than claiming a cycle "
          "finished when it only knows the launcher started",
          "WEAK" in verdict(HDR, TODAY, LATE)[1])
    check("C7 the marker is only credited for TODAY -- yesterday's completion "
          "beside today's bare header does not clear today",
          verdict(DONE.replace("09/09", "09/08") + HDR, TODAY, LATE)[0] == 1)
    check("C8 nothing dated today at all is still MISSED, not the new state",
          "MISSED" in verdict(DONE.replace("09/09", "09/08"), TODAY, LATE)[1])

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
