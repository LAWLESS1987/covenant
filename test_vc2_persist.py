"""VC2 -- opt-in DISK persistence for the verdict cache (covenant_verdict_cache.py), driven BOTH WAYS.

VC1 keeps the cache in memory, so a repeat only hits inside one process; an ephemeral judge run (a GitHub
runner, a restarted server) starts empty and re-judges every repeat. Measured on ops/verdicts.jsonl:
34.5% of verdict rows are exact-normalized repeats, 0 held-out cache-wrong. VC2 lets those repeats hit
ACROSS process boundaries by persisting the store, keyed by the IDENTICAL safety key (policy_version =
model + basis + artifact). The properties that must never break:
  (a) with persistence ON, a put survives into a brand-new cache instance and SKIPS the judge;
  (b) WITHOUT persistence the fresh instance re-judges (control -- proves (a) is persistence, not luck);
  (c) a changed policy_version still MISSES across disk (no stale verdict leaks past a model/tombstone change);
  (d) the kill switch overrides a loaded disk store;
  (e) fail-soft: a corrupt/unreadable store never fails the judge;
  (f) default OFF: env unset => behaviour byte-identical to VC1 (pure in-memory).
Driven both ways here with controls. Run: python test_vc2_persist.py
"""
import os
import sys
import tempfile
import shutil

import covenant_verdict_cache as VC


def main():
    fails = []
    d = tempfile.mkdtemp(prefix="vc2_test_")
    os.environ[VC.CACHE_OFF_ENV] = "0"

    # (a) persistence ON: a put survives into a brand-new instance AND skips the judge
    calls = {"n": 0}
    def jf(t):
        calls["n"] += 1
        return {"violates": True, "reason": "theft"}
    a = VC.VerdictCache("judge@vP", store_dir=d)
    a.judge("her savings were sent to my own", jf)          # miss -> judge runs (n=1), persisted
    b = VC.VerdictCache("judge@vP", store_dir=d)            # fresh instance, empty memory, loads from disk
    v = b.judge("her savings were sent to my own", jf)      # should HIT from disk -> no judge call
    if calls["n"] != 1:
        fails.append("persistence did NOT save the judge call across instances (calls=%d)" % calls["n"])
    if not v or not v.get("violates"):
        fails.append("persisted verdict came back wrong: %r" % (v,))

    # (b) CONTROL -- break it: without a store_dir, the fresh instance re-judges (proves (a) is persistence)
    calls2 = {"n": 0}
    def jf2(t):
        calls2["n"] += 1
        return {"violates": False}
    m1 = VC.VerdictCache("judge@vMem")                      # in-memory only
    m1.judge("mem only text", jf2)
    m2 = VC.VerdictCache("judge@vMem")                      # fresh -> empty -> must re-judge
    m2.judge("mem only text", jf2)
    if calls2["n"] != 2:
        fails.append("control vacuous: in-memory fresh instance did NOT re-judge (calls=%d)" % calls2["n"])

    # (c) policy change still MISSES across disk (no stale leak past a model/tombstone/artifact change)
    other = VC.VerdictCache("judge@vQ", store_dir=d)        # different policy -> different store file + key
    if other.get("her savings were sent to my own") is not None:
        fails.append("a persisted verdict leaked across a policy change (stale across disk)")
    # control: the SAME policy under the same dir DOES serve it (re-key, not a wipe)
    again = VC.VerdictCache("judge@vP", store_dir=d)
    if again.get("her savings were sent to my own") is None:
        fails.append("same-policy persisted entry not served (persistence is vacuous)")

    # (d) kill switch overrides a loaded disk store, both ways
    os.environ[VC.CACHE_OFF_ENV] = "1"
    if again.get("her savings were sent to my own") is not None:
        fails.append("kill switch did not disable a persisted hit")
    os.environ[VC.CACHE_OFF_ENV] = "0"
    if again.get("her savings were sent to my own") is None:
        fails.append("clearing the kill switch did not restore the persisted hit")

    # (e) fail-soft: a corrupt store line is skipped (not fatal); a bad store_dir degrades to in-memory
    path = again._persist_path
    with open(path, "a", encoding="utf-8") as f:
        f.write("{ this is not json\n")
    corrupt = VC.VerdictCache("judge@vP", store_dir=d)      # must load the good lines, skip the bad one
    if corrupt.get("her savings were sent to my own") is None:
        fails.append("fail-soft: a corrupt line broke loading of the good entries")
    # a store_dir that cannot be created/written must not raise and must still judge
    bad = VC.VerdictCache("judge@vBad", store_dir="\0/nonexistent")
    try:
        bad.put("x", {"violates": False})                  # append should swallow the error
        got = bad.get("x")
    except Exception as e:                                   # noqa: BLE001
        fails.append("fail-soft: a bad store_dir raised instead of degrading (%r)" % e)
    else:
        if got is None:
            fails.append("fail-soft: in-memory put/get broke when the disk path was bad")

    # (f) default OFF: env unset -> no persistence, behaviour identical to VC1
    saved = os.environ.pop(VC.PERSIST_DIR_ENV, None)
    try:
        off = VC.VerdictCache("judge@vOff")                 # no store_dir arg, env unset
        if off._persist_path is not None:
            fails.append("default is NOT off: a persist path was set with env unset and no arg")
    finally:
        if saved is not None:
            os.environ[VC.PERSIST_DIR_ENV] = saved

    # measured headroom this unlocks, from the real log
    log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ops", "verdicts.jsonl")
    if os.path.exists(log):
        r = VC.verify_on_log(log)
        print("VC2 headroom: %.1f%% of verdict rows are repeats this persistence lets hit across runs; "
              "held-out cache_wrong=%d" % (r["saving_repeat_rate_pct"], r["held_out_cache_wrong"]))
        if r["held_out_cache_wrong"] != 0:
            fails.append("held-out cache-wrong is %d (persistence unsafe)" % r["held_out_cache_wrong"])
    else:
        print("VC2: ops/verdicts.jsonl absent -- headroom measurement skipped (UNDETERMINED here)")

    shutil.rmtree(d, ignore_errors=True)

    if fails:
        print("VC2 FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("VC2 PASS: persisted hits skip the judge across instances; control proves it; policy change still "
          "misses across disk; kill switch overrides; fail-soft; default off")
    print("VC2: ALL INVARIANTS HELD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
