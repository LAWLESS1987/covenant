"""test_r1_lora_frame.py -- R1: the LoRa announce codec.

Pure functions: no node, no socket, no key, no radio. Runs on any platform in
under a second, which is the point -- the hardware question is open and this
half of the work does not depend on its answer.

Written from the failure side (M9): the section that matters most is R4, where
every check asserts that a malformed frame is REFUSED. A codec that is
permissive about what it accepts off a radio is a parser sitting on an
unauthenticated broadcast medium.

R3 is the PRE-FIX RECORD in the sense this project means it: it runs the
EXISTING json.dumps path against the same bearer ceilings and shows what does
not fit. Those checks pass on a tree with no codec in it at all, and they are
the measurement that justifies the file.

Sections
  R1  round trip: decode(encode(ev)) == ev, for every frame the mycelium sends
  R2  SIZE: the binary frames against real LoRaWAN payload ceilings
  R3  pre-fix record: the same events as JSON, and what they do not fit
  R4  refusal: malformed, hostile and over-long frames
  R5  explicit degradation: elision is flagged, absent != empty
  R6  no relaxation: the hash is carried whole and cannot be shortened
  R7  bearer arithmetic: airtime, duty cycle, and the 8 MiB block
  R8  source-level pins, on TOKENIZED code (M42)
"""
import io
import json
import sys
import tokenize

sys.path.insert(0, ".")
import covenant_lora_frame as C

PASS = FAIL = 0
def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}" + (f"\n        {detail}" if detail else ""))
def refuses(label, fn, *a, **k):
    try:
        fn(*a, **k)
        check(label, False, "accepted something it must refuse")
    except C.LoraFrameError as e:
        check(label, True); return e
    except Exception as e:
        check(label, False, f"raised {type(e).__name__} instead of LoraFrameError: {e}")

H = "3f" * 32
TXID = "a7" * 32
ANNOUNCE = {"type": "BLOCK_ANNOUNCE", "index": 3, "hash": H,
            "node_id": "A", "p2p_port": 5001}
HEARTBEAT = dict(ANNOUNCE, gossip=True, digest={
    "v": "v8.37", "src": "07e097f3e37f", "height": 3, "peers": 1,
    "crisis": False, "spike": []})
HEARTBEAT_SPIKING = dict(ANNOUNCE, gossip=True, digest={
    "v": "v8.37", "src": "07e097f3e37f", "height": 4210, "peers": 6,
    "crisis": True, "spike": ["peer_send_failure", "peer_tx_id_invalid"]})
REQUEST = {"type": "BLOCK_REQUEST", "from_index": 3, "node_id": "A", "p2p_port": 5001}
TXANN = {"type": "TX_ANNOUNCE", "tx_id": TXID, "node_id": "A", "p2p_port": 5001}

print("\n=== R1  ROUND TRIP -- decode(encode(ev)) is the dict the receiver expects")
for name, ev in [("novel announce", ANNOUNCE), ("heartbeat + digest", HEARTBEAT),
                 ("heartbeat, spiking, crisis", HEARTBEAT_SPIKING),
                 ("block request", REQUEST), ("tx announce", TXANN)]:
    got = C.decode(C.encode(ev))
    check(f"R1 {name} round-trips exactly", got == ev, f"{got!r}\n        != {ev!r}")
check("R1f a big chain height survives the varint",
      C.decode(C.encode(dict(ANNOUNCE, index=9_000_000)))["index"] == 9_000_000)
check("R1g encode is deterministic (same bytes twice)",
      C.encode(HEARTBEAT_SPIKING) == C.encode(HEARTBEAT_SPIKING))

print("\n=== R2  SIZE -- binary frames against real LoRaWAN ceilings")
sizes = {n: len(C.encode(e)) for n, e in
         [("BLOCK_ANNOUNCE", ANNOUNCE), ("heartbeat+digest", HEARTBEAT),
          ("heartbeat spiking", HEARTBEAT_SPIKING),
          ("BLOCK_REQUEST", REQUEST), ("TX_ANNOUNCE", TXANN)]}
print(f"    {'frame':22s} {'binary':>7s} {'json':>7s}  ratio")
for n, e in [("BLOCK_ANNOUNCE", ANNOUNCE), ("heartbeat+digest", HEARTBEAT),
             ("heartbeat spiking", HEARTBEAT_SPIKING),
             ("BLOCK_REQUEST", REQUEST), ("TX_ANNOUNCE", TXANN)]:
    b, j = sizes[n], len(json.dumps(e))
    print(f"    {n:22s} {b:6d}B {j:6d}B  {j/b:.2f}x")
check("R2a the novel announce fits LoRaWAN US915 DR1 (53 B, SF9)",
      sizes["BLOCK_ANNOUNCE"] <= C.LORAWAN_US915_DR1.max_frame_bytes,
      f"{sizes['BLOCK_ANNOUNCE']} B")
check("R2b the novel announce fits EU868 SF12 (51 B), the worst legal case",
      sizes["BLOCK_ANNOUNCE"] <= C.LORAWAN_EU868_SF12.max_frame_bytes,
      f"{sizes['BLOCK_ANNOUNCE']} B")
check("R2c the FULL heartbeat + A21 digest fits DR2 (125 B)",
      sizes["heartbeat+digest"] <= C.LORAWAN_US915_DR2.max_frame_bytes,
      f"{sizes['heartbeat+digest']} B")
check("R2d a spiking heartbeat still fits DR2 -- the worst real digest",
      sizes["heartbeat spiking"] <= C.LORAWAN_US915_DR2.max_frame_bytes,
      f"{sizes['heartbeat spiking']} B")
check("R2e every frame fits Meshtastic's conservative 200 B",
      max(sizes.values()) <= C.MESHTASTIC_LONGFAST.max_frame_bytes)

print("\n=== R3  PRE-FIX RECORD -- the same events as JSON, which is what ships today")
check("R3a JSON announce does NOT fit DR1 -- the codec is necessary, not cosmetic",
      len(json.dumps(ANNOUNCE)) > C.LORAWAN_US915_DR1.max_frame_bytes,
      f"{len(json.dumps(ANNOUNCE))} B vs 53 B")
check("R3b JSON announce does NOT fit DR2 either (one step down from usable)",
      len(json.dumps(ANNOUNCE)) > C.LORAWAN_US915_DR2.max_frame_bytes,
      f"{len(json.dumps(ANNOUNCE))} B vs 125 B")
check("R3c JSON heartbeat fits NO US915 data rate at all",
      len(json.dumps(HEARTBEAT)) > C.LORAWAN_US915_DR3.max_frame_bytes,
      f"{len(json.dumps(HEARTBEAT))} B vs 222 B")
check("R3d the JSON announce DOES fit DR3 -- so 'it works' until the link steps down",
      len(json.dumps(ANNOUNCE)) <= C.LORAWAN_US915_DR3.max_frame_bytes)

print("\n=== R4  REFUSAL -- every check here asserts a malformed frame is REJECTED")
good = C.encode(ANNOUNCE)
refuses("R4a bad magic byte", C.decode, b"\x00" + good[1:])
refuses("R4b unknown codec version", C.decode, bytes([C.MAGIC | 9]) + good[1:])
refuses("R4c unknown kind", C.decode, good[:1] + b"\x7f" + good[2:])
refuses("R4d truncated frame", C.decode, good[:-4])
refuses("R4e trailing bytes -- two events in one frame", C.decode, good + b"\x00")
refuses("R4f empty frame", C.decode, b"")
refuses("R4g not bytes at all", C.decode, "not a frame")
refuses("R4h a short hash cannot be encoded", C.encode, dict(ANNOUNCE, hash="3f" * 16))
refuses("R4i a non-hex hash cannot be encoded", C.encode, dict(ANNOUNCE, hash="z" * 64))
refuses("R4j a bool index is refused (A4's float-index class)",
        C.encode, dict(ANNOUNCE, index=True))
refuses("R4k a negative index is refused", C.encode, dict(ANNOUNCE, index=-1))
refuses("R4l a float index is refused", C.encode, dict(ANNOUNCE, index=2.0))
refuses("R4m an out-of-range port is refused", C.encode, dict(ANNOUNCE, p2p_port=99999))
refuses("R4n an over-long tx_id is refused (A3-send's amplifier, one layer out)",
        C.encode, dict(TXANN, tx_id="a" * 200_000))
refuses("R4o an unencodable type is refused", C.encode, {"type": "SOMETHING_ELSE"})
refuses("R4p an over-long varint is refused", C.decode,
        good[:3] + b"\xff" * 9 + good[4:])
e = refuses("R4q a frame over the bearer ceiling RAISES rather than truncating",
            C.encode, HEARTBEAT_SPIKING, 20)
check("R4r ...and the refusal names the ceiling it could not meet",
      bool(e) and "20 B" in str(e), str(e))
badnode = C.encode(dict(ANNOUNCE, node_id="N" * 500))
check("R4s an over-long node_id is CLAMPED at encode, never over-run",
      len(C.decode(badnode)["node_id"]) == C.MAX_NODE_ID_BYTES)
fuzzed = 0
for i in range(len(good)):
    for bit in (0x01, 0x80):
        m = bytearray(good); m[i] ^= bit
        try:
            C.decode(bytes(m))
        except C.LoraFrameError:
            fuzzed += 1
        except Exception as ex:
            check(f"R4t byte {i} bit {bit:#x}", False,
                  f"leaked {type(ex).__name__}: {ex}")
check("R4t single-bit flips never leak a non-LoraFrameError",
      True, f"{fuzzed} of {len(good)*2} flips rejected, none leaked")

print("\n=== R5  EXPLICIT DEGRADATION -- elision is flagged, absent != empty")
tight = C.encode(HEARTBEAT_SPIKING, sizes["heartbeat+digest"] + 2)
d = C.decode(tight)["digest"]
check("R5a a frame too tight for spike kinds still encodes", len(tight) > 0)
check("R5b ...and reports spikes_elided rather than an empty list",
      d.get("spikes_elided") is True and "spike" not in d, repr(d))
check("R5c an honestly-empty spike list is reported as [], NOT as elided",
      C.decode(C.encode(HEARTBEAT))["digest"] == {"v": "v8.37", "src": "07e097f3e37f",
      "height": 3, "peers": 1, "crisis": False, "spike": []})
check("R5d elision drops ONLY spike kinds -- height, peers, crisis survive",
      d["height"] == 4210 and d["peers"] == 6 and d["crisis"] is True, repr(d))
check("R5e crisis rides a flag bit, so it costs nothing and cannot be elided",
      C.decode(C.encode(HEARTBEAT_SPIKING))["digest"]["crisis"] is True)

print("\n=== R6  NO RELAXATION -- the hash is carried whole")
check("R6a HASH_BYTES is a full sha256", C.HASH_BYTES == 32)
check("R6b the decoded hash is the full 64-hex original",
      C.decode(C.encode(ANNOUNCE))["hash"] == H)
check("R6c the codec exposes no truncation parameter at all",
      not any("trunc" in n.lower() for n in dir(C) if not n.startswith("_")),
      str([n for n in dir(C) if "trunc" in n.lower()]))
check("R6d a tx_id must be an honest 64-char sha256 id (A3-send's rule)",
      C.decode(C.encode(TXANN))["tx_id"] == TXID)

print("\n=== R7  BEARER ARITHMETIC -- what the physics actually permits")
ann_b = sizes["BLOCK_ANNOUNCE"]
mesh_air = C.MESHTASTIC_LONGFAST.airtime_s(ann_b)
block_air = C.MESHTASTIC_LONGFAST.airtime_s(8 * 1024 * 1024)
print(f"    announce airtime, LongFast 1.07kbps : {mesh_air:.2f} s")
print(f"    8 MiB block, same bearer            : {block_air/3600:.1f} h continuous")
print(f"    ...under EU868's 1% duty cycle      : {block_air/0.01/86400:.0f} days")
print(f"    EU868 SF12 min legal announce gap   : "
      f"{C.LORAWAN_EU868_SF12.min_interval_s(ann_b):.0f} s")
check("R7a an announce is under 2 s of airtime even on the slowest preset",
      mesh_air < 2.0, f"{mesh_air:.2f}s")
check("R7b an 8 MiB block is over 10 h of continuous airtime -- never carry blocks",
      block_air > 10 * 3600, f"{block_air/3600:.1f}h")
check("R7c no LoRa bearer claims it can carry blocks",
      not any(b.can_carry_blocks for b in
              (C.LORAWAN_US915_DR1, C.LORAWAN_US915_DR2, C.LORAWAN_US915_DR3,
               C.LORAWAN_EU868_SF12, C.MESHTASTIC_LONGFAST)))
check("R7d no LoRa bearer claims a synchronous ack -- the field A23 must read",
      not any(b.synchronous_ack for b in
              (C.LORAWAN_US915_DR1, C.LORAWAN_US915_DR2, C.LORAWAN_US915_DR3,
               C.LORAWAN_EU868_SF12, C.MESHTASTIC_LONGFAST)))
check("R7e TCP still declares itself the transport that CAN carry blocks",
      C.TCP_BEARER.can_carry_blocks and C.TCP_BEARER.synchronous_ack)
gap = C.LORAWAN_EU868_SF12.min_interval_s(ann_b)
check("R7f EU868 SF12 needs a gossip interval longer than the 120 s default "
      "-- C4's COVENANT_TIP_GOSSIP_INTERVAL=600 lever is the right one",
      120 < gap <= 600, f"min legal gap {gap:.0f}s")

print("\n=== R8  SOURCE PINS, on tokenized code so a comment cannot satisfy them (M42)")
def code_only(path, names_only=False):
    """Tokenized view of a source file (M42: a comment that mentions the symbol
    you are forbidding will satisfy a naive `in` test).

    names_only additionally drops STRING tokens, and that distinction is
    load-bearing. It was learned inside this suite: R8e's first draft asked
    whether the word "truncat" appears in the code, and it DOES -- in
    `raise LoraFrameError("truncated varint")` and seven siblings, which are
    refusal messages saying "this frame arrived truncated, I reject it". That
    is the exact OPPOSITE of the feature being forbidden, and scrubbing those
    messages to make the check pass would have removed real diagnostics to
    satisfy a badly-worded assertion. A claim about whether something is
    IMPLEMENTED is a claim about identifiers; a refusal message is prose that
    happens to live in a string.
    """
    out = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE):
                continue
            if tok.type == tokenize.STRING:
                if names_only or tok.line.strip().startswith(('"""', "'''")):
                    continue
            if names_only and tok.type != tokenize.NAME:
                continue
            out.append(tok.string)
    return " ".join(out)
src = code_only("covenant_lora_frame.py")
names = code_only("covenant_lora_frame.py", names_only=True)
check("R8a the codec imports nothing from the node -- it cannot change node behaviour",
      "covenant_unified_v8" not in src and "import socket" not in src)
check("R8b the codec opens no socket and reads no file",
      "socket" not in src and "open (" not in src.replace("open(", "open ("))
check("R8c no bound is read from the environment here -- the bearer declares it",
      "os.environ" not in src and "getenv" not in src)
check("R8d 'BearerProfile' carries synchronous_ack, which is what A23 must consult",
      "synchronous_ack" in src)
check("R8e no IDENTIFIER implements truncation -- the rejected option is "
      "documented and priced, never built",
      "truncat" not in names.lower(),
      f"found among identifiers: "
      f"{[w for w in names.split() if 'truncat' in w.lower()]}")
check("R8f ...and 'truncated' DOES still appear in the REFUSAL messages, "
      "which is the opposite feature and must not be scrubbed to make R8e pass",
      "truncat" in src.lower())
# M31: mutation-test the boundary check itself. A guard that has only ever
# seen correct code has never been tested.
_mutant = open("covenant_lora_frame.py", encoding="utf-8").read().replace(
    "def encode(ev: Dict[str, Any], max_frame_bytes: Optional[int] = None) -> bytes:",
    "def encode(ev, max_frame_bytes=None, truncate_hash=False) -> bytes:", 1)
open("/tmp/_mutant_codec.py", "w", encoding="utf-8").write(_mutant)
check("R8g MUTATION: injecting a truncate_hash parameter makes R8e fail, so "
      "R8e is a measurement rather than a formality",
      "truncat" in code_only("/tmp/_mutant_codec.py", names_only=True).lower())

print(f"\n{'='*64}\nR1 LoRa frame codec: {PASS} passed, {FAIL} failed\n{'='*64}")
sys.exit(1 if FAIL else 0)
