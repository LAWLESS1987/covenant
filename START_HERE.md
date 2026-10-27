# Start here

This folder has 280-odd files and about twenty-five `.bat` launchers, most of
them superseded. **You need six of them.** Everything below is a double-click.

## The six

| double-click | what it does | how long | touches anything? |
|---|---|---|---|
| **`GO.bat`** | commit + merge, then publish to GitHub (private) | ~1 min | git only |
| **`ONE.bat`** | the full verification sweep, every suite, both integrity checks, the gates, live state | ~16 min | **no** |
| **`ONE_UP.bat`** | bring the nodes up — gates first, restart refused *before* the stop if a gate blocks | ~2 min | yes, restarts nodes |
| **`ONE_RETEST.bat`** | re-run only the not-clean suites, alone and twice (M18/M20) | ~2 min | **no** |
| **`ONE_PROBE.bat`** | measure what a refused vs dead TCP connect costs on this box | ~30 s | **no** |
| **`AP_CONSOLE.bat`** | the operational console on 127.0.0.1:5199 (read-only unless `--armed`) | — | no, unless armed |

Everything each one prints also lands in a `.txt` beside it — `ONE_RUN.txt`,
`ONE_UP.txt`, `GIT_SETUP.txt`, `GITHUB_PUSH.txt`, `PROBE_WIN_CONNECT.txt`. Those
are **outputs**: gitignored, and on `verify_bundle.py`'s `OUTPUTS` list. If you
ever add a launcher that writes a report here, add its report to **both** lists
in the same commit. That has been the same bug four times.

## In what order

    something changed        ->  ONE.bat        (is it still true?)
    a suite came out red     ->  ONE_RETEST.bat (is it red on its own, twice?)
    the chain is down        ->  ONE_UP.bat     (gates, then restart)
    work is finished         ->  GO.bat         (commit, merge, publish)

`ONE.bat` before `ONE_UP.bat` before a launch. A green CI tick on GitHub is
**not** a launch: it runs the Linux half only, and three suites behave
differently on Windows — a refused TCP connect costs 0.0 ms there and 2,045 ms
here.

## The rest of the .bat files

`AA_` through `AP_` are the older single-purpose launchers. They still work and
nothing has been moved, because `verify_deploy.py` calls `AB_RESTART_NODES.bat`
by name and `test_3node_config.py` asserts that `covenant_prod.bat`,
`AB_RESTART_NODES.bat` and `covenant_watchdog.py` agree about the three nodes.
**Moving them would break a suite and a launcher**, so they stay. Use the six
above; reach for the others only when one of them tells you to.

## If you are new to the folder, read in this order

1. `START_HERE.md` — this file
2. `UNISON.md` — how two people work here without clobbering each other
3. `LAUNCH.md` — what a launch actually requires
4. `README.md` — what the thing is

## When something refuses

Every launcher here refuses rather than guessing, and each refusal names its own
fix. Three you will meet:

* **"BLOCKED"** from the gates — read the `BLOCKED` line; it carries the exact
  command that clears it. `ONE_UP.bat` refuses the restart *before* stopping
  anything, so a blocked gate never leaves you with a stopped chain.
* **"Another git process seems to be running"** — a stale `.git/*.lock`.
  `GIT_SETUP.bat` clears stale locks itself, and refuses any lock under 60
  seconds old in case a real git process owns it.
* **"the working tree is dirty"** from the push — it still prints its whole
  diagnosis; only the push is refused. Run `GO.bat` instead, which does both
  steps in the right order.

## Recovering from anything git-shaped

    git reset --hard refs/backup/2026-08-27/main
    git for-each-ref refs/backup

Every branch head is tagged before any bulk operation.
