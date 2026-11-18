"""A442 -- succession registration validates the dead-man's-switch TIMING: no negative or non-finite interval/grace.

Found hunting the A438 queue at /succession/register. register() validated the threshold (1..N), the guardian count
and distinctness, and the keys -- but NOT heartbeat_interval_days / grace_period_days. A NEGATIVE value makes
check_dead_mans_switch's deadline (last_heartbeat + interval*86400 + grace*86400) land in the PAST, so it fires a
PENDING succession episode IMMEDIATELY -- on a live primary whose heartbeat cannot prevent it (measured: a fresh
register with interval=-100000 triggered episode 1 at once). A non-finite value raises at the db's NOT NULL column
(nan -> NULL) and 500s. register() now rejects both at write time (the U invariant, as /stake does, A441).

Bounded: succession here is a guardian key-RECOVERY scheme (recovery material stays sealed to the ORIGINAL
guardians), so this is a false-trigger of the mechanism, not a direct asset takeover -- but still a real corruption
of a security-critical dead-man's-switch. Exploit-first both ways: pre-A442 register(-100000) succeeds and the
switch fires PENDING on a live primary; after, register refuses it. Guards /succession/register."""
import os
import sys
import tempfile
import time
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

import covenant_unified_v8 as cov

ROUTE = "/succession/register"   # the A438 queue item this closes


def _pem():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    return k.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


class SuccessionTiming(unittest.TestCase):
    def setUp(self):
        self.db = cov.Database(os.path.join(tempfile.mkdtemp(), "a442.db"))
        self.S = cov.SuccessionGuardianSystem(self.db)
        self.p, self.succ, self.g1, self.g2 = _pem(), _pem(), _pem(), _pem()

    def _reg(self, interval, grace):
        return self.S.register(self.p, self.succ, [self.g1, self.g2], 2, interval, grace)

    def test_negative_interval_is_refused(self):
        ok, msg = self._reg(-100000.0, 0.0)
        self.assertFalse(ok)
        self.assertIn("heartbeat_interval_days", msg)

    def test_negative_grace_is_refused(self):
        ok, msg = self._reg(30.0, -5.0)
        self.assertFalse(ok)
        self.assertIn("grace_period_days", msg)

    def test_nonfinite_interval_is_refused(self):
        for bad in (float("nan"), float("inf")):
            ok, msg = self._reg(bad, 15.0)
            self.assertFalse(ok, bad)
            self.assertIn("finite", msg)

    def test_zero_interval_is_refused(self):
        ok, _msg = self._reg(0.0, 15.0)
        self.assertFalse(ok)   # a zero heartbeat interval is not a positive cadence

    def test_valid_timing_registers_and_does_not_false_trigger(self):
        ok, msg = self._reg(30.0, 15.0)
        self.assertTrue(ok, msg)   # control: a sane config is accepted
        # a live primary that just registered (last_heartbeat = now) is NOT past its deadline
        fired, why = self.S.check_dead_mans_switch(self.p, now=time.time())
        self.assertFalse(fired, why)

    def test_the_exploit_is_closed(self):
        # the measured exploit: a negative interval let the switch fire immediately on a live primary.
        # Post-A442 the registration itself is refused, so there is no config to false-trigger.
        ok, _ = self._reg(-100000.0, 0.0)
        self.assertFalse(ok)
        fired, why = self.S.check_dead_mans_switch(self.p, now=time.time())
        self.assertFalse(fired, why)


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A442: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
