#!/usr/bin/env python3
"""test_e2_chain_serialisation.py -- E2: the chain endpoint, measured.

WHAT WAS WRONG, and it was invisible at this chain's height.

    @self.app.route("/chain")
    def get_chain():
        return jsonify({"chain": [asdict(b) for b in self.node.chain]})

Two costs, neither of which shows at 3 blocks:

  1. `dataclasses.asdict()` deep-copies every field recursively. On a read-only
     serialisation path that copy buys nothing. Measured: 1,000 blocks 23.8 ms
     -> 2.2 ms; 10,000 blocks 183.0 ms -> 32.4 ms.
  2. It served the ENTIRE chain on every request, with no way to ask for less:

         3 blocks       11 KB     0.1 ms
     1,000 blocks      3.7 MB    44.0 ms
    10,000 blocks     36.7 MB   378.7 ms
    50,000 blocks    183.5 MB   902.8 ms

     public_ledger.py caps a relayed response at 8 MB, so the deliberate public
     read layer would have begun refusing at about 2,287 blocks -- a ceiling
     nobody chose and nobody would have noticed until it arrived.

WHAT E2 PINS.

  I*  THE OUTPUT IS IDENTICAL. This is the whole safety argument: a faster
      serialiser that emits anything different is a wire-format change wearing
      an optimisation's clothes. Byte-for-byte against asdict, and asserted
      field-by-field so that ADDING a nested dataclass to Block -- which would
      silently break the equivalence -- fails here rather than in a peer's
      parser.
  R*  the range is optional and half-open, no parameters means exactly the old
      behaviour, and `length` is always the FULL height so a client can page
      without a second request.
  B*  bad input is refused rather than crashing or silently returning
      everything.
  S*  the speedup is real, measured here rather than quoted from a commit
      message.

Pure: no node, no network.
"""
import json
import os
import sys
import time
from dataclasses import asdict, fields, is_dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def mktx():
    return C.Transaction(sender_pubkey="d" * 450, receiver="b" * 180,
                         data="payload", amount=1.5, signature="c" * 128)


def mkblock(i, ntx=3):
    return C.Block(index=i, transactions=[mktx() for _ in range(ntx)],
                   previous_hash="0" * 64, nonce=i, hash="f" * 64,
                   alignment_score=0.5, stake_rewards=1.25)


def main():
    print("E2 -- the chain endpoint: same bytes, less time, and a range\n")

    b = mkblock(7)
    a, m = asdict(b), C._block_dict(b)

    check("I1 IDENTICAL to asdict. A faster serialiser that emits anything "
          "different is a wire-format change wearing an optimisation's "
          "clothes, and peers would parse the difference before anyone read "
          "the commit", a == m, {k: (a.get(k), m.get(k))
                                 for k in set(a) | set(m) if a.get(k) != m.get(k)})
    check("I2 ...and identical as JSON BYTES, which is what actually goes on "
          "the wire",
          json.dumps(a, sort_keys=True) == json.dumps(m, sort_keys=True))
    check("I3 every declared Block field appears -- a field dropped here is a "
          "field a peer never receives",
          set(f.name for f in fields(C.Block)) <= set(m),
          set(f.name for f in fields(C.Block)) - set(m))
    check("I4 every declared Transaction field appears too",
          all(set(f.name for f in fields(C.Transaction)) <= set(t)
              for t in m["transactions"]))
    nested = [f.name for f in fields(C.Block)
              if f.name != "transactions"
              and is_dataclass(getattr(b, f.name, None))]
    check("I5 THE TRIPWIRE: Block has exactly ONE nested dataclass field, "
          "`transactions`, and this is what the shortcut relies on. If a "
          "second is ever added, asdict would recurse into it and _block_dict "
          "would emit a raw object -- so this must fail HERE rather than in a "
          "peer's parser", not nested, nested)
    m["transactions"][0]["amount"] = 999.0
    check("I6 mutating the returned dict cannot reach back into the block. "
          "__dict__ hands out the live mapping; this copies",
          b.transactions[0].amount == 1.5)

    # ---- R: the range ------------------------------------------------------
    chain = [mkblock(i) for i in range(50)]

    def slice_like_route(args):
        total = len(chain)
        try:
            lo = int(args.get("from", 0))
            hi = int(args.get("to", total))
        except (TypeError, ValueError):
            return None
        lo = max(0, min(lo, total))
        hi = max(lo, min(hi, total))
        return {"chain": [C._block_dict(x) for x in chain[lo:hi]],
                "length": total, "from": lo, "to": hi}

    full = slice_like_route({})
    check("R1 NO parameters returns the whole chain, exactly as before. Every "
          "existing caller and every peer is unaffected",
          len(full["chain"]) == 50 and full["from"] == 0 and full["to"] == 50)
    part = slice_like_route({"from": "10", "to": "20"})
    check("R2 a range is half-open [from, to)", len(part["chain"]) == 10
          and part["chain"][0]["index"] == 10
          and part["chain"][-1]["index"] == 19)
    check("R3 `length` is the FULL height, never the slice size, so a client "
          "can page without a second request", part["length"] == 50)
    check("R4 an over-range `to` clamps instead of erroring -- a client that "
          "guesses high gets what exists",
          len(slice_like_route({"from": "45", "to": "9999"})["chain"]) == 5)
    check("R5 a negative `from` clamps to zero",
          slice_like_route({"from": "-5", "to": "3"})["from"] == 0)
    check("R6 an inverted range yields nothing rather than a negative slice, "
          "which in Python would silently return the WRONG blocks",
          slice_like_route({"from": "30", "to": "10"})["chain"] == [])
    check("B1 non-integer input is refused, not coerced and not ignored",
          slice_like_route({"from": "'; DROP TABLE"}) is None)

    # ---- S: the speedup is real, measured here ----------------------------
    big = [mkblock(i) for i in range(2000)]
    t = time.perf_counter()
    [asdict(x) for x in big]
    t_old = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    [C._block_dict(x) for x in big]
    t_new = (time.perf_counter() - t) * 1000
    check("S1 measurably faster on 2,000 blocks, measured in this run rather "
          "than quoted from a commit message (asdict %.1f ms -> %.1f ms, %.1fx)"
          % (t_old, t_new, t_old / t_new if t_new else 0),
          t_new < t_old, (t_old, t_new))
    # S2 asserted `ratio >= 2.0` in its first version and failed at 1.93x --
    # while a full sweep and five other processes were running on this machine.
    # That was the same mistake test_a9_relay_race exhibits under sweep load,
    # committed within hours of diagnosing it: a WALL-CLOCK RATIO IS NOT A
    # PROPERTY OF THE CODE, it is a property of the machine at that moment. A
    # suite that fails when the box is busy teaches its reader to re-run it
    # until it passes, which is worse than not asserting at all.
    #
    # So the CAUSE is asserted instead, and it is load-independent: the fast
    # path must not do the recursive deepcopy. The timing above is evidence,
    # reported and not asserted.
    # BY AST, not by grep. The first version of S2 searched the source TEXT and
    # its companion counted `dict(` in it -- which counts the docstring too,
    # and the docstring necessarily mentions asdict because it explains what
    # this replaces. Third time today that a check matched a string where it
    # should have parsed a tree; the parse tree knows a call from a mention.
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(C._block_dict).lstrip())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
    check("S2 the CAUSE is pinned rather than the clock: by AST, the fast path "
          "CALLS neither asdict nor deepcopy, which is precisely why it is "
          "faster. Asserting the ratio instead fails whenever the machine is "
          "busy -- as it did, at 1.93x, with a sweep running",
          not (called & {"asdict", "deepcopy", "copy"}),
          sorted(called))

    n, ok = len(results), sum(results)
    print(f"\nE2: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
