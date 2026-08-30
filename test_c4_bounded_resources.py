#!/usr/bin/env python3
"""test_c4_bounded_resources.py -- C4: nothing a stranger can reach may grow
without a bound.

THREE DEFECTS, ONE SHAPE. Found by an adversarial review pass on 2026-08-30 and
confirmed by measurement before any of them was touched. Every one is reachable
without authentication, and every one is unbounded in something a caller
controls.

  C1  POST /succession/register accepted 5,000 guardians and returned 200 OK
      after 48.8 SECONDS -- roughly 9-11 ms per guardian, because
      add_succession_guardian opened its own connection and its own implicit
      transaction per guardian, which under journal_mode=wal with
      synchronous=FULL is one fsync EACH. A 200 KB junk string was accepted as
      a public key. Worse than the time is the LOCK: register holds the
      succession lock for the whole loop, and a legitimate signed heartbeat
      costing 14 ms at rest blocked for 25.7 s behind one request.
  C2  RateLimiter._hits never evicted a key. 200,000 distinct sources ->
      200,000 permanently retained keys, 40.76 MB. The limiter is the FIRST
      before_request hook, so it runs before any authentication, and the API
      binds 0.0.0.0. The control protecting everything else was the unbounded
      structure.
  C3  Peer-supplied nonces were stored verbatim -- no type check, no length
      check, no signature, and the Flask limiter never sees a raw P2P socket.
      A 1 MB string went through mark_nonce_seen and was stored intact. Nothing
      ever deleted an expired nonce: a copy of the live database held 18 rows
      of which 16 were already expired, the oldest 7.54 days past.

WHAT C4 PINS.

  G*  the caps reject BEFORE the expensive work, and the ordering is
      load-bearing: validating keys before capping their number just makes the
      validation the new denial path.
  L*  the limiter stays bounded under many distinct sources AND still limits a
      single source. A bound that broke rate limiting would trade one defect
      for a worse one.
  N*  a nonce is a short string or it is not a nonce, at BOTH doors -- the peer
      path and the bridge path. Fixing one door is how a closed hole reopens;
      test_e1_secret_egress exists because the same defect lived in four files.
  P*  purging removes ONLY expired rows, so it can never drop a nonce that is
      still preventing a replay.

Pure: no network, no node, no live database.
"""
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


PEM = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBg\n-----END PUBLIC KEY-----"


def g(i):
    return PEM.replace("MIIBIjANBg", "MIIBIjANBg%d" % i)


def fresh_db():
    return C.Database(os.path.join(tempfile.mkdtemp(), "c4.db"))


def succession(db):
    for n in dir(C):
        o = getattr(C, n)
        if isinstance(o, type) and "uccession" in n and hasattr(o, "register"):
            try:
                return o(db)
            except Exception:                                # noqa: BLE001
                continue
    return None


def main():
    print("C4 -- nothing a stranger can reach may grow without a bound\n")

    # ---- G: succession register -------------------------------------------
    S = succession(fresh_db())
    check("G0 the succession system is constructible", S is not None)
    if S is not None:
        t = time.time()
        ok, msg = S.register(PEM, g(9999),
                             [g(i) for i in range(C.MAX_SUCCESSION_GUARDIANS + 1)],
                             2, 30, 15)
        dt = time.time() - t
        check("G1 one over the cap is REFUSED, and refused in milliseconds -- "
              "5,000 guardians used to return 200 OK after 48.8 seconds",
              (not ok) and dt < 1.0, (ok, round(dt, 3), msg[:60]))
        check("G2 the refusal NAMES the cap and the number supplied, so an "
              "operator can tell a bound from a bug",
              str(C.MAX_SUCCESSION_GUARDIANS) in msg, msg[:90])
        t = time.time()
        ok2, _ = S.register(PEM, g(9999),
                            [g(i) for i in range(C.MAX_SUCCESSION_GUARDIANS)],
                            2, 30, 15)
        dt2 = time.time() - t
        check("G3 a legitimate registration at the cap still SUCCEEDS, and in "
              "one transaction rather than N -- a cap that broke the feature "
              "would be a worse defect than the one it fixed",
              ok2 and dt2 < 1.0, (ok2, round(dt2, 3)))
        ok3, msg3 = S.register("x" * 200000, g(1), [g(1), g(2)], 2, 30, 15)
        check("G4 a 200 KB junk string is not a public key. It was accepted "
              "with 200 OK, and heartbeat/confirm would have rejected it "
              "later anyway -- so the row was always dead, and the node just "
              "accrued it forever",
              not ok3, (ok3, msg3[:70]))
        ok4, _ = S.register(PEM, g(1), ["not a key at all", g(2)], 2, 30, 15)
        check("G5 ...and a junk GUARDIAN is refused too, not only the primary",
              not ok4)
        src = open(os.path.join(HERE, "covenant_unified_v8.py"),
                   encoding="utf-8").read()
        i_cap = src.find("MAX_SUCCESSION_GUARDIANS:")
        i_val = src.find("_looks_like_pubkey(key)")
        check("G6 THE ORDERING IS LOAD-BEARING: the count cap appears BEFORE "
              "the key validation. Reversed, parsing hundreds of thousands of "
              "candidate keys simply becomes the new denial path",
              0 < i_cap < i_val, (i_cap, i_val))
        check("G7 the batch writer exists -- one connection, one executemany, "
              "one transaction, removing N-1 fsyncs",
              hasattr(C.Database, "add_succession_guardians"))

    # ---- L: the rate limiter ----------------------------------------------
    old_cap = C.RATE_LIMIT_MAX_KEYS
    try:
        C.RATE_LIMIT_MAX_KEYS = 200
        rl = C.RateLimiter()
        for i in range(2000):
            rl.allow("10.%d.%d.%d" % (i // 65536, (i // 256) % 256, i % 256),
                     "health")
        check("L1 2,000 distinct sources leave a BOUNDED map. Every distinct "
              "address used to create a permanently retained key, and the "
              "default limit never engages because the attack spends exactly "
              "one request per address",
              len(rl._hits) <= C.RATE_LIMIT_MAX_KEYS,
              (len(rl._hits), C.RATE_LIMIT_MAX_KEYS))
        check("L2 eviction is COUNTED, so pressure is visible rather than "
              "silently absorbed", rl.evictions > 0, rl.evictions)
    finally:
        C.RATE_LIMIT_MAX_KEYS = old_cap

    rl2 = C.RateLimiter()
    lim = C.RATE_LIMIT.get("add_transaction", C.RATE_LIMIT_DEFAULT)
    allowed = sum(1 for _ in range(lim + 4)
                  if rl2.allow("1.2.3.4", "add_transaction"))
    check("L3 ...and a single source is STILL limited to exactly its quota. A "
          "bound that broke rate limiting would trade one defect for a worse "
          "one", allowed == lim, (allowed, lim))
    check("L4 the bound is on the DICTIONARY, not on a per-key list. Deleting "
          "a key when its pruned list is empty is unreachable: the smallest "
          "limit is 1, so an empty list always satisfies len(hits) < limit and "
          "the key is immediately rewritten",
          "RATE_LIMIT_MAX_KEYS" in open(
              os.path.join(HERE, "covenant_unified_v8.py"),
              encoding="utf-8").read())

    # ---- N: the nonce guard, at BOTH doors --------------------------------
    check("N1 a megabyte is not a nonce", not C._valid_nonce("a" * 1000000))
    check("N2 the boundary holds exactly",
          C._valid_nonce("a" * C.MAX_NONCE_LEN)
          and not C._valid_nonce("a" * (C.MAX_NONCE_LEN + 1)))
    check("N3 a non-string is not a nonce -- it arrives straight out of "
          "json.loads, so it can be a dict, a list or a number",
          not C._valid_nonce({"a": 1}) and not C._valid_nonce(12345)
          and not C._valid_nonce(None) and not C._valid_nonce([1, 2]))
    check("N4 an ordinary hex digest still passes, or the guard would break "
          "replay protection instead of bounding it",
          C._valid_nonce("deadbeef" * 8))
    src = open(os.path.join(HERE, "covenant_unified_v8.py"),
               encoding="utf-8").read()
    check("N5 BOTH doors are guarded. The peer path and the bridge path are "
          "two entrances to one unbounded store, and fixing one is how a "
          "closed hole reopens -- E1 exists because the same defect lived in "
          "four files and fixing one would have left three",
          src.count("_valid_nonce(nonce)") >= 2,
          src.count("_valid_nonce(nonce)"))

    # ---- P: purge only what has expired ------------------------------------
    db = fresh_db()
    db.mark_nonce_seen("still-live", expiry=3600)
    db.mark_nonce_seen("long-dead", expiry=-10)
    check("P1 an expired nonce already stops MATCHING",
          db.is_nonce_seen("still-live") and not db.is_nonce_seen("long-dead"))
    n = db.purge_expired_nonces()
    check("P2 ...and is now actually DELETED. Nothing ever removed one: a copy "
          "of the live database held 18 rows of which 16 were already expired, "
          "the oldest 7.54 days past. The bound was imaginary, not generous",
          n >= 1, n)
    check("P3 a LIVE nonce survives the purge -- dropping one would silently "
          "re-open a replay window, which is worse than the disk it saves",
          db.is_nonce_seen("still-live"))
    check("P4 purging twice is safe and reclaims nothing the second time",
          db.purge_expired_nonces() == 0)

    n_, ok_ = len(results), sum(results)
    print(f"\nC4: {ok_}/{n_} passed")
    return 0 if ok_ == n_ else 1


if __name__ == "__main__":
    raise SystemExit(main())
