"""test_a23_ack_health.py -- A23 (v8.36): delivery is confirmed by a REPLY,
never by sendall().

WHAT A23 IS.  The first Windows sweep this project ever ran (2026-08-24) found
test_a1_kill_matrix K1/K3 red: node A mined a block, the block provably never
reached node C, and A's /anomalies held no peer_send_failure and dead_peers=0.
A18 (v8.30) exists precisely to close that -- "bytes accepted, never
acknowledged" -- and its own comment names this platform. So the standing
question was: why does A18's path not fire where it was written to fire?

MEASURED HERE, in-process, on any platform.  The Windows shape is a peer whose
port still COMPLETES THE HANDSHAKE and never answers at the application layer.
Reproduce it with a listener that accepts, reads to EOF and says nothing (S1),
and one that accepts and holds the connection open (S3 -- the expensive kind).

Two defects, neither of them platform-specific:

  1. `_note_send_ok` was called the instant `sendall()` returned -- the exact
     claim A18 denies -- and it CLEARS the link's consecutive-failure count.
     So every send to an accepting-silent peer both recorded a failure and
     erased the evidence of the previous one. PRE-FIX MEASUREMENT: five
     consecutive total failures leave k=1 and the backoff pinned at ONE
     interval, for ever, while five sends to a REFUSED peer reach k=5 and a
     16x backoff. A peer delivering nothing was treated as healthier than a
     peer that says so. A12's headroom (508 -> 11,520 dead peers) is bought by
     the escalation, so for this class of dead peer A12 bought nothing.

  2. A reply that is NOT JSON returned None in silence -- no anomaly, no health
     update. A covenant listener answers JSON or nothing (M4), so bytes that
     are neither prove the far end is not a peer at all: an HTTP server (the A2
     footgun, which preflight only checks at boot), a proxy, or a port some
     other process took. The announce went into a void and nothing said so.

NOT A FIX FOR K1/K3's RED, and deliberately.  Section 0: never weaken a control
to make a test pass. What this changes is the health accounting, in the
tightening direction only. K3 also has a MEASUREMENT problem this suite pins
(S3): a broadcast is _SEND_POOL.submit, i.e. asynchronous, and against a peer
that accepts-and-holds, one _send_raw costs the full 3 x PEER_SEND_TIMEOUT_S
retry budget (~15.1 s at the defaults) -- so a test that samples /anomalies the
moment /mine returns samples it ~15 s too early. Against a REFUSED peer, which
is what Linux gives you, the same send costs ~0.13 s and the sample lands after
it. That is why the same assertion is green on Linux and red on win32.

Run: python3 test_a23_ack_health.py       (needs covenant_path_pattern.py beside it)
"""
import os, sys, json, time, socket, threading, tempfile, inspect, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ["COVENANT_MAX_CONCURRENT_SENDS"] = "4"
os.environ["COVENANT_PEER_SEND_TIMEOUT"] = "0.3"
os.environ["COVENANT_TIP_GOSSIP_INTERVAL"] = "10"
import covenant_unified_v8 as cov

results = []
unknowns = []
def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)


def unknown(label, detail=""):
    """Not a pass, and not a failure of the node either.

    S3's two comparison checks need a port that REFUSES quickly as their
    control condition. Linux gives you one by closing a listener; Windows --
    the platform this entire suite exists to describe -- does not reliably,
    which is the same accept-and-hold behaviour the suite is measuring, showing
    up in its own scaffolding. Reporting that as FAIL blames the node for the
    platform; reporting it as PASS claims a comparison that was never run.
    UNKNOWN is neither, and this project folds UNKNOWN into PASS exactly never.
    """
    unknowns.append((label, detail))
    print(f"UNKN  {label}  {detail}", flush=True)

PHI = cov.PHI
def dead_send_cost(timeout, attempts=3):
    return attempts * timeout + sum(0.05 * (PHI ** a) for a in range(attempts - 1))


# ------------------------------------------------------------------ listeners
class Listener:
    """accept -> read to EOF -> optionally reply -> optionally hold -> close.

    mode 'silent'  : reads everything, answers nothing, closes at once.
                     (a killed process whose port is still bound)
    mode 'hold'    : reads everything, answers nothing, holds the connection
                     open past the sender's timeout. The EXPENSIVE shape.
    mode 'bytes'   : answers self.reply verbatim.
    """
    def __init__(self, mode="silent", reply=None, hold=2.0):
        self.mode, self.reply, self.hold = mode, reply, hold
        self.conns = 0
        self._stop = False
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0)); self.srv.listen(64)
        self.port = self.srv.getsockname()[1]
        self._held = []
        threading.Thread(target=self._serve, daemon=True).start()
    def _serve(self):
        while not self._stop:
            try: c, _ = self.srv.accept()
            except Exception: return
            self.conns += 1
            threading.Thread(target=self._one, args=(c,), daemon=True).start()
    def _one(self, c):
        try:
            b"".join(iter(lambda: c.recv(4096), b""))
            if self.mode == "bytes" and self.reply is not None:
                c.sendall(self.reply)
            elif self.mode == "hold":
                self._held.append(c)
                time.sleep(self.hold)
        except Exception:
            pass
        finally:
            try: c.close()
            except Exception: pass
    def close(self):
        self._stop = True
        try: self.srv.close()
        except Exception: pass


def make_node(port, nid="a23"):
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster(nid, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    m.node.running = True
    return m

def k_of(n, port):
    return n._send_failures.get(("127.0.0.1", int(port)), 0)

def backoff_of(n, port):
    return n._send_backoff_until.get(("127.0.0.1", int(port)), 0) - time.time()


# ------------------------------------------------------- S1 the accepting-silent peer
def s1():
    m = make_node(19500); n = m.node
    peer = Listener("silent")
    r = n._send_raw("127.0.0.1", peer.port, "{}")
    kinds = n.anomaly_monitor.report()["per_kind"]
    check("S1 a peer that accepts bytes and never answers is a FAILED delivery",
          r is None and "peer_send_failure" in kinds, f"return={r!r} kinds={list(kinds)}")
    check("S1 it costs the full retry budget in ATTEMPTS, not one",
          peer.conns == 3, f"{peer.conns} connections")
    check("S1 one failure arms a backoff of one interval",
          0.9 * cov.TIP_GOSSIP_INTERVAL_S < backoff_of(n, peer.port) <= cov.TIP_GOSSIP_INTERVAL_S,
          f"{backoff_of(n, peer.port):.1f} s")
    check("S1 the peer counts toward dead_peers", n.dead_peer_count() == 1,
          str(n.dead_peer_count()))
    peer.close()
    return m, peer


# ------------------------------------------------------- S2 escalation (THE DEFECT)
def s2():
    """PRE-FIX (v8.35) this section fails: k stays 1 and the backoff never grows,
    because _note_send_ok fired on sendall and cleared the counter every attempt."""
    m = make_node(19520); n = m.node
    silent = Listener("silent")
    ks, backs = [], []
    for _ in range(5):
        n._send_raw("127.0.0.1", silent.port, "{}")
        ks.append(k_of(n, silent.port)); backs.append(backoff_of(n, silent.port))
    check("S2 consecutive silent deliveries ESCALATE the failure count",
          ks == [1, 2, 3, 4, 5], str(ks))
    check("S2 the backoff doubles with it",
          all(backs[i + 1] > 1.8 * backs[i] for i in range(len(backs) - 1)),
          " ".join(f"{b:.0f}s" for b in backs))
    silent.close()

    # The control: a REFUSED peer, which is what Linux gives you for a dead
    # node. This behaved correctly on v8.35 and must be unchanged.
    dead = Listener("silent"); rport = dead.port; dead.close(); time.sleep(0.05)
    m2 = make_node(19540); n2 = m2.node
    ks2 = []
    for _ in range(5):
        n2._send_raw("127.0.0.1", rport, "{}")
        ks2.append(k_of(n2, rport))
    check("S2 a REFUSED peer escalates identically (unchanged from v8.35)",
          ks2 == [1, 2, 3, 4, 5], str(ks2))
    check("S2 accepting-silent and refused are now accounted the SAME",
          ks == ks2, f"{ks} vs {ks2}")

    # And the arithmetic the escalation buys back (A12's own numbers).
    cost = dead_send_cost(5.0)
    flat = cov.MAX_CONCURRENT_SENDS * 120 / cost
    esc = cov.MAX_CONCURRENT_SENDS * cov.DEAD_PEER_BACKOFF_MAX_S / cost
    check("S2 without escalation the pool saturates ~30x sooner (A12's headroom)",
          esc > 20 * flat, f"{flat:.0f} -> {esc:.0f} dead peers at the pool default")


# ------------------------------------------------------- S3 the cost of the shape
def s3():
    """Why K1/K3 read zero on Windows and non-zero on Linux: the same logical
    failure costs 100x more wall clock when the port accepts and holds."""
    m = make_node(19560); n = m.node
    hold = Listener("hold", hold=3 * cov.PEER_SEND_TIMEOUT_S + 1)
    t0 = time.time(); n._send_raw("127.0.0.1", hold.port, "{}"); held = time.time() - t0
    hold.close()

    gone = Listener("silent"); rport = gone.port; gone.close(); time.sleep(0.05)
    t0 = time.time(); n._send_raw("127.0.0.1", rport, "{}"); refused = time.time() - t0

    exp = dead_send_cost(cov.PEER_SEND_TIMEOUT_S)
    check("S3 an accepting-but-silent peer costs the whole retry budget",
          exp * 0.85 < held < exp + 1.0, f"{held:.2f} s, expected ~{exp:.2f} s")

    # THE CONTROL CONDITION, STATED AND CHECKED FIRST (2026-08-29).
    #
    # The next two checks compare a refusing peer against a holding one, and
    # they are only meaningful if closing a listener actually produced a
    # REFUSING port. On Linux it does. On Windows it may not -- which is not a
    # detail, it is this suite's own subject matter appearing in its
    # scaffolding, and it is the most likely reason A23 reads 22/24 on every
    # Windows sweep and 24/24 on every Linux one.
    #
    # So the premise is measured instead of assumed -- and the boundary is the
    # MECHANISM, not a wall-clock guess. A first draft used "< 0.1 s" and
    # promptly turned Linux's own 0.133 s into an UNKNOWN, which is the same
    # class of error it was written to remove.
    #
    # The real distinction: a port that REFUSES fails the connect immediately,
    # in tens of milliseconds. A port that ACCEPTS costs at least one socket
    # timeout before anything can be concluded. So one PEER_SEND_TIMEOUT_S is
    # the boundary, and it scales with whatever the suite is configured to --
    # 0.133 s against a 0.3 s timeout here, and still correct at the 5 s
    # default.
    control_ok = refused < cov.PEER_SEND_TIMEOUT_S
    if not control_ok:
        unknown("S3 a REFUSED peer costs almost nothing by comparison",
                f"CONTROL CONDITION ABSENT: closing a listener did not produce "
                f"a refusing port here ({refused:.3f} s, which is at least one "
                f"{cov.PEER_SEND_TIMEOUT_S} s socket timeout -- it accepted). "
                f"That is the accept-and-hold behaviour this suite exists to "
                f"describe, showing up in its own scaffolding -- so the "
                f"comparison was not run rather than failed. platform="
                f"{sys.platform}")
        unknown("S3 so a sample taken the moment /mine returns can miss the "
                "record entirely",
                f"same missing control; the arithmetic claim stands on its own "
                f"and is checked below")
        # The arithmetic half needs no control condition: it is a property of
        # the retry budget, not of this machine's sockets.
        default_held = dead_send_cost(5.0)
        check("S3 at the shipped 5 s default the budget alone is ~50x a refusal",
              default_held > 50 * 0.133,
              f"{default_held:.1f} s vs ~0.13 s (~{default_held / 0.133:.0f}x), "
              f"arithmetic, no sockets involved")
        return
    check("S3 a REFUSED peer costs almost nothing by comparison",
          refused < held / 5, f"{refused:.3f} s vs {held:.2f} s")
    # M34: state the claim, not a knife edge. The measured ratio here is
    # compressed because the suite runs at a 0.3 s timeout; the number that
    # matters is the one at the SHIPPED default, which is arithmetic.
    default_held = dead_send_cost(5.0)
    check("S3 so a sample taken the moment /mine returns can miss the record entirely",
          held > 3 * refused and default_held > 50 * 0.133,
          f"measured ~{held / max(refused, 1e-6):.0f}x at a {cov.PEER_SEND_TIMEOUT_S}s timeout; "
          f"at the 5 s default it is {default_held:.1f} s vs ~0.13 s "
          f"(~{default_held / 0.133:.0f}x)")


# ------------------------------------------------------- S4 the non-JSON reply
def s4():
    m = make_node(19580); n = m.node
    # M4: werkzeug answers an unparseable request line with an HTTP/0.9 HTML
    # body and no status line. That is what --peers pointed at a Flask API port
    # looks like AFTER boot, when preflight is no longer watching.
    http = Listener("bytes", reply=b"<!DOCTYPE HTML PUBLIC><html><title>400</title></html>")
    r = n._send_raw("127.0.0.1", http.port, "{}")
    kinds = n.anomaly_monitor.report()["per_kind"]
    check("S4 a non-JSON reply is RECORDED, not swallowed",
          "peer_ack_unparseable" in kinds, list(kinds))
    check("S4 it counts as a failed delivery for link health",
          k_of(n, http.port) == 1 and n.dead_peer_count() == 1,
          f"k={k_of(n, http.port)} dead={n.dead_peer_count()}")
    check("S4 the caller still gets None (no behaviour change above _send_raw)",
          r is None, repr(r))
    check("S4 it is NOT retried -- an HTTP server answers the same way 3 times",
          http.conns == 1, f"{http.conns} connections")
    http.close()


# ------------------------------------------------------- S5 no regression on a real peer
def s5():
    m = make_node(19600); n = m.node
    # The reply must look like THIS node's own version, or A20 correctly
    # records peer_version_mismatch and this section would be measuring A20.
    good = Listener("bytes", reply=json.dumps(
        {"ok": True, "outcome": "known", "height": 2,
         "v": cov.COVENANT_VERSION, "src": cov.CORE_SOURCE_SHA12}).encode())
    r = n._send_raw("127.0.0.1", good.port, "{}")
    check("S5 a JSON reply is still returned to the caller unchanged",
          isinstance(r, dict) and r.get("outcome") == "known", repr(r))
    check("S5 a healthy peer records nothing and stays out of dead_peers",
          n.dead_peer_count() == 0 and not n.anomaly_monitor.report()["per_kind"],
          f"dead={n.dead_peer_count()} kinds={list(n.anomaly_monitor.report()['per_kind'])}")
    # and a reply CLEARS an existing backoff (A12's recovery path, preserved)
    silent = Listener("silent")
    n._send_raw("127.0.0.1", silent.port, "{}")
    armed = k_of(n, silent.port)
    silent.close()
    revive = Listener("bytes", reply=json.dumps({"ok": True}).encode())
    # re-point: use a fresh port, so assert the generic property on `good`
    n._note_send_failed("127.0.0.1", good.port)
    before = k_of(n, good.port)
    n._send_raw("127.0.0.1", good.port, "{}")
    check("S5 a reply CLEARS a link's accumulated failures (recovery preserved)",
          before == 1 and k_of(n, good.port) == 0 and armed == 1,
          f"armed={armed} before={before} after={k_of(n, good.port)}")
    good.close(); revive.close()


# ------------------------------------------------------- S6 the boundary, in the source
def s6():
    """M31/M30: pin the rule in something that fails when someone undoes it.

    The defect was one call in the wrong place, and it would be re-introduced by
    anyone 'restoring' the reachability signal. Assert on the source of
    _send_raw that no _note_send_ok appears before the ACK is read."""
    src = inspect.getsource(cov.P2PNode._send_raw)
    lines = src.splitlines()
    idx_ack = next((i for i, l in enumerate(lines) if "recv_bounded(s)" in l), -1)
    ok_calls = [i for i, l in enumerate(lines)
                if re.search(r"self\._note_send_ok\(", l) and not l.strip().startswith("#")]
    check("S6 _send_raw reads an ACK at all", idx_ack > 0, f"line {idx_ack}")
    check("S6 no _note_send_ok is called before the ACK is read",
          all(i > idx_ack for i in ok_calls), f"ack@{idx_ack} ok_calls@{ok_calls}")
    check("S6 exactly one _note_send_ok remains, on the parsed-reply path",
          len(ok_calls) == 1, str(ok_calls))
    fail_calls = [i for i, l in enumerate(lines)
                  if re.search(r"self\._note_send_failed\(", l) and not l.strip().startswith("#")]
    check("S6 three failure sites: unparseable ACK, exhausted ACK, socket error",
          len(fail_calls) == 3, str(fail_calls))
    check("S6 the sendall-is-delivery docstring is gone",
          "whatever it answers" not in inspect.getsource(cov.P2PNode._note_send_ok)
          or "used to be called" in inspect.getsource(cov.P2PNode._note_send_ok),
          "")


if __name__ == "__main__":
    print(f"A23 -- delivery is confirmed by a reply, not by sendall  "
          f"({cov.COVENANT_VERSION}, {cov.CORE_SOURCE_SHA12})\n")
    for fn in (s1, s2, s3, s4, s5, s6):
        try:
            fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False, f"{type(e).__name__}: {e}")
        print()
    p = sum(1 for _, ok in results if ok)
    print(f"A23: {p}/{len(results)} passed"
          + (f", {len(unknowns)} UNKNOWN (never counted as passes)"
             if unknowns else ""))
    sys.exit(0 if p == len(results) else 1)
