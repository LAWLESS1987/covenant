#!/usr/bin/env python3
"""MY1 -- the covenant's own wire: a door admits a caller by its key, not by the network.
RUN with fake requests, keys made here, a temp signer registry, a temp ally registry and
a temp ledger; the real registries and ledger are never touched.

Pins covenant_mycelium (2026-09-21, his words: "create our own native tailnet like
mycellium connection incase tail net goes down ... also as a rout for allies though
their system/companion wil have their own identity"):

  MY1a  the tailnet admits as before; an unsigned request off the tailnet is refused as
        before, with no record (it is the ordinary case).
  MY1b  a request off the tailnet signed by a registered signer (the phone's key) is
        admitted to any door; a bad signature, a stale timestamp and a reused nonce are
        refused; each decision off the tailnet is a ledger row.
  MY1c  an ally's key, registered by him, is admitted on the ally doors only, refused on
        every other door, refused when its signature is stale; an unregistered key is
        refused; a private key is never registered.
  MY1d  the LAN address is a real address of this PC or None (never loopback, never a
        tailnet address); status counts the ledger.
"""
import base64
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="my1_")
os.environ["COVENANT_MYCELIUM_PEERS"] = os.path.join(TMP, "peers.json")
os.environ["COVENANT_MYCELIUM_LEDGER"] = os.path.join(TMP, "ledger.jsonl")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_daily_plan as DP    # noqa: E402
import covenant_mycelium as MY      # noqa: E402
import covenant_unified_v8 as cov   # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


class Req:
    def __init__(self, addr, method="POST", path="/m/agent", headers=None):
        self.remote_addr, self.method, self.path, self.headers = addr, method, path, dict(headers or {})


def make_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def signed(key, method, path, body):
    return cov.sign_operator_request(key, DP.pubkey_pem(key), method, path, body)


def main():
    signers = os.path.join(TMP, "signers.json")
    phone, ally, stranger = make_key(), make_key(), make_key()
    DP.register_signer("phone", DP.pubkey_pem(phone), signers)
    tail = cov.tailnet_ok
    body = b'{"text":"hi"}'
    LAN = "192.168.1.50"

    print("MY1a -- the tailnet and the unsigned")
    ok, addr, who, how = MY.admit(Req("100.86.158.1"), body, tail, signers_path=signers)
    check("MY1a a tailnet address is admitted as before", ok and how == "tailnet" and who == "tailnet")
    ok, addr, who, how = MY.admit(Req(LAN), body, tail, signers_path=signers)
    check("MY1a an unsigned request off the tailnet is refused as before, and leaves no row", not ok and "unsigned" in how and not os.path.exists(os.environ["COVENANT_MYCELIUM_LEDGER"]), how)

    print("MY1b -- his signer over any road")
    h = signed(phone, "POST", "/m/agent", body)
    ok, addr, who, how = MY.admit(Req(LAN, headers=h), body, tail, signers_path=signers, seen=set())
    check("MY1b the phone's signature admits from the LAN to the conversation door, as the operator's signer", ok and who == "phone" and how == "signed:operator", (ok, who, how))
    h2 = signed(phone, "POST", "/checkin", body)
    ok2, _a, who2, how2 = MY.admit(Req(LAN, path="/checkin", headers=h2), body, tail, signers_path=signers, seen=set())
    check("MY1b ...and to a privileged door too (it IS his signer)", ok2 and who2 == "phone", (ok2, who2, how2))
    h3 = signed(phone, "POST", "/m/agent", body)
    ok3, _a, _w, how3 = MY.admit(Req(LAN, headers=h3), b'{"text":"changed"}', tail, signers_path=signers, seen=set())
    check("MY1b a signature over other bytes does not verify", not ok3 and "verify" in how3, how3)
    ok4, _a, _w, how4 = MY.admit(Req(LAN, headers=h), body, tail, signers_path=signers, seen=set(), now=time.time() + 3600)
    check("MY1b a stale timestamp is refused", not ok4 and "window" in how4, how4)
    seen = set()
    h5 = signed(phone, "POST", "/m/agent", body)
    MY.admit(Req(LAN, headers=h5), body, tail, signers_path=signers, seen=seen)
    ok5, _a, _w, how5 = MY.admit(Req(LAN, headers=h5), body, tail, signers_path=signers, seen=seen)
    check("MY1b a reused nonce is refused", not ok5 and "nonce" in how5, how5)
    rows = [json.loads(l) for l in open(os.environ["COVENANT_MYCELIUM_LEDGER"], encoding="utf-8") if l.strip()]
    check("MY1b every signed decision off the tailnet is a ledger row, admitted and refused alike", sum(1 for r in rows if r["kind"] == "admitted") >= 3 and sum(1 for r in rows if r["kind"] == "refused") >= 3, [r["kind"] for r in rows])

    print("MY1c -- an ally with its own identity")
    try:
        MY.register_ally("evil", "-----BEGIN PRIVATE KEY-----\nAAAA", "the operator")
        priv_ok = False
    except ValueError:
        priv_ok = True
    check("MY1c a private key is never registered", priv_ok)
    MY.register_ally("aurora", DP.pubkey_pem(ally), "the operator, 2026-09-21")
    ha = signed(ally, "POST", "/m/agent", body)
    oka, _a, whoa, howa = MY.admit(Req(LAN, headers=ha), body, tail, signers_path=signers, seen=set())
    check("MY1c an ally's signed request is admitted on the conversation door, by its own name", oka and whoa == "aurora" and howa == "signed:ally", (oka, whoa, howa))
    hb = signed(ally, "POST", "/checkin", body)
    okb, _a, whob, howb = MY.admit(Req(LAN, path="/checkin", headers=hb), body, tail, signers_path=signers, seen=set())
    check("MY1c the same ally is refused on a door that is not an ally door", not okb and whob == "aurora" and "not an ally door" in howb, howb)
    okc, _a, _w, howc = MY.admit(Req(LAN, headers=ha), body, tail, signers_path=signers, seen=set(), now=time.time() + 3600)
    check("MY1c an ally's stale signature is refused", not okc and "did not verify" in howc, howc)
    hs = signed(stranger, "POST", "/m/agent", body)
    oks, _a, whos, hows = MY.admit(Req(LAN, headers=hs), body, tail, signers_path=signers, seen=set())
    check("MY1c an unregistered key is refused, nameless", not oks and whos == "" and "not a registered" in hows, hows)
    check("MY1c the ally doors are the conversation, the handshake and health, nothing privileged", set(MY.ALLY_DOORS) == {"/m/agent", "/pc/handshake", "/health"})

    print("MY1d -- the second road and the status")
    lan = MY.lan_address(5000)
    check("MY1d the LAN address is this PC's own or None, never loopback and never a tailnet address", lan is None or (lan.endswith(":5000") and not lan.startswith("127.") and not lan.startswith("100.")), lan)
    st = MY.status()
    check("MY1d status counts the ledger and names the ally", st["allies"] == ["aurora"] and st["admitted_off_tailnet"] >= 4 and st["refused_off_tailnet"] >= 5, st)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("MY1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("MY1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
