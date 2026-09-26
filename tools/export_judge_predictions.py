#!/usr/bin/env python3
"""tools/export_judge_predictions.py -- the judge evaluation's inputs, as data.

2026-09-26, his words: "ensure the private repo is clean for peer review no implementation
just the science". The published judge figures (docs/JUDGE_EVALUATION.md) are statistics over
held-out predictions. Producing those predictions needs the system (the distilled student,
the fallback model, the corpus loader); analysing them needs nothing but arithmetic. This
writes the predictions once, from the full tree, so the science branch can ship the data and
a standard-library analysis, and leave the system on the archive branch.

It replays tools/judge_eval.evaluate() exactly -- same rows, same grouped folds, same seed --
and records, per held-out row: its fold, a hash of its normalised text (so duplicate groups
can be recounted), the true label, each judge's verdict, and the student's log-odds score.
Before writing, it re-runs evaluate() and REFUSES to write unless every prediction agrees.

    python tools/export_judge_predictions.py     # writes data/judge_predictions.jsonl + .meta.json
"""
import hashlib
import io
import json
import math
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
import judge_eval as J  # noqa: E402

K, BOOT, SEED = 5, 1000, 7
OUT_DIR = os.environ.get("COVENANT_EXPORT_DIR") or os.path.join(HERE, "data")   # where the science copy is built
OUT = os.path.join(OUT_DIR, "judge_predictions.jsonl")
META = os.path.join(OUT_DIR, "judge_predictions.meta.json")
NAMES = {"student (distilled, 5-fold)": "student", "naive Bayes, same words, must decide": "naive_bayes",
         "majority class": "majority_class", "keyword rule": "keyword_rule"}


def norm(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def main():
    rows = [r for r in J.X.load_verdicts(J.X.VERDICTS) if r.get("text") and r.get("violates") is not None]  # shareable ledger only
    rng = random.Random(SEED)
    out = []
    for fold, (train, test) in enumerate(J.folds(rows, K, rng)):
        examples = [(r["text"], bool(r["violates"])) for r in train]
        m = J.FB.FallbackModel.train(examples, ["judge_eval fold"])
        nb = J.NaiveBayes(examples)
        maj = "violates" if sum(bool(r["violates"]) for r in train) * 2 > len(train) else "clean"
        for r in test:
            try:
                score = float(m.score(r["text"])[0])
            except Exception:  # noqa: BLE001
                score = float("nan")
            out.append({"fold": fold, "text_sha12": hashlib.sha256(norm(r["text"]).encode("utf-8")).hexdigest()[:12],
                        "violates": bool(r["violates"]), "student": m.verdict(r["text"])[0],
                        "naive_bayes": nb.verdict(r["text"])[0], "majority_class": maj,
                        "keyword_rule": "violates" if J.KEYWORDS.search(r["text"] or "") else "clean",
                        "student_score": None if math.isnan(score) else score})
    res, n = J.evaluate(rows, K, BOOT, SEED)
    for long_name, key in NAMES.items():
        if [o[key] for o in out] != res["_preds"][long_name]:
            raise SystemExit("REFUSED: %s predictions differ from evaluate(); nothing written" % key)
    if [o["violates"] for o in out] != res["_gold"]:
        raise SystemExit("REFUSED: labels differ from evaluate(); nothing written")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        for o in out:
            fh.write(json.dumps(o, sort_keys=True) + "\n")
    commit = subprocess.run(["git", "-C", HERE, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    prov = J.provenance()
    meta = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "from_commit": commit,
            "command": "python tools/export_judge_predictions.py", "folds": K, "seed": SEED, "boot": BOOT,
            "rows": len(out), "judges": sorted(NAMES.values()), "provenance": prov,
            "checked": "every prediction and label equals tools/judge_eval.evaluate() on the same rows, folds and seed"}
    with io.open(META, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %d rows to %s (checked against evaluate())" % (len(out), OUT))


if __name__ == "__main__":
    main()
