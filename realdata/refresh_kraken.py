#!/usr/bin/env python3
"""realdata/refresh_kraken.py -- extend the verified daily series in realdata/deep/
to today, with the same checks the originals passed, and never silently.

WHY (2026-09-03). The deep series end 2026-08-21. A strategy validated on data
that stops two weeks ago is validated on a different market than the one it
would trade. Before any walk-forward result is quoted again the series must
reach the last SETTLED daily bar -- and the in-progress candle must be
dropped, as REAL_DATA_FINDINGS.md did by hand.

WHAT IT DOES
  For each file in realdata/deep matching <SYMBOL>_*.csv (timestamp,open,high,
  low,close,volume; 00:00 UTC daily), fetch Kraken's public OHLC (interval
  1440, the last ~720 bars), then:
    1. OVERLAP CHECK: every bar the file already has must agree with the fresh
       fetch to 0.5% on close (Kraken vs Kraken should agree exactly; a
       disagreement means the pair symbol is wrong or the file is not Kraken's);
    2. CONTIGUITY: appended bars must be exactly 86 400 s apart from the last;
    3. OHLC SANITY: low <= open,close <= high, all > 0;
    4. the newest bar is the in-progress candle when its timestamp is today's
       00:00 UTC: it is DROPPED, and the report says so.
  Then the extended file is written IN PLACE and a line goes to
  realdata/deep/REFRESH_LOG.md with bars added, the window, and sha256 before
  and after. Nothing is written when any check fails: the report names the
  failure and the file is left as it was.

USE
  python realdata/refresh_kraken.py            # all deep series
  python realdata/refresh_kraken.py XRP HBAR   # some
  python realdata/refresh_kraken.py --check    # fetch and compare, write nothing
LICENCE: public domain.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEEP = os.path.join(HERE, "deep")
LOG = os.path.join(DEEP, "REFRESH_LOG.md")
DAY = 86400
# Kraken pair names for the symbols the deep folder holds.
PAIRS = {"XRP": "XXRPZUSD", "XLM": "XXLMZUSD", "SOL": "SOLUSD", "ADA": "ADAUSD", "ATOM": "ATOMUSD",
         "AVAX": "AVAXUSD", "NEAR": "NEARUSD", "ONDO": "ONDOUSD", "PEPE": "PEPEUSD", "CRO": "CROUSD",
         "HBAR": "HBARUSD", "WLFI": "WLFIUSD"}


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


COLS = ["timestamp", "date", "open", "high", "low", "close", "vwap", "volume", "count"]


def read_series(path):
    """Rows as dicts keyed by the file's own header (the deep files carry
    timestamp,date,open,high,low,close,vwap,volume,count)."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        head = fh.readline().strip().lower().split(",")
        for line in fh:
            p = line.strip().split(",")
            if len(p) < len(head):
                continue
            d = dict(zip(head, p))
            d["timestamp"] = int(float(d["timestamp"]))
            for k in ("open", "high", "low", "close"):
                d[k] = float(d[k])
            rows.append(d)
    return head, rows


def fetch(pair):
    url = "https://api.kraken.com/0/public/OHLC?pair=%s&interval=1440" % pair
    req = urllib.request.Request(url, headers={"User-Agent": "covenant-refresh/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    if d.get("error"):
        raise RuntimeError("kraken: %s" % d["error"])
    res = d["result"]
    key = [k for k in res if k != "last"][0]
    out = []
    for row in res[key]:
        t, o, h, l, c, vw, v, n = row[:8]
        out.append({"timestamp": int(t), "date": time.strftime("%Y-%m-%d", time.gmtime(int(t))),
                    "open": float(o), "high": float(h), "low": float(l), "close": float(c),
                    "vwap": vw, "volume": v, "count": n})
    return out


def refresh(path, check_only, say=print):
    sym = os.path.basename(path).split("_")[0]
    pair = PAIRS.get(sym)
    if not pair:
        say("  %-5s SKIP no Kraken pair known" % sym); return None
    head, rows = read_series(path)
    fresh = fetch(pair)
    today0 = int(time.time()) // DAY * DAY
    fresh_by_t = {r["timestamp"]: r for r in fresh}
    # 1. overlap
    overlap = [r for r in rows if r["timestamp"] in fresh_by_t]
    bad = [(r["timestamp"], r["close"], fresh_by_t[r["timestamp"]]["close"]) for r in overlap
           if abs(r["close"] - fresh_by_t[r["timestamp"]]["close"]) > 0.005 * max(r["close"], 1e-12)]
    if bad:
        say("  %-5s FAIL overlap: %d of %d bars disagree with Kraken by >0.5%% (first %s)" % (sym, len(bad), len(overlap), bad[0]))
        return {"symbol": sym, "ok": False, "why": "overlap"}
    last_t = rows[-1]["timestamp"]
    add = [r for r in fresh if r["timestamp"] > last_t]
    dropped = 0
    if add and add[-1]["timestamp"] >= today0:
        add = add[:-1]; dropped = 1
    # 2/3. contiguity and sanity
    t = last_t
    for r in add:
        if r["timestamp"] != t + DAY:
            say("  %-5s FAIL contiguity: gap %ds before %d" % (sym, r["timestamp"] - t, r["timestamp"])); return {"symbol": sym, "ok": False, "why": "gap"}
        if not (0 < r["low"] <= min(r["open"], r["close"]) and max(r["open"], r["close"]) <= r["high"]):
            say("  %-5s FAIL sanity at %d: %s" % (sym, r["timestamp"], [r[k] for k in ("open", "high", "low", "close")])); return {"symbol": sym, "ok": False, "why": "sanity"}
        t = r["timestamp"]
    window = "%s -> %s" % (time.strftime("%Y-%m-%d", time.gmtime(rows[0]["timestamp"])), time.strftime("%Y-%m-%d", time.gmtime(t)))
    say("  %-5s overlap %d/%d agree; +%d bars; in-progress candle dropped: %d; window %s%s"
        % (sym, len(overlap), len(overlap), len(add), dropped, window, "  (check only)" if check_only else ""))
    if check_only or not add:
        return {"symbol": sym, "ok": True, "added": len(add), "written": False}
    before = sha(path)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        for r in add:
            fh.write(",".join(str(r.get(k, "")) for k in head) + "\n")
    after = sha(path)
    with open(LOG, "a", encoding="utf-8") as fh:
        if fh.tell() == 0:
            fh.write("# realdata/deep refresh log -- Kraken daily, appended by realdata/refresh_kraken.py; sha256 prefixes before -> after\n\n")
        fh.write("- %s %s: +%d bars (overlap %d agree, in-progress dropped %d) window %s; sha %s -> %s\n"
                 % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), os.path.basename(path), len(add), len(overlap), dropped, window, before, after))
    return {"symbol": sym, "ok": True, "added": len(add), "written": True, "window": window}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    files = sorted(glob.glob(os.path.join(DEEP, "*_20*.csv")))
    if args:
        files = [f for f in files if os.path.basename(f).split("_")[0] in args]
    # one series per symbol: the file with the most bars
    best = {}
    for f in files:
        s = os.path.basename(f).split("_")[0]
        n = sum(1 for _ in open(f, encoding="utf-8"))
        if s not in best or n > best[s][1]:
            best[s] = (f, n)
    results = []
    for s, (f, n) in sorted(best.items()):
        try:
            results.append(refresh(f, check_only))
        except Exception as e:                                       # noqa: BLE001
            print("  %-5s ERROR %s: %s" % (s, type(e).__name__, e)); results.append({"symbol": s, "ok": False, "why": str(e)})
        time.sleep(1.2)                                              # Kraken's public rate limit
    ok = [r for r in results if r and r.get("ok")]
    print("%d/%d series ok%s" % (len(ok), len([r for r in results if r]), "" if check_only else "; log: " + LOG))
    return 0 if len(ok) == len([r for r in results if r]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
