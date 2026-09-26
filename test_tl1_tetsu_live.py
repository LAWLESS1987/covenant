#!/usr/bin/env python3
"""TL1 -- Tetsu's permission in Coinbase: a live order is his straight question,
the trader's own gate, and the operator's yes -- all three, per order, or
nothing. RUN with temp ledgers, a stub gate, a stub venue and a stub direct
line; never a key, never a real order.

Pins covenant_tetsu_live (2026-09-21, his words: "I over ride and give
wetsuit permission in coinbase. He's free to ask me anything."):

  TL1a  no grant: nothing is requested and it is recorded as refused; the
        tree's grant file carries his words.
  TL1b  request: a sell of a floor asset refused; a size over max_order_usd
        clipped; the trader's gate is run and its reasons recorded; he is
        asked a straight question naming the request id, the size, the
        reason and -- when blocked -- the blocks; a paused switch refuses.
  TL1c  his answer: none until the question was shown; yes/no read from the
        first tailnet line after; a line naming the id wins over an earlier
        unrelated one.
  TL1d  settle: waiting without an answer; his no is recorded and nothing
        placed; his yes with the gate blocking NOW is recorded as not placed;
        his yes with a clear gate places through the venue's own call, dry
        run by default, live only when asked; a venue that raises is
        recorded; a settled request is never settled twice.
  TL1e  the module never imports the venue or the guards at module level
        (only inside the calls), and the real gate on this tree blocks today
        with its reasons named (measured).
"""
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="tl1_")
os.environ["COVENANT_TETSU_LIVE"] = os.path.join(TMP, "live.jsonl")
os.environ["COVENANT_TETSU_COINBASE_GRANT"] = os.path.join(TMP, "grant.json")
os.environ["COVENANT_ASK_LOG"] = os.path.join(TMP, "ask.jsonl")
os.environ["COVENANT_CONTACT_OUTBOX"] = os.path.join(TMP, "contact.jsonl")
os.environ["COVENANT_CONTACT_STATE"] = os.path.join(TMP, "contact_state.json")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_contact as CT     # noqa: E402
import covenant_tetsu_live as TL  # noqa: E402

FAILURES = []
PASSED = [0]
NOW = 1_800_000_000.0


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def write_grant(on=True):
    with open(os.environ["COVENANT_TETSU_COINBASE_GRANT"], "w", encoding="utf-8") as fh:
        json.dump({"granted": on, "words": ["his words"]}, fh)


def chat(text, at):
    # the real ask log writes LOCAL time with its offset, and the direct line reads it back with mktime
    t = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(at))
    with open(os.environ["COVENANT_ASK_LOG"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": t, "kind": "agent", "from": "100.72.0.10", "text": text}) + "\n")


class Venue:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def meta(self, sym):
        return {"product_id": sym + "-USD"}

    def best_bid_ask(self, pid):
        return 99.0, 101.0

    def place(self, sym, side, qty, live=False, **kw):
        self.calls.append({"sym": sym, "side": side, "qty": qty, "live": live})
        if self.fail:
            raise RuntimeError("venue refused")
        return {"order_id": "stub"}


def main():
    quiet = lambda *a, **k: None       # noqa: E731
    clean = lambda t: (True, "clean")  # noqa: E731
    asked = []

    def ask_fn(q, why, actor, judge=None):
        asked.append(q)
        return CT.say(q, why, actor, kind="question"), "asked"

    print("TL1a -- the grant")
    r = TL.request("buy", "SOL", 10, "trend", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
    check("TL1a no grant: refused, recorded, nothing asked", r["state"].startswith("refused: no grant") and asked == [] and TL._rows()[-1]["kind"] == "request", r["state"])
    g = json.load(open(os.path.join(HERE, "ops", "tetsu_coinbase_grant.json"), encoding="utf-8"))
    check("TL1a the tree's grant file carries his words and what still governs every order",
          g["granted"] is True and any("over ride" in w for w in g["words"]) and any("Rule 5" in x for x in g["what_still_governs_every_live_order"]))
    write_grant()

    print("TL1b -- request")
    r = TL.request("sell", "XRP", 10, "x", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
    check("TL1b a sell of a floor asset is refused before the gate and nothing asked", "hold-only floor" in r["state"] and asked == [], r["state"])
    r = TL.request("buy", "SOL", 500, "trend on the daily bar", consequence="worst paper drawdown 30%", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
    cap = TL.max_order_usd()
    check("TL1b a size over max_order_usd is clipped to it and recorded as clipped; the gate clear; he is asked with the id, the size, the reason and the consequence",
          r["usd"] == cap and r.get("clipped_from") == 500 and r["blocks"] == [] and r["state"] == "asked" and r["question_id"]
          and asked and ("request %s" % r["id"]) in asked[-1] and ("BUY $%.2f of SOL" % cap) in asked[-1] and "trend on the daily bar" in asked[-1]
          and "worst paper drawdown 30%" in asked[-1] and "rails are clear" in asked[-1] and asked[-1].endswith("?"), (r, asked[-1:]))
    seen_orders = []
    blocked = lambda o: (seen_orders.append(o) or ["Rule 5: 4 sealed signals on record, need 30", "no approved daily plan"])   # noqa: E731
    r2 = TL.request("buy", "BTC", 5, "b", ask_fn=ask_fn, preconditions=blocked, say=quiet)
    check("TL1b the trader's gate is run on the bounded order and its reasons are recorded; he is still asked, with the blocks named and 'your call'",
          seen_orders == [{"side": "buy", "usd": 5.0, "sym": "BTC"}] and r2["blocks"][0].startswith("Rule 5") and r2["state"] == "asked (blocked today)"
          and "Your own rails block it today: Rule 5" in asked[-1] and "your call, not mine" in asked[-1], (r2["blocks"], asked[-1:]))
    check("TL1b a question the line refuses is recorded as not asked", "not asked" in TL.request("buy", "ETH", 5, "e", ask_fn=lambda *a, **k: (None, "not straight"), preconditions=lambda o: [], say=quiet)["state"])
    real_paused = TL.paused
    try:
        TL.paused = lambda: (True, "tetsu-live: paused by him")
        rp = TL.request("buy", "SOL", 5, "p", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
        check("TL1b a paused switch refuses a request", rp["state"].startswith("refused: paused"), rp["state"])
    finally:
        TL.paused = real_paused
    check("TL1b junk side or symbol refused", "buy or sell" in TL.request("hold", "SOL", 5, "j", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)["state"])

    print("TL1c -- his answer")
    check("TL1c no answer until the question was shown to him", TL.his_answer(r) == (None, ""))
    CT.mark_seen([r["question_id"]], now=NOW)
    chat("what is the weather", NOW + 10)
    check("TL1c an unrelated first line is neither yes nor no (None), and is returned", TL.his_answer(r)[0] is None and "weather" in TL.his_answer(r)[1])
    chat("yes %s go ahead" % r["id"], NOW + 20)
    check("TL1c a later line naming the request id with yes wins over the earlier unrelated one", TL.his_answer(r) == ("yes", "yes %s go ahead" % r["id"]))
    CT.mark_seen([r2["question_id"]], now=NOW + 100)
    chat("no, not that one", NOW + 110)
    check("TL1c a plain no is read as no", TL.his_answer(r2)[0] == "no")

    print("TL1d -- settle")
    v = Venue()
    outs = TL.settle(dry_run=True, venue=v, preconditions=lambda o: [], say=quiet)
    by = {o["request"]: o["outcome"] for o in outs}
    rows = TL._rows()
    check("TL1d his yes with a clear gate: a DRY RUN placement through the venue's own call (live=False), recorded; his no recorded and not placed",
          by[r["id"]].startswith("dry run: would place buy") and len(v.calls) == 1 and v.calls[0]["live"] is False and v.calls[0]["sym"] == "SOL"
          and abs(v.calls[0]["qty"] - cap / 101.0) < 1e-9 and by[r2["id"]] == "he said no"
          and any(x["kind"] == "placed" and x["dry_run"] for x in rows) and any(x["kind"] == "no" and x["request"] == r2["id"] for x in rows), (by, v.calls))
    outs2 = TL.settle(dry_run=True, venue=v, preconditions=lambda o: [], say=quiet)
    check("TL1d a settled request is never settled twice", outs2 == [] and len(v.calls) == 1, outs2)
    r3 = TL.request("buy", "ETH", 5, "e3", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
    CT.mark_seen([r3["question_id"]], now=NOW + 200)
    chat("yes", NOW + 210)
    v2 = Venue()
    outs3 = TL.settle(dry_run=False, venue=v2, preconditions=lambda o: ["Rule 5: 4 sealed signals on record, need 30"], say=quiet)
    check("TL1d his yes but the gate blocking NOW: not placed, the reason recorded, the venue never called",
          outs3[0]["outcome"].startswith("yes, but blocked: Rule 5") and v2.calls == [] and TL._rows()[-1]["kind"] == "not_placed" and "his yes is on record" in TL._rows()[-1]["why"], outs3)
    outs3b = TL.settle(dry_run=False, venue=v2, preconditions=lambda o: [], say=quiet)
    check("TL1d a request blocked at settlement is closed, not retried into a live order later", outs3b == [] and v2.calls == [], outs3b)
    r4 = TL.request("buy", "ETH", 5, "e4", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
    CT.mark_seen([r4["question_id"]], now=NOW + 300)
    chat("go ahead", NOW + 310)
    v3 = Venue()
    outs4 = TL.settle(dry_run=False, venue=v3, preconditions=lambda o: [], say=quiet)
    check("TL1d LIVE only when asked: his yes, a clear gate, dry_run=False -> the venue is called with live=True and PLACED is recorded",
          outs4[0]["outcome"].startswith("PLACED buy") and v3.calls and v3.calls[0]["live"] is True and TL._rows()[-1]["kind"] == "placed" and TL._rows()[-1]["dry_run"] is False, outs4)
    r5 = TL.request("buy", "ETH", 5, "e5", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
    CT.mark_seen([r5["question_id"]], now=NOW + 400)
    chat("ok", NOW + 410)
    outs5 = TL.settle(dry_run=False, venue=Venue(fail=True), preconditions=lambda o: [], say=quiet)
    check("TL1d a venue that refuses is recorded as not placed, never raised", outs5[0]["outcome"].startswith("the venue refused") and TL._rows()[-1]["kind"] == "not_placed")
    r6 = TL.request("buy", "ETH", 5, "e6", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet)
    outs6 = TL.settle(dry_run=False, venue=Venue(), preconditions=lambda o: [], say=quiet)
    check("TL1d without his answer a request waits", outs6 == [{"request": r6["id"], "outcome": "waiting for his answer"}], outs6)
    write_grant(False)
    check("TL1d the grant revoked: nothing settles", TL.settle(dry_run=False, venue=Venue(), preconditions=lambda o: [], say=quiet) == [])
    write_grant(True)
    st = TL.status()
    check("TL1d status counts: requests, asked, placed live 1, placed dry 1, his no 1, not placed 2",
          st["placed_live"] == 1 and st["placed_dry"] == 1 and st["his_no"] == 1 and st["not_placed"] == 2 and st["requests"] >= 6, st)

    print("TL1e -- what the module does not do, and the real gate today")
    src = open(TL.__file__, encoding="utf-8").read()
    top = [l for l in src.splitlines() if l.startswith("import ") or l.startswith("from ")]
    check("TL1e no venue, guards or trader import at module level (only inside the calls)", not any(m in l for l in top for m in ("venues", "guards", "covenant_trader", "signal_ledger")), top)
    real = TL.gate_reasons({"side": "buy", "usd": 5.0, "sym": "BTC"})
    check("TL1e the real trader gate on this tree blocks a live order today and names why (measured, not assumed)", real and any("Rule 5" in x or "daily plan" in x or "armed" in x for x in real), real)

    # ---- TL1f (his words the same evening: "It can be a yes to a trading strategy also")
    print("TL1f -- a yes to a strategy")
    sr = TL.request_strategy("sma_cross 8/48", "it cleared the three tests on paper", consequence="worst paper drawdown 30%", ask_fn=ask_fn, say=quiet)
    check("TL1f a strategy request asks ONE straight question naming the rule, the rails, the consequence and 'until you say stop'",
          sr["scope"] == "strategy" and sr["state"].startswith("asked") and "trade the paper rule sma_cross 8/48 live" in asked[-1]
          and ("at most $%.2f an order" % cap) in asked[-1] and "worst paper drawdown 30%" in asked[-1] and "until you say 'stop sma_cross 8/48'" in asked[-1], (sr["state"], asked[-1:]))
    check("TL1f the same rule is not asked twice", TL.request_strategy("sma_cross 8/48", "again", ask_fn=ask_fn, say=quiet)["state"] == "already asked for this rule")
    check("TL1f before his answer no strategy is approved, and a covered order is still asked per order",
          TL.approved_strategies() == {} and TL.request("buy", "SOL", 5, "s", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet, strategy="sma_cross 8/48")["state"] == "asked")
    n_asked = len(asked)
    CT.mark_seen([sr["question_id"]], now=NOW + 500)
    chat("yes to the strategy", NOW + 510)
    outs = TL.settle(dry_run=True, venue=Venue(), preconditions=lambda o: [], say=quiet)
    check("TL1f his yes to the rule is recorded as strategy_yes and the rule is approved", TL.approved_strategies() == {"sma_cross 8/48": sr["id"]}
          and any(x["kind"] == "strategy_yes" and x["request"] == sr["id"] for x in TL._rows()) and any("he said yes to strategy" in o["outcome"] for o in outs), (TL.approved_strategies(), outs))
    cr = TL.request("buy", "SOL", 5, "signal +1", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet, strategy="sma_cross 8/48")
    check("TL1f an order under the approved rule is COVERED: recorded, not asked, no question id", cr["covered"] == sr["id"] and cr["state"].startswith("covered by his yes") and cr["question_id"] is None and len(asked) == n_asked, cr["state"])
    vc = Venue()
    outs = TL.settle(dry_run=True, venue=vc, preconditions=lambda o: [], say=quiet)
    check("TL1f a covered order settles under the strategy yes (dry run) through the venue's call, gate re-run", any(o["request"] == cr["id"] and o["outcome"].startswith("dry run: would place buy") for o in outs) and len(vc.calls) == 1, outs)
    cr2 = TL.request("buy", "SOL", 5, "signal +1", ask_fn=ask_fn, preconditions=lambda o: ["Rule 5: 4 of 30"], say=quiet, strategy="sma_cross 8/48")
    outs = TL.settle(dry_run=True, venue=vc, preconditions=lambda o: ["Rule 5: 4 of 30"], say=quiet)
    check("TL1f a covered order still passes the trader's gate at settlement: blocked -> not placed", any(o["request"] == cr2["id"] and "blocked: Rule 5" in o["outcome"] for o in outs) and len(vc.calls) == 1, outs)
    # signals: +1 raises a covered buy; -1 with nothing bought raises nothing; -1 after a live buy raises a sell of what was bought
    import strategy_validate as SV
    files = dict(list(SV.series_files().items())[:1])
    sym = list(files)[0]
    up = lambda view, pos: 1     # noqa: E731
    down = lambda view, pos: -1  # noqa: E731
    sig = TL.signals(rules=[("sma_cross 8/48", up, [sym])], files=files, preconditions=lambda o: [], say=quiet)
    check("TL1f a +1 signal on the last bar raises a COVERED buy of max_order_usd", sig and sig[0]["signal"] == 1 and sig[0]["request"] and TL._rows()[-1]["covered"] == sr["id"] and TL._rows()[-1]["usd"] == cap, sig)
    sig2 = TL.signals(rules=[("sma_cross 8/48", down, [sym])], files=files, preconditions=lambda o: [], say=quiet)
    check("TL1f a -1 signal with nothing bought under the rule raises nothing", sig2 and sig2[0]["signal"] == -1 and sig2[0]["request"] is None and "nothing bought" in sig2[0]["note"], sig2)
    vl = Venue()
    TL.settle(dry_run=False, venue=vl, preconditions=lambda o: [], say=quiet)      # the covered buy goes LIVE (stub venue)
    check("TL1f the covered buy placed live is recorded and counted as bought under the rule", TL.bought_under("sma_cross 8/48", sym) > 0 and vl.calls and vl.calls[-1]["live"] is True, TL.bought_under("sma_cross 8/48", sym))
    sig3 = TL.signals(rules=[("sma_cross 8/48", down, [sym])], files=files, preconditions=lambda o: [], say=quiet)
    check("TL1f a -1 signal after a live buy raises a covered SELL of what was bought", sig3 and sig3[0]["request"] and TL._rows()[-1]["side"] == "sell" and TL._rows()[-1]["covered"] == sr["id"], sig3)
    check("TL1f a rule without his yes reads no signal", TL.signals(rules=[("other rule", up, [sym])], files=files, preconditions=lambda o: [], say=quiet) == [])
    chat("stop sma_cross 8/48", NOW + 600)
    check("TL1f 'stop <rule>' on the line revokes the strategy yes", TL.approved_strategies() == {} and TL.stopped(sr))
    cr3 = TL.request("buy", "SOL", 5, "signal +1", ask_fn=ask_fn, preconditions=lambda o: [], say=quiet, strategy="sma_cross 8/48")
    check("TL1f after the stop an order under the rule is asked per order again", cr3["state"] == "asked" and cr3["covered"] is None and len(asked) == n_asked + 1)
    outs = TL.settle(dry_run=False, venue=Venue(), preconditions=lambda o: [], say=quiet)
    check("TL1f the pending covered sell raised before the stop is NOT placed after it", any("stopped or missing" in o["outcome"] for o in outs), outs)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("TL1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("TL1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
