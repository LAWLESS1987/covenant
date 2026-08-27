# Yield on-chain — the decision L has to make, with the evidence (2026-08-22)

**Ask from L:** "refine entire system repeatedly until confident in yield to
help with propagation."

**Short answer:** the yield *arithmetic* on v8.27 is sound; the yield
*location* is not. Staking lives in each node's private state, so on any
chain with more than one node the yield pays different people different
amounts on different nodes, and an honest stake or unstake forks the chain.
No amount of tightening fixes that — it needs one design decision (§3).
Measured, not argued: `claude/test_y1_stake_divergence.py`, 10/10 ×2 on the
shipped v8.27 (`07ff5266…`).

---

## 1. What is sound today (v8.27)

`sim_yield_safety.py` run against v8.27 for the first time (it was written
against v8.12 and never re-run):

- **Time yield** (`Stake.calculate_rewards`, `YIELD_RATE` 5 %/yr, compounds on
  each claim): bounded, exponential in rate × time as a yield should be; 5 %
  claimed monthly = 148× over a century. Not a bug.
- **Block reward** (`distribute_block_rewards`, 1 % of block volume split
  pro-rata by `stake.amount / total_staked`): **0.0 % over-issue at 1, 10,
  100, 1 000, 5 000 blocks.** The AK fix (derived `total_staked`, snapshot
  denominator) holds. The sim's own prose still says "NOT bounded … runaway"
  — that paragraph predates the fix; the numbers it prints say fixed.
- NaN / inf / negative rewards are refused before they touch a stake (AL).
- Peers distribute the block reward too (A4, v8.18), and a block whose
  `stake_rewards ≠ fsum(amount)·0.01` is refused — so *if* every node held
  the same stake table, every node would pay the same yield.

## 2. What is not sound — measured (Y1)

`stake`, `claim_rewards`, `unstake` are HTTP routes that mutate **this node's**
stake table and **this node's** ledger (`stake_lock` −amount / `unstake`
+payout entries). Nothing carries them to peers: patch log AC and `HANDOFF.md`
§4 say so ("deliberately not invented"). On two nodes A, B sharing one
exported genesis (the real deployment path):

| check | result |
|---|---|
| Y1a founder stakes 600 on A | A balance 400, B balance 1000 |
| Y1b founder spends 800 via B (honest on B's view) | B accepts; **A refuses `block_rejected_overdraft`** — A is one block behind for ever |
| Y1c a 300 spend both accept | reward 3.0 paid to the staker **on A**, to **nobody on B** (empty table); supply A = supply B + 3.0 |
| Y1d `/stakes` | differ the moment anyone stakes (the A9-S3 "agreement" was two empty tables) |
| Y1e unstake on A after the lock (patched clock) | A credits 603.08; a block A mines spending it is **refused by B** — the fork runs both ways |
| Y1f arithmetic | no fee: a sole staker cycling its own 1 000 through a second key mints 10 per block to itself — +100 % supply in ~200 blocks, bounded only by PoW time |

So on a multi-node chain today: the 1 % yield reaches nobody on any
`--genesis` node (this is A10's empty-table finding from the other side), the
first real stake anywhere forks the network on the next honest spend, and
whoever holds the only populated table can inflate at 1 % of volume per block.
"Propagation" and "yield" cannot both be true with node-local staking.

## 3. The decision

### Option A — staking becomes a chain event (recommended)

Use the carrier mechanism that already exists for `node_gift_*` (patch log AC:
an amount-0 transaction signed by the actor, carrying a `ledger_event`,
admitted through the mempool, propagated, applied by
`apply_transaction_ledger` on every node).

1. **`stake_lock`** = debit staker −amount, credit a reserved account
   `STAKING_ESCROW` +amount. Net-zero, so it passes the existing rule
   unchanged. Every node, on applying the block, calls
   `staking_pool.stake_from_chain(pubkey, amount, duration,
   start_time=tx.timestamp)` — start time from the **transaction**, never the
   local clock, so tables are identical everywhere. Balance check on
   admission *and* on block acceptance (same overdraft re-check as value
   transactions, against `get_spendable_balance`).
2. **`unstake`** = credit staker +principal, debit escrow −principal
   (net-zero) **plus** a reward mint `+R` with **R recomputed by every node**
   from the stake record and the block timestamp (`calculate_rewards` with
   `current_time = block.timestamp`, plus the block rewards already
   compounded into `stake.amount` identically on every node). A block whose
   mint ≠ the recomputed R is refused — the same shape as the v8.18
   `stake_rewards == fsum·0.01` rule. Lock enforced against
   `block.timestamp`, so A8's "no timestamp rule" must be closed at the same
   time (≤ now + skew, ≥ parent).
3. **`claim_rewards`** either becomes the same kind of event (verified mint,
   compounds into the chain-visible stake) or is retired — unstake already
   compounds the final reward. Recommendation: retire the route; one fewer
   mint path to verify.
4. **Genesis** carries the founder's stake as the same event (or the loader
   applies it from the block) so `add_genesis_block` and
   `load_canonical_genesis` produce **one** state — A10 disappears by
   construction. L still chooses *whether* genesis is staked/locked (A1c),
   but both paths then agree whichever way.
5. **`/stake`, `/unstake`** keep their signatures and semantics but *submit*
   the event instead of applying it; the reply becomes "accepted, pending"
   and the state change lands when the block does. `/stakes` is then a
   consensus view.
6. New validity rules → recorded under A7 (protocol-version note).
7. **Y1f (volume-minted reward with no fee)** is a separate economic choice:
   keep (the founder's stated design), cap the reward per block, or tie it to
   a fee the sender pays. Option A does not change it; it only makes whatever
   is chosen identical on every node.

Cost: one run for the event plumbing + rules, one for the genesis
unification, each with the pre-fix/post-fix test recipe (Y1 is the pre-fix
record). Roughly A4-sized.

### Option B — staking stays node-local

Document that yield is a per-node ledger that does not travel; remove the
`/stakes` cross-node checks; accept that the first stake forks a multi-node
chain. Honest, and cheap, but it means the chain cannot be both propagated
and yield-bearing, which is the opposite of the ask.

### Not an option

Making the decision silently in a scheduled run. It is a consensus change
(Section 0: controls are L's) and the source and HANDOFF both say so.

---

**Files:** `claude/test_y1_stake_divergence.py` (evidence, no source change),
this document. Node source unchanged (`07ff5266…`).
