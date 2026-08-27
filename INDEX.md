# What's in this folder, and what to actually run

Audited 2026-08-20 against the real contents of `C:\Users\Lawre\covenant`.

---

## FIX THIS FIRST — three private keys are in a folder that leaves your machine

```
covenant_A.db.key
nodeA_run.db.key
nodeB_run.db.key
```

This folder syncs to the cloud. Anything in it has already left your computer.
Those three files are node operator credentials — `covenant_A.db.key` is the
key that minted your genesis block and controls the founder identity.

**I did not move them,** because `covenant_A.db.key` is bound to
`covenant_A.db`; moving it without moving the database breaks that node's
identity. That's a decision about your ledger, not a cleanup task, so it's
yours to make.

What I'd do, in PowerShell:

```
mkdir C:\Users\Lawre\.covenant-keys
move C:\Users\Lawre\covenant\*.db.key C:\Users\Lawre\.covenant-keys\
```

then point the node at them explicitly, or keep the `.db` and `.key` pair
together outside the synced folder. The rule worth keeping: **nothing secret
lives in `covenant\`.** Same reason your Kraken credentials go in WSL's home and
not here.

Low stakes today — that chain holds nothing spendable. It's the habit that
matters, because the next key might be one that does.

---

## Start here

| you want to | run |
|---|---|
| today's holdings + rule check | `DAILY.bat` (or `python daily.py`) |
| your alert levels | read `ALERTS.md` |
| install Kraken CLI | WSL → `kraken\unpack-kraken.sh` |
| start paper trading | `python3 kraken\paper_run.py --init` |
| seal today's signals | `python3 kraken\paper_run.py --place` |
| see what the rules would trade | `python kraken\execute.py` |
| put the daily check on your phone | `phone\PHONE_SETUP.md` |

## The trading side

| file | what it does |
|---|---|
| `daily.py` | live prices, portfolio, 20% cap + cash floor check, phone push |
| `holdings.txt` | **the one file you edit.** Quantities and average buy prices |
| `ALERTS.md` | every regime line and the price where each position flips |
| `MY_STRATEGY.md` | the five rules, in plain language |
| `kraken/execute.py` | rules → exact orders, clamped to what Kraken actually holds |
| `kraken/paper_run.py` | seals signals in a tamper-evident journal, scores them |
| `kraken/KRAKEN_SETUP.md` | install, read-only key, MCP wiring |
| `kraken_balance.py` | older balance reader — superseded by the Kraken CLI |

## Research — how the strategy was tested

| file | what it does |
|---|---|
| `strategy_lab.py` | searches strategy families, deflates by trial count |
| `multi_scan.py` | same across a watchlist, one shared trial budget |
| `full_test.py` | the whole battery, writes a report |
| `rebalance_strategy.py` | rebalancing vs holding — needs no forecast |
| `signal_watch.py` | live sealed signals with a binomial p-value |
| `REAL_DATA_FINDINGS.md` | the results. Read this before trusting any backtest |
| `quant/covenant_backtest.py` | the engine: costs, walk-forward, deflated Sharpe |

## The ledger

| file | what it does |
|---|---|
| `covenant_unified_v8.py` | the node. 425KB, the core of everything |
| `covenant_client.py` | operator client — balance, send, mine, status |
| `covenant_judge_local.py` | DeepSeek / Mistral / Ollama judge providers |
| `NODES.md` | **read before running multiple nodes.** Port arithmetic will bite you |
| `run_with_claude_judge.py` | file-based judge gate, no API key |
| `phone/node-install.sh` | run a node on Android via Termux |

## Verified price data

`realdata/` now holds nine checked series: ADA, CRO, ONDO, PEPE, SOL, WLFI,
XLM (220 bars each), HBAR (419), XRP (349). All verified for exact 86400-second
spacing, no duplicate or missing days, no non-positive prices, in-progress bar
excluded.

`HBAR-USD.STALE-ends-2026-06-10.csv` is the old corrupted pull — 70 days out of
date. Renamed so nothing reads it by accident. `HBAR_c.csv` is the corrected
replacement. See `claude/PRICE_DATA_INTEGRITY.md` in the project for how that
one slipped through.

---

## Known gaps

- **`MY_STRATEGY.md` has none of your current numbers** — no portfolio total, no
  trim sizes, no dates. It states the rules but not where you stand.
- **`REAL_DATA_FINDINGS.md` was written on the stale HBAR data.** Its XRP results
  hold; the HBAR figures came from a series ending 2026-06-10.
- **Block propagation under node failure is unproven.** Replication and restart
  are tested; propagation isn't, because the genesis mint is fully stake-locked
  and no second block can be minted until you `/unstake`.
- **The two Rule-1 trims are still undone.** XLM and SOL by the Rule-1 amounts.
