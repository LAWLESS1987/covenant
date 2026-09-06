# Auto-sync

_2026-09-06, asked: "they need to auto sync without push."_

The working branch on this machine is now **main**. Claude pushes main directly after each of its commits. For every other commit -- yours, or the nightly loop's -- a `post-commit` hook pushes main to GitHub at once and moves `sentinel-witness` to the same commit, so the two branches never drift and nobody types a push.

The hook is tracked here as `ops/post-commit.autosync` and is installed with one command, once, by the operator (Claude is not permitted to install standing auto-push automation):

    cp ops/post-commit.autosync .git/hooks/post-commit

If a push fails the hook says so and the commit still stands; `git pull --rebase` and the next commit re-syncs. To stop auto-sync, delete `.git/hooks/post-commit`.
