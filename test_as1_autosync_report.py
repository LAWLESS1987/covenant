#!/usr/bin/env python3
"""AS1 -- the post-commit auto-sync says what actually happened to each branch.

2026-09-26 (A231): ops/post-commit.autosync pushed main and sentinel-witness in ONE command. The remote
sentinel-witness held a pre-rebase copy of a commit, so that half was refused, the command failed, and every
commit for a day printed "push FAILED" while main had landed. The hook now pushes and reports each ref on
its own. Driven here in a scratch clone with a bare remote, never the real one:

  AS1a  remote sentinel-witness diverged: main lands, the report says main was pushed and sentinel-witness
        was not, and never says the push of main failed.
  AS1b  remote sentinel-witness aligned: main lands and the report names no failure.
  AS1c  the installed hook, where this clone has hooks, is the tracked one byte for byte.

    python test_as1_autosync_report.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "ops", "post-commit.autosync")
PASSED, FAILED, NOT_RUN = [0], [], []
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.org")


def check(label, ok, detail=""):
    print("  %-76s %s" % (label[:76], "ok" if ok else "FAIL  %s" % str(detail)[:300]))
    if ok:
        PASSED[0] += 1
    else:
        FAILED.append(label)


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, env=ENV)


def main():
    if not shutil.which("git") or not shutil.which("sh"):
        NOT_RUN.append("AS1a-b: no git or no sh on this machine")
    else:
        base = tempfile.mkdtemp(prefix="as1_")
        bare, wk, other = (os.path.join(base, n) for n in ("remote.git", "work", "other"))
        subprocess.run(["git", "init", "-q", "--bare", bare], env=ENV, capture_output=True)
        subprocess.run(["git", "init", "-q", wk], env=ENV, capture_output=True)
        git(wk, "remote", "add", "origin", bare)
        open(os.path.join(wk, "a.txt"), "w").write("a\n")
        git(wk, "add", "a.txt")
        git(wk, "commit", "-q", "-m", "first")
        git(wk, "branch", "-M", "main")
        git(wk, "push", "-q", "origin", "main", "main:sentinel-witness")
        subprocess.run(["git", "clone", "-q", "-b", "sentinel-witness", bare, other], env=ENV, capture_output=True)
        open(os.path.join(other, "b.txt"), "w").write("b\n")
        git(other, "add", "b.txt")
        git(other, "commit", "-q", "-m", "only on the remote branch")
        git(other, "push", "-q", "origin", "sentinel-witness")
        # installed AS AN EXECUTABLE: git on Linux silently skips a hook without the bit (Windows runs it anyway), so
        # the first Linux CI run found AS1 at 0/2 with the hook never having run (2026-09-26)
        shutil.copyfile(HOOK, os.path.join(wk, ".git", "hooks", "post-commit"))
        os.chmod(os.path.join(wk, ".git", "hooks", "post-commit"), 0o755)

        def commit(name):
            open(os.path.join(wk, name), "w").write(name + "\n")
            git(wk, "add", name)
            p = git(wk, "commit", "-q", "-m", name)
            landed = git(wk, "rev-parse", "HEAD").stdout.strip() == git(bare, "rev-parse", "refs/heads/main").stdout.strip()
            return landed, p.stdout + p.stderr

        landed, said = commit("c.txt")
        check("AS1a diverged remote branch: main lands and is reported pushed; sentinel-witness reported NOT pushed",
              landed and "pushed main" in said and "sentinel-witness NOT pushed" in said and "main FAILED" not in said
              and "push FAILED" not in said, (landed, said))
        git(wk, "push", "-q", "--force", "origin", "main:sentinel-witness")
        landed2, said2 = commit("d.txt")
        check("AS1b aligned remote branch: main lands and no failure is reported",
              landed2 and "pushed main" in said2 and "NOT pushed" not in said2 and "FAILED" not in said2, (landed2, said2))
        # AS1d (2026-10-03, A243): the remote refuses main the way GitHub's ruleset does, with its words.
        pre = os.path.join(bare, "hooks", "pre-receive")
        with open(pre, "w", newline="\n") as fh:
            fh.write("#!/bin/sh\nwhile read old new ref; do\n  case \"$ref\" in refs/heads/main|refs/heads/sentinel-witness)\n"
                     "    echo \"- Changes must be made through a pull request.\" >&2\n    exit 1;;\n  esac\ndone\nexit 0\n")
        os.chmod(pre, 0o755)
        landed3, said3 = commit("e.txt")
        sha3 = git(wk, "rev-parse", "--short", "HEAD").stdout.strip()
        on_branch = git(bare, "rev-parse", "refs/heads/pending/" + sha3).stdout.strip() == git(wk, "rev-parse", "HEAD").stdout.strip()
        check("AS1d main refused by the PR rule: the report names the rule, not 'offline', and the commit lands as pending/<sha>",
              not landed3 and on_branch and "PR rule" in said3 and "pending/" + sha3 in said3 and "offline" not in said3,
              (landed3, on_branch, said3))
        check("AS1e sentinel-witness refused by the same rule: the report names the rule, never 'what only the remote holds'",
              "PR rule protects every branch" in said3 and "only the remote copy holds" not in said3, said3)
        os.remove(pre)
    hooks = os.path.join(HERE, ".git", "hooks")
    inst = os.path.join(hooks, "post-commit")
    # As A117.8b: a checkout with only git's samples (a fresh clone, a CI runner) has no hooks in use and nothing
    # is wrong; where a sibling hook is installed, this machine uses them, and post-commit must be the tracked one.
    in_use = any(os.path.isfile(os.path.join(hooks, h)) for h in ("pre-commit", "pre-push", "post-commit"))
    if not os.path.isdir(hooks) or not in_use:
        NOT_RUN.append("AS1c: no hooks in use on this checkout (the staged sweep copy, a fresh clone or a CI runner)")
    else:
        got = open(inst, encoding="utf-8").read() if os.path.exists(inst) else ""
        check("AS1c .git/hooks/post-commit is the tracked ops/post-commit.autosync, byte for byte",
              got == open(HOOK, encoding="utf-8").read(), "missing or different: cp ops/post-commit.autosync .git/hooks/post-commit")
    for n in NOT_RUN:
        print("  NOT RUN  %s" % n)
    print("AS1: %d/%d passed%s" % (PASSED[0], PASSED[0] + len(FAILED),
                                   (" (%d NOT RUN, not counted)" % len(NOT_RUN)) if NOT_RUN else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
