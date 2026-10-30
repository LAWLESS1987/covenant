#!/usr/bin/env python3
"""
test_hc1_head_commitment.py -- HC1. The signed HEAD-commitment ledger and its
standalone verifier, driven BOTH ways: a genuine ledger verifies PASS, and every
tamper (forged payload, broken hash-chain, sequence gap, wrong key) turns the
verifier's OWN check red. A guard that has only ever passed has never been
observed (CLAUDE.md rule 8).

Runs offline in a temp dir: no git, no node, no network. Exit 0 iff all checks
behave as specified.
"""
import copy
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_head_commit as hc          # noqa: E402
import verify_head_commitment as v         # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + detail) if detail and not cond else ''}")


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def build_good_ledger(tmp, n=3):
    """Make n genuine commitments in an isolated temp dir and return the rows +
    the published public key."""
    key_path = os.path.join(tmp, "k", "head_commit.key")
    pub_path = os.path.join(tmp, "pub.pem")
    ledger = os.path.join(tmp, "ledger.jsonl")
    # a fake 'committed tree': on-disk bound files, no git (head/tree come back None)
    with open(os.path.join(tmp, "MANIFEST.sha256"), "w", encoding="utf-8") as fh:
        fh.write("aa  some/file.py\n")
    with open(os.path.join(tmp, "genesis.json"), "w", encoding="utf-8") as fh:
        json.dump({"hash": "0000deadbeef"}, fh)
    for i in range(n):
        # mutate the manifest between commitments so each binds a different tree
        with open(os.path.join(tmp, "MANIFEST.sha256"), "a", encoding="utf-8") as fh:
            fh.write(f"bb  file{i}.py\n")
        hc.make_commitment(repo=tmp, key_path=key_path, pubkey_path=pub_path,
                           ledger=ledger, now=1700000000 + i)
    rows = hc._read_rows(ledger)
    pubkey_pem = open(pub_path, encoding="utf-8").read()
    return rows, pubkey_pem


def main():
    with tempfile.TemporaryDirectory() as tmp:
        rows, pub = build_good_ledger(tmp, n=3)

        # --- S1: the genuine ledger verifies PASS ---
        ok, finds = v.verify_rows(rows, pub)
        check("S1 a genuine, hash-chained, signed ledger verifies PASS", ok,
              "; ".join(finds))

        # --- S2: a forged payload turns the SIGNATURE check red ---
        bad = copy.deepcopy(rows)
        bad[1]["payload"]["head"] = "f" * 40          # edit a signed field, do NOT re-sign
        ok2, f2 = v.verify_rows(bad, pub)
        check("S2 editing a signed field (no re-sign) -> FAIL on signature",
              (not ok2) and any("SIGNATURE INVALID" in m for m in f2), "; ".join(f2))

        # --- S3: breaking the hash-chain turns the CHAIN check red ---
        bad = copy.deepcopy(rows)
        bad[2]["payload"]["prev_sha256"] = "0" * 64   # wrong link; its own sig also breaks
        ok3, f3 = v.verify_rows(bad, pub)
        check("S3 a broken prev_sha256 link -> FAIL (chain)",
              (not ok3) and any("row 2" in m for m in f3), "; ".join(f3))

        # --- S4: a dropped row turns the SEQUENCE check red ---
        bad = [copy.deepcopy(rows[0]), copy.deepcopy(rows[2])]   # drop seq 1
        ok4, f4 = v.verify_rows(bad, pub)
        check("S4 a dropped row (seq gap) -> FAIL on sequence",
              (not ok4) and any("seq is" in m for m in f4), "; ".join(f4))

        # --- S5: a different key cannot pass the ledger ---
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        other_pub = rsa.generate_private_key(public_exponent=65537, key_size=2048
                    ).public_key().public_bytes(
                        serialization.Encoding.PEM,
                        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        ok5, f5 = v.verify_rows(rows, other_pub)
        check("S5 verifying against the WRONG published key -> FAIL", not ok5,
              "a ledger must not verify under a key that did not sign it")

        # --- S6: removing the tamper restores PASS (the red was earned, not stuck) ---
        ok6, _ = v.verify_rows(rows, pub)
        check("S6 the original ledger still PASSes after the tamper tests", ok6)

        # --- S7: chaining actually covers content -- recompute prev independently ---
        indep = all(
            rows[i]["payload"]["prev_sha256"]
            == ("0" * 64 if i == 0 else hashlib.sha256(_canon(rows[i - 1])).hexdigest())
            for i in range(len(rows)))
        check("S7 each prev_sha256 independently recomputes from the prior row", indep)

    passed = sum(_results)
    total = len(_results)
    print(f"\nHC1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
