#!/usr/bin/env python3
"""
verify_grid_ledger.py -- STANDALONE verifier for the grid command ledger.

Imports NO covenant code (stdlib + `cryptography` only), the verify_head_commitment.py
model: a stranger drops this beside a public clone and proves, from bytes alone,
that the signed+chained command record was not rewritten and (if a gateway public
key is given) that every row carries a valid gateway signature.

It re-implements the framing/canonicalization and the raw-bytes hash chain locally
ON PURPOSE -- so the check depends on no covenant module.

Exit: 0 PASS, 1 FAIL (tamper), 2 UNDETERMINED (nothing to check / unreadable).

Usage:
  python verify_grid_ledger.py [--ledger ops/grid_commands.jsonl]
                               [--chain ops/grid_commands.chain.jsonl]
                               [--gateway-pubkey docs/GRID_GATEWAY_PUBKEY.pem]
"""
import argparse
import base64
import hashlib
import json
import os

CMD_DOMAIN = b"COVENANT_GRIDCMD_V1"
ZERO = "0" * 64


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _frame(domain, *fields):
    out = bytearray(domain)
    for f in fields:
        out += len(f).to_bytes(4, "big") + f
    return bytes(out)


def _read_rows(path):
    out = []
    with open(path, "rb") as fh:
        for raw in fh.read().split(b"\n"):
            if raw.strip():
                out.append(raw)
    return out


def _read_chain(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


def _verify_gateway_sig(row_obj, pub_pem):
    """row_obj is the parsed row; its gateway_sig covers the row WITHOUT that field."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.exceptions import InvalidSignature
    sig = row_obj.get("gateway_sig")
    if not sig:
        return None  # unsigned row (reference may omit the gateway key)
    core = {k: v for k, v in row_obj.items() if k != "gateway_sig"}
    try:
        pub = serialization.load_pem_public_key(pub_pem.encode() if isinstance(pub_pem, str) else pub_pem)
        pub.verify(base64.b64decode(sig), _frame(CMD_DOMAIN, _canon(core)),
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                   hashes.SHA256())
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def run(ledger, chain, gateway_pubkey=None):
    lines = []
    if not os.path.exists(ledger) or not os.path.exists(chain):
        return 2, ["UNDETERMINED: ledger or chain file absent (nothing honored yet?)"]
    try:
        rows = _read_rows(ledger)
        chn = _read_chain(chain)
    except Exception as e:  # noqa: BLE001
        return 2, ["UNDETERMINED: could not read ledger/chain: %r" % e]
    if not rows:
        return 2, ["UNDETERMINED: ledger is empty"]

    findings = []
    # Length: chain must cover exactly the ledger rows.
    if len(chn) != len(rows):
        if len(chn) < len(rows):
            findings.append("FAIL: %d command row(s) are NOT chained (ledger %d > chain %d): "
                            "forged/unsynced append" % (len(rows) - len(chn), len(rows), len(chn)))
        else:
            findings.append("FAIL: ledger SHORTER than chain (ledger %d < chain %d): a row was "
                            "removed/truncated" % (len(rows), len(chn)))
    n = min(len(rows), len(chn))
    for i in range(n):
        e = chn[i]
        if e.get("seq") != i:
            findings.append("FAIL: chain[%d] seq is %r, expected %d" % (i, e.get("seq"), i))
        if e.get("row_sha256") != _sha(rows[i]):
            findings.append("FAIL: chain[%d] committed hash != row %d (row edited in place)" % (i, i))
        expect_prev = ZERO if i == 0 else _sha(_canon(chn[i - 1]))
        if e.get("prev") != expect_prev:
            findings.append("FAIL: chain[%d] prev-hash link broken (chain itself tampered)" % i)

    # Optional: gateway signature on each row.
    pub = None
    if gateway_pubkey and os.path.exists(gateway_pubkey):
        with open(gateway_pubkey, encoding="utf-8") as fh:
            pub = fh.read()
    sig_checked = sig_bad = 0
    if pub:
        for i in range(len(rows)):
            try:
                obj = json.loads(rows[i])
            except Exception:  # noqa: BLE001
                findings.append("FAIL: row %d is not valid JSON" % i); continue
            res = _verify_gateway_sig(obj, pub)
            if res is True:
                sig_checked += 1
            elif res is False:
                sig_bad += 1
                findings.append("FAIL: row %d gateway signature invalid" % i)

    if findings:
        lines.append("GRID LEDGER: FAIL")
        lines.extend("  - " + f for f in findings)
        return 1, lines
    lines.append("GRID LEDGER: PASS -- %d rows, chain intact%s" %
                 (len(rows), (", %d gateway sigs valid" % sig_checked) if pub else " (no gateway key given; chain only)"))
    return 0, lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=os.path.join("ops", "grid_commands.jsonl"))
    ap.add_argument("--chain", default=os.path.join("ops", "grid_commands.chain.jsonl"))
    ap.add_argument("--gateway-pubkey", default=os.path.join("docs", "GRID_GATEWAY_PUBKEY.pem"))
    a = ap.parse_args(argv)
    code, lines = run(a.ledger, a.chain, a.gateway_pubkey)
    for ln in lines:
        print(ln)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
