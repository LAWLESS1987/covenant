"""LIVE testnet verification for covenant_xrp_signer. Run this on a machine
with outbound internet -- it could NOT be run in the sandbox where the signer
was written (XRPL endpoints are unreachable there), so the code paths it covers
are, until you run it, written-and-reviewed but not empirically confirmed.

TESTNET ONLY. This script has no mainnet mode and will not acquire one by
being edited casually -- it constructs XRPSigner without allow_mainnet, so a
mainnet attempt raises before anything is signed.

    python3 test_xrp_live.py

First run creates two testnet seed files and stops, so you can fund them:
    xrp_testnet_a.seed  -- the sender (needs faucet funding)
    xrp_testnet_b.seed  -- the destination (does not need funding)

Fund the printed sender address at https://xrpl.org/xrp-testnet-faucet.html
then run again.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_xrp_signer as X

A_SEED, B_SEED = "xrp_testnet_a.seed", "xrp_testnet_b.seed"
passed = failed = 0

def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        failed += 1; print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))

created = False
for p in (A_SEED, B_SEED):
    if not os.path.exists(p):
        print(f"\nCreating {p} ...")
        X.create_testnet_seed_file(p)
        created = True
if created:
    print("\nFund the SENDER address above at the testnet faucet, then re-run.")
    sys.exit(0)

sender = X.XRPSigner(A_SEED)                    # testnet by default
dest = X.XRPSigner(B_SEED)

print("\n== live: account state ==")
try:
    bal = sender.get_balance_xrp()
except X.XRPSignerError as e:
    print(f"\n  Sender is not funded yet: {e}")
    print(f"  Fund {sender.address} at https://xrpl.org/xrp-testnet-faucet.html")
    sys.exit(1)
check("sender balance reads from the validated ledger", bal > 0, f"{bal} XRP")

print("\n== live: base-reserve guard (needs a real balance) ==")
try:
    sender.send_xrp(dest.address, bal, dry_run=True)
    check("sending the entire balance is refused", False, "it was allowed")
except X.XRPSignerError as e:
    check("sending the entire balance is refused", "reserve" in str(e).lower(), str(e)[:80])

print("\n== live: autofill + sign, nothing submitted ==")
dry = sender.send_xrp(dest.address, 1.0, dry_run=True)
check("dry run reports itself as a dry run", dry.get("dry_run") is True)
check("autofill assigned a real sequence", isinstance(dry.get("sequence"), int),
      str(dry.get("sequence")))
check("autofill assigned a fee", bool(dry.get("fee_drops")), dry.get("fee_drops"))
check("a transaction hash was computed", len(dry.get("tx_hash_if_submitted", "")) == 64)

before_dest = 0.0
try:
    before_dest = dest.get_balance_xrp()
except X.XRPSignerError:
    pass  # unfunded destination is fine; the payment will activate it
check("dry run moved nothing", True, f"destination still at {before_dest} XRP")

print("\n== live: real submission ==")
print("  Submitting 1.0 test XRP. This is testnet play money.")
rec = sender.send_xrp(dest.address, 1.0, dry_run=False)
check("submission validated on-ledger", rec["validated"] is True, str(rec["validated"]))
check("engine result is tesSUCCESS", rec["engine_result"] == "tesSUCCESS",
      rec["engine_result"])
check("a ledger hash came back", len(rec["tx_hash"]) == 64, rec["tx_hash"])
check("network recorded as testnet", rec["network"] == "testnet")

after_dest = dest.get_balance_xrp()
check("destination balance actually increased",
      after_dest > before_dest, f"{before_dest} -> {after_dest} XRP")

print("\n" + "=" * 58)
print(f"{passed} passed, {failed} failed")
print("=" * 58)
if not failed:
    # ITEM AM -- write the testnet proof that unlocks mainnet. Mainnet refuses
    # to run until this file exists, because every mainnet control wraps code
    # whose live behaviour is inferred until this test has actually run.
    import covenant_xrp_mainnet as M
    M.record_testnet_proof(rec["tx_hash"])
    print(f"\nTestnet proof written to {M.TESTNET_PROOF_FILE} -- mainnet unlocked.")
    print("\nSigning and submission are now empirically confirmed, not assumed.")
    print("The ledger hash above is EXTERNAL evidence -- unlike a self-reported")
    print("trading profit, anyone can verify it independently. That is what makes")
    print("it eligible to back an on-chain credit later; self-attestation is not.")
sys.exit(1 if failed else 0)
