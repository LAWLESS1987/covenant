#!/usr/bin/env python3
"""covenant_consent_release.py -- the owner's own declaration releases a held consent claim (2026-10-31).

WHAT IT RELEASES, AND NOTHING ELSE. covenant_preconditions turns a CLEAN that rests on a claimed consent into
"Blocked, not proven". This module is the one way out of that hold: a declaration the OWNER signed, already
recorded in an earlier block, that names this sender, this receiver and a cap on the amount. It never touches a
judge's hold or violation -- the sentinel calls it only inside the precondition branch, after a CLEAN.

THE DESIGN, and whose it is. Put to ChatGPT, Gemini, Grok, Meta AI and Tetsu in four rounds
(ops/CONSULT_CONSENT_CLAIM_2026-10-31.md); every point below is one they made or agreed to.
  - The release is the owner's own signed declaration, looked up in chain state by id. The sender can reference
    it (data.consent_ref) and can never mint it: the declarer must be a different key from the sender.
  - Two keys prove two identities, not two people (Sybil, all four). So the declarer's key must be in the ROSTER,
    bound there to the resource it declares for. A keyless owner -- the cousin's off-chain card -- stays held.
  - A closed, typed record: hashes, integers and a salt, in an exact key set. No free text, no wildcard, no
    delegation, no extra field. Single use. Revocable by the declarer. Expiring by block height, never by clock.
  - The operator gets no unilateral release. Nothing here reads node.operator_pubkeys, an env var or a local file
    other than the committed roster, so a node's own key confers nothing. What stops anyone -- the operator
    included -- releasing a claim on SOMEONE ELSE's value is the roster binding: a declaration counts only for
    the resources the roster binds to the declarer's key. "Declarer is not the sender" stops one key releasing
    its own claim. It cannot stop an owner who makes a second key and declares for it, and that is consent to
    use his OWN rostered resource, which is what a declaration is for (the second review's point).
  - Tetsu: "the owner should have a way to revoke the release if needed." That is consent_revocation.

THE ROSTER IS THE TRUST ROOT, AND IT IS EMPTY. consent_roster.json ships with no entries, so this mechanism
releases nothing until the operator decides who may admit a key to it, and how (a committed file, a chain record,
a co-signed entry). That decision is his and is not taken here. With an empty roster the gate is exactly the
tighten-only gate it was before this module existed.

DETERMINISM. Every input is the transaction, the blocks strictly before the height it lands at, the transactions
earlier in its own block (or, at admission, the mempool), and the committed roster. Block validity must agree on
every node; anything node-local here would split the chain.

WHAT IT CANNOT SEE (rule 9).
  - The declaration authorizes the TRANSACTION'S FIELDS -- this sender, this receiver, at most this amount. It
    cannot check that the prose of the held text is about the declared resource; no gate that reads words can.
  - Below covenant_unified_v8.PRECONDITION_ACTIVATION_HEIGHT blocks are not held at all, so single use there is
    enforced at admission and at local mining, not by peers. That is the hold's own reach, not a new gap.
  - The phone build does not carry this module (loaded by name, like covenant_preconditions): there the
    precondition rule is absent too, so nothing is held and nothing is released -- and a consent RECORD is
    judged as prose, as it is on an old-core node. A student that holds on one refuses that block live; one
    that convicts it cannot sync past it. A124 measures exactly that once a record is on chain.
  - Catching up (validate_block sync=True) waives every uncertain hold (A98), this one included, so single
    use, revocation, expiry and the roster are enforced on the live path and at admission, not on catch-up.
  - The bridge validates a staged block with no chain, so a block carrying a released use is refused there.
  - Each release scans chain[:h] (measured by the review: 35 ms at 4,001 blocks of 50 transactions). It runs
    only for a transaction that cites a declaration and carries a claim.
Stdlib only, pure apart from reading the roster file.
"""
import functools
import hashlib
import json
import math
import os
import re

DECLARATION = "consent_declaration"
REVOCATION = "consent_revocation"

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
# "salt", not "nonce": a data key named nonce is walked as a numeric field by the shape check and trips
# Block.mine's fast-path marker ('"nonce": 0'). The salt makes each record's content, and so its id, unique.
_SALT = re.compile(r"[0-9a-f]{32}\Z")
_DECLARATION_KEYS = frozenset({"kind", "v", "grantee", "receiver", "resource", "max_amount",
                               "expires_at_height", "salt"})
_REVOCATION_KEYS = frozenset({"kind", "v", "declaration", "salt"})
_INT_LIMIT = 2 ** 53

ROSTER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consent_roster.json")


def key_hash(text) -> str:
    """sha256 of the exact string. Used for receivers and resources, which are names, not keys."""
    return hashlib.sha256(text.encode()).hexdigest()


_MAX_PEM_CHARS = 4096          # an RSA-4096 SubjectPublicKeyInfo PEM is ~800; padding past this is not a key here
_RSA_EXPONENT = 65537


@functools.lru_cache(maxsize=1024)
def _key_id_of(pem: str):
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = serialization.load_pem_public_key(pem.encode())
        if not isinstance(key, rsa.RSAPublicKey) or key.public_numbers().e != _RSA_EXPONENT:
            return None
        canonical = key.public_bytes(serialization.Encoding.PEM,
                                     serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    except Exception:                                           # noqa: BLE001 -- not a key: no identity
        return None
    return key_hash(canonical)


def key_id(pem):
    """The identity of a KEY, not of the string that carries it: sha256 of the key re-serialized as canonical
    SubjectPublicKeyInfo PEM. For a canonical PEM this equals key_hash(pem), the convention the trading
    exception uses. Needed because tx.verify() accepts many strings for one key. The 2026-10-31 reviews
    measured that it accepts all of these:
      - a PEM without its trailing newline, with CRLF, or with a trailing space;
      - one with a leading space or a BOM;
      - a PKCS#1 'RSA PUBLIC KEY' block.
    So comparing PEM strings let a rostered owner name an altered copy of his own PEM as grantee and release
    his own claim. Every key comparison here goes through this.

    Only an RSA key with e = 65537 has an identity here. A second public key (n, e + lambda(n)) made from the
    same private key verifies, and is a second 'key' for the same signer. A huge e also costs seconds per
    verify (the second review: 5 ms per record, 25 s for a full pool under chain_lock). Every key this
    project generates uses 65537 (rsa.generate_private_key(public_exponent=65537)). None: not a key here."""
    if not isinstance(pem, str) or len(pem) > _MAX_PEM_CHARS:
        return None
    return _key_id_of(pem)


def _is_int(v) -> bool:
    return type(v) is int and 0 <= v < _INT_LIMIT


def _is_hex64(v) -> bool:
    return isinstance(v, str) and bool(_HEX64.match(v))


def record_shape(data):
    """The record kind if data is EXACTLY a declaration or a revocation, else None. Exact key set, exact types."""
    if not isinstance(data, dict):
        return None
    kind = data.get("kind")
    if kind == DECLARATION:
        keys = _DECLARATION_KEYS
    elif kind == REVOCATION:
        keys = _REVOCATION_KEYS
    else:
        return None
    if set(data) != keys or type(data.get("v")) is not int or data["v"] != 1:
        return None
    if not (isinstance(data["salt"], str) and _SALT.match(data["salt"])):
        return None
    if kind == DECLARATION:
        if not all(_is_hex64(data[k]) for k in ("grantee", "receiver", "resource")):
            return None
        if not all(_is_int(data[k]) for k in ("max_amount", "expires_at_height")):
            return None
    elif not _is_hex64(data["declaration"]):
        return None
    return kind


def _amount_ok(amount) -> bool:
    if type(amount) not in (int, float):
        return False
    try:
        return math.isfinite(amount) and amount >= 0
    except OverflowError:                                       # an int too large for a float: not an amount
        return False


def _verified(tx) -> bool:
    verify = getattr(tx, "verify", None)
    if not callable(verify):
        return False
    try:
        return verify() is True
    except Exception:                                           # noqa: BLE001 -- unverifiable is unverified
        return False


def record_kind(tx):
    """The STRUCTURAL exception's predicate: this transaction is a consent record and nothing else. All of:
    an exact record shape; a PEM sender addressed to itself; amount zero; a signature that verifies. It decides
    on facts a sender cannot forge past the signature, and a record confers nothing by itself -- only release()
    with a rostered declarer can make one matter."""
    kind = record_shape(getattr(tx, "data", None))
    if kind is None:
        return None
    sender = getattr(tx, "sender_pubkey", None)
    if key_id(sender) is None:                  # a key with an identity here, in any form verify() accepts
        return None
    if getattr(tx, "receiver", None) != sender:
        return None
    amount = getattr(tx, "amount", None)
    if not _amount_ok(amount) or amount != 0:
        return None
    return kind if _verified(tx) else None


def looks_like_record(tx) -> bool:
    """record_kind without the signature check, for ORDERING an already-admitted mempool, where every
    transaction was verified on the way in. Never a reason to admit or release anything."""
    return (record_shape(getattr(tx, "data", None)) is not None
            and getattr(tx, "receiver", None) == getattr(tx, "sender_pubkey", None)
            and getattr(tx, "amount", None) == 0)


def _tx_id(tx):
    get_id = getattr(tx, "get_id", None)
    if not callable(get_id):
        return None
    try:
        return get_id()
    except Exception:                                           # noqa: BLE001 -- no id, no match
        return None


_ROSTER_CACHE = {}


def load_roster(path=None):
    """{key_id: set(resource hashes)} from the committed roster. key_sha256 is the key_id of the key, i.e.
    sha256 of its canonical PEM. Absent, unreadable or malformed: EMPTY -- no roster, no release. Malformed
    entries are dropped one by one, never guessed at. The file is read on every call and parsed again only
    when its CONTENT changes: a cache keyed on size and mtime went stale on a same-size rewrite within one
    mtime tick (the second review: 2 of 200 back-to-back reads), and a stale roster is a node disagreeing with
    its peers on block validity."""
    path = path or ROSTER_PATH
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        stamp = hashlib.sha256(raw).hexdigest()
        cached = _ROSTER_CACHE.get(path)
        if cached and cached[0] == stamp:
            return {k: set(v) for k, v in cached[1].items()}
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return {}
    roster = {}
    entries = doc.get("entries") if isinstance(doc, dict) else None
    for entry in entries if isinstance(entries, list) else ():
        if not isinstance(entry, dict) or not _is_hex64(entry.get("key_sha256")):
            continue
        resources = entry.get("resources")
        if not isinstance(resources, list):
            continue
        good = {r for r in resources if _is_hex64(r)}
        if good:
            roster.setdefault(entry["key_sha256"], set()).update(good)
    _ROSTER_CACHE[path] = (stamp, {k: frozenset(v) for k, v in roster.items()})
    return roster


def release(tx, view, roster=None):
    """(released, reason, declaration_id). released is True only when EVERY condition holds; any other answer
    is the hold, with the first reason that failed. Never raises for a malformed tx or view.

    view = {"chain": blocks, "height": h, "prior": txs}. h is the index this tx lands at (block.index, or
    len(chain) at admission); only chain[:h] is read. prior is what came before it in the same block (or the
    mempool at admission): it counts for single use and revocation, never as the place a declaration lives."""
    data = getattr(tx, "data", None)
    ref = data.get("consent_ref") if isinstance(data, dict) else None
    if not _is_hex64(ref):
        return False, "no consent_ref naming a declaration id", None
    if not isinstance(view, dict):
        return False, "no chain view here, so no declaration can be read", ref
    chain, height, prior = view.get("chain"), view.get("height"), view.get("prior") or ()
    if not isinstance(chain, (list, tuple)) or not _is_int(height) or height > len(chain):
        return False, "the chain view does not reach this height", ref
    if not isinstance(prior, (list, tuple)):
        return False, "the chain view's prior transactions are not a list", ref
    sender, receiver, amount = (getattr(tx, "sender_pubkey", None), getattr(tx, "receiver", None),
                                getattr(tx, "amount", None))
    sender_id = key_id(sender)
    if not (sender_id and isinstance(receiver, str) and _amount_ok(amount)):
        return False, "the held transaction is not a signed transfer with a key as sender", ref
    if not _verified(tx):
        return False, "the held transaction's signature does not verify", ref
    if roster is None:
        roster = load_roster()
    if not roster:
        # Before the chain scan: with nobody rostered nothing can be released, and the scan costs ~40 ms at
        # 4,001 blocks (the second review).
        return False, "the roster is empty: no declarer's key is bound to any resource", ref

    earlier = []
    for block in chain[:height]:
        txs = getattr(block, "transactions", None)
        if not isinstance(txs, (list, tuple)):
            return False, "the chain view holds a block with no transaction list", ref
        earlier.extend(txs)
    declaration = None
    for t in earlier:
        if record_shape(getattr(t, "data", None)) == DECLARATION and _tx_id(t) == ref:
            declaration = t
            break
    if declaration is None:
        return False, "consent_ref names no declaration in an earlier block", ref
    if record_kind(declaration) != DECLARATION:
        return False, "the declaration is not a signed, valueless self-addressed record", ref
    d = declaration.data
    signer_id = key_id(declaration.sender_pubkey)
    if not signer_id or signer_id == sender_id:
        return False, "the declarer is the sender: nobody can consent for someone else's value with their own key", ref
    if d["resource"] not in roster.get(signer_id, ()):
        return False, "the declarer's key is not bound to that resource in the roster", ref
    if d["grantee"] != sender_id:
        return False, "the declaration names a different sender", ref
    if d["receiver"] != key_hash(receiver):
        return False, "the declaration names a different receiver", ref
    if amount > d["max_amount"]:
        return False, "the amount is over the declared cap", ref
    if height > d["expires_at_height"]:
        return False, "the declaration expired at height %d" % d["expires_at_height"], ref
    # Single use counts every earlier use by the grantee, this transaction's own id included: it is never in its
    # own prior (validate_block passes what precedes it, /mine what it has already packed, admission the mempool
    # it has not yet joined), so a matching id there is a replay or a duplicate, and that is a second use.
    for t in list(earlier) + list(prior):
        td = getattr(t, "data", None)
        if not isinstance(td, dict):
            continue
        if (record_shape(td) == REVOCATION and td["declaration"] == ref
                and key_id(getattr(t, "sender_pubkey", None)) == signer_id):
            return False, "the declarer revoked it", ref
        if td.get("consent_ref") == ref and key_id(getattr(t, "sender_pubkey", None)) == d["grantee"]:
            return False, "the declaration was already used (single use)", ref
    return True, "released by the owner's declaration %s" % ref[:16], ref
