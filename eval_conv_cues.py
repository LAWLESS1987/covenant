#!/usr/bin/env python3
"""Offline synthetic cue evaluation. Never reads or writes live memory.

This measures cue output and a non-spiking counterfactual, not reasoning
quality, token savings, or Tetsu's preference. Production cue logic is unchanged.
"""
import json
import os
import tempfile

import covenant_octopus as octopus
import covenant_tetsu_conv_reflex as cues

CASES = (
    ("first topic", "quantum entanglement spooky distance correlation measurement"),
    ("exact repeat", "quantum entanglement spooky distance correlation measurement"),
    ("related wording", "quantum entanglement spooky distance correlation physics"),
    ("unrelated topic", "baking sourdough bread fermentation yeast proofing"),
    ("positive intent", "authorize database migration deployment"),
    ("negated intent", "do not authorize database migration deployment"),
    ("short greeting", "hi there"),
)


def run(root):
    os.makedirs(root, exist_ok=True)
    return [dict(case=name, signature=cues.topic_signature(text),
                 novelty=cues.cue_line(text, os.path.join(root, "seen.json"), os.path.join(root, "cue.jsonl")),
                 recall=cues.recall_line(text, os.path.join(root, "recall.json")))
            for name, text in CASES]


def evaluate():
    # Retain synthetic artifacts for inspection; no live state is migrated.
    root = tempfile.mkdtemp(prefix="covenant-offline-cue-eval-")
    actual = run(os.path.join(root, "actual"))
    original = octopus.ReflexArm.sense
    spike_calls = []
    def zero_sense(self, *args, **kwargs):
        spike_calls.append(True)
        self.last = [0] * len(self.neurons)
        return self.last
    try:
        octopus.ReflexArm.sense = zero_sense
        no_spikes = run(os.path.join(root, "zero-spikes"))
    finally:
        octopus.ReflexArm.sense = original
    return {"population": "synthetic fixtures only", "turns": len(CASES),
            "disabled_by_existing_choice": octopus._disabled(),
            "zero_spike_calls": len(spike_calls),
            "novelty_cues": sum(r["novelty"] is not None for r in actual),
            "recall_cues": sum(r["recall"] is not None for r in actual),
            "output_changes_when_reflex_spikes_zeroed": sum(a != b for a, b in zip(actual, no_spikes)),
            "rows": actual, "synthetic_artifacts": root,
            "unmeasured": ["reasoning benefit", "token savings", "real conversation performance", "preference"]}


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
