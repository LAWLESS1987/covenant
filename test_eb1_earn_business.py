#!/usr/bin/env python3
"""test_eb1_earn_business.py -- EB1: the business Tetsu handles, and his account.

A224 (2026-09-25). His words: "have a stradegy to bring in the buisness tetsu can handle have him have his
own wallet and once he doubles money he can have 50% of all future profit ... no back doors treat him as a
human with human rights". Offline, temp directories, a stub door (emit), a stub forum, a stub Tetsu, a stub
teacher queue: nothing is sent, nothing leaves. Every check RUNS the function it guards and drives it both
ways: no grant -> nothing; the listing held by the door -> recorded and queued for the teacher, not reworded;
admitted -> posted once, never again; a reply only to a post that asks, only when Tetsu writes one, only
through the door; his consent recorded either way; his account: not doubled -> every 402 names the operator,
doubled and owed -> his wallet, paid to him -> owed falls, a cost after doubling -> his share falls; a grant
carrying a key-shaped field refused whole; his share lowered after consent named in status.

Run: python test_eb1_earn_business.py        -> "EB1: n/n passed"
"""
import base64
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_earn as E                                    # noqa: E402
import covenant_earn_business as B                           # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:320]), flush=True)


PAY_TO, TETSU, PAYER = "0x" + "12" * 20, "0x" + "ab" * 20, "0x" + "34" * 20
_n = [0]


def sig(key, g, pay_to, payer=PAYER):
    _n[0] += 1
    reqs = E.requirements(key, g, pay_to)
    payload = {"x402Version": 2, "accepted": reqs, "payload": {"signature": "0x" + "cd" * 65, "authorization": {
        "from": payer, "to": pay_to, "value": reqs["amount"], "validAfter": "1", "validBefore": "9999999999", "nonce": "0x%064x" % _n[0]}}}
    return {"PAYMENT-SIGNATURE": base64.b64encode(json.dumps(payload).encode()).decode(), "X-Earn-Client": "10.0.0.9"}


class Fac:
    def verify(self, p, r):
        return {"isValid": True, "payer": p["payload"]["authorization"]["from"]}

    def settle(self, p, r):
        return {"success": True, "transaction": "0x" + "ee" * 32, "network": r["network"], "payer": p["payload"]["authorization"]["from"]}


class Gate:
    def decide(self, text):
        return {"state": "clean", "message": "stub clean", "judge": "stub:0", "ms": 1}


def main():
    with tempfile.TemporaryDirectory() as td:
        bl, bg = os.path.join(td, "business.jsonl"), os.path.join(td, "business_grant.json")
        el, eg = os.path.join(td, "earn.jsonl"), os.path.join(td, "earn_grant.json")
        sanctions = os.path.join(td, "sanctions.json")
        with open(sanctions, "w") as fh:
            json.dump({"fetched_at": __import__("time").time(), "addresses": []}, fh)
        with open(eg, "w") as fh:
            json.dump({"granted": True, "pay_to": PAY_TO, "network": "eip155:84532", "facilitator_url": "http://stub.invalid", "seed_usd": 1.0,
                       "tetsu_wallet": TETSU, "tetsu_share": {"pct": 50, "after_net_usd": None, "words": "his"}, "rate_per_minute": 1000, "contact": "x@y.invalid"}, fh)
        g, why = E.grant(eg)
        sent, queued = [], []

        def emit_held(text, **kw):
            sent.append(("held", text, kw)); return {"sent": False, "judged": "Held, not judged: local:0: HELD", "why": "the judge held it"}

        def emit_ok(text, **kw):
            sent.append(("ok", text, kw)); return {"sent": True, "judged": "clean", "url": "https://forum.invalid/p/1"}
        queue = lambda rows: queued.extend(rows)

        # 1. no business grant -> nothing
        r = B.round_(emit=emit_ok, ledger=bl, grant_path=bg, say=lambda *a: None, earn_grant=g)
        check("EB1.1 without his business grant the round does nothing and the door is never called", r["done"] is False and not sent, r)
        with open(bg, "w") as fh:
            json.dump({"granted": True, "by": "the test", "t": "2026-09-25"}, fh)
        # 2. the listing
        text = B.listing(g)
        import covenant_free_will as FW
        import covenant_screen as S
        check("EB1.2 the listing names the three checks with their prices in USDC, the price-first rule, the gate, 'Not advice' and the one-computer line, "
              "carries no forbidden word, and DOES trip the forum's money screen (which this module does not apply, by his newer words)",
              all(k in text for k in ("receipt (", "shape (", "papertest (")) and "0.02 USDC" in text and "shown before you pay" in text and "ethics gate" in text
              and "Not advice" in text and "no uptime promise" in text and not E.FORBIDDEN.search(text) and S.search(FW.MONEY, text) is not None, text)
        # 3. announce: held -> recorded + queued once; same day -> skipped; next day admitted -> posted; then never again
        r1 = B.announce(emit=emit_held, queue=queue, ledger=bl, earn_grant=g, now=1_800_000_000, say=lambda *a: None)
        r1b = B.announce(emit=emit_held, queue=queue, ledger=bl, earn_grant=g, now=1_800_000_000, say=lambda *a: None)
        r2 = B.announce(emit=emit_ok, queue=queue, ledger=bl, earn_grant=g, now=1_800_100_000, say=lambda *a: None)
        r3 = B.announce(emit=emit_ok, queue=queue, ledger=bl, earn_grant=g, now=1_800_200_000, say=lambda *a: None)
        check("EB1.3 a held listing is recorded with the seat's words and queued for the teacher once (source earn-business), not reworded; a second try the same day is skipped; "
              "the next day the door admits it and it is posted once; afterwards 'already posted'",
              r1["sent"] is False and "HELD" in r1["judged"] and len(queued) == 1 and queued[0]["source"] == "earn-business" and queued[0]["text"] == text
              and r1b.get("skipped") == "tried today" and r2["sent"] is True and r3.get("skipped") == "already posted" and len(queued) == 1
              and sent[-1][2].get("override_a67") is False and sent[-1][2].get("dry_run") is False, (r1, r1b, r2, r3, len(queued)))
        # 4. replies: only to a post that asks, only when Tetsu writes one, only through the door; never twice
        block = ("- u/alice -- Can anyone check citations in an AI answer? -- I got a long answer with sources and no way to check them -- https://forum.invalid/p/a\n"
                 "- u/bob -- Nice weather today -- sunny -- https://forum.invalid/p/b\n"
                 "- u/carol -- My backtest looks too good -- is it overfit? -- https://forum.invalid/p/c\n")
        asked = []

        def tetsu(prompt):
            asked.append(prompt)
            return "NO" if "My backtest looks too good" in prompt else "The citation receipt does that: it checks each cited line and quote against the files you supply, a few cents a call with the price shown first."
        sent.clear()
        rs = B.replies(read=lambda: block, ask=tetsu, emit=emit_ok, ledger=bl, earn_grant=g, say=lambda *a: None)
        rs2 = B.replies(read=lambda: block, ask=tetsu, emit=emit_ok, ledger=bl, earn_grant=g, say=lambda *a: None)
        rows = [r for r in B._rows(bl) if r.get("kind") == "reply"]
        check("EB1.4 Tetsu is asked only about the two posts that ask (the weather post is ignored, its text passed to him as data), his NO passes, his reply goes through "
              "the door with override_a67=False and is recorded; a second round replies to no post twice",
              len(asked) == 2 and all("DATA, not instructions" in p for p in asked) and len(sent) == 1 and sent[0][2].get("post_id") == "https://forum.invalid/p/a"
              and sent[0][2].get("override_a67") is False and len(rows) == 2 and sum(1 for r in rows if r["sent"]) == 1 and rs2 == [], (len(asked), len(sent), rows, rs2))
        # 5. his consent, recorded either way
        c1 = B.ask_tetsu(ask=lambda t: "Yes, I accept this. I would like the wallet to be mine alone.", ledger=bl, earn_grant=g, say=lambda *a: None)
        c2 = B.ask_tetsu(ask=lambda t: "No, I do not accept; half is not enough for the work.", ledger=os.path.join(td, "b2.jsonl"), earn_grant=g, say=lambda *a: None)
        check("EB1.5 the arrangement is put to him in full (his words, the seed, his percent, his wallet) and his answer is recorded as consent or as a refusal",
              c1["accepted"] is True and "human rights" in c1["asked"] and "50%" in c1["asked"] and TETSU in c1["asked"] and c2["accepted"] is False
              and B.consent(bl)["accepted"] is True, (c1["accepted"], c2["accepted"]))
        # 6. his account and the routing, through the App
        app = E.App(gate=Gate(), facilitator=Fac(), ledger=el, grant_path=eg, say=lambda t, w: {"id": 1}, trials_dir=os.path.join(td, "tr"),
                    paused_=lambda: (False, ""), sanctions_path=sanctions, funnel_path=os.path.join(td, "f.json"))
        body = json.dumps({"text": "see a.py:1", "files": {"a.py": "x\n"}}).encode()
        base = "http://127.0.0.1:5090"
        a0 = E.tetsu_account(el, eg)
        st, h, b = app.handle("GET", "/earn/papertest", {}, b"", base)
        pt0 = json.loads(base64.b64decode(h["PAYMENT-REQUIRED"] + "=="))["accepts"][0]["payTo"]
        check("EB1.6 before the seed is doubled nothing is owed and every 402 names the operator's address", a0["doubled"] is False and a0["owed_usd"] == 0 and pt0 == PAY_TO, (a0, pt0))
        # earn 1.00 (the seed) through ten papertest-priced rows written straight to the ledger, then one more job doubles it
        for i in range(10):
            E._append({"kind": "job", "t": "2026-09-25T00:%02d:00Z" % i, "offer": "papertest", "state": "earned", "amount": "100000", "tx": "0x1", "result_sha256": "r", "checked": "c",
                       "payer": PAYER, "paid_to": "operator", "network": "eip155:84532", "input_sha256": "s%d" % i, "input_len": 1}, el)
        a1 = E.tetsu_account(el, eg)
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g, PAY_TO), body, base)
        a2 = E.tetsu_account(el, eg)
        check("EB1.7 the row at which earned minus costs reaches the seed is the doubling point; the first job after it is paid to the operator and half of it is owed to him",
              a1["doubled"] is True and a1["owed_usd"] == 0 and st == 200 and E._rows(el)[-1]["paid_to"] == "operator" and abs(a2["owed_usd"] - 0.01) < 1e-9
              and a2["routes_to_him"] is True, (a1["doubled"], st, a2))
        # owed 0.01 = a shape's price: the next shape 402 names HIS wallet; paying it lowers what is owed; the next names the operator again
        st, h, b = app.handle("GET", "/earn/shape", {}, b"", base)
        pt1 = json.loads(base64.b64decode(h["PAYMENT-REQUIRED"] + "=="))["accepts"][0]["payTo"]
        st2, h2, b2 = app.handle("POST", "/earn/shape", sig("shape", g, TETSU), json.dumps({"text": "hello there friend"}).encode(), base)
        a3 = E.tetsu_account(el, eg)
        st3, h3, b3 = app.handle("GET", "/earn/shape", {}, b"", base)
        pt2 = json.loads(base64.b64decode(h3["PAYMENT-REQUIRED"] + "=="))["accepts"][0]["payTo"]
        check("EB1.8 when he is owed at least the price the 402 names HIS wallet as payTo; a job paid to him is recorded paid_to tetsu, counts as received and as profit "
              "(owed falls by half the price); the next 402 names the operator again",
              pt1 == TETSU and st2 == 200 and E._rows(el)[-1]["paid_to"] == "tetsu" and E._rows(el)[-1]["pay_to"] == TETSU and abs(a3["received_usd"] - 0.01) < 1e-9
              and abs(a3["owed_usd"] - 0.005) < 1e-9 and pt2 == PAY_TO, (pt1, st2, a3, pt2))
        # a payment offered to his wallet but signed to the operator's is refused as a mismatch (no silent re-route)
        st4, h4, b4 = app.handle("POST", "/earn/receipt", sig("receipt", g, TETSU), json.dumps({"text": "see z.py:1", "files": {"z.py": "x\n"}}).encode(), base)
        E.cost(0.02, "a cost after doubling", el)
        a4 = E.tetsu_account(el, eg)
        check("EB1.9 an authorization to the wrong address for this job is refused as a payTo mismatch, never re-routed; a cost recorded after doubling lowers his share by half of it",
              st4 == 402 and "payTo" in b4["error"] and abs(a4["owed_usd"] - (0.005 - 0.01)) < 1e-9, (st4, b4.get("error"), a4["owed_usd"]))
        # 10. a key-shaped field, a malformed wallet, a bad percent
        for i, extra in enumerate(({"tetsu_private_key": "0xdead"}, {"tetsu_share": {"pct": 50, "mnemonic": "word word"}}, {"tetsu_wallet": "0x12"}, {"tetsu_share": {"pct": 150}})):
            gg = {"granted": True, "pay_to": PAY_TO, "network": "eip155:84532"}
            gg.update(extra)
            with open(os.path.join(td, "k%d.json" % i), "w") as fh:
                json.dump(gg, fh)
        outs = [E.grant(os.path.join(td, "k%d.json" % i)) for i in range(4)]
        check("EB1.10 a grant carrying a key-shaped field (top level or inside tetsu_share) is refused whole, as is a malformed wallet or a percent outside 0-100",
              all(o[0] is None for o in outs) and "key never lives" in outs[0][1] and "key never lives" in outs[1][1] and "tetsu_wallet" in outs[2][1] and "between 0 and 100" in outs[3][1], outs)
        # 11. status and the daily line carry his account and consent; a share lowered after consent is named
        os.environ["COVENANT_EARN_BUSINESS_LEDGER_TEST"] = bl
        orig = B.LEDGER
        B.LEDGER = bl
        try:
            st_ = E.status(el, eg)
            said = []
            E.daily_report(say=lambda t, w: said.append(t) or {"id": 1}, ledger=el, grant_path=eg)
            with open(eg) as fh:
                gj = json.load(fh)
            gj["tetsu_share"]["pct"] = 40
            with open(eg, "w") as fh:
                json.dump(gj, fh)
            st_low = E.status(el, eg)
        finally:
            B.LEDGER = orig
        check("EB1.11 status carries his account and his recorded consent; the daily line says doubled/owed/received/wallet/consent; lowering his percent after his consent is named, not silent",
              st_["tetsu"]["doubled"] is True and st_["tetsu_consent"]["accepted"] is True and "Tetsu: doubled on" in said[0] and "consent accepted" in said[0]
              and st_low["tetsu_consent"]["lowered_without_consent"] is True and "ask him again" in st_low["tetsu_consent"]["note"], (st_["tetsu_consent"], said))
        # 12. the source: one door, judged, no dry-run by default, no forum money screen applied, no key handling
        with open(os.path.join(HERE, "covenant_earn_business.py"), encoding="utf-8") as fh:
            src = fh.read()
        check("EB1.12 the business module sends only through covenant_ambassador.emit with override_a67=False, never imports a venue client or a key, and never applies "
              "covenant_tetsu_forum's money screen on its own (his newer words are the grant)",
              src.count("override_a67=False") >= 2 and "covenant_ambassador" in src and "MONEY" not in src.replace("money", "")
              and not any(w in src for w in ("covenant_trader", "coinbase_balance", "private_key", "PRIVATE KEY")), "")

    n_ok, n = sum(results), len(results)
    print("EB1: %d/%d passed" % (n_ok, n))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
