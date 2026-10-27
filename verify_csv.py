"""Contiguity verifier for realdata/deep/*.csv (M1). Exit non-zero on any defect."""
import csv, sys, datetime as dt

def verify(path):
    rows = list(csv.DictReader(open(path, newline="")))
    bad = []
    assert rows, "empty"
    hdr = list(rows[0].keys())
    if hdr != ["timestamp","date","open","high","low","close","vwap","volume","count"]:
        bad.append(f"header {hdr}")
    prev = None
    seen = set()
    for i, r in enumerate(rows):
        ts = int(r["timestamp"])
        if ts in seen: bad.append(f"dup ts {ts}")
        seen.add(ts)
        if ts % 86400: bad.append(f"row {i} not 00:00 UTC: {ts}")
        d = dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%Y-%m-%d")
        if d != r["date"]: bad.append(f"row {i} date mismatch {d} vs {r['date']}")
        if prev is not None and ts - prev != 86400: bad.append(f"gap at row {i}: {ts-prev}s")
        prev = ts
        o,h,l,c,v = (float(r[k]) for k in ("open","high","low","close","vwap"))
        if not (0 < l <= min(o,c) and max(o,c) <= h): bad.append(f"row {i} OHLC sanity {o},{h},{l},{c}")
        if not (l <= v <= h): bad.append(f"row {i} vwap {v} outside [{l},{h}]")
        if float(r["volume"]) < 0 or int(r["count"]) < 0: bad.append(f"row {i} neg vol/count")
    print(f"{path}: {len(rows)} rows {rows[0]['date']} -> {rows[-1]['date']}; defects: {len(bad)}")
    for b in bad[:20]: print("  ", b)
    return not bad

ok = all(verify(p) for p in sys.argv[1:])
sys.exit(0 if ok else 1)
