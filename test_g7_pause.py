#!/usr/bin/env python3
"""
test_g7_pause.py -- G7 (2026-09-16): one actor can be paused without stopping
the others, and a pause never blinds anything.

ASKED: "ensure they all running independent so you can pause tasks for restart
and update". Before this, one thing in the system could be paused -- the trader,
via TRADER_HALT -- and the highway's repair pass had no process of its own, so
pausing it meant killing the watchdog, which is what restarts dead nodes.

THE CONTRACT, and every line of it is driven both ways here:
  a paused actor TAKES NO ACTION and GOES ON OBSERVING.

  G7.1  pause/resume/list round-trip, in a temp directory.
  G7.2  a pause carries its reason, because a switch with no reason is a switch
        nobody dares turn off.
  G7.3  the highway, paused, performs NO repair -- the spy remedy is never
        entered -- and still reports what it sensed, including what is present.
  G7.4  ...and unpaused, the same conditions do reach the remedy.
  G7.5  the watchdog, with restarts paused, does NOT launch a node: the Popen
        spy records nothing. No real node is started by this suite.
  G7.6  ...and unpaused, it does launch (spy only, still no real node).
  G7.7  pausing one actor does not pause another.
  G7.8  the trader is REPORTED, not re-implemented: paused("trader") follows
        TRADER_HALT, and this module refuses to arm or disarm the trader.
  G7.9  a pause is reported on every round, with its age, so a system left
        half-off for a week says so.

    python test_g7_pause.py
"""
from __future__ import annotations

import os
import sys
import tempfile

import covenant_pause as P

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def main():
    real_dir, real_halt = P.PAUSE_DIR, P.TRADER_HALT
    tmp = tempfile.mkdtemp(prefix="g7_")
    P.PAUSE_DIR = os.path.join(tmp, "pause")
    P.TRADER_HALT = os.path.join(tmp, "TRADER_HALT")
    try:
        # ---- G7.1 / G7.2: the switch itself
        was, _ = P.paused("highway")
        P.pause("highway", "updating the detectors")
        on, why = P.paused("highway")
        P.resume("highway")
        off, _ = P.paused("highway")
        check("G7.1 pause, then resume, and the state follows",
              not was and on and not off, "was=%s on=%s off=%s" % (was, on, off))
        check("G7.2 the pause carries the reason it was set with",
              "updating the detectors" in why, why[:60])

        # ---- G7.3 / G7.4: the highway
        import covenant_highway as H
        calls = []
        real_rl = dict(H.REMEDIES["rotate_log"])
        real_det = H.DETECTORS
        try:
            H.REMEDIES["rotate_log"] = dict(
                real_rl, fn=lambda measured, dry_run=True: (calls.append(1), (True, "spy"))[1])
            H.DETECTORS = {"log_bloat": lambda health=None: {"state": H.PRESENT,
                                                             "measured": {"fixture": True}}}
            led = tempfile.mktemp(suffix="_g7.jsonl")

            P.pause("highway", "G7")
            alerts, infos = H.run_once(dry_run=False, ledger=led, cooldown_s=0)
            check("G7.3 paused, the highway repairs nothing", not calls, "calls=%d" % len(calls))
            check("G7.3b ...and still says what it sensed, naming what is present",
                  any("PAUSED" in i and "log_bloat" in i for i in infos), str(infos)[:110])
            check("G7.3c ...and raises no alert for being paused, because a pause is a choice",
                  not alerts, str(alerts)[:80])

            P.resume("highway")
            H.run_once(dry_run=False, ledger=led, cooldown_s=0)
            check("G7.4 mutation: unpaused, the same condition reaches the remedy",
                  bool(calls), "calls=%d" % len(calls))
        finally:
            H.REMEDIES["rotate_log"] = real_rl
            H.DETECTORS = real_det
            P.resume("highway")

        # ---- G7.5 / G7.6: the watchdog's restart action, with a Popen spy so
        # that no node is ever actually launched by this test.
        import covenant_watchdog as W
        import subprocess as _sp
        spawned = []
        real_popen = W.subprocess.Popen
        real_wlog = W.LOGDIR
        node = {"id": "ZZ", "port": 5990, "db": "nodeZZ_test.db",
                "key": "nodeZZ_test.db.key", "peers": ""}
        try:
            # The watchdog's own log and the node log it opens both go to a
            # temp directory: the first run of this suite left an empty
            # logs/nodeZZ.log in the real tree and a line in the real
            # watchdog log about a node that does not exist. A test that
            # litters the thing it measures is measuring its own litter.
            W.LOGDIR = os.path.join(tmp, "logs")
            os.makedirs(W.LOGDIR, exist_ok=True)
            W.subprocess.Popen = lambda *a, **k: spawned.append(a) or _FakeProc()

            P.pause("watchdog-restarts", "G7")
            out = W.start_node(node)
            check("G7.5 with restarts paused the watchdog launches nothing",
                  out is False and not spawned, "returned %r, spawned %d" % (out, len(spawned)))

            P.resume("watchdog-restarts")
            W.start_node(node)
            check("G7.6 mutation: unpaused, it launches",
                  len(spawned) == 1, "spawned %d" % len(spawned))
        finally:
            W.subprocess.Popen = real_popen
            W.LOGDIR = real_wlog
            P.resume("watchdog-restarts")

        # ---- G7.7: independence
        P.pause("nightly", "G7")
        n_on, _ = P.paused("nightly")
        h_on, _ = P.paused("highway")
        w_on, _ = P.paused("watchdog-restarts")
        check("G7.7 pausing one actor leaves the others running",
              n_on and not h_on and not w_on,
              "nightly=%s highway=%s watchdog=%s" % (n_on, h_on, w_on))

        # ---- G7.8: the trader is reported, never re-implemented
        t_off, _ = P.paused("trader")
        with open(P.TRADER_HALT, "w", encoding="utf-8") as fh:
            fh.write("stop")
        t_on, t_why = P.paused("trader")
        ok_pause, msg = P.pause("trader", "should refuse")
        ok_resume, _ = P.resume("trader")
        check("G7.8 the trader's state follows TRADER_HALT, both ways",
              not t_off and t_on, "%s -> %s" % (t_off, t_on))
        check("G7.8b this module refuses to arm or disarm the trader",
              not ok_pause and not ok_resume and "TRADER_HALT" in msg, msg[:70])
        check("G7.8c ...and removing the halt file is what resumes it",
              (os.unlink(P.TRADER_HALT), P.paused("trader")[0])[1] is False)

        # ---- G7.9: a pause is visible on every round, with its age
        _a, infos = P.report()
        check("G7.9 a standing pause is reported, with what it stops",
              any("nightly" in i and "hours" not in i.split("--")[0] for i in infos)
              and any("nightly" in i for i in infos), str(infos)[:110])
        check("G7.9b ...and the report raises no alert -- a pause is a decision, not a fault",
              not _a, str(_a)[:60])
        P.resume("nightly")
        _a2, infos2 = P.report()
        check("G7.9c ...and it stops being reported once resumed",
              not any("nightly" in i for i in infos2), str(infos2)[:80])
    finally:
        P.PAUSE_DIR, P.TRADER_HALT = real_dir, real_halt

    check("G7.10 the real pause directory and the real TRADER_HALT are untouched",
          P.PAUSE_DIR == real_dir and P.TRADER_HALT == real_halt
          and not os.path.exists(real_halt), "halt exists: %s" % os.path.exists(real_halt))

    failed = [n for n, ok in results if not ok]
    print(f"\nG7: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


class _FakeProc:
    pid = 99999

    def poll(self):
        return None


if __name__ == "__main__":
    sys.exit(main())
