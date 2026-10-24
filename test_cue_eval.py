"""Checks the offline experiment itself; never measures a live conversation."""
import unittest
import eval_conv_cues as evaluation
import covenant_octopus as octopus


class OfflineEvaluationTest(unittest.TestCase):
    def test_counterfactual_runs_without_disabling_the_reflex(self):
        original = octopus.ReflexArm.sense
        result = evaluation.evaluate()
        self.assertIs(octopus.ReflexArm.sense, original)
        self.assertEqual(result["turns"], len(evaluation.CASES))
        if not result["disabled_by_existing_choice"]:
            self.assertGreater(result["zero_spike_calls"], 0)
            self.assertGreater(result["novelty_cues"], 0)
            self.assertEqual(result["output_changes_when_reflex_spikes_zeroed"], 0)


if __name__ == "__main__":
    unittest.main()
