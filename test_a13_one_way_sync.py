#!/usr/bin/env python3
"""
A13 -- one-way reachability never synced (v8.25 fix: read the announce reply).

SCENARIO. Two nodes X and Y. X can reach Y; Y cannot reach X (X behind CGNAT
or a one-way firewall, Y on a VPS -- NODE_DEPLOYMENT_FINDINGS.md section 5).
Y mints blocks. Y's announces to X fail, so X never hears of them. X's own
heartbeats DO reach Y, and Y answers every one with {"outcome": "known",
"height": <Y's height>} -- a height above X's. On v8.24 `announce_block`
submitted `_send_raw` straight to the pool and its return value (that reply)
was thrown away. Measured here against v8.24: X sits at height 2 beside a
reachable peer at height 4 for the whole window (pre-fix record, T2).

FIX (v8.25). `P2PNode._send_announce` wraps `_send_raw` for BLOCK_ANNOUNCE
frames; when the reply's `height` is a real int strictly above ours it
counts `peer_ahead_seen`, records `peer_ahead`, and -- gated by
`catchup_allowed()` -- submits the master's `_pull_from_peer_ahead` to
`_FETCH_POOL` (never inline on the send pool). The pull uses the existing
`request_missing_blocks` + `_apply_fetched_blocks`, so the one acceptance
gate and the A9 relay-onward both apply.

MODELLING THE ASYMMETRY in one process: Y is a real in-process master with
its real P2P listener running and NO peer entry for X (equivalent to every
announce from Y to X failing -- X hears nothing either way). X lists Y as a
peer. Both adopt Y's exported genesis (the real deployment path).

CHECKS (in-process, two real masters, real sockets for X->Y; ~10 s):
  T1  set-up: X height 2, Y height 4, X's heartbeat is answered known/4
  T2  after one _gossip_tip X converges to Y's height (the A13 fix itself)
  T3  the pull ran on a covenant-fetch thread, not a send-pool worker
  T4  peer_ahead recorded, peer_ahead_seen counted, /health exposes it
  T5  X relayed what it pulled onward (A9: announce with Y excluded)
  T6  lying peer (height 10**9, serves nothing): exactly one BLOCK_REQUEST
      per cooldown, chain intact, peer_ahead_empty recorded, no exception
  T7  garbage heights (bool / float / str / None / negative / equal / lower)
      never trigger a pull
  T8  a real (non-gossip) announce reply is read the same way
"""
import json
import os
import socket
import sys
import tempfile
import threading
import time

os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_CATCHUP_COOLDOWN", "2.0")   # make the gate visible
os.environ.setdefault("COVENANT_SKIP_PREFLIGHT", "1")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
import covenant_unified_v8 as cov  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail and not ok else ""))


def fresh_master(name, port, genesis_path=None):
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    if genesis_path:
        assert m.load_canonical_genesis(genesis_path)
    else:
        m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    return m


def value_block(m):
    """A zero-value, registration-PoW'd, signed block on top of m's tip (the
    test_a11 recipe). Returns the mined Block; caller applies it."""
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    tx = cov.Transaction(sender_pubkey=pem, receiver="HUMANITY", data={"origin": "human"},
                         amount=0.0, benefit_score=m.node.governor.get_current(), reg_nonce=reg)
    tx.sign(k)
    b = cov.Block(len(m.node.chain), [tx], m.node.chain[-1].hash)
    b.stake_rewards = 0.0
    b.alignment_score = tx.benefit_score
    b.mine()
    return b


def clone_block(b):
    raw = cov.asdict(b)
    txs = [cov.Transaction(**t) for t in raw["transactions"]]
    c = cov.Block(raw["index"], txs, raw["previous_hash"])
    c.timestamp = raw["timestamp"]; c.nonce = raw["nonce"]; c.hash = raw["hash"]
    c.alignment_score = raw["alignment_score"]; c.stake_rewards = raw["stake_rewards"]
    return c


def kinds(m):
    return {k: v["baseline"] for k, v in m.node.anomaly_monitor.report()["per_kind"].items()}


def wait_for(pred, timeout=10.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.05)
    return pred()


def main():
    X_PORT, Y_PORT = 19300, 19312          # 12 apart (M2)
    # ---- Y: founder, exports genesis, mints 1..3, listener up, NO peers
    y = fresh_master("Y", Y_PORT)
    gpath = tempfile.mktemp(suffix="_genesis.json")
    y.export_genesis(gpath)
    blocks = []
    for _ in range(3):
        b = value_block(y)
        assert y._accept_block_common(b)
        blocks.append(b)
    y.node.running = True
    threading.Thread(target=y._listen_for_peers, daemon=True).start()
    time.sleep(0.3)

    # ---- X: adopts the genesis, holds block 1 only, lists Y as its peer
    x = fresh_master("X", X_PORT, gpath)
    assert x._accept_block_common(clone_block(blocks[0]))
    x.node.running = True
    x.node.add_peer("Y", "127.0.0.1", Y_PORT + 1)
    pid = x.node.resolve_peer_id("127.0.0.1", Y_PORT + 1)

    # T1 -- the reply X's heartbeat gets from Y
    verdict = x.node._send_raw("127.0.0.1", Y_PORT + 1, json.dumps(
        {"type": "BLOCK_ANNOUNCE", "index": 1, "hash": x.node.chain[1].hash,
         "node_id": "X", "p2p_port": X_PORT + 1, "gossip": True}))
    check("T1 X height 2, Y height 4", len(x.node.chain) == 2 and len(y.node.chain) == 4,
          f"X={len(x.node.chain)} Y={len(y.node.chain)}")
    check("T1 Y answers X's heartbeat known with ITS height (4)",
          isinstance(verdict, dict) and verdict.get("outcome") == "known" and verdict.get("height") == 4, verdict)
    check("T1 Y has no route to X (one-way)", not y.node.peers, y.node.peers)
    # that probe bypassed the hook (it called _send_raw directly): nothing pulled
    time.sleep(0.3)
    check("T1 a bare _send_raw still pulls nothing (the hook is in the announce path)",
          len(x.node.chain) == 2 and getattr(x.node, "peer_ahead_seen", 0) == 0)

    # T2/T3 -- the fix: one heartbeat, X converges; the pull ran on the fetch pool
    threads = []
    orig_rmb = x.node.request_missing_blocks
    def tapped(host, port, from_index):
        threads.append(threading.current_thread().name)
        return orig_rmb(host, port, from_index)
    x.node.request_missing_blocks = tapped
    n = x._gossip_tip("periodic")
    converged = wait_for(lambda: len(x.node.chain) == 4, 10)
    check("T2 one heartbeat to a peer that is ahead pulls the gap: X now at Y's height",
          n == 1 and converged and x.node.chain[-1].hash == y.node.chain[-1].hash,
          f"X={len(x.node.chain)} Y={len(y.node.chain)} (pre-fix record on v8.24: X stays at 2)")
    check("T3 the pull ran on a covenant-fetch thread (not the send pool)",
          threads and all(t.startswith("covenant-fetch") for t in threads), threads)
    k = kinds(x)
    check("T4 peer_ahead recorded once, peer_ahead_filled recorded",
          k.get("peer_ahead", 0) == 1 and k.get("peer_ahead_filled", 0) == 1, k)
    check("T4 peer_ahead_seen counted", getattr(x.node, "peer_ahead_seen", 0) == 1, getattr(x.node, "peer_ahead_seen", 0))
    with x.api.app.test_client() as c:
        h = c.get("/health").get_json()
    check("T4 /health exposes peer_ahead_seen", h.get("peer_ahead_seen") == 1, h.get("peer_ahead_seen"))

    # T5 -- relay onward (A9): what X pulled it announces, excluding Y
    seen = []
    Z_PORT = Y_PORT + 12
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", Z_PORT)); srv.listen(8); srv.settimeout(60)   # was 15: expired once under a 6-suite parallel load (08-22 run)
    z_height = [0]   # Z answers honestly (0) during T5; T6 turns it into a liar.
    # (Was a fixed 10**9 from the start: then Z and Y BOTH answered "ahead" to the
    # T5 heartbeat, and whichever _delivery_order put first consumed the one
    # catch-up cooldown -- Z first meant X pulled nothing from Y and T5 failed
    # ~1 run in 4 on v8.25 and v8.26 alike. A liar starving the honest peer for
    # one cooldown is the designed cost of the cooldown, not a defect.)
    def serve_z(reply_height):
        while True:
            try:
                c, _ = srv.accept()
            except Exception:
                return
            try:
                buf = b"".join(iter(lambda: c.recv(4096), b""))
                msg = json.loads(buf.decode())
                seen.append(msg)
                if msg.get("type") == "BLOCK_ANNOUNCE":
                    c.sendall(json.dumps({"ok": True, "outcome": "known",
                                          "height": z_height[0]}).encode())
                elif msg.get("type") == "BLOCK_REQUEST":
                    c.sendall(json.dumps({"blocks": []}).encode())
            except Exception:
                pass
            finally:
                c.close()
    threading.Thread(target=serve_z, args=(10 ** 9,), daemon=True).start()
    x.node.add_peer("Z", "127.0.0.1", Z_PORT)
    # re-run the pull path with Z listening: X is at 4 now, so build block 4 on Y
    b4 = value_block(y); assert y._accept_block_common(b4)
    time.sleep(2.1)                       # let the catch-up cooldown expire
    x.node.peer_ahead_seen = 0
    x._gossip_tip("periodic")
    wait_for(lambda: len(x.node.chain) == 5, 10)
    wait_for(lambda: any(m.get("type") == "BLOCK_ANNOUNCE" and m.get("index") == 4
                         and "gossip" not in m for m in seen), 5)
    relayed = [m for m in seen if m.get("type") == "BLOCK_ANNOUNCE" and m.get("index") == 4 and "gossip" not in m]
    check("T5 X pulled block 4 from Y and RELAYED it to Z as a real announce (A9 path)",
          len(x.node.chain) == 5 and len(relayed) == 1, f"X={len(x.node.chain)} relayed={len(relayed)}")

    # T6 -- Z lies (height 1e9) and serves nothing: one request per cooldown, no harm
    z_height[0] = 10 ** 9
    time.sleep(2.1)
    seen.clear()
    k0 = kinds(x)
    x._gossip_tip("periodic")             # goes to Y (known/5) and Z (known/1e9)
    wait_for(lambda: kinds(x).get("peer_ahead_empty", 0) > k0.get("peer_ahead_empty", 0), 5)
    x._gossip_tip("periodic")             # inside the cooldown: no second pull
    time.sleep(1.0)
    reqs = [m for m in seen if m.get("type") == "BLOCK_REQUEST"]
    k1 = kinds(x)
    check("T6 lying peer: exactly one BLOCK_REQUEST to it within one cooldown",
          len(reqs) == 1, f"requests={len(reqs)} seen={[m.get('type') for m in seen]}")
    check("T6 lying peer: chain intact, peer_ahead_empty recorded, nothing failed",
          len(x.node.chain) == 5 and k1.get("peer_ahead_empty", 0) == k0.get("peer_ahead_empty", 0) + 1
          and k1.get("peer_ahead_failed", 0) == 0, k1)
    check("T6 both ahead-replies were counted even though only one pulled",
          x.node.peer_ahead_seen >= 2, x.node.peer_ahead_seen)

    # T7 -- garbage heights never pull (drive _send_announce with a stubbed _send_raw)
    pulls = []
    x.node.on_peer_ahead = lambda *a: pulls.append(a)
    real_send = x.node._send_raw
    for bad in [True, 5.0, "9", None, -1, 5, 4, {"h": 9}, [9]]:
        x.node._send_raw = lambda h, p, d, attempts=3, _b=bad: {"ok": True, "outcome": "known", "height": _b}
        before = x.node.peer_ahead_seen
        time.sleep(2.1)
        x.node._send_announce("127.0.0.1", 1, "{}", "p")
        check(f"T7 height={bad!r} ({type(bad).__name__}) does not pull or count",
              not pulls and x.node.peer_ahead_seen == before, pulls)
    x.node._send_raw = lambda h, p, d, attempts=3: None
    x.node._send_announce("127.0.0.1", 1, "{}", "p")
    check("T7 a silent peer (None verdict) does not pull", not pulls)
    x.node._send_raw = lambda h, p, d, attempts=3: {"ok": True, "outcome": "known", "height": 6}
    time.sleep(2.1)
    x.node._send_announce("127.0.0.1", 1, "{}", "p")
    wait_for(lambda: pulls, 5)            # the hook is submitted to _FETCH_POOL, not called inline
    check("T7 a real int above ours DOES pull (control)", len(pulls) == 1 and pulls[0] == ("127.0.0.1", 1, "p"), pulls)
    x.node._send_raw = real_send
    x.node.on_peer_ahead = x._pull_from_peer_ahead

    # T8 -- a real (non-gossip) announce reply is read too
    with x.node.peers_lock:
        x.node.peers.pop("Z", None)
    b5 = value_block(y); assert y._accept_block_common(b5)
    time.sleep(2.1)
    x.node.announce_block(x.node.chain[-1])        # non-gossip announce of our tip (block 4) to Y
    check("T8 a non-gossip announce whose reply shows the peer ahead also pulls",
          wait_for(lambda: len(x.node.chain) == 6, 10), f"X={len(x.node.chain)}")

    srv.close(); x.node.running = False; y.node.running = False
    p = sum(1 for _, ok in results if ok); f = len(results) - p
    print(f"\n{p}/{len(results)} passed" + (f", {f} FAILED" if f else ""))
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
