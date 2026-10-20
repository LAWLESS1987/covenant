#!/usr/bin/env python3
"""test_rct1_receipt.py -- RCT1: a portable signed receipt verifies from itself, and every tamper fails.

WHAT THIS GUARDS. covenant_receipt adds the Agent Embassy-style portable proof to a receipt: an eip191 signature
over the canonical SHA-256, verifiable from the receipt + proof alone (no ledger, no server). The property that
matters is that verification actually depends on the content and the signature -- a receipt altered after signing,
a corrupted signature, a forged signer, or a signer outside the published registry must all FAIL.

DRIVEN BOTH WAYS. RCT1.0 a validly signed receipt verifies; RCT1.1-1.4 each kind of tamper is rejected with a
reason; RCT1.5 the canonical hash is order-independent (same receipt, different key order -> same hash), so the
signature is over content, not JSON incidentals. Uses an ephemeral key, so it is independent of the deployed
signer. No network, no money. Run: python3 test_rct1_receipt.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_receipt as R                                           # noqa: E402

try:
    import eth_account                                                # noqa: F401 - optional dep for signing
    _HAVE_ETH = True
except ImportError:
    _HAVE_ETH = False

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:200]), flush=True)


def main():
    print("RCT1 -- a portable signed receipt verifies from itself; every tamper fails\n")

    # MONEY-SAFETY (runs regardless of the optional dep): covenant_earn._sign_receipt must NEVER block or raise on
    # a settled job. If signing is down, the receipt is emitted unsigned and the sale is unaffected.
    import covenant_earn as E
    orig_sign = R.sign
    try:
        R.sign = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("signing down"))
        rc = {"id": "safety", "amount_usdc": "0.020000"}
        E._sign_receipt(rc)                                          # must not raise
        check("RCT1.G signing failure NEVER blocks a settled job -- receipt emitted unsigned, no exception",
              "proof" not in rc)
    finally:
        R.sign = orig_sign

    if not _HAVE_ETH:
        print("\nRCT1: mechanism checks NOT RUN -- eth-account absent; the money-safety check above still ran.")
        ok_n = sum(1 for r in results if r)
        print("RCT1: %d/%d passed" % (ok_n, len(results)))
        return 0 if ok_n == len(results) else 1
    from eth_account import Account
    acct = Account.create()                                           # ephemeral signer, not the deployed one
    registry = [acct.address]

    receipt = {"tool": "receipt", "amount": "20000", "asset": "USDC", "network": "eip155:8453",
               "checked": "1 citation in a 1200-char text against 2 files", "t": "2026-10-20T00:00:00Z"}
    proof = R.sign(receipt, acct)

    # RCT1.0 -- a validly signed receipt verifies, from the receipt + proof alone, against the registry
    ok, why = R.verify(receipt, proof, allowed_signers=registry)
    check("RCT1.0 a validly signed receipt verifies (no ledger, no server)", ok, why)

    # RCT1.1 -- the receipt is altered after signing -> hash mismatch
    tampered = dict(receipt, amount="2000000")
    ok, why = R.verify(tampered, proof, allowed_signers=registry)
    check("RCT1.1 a receipt altered after signing is REJECTED (hash mismatch)", not ok and "hash mismatch" in why, why)

    # RCT1.2 -- the signature is corrupted -> unrecoverable / mismatch
    bad = dict(proof, signature=proof["signature"][:-6] + "000000")
    ok, why = R.verify(receipt, bad, allowed_signers=registry)
    check("RCT1.2 a corrupted signature is REJECTED", not ok, why)

    # RCT1.3 -- the claimed signer is forged (someone swaps in another address) -> signer mismatch
    forged = dict(proof, signer="0x000000000000000000000000000000000000dEaD")
    ok, why = R.verify(receipt, forged, allowed_signers=registry)
    check("RCT1.3 a forged claimed-signer is REJECTED (recovered address won't match)", not ok, why)

    # RCT1.4 -- a real, valid signature from a signer OUTSIDE the published registry -> rejected
    other = Account.create()
    other_proof = R.sign(receipt, other)
    ok, why = R.verify(receipt, other_proof, allowed_signers=registry)
    check("RCT1.4 a valid signature from an UNPUBLISHED signer is REJECTED (not in the registry)",
          not ok and "registry" in why, why)
    ok2, _ = R.verify(receipt, other_proof, allowed_signers=[other.address])   # ...and accepted under its own registry
    check("RCT1.4b ...but that same signature verifies under ITS own registry -- the registry is the only gate here",
          ok2)

    # RCT1.5 -- canonical hash is order-independent: content, not JSON key order, is what's signed
    reordered = {k: receipt[k] for k in reversed(list(receipt.keys()))}
    check("RCT1.5 the canonical hash is order-independent (same content, different key order -> same hash)",
          R.receipt_hash(receipt) == R.receipt_hash(reordered) == proof["hash"],
          (R.receipt_hash(receipt), R.receipt_hash(reordered)))

    # RCT1.6 -- LIVE INTEGRATION: covenant_earn attaches a proof that verifies from the receipt alone, against the
    # node's own published signer. This is the end-to-end path a buyer sees.
    live = {"id": "live", "offer": "receipt", "amount_usdc": "0.020000", "network": "eip155:8453",
            "input_sha256": "a" * 64, "result_sha256": "b" * 64, "checked": "1 citation"}
    E._sign_receipt(live)
    ok, why = R.verify({k: v for k, v in live.items() if k != "proof"}, live.get("proof", {}),
                       allowed_signers=[R.published_signer()])
    check("RCT1.6 live integration: covenant_earn signs a receipt that verifies against the node's published signer",
          "proof" in live and ok, why)
    disc = E._signer_discovery()
    check("RCT1.7 the signer-discovery endpoint exposes the signer a buyer verifies against",
          bool(disc) and disc.get("address") == R.published_signer() and disc.get("scheme") == "eip191-personal-sign",
          disc)

    ok_n = sum(1 for r in results if r)
    print("\nRCT1: %d/%d passed" % (ok_n, len(results)))
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
