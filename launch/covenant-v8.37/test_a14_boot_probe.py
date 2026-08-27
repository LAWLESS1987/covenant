#!/usr/bin/env python3
"""
A14 -- boot-time catch-up was sequential over peers (v8.26 fix: concurrent
probe through _FETCH_POOL, results applied in order of arrival).

THE HAZARD, measured on v8.25 (pre-fix record, P2 below). `bootstrap_chain`
called `request_missing_blocks` peer by peer. Every DROPPED (non-refusing)
peer costs one full PEER_SEND_TIMEOUT_S before the next peer is even asked,
so with D dead peers listed before the one live peer the node spends
D x timeout before it learns anything, and -- because the boot push
(`_gossip_tip("boot")`, A1/K2's path home) runs only after `bootstrap_chain`
returns -- D x timeout before a restarted miner tells anyone about the block
it mined just before the kill. Six rounds never help: a round with zero gain
ends the loop, but the FIRST round is always paid in full. `/sync` is the
same loop inside an HTTP worker (rounds=1), so an operator's recovery lever
hangs for D x timeout as well. At the defaults (5 s) a stale peer list of 8
dead entries is 40 s of boot latency; the measured figure here at 0.5 s is
~4 s vs ~0.5 s after the fix.

FIX (v8.26). One round now submits `request_missing_blocks` for EVERY peer to
`_FETCH_POOL` at once (bounded by MAX_CONCURRENT_FETCHES, so N dead peers
cost ceil(N / 32) x timeout, not N x timeout), waits with a bounded deadline
(BOOT_PROBE_DEADLINE_S = 2 x PEER_SEND_TIMEOUT_S + 1; stragglers are
recorded as `bootstrap_probe_timeout` and their result is discarded), and
applies replies in the order they ARRIVED through the unchanged
`_apply_fetched_blocks` gate. A reply whose blocks are all already held
(the usual case for the second answering peer) is skipped by index before
the gate so it does not record a spurious `block_already_held`. Nothing is
weakened: same request frame, same acceptance gate, same A9 relay-onward,
same six-round/pause shape, same `/sync` contract.

CHECKS (in-process, real masters, real sockets, real blackholes; ~20 s):
  P1  set-up: live peer L at height 3, joiner J at 1, D blackholes listed
      BEFORE L in J's peer table
  P2  bootstrap_chain latency: v8.25 >= D x timeout; v8.26 < 2 x timeout
      (the fix itself) -- and J converges to L's height either way
  P3  J relayed what it pulled onward with L excluded (A9 preserved)
  P4  no `block_already_held` recorded when TWO live peers both answer
      with the same blocks (arrival-order apply + index skip)
  P5  /sync has the same bound (rounds=1) and the same result
  P6  a peer whose reply never completes within the deadline is recorded
      as bootstrap_probe_timeout and does not hold the boot (v8.26 only)
  P7  the boot push follows promptly: _bootstrap_once's
      `boot: announced tip` reaches a live peer within 2 x timeout of start
      when D dead peers precede it (K2's path home)
  P8  import-time arithmetic: ceil(D/MAX_CONCURRENT_FETCHES) x timeout bound
      holds for D = 2 x MAX_CONCURRENT_FETCHES blackholes (worst case in
      one round; not run live with 64 sockets at the default, computed from
      the module's constants and checked live at D = 8)
"""
import io
import json
import math
import os
import socket
import sys
import tempfile
import threading
import time
from contextlib import redirect_stdout

os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_SKIP_PREFLIGHT", "1")
os.environ.setdefault("COVENANT_PEER_SEND_TIMEOUT", "0.5")
os.environ.setdefault("COVENANT_TIP_GOSSIP_INTERVAL", "0")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
import covenant_unified_v8 as cov  # noqa: E402

TIMEOUT = cov.PEER_SEND_TIMEOUT_S
FIXED = hasattr(cov, "BOOT_PROBE_DEADLINE_S")
results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


class Blackhole:
    """A port that completes no handshake: listen(0) with the one slot taken."""
    def __init__(self):
        self.l = socket.socket(); self.l.bind(("127.0.0.1", 0)); self.l.listen(0)
        self.port = self.l.getsockname()[1]
        self.plug = socket.socket(); self.plug.settimeout(1); self.plug.connect(("127.0.0.1", self.port))
    def close(self):
        self.plug.close(); self.l.close()


class Trickler:
    """Accepts a BLOCK_REQUEST and never finishes the reply (sends one byte
    every 0.2 s so the socket timeout never fires) -- a peer that is up but
    wedged. Only v8.26's deadline bounds it."""
    def __init__(self):
        self.srv = socket.socket(); self.srv.bind(("127.0.0.1", 0)); self.srv.listen(8)
        self.port = self.srv.getsockname()[1]
        self.stop = False
        threading.Thread(target=self._serve, daemon=True).start()
    def _serve(self):
        while not self.stop:
            try: c, _ = self.srv.accept()
            except Exception: return
            def drip(c=c):
                try:
                    b"".join(iter(lambda: c.recv(4096), b""))
                    while not self.stop:
                        c.sendall(b" "); time.sleep(0.2)
                except Exception: pass
                finally: c.close()
            threading.Thread(target=drip, daemon=True).start()
    def close(self):
        self.stop = True; self.srv.close()


class Recorder:
    """A fake peer that records every frame it receives, with arrival time."""
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
                self.seen.append((time.monotonic(), json.loads(buf.decode())))
                c.sendall(json.dumps({"ok": True, "outcome": "known", "height": 99}).encode())
            except Exception: pass
            finally: c.close()
    def close(self): self.srv.close()


_port = [23100]
def next_port():
    _port[0] += 12
    return _port[0]


def fresh_master(name, genesis_path=None, listen=False):
    port = next_port()
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    if genesis_path:
        assert m.load_canonical_genesis(genesis_path)
    else:
        m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    m.node.running = True
    if listen:
        threading.Thread(target=m._listen_for_peers, daemon=True).start()
        time.sleep(0.3)
    return m


def value_block(m):
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


def add_peer(m, pid, port):
    with m.node.peers_lock:
        m.node.peers[pid] = ("127.0.0.1", port)


def wait_for(pred, timeout=10.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def main():
    print(f"A14 boot probe -- source {'v8.26+ (fixed)' if FIXED else 'pre-fix'}; "
          f"PEER_SEND_TIMEOUT_S={TIMEOUT}, MAX_CONCURRENT_FETCHES={cov.MAX_CONCURRENT_FETCHES}")
    gen = tempfile.mktemp(suffix="_genesis.json")
    L = fresh_master("L", listen=True)
    L.export_genesis(gen)
    for _ in range(2):
        assert L._accept_block_common(value_block(L))
    L2 = fresh_master("L2", genesis_path=gen, listen=True)
    for b in L.node.chain[1:]:
        assert L2._accept_block_common(clone_block(b))

    D = 8
    holes = [Blackhole() for _ in range(D)]
    rec = Recorder()

    # ---------------- P1 / P2: D dead peers listed before the live one
    J = fresh_master("J", genesis_path=gen)
    for i, h in enumerate(holes):
        add_peer(J, f"dead{i}", h.port)
    add_peer(J, "L", L.node.port)
    add_peer(J, "rec", rec.port)
    check("P1 set-up: L at 3, J at 1, 8 blackholes listed before L",
          len(L.node.chain) == 3 and len(J.node.chain) == 1 and len(J.node.peers) == D + 2)
    t0 = time.monotonic()
    gained = J.bootstrap_chain()
    dt = time.monotonic() - t0
    check("P2a J converged to L's height", len(J.node.chain) == 3 and gained == 2,
          f"height {len(J.node.chain)} gained {gained}")
    if FIXED:
        # two rounds run (round 1 gains, round 2 confirms nothing more) + one pause
        check(f"P2b bootstrap_chain with {D} dead peers ahead of L took < 2 rounds x timeout + pause",
              dt < 2 * TIMEOUT + 1.0 + 0.5, f"{dt:.2f} s (v8.25: {2*D*TIMEOUT+1.0:.1f} s)")
    else:
        check(f"P2b (PRE-FIX RECORD) bootstrap_chain paid >= {D} x timeout sequentially",
              dt >= D * TIMEOUT, f"{dt:.2f} s")
    # A9 relay onward: rec must have seen a BLOCK_ANNOUNCE for index 2
    ok = wait_for(lambda: any(f.get("type") == "BLOCK_ANNOUNCE" and f.get("index") == 2
                              for _, f in rec.seen), 5)
    check("P3 J relayed the pulled tip onward (A9 preserved)", ok,
          f"frames: {[f.get('type') for _, f in rec.seen]}")
    kj = kinds(J)
    check("P3b catchup_failed is D per round -- none attributed to L",
          kj.get("catchup_failed", 0) % D == 0 and kj.get("catchup_failed", 0) > 0, f"{kj}")

    # ---------------- P4: two live peers answer with the same blocks
    J2 = fresh_master("J2", genesis_path=gen)
    add_peer(J2, "L", L.node.port)
    add_peer(J2, "L2", L2.node.port)
    gained = J2.bootstrap_chain()
    k2 = kinds(J2)
    check("P4a joiner with two live peers converges", len(J2.node.chain) == 3 and gained == 2,
          f"height {len(J2.node.chain)} gained {gained}")
    if FIXED:
        check("P4b no block_already_held recorded for the duplicate reply",
              k2.get("block_already_held", 0) == 0, f"{k2}")
    else:
        check("P4b (PRE-FIX RECORD) sequential pull asks L2 after L: either no duplicate "
              "(L2 answered an empty gap) -- informational", True, f"{k2}")

    # ---------------- P5: /sync
    J3 = fresh_master("J3", genesis_path=gen)
    for i, h in enumerate(holes):
        add_peer(J3, f"dead{i}", h.port)
    add_peer(J3, "L", L.node.port)
    t0 = time.monotonic()
    gained = J3.bootstrap_chain(rounds=1, pause=0.0)   # exactly what /sync calls
    dt = time.monotonic() - t0
    check("P5a /sync-shaped call (rounds=1) converges", len(J3.node.chain) == 3 and gained == 2)
    if FIXED:
        check("P5b /sync-shaped call bounded < 2 x timeout", dt < 2 * TIMEOUT, f"{dt:.2f} s")
    else:
        check(f"P5b (PRE-FIX RECORD) /sync-shaped call paid >= {D} x timeout", dt >= D * TIMEOUT,
              f"{dt:.2f} s")

    # ---------------- P6: a wedged peer (never completes its reply)
    tr = Trickler()
    J4 = fresh_master("J4", genesis_path=gen)
    add_peer(J4, "wedged", tr.port)
    add_peer(J4, "L", L.node.port)
    t0 = time.monotonic()
    done = threading.Event()
    out = {}
    def _boot():
        out["gained"] = J4.bootstrap_chain(rounds=1, pause=0.0)
        done.set()
    threading.Thread(target=_boot, daemon=True).start()
    budget = (cov.BOOT_PROBE_DEADLINE_S + 1.0) if FIXED else 6 * TIMEOUT
    finished = done.wait(budget)
    dt = time.monotonic() - t0
    k4 = kinds(J4)
    if FIXED:
        check("P6a wedged peer does not hold the boot: converged within deadline",
              finished and len(J4.node.chain) == 3 and dt < cov.BOOT_PROBE_DEADLINE_S + 1.0,
              f"{dt:.2f} s, deadline {cov.BOOT_PROBE_DEADLINE_S}")
        check("P6b bootstrap_probe_timeout recorded for the wedged peer",
              k4.get("bootstrap_probe_timeout", 0) == 1, f"{k4}")
    else:
        check(f"P6 (PRE-FIX RECORD) a peer that trickles bytes holds the boot past {budget:.0f} s "
              "-- the A3 size cap bounds bytes, not time; L never asked",
              not finished and len(J4.node.chain) == 1,
              f"finished={finished} height {len(J4.node.chain)} after {dt:.2f} s")
    tr.close()

    # ---------------- P7: the boot push behind dead peers (K2's path home)
    rec2 = Recorder()
    M = fresh_master("M", genesis_path=gen)
    for b in L.node.chain[1:]:
        assert M._accept_block_common(clone_block(b))
    for i, h in enumerate(holes):
        add_peer(M, f"dead{i}", h.port)
    add_peer(M, "rec2", rec2.port)
    t0 = time.monotonic()
    buf = io.StringIO()
    with redirect_stdout(buf):
        M._bootstrap_once()   # includes the 1.5 s settle sleep, then bootstrap, then boot push
    boot_dt = time.monotonic() - t0
    ok = wait_for(lambda: any(f.get("type") == "BLOCK_ANNOUNCE" for _, f in rec2.seen), 5)
    ann = [t for t, f in rec2.seen if f.get("type") == "BLOCK_ANNOUNCE"]
    arrived = (ann[0] - t0) if ann else float("inf")
    check("P7a boot push reached the live peer", ok and "boot: announced tip" in buf.getvalue(),
          f"_bootstrap_once took {boot_dt:.2f} s")
    if FIXED:
        check("P7b boot push arrived within 1.5 s settle + 2 x timeout despite 8 dead peers",
              arrived < 1.5 + 2 * TIMEOUT, f"{arrived:.2f} s")
    else:
        check(f"P7b (PRE-FIX RECORD) boot push delayed >= 1.5 + {D} x timeout",
              arrived >= 1.5 + D * TIMEOUT, f"{arrived:.2f} s")

    # ---------------- P8: arithmetic from the module's constants
    W = cov.MAX_CONCURRENT_FETCHES
    D_big = 2 * W
    seq = D_big * cov.PEER_SEND_TIMEOUT_S
    conc = math.ceil(D_big / W) * cov.PEER_SEND_TIMEOUT_S
    check(f"P8 bound: {D_big} dead peers cost {conc:.1f} s concurrently vs {seq:.1f} s sequentially",
          conc < seq and (not FIXED or cov.BOOT_PROBE_DEADLINE_S >= cov.PEER_SEND_TIMEOUT_S))
    if FIXED:
        check("P8b deadline is >= one socket timeout (an honest slow peer still answers)",
              cov.BOOT_PROBE_DEADLINE_S >= cov.PEER_SEND_TIMEOUT_S,
              f"{cov.BOOT_PROBE_DEADLINE_S} vs {cov.PEER_SEND_TIMEOUT_S}")

    for h in holes: h.close()
    rec.close(); rec2.close()
    n_ok = sum(1 for _, ok in results if ok)
    print(f"\n{n_ok}/{len(results)} passed")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
