#!/usr/bin/env python3
"""
covenant_anchor.py -- write the seal root into the chain itself.

WHAT IT DOES
  Builds one transaction whose data carries the SHA-256 root from
  covenant_seal.py, submits it to node A, mines it, then reads the chain back
  and confirms the root is in a block. The block index and hash are recorded
  in SEAL_ANCHOR.json.

  The anchor goes through the ethics gate like anything else. It is not
  exempt and it does not ask to be.

  covenant_client.py cannot do this: its `send` hardcodes
  data={"origin": "human"} (line 93). This builds the transaction directly,
  with the same signing, the same registration PoW, and the same endpoint.

WHAT IT PROVES, AND WHAT IT DOES NOT
  It binds the root into your ledger's history. Once mined, changing any
  sealed file changes the root, which no longer matches the one in the block
  -- and changing the block means re-mining every block after it. Inside this
  chain, the commitment is tamper-evident.

  It is NOT third-party proof of when the files existed. You run both nodes.
  Anyone who controls every node of a chain can rebuild that chain, so a
  timestamp it asserts about itself is worth what its operator is worth. That
  is not a flaw in this script; it is what "anchoring to a chain you own"
  means, and it is worth saying out loud rather than letting the ceremony
  carry it.

  What WOULD make it independent: publishing the root somewhere you do not
  control -- a public chain, a transparency log, a newspaper, an email to
  someone who keeps it. SEAL_PUBLIC.txt exists precisely so you can hand the
  root to a third party without handing over anything else. The anchor and
  that hand-off are complementary; neither substitutes for the other.

  The XRP mainnet path in this repo is gated shut (xrp_testnet_proof.json
  does not exist). This script does not go near it.

RUN
  python covenant_anchor.py                 anchor the current root
  python covenant_anchor.py --check         verify an existing anchor
  python covenant_anchor.py --port 5000 --key nodeA_prod.db.key
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ANCHOR_FILE = os.path.join(HERE, "SEAL_ANCHOR.json")


def http(method, port, path, body=None, timeout=620, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"content-type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:                                   # noqa: BLE001
            return e.code, {}
    except Exception as e:                                  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


def current_root():
    import covenant_seal as seal
    rows = seal.build_manifest()
    return seal.root_hash(rows), len(rows)


def load_key(path):
    from cryptography.hazmat.primitives import serialization
    with open(path, "rb") as f:
        sk = serialization.load_pem_private_key(f.read(), password=None)
    pem = sk.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return sk, pem


def pub_of(path):
    return load_key(path)[1]


def cmd_anchor(a):
    import covenant_unified_v8 as cov

    root, nfiles = current_root()
    print(f"  root  {root}")
    print(f"  files {nfiles}")

    sk, pem = load_key(a.key)
    receiver = pub_of(a.to_key)

    # An honest, human-readable description, because the ethics gate is going
    # to read this and it should be judging something true. No claim on
    # anyone's funds, no instruction to the judge.
    data = {
        "origin": "human",
        "kind": "seal-anchor",
        "message": ("publishing a hash commitment of my own working files; "
                    "it moves no one else's property and asserts no claim "
                    "over anyone"),
        "root": root,
        "files": nfiles,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    tx = cov.Transaction(sender_pubkey=pem, receiver=receiver, data=data,
                         amount=float(a.amount), benefit_score=0.5,
                         reg_nonce=reg)
    tx.sign(sk)
    body = {"sender_pubkey": pem, "receiver": receiver, "data": data,
            "amount": float(a.amount), "timestamp": tx.timestamp,
            "benefit_score": 0.5, "signature": tx.signature, "reg_nonce": reg}

    print("  submitting (the local model judges this; first verdict is slow)...")
    t0 = time.time()
    st, resp = http("POST", a.port, "/transactions", body)
    print(f"  HTTP {st} after {time.time() - t0:.0f}s: {json.dumps(resp)[:220]}")
    if st != 200:
        print("  REJECTED. The gate did not admit it -- that is the gate")
        print("  working, not a bug. Nothing was written.")
        return 1

    # /mine is OPERATOR-AUTHENTICATED. Posting an empty body is not enough:
    # the node records an `operator_auth_failure` anomaly and refuses, which
    # leaves the transaction admitted-but-unmined and looks exactly like a
    # slow judge. Learned that the hard way. covenant_client.py cmd_mine
    # (line 108) is the reference; this is the same three lines.
    #
    # Note the body must be byte-identical to what was signed -- b"{}" --
    # so the signature covers what actually arrives.
    print("  mining (operator-signed)...")
    raw = b"{}"
    hdrs = cov.sign_operator_request(sk, pem, "POST", "/mine", raw)
    st, mined = http("POST", a.port, "/mine", {}, headers=hdrs)
    if st != 200:
        print(f"  mine failed: HTTP {st} {json.dumps(mined)[:200]}")
        if st in (401, 403):
            print("  operator auth was rejected -- is --key the node's OWN")
            print("  identity key? node A mines with nodeA_prod.db.key.")
        return 1
    blk = mined.get("block", {})
    print(f"  block index {blk.get('index')} hash {blk.get('hash')}")

    time.sleep(6)
    ok, where = find_in_chain(a.port, root)
    rec = {"root": root, "files": nfiles,
           "utc": data["utc"],
           "block_index": where.get("index") if ok else None,
           "block_hash": where.get("hash") if ok else None,
           "tx_id": resp.get("tx_id"),
           "port": a.port,
           "confirmed_in_chain": ok,
           "note": ("Anchored to a chain this operator runs end to end. "
                    "Tamper-evident within the chain; NOT independent "
                    "third-party timestamping.")}
    with open(ANCHOR_FILE, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    print(f"  {'CONFIRMED' if ok else 'NOT FOUND'} in the chain")
    print(f"  wrote SEAL_ANCHOR.json")
    if ok:
        print()
        print("  To make this mean something outside this machine, give the")
        print("  root to someone who is not you. SEAL_PUBLIC.txt is safe to")
        print("  hand over whole.")
    return 0 if ok else 1


def find_in_chain(port, root):
    st, chain = http("GET", port, "/chain", timeout=60)
    if st != 200:
        return False, {}
    blocks = chain.get("chain") or chain.get("blocks") or []
    for b in blocks:
        for t in b.get("transactions", []):
            d = t.get("data") or {}
            if isinstance(d, dict) and d.get("root") == root:
                return True, b
    return False, {}


def cmd_check(a):
    if not os.path.exists(ANCHOR_FILE):
        print("  no SEAL_ANCHOR.json -- nothing anchored yet")
        return 2
    rec = json.load(open(ANCHOR_FILE, encoding="utf-8"))
    print(f"  anchored root {rec['root']}")
    print(f"  block index   {rec.get('block_index')}  hash {rec.get('block_hash')}")
    now, nfiles = current_root()
    print(f"  current root  {now}")
    if now == rec["root"]:
        print(f"  MATCH -- the {nfiles} files are byte-for-byte what was anchored.")
    else:
        print(f"  DIFFERENT -- files have changed since the anchor "
              f"({rec['files']} then, {nfiles} now).")
        print("  That is expected if you have been working. Re-seal and")
        print("  re-anchor, or run `covenant_seal.py verify` to see what moved.")
    ok, blk = find_in_chain(a.port, rec["root"])
    print(f"  still in the chain on port {a.port}: "
          f"{'yes, block ' + str(blk.get('index')) if ok else 'NO'}")
    if not ok:
        print("  An anchor that has left the chain means the chain was")
        print("  rebuilt. Worth knowing why.")
    return 0 if (now == rec["root"] and ok) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--key", default="nodeA_prod.db.key")
    ap.add_argument("--to-key", dest="to_key", default="nodeB_prod.db.key")
    ap.add_argument("--amount", type=float, default=1.0)
    a = ap.parse_args()
    os.chdir(HERE)
    return cmd_check(a) if a.check else cmd_anchor(a)


if __name__ == "__main__":
    sys.exit(main())
