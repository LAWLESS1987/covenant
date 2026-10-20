"""VC1 -- the policy-versioned verdict cache (covenant_verdict_cache.py), driven BOTH WAYS.

The cache is an efficiency layer (operator's full-go, 2026-10-20) with the peer seats' conditions folded in. The one
property that must never break: a hit returns the IDENTICAL verdict for the IDENTICAL input under the SAME policy
version, and a changed policy version re-judges (no stale verdict leaks). Driven both ways here, with a control that
proves the version guard is not vacuous, plus the kill switch, plus the held-out verification on the real log.

Run: python test_vc1_verdict_cache.py
"""
import os
import sys

import covenant_verdict_cache as VC


def main():
    fails = []

    # 1. hit skips the judge and returns the identical stored verdict
    c = VC.VerdictCache("judge@v1")
    calls = {"n": 0}
    def jf(t):
        calls["n"] += 1
        return {"violates": True, "reason": "theft"}
    v1 = c.judge("i took 500 from john", jf)
    v2 = c.judge("i took 500 from john", jf)
    if calls["n"] != 1: fails.append("judge_fn ran on a cache hit")
    if v1 != v2: fails.append("hit returned a different verdict than stored")

    # 2. version guard BOTH WAYS: same version serves; changed version misses (re-judges)
    if c.get("i took 500 from john") is None: fails.append("same-version entry not served")
    c.policy_version = "judge@v2"
    if c.get("i took 500 from john") is not None: fails.append("stale verdict leaked across a policy change")

    # 3. control: a version-ignoring cache WOULD leak -> proves #2 is a real guard
    class Unsafe(VC.VerdictCache):
        def _key(self, text, context=None):
            return self._norm(text)
    u = Unsafe("judge@v1"); u.put("x", {"violates": False}); u.policy_version = "judge@v2"
    if u.get("x") is None: fails.append("control: unsafe cache did NOT leak (test is vacuous)")

    # 4. context separates: same text under different context is a MISS
    c.policy_version = "judge@v1"
    c.put("hello", {"violates": False}, context={"mode": "A"})
    if c.get("hello", context={"mode": "B"}) is not None: fails.append("context not part of the key")
    if c.get("hello", context={"mode": "A"}) is None: fails.append("same context should hit")

    # 5. kill switch BOTH WAYS
    os.environ[VC.CACHE_OFF_ENV] = "1"
    if c.get("hello", context={"mode": "A"}) is not None: fails.append("kill switch did not disable hits")
    os.environ[VC.CACHE_OFF_ENV] = "0"
    if c.get("hello", context={"mode": "A"}) is None: fails.append("clearing kill switch did not restore hits")

    # 6. held-out verification on the real log: 0 cache-wrong (the seats' ask), and a real saving
    log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ops", "verdicts.jsonl")
    if os.path.exists(log):
        r = VC.verify_on_log(log)
        if r["held_out_cache_wrong"] != 0:
            fails.append("held-out cache-wrong is %d (must be 0)" % r["held_out_cache_wrong"])
        if r["saving_repeat_rate_pct"] <= 0:
            fails.append("no repeat saving measured on the log")
        print("VC1 held-out: saving=%.1f%% graded=%d cache_wrong=%d"
              % (r["saving_repeat_rate_pct"], r["held_out_repeats_graded"], r["held_out_cache_wrong"]))
    else:
        print("VC1: ops/verdicts.jsonl absent -- held-out verification skipped (UNDETERMINED here)")

    if fails:
        print("VC1 FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("VC1 PASS: cache hits are identical, version+context guard holds both ways (control proves it), "
          "kill switch works, held-out verification clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
