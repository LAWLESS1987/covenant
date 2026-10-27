"""Salvage the invariant checks from the 1000-node run's surviving databases.

The simulation process was killed mid-apply, but the node databases are real
and on disk. Nodes that finished all 300 events are valid samples; nodes that
did not are partially-applied and are reported separately rather than being
quietly averaged in.

This is the actual point of the exercise: do independent nodes that applied
the same blocks agree, and is value conserved.
"""
import sqlite3, glob, os, sys, json, hashlib, collections, tempfile

# The scratch dir is wherever sim1000_network.py put it, and that file uses
# `tempfile.mkdtemp(prefix="sim1000_")` -- which is /tmp on Linux and
# %TEMP% on Windows. This line said "/tmp" until 2026-08-27, so on the
# machine that actually runs this project it could only ever raise
# IndexError from a bare `[-1]`, with no hint of what was being looked for.
# A salvage tool that cannot say "there is nothing to salvage" is one more
# thing to debug at the moment you least want to.
SCRATCH = os.environ.get("SIM1000_DIR") or tempfile.gettempdir()
# Directories only: the prefix also matches loose files (a backup named
# sim1000_invariants.py.bak was picked as the "run" the first time this
# ran on Windows, and the report that followed was about an empty set).
runs = sorted(d for d in glob.glob(os.path.join(SCRATCH, "sim1000_*"))
              if os.path.isdir(d))
if not runs:
    print(f"no sim1000_* run directory under {SCRATCH}.\n"
          f"This script inspects the databases a run LEAVES BEHIND; it does "
          f"not create them. Run sim1000_network.py first, or point "
          f"SIM1000_DIR at the scratch dir of a run that has already "
          f"happened.")
    raise SystemExit(2)
root = runs[-1]
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
# NOTHING TO COMPARE IS NOT A DIVERGENCE (added 2026-08-27). With zero
# fully-applied nodes `len(states)` is 0, which fell into the else branch and
# printed "FAIL: consensus divergence" -- a consensus break reported over an
# empty directory -- and then died on `complete[0]` two lines later. UNKNOWN is
# never a PASS here, and it is never a FAIL either.
if not complete:
    print("  UNKNOWN: no fully-applied node database in this run directory, "
          "so there is nothing to compare. This is not a divergence and not a "
          "pass -- it means the simulation did not leave usable output.")
    raise SystemExit(2)
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
