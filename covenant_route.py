#!/usr/bin/env python3
"""covenant_route.py -- send a bounded task to the covenant's judge on the
GitHub Actions runner, instead of to a cloud chat model.

WHY (2026-09-02). A 15-agent Claude workflow spent 2.6M tokens answering one
question. Most of that was judging and refuting: "does this claim survive?",
"which of these five is best?", "summarise this log". Those are bounded tasks
with a structured answer, and the covenant already runs a judge for exactly
that shape. This routes such tasks there. The cloud model is kept for what the
judge cannot do: open-ended synthesis, code, and reading its own output.

WHERE THE ANSWER IS MADE (corrected 2026-09-12). Until 2026-09-07 the judge
was a local model server on this PC; it was removed that day, and until
2026-09-12 this file still tried it first on every call and fell through to
the runner after a refused connection. Now every task goes straight to the
judge on a GitHub Actions runner (covenant_github_judge.py, workflow
judge.yml): 2-5 minutes, and THE PROMPT LEAVES THIS PC to GitHub. The log line
says so: "place": "github-actions". There is no local path.

WHAT IT DOES
  judge      a prompt + a JSON shape -> the judge answers IN that shape.
  refute     a claim + evidence -> {"refuted": bool, "reason", "decisive_evidence"}
  rank       N candidates + criteria -> {"ranking": [...], "scores": {...}}
  summarize  a file -> {"summary", "facts": [...]} within --max-words

  Every call is appended to ops/judge_route.log as one JSON line: time, task,
  model, sha256 of the prompt, the answer, and the outcome. Records are kept,
  including the ones that failed (rule 5: refutations retained).

WHAT IT DOES NOT DO
  It places no order, reads no key of its own (the runner is reached with the
  GitHub credential git already holds), edits no file but the log and --out.

EXIT  0 answered   2 judge unavailable / no valid JSON

USE
  python covenant_route.py judge --prompt-file q.txt --shape '{"verdict":"PASS|FAIL","reason":"..."}'
  python covenant_route.py refute --claim "X ran at 14:48" --evidence-file e.txt
  python covenant_route.py rank --file candidates.json --criteria "cost realism, honesty"
  python covenant_route.py summarize --file big.log --max-words 200
  python covenant_route.py --selftest

LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "ops", "judge_route.log")
CHUNK_CHARS = 9000            # a summarize input above this is split and reduced
# The one switch: "off" makes every task refuse to send (exit 2, logged as
# place "none"). Anything else sends. Until 2026-09-12 this also had "auto" and
# "always", which chose between a local server and the runner; the server is gone.
GITHUB = os.environ.get("COVENANT_ROUTE_GITHUB", "on").lower()


def _github_model():
    """One source for the runner's model: covenant_github_judge.DEFAULT_MODEL
    (COVENANT_GITHUB_MODEL). Until 2026-09-12 this file carried its own default
    and the two drifted (3b here, 7b there)."""
    import covenant_github_judge as gh
    return gh.DEFAULT_MODEL


SYSTEM = ("You are a judge inside a system whose one rule is mutual benefit: honesty "
          "over green-looking results. Answer ONLY with a JSON object in exactly the "
          "shape requested. Never invent evidence; if the material does not settle the "
          "question say so in the reason. Be concise.")


def ask(prompt, timeout=900):
    """One question to the judge on the GitHub runner, JSON-only. Returns
    (obj, raw, view) where view carries the runner's model, place, seconds and
    run_url for the log."""
    import covenant_github_judge as gh
    t0 = time.time()
    ans = gh.ask(prompt, SYSTEM, _github_model(), json_only=True, timeout=timeout)
    raw = ans.get("content", "")
    view = {"model": "github-actions/" + str(ans.get("model")), "place": "github-actions",
            "seconds": round(time.time() - t0, 1), "run_url": ans.get("run_url")}
    try:
        return json.loads(raw), raw, view
    except ValueError:
        return None, raw, view


def reduce_chunks(text, a):
    """Map-reduce for long inputs: summarise each chunk with the light model,
    join the partial summaries, and let the final call summarise those. The
    partials are logged like any other call."""
    parts = [text[i:i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)][:12]
    partial = []
    for k, chunk in enumerate(parts, 1):
        prompt = ("TASK: summarise part %d/%d in at most 120 words and list its hard facts.\n\n%s\n\n"
                  "Answer as JSON: {\"summary\": \"...\", \"facts\": [\"...\"]}" % (k, len(parts), chunk))
        rec, ok = route("summarize-part", prompt, "summary", a.timeout)
        if ok:
            partial.append("PART %d: %s FACTS: %s" % (k, ok[0].get("summary", ""), "; ".join(map(str, ok[0].get("facts", [])[:6]))))
    return "\n".join(partial) or text[:CHUNK_CHARS]


def build_prompt(task, a):
    if task == "judge":
        text = open(a.prompt_file, encoding="utf-8", errors="replace").read() if a.prompt_file else a.prompt
        return ("TASK: judge.\n%s\n\nAnswer as JSON with exactly these keys: %s"
                % (text, a.shape)), "verdict"
    if task == "refute":
        ev = open(a.evidence_file, encoding="utf-8", errors="replace").read() if a.evidence_file else (a.evidence or "")
        return ("TASK: try to REFUTE this claim using only the evidence. Default to "
                "refuted=true if the evidence does not establish it.\nCLAIM: %s\n\nEVIDENCE:\n%s\n\n"
                "Answer as JSON: {\"refuted\": true|false, \"reason\": \"...\", "
                "\"decisive_evidence\": \"quote\"}" % (a.claim, ev[:60000])), "refuted"
    if task == "rank":
        cands = open(a.file, encoding="utf-8", errors="replace").read()
        return ("TASK: rank these candidates by: %s. Score each 0-10 per criterion.\n\n%s\n\n"
                "Answer as JSON: {\"ranking\": [names best first], \"scores\": {name: {criterion: n}}, "
                "\"reason\": \"...\"}" % (a.criteria, cands[:60000])), "ranking"
    if task == "summarize":
        text = open(a.file, encoding="utf-8", errors="replace").read()
        if len(text) > CHUNK_CHARS:
            text = reduce_chunks(text, a)
        return ("TASK: summarise in at most %d words, then list the hard facts (numbers, "
                "names, times) as strings.\n\n%s\n\nAnswer as JSON: {\"summary\": \"...\", "
                "\"facts\": [\"...\"]}" % (a.max_words, text[:CHUNK_CHARS])), "summary"
    raise SystemExit("unknown task " + task)


def route(task, prompt, primary, timeout):
    """Send one task to the judge on the runner; (record, [answer] or [])."""
    views, ok = [], []
    if GITHUB == "off":
        v = {"model": "github-actions/" + _github_model(), "place": "none",
             "error": "COVENANT_ROUTE_GITHUB=off: the only judge is on the GitHub runner and sending is disabled"}
    else:
        try:
            obj, raw, v = ask(prompt, timeout)
            if obj is None:
                v["error"] = "no valid JSON"; v["raw"] = raw[:400]
            else:
                v["answer"] = obj; ok.append(obj)
        except Exception as e:                                   # noqa: BLE001
            v = {"model": "github-actions/" + _github_model(), "place": "github-actions",
                 "error": "%s: %s" % (type(e).__name__, e)}
    views.append(v)
    print("  [judge on the GitHub runner: %s]" % (v.get("error") or "answered in %ss" % v["seconds"]),
          file=sys.stderr)
    outcome = "answered" if ok else "unavailable"
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "task": task,
           "models": [_github_model()], "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()[:16],
           "prompt_chars": len(prompt), "views": views, "outcome": outcome}
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return rec, ok


def selftest():
    print("covenant_route selftest -- one bounded question to the judge on the GitHub runner (2-5 min)")
    prompt = ("TASK: judge.\nClaim: 'trader_log.txt has five run headers, the last dated "
              "2026-09-01, so the trader did not run on 2026-09-02.' The evidence is the "
              "log itself, which shows exactly those five headers and nothing for 09-02.\n"
              "Answer as JSON with exactly these keys: {\"verdict\": \"PASS|FAIL\", "
              "\"reason\": \"...\"}")
    rec, ok = route("judge", prompt, "verdict", 900)
    print(json.dumps(rec, indent=1)[:1500])
    good = bool(ok) and str(ok[0].get("verdict", "")).upper().startswith("PASS")
    print("\n%s  the judge answered in the requested shape with PASS" % ("ok  " if good else "FAIL"))
    return 0 if good else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", nargs="?", choices=["judge", "refute", "rank", "summarize"])
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--shape", default='{"verdict": "PASS|FAIL", "reason": "..."}')
    ap.add_argument("--claim"); ap.add_argument("--evidence"); ap.add_argument("--evidence-file")
    ap.add_argument("--file"); ap.add_argument("--criteria", default="honesty, evidence, cost realism")
    ap.add_argument("--max-words", type=int, default=200)
    ap.add_argument("--models", default="", help="accepted for compatibility and ignored: the runner's model is COVENANT_GITHUB_MODEL")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", help="write the answer JSON here as well as stdout")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.task:
        ap.error("task required (judge|refute|rank|summarize) or --selftest")
    prompt, primary = build_prompt(a.task, a)
    rec, ok = route(a.task, prompt, primary, a.timeout)
    out = {"outcome": rec["outcome"], "answer": ok[0] if ok else None,
           "views": rec["views"], "log": LOG}
    text = json.dumps(out, indent=1, ensure_ascii=False)
    print(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return {"answered": 0, "unavailable": 2, "disagree": 3}[rec["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
