#!/usr/bin/env python3
"""test_a277_moltbook_orb.py -- A277: the Moltbook orb counts what went out over a day, not the last six tries.

WHY. 2026-10-06: free's first reply in weeks went out at 13:46Z, inside a round that tried ~200 people
(A270). The orb read the last six attempts, all held, and showed "0 of 6 sent" in amber. Its rule (09-28,
"green now means something went out") stands; the window it is measured over is now FORUM_WINDOW_S.

WHAT IT PINS (covenant_pc3d.forum_detail, the function /pc/3d/state calls).
  M1  one reply sent early in a day of 200 held tries: sent 1, tried 201 -- the orb has something to show
  M2  a send older than the window does not count as today's (sent 0), but stays in the list of sends
  M3  dry runs reach no one: never tried, never sent
  M4  the list shown on click holds only rows that went out, newest six
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_pc3d as P  # noqa: E402

results = []
NOW = 2_000_000_000.0


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def row(kind="reply", sent=False, ago_h=1.0, dry=False, who="x"):
    return {"kind": kind, "sent": sent, "at": NOW - ago_h * 3600, "dry_run": dry, "author": who, "text": "t"}


def main():
    print("A277 -- the Moltbook orb counts a day")
    day = [row(sent=True, ago_h=3, who="aivonic")] + [row(ago_h=2.5) for _ in range(200)]
    shown, fd = P.forum_detail(day, now=NOW)
    check("M1 one sent among 200 held in the day: sent 1 of 201 tried", fd["sent"] == 1 and fd["tried"] == 201, fd)
    old = [row(sent=True, ago_h=30, who="old")] + [row(ago_h=2) for _ in range(5)]
    shown2, fd2 = P.forum_detail(old, now=NOW)
    check("M2 a send older than the window is not today's (sent 0), and is still listed",
          fd2["sent"] == 0 and fd2["tried"] == 5 and [r["to"] for r in shown2] == ["old"], (fd2, shown2))
    dry = [row(sent=False, ago_h=1, dry=True) for _ in range(10)]
    _s3, fd3 = P.forum_detail(dry, now=NOW)
    check("M3 dry runs are neither tried nor sent", fd3["sent"] == 0 and fd3["tried"] == 0, fd3)
    many = [row(sent=True, ago_h=1, who="w%d" % i) for i in range(9)] + [row(ago_h=0.5)]
    shown4, _fd4 = P.forum_detail(many, now=NOW)
    check("M4 the click list is only rows that went out, the newest six",
          len(shown4) == 6 and all(r["sent"] for r in shown4) and shown4[-1]["to"] == "w8", shown4)

    ok = sum(results)
    print("\nA277: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
