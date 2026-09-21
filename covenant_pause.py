#!/usr/bin/env python3
"""covenant_pause.py -- pause one actor without stopping the rest.

ASKED 2026-09-16: "ensure they all running independent so you can pause tasks
for restart and update".

WHAT WAS TRUE BEFORE. Exactly one thing in this system could be paused: the
trader, by dropping a TRADER_HALT file. Everything else was all-or-nothing. The
highway's repair pass does not even have its own process -- it runs inside the
watchdog's round -- so "stop the highway while I update it" meant killing the
watchdog, which is the thing that restarts dead nodes. Updating one part
required taking down a part that was working.

WHAT PAUSE MEANS, AND WHAT IT DOES NOT. A paused actor TAKES NO ACTION and goes
on OBSERVING. It still measures, still reports, still writes its line. It does
not restart, repair, fetch, dispatch or place anything. That is the fail-safe
reading: pausing must never blind the system, because a blind system is how an
outage becomes an incident nobody saw. A pause that silenced the watchdog would
be worse than no pause at all.

HOW. One file per actor under ops/pause/. Present means paused; its contents are
the reason, shown wherever the pause is reported. The same idiom as TRADER_HALT,
which is deliberately NOT duplicated here: the trader's switch stays the file
covenant_trader.py and guards.py already read, and this module reports its state
rather than inventing a second switch for one condition.

USE
  python covenant_pause.py --list
  python covenant_pause.py --pause highway --why "updating the detectors"
  python covenant_pause.py --resume highway
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# COVENANT_PAUSE_DIR (2026-09-21, A190): a suite that drives an isolation rule (IM1) reached the REAL
# switch through a mutation run and paused Tetsu's immunity on the live tree; suites redirect it here.
PAUSE_DIR = os.environ.get("COVENANT_PAUSE_DIR") or os.path.join(HERE, "ops", "pause")
TRADER_HALT = os.path.join(HERE, "TRADER_HALT")

# Every actor that can be paused, and one line on what pausing it stops. An
# actor missing from here can still be paused by name -- the file is the
# mechanism -- but it will not appear in --list, and a switch nobody can see
# is a switch nobody will remember to turn off.
ACTORS = {
    "highway": "covenant_highway.run_once stops REPAIRING; it still senses and reports",
    "watchdog-restarts": "the watchdog stops RESTARTING nodes; it still watches and alerts",
    "nightly": "the nightly learning pass stops; nothing else is affected",
    "trader": "the existing TRADER_HALT file -- reported here, owned by guards.py",
    # 2026-09-21: free, the ambassador, may act on her own under his grant
    # (ops/ambassador_grant.json). This is her isolation: covenant_free_will
    # sets it when the judge refused every reply in two live rounds, and he
    # lifts it. She still learns and ranks nothing while paused.
    "ambassador": "free's round on Moltbook stops (no replies, no introduction); the grant stays on record",
    # 2026-09-21 (A182, A190): Tetsu under his grants. Both are STOP switches: "tetsu-live"
    # stops live requests and placements; "tetsu-immunity" is the immunity's own isolation
    # (covenant_immunity sets it past the day's limit; he lifts it).
    "tetsu-live": "Tetsu's live requests and placements on Coinbase stop; the grant stays on record",
    "tetsu-immunity": "Tetsu's words are judged as before (no immune pass); the grant stays on record",
}


def _path(name):
    return os.path.join(PAUSE_DIR, str(name).strip().replace(os.sep, "_")[:64])


def paused(name):
    """(bool, reason). Never raises: a pause switch that can throw is a hazard."""
    try:
        if name == "trader":
            if os.path.exists(TRADER_HALT):
                return True, "TRADER_HALT present"
            return False, ""
        p = _path(name)
        if not os.path.exists(p):
            return False, ""
        try:
            with open(p, encoding="utf-8") as fh:
                why = fh.read(300).strip()
        except OSError:
            why = ""
        return True, why or "paused (no reason recorded)"
    except Exception:                                            # noqa: BLE001
        return False, ""


def pause(name, why=""):
    if name == "trader":
        return False, ("the trader's switch is TRADER_HALT, owned by guards.py -- "
                       "drop that file rather than adding a second one")
    os.makedirs(PAUSE_DIR, exist_ok=True)
    with open(_path(name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("%s\n%s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), why.strip()))
    return True, "paused"


def resume(name):
    if name == "trader":
        return False, "remove TRADER_HALT yourself; this module does not arm the trader"
    try:
        os.unlink(_path(name))
        return True, "resumed"
    except FileNotFoundError:
        return True, "was not paused"
    except OSError as e:
        return False, str(e)


def report():
    """(alerts, infos) for the watchdog: a pause is never an alert, but a pause
    nobody remembers is how a system stays half-off for a week, so each one is
    said on every round with how long it has been there."""
    alerts, infos = [], []
    for name in sorted(ACTORS):
        is_paused, why = paused(name)
        if not is_paused:
            continue
        age = ""
        try:
            p = TRADER_HALT if name == "trader" else _path(name)
            age = " for %.1f h" % ((time.time() - os.path.getmtime(p)) / 3600.0)
        except OSError:
            pass
        infos.append("paused: %s%s -- %s (%s)" % (name, age, why, ACTORS[name]))
    return alerts, infos


def main(argv=None):
    ap = argparse.ArgumentParser(description="pause one actor without stopping the rest")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--pause")
    ap.add_argument("--resume")
    ap.add_argument("--why", default="")
    a = ap.parse_args(argv)
    if a.pause:
        ok, msg = pause(a.pause, a.why)
        print("%s: %s" % (a.pause, msg))
        return 0 if ok else 1
    if a.resume:
        ok, msg = resume(a.resume)
        print("%s: %s" % (a.resume, msg))
        return 0 if ok else 1
    for name, what in sorted(ACTORS.items()):
        is_paused, why = paused(name)
        print("%-18s %-7s %s" % (name, "PAUSED" if is_paused else "running",
                                 why if is_paused else what))
    return 0


if __name__ == "__main__":
    sys.exit(main())
