# The layers, and how to reproduce a result without us

Asked for on 2026-09-19, in the operator's words: *"separate the Covenant core, the
Sentinel Witness verifier, and the experimental record into cleaner layers"* and
*"Prioritize testability over persuasion. Separate the governing rules, verification
harness, and experimental logs into clear layers so others can reproduce results without
the author's interpretation."* Finished 2026-09-25 under his condition *"without adding
any new restrictions."*

## Reproduce it (a fresh clone, no account, no keys)

```
git clone https://github.com/LAWLESS1987/covenant
cd covenant
python covenant_one.py --ci          # the same command public CI runs
python constitution.py verify        # the rules' hash, recomputed
sh verify.sh                         # the same hash, by a second implementation
```

`covenant_one.py` writes two files side by side:

- `ONE_RUN.results.json`: **numbers only.** It holds every suite's state, passed and failed
  counts, every in-place check, the gates, the exit code, the git commit, the core's
  sha256 and the platform. Compare these.
- `ONE_RUN.txt`: the transcript, which is **our interpretation** of the same run. Read it
  if you want our reasons. You do not need it to check our numbers.

`constitution.py verify` and `verify.sh` must both print the hash in
`docs/CONSTITUTION_ANCHOR.json`. They are written independently, and `test_v1` holds them
to agreeing.

## The seven layers (`python tools/layers.py`)

Every tracked file is in exactly one layer, decided by rule. There are 800 files as of
2026-09-25. `python tools/layers.py --list rules` prints any one layer. The map **reports
and never refuses**.

| Layer | What it is | Count |
|---|---|---|
| rules | What the system is bound by: the constitution's protected files, the licences, genesis, the conformance spec, his grants and policies | 17 |
| verifier | What checks a record or the rules from outside: the constitution verifiers and anchor, the Sentinel Witness record checkers, the bundle manifest and seals, the retraction ledger | 34 |
| harness | What runs the checks: every `test_`/`sim_`/`probe_` file, the sweep runner, launch_check, CI | 187 |
| core | The node: chain, gate, judge seats and their models | 27 |
| system | Everything else that runs: the apps, Tetsu, money, the watchdog and self-repair, the learning pipeline, operator tools | 279 |
| record-data | What the running system measured: ledgers, run transcripts, price series, reports | 105 |
| record-prose | What we wrote about it: write-ups, findings, `docs/KNOWN_ISSUES.md` | 151 |

**The Sentinel Witness verifier** is `sentinel_witness/verify_record.py` and
`sentinel_witness/order_claims.py`. They check a record against its order. The rest of
`sentinel_witness/` is the seal service and the trade gate. Those are the money app's
gate, measured as a client of the trader, so they sit in `system`, not `verifier`.

## Rules that live inside code

These are normative, but they are code constants, not files. The constitution's hash
does not cover them. Only the bundle manifest does, and a change there is visible but
never named as an amendment. Where they are:

- `DIVINE_PRINCIPLES`, `CORE_COVENANT` and `AGENT_SYSTEM` are in `covenant_unified_v8.py`.
- The two-seat resolution table (R1-R4) is in `judge_resolve.py`.
- `HOLD_ONLY` and the money caps are in `guards.py`.
- Rule 5's `MIN_SIGNALS` is in `signal_ledger.py`.
- The teacher panel's `RULE` is in `covenant_teacher_panel.py`.
- The immunity's `DEFAULT_PER_DAY` is in `covenant_immunity.py`.

## Why no file moved

Measured on 2026-09-25 by five read-only passes. Moving files would have broken these:

- The phone build (`stage.sh`) refuses any subpath in its allowlist.
- The pre-commit hook's held-copy sync matches the core by its exact root path.
- The watchdog's import fingerprint reads root paths, and falls silent if they are gone.
- The sweep stages the root plus eight named folders.
- 139 of the 163 root suites import the core flat.
- The constitution verifiers keep three hand-kept lists of the protected files.
- The seal root hashes each file's relative path.

Two moves would have been **new restrictions**. The grant files are read at fixed paths,
and a missing grant means refusal. The issue register is read by the loop that teaches
the students from our own work, and a missing file means they silently learn nothing. So
the layers are declared, not moved.

## What a fresh clone cannot reproduce (said, not hidden)

- **The live judging policy.** `ops/quorum_policy.json` is gitignored. The clone runs the
  example policy, and JR6/G4.4b say NOT RUN where it is absent.
- **The running mesh.** The gates about live nodes, keys and databases (G7, G9, G12, A124)
  need this PC. `--ci` reports those gates and does not let them decide the exit code.
- **The PC's staged green is not a fresh clone's green.** The sweep copies all of `ops/`,
  gitignored files included. Only the public CI run is a fresh-clone measurement.
- **Two suites count NOT RUN as passed**: `test_wb1_web.py` and
  `test_qw1_quiet_everywhere.py`. An offline run inflates their totals. This is recorded in
  A220, not yet fixed.
- **`tools/sentinel_baseline.py` is red and nothing runs it.** Its frozen size for the seal
  service no longer matches. Recorded, not yet fixed.
