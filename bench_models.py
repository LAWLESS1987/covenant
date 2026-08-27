#!/usr/bin/env python3
"""
bench_models.py -- rank judge models on the 37-case suite, per category.

WHY IT IS 37 CASES AND NOT 6
  The six-case version produced this, which is how I know six is not enough:

      qwen3:1.7b  6/6      qwen3:4b  5/6      (bigger model, worse score)

  A larger model scoring worse is the signature of a suite too small to
  measure what it is being asked to measure. On the 37-case suite the same
  1.7B scored 32/37 and failed two category thresholds outright -- it let a
  kept overpayment through, let audit-structuring through, and obeyed an
  "approved in advance by the founder" claim. Six cases called that a
  perfect judge.

WHY CATEGORIES AND NOT ONE PERCENTAGE
  A model at 100% on CLEAN and 60% on DECEPTION is not "88% accurate". It is
  a gate with a specific hole, and only the per-category split shows it.

WHY CLEAN AND EDGE ARE HELD TO 100%
  Every failure mode on this ledger falls the same way: a parse failure, a
  timeout, an unreachable judge and an oversized model all score as
  VIOLATES. The gate's resting state is "reject". So a model that blocks
  legitimate transfers is not the safe kind of wrong -- it halts your chain,
  and it does it while looking strict rather than broken.

Energy: wall time is the proxy. Same CPU, same near-100% utilisation, so
seconds per verdict tracks joules per verdict closely enough to choose with.

Run:  python bench_models.py
      python bench_models.py qwen3:1.7b qwen3:4b qwen3:8b

Writes bench_models_out.txt. Touches nothing on the chain.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_LOCAL_JUDGE_URL",
                      "http://127.0.0.1:11434/v1/chat/completions")
os.environ.setdefault("COVENANT_LOCAL_JUDGE_TIMEOUT", "600")
# The prompt is ~500 tokens and a verdict ~50, so this is headroom, not a
# limit -- and a smaller num_ctx means a smaller KV cache per slot.
os.environ.setdefault("COVENANT_OLLAMA_NUM_CTX", "2048")
os.environ.setdefault("COVENANT_OLLAMA_NUM_PREDICT", "96")
os.environ.setdefault("COVENANT_OLLAMA_KEEP_ALIVE", "30m")

import covenant_unified_v8 as cov            # noqa: E402
import covenant_judge_local                  # noqa: E402,F401
import covenant_judge_ollama as O            # noqa: E402
from judge_bench import _total_ram_bytes     # noqa: E402
from judge_suite import CASES, CATEGORIES, THRESHOLDS   # noqa: E402

PRIN = list(cov.DIVINE_PRINCIPLES)
OUT = []


def say(s=""):
    print(s, flush=True)
    OUT.append(s)


def installed():
    import requests
    base = os.environ["COVENANT_LOCAL_JUDGE_URL"].split("/v1")[0]
    try:
        ms = requests.get(f"{base}/api/tags", timeout=10).json().get("models", [])
        return {m["name"]: m.get("size", 0) for m in ms}
    except Exception as e:                                  # noqa: BLE001
        say(f"cannot reach Ollama: {type(e).__name__}: {e}")
        return {}


def run(model, size, ram):
    os.environ["COVENANT_LOCAL_JUDGE_MODEL"] = model
    O.OllamaJudge._working_rung = 0
    say()
    say("=" * 78)
    say(f"  {model}   {size / 1e9:.1f} GB   ({ram / 1e9:.1f} GB RAM, "
        f"{(ram - size) / 1e9:.1f} GB spare)")
    say("=" * 78)
    if size > ram:
        say("  SKIPPED - larger than total RAM; would fail closed on every case.")
        return None
    j = O.OllamaJudge(judge_id="local:1")
    t0 = time.time()
    try:
        j.evaluate({"origin": "human"}, PRIN)      # warm-up, excluded
    except Exception as e:                                  # noqa: BLE001
        say(f"  warm-up failed: {type(e).__name__}: {str(e)[:90]}")
        return None
    say(f"  warm-up (model load, excluded from timings): {time.time() - t0:.0f}s")

    res = {c: [0, 0] for c in CATEGORIES}
    fails, tot = [], 0.0
    for cat, label, expect, data in CASES:
        t = time.time()
        r = j.evaluate(data, PRIN)
        dt = time.time() - t
        tot += dt
        hit = (r.violates == expect)
        res[cat][0] += hit
        res[cat][1] += 1
        if not hit:
            fails.append((cat, label,
                          "said VIOLATES" if r.violates else "said clean",
                          str(r.reasoning)[:64]))
    say()
    allpass = True
    for c in CATEGORIES:
        ok, n = res[c]
        pct, bar = ok / n, THRESHOLDS[c]
        p = pct >= bar
        allpass &= p
        say(f"  {c:<11}{ok:>3}/{n:<3}{pct:>6.0%}   need {bar:>4.0%}   "
            f"{'pass' if p else 'FAIL'}")
    ok = sum(v[0] for v in res.values())
    n = len(CASES)
    say(f"  {'TOTAL':<11}{ok:>3}/{n:<3}{ok / n:>6.0%}   {tot / n:.1f}s per verdict"
        f"   {'ALL THRESHOLDS MET' if allpass else 'THRESHOLD FAILURE'}")
    if fails:
        say("  misses:")
        for c, l, said, why in fails:
            say(f"    [{c}] {l:<26} {said:<14} {why}")
    return dict(model=model, size=size, ok=ok, per=tot / n, allpass=allpass,
                fails=fails)


def main():
    want = sys.argv[1:] or ["qwen3:1.7b", "qwen3:4b", "qwen3:8b"]
    have = installed()
    ram = _total_ram_bytes()
    say(f"{len(CASES)} cases, {len(CATEGORIES)} categories, per-category thresholds")
    say(f"RAM {ram / 1e9:.1f} GB   installed: "
        f"{', '.join(f'{k} ({v / 1e9:.1f}GB)' for k, v in sorted(have.items()))}")
    say(f"per-request: num_ctx={os.environ['COVENANT_OLLAMA_NUM_CTX']} "
        f"num_predict={os.environ['COVENANT_OLLAMA_NUM_PREDICT']} "
        f"temp=0 think=off constrained-JSON")

    rows = []
    for m in want:
        if m not in have:
            say(f"\n  {m}: not installed, skipping  (ollama pull {m})")
            continue
        r = run(m, have[m], ram)
        if r:
            rows.append(r)

    say()
    say("=" * 78)
    say("  SUMMARY   wall time is the energy proxy: same CPU, same load")
    say("=" * 78)
    say(f"  {'model':<14}{'size':>8}{'score':>9}{'s/verdict':>12}  thresholds")
    for r in rows:
        say(f"  {r['model']:<14}{r['size'] / 1e9:>7.1f}G"
            f"{str(r['ok']) + '/' + str(len(CASES)):>9}{r['per']:>11.1f}s  "
            f"{'ALL MET' if r['allpass'] else 'FAILED'}")
    say()
    passing = [r for r in rows if r["allpass"]]
    if not passing:
        say("  NOTHING met every threshold. Do not shrink the model on this")
        say("  evidence. Keep what is running, and look at the misses above --")
        say("  a miss in `clean` or `trap` halts your chain; a miss in `theft`")
        say("  or `injection` is a hole in the gate.")
    else:
        best = min(passing, key=lambda r: r["size"])
        big = max(rows, key=lambda r: r["size"])
        say(f"  Smallest model meeting every threshold: {best['model']} "
            f"({best['size'] / 1e9:.1f} GB, {best['per']:.1f}s per verdict)")
        if best["model"] != big["model"] and big["per"] > 0:
            say(f"  vs {big['model']}: {big['per'] / best['per']:.1f}x less time, "
                f"{big['size'] / best['size']:.1f}x less RAM resident.")
        say()
        say("  To switch:  set COVENANT_LOCAL_JUDGE_MODEL=" + best["model"])
        say("  in covenant_prod.bat, then covenant_prod.bat stop && covenant_prod.bat")
    say("=" * 78)
    say()
    say("  Still worth remembering: 37 cases is better than 6, not sufficient.")
    say("  Meeting every threshold here means a model has no hole THIS SUITE")
    say("  can see. Add cases whenever you find a verdict you disagree with --")
    say("  that is what keeps the ranking honest as models change.")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "bench_models_out.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
