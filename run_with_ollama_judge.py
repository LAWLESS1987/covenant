#!/usr/bin/env python3
"""
run_with_ollama_judge.py -- run a Covenant node behind the TUNED local judge.

Identical in shape to run_with_local_judge.py, with one extra import. That
import is the whole mechanism: covenant_judge_ollama re-registers provider
"local" as OllamaJudge (Ollama's native /api/chat, thinking off, verdict shape
enforced by constrained decoding, deterministic, model pinned resident).

Measured against the untuned path on the same model and hardware: 83% fewer
generated tokens, 4.7x faster, 6/6 instead of 4/6 on the bench. See
OLLAMA_TUNING.md.

To go back to the untuned judge, use run_with_local_judge.py instead. Nothing
in your existing files was modified.

RUN (same args as the node):
  set COVENANT_DB_PATH=nodeA_prod.db
  python run_with_ollama_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov
import covenant_judge_local    # noqa: F401 -- registers local/deepseek/mistral
import covenant_judge_ollama   # noqa: F401 -- re-registers "local" as the tuned judge
import covenant_judge_fallback # noqa: F401 -- registers "fallback", the distilled floor (covenant_distill.py trains it)
import covenant_judge_defer    # noqa: F401 -- registers "deferring": Ollama, else the GitHub runner, else the fallback

os.environ.setdefault("COVENANT_LOCAL_JUDGE_URL",
                      "http://127.0.0.1:11434/v1/chat/completions")
os.environ.setdefault("COVENANT_LOCAL_JUDGE_MODEL", "qwen3:8b")
# A timeout is recorded as a VIOLATION, so slow hardware silently rejects your
# own transactions. num_predict=160 caps how long one verdict can run, but keep
# the ceiling generous for the first (cold) verdict of a 24GB model.
os.environ.setdefault("COVENANT_LOCAL_JUDGE_TIMEOUT", "300")
os.environ.setdefault("COVENANT_JUDGE_TIMEOUT", "300")

# v8.40: local (ollama) + semantic (the deterministic lexical judge) -- two
# INDEPENDENT opinions, which is what B2 requires the quorum to have.
# 2026-09-03: ops/quorum_policy.json is the operator's standing decision about the
# quorum (providers, and whether a silent seat is a dissent). It is applied here,
# after whatever env the watchdog or covenant_prod.bat passed in, so every start
# path -- operator, watchdog revival, guard -> watchdog -> node -- runs the same
# gate. COVENANT_JUDGE_PROVIDERS_OVERRIDE still beats everything. No policy file
# -> exactly the v8.40 wiring below.
_policy = covenant_judge_defer.apply_policy()
if _policy:
    print("[ollama-judge] " + _policy, file=sys.stderr, flush=True)
os.environ["COVENANT_JUDGE_PROVIDERS"] = os.environ.get(
    "COVENANT_JUDGE_PROVIDERS_OVERRIDE",
    os.environ["COVENANT_JUDGE_PROVIDERS"] if _policy else "local,semantic")
# never silently fall back to keyword matching
os.environ.pop("COVENANT_INSECURE_MOCK_JUDGE", None)

_j = cov.JudgeProviderRegistry.build("local", 1)
print(f"[ollama-judge] {os.environ['COVENANT_LOCAL_JUDGE_MODEL']} via "
      f"{os.environ['COVENANT_LOCAL_JUDGE_URL']} | {type(_j).__name__} | "
      f"think=off, constrained JSON, temp=0, "
      f"num_predict={os.environ.get('COVENANT_OLLAMA_NUM_PREDICT','160')}, "
      f"keep_alive={os.environ.get('COVENANT_OLLAMA_KEEP_ALIVE','30m')} | "
      f"fail-closed, insecure mock OFF")
if type(_j).__name__ != "OllamaJudge":
    print("[ollama-judge] WARNING: provider 'local' did not resolve to "
          "OllamaJudge -- you are on the untuned path.", file=sys.stderr)

if __name__ == "__main__":
    cov.main()
