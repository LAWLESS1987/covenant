"""PROBE -- why does no mined block ever propagate?

The multi-node harness localized the failure precisely: A mines, announces,
B fetches the block successfully, and then _accept_block_common returns False.
Transport was never the problem. Every layer of the P2P stack works.

HYPOTHESIS: /mine mutates the block AFTER mining it.

    block.mine(MINING_DIFFICULTY)          # hash computed with stake_rewards = 0.0
    ...
    block_reward = sum(tx.amount ...) * 0.01
    block.stake_rewards = block_reward      # <-- FIELD IS INSIDE compute_hash()

stake_rewards is one of the seven fields compute_hash() hashes. Writing it after
mining leaves block.hash describing a block that no longer exists. The miner
never re-checks its own block, so it appends happily. Every PEER checks
`block.hash == block.compute_hash()` and refuses.

If true, this is not a networking bug at all: it means NO mined block carrying
any transaction with a positive amount has ever been acceptable to any peer, in
any version, and single-node operation hid it completely.
"""
import os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = k.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo).decode()

tx = cov.Transaction(sender_pubkey=pem, receiver="collective",
                     data={"origin": "human"}, amount=1.0, benefit_score=0.5)
tx.sign(k)

print("=" * 70)
print("reproducing the /mine sequence exactly")
print("=" * 70)
block = cov.Block(index=1, transactions=[tx], previous_hash="0" * 64)
block.mine(2)
print(f"  after mine():          hash == compute_hash() -> {block.hash == block.compute_hash()}")
print(f"  stake_rewards at mine time: {block.stake_rewards}")

block_reward = sum(t.amount for t in block.transactions) * 0.01
block.stake_rewards = block_reward       # the exact line from /mine
print(f"\n  /mine then sets stake_rewards = {block_reward}")
print(f"  after mutation:        hash == compute_hash() -> {block.hash == block.compute_hash()}")
print(f"    stored hash   : {block.hash[:48]}")
print(f"    recomputed    : {block.compute_hash()[:48]}")

if block.hash != block.compute_hash():
    print("\n  *** CONFIRMED: the block's own hash no longer describes it.")
    print("      A peer running `block.hash == block.compute_hash()` refuses it.")
    print("      The miner never re-checks, so single-node operation looks fine.")

print()
print("=" * 70)
print("when does this NOT bite? (why it stayed hidden)")
print("=" * 70)
for amt in (0.0, 1.0, 100.0):
    t = cov.Transaction(sender_pubkey=pem, receiver="collective",
                        data={"origin": "human"}, amount=amt, benefit_score=0.5)
    t.sign(k)
    b = cov.Block(index=1, transactions=[t], previous_hash="0" * 64)
    b.mine(2)
    b.stake_rewards = sum(x.amount for x in b.transactions) * 0.01
    ok = b.hash == b.compute_hash()
    print(f"  tx amount {amt:>7} -> block_reward {b.stake_rewards:>7} -> hash valid: {ok}")
print("\n  Only zero-amount blocks survive, because 0.0 == the mined-in default.")
print("  Every block that moves value is unacceptable to every peer.")

print()
print("=" * 70)
print("does the fix hold? set the field BEFORE mining")
print("=" * 70)
b = cov.Block(index=1, transactions=[tx], previous_hash="0" * 64)
b.stake_rewards = sum(t.amount for t in b.transactions) * 0.01
b.mine(2)
print(f"  stake_rewards set pre-mine: {b.stake_rewards}")
print(f"  hash == compute_hash() -> {b.hash == b.compute_hash()}")
print(f"  proof_of_work_ok()     -> {b.proof_of_work_ok()}")
