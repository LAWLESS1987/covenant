"""test_y1_stake_divergence.py -- Y1: staking is node-local, so yield and
balances diverge across a multi-node chain (evidence run, no source change).

WHY
  L asked for the system to be refined "until confident in yield, to help
  with propagation". The yield machinery itself is exact on v8.27
  (sim_yield_safety: 0.0% over-issue, time yield bounded). What is NOT
  sound is where it lives: `stake`, `claim_rewards` and `unstake` mutate
  one node's stake table and one node's ledger, and nothing carries that
  to peers (patch log AC, HANDOFF §4: "deliberately not invented").
  This test makes the consequences concrete, on the real classes, with the
  real shared-genesis path, so the decision in front of L is measured
  rather than argued.

WHAT IS REAL HERE
  Two in-process CovenantUnifiedMaster nodes (A, B) adopting the same
  exported genesis (the deployment path); the real StakingPool; the real
  `_accept_block_common` (signature, PoW, hash, reward and alignment rules,
  overdraft re-check, ledger apply, peer-side reward distribution); blocks
  built exactly as /mine builds them. No sockets -- the block is handed to
  each node the way `_fetch_announced` hands it over after a fetch.
  Time is advanced with a patched clock for the unstake case (M12).

CHECKS
  Y1a  a local stake on A debits A's ledger only: A sees 1000-S, B sees 1000
  Y1b  a block B accepts (founder spends more than A's post-stake balance)
       is REFUSED by A as block_rejected_overdraft -> chains diverge on a
       perfectly honest transaction; A stays one block behind for good
  Y1c  a non-overdrawing value block is accepted by BOTH, and the 1% block
       reward is paid to the staker on A and to NOBODY on B (empty table):
       the same block yields different supply on different nodes
  Y1d  /stakes disagree across nodes the moment anyone stakes (the A9 S3
       agreement was vacuous: both tables were empty)
  Y1e  after the lock, unstake on A credits A's ledger with principal +
       compounded rewards; a block A mines spending that credit is refused
       by B (overdraft) -> the fork runs both ways
  Y1f  arithmetic from the module's constants: with no fee, a sole staker
       cycling its own balance mints 1% of volume per block to itself; the
       growth factor per round-trip is printed (a design fact for L, not a
       bug in the split)

Run:  COVENANT_INSECURE_MOCK_JUDGE=1 COVENANT_JUDGE_PROVIDERS=mock \
      python3 test_y1_stake_divergence.py
"""
import json
import math
import os
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import covenant_unified_v8 as cov

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def pem_of(key):
    return key.public_key().public_bytes(serialization.Encoding.PEM,
                                         serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def fresh_master(name, port, genesis_path=None):
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    if genesis_path:
        assert m.load_canonical_genesis(genesis_path)
    else:
        m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    return m


def value_block(m, sender_key, receiver_pem, amount):
    """A block built the way /mine builds it: one signed, registration-PoW'd
    transaction, stake_rewards = fsum(amount)*0.01, alignment = mean
    benefit, mined at the live difficulty."""
    pem = pem_of(sender_key)
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    tx = cov.Transaction(sender_pubkey=pem, receiver=receiver_pem, data={"origin": "human"},
                         amount=float(amount), benefit_score=m.node.governor.get_current(),
                         reg_nonce=reg)
    tx.sign(sender_key)
    b = cov.Block(len(m.node.chain), [tx], m.node.chain[-1].hash)
    b.stake_rewards = math.fsum(t.amount for t in b.transactions) * 0.01
    b.alignment_score = tx.benefit_score
    b.mine()
    return b


def clone_block(b):
    raw = cov.asdict(b)
    txs = [cov.Transaction(**t) for t in raw["transactions"]]
    c = cov.Block(raw["index"], txs, raw["previous_hash"])
    c.timestamp = raw["timestamp"]; c.nonce = raw["nonce"]; c.hash = raw["hash"]
    c.alignment_score = raw["alignment_score"]; c.stake_rewards = raw["stake_rewards"]
    return c


def kinds(m):
    return {k: v["baseline"] for k, v in m.node.anomaly_monitor.report()["per_kind"].items()}


def stakes_view(m):
    return {k[:24]: round(s.amount, 9) for k, s in m.node.staking_pool.stakes.items()}


def main():
    F_PORT, A_PORT, B_PORT = 19500, 19512, 19524      # 12 apart (M2)
    print("== Y1 stake divergence (evidence run on the shipped source)")
    print(f"   YIELD_RATE={cov.YIELD_RATE} STAKE_MIN_DURATION={cov.STAKE_MIN_DURATION}s "
          f"block reward = 1% of volume, fees = none")

    # founder mints and exports; A and B adopt
    f = fresh_master("founder", F_PORT)
    gpath = tempfile.mktemp(suffix="_genesis.json")
    f.export_genesis(gpath)
    founder_key = f.private_key
    founder_pem = pem_of(founder_key)
    a = fresh_master("A", A_PORT, gpath)
    b = fresh_master("B", B_PORT, gpath)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = pem_of(other)

    # ---------------------------------------------------------------- Y1a
    S = 600.0
    ok, msg = a.node.staking_pool.stake(founder_pem, S, cov.STAKE_MIN_DURATION)
    bal_a, bal_b = a.db.get_balance(founder_pem), b.db.get_balance(founder_pem)
    check("Y1a local stake on A debits A only: A=400, B=1000",
          ok and abs(bal_a - 400.0) < 1e-9 and abs(bal_b - 1000.0) < 1e-9,
          f"stake={ok} ({msg}); A balance {bal_a:.3f}, B balance {bal_b:.3f}")

    # ---------------------------------------------------------------- Y1b
    blk1 = value_block(b, founder_key, other_pem, 800.0)     # honest on B's view
    acc_b = b._accept_block_common(clone_block(blk1))
    acc_a = a._accept_block_common(clone_block(blk1))
    ka = kinds(a)
    check("Y1b B accepts the honest 800 spend; A refuses it as block_rejected_overdraft",
          acc_b and not acc_a and ka.get("block_rejected_overdraft", 0) >= 1,
          f"B accepted={acc_b} A accepted={acc_a} A anomalies={ka}")
    check("Y1b chains diverged: B height 2, A height 1",
          len(b.node.chain) == 2 and len(a.node.chain) == 1,
          f"A={len(a.node.chain)} B={len(b.node.chain)}")

    # ---------------------------------------------------------------- Y1c
    # fresh pair so both start at height 1 with the same view
    a2 = fresh_master("A2", A_PORT + 36, gpath)
    b2 = fresh_master("B2", B_PORT + 36, gpath)
    assert a2.node.staking_pool.stake(founder_pem, S, cov.STAKE_MIN_DURATION)[0]
    blk2 = value_block(b2, founder_key, other_pem, 300.0)     # 300 <= 400: honest everywhere
    acc_b2 = b2._accept_block_common(clone_block(blk2))
    acc_a2 = a2._accept_block_common(clone_block(blk2))
    pool_a, pool_b = a2.node.staking_pool.total_staked, b2.node.staking_pool.total_staked
    check("Y1c both accept the 300 spend (height 2 on each)",
          acc_a2 and acc_b2 and len(a2.node.chain) == 2 and len(b2.node.chain) == 2,
          f"A2={acc_a2} B2={acc_b2}")
    check("Y1c the 1% block reward (3.0) is paid to the staker on A2 and to nobody on B2",
          abs(pool_a - (S + 3.0)) < 1e-9 and pool_b == 0.0,
          f"A2 pool {pool_a:.6f} (expected {S + 3.0}), B2 pool {pool_b:.6f}")
    supply_a = sum(a2.db.get_balance(p) for p in (founder_pem, other_pem)) + pool_a
    supply_b = sum(b2.db.get_balance(p) for p in (founder_pem, other_pem)) + pool_b
    check("Y1c same block, different total supply per node (A2 = B2 + 3.0)",
          abs(supply_a - supply_b - 3.0) < 1e-9,
          f"A2 supply {supply_a:.6f} vs B2 {supply_b:.6f}")

    # ---------------------------------------------------------------- Y1d
    va, vb = stakes_view(a2), stakes_view(b2)
    check("Y1d /stakes disagree across nodes once anyone stakes",
          va != vb, f"A2={va} B2={vb}")

    # ---------------------------------------------------------------- Y1e
    real_time = cov.time.time
    OFFSET = [0.0]
    cov.time.time = lambda: real_time() + OFFSET[0]
    try:
        OFFSET[0] = cov.STAKE_MIN_DURATION + 5.0
        payout, umsg = a2.node.staking_pool.unstake(founder_pem)
        bal_a2 = a2.db.get_balance(founder_pem)
        bal_b2 = b2.db.get_balance(founder_pem)
        check("Y1e unstake on A2 credits A2's ledger with principal + compounded rewards",
              payout > S + 3.0 and abs(bal_a2 - (100.0 + payout)) < 1e-6,
              f"payout {payout:.6f} ({umsg}); A2 balance {bal_a2:.6f}, B2 balance {bal_b2:.6f}")
        # A2 now mines a block that spends what B2 never saw credited
        spend = bal_a2 - 0.5
        blk3 = value_block(a2, founder_key, other_pem, spend)
        acc_a3 = a2._accept_block_common(clone_block(blk3))
        acc_b3 = b2._accept_block_common(clone_block(blk3))
        kb = kinds(b2)
        check("Y1e A2 accepts its own spend of the unstake credit; B2 refuses it (overdraft): fork both ways",
              acc_a3 and not acc_b3 and kb.get("block_rejected_overdraft", 0) >= 1,
              f"A2={acc_a3} B2={acc_b3} B2 anomalies={kb}")
    finally:
        cov.time.time = real_time

    # ---------------------------------------------------------------- Y1f
    # sole staker with stake S and spendable V cycles V through a second key
    # each block: every block mints 0.01*V, all of it to the staker.
    V, S0 = 1000.0, 1000.0
    rounds = 100
    stake_amt, supply = S0, S0 + V
    for _ in range(rounds):
        reward = V * 0.01
        stake_amt += reward
        supply += reward
    check("Y1f arithmetic: sole staker cycling 1000 mints 10/block to itself; +100% supply in ~200 blocks",
          abs(supply - (S0 + V + rounds * 10.0)) < 1e-9,
          f"after {rounds} blocks supply {supply:.1f} (was {S0 + V:.1f}); no fee opposes it; "
          f"unbounded in block count, bounded only by MINING_DIFFICULTY={cov.MINING_DIFFICULTY}")

    for m in (f, a, b, a2, b2):
        try:
            m.db.close()
        except Exception:
            pass
    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} passed" + ("" if passed == len(results) else f", {len(results) - passed} FAILED"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
