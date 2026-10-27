"""
A1 -- block propagation must survive node kills (real processes, hard kills).

Line topology A -- B -- C; C is never a peer of A, so every block that reaches
C did so by relay through B. Every kill is SIGKILL (no shutdown hook runs),
every restart reuses the node's own db, so what is tested is the persisted
state plus the boot-time sync paths, not a clean exit.

  K1  the bridge is dead while the block is mined. B is killed; A mines
      (A's announce to B fails, peer_send_failure); B restarts on its old db.
      B must pull the block from A by bootstrap AND relay it to C (v8.19).
  K2  the miner dies right after /mine returns. A is killed within the same
      second as the mine; whatever A managed to announce, the network must
      end converged once A is back. This is the case where the restarted
      node is AHEAD of its peers.
  K3  the leaf dies mid-flight. C is killed before the block exists, A mines,
      B relays into a dead socket, C restarts on its old db and must catch up
      from B without any new block being minted.
  K4  a node's own db survives the kill: after every restart the node's
      height is >= what it held when killed (no silent rollback).
  K5  (in-process) periodic tip gossip: with COVENANT_TIP_GOSSIP_INTERVAL
      small, a node that is ahead and idle announces its tip to a peer
      without any mine or restart -- the partition-heals case K2 cannot
      reach with signals alone (a SIGSTOPped peer still queues TCP in its
      backlog, so "dropped" cannot be staged that way).

Pre-fix (v8.19) K2 failed 3/3 checks: the restarted miner bootstrapped
nothing (it was ahead), announced nothing, and B and C stayed at genesis for
the whole 30 s window. v8.20 adds push-on-boot + periodic tip gossip.

Env: both COVENANT_INSECURE_MOCK_JUDGE=1 and COVENANT_JUDGE_PROVIDERS=mock.
Ports: --port N occupies N, N+1, N+11; --peers takes API+1.
"""
import os, sys, json, time, signal, subprocess, socket, threading, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_a9_relay_race import Net, http, check, results

# ---------------------------------------------------------------------------
# THE SAMPLING WINDOW.  Fixed 2026-08-29, and the assertion below is untouched.
#
# K1 and K3 have been red on every Windows sweep and green on every Linux one,
# with the same node and the same assertion. The cause is not the node and not
# the check -- it is WHEN the check looks.
#
# A broadcast is `_SEND_POOL.submit`, i.e. asynchronous. Against a peer whose
# port REFUSES -- which is what killing a process gives you on Linux -- one
# `_send_raw` fails in ~0.13 s. Against a peer that ACCEPTS AND HOLDS -- which
# is what it gives you on Windows -- it costs the full retry budget: 3 attempts
# x PEER_SEND_TIMEOUT_S plus the phi backoff sleeps, ~15.1 s at the defaults
# (the node's own A12 comment states this figure, and this suite does not
# override the timeout).
#
# The test slept 3.0 s and then read /anomalies. It was looking TWELVE SECONDS
# before the evidence could exist, and reporting the empty result as the node's
# failure.
#
# Section 0 forbids weakening a control to make a test pass, and nothing here
# does: the predicate is still exactly `"peer_send_failure" in anomalies`, and
# a peer that never records one still fails. What changes is that the suite now
# waits out the budget it is measuring against before deciding the evidence is
# absent. "It never appeared" and "I looked before it could appear" are
# different findings and only one of them is about the node.
#
# It also fixes P7. The instrumentation below was added on 2026-08-23 to answer
# whether A12's backoff had skipped the send, and was left for "the next
# Windows sweep" to report. That sweep reported `dead_peers 0->0,
# heartbeats_skipped 0->0` -- which looks like a refutation and is not one,
# because the `post` reading was taken at the SAME too-early moment as the
# assertion it was meant to explain. Both hypotheses predict 0 inside the blind
# window. The reading is now taken after the wait, so it can finally
# discriminate.
PEER_SEND_TIMEOUT_S = float(os.environ.get("COVENANT_PEER_SEND_TIMEOUT", "5"))
SEND_BUDGET_S = 3 * PEER_SEND_TIMEOUT_S + 3.0     # + phi backoff sleeps, + margin


def wait_anomaly(n, nid, kind, budget=None):
    """Poll /anomalies until `kind` appears, or the send budget elapses.

    Returns (present, waited_s) so the check's own detail line can say how long
    it looked -- a bounded wait that reports its bound is a measurement; one
    that does not is a magic number waiting to become wrong on a new platform.
    """
    budget = SEND_BUDGET_S if budget is None else budget
    t0 = time.time()
    while time.time() - t0 < budget:
        if kind in n.anomalies(nid):
            return True, round(time.time() - t0, 1)
        time.sleep(0.5)
    return kind in n.anomalies(nid), round(time.time() - t0, 1)


def p7(n, nid, when):
    """P7 (2026-08-23): MEASURE, do not guess.

    On Windows K1/K3 fail their "A recorded the failed delivery, not silence"
    assertion: /anomalies holds peer_message_error but NOT peer_send_failure,
    which means the node did not ATTEMPT the send. The standing hypothesis is
    that A12's dead-peer backoff had already marked the peer suspect and the
    broadcast skipped it -- in which case the node is behaving correctly and the
    missing thing is the RECORD, not the delivery.

    That hypothesis has never been measured. `dead_peers` and
    `heartbeats_skipped` are both on /health and answer it directly, so this
    prints them either side of the kill instead of anyone reasoning about it.
    It asserts NOTHING: the next Windows sweep's output carries the answer, and
    whoever reads it can then change the right thing.

    Deliberately not fixed here. "A skipped block delivery should leave a trace"
    is probably right, but a heartbeat skip must NOT -- it would flood
    /anomalies with exactly the tonic signal this project spent 2026-08-23
    removing from watchdog.log. Getting that distinction wrong is worse than
    the current gap.
    """
    try:
        _, h = http("GET", n.api[nid], "/health")
    except Exception as e:
        print(f"  P7 [{when}] {nid}: /health unavailable ({type(e).__name__})")
        return {}
    got = {k: h.get(k) for k in ("dead_peers", "heartbeats_skipped",
                                 "peers", "chain_height")}
    kinds = sorted(n.anomalies(nid))
    print(f"  P7 MEASUREMENT [{when}] {nid}: dead_peers={got.get('dead_peers')} "
          f"heartbeats_skipped={got.get('heartbeats_skipped')} "
          f"peers={got.get('peers')} kinds={kinds}")
    return got


class KNet(Net):
    def wait_height(self, nid, target, t=30):
        # /chain is rate-limited to 20 reads / 60 s per node; K2 polls three
        # nodes for 30 s, so poll slowly and treat a 429 as "not yet".
        t0 = time.time()
        while time.time() - t0 < t:
            try:
                if self.height(nid) >= target:
                    return True
            except Exception:
                pass
            time.sleep(3.0)
        return False

    def tip(self, nid):
        for _ in range(5):
            st, ch = http("GET", self.api[nid], "/chain")
            if st == 200:
                c = ch.get("chain", ch if isinstance(ch, list) else [])
                return c[-1].get("hash", "") if c else ""
            time.sleep(3.0)
        return "<rate-limited>"

    def log_has(self, nid, needle, wait_s=0.0):
        """wait_s: the boot push runs 1.5 s after start (_bootstrap_once's
        settle delay) and the process block-buffers stdout, so a check that
        follows an instantly-satisfied convergence wait (the kill lost the
        race and B already held the block) must give it time. Harness-only:
        observed once 2026-08-22 against v8.23 with B=2 at the kill."""
        t0 = time.time()
        while True:
            for name in (f"{nid}.log", f"{nid}.restart.log"):
                lp = os.path.join(self.work, name)
                if os.path.exists(lp) and needle in open(lp).read():
                    return True
            if time.time() - t0 >= wait_s:
                return False
            time.sleep(0.5)

    def kill(self, nid):
        p, logf = self.procs.pop(nid)
        p.kill(); p.wait(timeout=10)
        logf.close()

    def restart(self, nid, peers):
        """Same db, same key, new process. Log goes to <nid>.restart.log."""
        env = dict(os.environ, COVENANT_JUDGE_PROVIDERS="mock", COVENANT_INSECURE_MOCK_JUDGE="1",
                   COVENANT_GENESIS=self.genesis, COVENANT_DB_PATH=os.path.join(self.work, f"{nid}.db"),
                   PYTHONUNBUFFERED="1")   # the boot-push line must reach the log before we read it
        cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "covenant_unified_v8.py"),
               "--real", "--port", str(self.api[nid]), "--node-id", nid, "--genesis", self.genesis]
        if peers:
            cmd += ["--peers", ",".join(f"127.0.0.1:{self.api[p] + 1}" for p in peers)]
        logf = open(os.path.join(self.work, f"{nid}.restart.log"), "a")
        p = subprocess.Popen(cmd, env=env, stdout=logf, stderr=subprocess.STDOUT)
        self.procs[nid] = (p, logf)
        return self.wait_http(self.api[nid])

    def mine(self, nid, receiver, amount):
        st, r = self.submit_tx(nid, receiver, amount)
        if st != 200:
            return st, r
        return self.op_post(nid, "/mine", {})


def k1(base):
    print("\n== K1: bridge B is dead while A mines; B restarts on its old db ==")
    n = KNet(base)
    try:
        ok = n.launch("A", ["B"]) and n.launch("B", ["A", "C"]) and n.launch("C", ["B"])
        check("K1 three nodes up", ok)
        time.sleep(3.0)  # let every bootstrap round finish so the kill is the only variable
        n.kill("B")
        pre = p7(n, "A", "after kill, before mine")      # P7
        s, r = n.mine("A", n.pem("C"), 3.0)
        check("K1 A mined while B was dead", s == 200 and n.height("A") == 2, f"HTTP {s}")
        check("K1 C cannot have the block yet (its only peer is dead)", n.height("C") == 1, f"C={n.height('C')}")
        seen, waited = wait_anomaly(n, "A", "peer_send_failure")
        post = p7(n, "A", f"after the send budget ({waited}s)")   # P7, after the wait
        check("K1 A recorded the failed delivery, not silence",
              "peer_send_failure" in n.anomalies("A"),
              f"waited {waited}s of {SEND_BUDGET_S}s budget | "
              f"kinds={sorted(n.anomalies('A'))} | P7 dead_peers "
              f"{pre.get('dead_peers')}->{post.get('dead_peers')} "
              f"heartbeats_skipped {pre.get('heartbeats_skipped')}->"
              f"{post.get('heartbeats_skipped')}")
        check("K1 B restarted on its old db", n.restart("B", ["A", "C"]))
        check("K1 B pulled the block from A", n.wait_height("B", 2, 25), f"B={n.height('B')}")
        check("K1 C received it by relay from the restarted B", n.wait_height("C", 2, 25), f"C={n.height('C')}")
        tips = {x: n.tip(x)[:12] for x in "ABC"}
        check("K1 converged tip", len(set(tips.values())) == 1, tips)
    finally:
        n.stop()


def k2(base):
    print("\n== K2: miner A is SIGKILLed in the same second /mine returns ==")
    n = KNet(base)
    try:
        ok = n.launch("A", ["B"]) and n.launch("B", ["A", "C"]) and n.launch("C", ["B"])
        check("K2 three nodes up", ok)
        time.sleep(3.0)
        s, r = n.mine("A", n.pem("B"), 4.0)
        n.kill("A")                      # no grace: whatever went out, went out
        check("K2 /mine had returned 200 before the kill", s == 200, f"HTTP {s}")
        hB0, hC0 = n.height("B"), n.height("C")
        print(f"  (observed) right after the kill: B={hB0} C={hC0}")
        check("K2 A restarted on its old db (the mined block is in it)", n.restart("A", ["B"]))
        check("K2 A still holds its block after the hard kill (K4)", n.height("A") == 2, f"A={n.height('A')}")
        gotB = n.wait_height("B", 2, 30); gotC = n.wait_height("C", 2, 30)
        check("K2 B converged to the restarted miner's height", gotB, f"B={n.height('B')}")
        check("K2 C converged too", gotC, f"C={n.height('C')}")
        tips = {x: n.tip(x)[:12] for x in "ABC"}
        check("K2 converged tip", len(set(tips.values())) == 1, tips)
        check("K2 the restarted miner PUSHED its tip at boot (v8.20)",
              n.log_has("A", "boot: announced tip index 1", wait_s=10))
    finally:
        n.stop()


def k3(base):
    print("\n== K3: leaf C is dead during the mine; restarts on its old db with no new block ==")
    n = KNet(base)
    try:
        ok = n.launch("A", ["B"]) and n.launch("B", ["A", "C"]) and n.launch("C", ["B"])
        check("K3 three nodes up", ok)
        time.sleep(3.0)
        n.kill("C")
        pre = p7(n, "B", "after kill, before mine")      # P7 (B is C's only peer)
        s, r = n.mine("A", n.pem("B"), 2.0)
        check("K3 A mined while C was dead", s == 200, f"HTTP {s}")
        check("K3 B got it", n.wait_height("B", 2, 20), f"B={n.height('B')}")
        seen3, waited3 = wait_anomaly(n, "B", "peer_send_failure")
        post = p7(n, "B", f"after the send budget ({waited3}s)")  # P7, after the wait
        check("K3 B recorded the failed relay to dead C",
              "peer_send_failure" in n.anomalies("B"),
              f"waited {waited3}s of {SEND_BUDGET_S}s budget | "
              f"kinds={sorted(n.anomalies('B'))} | P7 dead_peers "
              f"{pre.get('dead_peers')}->{post.get('dead_peers')} "
              f"heartbeats_skipped {pre.get('heartbeats_skipped')}->"
              f"{post.get('heartbeats_skipped')}")
        check("K3 C restarted on its old db", n.restart("C", ["B"]))
        check("K3 C caught up from B with no new block minted", n.wait_height("C", 2, 30), f"C={n.height('C')}")
        check("K3 C did not roll back below genesis (K4)", n.height("C") >= 1)
        tips = {x: n.tip(x)[:12] for x in "ABC"}
        check("K3 converged tip", len(set(tips.values())) == 1, tips)
    finally:
        n.stop()


def k5():
    print("\n== K5: periodic tip gossip reaches an idle peer with no mine and no restart ==")
    os.environ["COVENANT_TIP_GOSSIP_INTERVAL"] = "2"
    import importlib, covenant_unified_v8 as cov
    importlib.reload(cov)   # pick up the interval at import time
    check("K5 interval honoured at import", cov.TIP_GOSSIP_INTERVAL_S == 2.0, cov.TIP_GOSSIP_INTERVAL_S)
    # A fake peer: records every frame that lands on its P2P port.
    seen = []
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0)); srv.listen(8); fake_port = srv.getsockname()[1]
    def serve():
        srv.settimeout(20)
        while True:
            try:
                c, _ = srv.accept()
            except Exception:
                return
            try:
                buf = b"".join(iter(lambda: c.recv(4096), b""))
                seen.append(json.loads(buf.decode()))
                c.sendall(json.dumps({"ok": True, "outcome": "known", "height": 1}).encode())
            except Exception:
                pass
            finally:
                c.close()
    threading.Thread(target=serve, daemon=True).start()
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster("k5", host="127.0.0.1", port=18700, p2p_port=18701, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)  # as test_a4 does
    m.node.add_peer("fake", "127.0.0.1", fake_port)
    m.node.running = True
    # at genesis: A17 (v8.28) -- the genesis tip IS announced now (it is the
    # probe that lets a one-way-peered node learn the peer's height via A13);
    # before v8.28 this asserted == 0 ("nothing to say").
    check("K5 a node at genesis gossips its genesis tip to its peer (A17)", m._gossip_tip("test") == 1)
    time.sleep(0.5)
    check("K5 the genesis announce names index 0", any(f.get("type") == "BLOCK_ANNOUNCE" and f.get("index") == 0 for f in seen), seen[:1])
    # give it one real block the cheap way: the same minting path /mine uses
    # is heavy; a direct announce of a second block is what the loop would do,
    # so mint via the acceptor is unnecessary -- append a mined block instead.
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    tx = cov.Transaction(sender_pubkey=pem, receiver="HUMANITY", data={"origin": "human"}, amount=0.0,
                         benefit_score=m.node.governor.get_current(), reg_nonce=reg)
    tx.sign(k)
    b = cov.Block(1, [tx], m.node.chain[-1].hash)
    b.stake_rewards = 0.0; b.alignment_score = tx.benefit_score; b.mine()
    check("K5 block accepted locally", m._accept_block_common(b) and len(m.node.chain) == 2,
          dict(m.node.anomaly_monitor.per_kind_counts()) if hasattr(m.node.anomaly_monitor, "per_kind_counts") else "")
    seen.clear()
    threading.Thread(target=m._tip_gossip_loop, daemon=True).start()
    t0 = time.time()
    while time.time() - t0 < 10 and not any(f.get("type") == "BLOCK_ANNOUNCE" for f in seen):
        time.sleep(0.2)
    ann = [f for f in seen if f.get("type") == "BLOCK_ANNOUNCE"]
    check("K5 an idle, ahead node announced its tip within 10 s with no mine and no restart",
          bool(ann), f"{len(seen)} frame(s) in {time.time()-t0:.1f}s")
    check("K5 the event names the tip (index 1, its hash)",
          bool(ann) and ann[0].get("index") == 1 and ann[0].get("hash") == b.hash, ann[:1])
    m.node.running = False
    srv.close()
    del os.environ["COVENANT_TIP_GOSSIP_INTERVAL"]


def main():
    k1(18400); k2(18500); k3(18600); k5()
    p = sum(1 for _, ok in results if ok); f = len(results) - p
    print(f"\n{p}/{len(results)} passed" + (f", {f} FAILED" if f else ""))
    sys.exit(1 if f else 0)

if __name__ == "__main__":
    main()
