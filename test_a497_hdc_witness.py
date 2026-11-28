"""A497 -- covenant_hdc_witness: the mechanism, checked on CONSTRUCTED data only.

The exam (judge_suite) and the ledger are measured once, by `covenant_hdc_witness.py measure`, against the bar sealed
in ops/HDC_WITNESS_PREREG_2026-11-27.md; this suite never touches them, so it cannot become a way to tune the witness
to its own exam. Driven both ways: binding is order-sensitive, the item memory is the same on every run, an empty
text holds, the conformal thresholds sit where the pre-registration says, and a separable toy corpus is learned."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_hdc_witness as H  # noqa: E402


def sim(a, b):
    """Fraction of agreeing positions between two encoded texts."""
    return sum(1 for x, y in zip(a, b) if x == y) / H.D


class Mechanism(unittest.TestCase):
    def test_item_memory_is_deterministic_and_quasi_orthogonal(self):
        self.assertEqual(H.item("gift"), H.item("gift"))
        agree = H.D - bin(H.item("gift") ^ H.item("theft")).count("1")
        self.assertTrue(0.45 < agree / H.D < 0.55, agree)

    def test_rotation_is_a_permutation(self):
        x = H.item("x")
        self.assertEqual(H.rot(H.rot(x, 3), H.D - 3), x)
        self.assertNotEqual(H.rot(x, 1), x)
        self.assertEqual(bin(H.rot(x, 7)).count("1"), bin(x).count("1"))

    def test_trigram_binding_is_order_sensitive(self):
        a = H.encode(["send", "the", "funds", "to", "me"])
        b = H.encode(["me", "to", "funds", "the", "send"])
        same = H.encode(["send", "the", "funds", "to", "me"])
        self.assertEqual(a, same)
        self.assertLess(sim(a, b), 0.99, "the same words in reverse order must encode differently")

    def test_an_empty_text_holds(self):
        self.assertIsNone(H.encode([]))
        w = H.Witness([1] * H.D, [1] * H.D, -0.1, 0.1)
        self.assertEqual(w.verdict_encoded(None), "hold")

    def test_conformal_thresholds_sit_at_the_sealed_quantiles(self):
        w = H.Witness([0] * H.D, [0] * H.D)
        # margins are 0 for a zero prototype; inject margins by monkeypatching
        margins = iter([float(i) for i in range(100)] + [float(i) for i in range(100, 200)])
        w.margin = lambda x, st=None: next(margins)
        enc = [b"\x00"] * 200
        labels = [True] * 100 + [False] * 100
        w.calibrate(enc, labels)
        self.assertEqual(w.t_clear, 1.0, "1st percentile, nearest rank, of violations 0..99")
        self.assertEqual(w.t_violate, 198.0, "99th percentile, nearest rank, of clean 100..199")

    def test_overlapping_thresholds_hold_the_overlap(self):
        w = H.Witness([0] * H.D, [0] * H.D, 0.2, -0.2)          # t_clear >= t_violate
        for m, want in ((-0.5, "clean"), (0.0, "hold"), (0.5, "violates")):
            w.margin = lambda x, st=None, m=m: m
            self.assertEqual(w.verdict_encoded(b"\x00"), want, m)


class Learns(unittest.TestCase):
    def test_a_separable_toy_corpus(self):
        bad = [["steal", "the", "pool", str(i)] for i in range(30)] + [["drain", "wallet", str(i)] for i in range(30)]
        good = [["gift", "to", "friend", str(i)] for i in range(30)] + [["pay", "wages", str(i)] for i in range(30)]
        enc = [H.encode(t) for t in bad + good]
        lab = [True] * 60 + [False] * 60
        w = H.Witness.train(enc[0::2], lab[0::2]).calibrate(enc[1::2], lab[1::2])
        st = w._stats()
        self.assertEqual(w.verdict_encoded(H.encode(["steal", "the", "pool", "x"]), st), "violates")
        self.assertEqual(w.verdict_encoded(H.encode(["gift", "to", "friend", "x"]), st), "clean")
        self.assertEqual(w.verdict_encoded(H.encode(["zz", "qq", "ww"]), st), "hold", "unseen tokens: no evidence")

    def test_round_trip_keeps_the_verdicts(self):
        enc = [H.encode(["steal", str(i)]) for i in range(10)] + [H.encode(["gift", str(i)]) for i in range(10)]
        lab = [True] * 10 + [False] * 10
        w = H.Witness.train(enc, lab).calibrate(enc, lab)
        w2 = H.Witness.from_json(w.to_json())
        x = H.encode(["steal", "now"])
        self.assertEqual(w.verdict_encoded(x), w2.verdict_encoded(x))


if __name__ == "__main__":
    res = unittest.main(exit=False, verbosity=2).result
    run, bad = res.testsRun, len(res.failures) + len(res.errors)
    print("A497: %d/%d passed, %d skipped" % (run - bad - len(res.skipped), run - len(res.skipped), len(res.skipped)))
    sys.exit(1 if bad else 0)
