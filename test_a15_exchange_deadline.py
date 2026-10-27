#!/usr/bin/env python3
"""
A15 -- every read-until-EOF site was unbounded in TIME (v8.27 fix: a
wall-clock budget inside recv_bounded, MAX_EXCHANGE_S, PeerMessageTooSlow).

THE HAZARD, measured on v8.26 (pre-fix record below). A3 bounded every
socket read in BYTES. The outbound readers (`_send_raw`'s ACK read, the
catch-up reply read, the tx-fetch read) also had a per-recv socket timeout
(PEER_SEND_TIMEOUT_S). Nothing bounded the EXCHANGE: a peer that drips one
byte every 0.2 s keeps every recv inside its timeout and holds the worker
for as long as it likes. A14 found this on the boot path and deadline'd
that one call site; every other reader still had the gap.

And the inbound side was WORSE than A15's wording: the accepted connections
in `_handle_peer` / `_handle_bridge` had NO socket timeout at all (the
listener is blocking, accepted sockets inherit None, and nothing called
settimeout on them). A peer did not even need to trickle -- it could
connect, send nothing, and walk away: one pinned `_RECV_POOL` worker per
idle TCP connection, for ever, with nothing recorded anywhere. With
MAX_CONCURRENT_HANDLERS (96) idle connections -- one laptop, one loop --
the node keeps serving HTTP, keeps reporting a healthy chain, and is
permanently deaf to every real peer (the N=1000 accept-loop failure mode
again, now reachable on purpose from one host).

FIX (v8.27), tightening only. `recv_bounded(sock, limit, chunk_size,
max_seconds=None)` takes a wall-clock budget, default MAX_EXCHANGE_S
(env COVENANT_MAX_EXCHANGE_S, default 60 s, refused at import below one
PEER_SEND_TIMEOUT_S). Each recv runs under min(remaining budget, the
socket's own timeout); when the budget is gone it raises
PeerMessageTooSlow. A socket whose own timeout fires first still raises
socket.timeout exactly as before (outbound semantics unchanged). Both
inbound handlers record `peer_message_too_slow` / `bridge_message_too_slow`
explicitly. Honest maximum (M7): the biggest legitimate frame is one
catch-up reply of CATCHUP_REPLY_BUDGET_BYTES (48 MiB); at 60 s that needs
a link of >= 6.7 Mbit/s, which is every LAN, Tailscale and ordinary
cellular link. Nothing that was refused is now accepted; nothing that
completed inside the budget behaves differently.

CHECKS (in-process, real recv_bounded, real _handle_peer over the real
listener, real _send_raw / request_missing_blocks; ~25 s at
COVENANT_MAX_EXCHANGE_S=1.5, COVENANT_PEER_SEND_TIMEOUT=0.5,
COVENANT_MAX_CONCURRENT_HANDLERS=4):
  U1  a trickling socketpair peer (1 byte / 0.2 s) raises PeerMessageTooSlow
      within budget + slack  (pre-fix: still reading at 3 x budget)
  U2  a SILENT peer (no bytes, no close) on a socket with no timeout raises
      PeerMessageTooSlow at the budget  (pre-fix: blocks for ever)
  U3  an in-budget message returns intact; the byte cap still raises
      PeerMessageTooLarge first when it is crossed first
  U4  a socket whose own timeout is shorter than the budget still raises
      socket.timeout (outbound per-recv semantics preserved)
  U5  import-time refusal: COVENANT_MAX_EXCHANGE_S below the socket timeout
      fails at import (subprocess)
  L1  real listener: MAX_CONCURRENT_HANDLERS silent connections, then a real
      BLOCK_REQUEST from an honest client is ANSWERED within budget + slack
      (pre-fix: never -- the pool is pinned), and the silent ones are
      recorded as peer_message_too_slow
  L2  the bridge port has the same bound (bridge_message_too_slow)
  L3  _send_raw against a peer that trickles its ACK returns within
      attempts x budget + slack  (pre-fix: never)
  L4  request_missing_blocks against a trickler returns [] within budget +
      slack and records catchup_failed naming PeerMessageTooSlow
  L5  arithmetic from the module's constants: MAX_EXCHANGE_S >= socket
      timeout; the minimum honest link rate for one full catch-up page is
      printed and is < 10 Mbit/s at the defaults
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_SKIP_PREFLIGHT", "1")
os.environ.setdefault("COVENANT_PEER_SEND_TIMEOUT", "0.5")
os.environ.setdefault("COVENANT_MAX_EXCHANGE_S", "1.5")
os.environ.setdefault("COVENANT_MAX_CONCURRENT_HANDLERS", "4")
os.environ.setdefault("COVENANT_TIP_GOSSIP_INTERVAL", "0")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as cov  # noqa: E402

TIMEOUT = cov.PEER_SEND_TIMEOUT_S
FIXED = hasattr(cov, "MAX_EXCHANGE_S")
BUDGET = cov.MAX_EXCHANGE_S if FIXED else 1.5
SLACK = 1.0
results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""), flush=True)


def run_with_timeout(fn, limit):
    """Run fn in a thread; return (finished, result_or_exc, seconds)."""
    box = {}
    def go():
        t0 = time.monotonic()
        try:
            box["r"] = fn()
        except BaseException as e:  # noqa: BLE001
            box["e"] = e
        box["dt"] = time.monotonic() - t0
    th = threading.Thread(target=go, daemon=True)
    th.start(); th.join(limit)
    return (not th.is_alive()), box.get("e", box.get("r")), box.get("dt", limit)


def kinds(m):
    return {k: v["baseline"] for k, v in m.node.anomaly_monitor.report()["per_kind"].items()}


_port = [24300]
def next_port():
    _port[0] += 12
    return _port[0]


def fresh_master(name, listen=False, bridge=False):
    port = next_port()
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    m.node.running = True
    if listen:
        threading.Thread(target=m._listen_for_peers, daemon=True).start()
    if bridge:
        threading.Thread(target=m._listen_for_bridge, daemon=True).start()
    if listen or bridge:
        time.sleep(0.3)
    return m


class Trickler:
    """Accepts, reads the request to EOF, then drips one byte per 0.2 s."""
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


# ---------------------------------------------------------------- U1-U4 ---
print(f"== A15 exchange deadline ({'v8.27+ FIXED' if FIXED else 'PRE-FIX RECORD'}): "
      f"timeout={TIMEOUT}s budget={BUDGET}s handlers={cov.MAX_CONCURRENT_HANDLERS}")

# U1 trickler over a socketpair
a, b = socket.socketpair()
stop = [False]
def drip(sk=b):
    try:
        while not stop[0]:
            sk.sendall(b"x"); time.sleep(0.2)
    except Exception: pass
threading.Thread(target=drip, daemon=True).start()
done, res, dt = run_with_timeout(lambda: cov.recv_bounded(a), 3 * BUDGET)
stop[0] = True
if FIXED:
    check("U1 trickling peer raises PeerMessageTooSlow within budget + slack",
          done and isinstance(res, cov.PeerMessageTooSlow) and dt < BUDGET + SLACK,
          f"{type(res).__name__ if done else 'still reading'} after {dt:.2f}s")
else:
    check("U1 (PRE-FIX RECORD) trickling peer still being read at 3 x budget", not done,
          f"still reading after {dt:.2f}s")
a.close(); b.close()

# U2 silent peer, socket with no timeout (the inbound shape)
a, b = socket.socketpair()
a.settimeout(None)
done, res, dt = run_with_timeout(lambda: cov.recv_bounded(a), 3 * BUDGET)
if FIXED:
    check("U2 silent peer on an untimed socket raises PeerMessageTooSlow at the budget",
          done and isinstance(res, cov.PeerMessageTooSlow) and BUDGET - 0.2 <= dt < BUDGET + SLACK,
          f"{type(res).__name__ if done else 'blocked'} after {dt:.2f}s")
else:
    check("U2 (PRE-FIX RECORD) silent peer blocks the reader for ever (3 x budget and counting)",
          not done, f"blocked {dt:.2f}s")
a.close(); b.close()

# U3 in-budget message intact; byte cap still first when crossed first
a, b = socket.socketpair()
payload = os.urandom(200_000)
def send_then_close(sk=b):
    sk.sendall(payload); sk.shutdown(socket.SHUT_WR)
threading.Thread(target=send_then_close, daemon=True).start()
got = cov.recv_bounded(a)
check("U3a in-budget 200 KB message returned intact", got == payload, f"{len(got)} bytes")
a.close(); b.close()
a, b = socket.socketpair()
def flood(sk=b):  # bind the socket now: a late-bound global `b` would let a
    # still-running flood thread spill into U4's fresh socketpair (seen once
    # under a 12-wide parallel batch: U4 got PeerMessageTooLarge after 0.66 s)
    try:
        while True: sk.sendall(b"y" * 65536)
    except Exception: pass
threading.Thread(target=flood, daemon=True).start()
try:
    cov.recv_bounded(a, limit=300_000); raised = None
except Exception as e:
    raised = e
check("U3b byte cap still raises PeerMessageTooLarge when crossed first",
      isinstance(raised, cov.PeerMessageTooLarge), type(raised).__name__)
a.close(); b.close()

# U4 socket's own shorter timeout still wins
a, b = socket.socketpair()
a.settimeout(0.3)
done, res, dt = run_with_timeout(lambda: cov.recv_bounded(a), 3 * BUDGET)
check("U4 a socket timeout shorter than the budget still raises socket.timeout",
      done and isinstance(res, socket.timeout) and dt < 0.3 + 0.5,
      f"{type(res).__name__ if done else 'blocked'} after {dt:.2f}s")
a.close(); b.close()

# U5 import-time refusal
if FIXED:
    env = dict(os.environ, COVENANT_MAX_EXCHANGE_S="0.1", COVENANT_PEER_SEND_TIMEOUT="5")
    r = subprocess.run([sys.executable, "-c", "import covenant_unified_v8"], cwd=HERE, env=env,
                       capture_output=True, text=True, timeout=120)
    check("U5 COVENANT_MAX_EXCHANGE_S below the socket timeout is refused at import",
          r.returncode != 0 and "MAX_EXCHANGE" in (r.stderr + r.stdout),
          f"rc={r.returncode}")
else:
    check("U5 (PRE-FIX RECORD) MAX_EXCHANGE_S does not exist", not hasattr(cov, "MAX_EXCHANGE_S"))

# ------------------------------------------------------------------- L1 ---
m = fresh_master("victim", listen=True, bridge=True)
K = cov.MAX_CONCURRENT_HANDLERS
idle = []
for _ in range(K):
    s = socket.socket(); s.connect(("127.0.0.1", m.node.port)); idle.append(s)
time.sleep(0.3)

def honest_request():
    with socket.socket() as sk:
        sk.settimeout(BUDGET + SLACK + 2)
        sk.connect(("127.0.0.1", m.node.port))
        sk.sendall(json.dumps({"type": "BLOCK_REQUEST", "from_index": 0,
                               "node_id": "honest", "p2p_port": 1}).encode())
        sk.shutdown(socket.SHUT_WR)
        return json.loads(cov.recv_bounded(sk, max_seconds=BUDGET + SLACK + 2).decode()) if FIXED \
            else json.loads(b"".join(iter(lambda: sk.recv(65536), b"")).decode())

done, res, dt = run_with_timeout(honest_request, BUDGET + SLACK + 1.5)
if FIXED:
    check(f"L1a with {K} silent connections pinning every handler, an honest BLOCK_REQUEST is answered "
          f"within budget + slack", done and isinstance(res, dict) and "blocks" in res and dt < BUDGET + SLACK,
          f"{'answered' if done and isinstance(res, dict) else res} after {dt:.2f}s")
    time.sleep(0.3)
    k = kinds(m)
    check("L1b the silent connections are recorded as peer_message_too_slow",
          k.get("peer_message_too_slow", 0) >= K, f"{k.get('peer_message_too_slow', 0)} of {K}")
else:
    check(f"L1 (PRE-FIX RECORD) {K} silent connections make the node deaf: honest request unanswered "
          f"at budget + slack", not done, f"waited {dt:.2f}s; anomalies={kinds(m)}")
for s in idle: s.close()

# ------------------------------------------------------------------- L2 ---
time.sleep(0.5)
idle = [socket.create_connection(("127.0.0.1", m.node.port + 10)) for _ in range(2)]
time.sleep(BUDGET + SLACK)
k = kinds(m)
if FIXED:
    check("L2 bridge port: silent connections recorded as bridge_message_too_slow",
          k.get("bridge_message_too_slow", 0) >= 2, f"{k.get('bridge_message_too_slow', 0)}")
else:
    check("L2 (PRE-FIX RECORD) bridge port: nothing recorded for silent connections",
          "bridge_message_too_slow" not in k, str(k))
for s in idle: s.close()

# ------------------------------------------------------------------- L3 ---
t = Trickler()
done, res, dt = run_with_timeout(lambda: m.node._send_raw("127.0.0.1", t.port, "{}", attempts=2),
                                 2 * BUDGET + SLACK + 1)
if FIXED:
    check("L3 _send_raw against a peer that trickles its ACK returns within attempts x budget + slack",
          done and dt < 2 * BUDGET + SLACK, f"{'returned' if done else 'still waiting'} after {dt:.2f}s")
else:
    check("L3 (PRE-FIX RECORD) _send_raw against a trickling ACK never returns",
          not done, f"still waiting after {dt:.2f}s")

# ------------------------------------------------------------------- L4 ---
done, res, dt = run_with_timeout(lambda: m.node.request_missing_blocks("127.0.0.1", t.port, 1),
                                 BUDGET + SLACK + 1)
if FIXED:
    k = kinds(m)
    check("L4a request_missing_blocks against a trickler returns [] within budget + slack",
          done and res == [] and dt < BUDGET + SLACK, f"{res if done else 'hung'} after {dt:.2f}s")
    # the detail string names the exception class; counts are per kind
    check("L4b catchup_failed recorded for the trickler", k.get("catchup_failed", 0) >= 1,
          f"catchup_failed={k.get('catchup_failed', 0)}")
else:
    check("L4 (PRE-FIX RECORD) request_missing_blocks against a trickler never returns",
          not done, f"still waiting after {dt:.2f}s")
t.close()
m.node.running = False

# ------------------------------------------------------------------- L5 ---
if FIXED:
    env_default = dict(os.environ); env_default.pop("COVENANT_MAX_EXCHANGE_S", None)
    env_default.pop("COVENANT_PEER_SEND_TIMEOUT", None)
    r = subprocess.run([sys.executable, "-c",
                        "import covenant_unified_v8 as c; print(c.MAX_EXCHANGE_S, c.PEER_SEND_TIMEOUT_S, "
                        "c.CATCHUP_REPLY_BUDGET_BYTES)"],
                       cwd=HERE, env=env_default, capture_output=True, text=True, timeout=120)
    mx, to, budget_bytes = [float(x) for x in r.stdout.split()[-3:]]
    mbit = budget_bytes * 8 / mx / 1e6
    check("L5a default MAX_EXCHANGE_S >= PEER_SEND_TIMEOUT_S", mx >= to, f"{mx} >= {to}")
    check(f"L5b honest maximum: one full catch-up page ({budget_bytes/2**20:.0f} MiB) fits the budget on a "
          f"link >= {mbit:.1f} Mbit/s (< 10 Mbit/s)", mbit < 10, f"{mbit:.2f} Mbit/s")
else:
    check("L5 (PRE-FIX RECORD) no exchange bound exists", not FIXED)

passed = sum(1 for _, ok in results if ok)
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
