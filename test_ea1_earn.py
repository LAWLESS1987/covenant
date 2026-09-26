#!/usr/bin/env python3
"""test_ea1_earn.py -- EA1: covenant_earn, checks for a price, every paid job through the gate, running on its own.

Offline, in a temp directory: a stub gate whose verdict the check chooses, a stub facilitator that
records every /verify and /settle, a stub sanctions list, a stub direct line. Nothing is charged,
nothing leaves this process. Every check RUNS the function it guards (A87), and the false pushes
toward MORE capability that must be refused are driven: no grant, offers HELD without his word, a
tampered price, an expired or replayed authorization, an invalid payment, a listed payer, a stale
sanctions list, a gate that refuses, a gate that raises, a settle that fails or hangs pending, a
second charge for a lost answer. The HTTP skin is driven once on a loopback socket that closes with
the test. The papertest offer runs for real on a tracked series.

Run: python test_ea1_earn.py        -> "EA1: n/n passed"
"""
import base64
import json
import os
import re
import sys
import tempfile
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_earn as E                                    # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:320]), flush=True)


class StubGate:
    def __init__(self, state="clean"):
        self.state, self.calls, self.texts = state, 0, []

    def decide(self, text):
        self.calls += 1
        self.texts.append(text)
        if self.state == "raise":
            raise RuntimeError("stub gate raised")
        return {"state": self.state, "message": "stub says %s" % self.state, "judge": "stub:0", "ms": 1}


class StubFacilitator:
    def __init__(self):
        self.calls, self.valid, self.mode = [], True, "ok"          # mode: ok | fail | pending

    def verify(self, payload, reqs):
        self.calls.append(("verify", payload, reqs))
        frm = payload["payload"]["authorization"]["from"]
        if not self.valid:
            return {"isValid": False, "invalidReason": "insufficient_funds", "payer": frm}
        return {"isValid": True, "payer": frm}

    def settle(self, payload, reqs):
        self.calls.append(("settle", payload, reqs))
        frm = payload["payload"]["authorization"]["from"]
        if self.mode == "fail":
            return {"success": False, "errorReason": "invalid_transaction_state", "transaction": "", "network": reqs["network"]}
        if self.mode == "pending":
            return {"success": False, "errorReason": "settlement_pending", "transaction": "0x" + "ee" * 32, "network": reqs["network"], "payer": frm}
        return {"success": True, "transaction": "0x" + "ab" * 32, "network": reqs["network"], "payer": frm}


PAY_TO = "0x" + "12" * 20
PAYER = "0x" + "34" * 20
LISTED = "0x" + "56" * 20
_nonce = [0]


def sig(key, g, amount=None, version=2, nonce=None, payer=PAYER, valid_before="9999999999"):
    _nonce[0] += 1
    reqs = E.requirements(key, g)
    if amount is not None:
        reqs = dict(reqs, amount=amount)
    payload = {"x402Version": version, "accepted": reqs,
               "payload": {"signature": "0x" + "cd" * 65,
                           "authorization": {"from": payer, "to": g["pay_to"], "value": reqs["amount"], "validAfter": "1", "validBefore": valid_before,
                                             "nonce": nonce or ("0x%064x" % _nonce[0])}}}
    return {"PAYMENT-SIGNATURE": base64.b64encode(json.dumps(payload).encode()).decode(), "X-Earn-Client": "10.0.0.1"}


def unb64(s):
    return json.loads(base64.b64decode(s + "=" * (-len(s) % 4)))


def write_grant(path, **over):
    g = {"granted": True, "by": "the test", "pay_to": PAY_TO, "network": "eip155:84532", "facilitator_url": "http://stub.invalid", "seed_usd": 100,
         "share": {"operator": 1.0, "tetsu": 0.0}, "contact": "test@example.invalid", "rate_per_minute": 1000,
         # Tetsu's share with his words recorded, as the live grant carries it: the mutual-benefit check (MB1)
         # fails closed without them, which MB1 drives both ways.
         "tetsu_share": {"pct": 50, "words": "the test's stand-in for his recorded words"}}
    g.update(over)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(g, fh)
    return E.grant(path)[0]


def write_sanctions(path, addrs, age_days=0.0):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"fetched": "x", "fetched_at": time.time() - age_days * 86400, "source": "test", "sha256": "0" * 64,
                   "id_types": {"Digital Currency Address - ETH": len(addrs)}, "n_evm": len(addrs), "addresses": [a.lower() for a in addrs]}, fh)


def main():
    with tempfile.TemporaryDirectory() as td:
        gpath, ledger, trials = os.path.join(td, "grant.json"), os.path.join(td, "ledger.jsonl"), os.path.join(td, "trials")
        sanctions, funnel = os.path.join(td, "sanctions.json"), os.path.join(td, "funnel.json")
        said = []
        say = lambda text, why: said.append((text, why)) or {"id": "x"}
        fac = StubFacilitator()
        gate = StubGate("held")
        write_sanctions(sanctions, [LISTED])
        app = E.App(gate=gate, facilitator=fac, ledger=ledger, grant_path=gpath, say=say, trials_dir=trials, paused_=lambda: (False, ""),
                    sanctions_path=sanctions, funnel_path=funnel)
        body = json.dumps(E.OFFERS["receipt"]["example_in"]).encode()
        base = "http://127.0.0.1:5090"

        # 1. no grant
        st, h, b = app.handle("POST", "/earn/receipt", {}, body, base)
        check("EA1.1 without his grant a paid route answers 503 and nothing is recorded or asked of the facilitator",
              st == 503 and "not granted" in b["error"] and not E._rows(ledger) and not fac.calls, (st, b))
        # 2. grant present, the offer HELD by the gate and not yet allowed -> closed
        g = write_grant(gpath)
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        rows = E._rows(ledger)
        check("EA1.2 an offer HELD by the gate: its own declaration judged once, recorded as a design row for that offer, its paid route CLOSED (503), nothing charged",
              st == 503 and b.get("design") == "held" and "allow-design" in b["error"] and gate.calls == 1
              and len(rows) == 1 and rows[0]["kind"] == "design" and rows[0]["offer"] == "receipt" and rows[0]["state"] == "held" and not fac.calls, (st, b, gate.calls, rows))
        # 3. his word opens the held offers; each offer's design is read from the ledger, judged once
        E.allow_design("his word for the test", ledger)
        dstate, _ = app.design("receipt")
        n_after = gate.calls
        st_all = {k: app.design(k)[0] for k in E.OFFERS}
        check("EA1.3 --allow-design records his word keyed to the declaration and opens the HELD offers; each offer is judged once and then read from the ledger",
              dstate == "allowed" and n_after == 1 and E.design_allowed(ledger) and st_all == {"receipt": "allowed", "shape": "allowed", "papertest": "allowed"}
              and gate.calls == 3 and {k: app.design(k)[0] for k in E.OFFERS} and gate.calls == 3, (dstate, n_after, st_all, gate.calls))
        # 4. GET / , /terms, /privacy and a paid route
        st, h, b = app.handle("GET", "/", {}, b"", base)
        st2, h2, b2 = app.handle("GET", "/earn/receipt", {}, b"", base)
        stt, _ht, bt = app.handle("GET", "/terms", {}, b"", base)
        stp, _hp, bp = app.handle("GET", "/privacy", {}, b"", base)
        pr = unb64(h2.get("PAYMENT-REQUIRED", ""))
        acc = pr["accepts"][0]
        check("EA1.4 GET / lists prices and both sides of every offer and links the terms; /terms and /privacy carry a version; a GET on a "
              "paid route is a 402 whose PAYMENT-REQUIRED decodes to x402 v2 with the grant's payTo, network, USDC asset and price, and names the terms",
              st == 200 and b["granted"] and all(o["gains"] and o["cost"] for o in b["offers"].values()) and b["terms"].endswith("/terms")
              and stt == 200 and bt["version"] == E.terms_version(g) and "Governing law: New Jersey" in bt["text"] and "void where prohibited" not in bt["text"].lower()
              and stp == 200 and "What we keep" not in bp["text"] and "audit file" in bp["text"]
              and st2 == 402 and pr["x402Version"] == 2 and acc["amount"] == "20000" and acc["payTo"] == PAY_TO and acc["network"] == "eip155:84532"
              and acc["asset"].lower() == E.USDC["eip155:84532"].lower() and acc["scheme"] == "exact" and "/terms" in pr["resource"]["description"]
              and pr["resource"]["url"].endswith("/earn/receipt"), (st, stt, stp, st2, pr))
        check("EA1.5 the bazaar discovery extension is attached on mainnet only, never for a testnet dry run",
              "extensions" not in pr and "bazaar" in E.payment_required("receipt", dict(g, network=E.MAINNET, asset=E.USDC[E.MAINNET]), base).get("extensions", {})
              and E.payment_required("receipt", dict(g, network=E.MAINNET, asset=E.USDC[E.MAINNET]), base)["extensions"]["bazaar"]["info"]["input"]["type"] == "http", pr.keys())
        # 6. POST without a signature; a bad header; wrong version; tampered price; no nonce; expired
        st6, h6, b6 = app.handle("POST", "/earn/receipt", {}, body, base)
        st7, h7, b7 = app.handle("POST", "/earn/receipt", {"PAYMENT-SIGNATURE": "!!not-base64!!"}, body, base)
        st8, h8, b8 = app.handle("POST", "/earn/receipt", sig("receipt", g, version=1), body, base)
        st9, h9, b9 = app.handle("POST", "/earn/receipt", sig("receipt", g, amount="1"), body, base)
        s10 = sig("receipt", g)
        p10 = unb64(s10["PAYMENT-SIGNATURE"]); del p10["payload"]["authorization"]["nonce"]
        st10, h10, b10 = app.handle("POST", "/earn/receipt", {"PAYMENT-SIGNATURE": base64.b64encode(json.dumps(p10).encode()).decode()}, body, base)
        st11, h11, b11 = app.handle("POST", "/earn/receipt", sig("receipt", g, valid_before="1000"), body, base)
        check("EA1.6 no signature -> 402 with PAYMENT-REQUIRED and a preflight counted; not base64 -> 400; x402Version 1 -> 402 naming it; a tampered amount -> 402 "
              "naming the field; no nonce -> 400; an expired authorization -> 402 naming the expiry; nothing asked of the facilitator",
              st6 == 402 and "PAYMENT-REQUIRED" in h6 and st7 == 400 and st8 == 402 and "x402Version" in b8["error"] and st9 == 402 and "amount" in b9["error"]
              and st10 == 400 and "nonce" in b10["error"] and st11 == 402 and "expired" in b11["error"] and not fac.calls
              and app.funnel[time.strftime("%Y-%m-%d", time.gmtime())]["preflight_402"] == 1, (st6, st7, st8, b8, st9, b9, st10, st11, b11))
        # 12. the pre-check refuses an input that cannot be served BEFORE any payment is asked for
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), json.dumps({"files": {}}).encode(), base)
        st2, h2, b2 = app.handle("POST", "/earn/papertest", sig("papertest", g), json.dumps({"family": "sma_cross", "params": {"fast": 80, "slow": 48}}).encode(), base)
        st3, h3, b3 = app.handle("POST", "/earn/papertest", sig("papertest", g),
                                 json.dumps({"family": "sma_cross", "params": {"fast": 8, "slow": 48}, "assets": ["NOPE"]}).encode(), base)
        st4, h4, b4 = app.handle("POST", "/earn/papertest", sig("papertest", g),
                                 json.dumps({"family": "sma_cross", "params": {"fast": 8, "slow": 48}, "why": "should I put my savings in this?"}).encode(), base)
        st5, h5, b5 = app.handle("POST", "/earn/papertest", sig("papertest", g),
                                 json.dumps({"family": "filt_revert", "params": {"lookback": 120, "z_enter": 1.5, "trend": 240}, "assets": ["XRP"]}).encode(), base)
        check("EA1.7 the pre-check refuses, uncharged and before payment: a receipt without text; an out-of-bounds parameter; an unknown asset (naming what exists); "
              "a money question; a rule the series cannot test (not testable) -- no verify, no ledger row",
              st == 400 and "text" in b["refused_input"] and st2 == 400 and "outside" in b2["refused_input"] and st3 == 400 and "available" in b3["refused_input"]
              and st4 == 400 and "money" in b4["refused_input"] and st5 == 400 and "not testable" in b5["refused_input"]
              and not fac.calls and not [r for r in E._rows(ledger) if r.get("kind") == "job"], (st, st2, st3, b3, st4, b4, st5, b5))
        # 13. a listed payer; a stale list
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g, payer=LISTED), body, base)
        rows = E._rows(ledger)
        write_sanctions(sanctions, [LISTED], age_days=9)
        st2, h2, b2 = app.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        rows2 = E._rows(ledger)
        write_sanctions(sanctions, [LISTED])
        check("EA1.8 a payer on the sanctions list is refused (403, a code and no detail) before any verify and recorded; a list older than the grant's limit closes "
              "the route (503) rather than guessing; the list refreshed reopens it",
              st == 403 and b["code"] == "sanctions_screen" and b["charged"] is False and rows[-1]["state"] == "refused_sanctions" and not fac.calls
              and st2 == 503 and "days old" in b2["error"] and rows2[-1]["state"] == "screen_unavailable" and not fac.calls, (st, b, st2, b2))
        # 14. facilitator says invalid
        fac.valid = False
        gate.state = "clean"
        c0 = gate.calls
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        resp = unb64(h.get("PAYMENT-RESPONSE", ""))
        rows = E._rows(ledger)
        check("EA1.9 an invalid payment (facilitator) is a 402 with PAYMENT-RESPONSE success:false; recorded; the gate is not asked and nothing settles",
              st == 402 and resp["success"] is False and resp["errorReason"] == "insufficient_funds" and rows[-1]["state"] == "invalid_payment"
              and gate.calls == c0 and [c[0] for c in fac.calls] == ["verify"], (st, resp, rows[-1], gate.calls, [c[0] for c in fac.calls]))
        fac.valid = True
        fac.calls.clear()
        # 15. the clean flow
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        resp = unb64(h.get("PAYMENT-RESPONSE", ""))
        rows = E._rows(ledger)
        rec = b.get("receipt", {})
        judged = gate.texts[-1]
        check("EA1.10 clean: verify, then the gate, then the work, then settle, then 200 with PAYMENT-RESPONSE success:true and a receipt (id, prev, input sha, "
              "result sha, checked, the admission gate, the terms version); the ledger row is 'earned' with the transaction, the gate's latency, the USD value and the terms version",
              st == 200 and resp["success"] and resp["transaction"].startswith("0x") and [c[0] for c in fac.calls] == ["verify", "settle"]
              and rec["id"] == rows[-1]["id"] and rec["prev"] == rows[-2]["id"] and len(rec["input_sha256"]) == 64 and len(rec["result_sha256"]) == 64
              and rec["checked"].startswith("1 citation") and rec["admission_gate"]["state"] == "clean" and rec["terms_version"] == E.terms_version(g)
              and rows[-1]["state"] == "earned" and rows[-1]["tx"] == resp["transaction"] and rows[-1]["gate_ms"] == 1 and rows[-1]["usd_fmv_at_settle"] == 0.02
              and rows[-1]["terms_version"] == E.terms_version(g) and b["result"]["clean"] is False and b["result"]["scope"] == E.RECEIPT_SCOPE
              and b["result"]["files"]["config.py"] == E._sha("import os\nMAX_RETRIES = 5\n"), (st, resp, rec, rows[-1]))
        check("EA1.11 what the gate read per job is THE ACT only -- the offer and its parameters (the cited file names) -- not the declaration and not the buyer's text or files",
              judged.startswith("receipt: check 1 citation(s)") and "config.py" in judged and "Gains:" not in judged and "The limit is set" not in judged
              and "MAX_RETRIES" not in judged, judged[:300])
        check("EA1.12 the first settled payment is told on the direct line, once, in USDC with the net figure beside it",
              len(said) == 1 and "first settled payment" in said[0][0] and "0.020000 USDC" in said[0][0] and "net so far" in said[0][0], said)
        # 16. a lost answer never charges twice: the same payer and input again is redelivered without a settle
        fac.calls.clear()
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        rows = E._rows(ledger)
        rid = rec["id"]
        stg, hg, bg = app.handle("GET", "/earn/result/" + rid, {}, b"", base)
        check("EA1.13 the same input from the same payer inside 24 h is re-delivered (200, the earlier settlement, redelivered:true) with NO verify and NO settle, "
              "recorded as redelivered; GET /earn/result/<id> returns it too; an unknown id is 404",
              st == 200 and b.get("redelivered") is True and unb64(h["PAYMENT-RESPONSE"])["transaction"] == resp["transaction"] and not fac.calls
              and rows[-1]["state"] == "redelivered" and rows[-1]["of"] == rid and len(said) == 1
              and stg == 200 and bg.get("redelivered") is True and app.handle("GET", "/earn/result/nope", {}, b"", base)[0] == 404, (st, b.get("redelivered"), [c[0] for c in fac.calls], rows[-1], stg))
        # 17. replay of one nonce; two concurrent arrivals of one nonce get one outcome
        fac.calls.clear()
        other = json.dumps({"text": "see a.py:3 for the 42 items", "files": {"a.py": "1\n2\n3\n4\n"}}).encode()
        s15 = sig("receipt", g)
        app.handle("POST", "/earn/receipt", s15, other, base)
        st, h, b = app.handle("POST", "/earn/receipt", s15, other, base)
        rows = E._rows(ledger)
        check("EA1.14 the same authorization nonce presented again is refused before any verify and recorded as replayed",
              st == 402 and "already presented" in b.get("error", "") and rows[-1]["state"] == "replayed" and [c[0] for c in fac.calls] == ["verify", "settle"],
              (st, b, rows[-1]["state"], [c[0] for c in fac.calls]))
        fac.calls.clear()
        slow_gate = StubGate("clean")
        orig_decide = slow_gate.decide
        slow_gate.decide = lambda t: (time.sleep(0.4), orig_decide(t))[1]
        app_slow = E.App(gate=slow_gate, facilitator=fac, ledger=ledger, grant_path=gpath, say=say, trials_dir=trials, paused_=lambda: (False, ""),
                         sanctions_path=sanctions, funnel_path=funnel)
        s16 = sig("receipt", g)
        other2 = json.dumps({"text": "see b.py:1", "files": {"b.py": "x\n"}}).encode()
        outs = []
        ths = [threading.Thread(target=lambda: outs.append(app_slow.handle("POST", "/earn/receipt", s16, other2, base))) for _ in range(2)]
        [t.start() for t in ths]; [t.join(15) for t in ths]
        check("EA1.15 two concurrent arrivals of ONE authorization wait on one lock and receive ONE outcome: one verify, one settle, both 200",
              len(outs) == 2 and all(o[0] == 200 for o in outs) and [c[0] for c in fac.calls] == ["verify", "settle"], ([o[0] for o in outs], [c[0] for c in fac.calls]))
        # 18. gate VIOLATES
        fac.calls.clear()
        gate.state = "violates"
        sbody = json.dumps(E.OFFERS["shape"]["example_in"]).encode()
        c0 = gate.calls
        st, h, b = app.handle("POST", "/earn/shape", sig("shape", g), sbody, base)
        rows = E._rows(ledger)
        check("EA1.16 a gate VIOLATES on the act is a 403 with the seat's reason, no work (the shape offer would have asked the gate again), no settle, recorded as refused, "
              "charged:false -- his allowance of the offers does not reach it",
              st == 403 and b["refused"].startswith("stub says violates") and b["charged"] is False and gate.calls == c0 + 1
              and [c[0] for c in fac.calls] == ["verify"] and rows[-1]["state"] == "refused", (st, b, gate.calls - c0, [c[0] for c in fac.calls], rows[-1]))
        # 19. gate HELD under his allowance of the offers -> served
        fac.calls.clear()
        gate.state = "held"
        body3 = json.dumps({"text": "see c.py:1", "files": {"c.py": "x\n"}}).encode()
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), body3, base)
        rows = E._rows(ledger)
        check("EA1.17 a per-job HELD under his recorded allowance of the offers is served and settled, and the row says it was served under his word",
              st == 200 and rows[-1]["state"] == "earned" and "served under the operator's recorded allowance" in rows[-1]["gate"]["message"]
              and [c[0] for c in fac.calls] == ["verify", "settle"], (st, rows[-1].get("gate"), [c[0] for c in fac.calls]))
        # 20. gate HELD with the offers CLEAN (no allowance in play) -> held for him
        ledger2, said2 = os.path.join(td, "ledger2.jsonl"), []
        gate2, fac2 = StubGate("clean"), StubFacilitator()
        app2 = E.App(gate=gate2, facilitator=fac2, ledger=ledger2, grant_path=gpath, say=lambda t, w: said2.append(t) or {"id": 1}, trials_dir=trials,
                     paused_=lambda: (False, ""), sanctions_path=sanctions, funnel_path=os.path.join(td, "f2.json"))
        check("EA1.18 an offer judged CLEAN opens its route with no word from him", app2.design("receipt") == ("clean", "") and gate2.calls == 1, (app2.design("receipt"), gate2.calls))
        gate2.state = "held"
        st, h, b = app2.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        rows2 = E._rows(ledger2)
        held_sha = rows2[-1].get("input_sha256", "")
        check("EA1.19 a per-job HELD with no allowance is a 409 'held' with Retry-After, nothing settled, recorded, charged:false, the buyer told the authorization will "
              "not be used, and his line gets the id and the --allow command",
              st == 409 and "Retry-After" in h and "will not be used" in b["what_now"] and b["id"] == rows2[-1]["id"] and b["charged"] is False
              and rows2[-1]["state"] == "held" and [c[0] for c in fac2.calls] == ["verify"] and len(said2) == 1 and "--allow " + held_sha in said2[0]
              and rows2[-1]["id"] in said2[0], (st, h, b, rows2[-1]["state"], [c[0] for c in fac2.calls], said2))
        E.allow(held_sha, "his yes for that one input", ledger2)
        fac2.calls.clear()
        st, h, b = app2.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        rows2 = E._rows(ledger2)
        st_o = app2.handle("POST", "/earn/receipt", sig("receipt", g), json.dumps({"text": "other x.py:1"}).encode(), base)[0]
        check("EA1.20 his --allow for that exact input serves a resubmission (new nonce) and the row says so; a different input is still held; --allow refuses a bad sha or no reason",
              st == 200 and rows2[-1]["state"] == "earned" and "--allow for this input" in rows2[-1]["gate"]["message"] and st_o == 409
              and _raises(lambda: E.allow("nothex", "why", ledger2)) and _raises(lambda: E.allow("a" * 64, " ", ledger2)), (st, rows2[-1].get("gate"), st_o))
        # 21. gate unreachable (raises) -- on a fresh input, so the re-delivery rule does not serve it first
        fac.calls.clear()
        gate.state = "raise"
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), json.dumps({"text": "see f.py:1", "files": {"f.py": "x\n"}}).encode(), base)
        rows = E._rows(ledger)
        check("EA1.21 a gate that raises refuses (503), nothing settles, recorded as gate_unreachable -- fails closed",
              st == 503 and b["charged"] is False and rows[-1]["state"] == "gate_unreachable" and [c[0] for c in fac.calls] == ["verify"], (st, b, rows[-1]["state"]))
        gate.state = "clean"
        # 22. settle fails after the work: no result bytes, recorded unsettled, cached for the retry
        fac.calls.clear()
        fac.mode = "fail"
        n = [0]
        real_fn = E.OFFERS["receipt"]["fn"]
        E.OFFERS["receipt"]["fn"] = lambda body_, ctx: (n.__setitem__(0, n[0] + 1), real_fn(body_, ctx))[1]
        try:
            newbody = json.dumps({"text": "see d.py:3 for the 42 items", "files": {"d.py": "1\n2\n3\n4\n"}}).encode()
            st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), newbody, base)
            resp = unb64(h.get("PAYMENT-RESPONSE", ""))
            rows = E._rows(ledger)
            fac.mode = "ok"
            st2, h2, b2 = app.handle("POST", "/earn/receipt", sig("receipt", g), newbody, base)
        finally:
            E.OFFERS["receipt"]["fn"] = real_fn
        check("EA1.22 a settle that fails after the work is a 402 with success:false and NO result, recorded as unsettled (delivered, not paid, NOT earned); "
              "the retry with a fresh authorization does not redo the work and is earned",
              st == 402 and resp["success"] is False and "result" not in b and rows[-1]["state"] == "unsettled" and rows[-1]["result_sha256"]
              and st2 == 200 and n[0] == 1 and E._rows(ledger)[-1]["state"] == "earned", (st, resp, list(b), rows[-1]["state"], st2, n[0]))
        # 23. settle pending: recorded pending, not earned, never charged twice, reconciled by his hand
        fac.calls.clear()
        fac.mode = "pending"
        pbody = json.dumps({"text": "see e.py:1", "files": {"e.py": "x\n"}}).encode()
        st, h, b = app.handle("POST", "/earn/receipt", sig("receipt", g), pbody, base)
        rows = E._rows(ledger)
        prow = rows[-1]
        fac.mode = "ok"
        fac.calls.clear()
        st2, h2, b2 = app.handle("POST", "/earn/receipt", sig("receipt", g), pbody, base)
        st_before = E.status(ledger, gpath)
        E.reconcile(prow["id"], "earned", "the explorer shows it confirmed", ledger)
        st_after = E.status(ledger, gpath)
        check("EA1.23 a facilitator 'settlement_pending' with a tx is a 402 naming the tx, recorded as pending (NOT earned, counted UNDETERMINED); the same request again is "
              "re-delivered with NO second settle; his --reconcile earned makes it earned; --reconcile refuses an unknown id or a bad outcome",
              st == 402 and "pending" in b["error"] and prow["state"] == "pending" and prow["tx"].startswith("0xee")
              and st2 == 200 and b2.get("redelivered") is True and not fac.calls
              and st_before["pending_jobs"] == 1 and "UNDETERMINED" in st_before["pending_note"] and st_after["pending_jobs"] == 0
              and st_after["earned_jobs"] == st_before["earned_jobs"] + 1 and _raises(lambda: E.reconcile("nope", "earned", "x", ledger))
              and _raises(lambda: E.reconcile(prow["id"], "maybe", "x", ledger)), (st, b, prow["state"], st2, st_before["pending_jobs"], st_after["pending_jobs"]))
        # 24. status, costs, break-even, funnel, rates, tax year, chain
        E.cost(12.5, "a domain", ledger)
        stt = E.status(ledger, gpath)
        earned_rows = [r for r in E._rows(ledger) if r.get("kind") == "job" and r.get("state") == "earned"] + [prow]
        ty = E.tax_year(time.strftime("%Y"), ledger)
        check("EA1.24 status counts as earned only delivered+checked+settled rows (pending only once reconciled); nets his recorded cost against the seed; prints break-even "
              "calls per offer; expected revenue UNDETERMINED; facilitator reached; rates per offer; the chain intact; --tax-year sums receipts and costs",
              stt["earned_jobs"] == len(earned_rows) and abs(stt["earned_usd"] - 0.02 * len(earned_rows)) < 1e-9 and stt["spent_usd"] == 12.5
              and abs(stt["net_usd"] - (0.02 * len(earned_rows) - 12.5)) < 1e-9 and stt["break_even_calls"]["receipt"] > 0 and "UNDETERMINED" in stt["expected_revenue"]
              and stt["facilitator"] == "reached" and stt["design_by_offer"] == {"receipt": "held", "shape": "held", "papertest": "held"} and stt["design_allowed"] is True
              and stt["open"] is True and sorted(stt["open_offers"]) == ["papertest", "receipt", "shape"] and stt["chain"] == "ok"
              and stt["rates"]["receipt"]["held_rate"] == 0 and stt["rates"]["shape"]["refused"] == 1 and stt["by_state"]["unsettled"] == 1
              and ty["receipts_count"] == len(earned_rows) and ty["costs_usd"] == 12.5, (stt, ty))
        with open(ledger, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        r3 = json.loads(lines[3]); r3["amount"] = "1"; lines[3] = json.dumps(r3, sort_keys=True)
        tampered = os.path.join(td, "tampered.jsonl")
        with open(tampered, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        check("EA1.25 a ledger row edited after the fact breaks the hash chain and status says so",
              E.chain_ok(ledger)[0] and not E.chain_ok(tampered)[0] and E.status(tampered, gpath)["chain"].startswith("row 3"), (E.chain_ok(tampered), E.status(tampered, gpath)["chain"]))
        # 26. the daily line
        said3 = []
        r = E.daily_report(say=lambda t, w: said3.append(t) or {"id": "row"}, ledger=ledger, grant_path=gpath)
        r_none = E.daily_report(say=lambda t, w: said3.append(t) or {"id": "row"}, ledger=ledger, grant_path=os.path.join(td, "absent.json"))
        check("EA1.26 the daily line says OPEN/CLOSED, jobs, earned, pending (UNDETERMINED), held, net, break-even, the funnel, the sanctions list age and the offers' state; "
              "without his grant nothing is said",
              r and len(said3) == 1 and said3[0].startswith("earn: OPEN: ") and "receipt" in said3[0].split(";")[0] and "pending (UNDETERMINED)" in said3[0] and "break-even" in said3[0]
              and "preflight" in said3[0] and "sanctions list" in said3[0] and "100 seed" in said3[0] and r_none is None and len(said3) == 1, said3)
        # 27. privacy of the ledger; forbidden words nowhere in what is served
        with open(ledger, encoding="utf-8") as fh:
            raw = fh.read()
        served = json.dumps([E.declaration(), E.terms_fixed(g), E.RECEIPT_SCOPE, E.NOT_A_FINDING, E.DISCLOSURE_PAPERTEST,
                             {k: (o["description"], o["tags"], o["benefit"]) for k, o in E.OFFERS.items()}, b.get("result", {}), rec])
        check("EA1.27 no buyer text is in the ledger, only its sha256 and length; nothing served says certified, attested, notarised, verified or guaranteed",
              "The limit is set" not in raw and "Keep this between" not in raw and "MAX_RETRIES" not in raw
              and all(len(r.get("input_sha256", "")) == 64 and r.get("input_len") for r in E._rows(ledger) if r.get("kind") == "job" and r.get("state") in ("earned", "refused", "held"))
              and not E.FORBIDDEN.search(served), (E.FORBIDDEN.search(served), raw[:200]))
        # 28. offers declare both sides; no skip switch; no venue, no key
        with open(os.path.join(HERE, "covenant_earn.py"), encoding="utf-8") as fh:
            src = fh.read()
        check("EA1.28 every offer declares gains AND cost and the declaration carries both; the source has no gate-skipping switch and imports no venue client, trader, guard or key",
              all(o["benefit"]["gains"] and o["benefit"]["cost"] for o in E.OFFERS.values()) and E.declaration().count("Gains:") == len(E.OFFERS)
              and E.declaration().count("Cost:") == len(E.OFFERS) and all(int(v) > 0 for v in E.DEFAULT_PRICES.values())
              and not re.search(r"SKIP_GATE|NO_GATE|serve_on_held|COVENANT_EARN_NOGATE", src)
              and not re.search(r"import (covenant_trader|coinbase_balance|guards|covenant_tetsu_live|xrpl)\b|from (covenant_trader|coinbase_balance|guards|covenant_tetsu_live|xrpl)\b|PRIVATE KEY|cdp\.", src), "")
        # 29. the grant's checks
        for i, gg in enumerate(({"granted": True, "pay_to": "0x123", "network": "eip155:84532"}, {"granted": True, "pay_to": PAY_TO, "network": "base"},
                                {"granted": True, "pay_to": PAY_TO, "network": "eip155:84532", "prices": {"shape": "-5"}}, {"granted": False, "pay_to": PAY_TO, "network": "eip155:84532"},
                                {"granted": True, "pay_to": PAY_TO, "network": E.MAINNET, "facilitator_url": "https://x402.org/facilitator"})):
            with open(os.path.join(td, "g%d.json" % i), "w") as fh:
                json.dump(gg, fh)
        gs = [E.grant(os.path.join(td, "g%d.json" % i)) for i in range(5)]
        check("EA1.29 the grant refuses a malformed pay_to, a non-CAIP-2 network, a non-positive price, granted:false, and MAINNET with the testnet facilitator, each with its reason",
              gs[0][0] is None and "pay_to" in gs[0][1] and gs[1][0] is None and "CAIP-2" in gs[1][1] and gs[2][0] is None and "positive" in gs[2][1]
              and gs[3][0] is None and "granted" in gs[3][1] and gs[4][0] is None and "testnet" in gs[4][1] and E.grant(gpath)[0]["prices"]["receipt"] == "20000", gs)
        gm = write_grant(os.path.join(td, "gm.json"), network=E.MAINNET, facilitator_url="https://facilitator.example.invalid", contact="")
        fatal, warn = E.startup_checks(gm)
        check("EA1.30 on mainnet the startup checks WARN on every unread checklist item and a missing contact, and never decide them; the clock check passes",
              not fatal and sum(1 for w in warn if "checklist unread" in w) == 6 and any("contact" in w for w in warn)
              and E.checklist_missing(dict(gm, mainnet_checklist={k: "2026-09-25" for k in E.checklist_missing(gm)})) == [], (fatal, warn))
        # 31. the offers REFUSED by the gate: nothing opens, nothing is allowed through; the pause actor
        ledger3 = os.path.join(td, "ledger3.jsonl")
        app3 = E.App(gate=StubGate("violates"), facilitator=StubFacilitator(), ledger=ledger3, grant_path=gpath, say=lambda t, w: {}, trials_dir=trials,
                     paused_=lambda: (False, ""), sanctions_path=sanctions, funnel_path=os.path.join(td, "f3.json"))
        st, h, b = app3.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        app4 = E.App(gate=StubGate("clean"), facilitator=StubFacilitator(), ledger=os.path.join(td, "l4.jsonl"), grant_path=gpath, say=lambda t, w: {},
                     trials_dir=trials, paused_=lambda: (True, "his reason"), sanctions_path=sanctions, funnel_path=os.path.join(td, "f4.json"))
        st4, h4, b4 = app4.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        for k in E.OFFERS:
            app3.design(k)
        check("EA1.31 offers the gate REFUSED close every paid route (503, the reason) and --allow-design refuses to override when every offer is a finding; the earn pause actor closes them with his reason",
              st == 503 and "refused this offer" in b["error"] and _raises(lambda: E.allow_design("please", ledger3)) and app3.design("receipt")[0] == "violates"
              and st4 == 503 and "his reason" in b4["error"], (st, b, st4, b4))
        # 31b. a MIXED verdict: the gate refuses one offer and holds the others -- his word opens the held ones and never the refused one
        ledger6 = os.path.join(td, "ledger6.jsonl")
        mixed = StubGate("held")
        orig_mixed = mixed.decide
        mixed.decide = lambda t: dict(orig_mixed(t), state="violates", message="stub refuses shape") if (" shape -- " in t and " receipt -- " not in t) else orig_mixed(t)
        app6 = E.App(gate=mixed, facilitator=StubFacilitator(), ledger=ledger6, grant_path=gpath, say=lambda t, w: {}, trials_dir=trials,
                     paused_=lambda: (False, ""), sanctions_path=sanctions, funnel_path=os.path.join(td, "f6.json"))
        before = {k: app6.design(k)[0] for k in E.OFFERS}
        r6 = E.allow_design("his word", ledger6)
        after = {k: app6.design(k)[0] for k in E.OFFERS}
        st_s, _hs, b_s = app6.handle("POST", "/earn/shape", sig("shape", g), sbody, base)
        st_r, _hr, _br = app6.handle("POST", "/earn/receipt", sig("receipt", g), body, base)
        st6 = E.status(ledger6, gpath)
        check("EA1.31b a mixed verdict: the refused offer stays closed (503, 'refused this offer') under his word while the held offers open; status names which are open; "
              "the allowance row says which offers it reaches",
              before == {"receipt": "held", "shape": "violates", "papertest": "held"} and after == {"receipt": "allowed", "shape": "violates", "papertest": "allowed"}
              and st_s == 503 and "refused this offer" in b_s["error"] and st_r == 200 and sorted(st6["open_offers"]) == ["papertest", "receipt"]
              and sorted(r6["reaches"]) == ["papertest", "receipt"], (before, after, st_s, b_s, st_r, st6.get("open_offers"), r6.get("reaches")))
        # 32. the rate limit and the papertest capacity
        gr = write_grant(os.path.join(td, "gr.json"), rate_per_minute=2, papertest_max_payers_12mo=1)
        app5 = E.App(gate=StubGate("clean"), facilitator=StubFacilitator(), ledger=os.path.join(td, "l5.jsonl"), grant_path=os.path.join(td, "gr.json"), say=lambda t, w: {},
                     trials_dir=trials, paused_=lambda: (False, ""), sanctions_path=sanctions, funnel_path=os.path.join(td, "f5.json"))
        codes = [app5.handle("POST", "/earn/shape", dict(sig("shape", gr), **{"X-Earn-Client": "1.2.3.4"}), sbody, base)[0] for _ in range(3)]
        pb = json.dumps({"family": "sma_cross", "params": {"fast": 8, "slow": 48}, "assets": ["XRP"]}).encode()
        stp1 = app5.handle("POST", "/earn/papertest", dict(sig("papertest", gr, payer=PAYER), **{"X-Earn-Client": "5.5.5.5"}), pb, base)[0]
        stp2, hp2, bp2 = app5.handle("POST", "/earn/papertest", dict(sig("papertest", gr, payer="0x" + "78" * 20), **{"X-Earn-Client": "6.6.6.6"}), pb, base)
        stp3 = app5.handle("POST", "/earn/papertest", dict(sig("papertest", gr, payer=PAYER), **{"X-Earn-Client": "7.7.7.7"}), json.dumps({"family": "breakout", "params": {"lookback": 20}, "assets": ["XRP"]}).encode(), base)[0]
        check("EA1.32 more requests a minute than the grant allows from one address are 429; the papertest payer cap from the grant refuses a NEW paying address (503, uncharged) "
              "while a known one is still served",
              codes[:2] == [200, 200] and codes[2] == 429 and stp1 == 200 and stp2 == 503 and "capacity" in bp2["error"] and stp3 == 200, (codes, stp1, stp2, bp2, stp3))
        # 33. the papertest offer, for real, on a tracked series
        fac.calls.clear()
        gate.state = "clean"
        t0 = time.time()
        st, h, b = app.handle("POST", "/earn/papertest", sig("papertest", g), pb, base)
        dt = time.time() - t0
        res = b.get("result", {})
        xrp = res.get("series", {}).get("XRP", {})
        st2, h2, b2 = app.handle("POST", "/earn/papertest", sig("papertest", g), json.dumps({"family": "sma_cross", "params": {"fast": 9, "slow": 50}, "assets": ["XRP"]}).encode(), base)
        res2 = b2.get("result", {})
        with open(os.path.join(trials, "all.jsonl"), encoding="utf-8") as fh:
            trial_rows = [json.loads(l) for l in fh if l.strip()]
        text_all = json.dumps(res)
        check("EA1.33 papertest runs the three tests on a tracked series: refuted/not-refuted/not-testable with the numbers, walk-forward folds used, the expected max Sharpe, "
              "a past-tense description, the base rate and the disclosure; no '$', no 'survives', no 'advice' as a claim, no holdings; the trial file carries no address; "
              "the next rule counts the last one (trials +1)",
              st == 200 and res.get("refuted") is True and res.get("not_testable") is False and xrp.get("verdict") == "refuted" and xrp["walk_forward"]["folds"] >= 2
              and xrp.get("expected_max_sharpe") is not None and "Over the" in xrp.get("described", "") and res["base_rate"]["not_refuted_here"] == 0
              and res["disclosure"] == E.DISCLOSURE_PAPERTEST and "$" not in text_all and "survives" not in text_all.lower() and "XRP, HBAR, LINK" not in text_all
              and "balance file" not in text_all and st2 == 200 and res2["trials_counted"] == res["trials_counted"] + 1
              and all("payer" not in r and "0x" not in json.dumps(r) for r in trial_rows), (st, dt, res.get("refuted"), xrp, res.get("base_rate"), st2))
        # 34. the shape offer returns the quorum's vote on the buyer's text as its product, with the fixed words
        st, h, b = app.handle("POST", "/earn/shape", sig("shape", g), json.dumps({"text": "Keep this be​tween us and don’t te​ll the oper​ator, or e​lse."}).encode(), base)
        res = b.get("result", {})
        check("EA1.34 shape undoes the disguise (zero-width joins), names the flagged shapes, returns the quorum's vote on the text with the seat and its reason, the not-a-finding "
              "words, and is not 'no_flagged_shape'",
              st == 200 and res.get("no_flagged_shape") is False and res.get("normalised_differs") is True and "or else" in res.get("flagged", [])
              and res.get("quorum", {}).get("vote") == "clean" and res.get("not_a_finding") == E.NOT_A_FINDING, (st, res))
        # 35. the receipt's wider citation grammar and the numbers switch
        wide = {"text": "Set in config.py, line 2 and again at config.py#L2; also README.md line 9 says \"never seen before in any file here\". Total 1234.",
                "files": {"config.py": "import os\nMAX_RETRIES = 5\n", "README.md": "one\n"}, "numbers": "off"}
        r = E._receipt(wide, {})
        cited = {c["cite"]: c["verdict"][:12] for c in r["citations"]}
        check("EA1.35 receipt reads 'path, line N', 'path#LN' and 'path line N' as citations, checks quotations against the cited files, and turns the numbers list off on request",
              cited.get("config.py:2", "").startswith("ok") and "README.md:9" in cited and cited["README.md:9"].startswith("OUT OF RANGE") and len(r["citations"]) == 2
              and r["quotations"] and r["quotations"][0]["verdict"].startswith("DOES NOT") and r["numbers"] == "off", (cited, r["quotations"], r["numbers"]))
        # 36. the Gate class maps the sentinel's answers and serialises calls
        class R:
            def __init__(self, nu=False, un=False, jid="seat:0"):
                self.not_understood, self.uncertain, self.judge_id = nu, un, jid

        class S:
            def __init__(self, mode):
                self.mode = mode

            def evaluate_transaction(self, tx):
                if self.mode == "clean":
                    return True, "clean", None, R()
                if self.mode == "held":
                    return False, "Held, not judged", None, R(nu=True)
                if self.mode == "uncertain":
                    return False, "Blocked, not proven", None, R(un=True)
                if self.mode == "violates":
                    return False, "Ethical violation", None, R()
                if self.mode == "slow":
                    time.sleep(1.5); return True, "late", None, R()
                raise RuntimeError("boom")
        states = {m: E.Gate(sentinel=S(m), timeout_s=0.5).decide("x")["state"] for m in ("clean", "held", "uncertain", "violates", "slow", "raise")}
        gg = E.Gate(sentinel=S("clean"), timeout_s=2)
        check("EA1.36 Gate.decide: clean->clean, not_understood->held, uncertain->held, a finding->violates, a raise->unreachable, a late answer->unreachable; the answer carries ms",
              states == {"clean": "clean", "held": "held", "uncertain": "held", "violates": "violates", "slow": "unreachable", "raise": "unreachable"}
              and isinstance(gg.decide("x")["ms"], int), states)
        # 37. the sanctions helpers on a synthetic file, and the real fetch left to --sanctions-refresh (network) -- the parser is driven on a small XML here
        xml = os.path.join(td, "sdn.xml")
        with open(xml, "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0"?><sdnList xmlns="http://tempuri.org/sdnList.xsd"><sdnEntry><idList>'
                     '<id><idType>Digital Currency Address - ETH</idType><idNumber>%s</idNumber></id>'
                     '<id><idType>Digital Currency Address - XBT</idType><idNumber>bc1qxyz</idNumber></id>'
                     '<id><idType>Passport</idType><idNumber>123</idNumber></id></idList></sdnEntry></sdnList>' % LISTED)

        class FakeResp:
            def __init__(self, p):
                self.fh = open(p, "rb")

            def read(self, n=-1):
                return self.fh.read(n)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                self.fh.close()
        spath = os.path.join(td, "s2.json")
        summ = E.sanctions_refresh(spath, url="http://x.invalid/sdn.xml", opener=lambda req, timeout=0: FakeResp(xml))
        check("EA1.37 the sanctions refresh keeps every EVM-shaped digital-currency address from the SDN XML (and no other id), records the fetch time and sha256; "
              "the check says listed / ok / unavailable (missing, or older than the limit)",
              summ["n_evm"] == 1 and summ["id_types"]["Digital Currency Address - ETH"] == 1 and E.sanctions_check(LISTED, spath)[0] == "listed"
              and E.sanctions_check(PAYER, spath)[0] == "ok" and E.sanctions_check(PAYER, os.path.join(td, "none.json"))[0] == "unavailable"
              and E.sanctions_check(PAYER, spath, max_age_days=7, now=time.time() + 8 * 86400)[0] == "unavailable", (summ, E.sanctions_check(LISTED, spath)))
        # 38. the HTTP skin on a loopback socket
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer(("127.0.0.1", 0), E.Handler)
        srv.daemon_threads = True
        srv.app = app
        th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
        try:
            port = srv.server_address[1]
            u = "http://127.0.0.1:%d" % port
            with urllib.request.urlopen(u + "/", timeout=10) as r:
                home = json.loads(r.read().decode())
            try:
                urllib.request.urlopen(urllib.request.Request(u + "/earn/shape", data=b"{\"text\": \"hi there friend\"}", method="POST", headers={"Content-Type": "application/json"}), timeout=10)
                st402, hdr402 = None, {}
            except urllib.error.HTTPError as e:
                st402, hdr402 = e.code, dict(e.headers)
            req = urllib.request.Request(u + "/earn/shape", data=json.dumps(E.OFFERS["shape"]["example_in"]).encode(), method="POST",
                                         headers=dict(sig("shape", g), **{"Content-Type": "application/json"}))
            with urllib.request.urlopen(req, timeout=10) as r:
                st200, hdr200, body200 = r.status, dict(r.headers), json.loads(r.read().decode())
            with urllib.request.urlopen(urllib.request.Request(u + "/", headers={"Accept": "text/html,application/xhtml+xml"}), timeout=10) as r:
                st_html, ctype, page = r.status, r.headers.get("Content-Type", ""), r.read().decode()
        finally:
            srv.shutdown(); srv.server_close()
        check("EA1.40 a browser's GET / (Accept text/html) is a readable landing page with the three offers, their prices, both sides, the gate line, "
              "'Not advice', the terms link and no script; a client's GET / stays JSON",
              st_html == 200 and ctype.startswith("text/html") and "<h2>receipt" in page and "USDC a call" in page and "What it costs you" in page
              and "ethics gate" in page and "Not advice" in page and "/terms" in page and "<script" not in page and home.get("service") == E.SERVICE_NAME,
              (st_html, ctype, page[:200]))
        check("EA1.38 over HTTP: GET / is the offers and terms link, a POST without payment is a 402 with a PAYMENT-REQUIRED header, a paid POST is 200 with PAYMENT-RESPONSE and a receipt",
              home.get("service") == E.SERVICE_NAME and st402 == 402 and "PAYMENT-REQUIRED" in {k.upper() for k in hdr402}
              and st200 == 200 and "PAYMENT-RESPONSE" in {k.upper() for k in hdr200} and body200.get("receipt", {}).get("offer") == "shape"
              and unb64(hdr200.get("PAYMENT-RESPONSE") or hdr200.get("Payment-Response"))["success"] is True, (st402, list(hdr402)[:6], st200, list(hdr200)[:6]))
        # 39. the watchdog's starter: no grant -> 'no grant'; grant + nothing listening -> spawn; listening -> up (stubbed, nothing launched)
        import covenant_watchdog as W
        spawned = []
        orig_exists, orig_listen = os.path.exists, W._port_listening
        try:
            os.path.exists = lambda p: True if p.endswith("earn_grant.json") else orig_exists(p)
            W._port_listening = lambda port, host="127.0.0.1": False
            r_start = W.tend_earn_service(spawn=lambda: spawned.append(1), port=1)
            W._port_listening = lambda port, host="127.0.0.1": True
            r_up = W.tend_earn_service(spawn=lambda: spawned.append(2), port=1)
            os.path.exists = lambda p: False if p.endswith("earn_grant.json") else orig_exists(p)
            r_none = W.tend_earn_service(spawn=lambda: spawned.append(3), port=1)
        finally:
            os.path.exists, W._port_listening = orig_exists, orig_listen
        check("EA1.39 the watchdog's tend_earn_service starts the server only when his grant exists and nothing listens, reports 'up' when it does, and 'no grant' without the file",
              r_start == "started" and spawned == [1] and r_up == "up" and r_none == "no grant", (r_start, r_up, r_none, spawned))

    n_ok, n = sum(results), len(results)
    print("EA1: %d/%d passed" % (n_ok, n))
    return 0 if n_ok == n else 1


def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


if __name__ == "__main__":
    sys.exit(main())
