"""FINAL PASS -- attack the newest code: the reservation state machine (items
AP/AR/AS) and the bootstrap/sync path (item AO).

Newest code is least-reviewed code, and this session has already produced three
bugs that were introduced by the fix for the previous bug. These are attacks the
new code was NOT designed against.

F1 release() writes a release_marker row and THEN rewrites the file to mark the
   reservation released. If a crash lands between those two, is the money
   invisible-but-held? pending_reservations() excludes anything with a
   release_marker; _counts() only excludes state == "released". Those are two
   different sets.
F2 can the same reservation be released twice, freeing headroom twice?
F3 does settle() on an unknown/forged reservation id corrupt the counts?
F4 bootstrap_chain blocks for up to rounds*pause seconds. /sync is unauthenticated
   and calls it synchronously inside a Flask worker. How long can one request
   hold a worker, and can it be repeated?
"""
import os, sys, json, time, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_xrp_mainnet as M

work = tempfile.mkdtemp(prefix="final_")
GOOD = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"
pol, proof = f"{work}/p.json", f"{work}/pr.json"
M.record_testnet_proof("a" * 64, proof)
json.dump({"destinations": [{"address": GOOD, "label": "w", "tag_not_required": True}],
           "max_per_payment_xrp": 10.0, "max_per_day_xrp": 50.0,
           "max_lifetime_xrp": 500.0, "require_confirmation_phrase": False},
          open(pol, "w"))
os.chmod(pol, 0o600)
findings = []

def auth(sl, amt):
    return M.authorize_mainnet_payment(destination=GOOD, amount_xrp=amt,
                                       policy_path=pol, spend_ledger_path=sl,
                                       testnet_proof_path=proof)

print("=" * 70)
print("F1: crash between the release marker and the rewrite")
print("=" * 70)
sl = f"{work}/s1.jsonl"
led = M.SpendLedger(sl)
r = auth(sl, 10.0)
led.attach_hash(r["reservation_id"], "D" * 64)
print(f"  held: {led.spent_today()} XRP, pending rows: {len(led.pending_reservations())}")

# Simulate the crash: the marker lands, the rewrite never happens.
with open(sl, "a") as fh:
    fh.write(json.dumps({"reservation_id": r["reservation_id"], "drops": 0,
                         "amount_xrp": 0.0, "state": "release_marker",
                         "releases": r["reservation_id"], "reason": "crash test",
                         "submitted_at": time.time()}, sort_keys=True) + "\n")

held = led.spent_today()
visible = len(led.pending_reservations())
print(f"  after a marker-only crash:")
print(f"    still counted against limits : {held} XRP")
print(f"    visible in reconciliation    : {visible} reservation(s)")
if held > 0 and visible == 0:
    findings.append("F1: headroom held but INVISIBLE after a partial release")
    print("  *** F1 CONFIRMED: the money is held and the operator cannot see it.")
    print("      _counts() excludes only state=='released'; pending_reservations()")
    print("      excludes anything with a release_marker. Two different sets.")
    print(f"    report says: {led.reconciliation_report()[:60]}")

print()
print("=" * 70)
print("F2: releasing the same reservation twice")
print("=" * 70)
sl2 = f"{work}/s2.jsonl"
led2 = M.SpendLedger(sl2)
r2 = auth(sl2, 10.0)
auth(sl2, 10.0)
print(f"  held before: {led2.spent_today()} XRP")
led2.release(r2["reservation_id"], "first release")
after1 = led2.spent_today()
led2.release(r2["reservation_id"], "second release -- should be a no-op")
after2 = led2.spent_today()
print(f"  after first release : {after1} XRP")
print(f"  after second release: {after2} XRP")
if after2 < after1:
    findings.append("F2: double release frees headroom twice")
    print("  *** F2 CONFIRMED: releasing twice freed the amount twice.")
else:
    print("  held: a second release is a no-op")

print()
print("=" * 70)
print("F3: settling / releasing an id that was never reserved")
print("=" * 70)
sl3 = f"{work}/s3.jsonl"
led3 = M.SpendLedger(sl3)
auth(sl3, 10.0)
base = led3.spent_today()
led3.settle("forged-id-that-never-existed", tx_hash="F" * 64, engine_result="tesSUCCESS")
led3.release("another-forged-id", "attacker supplied")
after = led3.spent_today()
print(f"  held before forged calls: {base} XRP")
print(f"  held after  forged calls: {after} XRP")
if after != base:
    findings.append("F3: forged reservation ids alter the counted total")
    print("  *** F3 CONFIRMED: a forged id changed the totals.")
else:
    print("  held: unknown ids do not affect the counts")

print()
print("=" * 70)
print("F4: is /sync still an unauthenticated, unbounded amplifier?")
print("=" * 70)
import covenant_unified_v8 as cov
import inspect, re

# CORRECTED PROBE -- this originally read bootstrap_chain's DEFAULTS via
# inspect.signature and checked RATE_LIMIT. Both were the wrong things to look
# at: the fix bounds the call the ROUTE makes (not the function's defaults) and
# authenticates via PROTECTED_OPERATOR_ENDPOINTS (not RATE_LIMIT). A probe that
# measures the wrong surface reports a fixed issue as open, which is its own
# kind of failure -- a false alarm teaches you to ignore the alarm.
authed = ("POST", "/sync") in cov.PROTECTED_OPERATOR_ENDPOINTS
src = inspect.getsource(cov.CovenantAPI)
m = re.search(r"def sync\(\):.*?bootstrap_chain\(([^)]*)\)", src, re.S)
call = m.group(1).strip() if m else ""
rounds = 1 if "rounds=1" in call else inspect.signature(
    cov.CovenantUnifiedMaster.bootstrap_chain).parameters["rounds"].default
pause = 0.0 if "pause=0.0" in call else inspect.signature(
    cov.CovenantUnifiedMaster.bootstrap_chain).parameters["pause"].default
worst = rounds * (pause + cov.PEER_SEND_TIMEOUT_S)
limit = cov.RATE_LIMIT.get("sync", cov.RATE_LIMIT_DEFAULT)

print(f"  authenticated                 : {authed}")
print(f"  route calls bootstrap_chain({call})")
print(f"  worst case one request holds  : ~{worst:.0f}s")
print(f"  rate limit                    : {limit}/60s")
if not authed:
    findings.append("F4: /sync is unauthenticated")
if worst > 20:
    findings.append(f"F4: one /sync can block a worker ~{worst:.0f}s")
if authed and worst <= 20:
    print("  held: authenticated, bounded to one round, and rate limited")

shutil.rmtree(work)
print()
print("=" * 70)
print(f"FINDINGS: {len(findings)}")
for f in findings:
    print(f"  - {f}")
print("=" * 70)
