"""test_a3s_send_bounds.py -- A3 send-side follow-on (v8.37): this node never
transmits a frame it knows the receiver must refuse, and never blames a peer
for one.

WHAT THIS CLOSES.  A3 (v8.16) bounded every READ. A5 (v8.17) made the payload
bounds coherent -- MAX_TX < MAX_BLOCK <= CATCHUP_BUDGET < MAX_PEER_MSG,
asserted at import. The backlog then carried a one-line follow-on for five
days: "the SEND side (_send_raw, catch-up REQUEST) is not size-bounded, but
those are outbound and self-limited by what this node builds." Measured
2026-08-26 on the shipped v8.36, both halves of that sentence are wrong.

  1. NOT SELF-LIMITED.  A TX_ANNOUNCE carries a tx_id chosen by the SENDER,
     and _fetch_announced_tx echoes it verbatim into the TX_REQUEST it builds.
     A real transaction id is a sha256 hexdigest: 64 characters. PRE-FIX
     MEASUREMENT: a 204,893-byte announcement (all of it tx_id, under the read
     cap) made the node build and transmit a 204,872-byte request -- ~3,200x
     the honest maximum, chosen by a peer, paid for by us. At the 64 MiB
     default read cap that is ~4 GiB across MAX_CONCURRENT_FETCHES workers,
     and the pool it exhausts is the one gap-fill and bootstrap need (A14).
     This is the ONLY field with that property. The first draft of this suite
     -- and of the node comment beside it -- also claimed BLOCK_ANNOUNCE's
     `index` is echoed into the request we build. S5f was written to prove it
     and disproved it: _fetch_announced asks from len(self.node.chain), our
     OWN height. The index guard stays, relabelled as what it is (shape
     hygiene: `true` read as index 1, a float read as an offset, a string
     raising into the FRAMING-error channel), and S5f now pins the real
     behaviour. Recorded here rather than quietly deleted -- Section 0.

  2. NOT SAFE TO OVERSHOOT.  PRE-FIX MEASUREMENT: handed a frame over the
     receiver's cap, _send_raw transmits it three times; the peer's
     recv_bounded refuses it and closes without replying; and A23 (v8.36) --
     correctly -- reads "no parsed reply" as non-delivery and calls
     _note_send_failed. So an oversized frame OF OUR OWN MAKING escalates the
     heartbeat backoff against a peer that behaved perfectly. That edge is new
     since A23, i.e. new since the run before this one (M33: audit the surface
     you just widened).

  3. THE FRAME IS NOT THE PAYLOAD.  A5's relation bounds what travels; the
     receiver's cap applies to what arrives, which is payload + envelope
     (measured: 128 bytes for BLOCK_PROPAGATE, 190 for TRANSACTION_PROPAGATE,
     62 for a catch-up reply). At the defaults there is 8x headroom, so this
     is a latent config hazard rather than a live bug -- but the assertion
     that was supposed to make it impossible did not mention the envelope.

NOTHING HERE RELAXES ANYTHING.  No verdict, route, bound or refusal is
loosened; three refusals and three anomaly kinds are added, and one blame is
removed from a peer that never earned it. S8 pins the rule in the source so it
cannot be undone quietly.

Run: python3 test_a3s_send_bounds.py     (needs covenant_path_pattern.py beside it)
     PRE-FIX record: run it in a directory holding pristine v8.36.
"""
import os, sys, json, time, socket, threading, tempfile, inspect, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
# A 256 KiB read cap makes the over-cap path cost kilobytes instead of
# gigabytes. MAX_BLOCK_BYTES derives from it (32 KiB) and MAX_TX_BYTES stays
# 16 KiB, so the A5 relation still holds and nothing else needs overriding.
os.environ["COVENANT_MAX_PEER_MSG_BYTES"] = str(256 * 1024)
os.environ["COVENANT_PEER_SEND_TIMEOUT"] = "0.3"
os.environ["COVENANT_MAX_CONCURRENT_SENDS"] = "4"
os.environ["COVENANT_TIP_GOSSIP_INTERVAL"] = "600"
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives import serialization as _ser

# ---------------------------------------------------------------- PRE-FIX
# So this suite can be run against the PRISTINE v8.36 and produce a RECORD
# rather than an AttributeError. The stand-ins model the OLD behaviour
# executably (M13): no frame bound, no id bound, int() coercion including
# bool. On v8.37 MISSING is empty and nothing below is patched.
MISSING = [n for n in ("frame_fits", "usable_tx_id", "sane_index",
                       "FRAME_ENVELOPE_BYTES", "MAX_TX_ID_CHARS", "MAX_CHAIN_INDEX")
           if not hasattr(cov, n)]
if MISSING:
    print(f"\n*** PRE-FIX RECORD RUN: this source is missing {MISSING}.")
    print("*** Stand-ins modelling the OLD behaviour are installed; the checks")
    print("*** that pass below are the record of what v8.36 already did right.\n")
    cov.FRAME_ENVELOPE_BYTES = 1024      # stand-in: the constant did not exist
    cov.MAX_TX_ID_CHARS = 128            # stand-in, so the test strings stay sane
    cov.MAX_CHAIN_INDEX = 2 ** 63 - 1    # stand-in
    cov.frame_fits = lambda payload: True                       # no bound at all
    cov.usable_tx_id = lambda v: (str(v) if v is not None else None)   # bare str()
    cov.sane_index = lambda v: (int(v) if isinstance(v, (int, float)) else None)

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)


def code_only(src: str) -> str:
    """Source with comments and docstrings removed.

    S8's first draft matched raw source text and failed on its OWN new comment,
    which contains the words it was looking for. A source-level pin has to look
    at code; a comment saying "do not call _note_send_failed" is not a call."""
    import io, tokenize
    out = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return src
    prev_type = tokenize.INDENT
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and prev_type in (
                tokenize.INDENT, tokenize.NEWLINE, tokenize.NL, tokenize.DEDENT):
            continue          # a bare string statement: a docstring
        out.append(tok.string)
        if tok.type not in (tokenize.NL, tokenize.NEWLINE):
            prev_type = tok.type
        else:
            prev_type = tok.type
    return " ".join(out)


def has(mon, kind):
    with mon._lock:
        return any(e[1] == kind for e in mon._events)


def kinds(mon):
    with mon._lock:
        return sorted({e[1] for e in mon._events})


class Peer:
    """A listener that behaves like a real covenant peer: it applies this
    file's OWN read cap and, like recv_bounded, refuses and closes without a
    reply once the frame crosses it."""

    def __init__(self, mode="reply", enforce_cap=True, reply=None):
        self.mode, self.enforce_cap = mode, enforce_cap
        self.reply = reply if reply is not None else json.dumps(
            {"ok": True, "outcome": "known", "height": 1,
             "v": cov.COVENANT_VERSION, "src": cov.CORE_SOURCE_SHA12}).encode()
        self.bytes_in = self.conns = self.refused = 0
        self.frames = []
        self._stop = False
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(64)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while not self._stop:
            try:
                c, _ = self.srv.accept()
            except Exception:
                return
            self.conns += 1
            threading.Thread(target=self._one, args=(c,), daemon=True).start()

    def _one(self, c):
        try:
            buf = bytearray()
            while True:
                chunk = c.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if self.enforce_cap and len(buf) > cov.MAX_PEER_MSG_BYTES:
                    self.refused += 1
                    self.bytes_in += len(buf)
                    return
            self.bytes_in += len(buf)
            self.frames.append(bytes(buf))
            if self.mode == "reply":
                c.sendall(self.reply)
        except Exception:
            pass
        finally:
            try:
                c.close()
            except Exception:
                pass

    def close(self):
        self._stop = True
        try:
            self.srv.close()
        except Exception:
            pass


def make_node(port, nid):
    m = cov.CovenantUnifiedMaster(nid, host="127.0.0.1", port=port,
                                  p2p_port=port + 1,
                                  db_path=tempfile.mktemp(suffix=".db"))
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    m.node.running = True
    return m


def drive(master, frame: bytes, addr=("127.0.0.1", 1)):
    """Run the REAL inbound handler on a socketpair (M12) and return its
    reply bytes. No listener, no second process."""
    a, b = socket.socketpair()
    b.settimeout(None)
    t = threading.Thread(target=master._handle_peer, args=(b, addr), daemon=True)
    t.start()
    a.sendall(frame)
    a.shutdown(socket.SHUT_WR)
    out = b""
    try:
        a.settimeout(5.0)
        while True:
            chunk = a.recv(65536)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    t.join(timeout=5.0)
    for s in (a, b):
        try:
            s.close()
        except Exception:
            pass
    return out


def child(env_extra, expect_fail=True):
    """Import this module in a subprocess under an env override, so an
    import-time assertion can be observed failing (M30: test that the check
    can fail)."""
    env = dict(os.environ)
    env.update(env_extra)
    env["COVENANT_SKIP_PREFLIGHT"] = "1"
    p = subprocess.run([sys.executable, "-c", "import covenant_unified_v8"],
                       cwd=os.path.dirname(os.path.abspath(__file__)),
                       env=env, capture_output=True, text=True, timeout=120)
    return p.returncode, (p.stdout + p.stderr)


# =====================================================================  S1
print("\n--- S1: the frame, not just the payload (measured with the real serializer) ---")
m1 = make_node(19500, "a3s1")
n1 = m1.node
pem = n1.public_key.public_bytes(
    _ser.Encoding.PEM, _ser.PublicFormat.SubjectPublicKeyInfo).decode()
tx = cov.Transaction(sender_pubkey=pem, receiver="collective",
                     data={"x": "y"}, amount=0.0, benefit_score=0.5)
tx.sign(n1.private_key)
tx_d = cov.asdict(tx)
blk_d = cov.asdict(n1.chain[-1])

env_blk = len(json.dumps({"type": "BLOCK_PROPAGATE", "block": blk_d,
                          "node_id": n1.node_id, "p2p_port": n1.port,
                          "nonce": "x" * 40})) - len(json.dumps(blk_d))
env_tx = len(json.dumps({"type": "TRANSACTION_PROPAGATE", "transaction": tx_d,
                         "node_id": n1.node_id, "p2p_port": n1.port,
                         "nonce": "y" * 80})) - len(json.dumps(tx_d))
env_cat = len(json.dumps({"blocks": [blk_d], "height": 1, "v": cov.COVENANT_VERSION,
                          "src": cov.CORE_SOURCE_SHA12})) - len(json.dumps([blk_d]))
biggest = max(env_blk, env_tx, env_cat)
check("S1a every measured envelope fits FRAME_ENVELOPE_BYTES",
      biggest <= cov.FRAME_ENVELOPE_BYTES,
      f"blk={env_blk} tx={env_tx} catchup={env_cat} <= {cov.FRAME_ENVELOPE_BYTES}")
check("S1b a maximal block's FRAME fits the receiver's cap",
      cov.MAX_BLOCK_BYTES + cov.FRAME_ENVELOPE_BYTES <= cov.MAX_PEER_MSG_BYTES,
      f"{cov.MAX_BLOCK_BYTES}+{cov.FRAME_ENVELOPE_BYTES} <= {cov.MAX_PEER_MSG_BYTES}")
check("S1c a maximal catch-up page's FRAME fits the receiver's cap",
      cov.CATCHUP_REPLY_BUDGET_BYTES + cov.FRAME_ENVELOPE_BYTES <= cov.MAX_PEER_MSG_BYTES)
check("S1d a real transaction id is 64 chars, well inside MAX_TX_ID_CHARS",
      len(tx.get_id()) == 64 and 64 <= cov.MAX_TX_ID_CHARS,
      f"id={len(tx.get_id())} limit={cov.MAX_TX_ID_CHARS}")

rc, out = child({"COVENANT_MAX_BLOCK_BYTES": str(cov.MAX_PEER_MSG_BYTES - 1),
                 "COVENANT_CATCHUP_REPLY_BUDGET_BYTES": str(cov.MAX_PEER_MSG_BYTES - 1)})
check("S1e import REFUSES a block bound whose frame cannot be read",
      rc != 0 and "envelope" in out,
      f"rc={rc} {'envelope' in out}")
rc, out = child({"COVENANT_MAX_TX_ID_CHARS": "10"})
check("S1f import REFUSES a tx-id bound below one honest hexdigest",
      rc != 0 and "sha256 hexdigest" in out, f"rc={rc}")
rc, out = child({})
check("S1g the default configuration still imports", rc == 0, f"rc={rc}")

# =====================================================================  S2
print("\n--- S2: the three pure guards ---")
check("S2a frame_fits accepts exactly the cap",
      cov.frame_fits(b"x" * cov.MAX_PEER_MSG_BYTES))
check("S2b frame_fits refuses one byte more",
      not cov.frame_fits(b"x" * (cov.MAX_PEER_MSG_BYTES + 1)))
check("S2c usable_tx_id accepts an honest 64-char id",
      cov.usable_tx_id("a" * 64) == "a" * 64)
check("S2d usable_tx_id accepts exactly MAX_TX_ID_CHARS",
      cov.usable_tx_id("a" * cov.MAX_TX_ID_CHARS) is not None)
check("S2e usable_tx_id refuses one char more",
      cov.usable_tx_id("a" * (cov.MAX_TX_ID_CHARS + 1)) is None)
check("S2f usable_tx_id refuses non-strings and empties",
      all(cov.usable_tx_id(v) is None for v in (None, 5, b"a" * 64, "", [], {})))
check("S2g sane_index accepts 0 and a large legal index",
      cov.sane_index(0) == 0 and cov.sane_index(10 ** 12) == 10 ** 12)
check("S2h sane_index refuses bool (True would have read as index 1)",
      cov.sane_index(True) is None and cov.sane_index(False) is None)
check("S2i sane_index refuses negatives, floats and strings",
      all(cov.sane_index(v) is None for v in (-1, 2.0, "3", None)))
check("S2j sane_index refuses an integer whose decimal expansion is a payload",
      cov.sane_index(10 ** 400) is None)

# =====================================================================  S3
print("\n--- S3: an over-cap frame is not sent, and the peer is not blamed ---")
m3 = make_node(19520, "a3s3")
n3 = m3.node
peer = Peer(mode="reply", enforce_cap=True)
over = json.dumps({"type": "BLOCK_PROPAGATE",
                   "pad": "P" * (cov.MAX_PEER_MSG_BYTES + 40 * 1024)})
key = ("127.0.0.1", peer.port)
t0 = time.monotonic()
verdict = n3._send_raw("127.0.0.1", peer.port, over)
dt = time.monotonic() - t0
k = n3._send_failures.get(key, 0)
check("S3a the over-cap frame is refused before any socket is opened",
      peer.conns == 0, f"connections={peer.conns} bytes={peer.bytes_in}")
check("S3b it is recorded, not silent",
      has(n3.anomaly_monitor, "outbound_message_too_large"), str(kinds(n3.anomaly_monitor)))
check("S3c the PEER is not blamed: no consecutive-failure count",
      k == 0, f"k={k} (v8.36 recorded k=1 here)")
check("S3d and no backoff is armed against it",
      key not in n3._send_backoff_until)
check("S3e no peer_send_failure is recorded for our own oversized frame",
      not has(n3.anomaly_monitor, "peer_send_failure"))
check("S3f it costs no retry budget",
      dt < cov.PEER_SEND_TIMEOUT_S, f"{dt:.3f}s < {cov.PEER_SEND_TIMEOUT_S}s")
check("S3g the verdict is still None -- callers see non-delivery",
      verdict is None)

# LIVENESS: the guard must not touch the honest path.
under = json.dumps({"type": "BLOCK_ANNOUNCE", "index": 0, "hash": "h",
                    "node_id": n3.node_id, "p2p_port": n3.port})
v2 = n3._send_raw("127.0.0.1", peer.port, under)
check("S3h an ordinary frame still goes out and is acknowledged",
      isinstance(v2, dict) and v2.get("ok") is True and peer.conns == 1,
      f"conns={peer.conns} verdict={str(v2)[:40]}")
check("S3i and a real reply still clears the link's health",
      n3._send_failures.get(key, 0) == 0)
peer.close()

# =====================================================================  S4
print("\n--- S4: the amplifier -- a peer sizing a frame WE build ---")
m4 = make_node(19540, "a3s4")
sink = Peer(mode="reply", enforce_cap=False)
big_id = "Z" * (200 * 1024)
frame = json.dumps({"type": "TX_ANNOUNCE", "tx_id": big_id, "node_id": "att",
                    "p2p_port": sink.port, "nonce": "s4a"}).encode()
check("S4a the oversized announcement is itself acceptable inbound",
      len(frame) < cov.MAX_PEER_MSG_BYTES, f"{len(frame)} bytes")
reply = drive(m4, frame, addr=("127.0.0.1", sink.port))
time.sleep(1.5)
check("S4b this node builds and sends NOTHING in response",
      sink.bytes_in == 0 and sink.conns == 0,
      f"sent {sink.bytes_in} bytes (v8.36 sent 204,872)")
check("S4c the refusal is recorded",
      has(m4.node.anomaly_monitor, "peer_tx_id_invalid"))
check("S4d the sender is told, rather than left waiting",
      b"invalid_tx_id" in reply, reply[:80].decode(errors="replace"))

# LIVENESS: an honest announcement must still be fetched.
good_id = "b" * 64
frame = json.dumps({"type": "TX_ANNOUNCE", "tx_id": good_id, "node_id": "hon",
                    "p2p_port": sink.port, "nonce": "s4b"}).encode()
drive(m4, frame, addr=("127.0.0.1", sink.port))
deadline = time.time() + 8
while time.time() < deadline and not sink.frames:
    time.sleep(0.1)
check("S4e an honest 64-char announcement IS still fetched",
      sink.conns >= 1, f"conns={sink.conns} frames={len(sink.frames)}")
got = sink.frames[0].decode() if sink.frames else ""
check("S4f and the request it builds carries that id",
      '"TX_REQUEST"' in got and good_id in got, got[:70])
sink.close()

# =====================================================================  S5
print("\n--- S5: BLOCK_ANNOUNCE index -- shape hygiene, NOT a second amplifier ---")
m5 = make_node(19560, "a3s5")
sink5 = Peer(mode="reply", enforce_cap=False)
huge = int("9" * 3000)          # legal JSON, 3000 digits, under any int-str cap
frame = json.dumps({"type": "BLOCK_ANNOUNCE", "index": huge, "hash": "h",
                    "node_id": "att", "p2p_port": sink5.port,
                    "nonce": "s5a"}).encode()
reply = drive(m5, frame, addr=("127.0.0.1", sink5.port))
time.sleep(1.5)
check("S5a a 3000-digit index builds no outbound request",
      sink5.bytes_in == 0, f"sent {sink5.bytes_in} bytes")
check("S5b it is recorded", has(m5.node.anomaly_monitor, "peer_index_invalid"))
check("S5c the sender still gets an answer (no silent hang)",
      b'"height"' in reply, reply[:60].decode(errors="replace"))

frame = json.dumps({"type": "BLOCK_ANNOUNCE", "index": True, "hash": "h",
                    "node_id": "att", "p2p_port": sink5.port,
                    "nonce": "s5b"}).encode()
drive(m5, frame, addr=("127.0.0.1", sink5.port))
time.sleep(0.6)
check("S5d index=true is refused, not read as index 1",
      sink5.bytes_in == 0, f"sent {sink5.bytes_in} bytes")

# LIVENESS: a novel honest index must still trigger a fetch.
frame = json.dumps({"type": "BLOCK_ANNOUNCE", "index": 7, "hash": "h7",
                    "node_id": "hon", "p2p_port": sink5.port,
                    "nonce": "s5c"}).encode()
drive(m5, frame, addr=("127.0.0.1", sink5.port))
deadline = time.time() + 8
while time.time() < deadline and not sink5.frames:
    time.sleep(0.1)
check("S5e an honest novel index IS still fetched",
      sink5.conns >= 1, f"conns={sink5.conns} frames={len(sink5.frames)}")
# CORRECTION, and this check exists because it caught me. S5's first draft
# asserted the request would carry from_index=7, on the reasoning that the
# peer's index is echoed onward -- which is what the source comment said too.
# It is not: _fetch_announced asks from len(self.node.chain), OUR height. So
# the index is NOT a send-side amplifier the way tx_id is, and both the suite
# and the node's comment were corrected rather than the check deleted.
got5 = sink5.frames[0].decode(errors="replace") if sink5.frames else ""
check("S5f the request asks from OUR height, never the peer's number",
      '"BLOCK_REQUEST"' in got5 and '"from_index": 1' in got5
      and '"from_index": 7' not in got5, got5[:90])
sink5.close()

# =====================================================================  S6
print("\n--- S6: the inbound twins (TX_REQUEST / BLOCK_REQUEST) ---")
m6 = make_node(19580, "a3s6")
reply = drive(m6, json.dumps({"type": "TX_REQUEST", "tx_id": "Q" * (200 * 1024),
                              "node_id": "att", "p2p_port": 1,
                              "nonce": "s6a"}).encode())
check("S6a an oversized TX_REQUEST is refused without scanning the mempool",
      b'"transaction": null' in reply and has(m6.node.anomaly_monitor, "peer_tx_id_invalid"),
      reply[:60].decode(errors="replace"))
reply = drive(m6, json.dumps({"type": "BLOCK_REQUEST", "from_index": int("9" * 3000),
                              "node_id": "att", "p2p_port": 1,
                              "nonce": "s6b"}).encode())
check("S6b an out-of-range from_index is refused with an empty page",
      b'"blocks": []' in reply and has(m6.node.anomaly_monitor, "peer_index_invalid"),
      reply[:60].decode(errors="replace"))
reply = drive(m6, json.dumps({"type": "BLOCK_REQUEST", "from_index": 0,
                              "node_id": "hon", "p2p_port": 1,
                              "nonce": "s6c"}).encode())
body = json.loads(reply.decode())
check("S6c an honest BLOCK_REQUEST still returns the page",
      len(body.get("blocks", [])) == 1 and body.get("height") == 1,
      f"blocks={len(body.get('blocks', []))} height={body.get('height')}")

# =====================================================================  S7
print("\n--- S7: the honest maximum still travels (M7) ---")
m7 = make_node(19600, "a3s7")
n7 = m7.node
peer7 = Peer(mode="reply", enforce_cap=True)
pad = "d" * (cov.MAX_BLOCK_BYTES - cov.serialized_size(cov.asdict(n7.chain[-1])) - 200)
big_blk = cov.asdict(n7.chain[-1])
big_blk["previous_hash"] = pad[:1000]
msg = json.dumps({"type": "BLOCK_PROPAGATE", "block": big_blk,
                  "node_id": n7.node_id, "p2p_port": n7.port,
                  "nonce": "z" * 40})
check("S7a a block at the payload bound plus its envelope is still sendable",
      cov.frame_fits(msg.encode()), f"{len(msg)} bytes vs {cov.MAX_PEER_MSG_BYTES}")
v = n7._send_raw("127.0.0.1", peer7.port, msg)
check("S7b and it is actually delivered and acknowledged",
      isinstance(v, dict) and peer7.conns == 1, f"conns={peer7.conns}")
peer7.close()

# =====================================================================  S8
print("\n--- S8: pinned in the source, so it cannot be undone quietly ---")
src = code_only(inspect.getsource(cov.P2PNode._send_raw))
i_guard = src.find("frame_fits")
i_loop = src.find("for attempt in range")
check("S8a _send_raw checks frame_fits BEFORE its retry loop",
      0 <= i_guard < i_loop, f"guard@{i_guard} loop@{i_loop}")
head = src[:i_loop] if i_loop > 0 else src
check("S8b the over-cap path does NOT call _note_send_failed",
      "_note_send_failed" not in head,
      "the peer never saw the frame and must not be blamed for it")
check("S8c _send_raw still has exactly three failure-recording sites",
      src.count("_note_send_failed") == 3, str(src.count("_note_send_failed")))
fsrc = code_only(inspect.getsource(cov.CovenantUnifiedMaster._fetch_announced_tx))
check("S8d _fetch_announced_tx bounds the id before building the frame",
      fsrc.find("usable_tx_id") < fsrc.find('"TX_REQUEST"'))
hsrc = code_only(inspect.getsource(cov.CovenantUnifiedMaster._handle_peer))
flat = hsrc.replace(" ", "")
check("S8e no ingest site coerces a peer's tx_id with a bare str()",
      'str(msg.get("tx_id"' not in flat, flat.count('usable_tx_id'))
check("S8f no ingest site coerces a peer's index with a bare int()",
      'int(msg.get("index"' not in flat and 'int(msg.get("from_index"' not in flat,
      flat.count('sane_index'))

# =====================================================================
passed = sum(1 for _, ok in results if ok)
print(f"\n{'=' * 62}\n{passed}/{len(results)} checks passed")
for label, ok in results:
    if not ok:
        print(f"  FAILED: {label}")
sys.exit(0 if passed == len(results) else 1)
