"""
A11 (v8.21) -- periodic tip gossip at scale must cost nothing on a held tip.

v8.20 added a tip heartbeat (boot push + every TIP_GOSSIP_INTERVAL_S) so a
node that comes back AHEAD of its peers is heard (A1, K2). The receiver treated
that heartbeat exactly like any redundant announce: record `announce_inhibited`
on the anomaly monitor and ATTENUATE the sender's link conductance. Measured
with the real classes (U1/U2 below, clock patched):

  * LinkConductance: -0.02 per heartbeat every 120 s against a 3600 s
    half-life relaxation toward 0.5 has an equilibrium far below MIN, so on a
    quiet chain EVERY link sits at MIN (0.05) within ~30 rounds (~1 h). The
    ordering the class exists to learn is erased by the gossip itself.
  * SpikingAnomalyMonitor: after a synchronized restart with >=5 peers the
    heartbeats arrive in lockstep; baseline is still short, so `recent > 3x
    expected` holds and /health reports "anomaly spike: ['announce_inhibited']"
    for the first ~5 minutes. A false alarm on the one channel an operator is
    told to watch.

Fix (v8.21): heartbeats carry `"gossip": true`. A receiver that ALREADY HOLDS
the tip counts it (`tip_gossip_seen`, exposed on /health) and does nothing
else. A receiver that is behind fetches exactly as before (the K2 path). An
untagged duplicate announce is still attenuated and recorded -- nothing was
weakened; the tag only removes a penalty on ordering, which never gates.

Checks drive the REAL `_handle_peer` in-process over a socketpair (no listener,
no second process; the same receiver code a live peer reaches), plus the real
`_gossip_tip` against a fake peer socket (the K5 recipe). ~20 s.
"""
import os, sys, json, time, socket, threading, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

results = []
def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)


# ---------------------------------------------------------------- U1 / U2
def u1_u2():
    real = time.time
    base = real()
    try:
        # U1: the v8.20 schedule against the REAL monitor -- documents the hazard.
        def schedule(d):
            mon = cov.SpikingAnomalyMonitor()
            flags = []
            for t in [1.5, 120.0, 240.0, 360.0]:
                cov.time.time = lambda t=t: base + t
                for _ in range(d):
                    mon.record("announce_inhibited", "index 5 already held")
                cov.time.time = lambda t=t: base + t + 1
                flags.append(mon.report()["spike_detected"])
            return flags
        f2, f5 = schedule(2), schedule(5)
        check("U1 v8.20 schedule: 2 peers never trip the monitor (L's 3-node net is safe)",
              not any(f2), f2)
        check("U1 v8.20 schedule: 5 peers trip a FALSE spike for the first 3 rounds",
              f5[:3] == [True, True, True] and f5[3] is False, f5)
        # U2: the v8.20 attenuate-per-heartbeat schedule against the REAL class.
        lc = cov.LinkConductance()
        ws = []
        for k in range(41):
            cov.time.time = lambda k=k: base + 120 * k
            lc.attenuate("p")
            ws.append(lc.weight("p"))
        first_min = next((k for k, w in enumerate(ws) if abs(w - cov.LinkConductance.MIN) < 1e-9), None)
        check("U2 v8.20 schedule: one heartbeat per 120 s drives a link from 0.5 to MIN within 35 rounds (~70 min)",
              ws[0] < 0.5 and first_min is not None and first_min <= 35,
              f"round0={ws[0]:.3f} round10={ws[10]:.3f} round30={ws[30]:.3f} MIN first at round {first_min}")
    finally:
        cov.time.time = real


# ---------------------------------------------------------------- live node
def make_node(port):
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster("a11", host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    tx = cov.Transaction(sender_pubkey=pem, receiver="HUMANITY", data={"origin": "human"}, amount=0.0,
                         benefit_score=m.node.governor.get_current(), reg_nonce=reg)
    tx.sign(k)
    b = cov.Block(1, [tx], m.node.chain[-1].hash)
    b.stake_rewards = 0.0; b.alignment_score = tx.benefit_score; b.mine()
    assert m._accept_block_common(b) and len(m.node.chain) == 2
    return m, b

def deliver(m, msg, src_port):
    """Push one frame through the REAL _handle_peer over a socketpair; return the reply."""
    a, b = socket.socketpair()
    a.sendall(json.dumps(msg).encode()); a.shutdown(socket.SHUT_WR)
    t = threading.Thread(target=m._handle_peer, args=(b, ("127.0.0.1", src_port)))
    t.start()
    reply = b"".join(iter(lambda: a.recv(4096), b""))
    t.join(10); a.close()
    return json.loads(reply.decode()) if reply else None

def live():
    m, tip = make_node(18800)
    PEER_P2P = 18901
    m.node.add_peer("fake", "127.0.0.1", PEER_P2P)
    pid = m.node.resolve_peer_id("127.0.0.1", PEER_P2P)
    check("L0 test peer resolves to a peer id (attenuation would key on it)", bool(pid), pid)
    counts = lambda: {k: v["baseline"] for k, v in m.node.anomaly_monitor.report()["per_kind"].items()}
    w0 = m.node.link_conductance.weight(pid)

    # L1 -- tagged heartbeat for the tip we hold
    r = deliver(m, {"type": "BLOCK_ANNOUNCE", "index": 1, "hash": tip.hash,
                    "node_id": "fake", "p2p_port": PEER_P2P, "gossip": True}, 40001)
    check("L1 held-tip heartbeat is answered known", r and r.get("outcome") == "known", r)
    check("L1 heartbeat counted on tip_gossip_seen", m.node.tip_gossip_seen == 1, m.node.tip_gossip_seen)
    check("L1 heartbeat recorded NO announce_inhibited", counts().get("announce_inhibited", 0) == 0, counts())
    check("L1 heartbeat did NOT attenuate the link",
          abs(m.node.link_conductance.weight(pid) - w0) < 1e-9, f"{w0:.3f} -> {m.node.link_conductance.weight(pid):.3f}")

    # L2 -- untagged duplicate: the control is intact
    r = deliver(m, {"type": "BLOCK_ANNOUNCE", "index": 1, "hash": tip.hash,
                    "node_id": "fake", "p2p_port": PEER_P2P}, 40002)
    check("L2 untagged duplicate is answered known", r and r.get("outcome") == "known", r)
    check("L2 untagged duplicate IS recorded as announce_inhibited", counts().get("announce_inhibited", 0) == 1, counts())
    check("L2 untagged duplicate IS attenuated (control not weakened)",
          m.node.link_conductance.weight(pid) < w0 - 0.01, f"{w0:.3f} -> {m.node.link_conductance.weight(pid):.3f}")
    check("L2 untagged duplicate not counted as gossip", m.node.tip_gossip_seen == 1, m.node.tip_gossip_seen)

    # L2b -- a forged tag on a non-gossip field value is not honoured
    r = deliver(m, {"type": "BLOCK_ANNOUNCE", "index": 1, "hash": tip.hash,
                    "node_id": "fake", "p2p_port": PEER_P2P, "gossip": "true"}, 40003)
    check("L2b gossip:'true' (string) is treated as untagged", counts().get("announce_inhibited", 0) == 2, counts())

    # L3 -- tagged heartbeat for a tip we do NOT hold: the fetch path is untouched
    called = []
    orig = m._fetch_announced
    m._fetch_announced = lambda *a, **k: called.append(a)
    r = deliver(m, {"type": "BLOCK_ANNOUNCE", "index": 2, "hash": "ab" * 32,
                    "node_id": "fake", "p2p_port": PEER_P2P, "gossip": True}, 40004)
    t0 = time.time()
    while not called and time.time() - t0 < 5: time.sleep(0.05)
    m._fetch_announced = orig
    check("L3 heartbeat for an unheld tip is answered novel", r and r.get("outcome") == "novel", r)
    check("L3 heartbeat for an unheld tip triggers the fetch (K2 path intact)",
          len(called) == 1 and called[0][2] == 2, called)
    check("L3 unheld heartbeat is not counted as a held one", m.node.tip_gossip_seen == 1)

    # L4 -- the sender side: _gossip_tip tags its frame; announce_block does not by default
    seen = []
    srv = socket.socket(); srv.bind(("127.0.0.1", PEER_P2P)); srv.listen(8); srv.settimeout(10)
    def serve():
        while True:
            try: c, _ = srv.accept()
            except Exception: return
            try:
                buf = b"".join(iter(lambda: c.recv(4096), b""))
                seen.append(json.loads(buf.decode()))
                c.sendall(json.dumps({"ok": True, "outcome": "known", "height": 2}).encode())
            except Exception: pass
            finally: c.close()
    threading.Thread(target=serve, daemon=True).start()
    m.node.running = True
    n = m._gossip_tip("test")
    t0 = time.time()
    while len(seen) < 1 and time.time() - t0 < 10: time.sleep(0.05)
    check("L4 _gossip_tip addressed the peer and the frame carries gossip:true",
          n == 1 and len(seen) == 1 and seen[0].get("gossip") is True and seen[0].get("index") == 1, seen[:1])
    m.node.announce_block(tip)
    t0 = time.time()
    while len(seen) < 2 and time.time() - t0 < 10: time.sleep(0.05)
    check("L4 a real (new-block) announce carries NO gossip tag",
          len(seen) == 2 and "gossip" not in seen[1], seen[1:2])
    srv.close(); m.node.running = False

    # L5 -- steady state at scale, per node: degree 50, 600 s of heartbeats
    before = m.node.tip_gossip_seen
    t0 = time.perf_counter()
    for i in range(250):
        deliver(m, {"type": "BLOCK_ANNOUNCE", "index": 1, "hash": tip.hash,
                    "node_id": f"n{i}", "p2p_port": PEER_P2P, "gossip": True}, 41000 + i)
    per = (time.perf_counter() - t0) / 250
    rep = m.node.anomaly_monitor.report()
    check("L5 250 heartbeats (degree 50 x 600 s): all counted, none recorded, no spike",
          m.node.tip_gossip_seen - before == 250 and counts().get("announce_inhibited", 0) == 2
          and not rep["spike_detected"],
          f"seen +{m.node.tip_gossip_seen - before}, inhibited={counts().get('announce_inhibited', 0)}, "
          f"spikes={rep['spikes']}, {per*1e3:.2f} ms/heartbeat (handler+socketpair)")
    check("L5 a heartbeat costs under 5 ms on the receiver", per < 0.005, f"{per*1e3:.2f} ms")
    check("L5 link conductance unmoved by 250 heartbeats",
          abs(m.node.link_conductance.weight(pid) - (w0 - cov.LinkConductance.ATTENUATE * 2)) < 0.01,
          f"{m.node.link_conductance.weight(pid):.3f}")

    # L6 -- /health exposes the counter
    with m.api.app.test_client() as c:
        h = c.get("/health").get_json()
    check("L6 /health exposes tip_gossip_seen", h.get("tip_gossip_seen") == m.node.tip_gossip_seen, h.get("tip_gossip_seen"))
    check("L6 /health carries no anomaly-spike warning", not any("anomaly spike" in w for w in h.get("warnings", [])),
          h.get("warnings"))


def main():
    u1_u2()
    live()
    p = sum(1 for _, ok in results if ok); f = len(results) - p
    print(f"\n{p}/{len(results)} passed" + (f", {f} FAILED" if f else ""))
    sys.exit(1 if f else 0)

if __name__ == "__main__":
    main()
