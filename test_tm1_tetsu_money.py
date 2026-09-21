#!/usr/bin/env python3
"""TM1 -- Tetsu and the money: reads the account from the local balance file
with the floor marked, builds strategy on PAPER against the three tests,
prices the consequence in plain words, and is not "comfortable" until the
measured bar is met; nothing here can place an order.

RUN with a temp balance file, a temp ledger, a stub model and a stub gate,
and one real price series from realdata/deep (tracked, so the runner has it):

  TM1a  holdings: the floor assets are marked and never counted above the
        floor; amounts without dollars say so; a missing file is UNDETERMINED.
  TM1b  build: the five families, bounds both ways, fast below slow, an
        unknown family refused.
  TM1c  evaluate on a real series: the three tests are measured and named,
        every trial ever made is counted against the deflated Sharpe, and the
        consequence line carries the worst drawdown in dollars at what he
        holds above the floor (the reserve applied), the worst fold, the time
        in market, the floor, and "his go".
  TM1d  study: a proposal is bounded, evaluated, judged with its consequence,
        recorded; a repeat is refused; a bad one is recorded as refused; a
        held reason is recorded and never a survivor; he is told only when a
        rule survives (stubbed evaluation), on the direct line by actor tetsu.
  TM1e  status: not comfortable with the reasons; three distinct survivors
        AND Rule 5 clearing make it comfortable, and live is still his go;
        the module imports no venue client and no trader (text, beside the run).
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="tm1_")
os.environ["COVENANT_COINBASE_BALANCE"] = os.path.join(TMP, "balance.json")
os.environ["COVENANT_TETSU_STRATEGY"] = os.path.join(TMP, "strategy.jsonl")
os.environ["COVENANT_CONTACT_OUTBOX"] = os.path.join(TMP, "contact.jsonl")
os.environ["COVENANT_CONTACT_STATE"] = os.path.join(TMP, "contact_state.json")
# A182: a surviving paper rule may raise a live request under his grant; this suite must never
# touch the real grant, the real live ledger or the real line, so both are redirected to
# temp paths (the grant to a path with no file: no grant, no request).
os.environ["COVENANT_TETSU_COINBASE_GRANT"] = os.path.join(TMP, "no_grant.json")
os.environ["COVENANT_TETSU_LIVE"] = os.path.join(TMP, "live.jsonl")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_tetsu_money as TM     # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def write_balance(balances, generated="2026-09-21T10:00:00Z"):
    with open(os.environ["COVENANT_COINBASE_BALANCE"], "w", encoding="utf-8") as fh:
        json.dump({"venue": "coinbase", "scheme": "cdp", "generated": generated, "balances": balances}, fh)


def ask_with(d):
    def ask(msgs, max_tokens=0):
        return ("here: " + json.dumps(d)) if isinstance(d, dict) else str(d), {"model": "stub"}
    return ask


def main():
    quiet = lambda *a, **k: None       # noqa: E731
    clean = lambda t: (True, "clean")  # noqa: E731

    print("TM1a -- holdings")
    h = TM.holdings()
    check("TM1a no balance file: not read, UNDETERMINED said, the key named as outside this folder", not h["read"] and "UNDETERMINED" in h["why"] and "key stays outside" in h["why"], h["why"])
    write_balance({"XRP": {"amount": 1000, "usd": 2500.0}, "HBAR": {"amount": 5000, "usd": 900.0}, "BTC": {"amount": 0.01, "usd": 600.0}, "SOL": {"amount": 2, "usd": 300.0}, "USD": {"amount": 0}})
    h = TM.holdings(now=1_800_000_000.0)
    floor = {a["asset"]: a["floor"] for a in h["assets"]}
    check("TM1a the floor assets are marked and never counted above the floor; the zero one is dropped; the age is measured",
          floor == {"XRP": True, "HBAR": True, "BTC": False, "SOL": False} and h["above_floor_usd"] == 900.0 and h["age_h"] is not None and h["reserve"] == 0.5, (floor, h["above_floor_usd"]))
    write_balance({"XRP": 1000, "BTC": 0.01})
    h2 = TM.holdings()
    check("TM1a amounts without dollars: read, the floor still marked, the dollar line unknown and said", h2["read"] and h2["above_floor_usd"] is None and "no dollar values" in h2["why"] and [a["floor"] for a in h2["assets"]] == [True, False], h2)
    write_balance({"XRP": {"amount": 1000, "usd": 2500.0}, "BTC": {"amount": 0.01, "usd": 600.0}, "SOL": {"amount": 2, "usd": 300.0}})
    hold = TM.holdings()

    print("TM1b -- build")
    ok_b = all(TM.build(x)[0] for x in [{"family": "sma_cross", "params": {"fast": 8, "slow": 48}}, {"family": "sma_longonly", "params": {"fast": 5, "slow": 30}},
                                        {"family": "mean_revert", "params": {"lookback": 24, "z_enter": 1.5}}, {"family": "breakout", "params": {"lookback": 24}},
                                        {"family": "filt_revert", "params": {"lookback": 16, "z_enter": 1.0, "trend": 72}}])
    check("TM1b the five families build inside bounds", ok_b)
    bad = 0
    for x in [{"family": "magic", "params": {}}, {"family": "sma_cross", "params": {"fast": 48, "slow": 8}}, {"family": "breakout", "params": {"lookback": 5000}},
              {"family": "mean_revert", "params": {"lookback": 24}}, {"family": "sma_cross", "params": {"fast": "x", "slow": 48}}]:
        try:
            TM.build(x)
        except ValueError:
            bad += 1
    check("TM1b an unknown family, fast above slow, a look-back out of bounds, a missing param and a non-number are all refused", bad == 5, bad)

    print("TM1c -- evaluate on one real series")
    import strategy_validate as SV
    files = dict(list(SV.series_files().items())[:1])
    check("TM1c a real daily series is on the tree for the test (realdata/deep is tracked)", bool(files), files)
    res = TM.evaluate({"family": "sma_cross", "params": {"fast": 8, "slow": 48}}, files=files, holdings_=hold)
    a = list(res["assets"].values())[0] if res["assets"] else {}
    check("TM1c the three tests are measured and named on the asset: dsr, pbo, walk-forward with folds and p, mdd, trades, time in market",
          all(k in a for k in ("dsr", "pbo", "wf", "mdd", "trades", "in_market", "survives")) and a["wf"] and "p" in a["wf"] and a["bars"] > 300, a)
    import strategy_lab as L
    check("TM1c every trial ever made is counted against the deflated Sharpe: the lab's grid plus the hypotheses on record plus this one",
          res["trials_counted"] == len(L.build_grid()) + 0 + 1, res["trials_counted"])
    c = res["consequence"]
    check("TM1c the consequence line: the worst drawdown in dollars at what he holds above the floor with the reserve applied, the worst fold, the time in market, the floor, his go",
          ("%.1f%%" % (a["mdd"] * 100)) in c and ("$%.0f of the $900" % (a["mdd"] * 900)) in c and ("about $%.0f of what could ever be at risk" % (a["mdd"] * 900 * 0.5)) in c
          and "worst walk-forward fold" in c and "in the market" in c and "XRP, HBAR, LINK" in c and "his go, per order" in c, c)
    res_nd = TM.evaluate({"family": "sma_cross", "params": {"fast": 8, "slow": 48}}, files=files, holdings_=h2)
    check("TM1c with no dollar values the consequence says the amount is unknown rather than inventing one", "unknown dollar amount" in res_nd["consequence"], res_nd["consequence"][:160])
    check("TM1c no series: UNDETERMINED, not a survivor", TM.evaluate({"family": "breakout", "params": {"lookback": 24}}, files={}, holdings_=hold)["why"].endswith("(UNDETERMINED)"))

    print("TM1d -- study")
    said = []
    hyp = {"family": "sma_cross", "params": {"fast": 8, "slow": 48}, "assets": list(files), "why": "trend following on a daily bar; the cost is a deep drawdown in a long chop"}
    out = TM.study(ask_with(hyp), judge=clean, say=said.append, files=files, hold=hold)
    rows = [r for r in TM._rows() if r["kind"] == "hypothesis"]
    check("TM1d a proposal is bounded, evaluated, judged with its consequence and recorded on paper with the gate's word",
          out["proposed"] and out["recorded"] and len(rows) == 1 and rows[0]["name"] == "sma_cross 8/48" and rows[0]["paper"] is True and rows[0]["gate"]["ok"] is True
          and "worst drawdown" in rows[0]["consequence"] and rows[0]["result"]["trials_counted"] == len(L.build_grid()) + 1, (out, rows[-1:]))
    seen = []
    TM.study(ask_with({"family": "breakout", "params": {"lookback": 24}, "assets": list(files), "why": "w"}), judge=lambda t: (seen.append(t) or (True, "")), say=said.append, files=files, hold=hold)
    check("TM1d the gate sees the reason AND the consequence line together", seen and seen[-1].startswith("w\nOn paper this rule") , seen[-1:][0][:80] if seen else "")
    check("TM1d the second hypothesis counts the first against it (trials +1)", [r for r in TM._rows() if r["kind"] == "hypothesis"][-1]["result"]["trials_counted"] == len(L.build_grid()) + 2)
    out_r = TM.study(ask_with(hyp), judge=clean, say=said.append, files=files, hold=hold)
    check("TM1d a repeat is refused, nothing recorded", "already on the record" in out_r["why"] and len([r for r in TM._rows() if r["kind"] == "hypothesis"]) == 2, out_r)
    out_b = TM.study(ask_with({"family": "sma_cross", "params": {"fast": 100, "slow": 5}, "why": "x"}), judge=clean, say=said.append, files=files, hold=hold)
    check("TM1d a hypothesis outside bounds is refused and recorded as refused", "refused" in out_b["why"] and TM._rows()[-1]["kind"] == "refused", out_b)
    out_n = TM.study(ask_with("no json here"), judge=clean, say=said.append, files=files, hold=hold)
    check("TM1d no JSON changes nothing", not out_n["proposed"] and "no JSON" in out_n["why"])
    surv = lambda h, **k: {"name": "stub", "survives": True, "assets": {"X": {"mdd": 0.1, "wf": {"worst_fold": -0.05}, "in_market": 0.5, "survives": True, "return": 0.12}}, "trials_counted": 1, "why": "survives on X", "consequence": "paper line"}   # noqa: E731
    out_h = TM.study(ask_with({"family": "mean_revert", "params": {"lookback": 24, "z_enter": 1.5}, "why": "y"}), judge=lambda t: (False, "HOLD"), say=said.append, files=files, hold=hold, evaluate_=surv)
    last = [r for r in TM._rows() if r["kind"] == "hypothesis"][-1]
    check("TM1d a reason the gate holds is recorded and is NEVER a survivor even when the tests pass", not out_h["survives"] and last["survives"] is False and last["gate"]["ok"] is False and "held by the gate" in out_h["why"], (out_h, last["gate"]))
    import covenant_contact as CT
    n0 = len(CT._rows())
    out_s = TM.study(ask_with({"family": "filt_revert", "params": {"lookback": 16, "z_enter": 1.0, "trend": 72}, "why": "z"}), judge=clean, say=said.append, files=files, hold=hold, evaluate_=surv)
    rows_c = CT._rows()
    check("TM1d a rule that survives (stubbed) is told on the direct line by actor tetsu with 'Nothing is live'",
          out_s["survives"] and len(rows_c) == n0 + 1 and rows_c[-1]["actor"] == "tetsu" and "Nothing is live" in rows_c[-1]["text"] and "cleared all three tests" in rows_c[-1]["text"], rows_c[-1:])
    check("TM1d a rule that does not survive tells him nothing", len(CT._rows()) == n0 + 1)

    print("TM1e -- comfort, and what this module cannot do")
    st = TM.status(rule5_={"clears": False, "why": "4 settled signals, need 30"})
    check("TM1e not comfortable: one survivor of three, Rule 5 not clearing, both named; live is never from here",
          st["comfortable"] is False and len(st["survivors"]) == 1 and len(st["why"]) == 2 and "never from this module" in st["live"], st)
    # A187 ("comfortable generating a profit"): a survivor counts only with a positive paper return on a surviving asset
    TM._append({"kind": "hypothesis", "name": "stub-loss", "survives": True, "paper": True, "result": {"assets": {"X": {"survives": True, "return": -0.02}}}})
    st1b = TM.status(rule5_={"clears": True, "why": ""})
    check("TM1e a survivor with a paper LOSS does not count toward comfort", st1b["comfortable"] is False and "stub-loss" in st1b["survivors"] and "stub-loss" not in st1b["profitable"], st1b)
    for n in ("a", "b"):
        TM._append({"kind": "hypothesis", "name": "stub-" + n, "survives": True, "paper": True, "result": {"assets": {"X": {"survives": True, "return": 0.05}}}})
    st2 = TM.status(rule5_={"clears": False, "why": "4 settled signals, need 30"})
    check("TM1e three distinct profitable survivors but Rule 5 not clearing: still not comfortable, one reason left",
          st2["comfortable"] is False and len(st2["profitable"]) == 3 and st2["why"] == ["Rule 5 does not clear: 4 settled signals, need 30"], (st2["profitable"], st2["why"]))
    st3 = TM.status(rule5_={"clears": True, "why": ""})
    check("TM1e three survivors AND Rule 5 clearing: comfortable, and going live is still his go per order", st3["comfortable"] is True and "his go" in st3["why"][0] and "each order is his go" in st3["live"], st3)
    check("TM1e the real Rule 5 summary is read (measured, not assumed): it does not clear today and says why", TM.rule5()["clears"] is False and TM.rule5()["why"])
    src = open(TM.__file__, encoding="utf-8").read()
    check("TM1e the module imports no venue client, no trader and no order path (text check beside the run above)",
          not any(("import " + m) in src or ("from " + m) in src for m in ("venues", "coinbase_balance", "covenant_trader", "trader", "rebalance_strategy", "urllib", "requests"))
          and "orders_create" not in src and "place_order" not in src)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("TM1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("TM1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
