"""Salvage the invariant checks from the 1000-node run's surviving databases.

The simulation process was killed mid-apply, but the node databases are real
and on disk. Nodes that finished all 300 events are valid samples; nodes that
did not are partially-applied and are reported separately rather than being
quietly averaged in.

This is the actual point of the exercise: do independent nodes that applied
the same blocks agree, and is value conserved.
"""
import sqlite3, glob, os, sys, json, hashlib, collections

root = sorted(glob.glob("/tmp/sim1000_*"))[-1]
files = sorted(glob.glob(os.path.join(root, "n*.db")))
print(f"inspecting {len(files)} node databases in {root}\n")

complete, partial, broken = [], [], []
for f in files:
    try:
        c = sqlite3.connect(f)
        n = c.execute("SELECT COUNT(*) FROM applied_ledger_events").fetchone()[0]
        c.close()
        (complete if n >= 300 else partial).append(f)
    except Exception as e:
        broken.append((f, str(e)[:50]))

print(f"  fully applied (300 events): {len(complete)}")
print(f"  partially applied:          {len(partial)}")
print(f"  unreadable:                 {len(broken)}")

def balances(f):
    c = sqlite3.connect(f)
    rows = c.execute(
        "SELECT pubkey, COALESCE(SUM(delta),0) FROM ledger_entries GROUP BY pubkey"
    ).fetchall()
    c.close()
    return {k: round(v, 9) for k, v in rows}

def fp(b):
    return hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()

print("\n== I1: CONVERGENCE across fully-applied nodes ==")
states = collections.defaultdict(list)
for f in complete:
    states[fp(balances(f))].append(os.path.basename(f))
print(f"  distinct network states among {len(complete)} nodes: {len(states)}")
if len(states) == 1:
    print("  PASS: every fully-applied node computed identical balances "
          "for every account")
else:
    print("  FAIL: consensus divergence")
    for h, members in list(states.items())[:5]:
        print(f"    {h[:16]} -- {len(members)} nodes, e.g. {members[0]}")

ref = balances(complete[0])
print("\n== I2: CONSERVATION ==")
total = sum(ref.values())
minted = 40 * 1000.0
print(f"  accounts:      {len(ref)}")
print(f"  minted:        {minted:.6f}")
print(f"  present:       {total:.9f}")
print(f"  drift:         {total - minted:+.12f}")
print("  " + ("PASS: value moved, none created or destroyed"
               if abs(total - minted) < 1e-6 else "FAIL: supply drifted"))

neg = {k: v for k, v in ref.items() if v < -1e-9}
print(f"\n  accounts below zero: {len(neg)}")
print("  " + ("PASS: no account went negative" if not neg else f"FAIL: {list(neg.values())[:3]}"))

print("\n== I3: ORDER INDEPENDENCE ==")
# Nodes 0-499 received blocks in order; 500-999 received them shuffled, and
# every 7th node received 5 blocks TWICE.
in_order = [f for f in complete if int(os.path.basename(f)[1:5]) < 500]
shuffled = [f for f in complete if int(os.path.basename(f)[1:5]) >= 500]
dupes = [f for f in shuffled if int(os.path.basename(f)[1:5]) % 7 == 0]
print(f"  in-order nodes:  {len(in_order)}")
print(f"  shuffled nodes:  {len(shuffled)}  (of which {len(dupes)} also got duplicate blocks)")
if in_order and shuffled:
    a, b = fp(balances(in_order[0])), fp(balances(shuffled[0]))
    print(f"  in-order  fingerprint: {a[:32]}")
    print(f"  shuffled  fingerprint: {b[:32]}")
    print("  " + ("PASS: block arrival order does not affect final state"
                   if a == b else "FAIL: order-dependent state"))
if dupes:
    d = fp(balances(dupes[0]))
    print(f"  duplicate-delivery fingerprint: {d[:32]}")
    print("  " + ("PASS: duplicate block delivery applied nothing twice"
                   if d == fp(ref) else "FAIL: duplicates double-applied"))

print("\n== I4: partially-applied nodes are CONSISTENT, not corrupt ==")
if partial:
    ok = 0
    for f in partial[:60]:
        b = balances(f)
        c = sqlite3.connect(f)
        n = c.execute("SELECT COUNT(*) FROM applied_ledger_events").fetchone()[0]
        c.close()
        # A node stopped mid-chain must still conserve: each applied event is
        # net-zero and all-or-nothing, so the total must equal what was minted.
        if abs(sum(b.values()) - minted) < 1e-6:
            ok += 1
    print(f"  sampled {min(60,len(partial))} partially-applied nodes")
    print(f"  conserving supply despite being mid-chain: {ok}/{min(60,len(partial))}")
    print("  " + ("PASS: an interrupted node holds a valid, conserving ledger"
                   if ok == min(60, len(partial))
                   else "FAIL: interruption left a node with invented or lost value"))

print("\n== ledger size ==")
c = sqlite3.connect(complete[0])
rows = c.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0]
evts = c.execute("SELECT COUNT(*) FROM applied_ledger_events").fetchone()[0]
c.close()
print(f"  per node: {rows} ledger rows, {evts} applied events")
print(f"  network total applied: ~{rows * len(complete):,} ledger rows")
