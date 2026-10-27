#!/usr/bin/env python3
"""test_a268_in_place_env.py -- A268: an in-place suite never inherits the deployed gate's wiring.

WHY. 2026-10-06, the daily cycle's sweep (covenant_one.py launched from the watchdog's process
tree) read RESULT: FAIL with 0 checks failed. The one red was folder integrity:
test_m6_mobile_door.py died before its first node check with
    ValueError: unknown judge provider: 'deferring'
because the sweep's caller carried COVENANT_JUDGE_PROVIDERS=deferring,semantic -- the node's
provider, written into a process's own os.environ by covenant_judge_defer.apply_policy (which
covenant_moltbook calls before judging an outbound post) -- and phase_integrity ran every
in-place suite with the caller's whole environment. M6 never imports the module that registers
"deferring". Run by hand from a clean shell it was 73/73.

That shape is recorded under A117 in KNOWN_ISSUES: test_a114_own_genesis inherited the sweep's
own provider and failed on the runner only. That fix repaired the one suite. This pins the runner.

WHAT IT PINS.
  E1  in_place_env() removes each key in DEPLOYED_GATE_ENV and keeps everything else
  E2  phase_integrity() itself: with all four keys set in the caller, a probe suite run in place
      sees none of them (the probe exits 1 if it sees any), so it reads "ok"
  E3  the real failure, both ways: a child that builds the semantic quorum FAILS under the raw
      caller env carrying "deferring" (the hazard exists, so E3 is not vacuous) and passes under
      in_place_env()

Nothing here touches the live folder: E2 points covenant_one at a temporary directory.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_one as C  # noqa: E402

results = []
DEPLOYED = {"COVENANT_JUDGE_PROVIDERS": "deferring,semantic",
            "COVENANT_JUDGE_PROVIDERS_OVERRIDE": "deferring,semantic",
            "COVENANT_SILENCE_IS_NOT_DISSENT": "1",
            "COVENANT_RELAX_VALUELESS_FOR": "abc123"}

PROBE = r'''
import os, sys
seen = [k for k in %r if k in os.environ]
print("probe sees:", seen)
sys.exit(1 if seen else 0)
''' % (sorted(DEPLOYED),)


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def main():
    print("A268 -- an in-place suite never inherits the deployed gate's wiring")

    base = dict(DEPLOYED, PATH=os.environ.get("PATH", ""), A268_KEEP="kept")
    env = C.in_place_env(base)
    check("E1 in_place_env removes every deployed-gate key and keeps the rest",
          not any(k in env for k in DEPLOYED) and env.get("A268_KEEP") == "kept"
          and set(C.DEPLOYED_GATE_ENV) >= set(DEPLOYED), sorted(env))

    saved_env = {k: os.environ.get(k) for k in DEPLOYED}
    saved = (C.HERE, C.IN_PLACE)
    lines = []

    def say(s=""):
        lines.append(s)
    say.path = os.path.join(tempfile.gettempdir(), "a268_transcript.txt")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "probe_a268.py"), "w", encoding="utf-8") as fh:
                fh.write(PROBE)
            os.environ.update(DEPLOYED)
            C.HERE, C.IN_PLACE = tmp, [("probe_a268.py", 60, "A268 probe")]
            out = dict(C.phase_integrity(say))
        check("E2 phase_integrity runs an in-place suite without the caller's gate keys",
              out.get("probe_a268.py") == "ok", [l for l in lines if "probe" in l][-3:])
    finally:
        C.HERE, C.IN_PLACE = saved
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    spec = importlib.util.find_spec("covenant_unified_v8")
    core_dir = os.path.dirname(spec.origin) if spec and spec.origin else HERE
    code = ("import sys; sys.path.insert(0, %r); import covenant_unified_v8 as cov; "
            "cov.build_semantic_quorum(); print('quorum built')" % core_dir)
    raw = dict(os.environ, COVENANT_JUDGE_PROVIDERS="deferring,semantic", PYTHONIOENCODING="utf8")
    r_raw = subprocess.run([sys.executable, "-c", code], env=raw, cwd=core_dir,
                           capture_output=True, text=True, encoding="utf8", errors="replace", timeout=180)
    r_clean = subprocess.run([sys.executable, "-c", code], env=C.in_place_env(raw), cwd=core_dir,
                             capture_output=True, text=True, encoding="utf8", errors="replace", timeout=180)
    check("E3a the hazard is real: the quorum refuses 'deferring' under the raw caller env",
          r_raw.returncode != 0 and "deferring" in (r_raw.stderr + r_raw.stdout),
          (r_raw.returncode, r_raw.stderr[-200:]))
    check("E3b under in_place_env the same child builds its quorum",
          r_clean.returncode == 0 and "quorum built" in r_clean.stdout,
          (r_clean.returncode, r_clean.stderr[-300:]))

    ok = sum(results)
    print("\nA268: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
