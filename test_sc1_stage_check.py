#!/usr/bin/env python3
"""SC2 (2026-10-03): the pre-commit stage-check runs committed suites where the runner runs them.

Stubs git, staging and the suite runs; the real end-to-end proof (the old E12r test fails in the
staged copy) was run by hand the day this landed and is recorded in its commit.

    python test_sc1_stage_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import stage_check as S  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


print("SC2 -- committed suites run in the runner's copy")
got = S.staged_tests(run=lambda: "test_a.py\ncovenant_x.py\ndocs/test_b.py\ntest_c.py\ntools/test_d.py\nREADME.md\n")
check("SC2.1 only top-level test_*.py files in the commit are taken", got == ["test_a.py", "test_c.py"], got)

said = []
P = type("P", (), {})


def runner(results):
    def run(t, w):
        p = P()
        p.returncode, p.stdout = results[t]
        return p
    return run


r = S.check(["test_a.py", "test_c.py"], stage=lambda say: "/tmp/w", clean=lambda w: None,
            run=runner({"test_a.py": (0, "A: 5/5 passed\n"), "test_c.py": (1, "C: 4/5 passed\n")}), say=said.append)
check("SC2.2 each suite is reported with its own last line, pass and fail told apart",
      r == {"test_a.py": (True, "A: 5/5 passed"), "test_c.py": (False, "C: 4/5 passed")}, r)
check("SC2.3 a failure is said loudly, and the commit is said NOT blocked",
      any("FAIL test_c.py" in s for s in said) and any("NOT blocked" in s for s in said), said)
said2 = []
r2 = S.check(["test_a.py"], stage=lambda say: "/tmp/w", clean=lambda w: None,
             run=runner({"test_a.py": (0, "A ok\n")}), say=said2.append)
check("SC2.4 all passing: no failure line at all", r2 == {"test_a.py": (True, "A ok")}
      and not any("FAIL" in s for s in said2), said2)


def boom(say):
    raise OSError("disk full")


said3 = []
r3 = S.check(["test_a.py"], stage=boom, say=said3.append)
check("SC2.5 staging that breaks is said ('nothing was checked'), never raised into the hook",
      r3 == {} and any("could not stage" in s and "nothing was checked" in s for s in said3), said3)
check("SC2.6 no test files in the commit: nothing staged, nothing said", S.check([], say=said3.append) == {})
hook = open(os.path.join(HERE, "ops", "pre-commit.synchold"), encoding="utf-8").read()
check("SC2.7 the tracked pre-commit hook calls it", "python tools/stage_check.py" in hook)

print("\nSC2: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
