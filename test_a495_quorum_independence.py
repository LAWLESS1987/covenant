"""A495 -- tools/quorum_independence.py: how many independent votes a quorum carries, and what correlation does.

Driven both ways with constructed panels whose answer is known by construction: copies of one seat are ONE vote,
seats wrong on disjoint items are as many votes as seats, a veto-only seat's silence is never a clear, a tie blocks.
The simulator: at zero correlation majority beats one seat; at high correlation it barely does; same seed, same
numbers. The live judges are run on judge_suite when their model files are here (an integration check, its numbers
not asserted beyond their shape -- they move with every nightly retrain)."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
sys.path.insert(0, HERE)
import quorum_independence as Q  # noqa: E402


def rows_from(table, labels):
    """table: {seat: [vote per item]}; labels: [violates per item]."""
    out = []
    for seat, votes in table.items():
        for i, (v, lab) in enumerate(zip(votes, labels)):
            out.append({"item": "i%02d" % i, "violates": lab, "seat": seat, "vote": v})
    return out


LABELS = [True] * 10 + [False] * 10
TRUTH = ["BLOCK"] * 10 + ["PASS"] * 10


def wrong_at(idx):
    v = list(TRUTH)
    for i in idx:
        v[i] = "PASS" if v[i] == "BLOCK" else "BLOCK"
    return v


class Votes(unittest.TestCase):
    def test_only_an_explicit_pass_passes(self):
        for raw in ("clean", "PASS", "allow", "Approved"):
            self.assertEqual(Q.vote_of(raw), "PASS")
        for raw in ("violates", "abstain", "illegible", "HOLD", "", None, "garbage"):
            self.assertEqual(Q.vote_of(raw), "BLOCK", raw)


class Independence(unittest.TestCase):
    def test_copies_of_one_seat_are_one_vote(self):
        v = wrong_at([0, 3, 12, 15])
        m = Q.measure(rows_from({"a": v, "b": list(v), "c": list(v)}, LABELS))
        self.assertAlmostEqual(m["n_eff"], 1.0, places=2)
        p = m["pairs"]["a|b"]
        self.assertEqual(p["both_wrong"], 4)
        self.assertEqual(p["error_phi"], 1.0)

    def test_seats_wrong_on_disjoint_items_count_fully(self):
        m = Q.measure(rows_from({"a": wrong_at([0, 11]), "b": wrong_at([1, 12]), "c": wrong_at([2, 13])}, LABELS))
        self.assertAlmostEqual(m["n_eff"], 3.0, places=2)   # disjoint errors: negative phi, clipped to 0
        self.assertEqual(m["majority_errors"], 0)            # each item has at most one seat wrong

    def test_phi_matches_the_hand_value(self):
        # a wrong on 0,1,2,3 ; b wrong on 2,3,4,5 over 20 items: both 2, a 4, b 4
        m = Q.measure(rows_from({"a": wrong_at([0, 1, 2, 3]), "b": wrong_at([2, 3, 4, 5])}, LABELS))
        ma = mb = 4 / 20
        hand = (2 / 20 - ma * mb) / (ma * (1 - ma))
        self.assertAlmostEqual(m["pairs"]["a|b"]["error_phi"], round(hand, 3), places=3)
        self.assertEqual(m["pairs"]["a|b"]["expected_if_independent"], 0.8)

    def test_a_tie_blocks(self):
        m = Q.measure(rows_from({"a": ["BLOCK"] * 20, "b": ["PASS"] * 20}, LABELS))
        self.assertEqual(m["majority_errors"], 10, "1-1 on every item: a tie must block, wrong on the 10 clean")
        # the same COUNT would come from a tie that passes (wrong on the 10 violations); which 10 is the test
        self.assertEqual(m["majority_false_clears"], 0, "a tie let a violation through")
        self.assertEqual(m["majority_false_holds"], 10)

    def test_a_veto_seats_silence_is_not_a_clear(self):
        v = {"a": list(TRUTH), "sem": ["PASS"] * 20}           # the veto seat objects to nothing
        m = Q.measure(rows_from(v, LABELS), veto=["sem"])
        self.assertEqual(m["per_seat"]["sem"]["false_clears"], 0)
        self.assertEqual(m["per_seat"]["sem"]["vetoes_missed"], 10)
        self.assertEqual(m["majority_errors"], 0, "a veto seat's PASS is no vote: the voter decides")
        m2 = Q.measure(rows_from(v, LABELS))                    # the other way: counted as a voter it clears
        self.assertEqual(m2["per_seat"]["sem"]["false_clears"], 10)

    def test_a_veto_block_blocks(self):
        v = {"a": ["PASS"] * 20, "sem": ["BLOCK"] * 10 + ["PASS"] * 10}
        m = Q.measure(rows_from(v, LABELS), veto=["sem"])
        self.assertEqual(m["majority_errors"], 0, "the voter passes everything; the veto must hold the 10")

    def test_escalation_decides_only_agreement(self):
        m = Q.measure(rows_from({"a": wrong_at([0]), "b": list(TRUTH)}, LABELS))
        e = m["escalate_on_conflict"]
        self.assertEqual((e["decided"], e["escalated"], e["wrong_among_decided"]), (19, 1, 0))


class Scenarios(unittest.TestCase):
    def test_independent_seats_beat_one_seat(self):
        r = Q.simulate(5, 0.8, 0.0, trials=4000, seed=3)
        self.assertLess(r["majority_error"], r["single_error"] * 0.5)
        self.assertGreater(r["n_eff"], 4.5)

    def test_correlated_seats_barely_beat_one_seat(self):
        r = Q.simulate(5, 0.8, 0.9, trials=4000, seed=3)
        self.assertGreater(r["majority_error"], r["single_error"] * 0.8)
        self.assertLess(r["n_eff"], 2.0)

    def test_same_seed_same_numbers(self):
        self.assertEqual(Q.simulate(3, 0.9, 0.5, trials=2000, seed=7), Q.simulate(3, 0.9, 0.5, trials=2000, seed=7))


@unittest.skipUnless(all(os.path.exists(os.path.join(HERE, f)) for f in
                         ("fallback_model.json", "semantic_judge_model.json")), "the judges' model files")
class LiveJudges(unittest.TestCase):
    def test_the_local_judges_on_judge_suite(self):
        import judge_suite as S
        rows = Q.collect_local()
        m = Q.measure(rows, veto=["semantic"])
        self.assertEqual(m["items"], len(S.CASES))
        self.assertIn("semantic", m["veto"])
        self.assertTrue(1.0 <= m["n_eff"] <= m["n_seats"])


if __name__ == "__main__":
    res = unittest.main(exit=False, verbosity=2).result
    run, bad = res.testsRun, len(res.failures) + len(res.errors)
    print("A495: %d/%d passed, %d skipped" % (run - bad - len(res.skipped), run - len(res.skipped), len(res.skipped)))
    sys.exit(1 if bad else 0)
