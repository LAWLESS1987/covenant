"""A468 (2026-11-22 security search): the local judge's verdict cache keys on the EXACT text.

The default normalization lower-cases and collapses white space. A text that differs from a judged one only in case
(base64 is case-sensitive) or in white space (indentation is meaning in code) was served that verdict unjudged.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_judge_local as J  # noqa: E402
import covenant_verdict_cache as VC  # noqa: E402

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append((label, bool(ok)))
    print(("ok    " if ok else "FAIL  ") + label + ("" if ok else "  -- %r" % (detail,)))


def main():
    os.environ.pop(VC.PERSIST_DIR_ENV, None)          # in memory only: this test writes no store
    os.environ.pop(VC.CACHE_OFF_ENV, None)
    J._VC_CACHES.clear()
    c = J._verdict_cache("no-such-model-a468")
    clean = {"violates": False, "reason": "judged clean"}
    a, b = "note: aGVsbG8gd29ybGQ=", "note: AGVSBG8GD29YBGQ="          # same letters, different bytes when decoded
    c.put(a, clean)
    check("A468.1 a text that differs only in case is NOT served the other's verdict", c.get(b) is None, c.get(b))
    check("A468.2 the exact text is still served (the cache still works)", c.get(a) == clean, c.get(a))
    code1, code2 = "if ok:\n    run()\nstop()", "if ok:\n    run()\n    stop()"
    c.put(code1, clean)
    check("A468.3 a text that differs only in white space (indentation) is NOT served", c.get(code2) is None, c.get(code2))
    check("A468.4 the policy version names the exact key, so no entry made under the old key is read",
          c.policy_version.endswith("::key=exact"), c.policy_version)
    # control: the default cache DOES fold both, so A468.1 and A468.3 can fail
    d = VC.VerdictCache("judge@control")
    d.put(a, clean)
    d.put(code1, clean)
    check("A468.5 control: the default normalization serves both twins (the old behaviour)",
          d.get(b) == clean and d.get(code2) == clean, (d.get(b), d.get(code2)))
    J._VC_CACHES.clear()
    failed = [n for n, ok in RESULTS if not ok]
    print("A468: %d/%d passed" % (len(RESULTS) - len(failed), len(RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
