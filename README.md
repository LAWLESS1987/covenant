# Covenant

A small peer-to-peer ledger with an **ethics gate inside the transaction
path**, built and audited empirically: every claim in this repository was
either observed by running code, or is marked as an assumption.

**v8.37** · source `07e097f3e37f` · 9,846 lines. Version, hash and line count
re-verified 2026-08-27. The suite and check totals that stood here are
**withdrawn** — see [Suite coverage](#suite-coverage).

---

### Start here if you work with AI systems over long periods

**→ [What we found](docs/WHAT_WE_FOUND.md)**

Five AI systems interrogated in one day about a body of work built with them
over months. The finding that generalises past this project: **empty knowledge
reports itself accurately, partial knowledge completes itself silently** — and a
fragment carries no marker saying "fragment." If your work is spread across
several systems, each holds a fragment and each will confidently complete it.

It also documents why models appear to agree across vendors and months (stored
memory retains your claims and discards their corrections), why demanding
honesty produces compliance while supplying a checkable contradiction does not,
and why fluency can never distinguish a sound claim from a generated one. Four
claims that did **not** survive checking are recorded alongside those that did.

No names, no personal data, nothing that requires trusting the author.

**→ [Succession](docs/SUCCESSION.md)** — how this outlives whoever built it, and
why publishing a state root lets someone verify a record they cannot read.

### Credit

The largest single efficiency in this network is **Misha Mahowald's**, from her
1992 *VLSI Analogs of Neuronal Visual Processing*. A neuron does not transmit its
state; when it spikes it emits its *address*, and bandwidth scales with activity
rather than with the size of the array. Applied to block propagation here, that
is 150 bytes where a full push costs 1,476. She died in 1996; the idea is still
working. See [What we found](docs/WHAT_WE_FOUND.md#a-credit-that-belongs-in-the-open).

---

## What it is

Three things, in one process:

- **A ledger.** Proof-of-work blocks, a persisted identity key, staking, gifts,
  and a canonical genesis exported once and shared. Value moves only where
  authorisation exists — net-zero validation alone was found to be insufficient
  and is not what authorises a transfer.
- **An ethics gate.** Every transaction is judged before it is accepted. The
  gate **fails closed**: a node with no reachable judge boots, serves `/chain`,
  peers correctly, reports healthy — and rejects everything. That is deliberate,
  and it is the single most surprising property of running this.
- **A propagation layer built as an address-event network.** A block announce is
  148 bytes because it carries an address, not a payload; the receiver fetches
  what it does not have. Link conductance is Hebbian, redundant announces are
  laterally inhibited, and the anomaly monitor is a spiking detector. The design
  is cited in the source to Mahowald's 1992 VLSI retina, and it is what makes a
  radio bearer arithmetically possible at all (see `docs/` on LoRa: 40 bytes and
  0.30 s of airtime per announce).

## What it is not

- **It does not move real money.** The XRP path is blocked in code behind four
  locks, and the submission path **has never executed on any network**.
- **It has no proven trading edge.** No timing edge survived out-of-sample
  (XRP −2.70% p=0.656; HBAR −7.06% p=0.891; rebalancing +0.45% at p=0.109).
  The regime rule is risk control, never alpha — and on three of ten assets it
  lost to holding. `docs/TRADING_READINESS.md` has the table.
- **It is not multi-operator ready.** Every node so far is one person's. The
  moment a second operator exists, the block-validity rules become a
  protocol-version question — see `docs/PROTOCOL.md`.

## Suite coverage

This file used to open with *33 suites · 1,043 checks green on Linux*. That
number is withdrawn, because the runner it was counted from could not have
produced it honestly.

`run_all_tests.sh` invokes **47** suites. **36** are on disk. The other
**eleven** — `verify_patches`, `verify_auth`, `verify_tx_aer`,
`test_path_pattern`, `test_succession_seal`, `test_ethics_judge`,
`test_golden_ratio`, `test_judge_individuality`, `test_multi_provider_quorum`,
`test_v86_bridge` and `test_v86_loss_tracking` — are named in the runner and
do not exist. Until 2026-08-27 `run` scraped a tally out of stdout, so a
missing suite contributed `0 passed, 0 failed`, printed `NO RESULT`, and left
the failure count untouched. Eleven suites could be absent and the sweep still
ended green. That is the orphan problem from the other direction:
`run_local_sweep.py` had suites on disk that no runner called; this one calls
suites that are not on disk. Both read as coverage and neither is.

A missing suite is now a **failure**, loudly. The consequence is that a full
sweep is currently red by construction, and will stay red until the eleven are
either restored or removed from the runner. That is the correct state: the
alternative is a green run that means nothing.

No replacement total is printed here yet. Putting one up would require a clean
sweep, and a clean sweep is not possible while eleven named suites are
missing. When it is, the number goes back with the platform beside it (§8).

## Start here

| you want | read |
|---|---|
| what is true and what is assumed | `HANDOFF.md` |
| to launch it | `LAUNCH.md`, then `AN_LAUNCH.bat` |
| what each gate means | `docs/GATES.md` |
| how it is deployed and configured | `DEPLOYMENT.md` |
| every finding, in order, with the wrong turns kept | `docs/IMPROVEMENT_LOG.md` |
| what changed between the project and the machine | `docs/DIVERGENCE_REPORT.md` |

## Quick start

```bash
pip install -r requirements.txt
python covenant_unified_v8.py --node-id FOUNDER --export-genesis genesis.json
python launch_check.py                       # twelve gates, changes nothing
python covenant_unified_v8.py --port 5000 --node-id A --genesis genesis.json
```

A node binds **three** ports: `--port` (HTTP), `--port + 1` (P2P), `--port + 11`
(bridge). Space nodes at least 20 apart. `--peers` takes each peer's **P2P**
port, not its API port; get it wrong and both nodes look peered and are not.
Since v8.15 `preflight_port_check` catches both at startup, with the arithmetic
in the message.

`GET /health` is the single status signal. It returns `degraded` plus a
`warnings` list naming exactly what is wrong, the version and source hash of
the process that is answering, and a quorum block describing what the ethics
gate actually is on this node.

## How this codebase was built, and why it reads the way it does

Every fix in here has an adversarial test written from the attacker's side, and
the record keeps the wrong turns. Six of fourteen findings in one audit were
*introduced by the fix for the previous finding*. So:

> A green suite after a fix proves the old bug is gone. It does not prove the
> fix is sound. Every change to the ledger or the guard layer gets its own
> adversarial pass, not just a regression run.

Comments that assert a data flow are checked in the same session they are
written, because one of them was wrong at birth. Claims about the environment
are measured rather than assumed. A check that is permanently red on one
platform is treated as switched off, not as passing. If you contribute, the
conventions are in `CONTRIBUTING.md` and they are not stylistic.

## Licence

**Not yet chosen** — see `LICENSE`. Until it is, this is all-rights-reserved by
default and cannot be redistributed.
