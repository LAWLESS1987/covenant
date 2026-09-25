#!/usr/bin/env python3
"""MK1 -- the model keeper steps UP to the largest model that fits once the running one is
counted as reclaimable, never down, never on a guess. RUN with the keeper's readings stubbed
and a temp models directory; no server is started.

Pins covenant_model.step_up (2026-09-21, his words: "we need to rapidly make up the gap in
ai"; measured that day: 15.3 GB RAM, 4.8 free with the 3B holding 2.0, the 7B needing 6.0 --
so the 7B fit only once the 3B was put away, which the plain pick never saw).
"""
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_model as M   # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def main():
    tmp = tempfile.mkdtemp(prefix="mk1_")
    big, small = M.CANDIDATES[0][0], M.CANDIDATES[-1][0]
    for name in (big, small):
        open(os.path.join(tmp, name), "wb").write(b"x")
    real = {k: getattr(M, k) for k in ("MODELS", "free_gb", "alive", "stop", "start", "_read_state", "LOG")}
    calls = []
    try:
        M.MODELS = tmp
        M.stop = lambda say=print: calls.append("stop")
        M.start = lambda say=print: (calls.append("start") or (True, "up"))
        quiet = lambda *a, **k: None      # noqa: E731

        # (a) 2026-09-25, his choice "2" (load the big model only with room to spare): the small
        # model is up, 4.8 free + 2.3 reclaimable = 7.1 covers the big one's 7.0 but not its
        # headroom -> it STAYS; with 7.0 free (9.3 >= 7.0 + 2.0) it steps up.
        M._read_state = lambda: {"model": small}
        M.alive = lambda: True
        M.free_gb = lambda: 4.8
        ok, why = M.step_up(say=quiet)
        check("MK1a small up, 4.8 free + 2.3 reclaimable < 7.0 + %.1f headroom: stays on the small one (his choice 2)" % M.HEADROOM_GB,
              ok is False and calls == [] and "already on the largest" in why, (ok, why, calls))
        M.free_gb = lambda: 7.0
        ok, why = M.step_up(say=quiet)
        check("MK1a2 ...and with room to spare (7.0 + 2.3 >= 7.0 + headroom) it steps up",
              ok and calls == ["stop", "start"] and why.startswith("stepped up"), (ok, why, calls))

        # (b) the big one already up: nothing changes, even with memory to spare
        calls.clear()
        M._read_state = lambda: {"model": big}
        M.free_gb = lambda: 9.0
        ok, why = M.step_up(say=quiet)
        check("MK1b the largest already up: no restart, said", ok is False and calls == [] and "already on the largest" in why, (ok, why, calls))

        # (c) never steps down: the big one up but memory tight -> the small one 'fits', and nothing moves
        M.free_gb = lambda: 1.0
        ok, why = M.step_up(say=quiet)
        check("MK1c the largest up and memory tight: never steps DOWN", ok is False and calls == [] and "already on the largest" in why, (ok, why))

        # (d) free memory unreadable: nothing on a guess
        M._read_state = lambda: {"model": small}
        M.free_gb = lambda: None
        ok, why = M.step_up(say=quiet)
        check("MK1d free memory unreadable: nothing changed, said", ok is False and calls == [] and "unreadable" in why, why)

        # (e) nothing up and the small one is all that fits: starts without a stop
        M.alive = lambda: False
        M.free_gb = lambda: 3.0
        M._read_state = lambda: {}
        ok, why = M.step_up(say=quiet)
        check("MK1e nothing running: no stop, one start", ok and calls == ["start"], (ok, why, calls))

        # (f) the small one up and the budget short of the big one: no restart
        calls.clear()
        M.alive = lambda: True
        M._read_state = lambda: {"model": small}
        M.free_gb = lambda: 3.0
        ok, why = M.step_up(say=quiet)
        check("MK1f small up, 3.0 + 2.3 < the big one's bar: stays (already on the largest that fits)", ok is False and calls == [] and "already on the largest" in why, (ok, why))

        # (h) the plain pick honours the headroom for the big one only
        picks = {}
        for f in (9.5, 8.0, 2.4, 2.0):
            M.free_gb = (lambda v: (lambda: v))(f)
            p = M.pick_model()
            picks[f] = p[1] if p else None
        check("MK1h pick: 9.5 free -> big; 8.0 -> small (big needs 7.0 + headroom); 2.4 -> small (no headroom); 2.0 -> none",
              picks == {9.5: big, 8.0: small, 2.4: small, 2.0: None}, picks)

        # (i) memory pressure puts an IDLE big model away; never mid-answer, never the small one
        stops = []
        M.stop = lambda say=print: stops.append("stop")
        M.alive = lambda: True
        M.LOG = os.path.join(tmp, "model.log")
        real_last = M._last_used[0]
        try:
            M._read_state = lambda: {"model": big}
            M.free_gb = lambda: 0.8
            M._last_used[0] = 1000.0
            a = M._pressure_check(now=1000.0 + 120)          # idle two minutes, 0.8 free: put away
            M._last_used[0] = 1000.0
            b = M._pressure_check(now=1000.0 + 10)           # used ten seconds ago: left alone
            M.free_gb = lambda: 1.5
            c = M._pressure_check(now=1000.0 + 120)          # above the floor: left alone
            M._read_state = lambda: {"model": small}
            M.free_gb = lambda: 0.5
            d = M._pressure_check(now=1000.0 + 120)          # the small one is never put away for pressure
            check("MK1i under the floor an idle big model is put away; mid-answer, above the floor, or the small one: left alone",
                  (a, b, c, d) == (True, False, False, False) and stops == ["stop"], (a, b, c, d, stops))
        finally:
            M._last_used[0] = real_last
    finally:
        for k, v in real.items():
            setattr(M, k, v)
    # The weights are not tracked (models/ is gitignored), so the runner's staged copy has none: the file
    # check is made only where the directory exists, and says so otherwise.
    have = os.path.isdir(M.MODELS) and any(os.path.isfile(os.path.join(M.MODELS, n)) for n, _ in M.CANDIDATES)
    check("MK1g the candidates are listed largest first%s" % ("; both weight files are on this tree" if have else " (no weights here: the staged runner)"),
          M.CANDIDATES[0][1] > M.CANDIDATES[-1][1] and (not have or all(os.path.isfile(os.path.join(M.MODELS, n)) for n, _ in M.CANDIDATES)))

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("MK1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("MK1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
