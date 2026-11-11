#!/usr/bin/env python3
"""tools/receipt_interop_vectors.py -- covenant's side of the receipt interop test vectors (2026-11-04).

WHY. Public promise, Hugging Face thread 180706 post #22 (2026-10-22), to nootxlm (Agent Embassy): "I'll put our
side of the vectors up first, negatives included." The cross-check there showed raw signature-verifiability over
published bytes; it did NOT show re-derivation of the canonical bytes from the object, or tamper rejection. These
vectors are for that.

WHAT. A receipt profile, its canonicalization pinned to RFC 8785 (JCS) plus four profile rules JCS leaves open,
and vectors that each name the expected outcome:

  profile rules (on top of JCS)
    P1  duplicate member names are rejected at parse (RFC 8259 leaves them undefined; JCS assumes valid input)
    P2  every string (names and values) must already be Unicode NFC; non-NFC is rejected, never normalized
    P3  a number TOKEN whose magnitude exceeds 2^53-1 is rejected, in any spelling (9007199254740993,
        9.007199254740993e15, 1e21, -9007199254740993). Checked on the token with exact decimal arithmetic,
        before any conversion to a double. Carry such values as strings
    P4  the proof is excluded at the TOP LEVEL only ("proof" member); a nested "proof" is signed content
    P5  ECDSA signatures must be low-s (EIP-2); a high-s twin is rejected even though it recovers
    P6  a relying party accepts a receipt only if  (a) domain is the one it expects, (b) audience is itself,
        (c) chain_id is the one it requires, and (d) (signer, nonce) is unseen -- and it records the pair on
        acceptance, so a second presentation is a replay. Each is checked and reported separately. A nonce is
        only as good as this consumption rule, and the rule requires the check-and-record to be atomic and
        durable; the vectors cannot test that, a verifier's own tests must.

    P7  each signer's framing is pinned in the discovery document; a verifier never falls back to the other one

  signing framing, one test key per framing, so each side can test its own:
    "hex-text"     EIP-191 personal_sign over the 64-char lowercase hex of SHA-256(canonical) -- covenant's framing
    "digest-bytes" EIP-191 personal_sign over the raw 32-byte SHA-256 -- Agent Embassy's framing

TEST KEYS ONLY. The keys below are derived from public phrases so anyone can reproduce every signature. They are
not covenant's receipt signer (ops/receipt_signer.*) and must never sign anything real.

HONEST SCOPE. covenant's production receipts (covenant_receipt.canonical) still canonicalize as Python
json.dumps(sort_keys, separators, ensure_ascii=False), NOT JCS. Each vector also carries that "current" form and
says whether it differs, so the vectors test a target, not a format we already run.

CHECKED TWO WAYS before any vector is written: the JCS serializer is run against RFC 8785's own samples
(Appendix B number table, the 3.2.3 sorting example, the 3.2.4 byte sequence); every vector's expected outcome is
then re-checked by an independent verifier pass, and --mutate turns each profile rule off in turn to show the
vector that guards it go red.

    .venv/Scripts/python.exe tools/receipt_interop_vectors.py            # self-check, write the vectors
    .venv/Scripts/python.exe tools/receipt_interop_vectors.py --mutate   # drive each rule both ways
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "interop" / "RECEIPT_VECTORS_v1.json"
MAX_SAFE = 2 ** 53 - 1
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

RULES = {"P1": True, "P2": True, "P3": True, "P4": True, "P5": True,
         "P6a": True, "P6b": True, "P6c": True, "P6d": True, "P7": True}   # --mutate flips one at a time


class Reject(ValueError):
    pass


# ---------------------------------------------------------------- strict parse (P1) ----------------------------
def _pairs(pairs):
    seen, out = set(), {}
    for k, v in pairs:
        if k in seen and RULES["P1"]:
            raise Reject("P1 duplicate member name %r" % k)
        seen.add(k)
        out[k] = v
    return out


def _p3_token(tok: str):
    """P3 on the number token itself, with exact decimal arithmetic, before anything becomes a double."""
    from decimal import Decimal
    d = Decimal(tok)
    if RULES["P3"] and abs(d) > MAX_SAFE:
        raise Reject("P3 number token %s has magnitude above 2^53-1; carry it as a string" % tok)
    return d


def parse(text: str):
    def bad_const(c):
        raise Reject("non-finite number %s" % c)

    def p_int(tok):
        _p3_token(tok)
        return int(tok)

    def p_float(tok):
        _p3_token(tok)
        return float(tok)
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=bad_const, parse_int=p_int, parse_float=p_float)


# ---------------------------------------------------------------- JCS (RFC 8785) -------------------------------
def _es_number(x) -> str:
    """ECMAScript Number::toString, as JCS 3.2.2.3 requires."""
    if isinstance(x, bool):
        raise TypeError
    if isinstance(x, int):
        if RULES["P3"] and abs(x) > MAX_SAFE:
            raise Reject("P3 integer %d outside +-(2^53-1); carry it as a string" % x)
        x = float(x)                                           # JCS coerces through an IEEE-754 double
    if math.isnan(x) or math.isinf(x):
        raise Reject("non-finite number")
    if x == 0:
        return "0"                                             # includes -0
    sign = "-" if x < 0 else ""
    r = repr(abs(x))                                           # shortest round-trip digits
    if "e" in r:
        mant, exp = r.split("e")
        exp = int(exp)
    else:
        mant, exp = r, 0
    if "." in mant:
        ip, fp = mant.split(".")
    else:
        ip, fp = mant, ""
    digits = (ip + fp).lstrip("0")
    lead_zeros = len(ip + fp) - len((ip + fp).lstrip("0"))
    n = len(ip) + exp - lead_zeros                             # value = 0.digits * 10^n
    digits = digits.rstrip("0") or "0"
    k = len(digits)
    if k <= n <= 21:
        s = digits + "0" * (n - k)
    elif 0 < n <= 21:
        s = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        s = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        es = ("+" if e >= 0 else "-") + str(abs(e))
        s = (digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + es)
    return sign + s


_ESC = {0x08: "\\b", 0x09: "\\t", 0x0A: "\\n", 0x0C: "\\f", 0x0D: "\\r", 0x22: '\\"', 0x5C: "\\\\"}


def _es_string(s: str) -> str:
    if RULES["P2"] and any(0xD800 <= ord(ch) <= 0xDFFF for ch in s):
        raise Reject("P2 string holds a lone surrogate, which is not valid Unicode (RFC 8785 requires I-JSON)")
    if RULES["P2"] and unicodedata.normalize("NFC", s) != s:
        raise Reject("P2 string is not NFC: %r" % s)
    out = []
    for ch in s:
        c = ord(ch)
        if c in _ESC:
            out.append(_ESC[c])
        elif c < 0x20:
            out.append("\\u%04x" % c)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _utf16_key(s: str):
    return list(s.encode("utf-16-be"))   # big-endian bytes compare as code units


def jcs(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return _es_number(v)
    if isinstance(v, str):
        return _es_string(v)
    if isinstance(v, list):
        return "[" + ",".join(jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v, key=_utf16_key)
        return "{" + ",".join(_es_string(k) + ":" + jcs(v[k]) for k in keys) + "}"
    raise TypeError(type(v))


def canonical_jcs(receipt: dict) -> bytes:
    body = {k: v for k, v in receipt.items() if k != "proof"} if RULES["P4"] else _strip_proof_deep(receipt)
    try:
        return jcs(body).encode("utf-8")
    except UnicodeEncodeError as e:            # reached only when P2 is off: a lone surrogate gets this far
        raise Reject("UTF-8 encoding failed: %s" % e)


def _strip_proof_deep(v):
    """What P4 forbids: recursive proof exclusion (used only by --mutate)."""
    if isinstance(v, dict):
        return {k: _strip_proof_deep(x) for k, x in v.items() if k != "proof"}
    if isinstance(v, list):
        return [_strip_proof_deep(x) for x in v]
    return v


def canonical_current(receipt: dict) -> bytes:
    """covenant_receipt.canonical as it is today (not JCS)."""
    body = {k: v for k, v in receipt.items() if k != "proof"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------- RFC 8785 self-check --------------------------
RFC_B = [("0000000000000000", "0"), ("8000000000000000", "0"), ("0000000000000001", "5e-324"),
         ("8000000000000001", "-5e-324"), ("7fefffffffffffff", "1.7976931348623157e+308"),
         ("ffefffffffffffff", "-1.7976931348623157e+308"), ("4340000000000000", "9007199254740992"),
         ("c340000000000000", "-9007199254740992"), ("4430000000000000", "295147905179352830000"),
         ("7fffffffffffffff", None), ("7ff0000000000000", None),
         ("44b52d02c7e14af5", "9.999999999999997e+22"), ("44b52d02c7e14af6", "1e+23"),
         ("44b52d02c7e14af7", "1.0000000000000001e+23"), ("444b1ae4d6e2ef4e", "999999999999999700000"),
         ("444b1ae4d6e2ef4f", "999999999999999900000"), ("444b1ae4d6e2ef50", "1e+21"),
         ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"), ("3eb0c6f7a0b5ed8d", "0.000001"),
         ("41b3de4355555553", "333333333.3333332"), ("41b3de4355555554", "333333333.33333325"),
         ("41b3de4355555555", "333333333.3333333"), ("41b3de4355555556", "333333333.3333334"),
         ("41b3de4355555557", "333333333.33333343"), ("becbf647612f3696", "-0.0000033333333333333333"),
         ("43143ff3c1cb0959", "1424953923781206.2")]
RFC_SORT_IN = ('{"\\u20ac":"Euro Sign","\\r":"Carriage Return","\\ufb33":"Hebrew Letter Dalet With Dagesh",'
               '"1":"One","\\ud83d\\ude00":"Emoji: Grinning Face","\\u0080":"Control",'
               '"\\u00f6":"Latin Small Letter O With Diaeresis"}')
RFC_SORT_OUT = ["Carriage Return", "One", "Control", "Latin Small Letter O With Diaeresis", "Euro Sign",
                "Emoji: Grinning Face", "Hebrew Letter Dalet With Dagesh"]
RFC_324_IN = ('{"numbers":[333333333.33333329,1E30,4.50,2e-3,0.000000000000000000000000001],'
              '"string":"\\u20ac$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/","literals":[null,true,false]}')
RFC_324_HEX = ("7b226c69746572616c73223a5b6e756c6c2c747275652c66616c73655d2c226e756d62657273223a"
               "5b3333333333333333332e333333333333332c31652b33302c342e352c302e3030322c31652d3237"
               "5d2c22737472696e67223a22e282ac245c75303030665c6e4127425c225c5c5c5c5c222f227d")


def rfc_selfcheck():
    """Plain JCS against the RFC's samples, so the profile rules are off for its duration: the 3.2.3 sorting sample
    contains U+FB33, which is not NFC-stable (NFC maps it to U+05D3 U+05BC), so P2 would refuse an input that plain
    JCS accepts. That is a real cost of P2 and is recorded in the vectors file."""
    saved = dict(RULES)
    RULES.update({k: False for k in RULES})
    try:
        return _rfc_selfcheck()
    finally:
        RULES.update(saved)


def _rfc_selfcheck():
    fails = []
    for hx, want in RFC_B:
        x = struct.unpack(">d", bytes.fromhex(hx))[0]
        try:
            got = _es_number(x)
        except Reject:
            got = None
        if got != want:
            fails.append("B %s: got %r want %r" % (hx, got, want))
    sorted_vals = [json.loads(jcs(parse(RFC_SORT_IN)))[k] for k in json.loads(jcs(parse(RFC_SORT_IN)))]
    if sorted_vals != RFC_SORT_OUT:
        fails.append("3.2.3 sort order %r" % sorted_vals)
    got = jcs(parse(RFC_324_IN)).encode("utf-8").hex()
    if got != RFC_324_HEX:
        fails.append("3.2.4 bytes differ")
    return len(RFC_B) + 2, fails


# ---------------------------------------------------------------- signing --------------------------------------
def _acct(phrase):
    from eth_account import Account
    return Account.from_key(hashlib.sha256(phrase.encode()).digest())


KEY_A = "covenant receipt interop TEST KEY A -- never sign anything real"      # pinned to hex-text
KEY_C = "covenant receipt interop TEST KEY C -- never sign anything real"      # pinned to digest-bytes
KEY_B = "covenant receipt interop TEST KEY B -- never sign anything real"      # in no discovery document


def _msg(digest: bytes, framing: str):
    from eth_account.messages import encode_defunct
    return encode_defunct(text=digest.hex()) if framing == "hex-text" else encode_defunct(primitive=digest)


def sign(cbytes: bytes, acct, framing: str) -> dict:
    from eth_account import Account
    sig = Account.sign_message(_msg(hashlib.sha256(cbytes).digest(), framing), acct.key).signature.hex()
    return {"signer": acct.address, "signature": sig if sig.startswith("0x") else "0x" + sig}


def sign_both(cbytes: bytes) -> list:
    """One signature per discovered signer, each under the framing its discovery entry pins."""
    return [sign(cbytes, _acct(KEY_A), "hex-text"), sign(cbytes, _acct(KEY_C), "digest-bytes")]


def discovery_document():
    return {"signers": [{"address": _acct(KEY_A).address, "scheme": "eip191-personal-sign", "framing": "hex-text"},
                        {"address": _acct(KEY_C).address, "scheme": "eip191-personal-sign", "framing": "digest-bytes"}],
            "test_only": True,
            "rule": "P7: a verifier takes the framing from this document, by signer, and never tries the other one"}


def high_s_twin(entry: dict) -> dict:
    b = bytes.fromhex(entry["signature"][2:])
    r, s, v = b[:32], int.from_bytes(b[32:64], "big"), b[64]
    s2 = SECP256K1_N - s
    v2 = 27 if v == 28 else 28
    return {"signer": entry["signer"], "signature": "0x" + (r + s2.to_bytes(32, "big") + bytes([v2])).hex()}


def verify(canonical_hex: str, entry: dict, discovery: dict):
    """(accept, reason) for one signature, statelessly: the claimed signer must be in the discovery document;
    low-s; recovery under the framing the document pins for that signer (P7) must give that signer."""
    from eth_account import Account
    pinned = {s["address"].lower(): s["framing"] for s in discovery["signers"]}
    claimed = str(entry.get("signer", "")).lower()
    if claimed not in pinned:
        return False, "signer %s is not in the discovery document" % entry.get("signer")
    sb = bytes.fromhex(entry["signature"][2:])
    if RULES["P5"] and int.from_bytes(sb[32:64], "big") > SECP256K1_N // 2:
        return False, "P5 high-s signature"
    digest = hashlib.sha256(bytes.fromhex(canonical_hex)).digest()
    framings = [pinned[claimed]] if RULES["P7"] else ["hex-text", "digest-bytes"]    # P7 off = the fallback
    last = "unrecoverable"
    for fr in framings:
        try:
            rec = Account.recover_message(_msg(digest, fr), signature=entry["signature"])
        except Exception as e:                                 # noqa: BLE001
            last = "unrecoverable: %s" % e
            continue
        if rec.lower() == claimed:
            return True, "recovers to the claimed, discovered signer under its pinned framing"
        last = "recovers to %s under %s, not the claimed %s" % (rec, fr, entry.get("signer"))
    return False, last


class RelyingParty:
    """P6, the consumption rule that makes a nonce mean anything."""
    def __init__(self, me, domain, chain):
        self.me, self.domain, self.chain, self.seen = me, domain, chain, set()

    def accept(self, receipt: dict, signer: str):
        if RULES["P6a"] and receipt.get("domain") != self.domain:
            return False, "P6a domain %r is not %r" % (receipt.get("domain"), self.domain)
        if RULES["P6b"] and receipt.get("audience") != self.me:
            return False, "P6b audience %r is not this relying party %r" % (receipt.get("audience"), self.me)
        if RULES["P6c"] and receipt.get("chain_id") != self.chain:
            return False, "P6c chain_id %r is not the required %r" % (receipt.get("chain_id"), self.chain)
        if RULES["P6d"] and not receipt.get("nonce"):
            return False, "P6d no nonce: a missing nonce is not a fresh one"
        key = (signer.lower(), receipt.get("nonce"))
        if RULES["P6d"] and key in self.seen:
            return False, "P6d replay: (signer, nonce) already accepted"
        self.seen.add(key)
        return True, "accepted and (signer, nonce) recorded"


# ---------------------------------------------------------------- the vectors ----------------------------------
BASE = {"domain": "covenant-earn-receipt/v1", "audience": "aemb.pro", "chain_id": "eip155:8453",
        "nonce": "6f1d0c3a9b8e4f20a7c5d1e3b2f40986", "id": "cov-vec-base", "offer": "receipt",
        "amount_usdc": "0.020000", "authorization": "authorized", "t": "2026-11-04T12:00:00Z"}


def _with(**kw):
    """A receipt like BASE with its own nonce (derived from its id), so no two vectors share a (signer, nonce)."""
    r = dict(BASE)
    r.update(kw)
    if "nonce" not in kw:
        r["nonce"] = hashlib.sha256(r["id"].encode()).hexdigest()[:32]
    return r


def lenient_bytes(text: str):
    """The bytes a NON-conforming verifier computes: P1-P3 off (last duplicate wins, no NFC or surrogate check, numbers
    through a double), then JCS. Reject vectors are signed over these, so that a verifier missing the rule would
    accept them and only the rule can reject. None when no UTF-8 bytes can exist (a lone surrogate)."""
    saved = dict(RULES)
    RULES.update({"P1": False, "P2": False, "P3": False})
    try:
        return canonical_jcs(parse(text))
    except Reject:
        return None
    finally:
        RULES.update(saved)


def raw_cases():
    """(id, what, input JSON TEXT as a relying party would receive it, expected 'accept'|'reject', why)."""
    j = lambda o: json.dumps(o, ensure_ascii=False)
    return [
        ("V01-base", "a plain receipt in the profile", j(BASE), "accept", "control"),
        ("V02-float", "numbers JCS spells differently from Python",
         j(_with(id="cov-vec-float", metrics={"one": 1.0, "tenth": 0.1, "big": 4.5e15, "small": 1e-7, "negzero": -0.0})),
         "accept", "JCS: 1, 0.1, 4500000000000000, 1e-7, 0"),
        ("V03-int-safe-as-string", "an integer past 2^53-1 carried as a string",
         j(_with(id="cov-vec-bigint-str", amount_atomic="9007199254740993")), "accept", "P3"),
        ("V04-int-unsafe-as-number", "the same integer as a JSON number",
         '{"amount_atomic":9007199254740993,' + j(_with(id="cov-vec-bigint-num"))[1:], "reject",
         "P3 -- through a double it would silently become 9007199254740992"),
        ("V05-nfc", "a non-ASCII string in NFC", j(_with(id="cov-vec-nfc", memo="café")), "accept", "P2"),
        ("V06-nfd", "the same string in NFD (e + combining acute)", j(_with(id="cov-vec-nfd", memo="café")),
         "reject", "P2 -- JCS keeps it as is, so the digest would differ from V05's"),
        ("V07-control", "control characters, DEL and U+2028 in a value",
         j(_with(id="cov-vec-ctrl", memo="a\nb\tc\u0007d\u001fe\u007ff g")), "accept",
         "JCS escaping: \\n \\t \\u0007 \\u001f; DEL and U+2028 raw"),
        ("V08-key-order", "non-ASCII member names (UTF-16 order differs from code-point order)",
         j(_with(id="cov-vec-keys", tags={"z": 1, "€": 2, "\U0001F600": 3, "ﬁ": 4})), "accept",
         "JCS: z, €, \U0001F600, ﬁ (code-point order would put ﬁ before \U0001F600)"),
        ("V09-duplicate", "a duplicate member name in the raw text",
         '{"amount_usdc":"0.020000","amount_usdc":"9.990000",' + j(_with(id="cov-vec-dup"))[1:].replace(
             '"amount_usdc": "0.020000", ', ""), "reject", "P1 -- a lenient parser keeps the last value silently"),
        ("V10-nested-proof", "a nested member named proof is signed content",
         j(_with(id="cov-vec-nested", meta={"proof": "citation-check-7", "files": 2})), "accept",
         "P4 -- only the top-level proof is excluded"),
        ("V11-int-unsafe-exponent", "the unsafe integer of V04 spelled in exponent form",
         '{"amount_atomic":9.007199254740993e15,' + j(_with(id="cov-vec-bigint-exp"))[1:], "reject",
         "P3 on the token -- a check made after parsing to a double sees 9007199254740992 and passes it"),
        ("V12-duplicate-escaped", "a duplicate member name, the second spelled with a \\u escape",
         '{"memo":"first","\\u006demo":"second",' + j(_with(id="cov-vec-dup-esc"))[1:], "reject",
         "P1 -- names are compared after unescaping"),
        ("V14-lone-surrogate", "a value holding a lone high surrogate, written as a JSON \\u escape",
         '{"memo":"x\\ud800y",' + j(_with(id="cov-vec-surrogate"))[1:], "reject",
         "P2 -- not a valid Unicode scalar value, so not valid UTF-8; JCS assumes I-JSON"),
        ("V15-int-boundary", "2^53-1 as a JSON number, the largest P3 allows",
         '{"amount_atomic":9007199254740991,' + j(_with(id="cov-vec-boundary"))[1:], "accept",
         "P3 boundary -- a verifier that rejects every large number would fail this"),
        ("V16-int-unsafe-negative", "-(2^53+1) as a JSON number",
         '{"amount_atomic":-9007199254740993,' + j(_with(id="cov-vec-bigint-neg"))[1:], "reject",
         "P3 -- the bound is on magnitude"),
        ("V17-nfd-member-name", "a member NAME in NFD",
         j(_with(id="cov-vec-nfd-name", tags={"cafe\u0301": 1})), "reject",
         "P2 -- names are strings too"),
        ("V18-boundary-exponent", "2^53-1 spelled in exponent form",
         '{"amount_atomic":9.007199254740991e15,' + j(_with(id="cov-vec-boundary-exp"))[1:], "accept",
         "P3 boundary -- a verifier that rejects every exponent would fail this"),
        ("V19-nonint-above-bound", "a non-integer just above 2^53-1",
         '{"amount_atomic":9007199254740991.5,' + j(_with(id="cov-vec-nonint"))[1:], "reject",
         "P3 -- the bound is on magnitude, integer or not"),
        ("V20-huge-exponent", "a number far outside double range",
         '{"amount_atomic":1e400,' + j(_with(id="cov-vec-huge"))[1:], "reject",
         "P3 -- exact decimal arithmetic must reject it without converting it (a double would be Infinity)"),
        ("V13-top-level-proof", "a receipt carrying its top-level proof member",
         j(_with(id="cov-vec-toplevel-proof", proof={"scheme": "eip191-personal-sign", "note": "excluded"})),
         "accept", "P4 -- the top-level proof is excluded from the canonical bytes"),
    ]


def build():
    a, b, c = _acct(KEY_A), _acct(KEY_B), _acct(KEY_C)
    discovery = discovery_document()
    vectors = []
    for vid, what, text, expect, why in raw_cases():
        v = {"id": vid, "what": what, "input_json_text": text, "expect": expect, "why": why}
        try:
            obj = parse(text)
            cb = canonical_jcs(obj)
        except Reject as e:
            v["expect_reason"] = why.split()[0]
            v["profile_rejects_with"] = str(e)
            lb = lenient_bytes(text)
            if lb is None:
                v["lenient_bytes"] = None
                v["signatures"] = []
                v["note"] = ("a verifier without the rule cannot produce canonical bytes for this input either (no "
                             "UTF-8 encoding for a lone surrogate; a double of Infinity for 1e400), so nothing can be "
                             "signed")
            else:
                v["lenient_bytes"] = lb.decode("utf-8")
                v["signatures"] = sign_both(lb)
                v["note"] = ("signed over the bytes a verifier WITHOUT this rule computes, so such a verifier accepts "
                             "it; only the rule can reject it")
            try:
                cur = canonical_current(json.loads(text))
                v["current_production_canonical"] = cur.decode("utf-8")
                v["current_production_note"] = "covenant's current canonicalizer produces bytes for this input"
            except Exception as e2:                            # noqa: BLE001
                v["current_production_note"] = "covenant's current canonicalizer crashes on it: %s" % e2
            vectors.append(v)
            continue
        cur = canonical_current(obj)
        v["canonical_jcs"] = cb.decode("utf-8")
        v["canonical_jcs_hex"] = cb.hex()
        v["sha256_jcs"] = hashlib.sha256(cb).hexdigest()
        v["current_production_canonical_differs"] = cur != cb
        if cur != cb:
            v["current_production_canonical"] = cur.decode("utf-8")
        v["signatures"] = sign_both(cb)
        vectors.append(v)

    base = next(x for x in vectors if x["id"] == "V01-base")
    cb = base["canonical_jcs"].encode()
    negatives = []
    mutated = base["canonical_jcs"].replace('"0.020000"', '"0.020001"')
    negatives.append({"id": "N01-mutated-bytes", "what": "amount changed in the canonical bytes; V01's signatures kept",
                      "canonical_jcs": mutated, "canonical_jcs_hex": mutated.encode().hex(),
                      "signatures": base["signatures"], "expect": "reject",
                      "why": "the digest changes, so recovery yields some other address"})
    forged = sign(cb, b, "hex-text")
    forged["signer"] = a.address
    negatives.append({"id": "N02-wrong-signer", "what": "V01's bytes signed by key B (in no discovery document), presented as A's",
                      "canonical_jcs": base["canonical_jcs"], "canonical_jcs_hex": cb.hex(),
                      "signatures": [forged], "signed_by_test_key": b.address, "expect": "reject",
                      "why": "a valid signature by the wrong key recovers to B, not A"})
    negatives.append({"id": "N03-high-s", "what": "V01's signatures with s replaced by n-s and v flipped",
                      "canonical_jcs": base["canonical_jcs"], "canonical_jcs_hex": cb.hex(),
                      "signatures": [high_s_twin(e) for e in base["signatures"]], "expect": "reject",
                      "why": "P5 -- each still recovers to its signer, so only an explicit low-s rule rejects it"})
    v10 = next(x for x in vectors if x["id"] == "V10-nested-proof")
    altered = json.loads(v10["input_json_text"])
    altered["meta"]["proof"] = "citation-check-8"
    negatives.append({"id": "N04-nested-proof-altered", "what": "V10 with meta.proof changed after signing; V10's signatures kept",
                      "input_json_text": json.dumps(altered, ensure_ascii=False),
                      "signatures": v10["signatures"], "expect": "reject",
                      "why": "P4 -- nested proof is signed content; a verifier that strips 'proof' recursively accepts this"})
    negatives.append({"id": "N05-framing-not-pinned", "what": "V01's bytes signed by A under digest-bytes; A is pinned to hex-text",
                      "canonical_jcs": base["canonical_jcs"], "canonical_jcs_hex": cb.hex(),
                      "signatures": [sign(cb, a, "digest-bytes")], "expect": "reject",
                      "why": "P7 -- a verifier that falls back to the other framing would accept this"})
    negatives.append({"id": "N06-framing-not-pinned-mirror", "what": "V01's bytes signed by C under hex-text; C is pinned to digest-bytes",
                      "canonical_jcs": base["canonical_jcs"], "canonical_jcs_hex": cb.hex(),
                      "signatures": [sign(cb, c, "hex-text")], "expect": "reject",
                      "why": "P7 -- the same, in the other direction"})

    replay = {"id": "S01-replay-sequence",
              "relying_party": {"me": "aemb.pro", "domain": "covenant-earn-receipt/v1", "chain_id": "eip155:8453"},
              "note": ("run against a FRESH relying party configured as above; the only vectors that share verifier "
                       "state. Each step presents one receipt with one signer's signature; every receipt carries its "
                       "own unused nonce except where a step reuses one on purpose, so each rejection can only come "
                       "from the rule named in expect_reason"),
              "steps": [
                  {"present": "V01-base", "signer": "A", "expect": "accept", "expect_reason": "accepted"},
                  {"present": "V01-base", "signer": "A", "expect": "reject", "expect_reason": "P6d"},
                  {"present": "V01-base", "signer": "C", "expect": "accept", "expect_reason": "accepted",
                   "why": "the same nonce from a different signer: the replay key is the (signer, nonce) pair"},
                  {"present": "R-wrong-audience", "signer": "A", "expect": "reject", "expect_reason": "P6b"},
                  {"present": "R-wrong-domain", "signer": "A", "expect": "reject", "expect_reason": "P6a"},
                  {"present": "R-wrong-chain", "signer": "A", "expect": "reject", "expect_reason": "P6c"},
                  {"present": "R-no-nonce", "signer": "A", "expect": "reject", "expect_reason": "P6d",
                   "why": "absent-field bypass: without the presence check this is accepted the first time"},
                  {"present": "R-no-domain", "signer": "A", "expect": "reject", "expect_reason": "P6a"},
                  {"present": "R-fresh", "signer": "A", "expect": "accept", "expect_reason": "accepted"}]}
    extra = {}
    for rid, obj in (("R-wrong-audience", _with(id="cov-vec-aud", audience="someone-else.example")),
                     ("R-wrong-domain", _with(id="cov-vec-dom", domain="covenant-earn-receipt/v0")),
                     ("R-wrong-chain", _with(id="cov-vec-chain", chain_id="eip155:1")),
                     ("R-no-nonce", {k: v for k, v in _with(id="cov-vec-no-nonce").items() if k != "nonce"}),
                     ("R-no-domain", {k: v for k, v in _with(id="cov-vec-no-domain").items() if k != "domain"}),
                     ("R-fresh", _with(id="cov-vec-fresh"))):
        cbx = canonical_jcs(obj)
        extra[rid] = {"input_json_text": json.dumps(obj, ensure_ascii=False), "canonical_jcs": cbx.decode(),
                      "sha256_jcs": hashlib.sha256(cbx).hexdigest(), "signatures": sign_both(cbx)}
    replay["receipts"] = extra
    return discovery, vectors, negatives, replay


def evaluate(discovery, vectors, negatives, replay):
    """Re-derive every outcome from the published fields and compare with 'expect'."""
    results = []
    for v in vectors:
        try:
            obj = parse(v["input_json_text"])
            cb = canonical_jcs(obj)
        except Reject as e:
            want_rule = v.get("expect_reason") if v["expect"] == "reject" else None
            got = "reject" if (want_rule is None or str(e).startswith(want_rule)) else "reject-for-another-reason"
            results.append((v["id"], got, str(e), v["expect"]))
            continue
        sigs = v["signatures"]
        ok = bool(sigs) and all(verify(cb.hex(), e, discovery)[0] for e in sigs)
        results.append((v["id"], "accept" if ok else "reject", "" if ok else "signature check failed", v["expect"]))
    for n in negatives:
        chex = n["canonical_jcs_hex"] if "canonical_jcs_hex" in n else canonical_jcs(parse(n["input_json_text"])).hex()
        oks = [verify(chex, e, discovery) for e in n["signatures"]]
        results.append((n["id"], "accept" if all(o[0] for o in oks) else "reject",
                        "; ".join(o[1] for o in oks), n["expect"]))
    rpc = replay["relying_party"]
    rp = RelyingParty(rpc["me"], rpc["domain"], rpc["chain_id"])
    pool = {v["id"]: v for v in vectors}
    pool.update(replay["receipts"])
    who = {"A": _acct(KEY_A).address, "C": _acct(KEY_C).address}
    for i, st in enumerate(replay["steps"]):
        src = pool[st["present"]]
        obj = parse(src["input_json_text"])
        cb = canonical_jcs(obj)
        entry = next(e for e in src["signatures"] if e["signer"] == who[st["signer"]])
        okv, why = verify(cb.hex(), entry, discovery)
        ok, why2 = rp.accept(obj, entry["signer"]) if okv else (False, why)
        got = ("accept" if ok else "reject") + ":" + why2.split()[0]
        want = st["expect"] + ":" + st["expect_reason"]
        results.append(("%s#%d %s/%s" % (replay["id"], i + 1, st["present"], st["signer"]), got, why2, want))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutate", action="store_true", help="turn each profile rule off and show its guard go red")
    a = ap.parse_args()

    n, fails = rfc_selfcheck()
    print("RFC 8785 self-check: %d samples, %d failing%s" % (n, len(fails), "" if not fails else ": " + "; ".join(fails)))
    if fails:
        return 1
    discovery, vectors, negatives, replay = build()
    res = evaluate(discovery, vectors, negatives, replay)
    bad = [r for r in res if r[1] != r[3]]
    for r in res:
        print("  %-24s %-6s (expect %-6s) %s" % (r[0], r[1], r[3], r[2][:90]))
    print("vectors: %d, all as expected: %s" % (len(res), not bad))
    if bad:
        return 1

    if a.mutate:
        red = {}
        for rule in RULES:
            RULES[rule] = False
            try:
                d2, v2, n2, r2 = build()
                got = evaluate(d2, v2, n2, r2)
                red[rule] = [r[0] for r in got if r[1] != r[3]]
            except Exception as e:                             # noqa: BLE001
                red[rule] = ["build failed: %s" % e]
            RULES[rule] = True
        for rule, ids in red.items():
            print("  rule %s off -> %s" % (rule, ("RED: " + ", ".join(ids)) if ids else "STILL GREEN (an unguarded rule)"))
        return 0 if all(red.values()) else 1

    doc = {"about": ("covenant's side of the receipt interop test vectors promised in Hugging Face thread 180706 "
                     "post #22. Canonicalization: RFC 8785 (JCS) plus profile rules P1-P6 below. TEST KEYS ONLY: "
                     "derived as sha256 of the phrases given, so every signature is reproducible; not covenant's "
                     "receipt signer. covenant's production receipts do NOT yet canonicalize with JCS: each vector "
                     "carries the current production canonical form where it differs."),
           "profile_rules": {
               "P1": "reject duplicate member names at parse",
               "P2": ("reject any string (name or value) that holds a lone surrogate or is not already Unicode NFC. Cost: some valid JCS input is "
                      "refused -- RFC 8785's own 3.2.3 sorting sample contains U+FB33, which NFC maps to U+05D3 U+05BC"),
               "P3": ("reject any number TOKEN whose magnitude exceeds 2^53-1, in any spelling (plain or exponent "
                      "form), checked on the token with exact decimal arithmetic before any conversion to a double; "
                      "carry such values as strings"),
               "P4": "exclude the proof at the top level only; nested 'proof' members are signed content",
               "P5": "reject high-s ECDSA signatures (EIP-2)",
               "P6a": "relying party rejects a domain other than the one it expects",
               "P6b": "relying party rejects an audience other than itself",
               "P6c": "relying party rejects a chain_id other than the one it requires",
               "P7": "a verifier takes each signer's framing from the discovery document and never tries the other one",
               "P6d": ("relying party rejects a receipt with no nonce, or a (signer, nonce) it has already accepted, and records the pair on "
                       "acceptance. The check-and-record must be atomic and durable (concurrent presentations, "
                       "restarts); these vectors cannot test that, a verifier's own tests must")},
           "issuer": ("the replay key is (signer, nonce) and nothing in the signed bytes names an issuer: the signing "
                      "key IS the issuer. A design choice; an issuer field in the signed content is the alternative"),
           "not_covered": [
               "number tokens that lose precision through a double (1.00000000000000001 canonicalizes to 1): P3 bounds "
               "magnitude only. Amounts in this profile are strings, which is why",
               "the trust root: N02 checks a signature against the signer a discovery document names; nothing here "
               "establishes that the discovery document itself is genuine (DNS/TLS, or an out-of-band pin)",
               "atomic, durable nonce consumption (see P6d)",
               "independence: results_by_our_verifier come from this file's own verifier, which shares its "
               "canonicalizer with the generator. A second implementation's results are the real cross-check"],
           "new_fields": ("domain, audience, chain_id and nonce are fields of this proposed profile; the receipt "
                          "exchanged in the thread on 2026-10-21 had none of them"),
           "signing": "deterministic ECDSA (RFC 6979, as eth_account does it): regenerating this file reproduces every signature byte for byte",
           "framing_choice": ("EIP-191, with each signer's framing pinned in the discovery document (P7). EIP-712, raised "
                              "in the thread as the clean route for domain separation, is not used here and is still open"),
           "reject_vectors": ("each profile-reject vector is signed (by A and by C) over the bytes a verifier WITHOUT the "
                              "rule computes, so such a verifier would accept it and only the rule can reject it; the "
                              "lone surrogate and 1e400 are the exceptions: no canonical bytes can exist for them"),
           "framings": {"hex-text": "EIP-191 personal_sign over the 64-char lowercase hex of SHA-256(canonical) "
                                    "(covenant)",
                        "digest-bytes": "EIP-191 personal_sign over the raw 32-byte SHA-256 (Agent Embassy)"},
           "test_keys": {"A": {"phrase": KEY_A, "private_key": "sha256(phrase)", "address": _acct(KEY_A).address,
                               "framing": "hex-text"},
                         "C": {"phrase": KEY_C, "private_key": "sha256(phrase)", "address": _acct(KEY_C).address,
                               "framing": "digest-bytes"},
                         "B": {"phrase": KEY_B, "private_key": "sha256(phrase)", "address": _acct(KEY_B).address,
                               "framing": "none: in no discovery document"}},
           "discovery_document": discovery,
           "rfc8785_selfcheck": "Appendix B (26 numbers incl. NaN/Infinity rejected), 3.2.3 sort order, 3.2.4 bytes: all pass",
           "vectors": vectors, "negatives": negatives, "replay_sequence": replay,
           "results_by_our_verifier": [{"id": r[0], "got": r[1], "expect": r[3], "reason": r[2]} for r in res]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:   # LF on every platform, so the bytes match
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
