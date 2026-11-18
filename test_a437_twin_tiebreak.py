"""A437 -- one tree, one watchdog even when two start in the same tick (extends A160).

A160's _twins_to_evict spared EVERY same-tick tie (two evicting each other would leave nothing running) and
_evict_twins ran only at daemon start -- so two watchdogs started in the same second by racing launchers BOTH
survived and persisted, with nothing to cull them. A437 adds a deterministic pid tiebreak (the lower pid stops
the higher; one-sided, so never a mutual kill and never an outage) and runs the A160 re-cull EVERY round, not
only at start, so a same-tick twin left by a start-time race is gone within one interval. Driven both ways: each
assertion marked NEW fails on the pre-A437 code (same-tick spared; no per-round cull; no _daemon_round)."""
import sys
import unittest

import covenant_watchdog as W

T0 = "2026-11-16T16:21:32Z"
T1 = "2026-11-16T16:21:40Z"   # strictly later than T0


class TwinTiebreak(unittest.TestCase):
    # --- the pure decision: _twins_to_evict ---------------------------------
    def test_strictly_older_is_still_evicted(self):
        # A160 unchanged: an older twin is stopped by the newer one.
        self.assertEqual(W._twins_to_evict([(100, T0), (300, T1)], my_pid=300, my_ppid=1), [100])

    def test_same_tick_lower_pid_evicts_the_higher(self):
        # NEW (A437): of two started in one tick, the LOWER pid stops the higher. Pre-A437 returned [].
        self.assertEqual(W._twins_to_evict([(100, T0), (201, T0)], my_pid=100, my_ppid=1), [201])

    def test_same_tick_higher_pid_defers(self):
        # The other direction: the higher pid evicts nobody -- so the pair never kill each other (no outage).
        self.assertEqual(W._twins_to_evict([(100, T0), (201, T0)], my_pid=201, my_ppid=1), [])

    def test_three_same_tick_lowest_survives(self):
        # NEW (A437): three in one tick collapse to the lowest pid; pre-A437 all three returned [].
        rows = [(100, T0), (200, T0), (300, T0)]
        self.assertEqual(W._twins_to_evict(rows, my_pid=100, my_ppid=1), [200, 300])  # lowest stops both
        self.assertEqual(W._twins_to_evict(rows, my_pid=200, my_ppid=1), [300])        # middle stops only the top
        self.assertEqual(W._twins_to_evict(rows, my_pid=300, my_ppid=1), [])           # top stops nobody

    def test_younger_twin_is_never_evicted(self):
        # a newer twin (a legitimate replacement mid-restart) is left to take over; its own start scan evicts us.
        self.assertEqual(W._twins_to_evict([(300, T1), (100, T0)], my_pid=100, my_ppid=1), [])

    def test_self_and_parent_are_never_evicted(self):
        # my_pid and my_ppid are excluded even when a same-tick twin would otherwise be a victim.
        self.assertEqual(W._twins_to_evict([(100, T0), (101, T0)], my_pid=100, my_ppid=101), [])

    def test_not_in_rows_evicts_nothing(self):
        # a measurement that cannot see the measurer is not trusted to act.
        self.assertEqual(W._twins_to_evict([(100, T0), (101, T0)], my_pid=999, my_ppid=998), [])

    # --- the placement: _daemon_round re-culls every round ------------------
    def test_daemon_round_culls_every_round(self):
        # NEW (A437): the daemon loop re-culls each round, not only at start. Pre-A437 had no _daemon_round.
        culls = {"n": 0}
        passes = {"n": 0}
        orig_pass, orig_evict = W.one_pass, W._evict_twins
        W.one_pass = lambda: passes.__setitem__("n", passes["n"] + 1)
        W._evict_twins = lambda: culls.__setitem__("n", culls["n"] + 1)
        try:
            W._daemon_round()
            W._daemon_round()
        finally:
            W.one_pass, W._evict_twins = orig_pass, orig_evict
        self.assertEqual(passes["n"], 2, "a health pass runs each round")
        self.assertEqual(culls["n"], 2, "A437: the cull must run EVERY round, not only at start")

    def test_cull_survives_a_failed_health_pass(self):
        # A failed one_pass must not skip the cull -- the cull is what keeps one-tree-one-watchdog true.
        culls = {"n": 0}
        orig_pass, orig_evict, orig_log = W.one_pass, W._evict_twins, W.log

        def _boom():
            raise RuntimeError("pass blew up")

        W.one_pass = _boom
        W._evict_twins = lambda: culls.__setitem__("n", culls["n"] + 1)
        W.log = lambda *a, **k: None
        try:
            W._daemon_round()   # must not raise
        finally:
            W.one_pass, W._evict_twins, W.log = orig_pass, orig_evict, orig_log
        self.assertEqual(culls["n"], 1, "a failed pass must not skip the cull")


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A437: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
