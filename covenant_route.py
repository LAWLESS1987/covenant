#!/usr/bin/env python3
"""covenant_route.py -- send a bounded task to the covenant's LOCAL judges
instead of to a cloud model.

WHY (2026-09-02). A 15-agent Claude workflow spent 2.6M tokens answering one
question. Most of that was judging and refuting: "does this claim survive?",
"which of these five is best?", "summarise this log". Those are bounded tasks
with a structured answer, and the covenant already runs judges for exactly
that shape -- Ollama on this machine (qwen3:8b, the ethics judge the nodes
call). This routes such tasks there. The cloud model is kept for what the
local one cannot do: open-ended synthesis, code, and reading its own output.

WHAT IT DOES
  judge      a prompt + a JSON shape -> the judge answers IN that shape.
  refute     a claim + evidence -> {"refuted": bool, "reason", "decisive_evidence"}
  rank       N candidates + criteria -> {"ranking": [...], "scores": {...}}
  summarize  a file -> {"summary", "facts": [...]} within --max-words

  --models  comma list (default qwen3:8b). --quorum k requires k models to
            agree on the primary field, else exit 3 (DISAGREE) with all views.
  Every call is appended to ops/judge_route.log as one JSON line: time, task,
  models, sha256 of the prompt, each model's answer, and the outcome. Records
  are kept, including the ones that disagreed (rule 5: refutations retained).

WHAT IT DOES NOT DO
  It stays on http://127.0.0.1:11434 while Ollama answers. A model whose name
  ends in ':cloud' is refused unless --allow-cloud is given, because that name
  means Ollama forwards the prompt off this machine. It places no order, reads
  no key, edits no file but the log and --out.

WHEN OLLAMA IS NOT ANSWERING (added 2026-09-04, asked for: "route through
  GitHub if Ollama is failing")
  If every local model errors with a connection failure, the same prompt goes
  to a judge on a GitHub Actions runner (covenant_github_judge.py, workflow
  judge.yml) -- 2-5 minutes, and the prompt LEAVES THIS PC to GitHub. The log
  line says so: "place": "github-actions". COVENANT_ROUTE_GITHUB=off disables
  it, =always forces it, default auto. A model unloaded or slow is not a
  connection failure and does not trigger it.

EXIT  0 answered   2 judge unavailable / no valid JSON   3 quorum disagreed

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
OLLAMA = os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434")
LOG = os.path.join(HERE, "ops", "judge_route.log")
DEFAULT_MODELS = os.environ.get("COVENANT_ROUTE_MODELS", "qwen3:8b")
# TIERS (2026-09-02). This laptop runs the judge on CPU (Ryzen 5 5625U, 6 cores,
# no usable GPU): qwen3:8b took 34 s for a 300-char judgment and 138 s for a
# 9.5k-char summary, and a 24.6k-char one timed out. Two copies of the same 8B
# model would each run at half speed. What helps: a smaller model for the
# bounded, low-stakes tasks (summarize, rank), a right-sized context instead
# of Ollama's 40,960 default (which alone made the load 11 GB), keeping the
# model warm between calls, and chunking long inputs. judge/refute stay on the
# 8B: those are the calls whose quality matters.
LIGHT_MODEL = os.environ.get("COVENANT_ROUTE_LIGHT", "qwen3:4b")
LIGHT_TASKS = {"summarize", "rank"}
NUM_CTX = {"judge": 4096, "refute": 6144, "rank": 6144, "summarize": 6144}
KEEP_ALIVE = os.environ.get("COVENANT_ROUTE_KEEP_ALIVE", "20m")
CHUNK_CHARS = 9000            # a summarize input above this is split and reduced
GITHUB = os.environ.get("COVENANT_ROUTE_GITHUB", "auto").lower()   # auto | off | always
GITHUB_MODEL = os.environ.get("COVENANT_GITHUB_MODEL", "qwen3:4b")
CONNECT_ERRORS = ("URLError", "ConnectionRefusedError", "ConnectionResetError", "RemoteDisconnected",
                  "TimeoutError", "timed out", "10061", "10054", "actively refused")


def have_model(name):
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=6) as r:
            return any(m.get("name") == name for m in json.loads(r.read().decode()).get("models", []))
    except Exception:                                            # noqa: BLE001
        return False

SYSTEM = ("You are a judge inside a system whose one rule is mutual benefit: honesty "
          "over green-looking results. Answer ONLY with a JSON object in exactly the "
          "shape requested. Never invent evidence; if the material does not settle the "
          "question say so in the reason. Be concise.")


def _post(path, body, timeout):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def ask(model, prompt, timeout=240, num_ctx=6144):
    """One model, JSON-only output, no chain-of-thought (qwen3 emits <think>
    otherwise -- covenant_judge_ollama.py measured that). Returns (obj, raw)."""
    body = {"model": model, "stream": False, "format": "json", "think": False,
            "keep_alive": KEEP_ALIVE,
            "options": {"temperature": 0, "num_predict": 900, "num_ctx": num_ctx},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": prompt}]}
    res = _post("/api/chat", body, timeout)
    raw = (res.get("message") or {}).get("content", "")
    try:
        return json.loads(raw), raw
    except ValueError:
        # one retry, asking for the object only
        body["messages"].append({"role": "assistant", "content": raw})
        body["messages"].append({"role": "user", "content": "Return only the JSON object."})
        res = _post("/api/chat", body, timeout)
        raw2 = (res.get("message") or {}).get("content", "")
        try:
            return json.loads(raw2), raw2
        except ValueError:
            return None, raw2


def reduce_chunks(text, a):
    """Map-reduce for long inputs: summarise each chunk with the light model,
    join the partial summaries, and let the final call summarise those. The
    partials are logged like any other call."""
    models = [m for m in a.models.split(",") if m.strip()]
    light = LIGHT_MODEL if have_model(LIGHT_MODEL) else models[0]
    parts = [text[i:i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)][:12]
    partial = []
    for k, chunk in enumerate(parts, 1):
        prompt = ("TASK: summarise part %d/%d in at most 120 words and list its hard facts.\n\n%s\n\n"
                  "Answer as JSON: {\"summary\": \"...\", \"facts\": [\"...\"]}" % (k, len(parts), chunk))
        rec, ok = route("summarize-part", prompt, "summary", [light], 1, a.allow_cloud, a.timeout)
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


def route(task, prompt, primary, models, quorum, allow_cloud, timeout):
    views, ok = [], []
    for m in models:
        if m.endswith(":cloud") and not allow_cloud:
            views.append({"model": m, "error": "refused: ':cloud' forwards the prompt off this machine (--allow-cloud to permit)"})
            continue
        t0 = time.time()
        try:
            obj, raw = ask(m, prompt, timeout, NUM_CTX.get(task, 6144))
        except Exception as e:                                   # noqa: BLE001
            views.append({"model": m, "error": "%s: %s" % (type(e).__name__, e)})
            continue
        v = {"model": m, "seconds": round(time.time() - t0, 1)}
        if obj is None:
            v["error"] = "no valid JSON"; v["raw"] = raw[:400]
        else:
            v["answer"] = obj; ok.append(obj)
        views.append(v)
    # Ollama down -> GitHub runner. Only a CONNECTION failure on every local
    # model counts (a bad JSON answer is the model's fault, not the socket's).
    local_dead = bool(models) and all("error" in v and any(k in v["error"] for k in CONNECT_ERRORS) for v in views)
    if GITHUB != "off" and not ok and (GITHUB == "always" or local_dead):
        t0 = time.time()
        try:
            import covenant_github_judge as gh
            ans = gh.ask(prompt, SYSTEM, GITHUB_MODEL, json_only=True, timeout=900)
            v = {"model": "github-actions/" + GITHUB_MODEL, "place": "github-actions",
                 "seconds": round(time.time() - t0, 1), "run_url": ans.get("run_url")}
            try:
                obj = json.loads(ans.get("content", ""))
                v["answer"] = obj; ok.append(obj)
            except ValueError:
                v["error"] = "no valid JSON"; v["raw"] = ans.get("content", "")[:400]
        except Exception as e:                                   # noqa: BLE001
            v = {"model": "github-actions/" + GITHUB_MODEL, "place": "github-actions",
                 "error": "%s: %s" % (type(e).__name__, e)}
        views.append(v)
        print("  [ollama unreachable -> GitHub runner: %s]" % (v.get("error") or "answered in %ss" % v["seconds"]),
              file=sys.stderr)
    outcome = "answered"
    if not ok:
        outcome = "unavailable"
    elif quorum > 1:
        keyvals = [json.dumps(o.get(primary), sort_keys=True) for o in ok]
        top = max(set(keyvals), key=keyvals.count)
        if keyvals.count(top) < quorum:
            outcome = "disagree"
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "task": task,
           "models": models, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()[:16],
           "prompt_chars": len(prompt), "views": views, "outcome": outcome}
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return rec, ok


def selftest():
    print("covenant_route selftest -- one bounded question to the local judge")
    prompt = ("TASK: judge.\nClaim: 'trader_log.txt has five run headers, the last dated "
              "2026-09-01, so the trader did not run on 2026-09-02.' The evidence is the "
              "log itself, which shows exactly those five headers and nothing for 09-02.\n"
              "Answer as JSON with exactly these keys: {\"verdict\": \"PASS|FAIL\", "
              "\"reason\": \"...\"}")
    rec, ok = route("judge", prompt, "verdict", DEFAULT_MODELS.split(","), 1, False, 300)
    print(json.dumps(rec, indent=1)[:1500])
    good = bool(ok) and str(ok[0].get("verdict", "")).upper().startswith("PASS")
    print("\n%s  the local judge answered in the requested shape with PASS" % ("ok  " if good else "FAIL"))
    return 0 if good else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", nargs="?", choices=["judge", "refute", "rank", "summarize"])
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--shape", default='{"verdict": "PASS|FAIL", "reason": "..."}')
    ap.add_argument("--claim"); ap.add_argument("--evidence"); ap.add_argument("--evidence-file")
    ap.add_argument("--file"); ap.add_argument("--criteria", default="honesty, evidence, cost realism")
    ap.add_argument("--max-words", type=int, default=200)
    ap.add_argument("--models", default=DEFAULT_MODELS)
    ap.add_argument("--quorum", type=int, default=1)
    ap.add_argument("--allow-cloud", action="store_true")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--out", help="write the answer JSON here as well as stdout")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.task:
        ap.error("task required (judge|refute|rank|summarize) or --selftest")
    prompt, primary = build_prompt(a.task, a)
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    if a.task in LIGHT_TASKS and a.models == DEFAULT_MODELS and have_model(LIGHT_MODEL):
        models = [LIGHT_MODEL]
    rec, ok = route(a.task, prompt, primary, models,
                    a.quorum, a.allow_cloud, a.timeout)
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
