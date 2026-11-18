"""A440 -- a stake-action signature is bound to its ACTION and its KEY: a 'claim' signature cannot authorize 'unstake'.

Found hunting the A438 queue at /claim_rewards. The v8.4 fix (covenant_unified_v8.verify_stake_action_signature,
PATCH LOG item L) put the action into the signed payload so a signature authorizing one stake action cannot be
replayed as another, and binds the pubkey so only the owner can act. test_a1a_a2 already proves a BAD signature is
refused (400), but NOTHING tested the properties the fix is FOR: that a valid 'claim' signature is refused for
'unstake' (action domain separation) and that another key's signature over the same frame is refused (ownership). A
fix whose key property has no runner is the A65 gap. This pins them, both ways: the separation holds only because
`action` is inside the signed frame -- drop it and a claim-sig verifies for unstake and this fails. Guards
/claim_rewards and /unstake, which share verify_stake_action_signature.

NOT covered here (recorded in KNOWN_ISSUES A440): the route-level REPLAY nonce (/claim_rewards, /unstake reject a
resubmitted signature) needs a booted node + staking pool; a node-boot test is the next step, not this unit."""
import base64
import sys
import time
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

import covenant_unified_v8 as cov

ROUTES = ("/claim_rewards", "/unstake")   # the A438 queue items this closes; both gate on the function below


def _keypair():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pem = k.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return k, pem


def _sign(key, pem, action, ts):
    """A valid stake-action signature over the domain frame -- the same bytes the real signer produces."""
    payload = cov._domain_frame(b"COVENANT_STAKE_ACTION_V1", pem, action, str(ts))
    return base64.b64encode(key.sign(
        payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())).decode()


class StakeActionAuth(unittest.TestCase):
    def setUp(self):
        self.key, self.pem = _keypair()
        self.ts = time.time()

    def test_claim_signature_authorizes_claim(self):
        # control: the happy path holds, so the refusals below are not refusing everything.
        sig = _sign(self.key, self.pem, "claim", self.ts)
        self.assertTrue(cov.verify_stake_action_signature(self.pem, "claim", self.ts, sig))

    def test_claim_signature_is_refused_for_unstake(self):
        # ACTION DOMAIN SEPARATION (v8.4 / PATCH LOG L): a claim authorization is not an unstake authorization.
        sig = _sign(self.key, self.pem, "claim", self.ts)
        self.assertFalse(cov.verify_stake_action_signature(self.pem, "unstake", self.ts, sig))

    def test_unstake_signature_is_refused_for_claim(self):
        sig = _sign(self.key, self.pem, "unstake", self.ts)
        self.assertFalse(cov.verify_stake_action_signature(self.pem, "claim", self.ts, sig))

    def test_tampered_timestamp_breaks_the_signature(self):
        # the timestamp is inside the signed frame, so a changed ts invalidates the signature.
        sig = _sign(self.key, self.pem, "claim", self.ts)
        self.assertFalse(cov.verify_stake_action_signature(self.pem, "claim", self.ts + 1, sig))

    def test_garbage_signature_is_refused(self):
        self.assertFalse(cov.verify_stake_action_signature(
            self.pem, "claim", self.ts, base64.b64encode(b"garbage").decode()))

    def test_another_keys_signature_is_refused(self):
        # OWNERSHIP: a different key signing over THIS pubkey's frame does not pass -- only the owner can act.
        other, _ = _keypair()
        sig = _sign(other, self.pem, "claim", self.ts)
        self.assertFalse(cov.verify_stake_action_signature(self.pem, "claim", self.ts, sig))


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A440: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
