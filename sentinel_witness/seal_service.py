#!/usr/bin/env python3
"""seal_service.py -- the local endpoint tradeGate.js seals through.

POST http://127.0.0.1:8433/seal  {"venue","symbol","side","amountUsd","note"}
  -> 200 {"ok": true,  "admission": "admitted", "detail": "...", "tx_id": "..."}
  -> 200 {"ok": false, "admission": "refused",  "detail": "..."}
  -> 4xx/5xx {"ok": false, "detail": "..."}   (also a refusal to the gate)

It signs a zero-amount self-send carrying the proposed order as its record
and submits it to the node exactly as covenant_trader.seal_decision does,
so the sentinel judges the decision and the ledger keeps it. It places no
order, holds no exchange credential, and binds to loopback only. A node
that cannot judge refuses, and that refusal is the answer; it is never
worked around here.

    python sentinel_witness/seal_service.py            # serve on 127.0.0.1:8433
    python test_sentinel_gate.py                        # its checks, no node needed
"""
from __future__ import annotations

import http.server
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

MAX_BODY = 8 * 1024
LISTEN = ("127.0.0.1", 8433)


def load_cfg():
    import covenant_trader as T
    return T.load_config() if hasattr(T, "load_config") else json.load(open(os.path.join(HERE, "trader_config.json"), encoding="utf-8"))


def seal(order, sealer=None, cfg=None):
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
            sealer = T.seal_decision
            cfg = cfg or load_cfg()
        ok, detail = sealer(cfg, record)
        detail = str(detail)
        admitted = bool(ok) and '"admitted"' in detail
        tx_id = None
        if admitted and '"tx_id": "' in detail:
            tx_id = detail.split('"tx_id": "', 1)[1].split('"', 1)[0]
        return 200, {"ok": admitted, "admission": "admitted" if admitted else "refused", "detail": detail[:300], "tx_id": tx_id}
    except Exception as e:                                        # noqa: BLE001 -- any failure refuses
        return 500, {"ok": False, "detail": "seal failed: %s: %s" % (type(e).__name__, str(e)[:200])}


def make_handler(sealer=None, cfg=None):
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
            code, body = seal(order, sealer, cfg)
            self._send(code, body)

        def do_GET(self):
            self._send(405, {"ok": False, "detail": "POST /seal only"})

    return H


def serve(listen=LISTEN, sealer=None, cfg=None, ready=None):
    srv = http.server.ThreadingHTTPServer(listen, make_handler(sealer, cfg))
    if ready:
        ready(srv)
    srv.serve_forever()


if __name__ == "__main__":
    print("seal service on http://%s:%d/seal  (loopback only; places no order)" % LISTEN)
    serve()
