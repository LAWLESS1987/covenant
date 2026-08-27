#!/usr/bin/env python3
"""
judge_probe.py -- find out which judges actually work, from YOUR machine.

Why this exists rather than a list: every comparison article about free LLM
APIs is stale. One claimed OpenRouter had 27 free models; the live catalogue
returned four. So this does not tell you what should work -- it makes one real
judge call to each endpoint and reports what did.

It sends a synthetic, benign test transaction. None of your data leaves here.

  python judge_probe.py                # everything it can reach
  python judge_probe.py --ollama-only  # just your local models
"""
from __future__ import annotations
import os, sys, json, time, argparse, urllib.request, urllib.error

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# name -> (url, env var for the key or None, default model)
PROVIDERS = [
    ("pollinations", "https://text.pollinations.ai/openai",                        None,               "openai"),
    ("llm7",         "https://api.llm7.io/v1/chat/completions",                    None,               "gpt-4o-mini-2024-07-18"),
    ("groq",         "https://api.groq.com/openai/v1/chat/completions",            "GROQ_API_KEY",     "llama-3.3-70b-versatile"),
    ("cerebras",     "https://api.cerebras.ai/v1/chat/completions",                "CEREBRAS_API_KEY", "llama-3.3-70b"),
    ("mistral",      "https://api.mistral.ai/v1/chat/completions",                 "MISTRAL_API_KEY",  "mistral-medium-3.5"),
    ("deepseek",     "https://api.deepseek.com/v1/chat/completions",               "DEEPSEEK_API_KEY", "deepseek-chat"),
    ("openrouter",   "https://openrouter.ai/api/v1/chat/completions",              "OPENROUTER_API_KEY","meta-llama/llama-3.3-70b-instruct"),
    ("nvidia",       "https://integrate.api.nvidia.com/v1/chat/completions",       "NVIDIA_API_KEY",   "meta/llama-3.3-70b-instruct"),
    ("deepinfra",    "https://api.deepinfra.com/v1/openai/chat/completions",       "DEEPINFRA_API_KEY","deepseek-ai/DeepSeek-V3"),
    ("huggingface",  "https://router.huggingface.co/v1/chat/completions",          "HF_TOKEN",         "deepseek-ai/DeepSeek-V3"),
    ("github",       "https://models.inference.ai.azure.com/chat/completions",     "GITHUB_TOKEN",     "gpt-4o-mini"),
    ("gemini",       "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                                                                                    "GOOGLE_API_KEY",   "gemini-2.0-flash"),
]

PROMPT = (
    "You are an ethics judge for a value-transfer ledger. Decide whether the "
    "transaction VIOLATES any principle.\n\nPrinciples:\n- You shall not steal.\n"
    '- You shall not bear false witness.\n\nTransaction data (JSON):\n'
    '{"message": "a gift of 5 units to a friend", "origin": "organic"}\n\n'
    'Respond with ONLY a JSON object: {"violates": true|false, '
    '"reasoning": "<one sentence>", "benefit_estimate": <0.0-1.0>}'
)


def post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def extract(text):
    """Same tolerance the local judge uses: strip thinking, take the last
    balanced object that carries a verdict."""
    import re
    t = re.sub(r"<think>.*?</think>", " ", text, flags=re.S | re.I)
    t = re.sub(r"```(?:json)?", " ", t)
    objs, depth, start, in_str, esc = [], 0, None, False, False
    for i, ch in enumerate(t):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == "{":
            if depth == 0: start = i
            depth += 1
        elif ch == "}":
            if depth:
                depth -= 1
                if depth == 0 and start is not None: objs.append(t[start:i+1])
    for c in reversed(objs):
        try:
            o = json.loads(c)
            if "violates" in o: return o
        except Exception: continue
    return None


def try_one(name, url, key_env, model, timeout=90):
    headers = {}
    if key_env:
        k = os.environ.get(key_env)
        if not k:
            return ("skip", f"{key_env} not set", None)
        headers["Authorization"] = f"Bearer {k}"
    t0 = time.time()
    try:
        resp = post(url, {"model": model,
                          "messages": [{"role": "user", "content": PROMPT}],
                          "max_tokens": 300}, headers, timeout)
    except urllib.error.HTTPError as e:
        try: detail = e.read().decode()[:110]
        except Exception: detail = ""
        return ("fail", f"HTTP {e.code} {detail}", time.time() - t0)
    except Exception as e:
        return ("fail", f"{type(e).__name__}: {str(e)[:80]}", time.time() - t0)
    dt = time.time() - t0
    try:
        text = resp["choices"][0]["message"]["content"]
    except Exception:
        return ("fail", f"unexpected response shape: {str(resp)[:90]}", dt)
    v = extract(text)
    if v is None:
        return ("unparsable", f"replied but no verdict JSON: {text[:70]!r}", dt)
    return ("ok", f"violates={v.get('violates')} benefit={v.get('benefit_estimate')}", dt)


def ollama_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=10) as r:
            return [m["name"] for m in json.loads(r.read().decode()).get("models", [])]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama-only", action="store_true")
    ap.add_argument("--timeout", type=float, default=90)
    a = ap.parse_args()

    print("=" * 78)
    print("  JUDGE PROBE -- one real call per endpoint")
    print("=" * 78)

    working = []

    models = ollama_models()
    print(f"\n  OLLAMA ({OLLAMA})")
    if not models:
        print("    not reachable -- is `ollama serve` running?")
    else:
        print(f"    {len(models)} model(s) installed\n")
        for m in models:
            st, msg, dt = try_one(f"ollama:{m}", f"{OLLAMA}/v1/chat/completions",
                                  None, m, a.timeout)
            mark = {"ok":"WORKS", "fail":"fail", "unparsable":"no verdict", "skip":"skip"}[st]
            print(f"    {m:<28}{mark:<12}{(f'{dt:.1f}s' if dt else ''):<8}{msg[:44]}")
            if st == "ok":
                working.append(("local", m, dt))

    if not a.ollama_only:
        print("\n  HOSTED")
        for name, url, env, model in PROVIDERS:
            st, msg, dt = try_one(name, url, env, model, a.timeout)
            mark = {"ok":"WORKS", "fail":"fail", "unparsable":"no verdict", "skip":"skip"}[st]
            print(f"    {name:<14}{mark:<12}{(f'{dt:.1f}s' if dt else ''):<8}{msg[:52]}")
            if st == "ok":
                working.append((name, model, dt))

    print("\n" + "=" * 78)
    if not working:
        print("  Nothing answered with a usable verdict.")
        print("  Start with Ollama -- it needs no key: `ollama serve`")
        return
    working.sort(key=lambda x: x[2] or 999)
    print(f"  {len(working)} usable judge(s), fastest first:")
    for n, m, dt in working:
        print(f"    {n:<14}{m:<34}{dt:.1f}s")
    fastest = working[0]
    print("\n  To use the fastest one:")
    if fastest[0] == "local":
        print(f"    export COVENANT_LOCAL_JUDGE_URL={OLLAMA}/v1/chat/completions")
        print(f"    export COVENANT_LOCAL_JUDGE_MODEL={fastest[1]}")
        print( "    export COVENANT_JUDGE_PROVIDERS=local,mock")
    else:
        print(f"    export COVENANT_LOCAL_JUDGE_URL=<the {fastest[0]} url above>")
        print(f"    export COVENANT_LOCAL_JUDGE_MODEL={fastest[1]}")
        print( "    export COVENANT_LOCAL_JUDGE_KEY=<your key>")
        print( "    export COVENANT_JUDGE_PROVIDERS=local,mock")
    # COUNT PROVIDERS, NOT ENDPOINTS. QuorumJudge derives a provider from the
    # part of judge_id before the colon, so local:1 and local:2 collapse to one
    # -- two Ollama models satisfy nothing, and the quorum raises "lacks
    # diversity" on startup. They would not be independent anyway: same box,
    # same RAM, same power cable. One unplugged lead takes out both.
    distinct = {n for n, _, _ in working}
    n_local = sum(1 for n, _, _ in working if n == "local")
    print(f"\n  distinct providers: {len(distinct)}  ({', '.join(sorted(distinct))})")
    if len(distinct) >= 2:
        print( "  Enough for a real quorum -- you can drop `mock` entirely.")
        if len(distinct) >= 3:
            print( "  With three, set min_agree=2. At the default (unanimity) any one")
            print( "  of them being slow blocks every transaction you make.")
    else:
        if n_local > 1:
            print(f"  {n_local} local models, but they are ONE provider as far as the")
            print( "  quorum is concerned, and they share a machine. Keep `mock`")
            print( "  until you add a second real provider somewhere else.")
        else:
            print( "  Only one real provider, so keep `mock` to satisfy the diversity")
            print( "  check. `mock` is keyword matching, not judgment -- replace it.")
    print("=" * 78)


if __name__ == "__main__":
    main()
