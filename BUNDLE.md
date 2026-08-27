# What is in this bundle, and where each file came from

**280 files.** The union of two places that each held part of the system and
neither of which held all of it.

```
covenant-v8.37/
  *.py *.bat *.sh *.md          the node, the suites, the operational scripts.
                                Flat, because run_all_tests.sh and
                                run_local_sweep.py expect them beside the core.
  AN_LAUNCH.bat                 NEW. The one double-click: gates, then restart.
  launch_check.py               NEW. Twelve gates. Changes nothing.
  verify_bundle.py              NEW. Hash census over everything shipped.
  MANIFEST.sha256               NEW. Regenerated over all 280 files.
  LAUNCH.md                     REWRITTEN. Old one kept in docs/variants/.
  AB_RESTART_NODES.bat          PATCHED. P17 guard before the first taskkill.
  AL_DASHBOARD.bat              FIXED. Was LF-only in a CRLF folder, and it is
                                built out of goto labels.

  docs/                         the loop's memory — 23 documents that existed
                                ONLY in the project and were never on the
                                machine, including IMPROVEMENT_LOG.md and
                                RUN_LOG_ARCHIVE.md.
  docs/semantic/                the cross-register pipeline, its corpus
                                manifests, and the null results.
  docs/results/                 sweep and measurement outputs, dated.
  docs/variants/                every file that existed in two versions. Both
                                are kept. DIVERGENCE_REPORT.md says which won.
  ops/                          NEW. fix_key_acl.bat, owner_only.py,
                                setup_mainnet_policy.py. Applies controls;
                                opens nothing.
  quant/ realdata/ phone/ vendor/   unchanged.
```

## What is deliberately NOT in here

| | why |
|---|---|
| `*.db`, `*.db-shm`, `*.db-wal` | the chain. State, not source. |
| `*.db.key` | **the operator credential and the genesis mint key.** A key must never travel in an archive, a manifest, or a chat message. |
| `logs/`, `__pycache__/`, `.venv/` | runtime and environment. |
| `KrakenDesktopInstaller.msi` | 88 MB, and not part of this system. |
| `daily_state.json` | it is written on every run, so keeping it beside the source would invalidate the seal every day and teach its operator to ignore a seal that is usually wrong. It belongs in `~/.covenant/`. A sample copy is in `docs/results/`. |

## Verifying it

```
python verify_bundle.py       # 0 = every file hashes to the manifest
python launch_check.py        # 12 gates; --json for the machine-readable form
```

`verify_bundle.py --write` regenerates the manifest — do that deliberately,
after an edit you meant, and never to make a red check go green.

## Assembled where, and what that means

This bundle was assembled in a **Linux** sandbox. Every `.py` in it byte-
compiles and every `.sh` parses, the CRLF of every `.bat` was checked against
its neighbours, and `ops/owner_only.py`'s mutation test passes in both
directions **on Linux**. None of that is a Windows result. The suites have not
been re-run on win32 since 2026-08-24, and three pieces of work — A23, A3-send
and P14's self-drift check — have never executed there at all.
