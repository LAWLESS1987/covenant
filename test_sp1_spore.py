#!/usr/bin/env python3
"""SP1 -- the spore road and the road neurons (covenant_spore.py, A374).
RUN with keys made here, a temp signer registry, a temp ledger, a temp relay folder and a relay server on an
ephemeral loopback port; the real registries, ledger and door are never touched (the door is a stub).

His words, 2026-10-19: "make our own similar option on the mycelial road using the spiking system".

  SP1a  the road neurons: preference order with no evidence; a dead tailnet is skipped after it fails and probed
        once per interval, not on every call; one blip on a road with a run of successes does not drop it; old
        evidence leaks away; the leak between events is exactly v * exp(-dt/tau); state survives JSON.
  SP1b  the road end to end: the phone's signed request, sealed, through a folder relay, admitted by key on the
        PC, handed to the door, the answer sealed back and opened by the phone. The relay's copy holds neither the
        path nor the body.
  SP1c  what the PC refuses: the same block twice (nonce), a stale block (window), an unregistered key (and it
        gets no answer), a request signed by another key than the block, a door that is not a spore door (the
        door is never called), a changed byte, an ally's key.
  SP1d  the phone ignores an answer not sealed by the PC's own key, and gives up at its timeout.
  SP1e  the HTTP relay on loopback: a block left and collected by the box's owner; a take by another key, a
        stale take and a reused take refused; a block over 1 MB refused.
"""
import base64
import json
import math
import os
import sys
import tempfile
import threading
import time

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="sp1_")
os.environ["COVENANT_MYCELIUM_PEERS"] = os.path.join(TMP, "peers.json")
os.environ["COVENANT_MYCELIUM_LEDGER"] = os.path.join(TMP, "ledger.jsonl")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_daily_plan as DP    # noqa: E402
import covenant_mycelium as MY      # noqa: E402
import covenant_sealed_mail as SM   # noqa: E402
import covenant_spore as SP         # noqa: E402
import covenant_unified_v8 as cov   # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def make_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class Door:
    """The PC's door, stubbed: records what reached it and answers."""

    def __init__(self):
        self.calls = []

    def __call__(self, method, path, body, headers):
        self.calls.append((method, path, body))
        return 200, json.dumps({"status": "ok", "echo": body.decode("utf-8", "replace")}).encode()


def sp1a():
    print("SP1a -- the road neurons")
    n = SP.RoadNeurons(tau_s=900, probe_s=300)
    check("SP1a with no evidence the order is the preference order", n.order(0) == ["tailnet", "lan", "spore"], n.order(0))
    # away from home, Tailscale off: the tailnet and the LAN fail to connect, the spore road answers
    n.event("tailnet", False, 0)
    n.event("lan", False, 1)
    n.event("spore", True, 2)
    o = n.order(3)
    check("SP1a after tailnet and LAN fail and spore answers, spore goes first", o[0] == "spore", o)
    # 20 calls a minute apart with the tailnet and the LAN dead: count connect attempts on the dead roads. Without
    # the neurons each call tries both before spore (40). With them: each dead road once per 300 s, alternating.
    tries = {"tailnet": 0, "lan": 0}
    for k in range(20):
        now = 10 + 60 * k
        first = n.order(now)[0]
        if first in tries:
            tries[first] += 1
            n.event(first, False, now)
        n.event("spore", True, now + 1)
    check("SP1a dead roads cost 6 connect attempts in 20 calls (3 each, alternating), not 40",
          tries == {"tailnet": 3, "lan": 3}, tries)
    # the tailnet comes back: its probe succeeds and it is first again
    now = 10 + 60 * 20 + 300
    o = n.order(now)
    check("SP1a a due probe of the preferred road goes first", o[0] == "tailnet", o)
    n.event("tailnet", True, now)
    check("SP1a once the probe succeeds, the tailnet is first again", n.order(now + 1)[0] == "tailnet", n.order(now + 1))
    # hysteresis: a run of successes, then one failed connect, does not drop the road
    m = SP.RoadNeurons()
    for k in range(4):
        m.event("tailnet", True, k)
    m.event("tailnet", False, 5)
    check("SP1a one blip after a run of successes keeps the road alive", m.alive("tailnet", 6) and m.order(6)[0] == "tailnet",
          m.potential("tailnet", 6))
    m.event("tailnet", False, 7)
    m.event("tailnet", False, 8)
    m.event("tailnet", False, 9)
    check("SP1a repeated failures do drop it", not m.alive("tailnet", 10), m.potential("tailnet", 10))
    # the leak: old evidence fades back to the preference order
    q = SP.RoadNeurons(tau_s=900)
    q.event("tailnet", False, 0)
    q.event("lan", False, 0)
    q.event("spore", True, 0)
    check("SP1a after five time constants the old evidence has leaked away", q.order(5 * 900) == ["tailnet", "lan", "spore"], q.order(5 * 900))
    v0 = q.v["spore"]
    check("SP1a the leak between events is v * exp(-dt/tau), exactly",
          abs(q.potential("spore", 450) - v0 * math.exp(-0.5)) < 1e-12, q.potential("spore", 450))
    r = SP.RoadNeurons.from_json(json.loads(json.dumps(n.to_json())))
    check("SP1a state survives JSON", r.order(now + 1) == n.order(now + 1) and r.v == n.v, (r.v, n.v))


def make_world():
    signers = os.path.join(TMP, "signers.json")
    pc, phone, stranger, ally = make_key(), make_key(), make_key(), make_key()
    pems = {k: SM.pubkey_pem(v) for k, v in (("pc", pc), ("phone", phone), ("stranger", stranger), ("ally", ally))}
    DP.register_signer("phone", pems["phone"], signers)
    return signers, (pc, phone, stranger, ally), pems


def request(sealer, key, pem, pc_pem, path="/m/agent", body=b'{"text":"hello from away"}', sign_key=None, sign_pem=None):
    h = cov.sign_operator_request(sign_key or key, sign_pem or pem, "POST", path, body)
    return SP.wrap_request(sealer, "POST", path, body, h, key, pem, pc_pem)


def sp1b_c_d(signers, keys, pems):
    pc, phone, stranger, ally = keys
    ledger = os.path.join(TMP, "ledger.jsonl")
    relay = SP.FileRelay(os.path.join(TMP, "relay"))
    sealer = SP.Sealer()
    door = Door()
    seen = set()
    pcbox, phonebox = SM.fingerprint(pems["pc"]), SM.fingerprint(pems["phone"])

    print("SP1b -- the road end to end")
    rid, block = request(sealer, phone, pems["phone"], pems["pc"])
    relay.put(pcbox, block)
    stored = open(os.path.join(relay.root, pcbox, sorted(os.listdir(os.path.join(relay.root, pcbox)))[0]), encoding="utf-8").read()
    check("SP1b the relay's copy holds neither the path nor the body", "/m/agent" not in stored and "hello from away" not in stored
          and "hello from away" not in base64.b64decode("".join(stored.splitlines()[1:-1])).decode("utf-8", "replace"))
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger, seen=seen)
    check("SP1b the PC admits it by key and hands it to the door, unchanged",
          door.calls == [("POST", "/m/agent", b'{"text":"hello from away"}')] and rows and rows[0]["kind"] == "answered", (door.calls, rows))
    led = [json.loads(l) for l in open(ledger, encoding="utf-8")]
    check("SP1b the admission is a ledger row on the spore road", any(r.get("addr") == "spore" and r.get("kind") == "admitted" for r in led), led[-2:])
    got = None
    for _b, text in relay.take(phonebox):
        env, obj, _s = SM.open_env(SM.blocks(text)[0], phone, pems["phone"], pems["pc"])
        if obj.get("id") == rid:
            got = (obj["code"], base64.b64decode(obj["body"]))
    check("SP1b the answer comes back sealed to the phone and opens there with the same id",
          got is not None and got[0] == 200 and b"hello from away" in got[1], got)

    print("SP1c -- what the PC refuses")
    door.calls.clear()
    relay.put(pcbox, block)                                       # the same block, captured and left again
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger, seen=seen)
    check("SP1c the same block twice is refused (nonce) and the door is not called",
          not door.calls and rows and rows[0]["kind"] == "refused" and "nonce" in rows[0]["why"], rows)
    _rid, b2 = request(sealer, phone, pems["phone"], pems["pc"])
    relay.put(pcbox, b2)
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger,
                      seen=seen, now=time.time() + 1000)
    check("SP1c a block older than the window is refused", not door.calls and rows[0]["kind"] == "refused" and "window" in rows[0]["why"], rows)
    relay.take(phonebox)                                          # clear the phone's refusals
    _rid, b3 = request(sealer, stranger, pems["stranger"], pems["pc"])
    relay.put(pcbox, b3)
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger, seen=seen)
    strangers = relay.take(SM.fingerprint(pems["stranger"]))
    check("SP1c an unregistered key is refused and gets no answer at all",
          not door.calls and rows[0]["kind"] == "refused" and strangers == [], (rows, len(strangers)))
    _rid, b4 = request(sealer, phone, pems["phone"], pems["pc"], sign_key=stranger, sign_pem=pems["stranger"])
    relay.put(pcbox, b4)
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger, seen=seen)
    check("SP1c a request signed by another key than the block is refused",
          not door.calls and "another key" in rows[0]["why"], rows)
    _rid, b5 = request(sealer, phone, pems["phone"], pems["pc"], path="/daily_plan/approve")
    relay.put(pcbox, b5)
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger, seen=seen)
    check("SP1c a door that is not a spore door is refused and never called", not door.calls and "not a spore door" in rows[0]["why"], rows)
    _rid, b6 = request(sealer, phone, pems["phone"], pems["pc"])
    lines = b6.splitlines()
    mid = lines[1]
    lines[1] = mid[:10] + ("A" if mid[10] != "A" else "B") + mid[11:]
    relay.put(pcbox, "\n".join(lines))
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger, seen=seen)
    check("SP1c a changed byte is refused before anything is opened", not door.calls and rows[0]["kind"] == "refused", rows)
    MY.register_ally("aurora", pems["ally"], "the test", path=os.environ["COVENANT_MYCELIUM_PEERS"])
    _rid, b7 = request(sealer, ally, pems["ally"], pems["pc"])
    relay.put(pcbox, b7)
    rows = SP.pc_pass(relay, pc, pems["pc"], forward=door, sealer=sealer, signers_path=signers, ledger_path=ledger, seen=seen)
    check("SP1c an ally's key, registered on the ally doors, is refused on the spore road", not door.calls and rows[0]["kind"] == "refused", rows)
    relay.take(phonebox)

    print("SP1d -- the phone's call")
    clock = [0.0]
    forged = SM.seal(SP.KIND_REPLY, {"kind": SP.KIND_REPLY, "id": "x", "code": 200, "body": ""}, stranger, pems["stranger"], pems["phone"])

    class Watch(SP.FileRelay):
        def put(self, box, blob):
            bid = super().put(box, blob)
            if box == pcbox:                                      # a stranger answers first, with the right id
                rid_now = None
                try:
                    _e, o, _s = SM.open_env(SM.blocks(blob)[0], pc, pems["pc"])
                    rid_now = o["id"]
                except Exception:                                 # noqa: BLE001
                    pass
                super().put(phonebox, SM.seal(SP.KIND_REPLY, {"kind": SP.KIND_REPLY, "id": rid_now, "code": 200, "body": ""},
                                              stranger, pems["stranger"], pems["phone"]))
            return bid

    w = Watch(os.path.join(TMP, "relay2"))
    h = cov.sign_operator_request(phone, pems["phone"], "POST", "/m/agent", b"{}")
    out = SP.call(w, sealer, "POST", "/m/agent", b"{}", h, phone, pems["phone"], pems["pc"], timeout=6, poll_s=2,
                  clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
    check("SP1d an answer not sealed by the PC's own key is ignored, and the call gives up at its timeout",
          out is None and clock[0] >= 6, (out, clock[0], forged[:20]))


def sp1e(pems, keys):
    print("SP1e -- the HTTP relay on loopback")
    pc, phone, stranger, _ally = keys
    srv = SP.make_relay_server(os.path.join(TMP, "relay_http"), "127.0.0.1", 0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        url = "http://127.0.0.1:%d" % srv.server_address[1]
        box = SM.fingerprint(pems["pc"])
        owner = SP.HttpRelay(url, pc, pems["pc"])
        bid = SP.HttpRelay(url).put(box, "a block")
        got = owner.take(box)
        check("SP1e a block left by anyone is collected by the box's owner", got == [(bid, "a block")], got)
        SP.HttpRelay(url).put(box, "another")
        thief = SP.HttpRelay(url, stranger, pems["stranger"])
        try:
            thief.take(box, proof=SP.take_proof(stranger, pems["stranger"], box))
            refused = False
        except Exception as e:                                    # noqa: BLE001
            refused = "403" in str(e)
        check("SP1e a take signed by another key is refused (403)", refused)
        try:
            owner.take(box, proof=SP.take_proof(pc, pems["pc"], box, now=time.time() - 1000))
            stale = False
        except Exception as e:                                    # noqa: BLE001
            stale = "403" in str(e)
        check("SP1e a stale take is refused", stale)
        p = SP.take_proof(pc, pems["pc"], box)
        first = owner.take(box, proof=p)
        try:
            owner.take(box, proof=p)
            reused = False
        except Exception as e:                                    # noqa: BLE001
            reused = "403" in str(e)
        check("SP1e the owner's take collects what waited; the same take proof twice is refused", first and first[0][1] == "another" and reused, (first, reused))
        try:
            SP.HttpRelay(url).put(box, "x" * ((1 << 20) + 10))
            big = False
        except Exception as e:                                    # noqa: BLE001
            big = "400" in str(e) or "413" in str(e)
        check("SP1e a block over 1 MB is refused", big)
    finally:
        srv.shutdown()
        srv.server_close()


def main():
    sp1a()
    signers, keys, pems = make_world()
    sp1b_c_d(signers, keys, pems)
    sp1e(pems, keys)
    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("SP1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("SP1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
