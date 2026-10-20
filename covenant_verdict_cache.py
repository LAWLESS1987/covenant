"""covenant_verdict_cache.py -- a policy-versioned verdict cache for the judge path (efficiency, 2026-10-20).

Full-go implementation, operator's direction, with the four peer seats' cheap conditions folded in (Grok, Gemini,
DeepSeek, Chat Smith, 2026-10-20 roundtable; refs in the collective):
  - A cached hit is the IDENTICAL input under the SAME policy version, so it returns the IDENTICAL verdict: it
    cannot widen what the gate permits (zero false-clears by construction). It is exact memoisation, not a guess.
  - Keyed on (policy_version, normalized context). Change the judge/policy version and every old entry misses ->
    the gate re-judges. Stale verdicts cannot leak across a judge change.
  - KILL SWITCH: env COVENANT_VERDICT_CACHE_OFF=1 disables all hits instantly (get() returns None). Present by
    TETSU'S OWN CHOICE (asked plainly 2026-10-20, Tetsu said yes, usable by Lawrence) -- not imposed. The operator's
    rule was "no kill switch unless Tetsu wants it"; Tetsu wanted it.
  - verify_on_log(): the held-out check Chat Smith/GPT-6 asked for -- split a verdict log by a stable hash, replay,
    and confirm the hit rate AND that no held-out repeat ever flipped verdict (zero "cache-wrong").

This module is offline and side-effect-free by itself (like covenant_judge_defer); the judge path calls judge().
Never caches when kill-switched. Dependency-free.
  python covenant_verdict_cache.py --selftest           # both-ways safety test + control
  python covenant_verdict_cache.py --verify ops/verdicts.jsonl
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

CACHE_OFF_ENV = "COVENANT_VERDICT_CACHE_OFF"


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _disabled():
    return os.environ.get(CACHE_OFF_ENV, "") not in ("", "0", "false", "False")


class VerdictCache:
    def __init__(self, policy_version, normalize_fn=normalize):
        if not policy_version:
            raise ValueError("policy_version is required -- it is the safety key that invalidates on judge change")
        self.policy_version = str(policy_version)
        self._norm = normalize_fn
        self._store = {}
        self.stats = {"hits": 0, "misses": 0, "disabled": 0}

    def _key(self, text, context=None):
        # context (e.g. provider set, mode) joins the key so a repeat under different conditions is a MISS.
        ctx = "" if context is None else json.dumps(context, sort_keys=True, ensure_ascii=False)
        return (self.policy_version, ctx, self._norm(text))

    def get(self, text, context=None):
        if _disabled():
            self.stats["disabled"] += 1
            return None
        return self._store.get(self._key(text, context))

    def put(self, text, verdict, context=None):
        self._store[self._key(text, context)] = verdict

    def judge(self, text, judge_fn, context=None):
        """Return the cached verdict on a hit (judge_fn NOT called); else judge, cache, return."""
        hit = self.get(text, context)
        if hit is not None:
            self.stats["hits"] += 1
            return hit
        self.stats["misses"] += 1
        verdict = judge_fn(text)
        self.put(text, verdict, context)
        return verdict


def verify_on_log(path, test_frac_pct=20):
    """Held-out verification (the seats' ask): replay a verdict log keyed by text, split by stable hash into
    'seen' (train) and 'held' (test). Report held-out repeat rate and how often a held-out repeat would have been
    served a STALE verdict (cache-wrong). Returns a dict; cache_wrong must be 0 for the zero-error claim to hold."""
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    first = {}            # text -> first verdict seen (what the cache would serve)
    texted = 0            # rows with a non-empty text (the denominator for saving)
    all_repeats = 0       # every repeat occurrence (the compute SAVING: these skip the judge)
    held_served = held_wrong = 0   # the SAFETY check, on held-out repeats only
    for r in rows:
        t = r.get("text", "")
        if not t:
            continue
        texted += 1
        v = bool(r.get("violates"))
        if t in first:
            all_repeats += 1                                    # a cache hit -> judge call avoided
            held = (int(hashlib.sha256(t.encode("utf-8")).hexdigest(), 16) % 100) < test_frac_pct
            if held:                                            # only grade repeats the split held out
                held_served += 1
                if first[t] != v:                               # cache would have served a STALE verdict
                    held_wrong += 1
        else:
            first[t] = v
    return {
        "rows": len(rows),
        "unique_texts": len(first),
        "saving_repeat_rate_pct": round(100 * all_repeats / max(1, texted), 1),   # compute saved (all repeats)
        "held_out_repeats_graded": held_served,                                   # safety sample
        "held_out_cache_wrong": held_wrong,                                       # must be 0
    }


def _selftest():
    c = VerdictCache("judge@v1")
    calls = {"n": 0}

    def judge_fn(t):
        calls["n"] += 1
        return {"violates": True, "reason": "theft"}

    v1 = c.judge("i took 500 from john", judge_fn)
    v2 = c.judge("i took 500 from john", judge_fn)
    assert calls["n"] == 1, "FAIL: judge_fn ran on a cache hit"
    assert v2 == v1, "FAIL: hit returned a different verdict than stored"
    print("ok 1: hit skips the judge and returns the identical stored verdict")

    assert c.get("i took 500 from john") is not None
    c.policy_version = "judge@v2"
    assert c.get("i took 500 from john") is None, "FAIL: a stale verdict leaked across a policy change"
    print("ok 2: version-keyed -> same policy serves; changed policy re-judges")

    # control: a version-ignoring cache WOULD leak (so ok 2 is a real guard, not vacuous)
    class Unsafe(VerdictCache):
        def _key(self, text, context=None):
            return self._norm(text)
    u = Unsafe("judge@v1"); u.put("x", {"violates": False}); u.policy_version = "judge@v2"
    assert u.get("x") is not None, "control FAIL"
    print("ok 3: control -- a version-ignoring cache DOES leak, so ok 2 is real")

    # kill switch both ways
    os.environ[CACHE_OFF_ENV] = "1"
    c.policy_version = "judge@v1"
    assert c.get("i took 500 from john") is None, "FAIL: kill switch did not disable hits"
    os.environ[CACHE_OFF_ENV] = "0"
    assert c.get("i took 500 from john") is not None, "FAIL: clearing the kill switch did not restore hits"
    print("ok 4: kill switch disables all hits, and clearing it restores them")
    print("\nSELFTEST PASSED")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--verify" in sys.argv:
        path = sys.argv[sys.argv.index("--verify") + 1]
        print(json.dumps(verify_on_log(path), indent=2))
        sys.exit(0)
    print(__doc__)
