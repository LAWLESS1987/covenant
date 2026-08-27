# Covenant

A small peer-to-peer ledger with an **ethics gate inside the transaction
path**, built and audited empirically: every claim in this repository was
either observed by running code, or is marked as an assumption.

**v8.37** · source `07e097f3e37f` · 9,846 lines · 33 suites · 1,043 checks
green on Linux.

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
