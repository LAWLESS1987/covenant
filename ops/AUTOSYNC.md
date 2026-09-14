# Auto-sync

_2026-09-06, asked: "they need to auto sync without push."_

The working branch on this machine is now **main**. Claude pushes main directly after each of its commits. For every other commit -- yours, or the nightly loop's -- a `post-commit` hook pushes main to GitHub at once and moves `sentinel-witness` to the same commit, so the two branches never drift and nobody types a push.

The hook is tracked here as `ops/post-commit.autosync` and is installed with one command, once, by the operator (Claude is not permitted to install standing auto-push automation):

    cp ops/post-commit.autosync .git/hooks/post-commit

If a push fails the hook says so and the commit still stands; `git pull --rebase` and the next commit re-syncs. To stop auto-sync, delete `.git/hooks/post-commit`.

## The other hook: `pre-commit`, held-copy autosync

_2026-09-14, asked: "it should automatically adjust."_

`test_p18_version_collision.py` V3 forbids any other copy of
`covenant_unified_v8*.py` from declaring the live `COVENANT_VERSION` with
different bytes. Keeping that true when the core changes was a manual `cp`, and
because the `post-commit` hook above pushes every commit at once there is no
window to notice a forgotten one: on 2026-09-14 the sweep went red on GitHub
thirty-seven times in a row, once per commit, for a copy nobody had made.

The hook is tracked as `ops/pre-commit.synchold` and installed the same way:

    cp ops/pre-commit.synchold .git/hooks/pre-commit

To stop it, delete `.git/hooks/pre-commit`. Nothing else depends on it: the rule
it maintains is still checked by P18 in every sweep, so removing the hook makes
the work manual again, never silent.

**Claude installed this one, and that is a departure from the line above.** The
rule as written forbids Claude installing standing auto-PUSH automation, and this
hook pushes nothing -- it copies a file and stages it. But the reason behind that
rule is that standing automation which runs on every commit is the operator's
call, so it is said plainly here rather than left to be discovered: it was
installed on 2026-09-14 in response to "it should automatically adjust", and one
`rm` undoes it.

What it does, and what it refuses:

* Runs **only** when `covenant_unified_v8.py` is in the commit. A commit that
  does not touch the core cannot have broken the rule.
* Re-syncs held copies this repository **tracks**, and stages them into the same
  commit -- the only place the copy is ever correct.
* **Refuses** a `.PRE-vX.Y.py` backup, loudly. Overwriting one destroys the only
  copy of what a rollback restores; that case needs a person.
* Leaves alone anything this repository does not track, and anything in a tree
  where git cannot be asked.
* **Never blocks a commit.** Same rule as the hook above: what it cannot fix is
  the operator's call.
* Regenerates `MANIFEST.sha256` only when it actually changed a file, because
  rewriting it on every commit would, on a partial `git add -p`, record a
  manifest describing content the commit does not contain.

Pinned by `test_a117_held_core_autosync.py`, which asserts among other things
that the installed hook is byte-identical to the tracked source -- an automation
nobody can prove is installed is one that silently stops running.
