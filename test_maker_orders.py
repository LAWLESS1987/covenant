#!/usr/bin/env python3
"""
test_maker_orders.py -- the Coinbase order body, offline.

Pins what the pre-push audits of 2026-09-06 found on the live-money path:
prices and sizes on the venue grid exactly (Decimal, not float truncation),
a maker order that expires instead of resting for ever, an explicit market
order that really takes, a client_order_id that repeats for a retry and is
absent from a preview, and a lost answer that is a VenueError rather than a
crash. No network: the venue's meta, book and transport are stubbed.

Run:  python test_maker_orders.py
"""
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import venues as V          # noqa: E402

FAILS = []


def check(cond, label):
    print(("ok    " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


class Stub(V.CoinbaseVenue):
    def __init__(self, bid=12.2534, ask=12.2536):
        super().__init__()
        self.bid, self.ask = bid, ask
        self.sent = []

    def meta(self, symbol):
        return {"product_id": f"{symbol}-USD", "base_increment": "0.00000001",
                "quote_increment": "0.001", "base_min_size": 0.00001}

    def best_bid_ask(self, product_id):
        return self.bid, self.ask

    def _call(self, method, path, body=None):
        self.sent.append((path, body))
        return {"success": True, "success_response": {"order_id": "oid-1"}}


snap = V.CoinbaseVenue._snap
check(snap(1.15, "0.01", "BUY") == "1.15" and snap(1.15, "0.01", "SELL") == "1.15",
      "S1 an on-grid price is unchanged either way (float truncation made 1.15 -> 1.14)")
check(snap(12.2534, "0.001", "BUY") == "12.253" and snap(12.2536, "0.001", "SELL") == "12.254",
      "S2 buys round down to the grid, sells round up")
check(snap(105.5, "1", "BUY") == "105" and snap(105.5, "1", "SELL") == "106",
      "S3 a whole-unit grid formats without a decimal point or exponent")
check(snap(0.00004567, "0.00000001", "BUY") == "0.00004567",
      "S4 a tiny size formats in full, never as 4.567e-05")

v = Stub()
v.place("LINK", "buy", 0.5, live=False)
path, body = v.sent[-1]
cfg = body["order_configuration"]
check(path.endswith("/orders/preview") and "client_order_id" not in body,
      "P1 a preview carries no client_order_id (Coinbase rejects it there)")
check("limit_limit_gtd" in cfg and cfg["limit_limit_gtd"]["post_only"] is True,
      "P2 the default order is a post-only good-till-date limit, not GTC and not market")
check(cfg["limit_limit_gtd"]["limit_price"] == "12.253" and cfg["limit_limit_gtd"]["base_size"] == "0.5",
      "P3 a default buy sits at the bid, snapped down; size is a plain decimal string")
check(cfg["limit_limit_gtd"]["end_time"].endswith("Z") and "T" in cfg["limit_limit_gtd"]["end_time"],
      "P4 end_time is RFC 3339 UTC")

v.place("LINK", "sell", 0.5, live=False)
check(v.sent[-1][1]["order_configuration"]["limit_limit_gtd"]["limit_price"] == "12.254",
      "P5 a default sell sits at the ask, snapped up (never below the ask, which post-only would reject)")

v.place("LINK", "buy", 0.5, live=False, ordertype="market")
check("market_market_ioc" in v.sent[-1][1]["order_configuration"],
      "P6 ordertype='market' really takes -- the maker default no longer swallows it")

r1 = v.place("LINK", "buy", 0.5, live=True, day="2026-09-06")
id1 = v.sent[-1][1]["client_order_id"]
r2 = v.place("LINK", "buy", 0.5, live=True, day="2026-09-06")
id2 = v.sent[-1][1]["client_order_id"]
v.place("LINK", "buy", 0.5, live=True, day="2026-09-07")
id3 = v.sent[-1][1]["client_order_id"]
check(v.sent[-1][0].endswith("/orders") and id1 == id2 and id1 != id3 and r1["txid"] == "oid-1",
      "L1 a live retry of the same order on the same day reuses its client_order_id; a new day gets a new one")


class Hang:
    def __enter__(self):
        raise TimeoutError("The read operation timed out")

    def __exit__(self, *a):
        return False


orig = urllib.request.urlopen
urllib.request.urlopen = lambda *a, **k: Hang()
try:
    try:
        V._http(urllib.request.Request("https://api.coinbase.com/x"), timeout=1)
        got = None
    except V.VenueError as e:
        got = str(e)
    except Exception as e:                                       # noqa: BLE001
        got = type(e)
finally:
    urllib.request.urlopen = orig
check(isinstance(got, str) and got.startswith("no response"),
      "H1 a read timeout after the request was sent is a VenueError ('no response'), not a bare TimeoutError")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("MAKER ORDERS: all passed")
