#!/usr/bin/env python3
"""arm_onboard_golive.py -- the operator's ONE step to take the AUTO_GATED
auto-onboard lane from armed-but-dark to green, rooted on HIS signature.

Why this exists: the lane (covenant_onboard.py) is armed once the operator
writes ops/AUTO_ONBOARD_ARMED with trust_root "signature", but it stays DARK
until a NODE_ROSTER.json signed by the operator's key verifies against
ops/operator_pubkey.pem. Claude never creates or signs keys (sovereignty + a
forever hard line), and the whois trust root would have to COMMIT the operator's
device names + tailnet IPs to the PUBLIC repo (the opsec push guard refuses
that). So the signature root is the only exposure-free, sovereignty-correct
path, and only the operator can take it. This tool is that one step.

What it does, with the operator's own private key and nothing else:
  1. reads `tailscale status --json` + `tailscale whois --json <ip>` for the
     named nodes, so machine_id (whois StableID) and pubkey (status PublicKey)
     are byte-identical to what covenant_onboard verifies at runtime;
  2. builds ops/NODE_ROSTER.json (LOCAL ONLY on the signature path -- do NOT
     commit it; it carries device names + tailnet IPs the opsec guard refuses
     to push);
  3. signs its canonical payload with the operator's key (Ed25519 or RSA-PSS),
     reusing covenant_onboard._canonical_payload so signer and verifier agree;
  4. writes ops/operator_pubkey.pem (gitignored) and the signed roster;
  5. prints is_armed() -- which flips to (True, 'signature') once both land.

Run (from the repo root, with the lane code present):
    python tools/arm_onboard_golive.py --key YOUR_KEY.pem \
        --account YOUR_TAILNET_LOGIN --nodes nodeA,nodeB
Options: --allowed peer,arm_task (default: peer only -- the most conservative).
No account or node names are baked in -- you pass your own, so nothing about
your tailnet (device names, login, IPs) is committed to this public repo.

It onboards ONLY the nodes you name, for ONLY the reversible local actions you
allow. Everything else (grid/ICS, keys, consent, installs, unknown nodes) stays
PROPOSE_ONLY / together-vote regardless of this roster.
"""
import argparse
import json
import os
import subprocess
import sys

# tools/ convention: put the repo root on sys.path so the lane imports cleanly
# whether this is run as `python tools/arm_onboard_golive.py` or `-m tools...`.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "."
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import covenant_onboard as ob  # the verifier -- reuse its canonical payload


def _status_ip(node_name, status_json):
    for peer in list((status_json.get("Peer") or {}).values()) + [status_json.get("Self") or {}]:
        names = (peer.get("HostName"), (peer.get("DNSName") or "").split(".")[0])
        if node_name in [n for n in names if n]:
            ips = peer.get("TailscaleIPs") or []
            return (ips[0] if ips else None), (peer.get("PublicKey") or peer.get("Key"))
    return None, None


def build_roster(account, node_names, allowed, *, status_json=None, whois_fn=None, peer_port=5001):
    """The unsigned roster body. whois_fn/status_json are injectable for testing;
    live, they come from the tailscale CLI. Fails loudly on any node that does not
    resolve or whose whois owner != the operator -- never writes a half-roster.

    peer_addr is written as "<verified ip>:<peer_port>" (default 5001, the P2P port): without
    it a peer action refused ("no valid host:port peer address"), and binding the host to the
    whois-verified ip is what the gate (evaluate 10b) checks, so the engine can only peer the
    address identity vouched for."""
    if status_json is None:
        r = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=20)
        status_json = json.loads(r.stdout or "{}")
    whois = whois_fn or ob._tailscale_whois
    nodes = {}
    for name in node_names:
        ip, pubkey = _status_ip(name, status_json)
        if not ip:
            raise SystemExit("no tailnet IP for node %r in `tailscale status` -- is it up?" % name)
        who = whois(ip)
        if not who:
            raise SystemExit("whois failed for %r (%s)" % (name, ip))
        if str(who.get("user")) != str(account):
            raise SystemExit("whois owner %r != operator %r for %r -- refusing" % (who.get("user"), account, name))
        nodes[name] = {"ip": ip, "machine_id": who.get("machine_id"), "pubkey": pubkey,
                       "peer_addr": "%s:%d" % (ip, int(peer_port)), "allowed": list(allowed)}
    return {"operator_account": account, "nodes": nodes}


def sign_roster(body, priv_pem):
    """body + a signature over its canonical payload. Ed25519 or RSA by key type."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, padding
    key = serialization.load_pem_private_key(priv_pem, password=None)
    payload = ob._canonical_payload(body)
    if isinstance(key, ed25519.Ed25519PrivateKey):
        sig, alg = key.sign(payload), "ed25519"
    else:
        sig = key.sign(payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                             salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        alg = "rsa-pss-sha256"
    signed = dict(body)
    signed["signature"] = sig.hex()
    signed["signed_by"] = "operator"
    signed["alg"] = alg
    return signed


def _pub_pem(priv_pem):
    from cryptography.hazmat.primitives import serialization
    key = serialization.load_pem_private_key(priv_pem, password=None)
    return key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sign the auto-onboard roster with your key and go green.")
    ap.add_argument("--key", required=True, help="path to YOUR private key (Ed25519 or RSA PEM)")
    ap.add_argument("--account", required=True,
                    help="your tailnet login / whois owner (the node's owning account)")
    ap.add_argument("--nodes", required=True,
                    help="comma list of node names to onboard, as `tailscale status` shows them")
    ap.add_argument("--allowed", default="peer", help="comma list; reversible only: peer, arm_task")
    ap.add_argument("--peer-port", type=int, default=5001,
                    help="the node's P2P port; peer_addr is written as <verified ip>:<peer-port> (default 5001)")
    a = ap.parse_args(argv)
    with open(a.key, "rb") as fh:
        priv = fh.read()
    body = build_roster(a.account, [n.strip() for n in a.nodes.split(",") if n.strip()],
                         [x.strip() for x in a.allowed.split(",") if x.strip()], peer_port=a.peer_port)
    signed = sign_roster(body, priv)
    with open(ob.OPERATOR_PUBKEY, "wb") as fh:
        fh.write(_pub_pem(priv))
    with open(ob.ROSTER, "w", encoding="utf-8") as fh:
        json.dump(signed, fh, indent=2)
    armed, root, why = ob.is_armed()
    print("wrote", ob.ROSTER, "(LOCAL ONLY on the signature path -- do NOT commit) and", ob.OPERATOR_PUBKEY)
    print("is_armed ->", armed, root, "|", why)
    if not armed:
        sys.exit("still dark -- check the key and account")
    print("GREEN: the auto-onboard lane is live for", list(signed["nodes"]), "actions", a.allowed)


if __name__ == "__main__":
    main()
