"""Offline regression cases for A480's cache evidence. No model, network or live files."""
import unittest

from tools.tetsu_replay import summary


def row(step, read=None, cache=None, digest="abc"):
    return dict(step=step, prompt_n=read, cache_n=cache, out_sha=digest)


class ReplayEvidence(unittest.TestCase):
    def test_missing_and_warm_baseline(self):
        self.assertIsNone(summary([row("A1", 10, 90), row("A2 (again)", 1)], None)["back_to_back_reused"])
        self.assertIsNone(summary([row("A1", 100), row("A2 (again)", 0)], None)["back_to_back_reused"])
        self.assertIsNone(summary([], None)["parity_A1_A2"])

    def test_zero_read_and_explicit_cache(self):
        r = summary([row("A1", 100, 0), row("A2 (again)", 0, 100), row("A after 1", 100, 0)], None)
        self.assertIs(r["back_to_back_reused"], True)
        self.assertIs(r["reused_A_after_1"], False)
        self.assertIn("cause not established", r["reading"])
        self.assertIs(r["parity_A1_A2"], True)

    def test_known_full_baseline(self):
        self.assertIs(summary([row("A2 (again)", 0)], 100)["back_to_back_reused"], True)
        self.assertIs(summary([row("A1", 100, 0), row("A2 (again)", 50)], None)["back_to_back_reused"], False)
        self.assertIsNone(summary([row("A2 (again)", 101)], 100)["back_to_back_reused"])

    def test_invalid_and_empty(self):
        for invalid in (None, -1, True, 1.5, "1"):
            self.assertIsNone(summary([row("A2 (again)", invalid, 100)], 100)["back_to_back_reused"])
        self.assertIsNone(summary([row("A2 (again)", 0, 0)], 100)["back_to_back_reused"])
        empty = "e3b0c44298fc1c14"
        self.assertIsNone(summary([row("A1", digest=empty), row("A2 (again)", digest=empty)], None)["parity_A1_A2"])

    def test_missing_after_does_not_prove_success(self):
        r = summary([row("A1", 100, 0), row("A2 (again)", 0, 100)], None)
        self.assertIn("incomplete", r["reading"])
        r = summary([row("A1", 100, 0), row("A2 (again)", 0, 100), row("A after 1", None)], None)
        self.assertIsNone(r["reused_A_after_1"])
        self.assertIn("incomplete", r["reading"])


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReplayEvidence))
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print("A480 replay: %d/%d passed" % (passed, result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() and passed == result.testsRun else 1)
