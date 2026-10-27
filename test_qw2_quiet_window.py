#!/usr/bin/env python3
"""test_qw2_quiet_window.py -- A361: the quiet-window reader says BUSY inside the scheduled window and while a
scheduled check runs, and QUIET otherwise. Clock and process listing are handed in; nothing is run.
  QW2.1  04:00 local, nothing running: BUSY, and the reason names the window
  QW2.2  14:00 local, nothing running: QUIET
  QW2.3  14:00 local, covenant_one.py in the listing: BUSY, and the reason names it
  QW2.4  the window's edges: 03:19 quiet, 03:20 busy, 05:44 busy, 05:45 quiet
"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import quiet_window as Q  # noqa: E402

PASSED, FAILED = [], []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("  %s %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -- %s" % (detail,)))


def at(h, m):
    return dt.datetime(2026, 10, 17, h, m)


def main():
    print("QW2 -- the quiet window")
    ok, why = Q.verdict(at(4, 0), listing="")
    check("QW2.1 04:00 with nothing running is BUSY, for the window", not ok and "window" in " ".join(why), why)
    ok, why = Q.verdict(at(14, 0), listing="")
    check("QW2.2 14:00 with nothing running is QUIET", ok and not why, why)
    ok, why = Q.verdict(at(14, 0), listing="C:\\x\\python.exe covenant_one.py --all\n")
    check("QW2.3 14:00 with covenant_one.py running is BUSY, and says so", not ok and "covenant_one.py" in " ".join(why), why)
    edges = [Q.in_window(at(3, 19)), Q.in_window(at(3, 20)), Q.in_window(at(5, 44)), Q.in_window(at(5, 45))]
    check("QW2.4 edges: 03:19 quiet, 03:20 busy, 05:44 busy, 05:45 quiet", edges == [False, True, True, False], edges)
    print("\nQW2: %d/%d passed" % (len(PASSED), len(PASSED) + len(FAILED)))
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
