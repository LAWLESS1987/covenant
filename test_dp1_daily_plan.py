#!/usr/bin/env python3
"""test_dp1_daily_plan.py -- DP1: the day's plan, the signed approval, the gate.

Offline, in a temp directory: the gatherer is stubbed, keys are generated
here, nothing is placed anywhere. Every check RUNS the function it guards
(A87's lesson). The false pushes toward MORE capability that must be refused:
an unregistered key, a replayed nonce, a stale timestamp, a decision for a
plan whose hash moved, and an order with no approved plan.

Run: python test_dp1_daily_plan.py        -> "DP1: n/n passed"
"""
import base64
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_daily_plan as DP                            # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:220]), flush=True)


def stub_gather(say=print):
    return {"posture": "STUB POSTURE", "rule5": {"clears": False, "why": "0 settled signals, need 30"},
            "armed": False, "halt": False, "caps": {"max_order_usd": 100.0}, "orders_placed_today": 0,
            "proposed_orders": [], "planner": "stub"}


def main():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    with tempfile.TemporaryDirectory() as td:
        plan_dir = os.path.join(td, "daily_plan"); approvals = os.path.join(td, "approvals.jsonl"); signers = os.path.join(td, "signers.json")
        say = lambda *a: None
        plan = DP.write(say=say, plan_dir=plan_dir, gatherer=stub_gather)
        loaded = DP.load(plan["date"], plan_dir)
        check("D1 write() writes today's plan with a hash over its canonical bytes, and load() checks that hash",
              loaded is not None and loaded["sha256"] == DP.plan_sha(loaded) and loaded["date"] == DP.today()
              and "hold" not in loaded["no_action_reason"] and "no order proposed" in loaded["no_action_reason"], plan.get("no_action_reason"))
        p = os.path.join(plan_dir, plan["date"] + ".json")
        raw = open(p, encoding="utf-8").read().replace("STUB POSTURE", "STUB POSTURE (edited)")
        open(p, "w", encoding="utf-8").write(raw)
        check("D2 a plan whose bytes moved after it was written is no plan (load() returns None)", DP.load(plan["date"], plan_dir) is None)
        plan = DP.write(say=say, plan_dir=plan_dir, gatherer=stub_gather)
        ok, why = DP.approved(plan["date"], plan_dir, approvals)
        check("D3 before any decision the plan is NOT approved, and it says so", not ok and "no decision" in why, why)

        phone = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        stranger = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        DP.register_signer("phone", DP.pubkey_pem(phone), signers)
        body = json.dumps({"date": plan["date"], "plan_sha256": plan["sha256"], "decision": "approve", "note": "looks right"}).encode()

        def signed(key, body_bytes, path=DP.APPROVE_PATH, method="POST"):
            h = DP.sign_headers(key, method, path, body_bytes)
            pem = base64.b64decode(h["X-Operator-Pubkey"]).decode()
            return pem, h

        seen = set()
        pem, h = signed(phone, body)
        ok, who = DP.verify_signed(pem, "POST", DP.APPROVE_PATH, body, h["X-Operator-Nonce"], h["X-Operator-Timestamp"], h["X-Operator-Signature"], signers, seen=seen)
        check("D4 a registered key's signature verifies and names the signer", ok and who == "phone", who)
        code, out = DP.handle_decision(body, who, pem, plan_dir, approvals)
        ok2, why2 = DP.approved(plan["date"], plan_dir, approvals)
        check("D5 the decision is recorded and the plan is APPROVED, by name", code == 200 and ok2 and "phone" in why2, (code, why2))

        pem_s, hs = signed(stranger, body)
        ok, who = DP.verify_signed(pem_s, "POST", DP.APPROVE_PATH, body, hs["X-Operator-Nonce"], hs["X-Operator-Timestamp"], hs["X-Operator-Signature"], signers, seen=seen)
        check("D6 an unregistered key is refused, however valid its signature", not ok and "not a registered" in who, who)
        ok, who = DP.verify_signed(pem, "POST", DP.APPROVE_PATH, body, h["X-Operator-Nonce"], h["X-Operator-Timestamp"], h["X-Operator-Signature"], signers, seen=seen)
        check("D7 the same signed request replayed is refused (nonce)", not ok and "nonce" in who, who)
        pem, h2 = signed(phone, body)
        ok, who = DP.verify_signed(pem, "POST", DP.APPROVE_PATH, body, h2["X-Operator-Nonce"], h2["X-Operator-Timestamp"], h2["X-Operator-Signature"], signers, now=time.time() + 3600, seen=set())
        check("D8 a signature outside the time window is refused", not ok and "window" in who, who)
        pem, h3 = signed(phone, body)
        ok, who = DP.verify_signed(pem, "POST", "/somewhere/else", body, h3["X-Operator-Nonce"], h3["X-Operator-Timestamp"], h3["X-Operator-Signature"], signers, seen=set())
        check("D9 a signature for another path does not verify here", not ok and "does not verify" in who, who)

        moved = json.dumps({"date": plan["date"], "plan_sha256": "0" * 64, "decision": "approve"}).encode()
        code, out = DP.handle_decision(moved, "phone", pem, plan_dir, approvals)
        check("D10 a decision naming a hash the plan does not have is refused (409), the ledger untouched",
              code == 409 and DP.approved(plan["date"], plan_dir, approvals)[0] is True, (code, out))
        code, out = DP.handle_decision(json.dumps({"date": plan["date"], "plan_sha256": plan["sha256"], "decision": "maybe"}).encode(), "phone", pem, plan_dir, approvals)
        check("D11 a decision that is neither approve nor decline is refused (400)", code == 400, code)

        dec = json.dumps({"date": plan["date"], "plan_sha256": plan["sha256"], "decision": "decline", "note": "not today"}).encode()
        code, out = DP.handle_decision(dec, "phone", pem, plan_dir, approvals)
        ok3, why3 = DP.approved(plan["date"], plan_dir, approvals)
        check("D12 a later decline withdraws the approval: the LAST decision wins, with its note", code == 200 and not ok3 and "declined" in why3 and "not today" in why3, why3)

        reasons = DP.gate_reasons(plan_dir=plan_dir, approvals=approvals)
        check("D13 the gate names the day and the reason when the plan is not approved", len(reasons) == 1 and plan["date"] in reasons[0] and "declined" in reasons[0], reasons)
        DP.handle_decision(body, "phone", pem, plan_dir, approvals)
        check("D14 the gate is silent for an approved plan", DP.gate_reasons(plan_dir=plan_dir, approvals=approvals) == [])
        check("D15 the gate refuses when no plan was written at all", "no plan written" in DP.gate_reasons(plan_dir=os.path.join(td, "nowhere"), approvals=approvals)[0])

        # the PC-side path: a node identity key on disk, loaded the way the node loads it, signs and is verified the same way
        kp = os.path.join(td, "node.db.key")
        open(kp, "wb").write(phone.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        code, out = DP.decide_locally("decline", "from the PC", key_path=kp, plan_dir=plan_dir, approvals=approvals, signers_path=signers)
        ok4, why4 = DP.approved(plan["date"], plan_dir, approvals)
        check("D16 --decline on the PC signs with the node key, verifies as the registered signer, and is the last word", code == 200 and not ok4 and "from the PC" in why4, (code, out))
        code, out = DP.decide_locally("approve", "", key_path=kp, plan_dir=plan_dir, approvals=approvals, signers_path=os.path.join(td, "empty.json"))
        check("D17 a key that is not registered cannot approve from the PC either", code == 403, (code, out))

        # the guard: one rule for every executor
        import guards
        save = (DP.PLAN_DIR, DP.APPROVALS)
        DP.PLAN_DIR, DP.APPROVALS = plan_dir, approvals
        try:
            order = {"side": "sell", "usd": 10.0, "sym": "XLM"}
            bad_declined = guards.preconditions(order, cfg={"armed": True}, st={}, sealed_ok=True, guard_blocks=[])
            DP.handle_decision(body, "phone", pem, plan_dir, approvals)
            bad_approved = guards.preconditions(order, cfg={"armed": True}, st={}, sealed_ok=True, guard_blocks=[])
            bad_off = guards.preconditions(order, cfg={"armed": True, "daily_plan_required": False}, st={}, sealed_ok=True, guard_blocks=[])
        finally:
            DP.PLAN_DIR, DP.APPROVALS = save
        has = lambda bad: any("daily plan" in b for b in bad)
        check("D18 guards.preconditions carries the daily-plan reason while the plan is declined, drops it once approved, and only cfg daily_plan_required=false switches it off",
              has(bad_declined) and not has(bad_approved) and not has(bad_off), (bad_declined, bad_approved, bad_off))

    n = sum(1 for r in results if r)
    print("\nDP1: %d/%d passed" % (n, len(results)))
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
