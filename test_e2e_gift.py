"""END-TO-END: a real signed gift through the live HTTP route, published to
the chain, mined into a block, and reconstructed by a peer that has only the
chain. Exercises the whole AE/AF/AG/AC path as an operator would hit it.

Repairs are cheap to claim and expensive to verify. This verifies.
"""
import os, sys, time, base64, tempfile, shutil, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov
from covenant_trading_bridge import TradingBridge
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

work = tempfile.mkdtemp(prefix="e2e_")
passed = failed = 0

def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        failed += 1; print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))

def kp():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return k, k.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()

pool_sk, POOL = kp()
rcp_sk, RCP = kp()

db = cov.Database(os.path.join(work, "e2e.db"))
sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
pool = cov.StakingPool(db)
succ = cov.SuccessionGuardianSystem(db)
fr = cov.FriendshipTracker(db)
node_sk, node_pem = kp()
node = cov.P2PNode("e2e", "127.0.0.1", 7001, node_sk, node_sk.public_key(), db)
node.sentinel, node.staking_pool, node.friendship = sentinel, pool, fr
node.trading_bridge = TradingBridge(db, sentinel, pool, succ, fr)
api = cov.CovenantAPI(node, db, "127.0.0.1", 7000)
client = api.app.test_client()

db.record_ledger_entry(POOL, 1000.0, "genesis_mint", ref_id="e2e_seed")

ts = time.time()
AMT = 100.0
sig = base64.b64encode(pool_sk.sign(
    cov._domain_frame(b"COVENANT_NODE_GIFT_V1", POOL, RCP, str(AMT), str(ts)),
    padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())).decode()

body = {"pool_pubkey": POOL, "recipient_pubkey": RCP,
        "amount": AMT, "timestamp": ts, "signature": sig}

print("== live route: POST /trading/gift_node ==")
r = client.post("/trading/gift_node", json=body)
j = r.get_json()
check("route returned 200", r.status_code == 200, f"HTTP {r.status_code} {str(j)[:90]}")
check("gift recorded locally", db.get_balance(RCP) == AMT, f"{db.get_balance(RCP)}")
check("pool debited exactly once", db.get_balance(POOL) == 900.0, f"{db.get_balance(POOL)}")
check("event was PUBLISHED, not just returned", j.get("published") is True,
      str(j.get("publish_detail"))[:70])
check("a carrier transaction is in the mempool",
      any(isinstance(t.data, dict) and t.data.get("ledger_event")
          for t in node.pending_transactions),
      f"{len(node.pending_transactions)} pending")

print("\n== replay protection ==")
r2 = client.post("/trading/gift_node", json=body)
check("an identical replayed gift is refused", r2.status_code != 200,
      f"HTTP {r2.status_code}")
check("balances unmoved by the replay",
      db.get_balance(RCP) == AMT and db.get_balance(POOL) == 900.0,
      f"pool={db.get_balance(POOL)} rcp={db.get_balance(RCP)}")

# ITEM AF: same signature, caller-chosen ref_id. The route derives the ref_id
# now, so the only way to attempt this is to forge the event directly.
print("\n== item AF: one signature, many ref_ids ==")
forged = {"entries": [
    {"pubkey": POOL, "delta": -AMT, "reason": "node_gift_sent", "ref_id": "attacker-choice"},
    {"pubkey": RCP, "delta": AMT, "reason": "node_gift_received", "ref_id": "attacker-choice"}],
    "auth": {POOL: {"kind": "node_gift_v1", "recipient": RCP, "amount": AMT,
                    "timestamp": ts, "signature": sig}}}
ok, why = cov.Database.validate_ledger_event(forged)
check("a caller-chosen ref_id is refused under a real gift signature", not ok, why[:80])

print("\n== chain -> peer reconstruction ==")
blk = cov.Block(index=1, transactions=list(node.pending_transactions),
                previous_hash="0" * 64)
node.chain.append(blk)
peer = cov.Database(os.path.join(work, "peer.db"))
for b in node.chain:
    peer.apply_transaction_ledger(b)
check("peer reconstructs the recipient balance from the chain alone",
      peer.get_balance(RCP) == AMT, f"peer={peer.get_balance(RCP)} origin={db.get_balance(RCP)}")
check("peer reconstructs the pool debit",
      peer.get_balance(POOL) == -AMT,
      f"peer={peer.get_balance(POOL)} (no genesis on peer, so -100 is correct)")

print("\n== origin replays its own chain (restart / resync) ==")
before_pool, before_rcp = db.get_balance(POOL), db.get_balance(RCP)
for b in node.chain:
    db.apply_transaction_ledger(b)
check("origin replaying its own chain double-applies nothing",
      db.get_balance(POOL) == before_pool and db.get_balance(RCP) == before_rcp,
      f"pool {before_pool}->{db.get_balance(POOL)} rcp {before_rcp}->{db.get_balance(RCP)}")

shutil.rmtree(work, ignore_errors=True)   # Windows will not unlink an open sqlite file;
                                          # this is teardown AFTER every check, so a
                                          # leftover temp dir must not fail the suite
print("\n" + "=" * 58)
print(f"{passed} passed, {failed} failed")
print("=" * 58)
sys.exit(1 if failed else 0)
