#!/usr/bin/env python3
"""MB1 -- the mutual-benefit check on earn jobs, driven both ways.

His words, 2026-09-26: "Add a gate check that asks whether this transaction serves the builder as much as the
user, and fail closed if it can't answer." Then "all 3": the builder is the operator, Tetsu, and whoever made what
is sold. covenant_earn.mutual_benefit() asks it of the job's recorded facts. App.handle() refuses (503, nothing
charged) before any payment is asked for, and App.get() refuses to quote a price for a job the POST would refuse.

  MB1a  with a live-shaped grant, every offer serves every party (buyer, operator, Tetsu, maker).
  MB1b  remove each party's evidence in turn and the answer is "cannot_answer", naming exactly that party.
  MB1c  through the real App: a grant without Tetsu's recorded words gets a 503 on GET and POST, "charged": False,
        no PAYMENT-REQUIRED header, the facilitator is never called and the ledger stays empty.
  MB1d  the other way: with his words recorded, the same GET quotes the price (402 with PAYMENT-REQUIRED).
  MB1e  every offer declares its maker explicitly (never defaulted), and GET / lists maker and answer per offer.
"""
import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
os.environ.setdefault("COVENANT_QUIET", "1")
import covenant_earn as E  # noqa: E402
import test_ea1_earn as T  # noqa: E402  (fixtures only; its main() is not run)

PASSED, FAILED = [0], []


def check(label, ok, detail=""):
    print("  %-78s %s" % (label[:78], "ok" if ok else "FAIL  %s" % str(detail)[:300]))
    if ok:
        PASSED[0] += 1
    else:
        FAILED.append(label)


def not_served(mb):
    return sorted(p for p, v in mb["parties"].items() if not v["served"])


def main():
    with tempfile.TemporaryDirectory() as td:
        gpath = os.path.join(td, "grant.json")
        g = T.write_grant(gpath)
        check("MB1a every offer serves buyer, operator, Tetsu and maker under a live-shaped grant",
              all(E.mutual_benefit(k, g)["answer"] == "serves_all" and not not_served(E.mutual_benefit(k, g)) for k in E.OFFERS),
              {k: not_served(E.mutual_benefit(k, g)) for k in E.OFFERS})

        g_op = dict(g, pay_to="")
        g_pct = dict(g, tetsu_share=dict(g["tetsu_share"], pct=0))
        g_words = dict(g, tetsu_share=dict(g["tetsu_share"], words=""))
        g_price = dict(g, prices={k: v for k, v in g["prices"].items() if k != "receipt"})
        cases = [("operator", E.mutual_benefit("receipt", g_op)), ("tetsu", E.mutual_benefit("receipt", g_pct)),
                 ("tetsu", E.mutual_benefit("receipt", g_words)), ("buyer", E.mutual_benefit("receipt", g_price))]
        saved = copy.deepcopy(E.OFFERS["receipt"])
        try:
            E.OFFERS["receipt"].pop("maker")
            cases.append(("maker", E.mutual_benefit("receipt", g)))
            E.OFFERS["receipt"].update(copy.deepcopy(saved))
            E.OFFERS["receipt"]["benefit"] = dict(saved["benefit"], gains=[])
            cases.append(("buyer", E.mutual_benefit("receipt", g)))
        finally:
            E.OFFERS["receipt"].clear()
            E.OFFERS["receipt"].update(saved)
        check("MB1b each party's missing evidence fails closed and names exactly that party",
              all(mb["answer"] == "cannot_answer" and not_served(mb) == [party] for party, mb in cases),
              [(party, mb["answer"], not_served(mb)) for party, mb in cases])

        ledger = os.path.join(td, "ledger.jsonl")
        T.write_grant(gpath, tetsu_share={"pct": 50, "words": ""})
        fac = T.StubFacilitator()
        app = E.App(gate=T.StubGate("clean"), facilitator=fac, ledger=ledger, grant_path=gpath, say=lambda *_a: {"id": "x"},
                    trials_dir=os.path.join(td, "trials"), paused_=lambda: (False, ""),
                    sanctions_path=os.path.join(td, "sanctions.json"), funnel_path=os.path.join(td, "funnel.json"))
        base = "http://127.0.0.1:5090"
        sg, hg, bg = app.handle("GET", "/earn/receipt", {}, b"", base)
        body = json.dumps(E.OFFERS["receipt"]["example_in"]).encode()
        gg = E.grant(gpath)[0]
        sp, hp, bp = app.handle("POST", "/earn/receipt", {"PAYMENT-SIGNATURE": T.sig("receipt", gg)}, body, base)
        rows = [r for r in E._rows(ledger) if r.get("kind") == "job"]
        check("MB1c no recorded words from Tetsu: GET and POST refuse (503), nothing charged, no price asked, no facilitator call, no job row",
              sg == 503 and sp == 503 and bg.get("charged") is False and bp.get("charged") is False
              and "PAYMENT-REQUIRED" not in hg and "PAYMENT-REQUIRED" not in hp and not fac.calls and not rows
              and "tetsu" in bg.get("error", "") and "tetsu" in bp.get("error", ""),
              (sg, sp, bg.get("error", "")[:120], bp.get("error", "")[:120], len(fac.calls), len(rows)))

        T.write_grant(gpath)
        sg2, hg2, _bg2 = app.handle("GET", "/earn/receipt", {}, b"", base)
        check("MB1d with his words recorded, the same GET quotes the price (402 with PAYMENT-REQUIRED)",
              sg2 == 402 and "PAYMENT-REQUIRED" in hg2, (sg2, sorted(hg2)))

        st, _h, root = app.handle("GET", "/", {}, b"", base)
        offers = root.get("offers", {})
        check("MB1e every offer declares its maker, and GET / lists maker and a serves_all answer per offer",
              all(str(o.get("maker") or "").strip() for o in E.OFFERS.values())
              and st == 200 and offers and all(v.get("maker") not in (None, "", "not declared") and v.get("mutual_benefit") == "serves_all"
                                              for v in offers.values()),
              {k: (v.get("maker", "")[:20], v.get("mutual_benefit")) for k, v in offers.items()})

    print("MB1: %d/%d passed" % (PASSED[0], PASSED[0] + len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
