#!/usr/bin/env python3
"""
run_node.py -- run a Covenant node behind the ethics gate it ships with.

What this file does is register the judge seats and apply the operator's
standing policy before the node starts: it imports the judge modules (each
import IS a registration), applies ops/quorum_policy.json over whatever the
environment said, falls back to "deferring,semantic" when there is no policy
(A93, 2026-09-12), prints one line naming what judges, and hands off to the
node's own main(). The seats are the two distilled students under the
"deferring" provider and the deterministic semantic judge; no model server is
assumed, and none is reached.

HISTORY. Until 2026-09-12 this file was run_with_ollama_judge.py, named for a
local model server that was removed from this PC on 2026-09-07 and from the
ethics quorum by policy before that. A one-line shim keeps the old name for one
release, because the watchdog, the restart scripts and the running processes
identified nodes by it. Nothing in the node changed with the name.

RUN (same args as the node):
  set COVENANT_DB_PATH=nodeA_prod.db
  python run_node.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov
import covenant_judge_local    # noqa: F401 -- registers local/deepseek/mistral
import covenant_judge_ollama   # noqa: F401 -- re-registers "local" as the tuned judge
import covenant_judge_fallback # noqa: F401 -- registers "fallback", the distilled floor (covenant_distill.py trains it)
import covenant_judge_defer    # noqa: F401 -- registers "deferring": Ollama, else the GitHub runner, else the fallback

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
# gate. COVENANT_JUDGE_PROVIDERS_OVERRIDE still beats everything.
#
# NO POLICY FILE -> "deferring,semantic". Decided by the operator 2026-09-12
# ("change the fallback to deferring,semantic"), closing A93. The line used to
# say "local,semantic" under a comment reading "exactly the v8.40 wiring below",
# which was true on 2026-08-29 and false from 2026-09-07, the day Ollama was
# deleted: provider "local" is OllamaJudge, so every CLONE -- the phone kit, a
# second operator -- came up with its first semantic seat pointed at a model
# server it did not run, while this PC never noticed because its gitignored
# ops/quorum_policy.json said deferring,semantic all along. "deferring" is the
# seat that never goes empty (students -> runner -> fallback); with no policy
# it is the only default that judges on a fresh clone. The environment is still
# discarded when there is no policy, deliberately: a clone's gate must not
# depend on what a shell happened to export. Measured before/after in
# test_a93_clone_seats_the_student.py.
_policy = covenant_judge_defer.apply_policy()
if _policy:
    print("[node] " + _policy, file=sys.stderr, flush=True)
os.environ["COVENANT_JUDGE_PROVIDERS"] = os.environ.get(
    "COVENANT_JUDGE_PROVIDERS_OVERRIDE",
    os.environ["COVENANT_JUDGE_PROVIDERS"] if _policy else "deferring,semantic")
# never silently fall back to keyword matching
os.environ.pop("COVENANT_INSECURE_MOCK_JUDGE", None)

# THE BOOT BANNER NAMES WHAT JUDGES (A39 asked for exactly this; 2026-09-12).
# It used to print a model tag and a URL on port 11434 -- a server deleted from
# this PC on 2026-09-07 -- and assert that provider "local" resolved to that
# server's class. What judges is the distilled student, so that is what the
# line says: its name and digest, read from the model file the node will use.
# dashboard_render.judge_model() reads this line.
try:
    import covenant_judge_fallback as _FB
    _student = "%s@%s" % (
        (_FB.FallbackJudge.STUDENTS.get(os.path.basename(_FB.MODEL_PATH)) or ("student",))[0],
        _FB.FallbackModel.load().digest)
except Exception as _e:                                          # noqa: BLE001
    _student = "unloaded (%s)" % type(_e).__name__
print(f"[node] providers={os.environ['COVENANT_JUDGE_PROVIDERS']} | student {_student} | "
      f"policy: {'ops/quorum_policy.json' if _policy else 'none (launcher default)'} | "
      f"fail-closed, insecure mock OFF", flush=True)

if __name__ == "__main__":
    cov.main()
