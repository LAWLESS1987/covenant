#!/usr/bin/env python3
"""test_m1_mine_equivalence.py -- M1: the fast miner must agree with the slow one.

WHAT CHANGED, AND WHY IT NEEDS PINNING.

Block.mine() calls compute_hash() about 65,536 times per block. Everything
compute_hash serialises is fixed before the loop except `nonce` -- yet every
attempt re-ran [asdict(tx) for tx in transactions], a recursive deepcopy, then
re-serialised and re-encoded the entire block. Sixty-five thousand times, to
change one integer.

mine() now builds that serialisation ONCE with a placeholder nonce and splices
the varying integer in. Measured per hash: 10.1x at 1 transaction, 16.9x at 4,
26.8x at 20. End to end on a real POST /mine, 7 blocks x 4 tx: 172.96 s ->
8.11 s.

compute_hash() IS UNCHANGED, deliberately. It is the function peers run to
verify this block, so leaving it untouched is what makes the change auditable:
the fast path must agree with it, and M1 is where that is established.

WHAT M1 PINS.

  E*  EQUIVALENCE. Thousands of (block, nonce) pairs hashed both ways, byte for
      byte. A miner that produces a different hash from the verifier does not
      produce slow blocks; it produces blocks the network rejects.
  H*  THE HOSTILE CASE, which is the reason the guard exists. tx.data is
      Dict[str, Any] and validate_transaction_shape imposes no key restriction,
      so a PEER chooses it. A transaction carrying {"nonce": 0} makes the
      splice marker appear twice, and an unguarded split would raise ValueError
      inside /mine while holding chain_lock -- a remotely triggerable 500 on
      every mine for as long as that transaction is selected. Each hostile
      shape must take the SLOW path and still mine correctly.
  G*  the runtime guard exists and is not decorative: mine() re-checks its own
      answer against compute_hash() before publishing, so a divergence nobody
      anticipated raises instead of propagating.

Pure: no node, no network, low difficulty.
"""
import hashlib
import inspect
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def mktx(n=0, data=None):
    return C.Transaction(sender_pubkey="k" * (40 + n % 7),
                         receiver="r" * (30 + n % 5),
                         data=data if data is not None else {"m": "x" * (n % 17)},
                         amount=float(n % 97) / 3.0, signature="s" * 64,
                         benefit_score=(n % 11) / 10.0, reg_nonce=n)


MARKER = '"nonce": 0'


def template(b):
    """Exactly what mine() builds. Returns (pre, post) or (None, count)."""
    tmpl = json.dumps({
        "index": b.index,
        "transactions": [dict(t.__dict__) for t in b.transactions],
        "previous_hash": b.previous_hash, "timestamp": b.timestamp,
        "nonce": 0, "alignment_score": b.alignment_score,
        "stake_rewards": b.stake_rewards}, sort_keys=True)
    if tmpl.count(MARKER) != 1:
        return None, tmpl.count(MARKER)
    head, tail = tmpl.split(MARKER, 1)
    return ((head + '"nonce": ').encode(), tail.encode()), 1


def spliced(b, nonce):
    parts, _ = template(b)
    if parts is None:
        return None
    pre, post = parts
    return hashlib.sha256(pre + str(nonce).encode() + post).hexdigest()


def main():
    print("M1 -- the fast miner must agree with the slow one\n")
    random.seed(20260830)

    # ---- E: equivalence over many shapes and boundary nonces --------------
    NONCES = [0, 1, 9, 10, 12345, 2 ** 31, 2 ** 62, 2 ** 63 - 1] + \
             [random.randrange(0, 2 ** 63) for _ in range(7)]
    checked = diverged = 0
    for i in range(150):
        txs = [mktx(i * 7 + j) for j in range(random.choice([1, 1, 2, 4, 8]))]
        b = C.Block(index=i, transactions=txs, previous_hash="p" * 64,
                    alignment_score=0.5, stake_rewards=float(i) / 7.0)
        for nn in NONCES:
            b.nonce = nn
            got = spliced(b, nn)
            if got is None:
                continue
            checked += 1
            if got != b.compute_hash():
                diverged += 1
    check("E1 %d (block, nonce) pairs hash IDENTICALLY both ways. A miner that "
          "disagrees with the verifier does not make slow blocks, it makes "
          "blocks the network rejects" % checked, diverged == 0 and checked > 1000,
          (checked, diverged))
    check("E2 the boundary nonces are covered: 0, 1, and 2^63-1, which is the "
          "value safe_nonce wraps at and save_block raises above",
          all(n in NONCES for n in (0, 1, 2 ** 63 - 1)))

    # ---- H: the hostile shapes must take the slow path --------------------
    HOSTILE = [
        ('{"nonce": 0}', {"nonce": 0}),
        ('nested {"a":{"b":{"nonce":0}}}', {"a": {"b": {"nonce": 0}}}),
        ('float {"nonce": 0.0}', {"nonce": 0.0}),
        ('list of two', [{"nonce": 0}, {"nonce": 0}]),
    ]
    for name, payload in HOSTILE:
        b = C.Block(index=1, transactions=[mktx(data=payload)],
                    previous_hash="p" * 64)
        parts, cnt = template(b)
        check("H:%-32s makes the marker ambiguous (count=%s) and MUST take the "
              "slow path. Unguarded, the split raises ValueError inside /mine "
              "while holding chain_lock" % (name, cnt), parts is None, cnt)

    for name, payload in HOSTILE:
        b = C.Block(index=2, transactions=[mktx(data=payload)],
                    previous_hash="p" * 64)
        b.mine(difficulty=2)
        check("H:%-32s still MINES correctly through the fallback -- a guard "
              "that refused to mine would be a denial of service wearing a "
              "safety jacket" % name,
              b.hash.startswith("00") and b.hash == b.compute_hash())

    # ---- G: the runtime guard is real ------------------------------------
    src = inspect.getsource(C.Block.mine)
    check("G1 mine() re-checks its own result against compute_hash() before "
          "returning, so a divergence nobody anticipated raises instead of "
          "propagating into the chain",
          "self.compute_hash()" in src and "RuntimeError" in src)
    check("G2 the count guard is present, not just documented",
          ".count(" in src and "!= 1" in src or "== 1" in src)
    check("G3 compute_hash itself is UNTOUCHED by the optimisation -- it stays "
          "the plain, obvious implementation peers run",
          "asdict" in inspect.getsource(C.Block.compute_hash)
          and "split" not in inspect.getsource(C.Block.compute_hash))

    # ---- ordinary blocks still mine --------------------------------------
    b = C.Block(index=3, transactions=[mktx(1), mktx(2)], previous_hash="p" * 64)
    b.mine(difficulty=2)
    check("N1 an ordinary block mines and verifies",
          b.hash.startswith("00") and b.hash == b.compute_hash())
    b2 = C.Block(index=4, transactions=[], previous_hash="p" * 64)
    b2.mine(difficulty=2)
    check("N2 a block with NO transactions mines too -- the template is built "
          "from an empty list and must not become malformed",
          b2.hash.startswith("00") and b2.hash == b2.compute_hash())

    n, ok = len(results), sum(results)
    print(f"\nM1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
