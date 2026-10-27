"""Verify the four external findings against covenant_xrp_mainnet, by running
them rather than by re-reading the code that produced them.

R1 authorize_mainnet_payment validates limits but records nothing, so nothing
   reserves the headroom it just checked.
R2 amounts are float, not integer drops; XRP has exactly 6 decimals and float
   accumulation drifts off the boundary.
R3 an RPC exception leaves activated=None, which SKIPS the activation and
   reserve check instead of failing closed.
R4 SpendLedger has no file locking, so concurrent processes read the same
   history and both authorize.
"""
import os, sys, json, time, math, tempfile, shutil, subprocess
from decimal import Decimal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_xrp_mainnet as M

work = tempfile.mkdtemp(prefix="review_")
GOOD = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"
pol = os.path.join(work, "policy.json")
proof = os.path.join(work, "proof.json")
M.record_testnet_proof("a" * 64, proof)

def write_policy(pp=10.0, pd=20.0, lt=100.0):
    with open(pol, "w") as fh:
        json.dump({"destinations": [{"address": GOOD, "label": "wallet",
                                     "tag_not_required": True}],
                   "max_per_payment_xrp": pp, "max_per_day_xrp": pd,
                   "max_lifetime_xrp": lt,
                   "require_confirmation_phrase": False}, fh)
    os.chmod(pol, 0o600)
write_policy()

print("=" * 70)
print("R1: does authorizing reserve any headroom?")
print("=" * 70)
sl = os.path.join(work, "spend1.jsonl")
auth = lambda amt, ledger=None: M.authorize_mainnet_payment(
    destination=GOOD, amount_xrp=amt, policy_path=pol,
    spend_ledger_path=ledger or sl, testnet_proof_path=proof)

before = M.SpendLedger(sl).spent_today()
n_ok = 0
for i in range(5):
    try:
        auth(10.0)          # each is exactly the per-payment cap
        n_ok += 1
    except M.MainnetGuardError as e:
        print(f"  call {i+1}: refused -- {str(e).splitlines()[0][:56]}")
after = M.SpendLedger(sl).spent_today()
print(f"  daily ceiling is 20.0 XRP; 10.0 XRP authorized {n_ok}/5 times")
print(f"  ledger total before: {before}   after: {after}")
if n_ok > 2:
    print(f"  *** R1 CONFIRMED: {n_ok} authorizations for {n_ok*10.0} XRP against a")
    print(f"      20.0 daily cap. Authorizing writes nothing, so nothing is held.")

print()
print("=" * 70)
print("R2: float vs integer drops at the limit boundary")
print("=" * 70)
sl2 = os.path.join(work, "spend2.jsonl")
led2 = M.SpendLedger(sl2)
for _ in range(3):
    led2.record(amount_xrp=16.666666, destination=GOOD, submitted_at=time.time(),
                committed=True, tx_hash="x" * 64)
tot = led2.spent_today()
exact = Decimal("16.666666") * 3
print(f"  three sends of 16.666666 XRP")
print(f"    float sum   : {tot!r}")
print(f"    exact sum   : {exact}")
print(f"    difference  : {Decimal(repr(tot)) - exact}")
print(f"    float == exact: {Decimal(repr(tot)) == exact}")
drift = abs(Decimal(repr(tot)) - exact)
if drift != 0:
    print(f"  *** R2 CONFIRMED: {drift} of drift after three sends. A limit")
    print(f"      comparison at the boundary is decided by rounding noise.")
# and the accumulation direction matters at a cap
print(f"    is the total already over a 49.999998 cap? {tot > 49.999998}")

print()
print("=" * 70)
print("R3: does an RPC exception fail open?")
print("=" * 70)
class ExplodingClient:
    def request(self, *a, **k):
        raise TimeoutError("simulated network timeout to the XRPL node")
sl3 = os.path.join(work, "spend3.jsonl")
try:
    res = M.authorize_mainnet_payment(
        destination=GOOD, amount_xrp=0.5, policy_path=pol,
        spend_ledger_path=sl3, testnet_proof_path=proof,
        client=ExplodingClient())
    print(f"  authorization SUCCEEDED despite the RPC failing")
    print(f"    destination_activated = {res['destination_activated']!r}")
    print(f"    amount {res['amount_xrp']} XRP is BELOW the 1 XRP reserve")
    print("  *** R3 CONFIRMED: the activation and reserve check was skipped,")
    print("      not enforced. An unreachable node silently disables a control.")
except M.MainnetGuardError as e:
    print(f"  refused: {str(e).splitlines()[0][:70]}")

print()
print("=" * 70)
print("R4: concurrent processes reading the same spend history")
print("=" * 70)
sl4 = os.path.join(work, "spend4.jsonl")
M.SpendLedger(sl4)
worker = os.path.join(work, "worker.py")
with open(worker, "w") as fh:
    fh.write(f'''
import sys, time
sys.path.insert(0, {os.path.dirname(os.path.abspath(__file__))!r})
import covenant_xrp_mainnet as M
t = float(sys.argv[1])
while time.time() < t:      # spin to a common start instant
    pass
try:
    r = M.authorize_mainnet_payment(
        destination={GOOD!r}, amount_xrp=10.0, policy_path={pol!r},
        spend_ledger_path={sl4!r}, testnet_proof_path={proof!r})
    M.SpendLedger({sl4!r}).record(
        amount_xrp=10.0, destination={GOOD!r}, submitted_at=time.time(),
        committed=True, tx_hash="c"*64)
    print("AUTHORIZED")
except M.MainnetGuardError as e:
    print("REFUSED")
''')
start = time.time() + 2.0
procs = [subprocess.Popen([sys.executable, worker, str(start)],
                          stdout=subprocess.PIPE, text=True) for _ in range(6)]
outs = [p.communicate()[0].strip() for p in procs]
authorized = sum(1 for o in outs if "AUTHORIZED" in o)
total = M.SpendLedger(sl4).spent_today()
print(f"  6 concurrent processes, 10.0 XRP each, 20.0 XRP daily cap")
print(f"    authorized: {authorized}    refused: {len(outs)-authorized}")
print(f"    total recorded as spent: {total} XRP")
if total > 20.0:
    print(f"  *** R4 CONFIRMED: {total} XRP got through a {20.0} XRP daily cap.")
    print(f"      Read-check-write with no lock is not a limit.")

shutil.rmtree(work)
