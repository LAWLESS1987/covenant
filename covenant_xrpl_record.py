#!/usr/bin/env python3
"""
covenant_xrpl_record.py -- the durable, public half of the seal.

ASKED 2026-09-06: "can we put all of this on the xrp ledger?" -- and the honest
answer was: the RECORD yes, the trading no. This is the record.

WHAT PROBLEM THIS SOLVES
  A sealed decision currently lands in the local chain (covenant_unified_v8),
  which lives on one PC, was at height 3 for days because nothing mined it, and
  is checkable only by the operator. KNOWN_ISSUES A53 fixed the mining. It did
  not fix the other half: a record only its owner can read is not evidence to
  anyone else. "Growing wealth for mutual benefit" is a claim, and a claim that
  cannot be audited by a stranger is a promise, not a commitment.

  The XRP Ledger settles in seconds, costs a fraction of a cent per write, and
  is validated by a network nobody here controls. A commitment written there is
  checkable by someone who was never asked to trust us. That is the whole point.

WHAT IS WRITTEN, AND WHAT IS NOT
  An AccountSet transaction carrying one Memo. AccountSet with no fields set is
  a no-op: it changes nothing about the account, costs only the base fee, and
  needs no destination (a Payment to yourself is rejected as temREDUNDANT).

  The memo carries the COMMITMENT ONLY -- the decimal SHA-256 of the decision
  snapshot, plus its kind and time. Never positions, never dollars, never a
  ticker. The snapshot itself stays under ~/.covenant/decisions/ and can be
  produced later to prove what the commitment commits to.

  This is not a convention, it is enforced: publishable() refuses any payload
  carrying a ticker, a dollar figure, an address, or a key-shaped string, and
  record() will not submit a payload it refuses. Tonight's A50 was exactly this
  failure -- a sealed record that carried the whole portfolio into a public
  runner and a published model -- so the rule is machinery now, not a comment.

DEFAULTS ARE THE REFUSING ONES
  network="testnet" and dry_run=True. Mainnet additionally requires
  allow_mainnet=True as a separate argument, the same pattern
  covenant_xrp_signer.XRPSigner uses for the money path: one mistyped config
  value should never be the only thing between a program and a live ledger.

THE SEED
  ~/.covenant/xrpl_seed, outside the synced folder, one line, mode 600. It is
  read by covenant_xrp_signer._read_seed_file, which is the same hygiene the
  payment path uses. A seed found inside the repository is refused outright:
  the repository is published, and a published seed is a lost account.

  This account is for WRITING RECORDS. It should hold the base reserve and a
  little for fees, and nothing else. It is not the operator's XRP holding, and
  the hold-only rule on that holding is untouched by this module.

SETTING IT UP (the operator's hands: this module never creates a key)
  1. python -c "import covenant_xrp_signer as S; S.create_testnet_seed_file(
       r'C:/Users/Lawre/.covenant/xrpl_seed')"
     Writes a NEW testnet seed at mode 0600, refuses to overwrite an existing
     file, prints the address -- and does NOT fund it.
  2. Fund that address at https://xrpl.org/xrp-testnet-faucet.html
  3. Set "xrpl_record": true in trader_config.json. Mainnet additionally needs
     "xrpl_network": "mainnet" AND "xrpl_allow_mainnet": true, two keys, on
     purpose.

USAGE
  python covenant_xrpl_record.py --self-test        # offline, no network, no keys
  python covenant_xrpl_record.py --address          # what account the seed names
  python covenant_xrpl_record.py --record <commitment> --live    # testnet write
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any, Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SEED_PATH = os.environ.get("COVENANT_XRPL_SEED") or os.path.join(
    os.path.expanduser("~"), ".covenant", "xrpl_seed")

MEMO_TYPE = "covenant/record"
MEMO_FORMAT = "application/json"

# A memo is part of the transaction and the whole transaction has a size limit.
# A commitment is ~78 digits; anything approaching this bound means somebody
# started putting the decision itself in the memo, which is the failure this
# module exists to prevent.
MAX_MEMO_BYTES = 512


class XRPLRecordError(Exception):
    """Every refusal here. Never a bare return code on a path that publishes."""


# --------------------------------------------------------------- publishable
_TICKERS = ("xrp", "xlm", "link", "ada", "hbar", "doge", "toshi", "jasmy",
            "wlfi", "xcn", "cro", "vet", "wld", "eos", "usdc", "usdt", "btc", "eth")
_FORBIDDEN = (
    (re.compile(r"\$\s*\d"), "a dollar figure"),
    (re.compile(r"\b(positions|holdings|balance|portfolio|qty|quantity)\b", re.I), "a position field"),
    (re.compile(r"-----BEGIN|privateKey|api[_-]?key|secret", re.I), "key material"),
    (re.compile(r"\br[1-9A-HJ-NP-Za-km-z]{24,34}\b"), "an XRPL address"),
    (re.compile(r"\b0x[0-9a-fA-F]{20,}\b"), "an EVM address or blob"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "an email address"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "an IP address"),
)


def publishable(payload: Dict[str, Any]) -> None:
    """Raise unless this payload is safe to publish to a permanent public ledger.

    THE ASYMMETRY THAT MAKES THIS STRICT. A local record can be redacted; the
    XRP Ledger cannot. There is no delete, no rewrite, and no support line. So
    the test is not "is this sensitive today" but "would I be content for this
    to be readable by anyone, for ever". The commitment hash passes that. The
    thing it commits to does not, which is why only the hash goes.
    """
    if not isinstance(payload, dict):
        raise XRPLRecordError("payload must be a dict")
    blob = json.dumps(payload, sort_keys=True)
    if len(blob.encode("utf-8")) > MAX_MEMO_BYTES:
        raise XRPLRecordError(
            f"payload is {len(blob.encode('utf-8'))} bytes, over the {MAX_MEMO_BYTES}-byte "
            f"limit -- a record memo carries a commitment, not a decision")
    for rx, what in _FORBIDDEN:
        m = rx.search(blob)
        if m:
            raise XRPLRecordError(
                f"payload contains {what} ({m.group(0)[:24]!r}) and will not be "
                f"published to a permanent public ledger. Commit to it with a "
                f"hash and keep the thing itself under ~/.covenant/decisions/.")
    low = blob.lower()
    for t in _TICKERS:
        if re.search(r'"\s*%s\s*"|\b%s\b\s*:' % (t, t), low):
            raise XRPLRecordError(
                f"payload names the asset {t.upper()} as a field -- a public "
                f"per-asset record is a portfolio disclosure (KNOWN_ISSUES A50)")
    return None


def _refuse_if_inside_repo(path: str) -> None:
    """A seed inside the published repository is a lost account, not a risk."""
    try:
        p = os.path.realpath(path)
        repo = os.path.realpath(HERE)
        if p == repo or p.startswith(repo + os.sep):
            raise XRPLRecordError(
                f"the XRPL seed is inside the repository ({path}). This "
                f"repository is published. Move it to ~/.covenant/ and never "
                f"put it back -- 'move it to X' where X is the refused path is "
                f"not advice.")
    except OSError:
        pass


def load_seed(path: str = SEED_PATH, require_strict_perms: bool = False) -> str:
    _refuse_if_inside_repo(path)
    from covenant_xrp_signer import _read_seed_file, XRPSignerError
    try:
        return _read_seed_file(path, require_strict_perms)
    except XRPSignerError as e:
        raise XRPLRecordError(str(e)) from None


def networks() -> Dict[str, str]:
    from covenant_xrp_signer import NETWORKS
    return dict(NETWORKS)


# ------------------------------------------------------------------ the write
def build(commitment: str, kind: str = "trade_decision", at: Optional[int] = None,
          seed: Optional[str] = None, address: Optional[str] = None):
    """The unsigned AccountSet and the payload it carries. No network, no key
    needed when `address` is supplied -- which is what the offline tests use."""
    from xrpl.models.transactions import AccountSet, Memo
    payload = {"k": kind, "c": str(commitment), "t": int(at if at is not None else time.time())}
    publishable(payload)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if address is None:
        from xrpl.wallet import Wallet
        address = Wallet.from_seed(seed or load_seed()).classic_address
    memo = Memo(memo_type=MEMO_TYPE.encode().hex().upper(),
                memo_format=MEMO_FORMAT.encode().hex().upper(),
                memo_data=blob.encode().hex().upper())
    return AccountSet(account=address, memos=[memo]), payload


def record(commitment: str, kind: str = "trade_decision", network: str = "testnet",
           dry_run: bool = True, allow_mainnet: bool = False,
           seed_path: str = SEED_PATH, at: Optional[int] = None) -> Dict[str, Any]:
    """Write one commitment to the XRP Ledger. Returns a dict; raises only on a
    refusal that the caller must not paper over (an unpublishable payload, a
    seed in the repository, mainnet without consent).

    dry_run=True builds and signs and returns the blob WITHOUT submitting, so
    what you inspect is what would have gone out."""
    nets = networks()
    if network not in nets:
        raise XRPLRecordError(f"unknown network {network!r}; choose one of {', '.join(nets)}")
    if network == "mainnet" and not allow_mainnet:
        raise XRPLRecordError(
            "network='mainnet' requires allow_mainnet=True as a separate, explicit "
            "argument. A record on mainnet is permanent and public; one config "
            "value should not be the only thing between this and for ever.")
    seed = load_seed(seed_path)
    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import Wallet
    from xrpl.transaction import autofill_and_sign

    wallet = Wallet.from_seed(seed)
    client = JsonRpcClient(nets[network])
    tx, payload = build(commitment, kind, at=at, address=wallet.classic_address)
    signed = autofill_and_sign(tx, client, wallet)
    out = {"ok": None, "network": network, "account": wallet.classic_address,
           "payload": payload, "dry_run": bool(dry_run),
           "fee_drops": getattr(signed, "fee", None)}
    if dry_run:
        out["ok"] = True
        out["detail"] = "dry run: signed, not submitted"
        return out
    from xrpl.transaction import submit_and_wait
    resp = submit_and_wait(signed, client, wallet)
    res = resp.result if hasattr(resp, "result") else {}
    engine = (res.get("meta") or {}).get("TransactionResult") or res.get("engine_result")
    out.update({"ok": engine == "tesSUCCESS", "tx_hash": res.get("hash"),
                "engine_result": engine, "validated": bool(res.get("validated")),
                "ledger_index": res.get("ledger_index")})
    out["detail"] = f"{engine} in ledger {out.get('ledger_index')}"
    if out["ok"]:
        note_write({"c": payload["c"], "k": payload["k"], "t": payload["t"],
                    "network": network, "tx_hash": out.get("tx_hash"),
                    "ledger_index": out.get("ledger_index"),
                    "account": wallet.classic_address})
    return out


def record_or_note(commitment: str, kind: str = "trade_decision", **kw) -> Dict[str, Any]:
    """record(), but a failure is a reported note rather than an exception.

    For the seal path: the XRP write is the DURABLE half, not the deciding
    half. A ledger that cannot be reached must not stop a decision that the
    judges already admitted -- it must be said out loud and tried again."""
    try:
        return record(commitment, kind, **kw)
    except Exception as e:                                       # noqa: BLE001
        return {"ok": False, "detail": f"{type(e).__name__}: {str(e)[:200]}",
                "payload": None, "network": kw.get("network", "testnet")}


# ------------------------------------------------------------------ proving it
INDEX_PATH = os.environ.get("COVENANT_XRPL_INDEX") or os.path.join(
    os.path.expanduser("~"), ".covenant", "xrpl_records.jsonl")

DECISIONS_DIR = os.path.join(os.path.expanduser("~"), ".covenant", "decisions")


def commitment_of_file(path: str) -> str:
    """The commitment a snapshot file produces, recomputed from its bytes.

    THIS IS THE HALF THAT MAKES THE OTHER HALF MEAN ANYTHING. Writing a hash to
    a public ledger proves only that somebody wrote a number. What makes it
    evidence is being able to hand a stranger the snapshot and have him derive
    the same number himself. covenant_trader.seal_decision writes the exact
    bytes it hashed, so this is a re-read, not a reconstruction -- there is no
    re-serialisation step here that could disagree with the original.
    """
    import hashlib
    with open(path, "rb") as fh:
        return str(int(hashlib.sha256(fh.read()).hexdigest(), 16))


def find_snapshot(commitment: str, decisions_dir: str = DECISIONS_DIR) -> Optional[str]:
    """The snapshot file whose bytes produce this commitment, or None.

    A ledger memo carries the commitment and its own write time, not the
    snapshot's filename, so the link is established by recomputation rather
    than by trusting a name. That is the correct direction: a filename can be
    changed by anyone, a preimage cannot be invented."""
    c = str(commitment).strip()
    try:
        names = sorted(os.listdir(decisions_dir), reverse=True)
    except OSError:
        return None
    for n in names:
        if not n.endswith(".json"):
            continue
        f = os.path.join(decisions_dir, n)
        try:
            if commitment_of_file(f) == c:
                return f
        except OSError:
            continue
    return None


def note_write(entry: Dict[str, Any], path: str = INDEX_PATH) -> None:
    """Append one successful ledger write to a local index. Best effort: the
    ledger is the record, this is only a finding aid, and a failure to write it
    must never look like a failure to record."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def verify(commitment: Optional[str] = None, snapshot: Optional[str] = None,
           decisions_dir: str = DECISIONS_DIR) -> Dict[str, Any]:
    """Prove (or fail to prove) that a snapshot and a commitment are the same
    decision. Give it either, or both.

      --verify <file>            -> the commitment that file produces
      --verify-commitment <n>    -> the file that produces it, if it is here
    """
    out: Dict[str, Any] = {"commitment": None, "snapshot": None, "matches": None}
    if snapshot:
        out["snapshot"] = snapshot
        out["commitment"] = commitment_of_file(snapshot)
        if commitment is not None:
            out["matches"] = out["commitment"] == str(commitment).strip()
        return out
    if commitment:
        out["commitment"] = str(commitment).strip()
        f = find_snapshot(out["commitment"], decisions_dir)
        out["snapshot"] = f
        out["matches"] = f is not None
        return out
    raise XRPLRecordError("verify() needs a commitment, a snapshot path, or both")


# ------------------------------------------------------------------ self-test
def _self_test() -> int:
    fails = []

    def check(cond, label):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    A = "rBTwLga3i4gz4bV2jXcRPGGBB3hEHVdVwv"          # a valid checksummed address
    ok_payload = {"k": "trade_decision", "c": "1" * 78, "t": 1788700000}
    try:
        publishable(ok_payload)
        check(True, "P1 a commitment payload is publishable")
    except XRPLRecordError as e:
        check(False, f"P1 a commitment payload is publishable ({e})")

    for bad, why in (
            ({"k": "x", "positions": {"a": 1}}, "P2 a positions field is refused"),
            ({"k": "x", "c": "1", "note": "$3,860.99 total"}, "P3 a dollar figure is refused"),
            ({"k": "x", "XRP": 3155.41}, "P4 a ticker field is refused"),
            ({"k": "x", "c": "1", "who": "a@b.com"}, "P5 an email is refused"),
            ({"k": "x", "c": "1", "from": "73.150.40.24"}, "P6 an IP is refused"),
            ({"k": "x", "c": "1", "key": "-----BEGIN EC PRIVATE KEY-----"}, "P7 key material is refused"),
            ({"k": "x", "c": "1", "pad": "z" * 600}, "P8 an oversized payload is refused")):
        try:
            publishable(bad)
            check(False, why)
        except XRPLRecordError:
            check(True, why)

    tx, payload = build("12345", "trade_decision", at=1788700000, address=A)
    check(tx.account == A and len(tx.memos) == 1, "B1 build makes one AccountSet with one memo")
    m = tx.memos[0]
    memo = m.memo if hasattr(m, "memo") else m
    data = bytes.fromhex(memo.memo_data).decode()
    check(json.loads(data) == payload, "B2 the memo decodes back to exactly the payload")
    check(bytes.fromhex(memo.memo_type).decode() == MEMO_TYPE, "B3 the memo is typed covenant/record")
    check("Destination" not in tx.to_dict(), "B4 no destination: AccountSet is a no-op that only carries the memo")

    try:
        record("1", network="mainnet", seed_path=os.path.join(HERE, "nope"))
        check(False, "R1 mainnet without allow_mainnet is refused")
    except XRPLRecordError as e:
        check("allow_mainnet" in str(e), "R1 mainnet without allow_mainnet is refused")
    try:
        load_seed(os.path.join(HERE, "xrpl_seed"))
        check(False, "R2 a seed inside the repository is refused")
    except XRPLRecordError as e:
        check("published" in str(e), "R2 a seed inside the repository is refused")
    r = record_or_note("1", seed_path=os.path.join(HERE, "does_not_exist_xyz"))
    check(r["ok"] is False and "detail" in r,
          "R3 record_or_note reports a failure instead of raising into the seal path")

    import hashlib
    import tempfile
    d = tempfile.mkdtemp()
    snap = os.path.join(d, "1788700000.json")
    raw = b'{"at":"2026-09-06","orders":[],"total":1}'
    with open(snap, "wb") as fh:
        fh.write(raw)
    want = str(int(hashlib.sha256(raw).hexdigest(), 16))
    check(commitment_of_file(snap) == want, "V1 a snapshot's commitment is recomputed from its bytes")
    check(find_snapshot(want, d) == snap, "V2 a commitment finds its snapshot by recomputation, not by filename")
    check(find_snapshot("999", d) is None, "V3 a commitment with no matching snapshot finds nothing")
    v = verify(commitment=want, snapshot=snap)
    check(v["matches"] is True, "V4 verify() confirms a snapshot and a commitment are the same decision")
    v = verify(commitment="123", snapshot=snap)
    check(v["matches"] is False, "V5 ...and says so plainly when they are not")
    idx = os.path.join(d, "idx.jsonl")
    note_write({"c": want, "tx_hash": "ABC"}, idx)
    check(json.loads(open(idx, encoding="utf-8").readline())["tx_hash"] == "ABC",
          "V6 a successful write is noted locally as a finding aid")
    note_write({"c": "1"}, os.path.join(d, "no", "such", "dir", "x.jsonl"))
    check(True, "V7 a failed index write is swallowed: the ledger is the record, this is not")

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        return 1
    print("XRPL RECORD: all passed (offline; no key was created, nothing was submitted)")
    return 0


def main() -> int:
    a = sys.argv[1:]
    if "--self-test" in a:
        return _self_test()
    if "--address" in a:
        from xrpl.wallet import Wallet
        print(Wallet.from_seed(load_seed()).classic_address)
        return 0
    if "--preview" in a:
        # OFFLINE, AND THAT IS THE POINT. dry_run still signs, which needs the
        # account to exist and a network round trip for sequence and fee -- so
        # it cannot answer "what would this publish?" before an account exists.
        # This can: no key, no network, no account. Look at the bytes first.
        i = a.index("--preview")
        c = a[i + 1] if len(a) > i + 1 else "0" * 8
        addr = a[a.index("--as") + 1] if "--as" in a else "rBTwLga3i4gz4bV2jXcRPGGBB3hEHVdVwv"
        tx, payload = build(c, at=0, address=addr)
        m = tx.memos[0]
        memo = m.memo if hasattr(m, "memo") else m
        print(json.dumps({"payload": payload,
                          "memo_type": bytes.fromhex(memo.memo_type).decode(),
                          "memo_bytes": len(bytes.fromhex(memo.memo_data)),
                          "published_text": bytes.fromhex(memo.memo_data).decode(),
                          "transaction": tx.to_dict()}, indent=2))
        print("\nThis is everything that would appear on a public ledger, for ever.")
        return 0
    if "--verify" in a:
        i = a.index("--verify")
        print(json.dumps(verify(snapshot=a[i + 1]), indent=2))
        return 0
    if "--verify-commitment" in a:
        i = a.index("--verify-commitment")
        out = verify(commitment=a[i + 1])
        print(json.dumps(out, indent=2))
        return 0 if out["matches"] else 1
    if "--record" in a:
        i = a.index("--record")
        commitment = a[i + 1] if len(a) > i + 1 else str(int(time.time()))
        net = a[a.index("--network") + 1] if "--network" in a else "testnet"
        out = record(commitment, network=net, dry_run="--live" not in a,
                     allow_mainnet="--allow-mainnet" in a)
        print(json.dumps(out, indent=2)[:1200])
        return 0 if out.get("ok") else 1
    print(__doc__.strip().splitlines()[1])
    print("  --self-test   offline checks, no network and no keys")
    print("  --address     the account the seed names")
    print("  --record C [--network testnet] [--live]")
    print("  --preview C [--as <addr>]       exactly what would be published; no key, no network")
    print("  --verify <snapshot.json>        the commitment that file produces")
    print("  --verify-commitment <number>    the snapshot that produces it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
