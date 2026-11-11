import json, os, random, sys
REPO = sys.argv[1]
sys.path.insert(0, REPO); sys.path.insert(0, os.path.join(REPO, "tools"))
import covenant_distill as X, covenant_judge_fallback as FB, judge_eval as JE
rows = [r for r in X.load_verdicts(X.VERDICTS) if r.get("text") and r.get("violates") is not None]
out = []
for train, test in JE.folds(rows, 5, random.Random(7)):
    m = FB.FallbackModel.train([(r["text"], bool(r["violates"])) for r in train], ["dump44"])
    for r in test:
        if r["violates"] and m.verdict(r["text"])[0] == "clean":
            out.append({k: r.get(k) for k in ("text", "source", "principle", "reasoning", "votes", "panel") if r.get(k) is not None})
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
print(len(out))
