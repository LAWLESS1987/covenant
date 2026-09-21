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
        # The node refuses a key readable beyond its owner (ops/owner_only.py), and the way the
        # node loads it is what D16 tests. On Linux the fixture's default mode is 0o644 and the
        # refusal fired on every CI run (carried back from the artifact, 5c9c0d9, 2026-09-21);
        # on NTFS the mode bit is not carried and Windows never saw it. The fixture writes the
        # key the way the node writes its own -- owner-only.
        os.chmod(kp, 0o600)
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

    # the heartbeat
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "checkins.jsonl")
        code, out = DP.record_checkin(json.dumps({"node_id": "phone", "chain_height": 18, "peers": 1, "app": "1.0", "battery": 71, "secret": "x" * 500}).encode(), "phone", led)
        rows = [json.loads(l) for l in open(led, encoding="utf-8")]
        check("D19 a signed check-in is recorded with the named fields only (the extra key is dropped unread)",
              code == 200 and len(rows) == 1 and rows[0]["chain_height"] == 18 and "secret" not in rows[0], rows)
        a1, i1 = DP.checkin_report(now=rows[0]["at"] + 300, path=led)
        a2, i2 = DP.checkin_report(now=rows[0]["at"] + 7200, path=led)
        a3, i3 = DP.checkin_report(now=rows[0]["at"] + 90000, path=led)
        check("D20 five minutes on it is an info line; two hours on it is an ALERT; a day on it is an info line again (an old phone is not news)",
              not a1 and len(i1) == 1 and "height 18" in i1[0] and len(a2) == 1 and "SILENT" in a2[0] and not a3 and len(i3) == 1, (a1, i1, a2, a3))
        # D20b (2026-09-14) -- THE ALERT TEXT MUST NOT CHANGE WHILE THE CONDITION DOES NOT.
        # The watchdog keys an alert on its first 80 characters and treats any change as
        # news, so a minute count inside the text made this line alert and CLEAR once a
        # minute for five hours while the phone sat switched off (measured live in
        # logs/watchdog.log). A60's lesson. Two readings an hour apart must be the same
        # string, and the first 80 characters -- the watchdog's actual key -- must match.
        a4, _i4 = DP.checkin_report(now=rows[0]["at"] + 7200, path=led)
        a5, _i5 = DP.checkin_report(now=rows[0]["at"] + 10800, path=led)
        check("D20b the SILENT alert says WHEN the phone went quiet, so its text (and the watchdog's "
              "key, its first 80 characters) is identical an hour later -- one alert, not one a minute",
              len(a4) == 1 and len(a5) == 1 and a4[0] == a5[0] and a4[0][:80] == a5[0][:80], (a4, a5))
        check("D20c ...and the changing minute count is still reported, in the INFO heartbeat line",
              "min ago" in i1[0], i1)
        code, out = DP.record_checkin(b"not json", "phone", led)
        check("D21 a body that is not JSON is refused (400) and nothing is written", code == 400 and len(open(led, encoding="utf-8").readlines()) == 1, code)
        # D21b (2026-09-19). The heartbeat names its installer of record, and
        # the ledger keeps it -- as a string, capped at 80 -- because Android's
        # no-tap install rule turns on exactly this fact. Driven both ways:
        # a dict where a string belongs is stringified and cut, never stored
        # whole; and the field is absent when the phone did not send it.
        with tempfile.TemporaryDirectory() as td2:
            led2 = os.path.join(td2, "c.jsonl")
            DP.record_checkin(json.dumps({"node_id": "phone", "installer": "org.covenant.node", "build": "65bc28b"}).encode(), "phone", led2)
            DP.record_checkin(json.dumps({"node_id": "phone", "installer": {"x": "y" * 200}}).encode(), "phone", led2)
            DP.record_checkin(json.dumps({"node_id": "phone"}).encode(), "phone", led2)
            r2 = [json.loads(l) for l in open(led2, encoding="utf-8")]
            # D21c (2026-09-19): the AI-chat batch recorder and the teacher's queue, both ways.
            cd, qp = os.path.join(td2, "chats"), os.path.join(td2, "queue.jsonl")
            body = json.dumps({"v": 1, "node_id": "phone", "lines": [
                {"t": 1, "pkg": "com.openai.chatgpt", "text": "a plain line about hash chains", "secret": "x" * 500},
                {"t": 2, "pkg": "../evil/../", "text": "y" * 900},
                "not a dict", {"t": 3, "pkg": "ai.x.grok", "text": "   "}]}).encode()
            code, out = DP.record_ai_chats(body, "phone", chats_dir=cd, queue_path=qp)
            files = sorted(os.listdir(cd))
            q = [json.loads(l) for l in open(qp, encoding="utf-8")]
            check("D21c a signed batch keeps the named fields only, caps a line at 600, sanitises the package name, skips junk and blanks, and queues every kept line for the teacher",
                  code == 200 and out["recorded"] == 2 and out["queued"] == 2 and files == ["..evil...jsonl", "com.openai.chatgpt.jsonl"]
                  and len(q) == 2 and len(q[1]["text"]) == 600 and "secret" not in open(os.path.join(cd, "com.openai.chatgpt.jsonl"), encoding="utf-8").read(),
                  (code, out, files, [len(x["text"]) for x in q]))
            code2, _ = DP.record_ai_chats(b"{}", "phone", chats_dir=cd, queue_path=qp)
            check("D21c a body without a lines list is refused 400 and nothing is written", code2 == 400 and len([json.loads(l) for l in open(qp, encoding="utf-8")]) == 2)
            check("D21c the queue is bounded: past TEACHER_QUEUE_MAX_ROWS nothing more is appended",
                  DP.teacher_queue_append([{"text": "z"}] * 3, path=qp) == 3 and (lambda: (setattr(DP, "TEACHER_QUEUE_MAX_ROWS", 5), DP.teacher_queue_append([{"text": "over"}], path=qp))[1])() == 0)
            DP.TEACHER_QUEUE_MAX_ROWS = 5000
            check("D21b the check-in's `installer` is kept as a string capped at 80, and absent when not sent",
                  r2[0].get("installer") == "org.covenant.node" and isinstance(r2[1]["installer"], str) and len(r2[1]["installer"]) == 80
                  and "installer" not in r2[2], r2)

        # D22 (2026-09-14). An empty order list means one of two completely
        # different things and the plan used to say the same calm sentence for
        # both: the planner ran and proposed nothing, or the planner could not
        # be asked at all. The second is what a person reads on their phone at
        # 07:26 before approving, so a crashed planner looked exactly like a
        # quiet market -- every morning, indefinitely. Both directions are
        # pinned: the crash must be LOUD, and an honest quiet day must NOT be.
        import tempfile as _tf
        _td = _tf.mkdtemp(prefix="dp1_d22_")

        def _g(planner, clears):
            def _inner(say=print):
                return {"posture": "", "rule5": {"clears": clears, "why": "because"},
                        "armed": True, "halt": False, "caps": {},
                        "orders_placed_today": 0, "proposed_orders": [], "planner": planner}
            return _inner

        crashed = DP.write(day="2099-01-01", say=lambda *a, **k: None, plan_dir=_td,
                           gatherer=_g("planner unavailable: RuntimeError: boom", True))
        quiet = DP.write(day="2099-01-02", say=lambda *a, **k: None, plan_dir=_td,
                         gatherer=_g("covenant_trader.run_once(plan_only=True)", False))
        check("D22a a planner that could not run says NOT ASKED, not 'no order proposed'",
              "NOT ASKED" in crashed["no_action_reason"]
              and "boom" in crashed["no_action_reason"],
              crashed["no_action_reason"][:70])
        check("D22b ...and a genuine quiet day still reads as one",
              quiet["no_action_reason"].startswith("no order proposed")
              and "NOT ASKED" not in quiet["no_action_reason"],
              quiet["no_action_reason"][:70])
        check("D22c ...and the two are not the same sentence",
              crashed["no_action_reason"] != quiet["no_action_reason"], "")

    n = sum(1 for r in results if r)
    print("\nDP1: %d/%d passed" % (n, len(results)))
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
