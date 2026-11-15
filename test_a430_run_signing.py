#!/usr/bin/env python3
"""A430S: hash-bearing operator requests use the exact bytes signed, on every road.

Ephemeral in-memory keys; no node, key file, network or ledger is touched.
The real core signature verifier checks the requests; only signer registration,
logging and the spore envelope/relay are in-memory fixtures.
"""
import base64
import hashlib
import json
import types
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa

import covenant_daily_plan as DP
import covenant_mycelium as M
import covenant_spore as S
import covenant_unified_v8 as cov


CASES = []
DIGEST = hashlib.sha256(b"print('approved')\n").hexdigest()
OTHER = hashlib.sha256(b"print('changed')\n").hexdigest()
PATH = "/m/agent"


def case(fn):
    CASES.append(fn)
    return fn


def verifies(body, headers, method="POST", path=PATH):
    return cov.verify_operator_signature(
        base64.b64decode(headers["X-Operator-Pubkey"]).decode(), method, path, body,
        headers["X-Operator-Nonce"], float(headers["X-Operator-Timestamp"]),
        headers["X-Operator-Signature"])


def changed(body):
    return body.replace(DIGEST.encode(), OTHER.encode())


def rejects(fn):
    try:
        fn()
    except ValueError as exc:
        assert "run_sha256" in str(exc)
        return
    raise AssertionError("invalid run_sha256 was accepted")


@case
def helper_adds_hash_before_signing(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {"message": "try the script"}, run_sha256=DIGEST)
    assert json.loads(body)["run_sha256"] == DIGEST
    assert verifies(body, headers)
    assert not verifies(changed(body), headers)


@case
def helper_keeps_ordinary_requests(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {"message": "hello"})
    assert json.loads(body) == {"message": "hello"}
    assert verifies(body, headers)


@case
def helper_validates_explicit_hash(key):
    for bad in ("", "a" * 63, "a" * 65, "G" * 64, DIGEST.upper(), DIGEST + "\n", 7, True, []):
        rejects(lambda: DP.sign_json_request(key, "POST", PATH, {}, run_sha256=bad))


@case
def helper_signs_existing_payload_hash(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {"run_sha256": DIGEST})
    assert json.loads(body)["run_sha256"] == DIGEST
    assert verifies(body, headers)


@case
def helper_validates_existing_payload_hash(key):
    for bad in (None, "", DIGEST.upper(), 7):
        rejects(lambda: DP.sign_json_request(key, "POST", PATH, {"run_sha256": bad}))


@case
def helper_refuses_conflicting_hashes(key):
    rejects(lambda: DP.sign_json_request(key, "POST", PATH, {"run_sha256": OTHER}, run_sha256=DIGEST))


@case
def helper_accepts_matching_hashes(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {"run_sha256": DIGEST}, run_sha256=DIGEST)
    assert json.loads(body)["run_sha256"] == DIGEST and verifies(body, headers)


@case
def helper_does_not_modify_callers_payload(key):
    payload = {"message": "try the script"}
    body, headers = DP.sign_json_request(key, "POST", PATH, payload, run_sha256=DIGEST)
    assert payload == {"message": "try the script"}
    assert json.loads(body)["run_sha256"] == DIGEST and verifies(body, headers)


@case
def helper_keeps_method_and_path_bound(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {}, run_sha256=DIGEST)
    assert verifies(body, headers)
    assert not verifies(body, headers, method="GET")
    assert not verifies(body, headers, path="/mine")


@case
def existing_raw_signer_covers_hash_bytes(key):
    body = json.dumps({"message": "try the script", "run_sha256": DIGEST}).encode()
    headers = DP.sign_headers(key, "POST", PATH, body)
    assert verifies(body, headers) and not verifies(changed(body), headers)


@case
def mycelium_accepts_signed_hash_and_rejects_tampering(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {}, run_sha256=DIGEST)
    req = types.SimpleNamespace(remote_addr="192.0.2.10", method="POST", path=PATH, headers=headers)
    with patch.object(DP, "signer_name", return_value="operator"), patch.object(M, "_record"):
        assert M.admit(req, body, lambda addr: False, seen=set())[0]
        assert not M.admit(req, changed(body), lambda addr: False, seen=set())[0]


def spore_pass(key, body, headers):
    pem = DP.pubkey_pem(key)
    # The production wrapper and admission/forwarding path run; sealing and
    # storage are fixtures because this test is about the inner signature.
    sealer = types.SimpleNamespace(
        seal=lambda kind, obj, *args: obj,
        blocks=lambda obj: [obj],
        open_env=lambda obj, *args: ({"kind": S.KIND_REQ}, obj, pem),
        fingerprint=lambda ignored: "box", error=ValueError)
    _, block = S.wrap_request(sealer, "POST", PATH, body, headers, key, pem, pem)
    relay = types.SimpleNamespace(take=lambda *args, **kwargs: [("block", block)], put=lambda *args: None)
    forwarded = []

    def forward(method, path, raw, signed):
        forwarded.append((method, path, raw, signed))
        return 200, b"{}", {}

    with patch.object(DP, "signer_name", return_value="operator"), patch.object(M, "_record"):
        rows = S.pc_pass(relay, key, pem, forward=forward, sealer=sealer, seen=set())
    return rows, forwarded


@case
def spore_forwards_exact_signed_hash_bytes(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {}, run_sha256=DIGEST)
    rows, forwarded = spore_pass(key, body, headers)
    assert rows[-1]["kind"] == "answered" and len(forwarded) == 1
    method, path, received, signed = forwarded[0]
    assert received == body and json.loads(received)["run_sha256"] == DIGEST
    assert verifies(received, signed, method, path)


@case
def spore_refuses_hash_changed_after_signing(key):
    body, headers = DP.sign_json_request(key, "POST", PATH, {}, run_sha256=DIGEST)
    rows, forwarded = spore_pass(key, changed(body), headers)
    assert rows[-1]["kind"] == "refused" and forwarded == []


def main():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    passed = 0
    for fn in CASES:
        try:
            fn(key)
        except Exception as exc:
            print("FAIL %s: %s: %s" % (fn.__name__, type(exc).__name__, str(exc)[:180]), flush=True)
        else:
            passed += 1
            print("ok   " + fn.__name__, flush=True)
    print("A430S: %d/%d passed" % (passed, len(CASES)))
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
