#!/usr/bin/env python3
"""
A421 / PG1 -- the peer and bridge listeners took any caller on any network.

THE HAZARD. COVENANT_API_HOST (2026-09-12) put the phone's HTTP API on loopback
and said of the rest: "Peers still reach 5001". Read on the phone 2026-11-11
(adb, from the laptop; and from a second machine with no credentials): the API
port refuses, the peer port and the bridge port accept a connection from
wherever it comes. The node binds 0.0.0.0, so that is every network the phone
joins, and _accept_loop hands each caller's bytes straight to the handler.

THE REPAIR. COVENANT_PEER_CALLERS=tailnet: the accept loop closes a caller that
tailnet_ok refuses (not loopback, not 100.64.0.0/10) before a byte is read, and
records it as <label>_caller_refused. Unset, nothing changes: every node that
peers over a LAN today keeps doing so.

WHY THESE CHECKS ARE BEHAVIOURAL. Each runs the real _accept_loop. The callers
are scripted through a listening socket whose accept() returns them, because one
machine cannot dial itself from a public address; G8 then does it with real
sockets where the host has the addresses for it, and says SKIP where it does
not. Nothing here reads the source of covenant_unified_v8.py.

CHECKS (~3 s, no node):
  G1  the setting: unset and the off words are open, "tailnet" gates, and a
      value nobody recognises gates too (a typo must not open the door)
  G2  DEFAULT UNCHANGED: unset, LAN, public and tailnet callers all reach the
      handler and nothing is recorded
  G3  PASSING CASE: gated, loopback and tailnet callers reach the handler
  G4  REJECTED CASE: gated, LAN, public, the two addresses either side of the
      /10 and an unparseable caller never reach the handler; each is closed
      unread and recorded with its address
  G5  the bridge listener is gated by the same loop, under its own label
  G6  the loop outlives a refusal: a tailnet caller behind three refused ones
      is still served
  G7  a close() that fails on a refused caller is recorded, not swallowed
  G8  real sockets: gated, a loopback client is served; a client arriving from
      this host's own LAN address is closed without being served
  M1  MUTATION: tailnet_ok forced True and the LAN caller is served -- G4's
      refusals come from the guard and nothing else
  M2  MUTATION: tailnet_ok forced False and the gated loopback caller is
      refused, while the ungated one is still served -- unset never asks it
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

ENV = "COVENANT_PEER_CALLERS"
LOOPBACK, TAILNET = "127.0.0.1", "100.72.0.10"
OUTSIDE = ["192.168.1.50", "10.77.0.12", "203.0.113.7", "100.63.255.255", "100.128.0.1", "bogus"]

results, skipped = [], []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    detail = "" if detail == "" or detail is None else str(detail)[:110]
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, ("  -- " + detail) if detail else ""))


def skip(label, why):
    skipped.append(label)
    print("  [SKIP] %s  -- %s" % (label, why))


class Recorder:
    """Stands in for SpikingAnomalyMonitor: the same record(kind, detail)."""

    def __init__(self):
        self.events, self._lock = [], threading.Lock()

    def record(self, kind, detail=""):
        with self._lock:
            self.events.append((kind, detail))

    def details(self, kind):
        with self._lock:
            return [d for k, d in self.events if k == kind]


class FakeNode:
    def __init__(self):
        self.running, self.anomaly_monitor = True, Recorder()


class FakeMaster:
    """Only what _accept_loop touches."""

    def __init__(self):
        self.node = FakeNode()


class Conn:
    def __init__(self, fail_close=False):
        self.closed, self.reads, self.fail_close = False, 0, fail_close

    def recv(self, n):
        self.reads += 1
        return b""

    def close(self):
        if self.fail_close:
            raise OSError("close failed")
        self.closed = True


class ScriptedListener:
    """accept() returns the scripted callers in order, then ends the loop the way a stopping node does."""

    def __init__(self, node, callers):
        self.node, self.callers = node, list(callers)

    def accept(self):
        if self.callers:
            return self.callers.pop(0)
        self.node.running = False
        raise OSError("listener closed")


class setting:
    """COVENANT_PEER_CALLERS set to `value` (None: unset) for the block, then put back."""

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.old = os.environ.get(ENV)
        if self.value is None:
            os.environ.pop(ENV, None)
        else:
            os.environ[ENV] = self.value

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop(ENV, None)
        else:
            os.environ[ENV] = self.old


def wait_for(fn, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if fn():
            return True
        time.sleep(0.02)
    return bool(fn())


def run_loop(addrs, value, label="peer", fail_close=False):
    """The real _accept_loop over scripted callers. Returns (addresses served, monitor, the connections)."""
    m, served = FakeMaster(), []
    conns = [Conn(fail_close) for _ in addrs]
    callers = [(c, (a, 40000 + i)) for i, (c, a) in enumerate(zip(conns, addrs))]
    with setting(value):
        cov.CovenantUnifiedMaster._accept_loop(
            m, ScriptedListener(m.node, callers), lambda conn, addr: served.append(addr[0]), label)
    time.sleep(0.25)                    # the handlers run on a pool: let a wrongly served caller show up
    return sorted(served), m.node.anomaly_monitor, conns


def real_loop(bind_addr, value):
    """The real _accept_loop on a real listener bound to `bind_addr`; one client connects from that address.
    Returns (served, refused, what the client read: b'' or 'reset' when closed on it, None when left open)."""
    m, served = FakeMaster(), []
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((bind_addr, 0))
    s.listen(4)
    with setting(value):
        t = threading.Thread(target=cov.CovenantUnifiedMaster._accept_loop,
                             args=(m, s, lambda conn, addr: (served.append(addr[0]), conn.close()), "peer"),
                             daemon=True)
        t.start()
        time.sleep(0.2)                 # the loop reads the setting as it starts
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.settimeout(3)
    try:
        c.connect((bind_addr, s.getsockname()[1]))
        try:
            got = c.recv(1)
        except socket.timeout:
            got = None
        except OSError:
            got = "reset"
    finally:
        c.close()
    wait_for(lambda: served or m.node.anomaly_monitor.details("peer_caller_refused"), 2)
    m.node.running = False
    s.close()
    t.join(3)
    return served, m.node.anomaly_monitor.details("peer_caller_refused"), got


def lan_address():
    """One of this host's own IPv4 addresses that is neither loopback nor tailnet, or None."""
    found = []
    try:
        found += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    try:
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.connect(("192.0.2.1", 9))     # sends nothing: asks the OS which address it would use
        found.append(u.getsockname()[0])
        u.close()
    except OSError:
        pass
    for a in found:
        if not cov.tailnet_ok(a) and not a.startswith("0."):
            return a
    return None


def main():
    print("A421 / PG1 -- the peer and bridge listeners can be limited to loopback and tailnet callers\n")

    if not hasattr(cov, "peer_callers_gated"):
        check("PG1 the gate exists", False, "peer_callers_gated is not in covenant_unified_v8")
        print("\n0 of 1")
        return 1

    # ---- G1: the setting -------------------------------------------------
    def gated(value):
        with setting(value):
            return cov.peer_callers_gated()

    still_open = [v for v in (None, "", "  ", "any", "ALL", "off", "0") if gated(v)]
    not_gated = [v for v in ("tailnet", " Tailnet ", "TAILNET") if not gated(v)]
    typo_open = [v for v in ("tailnett", "yes", "1", "loopback") if not gated(v)]
    check("G1 unset and the off words leave the listeners open", not still_open, f"gated {still_open}")
    check("G1 'tailnet' gates, whatever its case or padding", not not_gated, f"open {not_gated}")
    check("G1 a value nobody recognises gates rather than opens", not typo_open, f"open {typo_open}")

    # ---- G2: default unchanged -------------------------------------------
    everyone = [LOOPBACK, TAILNET] + OUTSIDE
    served, mon, _ = run_loop(everyone, None)
    check("G2 unset: every caller reaches the handler, as before", served == sorted(everyone),
          f"served {len(served)} of {len(everyone)}")
    check("G2 unset: nothing is recorded", not mon.events, mon.events[:2])

    # ---- G3: passing case ------------------------------------------------
    served, mon, _ = run_loop([LOOPBACK, TAILNET, "::1"], "tailnet")
    check("G3 gated: loopback and tailnet callers reach the handler",
          served == sorted([LOOPBACK, TAILNET, "::1"]), served)
    check("G3 gated: none of them is recorded as refused", not mon.events, mon.events[:2])

    # ---- G4: rejected case -----------------------------------------------
    served, mon, conns = run_loop(OUTSIDE, "tailnet")
    check("G4 gated: LAN, public, boundary and junk callers never reach the handler", served == [], served)
    check("G4 each is recorded with its address",
          sorted(mon.details("peer_caller_refused")) == sorted(OUTSIDE), mon.details("peer_caller_refused"))
    check("G4 each is closed", all(c.closed for c in conns), [c.closed for c in conns])
    check("G4 not a byte of any is read", not any(c.reads for c in conns), [c.reads for c in conns])

    # ---- G5: the bridge --------------------------------------------------
    served, mon, _ = run_loop(["192.168.1.50", TAILNET], "tailnet", label="bridge")
    check("G5 the bridge listener is gated under its own label",
          served == [TAILNET] and mon.details("bridge_caller_refused") == ["192.168.1.50"]
          and not mon.details("peer_caller_refused"), (served, mon.events))

    # ---- G6: the loop survives -------------------------------------------
    served, mon, _ = run_loop(["203.0.113.7", "203.0.113.8", "10.77.0.12", TAILNET], "tailnet")
    check("G6 a tailnet caller behind three refused ones is still served",
          served == [TAILNET] and len(mon.details("peer_caller_refused")) == 3, (served, len(mon.events)))

    # ---- G7: a failed close is not swallowed -----------------------------
    served, mon, _ = run_loop(["203.0.113.7"], "tailnet", fail_close=True)
    check("G7 a close() that fails on a refused caller is recorded",
          served == [] and len(mon.details("peer_close_error")) == 1, mon.events)

    # ---- G8: real sockets ------------------------------------------------
    served, refused, _ = real_loop(LOOPBACK, "tailnet")
    check("G8 real socket, gated: a loopback client is served", served == [LOOPBACK] and not refused,
          (len(served), len(refused)))
    lan = lan_address()
    if lan is None:
        skip("G8 real socket, gated: a client from this host's LAN address is closed unserved",
             "this host has no address outside loopback and the tailnet")
    else:
        served, refused, got = real_loop(lan, "tailnet")
        check("G8 real socket, gated: a client from this host's LAN address is closed unserved",
              served == [] and refused == [lan] and got in (b"", "reset"),
              (len(served), len(refused), "closed" if got in (b"", "reset") else "left open"))
        served, refused, _ = real_loop(lan, None)
        check("G8 real socket, unset: the same client is served, as before", served == [lan] and not refused,
              (len(served), len(refused)))

    # ---- M1 / M2: the guard, flipped both ways ---------------------------
    real = cov.tailnet_ok
    try:
        cov.tailnet_ok = lambda addr: True
        served, mon, _ = run_loop(["192.168.1.50"], "tailnet")
        check("M1 MUTATION: tailnet_ok forced True and the LAN caller is served",
              served == ["192.168.1.50"] and not mon.events, (served, mon.events))
        cov.tailnet_ok = lambda addr: False
        served, mon, _ = run_loop([LOOPBACK], "tailnet")
        check("M2 MUTATION: tailnet_ok forced False and the gated loopback caller is refused",
              served == [] and mon.details("peer_caller_refused") == [LOOPBACK], (served, mon.events))
        served, mon, _ = run_loop([LOOPBACK], None)
        check("M2 ... while unset never asks it: the caller is served", served == [LOOPBACK] and not mon.events,
              (served, mon.events))
    finally:
        cov.tailnet_ok = real

    passed = sum(1 for _, ok in results if ok)
    # The last line is what covenant_one's TALLY pattern reads. "20 of 20" was not one it knows,
    # and the runner said so the only way it can: NO RESULT.
    print("\nPG1: %d/%d passed%s" % (passed, len(results), (", %d skipped" % len(skipped)) if skipped else ""))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
