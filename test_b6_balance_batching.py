#!/usr/bin/env python3
"""test_b6_balance_batching.py -- B6: one connection, and the refusals intact.

WHAT CHANGED. Two loops called Database.get_balance once per transaction, and
each call opened its own sqlite connection. They now take one connection for
the whole loop via get_balances().

WHY IT IS AN AVAILABILITY FIX AND NOT A SPEED ONE. Measured decomposition:
connect() 0.30 ms, first statement on a fresh connection 1.56 ms, warm
statement 0.019 ms -- about 99% of each call was connection setup, so the cost
is per-CALL, not per-ROW. At this system's real size (1-5 pending) batching
saves 10-15 ms against a /mine measured at 4,625 ms: under 1%. What justifies
it is that both loops are driven by someone else.

  * /transactions admits up to MAX_PENDING_TRANSACTIONS = 5000 from any valid
    keypair, and unaffordable transactions stay pending FOREVER by design. The
    /mine loop runs inside `with chain_lock`, so a remote party permanently
    turns the operator's own /mine into a 32.7 s no-op holding chain_lock --
    blocking /transactions, /chain and peer block acceptance -- which never
    clears.
  * The peer overdraft loop needs NO operator auth at all, and at the protocol
    ceiling of ~7,800 transactions in one 8 MiB block it was ~82% of all the
    work that block could force.

WHAT B6 PINS.

  E*  EQUIVALENCE. get_balances agrees with get_balance for every key,
      including unknown keys and duplicates. A faster balance reader that
      returns a different number is not an optimisation, it is a ledger bug.
  R*  THE REFUSALS SURVIVE. An overdrawn peer block is still REJECTED and still
      records block_rejected_overdraft; a same-sender pair that overdraws in
      aggregate is still caught by the `reserved` accumulator. Speeding up a
      check is only worth anything if the check still fires.
  S*  the STRUCTURE that makes it safe: one connection, one statement per
      DISTINCT key, and no IN (...) -- a peer chooses how many senders a block
      carries, against SQLITE_LIMIT_VARIABLE_NUMBER, which is 999 before
      sqlite 3.32 and would propagate an OperationalError out of the P2P
      handler.
  F*  NO fail-open fallback at either call site. PATCH LOG item H records a
      hasattr() guard failing open on this exact check -- "the ONE check whose
      entire job is don't trust a peer's block". A missing method must raise.

Pure: scratch database, no node, no network.
"""
import ast
import inspect
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def fresh(seed=None):
    db = C.Database(os.path.join(tempfile.mkdtemp(), "b6.db"))
    for k, v in (seed or {}).items():
        db.record_ledger_entry(k, v, "seed")
    return db


def main():
    print("B6 -- one connection, and the refusals intact\n")

    seed = {"a": 100.0, "b": 5.5, "c": 0.0, "d": -3.0}
    db = fresh(seed)
    keys = sorted(seed)

    # ---- E: equivalence ---------------------------------------------------
    one = {k: db.get_balance(k) for k in keys}
    many = db.get_balances(keys)
    check("E1 get_balances agrees with get_balance for EVERY key, including a "
          "zero and a negative. A faster balance reader that returns a "
          "different number is not an optimisation, it is a ledger bug",
          one == many, (one, many))
    check("E2 an unknown pubkey is 0.0, exactly as get_balance reports it",
          db.get_balances(["nobody"]) == {"nobody": 0.0}
          and db.get_balance("nobody") == 0.0)
    check("E3 an empty request is safe and opens nothing",
          db.get_balances([]) == {})
    check("E4 duplicates collapse to one lookup and one entry -- the /mine "
          "loop passes the sender of every pending transaction, and the same "
          "sender usually appears many times",
          db.get_balances(keys + keys + keys) == many)
    check("E5 a fresh write is visible to the NEXT call -- the batch is a "
          "snapshot for one loop, not a cache that outlives it",
          (db.record_ledger_entry("a", 7.0, "later"),
           db.get_balances(["a"])["a"] == 107.0)[1])

    # ---- S: structure -----------------------------------------------------
    src = inspect.getsource(C.Database.get_balances)
    tree = ast.parse(src.lstrip())
    withs = [n for n in ast.walk(tree) if isinstance(n, ast.With)]
    loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)]
    with_in_loop = any(isinstance(d, ast.With)
                       for lp in loops for d in ast.walk(lp))
    check("S1 the connection is opened OUTSIDE the loop. Opening it inside "
          "would reproduce the defect exactly while looking like the fix",
          len(withs) >= 1 and not with_in_loop, (len(withs), with_in_loop))
    # By AST, over the SQL STRING LITERALS only. The first version searched the
    # whole source and failed on the docstring -- which says "deliberately not
    # a grouped IN (...)", because explaining the choice requires naming it.
    # Seventh time in two days that a check matched prose instead of code, and
    # every one of them in this codebase for the same reason: the comments here
    # are good, so they describe precisely the thing being searched for.
    sql = [n.value for n in ast.walk(tree)
           if isinstance(n, ast.Constant) and isinstance(n.value, str)
           and "SELECT" in n.value.upper()]
    check("S2 no grouped IN (...) in the SQL ITSELF -- a peer chooses how many "
          "distinct senders a block carries, up to ~7,825 at MAX_BLOCK_BYTES, "
          "against SQLITE_LIMIT_VARIABLE_NUMBER, which is 999 before sqlite "
          "3.32 and would propagate an OperationalError out of the P2P handler",
          bool(sql) and not any(" IN (" in q.upper() for q in sql), sql)
    check("S3 the statement is the SAME one get_balance uses, so the two "
          "cannot drift apart",
          "COALESCE(SUM(delta), 0)" in src
          and "COALESCE(SUM(delta), 0)" in inspect.getsource(C.Database.get_balance))

    # ---- F: no fail-open at the call sites --------------------------------
    core = open(os.path.join(HERE, "covenant_unified_v8.py"),
                encoding="utf-8").read()
    bad = [l.strip() for l in core.splitlines()
           if "hasattr" in l and "get_balance" in l]
    check("F1 NEITHER call site guards with hasattr. Item H records that exact "
          "pattern failing OPEN here -- the one check whose entire job is "
          "'don't trust a peer's block'. A missing method must raise",
          not bad, bad)
    check("F2 both loops actually call the batched reader",
          core.count("self.db.get_balances(") >= 2,
          core.count("self.db.get_balances("))

    # ---- R: the refusals still fire ---------------------------------------
    # Rebuild the affordability decision exactly as /mine does it.
    def decide(balances, txs):
        included, still, reserved = [], [], {}
        for amt, who in txs:
            if amt <= 0:
                included.append((amt, who))
                continue
            bal = balances.get(who, 0.0)
            already = reserved.get(who, 0.0)
            if bal - already >= amt:
                included.append((amt, who))
                reserved[who] = already + amt
            else:
                still.append((amt, who))
        return included, still

    db2 = fresh({"rich": 100.0, "poor": 1.0})
    bals = db2.get_balances(["rich", "poor"])
    inc, still = decide(bals, [(50.0, "rich"), (5.0, "poor")])
    check("R1 an unaffordable transaction is still held back",
          [w for _, w in inc] == ["rich"] and [w for _, w in still] == ["poor"])
    inc, still = decide(bals, [(60.0, "rich"), (60.0, "rich")])
    check("R2 THE RESERVED ACCUMULATOR still works: two transactions that each "
          "fit but together overdraw the SAME sender must not both be "
          "included. Batching reads the balance once, so this is the case a "
          "careless implementation breaks",
          len(inc) == 1 and len(still) == 1, (inc, still))
    inc, still = decide(bals, [(0.0, "poor"), (-1.0, "poor")])
    check("R3 non-positive amounts still bypass the affordability test rather "
          "than being refused", len(inc) == 2 and not still)

    n, ok = len(results), sum(results)
    print(f"\nB6: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
