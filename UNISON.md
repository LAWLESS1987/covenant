# Working on this repository in unison

Two of us build here: **L**, on the Windows box where production runs, and
**Claude**, from a cloud workspace with a bridge to that box. This file is the
convention that keeps us from clobbering each other. It is short on purpose.

## The rule that produced this file

On 2026-08-27 `main` was missing five branches. Two of them fixed defects that
were then **rediscovered from scratch, hours of work**, because nobody knew the
fix already existed. One of them carried `test_k2_tally_arithmetic.py` — a
suite that existed on exactly one branch and on no machine.

> **Unmerged work is invisible work.** A branch is a proposal with a deadline,
> not a shelf. Merge it or delete it; do not accumulate it.

If a branch has been open longer than the thing it fixes has been broken, it is
costing more than it is saving.

## Branches

Existing convention, unchanged:

    fix/<what-it-fixes>      a defect, with a suite that fails before it
    feat/<what-it-adds>      new capability
    docs/<what-it-corrects>  documentation only
    chore/<what-it-tidies>   no behaviour change

**Claude never commits to `main` directly.** Work lands on a branch, CI runs,
L merges. `main` is L's to move. The one exception is a merge L has explicitly
asked for in the session, and even then every branch head is tagged under
`refs/backup/<date>/` first so it reverts with one command.

## What each side is authoritative for

| | authoritative for | cannot answer |
|---|---|---|
| **GitHub Actions** (`covenant.yml`) | the Linux sweep, every push and PR, on 3.11 and 3.12 | win32, the launch gates, anything needing a judge or a node |
| **`ONE.bat`** on the box | win32 — the platform production runs on | nothing else runs there automatically |
| **`ONE_UP.bat`** | the launch itself, gates first | — |

**A green tick is not a launch.** Three suites behave differently on Windows,
and a refused TCP connect costs 0.0 ms in CI and 2,045 ms on the box. Run
`ONE.bat` on the box before any launch. CI does not replace it and says so in
its own header.

The workflow deliberately has **no list of suites of its own**. It calls
`covenant_one.py --ci` — the same file that runs on the box. A second list is a
second thing to go stale, which is exactly how `run_all_tests.sh` came to name
eleven suites that were not on disk.

## Three things that must not be committed

1. **The portfolio.** `holdings.txt` and `TRADING_POLICY.json` are gitignored.
   They were in the **history** from before 2026-08-27 -- and the same table
   sat in `docs/DAILY_CHECK.md` in every commit -- until the history was
   rewritten on 2026-09-05 (`tools/purge_history.py`) and the GitHub
   repository recreated from the rewritten history. The repository is public;
   the private corpus is not in it, and `python tools/purge_history.py
   --verify` scans every blob of every ref to prove that on demand. See
   docs/KNOWN_ISSUES.md issue 15.
2. **Launcher outputs.** Anything a `.bat` writes into this folder —
   `ONE_RUN.txt`, `DEPLOY_VERIFY.txt`, `LAUNCH_CHECK.json`, `NODE_RESTART.txt`,
   `GIT_SETUP.txt`, and so on. Tracking an output as an input means every run
   dirties the worktree. **Adding a launcher that writes a report here means
   adding its report to `.gitignore` and to `verify_bundle.py`'s `OUTPUTS`, in
   the same commit.** This has now been the same bug four times.
3. **Keys and databases.** Already covered by `.gitignore`; never relax it.

`MANIFEST.sha256` **is** tracked, deliberately: it is a release reference
written on purpose, like a lockfile, not a report written on every run.

## Adding a suite

A suite that no runner runs is a switched-off check that still reads as
coverage. So when you add one, do one of two things and never neither:

* add it to `SUITES` in `covenant_one.py`, **or**
* add it to `DELIBERATELY_OFF` with the reason and the remedy.

The COVERAGE phase diffs that table against the disk in both directions on
every run and names anything that is in neither. It will find you.

## Recovering from anything

    git reset --hard refs/backup/<date>/main
    git for-each-ref refs/backup            # what snapshots exist

Every branch head is tagged before any bulk operation.

## A note on git through the file bridge

Claude's bridge to the box **cannot delete files**, and git deletes a `.lock`
after every ref write — so a git write through the bridge succeeds and then
poisons the next one with *"Another git process seems to be running"*. Git
writes therefore happen on Windows, via `GIT_SETUP.bat`. Read-only git through
the bridge is fine, and must use `git --no-optional-locks`, because a plain
`git status` refreshes the index and takes a write lock. A read-only check has
no business taking one.
