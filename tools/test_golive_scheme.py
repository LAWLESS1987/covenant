"""Prove the go-live helper's signing scheme verifies under covenant_onboard,
and the full gate reaches ACT -- using a THROWAWAY key and FAKE nodes only.
No real identities, no real ops/ files. Both ways: good->ACT, tamper/absent->dark.

Run: python tools/test_golive_scheme.py   (exit 0 = all pass, 1 = a failure)
"""
import os
import sys

# tools/ convention: repo root on sys.path for covenant_onboard; this file's own
# dir (tools/) is already sys.path[0], which is where arm_onboard_golive lives.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "."
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import covenant_onboard as ob
import arm_onboard_golive as gl
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

ACCT = "op@"
STATUS = {"Self": {"HostName": "node-a", "TailscaleIPs": ["1.2.3.4"], "PublicKey": "nodekey:FAKE"}}
WHOIS = lambda ip: {"machine_id": "nFAKE", "user": ACCT}          # noqa: E731
PIN   = lambda ip: "nodekey:FAKE"                                  # noqa: E731


def pub(priv):
    return priv.public_key().public_bytes(serialization.Encoding.PEM,
                                           serialization.PublicFormat.SubjectPublicKeyInfo).decode()


priv = ed25519.Ed25519PrivateKey.generate()
other = ed25519.Ed25519PrivateKey.generate()
priv_pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption())

body = gl.build_roster(ACCT, ["node-a"], ["peer"], status_json=STATUS, whois_fn=WHOIS)
signed = gl.sign_roster(body, priv_pem)

ok = True


def check(name, cond):
    global ok
    print(("[PASS] " if cond else "[FAIL] ") + name)
    ok = ok and cond


# signature verifies under the REAL verifier
check("operator-signed roster verifies", ob._verify_signature(signed, pub(priv)))
check("trust root is 'signature'", ob.roster_trust_root(signed, pubkey=pub(priv))[0] == "signature")
# both ways: wrong key, tampered body -> False
check("wrong key does NOT verify", not ob._verify_signature(signed, pub(other)))
tampered = dict(signed); tampered["nodes"] = {"node-a": dict(signed["nodes"]["node-a"], allowed=["peer", "arm_task"])}
check("tampered roster does NOT verify", not ob._verify_signature(tampered, pub(priv)))

# full gate: armed + signed + identity stubbed -> ACT
armed_cfg = {"armed": True, "trust_root": "signature"}
ev = ob.evaluate("peer", {"node": "node-a"}, {"source": "roster_scan"}, roster=signed,
                 pubkey=pub(priv), armed_cfg=armed_cfg, operator_account=ACCT,
                 whois_fn=WHOIS, status_fn=PIN, paused=False, may_act=True,
                 choices={}, refusals={})
check("gate ACTs on a signed, identity-verified node", ev["decision"] == ob.ACT)

# absent signature -> dark (PROPOSE), not ACT
ev2 = ob.evaluate("peer", {"node": "node-a"}, {"source": "roster_scan"}, roster=body,
                  pubkey=pub(priv), armed_cfg=armed_cfg, operator_account=ACCT,
                  whois_fn=WHOIS, status_fn=PIN, paused=False, may_act=True, choices={}, refusals={})
check("unsigned roster -> dark (PROPOSE)", ev2["decision"] == ob.PROPOSE)

# model-sourced trigger is always refused, even fully armed+signed
ev3 = ob.evaluate("peer", {"node": "node-a"}, {"source": "model"}, roster=signed,
                  pubkey=pub(priv), armed_cfg=armed_cfg, operator_account=ACCT,
                  whois_fn=WHOIS, status_fn=PIN, paused=False, may_act=True, choices={}, refusals={})
check("model trigger REFUSED even when armed+signed", ev3["decision"] == ob.REFUSE)

print("ALL PASS" if ok else "FAILURES ABOVE")
raise SystemExit(0 if ok else 1)
