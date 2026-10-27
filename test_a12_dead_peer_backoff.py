"""
A12 (v8.23) -- heartbeats to dead peers must not saturate the send pool.

The hazard, by arithmetic on the shipped constants (U1) and then observed with
the REAL pool (L2 with backoff disabled): a periodic tip heartbeat to an
unreachable (non-refusing) host costs _send_raw its whole retry budget --
3 x PEER_SEND_TIMEOUT_S plus the phi sleeps, ~15.1 s at the defaults --
inside one of MAX_CONCURRENT_SENDS (64) workers, and it is re-queued every
TIP_GOSSIP_INTERVAL_S (120 s). Above ~508 dead peers the queue grows without
bound and every NOVEL announce waits behind it.

Fix (v8.23): per-link send health on P2PNode. After k consecutive failures a
PERIODIC heartbeat to that link is withheld until last_failure +
min(TIP_GOSSIP_INTERVAL_S x 2^(k-1), DEAD_PEER_BACKOFF_MAX_S). Never withheld:
the boot push, novel/tx announces, the first send. Any inbound frame from the
peer (a restarted node pushes its tip on boot) or one successful send clears
the backoff. /health exposes heartbeats_skipped and dead_peers.

Blackhole: a local listener with listen(0) and its single backlog slot already
taken -- the kernel drops further SYNs, so connect() times out exactly like an
unreachable host (verified in the sandbox; 10.255.255.1 behaves the same but
needs a route). Everything runs in-process: real _send_raw, real _SEND_POOL
(sized 4 via env before import), real _handle_peer over a socketpair (M12).
"""
import os, sys, json, time, socket, threading, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ["COVENANT_MAX_CONCURRENT_SENDS"] = "4"      # pool is built at import
os.environ["COVENANT_PEER_SEND_TIMEOUT"] = "0.3"       # 3 x 0.3 + sleeps ~ 1.03 s per dead send
os.environ["COVENANT_TIP_GOSSIP_INTERVAL"] = "10"      # backoff base for the live checks (must outlast a drained tick)
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

results = []
def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)

PHI = cov.PHI

def dead_send_cost(timeout, attempts=3):
    return attempts * timeout + sum(0.05 * (PHI ** a) for a in range(attempts - 1))


# ---------------------------------------------------------------- U1: arithmetic on the defaults
def u1():
    cost = dead_send_cost(5.0)
    cap = 64 * 120 / cost
    check("U1 one heartbeat to a dead peer holds a worker ~15 s at the defaults",
          14.5 < cost < 16, f"{cost:.2f} s")
    check("U1 default pool (64) x interval (120 s) saturates above ~500 dead peers",
          480 < cap < 540, f"{cap:.0f} dead peers")
    # Steady-state with v8.23 backoff: one probe per DEAD_PEER_BACKOFF_MAX_S per dead peer.
    cap2 = 64 * 3600 / cost
    check("U1 with hourly backoff the same pool absorbs ~30x more dead peers",
          cap2 > 14000, f"{cap2:.0f}")


# ---------------------------------------------------------------- helpers
class Blackhole:
    """A port that completes no handshake: listen(0) with the one slot taken."""
    def __init__(self):
        self.l = socket.socket(); self.l.bind(("127.0.0.1", 0)); self.l.listen(0)
        self.port = self.l.getsockname()[1]
        self.plug = socket.socket(); self.plug.settimeout(1); self.plug.connect(("127.0.0.1", self.port))
    def close(self):
        self.plug.close(); self.l.close()

class LivePeer:
    """Records arrival time of every frame and answers known."""
    def __init__(self):
        self.seen = []
        self.srv = socket.socket(); self.srv.bind(("127.0.0.1", 0)); self.srv.listen(64)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()
    def _serve(self):
        while True:
            try: c, _ = self.srv.accept()
            except Exception: return
            try:
                buf = b"".join(iter(lambda: c.recv(4096), b""))
                self.seen.append((time.time(), json.loads(buf.decode())))
                c.sendall(json.dumps({"ok": True, "outcome": "known", "height": 2}).encode())
            except Exception: pass
            finally: c.close()
    def wait(self, n, budget=15):
        t0 = time.time()
        while len(self.seen) < n and time.time() - t0 < budget: time.sleep(0.01)
        return len(self.seen) >= n
    def close(self): self.srv.close()

def make_node(port):
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster("a12", host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
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
    m.node.running = True
    return m, b

def deliver(m, msg, src_port):
    a, b = socket.socketpair()
    a.sendall(json.dumps(msg).encode()); a.shutdown(socket.SHUT_WR)
    t = threading.Thread(target=m._handle_peer, args=(b, ("127.0.0.1", src_port)))
    t.start()
    reply = b"".join(iter(lambda: a.recv(4096), b""))
    t.join(10); a.close()
    return json.loads(reply.decode()) if reply else None

def drain_pool():
    """Block until NOTHING else is running in the pool: all 4 workers must meet
    at a barrier at the same time, which is only possible once every queued and
    in-flight send has finished (a qsize()==0 check misses in-flight sends)."""
    bar = threading.Barrier(cov.MAX_CONCURRENT_SENDS)
    fs = [cov._SEND_POOL.submit(bar.wait) for _ in range(cov.MAX_CONCURRENT_SENDS)]
    for f in fs: f.result(timeout=60)


# ---------------------------------------------------------------- L1: one dead send, measured
def l1(m, bh):
    t0 = time.time()
    r = m.node._send_raw("127.0.0.1", bh.port, "{}")
    d = time.time() - t0
    exp = dead_send_cost(cov.PEER_SEND_TIMEOUT_S)
    check("L1 a send to a blackhole costs the full retry budget (real _send_raw)",
          r is None and exp * 0.9 < d < exp + 1.0, f"{d:.2f} s, expected ~{exp:.2f} s")
    kinds = m.node.anomaly_monitor.report()["per_kind"]
    check("L1 the failure is recorded as peer_send_failure", "peer_send_failure" in kinds, list(kinds))
    check("L1 one failure arms a backoff of one interval",
          m.node.heartbeat_suppressed("127.0.0.1", bh.port)
          and abs(m.node._send_backoff_until[("127.0.0.1", bh.port)] - time.time() - cov.TIP_GOSSIP_INTERVAL_S) < 0.5,
          f"until in {m.node._send_backoff_until[('127.0.0.1', bh.port)] - time.time():.2f} s")


# ---------------------------------------------------------------- L2: the pool hazard, with and without backoff
def l2(dead_count=8, backoff=True):
    """Two heartbeat ticks then a NOVEL announce; how late does the live peer hear it?"""
    m, tip = make_node(18700)
    bhs = [Blackhole() for _ in range(dead_count)]
    live = LivePeer()
    for i, b in enumerate(bhs): m.node.add_peer(f"dead{i}", "127.0.0.1", b.port)
    m.node.add_peer("live", "127.0.0.1", live.port)
    saved = cov.DEAD_PEER_BACKOFF_MAX_S
    cov.DEAD_PEER_BACKOFF_MAX_S = 3600.0 if backoff else 0.0   # 0 == v8.22 behaviour
    try:
        m._gossip_tip("periodic")             # tick 1: 8 dead + 1 live queued
        live.wait(1)
        drain_pool()                           # let every dead send fail once
        skipped0 = m.node.heartbeats_skipped
        n = len(live.seen)
        t_tick = time.time()
        m._gossip_tip("periodic")             # tick 2: dead peers now backed off (or not)
        m.node.announce_block(tip)             # a NOVEL block right behind it
        ok = live.wait(n + 2, budget=20)
        late = (live.seen[-1][0] - t_tick) if ok else float("inf")
        novel_frames = [f for _, f in live.seen[n:] if "gossip" not in f]
        drain_pool()
        return {"late": late, "skipped": m.node.heartbeats_skipped - skipped0,
                "novel_seen": len(novel_frames), "dead": m.node.dead_peer_count(),
                "failures": m.node.anomaly_monitor.report()["per_kind"].get("peer_send_failure", {}).get("recent", 0),
                "node": m}
    finally:
        cov.DEAD_PEER_BACKOFF_MAX_S = saved
        for b in bhs: b.close()
        live.close(); m.node.running = False


# ---------------------------------------------------------------- L3-L6 on one node
def l3_l6():
    m, tip = make_node(18720)
    bh = Blackhole(); live = LivePeer()
    m.node.add_peer("dead", "127.0.0.1", bh.port)
    m.node.add_peer("live", "127.0.0.1", live.port)
    key = ("127.0.0.1", bh.port)
    try:
        # L3: backoff growth 1x, 2x, 4x interval, capped
        for k in range(1, 5):
            m.node._note_send_failed(*key)
        until = m.node._send_backoff_until[key] - time.time()
        check("L3 four failures back off 2^3 = 8 intervals", abs(until - 8 * cov.TIP_GOSSIP_INTERVAL_S) < 0.5, f"{until:.2f} s")
        saved = cov.DEAD_PEER_BACKOFF_MAX_S
        cov.DEAD_PEER_BACKOFF_MAX_S = 5.0
        m.node._note_send_failed(*key)
        until = m.node._send_backoff_until[key] - time.time()
        cov.DEAD_PEER_BACKOFF_MAX_S = saved
        check("L3 backoff is capped at DEAD_PEER_BACKOFF_MAX_S", abs(until - 5.0) < 0.5, f"{until:.2f} s")

        # L4: periodic heartbeat skips the dead peer; the BOOT push does not
        sends = []
        orig = m.node._send_raw
        m.node._send_raw = lambda h, p, d, attempts=3: sends.append((p, json.loads(d)))
        m._gossip_tip("periodic")
        drain_pool()
        check("L4 periodic heartbeat withheld from the backed-off peer, sent to the live one",
              [p for p, _ in sends] == [live.port], sends)
        sends.clear()
        m._gossip_tip("boot")
        drain_pool()
        check("L4 the BOOT push goes to every peer, backed off or not",
              sorted(p for p, _ in sends) == sorted([bh.port, live.port]) and all(f.get("gossip") for _, f in sends), sends)
        sends.clear()
        m.node.announce_block(tip)
        m.node.announce_transaction(tip.transactions[0])
        drain_pool()
        check("L4 novel block and tx announces are never gated",
              sorted(p for p, _ in sends) == sorted([bh.port, live.port] * 2), sends)
        m.node._send_raw = orig

        # L5: an inbound frame from the dead peer clears its backoff at once
        r = deliver(m, {"type": "BLOCK_ANNOUNCE", "index": 1, "hash": tip.hash,
                        "node_id": "dead", "p2p_port": bh.port, "gossip": True}, 40010)
        check("L5 inbound heartbeat from the backed-off peer is handled normally", r and r.get("outcome") == "known", r)
        check("L5 ...and clears its backoff", not m.node.heartbeat_suppressed(*key) and key not in m.node._send_failures)
        # a frame WITHOUT p2p_port proves nothing about any link
        m.node._note_send_failed(*key)
        deliver(m, {"type": "BLOCK_ANNOUNCE", "index": 1, "hash": tip.hash, "node_id": "dead"}, 40011)
        check("L5 a frame with no advertised port clears nothing", m.node.heartbeat_suppressed(*key))
        # one successful send clears it too
        m.node._send_raw("127.0.0.1", live.port, json.dumps({"type": "BLOCK_ANNOUNCE", "index": 1, "hash": tip.hash,
                                                               "node_id": "a12", "p2p_port": 18721, "gossip": True}))
        m.node._note_send_failed("127.0.0.1", live.port)
        m.node._send_raw("127.0.0.1", live.port, "{}")
        check("L5 one successful send clears a link's backoff", not m.node.heartbeat_suppressed("127.0.0.1", live.port))

        # L6: /health
        with m.api.app.test_client() as c:
            h = c.get("/health").get_json()
        check("L6 /health exposes heartbeats_skipped and dead_peers",
              h.get("heartbeats_skipped") == m.node.heartbeats_skipped and h.get("dead_peers") == 1,
              {k: h.get(k) for k in ("heartbeats_skipped", "dead_peers")})
        check("L6 /health warns about the unreachable peer",
              any("unreachable" in w for w in h.get("warnings", [])), h.get("warnings"))
    finally:
        bh.close(); live.close(); m.node.running = False


def main():
    u1()
    m, tip = make_node(18740)
    bh = Blackhole()
    try:
        l1(m, bh)
    finally:
        bh.close(); m.node.running = False

    pre = l2(backoff=False)
    check("L2 [v8.22 behaviour, backoff off] tick 2 re-queues every dead peer; the novel announce is late",
          pre["skipped"] == 0 and pre["late"] > 1.0 and pre["novel_seen"] == 1,
          f"novel late by {pre['late']:.2f} s, skipped={pre['skipped']}")
    post = l2(backoff=True)
    check("L2 [v8.23] tick 2 skips all 8 backed-off peers",
          post["skipped"] == 8 and post["dead"] == 8, f"skipped={post['skipped']} dead={post['dead']}")
    check("L2 [v8.23] the novel announce reaches the live peer promptly",
          post["novel_seen"] == 1 and post["late"] < 0.5, f"novel late by {post['late']*1e3:.0f} ms")
    check("L2 [v8.23] the novel announce was still ATTEMPTED to every dead peer (delivery not gated)",
          post["failures"] >= 16, f"peer_send_failure recent={post['failures']} (8 tick-1 + 8 novel)")
    l3_l6()
    p = sum(1 for _, ok in results if ok); f = len(results) - p
    print(f"\n{p}/{len(results)} passed" + (f", {f} FAILED" if f else ""))
    sys.exit(1 if f else 0)

if __name__ == "__main__":
    main()
