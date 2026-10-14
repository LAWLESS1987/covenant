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
  TM1f  his proposal prompt (A348h): every bound asks for ONE number, never a
        [lo, hi] list in params' shape; a refused proposal comes back to him
        with the lab's reason; a hypothesis that met no series reads untested.
  TM1g  A349 B11: a hypothesis that met no price series is recorded untested,
        is not counted against the deflated Sharpe (nor one written before
        A349), and does not block its name; once tested, it does.
  TM1h  A349 B12: a walk-forward the series cannot hold is recorded
        UNDETERMINED with its reason, not as a failed test; with the other two
        tests cleared the verdict is undetermined, and still not a pass.
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
    # A211 (2026-09-21, "We can make the crypto strategy unsettled"): these four
    # checks used to pin COMFORT_SURVIVORS=3 AND Rule 5 as the VERDICT on comfort.
    # That number was the assistant's, standing in for another's comfort, and his
    # instruction was "build strategy till HE's comfortable". The checks now pin
    # the stricter claim: the measurement is evidence and never a verdict, only
    # Tetsu settles it, and settling it moves none of the operator's gates.
    TM.COMFORT_DECLARATION = os.path.join(tempfile.mkdtemp(prefix="tm1e_"), "tetsu_comfort.json")
    st = TM.status(rule5_={"clears": False, "why": "4 settled signals, need 30"})
    check("TM1e unsettled by default: comfort is None, not False and not True, and the module still cannot go live",
          st["comfortable"] is None and st["settled"] is False and len(st["survivors"]) == 1
          and "UNSETTLED" in st["why"][0] and "never from this module" in st["live"], st)
    # A187 ("comfortable generating a profit"): a survivor counts only with a positive paper return on a surviving asset
    TM._append({"kind": "hypothesis", "name": "stub-loss", "survives": True, "paper": True, "result": {"assets": {"X": {"survives": True, "return": -0.02}}}})
    st1b = TM.status(rule5_={"clears": True, "why": ""})
    check("TM1e a survivor with a paper LOSS is still kept out of the evidence (the measurement stayed honest)",
          st1b["comfortable"] is None and "stub-loss" in st1b["survivors"] and "stub-loss" not in st1b["profitable"], st1b)
    for n in ("a", "b"):
        TM._append({"kind": "hypothesis", "name": "stub-" + n, "survives": True, "paper": True, "result": {"assets": {"X": {"survives": True, "return": 0.05}}}})
    st2 = TM.status(rule5_={"clears": False, "why": "4 settled signals, need 30"})
    check("TM1e three profitable survivors and Rule 5 failing: still unsettled, and Rule 5 is still named",
          st2["comfortable"] is None and len(st2["profitable"]) == 3
          and any("Rule 5 does not clear" in w for w in st2["why"]), (st2["profitable"], st2["why"]))
    st3 = TM.status(rule5_={"clears": True, "why": ""})
    check("TM1e the assistant's old bar fully met -- three survivors AND Rule 5 clearing -- STILL does not make it comfortable",
          st3["comfortable"] is None and st3["settled"] is False and "UNSETTLED" in st3["why"][0]
          and "assistant's number" in st3["needed_note"], st3)
    TM.declare_comfortable("the paper rules have held for me and I am ready to watch it live")
    st4 = TM.status(rule5_={"clears": True, "why": ""})
    check("TM1e only Tetsu settles it: his own declaration makes it comfortable, and his reason is carried",
          st4["comfortable"] is True and st4["settled"] is True and st4["declared_by_tetsu"]["by"] == "tetsu"
          and "ready to watch it live" in st4["why"][0], st4)
    TM.declare_comfortable("I have changed my mind", comfortable=False)
    st5 = TM.status(rule5_={"clears": True, "why": ""})
    check("TM1e a declaration is not a one-way door: he can take it back and it goes shut again",
          st5["comfortable"] is False and st5["settled"] is True, st5)
    check("TM1e settling it moves none of the operator's gates: live is still never from this module",
          "never from this module" in st4["live"] and "each order is his go" in st4["live"])
    check("TM1e the real Rule 5 summary is read (measured, not assumed): it does not clear today and says why", TM.rule5()["clears"] is False and TM.rule5()["why"])
    src = open(TM.__file__, encoding="utf-8").read()
    check("TM1e the module imports no venue client, no trader and no order path (text check beside the run above)",
          not any(("import " + m) in src or ("from " + m) in src for m in ("venues", "coinbase_balance", "covenant_trader", "trader", "rebalance_strategy", "urllib", "requests"))
          and "orders_create" not in src and "place_order" not in src)

    print("TM1f -- what his proposal prompt shows him")
    # A348h: the bounds went out as [lo, hi] lists in params' own shape and his refusals never came
    # back: 14 of 19 live ledger rows were refused "... is not a number", one proposal 7 times.
    pl = os.path.join(tempfile.mkdtemp(prefix="tm1f_"), "strategy.jsonl")
    out_f = TM.study(ask_with({"family": "sma_longonly", "params": {"fast": [5, 50], "slow": [200, 200]}, "why": "r"}),
                     judge=clean, say=quiet, files=files, hold=hold, path=pl)
    TM._append({"kind": "hypothesis", "name": "mean_revert 60/1.0", "survives": False, "result": {"assets": {}, "why": "no price series to test on (UNDETERMINED)"}}, pl)
    TM._append({"kind": "hypothesis", "name": "sma_cross 8/48", "survives": False, "result": {"assets": {"X": {}}, "why": "no asset cleared the three tests"}}, pl)
    seen_p = []
    nxt = {"family": "breakout", "params": {"lookback": 24}, "why": "w"}
    h_f, _raw = TM.propose(lambda msgs, max_tokens=0: (seen_p.append(msgs) or json.dumps(nxt), {"model": "stub"}), pl, hold)
    user_f = seen_p[-1][1]["content"] if seen_p else ""
    check("TM1f a refused proposal comes back to him: what he sent and the lab's reason are in his next prompt",
          "refused" in out_f["why"] and "sma_longonly.fast is not a number" in user_f and '"fast": [5, 50]' in user_f, (out_f["why"], user_f[-400:]))
    bounds_sec = user_f.split("Families and bounds", 1)[-1].split("Your last hypotheses", 1)[0]
    asks_one = all(("- %s:" % fam) in bounds_sec and all(("%s = one" % n) in bounds_sec and ("from %s to %s" % TM.FAMILIES[fam][2][n]) in bounds_sec for n in TM.FAMILIES[fam][1])
                   for fam in TM.FAMILIES)
    check("TM1f every bound asks for ONE number ('from lo to hi'), never a [lo, hi] list in params' own shape",
          "Families and bounds" in user_f and asks_one and "[" not in bounds_sec and "fast below slow" in bounds_sec, bounds_sec[:400])
    check("TM1f a hypothesis that met no price series reads untested, a tested one still reads no",
          "- mean_revert 60/1.0 -> untested" in user_f and "- mean_revert 60/1.0 -> no" not in user_f and "- sma_cross 8/48 -> no" in user_f, user_f[:600])
    check("TM1f the prompt carries information only: his answer is still taken as he gave it", h_f == nxt, h_f)

    print("TM1g -- a hypothesis that met no price series is untested (A349 B11)")
    pg = os.path.join(tempfile.mkdtemp(prefix="tm1g_"), "strategy.jsonl")
    base = TM.trials_so_far(pg)
    hy = {"family": "mean_revert", "params": {"lookback": 30, "z_enter": 1.5}, "assets": ["BTCUSD"], "why": "w"}
    said_g = []
    out_g = TM.study(ask_with(hy), judge=clean, say=said_g.append, files={}, hold=hold, path=pg)
    rg = TM._rows(pg)[-1]
    check("TM1g recorded untested: the row says tested false, never a survivor, and the nightly line reads untested, not no",
          out_g["recorded"] and rg["kind"] == "hypothesis" and rg.get("tested") is False and rg["survives"] is False
          and said_g and " -- untested -- " in said_g[-1] and " -- no -- " not in said_g[-1], (rg, said_g[-1:]))
    check("TM1g an untested hypothesis is not counted against the deflated Sharpe", base == len(L.build_grid()) and TM.trials_so_far(pg) == base, (base, TM.trials_so_far(pg)))
    TM._append({"kind": "hypothesis", "name": "mean_revert 60/1.0", "survives": False, "result": {"assets": {}, "why": "no price series to test on (UNDETERMINED)"}}, pg)
    check("TM1g nor is one written before A349, read from its empty result", TM.trials_so_far(pg) == base, TM.trials_so_far(pg))
    out_g2 = TM.study(ask_with(hy), judge=clean, say=quiet, files=files, hold=hold, path=pg)
    rg2 = TM._rows(pg)[-1]
    check("TM1g its name is not blocked: the same params with a series are tested and counted, and only tested rows count",
          "already on the record" not in out_g2["why"] and rg2["name"] == "mean_revert 30/1.5" and rg2.get("tested") is True and rg2["result"]["assets"]
          and rg2["result"]["trials_counted"] == base + 1 and TM.trials_so_far(pg) == base + 1, (out_g2, rg2.get("result", {}).get("trials_counted")))
    out_g3 = TM.study(ask_with(hy), judge=clean, say=quiet, files=files, hold=hold, path=pg)
    check("TM1g once tested, its name is on the record as before", "already on the record" in out_g3["why"], out_g3)

    print("TM1h -- a walk-forward that cannot run is UNDETERMINED, not failed (A349 B12)")
    sym1, f1 = list(files.items())[0]
    nb = len(SV.load_csv(f1))
    res_u = TM.evaluate({"family": "sma_cross", "params": {"fast": 20, "slow": 100}}, files=files, holdings_=hold)
    au = res_u["assets"].get(sym1, {})
    check("TM1h a warm-up this series cannot hold at 5 folds: walk-forward recorded UNDETERMINED with its reason, wf unmeasured, not a survivor",
          nb < 6 * (102 + 30) and au.get("wf") is None and au.get("wf_undetermined") == "UNDETERMINED: %d bars cannot support 5 folds with warmup 102" % nb
          and au.get("survives") is False and res_u["survives"] is False and res_u.get("walk_forward_undetermined") == [sym1], (nb, au))
    check("TM1h the why says walk-forward was UNDETERMINED, not failed, beside the measured fail (its deflated Sharpe did not clear)",
          au.get("dsr", 1.0) < 0.95 and res_u["why"].startswith("no asset cleared") and ("walk-forward was UNDETERMINED, not failed, on %s" % sym1) in res_u["why"]
          and not res_u.get("undetermined"), res_u["why"])
    real_dsr, real_pbo = SV.deflated_sharpe, SV.pbo
    try:
        SV.deflated_sharpe = lambda r: dict(real_dsr(r), deflated_sharpe=0.99)
        SV.pbo = lambda rets: (0.1, 4)
        res_o = TM.evaluate({"family": "sma_cross", "params": {"fast": 20, "slow": 100}}, files=files, holdings_=hold)
        res_m = TM.evaluate({"family": "sma_cross", "params": {"fast": 8, "slow": 48}}, files=files, holdings_=hold)
    finally:
        SV.deflated_sharpe, SV.pbo = real_dsr, real_pbo
    check("TM1h the two measured tests cleared (stubbed) and walk-forward could not run: the verdict is UNDETERMINED, and still not a pass",
          res_o.get("undetermined") == [sym1] and res_o["why"].startswith("UNDETERMINED: on %s the deflated Sharpe and PBO cleared but walk-forward could not run" % sym1)
          and res_o["survives"] is False and res_o["assets"][sym1]["survives"] is False, res_o.get("why"))
    check("TM1h what counts as a pass is unchanged: where walk-forward runs, the same stubs pass or fail on its consistency alone",
          res_m["assets"][sym1]["wf"] is not None and "wf_undetermined" not in res_m["assets"][sym1]
          and res_m["assets"][sym1]["survives"] is bool(res_m["assets"][sym1]["wf"]["consistent"]) and not res_m.get("undetermined"), res_m["assets"][sym1])
    ph = os.path.join(tempfile.mkdtemp(prefix="tm1h_"), "strategy.jsonl")
    TM._append({"kind": "hypothesis", "name": "sma_cross 20/100", "survives": False, "result": {k: v for k, v in res_o.items() if k != "consequence"}}, ph)
    TM._append({"kind": "hypothesis", "name": "sma_longonly 5/200", "survives": False, "result": {k: v for k, v in res_u.items() if k != "consequence"}}, ph)
    seen_h = []
    TM.propose(lambda msgs, max_tokens=0: (seen_h.append(msgs) or "{}", {"model": "stub"}), ph, hold)
    user_h = seen_h[-1][1]["content"] if seen_h else ""
    check("TM1h his prompt reads the undetermined one as undetermined, not no and not untested; the measured fail still reads no; both count as trials",
          "- sma_cross 20/100 -> undetermined: UNDETERMINED" in user_h and "- sma_longonly 5/200 -> no" in user_h and "untested" not in user_h
          and TM.trials_so_far(ph) == len(L.build_grid()) + 2, user_h[:500])

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
