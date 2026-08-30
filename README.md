# Covenant

A small peer-to-peer ledger with an **ethics gate inside the transaction
path**, built and audited empirically: every claim in this repository was
either observed by running code, or is marked as an assumption.

**v8.40** · source `c4f1b285942a` · 10,633 lines · **60 suites, 1,765 checks,
0 failed** on win32. Version, hash, line count and totals re-verified
2026-08-30 against a live restarted chain. What that number does and does not
cover is in [Suite coverage](#suite-coverage), and it is worth reading before
quoting it.

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

- **It does not move real money — and here is the shape of that, because the
  short version misleads in both directions.** The XRP path is blocked behind
  four locks and its submission path **has never executed on any network**:
  there is no testnet proof and no mainnet policy on disk.

  What is easy to miss is that this repository *does* hold Kraken and Coinbase
  order adapters (`venues.py`), a planner (`covenant_trader.py`), and a
  scheduled task that runs the planner **daily, without a human**. Every order
  it builds goes to the venue's own dry-run endpoint — Kraken `validate=true`,
  Coinbase `/orders/preview` — which prices and rejects an order without
  booking it. The trader is disarmed; armed, it would still be bounded by a
  halt file, $25 per order, $50 per day, two orders per day, and a requirement
  that the decision be sealed to the chain first.

  So *"it cannot trade"* is false, and *"it is trading"* is false. What stands
  between them is a commitment — `docs/CONSTITUTION.md` II.1 — rather than an
  absence of capability, and a promise whose shape you cannot see is not a
  promise but a reassurance. It is a live state that one config flag changes,
  so it is measured rather than asserted: **`python money_posture.py`**. That
  reads no key, places nothing, and arms nothing. If it ever prints ARMED, the
  clause is being broken and these documents are out of date.
- **It has no proven trading edge.** No timing edge survived out-of-sample
  (XRP −2.70% p=0.656; HBAR −7.06% p=0.891; rebalancing +0.45% at p=0.109).
  The regime rule is risk control, never alpha — and on three of ten assets it
  lost to holding. `docs/TRADING_READINESS.md` has the table.
- **It is not multi-operator ready.** Every node so far is one person's. The
  moment a second operator exists, the block-validity rules become a
  protocol-version question — see `docs/PROTOCOL.md`.

## Suite coverage

**60 suites · 1,765 checks · 0 failed**, win32, 2026-08-30, against the live
chain after a restart. `python covenant_one.py` reproduces it and writes a
transcript.

This section previously said the opposite, and that history is kept because it
is the more useful half.

It once opened with *33 suites · 1,043 checks green on Linux*. That was
**withdrawn** on 2026-08-27, because the runner it came from could not have
produced it honestly: `run_all_tests.sh` named **47** suites of which **36**
existed, and its helper scraped a tally out of stdout — so a missing suite
contributed `0 passed, 0 failed`, printed `NO RESULT`, and left the failure
count untouched. Eleven suites could be absent and the sweep still ended green.
All eleven are now gone from the runner, and a missing suite is a **failure**,
loudly.

**What the current number covers, said so it cannot be quoted as more.**

- It is **win32**. Three suites behave differently on Linux — a refused TCP
  connect costs about 0.0 ms there and about 2,045 ms here. CI runs the same
  file on ubuntu for that reason, and a green tick in either place does not
  speak for the other.
- The **launch gates are reported, not passed**. A CI runner has no ethics
  judge, no nodes, no identity keys and no delivery manifest, so those gates
  cannot pass there. They are printed in full and are not allowed to decide the
  exit code, because a check that is always red teaches people to skim past it.
- **Two suites are deliberately off**, on the record with reasons:
  `test_xrp_live.py` needs a funded testnet account, `test_covenant_app.py`
  needs the chain stopped. No green run speaks for either.
- A **suite the runner names but is not on disk**, an **orphan on disk that no
  runner calls**, a suite **kept out of the delivery by an ignore rule**, and a
  **missing declared dependency** are each their own named outcome, and none is
  ever folded into a pass. All four exist because each happened here first.

**The failure that produced the last two.** From 2026-08-29 to 2026-08-30 CI was
red, and not for a defect in the code. `.gitignore`'s `*_secret*` rule silently
swallowed `test_e1_secret_egress.py` — the regression suite proving a credential
cannot escape through an error message, whose every "secret" is a labelled
fixture. It existed on the development machine, so local runs passed. It was
never committed, so CI checked out a tree without it and correctly called it
ABSENT. The rule matched on the **name** and not the **nature**, and a file
called `*_secret*` is at least as likely to be the check that no secret escapes
as it is to be a secret.

The coverage phase could not catch it either, because it asked `os.path.isfile`
— *is this on THIS disk* — and never *is this in what I am about to ship*. The
check written to stop a runner naming an absent suite could therefore only fire
on a machine where the mistake had not been made. It now asks git as well, and
separates **IGNORED** (an ignore rule keeps it out of the delivery: reddens the
run, names the rule and its line number) from **UNSHIPPED** (merely uncommitted:
loud, but does not redden — otherwise every in-progress suite turns the run
amber, and permanent amber is skimmed past).

**And one more, found while writing this paragraph.** An earlier run today
reported *1,744 checks, 0 failed, RESULT: PASS* — and the same transcript said
`folder integrity  test_p18_version_collision.py=FAIL rc=1` a few lines above
it. Both sentences were in one file. `--ci` discarded **every** in-place
failure (`... if not args.ci else []`), so a real version collision —
`pending-v8.38/covenant_unified_v8.py` declaring `VERSION = "v8.40"` with
different bytes from the root core — had been suppressed in every CI run since
the flag existed. The blanket exclusion was never needed: the one in-place
check that genuinely cannot apply to a copy is the delivery manifest, and
`--transported` already reports that as N/A. A version collision is a fact
about a tree, and a copy is a tree. Failures now count everywhere, verified by
planting a collision and confirming a `--ci` run turns red.

Separately, four suites had been failing for one missing declared dependency.
`xrpl-py` is in `requirements.txt` and simply was not installed, so a SECURITY
suite read 14/16 and looked like a regression. The runner named four symptoms
and no cause. `preflight_deps.py` now names a missing dependency **and the
suites it will take down with it**, found by walking the import graph — because
its first version reported only the file that imports `xrpl` directly and
missed all four that reach it through `covenant_xrp_mainnet`.

## Start here

| you want | read |
|---|---|
| what is true and what is assumed | `HANDOFF.md` |
| to launch it | `LAUNCH.md`, then `AN_LAUNCH.bat` |
| what each gate means | `docs/GATES.md` |
| how it is deployed and configured | `DEPLOYMENT.md` |
| every finding, in order, with the wrong turns kept | `docs/IMPROVEMENT_LOG.md` |
| what changed between the project and the machine | `docs/DIVERGENCE_REPORT.md` |
| **how authority is distributed, and what it survives** | **`docs/GOVERNANCE.md`** |
| what binds whoever runs it | `docs/CONSTITUTION.md` |
| how independent peers relate, without a centre | `docs/FEDERATION.md` |
| what happens when a person stops | `docs/SUCCESSION.md` |

### A debt to the Mahowald Prize shortlist

The 2025 Misha Mahowald Prize shortlist was read here for what it implies, not
for what it builds, and one idea runs under all three entries: **canonical
meaning survives incidental form.**

- **Jens Egholm Pedersen** (KTH), *Neuromorphic Intermediate Representation* —
  stop comparing implementations, compare a canonical description of the
  computation. `conformance.py` and the CONFORMANT verdict in `federation.py`
  are that idea applied to governance: a fork can now prove it agrees without
  running these exact bytes.
- **Mark Iskarous** (Johns Hopkins) — a texture representation invariant to
  force and speed. The identity survives, the incidental variation is
  discarded. The same move fixed two real bugs here in one day: a heading's em
  dash counted as part of what was signed, and a level's value depending on how
  deep it sat.
- **Kerem Çamsarı and the OPUS Lab** (UC Santa Barbara) — massive parallelism,
  asynchronous dynamics, sparsity. Agreement with no clock and no centre, which
  is the same problem a federation has.

None of them had this project in mind. The debt is recorded because taking an
idea and not saying where it came from is the thing this repository is about.

### Checking it without trusting it

The point of the list above is that none of it has to be taken on faith. Three
verifiers compute the same constitution hash in three languages sharing no
code, so no single runtime — and no single implementation — has to be believed:

```bash
python constitution.py verify      # needs Python
sh verify.sh                       # needs neither Python nor Windows
powershell -File verify.ps1        # needs neither Python nor a Unix shell
python redundancy.py               # how many carriers at every level, and what they share
```

They have already disagreed once, over whether a heading's em dash was part of
what was signed. That disagreement was the finding, and it was worth more than
any one of them alone.

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
