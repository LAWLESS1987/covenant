"""
A12 (v8.23) -- unreachable peers must not eat the send pool or delay live ones.

Every outbound message goes through _send_raw: up to 3 attempts, each bounded
by PEER_SEND_TIMEOUT_S (5 s), so one message to a peer whose host DROPS packets
(powered off, CGNAT, firewall, a phone off wifi) costs ~15.1 s of one of the
MAX_CONCURRENT_SENDS (64) pool workers. A refusing peer is cheap (instant
ECONNREFUSED); a black-holed one is not. v8.20 added a heartbeat to EVERY peer
every TIP_GOSSIP_INTERVAL_S (120 s), so a node's steady-state cost for D dead
peers became 15.1*D worker-seconds per 120 s -- the pool is permanently busy at
D ~ 508, and the FIFO queue puts every real announce behind the heartbeat burst
long before that: with D >= 64 a novel-block announce to a LIVE peer waits a
full 15 s generation because ties in delivery order fall back to insertion
order and a dead peer sits at baseline conductance forever (it is never
reinforced or attenuated -- it never answers).

Measured here with the REAL P2PNode/_send_raw/_gossip_tip and a socket shim
that makes chosen addresses black-hole (sleep the socket timeout, then raise
socket.timeout -- deterministic on any OS, no network needed). Scaled down so
the run is ~1 min: timeout 0.5 s, 4 workers, 8 dead peers + 1 live fake peer.

Fix (v8.23): PeerHealth, an outbound failure detector fed ONLY by this node's
own send outcomes (connect+send succeeded = ok; every attempt raised = failed):
  * delivery ORDER puts peers whose last send succeeded first, unknown next,
    failing last -- ordering only, nothing dropped (LinkConductance's rule);
  * after PEER_SUSPECT_AFTER consecutive failures a peer is SUSPECT: real
    messages still go to it (one attempt instead of three -- the message is
    the probe), periodic heartbeats skip it until an exponential backoff
    (PEER_BACKOFF_BASE_S doubling to PEER_BACKOFF_MAX_S) expires and then
    serve as the probe; any success resets it;
  * periodic heartbeats use one attempt (the next heartbeat IS the retry);
    the BOOT push keeps three (K2's path home);
  * /health reports peers_suspect and warns; GET /peers carries the table.
Written from the failure side (M9): every check below FAILS on v8.22.
"""
import os, sys, json, time, socket, threading, tempfile, types, subprocess, concurrent.futures
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ["COVENANT_PEER_SEND_TIMEOUT"] = "0.5"        # 5 s in production
os.environ["COVENANT_MAX_CONCURRENT_SENDS"] = "4"       # 64 in production
os.environ["COVENANT_TIP_GOSSIP_INTERVAL"] = "0"        # rounds are driven by hand
os.environ["COVENANT_PEER_SUSPECT_AFTER"] = "3"
os.environ["COVENANT_PEER_BACKOFF_BASE_S"] = "100"      # 120 s in production
os.environ["COVENANT_PEER_BACKOFF_MAX_S"] = "400"       # 900 s in production
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

results = []
def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)

T = cov.PEER_SEND_TIMEOUT_S
W = cov.MAX_CONCURRENT_SENDS
D = 8
LIVE = ("127.0.0.1", 19101)
LIVE2 = ("127.0.0.1", 19111)   # L8 uses its own listener: a closed listener's accept thread may still hold the port

# ------------------------------------------------------------ socket shim
DEAD, REVIVED, HITS = set(), {}, {}
HIT_LOCK = threading.Lock()
class DeadAwareSocket(socket.socket):
    """connect() to an address in DEAD behaves like a black hole: the full
    socket timeout elapses, then socket.timeout. REVIVED maps an address to a
    real one (a dead peer that came back)."""
    def connect(self, addr):
        addr = tuple(addr)
        if addr in REVIVED:
            return super().connect(REVIVED[addr])
        if addr in DEAD:
            with HIT_LOCK:
                HITS[addr] = HITS.get(addr, 0) + 1
            time.sleep(self.gettimeout() or T)
            raise socket.timeout(f"simulated black hole {addr}")
        return super().connect(addr)
shim = types.ModuleType("socket_shim"); shim.__dict__.update(socket.__dict__)
shim.socket = DeadAwareSocket

def hits():
    with HIT_LOCK:
        return sum(HITS.values())

# ------------------------------------------------------------ virtual clock
REAL_TIME = time.time
OFFSET = [0.0]
def advance(s):
    OFFSET[0] += s

# ------------------------------------------------------------ send-pool tap
SUBMITS, FUTS = [], []
ORIG_SUBMIT = cov._SEND_POOL.submit
def tracked_submit(fn, *a, **k):
    att = a[3] if len(a) > 3 else k.get("attempts", 3)
    SUBMITS.append((time.monotonic(), a[0], int(a[1]), att))
    f = ORIG_SUBMIT(fn, *a, **k); FUTS.append(f); return f

def drain(timeout=40):
    concurrent.futures.wait(list(FUTS), timeout=timeout)
    FUTS.clear()

def reset():
    SUBMITS.clear()
    with HIT_LOCK:
        HITS.clear()

def qsize():
    return cov._SEND_POOL._work_queue.qsize()

# ------------------------------------------------------------ fake live peer
SEEN = []
def start_live_peer(addr=LIVE):
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(addr); srv.listen(64); srv.settimeout(300)
    def serve():
        while True:
            try: c, _ = srv.accept()
            except Exception: return
            try:
                buf = b"".join(iter(lambda: c.recv(4096), b""))
                SEEN.append((time.monotonic(), json.loads(buf.decode())))
                c.sendall(json.dumps({"ok": True, "outcome": "known", "height": 2}).encode())
            except Exception as e:
                SEEN.append((time.monotonic(), {"error": repr(e)}))
            finally:
                c.close()
    threading.Thread(target=serve, daemon=True).start()
    return srv

def wait_seen(n, t=15):
    t0 = time.monotonic()
    while len(SEEN) < n and time.monotonic() - t0 < t:
        time.sleep(0.01)
    return len(SEEN) >= n

# ------------------------------------------------------------ node
def make_node(port, label):
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster(label, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
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
    return m, b, tx

def add_dead(m, subnet, port0):
    addrs = []
    for i in range(D):
        host, port = f"10.{subnet}.0.{i + 1}", port0 + i
        m.node.add_peer(f"dead{subnet}_{i}", host, port)
        DEAD.add((host, port)); addrs.append((host, port))
    return addrs

def health(m):
    h = getattr(m.node, "peer_health", None)
    return h.snapshot() if h is not None else {}

def round_(m, reason="periodic", expect_live=True):
    """One heartbeat round; returns (submits, dead_hits, live_latency_s)."""
    reset(); n0 = len(SEEN)
    t0 = time.monotonic()
    m._gossip_tip(reason)
    lat = None
    if expect_live and wait_seen(n0 + 1):
        lat = SEEN[n0][0] - t0
    drain()
    return len(SUBMITS), hits(), lat

# ================================================================ checks
def unit_health():
    print("\n== U: PeerHealth (pure, patched clock) ==")
    PH = getattr(cov, "PeerHealth", None)
    check("U0 PeerHealth class exists", PH is not None)
    if PH is None:
        return
    h = PH()
    check("U1 unknown peer: rank 1 (between proven-good 0 and failing 2), not suspect",
          h.rank("x") == 1 and not h.is_suspect("x"))
    h.ok("x")
    check("U1 after a success: rank 0", h.rank("x") == 0)
    for _ in range(cov.PEER_SUSPECT_AFTER - 1):
        h.failed("x")
    check(f"U2 {cov.PEER_SUSPECT_AFTER - 1} failures: rank 2 (failing) but NOT yet suspect",
          h.rank("x") == 2 and not h.is_suspect("x"), h.snapshot().get("x"))
    h.failed("x")
    now = cov.time.time()
    check("U2 K-th consecutive failure makes the peer suspect, heartbeat skipped (probe not due)",
          h.is_suspect("x") and h.skip_heartbeat("x", now), h.snapshot().get("x"))
    check("U3 probe becomes due after PEER_BACKOFF_BASE_S",
          h.skip_heartbeat("x", now + cov.PEER_BACKOFF_BASE_S - 1)
          and not h.skip_heartbeat("x", now + cov.PEER_BACKOFF_BASE_S + 0.01))
    h.failed("x")
    check("U3 next failure doubles the backoff",
          h.skip_heartbeat("x", now + 2 * cov.PEER_BACKOFF_BASE_S - 1)
          and not h.skip_heartbeat("x", now + 2 * cov.PEER_BACKOFF_BASE_S + 0.01))
    for _ in range(12):
        h.failed("x")
    snap = h.snapshot()["x"]
    check("U3 backoff is capped at PEER_BACKOFF_MAX_S",
          snap["backoff_remaining_s"] <= cov.PEER_BACKOFF_MAX_S + 1e-6, snap)
    h.ok("x")
    check("U4 one success resets: rank 0, not suspect, zero failures",
          h.rank("x") == 0 and not h.is_suspect("x") and h.snapshot()["x"]["consecutive_failures"] == 0)
    check("U5 the relation is asserted: 1 <= BASE <= MAX, K >= 1",
          1 <= cov.PEER_BACKOFF_BASE_S <= cov.PEER_BACKOFF_MAX_S and cov.PEER_SUSPECT_AFTER >= 1)


def live_checks():
    print("\n== L: real P2PNode / _send_raw / _gossip_tip against dead + live peers ==")
    srv = start_live_peer()
    m, tip, tx = make_node(19000, "a12")
    dead = add_dead(m, 0, 19201)
    m.node.add_peer("live", *LIVE)          # added LAST: ties in delivery order fall to insertion order

    # L0 -- the unit cost of one message to a black hole (informational, pre and post)
    t0 = time.monotonic(); m.node._send_raw(dead[0][0], dead[0][1], "{}"); one = time.monotonic() - t0
    print(f"      one _send_raw to a black hole: {one:.2f} s  (3 attempts x {T} s + backoff sleeps)")
    m.node.anomaly_monitor = cov.SpikingAnomalyMonitor()
    if hasattr(m.node, "peer_health"):
        m.node.peer_health = cov.PeerHealth()
    reset()

    # L1 -- startup: bootstrap_chain probes every peer, then the boot push.
    t0 = time.monotonic()
    m.bootstrap_chain(rounds=1)
    boot_probe = time.monotonic() - t0
    print(f"      bootstrap_chain over {D} dead + 1 live peers: {boot_probe:.2f} s (sequential, {T} s each)")
    n, h, lat = round_(m, "boot")
    check("L1 boot push addresses EVERY peer with the full 3 attempts (K2's path home kept)",
          n == D + 1 and h == 3 * D, f"submits={n} dead_hits={h}")
    check("L1 boot push reaches the live peer FIRST (bootstrap already showed who answers)",
          lat is not None and lat < 0.3, f"live latency {lat if lat is None else round(lat, 3)} s")
    check("L1 boot push frame is a tagged heartbeat", SEEN[-1][1].get("gossip") is True and SEEN[-1][1].get("index") == 1)

    # L2 -- the first periodic round: dead peers have failed twice (bootstrap probe, boot push) -- still attempted
    n, h, lat = round_(m)
    check("L2 round 1: every peer still attempted, ONE attempt each (the next heartbeat is the retry)",
          n == D + 1 and h == D, f"submits={n} dead_hits={h} (v8.22: {3 * D})")
    check(f"L2 round 1: live peer is served first, not behind {D} dead ones",
          lat is not None and lat < 0.3, f"live latency {lat if lat is None else round(lat, 3)} s "
          f"(v8.22 ~{2 * (3 * T + 0.13):.1f} s)")
    snap = health(m)
    check("L2 after 3 consecutive failures (probe, boot push, round 1) every dead peer is suspect; the live one is not",
          all(snap.get(f"dead0_{i}", {}).get("suspect") for i in range(D)) and not snap.get("live", {}).get("suspect"),
          {k: v.get("consecutive_failures") for k, v in snap.items()})

    # L3 -- backoff: heartbeats skip suspect peers until the probe is due
    for r in (2, 3):
        n, h, lat = round_(m)
        check(f"L3 round {r}: heartbeat goes to the live peer only (dead peers in backoff)",
              n == 1 and h == 0 and lat is not None and lat < 0.3, f"submits={n} dead_hits={h} lat={lat}")

    # L4 -- a REAL announce while the dead peers are suspect: nobody is dropped, live first, one attempt
    reset(); n0 = len(SEEN); t0 = time.monotonic()
    m.node.announce_block(tip)
    got = wait_seen(n0 + 1); lat = SEEN[n0][0] - t0 if got else None
    drain()
    check("L4 real block announce still addresses every peer (nothing gated)",
          len(SUBMITS) == D + 1, f"submits={len(SUBMITS)}")
    check("L4 real announce is submitted to the live peer FIRST",
          SUBMITS and (SUBMITS[0][1], SUBMITS[0][2]) == LIVE, SUBMITS[:2])
    check("L4 real announce to a suspect peer uses ONE attempt", hits() == D, f"dead_hits={hits()} (v8.22: {3 * D})")
    check("L4 live peer received the real (untagged) announce promptly",
          got and lat < 0.3 and "gossip" not in SEEN[n0][1], f"lat={lat}")
    reset(); n0 = len(SEEN)
    m.node.announce_transaction(tx)
    wait_seen(n0 + 1); drain()
    check("L4 transaction announce goes through the same ordering (live first, all addressed)",
          len(SUBMITS) == D + 1 and (SUBMITS[0][1], SUBMITS[0][2]) == LIVE, SUBMITS[:1])
    reset(); n0 = len(SEEN)
    m.node.propagate_transaction(tx)
    wait_seen(n0 + 1); drain()
    check("L4 legacy propagate_transaction too", len(SUBMITS) == D + 1 and (SUBMITS[0][1], SUBMITS[0][2]) == LIVE)

    # L5 -- the probe schedule: due after the backoff, which doubles to a cap
    # (each real announce above was a failed probe, so the backoff has grown)
    snap = health(m)
    if not snap:   # v8.22: no PeerHealth at all -- record it and keep going so L8 still runs
        for lbl in ("L5 probe schedule", "L6 recovery", "L7 /health + /peers"):
            check(f"{lbl} (no peer_health on this build)", False)
        srv.close(); m.node.running = False
        return
    rem = max(v["backoff_remaining_s"] for k, v in snap.items() if k.startswith("dead"))
    advance(rem - 5)
    n, h, _ = round_(m)
    check("L5 just before the backoff expires: still skipped", n == 1 and h == 0, f"submits={n} remaining~{rem:.0f}s")
    advance(6)
    n, h, lat = round_(m)
    check("L5 once due, the heartbeat IS the probe: every dead peer gets exactly one attempt, live still first",
          n == D + 1 and h == D and lat is not None and lat < 0.3, f"submits={n} dead_hits={h} lat={lat}")
    snap = health(m)
    rem2 = max(v["backoff_remaining_s"] for k, v in snap.items() if k.startswith("dead"))
    check("L5 a failed probe pushes the next one out, never past PEER_BACKOFF_MAX_S",
          rem < rem2 <= cov.PEER_BACKOFF_MAX_S + 1e-6 or abs(rem2 - cov.PEER_BACKOFF_MAX_S) < 1e-6,
          f"{rem:.0f}s -> {rem2:.0f}s (cap {cov.PEER_BACKOFF_MAX_S}s)")

    # L6 -- recovery: a dead peer comes back; the next due probe finds it and it is healthy again
    REVIVED[dead[0]] = LIVE
    advance(cov.PEER_BACKOFF_MAX_S + 1)
    n0 = len(SEEN)
    n, h, _ = round_(m)
    wait_seen(n0 + 2)
    snap = health(m)
    check("L6 due probe reaches the revived peer (live listener saw two frames: live + revived)",
          n == D + 1 and h == D - 1 and len(SEEN) - n0 == 2, f"submits={n} dead_hits={h} frames={len(SEEN) - n0}")
    check("L6 revived peer is reset: not suspect, zero failures, rank restored",
          not snap["dead0_0"]["suspect"] and snap["dead0_0"]["consecutive_failures"] == 0
          and m.node.peer_health.rank("dead0_0") == 0, snap.get("dead0_0"))
    n, h, _ = round_(m)
    check("L6 next heartbeat addresses live + revived only", n == 2 and h == 0, f"submits={n} dead_hits={h}")
    reset(); n0 = len(SEEN)
    m.node.announce_block(tip); wait_seen(n0 + 2); drain()
    att = {(s[1], s[2]): s[3] for s in SUBMITS}
    check("L6 a real announce to the revived peer gets its 3 attempts back; suspects keep 1",
          att.get(dead[0]) == 3 and att.get(LIVE) == 3 and all(att.get(a) == 1 for a in dead[1:]), att)

    # L7 -- /health and /peers expose it
    with m.api.app.test_client() as c:
        hj = c.get("/health").get_json(); pj = c.get("/peers").get_json()
    check("L7 /health reports peers_suspect and warns about unreachable peers",
          hj.get("peers_suspect") == D - 1 and any("unreachable" in w for w in hj.get("warnings", [])),
          f"peers_suspect={hj.get('peers_suspect')} warnings={hj.get('warnings')}")
    check("L7 /health is NOT degraded by unreachable peers (they are a warning, not a fault)",
          hj.get("degraded") == bool(hj.get("judge_keyless") or hj.get("judge_insecure")
                                     or hj.get("own_genesis") or hj.get("crisis_mode")),
          f"degraded={hj.get('degraded')} from keyless/insecure/own_genesis/crisis only")
    check("L7 GET /peers carries the health table", isinstance(pj.get("health"), dict) and "dead0_1" in pj["health"],
          list(pj.get("health", {}))[:3])
    srv.close(); m.node.running = False
    del REVIVED[dead[0]]


def pool_bound():
    """L8 -- heartbeats at an interval shorter than the dead-peer cost: the
    pre-fix queue grows without bound; post-fix it drains every round and is
    empty within a second of the last one."""
    print("\n== L8: bounded send-pool queue under a heartbeat interval shorter than the dead-peer cost ==")
    srv = start_live_peer(LIVE2)
    m, tip, _ = make_node(19020, "a12q")
    add_dead(m, 1, 19301)
    m.node.add_peer("live", *LIVE2)
    reset()
    interval, rounds = 1.2, 6
    maxq = 0
    t0 = time.monotonic()
    for r in range(rounds):
        m._gossip_tip("periodic")
        tn = t0 + (r + 1) * interval
        while time.monotonic() < tn:
            maxq = max(maxq, qsize()); time.sleep(0.02)
    q_end = qsize()
    t1 = time.monotonic()
    while (qsize() > 0 or any(not f.done() for f in FUTS)) and time.monotonic() - t1 < 3.0:
        time.sleep(0.02)
    drained_in = time.monotonic() - t1
    ok = qsize() == 0 and all(f.done() for f in FUTS)
    pre_note = (f"v8.22: each round adds {D}x{3 * T + 0.13:.2f} s of work to {W} workers every {interval} s -> queue grows "
                f"~{D * (3 * T + 0.13) / interval - W:.0f} tasks/round")
    check(f"L8 queue is empty within 3 s of the last heartbeat round ({rounds} rounds x {interval} s, {D} dead peers)",
          ok, f"queue at end={q_end} max={maxq} drained_in={drained_in:.2f}s submits={len(SUBMITS)} dead_hits={hits()}; {pre_note}")
    check("L8 submits stop going to dead peers once they are suspect (total well under rounds x peers)",
          len(SUBMITS) <= 3 * (D + 1) + (rounds - 3) * 1 + 2, f"submits={len(SUBMITS)} (v8.22: {rounds * (D + 1)})")
    drain(); srv.close(); m.node.running = False


def import_guards():
    print("\n== G: import-time refusal of incoherent knobs (M7) ==")
    def boot(env):
        e = dict(os.environ, **env)
        r = subprocess.run([sys.executable, "-c", "import covenant_unified_v8"], env=e, cwd=HERE,
                           capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stderr or "")[-300:]
    rc, err = boot({"COVENANT_PEER_BACKOFF_BASE_S": "100", "COVENANT_PEER_BACKOFF_MAX_S": "10"})
    check("G1 BASE > MAX refuses to start", rc != 0 and "backoff" in err.lower(), f"rc={rc} {err[-120:]!r}")
    rc, err = boot({"COVENANT_PEER_SUSPECT_AFTER": "0"})
    check("G2 PEER_SUSPECT_AFTER=0 refuses to start", rc != 0 and "suspect" in err.lower(), f"rc={rc} {err[-120:]!r}")
    rc, err = boot({"COVENANT_PEER_BACKOFF_BASE_S": "60", "COVENANT_PEER_BACKOFF_MAX_S": "60"})
    check("G3 BASE == MAX is allowed (constant backoff)", rc == 0, f"rc={rc} {err[-120:]!r}")


def arithmetic():
    print("\n== A: the saturation arithmetic with the file's own constants (M7) ==")
    # Production constants are read back from the module by a fresh import so the scaled env above does not leak.
    src = ("import os; [os.environ.pop(k, None) for k in list(os.environ) if k.startswith('COVENANT_PEER') or k.startswith('COVENANT_MAX_CONCURRENT') or k.startswith('COVENANT_TIP')]\n"
           "import covenant_unified_v8 as c, json\n"
           "print(json.dumps(dict(W=c.MAX_CONCURRENT_SENDS, T=c.PEER_SEND_TIMEOUT_S, I=c.TIP_GOSSIP_INTERVAL_S,"
           " K=getattr(c,'PEER_SUSPECT_AFTER',None), B=getattr(c,'PEER_BACKOFF_BASE_S',None), M=getattr(c,'PEER_BACKOFF_MAX_S',None))))")
    out = subprocess.run([sys.executable, "-c", src], cwd=HERE, capture_output=True, text=True, timeout=120).stdout.strip().splitlines()[-1]
    k = json.loads(out)
    per_msg_pre = 3 * k["T"] + 0.05 + 0.05 * cov.PHI      # three attempts + the two backoff sleeps
    d_sat_pre = k["W"] * k["I"] / per_msg_pre
    print(f"      production: W={k['W']} T={k['T']} s I={k['I']} s -> one message to a black hole costs {per_msg_pre:.2f} s;"
          f" heartbeats alone keep the pool permanently busy at D >= {d_sat_pre:.0f} dead peers (pre-fix)")
    if k["M"]:
        d_sat_post = k["W"] * k["M"] / k["T"]
        print(f"      post-fix steady state: one {k['T']} s probe per >= {k['M']} s per dead peer -> saturation at D >= {d_sat_post:.0f}")
        check("A1 post-fix steady-state saturation threshold is >= 10x the pre-fix one",
              d_sat_post >= 10 * d_sat_pre, f"{d_sat_post:.0f} vs {d_sat_pre:.0f}")
        check("A1 a suspect peer's heartbeat probe period is bounded by the cap (K*I + MAX is the worst-case time to notice a revival)",
              k["K"] * k["I"] + k["M"] < 3600, f"{k['K'] * k['I'] + k['M']:.0f} s")
    else:
        check("A1 PEER_BACKOFF_MAX_S exists", False, "v8.22 has no backoff")


def main():
    cov.socket = shim
    cov.time.time = lambda: REAL_TIME() + OFFSET[0]
    cov._SEND_POOL.submit = tracked_submit
    try:
        unit_health()
        live_checks()
        pool_bound()
    finally:
        cov.socket = socket
        cov.time.time = REAL_TIME
        cov._SEND_POOL.submit = ORIG_SUBMIT
    import_guards()
    arithmetic()
    p = sum(1 for _, ok in results if ok); f = len(results) - p
    print(f"\n{p}/{len(results)} passed" + (f", {f} FAILED" if f else ""))
    sys.exit(1 if f else 0)

if __name__ == "__main__":
    main()
