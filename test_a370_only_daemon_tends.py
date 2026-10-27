#!/usr/bin/env python3
"""
test_a370_only_daemon_tends.py -- A370 (2026-10-18): only the daemon, in a tree that can relaunch its own nodes,
starts a service or signs with the node key.

On 2026-10-15 a suite run in a worktree started six seal services that listened on 127.0.0.1:8433 beside the real
one for three days (SO_REUSEADDR lets a second bind share the port on Windows). test_watchdog_outage.py makes
exactly six one_pass() calls that are not a total outage and stubs every remedy but the tends. Every check here
runs the code; nothing is read from source text. No process is started, no node is contacted, nothing is mined:
subprocess.Popen and urlopen are tripwires throughout.

Run:  python test_a370_only_daemon_tends.py
"""
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_watchdog as W          # noqa: E402
import covenant_highway as _HW         # noqa: E402

RAN, FAILS = [], []


def check(label, cond, detail=""):
    RAN.append(bool(cond))
    print(("ok    " if cond else "FAIL  ") + label + ("" if detail == "" else "  [%s]" % (detail,)))
    if not cond:
        FAILS.append(label)


popen, urlopen = [], []
saved = (subprocess.Popen, urllib.request.urlopen, W._port_listening, W.highway_may_act, dict(W._self_eval),
         W.health, W.start_node, W.log, _HW.run_once, _HW.sense, os.path.exists)


def _popen_trip(*a, **k):
    popen.append(a)
    raise RuntimeError("A370: a real process was started from a suite")


def _url_trip(*a, **k):
    urlopen.append(a)
    raise RuntimeError("A370: a real node was contacted from a suite")


_real_exists = os.path.exists
try:
    subprocess.Popen = _popen_trip
    urllib.request.urlopen = _url_trip
    W._port_listening = lambda port, host="127.0.0.1": False      # the 10-15 condition: nothing seen on the port
    os.path.exists = lambda p: True if str(p).endswith("earn_grant.json") else _real_exists(p)

    # --- outside the daemon -------------------------------------------------
    W._self_eval["persist"] = False
    W.highway_may_act = lambda: True                              # even in a tree that may act
    r = W.tend_seal_service()
    check("A370.1 outside the daemon the seal service is NOT started", r.startswith("not started") and not popen, r)
    r = W.tend_earn_service(port=1)
    check("A370.2 ...nor the earn service, with his grant present", r.startswith("not started") and not popen, r)
    r = W.tend_pending()
    check("A370.3 ...and nothing is mined: the node is not even asked", r.startswith("not mined") and not urlopen, r)

    # --- the daemon, in a tree that cannot relaunch its nodes ---------------
    W._self_eval["persist"] = True
    W.highway_may_act = lambda: False
    r = W.tend_seal_service()
    check("A370.4 the daemon in a staged copy or worktree starts nothing", r.startswith("not started")
          and "relaunch" in r and not popen, r)

    # --- the daemon in the production tree: the green path still works -----
    W.highway_may_act = lambda: True
    started = []
    subprocess.Popen = lambda *a, **k: started.append((a, k)) or None
    r = W.tend_seal_service()
    argv = started[0][0][0] if started else []
    check("A370.5 the daemon in a tree that can relaunch its nodes DOES start the seal service",
          r == "started" and len(started) == 1 and any(str(x).endswith("hidden_task.py") for x in argv)
          and "sentinel_witness/seal_service.py" in argv, r)
    started.clear()
    r = W.tend_earn_service(port=1)
    check("A370.6 ...and the earn service, with his grant present", r == "started" and len(started) == 1, r)
    subprocess.Popen = _popen_trip
    started.clear()

    # --- the shape that happened: test_watchdog_outage's passes, real tends ---
    # one_pass also READS the mesh (mycelium's topology, over urlopen); a read is not a remedy. Here every urlopen
    # fails offline as a URLError, the way an unreachable node does, and is recorded: none may be /mine, and the
    # pending tend must not have asked node A at all.
    import urllib.error
    urls = []

    def _url_offline(req, *a, **k):
        urls.append(str(getattr(req, "full_url", req)))
        raise urllib.error.URLError("A370: offline in this suite")

    urllib.request.urlopen = _url_offline
    # one_pass's balance check runs a read-only subprocess, as in test_watchdog_outage; only a SERVICE launch (the
    # hidden_task.py launcher every tend uses) trips here
    _real_popen = saved[0]

    def _popen_services_trip(cmd, *a, **k):
        if any(str(x).endswith("hidden_task.py") for x in (cmd if isinstance(cmd, (list, tuple)) else [cmd])):
            return _popen_trip(cmd)
        return _real_popen(cmd, *a, **k)

    subprocess.Popen = _popen_services_trip
    W._self_eval["persist"] = False
    W.highway_may_act = saved[3]
    _HW.run_once = lambda *a, **k: ([], [])
    _HW.sense = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("A244 tripwire"))
    W.start_node = lambda n: None
    W.log = lambda level, msg: None
    ok = {"warnings": [], "chain_height": 9, "peers": 1, "version": "v8.40", "judge": "quorum(x)"}
    one_down = lambda port, timeout=8: ((None, "refused") if port == W.NODES[0]["port"] else (dict(ok), None))
    W.health = one_down
    results = []
    real = (W.tend_seal_service, W.tend_earn_service, W.tend_pending)
    W.tend_seal_service = lambda: results.append(real[0]()) or results[-1]
    W.tend_earn_service = lambda: results.append(real[1](port=1)) or results[-1]
    W.tend_pending = lambda: results.append(real[2]()) or results[-1]
    W._fail_counts = {n["id"]: 0 for n in W.NODES}
    for _ in range(6):
        W.one_pass()
    W.tend_seal_service, W.tend_earn_service, W.tend_pending = real
    check("A370.7 six outage-suite passes with the REAL tends start no process and mine nothing",
          len(results) == 18 and not popen and not any("/mine" in u for u in urls)
          and all(x.startswith(("not started", "not mined")) for x in results),
          "%d tends, %d Popen, reads %s" % (len(results), len(popen), sorted({u.split('/')[-1] for u in urls})))
finally:
    (subprocess.Popen, urllib.request.urlopen, W._port_listening, W.highway_may_act, se, W.health, W.start_node,
     W.log, _HW.run_once, _HW.sense, os.path.exists) = saved
    W._self_eval.clear()
    W._self_eval.update(se)

print()
if FAILS:
    print("%d FAILED:" % len(FAILS))
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("A370 ONLY THE DAEMON TENDS: %d/%d passed (no service started, nothing mined; reads failed offline)"
      % (len(RAN), len(RAN)))
