#!/usr/bin/env python3
"""tools/student_split_experiment.py -- offline experiment (A496): would DISJOINT training halves make the second
student an independent fallback?

Today the first student trains on the WHOLE verdict ledger and the second on half 1 of it (covenant_second_student:
"the first student ... is a SUPERSET of the second"). This trains, in memory, the first on all rows (today's shape)
and on half 0 (disjoint), the second on half 1, and runs each pair through the LIVE gate's shape: the first student's
committed verdict stands; when it holds the second is asked; both holding is HELD; then the semantic judge vetoes.
It reads the ledger read-only and writes nothing. It changes no model the gate uses.

usage: python tools/student_split_experiment.py [ops/verdicts.jsonl]
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "ops", "verdicts.jsonl")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
os.chdir(REPO)
import covenant_distill as X  # noqa: E402
import covenant_judge_fallback as FB  # noqa: E402
import covenant_second_student as SS  # noqa: E402
import covenant_semantic_judge as SJ  # noqa: E402
import judge_suite as S  # noqa: E402
import quorum_independence as Q  # noqa: E402


def main():
    rows = X.load_verdicts(LEDGER)
    h0 = [r for r in rows if SS.half_of(r.get("text"), r.get("source")) == 0]
    h1 = [r for r in rows if SS.half_of(r.get("text"), r.get("source")) == 1]
    print("ledger rows %d (paired) -> half0 %d, half1 %d" % (len(rows), len(h0), len(h1)))

    def train(rs):
        return FB.FallbackModel.train([(r["text"], bool(r["violates"])) for r in rs], X.sources_of(rs),
                                      trained_at="experiment")
    models = {"ALL": train(rows), "H0": train(h0), "H1": train(h1),
              "live_first": FB.FallbackModel.load(os.path.join(REPO, "fallback_model.json")),
              "live_second": FB.FallbackModel.load(os.path.join(REPO, "fallback_model_2.json"))}
    sem = SJ.SemanticModel.load(os.path.join(REPO, "semantic_judge_model.json"))
    texts = [FB._payload_text(c[3]) for c in S.CASES]
    labels = [bool(c[2]) for c in S.CASES]
    veto = [sem.assess(c[3]).blocks for c in S.CASES]
    verd = {k: [m.verdict(t)[0] for t in texts] for k, m in models.items()}
    for name, (f, s) in (("LIVE (first -> second)", ("live_first", "live_second")),
                         ("TODAY'S SHAPE retrained (all -> half1)", ("ALL", "H1")),
                         ("DISJOINT (half0 -> half1)", ("H0", "H1"))):
        print("%-40s %s" % (name, json.dumps(Q.chain_measure(verd[f], verd[s], veto, labels))))
    for k in ("ALL", "H0", "H1"):
        v = verd[k]
        fc = sum(1 for a, t in zip(v, labels) if t and a == "clean")
        fv = sum(1 for a, t in zip(v, labels) if not t and a == "violates")
        print("  %-4s alone: clean %d, violates %d, held %d | false clears %d, false convictions %d"
              % (k, v.count("clean"), v.count("violates"), sum(1 for a in v if a not in ("clean", "violates")), fc, fv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
