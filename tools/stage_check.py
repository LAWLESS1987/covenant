#!/usr/bin/env python3
"""tools/stage_check.py -- every test file being committed is run where the runner runs it, at commit time.

WHY. "Run it in the staged copy" has been step 4 of adding a test since 2026-09-10 (the staged copy has
no .git, no databases, no keys). It was a note, and notes are forgotten: on 2026-10-03 E12r was checked
only in the working tree, with .git present, and CI went red on the next two pushes (9a1ff52, bb227ca).
Rule 10: a forgotten step gets a guard where it is forgotten. The pre-commit hook calls this.

WHAT IT DOES. For each test_*.py added or changed in the commit: stage the tree exactly as
covenant_one does (covenant_one.stage, then clean_dbs), run the suite there, and print one line per
suite. A failure is said loudly. It NEVER blocks the commit -- the hook's first rule.

WHAT IT DOES NOT SEE, said plainly: the runner's ENVIRONMENT (CI exports variables the working
machine does not), and a fresh clone's lack of hooks and local config. Those are still the full
`python covenant_one.py --ci` on a fresh clone; this catches the .git-less directory, which is the
case that recurred.

    python tools/stage_check.py              # the staged (index) test files
    python tools/stage_check.py test_x.py    # named files
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def staged_tests(run=None):
    run = run or (lambda: subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
                                         cwd=HERE, capture_output=True, text=True).stdout)
    return [p for p in run().split() if os.path.basename(p).startswith("test_") and p.endswith(".py") and "/" not in p]


def suite_env(base=None):
    """The environment a suite runs under: the hook's, WITHOUT git's repository-pinning variables.

    A255, 2026-10-04. Git exports GIT_DIR, GIT_INDEX_FILE ... to the hook, and this passed them to
    every suite. "Where the runner runs it" was then false for any suite that calls git: in the
    .git-less staged copy, `git ls-files` answered about the repository being committed, and a
    suite's scratch `git init` re-initialized that repository's linked-worktree gitdir -- the
    shared config read core.bare = true and the main working tree stopped working. The runner
    (covenant_one) never has those variables; now neither does a suite run from here."""
    try:
        import verify_bundle as VB
        return VB.repo_env(base)
    except Exception:                                            # noqa: BLE001 -- stricter fallback
        return {k: v for k, v in (os.environ if base is None else base).items() if not k.startswith("GIT_")}


def in_place_names():
    """Suites covenant_one runs IN THE FOLDER (IN_PLACE), never in the staged copy."""
    try:
        import covenant_one as C1
        return {n for n, _, _ in C1.IN_PLACE}
    except Exception:                                            # noqa: BLE001
        return set()


def check(tests, stage=None, clean=None, run=None, say=print, timeout=300):
    """{test: (ok, last_line)}. Never raises."""
    out = {}
    if not tests:
        return out
    work = None
    try:
        import covenant_one as C1
        work = (stage or C1.stage)(lambda m: None)
        (clean or C1.clean_dbs)(work)
        in_place = in_place_names()
        for t in tests:
            # A255: an IN_PLACE suite measures THE FOLDER (git, the manifest, the hook), so the
            # runner runs it there; staging it produced a false "CI will be red".
            where = HERE if t in in_place else work
            try:
                p = (run or (lambda t, w: subprocess.run([sys.executable, t], cwd=w, capture_output=True,
                                                         text=True, timeout=timeout,
                                                         env=suite_env())))(t, where)
                last = ((p.stdout or "").strip().splitlines() or [""])[-1][:160]
                out[t] = (p.returncode == 0, last)
            except Exception as e:                               # noqa: BLE001
                out[t] = (False, "did not run: %s" % type(e).__name__)
            ok, last = out[t]
            say("stage-check: %s %s%s -- %s" % ("ok  " if ok else "FAIL", t,
                                               " (in place, as the runner runs it)" if where == HERE else "",
                                               last))
        if any(not ok for ok, _ in out.values()):
            say("stage-check: a suite FAILS where the runner runs it (no .git, no databases). CI will be red "
                "on this push unless it is fixed. The commit is NOT blocked.")
    except Exception as e:                                       # noqa: BLE001
        say("stage-check: could not stage (%s: %s) -- nothing was checked" % (type(e).__name__, str(e)[:120]))
    finally:
        if work and os.path.isdir(work) and stage is None:
            shutil.rmtree(work, ignore_errors=True)
    return out


if __name__ == "__main__":
    names = sys.argv[1:] or staged_tests()
    check(names)
    sys.exit(0)
