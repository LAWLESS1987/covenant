#!/usr/bin/env python3
"""
A77 -- the listener's bind() could fail in total silence, leaving a node that
looks healthy and is deaf.

THE HAZARD. _accept_loop was hardened at the 1000-node scale test with an
explicit finding, quoted from its own docstring: a dead listener thread leaves a
node that "stayed up, kept serving HTTP, kept reporting a healthy chain -- and
was permanently deaf to every peer from that moment on, with nothing recorded
anywhere". That fix was applied to accept(). bind() and listen(), the two calls
one line above that decide whether the listener exists AT ALL, stayed bare.

MEASURED, not hypothetical. w2_w2off.err, 2026-09-09 02:12, untracked in the
repo root:

    Exception in thread Thread-2 (_listen_for_peers):
      File "covenant_unified_v8.py", line 8714, in _listen_for_peers
        s.bind((self.node.host, self.node.port))
    OSError: [WinError 10048] Only one usage of each socket address ...

A traceback on stderr into a file nobody reads, and the node carried on. The
monitor could not have helped: SpikingAnomalyMonitor says so itself -- "it
cannot detect anything nobody calls record() for" -- and nothing called it here.

A19 makes this the COMMON case on the platform that runs this node, by design:
SO_EXCLUSIVEADDRUSE exists to REFUSE a port another process holds rather than
silently share it. Being correct at the socket layer and then dropping the
result on the floor is the worst of both.

WHY THESE CHECKS ARE BEHAVIOURAL. Every one of them occupies a real port and
runs the real method. None reads the source of covenant_unified_v8.py or
asserts on a string in it -- that is the fake-guard shape the 2026-09-09
mutation audit found in 35 of 36 suites, and this file was written after it.
Delete the try/except in _bind_and_serve and P2 through P5 go red.

A81 EXTENDS IT TO THE OTHER TWO THREADS THAT DIE IN SILENCE. A77 hardened ONE
of the six thread targets CovenantUnifiedMaster.run() starts. Two more mattered:

  * `_integrity_monitor_loop` had no exception handling at all, and what kills
    it is the very thing it exists to detect. A genesis whose `message` is not
    a string raises on `.encode`; one whose `data` is null raises on `.get` a
    line earlier. Measured by construction with a real signed and mined genesis
    adopted through the real load_canonical_genesis: message=12345 left the
    thread DEAD, crisis_mode False, and the anomaly monitor holding zero
    events, while the same tamper carrying a STRING was caught correctly. The
    guard has real value and one input type switched it off silently.
  * the HTTP API thread was bare. Whatever the WSGI backend raises -- both
    waitress and werkzeug bind inside run() -- killed it, and the node carried
    on mining and gossiping with no /health, no /sync, no succession endpoints
    and no watchdog view. A node invisible to the watchdog is reported as
    unreachable, which is indistinguishable from one that is down: the single
    failure that removes the ability to SAY anything was the one nothing said.

CHECKS (~10 s, real sockets, no node):
  P1  the port is genuinely un-bindable while occupied (the premise itself,
      because a test whose setup silently fails would pass by construction)
  P2  a failed bind is RECORDED as <label>_bind_error, naming the port and
      the attempt number -- pre-fix: nothing, anywhere
  P3  the thread SURVIVES the failure and keeps retrying -- pre-fix: gone
  P4  when the port frees it BINDS and enters the accept loop: recovery,
      not merely a louder death
  P5  the recovery is recorded as <label>_bind_recovered with the count
  P6  the clean path is unchanged: free port, bound first try, accept loop
      entered, and ZERO anomalies recorded
  P7  the refactor kept the port arithmetic: peers on node.port, bridge on
      node.port + 10
  P8  a genesis message that is not a string does not raise out of the
      integrity check, and "could not be compared" is RECORDED rather than
      read as "no tamper" -- cannot-tell is not clean
  P8c an honest genesis records nothing: a guard that alerts on everything
      is the same as one that alerts on nothing
  P8d a check that throws does not END the monitor; it runs again, and every
      failure is recorded
  P9  an HTTP API that cannot start is recorded and retried, not lost, and
      the clean path still records nothing
"""
import os
import socket
import sys
import threading
import time

os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_SKIP_PREFLIGHT", "1")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    tag = "PASS" if ok else "FAIL"
    # str(), because a check that CRASHES on its own failure message reports
    # nothing at all -- which is this file's whole subject, one level up.
    detail = "" if detail == "" or detail is None else str(detail)[:110]
    print("  [%s] %s%s" % (tag, label, ("  -- " + detail) if detail else ""))


class Recorder:
    """Stands in for SpikingAnomalyMonitor: the same record(kind, detail)."""

    def __init__(self):
        self.events, self._lock = [], threading.Lock()

    def record(self, kind, detail=""):
        with self._lock:
            self.events.append((kind, detail))

    def count(self, kind):
        with self._lock:
            return sum(1 for k, _ in self.events if k == kind)

    def detail_for(self, kind):
        with self._lock:
            for k, d in self.events:
                if k == kind:
                    return d
        return ""


class FakeNode:
    def __init__(self, port):
        self.host, self.port, self.running = "127.0.0.1", port, True
        self.anomaly_monitor = Recorder()


class FakeMaster:
    """Only what _bind_and_serve touches. _accept_loop is a stub that signals
    it was reached and then blocks, exactly as the real one blocks in accept()."""

    def __init__(self, port):
        self.node = FakeNode(port)
        self.entered = threading.Event()
        self.release = threading.Event()
        self.bound_port = None

    def _accept_loop(self, sock, handler, label):
        self.bound_port = sock.getsockname()[1]
        self.entered.set()
        self.release.wait(10)
        try:
            sock.close()
        except OSError:
            pass

    def _handle_peer(self, conn, addr):
        pass

    def _handle_bridge(self, conn, addr):
        pass


def serve(master, port, label="peer"):
    t = threading.Thread(
        target=cov.CovenantUnifiedMaster._bind_and_serve,
        args=(master, port, master._handle_peer, label), daemon=True)
    t.start()
    return t


def wait_for(fn, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if fn():
            return True
        time.sleep(0.05)
    return bool(fn())


def main():
    print("A77 -- listener bind failure must be recorded and survivable\n")

    if not hasattr(cov.CovenantUnifiedMaster, "_bind_and_serve"):
        check("A77 _bind_and_serve exists", False, "the fix is not present")
        print("\n0 of 1")
        return 1

    occupier = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupier.bind(("127.0.0.1", 0))
    occupier.listen(4)
    port = occupier.getsockname()[1]

    # P1 -- the premise. If a second exclusive bind SUCCEEDS here then this
    # machine cannot host the hazard at all, and every check below would pass
    # for the wrong reason. Say so rather than reporting green.
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cov._bind_exclusive(probe)
    try:
        probe.bind(("127.0.0.1", port))
        premise, why = False, "second bind SUCCEEDED; port is shareable here"
    except OSError as e:
        premise, why = True, "%s: %s" % (type(e).__name__, e)
    finally:
        try:
            probe.close()
        except OSError:
            pass
    check("P1 an occupied port really refuses a second exclusive bind",
          premise, why[:80])
    if not premise:
        occupier.close()
        print("\nnot runnable on this host")
        return 1

    m = FakeMaster(port)
    serve(m, port)
    mon = m.node.anomaly_monitor

    got = wait_for(lambda: mon.count("peer_bind_error") >= 1, 4)
    d = mon.detail_for("peer_bind_error")
    check("P2 a failed bind is recorded as peer_bind_error", got, d[:70])
    check("P2b the record names the port and the attempt",
          str(port) in d and "attempt 1" in d, d[:70])

    again = wait_for(lambda: mon.count("peer_bind_error") >= 2, 4)
    check("P3 the thread SURVIVES the failure and retries",
          again, "%d attempts recorded" % mon.count("peer_bind_error"))

    occupier.close()
    up = wait_for(lambda: m.entered.is_set(), 45)
    check("P4 once the port frees it binds and enters the accept loop",
          up, "bound_port=%s" % m.bound_port)
    check("P4b it bound the port it was asked for",
          m.bound_port == port, "%s vs %s" % (m.bound_port, port))
    check("P5 recovery is recorded once, naming the failed-attempt count",
          mon.count("peer_bind_recovered") == 1
          and "attempt" in mon.detail_for("peer_bind_recovered"),
          mon.detail_for("peer_bind_recovered")[:70])
    m.node.running = False
    m.release.set()

    free = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free.bind(("127.0.0.1", 0))
    free_port = free.getsockname()[1]
    free.close()
    m2 = FakeMaster(free_port)
    serve(m2, free_port)
    ok2 = wait_for(lambda: m2.entered.is_set(), 5)
    check("P6 a free port binds first try and enters the accept loop",
          ok2, "bound_port=%s" % m2.bound_port)
    check("P6b nothing is recorded on the clean path",
          m2.node.anomaly_monitor.events == [],
          str(m2.node.anomaly_monitor.events)[:70])
    m2.node.running = False
    m2.release.set()

    seen = {}

    class PortSpy(FakeMaster):
        def _bind_and_serve(self, bind_port, handler, label):
            seen[label] = bind_port

    spy = PortSpy(6001)
    cov.CovenantUnifiedMaster._listen_for_peers(spy)
    cov.CovenantUnifiedMaster._listen_for_bridge(spy)
    check("P7 peers listen on node.port", seen.get("peer") == 6001, str(seen))
    check("P7b bridge listens on node.port + 10", seen.get("bridge") == 6011,
          str(seen))

    # ---- A81: the other two threads that could die in silence ----------
    #
    # A77 fixed ONE thread target. CovenantUnifiedMaster.run() starts six.
    # These are the two whose death is invisible and consequential: the
    # integrity monitor (killed by the very tamper it exists to detect) and
    # the HTTP API (whose loss removes every operator lever and the watchdog's
    # entire view of the node).
    class FakeChainNode:
        def __init__(self):
            self.chain_lock = threading.Lock()
            self.running = True
            self.crisis_mode, self.crisis_reason = False, ""
            self.anomaly_monitor = Recorder()
            self.governor = type("G", (), {"get_current": lambda _s: 1.0})()
            self.chain = []

    class Tx:
        def __init__(self, data):
            self.data = data

    class Blk:
        def __init__(self, txs):
            self.transactions = txs

    def integrity_master(msg):
        m = type("M", (), {})()
        m.node = FakeChainNode()
        m.node.chain = [Blk([Tx({"message": msg} if msg is not _NODATA else None)])]
        m._integrity_breach_count = 0
        return m

    _NODATA = object()

    # P8: a genesis message that is not a string used to raise AttributeError
    # out of the loop and kill the thread, leaving crisis_mode False and the
    # anomaly monitor empty -- the check silently stopped checking.
    for _label, _msg in (("an int", 12345), ("null data", _NODATA)):
        _m = integrity_master(_msg)
        try:
            cov.CovenantUnifiedMaster._integrity_check_once(_m)
            _raised = None
        except Exception as _e:                                   # noqa: BLE001
            _raised = "%s: %s" % (type(_e).__name__, _e)
        check("P8 a genesis whose message is %s does not raise out of the "
              "integrity check" % _label, _raised is None, _raised)
        check("P8b ...and 'could not be compared' is RECORDED, not read as "
              "'no tamper' (%s)" % _label,
              _m.node.anomaly_monitor.count("integrity_genesis_unreadable") == 1,
              _m.node.anomaly_monitor.events)

    # P8c: an honest genesis must still be silent -- a guard that alerts on
    # everything is the same as one that alerts on nothing.
    _ok = integrity_master(cov.CORE_COVENANT if hasattr(cov, "CORE_COVENANT") else "x")
    cov.CovenantUnifiedMaster._integrity_check_once(_ok)
    check("P8c a readable genesis records nothing (no false alarm)",
          _ok.node.anomaly_monitor.events == [], _ok.node.anomaly_monitor.events)

    # P8d: and the LOOP survives a check that throws for any other reason.
    _m = integrity_master("x")
    _calls = {"n": 0}

    def _boom_check(_self):
        _calls["n"] += 1
        if _calls["n"] >= 3:
            _self.node.running = False
        raise RuntimeError("planted")

    # The stub goes on the INSTANCE, not the class: _m is a stand-in, not a
    # CovenantUnifiedMaster, so `self._integrity_check_once()` resolves on the
    # object. Patching the class here left the real method unreachable, the
    # loop caught AttributeError every 10ms, and `running` was never cleared --
    # a test that hung instead of failing, which is its own small lesson.
    _m._integrity_check_once = lambda: _boom_check(_m)
    cov.CovenantUnifiedMaster._integrity_monitor_loop(_m, interval=0.01)
    check("P8d a check that throws does not end the monitor: it ran again and "
          "each failure is recorded",
          _calls["n"] >= 3
          and _m.node.anomaly_monitor.count("integrity_check_error") >= 3,
          "%d calls, %d recorded"
          % (_calls["n"], _m.node.anomaly_monitor.count("integrity_check_error")))

    # P9: the HTTP API was the third listener and A77 did not reach it.
    class FakeAPI:
        def __init__(self, fail_times):
            self.host, self.port = "127.0.0.1", 5999
            self.left = fail_times
            self.served = 0

        def run(self):
            if self.left > 0:
                self.left -= 1
                raise OSError("planted: address in use")
            self.served += 1

    _am = type("M", (), {})()
    _am.node = FakeChainNode()
    _am.api = FakeAPI(fail_times=2)
    cov.CovenantUnifiedMaster._serve_api(_am)
    check("P9 an HTTP API that cannot start is RECORDED rather than dying "
          "silently", _am.node.anomaly_monitor.count("api_serve_error") == 2,
          _am.node.anomaly_monitor.events)
    check("P9b ...and it retries until it serves, instead of leaving the node "
          "alive with no /health and no watchdog view",
          _am.api.served == 1, _am.api.served)
    _am2 = type("M", (), {})()
    _am2.node = FakeChainNode()
    _am2.api = FakeAPI(fail_times=0)
    cov.CovenantUnifiedMaster._serve_api(_am2)
    check("P9c the clean path records nothing and serves once",
          _am2.api.served == 1 and _am2.node.anomaly_monitor.events == [],
          _am2.node.anomaly_monitor.events)

    n = sum(1 for _, ok in results if ok)
    # "A77: n/m passed" rather than "n of m": covenant_one.TALLY reads the
    # former and reported the latter as "NO RESULT (no tally line)", scoring a
    # suite that had exited 0 as a failure. A suite the runner cannot read is
    # not measured, whatever its exit code says.
    print("\nA77: %d/%d passed" % (n, len(results)))
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
