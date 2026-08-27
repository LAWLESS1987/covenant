#!/usr/bin/env python3
"""
run_with_local_judge.py -- run a Covenant node whose ethics gate is a LOCAL
model served by Ollama (or any OpenAI-compatible endpoint), instead of an API
key or the insecure mock.

WHY THIS FILE EXISTS
  covenant_judge_local.py registers the "local", "deepseek" and "mistral"
  providers at import time (its last three lines). covenant_unified_v8.py never
  imports it. So starting the node with COVENANT_JUDGE_PROVIDERS=local -- the
  wiring OLLAMA_JUDGE.md section 2 tells you to use -- dies at startup with:

      ValueError: unknown judge provider: 'local'
                  (known: ['claude', 'google', 'mock', 'openai'])

  Nothing was wrong with the judge itself; it was simply never reachable from
  the node. This launcher imports the module first, exactly the way
  run_with_claude_judge.py does for its own provider, and then hands off to the
  normal node main().

RUN (same args as the node):
  set COVENANT_DB_PATH=nodeA_prod.db
  python run_with_local_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov
import covenant_judge_local  # noqa: F401 -- the import IS the registration

# Defaults that match OLLAMA_JUDGE.md. Anything already set in the environment
# wins, so start_live_local.bat / your own exports still control this.
os.environ.setdefault("COVENANT_LOCAL_JUDGE_URL",
                      "http://localhost:11434/v1/chat/completions")
os.environ.setdefault("COVENANT_LOCAL_JUDGE_MODEL", "qwen3.6:latest")
# A timeout is recorded as a VIOLATION, so slow hardware silently rejects your
# own transactions. Keep this generous -- see OLLAMA_JUDGE.md section 3.
os.environ.setdefault("COVENANT_LOCAL_JUDGE_TIMEOUT", "300")
os.environ.setdefault("COVENANT_JUDGE_TIMEOUT", "300")

os.environ["COVENANT_JUDGE_PROVIDERS"] = os.environ.get(
    "COVENANT_JUDGE_PROVIDERS_OVERRIDE", "local")
# never silently fall back to keyword matching
os.environ.pop("COVENANT_INSECURE_MOCK_JUDGE", None)

print(f"[local-judge] {os.environ['COVENANT_LOCAL_JUDGE_MODEL']} via "
      f"{os.environ['COVENANT_LOCAL_JUDGE_URL']} "
      f"(timeout {os.environ['COVENANT_LOCAL_JUDGE_TIMEOUT']}s, fail-closed, "
      f"insecure mock OFF)")

if __name__ == "__main__":
    cov.main()
