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

    # ---- 2026-11-13: the orb reads with the machine's profile, and no reading is never drawn green
    class FakeHere(FakeH):
        def __init__(self, names, seen, profile):
            FakeH.__init__(self, names, seen)
            self._profile, self.machine_seen = profile, "not passed"

        def machine_profile(self):
            return self._profile

        def sense(self, only=None, machine=None):
            self.machine_seen = machine
            self.sensed_only = list(only or [])
            skip = (machine or {}).get("not_applicable") or {}
            return {k: {"state": "ABSENT" if k in skip else "PRESENT"} for k in self.sensed_only}

    away = {"acts_here": False, "not_applicable": {"node_down": "elsewhere", "public_ci_red": "elsewhere"}}
    h5 = FakeHere(names, None, away)
    d5, n5 = P.highway_detail(h5)
    check("O5 with no fresh pass the core is sensed WITH this machine's profile",
          h5.machine_seen is away and d5["node_down"] == "absent" and d5["sweep_red"] == "present", (h5.machine_seen, d5))
    check("O5 ...and a detector outside the core that does not apply here is absent, not unknown; one that does is unknown",
          d5["public_ci_red"] == "absent" and d5["tetsu_asks_failing"] == "unknown" and "1 detector" in (n5 or ""), (d5, n5))
    h6 = FakeHere(names, None, {"acts_here": True, "not_applicable": {}})
    d6, _n6 = P.highway_detail(h6)
    check("O6 mutation: the home profile changes nothing -- the core as sensed, the rest unknown",
          d6["node_down"] == "present" and d6["public_ci_red"] == "unknown", d6)
    check("O7 a road object with no machine_profile (an older tree) is read as before", h2.sensed_only and d2["public_ci_red"] == "unknown")
    page = P.PAGE
    check("O8 the page draws NO reading as amber ('no reading'), on the Highway orb and on the mycelium",
          "const hwNone=!Object.keys(hw).length;" in page and "(hu.length||hwNone)?UNK:OK" in page
          and "CW.setMycelium(myc,hcol);" in page and "hwNone?'no reading'" in page)
    check("O8 ...and the old rule that drew an empty reading green is gone",
          "CW.setMycelium(myc,hp.length?BAD:(hu.length?UNK:OK));" not in page)

    ok = sum(results)
    print("\nA288: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
