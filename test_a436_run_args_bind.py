"""A436 -- a signed-door HANDS RUN approves the exact script, not an invocation (follows A430; closes quorum C3).

A430's run_sha256 binds the script FILE's bytes but not its ARGUMENTS, which come from the model's answer line. So
the operator's signature names the file, and a planted instruction could append arguments the operator never saw. On
the signed door (run_sha256 bound) a RUN that carries arguments is now refused; it runs with no arguments. The
practice path (in-process: run_auth set, run_sha256 UNBOUND) and any unsigned/plain caller are untouched -- only the
signed door binds run_sha256. Driven both ways."""
import sys
import time
import unittest

import covenant_tetsu_hands as h
import covenant_tetsu_practice as P

GOOD = "a" * 64


class RunArgsBind(unittest.TestCase):
    def test_signed_door_run_with_args_is_refused(self):
        _handled, data, rec = h.act("HANDS RUN script.py --wipe /", may_run=True, run_sha256=GOOD)
        self.assertTrue(rec.get("run_args_refused"), rec)
        self.assertTrue(rec.get("refused"), rec)
        self.assertIn("no arguments", data.lower(), data)
        self.assertIsNone(rec.get("code"), rec)                       # nothing ran

    def test_signed_door_run_without_args_is_not_refused_by_a436(self):
        # no args -> A436 does not fire; it proceeds to A430's hash binding (the file is absent, so it does not run,
        # but it is NOT an A436 refusal). The point: A436 left the no-args signed run alone.
        _handled, _data, rec = h.act("HANDS RUN script.py", may_run=True, run_sha256=GOOD)
        self.assertIsNone(rec.get("run_args_refused"), rec)

    def test_practice_path_with_args_is_untouched(self):
        # in-process practice: run_auth set, run_sha256 UNBOUND -> A436 does not fire (only the signed door binds it)
        auth = P.PracticeRunAuth(max_runs=5, expiry=time.time() + 1000)
        _handled, _data, rec = h.act("HANDS RUN script.py somearg", may_run=True, run_auth=auth)
        self.assertIsNone(rec.get("run_args_refused"), rec)

    def test_plain_in_process_caller_with_args_is_untouched(self):
        # no run_auth, run_sha256 UNBOUND (the default in-process caller) -> A436 does not fire
        _handled, _data, rec = h.act("HANDS RUN script.py somearg", may_run=True)
        self.assertIsNone(rec.get("run_args_refused"), rec)

    def test_unsigned_run_is_refused_by_a423_first_not_a436(self):
        _handled, _data, rec = h.act("HANDS RUN script.py arg", may_run=False, run_sha256=GOOD)
        self.assertTrue(rec.get("refused"), rec)
        self.assertIsNone(rec.get("run_args_refused"), rec)           # A423 (may_run) refuses before A436 is reached


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A436: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
