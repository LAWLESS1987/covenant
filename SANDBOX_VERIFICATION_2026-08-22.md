# Covenant — sandbox verification pass, 2026-08-22

Reproduced the assembly-pass setup in a clean Linux sandbox (Python 3.11.15,
fresh venv, `flask cryptography requests xrpl-py` from `requirements.txt`) from
the source in `C:\Users\Lawre\covenant`. Your machine was not modified.

---

## 1. The battery — 287 checks, 0 failures

| suite | result |
|---|---|
| `test_security_audit.py` | **127 passed, 0 failed** |
| `test_xrp_mainnet.py` | **69 passed, 0 failed** |
| `test_xrp_signer.py` | **22 passed, 0 failed** |
| `test_adversarial_suite.py` | **21 passed, 0 failed** |
| `test_multinode_live.py` | **21 passed, 0 failed** (real processes, real sockets) |
| `quant/test_backtest_guardrails.py` | **16 passed, 0 failed** |
| `test_e2e_gift.py` | **11 passed, 0 failed** |
| `probe_final_pass.py` | **FINDINGS: 0** |
| `sim_order_independence.py` | **ALL INVARIANTS HELD** |

That is 266 checks matching `HANDOFF.md`'s table exactly, plus the 21-check
multi-node suite. The propagation fix (finding AV) holds: the 2-hop node reached
the new height by push, and the forged-genesis attack was rejected by node B
while all three nodes stayed responsive.

Not run, deliberately: `test_xrp_live.py` — it needs a funded testnet account and
it is the gate that unlocks mainnet. Untouched.

## 2. `start_live.bat` rehearsed end-to-end — it works

I replayed its exact sequence under the mock judge (fresh `nodeA_prod.db` /
`nodeB_prod.db`, founder key copied to node A, both started with
`--genesis genesis.json`):

```
founder balance      1000.0        <- as the script expects
send 10 A->B         accepted
mine on A            block 00001dd0fffaf08d, index 1
status               height=2 on both, same tip, converged: True
balances after       founder 990 / nodeB 10  -- identical on BOTH nodes
```

So the production launcher is sound. The only thing standing between you and a
live run is your API key.

**A correction worth recording.** My first rehearsal ran node A on the *same* DB
that minted the genesis, and it failed hard — founder balance `0.00`, send
rejected as `Insufficient balance`. I was about to report that as a blocker in
your launcher. It wasn't; it was my topology, not yours. But chasing it down
surfaced something real, below.

## 3. FINDING — the founder has two different balances depending on which DB the node runs from

Two code paths create the genesis, and they do not agree:

- `add_genesis_block()` (line ~7221) credits 1000 **and then**
  `staking_pool.stake(pubkey, 1000.0, 31536000)` — the entire mint is
  stake-locked for **365 days**.
- `adopt_canonical_genesis()` (line ~7165) records the `genesis_mint` credit and
  **never replays the stake**.

So the same founder identity reads:

| node's DB | founder balance |
|---|---|
| the DB that minted (`covenant_A.db`) | **0.00**, for a year |
| any DB that adopted `genesis.json` | **1000.00**, spendable now |

Demonstrated, both nodes carrying the identical genesis hash:

```
founder balance as node A's db sees it (minted):   0.0
founder balance as node B's db sees it (adopted):  1000.0
```

**It produces a real fork.** I submitted the founder's send to the adopting node,
which admitted it (`"admission": "admitted"`), mined it, and went to height 2.
The minting node stayed at height 1 and never converged — not after the
bootstrap window, not after a direct sync attempt:

```
5300 -> height 1 tip 000004021025      (minting DB)
5320 -> height 2 tip 00002d13ec25      (adopting DB)
```

**The convergence check does not catch it.** Before the fork,
`covenant_client.py status` reported `converged on one tip: True` while the two
nodes disagreed 0 vs 1000 on a spendable balance. Tip-hash equality is not state
equality. That is the silent-failure class `HANDOFF.md` §9.3 names as the worst
one in this codebase, and the existing check is blind to it.

**`NODES.md` finding #2 prescribes a fix that cannot work.** It says unstaking is
"a mandatory first step on any new chain." The genesis stake is locked for
31,536,000 seconds; `unstake()` returns `Stake still locked for ~31535940 more
seconds`. There is no unstaking your way out of it for a year.

Your launchers avoid this by always building fresh `nodeA_prod.db` /
`nodeA_run.db` that adopt. What is exposed is anything pointed at the minting DB
— including `preflight.py --db covenant_A.db` and
`go_live_check.sh --db covenant_A.db`, both of which you run as gates.

I did not change the ledger code. `HANDOFF.md` §5 is explicit that a fix here
needs its own adversarial pass and a human reading the diff, and it is right.

## 4. HAZARD — `run_all_tests.sh` deletes your founder key

Line 8, and again after every suite:

```bash
rm -f covenant_unified_*.db* *.db.key 2>/dev/null
```

`*.db.key` matches `covenant_A.db.key`. Per `INDEX.md`, that file is the founder
identity **and** the genesis mint key, and losing it strands the genesis balance
permanently. Running that script inside `covenant\` destroys it, silently,
before the first test.

Back the key up before that script ever runs. I ran the suites individually, from
a copy, and never staged your `.db.key` files off your machine.

## 5. `preflight.py`'s key-permission FAIL cannot clear on Windows

```python
mode = stat.S_IMODE(os.stat(keyfile).st_mode)
if mode & 0o077:  ->  FAIL "chmod 600 it"
```

CPython on Windows reports `0o666` for a writable file and `0o444` for a
read-only one — your own `preflight_out.txt` shows `0o666`. Both trip
`mode & 0o077`, and `os.chmod` on Windows only toggles the read-only bit. So this
BLOCKING item is unsatisfiable there no matter what you do. Real protection on
NTFS is an ACL (`icacls`), which `st_mode` does not reflect.

Treat it as a POSIX-only check. Worth making the check skip on `nt` rather than
block a launch on something that cannot be fixed.

## 6. Minor — the version string disagrees with itself

```
COVENANT_VERSION = "v8.9-merged"        (line 412)
banner:            "Covenant Unified v7.0 running"   (line 6422)
HANDOFF.md:        "Current version: v8.18"
```

Three answers to "what is running." The banner is the one people read.

---

## What is still yours to do

1. **Back up `covenant_A.db.key`** somewhere outside the synced folder, before
   anything else. `INDEX.md` has been telling you this since 2026-08-20.
2. **Run the production launch.** `start_live.bat` works — I proved the sequence.
   You type the key; I will not.
3. One caution on that: `set /p` **echoes the key in plaintext** into the console
   window and its scrollback. Use `start_live_env.bat` (included) if you would
   rather read it from an environment variable and never have it on screen.

Mainnet stays blocked. `xrp_testnet_proof.json` does not exist, so the gate in
code is still closed, and nothing here changed that.
