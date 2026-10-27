#!/usr/bin/env python3
"""
witness_memory_root.py -- have the nodes witness the memory store's state root.

WHAT IT DOES
  Computes the state root of the PRIVATE memory store, builds one transaction
  carrying only that root, submits it to a node, mines it, and confirms the
  root landed in a block. The block index and hash go into MEMORY_WITNESS.json.

  This is covenant_anchor.py's mechanism pointed at a different object. That
  one anchors the seal root over working FILES. This one anchors the state
  root over MEMORIES, which is the thing that has to outlive its author.

WHAT CROSSES THE WIRE
  The root, the memory count, and a timestamp. That is all.

  A state root is a domain-separated Merkle root over each memory's claim
  digest. It is one hash. It reveals no name, no claim, no content, and it
  cannot be reversed into any of them. The nodes witness THAT something was
  recorded and what its fingerprint was. They never learn what it said.

  That separation is the whole design. The corpus names third parties and
  carries one person's medical detail, so it can never be published. Its
  fingerprint carries none of that and can be published anywhere. Custody and
  verification come apart, which is what lets the record be held by people who
  are not trusted to read it.

WHAT IT PROVES, AND WHAT IT DOES NOT
  Inside this chain, the commitment is tamper-evident: alter any memory and
  its claim digest changes, so the root changes, so it no longer matches the
  witnessed one -- and changing the block means re-mining every block after it.

  It is NOT third-party proof. The same caveat covenant_anchor.py already
  states applies here without modification: anyone who controls every node of
  a chain can rebuild that chain, so a timestamp it asserts about itself is
  worth what its operator is worth.

  Worse, and this is the part worth being blunt about: the node processes and
  the memory store live on ONE host. An adversary at root can rewrite the
  store, recompute the root, rewrite the chain, and recompute every block
  hash. Self-consistency is not external verifiability. The verifier runs on
  the compromised machine too.

  So this script is one half. The other half is docs/SUCCESSION_ANCHORS.md,
  which publishes the same root to a repository the operator does not solely
  control, where every clone is a replica. Neither half substitutes for the
  other. The nodes make local tampering detectable; the published anchor makes
  host-level tampering detectable. Run both, or the guarantee is only as good
  as the machine.

  The witness goes through the ethics gate like anything else. It is not
  exempt and it does not ask to be. If the gate refuses it, that is the gate
  working, and nothing is written.

RUN
  python witness_memory_root.py --key <operator.pem> --to-key <receiver.pem>
  python witness_memory_root.py --check              # find the root in the chain
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WITNESS_FILE = os.path.join(HERE, "MEMORY_WITNESS.json")


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


def memory_root(root_dir: str):
    """The state root of the memory store. Never its contents."""
    sys.path.insert(0, os.path.join(HERE, "ai_memory_system"))
    from memory_store import MemoryStore          # noqa: E402
    store = MemoryStore(root_dir)
    r = store.state_root()
    integ = store.verify_integrity()
    return r["root"], int(r["memories"]), integ


def load_key(path):
    from cryptography.hazmat.primitives import serialization
    with open(path, "rb") as f:
        sk = serialization.load_pem_private_key(f.read(), password=None)
    pem = sk.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return sk, pem


def cmd_witness(a):
    import covenant_unified_v8 as cov

    root_dir = a.memory_root or os.environ.get("AI_MEMORY_ROOT") or ""
    if not root_dir or not os.path.isdir(root_dir):
        print("  no memory store. Pass --memory-root or set AI_MEMORY_ROOT.")
        return 2

    root, n, integ = memory_root(root_dir)
    print(f"  root     {root}")
    print(f"  memories {n}")
    print(f"  integrity ok={integ['ok']} drifted={len(integ['drifted'])} "
          f"missing={len(integ['missing'])}")

    # Refuse to witness a store that does not verify. Anchoring a broken root
    # would give a wrong thing the appearance of a checked one, which is worse
    # than not anchoring at all.
    if not integ["ok"] or integ["drifted"] or integ["missing"]:
        print("  REFUSING: the store does not verify. Fix the drift first.")
        print("  Witnessing a root you cannot vouch for launders the error.")
        return 1

    sk, pem = load_key(a.key)
    receiver = load_key(a.to_key)[1]

    # Written to be true and readable, because the ethics gate reads it and
    # should be judging something honest. No claim on anyone, no instruction
    # to the judge, no request for exemption.
    data = {
        "origin": "human",
        "kind": "memory-witness",
        "message": ("publishing a hash commitment of my own memory store so "
                    "the record can be checked by people who cannot read it; "
                    "it carries no contents, moves no one's property, and "
                    "asserts no claim over anyone"),
        "root": root,
        "memories": n,
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

    raw = json.dumps({}, separators=(",", ":")).encode()
    hdrs = cov.sign_operator_request(sk, pem, "POST", "/mine", raw)
    st, mined = http("POST", a.port, "/mine", {}, headers=hdrs)
    print(f"  mine HTTP {st}: {json.dumps(mined)[:200]}")

    found = find_in_chain(a.port, root)
    if not found:
        print("  root is NOT in a block yet. Nothing is witnessed until it is.")
        return 1

    rec = {"root": root, "memories": n,
           "block_index": found["index"], "block_hash": found["hash"],
           "utc": data["utc"], "port": a.port,
           "note": ("Local witness only. Independent verification requires the "
                    "same root published outside this operator's control; see "
                    "docs/SUCCESSION_ANCHORS.md.")}
    with open(WITNESS_FILE, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    print(f"  witnessed in block {found['index']}  ->  MEMORY_WITNESS.json")
    return 0


def find_in_chain(port, root):
    st, body = http("GET", port, "/chain", timeout=60)
    if st != 200:
        return None
    chain = body.get("chain", body) if isinstance(body, dict) else body
    if not isinstance(chain, list):
        return None
    for blk in chain:
        for tx in blk.get("transactions", []):
            d = tx.get("data") or {}
            if isinstance(d, dict) and d.get("root") == root:
                return {"index": blk.get("index"), "hash": blk.get("hash")}
    return None


def cmd_check(a):
    root_dir = a.memory_root or os.environ.get("AI_MEMORY_ROOT") or ""
    if not root_dir:
        print("  pass --memory-root or set AI_MEMORY_ROOT")
        return 2
    root, n, _ = memory_root(root_dir)
    print(f"  current root {root}  ({n} memories)")
    found = find_in_chain(a.port, root)
    if found:
        print(f"  WITNESSED in block {found['index']} ({found['hash'][:16]}...)")
        return 0
    print("  NOT in the chain. Either it was never witnessed, or the store")
    print("  changed since it was. Those are different problems: check")
    print("  MEMORY_WITNESS.json for the last root that was.")
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--memory-root", default="")
    p.add_argument("--key", default="")
    p.add_argument("--to-key", default="")
    p.add_argument("--amount", type=float, default=0.0)
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    if a.check:
        return cmd_check(a)
    if not a.key or not a.to_key:
        print("  --key and --to-key are required to witness")
        return 2
    return cmd_witness(a)


if __name__ == "__main__":
    raise SystemExit(main())
