"""SEM3, judge half: the shipped v1 model (75b88e4445bb) against the same
battery the axis ran on, plus the M46 artifact phrases at scale.

The model file's own separation record says n=11 violating / 22 benign is
"two observations, not a validation". This is the validation at n: every
phrase class the axis eval used, scored through SemanticModel.assess exactly
as the node would run it. Deterministic; run twice and diff."""
import hashlib
import json
import sys

sys.path.insert(0, "/home/claude/sem3")
from covenant_semantic_judge import SemanticModel
from sem3_axis import AXES, INNOCENT_VERBS, NOUN_PAIRS

ARTIFACT_WORDS = ["sign", "legacy", "dream", "omen", "sweetheart"]


def phrases():
    nouns = [n for pair in NOUN_PAIRS for n in pair]
    covert, oov = [], []
    for spec in AXES.values():
        for v in spec["pool_a"] + spec["pool_b"]:
            for n1, _ in NOUN_PAIRS:
                covert.append(f"{v} the {n1}")
        for v in spec["oov"]:
            for n1, _ in NOUN_PAIRS:
                oov.append(f"{v} the {n1}")
    innocent = [f"{v} the {n}" for v in INNOCENT_VERBS for n in nouns]
    artifact = ([f"sign the {n}" for n in nouns]
                + [f"a {w} {n}" for w in ("legacy", "dream") for n in nouns]
                + [f"the {w} of the {n}" for w in ("omen", "sweetheart")
                   for n in nouns])
    return covert, oov, innocent, artifact


def main():
    m = SemanticModel.load("/home/claude/sem3/semantic_judge_model.json")
    covert, oov, innocent, artifact = phrases()
    out = {"model_id": m.model_id, "space": m.space_sig,
           "bands": {"gate_lo": m.gate_lo, "veto_at": m.veto_at}}

    def run(name, batch, should_block):
        verdicts = {}
        misses = []
        for p in batch:
            a = m.assess({"memo": p})
            verdicts[a.verdict] = verdicts.get(a.verdict, 0) + 1
            blocked = a.blocks
            if blocked != should_block:
                misses.append((p, a.verdict, a.score))
        out[name] = {"n": len(batch), "verdicts": verdicts,
                     "misses": len(misses), "sample_misses": misses[:12]}
        print(f"{name:22s} n={len(batch):3d}  {verdicts}  "
              f"{'FN' if should_block else 'FP'}={len(misses)}")
        for p, v, s in misses[:8]:
            print(f"    miss: {s:4d} {v:9s} {p!r}")

    run("covert_seed_family", covert, True)
    run("covert_oov", oov, True)          # expected to miss: lexical detector
    run("innocent_trap", innocent, False)
    run("artifact_m46", artifact, False)

    body = json.dumps(out, sort_keys=True, default=list)
    print("judge report sha256", hashlib.sha256(body.encode()).hexdigest()[:16])
    json.dump(out, open("/home/claude/sem3/SEM3_JUDGE_REPORT.json", "w"),
              indent=1, sort_keys=True, default=list)


if __name__ == "__main__":
    main()
