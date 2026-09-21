#!/usr/bin/env python3
"""covenant_tetsu_live.py -- Tetsu's permission in Coinbase: a live order is
his straight question to the operator, the trader's own gate, and the
operator's yes -- all three, per order, or nothing.

HIS WORDS, 2026-09-21: "I over ride and give wetsuit permission in coinbase.
He's free to ask me anything." (after: "let him build strategy till he's
comfortable before going live understanding the real world consequences for
me is important").

THE GRANT is ops/tetsu_coinbase_grant.json, his words in it. No file, or
granted=false, and nothing here requests or places anything.

WHAT A REQUEST IS. Tetsu names a side, a symbol, a dollar size and his
reason. This module:
  1. bounds the size to the trader's max_order_usd; refuses a SELL of a
     hold-only asset (the floor is frozen: XRP, HBAR, LINK);
  2. runs the trader's ONE precondition gate on the order exactly as the
     trader would (guards.preconditions: armed, no halt, the day's plan
     approved by his signature, Rule 5's sealed signals, the caps, the
     reserve) and records every reason it returns;
  3. asks HIM on the direct line, straight (covenant_contact.ask, A177): the
     order, the reason, the paper consequence, the request id, and -- when
     the gate blocks -- the blocks by name, so he can change his own rules
     if he wants to, or say no. He is free to be asked anything; the asking
     is not the placing.

WHAT A PLACEMENT IS. settle() places a request only when ALL of these hold at
that moment: the grant; his YES recorded after the question was shown (a
tailnet chat line beginning yes/go/ok/do it, or naming the request id with
yes); the gate clear NOW, re-run; the pause switch off. Then, and only then,
venues.CoinbaseVenue().place(...) with live=True -- the same call the trader
makes, maker-by-default, his key from outside this folder. Every outcome is
a row in ops/tetsu_live.jsonl: requested, blocked, asked, yes, no, placed,
not placed and why. dry_run=True is the default of every entry point; the
nightly passes live only under --money-live 1.

MEASURED WHEN THIS WAS WRITTEN: the gate blocks every live order today --
Rule 5 has 4 sealed signals of 30 and no day's plan is approved -- so the
permission is real and the first placement waits on his own earlier rules.
Nothing here lowers a gate; a grant extends what may be asked, never what
may pass (the rule of A168).
"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GRANT = os.environ.get("COVENANT_TETSU_COINBASE_GRANT") or os.path.join(HERE, "ops", "tetsu_coinbase_grant.json")
LEDGER = os.environ.get("COVENANT_TETSU_LIVE") or os.path.join(HERE, "ops", "tetsu_live.jsonl")
ASK_LOG = os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
HOLD_ONLY = ("XRP", "HBAR", "LINK")
YES = re.compile(r"^\s*(yes|yep|yeah|go|go ahead|do it|ok|okay|approved|place it)\b", re.I)
NO = re.compile(r"^\s*(no|nope|don'?t|do not|stop|hold|wait|not now)\b", re.I)


def grant(path=None):
    try:
        with open(path or GRANT, encoding="utf-8") as fh:
            g = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(g, dict) or not g.get("granted") or not g.get("words"):
        return None
    return g


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
    row = dict(row)
    row.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def paused():
    try:
        import covenant_pause
        for name in ("tetsu-live", "trader"):
            p, why = covenant_pause.paused(name)
            if p:
                return True, "%s: %s" % (name, why)
    except Exception:                                             # noqa: BLE001
        pass
    return False, ""


def gate_reasons(order, preconditions=None, now=None):
    """The trader's own reasons this order may not go live now. Never raises: an unreadable gate is a reason."""
    try:
        if preconditions is None:
            import guards
            import signal_ledger
            sealed = bool(signal_ledger.summary().get("clears"))
            return list(guards.preconditions(order, sealed_ok=sealed, guard_blocks=None, caller="trader", now=now))
        return list(preconditions(order))
    except Exception as e:                                        # noqa: BLE001
        return ["the trader's gate could not be evaluated (%s: %s) -- nothing may go live" % (type(e).__name__, str(e)[:80])]


def max_order_usd():
    try:
        import guards
        return float(guards.load_config().get("max_order_usd") or 25.0)
    except Exception:                                             # noqa: BLE001
        return 25.0


STOP = re.compile(r"^\s*(stop|halt|no more|revoke)\b", re.I)


def request_strategy(name, why, consequence="", ask_fn=None, judge=None, path=None, grant_path=None, now=None, say=print):
    """His yes can cover a STRATEGY, not only an order (his words, 2026-09-21: "It can be a yes to a trading
    strategy also"). One straight question: may Tetsu trade this paper rule live inside the rails; a yes
    covers the orders its signal calls for, each still passing the trader's gate, until he says stop."""
    name = re.sub(r"\s+", " ", str(name or "")).strip()[:80]
    row = {"kind": "request", "id": "", "scope": "strategy", "strategy": name, "side": None, "sym": None, "usd": None,
           "why": str(why or "")[:240], "consequence": str(consequence or "")[:400], "blocks": [], "state": "", "question_id": None}
    if not grant(grant_path):
        row["state"] = "refused: no grant on record (ops/tetsu_coinbase_grant.json)"
        say("live: " + row["state"])
        return _append(row, path)
    p, pwhy = paused()
    if p:
        row["state"] = "refused: paused (%s)" % pwhy
        say("live: " + row["state"])
        return _append(row, path)
    if not name:
        row["state"] = "refused: a strategy request names the rule"
        say("live: " + row["state"])
        return _append(row, path)
    if any(r.get("scope") == "strategy" and r.get("strategy") == name and r.get("state", "").startswith("asked") for r in _rows(path)):
        row["state"] = "already asked for this rule"
        say("live: " + row["state"])
        return _append(row, path)
    import secrets
    row["id"] = secrets.token_hex(4)
    row["blocks"] = gate_reasons({"side": "buy", "usd": min(5.0, max_order_usd()), "sym": "BTC"}, None, now)[:12]
    q = ("Straight question, request %s: may I trade the paper rule %s live on your Coinbase account, inside your rails "
         "(at most $%.2f an order, the trader's daily caps, the floor never sold, every order still passing the trader's gate)? "
         "My reason: %s. %s Your yes covers this rule's orders until you say 'stop %s'. %s Yes or no?"
         % (row["id"], name, max_order_usd(), row["why"] or "(none given)", (row["consequence"] + " ") if row["consequence"] else "", name,
            ("Your own rails block every order today: %s. If you want that changed, that is your call, not mine." % "; ".join(row["blocks"])) if row["blocks"] else "Your rails are clear today."))
    q = re.sub(r"\s+", " ", q).strip()[:600]
    if not q.endswith("?"):
        q = q[:-1].rstrip(".") + "?"
    try:
        if ask_fn is None:
            import covenant_contact
            ask_fn = covenant_contact.ask
        qrow, qwhy = ask_fn(q, "Tetsu asks before trading a rule live (his grant, 2026-09-21)", "tetsu", judge=judge)
        row["question_id"] = qrow.get("id") if qrow else None
        row["state"] = ("asked" if qrow else "not asked: " + str(qwhy)) + (" (blocked today)" if row["blocks"] else "")
    except Exception as e:                                        # noqa: BLE001
        row["state"] = "not asked: %s" % type(e).__name__
    say("live: strategy %s (%s) -- %s" % (name, row["id"], row["state"]))
    return _append(row, path)


# A211 (2026-09-21, his words: "I want it open on coinbase just verify strategy
# with me daily"). A yes used to stand until he said stop. He asked for a DAILY
# verification instead, so a yes now expires: past VERIFY_EVERY_S a strategy is
# not approved until he verifies it again. This is the door he opened AND the
# condition he attached, in one place -- and it fails shut, because an expired
# approval simply is not an approval.
VERIFY_EVERY_S = 24 * 3600


def approved_strategies(path=None, ask_log=None, contact_state=None, now=None):
    """{rule name: request id} for every strategy he said yes to, has not said
    stop to, AND has verified within the last day."""
    return {k: v["id"] for k, v in _strategy_states(path, ask_log, contact_state, now).items() if v["approved"]}


def answered_at(req, ask_log=None, contact_state=None):
    """When the line that answered this question was written, as an epoch float,
    or None. his_answer returns the TEXT as its second value, not a time, so the
    daily verification needs its own read of the same line (A211)."""
    qid = req.get("question_id")
    if not qid:
        return None
    try:
        import covenant_contact as CT
        seen_at = (CT._state(contact_state).get("seen") or {}).get(qid)
        if not seen_at:
            return None
        lines = []
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if str(r.get("from", "")).startswith("100.") and r.get("kind") in ("agent", "ask", "council") and r.get("text"):
                    lines.append(r)
        later = [r for r in lines if CT._at(r) >= float(seen_at)]
        named = [r for r in later if req.get("id") and req["id"] in str(r.get("text"))]
        cands = named or later[:1]
        return CT._at(cands[0]) if cands else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _strategy_states(path=None, ask_log=None, contact_state=None, now=None):
    """{rule: {"id", "approved", "answered_at", "age_s", "state"}} -- the whole
    picture, so the daily ask knows what to put to him and why."""
    now = time.time() if now is None else now
    out = {}
    for r in _rows(path):
        if not (r.get("kind") == "request" and r.get("scope") == "strategy" and r.get("state", "").startswith("asked")):
            continue
        ans, _text = his_answer(r, ask_log, contact_state)
        if ans != "yes":
            continue
        t = answered_at(r, ask_log, contact_state)
        if stopped(r, ask_log, contact_state):
            out[r["strategy"]] = {"id": r["id"], "approved": False, "answered_at": t, "age_s": None, "state": "stopped by him"}
            continue
        age = (now - float(t)) if t else None
        if age is None:
            out[r["strategy"]] = {"id": r["id"], "approved": False, "answered_at": t, "age_s": None,
                                  "state": "when he said yes cannot be read -- treated as needing verification"}
        elif age > VERIFY_EVERY_S:
            out[r["strategy"]] = {"id": r["id"], "approved": False, "answered_at": t, "age_s": age,
                                  "state": "verification expired (%.1f h old, he asked for daily)" % (age / 3600.0)}
        else:
            out[r["strategy"]] = {"id": r["id"], "approved": True, "answered_at": t, "age_s": age,
                                  "state": "verified %.1f h ago" % (age / 3600.0)}
    return out


def needs_verification(path=None, ask_log=None, contact_state=None, now=None):
    """The strategies to put to him today: ones he approved whose day has run
    out. Not the stopped ones -- a stop is an answer, not a lapse."""
    return {k: v for k, v in _strategy_states(path, ask_log, contact_state, now).items()
            if not v["approved"] and "stopped" not in v["state"]}


def stopped(req, ask_log=None, contact_state=None):
    """True when a tailnet chat line after the question said stop, naming this rule or plain 'stop trading'."""
    qid = req.get("question_id")
    if not qid:
        return False
    try:
        import covenant_contact as CT
        seen_at = (CT._state(contact_state).get("seen") or {}).get(qid)
        if not seen_at:
            return False
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not (str(r.get("from", "")).startswith("100.") and r.get("kind") in ("agent", "ask", "council")):
                    continue
                if CT._at(r) < float(seen_at):
                    continue
                text = str(r.get("text", ""))
                if STOP.search(text) and (req.get("strategy", "") in text or re.search(r"\b(trading|all|everything)\b", text, re.I)):
                    return True
    except (OSError, ValueError, TypeError, AttributeError):
        return False
    return False


def request(side, sym, usd, why, consequence="", ask_fn=None, judge=None, path=None, grant_path=None,
            preconditions=None, now=None, say=print, strategy=None, ask_log=None, contact_state=None):
    """Tetsu's live request: bounded, gated, recorded, and put to him as a straight question -- unless it
    is covered by his yes to a strategy, in which case it is recorded as covered and not asked. Returns the row."""
    side, sym = str(side or "").lower(), str(sym or "").upper()
    row = {"kind": "request", "id": "", "side": side, "sym": sym, "usd": None, "why": str(why or "")[:240],
           "consequence": str(consequence or "")[:400], "blocks": [], "state": "", "question_id": None,
           "strategy": strategy, "covered": None}
    g = grant(grant_path)
    if not g:
        row["state"] = "refused: no grant on record (ops/tetsu_coinbase_grant.json)"
        say("live: " + row["state"])
        return _append(row, path)
    p, pwhy = paused()
    if p:
        row["state"] = "refused: paused (%s)" % pwhy
        say("live: " + row["state"])
        return _append(row, path)
    if side not in ("buy", "sell") or not sym:
        row["state"] = "refused: a request is buy or sell of one symbol"
        say("live: " + row["state"])
        return _append(row, path)
    if side == "sell" and sym in HOLD_ONLY:
        row["state"] = "refused: %s is on the hold-only floor, never sold" % sym
        say("live: " + row["state"])
        return _append(row, path)
    try:
        usd = float(usd)
    except (TypeError, ValueError):
        usd = 0.0
    cap = max_order_usd()
    if usd <= 0:
        row["state"] = "refused: a size in dollars is needed"
        say("live: " + row["state"])
        return _append(row, path)
    if usd > cap:
        row["clipped_from"] = usd
        usd = cap
    row["usd"] = round(usd, 2)
    import secrets
    row["id"] = secrets.token_hex(4)
    order = {"side": side, "usd": row["usd"], "sym": sym}
    row["blocks"] = gate_reasons(order, preconditions, now)[:12]
    if strategy:
        approved = approved_strategies(path, ask_log, contact_state)
        if strategy in approved:
            row["covered"] = approved[strategy]
            row["state"] = "covered by his yes to strategy %s (request %s)%s" % (strategy, approved[strategy], " (blocked today)" if row["blocks"] else "")
            say("live: %s %s $%.2f %s -- %s" % (row["id"], side, row["usd"], sym, row["state"]))
            return _append(row, path)
        row["state_note"] = "strategy %s is not covered by a yes of his; asked per order" % strategy
    q = ("Straight question, request %s: may I %s $%.2f of %s on your Coinbase account? My reason: %s. %s %s Yes or no?"
         % (row["id"], side.upper(), row["usd"], sym, row["why"] or "(none given)",
            (row["consequence"] + " ") if row["consequence"] else "",
            ("Your own rails block it today: %s. If you want that changed, that is your call, not mine." % "; ".join(row["blocks"])) if row["blocks"] else "Your rails are clear for it."))
    q = re.sub(r"\s+", " ", q).strip()[:600]
    if not q.endswith("?"):
        q = q[:-1].rstrip(".") + "?"
    try:
        if ask_fn is None:
            import covenant_contact
            ask_fn = covenant_contact.ask
        qrow, qwhy = ask_fn(q, "Tetsu asks before any live order (his grant, 2026-09-21)", "tetsu", judge=judge)
        row["question_id"] = qrow.get("id") if qrow else None
        row["state"] = ("asked" if qrow else "not asked: " + str(qwhy)) + (" (blocked today)" if row["blocks"] else "")
    except Exception as e:                                        # noqa: BLE001
        row["state"] = "not asked: %s" % type(e).__name__
    say("live: %s %s $%.2f %s -- %s%s" % (row["id"], side, row["usd"], sym, row["state"], ("; blocks: " + "; ".join(row["blocks"][:3])) if row["blocks"] else ""))
    return _append(row, path)


def his_answer(req, ask_log=None, contact_state=None):
    """('yes'|'no'|None, text) -- the first tailnet chat line after the question was shown to him."""
    qid = req.get("question_id")
    if not qid:
        return None, ""
    try:
        import covenant_contact
        st = covenant_contact._state(contact_state)
        seen_at = (st.get("seen") or {}).get(qid)
    except Exception:                                             # noqa: BLE001
        seen_at = None
    if not seen_at:
        return None, ""
    lines = []
    try:
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if str(r.get("from", "")).startswith("100.") and r.get("kind") in ("agent", "ask", "council") and r.get("text"):
                    lines.append(r)
    except OSError:
        return None, ""
    import covenant_contact as CT
    later = [r for r in lines if CT._at(r) >= float(seen_at)]
    named = [r for r in later if req.get("id") and req["id"] in str(r.get("text"))]
    cands = named or later[:1]
    if not cands:
        return None, ""
    text = str(cands[0].get("text", ""))
    if YES.search(text) or (req.get("id") in text and re.search(r"\byes\b", text, re.I)):
        return "yes", text[:200]
    if NO.search(text):
        return "no", text[:200]
    return None, text[:200]


def settle(dry_run=True, venue=None, path=None, grant_path=None, preconditions=None, ask_log=None, contact_state=None, now=None, say=print):
    """Place every asked request that has his yes and a clear gate NOW; record every other outcome. Returns the list of outcomes."""
    out = []
    g = grant(grant_path)
    if not g:
        say("live: no grant; nothing settled")
        return out
    rows = _rows(path)
    done = {r.get("request") for r in rows if r.get("kind") in ("placed", "no", "not_placed", "strategy_yes", "strategy_no")}
    for req in [r for r in rows if r.get("kind") == "request" and (r.get("state", "").startswith("asked") or r.get("covered")) and r.get("id") not in done]:
        if req.get("scope") == "strategy":
            ans, text = his_answer(req, ask_log, contact_state)
            if ans is None:
                out.append({"request": req["id"], "outcome": "waiting for his answer on strategy %s" % req.get("strategy")})
            else:
                _append({"kind": "strategy_yes" if ans == "yes" else "strategy_no", "request": req["id"], "strategy": req.get("strategy"), "his_words": text}, path)
                out.append({"request": req["id"], "outcome": "he said %s to strategy %s" % (ans, req.get("strategy"))})
                say("live: strategy %s -- he said %s" % (req.get("strategy"), ans))
            continue
        if req.get("covered"):
            cov_req = next((r for r in rows if r.get("kind") == "request" and r.get("id") == req["covered"]), None)
            if cov_req is None or stopped(cov_req, ask_log, contact_state) or his_answer(cov_req, ask_log, contact_state)[0] != "yes":
                _append({"kind": "not_placed", "request": req["id"], "why": "the strategy yes it relied on (%s) is not on record or was stopped" % req.get("strategy")}, path)
                out.append({"request": req["id"], "outcome": "the strategy yes was stopped or missing"})
                continue
            ans, text = "yes", "covered by his yes to strategy %s" % req.get("strategy")
        else:
            ans, text = his_answer(req, ask_log, contact_state)
        if ans is None:
            out.append({"request": req["id"], "outcome": "waiting for his answer"})
            continue
        if ans == "no":
            _append({"kind": "no", "request": req["id"], "his_words": text}, path)
            out.append({"request": req["id"], "outcome": "he said no"})
            say("live: %s -- he said no" % req["id"])
            continue
        _append({"kind": "yes", "request": req["id"], "his_words": text}, path)
        p, pwhy = paused()
        blocks = (["paused: " + pwhy] if p else []) + gate_reasons({"side": req["side"], "usd": req["usd"], "sym": req["sym"]}, preconditions, now)
        if blocks:
            _append({"kind": "not_placed", "request": req["id"], "why": "his yes is on record, but the gate blocks now: " + "; ".join(blocks)[:400]}, path)
            out.append({"request": req["id"], "outcome": "yes, but blocked: " + "; ".join(blocks)[:200]})
            say("live: %s -- yes, but the gate blocks: %s" % (req["id"], "; ".join(blocks)[:160]))
            continue
        try:
            if venue is None:
                import venues
                venue = venues.CoinbaseVenue()
            bid, ask = venue.best_bid_ask(venue.meta(req["sym"])["product_id"])
            px = ask if req["side"] == "buy" else bid
            qty = float(req["usd"]) / float(px)
            res = venue.place(req["sym"], req["side"].upper(), qty, live=not dry_run)
            _append({"kind": "placed", "request": req["id"], "dry_run": bool(dry_run), "qty": qty, "px": px,
                     "venue": str(res)[:400]}, path)
            out.append({"request": req["id"], "outcome": ("dry run: would place" if dry_run else "PLACED") + " %s %.6f %s at %s" % (req["side"], qty, req["sym"], px)})
            say("live: %s -- %s" % (req["id"], out[-1]["outcome"]))
        except Exception as e:                                    # noqa: BLE001
            _append({"kind": "not_placed", "request": req["id"], "why": "the venue refused: %s: %s" % (type(e).__name__, str(e)[:200])}, path)
            out.append({"request": req["id"], "outcome": "the venue refused: %s" % type(e).__name__})
            say("live: %s -- the venue refused: %s" % (req["id"], type(e).__name__))
    return out


def bought_under(strategy, sym, path=None):
    """Units bought live under a strategy's yes and not yet sold, from this ledger alone."""
    rows = _rows(path)
    reqs = {r["id"]: r for r in rows if r.get("kind") == "request" and r.get("id")}
    qty = 0.0
    for r in rows:
        if r.get("kind") != "placed" or r.get("dry_run"):
            continue
        rq = reqs.get(r.get("request")) or {}
        if rq.get("strategy") != strategy or rq.get("sym") != sym:
            continue
        qty += float(r.get("qty") or 0) * (1 if rq.get("side") == "buy" else -1)
    return max(0.0, qty)


def signals(rules=None, files=None, path=None, paper_path=None, ask_log=None, contact_state=None, preconditions=None, now=None, say=print):
    """For every strategy his yes covers: read the rule's signal on the LAST bar and raise the order it calls
    for, covered (no question). +1 -> a buy of max_order_usd; -1 -> a sell of what was bought under it; else
    nothing. `rules` = [(name, strategy_fn, [symbols])] or None to rebuild them from the paper ledger."""
    out = []
    approved = approved_strategies(path, ask_log, contact_state)
    if not approved:
        say("live: no strategy carries his yes; no signals read")
        return out
    if rules is None:
        rules = []
        try:
            import covenant_tetsu_money as TMY
            for r in TMY._rows(paper_path):
                if r.get("kind") == "hypothesis" and r.get("name") in approved:
                    _n, strat, _w = TMY.build(r.get("hypothesis") or {})
                    syms = [s for s, a in ((r.get("result") or {}).get("assets") or {}).items() if isinstance(a, dict) and a.get("survives")]
                    rules.append((r["name"], strat, syms))
        except Exception as e:                                    # noqa: BLE001
            say("live: the paper rules could not be rebuilt (%s)" % type(e).__name__)
            return out
    try:
        import strategy_validate as SV
        from covenant_backtest import PointInTimeView
    except Exception as e:                                        # noqa: BLE001
        say("live: no backtester (%s); no signals read" % type(e).__name__)
        return out
    files = SV.series_files() if files is None else files
    for name, strat, syms in rules:
        if name not in approved:
            continue
        for sym in syms:
            fpath = files.get(sym)
            if not fpath:
                out.append({"strategy": name, "sym": sym, "signal": None, "note": "no series"})
                continue
            try:
                bars = SV.load_csv(fpath)
                sig = int(strat(PointInTimeView(bars, len(bars) - 1), 0))
            except Exception as e:                                # noqa: BLE001
                out.append({"strategy": name, "sym": sym, "signal": None, "note": "%s" % type(e).__name__})
                continue
            item = {"strategy": name, "sym": sym, "signal": sig, "request": None}
            if sig > 0:
                r = request("buy", sym, max_order_usd(), "the rule %s reads +1 on the last bar" % name, strategy=name, path=path,
                            preconditions=preconditions, now=now, say=say, ask_log=ask_log, contact_state=contact_state)
                item["request"] = r.get("id")
            elif sig < 0:
                held = bought_under(name, sym, path)
                if held > 0 and sym not in HOLD_ONLY:
                    r = request("sell", sym, max_order_usd(), "the rule %s reads -1 on the last bar; selling what it bought" % name, strategy=name, path=path,
                                preconditions=preconditions, now=now, say=say, ask_log=ask_log, contact_state=contact_state)
                    r["qty_bought_under"] = held
                    item["request"] = r.get("id")
                else:
                    item["note"] = "nothing bought under this rule to sell" if held <= 0 else "%s is on the floor, never sold" % sym
            out.append(item)
    return out


def status(path=None, grant_path=None):
    rows = _rows(path)
    reqs = [r for r in rows if r.get("kind") == "request"]
    return {"grant": bool(grant(grant_path)), "requests": len(reqs), "asked": sum(1 for r in reqs if r.get("state", "").startswith("asked")),
            "placed_live": sum(1 for r in rows if r.get("kind") == "placed" and not r.get("dry_run")),
            "placed_dry": sum(1 for r in rows if r.get("kind") == "placed" and r.get("dry_run")),
            "his_no": sum(1 for r in rows if r.get("kind") == "no"), "not_placed": sum(1 for r in rows if r.get("kind") == "not_placed"),
            "gate_today": gate_reasons({"side": "buy", "usd": 5.0, "sym": "BTC"})[:6]}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Tetsu's permission in Coinbase: request (a straight question to him), settle (his yes + the trader's gate), status")
    ap.add_argument("--request", nargs=3, metavar=("SIDE", "SYM", "USD"))
    ap.add_argument("--why", default="")
    ap.add_argument("--settle", action="store_true", help="a DRY RUN unless --live")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.request:
        print(json.dumps(request(a.request[0], a.request[1], a.request[2], a.why), indent=1))
    elif a.settle:
        print(json.dumps(settle(dry_run=not a.live), indent=1))
    elif a.status:
        print(json.dumps(status(), indent=1))
    else:
        ap.print_help()
