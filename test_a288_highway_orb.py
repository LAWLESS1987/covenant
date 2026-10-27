#!/usr/bin/env python3
"""test_a288_highway_orb.py -- A288: the Highway orb reads every detector on the road, not seven.

WHY. 2026-10-06: the orb read seven fixed detectors while the road had grown to 25; public_ci_red,
mesh_source_split and every detector added that day never reached it. covenant_pc3d.highway_detail now reads
all of them from the watchdog's fresh pass, and when that pass is stale it senses the core seven and marks the
rest unknown (amber).

WHAT IT PINS (a stand-in highway module; nothing is sensed for real).
  O1  a fresh full pass: every detector is shown, and a non-core PRESENT one reaches the orb
  O2  no fresh pass: the core seven are sensed, every other detector is 'unknown', and a note says why
  O3  a pass that predates a detector (the watchdog not yet restarted) is treated as not fresh
  O4  the real registry: every registered detector appears in the orb's detail
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_pc3d as P  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


class FakeH:
    def __init__(self, names, seen):
        self.DETECTORS = {n: None for n in names}
        self._seen = seen
        self.sensed_only = None

    def last_sense(self):
        return self._seen

    def sense(self, only=None):
        self.sensed_only = list(only or [])
        return {k: {"state": "ABSENT"} for k in self.sensed_only}


def main():
    print("A288 -- the Highway orb reads the whole road")
    names = list(P.HIGHWAY_CORE) + ["public_ci_red", "tetsu_asks_failing"]
    full = {n: "ABSENT" for n in names}
    full["public_ci_red"] = "PRESENT"
    d1, n1 = P.highway_detail(FakeH(names, full))
    check("O1 a fresh full pass shows every detector, and a non-core PRESENT one reaches the orb",
          set(d1) == set(names) and d1["public_ci_red"] == "present" and n1 is None, (d1, n1))
    h2 = FakeH(names, None)
    d2, n2 = P.highway_detail(h2)
    check("O2 no fresh pass: the core seven sensed here, the rest unknown, and a note says so",
          sorted(h2.sensed_only) == sorted(P.HIGHWAY_CORE) and d2["public_ci_red"] == "unknown"
          and d2["tetsu_asks_failing"] == "unknown" and all(d2[k] == "absent" for k in P.HIGHWAY_CORE) and n2, (d2, n2))
    partial = dict(full)
    del partial["tetsu_asks_failing"]
    h3 = FakeH(names, partial)
    d3, n3 = P.highway_detail(h3)
    check("O3 a pass that predates a detector is not fresh: the newcomer is unknown, not silently absent",
          d3["tetsu_asks_failing"] == "unknown" and n3, (d3, n3))
    import covenant_highway as H
    real = H.last_sense
    try:
        H.last_sense = lambda *a, **k: {n: "ABSENT" for n in H.DETECTORS}
        d4, _n4 = P.highway_detail(H)
    finally:
        H.last_sense = real
    check("O4 every detector the road registers appears in the orb's detail", set(d4) == set(H.DETECTORS),
          sorted(set(H.DETECTORS) - set(d4)))

    ok = sum(results)
    print("\nA288: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
