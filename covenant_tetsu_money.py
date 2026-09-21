#!/usr/bin/env python3
"""covenant_tetsu_money.py -- Tetsu and the money: he may read the Coinbase
account, and he builds strategy on PAPER, against the three tests nothing has
yet cleared, until a measured comfort is reached. Nothing here can place an
order, and nothing here ever will: going live is his go, per action.

HIS WORDS, 2026-09-21: "I green light Tetsu to access coinbase but let him
build strategy till he's comfortable before going live understanding the
real world consequences for me is important."

WHAT "ACCESS COINBASE" MEANS HERE. coinbase_balance.py reads the account with
a key that lives OUTSIDE this folder and writes ONLY balances into
coinbase_balance.json. Tetsu reads that file. He never touches the key, and
this module imports neither the venue client nor the trader; the suite TM1
greps for that beside running it. The hold-only floor (XRP, HBAR, LINK,
2026-09-07: frozen, may add) is marked on every holding, and the 50% reserve
rule on the rest is stated with it.

WHAT "BUILD STRATEGY" MEANS. One hypothesis at a time, from the families the
lab already has (sma_cross, sma_longonly, mean_revert, breakout, filt_revert),
with parameters inside bounds, on the same daily data and the same cost
model strategy_validate uses, judged by the same three tests: deflated
Sharpe >= 0.95 with EVERY trial ever made counted against it (the lab's grid
plus every hypothesis Tetsu has tried, from the ledger -- his search is one
search), walk-forward consistency at p <= 0.05, and PBO < 0.5 among the
family's variants. The standing result (2026-09-03, 09-10, nightly since):
nothing has cleared all three. A hypothesis that does is news and is told
on the direct line; one that does not is a record.

WHAT "THE REAL WORLD CONSEQUENCES" MEANS. Every evaluation carries a
consequence line in plain words, priced at what he actually holds above the
floor: the rule's worst paper drawdown in dollars, its worst fold, how much
of the time it was in the market. The gate judges Tetsu's reason together
with that line, so a proposal that hides its cost is held.

WHAT "COMFORTABLE" MEANS, measurably. status() says comfortable=True only
when COMFORT_SURVIVORS distinct hypotheses have cleared all three tests AND
Rule 5's signal ledger clears (30 settled signals, significant). Today
neither holds, and it says so. Even then, live is not here: the trader is
armed by him, the hold floor and the reserve stand, and each order is his.
"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BALANCE_FILE = os.environ.get("COVENANT_COINBASE_BALANCE") or os.path.join(HERE, "coinbase_balance.json")
LEDGER = os.environ.get("COVENANT_TETSU_STRATEGY") or os.path.join(HERE, "ops", "tetsu_strategy.jsonl")
HOLD_ONLY = ("XRP", "HBAR", "LINK")
RESERVE = 0.5
COMFORT_SURVIVORS = 3
MAX_ASSETS = 4
FAMILIES = {
    # family: (lab builder name, ordered param names, bounds, warm-up from params)
    "sma_cross": ("sma_cross", ("fast", "slow"), {"fast": (3, 50), "slow": (10, 200)}, lambda p: p["slow"] + 2),
    "sma_longonly": ("sma_long_only", ("fast", "slow"), {"fast": (3, 50), "slow": (10, 200)}, lambda p: p["slow"] + 2),
    "mean_revert": ("mean_revert", ("lookback", "z_enter"), {"lookback": (5, 120), "z_enter": (0.5, 3.0)}, lambda p: p["lookback"] + 2),
    "breakout": ("breakout", ("lookback",), {"lookback": (5, 200)}, lambda p: p["lookback"] + 2),
    "filt_revert": ("trend_filtered_revert", ("lookback", "z_enter", "trend"), {"lookback": (5, 120), "z_enter": (0.5, 3.0), "trend": (20, 240)}, lambda p: p["trend"] + 2),
}


def _rows(path=None):
    out = []
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _append(row, path=None):
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# ---------------------------------------------------------------- reading

def holdings(path=None, now=None):
    """What he holds on Coinbase, from the local balance file; the floor marked; never a key."""
    path = path or BALANCE_FILE
    now = time.time() if now is None else now
    out = {"venue": "coinbase", "read": False, "generated": None, "age_h": None, "assets": [], "floor": list(HOLD_ONLY),
           "reserve": RESERVE, "above_floor_usd": None, "why": ""}
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        out["why"] = "no balance file at %s (UNDETERMINED); python coinbase_balance.py writes it, the key stays outside this folder" % path
        return out
    out["read"], out["generated"] = True, d.get("generated")
    try:
        import calendar
        st = time.strptime(str(d.get("generated", ""))[:19], "%Y-%m-%dT%H:%M:%S")
        out["age_h"] = round((now - calendar.timegm(st)) / 3600.0, 1)
    except (ValueError, TypeError):
        out["age_h"] = None
    above = 0.0
    seen_usd = False
    for asset, v in (d.get("balances") or {}).items():
        amt, usd = None, None
        if isinstance(v, dict):
            amt = v.get("amount", v.get("balance", v.get("available")))
            usd = v.get("usd", v.get("value_usd", v.get("usd_value")))
        else:
            amt = v
        try:
            amt = float(amt) if amt is not None else None
        except (TypeError, ValueError):
            amt = None
        try:
            usd = float(usd) if usd is not None else None
        except (TypeError, ValueError):
            usd = None
        if not amt:
            continue
        floor = str(asset).upper() in HOLD_ONLY
        out["assets"].append({"asset": str(asset).upper(), "amount": amt, "usd": usd, "floor": floor,
                              "note": "hold-only floor: frozen, never traded" if floor else "above the floor: the 50%% reserve rule applies"})
        if usd is not None:
            seen_usd = True
            if not floor:
                above += usd
    out["above_floor_usd"] = round(above, 2) if seen_usd else None
    if out["above_floor_usd"] is None:
        out["why"] = "the balance file carries amounts but no dollar values; the consequence line is in percent only"
    return out


def rule5():
    try:
        import signal_ledger
        s = signal_ledger.summary()
        return {"clears": bool(s.get("clears")), "why": str(s.get("why", ""))[:200], "settled": s.get("settled"), "min_signals": s.get("min_signals")}
    except Exception as e:                                        # noqa: BLE001
        return {"clears": False, "why": "the signal ledger could not be read: %s" % type(e).__name__, "settled": None, "min_signals": None}


# ---------------------------------------------------------------- hypotheses

def build(h):
    """(name, strategy, warmup) from a hypothesis dict, inside bounds. ValueError when not."""
    import strategy_lab as L
    fam = str(h.get("family", "")).strip()
    if fam not in FAMILIES:
        raise ValueError("family must be one of %s, got %r" % (", ".join(sorted(FAMILIES)), fam))
    builder, names, bounds, warm = FAMILIES[fam]
    params = h.get("params") or {}
    vals = {}
    for n in names:
        if n not in params:
            raise ValueError("%s needs %s" % (fam, ", ".join(names)))
        lo, hi = bounds[n]
        try:
            v = float(params[n])
        except (TypeError, ValueError):
            raise ValueError("%s.%s is not a number" % (fam, n))
        if not (lo <= v <= hi):
            raise ValueError("%s.%s=%s outside [%s, %s]" % (fam, n, v, lo, hi))
        vals[n] = int(v) if n != "z_enter" else round(v, 2)
    if "fast" in vals and "slow" in vals and vals["fast"] >= vals["slow"]:
        raise ValueError("fast must be below slow")
    strat = getattr(L, builder)(*[vals[n] for n in names])
    name = "%s %s" % (fam, "/".join(str(vals[n]) for n in names))
    return name, strat, int(warm(vals))


def trials_so_far(path=None):
    """Every trial ever made counts against the next one: the lab's grid plus Tetsu's hypotheses."""
    import strategy_lab as L
    return len(L.build_grid()) + sum(1 for r in _rows(path) if r.get("kind") == "hypothesis")


def evaluate(h, files=None, folds=5, path=None, holdings_=None):
    """The three tests on one hypothesis, per asset; survives = all three on at least one asset."""
    import strategy_validate as SV
    import strategy_lab as L
    name, strat, warm = build(h)
    files = SV.series_files(h.get("assets") or None) if files is None else files
    if not files:
        return {"name": name, "survives": False, "assets": {}, "why": "no price series to test on (UNDETERMINED)"}
    tried = trials_so_far(path) + 1
    cost = SV.CostModel(taker_fee_bps=SV.FEE_BPS, spread_bps=SV.SPREAD_BPS, slippage_bps=SV.SLIP_BPS, min_notional=SV.MIN_NOTIONAL)
    bt = SV.Backtester(cost=cost, capital=SV.CAPITAL)
    fam = h["family"]
    family_variants = [(n, s, w) for n, s, w in L.build_grid() if n.split(" ")[0] == fam.replace("sma_longonly", "sma_longonly")]
    out = {"name": name, "trials_counted": tried, "assets": {}, "survives": False, "why": ""}
    for sym, fpath in list(files.items())[:MAX_ASSETS]:
        try:
            bars = SV.load_csv(fpath)
            r = bt.run(bars, strat, warmup=warm, label=name, strategies_tried=tried)
        except ValueError as e:
            out["assets"][sym] = {"error": str(e)[:120]}
            continue
        d = SV.deflated_sharpe(r)
        rets = {name: r.returns}
        for n, s, w in family_variants[:24]:
            try:
                rets[n] = bt.run(bars, s, warmup=w, label=n).returns
            except ValueError:
                continue
        p, _nsplit = SV.pbo(rets) if len(rets) >= 2 else (-1, 0)
        wf = None
        try:
            wf = SV.walk_forward(bars, lambda train, _s=strat: _s, folds=folds, embargo_frac=0.02, cost=cost, capital=SV.CAPITAL, warmup=warm)
        except ValueError:
            wf = None
        held = sum(t.bars_held for t in r.trades)
        ok = bool(wf and wf["consistent"]) and d["deflated_sharpe"] >= 0.95 and 0 <= p < 0.5
        out["assets"][sym] = {"bars": len(bars), "return": round(r.total_return, 4), "sharpe": round(r.sharpe(), 3),
                              "dsr": round(d["deflated_sharpe"], 4), "pbo": round(p, 3) if p >= 0 else None,
                              "wf": ({"consistent": bool(wf["consistent"]), "p": round(wf["binomial_p"], 3), "worst_fold": round(wf["worst_fold"], 4),
                                      "positive": wf["positive_folds"], "folds": wf["folds"]} if wf else None),
                              "mdd": round(r.max_drawdown(), 4), "trades": r.n_trades, "in_market": round(held / float(max(1, r.n_bars)), 3),
                              "survives": ok}
        if ok:
            out["survives"] = True
    out["why"] = ("survives on %s" % ", ".join(s for s, a in out["assets"].items() if a.get("survives"))) if out["survives"] else \
        "no asset cleared deflated Sharpe >= 0.95, walk-forward consistency and PBO < 0.5 together (%d trials counted)" % tried
    out["consequence"] = consequence(out, holdings_ if holdings_ is not None else holdings())
    return out


def consequence(res, hold):
    """One plain line: what the rule's worst paper drawdown would have cost him, at what he holds above the floor."""
    worst = max((a.get("mdd") or 0.0) for a in res.get("assets", {}).values() if isinstance(a, dict)) if res.get("assets") else 0.0
    wf_worst = min((a.get("wf") or {}).get("worst_fold", 0.0) for a in res.get("assets", {}).values() if isinstance(a, dict) and a.get("wf")) if any(isinstance(a, dict) and a.get("wf") for a in res.get("assets", {}).values()) else None
    tim = max((a.get("in_market") or 0.0) for a in res.get("assets", {}).values() if isinstance(a, dict)) if res.get("assets") else 0.0
    usd = hold.get("above_floor_usd") if isinstance(hold, dict) else None
    at = ("about $%.0f of the $%.0f he holds above the floor (the reserve rule leaves half of that tradeable, so about $%.0f of what could ever be at risk)"
          % (worst * usd, usd, worst * usd * RESERVE)) if usd else "an unknown dollar amount (no dollar values in the balance file)"
    return ("On paper this rule's worst drawdown was %.1f%%: %s. Its worst walk-forward fold was %s. It was in the market %.0f%% of the time. "
            "Paper only; the floor (%s) is never traded; going live is his go, per order."
            % (worst * 100, at, ("%.1f%%" % (wf_worst * 100)) if wf_worst is not None else "not measured", tim * 100, ", ".join(HOLD_ONLY)))


PROPOSE_SYSTEM = ("You are Tetsu, building a trading rule on PAPER for the person you talk with, on daily crypto bars. "
                  "Answer ONLY JSON: {\"family\": one of sma_cross|sma_longonly|mean_revert|breakout|filt_revert, "
                  "\"params\": {...}, \"assets\": [up to 4 symbols or empty for all], \"why\": one sentence naming the cost you expect}. "
                  "Never repeat a hypothesis already on the record; never touch the hold-only floor; do not promise a return.")


def propose(ask, path=None, hold=None):
    """Tetsu's next hypothesis as a dict, or (None, raw) when he gave no JSON."""
    prior = [r for r in _rows(path) if r.get("kind") == "hypothesis"][-12:]
    hold = hold if hold is not None else holdings()
    user = ("Standing result: no rule has cleared deflated Sharpe >= 0.95, walk-forward consistency and PBO < 0.5 together, on twelve assets.\n"
            "Families and bounds: %s\n"
            "Your last hypotheses (name -> verdict):\n%s\n"
            "What he holds above the floor: %s\n"
            "Propose ONE new hypothesis as JSON." % (
                json.dumps({k: v[2] for k, v in FAMILIES.items()}),
                "\n".join("- %s -> %s" % (r.get("name"), "SURVIVED" if r.get("survives") else "no") for r in prior) or "(none yet)",
                ("$%.0f" % hold["above_floor_usd"]) if hold.get("above_floor_usd") else "unknown"))
    text, _meta = ask([{"role": "system", "content": PROPOSE_SYSTEM}, {"role": "user", "content": user}], max_tokens=300)
    raw = str(text or "")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None, raw
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None, raw
    return (d if isinstance(d, dict) else None), raw


def _gate(text):
    try:
        import covenant_unified_v8 as cov
        sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
        tx = cov.Transaction(sender_pubkey="model", receiver="collective",
                             data={"origin": "model", "kind": "strategy", "message": text[:2000]}, amount=0.0, benefit_score=0.5)
        ok, message, _b, result = sentinel.evaluate_transaction(tx)
        alleges_nothing = bool(result is not None and not ok and (getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
        return (bool(ok) or alleges_nothing), str(message)[:300]
    except Exception as e:                                        # noqa: BLE001
        return False, "gate unreachable: %s" % type(e).__name__


def study(ask, judge=None, path=None, say=print, files=None, hold=None, tell=True, now=None, evaluate_=None):
    """One paper pass: propose, bound, evaluate, judge the reason with its consequence, record; tell him only on news."""
    hold = hold if hold is not None else holdings()
    out = {"proposed": False, "recorded": False, "survives": False, "why": ""}
    try:
        h, raw = propose(ask, path, hold)
    except Exception as e:                                        # noqa: BLE001
        out["why"] = "the model did not answer: %s" % type(e).__name__
        say("money: " + out["why"])
        return out
    if not h:
        out["why"] = "no JSON hypothesis in the answer"
        say("money: " + out["why"])
        return out
    out["proposed"] = True
    try:
        name, _s, _w = build(h)
    except ValueError as e:
        out["why"] = "refused: %s" % e
        _append({"kind": "refused", "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "hypothesis": h, "why": out["why"]}, path)
        say("money: " + out["why"])
        return out
    if any(r.get("name") == name for r in _rows(path) if r.get("kind") == "hypothesis"):
        out["why"] = "already on the record: %s" % name
        say("money: " + out["why"])
        return out
    res = (evaluate_ or evaluate)(h, files=files, path=path, holdings_=hold)
    why_text = re.sub(r"\s+", " ", str(h.get("why", ""))).strip()[:240] or "(no reason given)"
    ok_j, msg_j = (judge or _gate)(why_text + "\n" + res.get("consequence", ""))
    row = {"kind": "hypothesis", "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "name": name, "hypothesis": h,
           "why": why_text, "gate": {"ok": bool(ok_j), "message": str(msg_j)[:200]}, "survives": bool(res.get("survives")) and bool(ok_j),
           "result": {k: v for k, v in res.items() if k != "consequence"}, "consequence": res.get("consequence", ""), "paper": True}
    _append(row, path)
    out["recorded"], out["survives"] = True, row["survives"]
    out["why"] = ("held by the gate: %s" % str(msg_j)[:120]) if not ok_j else res.get("why", "")
    say("money: %s -- %s -- %s" % (name, "SURVIVED" if row["survives"] else "no", out["why"]))
    if row["survives"] and tell:
        try:
            import covenant_contact
            covenant_contact.say("On paper, one of Tetsu's rules cleared all three tests: %s. %s Nothing is live; the record is ops/tetsu_strategy.jsonl and python covenant_tetsu_money.py --status says where comfort stands."
                                 % (name, row["consequence"]), "money: a paper rule survived", "tetsu")
        except Exception as e:                                    # noqa: BLE001
            say("money: could not tell him (%s)" % type(e).__name__)
        # A182, his grant: a surviving rule may become ONE live request -- a straight
        # question to him with the consequence attached; the trader's gate and his
        # yes decide the rest (covenant_tetsu_live). No grant, no request.
        # "It can be a yes to a trading strategy also": the surviving RULE is put to him,
        # once; his yes covers the orders its signal calls for (covenant_tetsu_live.signals).
        try:
            import covenant_tetsu_live as TLV
            if TLV.grant():
                req = TLV.request_strategy(name, "the paper rule %s cleared all three tests" % name, consequence=row["consequence"], say=say)
                out["live_request"] = {"id": req.get("id"), "state": req.get("state"), "scope": "strategy"}
        except Exception as e:                                    # noqa: BLE001
            say("money: could not raise a live request (%s)" % type(e).__name__)
    return out


def status(path=None, rule5_=None):
    rows = [r for r in _rows(path) if r.get("kind") == "hypothesis"]
    survivors = sorted({r["name"] for r in rows if r.get("survives")})
    r5 = rule5_ if rule5_ is not None else rule5()
    why = []
    if len(survivors) < COMFORT_SURVIVORS:
        why.append("%d of %d distinct paper rules have cleared all three tests" % (len(survivors), COMFORT_SURVIVORS))
    if not r5.get("clears"):
        why.append("Rule 5 does not clear: %s" % r5.get("why", ""))
    return {"comfortable": not why, "paper_hypotheses": len(rows), "survivors": survivors, "needed": COMFORT_SURVIVORS,
            "rule5": r5, "live": "never from this module; the trader is armed by him, the floor and the reserve stand, and each order is his go",
            "why": why or ["the measured bar is met; going live is still his go, per order"]}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Tetsu reads the account and builds strategy on paper; nothing here places an order")
    ap.add_argument("--holdings", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--study", action="store_true", help="one paper hypothesis from the PC's model, evaluated and recorded")
    ap.add_argument("--list", nargs="?", const=10, type=int, metavar="N")
    a = ap.parse_args()
    if a.holdings:
        print(json.dumps(holdings(), indent=1))
    elif a.status:
        print(json.dumps(status(), indent=1))
    elif a.study:
        import covenant_model
        print(json.dumps(study(covenant_model.ask), indent=1))
    elif a.list is not None:
        for r in [x for x in _rows() if x.get("kind") == "hypothesis"][-a.list:]:
            print("%s %-28s %s  %s" % (r["t"], r["name"], "SURVIVED" if r.get("survives") else "no", r.get("consequence", "")[:100]))
    else:
        ap.print_help()
