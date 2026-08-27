# The loop was open at the PC end — closed 2026-08-22, and what it had cost

## The finding

Every run since 2026-08-21 05:35 ended the same way: *"**L: copy
`covenant_unified_v8.py` into `C:\Users\Lawre\covenant`** beside
`covenant_path_pattern.py`."* Sixteen runs, fourteen node versions, twenty-five
closed backlog items. M5 recorded why the loop could not do it itself —
scheduled cloud runs have no device bridge — and treated that as settled.

It was never checked. This run checked it:

```
PC   covenant_unified_v8.py   7774 lines   54955648…   mtime 2026-08-20 23:33
project                       8609 lines   76d2c54e…   v8.28, 2026-08-22 07:56
```

`grep` on the PC copy, for the symbol each closed item names (M6's own rule):

| item | symbol | on the PC |
|---|---|---|
| A2 port preflight (v8.15) | `preflight_port_check` | **0** |
| A5 size coherence (v8.17) | `serialized_size` | **0** |
| A1/K2 tip gossip (v8.20) | `_gossip_tip` | **0** |
| A12 dead peers (v8.23) | `_delivery_order` | **0** |
| A13 one-way sync (v8.25) | `_send_announce` | **0** |
| A14 boot probe (v8.26) | `_bootstrap_round` | **0** |
| A15 exchange deadline (v8.27) | `MAX_EXCHANGE_S` | **0** |
| B3 judge observability (v8.22) | `infrastructure_failure` | **0** |

The machine that actually runs the node was two days and fourteen versions
behind. Not one of those fixes had ever executed anywhere except a test in a
cloud sandbox. `nodeB_prod.db-wal` had been touched at 11:01 that morning, so
the node was being *run* — on a source with unbounded inbound sockets (A15), no
port preflight (A2), and no path home for a restarted miner (A1/K2).

**This is M6 turned around.** M6 says: do not trust the backlog's claim that
the code was changed — grep the source. The loop grepped *the project's* source
faithfully, twenty times. Nobody grepped the deployed one. "Shipped" had quietly
come to mean "written to the project", and the log's own delivery lines say
"L: copy…" precisely because everyone knew that was not the same thing.

## What actually changed

An **attended** session has the device bridge; a scheduled one does not. That
distinction was never in the log — M5 says "scheduled cloud runs have no device
bridge", which is true, and the 10:30 and 23:30 runs both recorded L present and
still no bridge *because a schedule had started those sessions*. So the rule is
sharper than M5 states:

> The bridge exists when **L starts the session**, not when L is merely present
> in one. A run that a schedule started can never write to the PC, whatever the
> operator is doing at the time.

Both directions now work, and were used:

- **PC → project.** `daily.py`, `guards.py`, `paper_bot.py`, `holdings.txt`,
  `TRADING_POLICY.json`, `MY_STRATEGY.md`, `REAL_DATA_FINDINGS.md`,
  `phone/*.sh` — the files D3, D4, D5, D6 and C1 had been blocked on for
  eleven runs. They are in the project now, so an unattended run can work on
  them without waiting for an upload.
- **project → PC.** v8.29 (backed up as `covenant_unified_v8.PRE-v8.29.py`),
  the wired `daily.py` (backed up as `daily.PRE-D4.py`), the two new suites,
  `run_all_tests.sh`, `requirements.txt`, and all twelve verified deep price
  series into `realdata/deep/` — which the backtests had never had locally.

### Where the pulled files live in the project

`project_write` puts a new bare filename under `claude/`, which would mix L's
repo files in with the loop's own notes. So the files pulled off the PC sit
under **`pc/`**, which mirrors `C:\Users\Lawre\covenant\` exactly:

```
pc/daily.py  pc/guards.py  pc/paper_bot.py  pc/holdings.txt
pc/TRADING_POLICY.json  pc/MY_STRATEGY.md  pc/REAL_DATA_FINDINGS.md
pc/phone/node-install.sh  pc/phone/node-install-v2.sh  pc/phone/covenant-doctor.sh
```

A run that edits one of these puts it back at the PC path with the `pc/` prefix
stripped — `pc/daily.py` → `C:\Users\Lawre\covenant\daily.py`. `daily.py`
imports `guards` as a sibling, so they must stay in the same directory whatever
that directory is called.

## The standing rule this replaces

Delivery is not `project_write`. Delivery is `project_write` **plus** a
recorded answer to "is it on the machine that runs it?" Concretely, for every
future run:

1. Ship to the project as always (an unattended run has no other option).
2. Write the delivery line as it always was — L still has to act when the loop
   cannot reach the disk.
3. **In an attended, L-started session, do the copy** with the bridge and
   verify by hash on the far side, then say so.
4. **At the top of any run that can reach the PC, hash-compare the deployed
   source against the project's before choosing an item.** Drift is a finding
   in its own right, and it outranks the backlog: fixing item N+1 in a file
   nobody runs is not progress.

## Two things the bridge does not fix

- **The seal.** `covenant_seal.py` hashes all 134 files and
  `covenant_anchor.py` anchors the root to the chain (`SEAL_ROOT.txt`,
  `c119afb5…`, 2026-08-22 05:23, block 2). Every write above invalidates it.
  Re-run the seal and re-anchor — and note that this is now a routine event, so
  the anchor's value depends on it being re-run promptly rather than tolerated
  as stale. A tamper-evident seal that is usually wrong teaches its operator to
  ignore it.
- **`daily_state.json`.** The circuit breakers need a history journal. It is
  deliberately written to `~/.covenant/daily_state.json`, **outside** the synced
  folder, for the same two reasons: the folder leaves the machine, and a file
  that changes on every run would break the seal daily.
