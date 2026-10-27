#!/usr/bin/env python3
"""verify_record.py -- go and read back what the witness says it wrote.

THE GAP THIS CLOSES (2026-09-18). The witness returned a `tx_id` and nothing
ever looked at it again. The whole claim of this design -- that a proposal is
RECORDED whether or not it was allowed -- rested on the seal service reporting
its own success. A gate that says "I wrote that down" and is never asked to
produce it is not an audit trail; it is a promise.

WHAT INDEPENDENT MEANS HERE, precisely, because the word is doing work:

  * independent of the SEAL SERVICE's claim -- the record is fetched from the
    node's `/chain`, not from anything seal_service kept;
  * independent of the node's WORD about the id -- the id is RECOMPUTED from
    the stored bytes (content-addressed over sender, receiver, timestamp,
    amount and canonical data) and compared to the one the seal reported. A
    node that returned an id for a record it did not store fails here;
  * NOT independent of the id DERIVATION. It uses the core's own Transaction
    for that, so this checks the claim, not the hash function. A reimplemented
    hash would drift from the chain's and start reporting false tampering,
    which is worse than the gap it closes. Said out loud rather than implied.

  python sentinel_witness/verify_record.py --node http://127.0.0.1:5000 --tail 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

#: Fields of the sentinel's own record that MUST match byte for byte. `text` is
#: the judged field, so a mismatch there means the chain holds something other
#: than what the judge was shown -- the worst case this file exists to catch.
MUST_MATCH = ("venue", "symbol", "side", "amount_usd", "text", "source")


def fetch_chain(node, lo=None, hi=None, timeout=30):
    url = node.rstrip("/") + "/chain"
    if lo is not None and hi is not None:
        url += "?from=%d&to=%d" % (lo, hi)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _recompute_id(tx):
    """The id the CHAIN's own derivation gives for this stored transaction."""
    import covenant_unified_v8 as cov
    t = cov.Transaction(
        sender_pubkey=tx.get("sender_pubkey", ""),
        receiver=tx.get("receiver", ""),
        amount=tx.get("amount", 0.0),
        data=tx.get("data") or {},
        timestamp=tx.get("timestamp", 0),
    )
    return t.get_id()


def find(node, tx_id, tail=None, timeout=30):
    """(block_index, tx, recomputed_id) for tx_id, or (None, None, None).

    Scans newest-first: a record just sealed is at the tip, and the whole point
    is to check it promptly. `tail` bounds the read -- /chain serves the entire
    chain by default and that is 183 MB at 50,000 blocks.
    """
    head = fetch_chain(node, timeout=timeout) if tail is None else None
    if head is None:
        meta = fetch_chain(node, 0, 1, timeout=timeout)
        n = int(meta.get("length") or 0)
        lo = max(0, n - int(tail))
        head = fetch_chain(node, lo, n, timeout=timeout)
    blocks = head.get("chain") or []
    for b in reversed(blocks):
        for tx in (b.get("transactions") or []):
            try:
                got = _recompute_id(tx)
            except Exception:                                    # noqa: BLE001
                continue
            if got == tx_id:
                return b.get("index"), tx, got
    return None, None, None


def verify(node, tx_id, expected_record, tail=None, timeout=30):
    """(ok, reasons, where). `ok` only when the record is ON the chain AND says
    what the witness claimed it said.

    Every failure is named rather than collapsed into False, because "not on the
    chain" and "on the chain saying something else" need different responses:
    the first is a lost record, the second is a chain that disagrees with the
    gate that wrote to it.
    """
    reasons, where = [], {}
    if not tx_id:
        return False, ["the witness returned no tx_id, so there is nothing to "
                       "look up -- an unverifiable claim, not a verified one"], where
    try:
        idx, tx, got = find(node, tx_id, tail=tail, timeout=timeout)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return False, ["the chain could not be read (%s: %s) -- UNVERIFIED, "
                       "which is not the same as refuted"
                       % (type(e).__name__, str(e)[:90])], where
    if tx is None:
        return False, ["no transaction on the chain recomputes to %s -- the "
                       "witness claimed a record that is not there" % tx_id[:16]], where
    where = {"block": idx, "recomputed_id": got}
    data = tx.get("data") or {}
    for k in MUST_MATCH:
        want, have = expected_record.get(k), data.get(k)
        if k == "amount_usd":
            try:
                same = abs(float(want) - float(have)) < 1e-9
            except (TypeError, ValueError):
                same = want == have
        else:
            same = want == have
        if not same:
            reasons.append("field %r: the gate sealed %r, the chain holds %r"
                           % (k, want, have))
    return (not reasons), reasons, where


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--node", default="http://127.0.0.1:5000")
    ap.add_argument("--tail", type=int, default=5,
                    help="how many blocks back to read (default 5)")
    a = ap.parse_args(argv)
    try:
        meta = fetch_chain(a.node, 0, 1)
        n = int(meta.get("length") or 0)
        lo = max(0, n - a.tail)
        blocks = (fetch_chain(a.node, lo, n).get("chain") or [])
    except Exception as e:                                       # noqa: BLE001
        print("cannot read %s: %s: %s" % (a.node, type(e).__name__, e))
        return 2
    print("chain height %d; reading blocks %d..%d" % (n, lo, n))
    found = 0
    for b in blocks:
        for tx in (b.get("transactions") or []):
            d = tx.get("data") or {}
            if d.get("source") != "sentinel_witness":
                continue
            found += 1
            ok, reasons, where = verify(a.node, _recompute_id(tx), d, tail=a.tail)
            print("  block %-4s %-8s %s"
                  % (b.get("index"), "VERIFIED" if ok else "MISMATCH",
                     (reasons or ["text=%r" % str(d.get("text"))[:48]])[0][:80]))
    if not found:
        print("  no sentinel_witness records in those blocks -- nothing to verify,")
        print("  which is a statement about this chain and not about the loop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
