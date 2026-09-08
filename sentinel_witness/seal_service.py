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


def _blocked_by(gate_order, cfg, sealed, gate=None):
    """The trader's preconditions, asked of this proposal. Anything that goes
    wrong here REFUSES; a gate that cannot evaluate must not admit."""
    if gate is not None:
        return list(gate(gate_order, cfg))
    try:
        import guards as G
        return list(G.preconditions(gate_order, cfg=cfg, sealed_ok=sealed,
                                    guard_blocks=None, caller="sentinel"))
    except Exception as e:                                        # noqa: BLE001
        return ["the preconditions could not be evaluated (%s: %s) -- refusing"
                % (type(e).__name__, str(e)[:120])]


def seal(order, sealer=None, cfg=None, gate=None):
    """Returns (status_code, body). Any exception is a refusal."""
    try:
        v, s, side, amt = order.get("venue"), order.get("symbol"), order.get("side"), order.get("amountUsd")
        if not v or not s or side not in ("buy", "sell"):
            return 400, {"ok": False, "detail": "order is missing venue, symbol or side"}
        amt = float(amt)
        if not (amt > 0) or amt != amt or amt in (float("inf"),):
            return 400, {"ok": False, "detail": "amountUsd must be a finite positive number"}
        record = {"venue": str(v)[:40], "symbol": str(s)[:20], "side": side, "amount_usd": amt,
                  "text": "proposed %s of $%.2f %s on %s: %s" % (side, amt, s, v, str(order.get("note", ""))[:300]),
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
        blocked = [] if not sealed else _blocked_by(
            {"side": side, "usd": amt, "sym": str(s)[:20]}, cfg, sealed, gate)
        if blocked:
            detail = (detail + " || refused by: " + "; ".join(blocked))
        return 200, {"ok": sealed and not blocked,
                     "admission": "admitted" if sealed else "refused",
                     "sealed": sealed,
                     "blocked_by": blocked,
                     "detail": detail[:300],
                     "tx_id": res.get("tx_id")}
    except Exception as e:                                        # noqa: BLE001 -- any failure refuses
        return 500, {"ok": False, "detail": "seal failed: %s: %s" % (type(e).__name__, str(e)[:200])}


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
                return self._send(404, {"ok": False, "detail": "only POST /seal exists here"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self._send(400, {"ok": False, "detail": "bad Content-Length"})
            if n <= 0 or n > MAX_BODY:
                return self._send(400, {"ok": False, "detail": "body must be 1..%d bytes" % MAX_BODY})
            try:
                order = json.loads(self.rfile.read(n).decode("utf-8"))
                if not isinstance(order, dict):
                    raise ValueError("not an object")
            except (ValueError, UnicodeDecodeError) as e:
                return self._send(400, {"ok": False, "detail": "body is not a JSON object: %s" % e})
            code, body = seal(order, sealer, cfg, gate)
            self._send(code, body)

        def do_GET(self):
            self._send(405, {"ok": False, "detail": "POST /seal only"})

    return H


def serve(listen=LISTEN, sealer=None, cfg=None, ready=None, gate=None):
    srv = http.server.ThreadingHTTPServer(listen, make_handler(sealer, cfg, gate))
    if ready:
        ready(srv)
    srv.serve_forever()


if __name__ == "__main__":
    print("seal service on http://%s:%d/seal  (loopback only; places no order)" % LISTEN)
    serve()
