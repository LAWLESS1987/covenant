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


def probe(port, timeout=4):
    """(state, detail) for one node. State is one of:

        "up"            answered 200 and detail is the parsed /health
        "rate_limited"  answered 429: the node is ALIVE and refusing to be asked again
        "http_error"    answered some other status: alive, but something is wrong
        "down"          nothing answered: refused, timed out, or unreachable

    THE DISTINCTION IS THE WHOLE POINT (2026-09-14). This used to collapse every
    failure into None and the caller printed "NOT ANSWERING". /health is an
    unlisted read endpoint, so it carries RATE_LIMIT_DEFAULT: 20 requests per 60
    seconds per source. The watchdog polls all three nodes every 60 s, this
    script polls once per second while waiting for a port to free, and a couple
    of manual status checks sit on top -- and 127.0.0.1 is ONE source to the
    limiter. Cross 20 and healthy nodes start answering 429.

    Measured today: nodes B and C were reported NOT ANSWERING by this very
    script while their processes were alive, listening, and returning 429 in
    1.5 milliseconds. That is the same mistake as the own_genesis alarm this
    script stopped on earlier -- a check reporting an emergency for a benign
    cause -- and here it is worse, because the obvious response to "two nodes
    are down" is to restart them, which would be a real outage caused entirely
    by having asked too often."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=timeout) as r:
            return "up", json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return ("rate_limited" if e.code == 429 else "http_error"), e.code
    except Exception as e:                                        # noqa: BLE001
        # A TIMEOUT IS NOT AN EMPTY PORT (2026-09-14). A connection that is
        # refused means nothing is listening; a connection that is accepted and
        # then does not answer in time means something IS listening and is
        # busy -- a node mid-boot building its judges, or one held up on a slow
        # verdict. Collapsing both into "down" let port_free() below declare an
        # occupied port free, which is the single thing its docstring promises
        # it will not do.
        inner = getattr(e, "reason", None)
        blob = ("%s %s %s" % (type(e).__name__, type(inner).__name__ if inner else "", e)).lower()
        if "timed out" in blob or "timeout" in blob:
            return "slow", type(inner).__name__ if inner else type(e).__name__
        return "down", type(e).__name__


def health(port, timeout=4):
    """The parsed /health, or None if it could not be read for ANY reason.
    Callers that must tell 'alive' from 'dead' use probe() instead."""
    state, detail = probe(port, timeout)
    return detail if state == "up" else None


def pids_for(node_id, port=None):
    """Every python process whose command line names this node -- and, when the
    port is given, THIS node on THIS port. The command line is the only thing
    that identifies one of these; see the module docstring.

    Scoped by port on 2026-09-20 (A164). Two trees on one machine both run
    nodes named A, B and C: by id alone this stopped the OTHER tree's node,
    which is how the research artifact's copy of this file killed the
    production mesh and relaunched it from the artifact tree. start_node
    writes "--port N --node-id X" adjacent, so the pattern below matches only
    a node that holds this tree's port. With no port given it behaves as
    before, for callers that have only an id."""
    like = ("*--port " + str(port) + " --node-id " + node_id + "*") if port else ("*--node-id " + node_id + "*")
    ps = ("Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
          "Where-Object { $_.CommandLine -like '" + like + "' } | "
          "Select-Object -ExpandProperty ProcessId")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:                                             # noqa: BLE001
        return []
    return [int(x) for x in out.split() if x.strip().isdigit()]


def stop(node_id, say, port=None):
    pids = pids_for(node_id, port)
    if not pids:
        say("    nothing is running as node %s%s" % (node_id, (" on port %s" % port) if port else ""))
        return True
    say("    stopping pid(s) %s" % ", ".join(str(p) for p in pids))
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %s -Force -ErrorAction SilentlyContinue" % ",".join(str(p) for p in pids)],
                   capture_output=True, timeout=60)
    return True


def port_free(port, deadline, say):
    """True only when NOTHING is on the port. A 429 means a live process is
    still holding it -- treating that as free would start a second node on an
    occupied port, which is the footgun run_node's own preflight exists to
    refuse. Polls every 2 s rather than every 1 s so that waiting here does not
    itself push the limiter over."""
    while time.time() < deadline:
        state, detail = probe(port, timeout=4)
        if state == "down":
            return True
        if state == "rate_limited":
            say("    port %d is rate-limiting (429), so something is still listening; waiting" % port)
        elif state == "slow":
            say("    port %d accepted a connection and did not answer in time (%s) -- "
                "that is a busy listener, not an empty port; waiting" % (port, detail))
        time.sleep(2)
    say("    port %d is STILL answering; stopping here rather than starting a second node on it" % port)
    return False


def wait_up(node, want_sha, before_height, say):
    """Wait for the node to answer, WITHOUT spending the /health budget doing it.

    /health allows 20 requests per 60 s from one source. This used to ask every
    2 seconds for up to 120 -- up to 60 requests, three times the budget -- so
    on any boot slower than about forty seconds it guaranteed the very 429 it
    would then report as "did not answer". It did exactly that today. A probe
    frequent enough to break what it is measuring is not a measurement.

    So: three quick looks, because most boots land inside six seconds, then one
    every eight. And on a 429, back off hard -- the answer to being over the
    limit is to stop asking, never to ask again immediately."""
    deadline = time.time() + UP_TIMEOUT_S
    saw_429 = False
    tries = 0
    while time.time() < deadline:
        state, h = probe(node["port"])
        tries += 1
        if state == "rate_limited":
            saw_429 = True
            say("    /health is rate-limited (429); backing off 30 s rather than asking harder")
            time.sleep(30)
            continue
        if state == "up":
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
        time.sleep(2 if tries <= 3 else 8)
    if saw_429:
        return False, ["it answered 429 (rate limited) and never got to 200 within %d s -- the node is "
                       "ALIVE and refusing to be asked again, not dead. Do NOT restart it; wait 60 s "
                       "and run --status." % UP_TIMEOUT_S]
    return False, ["it did not answer /health within %d s" % UP_TIMEOUT_S]


def restart_one(node, want_sha, say):
    import covenant_watchdog as W
    say("  node %s (port %d)" % (node["id"], node["port"]))
    before = health(node["port"])
    before_height = before.get("chain_height") if before else None
    say("    before: %s" % ("height %s, source %s" % (before_height, str(before.get("source_sha256", ""))[:12])
                            if before else "not answering"))
    stop(node["id"], say, node.get("port"))
    if not port_free(node["port"], time.time() + PORT_FREE_TIMEOUT_S, say):
        return False
    if W.start_node(node) is False:
        # start_node refuses while ops/pause/watchdog-restarts is present. Say
        # that, rather than "started" followed by a puzzling timeout: the node
        # is down because someone asked for it to stay down.
        say("    NOT started -- restarts are paused (covenant_pause.py --list)")
        return False
    say("    started; waiting for it to answer")
    ok, problems = wait_up(node, want_sha, before_height, say)
    for p in problems:
        say("    PROBLEM: %s" % p)
    return ok


def status(say=print):
    want = disk_sha()
    import covenant_watchdog as W
    wimp = W.disk_imports_sha12()
    say("disk source: %s   imports: %s (%d modules)" % (want, wimp, len(W.runtime_import_set())))
    for node in W.NODES:
        state, h = probe(node["port"])
        if state == "rate_limited":
            say("  node %-2s port %-5d ALIVE but rate-limiting (429) -- asked too often, not down; "
                "wait 60 s and ask again" % (node["id"], node["port"]))
            continue
        if state == "http_error":
            say("  node %-2s port %-5d answering HTTP %s -- alive, but /health is erroring"
                % (node["id"], node["port"], h))
            continue
        if state == "slow":
            say("  node %-2s port %-5d accepted the connection but did not answer in time (%s) "
                "-- listening and busy, not down" % (node["id"], node["port"], h))
            continue
        if state != "up":
            say("  node %-2s port %-5d NOT ANSWERING (%s)" % (node["id"], node["port"], h))
            continue
        src = str(h.get("source_sha256", ""))[:12]
        say("  node %-2s port %-5d height %-4s peers %-2s source %s  %s" % (
            node["id"], node["port"], h.get("chain_height"), h.get("peers"), src,
            W.source_verdict(h, want, wimp)))
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
    import covenant_watchdog as _W
    wimp = _W.disk_imports_sha12()
    print("disk source: %s   imports: %s" % (want, wimp))
    print("order: %s" % " then ".join(ids))
    print("")

    done, skipped = [], []
    for i in ids:
        node = by_id[i]
        state, h = probe(node["port"])
        # REFUSE TO RESTART A NODE WE CANNOT READ (2026-09-14). A 429 used to
        # read as "no health", which fell through to "restart it" -- so asking
        # /health too often was enough to make this script take a healthy node
        # down and stand it back up. A restart is the one thing here that costs
        # something; it must never be the consequence of a rate limit.
        if state in ("rate_limited", "slow") and not a.all and not a.only:
            print("  node %s is %s: ALIVE, but its source cannot be read right now." % (
                i, "rate-limiting (429)" if state == "rate_limited"
                else "accepting connections without answering in time"))
            print("     Not restarting it on an unread answer. Wait and run again.")
            skipped.append(i)
            continue
        if state == "up" and not a.all and not a.only and str(h.get("source_sha256", ""))[:12] == want and (wimp is None or str(h.get("imports_sha12") or "")[:12] == wimp):
            print("  node %s is already on the disk source, imports current; leaving it alone" % i)
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
