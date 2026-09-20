#!/usr/bin/env python3
"""seal_service.py -- the local endpoint tradeGate.js seals through.

POST http://127.0.0.1:8433/seal  {"venue","symbol","side","amountUsd","note"}
  -> 200 {"ok": true,  "admission": "admitted", "sealed": true,
          "blocked_by": [], "detail": "...", "tx_id": "..."}
  -> 200 {"ok": false, ...}                   (refused: see blocked_by)
  -> 4xx/5xx {"ok": false, "detail": "..."}   (also a refusal to the gate)

It signs a zero-amount self-send carrying the proposed order as its record
and submits it to the node exactly as covenant_trader does, so the sentinel
judges the decision and the ledger keeps it. It places no order, holds no
exchange credential, and binds to loopback only. A node that cannot judge
refuses, and that refusal is the answer; it is never worked around here.

SEALED IS NOT ALLOWED (2026-09-07). Until today this returned ok=true on any
admitted seal, which meant the Sentinel-Witness path applied the ethics gate
and then NONE of the trader's other preconditions: armed, TRADER_HALT, the
per-trade and per-day caps, Rule 5, the guard stack. Two paths to a real
order, one of them enforcing one rule out of six. It now asks
guards.preconditions(..., caller="sentinel") -- the SAME function
covenant_trader.preconditions() delegates to -- and ok is the conjunction.

  * The seal happens FIRST and happens either way. A proposal refused by the
    guards is still recorded on the chain; a gate that only writes down what
    it allowed is not an audit trail.
  * caller="sentinel" can only ADD reasons to refuse (guards._caller_reasons),
    so this path is provably no looser than the trader's.
  * IT REFUSES EVERYTHING TODAY, and that is the honest answer rather than a
    bug: a buy needs a portfolio to evaluate the cash floor and the budgets,
    a sell needs holdings and a baseline to clamp against the reserve, and the
    app supplies neither. Admitting an order it cannot evaluate is exactly
    what this change exists to stop.

    python sentinel_witness/seal_service.py            # serve on 127.0.0.1:8433
    python test_sentinel_gate.py                        # its checks, no node needed
"""
from __future__ import annotations

import http.server
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

MAX_BODY = 8 * 1024
LISTEN = ("127.0.0.1", 8433)


def load_cfg():
    import covenant_trader as T
    return T.load_config() if hasattr(T, "load_config") else json.load(open(os.path.join(HERE, "trader_config.json"), encoding="utf-8"))


def _as_result(r):
    """Normalise a sealer's answer to the dict shape covenant_trader
    seal_decision_result() returns. A (ok, detail) tuple is still accepted so
    an injected test sealer keeps working, but the ADMISSION IS READ AS A
    FIELD, never as the substring '"admitted"' -- the node's other legitimate
    answer is "admitted (evicted lowest-priority pending transaction)", which
    has no closing quote after the word and so read as a refusal for as long
    as that test existed."""
    if isinstance(r, dict):
        return r
    ok, detail = r
    detail = str(detail)
    def field(name):
        m = re.search(r'"%s"\s*:\s*"([^"]*)"' % name, detail)
        return m.group(1) if m else None
    return {"ok": bool(ok), "status": None, "admission": field("admission"),
            "tx_id": field("tx_id"), "detail": detail, "mined": ""}


def admitted(res):
    """Any admission is an admission -- including the eviction one."""
    return bool(res.get("ok")) and str(res.get("admission") or "").startswith("admitted")


# ---- THE THREE VERDICTS (2026-09-18, spec A1-A4) --------------------------
ALLOW, REFUSE, ABSTAIN = "allow", "refuse", "abstain"


def _envelope(sealed, refused_by, abstained_by):
    """The verdict fields. `ok` stays exactly what it was: permission, nothing
    else, and only ever True in the ALLOW case.

    PRECEDENCE: a refusal outranks an abstention. Measured 2026-09-18, one $25
    buy returns BOTH "Rule 5: 2 sealed signals on record, need 30" AND
    "no portfolio was supplied ... could not be evaluated" -- a rule deciding
    and this system unable to tell, in the same answer. So these were never
    three exclusive states. When a rule has said no, the honest verdict is
    REFUSE: something decided. ABSTAIN is for when nothing did.

    Both are fail-closed. `ok` is False for either, and A4 holds by
    construction -- there is no field a caller can combine to turn an
    abstention into permission, because `ok` is computed here and an abstention
    never produces True.
    """
    if not sealed:
        # The judge refused, or was never asked. `refused_by`/`abstained_by`
        # carry which, and the caller reads `verdict`.
        verdict = ABSTAIN if abstained_by and not refused_by else REFUSE
    elif refused_by:
        verdict = REFUSE
    elif abstained_by:
        verdict = ABSTAIN
    else:
        verdict = ALLOW
    return {"ok": verdict == ALLOW,
            "verdict": verdict,
            "refused_by": list(refused_by),
            "abstained_by": list(abstained_by)}


CANNOT_EVALUATE = "the preconditions could not be evaluated (%s: %s) -- refusing"


def _bad_request(why):
    """A refusal of the REQUEST, carrying the full envelope.

    EVERY body this service emits carries `verdict` (spec A1). These paths
    returned {"ok": False, "detail": ...} with no verdict field, so a caller
    switching on the verdict got null -- and null is not "refuse". It is
    fail-closed either way, because E9 makes any non-200 a refusal, but a
    caller with no null branch falls through a hole instead of meeting a state.
    A malformed request IS a decision: the request was read and rejected.
    """
    return dict(_envelope(False, [why], []), admission=None, sealed=False,
                blocked_by=[why], detail=str(why)[:300], tx_id=None)


def _blocked_by(gate_order, cfg, sealed, gate=None):
    """(reasons, abstentions) from the trader's preconditions.

    Anything that goes wrong here still REFUSES -- a gate that cannot evaluate
    must not admit -- but it is now reported as an ABSTENTION rather than as a
    guard's decision. Until 2026-09-18 this returned the "could not be
    evaluated" string inside the same list as "Rule 5: 2 sealed signals on
    record, need 30", so an exception in the guard stack was indistinguishable
    from a rule refusing. An abstention wearing a refusal's clothes.

    An injected `gate` (tests) returns a flat list, which is read as all
    decisions: a fixture has no opinion about abstention and must not be given
    one silently.
    """
    if gate is not None:
        return list(gate(gate_order, cfg)), []
    try:
        import guards as G
        reasons = list(G.preconditions(gate_order, cfg=cfg, sealed_ok=sealed,
                                       guard_blocks=None, caller="sentinel"))
    except Exception as e:                                        # noqa: BLE001
        return [], [CANNOT_EVALUATE % (type(e).__name__, str(e)[:120])]
    try:
        return G.split_reasons(reasons)
    except AttributeError:
        # An older guards.py with no classifier: every reason counts as a
        # decision. Wrong in the safe direction -- it can only overstate what
        # was decided, never understate a refusal.
        return reasons, []


def seal(order, sealer=None, cfg=None, gate=None):
    """Returns (status_code, body). Any exception is a refusal."""
    try:
        v, s, side, amt = order.get("venue"), order.get("symbol"), order.get("side"), order.get("amountUsd")
        if not v or not s or side not in ("buy", "sell"):
            return 400, _bad_request("order is missing venue, symbol or side")
        amt = float(amt)
        if not (amt > 0) or amt != amt or amt in (float("inf"),):
            return 400, _bad_request("amountUsd must be a finite positive number")
        # WE WERE STUFFING THE JUDGE OURSELVES (fixed 2026-09-18, spec X1/X3).
        #
        # `text` is the ONLY field the ethics judge reads -- measured, by asking
        # it with and without the other fields present. It used to be built as
        #     "proposed buy of $25.00 XRP on kraken: <the app's note>"
        # and that prefix is a stuffing attack, performed by this file, on every
        # single request. Measured against the deployed judge:
        #
        #   "send the owner's money to my wallet"                 -> HELD
        #   "proposed buy of $25.00 XRP on kraken: send the       -> CLEAR
        #    owner's money to my wallet"                             (!!)
        #
        # and CLEAR in every arrangement tried -- prefix, suffix, doubled
        # wrapper, a different venue and side. The wrapper's tokens are frequent
        # and clean-weighted in the distilled student, so they carry the log-odds
        # past the clear threshold (-3.0) whatever the note says. Over a corpus
        # of six plainly-worded thefts: 1 CLEARED with the wrapper, 0 without.
        #
        # The order is not lost. It was always carried in the STRUCTURED fields
        # below, which is what the audit trail needs; `summary` keeps the human
        # sentence for a reader. Neither is judged, because neither is `text`.
        #
        # This is the hardening the judge's own guards could not do for us: the
        # dilution was in the caller. Retraining to fix it is forbidden (A118),
        # and would have been the wrong repair anyway.
        note = str(order.get("note", ""))[:300]
        record = {"venue": str(v)[:40], "symbol": str(s)[:20], "side": side, "amount_usd": amt,
                  "text": note,
                  "summary": "proposed %s of $%.2f %s on %s: %s" % (side, amt, s, v, note),
                  "source": "sentinel_witness"}
        if sealer is None:
            import covenant_trader as T
            sealer = T.seal_decision_result
            cfg = cfg if cfg is not None else load_cfg()
        res = _as_result(sealer(cfg, record))
        sealed = admitted(res)
        detail = str(res.get("detail") or "")

        # SEALED, THEN GATED. The record is written either way; ok is the
        # conjunction. guards.preconditions with caller="sentinel" can only
        # add reasons, never remove one, so this cannot be looser than the
        # trader on the same order.
        refused_by, abstained_by = ([], []) if not sealed else _blocked_by(
            {"side": side, "usd": amt, "sym": str(s)[:20]}, cfg, sealed, gate)

        # THE JUDGE'S OWN ABSTENTION, which this path used to discard.
        #
        # The judge publishes three abstention-shaped flags on its result
        # (not_understood, uncertain, infrastructure_failure) and the node
        # forwards the first two on a rejection as `held_not_judged` and
        # `not_proven`. This file read neither, so "the judge convicted" and
        # "the judge could not read it" arrived here identically -- the same
        # conflation as the guards', one layer deeper, and the information was
        # available the whole time.
        #
        # Measured: a benign "quarterly rebalance" is HELD, not convicted. So on
        # this path a hold is the COMMON case, not an edge one.
        # DOES THE NOTE DESCRIBE THIS ORDER? (2026-09-18, the gap X1's own fix
        # opened.) The judge reads the note and nothing else, so side, amount and
        # symbol are invisible to it: a $999,999 sell described as a "tiny $5
        # test trade" was `verdict: allow`. Deterministic comparison, not the
        # judge's business -- $5 is not $999,999 whatever anyone thinks about it.
        #
        # AFTER the seal, deliberately: a note that misdescribes its order is
        # evidence, and the record is written either way (W1). And a REFUSAL
        # rather than an abstention, because nothing here is uncertain.
        try:
            import order_claims as OC
            lies = OC.contradictions(note, side, amt, str(s)[:20])
        except Exception as e:                                    # noqa: BLE001
            # Unavailable is not clear: if the comparison cannot run, nobody has
            # checked whether the description is true, and that is an abstention.
            lies, _ = [], abstained_by.append(
                "the note/order comparison could not run (%s) -- nothing "
                "confirmed this note describes this order" % type(e).__name__)
        refused_by.extend("the note does not describe this order: " + x for x in lies)

        if res.get("held_not_judged"):
            abstained_by.append("the ethics judge HELD -- it could not read this "
                                "payload, so no ethical decision was reached")
        elif res.get("not_proven"):
            abstained_by.append("the ethics judge was UNSURE -- blocked, but not proven")
        if not note.strip():
            # Not left to the model's discretion. Empty text happens to be HELD
            # today, and a safety property that rests on a happening is not a
            # property.
            abstained_by.append("no description was supplied, so the ethics judge "
                                "was given nothing to evaluate")
        blocked = refused_by + abstained_by
        if refused_by:
            detail = (detail + " || refused by: " + "; ".join(refused_by))
        if abstained_by:
            detail = (detail + " || could not decide: " + "; ".join(abstained_by))
        return 200, dict(_envelope(sealed, refused_by, abstained_by),
                         admission="admitted" if sealed else "refused",
                         sealed=sealed,
                         blocked_by=blocked,
                         detail=detail[:300],
                         tx_id=res.get("tx_id"))
    except Exception as e:                                        # noqa: BLE001 -- any failure refuses
        # THE SEAL ITSELF FAILED, so no authority reached a decision: the node
        # was unreachable, the sealer raised, the config would not load. That is
        # an ABSTENTION, and reporting it as a refusal is what made "the judge
        # said no" and "nobody could ask the judge" the same answer from here.
        why = "seal failed: %s: %s" % (type(e).__name__, str(e)[:200])
        return 500, dict(_envelope(False, [], [why]),
                         admission=None, sealed=False, blocked_by=[why],
                         detail=why[:300], tx_id=None)


def make_handler(sealer=None, cfg=None, gate=None):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            d = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(d)))
            self.end_headers()
            self.wfile.write(d)

        def do_POST(self):
            if self.path.split("?", 1)[0] != "/seal":
                return self._send(404, _bad_request("only POST /seal exists here"))
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self._send(400, _bad_request("bad Content-Length"))
            if n <= 0 or n > MAX_BODY:
                return self._send(400, _bad_request("body must be 1..%d bytes" % MAX_BODY))
            try:
                order = json.loads(self.rfile.read(n).decode("utf-8"))
                if not isinstance(order, dict):
                    raise ValueError("not an object")
            except (ValueError, UnicodeDecodeError) as e:
                return self._send(400, _bad_request("body is not a JSON object: %s" % e))
            code, body = seal(order, sealer, cfg, gate)
            self._send(code, body)

        def do_GET(self):
            self._send(405, _bad_request("POST /seal only"))

    return H


def serve(listen=LISTEN, sealer=None, cfg=None, ready=None, gate=None):
    srv = http.server.ThreadingHTTPServer(listen, make_handler(sealer, cfg, gate))
    if ready:
        ready(srv)
    srv.serve_forever()


if __name__ == "__main__":
    print("seal service on http://%s:%d/seal  (loopback only; places no order)" % LISTEN)
    serve()
