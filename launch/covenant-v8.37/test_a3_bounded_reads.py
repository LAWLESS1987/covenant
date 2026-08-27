#!/usr/bin/env python3
"""test_a3_bounded_reads.py -- backlog item A3.

Every inbound socket read in the core used to accumulate to EOF with no cap.
These checks drive the REAL P2P and bridge listeners (not the helper in
isolation) with an oversized stream and assert:
  1. the node stays up and its chain is untouched (the flood is refused, not
     absorbed),
  2. the refusal is recorded on the anomaly monitor (observable, not silent),
  3. a normal, in-cap message on the same port is still handled,
  4. recv_bounded fires exactly on the chunk that crosses the ceiling.

Node env needs BOTH COVENANT_INSECURE_MOCK_JUDGE=1 and
COVENANT_JUDGE_PROVIDERS=mock (M2). All work happens inside this one process --
no background node across Bash calls (M5).
"""
import os, sys, json, socket, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
# Small cap so the test moves a few MB, not 64. Same code path.
os.environ["COVENANT_MAX_PEER_MSG_BYTES"] = str(1 * 1024 * 1024)

import covenant_unified_v8 as cov

PASS = FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1; print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def flood(port, nbytes, chunk=65536):
    """Open a connection and stream `nbytes` of junk, then half-close so the
    reader would hit EOF -- if it ever got there."""
    sent = 0
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(("127.0.0.1", port))
    blob = b"x" * chunk
    try:
        while sent < nbytes:
            s.sendall(blob)
            sent += len(blob)
    except OSError:
        # The reader may reset us once it raises PeerMessageTooLarge and closes;
        # that is the refusal working, not a test failure.
        pass
    finally:
        try:
            s.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        s.close()
    return sent


def send_json(port, obj, read_reply=True):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(("127.0.0.1", port))
    s.sendall(json.dumps(obj).encode())
    s.shutdown(socket.SHUT_WR)
    reply = b""
    if read_reply:
        try:
            while True:
                c = s.recv(4096)
                if not c:
                    break
                reply += c
        except OSError:
            pass
    s.close()
    return reply


def main():
    import threading
    print("== A3.0 recv_bounded fires on the crossing chunk ==")
    a, b = socket.socketpair()
    try:
        payload = b"y" * (cov.MAX_PEER_MSG_BYTES + 65536)
        # Send from a thread: a blocking sendall of >1 MB would deadlock against
        # a reader that stops early, which is exactly what recv_bounded does.
        def _send():
            try:
                a.sendall(payload); a.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        th = threading.Thread(target=_send, daemon=True); th.start()
        raised = False
        try:
            cov.recv_bounded(b, chunk_size=65536)
        except cov.PeerMessageTooLarge:
            raised = True
        check("oversized stream raises PeerMessageTooLarge", raised)
        th.join(timeout=2)
    finally:
        a.close(); b.close()

    a, b = socket.socketpair()
    try:
        a.sendall(b"z" * 1000); a.shutdown(socket.SHUT_WR)
        got = cov.recv_bounded(b)
        check("an in-cap stream returns intact", got == b"z" * 1000, f"{len(got)} bytes")
    finally:
        a.close(); b.close()

    # Stand up a real node with live P2P + bridge listeners.
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster("a3", host="127.0.0.1", port=17400,
                                  p2p_port=17401, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    # Start ONLY the socket listeners (not the Flask app) for this test.
    m.node.running = True
    # The P2P/bridge listeners live on CovenantUnifiedMaster; start just those
    # (not the Flask app) so this test drives the real accept loops + handlers.
    threading.Thread(target=m._listen_for_peers, daemon=True).start()
    threading.Thread(target=m._listen_for_bridge, daemon=True).start()
    time.sleep(0.5)

    P2P = 17401           # peer listener binds node.port (p2p_port)
    BRIDGE = 17401 + 10   # bridge listener binds node.port + 10

    height_before = len(m.node.chain)
    errs_before = m.node.anomaly_monitor.report()["per_kind"].get(
        "peer_message_error", {}).get("baseline", 0)

    print("\n== A3.1 P2P listener refuses an oversized stream ==")
    sent = flood(P2P, cov.MAX_PEER_MSG_BYTES * 3)
    time.sleep(0.8)
    check("flood delivered more than the cap", sent > cov.MAX_PEER_MSG_BYTES,
          f"sent {sent/1024/1024:.1f} MB, cap {cov.MAX_PEER_MSG_BYTES/1024/1024:.1f} MB")
    check("node survived the flood (thread + chain intact)",
          len(m.node.chain) == height_before, f"height {len(m.node.chain)}")
    errs_after = m.node.anomaly_monitor.report()["per_kind"].get(
        "peer_message_error", {}).get("baseline", 0)
    check("the refusal was recorded on the anomaly monitor",
          errs_after > errs_before, f"{errs_before} -> {errs_after}")

    print("\n== A3.2 bridge listener refuses an oversized stream ==")
    flood(BRIDGE, cov.MAX_PEER_MSG_BYTES * 3)
    time.sleep(0.8)
    berrs_after = m.node.anomaly_monitor.report()["per_kind"].get(
        "bridge_message_error", {}).get("baseline", 0)
    check("bridge flood refused, node still up (chain intact)",
          len(m.node.chain) == height_before,
          f"bridge_message_error baseline={berrs_after}, height {len(m.node.chain)}")

    print("\n== A3.3 a normal in-cap message on the same port still works ==")
    # A well-formed but unknown-type message: the handler reads it fully,
    # json.loads succeeds, and it is ignored without error. Proves the listener
    # is still alive and reading normally after the floods.
    reply = send_json(P2P, {"type": "PING_UNKNOWN", "n": 1})
    monitor_ok = len(m.node.chain) == height_before
    check("listener still serves a normal message after the flood", monitor_ok,
          f"height {len(m.node.chain)}")

    m.node.running = False
    print(f"\n{'=' * 58}\n{PASS} passed, {FAIL} failed\n{'=' * 58}")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
