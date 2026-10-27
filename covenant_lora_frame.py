"""covenant_lora_frame.py -- R1: a compact wire codec so the mycelium's ANNOUNCE
fits in a LoRa frame. ADDITIVE ONLY. Nothing in covenant_unified_v8.py changes.

WHY THIS FILE EXISTS, AND WHY IT IS A FILE RATHER THAN AN EDIT.

The node's peer frames are JSON, and they are the right size for TCP:

    BLOCK_ANNOUNCE                 148 B
    heartbeat (announce + digest)  268 B

Against LoRaWAN US915 application payloads (Things Network regional parameters
-- DR0 11, DR1 53, DR2 125, DR3/DR4 222) the announce fits only at the top two
data rates, and the heartbeat fits none of them. DR2 is where a link lands the
moment range or noise costs it one step down, so "fits DR3" means "works until
it matters".

This codec is a pure, total, stdlib-only translation of the SAME events into a
binary form. It is not a new protocol and it decides nothing: encode() takes the
dict announce_block() already builds and decode() returns that dict back. The
TCP path never calls either function.

THE RULE THIS FILE IS WRITTEN UNDER (L, 2026-08-26: "we want lora integration
nor removal of other aspects"):

  * Nothing is removed. JSON over TCP stays byte-for-byte what it was, and it
    stays the ONLY transport that can carry a block.
  * Nothing is relaxed. No bound, verdict, route or refusal changes. In
    particular the block hash is carried in FULL -- see the note on truncation
    below, which was measured, found unnecessary, and rejected.
  * Every degradation is EXPLICIT. When something must be dropped to fit a
    frame, a flag says so and the decoder reports it. A field the receiver acts
    on is never silently shortened.

SIZES MEASURED BY test_r1_lora_frame.py (not asserted here -- run it):
the binary BLOCK_ANNOUNCE is ~48 B and the full heartbeat WITH the A21 digest
is ~70 B, so both clear DR1 (53 B) / DR2 (125 B) with headroom, and the whole
scheme survives a two-step data-rate drop that the JSON form does not.

ON HASH TRUNCATION -- CONSIDERED AND REJECTED.
The obvious saving is to carry 16 of the hash's 32 bytes: the announce's job is
only "do you already hold this?", and _accept_block_common validates the real
block on arrival, so a short dedup key would not be a security relaxation. It is
still not here, for one reason: it is not NEEDED. The full-hash frame already
fits DR1. Adding an option that weakens a field, to buy headroom nobody is
short of, is how a relaxation ends up in a codebase -- so the option does not
exist, and this paragraph is the record that it was priced rather than missed.
"""
from typing import Any, Dict, Optional, Tuple

CODEC_VERSION = 1
MAGIC = 0xC0                      # 0xC0 | version, so byte 0 self-describes (P11)

KIND_BLOCK_ANNOUNCE = 1
KIND_BLOCK_REQUEST = 2
KIND_TX_ANNOUNCE = 3
KIND_ACK = 4
_KIND_NAME = {KIND_BLOCK_ANNOUNCE: "BLOCK_ANNOUNCE",
              KIND_BLOCK_REQUEST: "BLOCK_REQUEST",
              KIND_TX_ANNOUNCE: "TX_ANNOUNCE"}
_NAME_KIND = {v: k for k, v in _KIND_NAME.items()}

FLAG_GOSSIP = 0x01
FLAG_DIGEST = 0x02
FLAG_CRISIS = 0x04
FLAG_SPIKES_ELIDED = 0x08         # set when spike kinds were dropped to fit

MAX_NODE_ID_BYTES = 32
MAX_VERSION_BYTES = 16
MAX_SPIKE_KINDS = 5               # matches build_digest's own cap
MAX_SPIKE_KIND_BYTES = 24
SRC_BYTES = 6                     # CORE_SOURCE_SHA12 is 12 hex chars = 6 raw
HASH_BYTES = 32                   # FULL sha256. Never truncated -- see docstring.


class LoraFrameError(ValueError):
    """Raised on any malformed frame. Callers treat it exactly as the TCP path
    treats a non-JSON reply: evidence the far end is not a covenant peer."""


# ------------------------------------------------------------------ varint
def _put_varint(out: bytearray, n: int) -> None:
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise LoraFrameError(f"varint needs a non-negative int, got {n!r}")
    if n > 0xFFFFFFFFFFFF:                       # 2^48: a chain height, not a bomb
        raise LoraFrameError(f"varint out of range: {n}")
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return


def _get_varint(buf: bytes, i: int) -> Tuple[int, int]:
    n = shift = 0
    start = i
    while True:
        if i >= len(buf):
            raise LoraFrameError("truncated varint")
        if i - start >= 8:
            raise LoraFrameError("over-long varint")
        b = buf[i]; i += 1
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            return n, i
        shift += 7


def _put_str(out: bytearray, s: str, cap: int) -> None:
    raw = str(s).encode("utf-8")[:cap]
    out.append(len(raw))
    out.extend(raw)


def _get_str(buf: bytes, i: int, cap: int) -> Tuple[str, int]:
    if i >= len(buf):
        raise LoraFrameError("truncated string length")
    n = buf[i]; i += 1
    if n > cap:
        raise LoraFrameError(f"string length {n} over cap {cap}")
    if i + n > len(buf):
        raise LoraFrameError("truncated string body")
    return buf[i:i + n].decode("utf-8", "replace"), i + n


def _hex_to_raw(h: Any, nbytes: int, what: str) -> bytes:
    if not isinstance(h, str) or len(h) != nbytes * 2:
        raise LoraFrameError(f"{what} must be {nbytes*2} hex chars, got {h!r:.40}")
    try:
        return bytes.fromhex(h)
    except ValueError:
        raise LoraFrameError(f"{what} is not hex")


# ------------------------------------------------------------------ encode
def encode(ev: Dict[str, Any], max_frame_bytes: Optional[int] = None) -> bytes:
    """Encode one peer event. `ev` is the dict announce_block() already builds.

    max_frame_bytes, when given, is the bearer's own ceiling. If the frame does
    not fit, the ONLY thing dropped is the digest's spike-kind list -- the least
    load-bearing field in it -- and FLAG_SPIKES_ELIDED records that it happened.
    If it still does not fit, this raises rather than shipping a frame the
    receiver cannot use. A bearer never silently sends a partial event.
    """
    kind = _NAME_KIND.get(ev.get("type"))
    if kind is None:
        raise LoraFrameError(f"unencodable type {ev.get('type')!r}")

    def build(spikes_ok: bool) -> bytes:
        out = bytearray()
        flags = 0
        if ev.get("gossip") is True:
            flags |= FLAG_GOSSIP
        dig = ev.get("digest")
        if isinstance(dig, dict):
            flags |= FLAG_DIGEST
            if dig.get("crisis") is True:
                flags |= FLAG_CRISIS
            if not spikes_ok and dig.get("spike"):
                flags |= FLAG_SPIKES_ELIDED
        out.append(MAGIC | CODEC_VERSION)
        out.append(kind)
        out.append(flags)
        if kind == KIND_BLOCK_ANNOUNCE:
            _put_varint(out, ev.get("index", 0))
            out.extend(_hex_to_raw(ev.get("hash"), HASH_BYTES, "block hash"))
        elif kind == KIND_BLOCK_REQUEST:
            _put_varint(out, ev.get("from_index", 0))
        elif kind == KIND_TX_ANNOUNCE:
            # A3-send (v8.37): a peer chooses this field's length, so the codec
            # refuses anything that is not an honest 64-char sha256 id. Same
            # rule as usable_tx_id(), enforced one layer out.
            out.extend(_hex_to_raw(ev.get("tx_id"), HASH_BYTES, "tx_id"))
        _put_str(out, ev.get("node_id", ""), MAX_NODE_ID_BYTES)
        port = ev.get("p2p_port", 0)
        if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
            raise LoraFrameError(f"p2p_port out of range: {port!r}")
        out.extend(port.to_bytes(2, "big"))
        if flags & FLAG_DIGEST:
            _put_str(out, dig.get("v", ""), MAX_VERSION_BYTES)
            out.extend(_hex_to_raw(dig.get("src"), SRC_BYTES, "digest src"))
            _put_varint(out, dig.get("height", 0))
            _put_varint(out, dig.get("peers", 0))
            kinds = list(dig.get("spike") or [])[:MAX_SPIKE_KINDS] if spikes_ok else []
            out.append(len(kinds))
            for k in kinds:
                _put_str(out, k, MAX_SPIKE_KIND_BYTES)
        return bytes(out)

    frame = build(True)
    if max_frame_bytes is not None and len(frame) > max_frame_bytes:
        frame = build(False)
    if max_frame_bytes is not None and len(frame) > max_frame_bytes:
        raise LoraFrameError(
            f"frame is {len(frame)} B against this bearer's {max_frame_bytes} B "
            f"ceiling even with spike kinds elided -- refusing to send a partial "
            f"event")
    return frame


# ------------------------------------------------------------------ decode
def decode(frame: bytes) -> Dict[str, Any]:
    """Decode to the same dict shape the TCP path hands to the receiver.

    A frame carrying a digest whose spike list was dropped comes back with
    `spikes_elided: True` and NO `spike` key -- an absent list and an empty list
    are different claims, and conflating them is how a monitor learns to report
    calm it never measured.
    """
    if not isinstance(frame, (bytes, bytearray)) or len(frame) < 5:
        raise LoraFrameError("frame too short to be a covenant LoRa frame")
    frame = bytes(frame)
    if frame[0] & 0xF0 != MAGIC:
        raise LoraFrameError(f"bad magic 0x{frame[0]:02x}")
    ver = frame[0] & 0x0F
    if ver != CODEC_VERSION:
        raise LoraFrameError(f"codec version {ver}, this build speaks {CODEC_VERSION}")
    kind, flags, i = frame[1], frame[2], 3
    if kind not in _KIND_NAME:
        raise LoraFrameError(f"unknown kind {kind}")
    ev: Dict[str, Any] = {"type": _KIND_NAME[kind]}
    if kind == KIND_BLOCK_ANNOUNCE:
        ev["index"], i = _get_varint(frame, i)
        if i + HASH_BYTES > len(frame):
            raise LoraFrameError("truncated block hash")
        ev["hash"] = frame[i:i + HASH_BYTES].hex(); i += HASH_BYTES
    elif kind == KIND_BLOCK_REQUEST:
        ev["from_index"], i = _get_varint(frame, i)
    elif kind == KIND_TX_ANNOUNCE:
        if i + HASH_BYTES > len(frame):
            raise LoraFrameError("truncated tx_id")
        ev["tx_id"] = frame[i:i + HASH_BYTES].hex(); i += HASH_BYTES
    ev["node_id"], i = _get_str(frame, i, MAX_NODE_ID_BYTES)
    if i + 2 > len(frame):
        raise LoraFrameError("truncated p2p_port")
    ev["p2p_port"] = int.from_bytes(frame[i:i + 2], "big"); i += 2
    if flags & FLAG_GOSSIP:
        ev["gossip"] = True
    if flags & FLAG_DIGEST:
        v, i = _get_str(frame, i, MAX_VERSION_BYTES)
        if i + SRC_BYTES > len(frame):
            raise LoraFrameError("truncated digest src")
        src = frame[i:i + SRC_BYTES].hex(); i += SRC_BYTES
        height, i = _get_varint(frame, i)
        peers, i = _get_varint(frame, i)
        if i >= len(frame):
            raise LoraFrameError("truncated spike count")
        n = frame[i]; i += 1
        if n > MAX_SPIKE_KINDS:
            raise LoraFrameError(f"spike count {n} over cap {MAX_SPIKE_KINDS}")
        kinds = []
        for _ in range(n):
            k, i = _get_str(frame, i, MAX_SPIKE_KIND_BYTES)
            kinds.append(k)
        dig: Dict[str, Any] = {"v": v, "src": src, "height": height,
                               "peers": peers, "crisis": bool(flags & FLAG_CRISIS)}
        if flags & FLAG_SPIKES_ELIDED:
            dig["spikes_elided"] = True
        else:
            dig["spike"] = kinds
        ev["digest"] = dig
    if i != len(frame):
        raise LoraFrameError(f"{len(frame) - i} trailing byte(s) -- not this frame")
    return ev


# ------------------------------------------------------------- bearer facts
class BearerProfile:
    """What a bearer can carry, declared rather than assumed (A5's exile bug in
    radio form: a peer that cannot receive what this node mines must be KNOWN to
    be a notification-only peer, not discovered to be one).

    `synchronous_ack=False` is the field A23 has to consult. It is declared here
    and read there; this class decides nothing on its own.
    """
    def __init__(self, name: str, max_frame_bytes: int, synchronous_ack: bool,
                 can_carry_blocks: bool, typical_bps: float,
                 duty_cycle_limit: Optional[float] = None):
        self.name = name
        self.max_frame_bytes = int(max_frame_bytes)
        self.synchronous_ack = bool(synchronous_ack)
        self.can_carry_blocks = bool(can_carry_blocks)
        self.typical_bps = float(typical_bps)
        self.duty_cycle_limit = duty_cycle_limit

    def airtime_s(self, frame_bytes: int) -> float:
        return (frame_bytes * 8) / self.typical_bps

    def min_interval_s(self, frame_bytes: int) -> float:
        """Shortest legal repeat of this frame under the bearer's duty cycle."""
        if not self.duty_cycle_limit:
            return 0.0
        return self.airtime_s(frame_bytes) / self.duty_cycle_limit

    def __repr__(self):
        return (f"BearerProfile({self.name!r}, max_frame={self.max_frame_bytes}B, "
                f"sync_ack={self.synchronous_ack}, blocks={self.can_carry_blocks})")


TCP_BEARER = BearerProfile("tcp", 64 * 1024 * 1024, True, True, 1e7, None)
# Verified against Things Network US915 regional parameters, 2026-08-26.
LORAWAN_US915_DR1 = BearerProfile("lorawan-us915-dr1", 53, False, False, 5470, None)
LORAWAN_US915_DR2 = BearerProfile("lorawan-us915-dr2", 125, False, False, 12500, None)
LORAWAN_US915_DR3 = BearerProfile("lorawan-us915-dr3", 222, False, False, 21900, None)
LORAWAN_EU868_SF12 = BearerProfile("lorawan-eu868-sf12", 51, False, False, 250, 0.01)
# Meshtastic payload (~200-237 B) is NOT pinned to a primary source -- the
# conservative 200 is used deliberately, and this comment is the flag (M40).
MESHTASTIC_LONGFAST = BearerProfile("meshtastic-longfast", 200, False, False, 1070, None)
