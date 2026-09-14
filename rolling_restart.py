#!/usr/bin/env python3
"""rolling_restart.py -- restart the nodes ONE AT A TIME, verifying each one is
back and on the source that is on disk before touching the next.

WHY THIS EXISTS ALONGSIDE AB_RESTART_NODES.bat (2026-09-14, the operator's
instruction: "Restart one at a time"). That script stops all three, proves the
ports are free, and starts them again -- and it refuses a healthy mesh on
purpose, because forcing one on 2026-09-06 took the chain down twice. Both
refusals are right for what it is: an all-at-once restart is a real outage, so
it should be hard to do by accident.

A rolling restart is a different act. At most one node is ever down, the other
two keep answering, and each one is proved healthy again before the next is
touched -- so the reason to refuse a healthy mesh does not apply. What it is
FOR is the case this repository hits every time the core changes: the nodes go
on running the source they were started with, and `covenant_watchdog` says so
("node(s) running a source that is NOT the one on disk"). That drift is
resolved by restarting, and there is no reason to take the chain down to do it.

WHAT IT WILL NOT DO.
  * It never deletes or rebuilds a database. Production resumes a chain.
  * It never starts a node the way it invents: it calls the watchdog's own
    start_node(), which reproduces the operator's environment key for key --
    the judge providers, the standing quorum policy, the timeouts. A node this
    starts is wired exactly like one covenant_prod.bat starts, which is the
    whole point of not writing a second launcher (P17's hazard).
  * It stops a node by its COMMAND LINE, never by window title: `tasklist /v`
    reports every python.exe title as "N/A" on this machine, which is how two
    watchdogs once came to be running at once.
  * It stops if a node does not come back. Two nodes down at once is the
    outage this exists to avoid, so a failure ends the run rather than
    continuing to the next one.

ORDER. B is the hub -- A and C each peer only with B, so while B is down those
two cannot reach each other. Nothing can avoid that; it is done in the middle,
between two nodes proved healthy, and A (the one the phone's heartbeat talks
to) is left for last.

Run:
  python rolling_restart.py            restart every node that is not on the disk source
  python rolling_restart.py --all      restart all three even if they already match
  python rolling_restart.py --status   what is running and on which source; changes nothing
  python rolling_restart.py --only C   just that one
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ORDER = ["C", "B", "A"]          # the hub in the middle; the phone's node last
UP_TIMEOUT_S = 120               # a cold node adopts genesis and builds its judges
PORT_FREE_TIMEOUT_S = 30


def disk_sha():
    with open(os.path.join(HERE, "covenant_unified_v8.py"), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def health(port, timeout=4):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:                                             # noqa: BLE001
        return None


def pids_for(node_id):
    """Every python process whose command line names this node. The command line is the
    only thing that identifies one of these; see the module docstring."""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
          "Where-Object { $_.CommandLine -like '*--node-id " + node_id + "*' } | "
          "Select-Object -ExpandProperty ProcessId")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:                                             # noqa: BLE001
        return []
    return [int(x) for x in out.split() if x.strip().isdigit()]


def stop(node_id, say):
    pids = pids_for(node_id)
    if not pids:
        say("    nothing is running as node %s" % node_id)
        return True
    say("    stopping pid(s) %s" % ", ".join(str(p) for p in pids))
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %s -Force -ErrorAction SilentlyContinue" % ",".join(str(p) for p in pids)],
                   capture_output=True, timeout=60)
    return True


def port_free(port, deadline, say):
    while time.time() < deadline:
        if health(port, timeout=2) is None:
            return True
        time.sleep(1)
    say("    port %d is STILL answering; stopping here rather than starting a second node on it" % port)
    return False


def wait_up(node, want_sha, before_height, say):
    deadline = time.time() + UP_TIMEOUT_S
    while time.time() < deadline:
        h = health(node["port"])
        if h:
            src = str(h.get("source_sha256", ""))[:12]
            height = h.get("chain_height")
            say("    up: height %s, source %s, peers %s, genesis %s" % (
                height, src, h.get("peers"), str(h.get("genesis", ""))[:8]))
            problems = []
            if src != want_sha:
                problems.append("it came back on %s, not the disk's %s" % (src, want_sha))
            if h.get("own_genesis"):
                # Trustworthy since 2026-09-14 (A114/A40) and not before. On the
                # first run of this script node A tripped this and the run
                # stopped, which was the right call by these rules and the wrong
                # answer: /health was asking who SIGNED the genesis, and node A
                # is the founder whose genesis B and C adopted. All three chains
                # were identical at the time. The flag now means what it says --
                # this node's genesis is not the canonical one -- so stopping on
                # it is correct. Read the warning in /health: it names both
                # hashes.
                problems.append("own_genesis is true -- its genesis is not the canonical one")
            try:
                if before_height is not None and int(height) < int(before_height):
                    problems.append("height went backwards: %s -> %s" % (before_height, height))
            except (TypeError, ValueError):
                pass
            return (not problems), problems
        time.sleep(2)
    return False, ["it did not answer /health within %d s" % UP_TIMEOUT_S]


def restart_one(node, want_sha, say):
    import covenant_watchdog as W
    say("  node %s (port %d)" % (node["id"], node["port"]))
    before = health(node["port"])
    before_height = before.get("chain_height") if before else None
    say("    before: %s" % ("height %s, source %s" % (before_height, str(before.get("source_sha256", ""))[:12])
                            if before else "not answering"))
    stop(node["id"], say)
    if not port_free(node["port"], time.time() + PORT_FREE_TIMEOUT_S, say):
        return False
    W.start_node(node)
    say("    started; waiting for it to answer")
    ok, problems = wait_up(node, want_sha, before_height, say)
    for p in problems:
        say("    PROBLEM: %s" % p)
    return ok


def status(say=print):
    want = disk_sha()
    say("disk source: %s" % want)
    import covenant_watchdog as W
    for node in W.NODES:
        h = health(node["port"])
        if not h:
            say("  node %-2s port %-5d NOT ANSWERING" % (node["id"], node["port"]))
            continue
        src = str(h.get("source_sha256", ""))[:12]
        say("  node %-2s port %-5d height %-4s peers %-2s source %s  %s" % (
            node["id"], node["port"], h.get("chain_height"), h.get("peers"), src,
            "on the disk source" if src == want else "STALE -- restart would pick up %s" % want))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="restart the nodes one at a time, verifying each")
    ap.add_argument("--all", action="store_true", help="restart every node, even one already on the disk source")
    ap.add_argument("--only", metavar="ID", help="restart just this node (A, B or C)")
    ap.add_argument("--status", action="store_true", help="what is running and on which source; changes nothing")
    a = ap.parse_args(argv)
    if a.status:
        return status()

    import covenant_watchdog as W
    want = disk_sha()
    by_id = {n["id"]: n for n in W.NODES}
    ids = [a.only.upper()] if a.only else ORDER
    for i in ids:
        if i not in by_id:
            print("no such node: %s (have %s)" % (i, ", ".join(sorted(by_id))))
            return 2

    print("rolling restart -- one at a time, each proved back before the next")
    print("disk source: %s" % want)
    print("order: %s" % " then ".join(ids))
    print("")

    done, skipped = [], []
    for i in ids:
        node = by_id[i]
        h = health(node["port"])
        if h and not a.all and not a.only and str(h.get("source_sha256", ""))[:12] == want:
            print("  node %s is already on the disk source; leaving it alone" % i)
            skipped.append(i)
            continue
        if not restart_one(node, want, print):
            print("")
            print("STOPPED at node %s. The other nodes were not touched." % i)
            print("Nothing was deleted. Look at logs/node%s.log, then decide." % i)
            return 1
        done.append(i)
        print("")

    print("done: restarted %s%s" % (", ".join(done) or "nothing",
                                    "; already current: " + ", ".join(skipped) if skipped else ""))
    print("")
    return status()


if __name__ == "__main__":
    sys.exit(main())
