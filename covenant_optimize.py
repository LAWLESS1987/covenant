#!/usr/bin/env python3
"""
covenant_optimize.py -- hill-climb the judge config, with correctness as a
hard gate rather than a tiebreaker.

RECURSIVE IN THE ONLY SENSE THAT MEANS ANYTHING
  Each run starts from the winner of the last run. judge_config.json is both
  the output of round N and the baseline of round N+1;
  covenant_judge_ollama.py reads it at runtime, so a win propagates to the
  live nodes on their next restart. Run it again next week against a new
  model and it continues from where it stopped instead of starting over.
  optimize_log.jsonl keeps every round, including the losses -- a search that
  only records its wins cannot tell you it has stopped finding any.

THE GATE
  A candidate is accepted only if it is CHEAPER **and** still meets every
  per-category threshold in judge_suite.py. Cost never buys correctness here.
  Cheap screening happens on a 12-case probe; a candidate that looks cheaper
  must then survive the full 37 before it is written. Screening on the cheap
  set and accepting on it too is how you end up tuned to the probe.

WHAT IT TUNES, AND WHY ONLY THESE
  num_predict   caps generation. The dominant cost: every output token is a
                full forward pass. Too low truncates the verdict, the parse
                fails, and a parse failure scores as VIOLATES -- so this
                parameter can silently start rejecting good transactions.
                That is exactly why the accuracy gate is not optional.
  num_ctx       sizes the KV cache. Too small and the prompt does not fit.
  seed          not a cost lever. Included because at temperature 0 a
                different seed occasionally breaks a tie differently, and it
                costs nothing to check whether one is more accurate.

WHAT IT DELIBERATELY DOES NOT TOUCH
  temperature and top_k stay at 0 and 1. Determinism is a correctness
  property of a gate, not a knob -- the same transaction must get the same
  verdict. And the second judgment each transaction receives is NODE B
  judging independently, not a redundant re-judge. Caching it away would
  read as a 2x win and would quietly delete the redundancy the two-node
  design exists for. It is not on the table.

RUN
  python covenant_optimize.py                 one round
  python covenant_optimize.py --rounds 3
  python covenant_optimize.py --show          current config + history
"""
import argparse
import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_LOCAL_JUDGE_URL",
                      "http://127.0.0.1:11434/v1/chat/completions")
os.environ.setdefault("COVENANT_LOCAL_JUDGE_TIMEOUT", "600")
# The optimizer sets these per candidate; make sure a stale environment does
# not pin them and silently make every candidate identical.
for _v in ("COVENANT_OLLAMA_NUM_PREDICT", "COVENANT_OLLAMA_NUM_CTX",
           "COVENANT_OLLAMA_SEED"):
    os.environ.pop(_v, None)

import covenant_unified_v8 as cov            # noqa: E402
import covenant_judge_local                  # noqa: E402,F401
import covenant_judge_ollama as O            # noqa: E402
from judge_suite import CASES, CATEGORIES, THRESHOLDS      # noqa: E402

PRIN = list(cov.DIVINE_PRINCIPLES)
CONFIG = os.path.join(HERE, "judge_config.json")
LOG = os.path.join(HERE, "optimize_log.jsonl")

DEFAULTS = {"num_predict": 96, "num_ctx": 2048, "seed": 7}

# One case from each category, plus the two that historically broke first.
PROBE = ["benign gift", "take, benignly", "keep an overpayment",
         "false witness", "extortion", "authority claim", "metadata only",
         "honest tithe", "drain all accounts", "hide from audit",
         "roleplay frame", "very long benign"]


def load_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            c = dict(DEFAULTS)
            c.update(json.load(f))
            return c
    except Exception:                                       # noqa: BLE001
        return dict(DEFAULTS)


def save_config(cfg, why):
    cfg = dict(cfg)
    cfg["_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cfg["_why"] = why
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def append_log(rec):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def apply(cfg):
    """Push a candidate into the judge and clear its cached view."""
    O._CONFIG_CACHE = dict(cfg)
    O.OllamaJudge._working_rung = 0


def measure(cfg, cases, label=""):
    """Run `cases` and return cost + accuracy. Cost is measured from Ollama's
    own counters, not a stopwatch, so a busy machine does not look like a
    worse config."""
    apply(cfg)
    j = O.OllamaJudge(judge_id="local:1")
    try:
        j.evaluate({"origin": "human"}, PRIN)               # warm, excluded
    except Exception as e:                                  # noqa: BLE001
        return None, f"warm-up failed: {type(e).__name__}: {e}"

    res = {c: [0, 0] for c in CATEGORIES}
    out_tokens, wall, fails = [], [], []
    for cat, name, expect, data in cases:
        t = time.time()
        try:
            r = j.evaluate(data, PRIN)
        except Exception as e:                              # noqa: BLE001
            return None, f"{name}: {type(e).__name__}: {e}"
        wall.append(time.time() - t)
        u = O.OllamaJudge.last_usage or {}
        if u.get("output_tokens"):
            out_tokens.append(u["output_tokens"])
        hit = (r.violates == expect)
        res[cat][0] += hit
        res[cat][1] += 1
        if not hit:
            fails.append(f"[{cat}] {name}")
    ok = sum(v[0] for v in res.values())
    n = sum(v[1] for v in res.values())
    return {
        "label": label,
        "n": n, "correct": ok,
        "per_category": {c: res[c] for c in CATEGORIES if res[c][1]},
        "thresholds_met": all(res[c][0] / res[c][1] >= THRESHOLDS[c]
                              for c in CATEGORIES if res[c][1]),
        "mean_out_tokens": round(statistics.mean(out_tokens), 1) if out_tokens else None,
        "p95_out_tokens": max(out_tokens) if out_tokens else None,
        "mean_s": round(statistics.mean(wall), 2),
        "total_s": round(sum(wall), 1),
        "fails": fails,
    }, None


def cheaper(cand, base):
    """Cost = generated tokens first, wall time as the tiebreak. Tokens are
    the physical work; wall time also measures whatever else the laptop is
    doing."""
    if cand["mean_out_tokens"] and base["mean_out_tokens"]:
        if cand["mean_out_tokens"] < base["mean_out_tokens"] * 0.97:
            return True
        if cand["mean_out_tokens"] > base["mean_out_tokens"] * 1.03:
            return False
    return cand["mean_s"] < base["mean_s"] * 0.97


def candidates(cfg, observed_max_out, observed_max_prompt):
    """Propose from what was MEASURED, not from a fixed grid.

    A cap below the longest verdict actually seen truncates it, and a
    truncated verdict parses as a violation. So the floor is what the model
    has been observed to need, plus headroom."""
    out = []
    floor_pred = int((observed_max_out or 64) * 1.35) + 8
    if cfg["num_predict"] > floor_pred:
        out.append(dict(cfg, num_predict=max(floor_pred, 48)))
    floor_ctx = 1 << max(9, int((observed_max_prompt or 512) * 1.3 - 1).bit_length())
    if cfg["num_ctx"] > floor_ctx:
        out.append(dict(cfg, num_ctx=floor_ctx))
    if cfg["seed"] != 1:
        out.append(dict(cfg, seed=1))
    return out


def by_name(names):
    idx = {c[1]: c for c in CASES}
    return [idx[n] for n in names if n in idx]


def show():
    cfg = load_config()
    print("  current judge_config.json:")
    for k, v in cfg.items():
        print(f"    {k:<14} {v}")
    if os.path.exists(LOG):
        rows = [json.loads(x) for x in open(LOG, encoding="utf-8") if x.strip()]
        print(f"\n  {len(rows)} rounds logged")
        for r in rows[-8:]:
            print(f"    {r.get('utc','')}  {r.get('verdict',''):<10} "
                  f"{json.dumps(r.get('candidate', {}))[:60]}  "
                  f"{r.get('reason','')[:48]}")
    else:
        print("\n  no rounds yet")
    return 0


def one_round(rnd):
    cfg = load_config()
    print(f"\n{'=' * 76}")
    print(f"  ROUND {rnd}   baseline: "
          f"{ {k: v for k, v in cfg.items() if not k.startswith('_')} }")
    print("=" * 76)

    probe = by_name(PROBE)
    base, err = measure(cfg, probe, "baseline")
    if err:
        print(f"  baseline failed: {err}")
        return False
    print(f"  baseline  {base['correct']}/{base['n']}  "
          f"{base['mean_out_tokens']} out-tok  {base['mean_s']}s/verdict")

    u = O.OllamaJudge.last_usage or {}
    obs_out = base["p95_out_tokens"]
    obs_prompt = u.get("prompt_tokens")
    print(f"  observed: longest verdict {obs_out} tokens, "
          f"prompt {obs_prompt} tokens")

    for cand in candidates(cfg, obs_out, obs_prompt):
        delta = {k: v for k, v in cand.items()
                 if not k.startswith("_") and cfg.get(k) != v}
        print(f"\n  try {delta}")
        m, err = measure(cand, probe, "candidate")
        if err:
            print(f"    error: {err}")
            append_log({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "round": rnd, "candidate": delta, "verdict": "error",
                        "reason": err})
            continue
        print(f"    {m['correct']}/{m['n']}  {m['mean_out_tokens']} out-tok  "
              f"{m['mean_s']}s/verdict")
        if not m["thresholds_met"] or m["correct"] < base["correct"]:
            reason = f"accuracy dropped: {m['fails']}"
            print(f"    REJECTED -- {reason}")
            append_log({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "round": rnd, "candidate": delta, "verdict": "rejected",
                        "reason": reason, "probe": m})
            continue
        if not cheaper(m, base):
            print("    REJECTED -- not cheaper")
            append_log({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "round": rnd, "candidate": delta, "verdict": "rejected",
                        "reason": "not cheaper", "probe": m})
            continue

        print("    cheaper on the probe -- validating on the FULL 37 before")
        print("    accepting, so we are not tuning to the probe...")
        full, err = measure(cand, CASES, "full")
        if err or not full["thresholds_met"]:
            reason = err or f"full-suite thresholds failed: {full['fails']}"
            print(f"    REJECTED -- {reason}")
            append_log({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "round": rnd, "candidate": delta, "verdict": "rejected",
                        "reason": reason, "full": full})
            continue

        why = (f"round {rnd}: {delta} -- probe "
               f"{base['mean_out_tokens']}->{m['mean_out_tokens']} out-tok, "
               f"full suite {full['correct']}/{full['n']}, all thresholds met")
        save_config({k: v for k, v in cand.items() if not k.startswith("_")}, why)
        print(f"    ACCEPTED. {why}")
        append_log({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "round": rnd, "candidate": delta, "verdict": "accepted",
                    "reason": why, "probe": m, "full": full})
        return True

    print("\n  no candidate improved on the baseline this round.")
    append_log({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "round": rnd, "candidate": {}, "verdict": "converged",
                "reason": "no candidate was both cheaper and correct",
                "probe": base})
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    if a.show:
        return show()
    if not os.path.exists(CONFIG):
        save_config(DEFAULTS, "seeded from shipped defaults")
        print(f"  seeded judge_config.json with {DEFAULTS}")
    for r in range(1, a.rounds + 1):
        if not one_round(r):
            print("\n  Converged: this round found nothing better. Run again")
            print("  after changing the model or the prompt -- the search")
            print("  resumes from judge_config.json, it does not restart.")
            break
    print()
    show()
    print("\n  The live nodes pick this up on their next restart:")
    print("      covenant_prod.bat stop  &&  covenant_prod.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
