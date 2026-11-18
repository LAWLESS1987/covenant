"""A439 -- a non-finite (nan) request timestamp is refused at the operator-request gate.

FOUND hunting the A438 attack-surface queue at /actuator_learn (the first item). The shared gate
covenant_daily_plan.verify_signed checked freshness with `abs(now - ts) > WINDOW_S`, which is FALSE
for ts = nan -- so a nan timestamp slipped the window and was never rejected as stale. Because the
nonce store (_seen_nonces) is in-memory and resets on restart, a captured nan-stamped request could
replay after a restart. The signature still had to come from a REGISTERED key, so the reach is a
trusted signer or a leaked request -- minor, defense-in-depth -- but it broke the U invariant
(test_security_audit: reject non-finite at every ingress). FIX: verify_signed rejects a non-finite
ts before the window and the signature checks.

Driven both ways, EXPLOIT-FIRST: the SAME nan request now refused would have VERIFIED on the
pre-A439 code (a valid signature over nan slips the window), and a finite request on the SAME route
still verifies -- so the gate did not simply start refusing everything. The gate also fronts
/daily_plan/approve, /checkin and /ai_chats, so this hardens all of them."""
import base64
import os
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

import covenant_daily_plan as DP
import covenant_unified_v8 as cov

ROUTE = "/actuator_learn"   # the A438 queue item this closes


def _keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pem


def _sign(priv, pem, method, path, body, nonce, timestamp):
    """A valid X-Operator-Signature over (method, path, body, nonce, timestamp) -- exactly what a
    registered signer produces, but with a timestamp WE choose (here, a non-finite one)."""
    payload = cov.operator_signing_payload(pem, method, path, body, nonce, timestamp)
    return base64.b64encode(priv.sign(
        payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())).decode()


class NonFiniteTimestamp(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.signers = os.path.join(self.td, "signers.json")
        self.priv, self.pem = _keypair()
        DP.register_signer("phone", self.pem, self.signers)

    def _verify(self, ts_header, ts_signed):
        nonce = base64.b16encode(os.urandom(8)).decode()
        sig = _sign(self.priv, self.pem, "POST", ROUTE, b"{}", nonce, ts_signed)
        return DP.verify_signed(self.pem, "POST", ROUTE, b"{}", nonce, ts_header, sig,
                                self.signers, now=1000.0, seen=set())

    def test_nan_timestamp_is_refused(self):
        # EXPLOIT-FIRST: this exact request VERIFIES on the pre-A439 code (valid sig over nan, and
        # nan slips the window). Post-A439 it is refused at the ingress, before the signature check.
        ok, why = self._verify("nan", float("nan"))
        self.assertFalse(ok, why)
        self.assertEqual(why, "bad timestamp")

    def test_inf_timestamp_is_refused(self):
        ok, why = self._verify("inf", float("inf"))
        self.assertFalse(ok, why)
        self.assertEqual(why, "bad timestamp")

    def test_finite_in_window_request_still_verifies(self):
        # the gate did not start refusing everything: a legit finite request on the SAME route passes.
        ok, who = self._verify("1000.0", 1000.0)
        self.assertTrue(ok, who)
        self.assertEqual(who, "phone")


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A439: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
