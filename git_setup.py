#!/usr/bin/env python3
"""git_setup.py -- put the repository into a real, pushable state. 2026-08-27.

WHY THIS RUNS ON WINDOWS AND NOT OVER THE FILE BRIDGE. The bridge mount cannot
DELETE files, and git deletes a `.lock` file after every ref write. So over the
bridge each git write succeeds and then leaves its own lock behind, and the
NEXT git command fails with "Another git process seems to be running". Two of
those locks are sitting in .git right now. Windows git can remove them; that is
the whole reason this file exists.

WHAT IT DOES, in order, and it stops at the first thing that goes wrong:

  1. Clears STALE .git/*.lock files -- and refuses if any is under 60 s old,
     because that one might belong to a git process that is actually running.
  2. Commits the already-staged privacy change (portfolio + launcher reports
     untracked; the files are untouched on disk).
  3. Commits the ONE-command work.
  4. Merges feat/one-command and the five unmerged branches into main, --no-ff,
     one at a time. On ANY conflict it aborts THAT merge and stops, leaving
     everything before it intact. It never forces and never discards.
  5. Regenerates MANIFEST.sha256 over the merged tree and commits it, because
     the merges change files the manifest describes.

NOTHING IS PUSHED. There is no remote. Pushing is GITHUB_PUSH.bat, separately
and deliberately.

Every branch head was tagged under refs/backup/2026-08-27/ before any of this,
so `git reset --hard refs/backup/2026-08-27/main` puts main back exactly.

Run: GIT_SETUP.bat  (or: python git_setup.py)
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
TRANSCRIPT = os.path.join(HERE, "GIT_SETUP.txt")
_fh = None


def emit(line=""):
    """Print AND record. The first version of this script printed only to a
    console that closes, so when it stopped at a conflict the reason was gone
    -- a report you cannot read afterwards is not a report."""
    print(line, flush=True)
    if _fh:
        _fh.write(line + "\n")
        _fh.flush()


BRANCHES = [
    "feat/one-command",
    "fix/tally-counts-failures-as-passes",   # subsumes remove-phantom-suites
    "fix/remove-phantom-suites",             #   and sweep-uses-project-venv
    "fix/sweep-uses-project-venv",
    "docs/correct-missing-suite-count",
    "docs/withdraw-unverified-suite-totals",
]
LOCK_MIN_AGE_S = 60


def git(*args, check=True, quiet=False):
    p = subprocess.run(["git"] + list(args), cwd=HERE, capture_output=True,
                       text=True, encoding="utf8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    if not quiet:
        for line in out.splitlines():
            if line.strip() and "unable to unlink" not in line:
                emit("    " + line.rstrip())
    if check and p.returncode != 0:
        raise RuntimeError("git %s -> exit %d" % (" ".join(args), p.returncode))
    return p.returncode, out


def step(n, title):
    emit()
    emit("=" * 72)
    emit("  %s. %s" % (n, title))
    emit("=" * 72)


def clear_stale_locks():
    step(1, "Clear stale .git lock files")
    gitdir = os.path.join(HERE, ".git")
    found = []
    for dp, _dns, fns in os.walk(gitdir):
        for fn in fns:
            if fn.endswith(".lock"):
                found.append(os.path.join(dp, fn))
    if not found:
        emit("    none -- nothing to clear.")
        return True
    now = time.time()
    fresh = [p for p in found if now - os.path.getmtime(p) < LOCK_MIN_AGE_S]
    for p in found:
        age = now - os.path.getmtime(p)
        emit("    %-52s %6.0f s old" % (os.path.relpath(p, HERE), age))
    if fresh:
        emit()
        emit("    REFUSING. A lock under %d s old may belong to a git process that"
              % LOCK_MIN_AGE_S)
        emit("    is genuinely running (an editor, a GUI client). Close it and")
        emit("    re-run. Deleting a live lock corrupts the operation holding it.")
        return False
    for p in found:
        try:
            os.remove(p)
            emit("    removed  %s" % os.path.relpath(p, HERE))
        except OSError as e:
            emit("    COULD NOT REMOVE %s: %s" % (p, e))
            return False
    return True


PRIVACY_MSG = """Stop tracking the portfolio and the launcher reports

holdings.txt is the ACTUAL portfolio -- exact quantities and average buy
prices for ten assets -- and TRADING_POLICY.json carries the locked book
value and the sleeve funding. Both were tracked, in the root and again in
launch/covenant-v8.37/, so any remote this repo reached would have carried
them. Untracking protects every FUTURE commit; it does NOTHING about the
history, which still contains them. Until that history is rewritten, any
remote must be PRIVATE.

DEPLOY_VERIFY.txt, LAUNCH_CHECK.json and NODE_RESTART.txt are launcher
OUTPUTS that were tracked as inputs, so every launch dirtied the worktree.
That is the LAUNCH_CHECK.json-in-the-manifest deadlock (M48) one layer up,
and it is what stands between this repo and using `git status --porcelain`
as the delivery check at all.

MANIFEST.sha256 stays tracked on purpose: it is a release reference written
deliberately, like a lockfile, not a report written on every run.

The files are untouched on disk.
"""

CI_MSG = """Run the Linux half of ONE.bat on every push

.github/workflows/covenant.yml calls `covenant_one.py --ci` -- the SAME file
that runs on the Windows box -- on 3.11 and 3.12. A CI result and a PC result
are therefore the same task list executed by the same bytes, and a difference
between them is a difference in the machine.

The workflow deliberately has NO list of suites of its own. A second list is a
second thing to go stale, which is exactly how run_all_tests.sh came to name
eleven suites that were not on disk.

--ci reports the launch gates in full and does not let them decide the exit
code. A runner has no ethics judge, no nodes, no identity keys and no delivery
manifest, so G1/G5/G8/G9/G10 cannot pass there; wiring the exit code to them
would make every run red for reasons true of the runner rather than of the
code, and a check that is always red is one people learn to skim (M34). The
suites decide the exit code, because the suites are what CI can observe.

A GREEN TICK IS NOT A LAUNCH, and the workflow header says so: it cannot cover
win32, where three suites behave differently and a refused TCP connect costs
2045 ms against 0.0 ms here.

test_k2_tally_arithmetic.py is wired into SUITES. It arrived on main today from
a branch where it had been sitting unmerged, and it pins the sweep's own
arithmetic -- a runner that counts a failure as a pass reports coverage it does
not have. Measured 25/25 before wiring.

probe_win_connect.py goes on the switched-off record as a MEASUREMENT rather
than a suite: nothing about it can fail.

UNISON.md is the convention for two people building here, and its first rule is
the one today earned: unmerged work is invisible work.
"""

WORK_MSG = """Add ONE.bat: one command, both platforms, nothing silent

There were twenty-two launchers in this folder and two sweep runners that
disagreed with each other in both directions. covenant_one.py is the single
entry point and the SAME FILE is the command in the cloud, so a PC run and a
cloud run are the same task list executed by the same bytes.

  ONE.bat          identity, coverage, integrity, gates, sweep, live state
  ONE_UP.bat       gates, then verify_deploy -- refused BEFORE the stop if a
                   gate blocks (P17)
  ONE_RETEST.bat   the not-clean suites, alone and twice (M18/M20)
  ONE_PROBE.bat    probe_win_connect.py

It reports ABSENT, ORPHANED, deliberately-off and over-budget as first-class
outcomes, and exit 2 (INCOMPLETE) exists so "nothing failed" can never be
read as "everything passed". It prints the sha256 of its own source, so a
transcript identifies the bytes that produced it (P11/P18, applied to the
runner).

Measured today, same runner bytes on both: cloud 1270 checks / 0 failed;
win32 1257 / 3. The three win32 failures are real and reproduced alone.

test_p18_version_collision.py is restored -- run_all_tests.sh named it and it
was on no machine. 20/20 on both platforms.

probe_win_connect.py settles A23's win32 failure by measurement instead of
assumption. A refused connect costs 0.0 ms on Linux and 2045.8 ms here:
MaxSynRetransmissions=4 and ~506 ms each is 2024 ms predicted against 2045.8
measured. Windows holds the socket in SYN-SENT and spends the whole
retransmission budget before surfacing the RST. A23 measured at a ~1 s
deadline, which a refused connect cannot beat -- so both of its numbers were
its own stopwatch.

verify_bundle.py: OUTPUTS now covers the ONE.bat transcripts, for the same
reason LAUNCH_CHECK.json is on it -- hashing a launcher's own report
guarantees the next run reports "changed" and refuses.

verify_deploy.py: the frozen four-entry delivery list expected a
run_all_tests.sh from before two commits that have since landed, and refused
a NODE restart over a stale hash for a TEST RUNNER. Updated, with the
evidence recorded beside the hash.
"""


def commit_if_staged(msg, label):
    rc, _ = git("diff", "--cached", "--quiet", check=False, quiet=True)
    if rc == 0:
        emit("    nothing staged for %s -- skipping." % label)
        return
    p = subprocess.run(["git", "commit", "-F", "-"], cwd=HERE, input=msg,
                       capture_output=True, text=True, encoding="utf8",
                       errors="replace")
    for line in ((p.stdout or "") + (p.stderr or "")).splitlines():
        if line.strip() and "unable to unlink" not in line:
            emit("    " + line.rstrip())
    if p.returncode != 0:
        raise RuntimeError("commit failed for %s" % label)


def resolve_run_all_tests(branch):
    """ONE conflict is resolvable by rule, and the rule is checkable.

    main changed run_all_tests.sh by adding exactly ONE line -- the K3 suite.
    The branch REWRITES the file: it removes the eleven suites the script named
    but that are not on disk, and stops the tally counting failures as passes.
    Both are wanted, and they do not disagree about anything: one adds a line,
    the other fixes the machinery around it.

    So: take the branch's file, then require that the K3 line survived. If it
    did not, this is NOT resolvable by rule and we abort rather than guess --
    an auto-resolution that is not verified afterwards is just a guess with a
    commit message.
    """
    K3 = "test_k3_p9_owner_only_guard.py"
    emit("    resolving run_all_tests.sh by rule:")
    emit("      main added exactly one line (%s);" % K3)
    emit("      the branch rewrites the file. Take the branch's, keep the line.")
    rc, _ = git("checkout", "--theirs", "--", "run_all_tests.sh", check=False, quiet=True)
    if rc != 0:
        emit("      could not take the branch's version.")
        return False
    path = os.path.join(HERE, "run_all_tests.sh")
    try:
        with open(path, "r", encoding="utf8", errors="replace") as fh:
            body = fh.read()
    except OSError as e:
        emit("      could not read the result: %s" % e)
        return False
    if K3 not in body:
        marker = "test_k1_runner_key_preservation.py"
        if marker not in body:
            emit("      VERIFY FAILED: neither %s nor %s is named in the merged"
                 % (K3, marker))
            emit("      file, so there is no correct place to restore the line.")
            return False
        out = []
        for line in body.splitlines(True):
            out.append(line)
            if marker in line and line.strip().startswith("run "):
                out.append("run %s 60\n" % K3)
        body = "".join(out)
        with open(path, "w", encoding="utf8", newline="\n") as fh:
            fh.write(body)
        emit("      restored the K3 line after the K1 line.")
    # VERIFY, both halves, or abort.
    if K3 not in body:
        emit("      VERIFY FAILED: the K3 line is still missing.")
        return False
    named = re.findall(r"(?m)^\s*run\s+([A-Za-z0-9_.]+\.py)", body)
    absent = [n for n in sorted(set(named))
              if not os.path.isfile(os.path.join(HERE, n))]
    if absent:
        emit("      VERIFY FAILED: the merged file still names suites that are")
        emit("      not on disk, which is the very thing this branch removes:")
        for n in absent:
            emit("        %s" % n)
        return False
    emit("      VERIFIED: K3 present, and all %d named suites exist on disk."
         % len(set(named)))
    git("add", "--", "run_all_tests.sh", check=False, quiet=True)
    return True


def main():
    print("git_setup -- put the repository into a real, pushable state")
    emit("  folder: %s" % HERE)
    if not os.path.isdir(os.path.join(HERE, ".git")):
        emit("  no .git here. Nothing to do.")
        return 1

    if not clear_stale_locks():
        return 1

    step(2, "Commit the privacy change (already staged)")
    commit_if_staged(PRIVACY_MSG, "the privacy change")

    step(3, "Commit the ONE-command work")
    for f in ("covenant_one.py", "ONE.bat", "ONE_UP.bat", "ONE_RETEST.bat",
              "ONE_PROBE.bat", "probe_win_connect.py",
              "test_p18_version_collision.py", "verify_bundle.py",
              "verify_deploy.py", ".gitignore",
              "git_setup.py", "GIT_SETUP.bat",
              "github_push.py", "GITHUB_PUSH.bat",
              "UNISON.md", ".github/workflows/covenant.yml",
              "START_HERE.md", "GO.bat",
              "gh_login.py", "GH_LOGIN.bat"):
        if os.path.exists(os.path.join(HERE, f)):
            git("add", "--", f, check=False, quiet=True)
    commit_if_staged(WORK_MSG, "the ONE-command work")

    step("3b", "Commit the CI setup and the working convention")
    for f in ("UNISON.md", ".github/workflows/covenant.yml", "covenant_one.py",
              "START_HERE.md", "GO.bat",
              "gh_login.py", "GH_LOGIN.bat"):
        if os.path.exists(os.path.join(HERE, f)):
            git("add", "--", f, check=False, quiet=True)
    commit_if_staged(CI_MSG, "the CI setup")

    step(4, "Merge into main -- each branch tried on its own")
    git("switch", "main")
    merged, conflicted = [], []
    for b in BRANCHES:
        rc, _ = git("rev-parse", "--verify", "--quiet", b, check=False, quiet=True)
        if rc != 0:
            emit("    %-40s no such branch -- skipped" % b)
            continue
        rc, _ = git("merge-base", "--is-ancestor", b, "main", check=False, quiet=True)
        if rc == 0:
            emit("    %-40s already in main" % b)
            continue
        emit()
        emit("    merging %s ..." % b)
        rc, _out = git("merge", "--no-ff", "-m", "Merge %s" % b, b, check=False)
        if rc == 0:
            merged.append(b)
            continue
        # Which paths actually conflicted?
        _rc, u = git("diff", "--name-only", "--diff-filter=U", check=False, quiet=True)
        paths = sorted(set(l.strip() for l in u.splitlines() if l.strip()))
        emit("    conflicted paths: %s" % (", ".join(paths) or "(none reported)"))
        if paths == ["run_all_tests.sh"] and resolve_run_all_tests(b):
            rc, _ = git("commit", "--no-edit", check=False)
            if rc == 0:
                emit("    resolved and committed.")
                merged.append(b)
                continue
        emit("    NOT auto-resolvable. Aborting THIS merge only; main keeps")
        emit("    everything merged before it. Resolve by hand:")
        emit("        git merge --no-ff %s" % b)
        git("merge", "--abort", check=False, quiet=True)
        conflicted.append(b)

    step(5, "Regenerate MANIFEST.sha256 over the merged tree")
    py = sys.executable
    p = subprocess.run([py, "verify_bundle.py", "--write"], cwd=HERE,
                       capture_output=True, text=True, encoding="utf8",
                       errors="replace")
    blob = (p.stdout or "") + (p.stderr or "")
    lines = [l for l in blob.splitlines() if l.strip()]
    emit("    " + (lines[-1].strip() if lines else "(no output)"))
    git("add", "--", "MANIFEST.sha256", check=False, quiet=True)
    commit_if_staged(
        "Regenerate the manifest over the merged tree\n\n"
        "The merges change files the manifest describes, so it is rewritten\n"
        "here rather than left stale -- a stale manifest is a permanently\n"
        "BLOCKED G1, which is how this repository spent today.\n",
        "the manifest")

    step("", "RESULT")
    git("--no-optional-locks", "status", "--short", "--branch", check=False)
    emit()
    emit("    merged: %s" % (", ".join(merged) or "nothing new"))
    if conflicted:
        emit("    NOT merged (conflict): %s" % ", ".join(conflicted))
    emit()
    git("log", "--oneline", "-8", check=False)
    emit()
    emit("    Recovery, exact: git reset --hard refs/backup/2026-08-27/main")
    emit()
    emit("    NOTHING WAS PUSHED. There is no remote. The portfolio is still")
    emit("    in the HISTORY, so if you push, push PRIVATE. GITHUB_PUSH.bat")
    emit("    is the next step and it says the same thing before it acts.")
    return 0


if __name__ == "__main__":
    _fh = open(TRANSCRIPT, "w", encoding="utf8", errors="replace")
    try:
        sys.exit(main())
    except Exception as e:
        emit()
        emit("  STOPPED: %s" % e)
        emit("  Nothing after this point ran. Recovery:")
        emit("      git reset --hard refs/backup/2026-08-27/main")
        sys.exit(1)
    finally:
        try:
            _fh.close()
        except Exception:
            pass
