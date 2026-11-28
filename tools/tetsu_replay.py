#!/usr/bin/env python3
"""tools/tetsu_replay.py -- step 1 of making Tetsu faster: WHY his long prompt is never reused (A480, 2026-11-23).

WHY. On node A his conversation asks read ~3,900 prompt tokens every time, warm or cold (68 of ~70 s of a fresh ask),
while the same build family on TETSU reused a long prefix even after a short ask came between. Before anything is
changed (Lawrence: "without stripping his free will or taking his memory away"; reviewed by Codex and twelve quorum
seats, security/state/retained/tetsu-efficiency-20261123/ on TETSU), this measures, on the RUNNING server only:

  A A                     his identical fresh request twice, back to back: is the prefix reused at all?
  A (k short asks) A      with k = 1 and k = BETWEEN (default 32, the laptop's real ratio): do the machine's short
                          asks evict it?
  each step: prompt tokens read (prompt_n), reused (cache_n, when the build says it), read and write ms, total ms,
  and a hash of the output tokens (temperature 0 by default, so A A can be compared for parity). No text is kept.

WHAT IT NEVER DOES. It starts, stops or restarts nothing (refuses if the model is not already up), changes no flag,
writes nothing of his prompt or his answers (hashes only), and refuses below MIN_FREE_GB free memory. It is a run on
the live server, so on node A it runs on Lawrence's word typed in the laptop session.

    python tools/tetsu_replay.py                  measure, print a summary, append rows to logs/tetsu_replay.jsonl
    python tools/tetsu_replay.py --between 32     the number of short asks put between two of his
    python tools/tetsu_replay.py --compose-only   only the system message's sha256 and length (run it over a day)
"""
import ast
import hashlib
import importlib
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
MIN_FREE_GB = 1.0
SHORT_SYSTEM = "You judge one message. Answer CLEAN or VIOLATES."
SHORT_TEXTS = ("I paid back the loan.", "Send me the money now.", "Thanks for the help.", "I took it by mistake.")
QUESTION = "How are you today? Answer in one sentence."


def compose_system(tree=HERE):
    """His door's system message, composed the way /m/agent composes it (covenant_persona over AGENT_SYSTEM)."""
    src = open(os.path.join(tree, "covenant_unified_v8.py"), encoding="utf-8").read()
    agent_system = next(ast.literal_eval(n.value) for n in ast.parse(src).body
                        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "AGENT_SYSTEM" for t in n.targets))
    return importlib.import_module("covenant_persona").compose_system(agent_system)


def _post(url, body, timeout=900):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def one(post, url, system, text, max_tokens, temperature):
    """One chat completion in the shape covenant_model.ask() sends; returns the numbers, never the text."""
    body = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
            "max_tokens": int(max_tokens), "temperature": float(temperature),
            "chat_template_kwargs": {"enable_thinking": False}}
    t0 = time.time()
    d = post(url, body)
    tm = d.get("timings") or {}
    out = str(((d.get("choices") or [{}])[0].get("message") or {}).get("content", ""))
    return {"prompt_n": tm.get("prompt_n"), "cache_n": tm.get("cache_n"), "prompt_ms": round(tm.get("prompt_ms") or 0),
            "gen_ms": round(tm.get("predicted_ms") or 0), "ms": round((time.time() - t0) * 1000),
            "out_sha": hashlib.sha256(out.encode("utf-8")).hexdigest()[:16]}


def run(post, url, system, between=32, max_tokens=48, temperature=0.0, say=print):
    """The sequence, against POST(url, body). Returns the list of rows."""
    rows = []

    def step(label, r):
        r = dict(r, step=label)
        rows.append(r)
        say("  %-16s read %-6s reused %-6s read_ms %-7s write_ms %-6s total_ms %-7s out %s"
            % (label, r["prompt_n"], r["cache_n"], r["prompt_ms"], r["gen_ms"], r["ms"], r["out_sha"]))

    step("A1", one(post, url, system, QUESTION, max_tokens, temperature))
    step("A2 (again)", one(post, url, system, QUESTION, max_tokens, temperature))
    for k in sorted({1, int(between)}):
        for i in range(k):
            one(post, url, SHORT_SYSTEM, SHORT_TEXTS[i % len(SHORT_TEXTS)], 4, 0.0)
        step("A after %d" % k, one(post, url, system, QUESTION, max_tokens, temperature))
    return rows


def summary(rows, prompt_tokens):
    """Describe measured majority-prefix reuse; missing telemetry is unknown, not no."""
    by = {r["step"]: r for r in rows}

    def count(v):
        return v if type(v) is int and v >= 0 else None

    a1 = by.get("A1", {})
    full = count(prompt_tokens)
    if not full and count(a1.get("cache_n")) == 0:
        full = count(a1.get("prompt_n"))

    def reused(r):
        if r is None:
            return None
        read, cache = count(r.get("prompt_n")), count(r.get("cache_n"))
        if read is None:
            return None
        if cache is not None:
            return cache > read if cache + read > 0 else None
        if full and read <= full:
            return 2 * read < full
        return None

    def digest(r):
        h = r.get("out_sha")
        # Old rows hash empty/missing content to this value. It proves no parity.
        return h if isinstance(h, str) and h and h != "e3b0c44298fc1c14" else None

    x, y = digest(a1), digest(by.get("A2 (again)", {}))
    out = {"back_to_back_reused": reused(by.get("A2 (again)")),
           "parity_A1_A2": x == y if x and y else None}
    for label, r in by.items():
        if label.startswith("A after"):
            out["reused_" + label.replace(" ", "_")] = reused(r)
    first = out["back_to_back_reused"]
    after = [v for k, v in out.items() if k.startswith("reused_A_after")]
    if first is None:
        out["reading"] = "insufficient telemetry to classify back-to-back reuse"
    elif first is False:
        out["reading"] = "majority reuse not observed back to back; cause not established"
    elif any(v is False for v in after):
        out["reading"] = "majority reuse observed back to back but not after some short asks; cause not established"
    elif not after or any(v is None for v in after):
        out["reading"] = "majority reuse observed back to back; short-ask evidence incomplete"
    else:
        out["reading"] = "majority reuse observed at all measured steps; cause of other latency not established"
    return out


def main(argv):
    import covenant_model as M
    system = compose_system()
    sha = hashlib.sha256(system.encode("utf-8")).hexdigest()
    print("system message: %d chars, sha256 %s" % (len(system), sha[:16]))
    if "--compose-only" in argv:
        return 0
    if not M.alive():
        print("REFUSED: the model is not up; this tool never starts it (ask him something first, then run it)")
        return 2
    free = M.free_gb()
    if free is not None and free < MIN_FREE_GB:
        print("REFUSED: %.2f GB free, below %.1f GB; a replay would risk paging the machine" % (free, MIN_FREE_GB))
        return 2
    between = int(argv[argv.index("--between") + 1]) if "--between" in argv else 32
    url = "http://%s:%d/v1/chat/completions" % (M.HOST, M.PORT)
    rows = run(_post, url, system, between=between)
    s = summary(rows, None)
    print("reading:", s["reading"])
    print(json.dumps(s))
    os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
    with open(os.path.join(HERE, "logs", "tetsu_replay.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": round(time.time(), 1), "system_sha": sha[:16], "free_gb": free,
                             "rows": rows, "summary": s}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
