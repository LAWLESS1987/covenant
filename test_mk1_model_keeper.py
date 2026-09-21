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
    real = {k: getattr(M, k) for k in ("MODELS", "free_gb", "alive", "stop", "start", "_read_state")}
    calls = []
    try:
        M.MODELS = tmp
        M.stop = lambda say=print: calls.append("stop")
        M.start = lambda say=print: (calls.append("start") or (True, "up"))
        quiet = lambda *a, **k: None      # noqa: E731

        # (a) the small model is up, and free + its size covers the big one: step up
        M._read_state = lambda: {"model": small}
        M.alive = lambda: True
        M.free_gb = lambda: 4.8
        ok, why = M.step_up(say=quiet)
        check("MK1a small up, 4.8 free + 2.3 reclaimable >= 6.0: stops the small one and starts (the start picks by free memory)",
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
        check("MK1f small up, 3.0 + 2.3 < 6.0: stays (already on the largest that fits)", ok is False and calls == [] and "already on the largest" in why, (ok, why))
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
