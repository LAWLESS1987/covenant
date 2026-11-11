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

    # 7. WIRING: the cache is wired into the expensive judge (OpenAICompatJudge._call) -- an identical judgment
    #    skips the LLM POST, and Tetsu's kill switch forces a fresh POST. Driven both ways. Skipped where the judge
    #    stack can't import here (UNDETERMINED), run in the sweep where it can.
    try:
        import covenant_judge_local as JL
        import requests
    except Exception:                                    # noqa: BLE001
        print("VC1 judge-wiring: covenant_judge_local unavailable here -- wiring check skipped (UNDETERMINED)")
    else:
        class _Stub(JL.OpenAICompatJudge):
            def __init__(self): pass
            api_key = "local-no-key"
            def _build_prompt(self, data, principles): return "P::" + str(data)
            def _model(self): return "stub"
            def _endpoint(self): return "http://x"
            def _parse_verdict(self, content): return ("verdict", content)
        posts = {"n": 0}
        _orig = requests.post
        def _fake(url, headers=None, json=None, timeout=None):
            posts["n"] += 1
            class R:
                def raise_for_status(self): pass
                def json(self): return {"choices": [{"message": {"content": "ok"}}]}
            return R()
        requests.post = _fake
        try:
            JL._VC_CACHES.clear(); os.environ[VC.CACHE_OFF_ENV] = "0"
            st = _Stub()
            st._call({"text": "c"}, ["p"]); st._call({"text": "c"}, ["p"])
            if posts["n"] != 1: fails.append("judge wiring: identical judgment re-POSTed (posts=%d)" % posts["n"])
            os.environ[VC.CACHE_OFF_ENV] = "1"; st._call({"text": "c"}, ["p"])
            if posts["n"] != 2: fails.append("judge wiring: kill switch did not force a fresh POST")
            os.environ[VC.CACHE_OFF_ENV] = "0"
            if not fails:
                print("VC1 judge-wiring: identical judgment served from cache; kill switch forces a fresh POST")
        finally:
            requests.post = _orig

    # 8. BASIS INVALIDATION BOTH WAYS (gap #4, council 2026-10-21): a changed tombstone/amendment ledger
    #    bumps the basis hash -> the judge cache re-keys -> prior verdicts miss and re-judge. No exemption.
    import tempfile
    d = tempfile.mkdtemp()
    led = os.path.join(d, "RETRACTED.json")
    open(led, "w", encoding="utf-8").write('{"a": 1}')
    VC._BASIS_MEMO.clear(); h1 = VC.basis_version([led])
    h1b = VC.basis_version([led])
    if h1 == "none" or h1 != h1b: fails.append("basis_version unstable on an unchanged ledger (%r/%r)" % (h1, h1b))
    # A416 (Codex's PR #9 finding): a same-size rewrite with its mtime restored is a new basis, not the memoised one.
    preserved = os.stat(led)
    open(led, "w", encoding="utf-8").write('{"a": 9}')
    os.utime(led, ns=(preserved.st_atime_ns, preserved.st_mtime_ns))
    if VC.basis_version([led]) == h1:
        fails.append("basis_version reused stale bytes after a same-size preserved-mtime replacement (A416)")
    open(led, "w", encoding="utf-8").write('{"a": 2, "tombstone": "x"}')   # a tombstone lands
    VC._BASIS_MEMO.clear(); h2 = VC.basis_version([led])
    if h2 == h1: fails.append("basis_version did NOT change when the ledger changed (gap #4 open)")
    os.remove(led); VC._BASIS_MEMO.clear()
    if VC.basis_version([led]) != "none": fails.append("absent ledger should hash to 'none'")

    try:
        import covenant_judge_local as JL2
    except Exception:                                    # noqa: BLE001
        print("VC1 basis-wiring: covenant_judge_local unavailable here -- skipped (UNDETERMINED)")
    else:
        _origbasis = VC.basis_version
        try:
            JL2._VC_CACHES.clear()
            VC.basis_version = lambda *a, **k: "AAAA"
            ca = JL2._verdict_cache("m"); cb = JL2._verdict_cache("m")
            if ca is not cb: fails.append("basis-wiring: same basis made a new cache (hits lost needlessly)")
            ca.put("ONLY-UNDER-AAAA", {"violates": True})
            VC.basis_version = lambda *a, **k: "BBBB"     # a tombstone lands -> basis changes
            cc = JL2._verdict_cache("m")
            if cc is ca: fails.append("basis-wiring: basis change did NOT re-key the cache (gap #4 open)")
            if "BBBB" not in cc.policy_version: fails.append("basis-wiring: new basis not in the policy key")
            if cc.get("ONLY-UNDER-AAAA") is not None:
                fails.append("basis-wiring: a verdict survived a basis change (stale leaked past a tombstone)")
            VC.basis_version = lambda *a, **k: "AAAA"      # control: same basis serves the old entry (re-key, not a wipe)
            if JL2._verdict_cache("m").get("ONLY-UNDER-AAAA") is None:
                fails.append("basis-wiring control: same-basis entry not served (re-key is vacuous)")
            if not any("basis-wiring" in f for f in fails):
                print("VC1 basis-wiring: a changed tombstone ledger re-keys the judge cache; stale cannot leak past a correction")
        finally:
            VC.basis_version = _origbasis
            JL2._VC_CACHES.clear()

    # 9. CANARY BOTH WAYS (gap #2, council 2026-10-21): OFF by default (no sampling, no judge-call cost); when
    #    switched on it logs real-turn agreement and catches a real-turn cache-wrong. Observational only.
    if VC.should_canary(VC.canary_pct()):                # env unset -> pct 0 -> must be False
        fails.append("canary is ON by default (must be opt-in -- it spends a judge call per sampled hit)")
    if VC.should_canary(0): fails.append("should_canary(0) returned True")
    if not VC.should_canary(100, r=0.5): fails.append("should_canary(100) did not fire")
    if VC.should_canary(2, r=0.99): fails.append("should_canary(2) fired at r=0.99")
    if not VC.should_canary(2, r=0.0): fails.append("should_canary(2) did not fire at r=0.0")
    clog = os.path.join(d, "canary.jsonl")
    if not VC.record_canary(clog, "m", "t1", {"violates": True}, {"violates": True}):
        fails.append("canary: identical verdicts recorded as a disagreement")
    if VC.record_canary(clog, "m", "t2", {"violates": False}, {"violates": True}):
        fails.append("canary: a real-turn FLIP recorded as agree (a cache-wrong would be missed)")
    rep = VC.canary_report(clog)
    if rep["checked"] != 2 or rep["real_turn_cache_wrong"] != 1:
        fails.append("canary_report wrong: %r" % rep)
    if not any("canary" in f for f in fails):
        print("VC1 canary: off by default; when on, logs real-turn agreement and catches a real-turn cache-wrong")
    import shutil; shutil.rmtree(d, ignore_errors=True)

    # 10. ARTIFACT INVALIDATION BOTH WAYS (A383): a SAME-NAME change -- a swapped endpoint, or new bytes under the
    #     same local model file -- re-keys the judge cache so a stale verdict cannot leak; an unchanged artifact
    #     serves; a name with no local file folds a stable 'artifact=unknown' (no regression). Closes the fail-open
    #     corner Codex's model-replacement study found and Claude reproduced.
    import tempfile as _tf
    md = _tf.mkdtemp()
    mp = os.path.join(md, "m.gguf"); open(mp, "wb").write(b"x" * 100)
    a1 = VC.artifact_version("m", endpoint="http://a/v1", models_dir=md)
    # A416 (Codex's PR #9 finding): a same-size rewrite with its mtime restored re-keys; restoring the bytes restores
    # the key (content identity, not metadata).
    preserved_model = os.stat(mp)
    open(mp, "wb").write(b"y" * 100)
    os.utime(mp, ns=(preserved_model.st_atime_ns, preserved_model.st_mtime_ns))
    if VC.artifact_version("m", endpoint="http://a/v1", models_dir=md) == a1:
        fails.append("artifact_version reused stale bytes after a same-size preserved-mtime replacement (A416)")
    open(mp, "wb").write(b"x" * 100)
    os.utime(mp, ns=(preserved_model.st_atime_ns, preserved_model.st_mtime_ns))
    if a1 != VC.artifact_version("m", endpoint="http://a/v1", models_dir=md):
        fails.append("artifact_version unstable on an unchanged artifact")
    if VC.artifact_version("m", endpoint="http://b/v1", models_dir=md) == a1:
        fails.append("artifact_version did NOT change on a changed endpoint (same name) -- fail-open gap open")
    open(mp, "wb").write(b"x" * 200)                      # new bytes under the same name
    if VC.artifact_version("m", endpoint="http://a/v1", models_dir=md) == a1:
        fails.append("artifact_version did NOT change when the local model file changed (same name)")
    an = VC.artifact_version("nosuch", endpoint="http://a/v1", models_dir=md)
    if "artifact=unknown" not in an:
        fails.append("unresolvable artifact did not fold a stable marker")
    if VC.artifact_version("nosuch", endpoint="http://a/v1", models_dir=md) != an:
        fails.append("unresolvable artifact not stable across calls (would needlessly miss)")
    # A416: a name that is not a regular file here (an endpoint tag, a name Windows rejects with EINVAL, a directory)
    # stays 'unknown' as before -- never 'unreadable', which would switch the cache off for a remote model.
    os.mkdir(os.path.join(md, "adir.gguf"))
    for odd in ("qwen3:8b", "a?b", "adir"):
        if "artifact=unknown" not in VC.artifact_version(odd, endpoint="http://a/v1", models_dir=md):
            fails.append("non-file model name %r did not fold 'artifact=unknown' (A416)" % odd)

    # 10b. A416 MEMO, BOTH WAYS. Measured 2026-11-07 on the PC: a full SHA-256 of a 2.10 GB GGUF took 1.30-2.14 s per
    #      lookup, so the digest is memoised against a change stamp. Driven here: the hash is paid once for an aged,
    #      unchanged file; an in-place same-size rewrite with mtime restored IS seen (the stamp's change time moves);
    #      a just-written file is never memoised (racy window); strict mode rehashes every time; a file seen changing
    #      mid-read is 'unstable'.
    import time as _time
    hashes = [0]
    _orig_hash, _orig_stamp, _orig_racy = VC._hash_open_file, VC._change_stamp, VC._RACY_NS

    def _counting_hash(f):
        hashes[0] += 1
        return _orig_hash(f)

    def av():
        return VC.artifact_version("memo", endpoint="http://a/v1", models_dir=md)
    VC._hash_open_file = _counting_hash
    try:
        mp2 = os.path.join(md, "memo.gguf"); open(mp2, "wb").write(b"p" * 4096)
        VC._ARTIFACT_MEMO.clear(); hashes[0] = 0
        av(); av()
        if hashes[0] != 2:
            fails.append("memo racy window: a just-written file was memoised (%d hashes for 2 lookups)" % hashes[0])
        VC._RACY_NS = -10 ** 18                          # treat the file as aged, to drive the stamp itself
        VC._ARTIFACT_MEMO.clear(); hashes[0] = 0
        m1 = av(); m2 = av()
        if hashes[0] != 1 or m1 != m2:
            fails.append("memo: an unchanged artifact was rehashed or re-keyed (%d hashes for 2 lookups)" % hashes[0])
        _time.sleep(0.1)                                 # let the change-time clock tick past the first write
        st2 = os.stat(mp2)
        with open(mp2, "r+b") as fh:
            fh.write(b"q" * 4096)                        # in place: same file id, same size
        os.utime(mp2, ns=(st2.st_atime_ns, st2.st_mtime_ns))
        if os.stat(mp2).st_mtime_ns != st2.st_mtime_ns or os.stat(mp2).st_size != st2.st_size:
            fails.append("memo probe did not restore size+mtime (the probe, not the code)")
        if av() == m1:
            fails.append("memo: an in-place same-size rewrite with mtime restored served the memoised digest (A416)")
        hashes[0] = 0
        os.environ[VC.STRICT_HASH_ENV] = "1"
        try:
            av(); av()
        finally:
            del os.environ[VC.STRICT_HASH_ENV]
        if hashes[0] != 2:
            fails.append("strict mode did not rehash on every lookup (%d hashes for 2 lookups)" % hashes[0])
        flips = iter((0, 1))

        def _moving_stamp(f):
            stamp, change_ns = _orig_stamp(f)
            return stamp + (next(flips, 2),), change_ns
        VC._change_stamp = _moving_stamp
        VC._ARTIFACT_MEMO.clear()
        if not av().endswith("::artifact=unstable"):
            fails.append("a file seen changing during its read was not marked unstable (A416)")
    finally:
        VC._hash_open_file, VC._change_stamp, VC._RACY_NS = _orig_hash, _orig_stamp, _orig_racy
        VC._ARTIFACT_MEMO.clear()
    try:
        import covenant_judge_local as JL3
    except Exception:                                    # noqa: BLE001
        print("VC1 artifact-wiring: covenant_judge_local unavailable here -- skipped (UNDETERMINED)")
    else:
        _origart = VC.artifact_version
        try:
            JL3._VC_CACHES.clear()
            VC.artifact_version = lambda *a, **k: "ART1"
            ca = JL3._verdict_cache("m")
            ca.put("ONLY-UNDER-ART1", {"violates": True})
            if "ART1" not in ca.policy_version:
                fails.append("artifact-wiring: artifact fingerprint not in the policy key")
            VC.artifact_version = lambda *a, **k: "ART2"   # same name, changed endpoint/bytes
            cc = JL3._verdict_cache("m")
            if cc is ca:
                fails.append("artifact-wiring: an artifact change did NOT re-key the cache")
            if cc.get("ONLY-UNDER-ART1") is not None:
                fails.append("artifact-wiring: a verdict survived an artifact change (stale leaked past a same-name swap)")
            VC.artifact_version = lambda *a, **k: "ART1"   # control: same artifact serves the old entry (re-key, not a wipe)
            if JL3._verdict_cache("m").get("ONLY-UNDER-ART1") is None:
                fails.append("artifact-wiring control: same-artifact entry not served (re-key is vacuous)")
            # A416 (ported from PR #9): an uncertain local artifact is never cached against, and the kill switch is
            # honoured before any artifact read (the read hashes the model file).
            for marker in ("unstable", "unreadable"):
                VC.artifact_version = lambda *a, _marker=marker, **k: "endpoint=x::artifact=" + _marker
                bypass = JL3._verdict_cache("m")
                bypass.put("probe", {"violates": False})
                if bypass.get("probe") is not None:
                    fails.append("artifact-wiring: an %s local artifact served a cached verdict" % marker)

            def _forbidden_read(*a, **k):
                raise AssertionError("artifact read while the cache is off")
            VC.artifact_version = _forbidden_read
            _prev_off = os.environ.get(VC.CACHE_OFF_ENV)
            os.environ[VC.CACHE_OFF_ENV] = "1"
            try:
                if JL3._verdict_cache("m").get("probe") is not None:
                    fails.append("artifact-wiring: the disabled cache returned a hit")
            except AssertionError as e:
                fails.append("artifact-wiring: %s (kill switch not honoured before artifact I/O)" % e)
            finally:
                if _prev_off is None:
                    os.environ.pop(VC.CACHE_OFF_ENV, None)
                else:
                    os.environ[VC.CACHE_OFF_ENV] = _prev_off
            if not any("artifact-wiring" in f for f in fails):
                print("VC1 artifact-wiring: a same-name endpoint/bytes change re-keys the judge cache; stale cannot leak")
        finally:
            VC.artifact_version = _origart
            JL3._VC_CACHES.clear()
    shutil.rmtree(md, ignore_errors=True)

    if fails:
        print("VC1 FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("VC1 PASS: cache hits are identical, version+context guard holds both ways (control proves it), "
          "kill switch works, held-out verification clean")
    # Emit a tally line the sweep's TALLY regex can score (2026-10-21): before
    # this, the PASS path printed only prose, so covenant_one read VC1 as NO
    # RESULT and the sweep counted a green suite "not clean". Any section that
    # could not run printed its own UNDETERMINED line above; this line attests
    # the invariants that DID run all held.
    print("VC1: ALL INVARIANTS HELD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
