"""A441 -- a non-finite stake amount is rejected before it can corrupt the pool.

Found hunting the A438 queue at /stake. StakingPool.stake checked `amount <= 0` and `balance < amount`, but BOTH
are False for nan (nan comparisons are always False), so a nan amount slipped both guards, was written into
self.stakes[pubkey] -- which total_staked is DERIVED from, so total_staked becomes nan and poisons every yield and
reward sum -- and then diverged from the db when save_stake hit SQLite's NOT NULL constraint (nan -> NULL) and
raised. A single authenticated /stake with amount=nan thus poisons the in-memory pool AND locks the staker out
(pubkey is now 'already staked' with a row the db never got). The U invariant -- reject non-finite amounts at EVERY
ingress -- covered transactions, the trading bridge and the ledger, but NOT /stake. Fixed: stake() rejects a
non-finite amount before any state change.

Exploit-first, both ways: on the pre-A441 code stake(pubkey, nan, ...) RAISES (IntegrityError) and leaves pubkey in
self.stakes (the corruption); after, it returns (False, finite) and touches nothing. Guards /stake."""
import os
import sys
import tempfile
import unittest

import covenant_unified_v8 as cov

ROUTE = "/stake"   # the A438 queue item this closes


class NonFiniteStake(unittest.TestCase):
    def setUp(self):
        self.db = cov.Database(os.path.join(tempfile.mkdtemp(), "a441.db"))
        self.pool = cov.StakingPool(self.db)
        self.pk = "staker-pubkey"

    def test_nan_amount_is_refused_and_does_not_corrupt(self):
        ok, msg = self.pool.stake(self.pk, float("nan"), cov.STAKE_MIN_DURATION)
        self.assertFalse(ok)
        self.assertIn("finite", msg.lower())
        self.assertNotIn(self.pk, self.pool.stakes)   # nothing written -- the corruption is gone

    def test_inf_amount_is_refused_and_does_not_corrupt(self):
        ok, msg = self.pool.stake(self.pk, float("inf"), cov.STAKE_MIN_DURATION)
        self.assertFalse(ok)
        self.assertIn("finite", msg.lower())
        self.assertNotIn(self.pk, self.pool.stakes)

    def test_zero_and_negative_still_rejected_as_positive(self):
        # the existing positive-amount guard is intact: a check was added, not replaced.
        for amt in (0.0, -5.0):
            ok, msg = self.pool.stake(self.pk, amt, cov.STAKE_MIN_DURATION)
            self.assertFalse(ok)
            self.assertIn("positive", msg.lower())
            self.assertNotIn(self.pk, self.pool.stakes)

    def test_finite_amount_passes_the_guards_to_the_balance_check(self):
        # a finite positive amount is NOT rejected by the finite/positive guards -- it reaches the balance
        # check (no balance here -> Insufficient), proving the guard did not start refusing everything.
        ok, msg = self.pool.stake(self.pk, 50.0, cov.STAKE_MIN_DURATION)
        self.assertFalse(ok)
        self.assertIn("insufficient", msg.lower())
        self.assertNotIn(self.pk, self.pool.stakes)


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A441: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
