"""A466: the independent-verifier spec's rule C3 must name the PSS salt length the node actually signs with.

The spec told an independent verifier to check the genesis signature with a salt length equal to the digest length
(32 bytes). The node signs with the maximum (PSS.MAX_LENGTH: 222 bytes for RSA-2048 with SHA-256), so a verifier
built from the spec rejected the real genesis. This guard runs the real genesis.json both ways and reads the rule's
text, so the spec and the chain cannot drift apart again silently."""
import base64
import json
import os
import re
import sys
import unittest

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

HERE = os.path.dirname(os.path.abspath(__file__))


def genesis_tx():
    with open(os.path.join(HERE, "genesis.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    return (g.get("transactions") or g["data"]["transactions"])[0] if isinstance(g, dict) else g[0]["transactions"][0]


def framed(tx):
    out = b"COVENANT_TX_V1"
    for field in (tx["sender_pubkey"], tx["receiver"], str(tx["timestamp"]), json.dumps(tx["data"], sort_keys=True),
                  str(tx["amount"])):
        b = field.encode("utf-8")
        out += len(b).to_bytes(4, "big") + b
    return out


def verifies(salt):
    tx = genesis_tx()
    key = serialization.load_pem_public_key(tx["sender_pubkey"].encode())
    try:
        key.verify(base64.b64decode(tx["signature"]), framed(tx),
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=salt), hashes.SHA256())
        return True
    except InvalidSignature:
        return False


class VerifierSalt(unittest.TestCase):
    def test_the_real_genesis_verifies_with_the_salt_the_spec_now_names_and_not_with_the_old_one(self):
        self.assertTrue(verifies(222))
        self.assertTrue(verifies(padding.PSS.MAX_LENGTH))
        self.assertFalse(verifies(32))                                   # the retracted rule (A466)

    def test_rule_c3_names_222_bytes_and_cites_the_retraction(self):
        with open(os.path.join(HERE, "docs", "SPEC_INDEPENDENT_VERIFIER.md"), encoding="utf-8") as fh:
            c3 = next(line for line in fh if line.startswith("| C3 |"))
        self.assertIn("222 bytes", c3)
        self.assertIn("A466-VERIFIER-SALT", c3)
        self.assertIsNone(re.search(r"salt length = digest length", c3))


if __name__ == "__main__":
    # The runner (covenant_one) reads a tally line; unittest.main prints none, so CI called this suite "NO RESULT"
    # (2026-11-22, both sweeps on PR #101). The same ending as test_a443_runner_isolation.py.
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("VS1: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
