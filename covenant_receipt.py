#!/usr/bin/env python3
"""covenant_receipt.py -- portable, third-party-verifiable receipts for covenant_earn.

CREDIT. The portable-receipt design is borrowed from Agent Embassy (nootxlm, aemb.pro), with attribution: an
eip191 signature over a canonical SHA-256 of the receipt, the signer published at a well-known path, verifiable
from the receipt alone (no server, no ledger). See docs/INTEROP_AGENT_EMBASSY.md. covenant_earn already emits
honest-scoped receipts hash-chained to a public-method ledger; this adds the portable signature so a receipt
verifies WITHOUT the ledger.

NOT A MONEY KEY. This signs RECEIPTS (attestations), never transactions. A compromised receipt signer can forge an
attestation, not move funds -- a strictly lower-stakes key than the payment wallet, and kept separate from it on
purpose (Agent Embassy keeps its signer distinct from its payment wallet too). The private key is generated here,
stored gitignored, chmod 600, and should be ACL-locked the same way the money key is. Only the PUBLIC signer is
committed. This module does not move money and is not wired into the live /earn payment path -- that integration
is a separate, operator-gated step.

Honest scope, same as the rest of covenant_earn: a signed receipt attests "this content hashed to this value and
this signer vouched for it at signing time." It does not attest ongoing truth.
"""
from __future__ import annotations

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SIGNER_KEY = os.path.join(HERE, "ops", "receipt_signer.key")          # gitignored private key (hex)
SIGNER_PUB = os.path.join(HERE, "ops", "receipt_signer.pub.json")     # committed public signer (discovery)
PROOF_FIELDS = ("proof",)                                            # excluded from the canonical hash


def canonical(receipt):
    """Canonical bytes of a receipt: JSON with sorted keys, no spaces, the proof stage excluded. Two parties
    computing this over the same receipt get the same bytes, so the same SHA-256."""
    body = {k: v for k, v in receipt.items() if k not in PROOF_FIELDS}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def receipt_hash(receipt):
    return hashlib.sha256(canonical(receipt)).hexdigest()


def _Account():
    from eth_account import Account                                   # optional dep; imported lazily
    return Account


def load_or_create_signer(path=SIGNER_KEY, pub_path=SIGNER_PUB):
    """Return the receipt-signing account, creating and storing the key if absent. Private key is gitignored and
    chmod 600; the public signer is written for discovery (committed)."""
    Account = _Account()
    if os.path.exists(path):
        acct = Account.from_key(open(path, encoding="utf-8").read().strip())
    else:
        acct = Account.create()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(acct.key.hex())
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    if not os.path.exists(pub_path):
        with open(pub_path, "w", encoding="utf-8") as fh:
            json.dump({"address": acct.address, "scheme": "eip191-personal-sign",
                       "design_credit": "Agent Embassy (nootxlm, aemb.pro) -- portable signed receipts",
                       "note": "public receipt signer; verify a receipt by recomputing its canonical SHA-256 and "
                               "recovering this address from the eip191 signature over that hash"}, fh, indent=1)
    return acct


def sign(receipt, acct=None):
    """Attach a portable proof to a receipt: eip191-personal-sign over the canonical SHA-256. Returns the proof
    dict (does not mutate the receipt)."""
    from eth_account.messages import encode_defunct
    Account = _Account()
    acct = acct or load_or_create_signer()
    h = receipt_hash(receipt)
    sig = Account.sign_message(encode_defunct(text=h), acct.key)
    signature = sig.signature.hex()
    if not signature.startswith("0x"):
        signature = "0x" + signature
    return {"scheme": "eip191-personal-sign", "signer": acct.address, "hash": h, "signature": signature}


def verify(receipt, proof, allowed_signers=None):
    """(ok, reason). Recompute the canonical hash, confirm the proof's hash matches (the receipt is unaltered),
    recover the signer from the signature, confirm it matches the claimed signer, and -- when a registry is given
    -- that the signer is published. Verifiable from the receipt + proof alone; no ledger, no server."""
    from eth_account.messages import encode_defunct
    Account = _Account()
    h = receipt_hash(receipt)
    if proof.get("hash") != h:
        return False, "hash mismatch: the receipt was altered after signing"
    try:
        rec = Account.recover_message(encode_defunct(text=h), signature=proof.get("signature"))
    except Exception as e:                                            # noqa: BLE001 - any recovery failure is a no
        return False, "signature could not be recovered: %s" % e
    if rec.lower() != str(proof.get("signer", "")).lower():
        return False, "signer mismatch: signature recovers to %s, not the claimed %s" % (rec, proof.get("signer"))
    if allowed_signers is not None and rec.lower() not in {str(s).lower() for s in allowed_signers}:
        return False, "signer %s is not in the published registry" % rec
    return True, "verified: canonical hash matches and the signature recovers to the published signer"


def published_signer(pub_path=SIGNER_PUB):
    try:
        return json.load(open(pub_path, encoding="utf-8")).get("address")
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    acct = load_or_create_signer()
    r = {"tool": "receipt", "amount": "20000", "asset": "USDC", "network": "eip155:8453",
         "checked": "1 citation", "t": "demo"}
    p = sign(r, acct)
    ok, why = verify(r, p, allowed_signers=[published_signer()])
    print("signer:", acct.address)
    print("proof :", json.dumps(p)[:120], "...")
    print("verify:", ok, "--", why)
