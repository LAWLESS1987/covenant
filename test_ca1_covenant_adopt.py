"""CA1 -- covenant_adopt's gate is fail-closed and PROPOSE by default.

tools/covenant_adopt.py decides whether an incoming origin/main is safe to adopt (covenant-native, reusing
covenant_one's differential gate + node D's proven scan/classify patterns). This pins its gate both ways: GO
only when the diff is NORMAL, merges clean, the backdoor scan is clean, and no NEW gate fails; a HIGH
(security-sensitive) diff, a scan hit, an unclean merge, or a newly-failing gate each force NO-GO. And it pins
the two brakes that keep it safe: AUTO is OFF by default (PROPOSE-only -- a GO applies nothing without arming),
and apply refuses with no updater configured. Each NO-GO case fails if the gate stopped failing closed."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import covenant_adopt as A  # noqa: E402


class Classify(unittest.TestCase):
    def test_sensitive_paths_are_HIGH(self):
        for f in ("covenant_watchdog.py", "covenant_highway.py", "covenant_tetsu_hands.py",
                  "ops/operator_keys.json", "run_node.py", "covenant_grid_guard.py"):
            self.assertEqual(A.classify([f])[0], "HIGH", f)

    def test_ordinary_paths_are_NORMAL(self):
        self.assertEqual(A.classify(["docs/README.md", "tools/readme_totals.py"])[0], "NORMAL")


class Scan(unittest.TestCase):
    def test_each_backdoor_pattern_is_caught(self):
        cases = {
            "reverse_shell": "import pty; pty.spawn('/bin/sh')",
            "exec_of_decoded": "exec(base64.b64decode(payload))",
            "persistence_new": "subprocess.run(['schtasks','/create','/tn','x'])",
            "cred_capture": "open(os.path.expanduser('~/.ssh/id_rsa')).read()",
            "listener_all_ifaces": "s.bind(('0.0.0.0', 9999))",
        }
        for label, line in cases.items():
            hits = [h["pattern"] for h in A.scan_lines([("x.py", line)])]
            self.assertIn(label, hits, label)

    def test_ordinary_code_is_clean(self):
        self.assertEqual(A.scan_lines([("x.py", "def f(a): return a + 1"),
                                       ("y.py", "resp = requests.get(url)")]), [])


class Decide(unittest.TestCase):
    CLEAN = dict(cls="NORMAL", sens=[], scan={"state": "clean"}, test={"ok": True}, merge_ok=True)

    def _d(self, **over):
        a = dict(self.CLEAN, **over)
        return A.decide(a["cls"], a["sens"], a["scan"], a["test"], a["merge_ok"])

    def test_go_only_when_everything_clean(self):
        self.assertEqual(self._d()[0], "GO")

    def test_high_sensitivity_holds(self):
        self.assertEqual(self._d(cls="HIGH", sens=["covenant_watchdog.py"])[0], "NO-GO")

    def test_scan_hit_holds(self):
        self.assertEqual(self._d(scan={"state": "hits"})[0], "NO-GO")

    def test_new_failing_gate_holds(self):
        self.assertEqual(self._d(test={"ok": False, "new_failures": ["G5"]})[0], "NO-GO")

    def test_unclean_merge_holds(self):
        self.assertEqual(self._d(merge_ok=False)[0], "NO-GO")


class Brakes(unittest.TestCase):
    def test_auto_is_off_by_default(self):
        # PROPOSE by default: without COVENANT_ADOPT_AUTO=1 the module never arms, so a GO applies nothing.
        self.assertFalse(A.AUTO, "AUTO must default OFF -- apply must need an explicit arm")

    def test_apply_refuses_without_an_updater(self):
        # with no COVENANT_ADOPT_UPDATER, apply never runs the mesh -- it reports an error and applies nothing.
        orig = A.UPDATER
        A.UPDATER = None
        try:
            steps = A.apply({"head": "deadbeef0000"}, dry=False)
        finally:
            A.UPDATER = orig
        self.assertFalse(steps.get("applied"))
        self.assertIn("error", steps)


class Digest(unittest.TestCase):
    def test_digest_returns_a_summary(self):
        d = A.digest()
        self.assertIn("armed", d)


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("CA1: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
