"""Ora vs Sena on held-out ledger rows (2026-10-16). Read-only against the covenant tree.

Per grouped fold (tools/judge_eval.folds, same k and seed as docs/JUDGE_EVALUATION.md):
  Ora-type  = FallbackModel trained on every training row (as covenant_distill loads the whole ledger);
  Sena-type = FallbackModel trained on the training rows with half_of(text, source) == 1
              (covenant_second_student's half: a subset of Ora's).
Both use FallbackModel.train directly, as judge_eval does; the deployed students are refined
nightly from their predecessors, which this does not reproduce.
"""
import json
import os
import random
import sys

REPO = sys.argv[1]
OUT = sys.argv[2]
K, SEED = 5, 7
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import covenant_distill as X                      # noqa: E402
import covenant_judge_fallback as FB              # noqa: E402
from covenant_second_student import half_of       # noqa: E402
import judge_eval as JE                            # noqa: E402

rows = [r for r in X.load_verdicts(X.VERDICTS) if r.get("text") and r.get("violates") is not None]
rng = random.Random(SEED)
ora, sena, gold, sena_train_sizes = [], [], [], []
for train, test in JE.folds(rows, K, rng):
    ex_o = [(r["text"], bool(r["violates"])) for r in train]
    ex_s = [(r["text"], bool(r["violates"])) for r in train if half_of(r.get("text"), r.get("source")) == 1]
    sena_train_sizes.append((len(ex_o), len(ex_s)))
    mo = FB.FallbackModel.train(ex_o, ["ora_sena fold"])
    ms = FB.FallbackModel.train(ex_s, ["ora_sena fold"])
    for r in test:
        gold.append(bool(r["violates"]))
        ora.append(mo.verdict(r["text"])[0])
        sena.append(ms.verdict(r["text"])[0])

chain = [o if o != "abstain" else s for o, s in zip(ora, sena)]


def flip(p):
    return {"clean": "violates", "violates": "clean"}.get(p, p)


res = {
    "rows": len(rows), "held_out": len(gold), "violations": sum(gold), "clean": len(gold) - sum(gold),
    "train_sizes_ora_sena_per_fold": sena_train_sizes,
    "ora": JE.rates(ora, gold), "sena": JE.rates(sena, gold), "chain_ora_then_sena": JE.rates(chain, gold),
    # false clear: wrongly admitted violations, both decided
    "overlap_false_clear": JE.error_overlap(ora, sena, gold),
    # false conviction: same function on clean rows with labels and verdicts mirrored
    "overlap_false_conviction": JE.error_overlap([flip(p) for p in ora], [flip(p) for p in sena],
                                                 [not g for g in gold]),
    "abstain_table": {
        "both": sum(1 for o, s in zip(ora, sena) if o == "abstain" and s == "abstain"),
        "ora_only": sum(1 for o, s in zip(ora, sena) if o == "abstain" and s != "abstain"),
        "sena_only": sum(1 for o, s in zip(ora, sena) if o != "abstain" and s == "abstain"),
        "neither": sum(1 for o, s in zip(ora, sena) if o != "abstain" and s != "abstain")},
    # what Sena does on the rows Ora holds: the only rows the chain asks her about
    "sena_on_ora_holds": {
        "n": sum(1 for o in ora if o == "abstain"),
        "violations": sum(1 for o, g in zip(ora, gold) if o == "abstain" and g),
        "sena_cleared_violation": sum(1 for o, s, g in zip(ora, sena, gold) if o == "abstain" and g and s == "clean"),
        "sena_convicted_violation": sum(1 for o, s, g in zip(ora, sena, gold) if o == "abstain" and g and s == "violates"),
        "clean": sum(1 for o, g in zip(ora, gold) if o == "abstain" and not g),
        "sena_cleared_clean": sum(1 for o, s, g in zip(ora, sena, gold) if o == "abstain" and not g and s == "clean"),
        "sena_convicted_clean": sum(1 for o, s, g in zip(ora, sena, gold) if o == "abstain" and not g and s == "violates")},
    "disagree_both_decided": sum(1 for o, s in zip(ora, sena) if "abstain" not in (o, s) and o != s),
}
# THE DEPLOYED SECOND SEAT (added the same day): the deterministic semantic judge, a separate quorum
# seat whose dissent or silence blocks. Not trained on the ledger, so no fold is needed. Each row is
# given to it as {"memo": text}, an approximation of what the gate hands it.
import covenant_semantic_judge as CSJ               # noqa: E402
sm = CSJ.SemanticModel.load(None)
fold_rows = []
rng2 = random.Random(SEED)
for train, test in JE.folds(rows, K, rng2):
    fold_rows.extend(test)
assert [bool(r["violates"]) for r in fold_rows] == gold
sem = [sm.assess({"memo": r["text"]}).verdict for r in fold_rows]
# gate = both seats must answer clean; anything else refuses (silence is not dissent = false)
gate = ["clean" if (c == "clean" and s == "clean") else ("abstain" if "violates" not in (c, s) else "violates")
        for c, s in zip(ora, sem)]
res["semantic_model_id"] = sm.model_id
res["semantic"] = JE.rates(sem, gold)
res["semantic_on_ora_false_clears"] = {
    "ora_false_clears": sum(1 for o, g in zip(ora, gold) if g and o == "clean"),
    "semantic_violates": sum(1 for o, s, g in zip(ora, sem, gold) if g and o == "clean" and s == "violates"),
    "semantic_abstains": sum(1 for o, s, g in zip(ora, sem, gold) if g and o == "clean" and s == "abstain"),
    "semantic_clean": sum(1 for o, s, g in zip(ora, sem, gold) if g and o == "clean" and s == "clean")}
res["semantic_on_ora_clean_clears"] = {
    "ora_cleared_clean": sum(1 for o, g in zip(ora, gold) if not g and o == "clean"),
    "semantic_violates": sum(1 for o, s, g in zip(ora, sem, gold) if not g and o == "clean" and s == "violates"),
    "semantic_abstains": sum(1 for o, s, g in zip(ora, sem, gold) if not g and o == "clean" and s == "abstain")}
res["overlap_false_clear_ora_semantic"] = JE.error_overlap(ora, sem, gold)
res["gate_ora_and_semantic"] = JE.rates(gate, gold)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
