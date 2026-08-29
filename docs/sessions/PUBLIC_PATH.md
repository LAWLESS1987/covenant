# Going public later — the decided route

Written 2026-08-29, immediately after `covenant` was published to
`github.com/LAWLESS1987/covenant` as a **private** repo (39 commits, HEAD
`f51fe8a`). Private was chosen deliberately, not by default. This file is the
plan for reversing that decision safely, if and when it is wanted.

## Why not public today — measured, not assumed

`holdings.txt` and `TRADING_POLICY.json` stopped being tracked at commit
`2dfe018`. They are still in the history and still readable:

| | |
|---|---|
| readable at | `965ba6e` (the parent of the removal) |
| on `origin/main`? | **yes** |
| `holdings.txt` | 505 bytes, 13 lines, ~10 position rows with quantities and average buy prices |
| `TRADING_POLICY.json` | keys `policy`, `locked_positions`, `sleeve`, `graduation_requirements`, `overrides` |
| paths to purge | 4 — root and `launch/covenant-v8.37/` for both files |
| commits that MODIFIED them | `716a60a` (added), `2dfe018` (removed) |
| commits whose TREE CONTAINS them | **16** — every commit between those two |

A correction worth keeping, because it was nearly a mistake in this very
file: only **two** commits modify those files, but **sixteen** commits have
them in their tree. Anyone can read the data from any of the sixteen. A purge
must be verified against every reachable commit, which is what the loop in
step 2 does — not against the two that `git log -- <path>` reports.

`sync_holdings.py` was checked separately and embeds no position data — it
reads the file, it does not carry it. It can stay.

The asymmetry is the whole argument: private -> public is two clicks, any
day. Public -> private does not exist. Deleting a public repo does not recall
forks, clones, caches or third-party mirrors.

## The route, in order. Do not reorder.

### 1. Purge the four paths from history

`git-filter-repo`, not `filter-branch` (deprecated and slow). Install once:
`pip install git-filter-repo`.

Tag a rollback point first — every SHA is about to change:

    git tag backup/pre-purge-2026-08-29 main

Then, from a clean tree:

    git filter-repo --invert-paths \
      --path holdings.txt \
      --path TRADING_POLICY.json \
      --path launch/covenant-v8.37/holdings.txt \
      --path launch/covenant-v8.37/TRADING_POLICY.json

Note `git-filter-repo` **removes `origin` on purpose** so you cannot push a
rewrite by reflex. That is a feature; step 3 puts it back deliberately.

### 2. Verify the purge by measurement, not by assumption

    git log --all --oneline -- holdings.txt TRADING_POLICY.json      # expect empty
    git rev-list --all | while read c; do
        git ls-tree -r --name-only "$c" | grep -qiE 'holdings\.txt|TRADING_POLICY\.json' \
          && echo "STILL PRESENT in $c"
    done                                                             # expect silence

If either prints anything, stop. Do not continue to step 3.

### 3. Do NOT force-push. Delete the GitHub repo and publish fresh.

A force-push leaves the old commits reachable on GitHub by direct SHA URL
until GitHub's own garbage collection runs, and purging those properly means
opening a support ticket. Since this repo is private and the only clone is
this machine, the clean guarantee is cheaper:

1. github.com -> covenant -> Settings -> Danger Zone -> **Delete this repository**
2. GitHub Desktop -> Publish repository -> name `covenant`
3. Decide private-or-public at that dialog, with a history that no longer
   carries the portfolio

That leaves no dangling objects anywhere, because the remote is new.

### 4. Choose a licence before flipping the switch

`docs/sessions/LICENSE_DECISION.md` is a placeholder, not a licence. Under
Berne, no licence means **all rights reserved** — a public repo with no
licence gives readers no rights at all, which is exposure without usefulness.
The three candidates are argued there; AGPL-3.0 is the one that matches the
project's own stated reason to exist ("every node's ethics gate can be read
by the people it judges").

### 5. The thing that is easy to forget: `realdata/`

`LICENSE_DECISION.md` already flagged it and it applies at exactly this step.
`realdata/deep/*.csv` is market data fetched from Kraken's public API; its
**redistribution is governed by Kraken's terms, not by whatever licence you
pick**. Before publishing, either confirm redistribution is permitted, or drop
the CSVs and ship the fetcher (`docs/semantic/fetch46.py`, `verify_csv.py`)
instead. The series are reproducible from the fetcher by design.

Those 15 CSVs were removed from the Claude project on 08-29 for capacity;
they remain tracked here, which is the right place for them either way.

## Operational note discovered while publishing

`device_bash` runs in a Linux VM with no credential helper, so **it can commit
but it cannot push**. Pushes go through GitHub Desktop (or a Windows shell
where Git Credential Manager is authorised). Anything automated that is meant
to keep this remote current has to account for that — committing is not
publishing.
