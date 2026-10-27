#!/usr/bin/env python3
"""test_a5_size_coherence.py -- backlog item A5 (v8.17).

A3 capped every inbound socket read at MAX_PEER_MSG_BYTES (64 MiB) and called
the cap "generous". It was not checked against the file's own constants. This
file first MEASURES the honest worst case with the real serializer, then
verifies the v8.17 fix: transaction, block, catch-up page and HTTP body bounds
that are coherent by construction, so the read cap can refuse only an attack,
never a legitimate catch-up.

Checks:
  A5.0  the finding -- 64 full blocks of bare transactions exceed the read cap
  A5.1  bound coherence is enforced (MAX_TX < MAX_BLOCK <= PAGE < READ CAP)
  A5.2  validate_transaction_shape rejects an oversized tx, accepts a bare one
  A5.3  validate_block_shape rejects an oversized block, accepts the genesis
  A5.4  admit_pending_transaction refuses an oversized tx (mempool backstop)
  A5.5  LIVE: BLOCK_REQUEST reply is byte-paged -- never over the budget,
        always >= 1 block, truncation recorded on the anomaly monitor, and a
        requester paging repeatedly still reaches the tip
  A5.6  LIVE: the real request_missing_blocks reader accepts the page
  A5.7  LIVE: HTTP POST /transaction with an oversized body is refused (413),
        and with an oversized `data` field inside a small body is refused (413)

Node env needs BOTH COVENANT_INSECURE_MOCK_JUDGE=1 and
COVENANT_JUDGE_PROVIDERS=mock (M2). Everything runs inside this one process
(M5). Ports 17500/17501/17511 (API / P2P / bridge).
"""
import os, sys, json, socket, tempfile, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
# Small, coherent bounds so the live paging test moves KB, not MB. Same code.
os.environ["COVENANT_MAX_PEER_MSG_BYTES"] = str(256 * 1024)
os.environ["COVENANT_CATCHUP_REPLY_BUDGET_BYTES"] = str(96 * 1024)
os.environ["COVENANT_MAX_BLOCK_BYTES"] = str(64 * 1024)
os.environ["COVENANT_MAX_TX_BYTES"] = str(16 * 1024)
os.environ["COVENANT_MAX_HTTP_BODY_BYTES"] = str(64 * 1024)

from dataclasses import asdict
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

PASS = FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1; print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def keypair():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return k, pem


def signed_tx(k, pem, data=None, amount=1.0):
    tx = cov.Transaction(sender_pubkey=pem, receiver=pem, data=data or {"type": "transfer"},
                         amount=amount)
    tx.sign(k)
    return tx


def send_json(port, obj):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(("127.0.0.1", port))
    s.sendall(json.dumps(obj).encode())
    s.shutdown(socket.SHUT_WR)
    reply = b""
    try:
        while True:
            c = s.recv(65536)
            if not c:
                break
            reply += c
    except OSError:
        pass
    s.close()
    return reply


def http_post(port, path, body_bytes):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(("127.0.0.1", port))
    head = (f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\n"
            f"Content-Length: {len(body_bytes)}\r\nConnection: close\r\n\r\n").encode()
    try:
        s.sendall(head + body_bytes)
    except OSError:
        pass   # server may close early on 413; the status line is what matters
    reply = b""
    try:
        while True:
            c = s.recv(65536)
            if not c:
                break
            reply += c
    except OSError:
        pass
    s.close()
    return reply.split(b"\r\n", 1)[0].decode(errors="replace")


def main():
    k, pem = keypair()

    print("== A5.0 the finding: honest worst case vs the default read cap ==")
    bare = signed_tx(k, pem)
    tx_sz = cov.serialized_size(asdict(bare))
    blk = cov.Block(1, [bare] * cov.MAX_PENDING_TRANSACTIONS, "0" * 64)
    blk_sz = cov.serialized_size(asdict(blk))
    page_sz = cov.serialized_size({"blocks": [asdict(blk)] * cov.MAX_CATCHUP_BLOCKS, "height": 65})
    default_cap = 64 * 1024 * 1024
    check("bare signed transaction is ~1.4 KB", 1200 < tx_sz < 1800, f"{tx_sz} bytes")
    check("64 full count-only pages would exceed the default 64 MiB read cap",
          page_sz > default_cap, f"page {page_sz/2**20:.0f} MiB vs cap {default_cap/2**20:.0f} MiB")
    check("a default full block (5000 bare tx) fits under default MAX_BLOCK_BYTES (8 MiB)",
          blk_sz <= 8 * 1024 * 1024, f"block {blk_sz/2**20:.2f} MiB")

    print("\n== A5.1 bound coherence ==")
    check("MAX_TX < MAX_BLOCK <= PAGE BUDGET < READ CAP",
          cov.MAX_TX_BYTES < cov.MAX_BLOCK_BYTES <= cov.CATCHUP_REPLY_BUDGET_BYTES < cov.MAX_PEER_MSG_BYTES,
          f"{cov.MAX_TX_BYTES} < {cov.MAX_BLOCK_BYTES} <= {cov.CATCHUP_REPLY_BUDGET_BYTES} < {cov.MAX_PEER_MSG_BYTES}")

    print("\n== A5.2 transaction size is part of shape ==")
    big = signed_tx(k, pem, data={"type": "transfer", "blob": "x" * cov.MAX_TX_BYTES})
    rejected = False
    try:
        cov.validate_transaction_shape(asdict(big))
    except cov.ShapeValidationError as e:
        rejected = "MAX_TX_BYTES" in str(e)
    check("oversized tx rejected by validate_transaction_shape", rejected)
    check("bare tx accepted", cov.validate_transaction_shape(asdict(bare)) is True)

    print("\n== A5.3 block size is part of shape ==")
    n = cov.MAX_BLOCK_BYTES // tx_sz + 2
    bigblk = cov.Block(1, [bare] * n, "0" * 64)
    rejected = False
    try:
        cov.validate_block_shape(asdict(bigblk))
    except cov.ShapeValidationError as e:
        rejected = "MAX_BLOCK_BYTES" in str(e)
    check("oversized block rejected by validate_block_shape", rejected,
          f"{n} tx, {cov.serialized_size(asdict(bigblk))} bytes > {cov.MAX_BLOCK_BYTES}")

    # Stand up a real node.
    tmp = tempfile.mktemp(suffix=".db")
    API, P2P = 17500, 17501
    m = cov.CovenantUnifiedMaster("a5", host="127.0.0.1", port=API, p2p_port=P2P, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    check("genesis block passes validate_block_shape under the size bound",
          cov.validate_block_shape(asdict(m.node.chain[0])) is True,
          f"genesis {cov.serialized_size(asdict(m.node.chain[0]))} bytes")

    print("\n== A5.4 mempool backstop ==")
    ok, why = m.node.admit_pending_transaction(big)
    check("admit_pending_transaction refuses an oversized tx", not ok and "MAX_TX_BYTES" in why, why)
    ok, why = m.node.admit_pending_transaction(bare)
    check("admit_pending_transaction admits a bare tx", ok, why)
    m.node.pending_transactions.clear()

    # Synthetic chain: 40 blocks of ~8 KB each (~6 tx) appended directly, so the
    # catch-up SERVER has something bigger than one page to serve. The page
    # budget is 96 KB => ~11 blocks/page. This bypasses acceptance on purpose;
    # the server's paging is what is under test, not block validity.
    prev = m.node.chain[-1].hash
    for i in range(1, 41):
        txs = [signed_tx(k, pem, data={"type": "t", "i": i, "j": j}) for j in range(5)]
        b = cov.Block(i, txs, prev)
        b.hash = b.compute_hash()
        m.node.chain.append(b)
        prev = b.hash
    one_blk = cov.serialized_size(asdict(m.node.chain[5]))
    check("synthetic blocks are under MAX_BLOCK_BYTES", one_blk <= cov.MAX_BLOCK_BYTES, f"{one_blk} bytes")

    m.node.running = True
    threading.Thread(target=m._listen_for_peers, daemon=True).start()
    threading.Thread(target=m.api.run, daemon=True).start()
    time.sleep(1.0)

    print("\n== A5.5 LIVE: BLOCK_REQUEST is byte-paged ==")
    raw = send_json(P2P, {"type": "BLOCK_REQUEST", "from_index": 1, "node_id": "probe", "p2p_port": 1})
    reply = json.loads(raw.decode())
    blocks = reply["blocks"]
    check("page is under the byte budget", len(raw) <= cov.CATCHUP_REPLY_BUDGET_BYTES + 64,
          f"{len(raw)} bytes <= {cov.CATCHUP_REPLY_BUDGET_BYTES}")
    check("page carries at least one block and fewer than the count limit",
          1 <= len(blocks) < min(cov.MAX_CATCHUP_BLOCKS, 40), f"{len(blocks)} blocks")
    check("page reports true height", reply["height"] == 41, f"height {reply['height']}")
    trunc = m.node.anomaly_monitor.report()["per_kind"].get("catchup_page_truncated", {}).get("baseline", 0)
    check("truncation recorded on the anomaly monitor", trunc >= 1, f"catchup_page_truncated={trunc}")
    # Page through to the tip the way a requester would.
    idx, pages, got = 1, 0, 0
    while idx < 41 and pages < 20:
        r = json.loads(send_json(P2P, {"type": "BLOCK_REQUEST", "from_index": idx,
                                       "node_id": "probe", "p2p_port": 1}).decode())
        if not r["blocks"]:
            break
        assert all(b["index"] == idx + n for n, b in enumerate(r["blocks"])), "page not contiguous"
        idx += len(r["blocks"]); got += len(r["blocks"]); pages += 1
    check("repeated paging reaches the tip, contiguously", idx == 41 and got == 40, f"{got} blocks in {pages} pages")

    print("\n== A5.6 LIVE: the real catch-up reader accepts the page ==")
    # Use a second node object purely as a requester (no listeners started).
    tmp2 = tempfile.mktemp(suffix=".db")
    r = cov.CovenantUnifiedMaster("a5r", host="127.0.0.1", port=17520, p2p_port=17521, db_path=tmp2)
    raws = r.node.request_missing_blocks("127.0.0.1", P2P, 1)
    fails = r.node.anomaly_monitor.report()["per_kind"].get("catchup_failed", {}).get("baseline", 0)
    check("request_missing_blocks returns a page without catchup_failed",
          len(raws) >= 1 and fails == 0, f"{len(raws)} blocks, catchup_failed={fails}")

    print("\n== A5.7 LIVE: HTTP body and transaction size bounds ==")
    status = http_post(API, "/transactions", b"{" + b'"data": "' + b"x" * (cov.MAX_HTTP_BODY_BYTES + 4096) + b'"}')
    check("oversized HTTP body refused with 413", " 413 " in status, status)
    body = json.dumps({**asdict(big)}).encode()
    status = http_post(API, "/transactions", body)
    check("small body with oversized tx.data refused with 413", " 413 " in status,
          f"{status} (body {len(body)} bytes)")
    body = json.dumps({**asdict(bare), "amount": 0.0}).encode()
    status = http_post(API, "/transactions", body)
    check("bare tx is not refused for size (reaches later checks)", " 413 " not in status, status)

    m.node.running = False
    print(f"\n{'=' * 58}\n{PASS} passed, {FAIL} failed\n{'=' * 58}")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
