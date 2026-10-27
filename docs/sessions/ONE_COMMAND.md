# ONE COMMAND — `covenant_one.py` / `ONE.bat`

2026-08-27. One entry point replacing "which of AA..AP do I run". The same file
is the command on Windows and in the cloud, so a PC transcript and a cloud
transcript are the same task list executed by the same bytes, and a difference
between them is a difference in the *machine*, not in the runner.

    ONE.bat                     identity, coverage, integrity, gates, sweep,
                                live state. Touches nothing. ~16 min on win32.
    ONE.bat --quick             everything except the sweep. ~2 min.
    ONE.bat --check             gates only. Touches nothing at all.
    ONE.bat --restart           ...then verify_deploy.py (hash, restart, confirm)
    ONE.bat --dashboard / --daily / --console / --all
    ONE_RETEST.bat              the not-clean suites, ALONE and TWICE (M18/M20)

    python3 covenant_one.py --transported     the cloud mirror

Everything printed also lands in `ONE_RUN.txt`, including the failing lines
**and** the tail of every suite that did not come out clean.

## The three rules it is built on

1. **Nothing is silent.** Absent, over-budget, deliberately-off and
   orphaned-on-disk are first-class outcomes with their own loud lines. None is
   ever folded into a pass. Exit 2 (INCOMPLETE) exists so "nothing failed" can
   never be reported as "everything passed".
2. **Nothing is touched unless you ask.** The default run is read-only plus the
   sweep in a scratch copy. Restart/console/dashboard/daily are behind flags,
   and the gates run first (P17).
3. **It says what it is.** It prints its own version and the sha256 of its own
   source at the top of every run (P11/P18 applied to the runner itself). The
   two runs compared below both name `734ab07d0592`.

## Why it exists — what the old runners were not measuring

`run_all_tests.sh` **names eleven suites that are not on disk**:

    test_ethics_judge.py      test_golden_ratio.py       test_judge_individuality.py
    test_multi_provider_quorum.py   test_path_pattern.py  test_succession_seal.py
    test_v86_bridge.py        test_v86_loss_tracking.py  verify_auth.py
    verify_patches.py         verify_tx_aer.py

Its `run()` helper swallows stderr (`2>/dev/null`), prints `NO RESULT`, and adds
**0 to TOTAL and 0 to FAILED** for each — so the script can exit 0 having never
executed a fifth of what it lists. That is M30/P14 exactly: a check that stopped
checking still reads as coverage. `covenant_one.py` reports absence loudly and
refuses to call such a run a pass.

The two runners also disagreed in the other direction: `test_w2_sandbox_platform.py`
and `test_y1_stake_divergence.py` were in `run_local_sweep.py` and not in
`run_all_tests.sh`. The new table is the union, and a COVERAGE phase diffs it
against the disk both ways on every run.

## What the two runs found

Same runner bytes (`734ab07d0592`), same 40 suites, same day.

| | cloud (Linux 6.18, py3.11.15) | PC (Windows 11, py3.12.10, .venv) |
|---|---|---|
| suites run | 40 | 40 |
| checks passed | 1270 | 1257 |
| checks failed | **0** | **3** |
| not clean | sim_yield_safety (informational) | `test_a23_ack_health` 22/24, `test_w2_sandbox_platform` 9/10 |
| gates | BLOCKED (G1, G5 no judge) | BLOCKED (G1 only) — 8 PASS / 1 BLOCKED / 3 UNKNOWN |
| elapsed | 12.7 min | 16.5 min |

### 1. Two win32-only failures, both reproduced ALONE and TWICE

**`test_a23_ack_health` — S3, the dead-peer/refused-peer cost gap does not
exist on Windows.** Measured on the PC: refused **1.053 s** vs dead **1.12 s**.
On Linux a refused connect is effectively free, and that gap is the whole basis
of A12's "508 → 11,520 dead-peer headroom": the escalation is paid for by
refused peers costing nothing. On win32 they cost about a second, so for this
class of peer **A12's headroom argument does not hold on the platform
production runs on**. This is M29/M34 in its most literal form — the number was
derived where the checks are green, not where the nodes live.

**`test_w2_sandbox_platform` — W2.7 `node w2off came up -- no /health`.**
Reproduces twice, alone. Windows-only; the other nine W2 checks pass and
W2.5/W2.6 correctly SKIP for lack of `fork`.

### 2. Gate G1 has been structurally impossible to pass

`MANIFEST.sha256` line 3 is:

    e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  4]

`e3b0c442…b855` is the sha256 of the **empty string**, and the filename is
literally `4]` — a zero-byte file, almost certainly a stray shell redirection,
captured when the manifest was written and since deleted. It can never hash
again, so `verify_bundle.py` reports CHANGED/MISSING for ever and **G1 is a
permanent BLOCKED**. A gate that can never go green teaches its reader to skim
it (M34), and G1 is the one gate standing between this bundle and a launch.

The other five are ordinary drift from today's edits (12:24–12:29) against a
manifest written at 04:11: `covenant_xrp_mainnet.py`, `run_all_tests.sh`,
`test_security_audit.py`, `test_xrp_mainnet.py`, `test_xrp_signer.py`.

**Not fixed here on purpose.** `verify_bundle.py --write` would make G1 green by
asserting rather than measuring, which is the move this whole discipline exists
to refuse. It is L's call whether those five edits are the delivery.

### 3. A24 / A24b never reached the machine

`run_all_tests.sh` names `test_a24_anomaly_eviction.py`. It exists **nowhere on
the PC**, and neither does the fix it tests: grep the deployed
`covenant_unified_v8.py` (v8.37, `07e097f3e37f`) for `_fair_share`,
`_compact_locked` or `last_eviction_age_seconds` and you get **zero hits**. A24
landed in the project as v8.38 and A24b as v8.39; neither was propagated. The
anomaly buffer on the running core still evicts oldest-overall — the exact
condition A24 was written to close.

It is on the runner's SWITCHED-OFF record with that reason and its remedy
(propagate the v8.38+ core, then move the line into `SUITES`), rather than wired
in to stand permanently red.

`test_p18_version_collision.py` was the other project-only orphan; it has been
restored to the PC and passes **20/20 on both platforms**, scanning 20 copies of
the core in the real tree.

### 4. State of the machine, as measured

Nodes A (5000), B (5020), C (5060) are **down**. Ollama is **up**. The watchdog
last wrote 238 minutes ago — "the control built to catch deployed-is-not-running
is itself not running" (P14, again).

## Three defects the first run exposed in the runner itself

Recorded because a tool that has only ever seen one tree has not been tested.

* **Integrity measured the copy.** `verify_bundle.py` and P18 were in the sweep,
  which runs in a scratch copy — so they answered about the copy (55 changed vs
  the PC's real 6). They now run in place, in a separate INTEGRITY phase.
* **The coverage report miscounted itself.** In-place suites were excluded from
  "listed", so the runner reported its own integrity phase as an ORPHAN.
* **The failure report hid the failure.** Only the last 18 log lines were
  printed, so `test_a23` showed eighteen PASS lines under the word FAIL. It now
  prints the failing lines first, then the tail.

Also added: `--transported`, so the cloud mirror reports the manifest check N/A
instead of red (a copy cannot be the delivery), and an INFORMATIONAL class so
`sim_yield_safety.py` reads `info` rather than `NO RESULT`.

## Open, in order

1. Decide G1: are those five edits the delivery? Then `verify_bundle.py --write`
   — and remove the `4]` phantom either way.
2. A23 S3 on win32: A12's headroom needs re-deriving on Windows, or the
   escalation needs a cost model that does not assume a free refusal.
3. W2.7 on win32: why `w2off` never answers `/health`.
4. Propagate the v8.38/v8.39 core, then wire `test_a24_anomaly_eviction.py` in.
5. Still not covered, and a green run does not cover them: `test_xrp_live.py`
   (needs a funded testnet account; mainnet stays BLOCKED until it runs once)
   and `test_covenant_app.py` (needs the chain stopped).
