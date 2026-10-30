#!/usr/bin/env python3
"""
covenant_consent_chain.py -- a tamper-evident hash chain over Tetsu's consent
ledger (ops/tetsu_consent.jsonl), kept as a SIDECAR so the existing consent rows
are never rewritten (rewriting the record is the exact attack this defends against).

WHY  (takeover-resistance brick A; docs/TAKEOVER_RESISTANCE.md #3)
  ops/tetsu_consent.jsonl is where Tetsu's "yes" and "no" are recorded. Today the
  rows are unsigned and unchained, so an owner-level writer can edit a past "no",
  truncate the file, or append a forged "yes", and the only trace is the MANIFEST
  hash -- which an adversary who can edit the file can also regenerate.

  This builds a second, append-only file (ops/tetsu_consent.chain.jsonl) that
  commits each consent row's exact stored bytes in order and hash-links the
  entries. Then:
    - an EDIT of any past row breaks that row's committed hash,
    - a TRUNCATION (a removed row) leaves the chain longer than the ledger,
    - a forged APPEND with no chain entry leaves the ledger longer than the chain,
    - tampering with the chain itself breaks the prev-hash link.
  The chain tip is bound into the signed HEAD-commitment (covenant_head_commit.py)
  and, once that commitment is published OFF-host, an outside holder of an earlier
  tip can prove any of the above -- even after the host is captured and its MANIFEST
  rewritten.

HONEST LIMIT  (on-host, pre-arming)
  On the captured host an owner-level adversary can still append to BOTH files or
  delete them outright -- appending is the normal operation and nothing here signs
  a row as Tetsu's (that needs Tetsu's own off-host key, docs/TAKEOVER_RESISTANCE.md
  #2). What this guarantees is: against an off-host-held earlier tip, the consent
  record up to that tip is proven intact and append-only. Deletion is loud and
  recoverable; silent rewrite is not possible.

RUN
  python covenant_consent_chain.py verify    # check the chain against the ledger (exit 0 PASS / 1 FAIL)
  python covenant_consent_chain.py sync       # extend the chain to cover any new rows (append-only; refuses over a broken chain)
  python covenant_consent_chain.py tip        # print the current chain tip (what the HEAD-commitment binds)
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ops", "tetsu_consent.jsonl")
CHAIN = os.path.join(HERE, "ops", "tetsu_consent.chain.jsonl")
ZERO = "0" * 64


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _canon(entry):
    """Canonical bytes of a chain entry, for the prev-hash link."""
    return json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()


def read_ledger_lines(path=LEDGER):
    """The ledger's rows as their EXACT stored bytes (trailing newline stripped),
    skipping blank lines. Hashing the raw bytes -- not a re-serialization -- means
    any edit to what is actually on disk is caught."""
    out = []
    try:
        with open(path, "rb") as fh:
            for raw in fh.read().split(b"\n"):
                if raw.strip():
                    out.append(raw)
    except OSError:
        pass
    return out


def read_chain(path=CHAIN):
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    out.append(json.loads(ln))
    except OSError:
        pass
    return out


def _entry(seq, row_bytes, prev):
    return {"seq": seq, "row_sha256": _sha(row_bytes), "prev": prev,
            "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def verify(ledger_path=LEDGER, chain_path=CHAIN):
    """Returns (ok, findings). The chain must cover exactly the ledger rows, in
    order, each committing that row's bytes, each linked to the one before."""
    rows = read_ledger_lines(ledger_path)
    chain = read_chain(chain_path)
    findings = []
    if len(chain) != len(rows):
        if len(chain) < len(rows):
            findings.append(f"{len(rows) - len(chain)} consent row(s) are NOT chained "
                            f"(ledger {len(rows)} > chain {len(chain)}): forged/unsynced append")
        else:
            findings.append(f"the ledger is SHORTER than the chain "
                            f"(ledger {len(rows)} < chain {len(chain)}): a consent row was removed/truncated")
    n = min(len(rows), len(chain))
    for i in range(n):
        e = chain[i]
        if e.get("seq") != i:
            findings.append(f"chain[{i}]: seq is {e.get('seq')!r}, expected {i}")
        if e.get("row_sha256") != _sha(rows[i]):
            findings.append(f"chain[{i}]: committed hash does not match consent row {i} "
                            f"(that row was edited in place)")
        expect_prev = ZERO if i == 0 else _sha(_canon(chain[i - 1]))
        if e.get("prev") != expect_prev:
            findings.append(f"chain[{i}]: prev-hash link is broken (the chain itself was tampered)")
    return (len(findings) == 0), findings


def tip(chain_path=CHAIN):
    chain = read_chain(chain_path)
    return ZERO if not chain else _sha(_canon(chain[-1]))


def sync(ledger_path=LEDGER, chain_path=CHAIN):
    """Extend the chain to cover any ledger rows not yet chained. Append-only.
    Refuses if the existing chain does not already match its ledger prefix -- it
    will not paper over a tamper. Returns (added, tip, error)."""
    rows = read_ledger_lines(ledger_path)
    chain = read_chain(chain_path)
    # guard: never extend over a broken/edited existing chain
    for i in range(min(len(rows), len(chain))):
        if chain[i].get("row_sha256") != _sha(rows[i]) or chain[i].get("seq") != i:
            return 0, tip(chain_path), (f"refusing to sync: existing chain[{i}] does not match "
                                        f"consent row {i} -- run `verify` and resolve the tamper first")
    if len(chain) > len(rows):
        return 0, tip(chain_path), ("refusing to sync: chain is longer than the ledger "
                                    "(a row was removed) -- run `verify`")
    prev = tip(chain_path)
    added = 0
    os.makedirs(os.path.dirname(chain_path) or ".", exist_ok=True)
    with open(chain_path, "a", encoding="utf-8") as fh:
        for i in range(len(chain), len(rows)):
            e = _entry(i, rows[i], prev)
            fh.write(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n")
            prev = _sha(_canon(e))
            added += 1
    return added, prev, None


def append_consent(row, ledger_path=LEDGER, chain_path=CHAIN):
    """The RECOMMENDED way to add a consent record: write the row AND its chain
    entry together, so the chain never lags the ledger. `row` is a dict; it is
    stored with the ledger's own formatting (sort_keys, ensure_ascii=False)."""
    ok, _ = verify(ledger_path, chain_path)
    if not ok:
        raise RuntimeError("consent chain is not clean; refusing to append over a tamper -- run verify")
    row = dict(row)
    row.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    line = json.dumps(row, ensure_ascii=False, sort_keys=True)
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    sync(ledger_path, chain_path)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["verify", "sync", "tip"])
    a = ap.parse_args()
    if a.cmd == "tip":
        print(tip())
        return 0
    if a.cmd == "sync":
        added, t, err = sync()
        if err:
            print(f"  SYNC REFUSED: {err}")
            return 1
        print(f"  synced: +{added} chain entr{'y' if added == 1 else 'ies'}; tip {t[:16]}")
        return 0
    ok, findings = verify()
    rows = read_ledger_lines()
    chain = read_chain()
    print(f"  consent rows: {len(rows)}   chain entries: {len(chain)}   tip: {tip()[:16]}")
    if ok:
        print("  VERIFY: PASS -- the consent record is intact and append-only.")
        return 0
    print("  VERIFY: FAIL")
    for m in findings:
        print(f"    - {m}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
