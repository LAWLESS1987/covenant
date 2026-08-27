#!/usr/bin/env python3
"""A22 (2026-08-23): the topology stream reaches the thing that acts.

WHY
---
`/mycelium` reports the node's real peer table and each link's conductance. It
was exposed on a route and read by NOTHING -- the same shape `/anomalies` had
twelve hours earlier. It is also the only place the node says WHO IT IS TALKING
TO, which makes it where a bad actor becomes visible.

`POST /peers` is operator-authenticated (P1 below asserts that, so the control
cannot quietly regress), which is what makes an unexpected peer worth an alert
rather than a shrug: it did not arrive by accident.

Also covers two defects found in this loop's OWN code from ninety minutes
earlier, while reviewing the peer-input surface A20/A21 added:

  T8  the peer table refused newcomers when full, so anything that could reach
      the node from enough sources could fill it and then permanently suppress
      the A7 split-source warning -- an attacker turning OFF a signal. Now
      evicts the oldest.
  T9  `peer_version_mismatch` was recorded on EVERY observation, i.e. once per
      heartbeat per differing peer for ever: a permanent condition transmitted
      at full rate inside a bounded anomaly buffer, crowding out the phasic
      events the buffer exists to keep. The exact failure this same night's work
      fixed one layer up. Now recorded on change.

CHECKS
  P1        POST /peers is in PROTECTED_OPERATOR_ENDPOINTS and the hook enforces
            it -- the control asserted, not described
  P2        the route comment no longer denies the control it sits on
  M1-M10    topology_report: unexpected peers, floored conductance, height and
            uptime regressions, and junk input
  T8-T9     the two fixes above
  L1-L3     /mycelium on a live node has the shape the report expects
"""
import atexit, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "covenant_unified_v8.py")
ENV = dict(os.environ, COVENANT_INSECURE_MOCK_JUDGE="1",
           COVENANT_JUDGE_PROVIDERS="mock")

import covenant_unified_v8 as cov

TMP = tempfile.mkdtemp(prefix="covtest_a22_")
SPAWNED, results = [], []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def stop(p, timeout=10):
    if p is None or p.poll() is not None:
        return
    try:
        p.terminate(); p.wait(timeout=timeout)
    except Exception:
        try:
            p.kill(); p.wait(timeout=5)
        except Exception:
            pass


def _reap():
    for p in SPAWNED:
        stop(p, timeout=5)
    shutil.rmtree(TMP, ignore_errors=True)


atexit.register(_reap)


def pick_base(span=14):
    for base in range(24200, 25800, 100):
        for off in range(span):
            s = socket.socket()
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                s.bind(("127.0.0.1", base + off))
            except OSError:
                s.close(); break
            s.close()
        else:
            return base
    raise SystemExit("no free port block")


# ------------------------------------------------------- the control ------
def control_checks():
    check("P1 POST /peers is an operator-protected endpoint",
          ("POST", "/peers") in cov.PROTECTED_OPERATOR_ENDPOINTS,
          str(sorted(cov.PROTECTED_OPERATOR_ENDPOINTS)))

    src = open(SRC, encoding="utf-8").read()
    i = src.find('@self.app.route("/peers", methods=["POST"])')
    seg = src[i:i + 2200] if i > 0 else ""
    check("P1b the auth hook covers it by membership, not a per-route decorator",
          "if (request.method, request.path) not in PROTECTED_OPERATOR_ENDPOINTS"
          in src)
    # First version of this check searched for the ABSENCE of the old wording.
    # That is a proxy, not the claim, and it failed on correct code: the
    # correction note quotes the wrong sentence in order to record what was
    # wrong, which is the right thing for it to do. The claim is that the
    # comment now STATES the control and marks the old text as quoted history.
    phrase = "anyone can register a peer"
    at = seg.find(phrase)
    quoted = at > 0 and "It said" in seg[:at]
    check("P2 the route comment now states the control instead of denying it",
          i > 0 and "PROTECTED_OPERATOR_ENDPOINTS" in seg
          and "fails CLOSED" in seg
          and (at < 0 or quoted),
          "old wording is asserted, not quoted" if at > 0 and not quoted
          else "corrected, with the old wording kept as quoted history")


# ---------------------------------------------------- topology report -----
def topo(links, height=5, uptime=100.0):
    return {"node_id": "A", "peer_count": len(links), "links": links,
            "chain_height": height, "uptime_seconds": uptime}


def link(host="127.0.0.1", port=5021, pid="p1", cond=0.5):
    return {"peer_id": pid, "host": host, "port": port, "conductance": cond}


def report_checks(wd):
    EXP = {"127.0.0.1:5021"}

    a, i, st = wd.topology_report("A", topo([link()]), {}, EXP)
    check("M1 a configured peer at expected conductance is quiet",
          a == [] and i == [], f"{a} {i}")

    a, i, _ = wd.topology_report(
        "A", topo([link(), link(host="10.0.0.9", port=9999, pid="ghost")]), {}, EXP)
    check("M2 an UNEXPECTED peer is an alert naming it and the expected set",
          len(a) == 1 and "ghost" in a[0] and "10.0.0.9:9999" in a[0]
          and "127.0.0.1:5021" in a[0] and "operator signature" in a[0], str(a))

    a, i, _ = wd.topology_report("A", topo([]), {}, EXP)
    check("M3 a configured peer MISSING from the table is info, not an alert",
          a == [] and len(i) == 1 and "not holding configured peer" in i[0],
          f"{a} {i}")

    a, i, _ = wd.topology_report("A", topo([link(cond=0.05)]), {}, EXP)
    check("M4 every link at the conductance floor is the A11 signature -> alert",
          any("conductance floor" in x and "A11" in x for x in a), str(a))

    a, i, _ = wd.topology_report(
        "A", topo([link(cond=0.05), link(port=5031, pid="p2", cond=0.5)]),
        {}, EXP | {"127.0.0.1:5031"})
    check("M5 SOME links floored is not the signature -- no alert",
          not any("conductance floor" in x for x in a), str(a))

    prev = {"height": 9, "uptime": 500.0, "addrs": ["127.0.0.1:5021"]}
    a, i, _ = wd.topology_report("A", topo([link()], height=7, uptime=600.0),
                                 prev, EXP)
    check("M6 a chain that SHORTENS is a loud alert with both heights",
          any("WENT BACKWARDS" in x and "9 -> 7" in x and "Do not transact" in x
              for x in a), str(a))

    a1, _, _ = wd.topology_report("A", topo([link()], height=9, uptime=12.0),
                                  prev, EXP)
    a2, _, _ = wd.topology_report("A", topo([link()], height=9, uptime=13.0),
                                  {"height": 9, "uptime": 12.0,
                                   "addrs": ["127.0.0.1:5021"]}, EXP)
    check("M7 a silent restart alerts once, with text stable enough to CLEAR",
          any("restarted since the last check" in x for x in a1)
          and not any("restarted" in x for x in a2), f"{a1} | {a2}")

    a, i, _ = wd.topology_report(
        "A", topo([link()]),
        {"height": 5, "uptime": 50.0,
         "addrs": ["127.0.0.1:5021", "127.0.0.1:5031"]},
        EXP | {"127.0.0.1:5031"})
    check("M8 a configured peer DROPPED from the table is reported",
          any("dropped configured peer" in x for x in i), str(i))

    for junk in (None, "nope", {}, {"links": "not-a-list"},
                 {"links": [None, 3, {"host": None}]},
                 {"links": [{"host": "h", "port": 1, "conductance": True}]}):
        try:
            wd.topology_report("A", junk, {}, EXP)
        except Exception as e:
            check("M9 junk from /mycelium cannot crash the watchdog", False,
                  f"{junk!r} -> {type(e).__name__}: {e}")
            break
    else:
        check("M9 junk from /mycelium cannot crash the watchdog", True)

    a, i, _ = wd.topology_report("A", topo([link()], height=5, uptime=10.0),
                                 {}, EXP)
    check("M10 the first round cannot produce a regression alert",
          not any("BACKWARDS" in x or "restarted" in x for x in a), str(a))


# --------------------------------------------- the two self-inflicted -----
def selffix_checks():
    T = cov.PeerStateTable

    t = T()
    for i in range(T.MAX_PEERS_TRACKED):
        t.observe(f"flood{i}", {"src": "f" * 12})
        t._rows[f"flood{i}"]["seen"] = 1000.0 + i
    t.observe("real-peer", {"src": "abcabcabcabc", "height": 3})
    snap = t.snapshot()
    check("T8 a full table EVICTS the oldest rather than locking a peer out",
          "real-peer" in snap and len(snap) == T.MAX_PEERS_TRACKED
          and "flood0" not in snap,
          f"tracked={len(snap)} real-peer={'real-peer' in snap} "
          f"oldest-evicted={'flood0' not in snap}")

    class Mon:
        def __init__(self): self.rec = []
        def record(self, k, d): self.rec.append((k, d))

    m = Mon()
    t2 = T()
    for _ in range(10):
        t2.observe("p:1", {"v": "v8.30", "src": "0b04473b7cbd"},
                   monitor=m, own_src="773cb7d7adef")
    check("T9 a differing peer records the mismatch ONCE, not per heartbeat",
          len(m.rec) == 1, f"{len(m.rec)} records from 10 observations")

    t2.observe("p:1", {"v": "v8.31", "src": "4b7e0a0f6b74"},
               monitor=m, own_src="773cb7d7adef")
    check("T9b but a peer that CHANGES source records again",
          len(m.rec) == 2, f"{len(m.rec)} records")

    m2 = Mon()
    t3 = T()
    for _ in range(5):
        t3.observe("q:1", {"v": "v8.34", "src": "773cb7d7adef"},
                   monitor=m2, own_src="773cb7d7adef")
    check("T9c a peer on OUR source still records nothing at all",
          m2.rec == [], str(m2.rec))


# ------------------------------------------------------------ live -------
def live_checks():
    base = pick_base()
    p = subprocess.Popen([sys.executable, SRC, "--port", str(base),
                          "--node-id", "T"],
                         env=dict(ENV, COVENANT_DB_PATH=os.path.join(TMP, "t.db"),
                                  PYTHONUNBUFFERED="1"),
                         cwd=TMP, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    SPAWNED.append(p)
    try:
        t0 = time.time()
        up = False
        while time.time() - t0 < 40:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{base}/health", timeout=2)
                up = True
                break
            except urllib.error.HTTPError:
                up = True
                break
            except Exception:
                time.sleep(0.5)
        check("L1 node came up", up)
        with urllib.request.urlopen(f"http://127.0.0.1:{base}/mycelium",
                                    timeout=10) as r:
            topo_live = json.loads(r.read().decode())
        check("L2 /mycelium has the fields topology_report reads",
              set(topo_live) >= {"node_id", "peer_count", "links",
                                 "chain_height", "uptime_seconds"},
              str(sorted(topo_live)))
        import covenant_watchdog as wd
        a, i, st = wd.topology_report("T", topo_live, {}, set())
        check("L3 a real reading produces a clean state with no false alarm",
              a == [] and st.get("height") == topo_live["chain_height"],
              f"{a} {st}")
    finally:
        stop(p)


def main():
    print(f"source under test: {SRC}")
    try:
        import covenant_watchdog as wd
    except Exception as e:
        check("W0 watchdog importable", False, f"{type(e).__name__}: {e}")
        wd = None
    if wd is None or not hasattr(wd, "topology_report"):
        check("W0 watchdog carries the topology reader", False,
              "pre-A22 watchdog: no topology_report")
        print("\n=== PRE-FIX RECORD: /mycelium has no internal consumer ===")
    else:
        check("W0 watchdog carries the topology reader", True)
        control_checks()
        report_checks(wd)
        selffix_checks()
        live_checks()
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n{ok}/{len(results)} passed")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
