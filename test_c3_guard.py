#!/usr/bin/env python3
"""test_c3_guard.py -- C3: the guard that heals the watchdog.

WHY THIS SUITE EXISTS. The guard was shipped 2026-08-29 with a live status
check and nothing else -- it said "ok: last line 36s old" once, and that was
the entire evidence for a component whose job is to spawn processes on a
production box. A supervisor nobody has tested against the cases it exists
for is a supervisor you find out about during the outage.

Every decision the guard makes goes through ONE pure function, decide(), and
that is deliberate: the spawning, the PID probe and the clock all arrive as
arguments, so the judgement can be exercised without a watchdog, a node, or
a process to kill. This suite drives it through every branch, including the
three refusals that matter more than the action:

  D*   decide(): healthy, dead, wedged-not-dead, cooling down, broken source
  S*   last_stamp(): the P16 gap reading the whole thing rests on
  T*   the cooldown state file: written BEFORE the spawn, never after
  R*   REPORT-ONLY by AST -- decide() cannot spawn, kill, or touch a node

No watchdog is started, no process is killed, no node is touched. M13 shape.
"""
import ast
import inspect
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_watchdog_guard as g   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:150]}", flush=True)


def d(gap, dead=300, alive=False, age=None, cool=900, compiles=True):
    return g.decide(gap, dead, alive, age, cool, compiles)


def main():
    print("C3 -- the guard: every branch of the decision, and its refusals\n")

    # ---- D: the decision --------------------------------------------------
    act, why = d(30)
    check("D1 a fresh log is healthy and says how fresh",
          act == "healthy" and "30" in why, (act, why))

    act, why = d(301)
    check("D2 past the death threshold with no live PID, it REVIVES",
          act == "revive", (act, why))

    act, why = d(None)
    check("D3 no log at all is report-only -- nothing to measure a gap "
          "against is not the same as a dead watchdog",
          act == "report-only" and "nothing to measure" in why, (act, why))

    # The refusal that stops the guard doubling every restart.
    act, why = d(9999, alive=True)
    check("D4 a huge gap but a LIVE pid is report-only, never revive -- a "
          "wedged process is not a dead one, and a second watchdog would "
          "double every restart the first might still make",
          act == "report-only" and "wedged" in why, (act, why))

    act, why = d(400, age=10)
    check("D5 inside the cooldown it HOLDS, and names the numbers",
          act == "hold" and "10" in why and "900" in why, (act, why))

    act, why = d(400, age=901)
    check("D6 past the cooldown it revives again", act == "revive", (act, why))

    act, why = d(400, compiles=False)
    check("D7 a watchdog that does not COMPILE is never revived -- that "
          "turns one death into a restart loop",
          act == "report-only" and "compile" in why, (act, why))

    check("D8 the threshold is a boundary, not a range: exactly at it is "
          "still healthy, one past it is not",
          d(300)[0] == "healthy" and d(300.1)[0] == "revive",
          (d(300)[0], d(300.1)[0]))

    check("D9 every branch explains itself -- a supervisor that acts "
          "without a reason cannot be audited afterwards",
          all(len(d(*a)[1].strip()) > 20 for a in
              [(30,), (301,), (None,)]), "")

    # ---- S: the P16 gap ---------------------------------------------------
    log = ("2026-08-29T14:00:00Z INFO  watchdog started\n"
           "2026-08-29T14:01:00Z INFO  nodeA ok\n")
    ts = g.last_stamp(log)
    check("S1 the NEWEST timestamp is taken, not the first",
          ts is not None and abs(ts - 1788012060.0) < 2, ts)
    check("S2 a log with no parseable stamp yields None, so the caller "
          "reports rather than guessing at a gap",
          g.last_stamp("no timestamps here\njust words\n") is None, "")
    check("S3 an empty log is None, not zero -- zero would read as 1970 "
           "and make every gap look infinite",
          g.last_stamp("") is None, "")
    check("S4 a torn final line does not hide the good line before it",
          g.last_stamp(log + "2026-08-29T14:02") is not None, "")

    # ---- T: the cooldown record ------------------------------------------
    tmp = tempfile.mkdtemp(prefix="c3_")
    old_state, old_log = g.STATE, g.GUARD_LOG
    g.STATE = os.path.join(tmp, "guard_state.json")
    g.GUARD_LOG = os.path.join(tmp, "guard.log")
    try:
        check("T1 an absent state file reads as empty, not an error",
              g.read_state() == {}, "")
        g.write_state({"last_attempt_epoch": 123.0, "attempts": 2})
        check("T2 state round-trips", g.read_state()["attempts"] == 2, "")
        g.glog("test line")
        check("T3 the guard logs to its OWN file -- writing into "
              "watchdog.log would pollute the very P16 gap signal that "
              "death is read from",
              os.path.exists(g.GUARD_LOG)
              and "test line" in open(g.GUARD_LOG, encoding="utf-8").read(),
              "")
        src = inspect.getsource(g.main)
        i_write = src.index("write_state")
        i_revive = src.index("new_pid = revive()")
        check("T4 the cooldown is recorded BEFORE the spawn, so a guard that "
              "dies mid-spawn cannot retry hot",
              i_write < i_revive, (i_write, i_revive))
    finally:
        g.STATE, g.GUARD_LOG = old_state, old_log
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- N: the nodes, seen but never touched -----------------------------
    # Added 2026-08-29 after a real outage in which the nodes AND the
    # watchdog died together (one console group, one Ctrl+C) and the guard's
    # log -- the only thing still being written -- said nothing about the
    # chain being down.
    check("N1 the guard can SEE the nodes", callable(getattr(g, "node_report",
                                                             None)), "")
    up, down = g.node_report()
    check("N2 it returns (up, down) as ports, and every port is accounted "
          "for -- a node missing from both lists would be invisible",
          sorted(up + down) == sorted(g.NODE_PORTS), (up, down))
    nsrc = inspect.getsource(g.node_report)
    check("N3 IT ONLY LOOKS. No restart, no spawn, no kill anywhere in it -- "
          "restarting nodes is the watchdog's job, and two supervisors on "
          "one machine disagreeing is worse than a slow recovery",
          not any(w in nsrc for w in ("revive", "Popen", "start_node",
                                      "taskkill", "kill", "subprocess")),
          [w for w in ("revive", "Popen", "start_node", "taskkill", "kill",
                       "subprocess") if w in nsrc])
    check("N4 ...and it says WHY it does not act, in the code, so nobody "
          "later 'improves' it into a second supervisor",
          "watchdog owns" in inspect.getsource(g.main)
          or "watchdog's job" in nsrc, "")
    check("N5 the death threshold is tuned to the watchdog's OWN contract: "
          "it writes every 60s, so 180s is three missed rounds, not five",
          g.GAP_DEAD_S == 180, g.GAP_DEAD_S)

    # ---- R: report-only, by AST ------------------------------------------
    tree = ast.parse(inspect.getsource(g.decide).lstrip())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            called.add(f.attr if isinstance(f, ast.Attribute)
                       else getattr(f, "id", "?"))
    banned = {"revive", "Popen", "run", "kill", "unlink", "remove", "open",
              "write_state", "glog"}
    check("R1 decide() is PURE by AST: it cannot spawn, kill, write or log "
          "-- it only returns a judgement",
          not (called & banned), sorted(called & banned))

    gsrc = open(os.path.join(HERE, "covenant_watchdog_guard.py"),
                encoding="utf-8").read()
    check("R2 the guard never touches a node, a database or a key",
          not any(w in gsrc for w in ("nodeA", "nodeB", ".db", ".key",
                                      "taskkill")),
          [w for w in ("nodeA", "nodeB", ".db", ".key", "taskkill")
           if w in gsrc])
    check("R3 --status can never act",
          "status_only" in gsrc and 'if status_only or action in' in gsrc, "")
    check("R4 the revive spawns the WATCHDOG and nothing else",
          "WD_SRC" in inspect.getsource(g.revive), "")

    p = sum(results)
    print(f"\nC3: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
