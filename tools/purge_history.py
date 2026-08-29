#!/usr/bin/env python3
"""purge_history.py -- remove the portfolio files from every commit, safely.

WHAT AND WHY. holdings.txt and TRADING_POLICY.json stopped being TRACKED at
commit 2dfe018. They are still IN THE HISTORY and still readable: 505 bytes,
~10 positions with quantities and average buy prices, at 965ba6e, which is on
origin/main. Four paths carry them -- the repo root AND launch/covenant-v8.37/.
Sixteen commits have them in their tree; only two MODIFY them, so
`git log -- <path>` reports 2 and is the wrong set to verify against.

This blocks: making the repo public, AND adding any collaborator, because a
collaborator on a private repo clones the full history. See
docs/sessions/PUBLIC_PATH.md.

THIS SCRIPT DOES NOT PUSH AND DOES NOT DELETE ANYTHING REMOTE. It rewrites
local history and then verifies. Publishing the result is a separate,
deliberate act -- and PUBLIC_PATH.md argues for delete-the-GitHub-repo and
republish rather than force-push, because a force-push leaves the old commits
reachable by direct SHA until GitHub's GC runs.

    python3 tools/purge_history.py            # dry run: report only, no writes
    python3 tools/purge_history.py --run      # rewrite, after a tagged backup

Requires git-filter-repo (`pip install git-filter-repo`). filter-branch is
deprecated, slow, and easy to get wrong; it is deliberately not used.
"""
import os, subprocess, sys

PATHS = ["holdings.txt", "TRADING_POLICY.json",
         "launch/covenant-v8.37/holdings.txt",
         "launch/covenant-v8.37/TRADING_POLICY.json"]
BACKUP_TAG = "backup/pre-purge"


def git(*a, check=True):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(a)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def commits_containing():
    """Every commit whose TREE contains any target path -- not just the two
    that modify them. This is the set a purge must be verified against."""
    hits = []
    for c in git("rev-list", "--all").splitlines():
        tree = git("ls-tree", "-r", "--name-only", c, check=False)
        if any(p in tree.split("\n") for p in PATHS):
            hits.append(c)
    return hits


def main():
    run = "--run" in sys.argv
    if git("rev-parse", "--is-inside-work-tree") != "true":
        sys.exit("not a git work tree")
    if git("status", "--porcelain"):
        sys.exit("working tree is dirty. Commit or stash first -- a rewrite "
                 "over uncommitted work is how work disappears.")

    before = commits_containing()
    print(f"commits whose tree contains a target path: {len(before)}")
    for p in PATHS:
        n = len(git("log", "--all", "--oneline", "--", p, check=False).splitlines())
        print(f"  {p:<42} modified in {n} commit(s)")
    if not before:
        print("\nnothing to purge -- already clean.")
        return 0

    if not run:
        print("\nDRY RUN. Nothing written. Re-run with --run to rewrite.")
        print("After --run, publishing is still a separate act:")
        print("  see docs/sessions/PUBLIC_PATH.md step 3 "
              "(delete-and-republish, NOT force-push)")
        return 0

    if subprocess.run(["git", "filter-repo", "--version"],
                      capture_output=True).returncode:
        sys.exit("git-filter-repo not found. `pip install git-filter-repo`")

    head = git("rev-parse", "HEAD")
    git("tag", "-f", BACKUP_TAG, head)
    print(f"\nbackup tag {BACKUP_TAG} -> {head[:12]}")
    print("every SHA is about to change; that tag is the way back.\n")

    args = ["filter-repo", "--invert-paths", "--force"]
    for p in PATHS:
        args += ["--path", p]
    git(*args)
    print("rewrite done.\n")

    after = commits_containing()
    print(f"VERIFY -- commits still containing a target path: {len(after)}")
    if after:
        print("  *** PURGE INCOMPLETE. DO NOT PUBLISH. ***")
        for c in after[:10]:
            print("   ", c)
        return 1
    print("  clean across every reachable commit.")
    print("\nNOTE: git-filter-repo removes 'origin' on purpose, so a rewrite "
          "cannot be pushed by reflex. That is a feature.")
    print("Next: PUBLIC_PATH.md step 3, then step 4 (choose a licence).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
