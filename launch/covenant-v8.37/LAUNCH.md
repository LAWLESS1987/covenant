# Covenant — Launch

**v8.37 · source `07e097f3e37f` · 9,846 lines · assembled 2026-08-26**

This replaces the 2026-08-20 runbook, which is kept verbatim at
`docs/variants/LAUNCH.md.PC-COPY-2026-08-20`. Read `HANDOFF.md` for what is
verified and what is assumed; read this for what to do.

---

## The one command

```
AN_LAUNCH.bat
```

It runs `launch_check.py` first — twelve gates, **changing nothing** — and
only hands over to `verify_deploy.py` (hash the delivery, then restart) if
nothing is BLOCKED. `AN_LAUNCH.bat --check` stops after the gates and touches
nothing at all.

That order is the whole design. This project's repeated failure is not a bug
in the ledger; it is a claim that was asserted once and drifted invisibly. So
every gate reports **PASS**, **BLOCKED** or **UNKNOWN**, and UNKNOWN is never
folded into PASS — a node that cannot be reached is UNKNOWN, not OK.

Exit codes: `0` all pass · `1` something blocked, do not launch · `2` nothing
blocked but something unmeasurable, **which is not a pass**.

---

## State at the time this was assembled

Measured on the machine, not inferred. Three claims, and they drift
independently (M38):

| claim | value |
|---|---|
| project | v8.37 `07e097f3e37f` |
| disk | v8.37 `07e097f3e37f`, 9,846 lines — delivered and verified 08-26 19:20 |
| **running** | **v8.35 `1207bd2e7dc5`, both nodes** — the restart has not happened |
| watchdog | dead. Last line 20:01:45Z against a ~60-second bound; it was still writing *"balance agrees"* when it stopped |

So the gap is exactly one double-click, and it always was. What changed today
is that the double-click can now refuse.

---

## What runs before anything is stopped

`AB_RESTART_NODES.bat` used to stop the nodes and *then* call
`covenant_prod.bat` — which correctly aborts if Ollama is not answering on
11434, because a judge that cannot be reached fails **closed** and a node in
that state rejects every transaction while looking healthy.

Composed, a stop that always succeeds with a start that can refuse is not a
restart. It is a stop. On a box measured at ~3.5 GB free against a 5.2 GB
model, "Ollama is not answering right now" is an ordinary state.

**Fixed (P17):** the restart now probes 11434 *before* the first `taskkill`
and refuses, exit 3, writing the reason to `NODE_RESTART.txt`. It can only
ever decline to act.

---

## Launch sequence, if you want the steps rather than the button

1. **A judge, or nothing works.** No key and no local model means the gate
   fails closed: the node boots, serves `/chain`, peers, reports healthy —
   and rejects 100% of transactions. `COVENANT_JUDGE_PROVIDERS=local` with
   Ollama up, or `ANTHROPIC_API_KEY` set. The `mock` provider needs
   `COVENANT_INSECURE_MOCK_JUDGE=1` as well, prints a banner, and adversarial
   transactions are known to pass it — a test rig, never a launch. → gate G5
2. **One genesis for the whole network**, exported once and shared. Without
   it nodes cannot converge and each mints itself 1000. → G4
3. `AN_LAUNCH.bat --check` — read every gate.
4. `AN_LAUNCH.bat` — verify the delivery by sha256, then restart.
5. `python run_local_sweep.py` — the win32 sweep, ~45 min, 33 suites. Three
   things have never executed on Windows and are waiting on it: **A23**
   (v8.36), **A3-send** (v8.37), and **P14**'s self-drift check.
6. `python launch_check.py` again. G9 should now read `== disk` for both
   nodes and G10 should show the watchdog writing.

---

## Real money is behind four locks, and this bundle opens none of them

`python ops/setup_mainnet_policy.py` walks them and reports. It can create the
*empty* policy template and nothing else.

1. **Testnet proof.** `require_testnet_proof()` refuses without
   `xrp_testnet_proof.json`. The XRP submission path **has never executed on
   any network** — `autofill`, `submit_and_wait` and the reserve check are
   written and reviewed, never run. Only `test_xrp_live.py` on a networked
   machine clears it. Five minutes and a faucet account.
2. **Allowlist.** One address, added by you, checked against its source.
   Ceilings low. A signing key alone must not be enough to move funds
   somewhere new.
3. **File permissions.** The policy must be owner-only. **On Windows this is
   currently unsatisfiable** — `os.stat().st_mode` reports `0o666` whatever
   the ACL says, so `MainnetPolicy.load` refuses on that machine
   unconditionally (**P9**). `ops/fix_key_acl.bat` applies the real NTFS ACL;
   the code change that would let the guard *read* it is written, mutation-
   tested and **not applied** — see `docs/P9_WINDOWS_OWNER_ONLY.md`. It
   changes a security control, so it is yours to approve.
4. **Destination tags**, required by default. Sending to an exchange without
   one means the ledger reports success and the funds are unrecoverable.

Limits are enforced by reserve-then-settle under a file lock. A crash leaves
the hold standing, deliberately: `reconciliation_report()` shows orphans and
`release()` is manual and must stay that way.

---

## Decisions that are yours, not the loop's

None of these are bugs. Each is a real fork in the design where a model
picking for you would be the wrong outcome.

| | question |
|---|---|
| **A10** | which genesis state is canonical — locked or spendable? The two paths produce different ledgers from the same block hash |
| **A16** | staking is node-local, so yield diverges across nodes. Option A (on-chain, escrow counterparty) is recommended and written up in `docs/YIELD_ON_CHAIN_DESIGN.md` |
| **B4** | is the ethics verdict a **consensus rule** or an **admission policy**? Measured: this is worth ~100× the system's energy at scale — one verdict is ~512 J against ~13.6 J to mine the block it sits in, and consensus means every node pays it and needs 5.2 GB resident to take part |
| **A7 / A8** | block-size and PoW validity rules; block timestamps are unbounded; registration PoW is not re-checked on the block path |
| **A12** | may a real message be skipped to a suspect peer, or only heartbeats? And which of the two v8.23 sources is canonical |
| **P2 / P3** | 12 suites in `run_all_tests.sh` that exist nowhere; folding the port-kill into `covenant_prod.bat` |
| **P9** | the code change above |
| **C5** | try the APK, answer `docs/ANDROID_GUARD.md` §7 |
| **R1** | LoRa: hardware, stack (raw SX1262 or Meshtastic recommended), and goal. A23 must become per-bearer first or every radio peer is marked failing on its first send |

---

## Known-open, measured, not fixed here

- **A24** — a peer can flood one anomaly kind and evict every real record from
  the 5,000-event buffer. Architectural, predates every guard, reproduced on
  both v8.36 and v8.37. The fix changes what the spike detector sees, so it
  does not ship in the same hour as a propagation.
- **A25** — `/health`'s `source_sha256` contains 12 characters, not a sha256.
  The contract is correct and pinned; only the name lies.
- **P15** — ollama is the fourth long-lived process and nothing reports its
  identity. Re-tagging the model changes what the gate decides and no surface
  says anything changed.
- **P13** — narrower than filed: the pre-A20 fixture *is* on the PC
  (`covenant_unified_v8.PRE-v8.33.py`, v8.32, zero A20 markers), so C1–C5 run
  there. The gap is a fresh sandbox.

---

## Rollback

Every delivery leaves its predecessor beside it. `covenant_unified_v8.PRE-*.py`
goes back to v8.29; `covenant_watchdog.PRE-*.py` and the `.PRE-P7/P8/P10`
suites likewise. To roll back: copy the `PRE-` file over
`covenant_unified_v8.py`, run `python verify_bundle.py` (it will report the
change, which is correct), then `AB_RESTART_NODES.bat`. No database is ever
deleted by any script in this bundle except `covenant_go.bat`, which is a test
rig and says so.
