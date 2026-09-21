#!/usr/bin/env python3
"""covenant_mycelium.py -- the covenant's own wire: a door admits a caller by
its KEY, not by the network it arrived on. The tailnet stays the first road;
when it is down, a signed request over any road is the same caller.

HIS WORDS, 2026-09-21: "create our own native tailnet like mycellium
connection incase tail net goes down" -- "also as a rout for allies though
their system/companion wil have their own identity".

WHAT WAS THERE. Every door the phone uses (/m/agent, /checkin, /pc/*) was
gated by the caller's ADDRESS: loopback or a Tailscale CGNAT address
(tailnet_ok). And every privileged request from the phone already carried
the operator-request signature (X-Operator-* headers, a registered key, a
nonce, a timestamp inside a window) -- identity by key, verified by
covenant_daily_plan.verify_signed. The two were never joined: a request
from the LAN with a perfect signature was refused for its address.

WHAT THIS JOINS. admit(request, body): the tailnet admits as before; off
the tailnet, a request signed by one of HIS registered signers (the phone,
the PC) is admitted to every door; a request signed by a registered ALLY
key (ops/mycelium_peers.json, granted by him, with a scope) is admitted to
the ally doors only (ALLY_DOORS: the conversation, the handshake, health);
everything else is refused as before. Every off-tailnet decision is one
row in ops/mycelium.jsonl. The PC's LAN address rides the check-in answer
so the phone knows the second road (entry.py takes it when the first fails,
signing the call).

WHAT IT IS NOT. Not an overlay network: no tunnel, no discovery beyond the
LAN address the PC names; the phone must be able to reach that address
(the same Wi-Fi, or a port he opens). Not a lowering of a gate: an
unsigned request off the tailnet is refused exactly as before, and the
signature scheme is the one that guards the daily plan, with its window
and its single-use nonces.
"""
import base64
import json
import os
import socket
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PEERS = os.environ.get("COVENANT_MYCELIUM_PEERS") or os.path.join(HERE, "ops", "mycelium_peers.json")
LEDGER = os.environ.get("COVENANT_MYCELIUM_LEDGER") or os.path.join(HERE, "ops", "mycelium.jsonl")
ALLY_DOORS = ("/m/agent", "/pc/handshake", "/health")
WINDOW_S = 300
_seen = set()


def lan_address(port=5000):
    """The address this PC has on its local network, with the API port; None when it cannot be read."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        finally:
            s.close()
        if not ip or ip.startswith("127.") or ip.startswith("100."):
            return None
        return "%s:%d" % (ip, int(port))
    except OSError:
        return None


def allies(path=None):
    try:
        with open(path or PEERS, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _norm(pem):
    return "".join(str(pem or "").split())


def ally_name(pem, path=None):
    n = _norm(pem)
    for name, row in allies(path).items():
        if isinstance(row, dict) and _norm(row.get("pem")) == n and row.get("granted"):
            return name
    return None


def register_ally(name, pem, granted_by, scope=None, path=None):
    """His hand: an ally's public key, its name, who granted it. Never a private key."""
    if "PRIVATE KEY" in str(pem):
        raise ValueError("a private key is never registered")
    path = path or PEERS
    d = allies(path)
    d[str(name)[:60]] = {"pem": str(pem), "granted": True, "granted_by": str(granted_by)[:120], "scope": list(scope or ALLY_DOORS),
                         "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, path)
    return d[str(name)[:60]]


def _record(row, path=None):
    path = path or LEDGER
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        row = dict(row)
        row.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def admit(req, body, tailnet_ok, signers_path=None, peers_path=None, ledger_path=None, now=None, seen=None):
    """(ok, addr, who, how). The tailnet first; then a registered signer over any road; then an ally on its doors."""
    addr = (getattr(req, "remote_addr", "") or "").strip()
    if tailnet_ok(addr):
        return True, addr, "tailnet", "tailnet"
    headers = getattr(req, "headers", {}) or {}
    sig = headers.get("X-Operator-Signature", "")
    if not sig:
        return False, addr, "", "unsigned off the tailnet"
    try:
        pem = base64.b64decode(headers.get("X-Operator-Pubkey", "")).decode()
    except Exception:                                             # noqa: BLE001
        _record({"kind": "refused", "addr": addr, "path": getattr(req, "path", ""), "why": "bad pubkey header"}, ledger_path)
        return False, addr, "", "bad X-Operator-Pubkey"
    method, path = getattr(req, "method", "GET"), getattr(req, "path", "")
    nonce, ts = headers.get("X-Operator-Nonce", ""), headers.get("X-Operator-Timestamp", "")
    try:
        import covenant_daily_plan as DP
        ok, who = DP.verify_signed(pem, method, path, body or b"", nonce, ts, sig, signers_path=signers_path, now=now, seen=seen)
    except Exception as e:                                        # noqa: BLE001
        ok, who = False, "verification unavailable: %s" % type(e).__name__
    if ok:
        _record({"kind": "admitted", "addr": addr, "path": path, "who": who, "how": "signed:operator"}, ledger_path)
        return True, addr, who, "signed:operator"
    name = ally_name(pem, peers_path)
    if name:
        row = allies(peers_path).get(name) or {}
        doors = tuple(row.get("scope") or ALLY_DOORS)
        if path not in doors:
            _record({"kind": "refused", "addr": addr, "path": path, "who": name, "why": "an ally, but not an ally door"}, ledger_path)
            return False, addr, name, "ally: %s is not an ally door" % path
        try:
            import covenant_unified_v8 as cov
            tsf = float(ts)
            fresh = abs((now if now is not None else time.time()) - tsf) <= WINDOW_S
            s = _seen if seen is None else seen
            good = fresh and nonce and nonce not in s and cov.verify_operator_signature(pem, method, path, body or b"", nonce, tsf, sig)
            if good:
                s.add(nonce)
        except Exception:                                         # noqa: BLE001
            good = False
        if good:
            _record({"kind": "admitted", "addr": addr, "path": path, "who": name, "how": "signed:ally"}, ledger_path)
            return True, addr, name, "signed:ally"
        _record({"kind": "refused", "addr": addr, "path": path, "who": name, "why": "ally signature did not verify (window, nonce or bytes)"}, ledger_path)
        return False, addr, name, "ally signature did not verify"
    _record({"kind": "refused", "addr": addr, "path": path, "why": str(who)[:120]}, ledger_path)
    return False, addr, "", str(who)[:120]


def status(path=None, ledger_path=None):
    rows = []
    try:
        with open(ledger_path or LEDGER, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    except (OSError, ValueError):
        rows = []
    return {"lan": lan_address(), "allies": sorted(allies(path)), "ally_doors": list(ALLY_DOORS),
            "admitted_off_tailnet": sum(1 for r in rows if r.get("kind") == "admitted"),
            "refused_off_tailnet": sum(1 for r in rows if r.get("kind") == "refused")}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="the covenant's own wire: admission by key; the LAN address; the allies")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--register-ally", nargs=2, metavar=("NAME", "PEM_FILE"))
    ap.add_argument("--granted-by", default="the operator")
    a = ap.parse_args()
    if a.register_ally:
        pem = open(a.register_ally[1], encoding="utf-8").read()
        print(json.dumps(register_ally(a.register_ally[0], pem, a.granted_by), indent=1))
    else:
        print(json.dumps(status(), indent=1))
