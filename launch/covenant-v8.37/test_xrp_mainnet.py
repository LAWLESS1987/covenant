"""Offline tests for covenant_xrp_mainnet. No network, no funds, no signing.

Every check here corresponds to a way people permanently lose XRP.
"""
import os, sys, json, time, stat, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_xrp_mainnet as M

passed = failed = 0
def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        failed += 1; print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))

def refuses(fn, needle):
    try:
        fn(); return False, "no exception raised"
    except M.MainnetGuardError as e:
        return needle.lower() in str(e).lower(), str(e).replace("\n", " ")[:78]
    except Exception as e:
        return False, f"wrong type {type(e).__name__}: {e}"

work = tempfile.mkdtemp(prefix="mainnet_")
GOOD = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"
GOOD2 = "r9cZA1mLK5R5Am25ArfXFmqgNwjZgnfk59"

print("== address validation (checksum, not prefix) ==")
c, t = M.validate_destination(GOOD)
check("a real classic address validates", c == GOOD and t is None)
ok, why = refuses(lambda: M.validate_destination("rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRX"), "checksum")
check("a single mistyped character is caught", ok, why)
ok, why = refuses(lambda: M.validate_destination("rDest0000000000000000000000000"), "checksum")
check("the old signer's own test address is rejected", ok, why)
ok, why = refuses(lambda: M.validate_destination(""), "empty")
check("an empty destination is rejected", ok, why)
c, t = M.validate_destination("X7AcgcsBL6XDcUb289X4mJ8djcdyKaB5hJDWMArnXr61cqZ")
check("an X-address decodes to classic form", c == GOOD2, f"{c} tag={t}")

print("\n== testnet proof gate ==")
proof = os.path.join(work, "proof.json")
ok, why = refuses(lambda: M.require_testnet_proof(proof), "never executed")
check("mainnet is blocked with no testnet proof", ok, why)
M.record_testnet_proof("a" * 64, proof)
check("a recorded proof unlocks the gate",
      M.require_testnet_proof(proof)["tx_hash"] == "a" * 64)
with open(proof, "w") as fh:
    json.dump({"tx_hash": "short"}, fh)
ok, why = refuses(lambda: M.require_testnet_proof(proof), "valid testnet tx hash")
check("a malformed proof does not unlock the gate", ok, why)
M.record_testnet_proof("a" * 64, proof)

print("\n== policy file ==")
pol = os.path.join(work, "policy.json")
ok, why = refuses(lambda: M.MainnetPolicy.load(pol), "no mainnet policy")
check("a missing policy blocks all sends", ok, why)
M.write_policy_template(pol)
check("template is written mode 0600",
      stat.S_IMODE(os.stat(pol).st_mode) == 0o600)
ok, why = refuses(lambda: M.write_policy_template(pol), "refusing to overwrite")
check("an existing policy is never overwritten", ok, why)
ok, why = refuses(lambda: M.MainnetPolicy.load(pol), "checksum")
check("the template's placeholder address fails validation", ok, why)

def write_policy(dests, **kw):
    body = {"destinations": dests, "max_per_payment_xrp": kw.get("pp", 10.0),
            "max_per_day_xrp": kw.get("pd", 50.0),
            "max_lifetime_xrp": kw.get("lt", 500.0),
            "require_confirmation_phrase": kw.get("conf", True)}
    with open(pol, "w") as fh:
        json.dump(body, fh)
    os.chmod(pol, 0o600)

write_policy([])
ok, why = refuses(lambda: M.MainnetPolicy.load(pol), "no destinations")
check("an empty allowlist means no sends", ok, why)

write_policy([{"address": GOOD, "label": "exchange deposit",
               "destination_tag": 12345}])
os.chmod(pol, 0o644)
ok, why = refuses(lambda: M.MainnetPolicy.load(pol), "chmod 600")
check("a world-readable policy is refused", ok, why)
os.chmod(pol, 0o600)

write_policy([{"address": GOOD, "label": "x", "destination_tag": 1}], pp=100.0, pd=50.0)
ok, why = refuses(lambda: M.MainnetPolicy.load(pol), "never bind")
check("a per-payment cap above the daily cap is refused", ok, why)

print("\n== the gate ==")
sl = os.path.join(work, "spend.jsonl")
def auth(**kw):
    args = dict(destination=GOOD, amount_xrp=1.0, policy_path=pol,
                spend_ledger_path=sl, testnet_proof_path=proof)
    args.update(kw)
    return M.authorize_mainnet_payment(**args)

write_policy([{"address": GOOD, "label": "exchange deposit", "destination_tag": 12345}])
ok, why = refuses(lambda: auth(destination=GOOD2), "not in the mainnet allowlist")
check("an address outside the allowlist is refused", ok, why)

for bad, needle in ((0.0, "positive"), (-1.0, "positive"),
                    (float("nan"), "finite"), (float("inf"), "finite"),
                    ("lots", "not a valid decimal number")):
    ok, why = refuses(lambda b=bad: auth(amount_xrp=b), needle)
    check(f"amount {bad!r} is refused", ok, why)

ok, why = refuses(lambda: auth(amount_xrp=999.0), "per-payment ceiling")
check("a payment over the per-payment ceiling is refused", ok, why)

ok, why = refuses(lambda: auth(destination_tag=999), "policy does not name")
check("a tag that disagrees with the policy is refused", ok, why)

write_policy([{"address": GOOD, "label": "some exchange"}])
ok, why = refuses(lambda: auth(), "most common way xrp is permanently lost")
check("sending with NO destination tag is refused by default", ok, why)

write_policy([{"address": GOOD, "label": "my own wallet", "tag_not_required": True}])
ok, why = refuses(lambda: auth(), "not confirmed")
check("a tag-exempt destination proceeds to confirmation", ok, why)

phrase = M.confirmation_phrase(GOOD, 1.0, None)
res = auth(confirmation=phrase)
check("the correct confirmation phrase authorizes", res["amount_xrp"] == 1.0, phrase)
ok, why = refuses(lambda: auth(confirmation="SEND-1-XRP-WRONG1"), "not confirmed")
check("a wrong confirmation phrase is refused", ok, why)
ok, why = refuses(lambda: auth(amount_xrp=2.0, confirmation=phrase), "not confirmed")
check("a phrase for one amount cannot confirm another", ok, why)

print("\n== cumulative limits (item AP: reserve-then-settle, exact drops) ==")
write_policy([{"address": GOOD, "label": "w", "tag_not_required": True}],
             pp=10.0, pd=20.0, lt=40.0, conf=False)
sl3 = os.path.join(work, "spend3.jsonl")
a3 = lambda amt: M.authorize_mainnet_payment(
    destination=GOOD, amount_xrp=amt, policy_path=pol,
    spend_ledger_path=sl3, testnet_proof_path=proof)

r1 = a3(10.0)
check("authorizing RESERVES headroom immediately",
      abs(M.SpendLedger(sl3).spent_today() - 10.0) < 1e-9,
      f"{M.SpendLedger(sl3).spent_today()}")
check("a reservation id is returned", bool(r1.get("reservation_id")))
r2 = a3(10.0)
ok, why = refuses(lambda: a3(10.0), "daily ceiling")
check("the daily ceiling binds on the THIRD authorization", ok, why)

M.SpendLedger(sl3).settle(r2["reservation_id"], tx_hash="b" * 64,
                          engine_result="tesSUCCESS")
check("settling does NOT free headroom",
      abs(M.SpendLedger(sl3).spent_today() - 20.0) < 1e-9,
      f"{M.SpendLedger(sl3).spent_today()}")

M.SpendLedger(sl3).release(r1["reservation_id"], "ledger rejected: tecNO_DST")
check("releasing a definitely-failed payment returns its headroom",
      abs(M.SpendLedger(sl3).spent_today() - 10.0) < 1e-9,
      f"{M.SpendLedger(sl3).spent_today()}")

print("\n== exact drops, never float ==")
check("1.1 XRP is exactly 1100000 drops", M.xrp_to_drops_exact("1.1") == 1100000)
check("1.1 + 2.2 in drops is exact (float gives 3.3000000000000003)",
      M.xrp_to_drops_exact(1.1) + M.xrp_to_drops_exact(2.2) == M.xrp_to_drops_exact("3.3"))
check("0.7 x 3 in drops is exact (float gives 2.0999999999999996)",
      3 * M.xrp_to_drops_exact(0.7) == M.xrp_to_drops_exact("2.1"))
ok, why = refuses(lambda: M.xrp_to_drops_exact(0.0000001), "finer than one drop")
check("a sub-drop amount is refused, not silently accepted", ok, why)
ok, why = refuses(lambda: M.xrp_to_drops_exact(float("nan")), "finite")
check("NaN is refused by the drops converter", ok, why)

print("\n== fail closed when a control cannot be evaluated ==")
class _Exploding:
    def request(self, *a, **k):
        raise TimeoutError("simulated node timeout")
sl4 = os.path.join(work, "spend4.jsonl")
ok, why = refuses(lambda: M.authorize_mainnet_payment(
    destination=GOOD, amount_xrp=0.5, policy_path=pol, spend_ledger_path=sl4,
    testnet_proof_path=proof, client=_Exploding()), "cannot be evaluated")
check("an RPC failure REFUSES rather than skipping the activation check", ok, why)

print("\n== AQ: locking is portable, and never silently absent ==")
check("a locking implementation was selected",
      M._LOCK_IMPL in ("fcntl", "msvcrt"), str(M._LOCK_IMPL))
_orig = M._LOCK_IMPL
M._LOCK_IMPL = None
ok, why = refuses(lambda: M.SpendLedger(os.path.join(work, "nolock.jsonl")),
                  "not a spending limit")
check("with no locking available, SpendLedger refuses to exist", ok, why)
M._LOCK_IMPL = _orig
check("normal construction still works once locking is restored",
      M.SpendLedger(os.path.join(work, "relock.jsonl")) is not None)

print("\n== AR: orphaned reservations are visible and reconcilable ==")
write_policy([{"address": GOOD, "label": "w", "tag_not_required": True}],
             pp=10.0, pd=20.0, lt=40.0, conf=False)
sl6 = os.path.join(work, "spend6.jsonl")
led6 = M.SpendLedger(sl6)
check("a clean ledger reports nothing to reconcile",
      "No unsettled reservations" in led6.reconciliation_report())

a6 = lambda amt: M.authorize_mainnet_payment(
    destination=GOOD, amount_xrp=amt, policy_path=pol,
    spend_ledger_path=sl6, testnet_proof_path=proof)
r_orphan = a6(10.0)                      # reserved, signed, never settled
led6.attach_hash(r_orphan["reservation_id"], "D" * 64)
r_done = a6(10.0)
led6.settle(r_done["reservation_id"], tx_hash="E" * 64, engine_result="tesSUCCESS")

pend = led6.pending_reservations()
check("exactly the unsettled reservation is reported", len(pend) == 1, f"{len(pend)}")
check("a settled reservation is NOT reported as pending",
      all(p["reservation_id"] != r_done["reservation_id"] for p in pend))
check("the orphan carries the tx_hash needed to check the ledger",
      pend[0].get("tx_hash") == "D" * 64, str(pend[0].get("tx_hash"))[:16])
check("age is reported so a stale hold is recognisable", "age_s" in pend[0])
check("age filtering works", len(led6.pending_reservations(older_than_s=3600)) == 0)

ok, why = refuses(lambda: a6(5.0), "UNSETTLED RESERVATIONS")
check("a limit refusal TELLS the operator orphans are part of the total", ok, why)

rep = led6.reconciliation_report()
check("the report explains how to resolve each case",
      "settle(" in rep and "release(" in rep and "UNSURE" in rep)
check("the report warns against releasing an ambiguous send",
      "duplicate payment" in rep)

led6.release(r_orphan["reservation_id"], "confirmed absent from ledger")
check("releasing the orphan frees its headroom and clears the report",
      abs(led6.spent_today() - 10.0) < 1e-9
      and "No unsettled reservations" in led6.reconciliation_report(),
      f"{led6.spent_today()}")

print("\n== AS: ledger reconciliation automates investigation, not release ==")
write_policy([{"address": GOOD, "label": "w", "tag_not_required": True}],
             pp=10.0, pd=30.0, lt=100.0, conf=False)
sl7 = os.path.join(work, "spend7.jsonl")
led7 = M.SpendLedger(sl7)
a7 = lambda amt: M.authorize_mainnet_payment(
    destination=GOOD, amount_xrp=amt, policy_path=pol,
    spend_ledger_path=sl7, testnet_proof_path=proof)

_rf = a7(10.0); led7.attach_hash(_rf["reservation_id"], "A" * 64)   # landed
_ra = a7(10.0); led7.attach_hash(_ra["reservation_id"], "B" * 64)   # never landed
_rn = a7(10.0)                                                      # died pre-signing

class _Resp:
    def __init__(self, ok, res): self._ok = ok; self.result = res
    def is_successful(self): return self._ok
class _FakeLedger:
    def request(self, req):
        h = getattr(req, "transaction", None) or getattr(req, "tx_hash", "")
        if h == "A" * 64:
            return _Resp(True, {"meta": {"TransactionResult": "tesSUCCESS"}})
        return _Resp(False, {"error": "txnNotFound"})

_held_before = led7.spent_today()
_rep = led7.reconcile_with_ledger(_FakeLedger(), auto_settle=True)
check("a payment present on-ledger is classified FOUND", len(_rep["found"]) == 1)
check("a payment absent from the ledger is classified ABSENT", len(_rep["absent"]) == 1)
check("a reservation that never signed is classified UNKNOWN", len(_rep["unknown"]) == 1)
check("a confirmed tesSUCCESS payment is auto-settled", len(_rep["settled"]) == 1)
check("auto-settling frees NO headroom",
      abs(led7.spent_today() - _held_before) < 1e-9,
      f"{_held_before} -> {led7.spent_today()}")
check("NOTHING is ever auto-released", led7.spent_today() >= 30.0 - 1e-9,
      f"{led7.spent_today()}")
check("the ABSENT verdict warns about the account sequence",
      "sequence" in _rep["absent"][0]["verdict"])
_still = {r["reservation_id"] for r in led7.pending_reservations()}
check("the settled one drops out of pending, the other two remain",
      _rf["reservation_id"] not in _still and _ra["reservation_id"] in _still
      and _rn["reservation_id"] in _still)

class _BrokenLedger:
    def request(self, req): raise TimeoutError("node unreachable")
_rep2 = M.SpendLedger(sl7).reconcile_with_ledger(_BrokenLedger(), auto_settle=True)
check("an unreachable ledger yields UNKNOWN, never a release",
      len(_rep2["settled"]) == 0 and abs(M.SpendLedger(sl7).spent_today() - 30.0) < 1e-9,
      f"{M.SpendLedger(sl7).spent_today()}")

print("\n== AQ: the lock region is unambiguous ==")
_l = M.SpendLedger(os.path.join(work, "lockcheck.jsonl"))
check("the lock file holds at least one byte, so byte 0 is a real range",
      os.path.getsize(_l.lock_path) >= 1, f"{os.path.getsize(_l.lock_path)} bytes")

print("\n== AT: a crash mid-release must not hide held money ==")
sl8 = os.path.join(work, "spend8.jsonl")
led8 = M.SpendLedger(sl8)
write_policy([{"address": GOOD, "label": "w", "tag_not_required": True}],
             pp=10.0, pd=50.0, lt=500.0, conf=False)
r8 = M.authorize_mainnet_payment(destination=GOOD, amount_xrp=10.0, policy_path=pol,
                                 spend_ledger_path=sl8, testnet_proof_path=proof)
with open(sl8, "a") as fh:      # marker lands, rewrite never happens
    fh.write(json.dumps({"reservation_id": r8["reservation_id"], "drops": 0,
                         "amount_xrp": 0.0, "state": "release_marker",
                         "releases": r8["reservation_id"], "reason": "crash",
                         "submitted_at": time.time()}, sort_keys=True) + "\n")
check("money still held after a partial release is STILL VISIBLE",
      led8.spent_today() > 0 and len(led8.pending_reservations()) == 1,
      f"held {led8.spent_today()}, visible {len(led8.pending_reservations())}")
check("the report does not claim there is nothing to reconcile",
      "No unsettled reservations" not in led8.reconciliation_report())
n_fixed = led8.repair_partial_releases()
check("repair_partial_releases completes the interrupted release", n_fixed == 1, str(n_fixed))
check("after repair the headroom is returned and the report is clean",
      abs(led8.spent_today()) < 1e-9 and not led8.pending_reservations(),
      f"{led8.spent_today()}")
check("repair is idempotent", led8.repair_partial_releases() == 0)

print("\n== AU: /sync is privileged and bounded ==")
import covenant_unified_v8 as _cov
check("POST /sync requires operator authentication",
      ("POST", "/sync") in _cov.PROTECTED_OPERATOR_ENDPOINTS,
      str(sorted(_cov.PROTECTED_OPERATOR_ENDPOINTS)))

print("\n== concurrent processes cannot breach the cap ==")
# Restore the 20 XRP daily cap: the reconciliation section above rewrote the
# shared policy file to 30, and this test asserts against 20.
write_policy([{"address": GOOD, "label": "w", "tag_not_required": True}],
             pp=10.0, pd=20.0, lt=100.0, conf=False)
import subprocess as _sp
sl5 = os.path.join(work, "spend5.jsonl")
M.SpendLedger(sl5)
wpath = os.path.join(work, "w.py")
with open(wpath, "w") as fh:
    fh.write(f"""
import sys, time
sys.path.insert(0, {os.path.dirname(os.path.abspath(__file__))!r})
import covenant_xrp_mainnet as M
t = float(sys.argv[1])
while time.time() < t: pass
try:
    r = M.authorize_mainnet_payment(destination={GOOD!r}, amount_xrp=10.0,
        policy_path={pol!r}, spend_ledger_path={sl5!r}, testnet_proof_path={proof!r})
    time.sleep(0.3)
    M.SpendLedger({sl5!r}).settle(r["reservation_id"], tx_hash="c"*64,
                                  engine_result="tesSUCCESS")
    print("A")
except M.MainnetGuardError:
    print("R")
""")
_start = time.time() + 2.0
_ps = [_sp.Popen([sys.executable, wpath, str(_start)], stdout=_sp.PIPE, text=True)
       for _ in range(8)]
_outs = [p.communicate()[0].strip() for p in _ps]
_tot = M.SpendLedger(sl5).spent_today()
check("8 concurrent processes cannot exceed a 20 XRP daily cap",
      _tot <= 20.0 + 1e-9,
      f"{sum(1 for o in _outs if o=='A')} authorized, {_tot} XRP total")

shutil.rmtree(work)
print("\n" + "=" * 62)
print(f"{passed} passed, {failed} failed")
print("=" * 62)
sys.exit(1 if failed else 0)
