#!/usr/bin/env python3
"""memory_watchdog.py -- the supervisor over nodes D, E and F.

Mirrors the chain's watchdog one layer down, and carries down the same
division of labour: this restarts a node that is DEAD, and it refuses to
repair a node that DISAGREES.

WHY IT WILL NOT HEAL A SPLIT, WHICH IS THE WHOLE POINT.

Healing a split means choosing which version of history is true and
overwriting the others with it. That is auto-resolution of a contradiction --
precisely the behaviour this memory system exists to refuse. `reconcile()`
returns CONTESTED instead of merging two disagreeing memories; a watchdog that
silently picked a winner among three disagreeing NODES would be committing the
same sin at the scale above, and would do it unattended, at 3am, with no
record of what the losing nodes had said.

So a split is REPORTED, loudly and with both heads named, and the operator
decides. A restart is different: a process that is not running holds no
opinion, and starting it back up destroys nothing.

The decision is a pure function (`decide`) over an assessment, so every branch
is exercised without ports, processes, or sleeping.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cluster import (AGREE, DEGRADED, NO_QUORUM, NODES,  # noqa: E402
                     SPLIT, assess, poll, roots)

POLL_S = int(os.environ.get("MEMORY_WD_POLL_S", "120"))
COOLDOWN_S = int(os.environ.get("MEMORY_WD_COOLDOWN_S", "900"))
LOG = os.environ.get("MEMORY_WD_LOG",
                     os.path.join(HERE, "logs", "memory_watchdog.log"))
STATE = os.path.join(HERE, "logs", "memory_watchdog_state.json")

# Actions this watchdog can return. `report-only` is the default for anything
# it does not positively know how to fix.
REVIVE, REPORT, HOLD, HEALTHY = "revive", "report-only", "hold", "healthy"


def decide(assessment: Dict[str, Any], dead_nodes: Tuple[str, ...],
           cooldown_age: Optional[float], cooldown_s: int = COOLDOWN_S
           ) -> Tuple[str, str]:
    """What to do about the cluster right now. Pure: no I/O, no clock."""
    v = assessment.get("verdict")

    if v == SPLIT:
        # NEVER auto-repaired, whatever else is true. Checked first so that a
        # split accompanied by a dead node cannot be answered with a restart,
        # which would look like action while leaving the disagreement standing.
        return REPORT, ("NODES DISAGREE ON HISTORY -- not repaired by design. "
                        "Choosing a winner would overwrite what the other "
                        "nodes recorded, which is the auto-resolution this "
                        "system refuses. Operator decides. "
                        + str(assessment.get("reason", "")))

    if not dead_nodes:
        if v == AGREE:
            return HEALTHY, str(assessment.get("reason", ""))
        if v == DEGRADED:
            return REPORT, ("quorum holds but a node is failing its own "
                            "self-check; a node that cannot verify its files "
                            "is not a witness. "
                            + str(assessment.get("reason", "")))
        return REPORT, str(assessment.get("reason", ""))

    if cooldown_age is not None and cooldown_age < cooldown_s:
        return HOLD, (f"{len(dead_nodes)} node(s) down {sorted(dead_nodes)} "
                      f"but last revive was {int(cooldown_age)}s ago, "
                      f"cooldown is {cooldown_s}s -- a restart loop is worse "
                      f"than a down node")

    return REVIVE, (f"node(s) {sorted(dead_nodes)} not answering; a stopped "
                    f"process holds no opinion, so starting it back up "
                    f"destroys nothing")


def wlog(msg: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + msg
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def read_state() -> Dict[str, Any]:
    try:
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_state(d: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, STATE)


def revive(names: Tuple[str, ...], base: str, token: str = "") -> Dict[str, int]:
    """Start the named nodes. Spawns ONLY this package's server, by absolute
    path, with the port and root this module owns -- never a command supplied
    from outside."""
    started, r = {}, roots(base)
    for nm, port in NODES:
        if nm not in names:
            continue
        os.makedirs(r[nm], exist_ok=True)
        # Through main.py, which is the entry point that parses arguments --
        # server.py exposes serve() but has no __main__, so spawning it
        # directly starts nothing and the watchdog would report a revive that
        # never happened. Caught by running it rather than reading it.
        cmd = [sys.executable, os.path.join(HERE, "main.py"),
               "--root", r[nm], "server",
               "--host", "127.0.0.1", "--port", str(port)]
        if token:
            cmd += ["--token", token]
        try:
            p = subprocess.Popen(cmd, cwd=HERE,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            started[nm] = p.pid
        except OSError as exc:
            wlog(f"revive {nm} FAILED: {type(exc).__name__}: {exc}")
    return started


def one_pass(base: str, token: str = "") -> Dict[str, Any]:
    reports = poll(NODES, token)
    a = assess(reports)
    dead = tuple(r["node"] for r in reports if not r["ok"])
    st = read_state()
    last = st.get("last_revive_epoch")
    age = (time.time() - float(last)) if last else None
    action, why = decide(a, dead, age)

    if action == HEALTHY:
        wlog(f"ok: {why}")
    elif action == REPORT:
        wlog(f"REPORT {a['verdict'].upper()}: {why}")
    elif action == HOLD:
        wlog(f"hold: {why}")
    elif action == REVIVE:
        wlog(f"REVIVE: {why}")
        # Cooldown is written BEFORE the spawn, so a watchdog that dies
        # mid-revive cannot come back and retry hot.
        st["last_revive_epoch"] = time.time()
        st["attempts"] = int(st.get("attempts", 0)) + 1
        write_state(st)
        started = revive(dead, base, token)
        wlog(f"started: {started or 'nothing'}")
    return {"action": action, "why": why, "assessment": a, "nodes": reports}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="watchdog for memory nodes D/E/F")
    ap.add_argument("--base", default=os.path.join(HERE, "cluster"),
                    help="base directory holding nodeD/ nodeE/ nodeF/")
    ap.add_argument("--token", default=os.environ.get("MEMORY_TOKEN", ""))
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--status", action="store_true",
                    help="report and exit; never acts")
    a = ap.parse_args(argv)

    if a.status:
        reports = poll(NODES, a.token)
        out = {"assessment": assess(reports), "nodes": reports}
        print(json.dumps(out, indent=1, sort_keys=True))
        return 0 if out["assessment"]["verdict"] in (AGREE, DEGRADED) else 1

    if a.once:
        r = one_pass(a.base, a.token)
        return 0 if r["action"] in (HEALTHY,) else 1

    wlog(f"memory watchdog up: nodes={[n for n, _ in NODES]} poll={POLL_S}s")
    while True:
        try:
            one_pass(a.base, a.token)
        except Exception as exc:                  # noqa: BLE001
            wlog(f"pass failed: {type(exc).__name__}: {exc}")
        time.sleep(POLL_S)


if __name__ == "__main__":
    sys.exit(main())
