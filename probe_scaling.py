"""SCALING PROBE -- what does a balance read cost as the ledger grows?

get_balance is a live SUM over an append-only table. That design was chosen
deliberately (no cached counter can drift). The question this probe asks is
what it COSTS, because the table only ever grows and balance reads sit in the
hot path of staking, gifting and every value-moving route.

H11: get_balance is O(total ledger rows), not O(rows for that account), so
     every node gets monotonically slower forever and never recovers.
H12: the only index is PARTIAL (WHERE ref_id != ''), so it cannot serve a
     plain pubkey lookup and SQLite falls back to a full scan.
"""
import os, sys, time, tempfile, shutil, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov

work = tempfile.mkdtemp(prefix="scale_")
db_path = os.path.join(work, "scale.db")
db = cov.Database(db_path)

PEM = "-----BEGIN PUBLIC KEY-----\nTARGET\n-----END PUBLIC KEY-----"
OTHER = "-----BEGIN PUBLIC KEY-----\nOTHER\n-----END PUBLIC KEY-----"

print("== query plan for get_balance ==")
with sqlite3.connect(db_path) as c:
    for row in c.execute(
            "EXPLAIN QUERY PLAN SELECT COALESCE(SUM(delta),0) "
            "FROM ledger_entries WHERE pubkey = ?", (PEM,)):
        print("  ", row[-1])

print("\n== growth curve ==")
db.record_ledger_entry(PEM, 1000.0, "genesis_mint", ref_id="seed")

def timed_read(n=200):
    t = time.time()
    for _ in range(n):
        db.get_balance(PEM)
    return (time.time() - t) / n * 1000.0

rows = 0
import sqlite3 as _s
with _s.connect(db_path) as _c:
    print("  indices:", [r[1] for r in _c.execute("PRAGMA index_list(ledger_entries)")])
print(f"  {'ledger rows':>12} | {'get_balance ms':>14} | {'target rows':>11}")
print("  " + "-" * 45)
baseline = None
for batch in range(8):
    ms = timed_read()
    if baseline is None:
        baseline = ms
    with sqlite3.connect(db_path) as c:
        tgt = c.execute("SELECT COUNT(*) FROM ledger_entries WHERE pubkey=?",
                        (PEM,)).fetchone()[0]
    print(f"  {rows:>12,} | {ms:>14.3f} | {tgt:>11,}")
    # Grow the table with entries belonging to OTHER accounts only. The target
    # account gains nothing; if reads slow down anyway, cost tracks TABLE size.
    with sqlite3.connect(db_path) as c:
        c.executemany(
            "INSERT INTO ledger_entries (pubkey, delta, reason, ref_id, timestamp) "
            "VALUES (?,?,?,?,?)",
            [(OTHER, 0.01, "noise", f"n{rows+i}", time.time()) for i in range(25000)])
    rows += 25000

final = timed_read()
print(f"  {rows:>12,} | {final:>14.3f} | (target account unchanged throughout)")
print(f"\n  slowdown for an account that gained ZERO new entries: "
      f"{final/baseline:.1f}x")
if final / baseline > 5:
    print("  *** CONFIRMED: balance-read cost tracks TOTAL ledger size, not the")
    print("      account's own history. Unbounded growth in the hot path.")

print("\n== does an index on pubkey fix it? ==")
with sqlite3.connect(db_path) as c:
    c.execute("CREATE INDEX IF NOT EXISTS idx_ledger_pubkey ON ledger_entries (pubkey)")
after = timed_read()
print(f"  before index: {final:.3f} ms")
print(f"  after  index: {after:.3f} ms   ({final/after:.0f}x faster)")
with sqlite3.connect(db_path) as c:
    for row in c.execute(
            "EXPLAIN QUERY PLAN SELECT COALESCE(SUM(delta),0) "
            "FROM ledger_entries WHERE pubkey = ?", (PEM,)):
        print("  new plan:", row[-1])

shutil.rmtree(work)
