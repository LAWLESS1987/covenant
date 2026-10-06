#!/usr/bin/env python3
"""tools/pin_deploy.py -- every deploy pin besides the core's moves in the SAME commit as its file (A267, M53).

WHY. verify_deploy.py pins five files by sha256. tools/pin_core.py (2026-10-03) moves the core's pin when
the core is committed; nothing moved the other four, so its tombstone covered one pin of five. Measured over
main's first-parent history on 2026-10-06: run_all_tests.sh's pin was stale in six spans -- the longest from
eb892c0 (09-12) to 8bf4d56 (10-05), the last 16e389e, re-pinned by hand in 260f3dd -- run_local_sweep.py's in
three, test_a3s_send_bounds.py's in one. Most changes that add a suite add a line to run_all_tests.sh, and every
such commit made verify_deploy read FAIL and refuse the restarts it gates. So the pre-commit hook calls this on
every commit, and it acts on the pinned files that commit stages.

WHICH FILES. Discovered, never listed (CLAUDE.md rule 2): the names are read from verify_deploy.py's MANIFEST
(ast, never imported), so a sixth pin is seen the day it is added. The core is pin_core's and is left to it.
Each other file needs the suites that judge its bytes in JUDGES -- the ones its pin comment has recorded at
every hand move. A pinned file with none is NOT moved, and that is said; PC2.10 fails the sweep until it has.

THE ORDER (the b969 lesson, as pin_core keeps it). A pin proves WHICH bytes arrived, never that they are right,
so the judges run first and a pin moves only if all of its judges pass. If one fails the pin stays, verify_deploy
reads FAIL and a person looks. Like the hook that calls it, this never blocks a commit.

THE BYTES. The pin is the hash of what the commit holds. A file whose bytes on disk are not its bytes in the
index (a partial `git add -p`, or a CRLF copy -- the 09-20 re-pin hashed one, 7bde90e1effa, and matched no
commit for two weeks) is NOT moved. Nor is anything when verify_deploy.py has changes this commit does not
stage: staging it would commit them. The judges read the files on disk, and that is the same bytes only
because of the first rule.

WHAT IT CANNOT SEE. test_p19_overlay_guard.py and test_a3s_send_bounds.py are pinned test files and their only
judge is themselves: passing proves they run green on these bytes, not that they still bite. A suite weakened
until it passes would be pinned, as it would have been by hand.

    python tools/pin_deploy.py --check              # every pin but the core's: does it match the file on disk?
    python tools/pin_deploy.py --write --staged     # the hook: the pinned files this commit stages
    python tools/pin_deploy.py --write [FILE ...]   # by hand: the named files, or every stale one
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VD = os.path.join(HERE, "verify_deploy.py")
OWNED_ELSEWHERE = {"covenant_unified_v8.py": "tools/pin_core.py"}
JUDGES = {
    "run_all_tests.sh": ("test_k1_runner_key_preservation.py", "test_k2_tally_arithmetic.py"),
    "run_local_sweep.py": ("test_p19_overlay_guard.py",),
    "test_p19_overlay_guard.py": ("test_p19_overlay_guard.py",),
    "test_a3s_send_bounds.py": ("test_a3s_send_bounds.py",),
}


def manifest(text):
    """verify_deploy.py's MANIFEST as {name: sha256}, read with ast; None when it is not a literal of 64-hex
    strings. The watchdog reads it the same way (_verify_deploy_pin)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "MANIFEST" for t in node.targets):
            try:
                man = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                return None
            if isinstance(man, dict) and all(isinstance(k, str) and isinstance(v, str)
                                             and re.fullmatch(r"[0-9a-f]{64}", v) for k, v in man.items()):
                return man
            return None
    return None


def pin_re(name):
    return re.compile(r'("%s":\s*")([0-9a-f]{64})(")' % re.escape(name))


def rewrite(text, name, sha):
    """One digest replaced in place; every other byte -- the history comments, the trailing comment on the
    digest's own line -- untouched. Refused, never half-done, unless the pattern matches exactly once AND the
    result reads back as MANIFEST with only that entry changed."""
    rx = pin_re(name)
    if len(rx.findall(text)) != 1:
        raise ValueError("verify_deploy.py does not pin %s exactly once" % name)
    out = rx.sub(lambda m: m.group(1) + sha + m.group(3), text, count=1)
    before, after = manifest(text), manifest(out)
    if before is None or after is None or after.get(name) != sha or \
            {k: v for k, v in after.items() if k != name} != {k: v for k, v in before.items() if k != name}:
        raise ValueError("moving %s's pin would not change MANIFEST[%r] alone" % (name, name))
    return out


def sha_of(data):
    return hashlib.sha256(data).hexdigest()


def disk(name):
    try:
        with open(os.path.join(HERE, name), "rb") as fh:
            return fh.read()
    except OSError:
        return None


def git(*args):
    """A git call about THIS repository, under the hook's own environment: GIT_INDEX_FILE is how a commit of
    named paths (`git commit -a`, `git commit FILE`) shows the hook the index it will commit. None if git
    cannot answer."""
    try:
        p = subprocess.run(["git"] + list(args), cwd=HERE, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def indexed(name):
    """The bytes the commit holds for `name`, or None (not in the index, or no git here)."""
    return git("cat-file", "blob", ":" + name)


def staged_names():
    out = git("diff", "--cached", "--name-only")
    return None if out is None else out.decode("utf-8", "replace").split()


def stage(path):
    return git("add", "--", path) is not None


def suite_env(base=None):
    """The judges run without git's repository-pinning variables (A255: a suite run from a hook inherited
    GIT_DIR, and its scratch `git init` turned the shared repository bare)."""
    try:
        sys.path.insert(0, HERE)
        import verify_bundle as VB
        return VB.repo_env(base)
    except Exception:                                            # noqa: BLE001 -- stricter fallback
        return {k: v for k, v in (os.environ if base is None else base).items() if not k.startswith("GIT_")}
    finally:
        if sys.path and sys.path[0] == HERE:
            sys.path.pop(0)


def run_judges(judges, run=None):
    """Each judge once, however many files it judges; the ones that failed."""
    run = run or (lambda t: subprocess.run([sys.executable, t], cwd=HERE, capture_output=True, text=True,
                                           timeout=600, env=suite_env()).returncode)
    failed = []
    for t in judges:
        try:
            rc = run(t)
        except Exception as e:                                   # noqa: BLE001 -- a judge that cannot run failed
            rc = "raised %s" % type(e).__name__
        if rc != 0:
            failed.append(t)
    return failed


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    say = lambda s: print("pin_deploy: " + s)                    # noqa: E731
    try:
        with open(VD, "rb") as fh:
            vd_raw = fh.read()
    except OSError as e:
        say("cannot read verify_deploy.py: %s" % e)
        return 2
    text = vd_raw.decode("utf-8")
    man = manifest(text)
    if man is None:
        say("verify_deploy.py's MANIFEST could not be read as a literal -- no pin was checked")
        return 2
    mine = sorted(n for n in man if n not in OWNED_ELSEWHERE)
    rc = 0

    if "--write" not in argv:
        for n in mine:
            raw = disk(n)
            got = sha_of(raw) if raw is not None else None
            if got == man[n]:
                say("ok     %s %s" % (n, got[:12]))
            else:
                say("STALE  %s -- pinned %s, on disk %s" % (n, man[n][:12], (got or "MISSING")[:12]))
                rc = 1
            if n not in JUDGES:
                say("NO JUDGES  %s -- nothing records which suites judge it, so nothing can move its pin" % n)
                rc = 1
        return rc

    named = [a for a in argv if not a.startswith("--")]
    if "--staged" in argv:
        staged = staged_names()
        if staged is None:
            say("git could not say what this commit stages -- no pin was checked")
            return 1
        targets = [n for n in mine if n in staged]
    elif named:
        targets = []
        for n in named:
            if n in OWNED_ELSEWHERE:
                say("%s is moved by %s, not here" % (n, OWNED_ELSEWHERE[n]))
            elif n not in man:
                say("%s is not pinned by verify_deploy.py" % n)
                rc = 1
            else:
                targets.append(n)
    else:
        targets = mine

    need = {}
    for n in targets:
        raw = disk(n)
        if raw is not None and sha_of(raw) == man[n]:
            if named or "--staged" in argv:
                say("%s already matches its pin (%s)" % (n, man[n][:12]))
            continue
        if n not in JUDGES:
            say("NOT moved: %s -- no suites are recorded as judging it (JUDGES). verify_deploy will read FAIL "
                "until a person pins it or adds its judges" % n)
            rc = 1
            continue
        held = indexed(n)
        if raw is None or held is None:
            say("NOT moved: %s -- %s" % (n, "it is not on disk" if raw is None else
                                           "git holds no staged copy of it to compare"))
            rc = 1
            continue
        if held != raw:
            say("NOT moved: %s -- its bytes on disk (%s) are not the bytes this commit holds (%s): a partial "
                "stage, or line endings. A pin of either would describe a file some checkout does not have"
                % (n, sha_of(raw)[:12], sha_of(held)[:12]))
            rc = 1
            continue
        need[n] = sha_of(raw)
    if not need:
        return rc

    if "--staged" in argv and indexed("verify_deploy.py") != vd_raw:
        say("NOT moved: %s -- verify_deploy.py has changes this commit does not stage, and moving a pin means "
            "staging it. Stage or set those aside, then: python tools/pin_deploy.py --write %s"
            % (", ".join(sorted(need)), " ".join(sorted(need))))
        return 1

    judges = []
    for n in sorted(need):
        judges += [t for t in JUDGES[n] if t not in judges]
    failed = run_judges(judges)
    moved = []
    for n in sorted(need):
        bad = [t for t in JUDGES[n] if t in failed]
        if bad:
            say("NOT moved: %s -- the suites that judge these bytes failed: %s. verify_deploy will read FAIL "
                "until this is looked at; that is the point." % (n, ", ".join(bad)))
            rc = 1
            continue
        try:
            text = rewrite(text, n, need[n])
        except ValueError as e:
            say("NOT moved: %s -- %s" % (n, e))
            rc = 1
            continue
        moved.append(n)
        say("moved %s %s -> %s, after %s passed on these bytes"
            % (n, man[n][:12], need[n][:12], "/".join(JUDGES[n])))
    if moved:
        with open(VD, "wb") as fh:
            fh.write(text.encode("utf-8"))
        if "--staged" in argv:
            if stage(os.path.relpath(VD, HERE)):
                say("staged verify_deploy.py with the moved pin")
            else:
                say("the pin moved on disk but verify_deploy.py could NOT be staged -- add it to this commit")
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
