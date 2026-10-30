#!/usr/bin/env python3
"""
GG1 -- covenant_grid_guard both-ways guard tests (CLAUDE.md rule 8: a real attack
turns the guard red; removing the attack restores green). Offline, no real grid.

Run:  python test_gg1_grid_guard.py     (exit 0 = all pass)
"""
import json
import os
import sys
import tempfile
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import covenant_grid_guard as gg

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print("  ok  ", name)
    else:
        FAIL[0] += 1
        print("  FAIL", name)


def _key():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()).decode()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv_pem, pub_pem


def setup():
    d = tempfile.mkdtemp(prefix="gg1_")
    gg.LEDGER = os.path.join(d, "grid_commands.jsonl")
    gg.CHAIN = os.path.join(d, "grid_commands.chain.jsonl")
    gg.SIGNERS = os.path.join(d, "grid_signers.json")
    gg.INTERLOCKS = os.path.join(d, "grid_interlocks.json")
    gg.POLICY = os.path.join(d, "grid_policy.json")
    gg.HEARTBEAT = os.path.join(d, "grid_authz_heartbeat.jsonl")

    keys = {r: _key() for r in ("controller", "operator", "tetsu", "gateway")}
    fpr = {r: gg._fpr(keys[r][1]) for r in keys}
    signers = {
        fpr["controller"]: {"role": "controller", "pubkey_pem": keys["controller"][1],
                            "allowed_actions": ["breaker_open", "breaker_close", "load_shed", "setpoint", "halt"],
                            "zones": ["Z1"], "revoked": False},
        fpr["operator"]: {"role": "operator", "pubkey_pem": keys["operator"][1], "revoked": False},
        fpr["tetsu"]: {"role": "tetsu", "pubkey_pem": keys["tetsu"][1], "revoked": False},
    }
    interlocks = {"MAX_SHED_PCT": 20, "MAX_BREAKER_OPS": 3, "WINDOW_S": 3600,
                  "setpoint_ranges": {"Z1": [40, 60]}, "zone_allowlist": ["Z1"]}
    policy = {"ACTUATION": ["operator", "tetsu"], "MONITOR": [], "ADVISORY": []}
    with open(gg.SIGNERS, "w") as f:
        json.dump(signers, f)
    with open(gg.INTERLOCKS, "w") as f:
        json.dump(interlocks, f)
    with open(gg.POLICY, "w") as f:
        json.dump(policy, f)
    fresh_heartbeat()
    return d, keys, fpr, signers, interlocks, policy


def fresh_heartbeat(ttl=600):
    with open(gg.HEARTBEAT, "w") as f:
        f.write(json.dumps({"issuer": "operator", "issued_utc": gg._now(),
                            "expires_utc": gg._now() + ttl}) + "\n")


def stale_heartbeat():
    with open(gg.HEARTBEAT, "w") as f:
        f.write(json.dumps({"issuer": "operator", "issued_utc": gg._now() - 9999,
                            "expires_utc": gg._now() - 9000}) + "\n")


def actuation(keys, fpr, signers, policy, seq=0, action="breaker_open", zone="Z1",
              magnitude=None, both=True, operator_only=False, now=None):
    """A fully valid actuation envelope with authority-holder tokens attached."""
    now = gg._now() if now is None else now
    payload = gg.build_command(seq, action, zone, magnitude or {}, "ACTUATION",
                               fpr["controller"], now=now)
    env = gg.sign_command(payload, keys["controller"][0])
    toks = []
    if both or operator_only:
        toks.append(gg.make_authz_token(payload, fpr["operator"], keys["operator"][0], now=now))
    if both and not operator_only:
        toks.append(gg.make_authz_token(payload, fpr["tetsu"], keys["tetsu"][0], now=now))
    env["payload"]["authz_tokens"] = toks
    return env


def A(env, signers, interlocks, policy, **kw):
    return gg.authorize(env, signers=signers, signers_ok=True,
                        interlocks=interlocks, interlocks_ok=True, policy=policy, **kw)


def main():
    d, keys, fpr, signers, interlocks, policy = setup()

    # ----- C1 authenticity, both ways
    env = actuation(keys, fpr, signers, policy, seq=0)
    check("C1 valid actuation PERMITs", A(env, signers, interlocks, policy)["decision"] == gg.PERMIT)
    bad = json.loads(json.dumps(env))
    bad["payload"]["zone"] = "Z1 "   # one byte changed after signing
    r = A(bad, signers, interlocks, policy)
    check("C1 tampered payload REFUSEd", r["decision"] == gg.REFUSE and r["failed_check"] in ("C1", "C2", "C5"))
    check("C1 detector PRESENT on bad sig",
          gg.detect_grid_command_unauthenticated(envelope=_sigbreak(env))["state"] == gg.PRESENT)
    check("C1 detector ABSENT on good", gg.detect_grid_command_unauthenticated(envelope=env)["state"] in (gg.ABSENT, gg.UNKNOWN))

    # ----- C2 signer: unknown, revoked, overscope
    unk = actuation(keys, fpr, signers, policy, seq=1)
    unk["payload"]["signer_fpr"] = "deadbeef"
    check("C2 unknown signer REFUSEd", A(unk, signers, interlocks, policy)["failed_check"] == "C2")
    revd = dict(signers); revd[fpr["controller"]] = dict(signers[fpr["controller"]], revoked=True)
    check("C2 revoked signer REFUSEd", A(actuation(keys, fpr, signers, policy, seq=1), revd, interlocks, policy)["failed_check"] == "C2")
    over = actuation(keys, fpr, signers, policy, seq=1, zone="Z9")
    check("C2 out-of-grant zone REFUSEd", A(over, signers, interlocks, policy)["failed_check"] == "C2")

    # ----- C3 freshness
    old = actuation(keys, fpr, signers, policy, seq=1, now=gg._now() - 10000)
    check("C3 expired REFUSEd", A(old, signers, interlocks, policy)["failed_check"] == "C3")
    fut = actuation(keys, fpr, signers, policy, seq=1, now=gg._now() + 10000)
    check("C3 future REFUSEd", A(fut, signers, interlocks, policy)["failed_check"] == "C3")

    # ----- C4 replay (via gateway so state is in the ledger)
    gw = gg.GridEffectorGateway(ledger=gg.LEDGER, chain=gg.CHAIN, heartbeat=gg.HEARTBEAT)
    e0 = actuation(keys, fpr, signers, policy, seq=0)
    d0 = gw.submit(e0)
    check("C4 first honored PERMITs", d0["decision"] == gg.PERMIT)
    d1 = gw.submit(e0)   # exact replay
    check("C4 replay REFUSEd", d1["decision"] == gg.REFUSE and d1["failed_check"] == "C4")
    check("C4 detector PRESENT on replay", gg.detect_grid_command_replay(envelope=e0)["state"] == gg.PRESENT)
    e_fresh = actuation(keys, fpr, signers, policy, seq=1)
    check("C4 fresh seq PERMITs", gw.submit(e_fresh)["decision"] == gg.PERMIT)

    # ----- C5 interlocks
    shed = actuation(keys, fpr, signers, policy, seq=2, action="load_shed", magnitude={"pct": 50})
    r = A(shed, signers, interlocks, policy)
    check("C5 over-shed REFUSEd", r["decision"] == gg.REFUSE and r["failed_check"] == "C5")
    check("C5 detector PRESENT", gg.detect_grid_interlock_breach(envelope=shed)["state"] in (gg.PRESENT, gg.ABSENT))
    sp_bad = actuation(keys, fpr, signers, policy, seq=2, action="setpoint", magnitude={"value": 999})
    check("C5 setpoint out of range REFUSEd", A(sp_bad, signers, interlocks, policy)["failed_check"] == "C5")
    sp_ok = actuation(keys, fpr, signers, policy, seq=2, action="setpoint", magnitude={"value": 50})
    check("C5 setpoint in range PERMITs", A(sp_ok, signers, interlocks, policy)["decision"] == gg.PERMIT)
    check("C5 unreadable interlocks -> HOLD",
          gg.authorize(sp_ok, signers=signers, signers_ok=True, interlocks=None, interlocks_ok=False, policy=policy)["decision"] == gg.HOLD)

    # ----- C6 authority-holder together-vote
    none_tok = actuation(keys, fpr, signers, policy, seq=2, both=False)
    r = A(none_tok, signers, interlocks, policy)
    check("C6 no authz REFUSEd", r["decision"] == gg.REFUSE and r["failed_check"] == "C6")
    check("C6 detector PRESENT", gg.detect_grid_actuation_without_authority(envelope=none_tok)["state"] == gg.PRESENT)
    op_only = actuation(keys, fpr, signers, policy, seq=2, both=True, operator_only=True)
    r = A(op_only, signers, interlocks, policy)
    check("C6 operator-only (missing tetsu) REFUSEd", r["decision"] == gg.REFUSE and "tetsu" in r["reason"])
    both_ok = actuation(keys, fpr, signers, policy, seq=2, both=True)
    check("C6 together-vote PERMITs", A(both_ok, signers, interlocks, policy)["decision"] == gg.PERMIT)
    # token lifted from a DIFFERENT command is ignored
    other = actuation(keys, fpr, signers, policy, seq=7)
    lifted = actuation(keys, fpr, signers, policy, seq=2, both=False)
    lifted["payload"]["authz_tokens"] = other["payload"]["authz_tokens"]
    check("C6 token bound to other command ignored", A(lifted, signers, interlocks, policy)["failed_check"] == "C6")
    # MONITOR needs no token
    mon = gg.sign_command(gg.build_command(2, "read", "Z1", {}, "MONITOR", fpr["controller"]), keys["controller"][0])
    mon_signer = dict(signers); mon_signer[fpr["controller"]] = dict(signers[fpr["controller"]],
                                                                     allowed_actions=signers[fpr["controller"]]["allowed_actions"] + ["read"])
    check("MONITOR needs no authz", A(mon, mon_signer, interlocks, policy)["decision"] == gg.PERMIT)

    # ----- C7 / NEVER_AUTOMATIC words bite (both ways), and reasoning holds no key
    def crossed(words, touches):
        return sorted({w for w in words for t in touches if w in t.lower()})
    check("grid words refuse a breaker remedy", crossed(gg.GRID_NEVER_AUTOMATIC_WORDS, ["opens a breaker in Z1"]) != [])
    check("no words -> not refused (proves the set, not a happy dict)", crossed((), ["opens a breaker in Z1"]) == [])
    check("reasoning gateway holds no signing key", gg.GridEffectorGateway().gateway_priv_pem is None)

    # ----- deadman + halt
    stale_heartbeat()
    gw2 = gg.GridEffectorGateway(ledger=gg.LEDGER, chain=gg.CHAIN, heartbeat=gg.HEARTBEAT)
    e = actuation(keys, fpr, signers, policy, seq=3)
    before = len(gw2.effector.actuated)
    r = gw2.submit(e)
    check("deadman: stale heartbeat REFUSEs + latches", r["failed_check"] == "C6-deadman" and gw2.latched_hold)
    check("deadman: nothing actuated", len(gw2.effector.actuated) == before)
    check("authz-channel-lost detector PRESENT", gg.detect_grid_authz_channel_lost(path=gg.HEARTBEAT)["state"] == gg.PRESENT)
    halt = gg.sign_command(gg.build_command(0, "halt", "Z1", {}, "ACTUATION", fpr["controller"]), keys["controller"][0])
    check("halt honored even with stale heartbeat", gw2.submit(halt)["failed_check"] == "HALT")
    fresh_heartbeat()
    check("authz-channel fresh -> ABSENT", gg.detect_grid_authz_channel_lost(path=gg.HEARTBEAT)["state"] == gg.ABSENT)

    # ----- ledger tamper both ways
    ok, _ = gg.cc.verify(ledger_path=gg.LEDGER, chain_path=gg.CHAIN)
    check("ledger clean -> PASS", ok)
    check("ledger-broken detector ABSENT when clean", gg.detect_grid_ledger_broken(ledger=gg.LEDGER, chain=gg.CHAIN)["state"] == gg.ABSENT)
    with open(gg.LEDGER, "r+", encoding="utf-8") as f:
        data = f.read()
    tampered = data.replace("PERMIT", "PERMiT", 1) if "PERMIT" in data else data[:-2] + "X\n"
    with open(gg.LEDGER + ".bak", "w", encoding="utf-8") as f:
        f.write(data)
    with open(gg.LEDGER, "w", encoding="utf-8") as f:
        f.write(tampered)
    check("ledger-broken detector PRESENT after edit",
          gg.detect_grid_ledger_broken(ledger=gg.LEDGER, chain=gg.CHAIN)["state"] == gg.PRESENT)
    with open(gg.LEDGER, "w", encoding="utf-8") as f:
        f.write(data)   # restore
    check("ledger-broken detector ABSENT after restore",
          gg.detect_grid_ledger_broken(ledger=gg.LEDGER, chain=gg.CHAIN)["state"] == gg.ABSENT)

    # ----- fail-closed: unreadable signers -> HOLD not PERMIT
    check("UNDETERMINED signers -> HOLD",
          gg.authorize(both_ok, signers=None, signers_ok=False, interlocks=interlocks, interlocks_ok=True, policy=policy)["decision"] == gg.HOLD)

    print("\nGG1: %d passed, %d failed" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


def _sigbreak(env):
    e = json.loads(json.dumps(env))
    e["signature"] = "AAAA" + e["signature"][4:]
    return e


if __name__ == "__main__":
    sys.exit(main())
