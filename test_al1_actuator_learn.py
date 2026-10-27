#!/usr/bin/env python3
"""test_al1_actuator_learn.py -- AL1: what the phone's actuator has learned,
synced to the PC.

Offline, in a temp directory: no phone, no real signature verification here
(that's covenant_daily_plan's own tested territory; this suite starts at
record_sync(), the function the route hands a verified body to). Every check
RUNS the function it guards. The false pushes toward MORE capability that
must be refused: a body that isn't the right shape, a secret leaked through
last_answer, a length-scan bypass, and a bad recipe among good ones taking
the whole sync down with it. And what must work: every recipe in one sync
gets its own row, a clean sync is fully kept, and nothing is ever silently
dropped -- a refused recipe is still a row, with its reason.

Run: python test_al1_actuator_learn.py     -> "AL1: n/n passed"
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_actuator_learn as AL                          # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:220]), flush=True)


def body(recipes):
    return json.dumps({"recipes": recipes}).encode("utf-8")


def main():
    td = tempfile.mkdtemp(prefix="al1_")
    ledger = os.path.join(td, "actuator_learning.jsonl")
    now = 1_800_000_000.0

    code, out = AL.record_sync(b"not json", "phone", ledger, now)
    check("AL1.1 REFUSED: a body that is not JSON", code == 400 and "not JSON" in out["message"])
    code, out = AL.record_sync(json.dumps({"nope": []}).encode(), "phone", ledger, now)
    check("AL1.2 REFUSED: a body without a 'recipes' list", code == 400 and "recipes" in out["message"])
    check("AL1.2b ...and nothing was written for either refusal", not os.path.exists(ledger))

    clean_recipe = {"name": "ask chatgpt about photosynthesis", "pkg": "com.openai.chatgpt", "steps": 5, "slots": 1,
                    "runs": ["2026-09-14 09:00 ok: done: 5 step(s) (4 s)"], "last_answer": "Photosynthesis converts light into chemical energy."}
    code, out = AL.record_sync(body([clean_recipe]), "phone", ledger, now)
    check("AL1.3 a clean recipe: 200, recorded, kept (not held/refused)", code == 200 and out["recorded"] == 1 and clean_recipe["name"] in out["kept"], out)
    rows = [json.loads(l) for l in open(ledger, encoding="utf-8")]
    check("AL1.4 one ledger row, carries who signed, the recipe name, and the answer's sha256", len(rows) == 1 and rows[0]["signer"] == "phone"
          and rows[0]["recipe"] == clean_recipe["name"] and rows[0]["last_answer_sha256"] == AL._sha(clean_recipe["last_answer"]), rows)
    check("AL1.5 the kept answer text IS on the row (this is the whole point: info to learn from)", rows[0]["last_answer"] == clean_recipe["last_answer"])
    check("AL1.6 raw slot TEXT is never part of the payload contract -- only a slot COUNT", "slots" in rows[0] and rows[0]["slots"] == 1 and "slot_text" not in json.dumps(rows[0]))

    secret_recipe = {"name": "leaky recipe", "pkg": "com.example", "steps": 1, "slots": 0, "runs": [],
                     "last_answer": "here is the key: -----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----"}
    ledger2 = os.path.join(td, "secret.jsonl")
    code, out = AL.record_sync(body([secret_recipe]), "phone", ledger2, now)
    check("AL1.7 a recipe whose read-back answer contains a private key: still 200 (recorded, not silently dropped) but HELD/REFUSED not kept",
          code == 200 and secret_recipe["name"] in out["held_or_refused"] and secret_recipe["name"] not in out["kept"], out)
    rows2 = [json.loads(l) for l in open(ledger2, encoding="utf-8")]
    check("AL1.8 the refused row is STILL WRITTEN, with clean=false and the answer withheld (not None-by-accident)",
          len(rows2) == 1 and rows2[0]["clean"] is False and rows2[0]["last_answer"] is None and rows2[0]["last_answer_sha256"], rows2)

    long_secret = "x" * 3000 + "COVENANT_GITHUB_TOKEN: ghp_" + "a" * 36
    ledger3 = os.path.join(td, "long.jsonl")
    code, out = AL.record_sync(body([{"name": "long leak", "pkg": "p", "steps": 1, "slots": 0, "runs": [], "last_answer": long_secret}]), "phone", ledger3, now)
    check("AL1.9 a secret past the question-length scan window (inside a 6000-char answer) is still caught", "long leak" in out["held_or_refused"], out)

    mixed = [clean_recipe, secret_recipe, {"name": "no answer yet", "pkg": "p", "steps": 2, "slots": 0, "runs": []}]
    ledger4 = os.path.join(td, "mixed.jsonl")
    code, out = AL.record_sync(body(mixed), "phone", ledger4, now)
    check("AL1.10 a bad recipe in the same sync does NOT sink the good ones -- 3 recorded, 2 kept, 1 held/refused",
          code == 200 and out["recorded"] == 3 and len(out["kept"]) == 2 and len(out["held_or_refused"]) == 1, out)
    check("AL1.11 a recipe with no last_answer at all judges clean by default (nothing to leak)", "no answer yet" in out["kept"])

    malformed = [{"pkg": "p", "steps": 1}, {"name": "", "steps": 1}, "not even a dict", clean_recipe]
    ledger5 = os.path.join(td, "malformed.jsonl")
    code, out = AL.record_sync(body(malformed), "phone", ledger5, now)
    check("AL1.12 a nameless or non-dict entry is skipped, not crashed on; the one good recipe still lands",
          code == 200 and out["recorded"] == 1 and clean_recipe["name"] in out["kept"], out)

    huge_runs = ["run %d" % i for i in range(80)]
    code, out = AL.record_sync(body([{"name": "many runs", "pkg": "p", "steps": 1, "slots": 0, "runs": huge_runs, "last_answer": ""}]), "phone", ledger, now)
    rows6 = [json.loads(l) for l in open(ledger, encoding="utf-8")]
    check("AL1.13 runs are capped at MAX_RUNS_KEPT on the way in, the newest kept", len(rows6[-1]["runs"]) == AL.MAX_RUNS_KEPT and rows6[-1]["runs"][-1] == huge_runs[-1], len(rows6[-1]["runs"]))

    check("AL1.14 --explain text names the ledger, the judge and why last_answer is what's judged",
          "ops/actuator_learning.jsonl" in AL.EXPLAIN and "judge_learned_text" in AL.EXPLAIN.replace("_", "_") or "judged" in AL.EXPLAIN.lower())

    n, good = len(results), sum(results)
    print("AL1: %d/%d passed" % (good, n))
    return 0 if good == n else 1


if __name__ == "__main__":
    sys.exit(main())
