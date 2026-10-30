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
    gg.SAFE_STATE = os.path.join(d, "GRID_SAFE_STATE.json")

    keys = {r: _key() for r in ("controller", "operator", "tetsu", "gateway")}
    fpr = {r: gg._fpr(keys[r][1]) for r in keys}
    KEYS.update(keys)
    FPR.update(fpr)
    signers = {
        # the shipped ops/grid_signers.json carries a string "_note"; keep one here
        # so every lookup is exercised against it (review finding: it crashed).
        "_note": "public keys only; a string entry every lookup must survive",
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


KEYS, FPR = {}, {}


def _write_hb(row):
    with open(gg.HEARTBEAT, "w") as f:
        f.write(json.dumps(row) + "\n")


def fresh_heartbeat(ttl=600, role="operator"):
    _write_hb(gg.make_heartbeat(FPR[role], KEYS[role][0], ttl_s=ttl))


def stale_heartbeat():
    _write_hb(gg.make_heartbeat(FPR["operator"], KEYS["operator"][0], ttl_s=600,
                                now=gg._now() - 9999))


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
    check("C1 detector ABSENT on good", gg.detect_grid_command_unauthenticated(envelope=env)["state"] == gg.ABSENT)

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
    check("C5 detector PRESENT", gg.detect_grid_interlock_breach(envelope=shed)["state"] == gg.PRESENT)
    check("C5 detector ABSENT on an in-bounds shed",
          gg.detect_grid_interlock_breach(envelope=actuation(keys, fpr, signers, policy, seq=2, action="load_shed",
                                                             magnitude={"pct": 5}))["state"] == gg.ABSENT)
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

    # ----- C7 / NEVER_AUTOMATIC: the grid words are in the LIVE tuple the engine
    # enforces (NA1 drives apply_remedy's refusal itself). The earlier check ran a
    # local copy of the substring test and so never read the engine at all.
    import covenant_highway as H
    missing = [w for w in gg.GRID_NEVER_AUTOMATIC_WORDS if w not in H.NEVER_AUTOMATIC]
    check("every grid word is in covenant_highway.NEVER_AUTOMATIC", missing == [])
    orig = H.NEVER_AUTOMATIC
    try:
        H.NEVER_AUTOMATIC = tuple(w for w in orig if w != "breaker")
        check("  (mutation: drop 'breaker' -> the check sees it missing)",
              [w for w in gg.GRID_NEVER_AUTOMATIC_WORDS if w not in H.NEVER_AUTOMATIC] == ["breaker"])
    finally:
        H.NEVER_AUTOMATIC = orig
    check("reasoning gateway holds no signing key", gg.GridEffectorGateway().gateway_priv_pem is None)

    # ----- class is fixed by the ACTION, not chosen by the signer (review HIGH)
    for lie in ("MONITOR", "ADVISORY"):
        mis = gg.sign_command(gg.build_command(9, "breaker_open", "Z1", {}, lie, fpr["controller"]),
                              keys["controller"][0])
        r = A(mis, signers, interlocks, policy)
        check("breaker_open labelled %s with no token REFUSEd at C6" % lie,
              r["decision"] == gg.REFUSE and r["failed_check"] == "C6")
    mis_shed = gg.sign_command(gg.build_command(9, "load_shed", "Z1", {"pct": 5}, "MONITOR", fpr["controller"]),
                               keys["controller"][0])
    check("load_shed labelled MONITOR REFUSEd", A(mis_shed, signers, interlocks, policy)["decision"] == gg.REFUSE)
    read_as_act = gg.sign_command(gg.build_command(9, "read", "Z1", {}, "ACTUATION", fpr["controller"]),
                                  keys["controller"][0])
    check("read labelled ACTUATION REFUSEd (class must equal the action's class)",
          A(read_as_act, mon_signer, interlocks, policy)["failed_check"] == "C6")
    check("an unlisted action has no class", gg.required_class("open_valve") is None)
    grant_ov = dict(signers); grant_ov[fpr["controller"]] = dict(
        signers[fpr["controller"]], allowed_actions=signers[fpr["controller"]]["allowed_actions"] + ["open_valve"])
    ov = actuation(keys, fpr, signers, policy, seq=9, action="open_valve")
    r = A(ov, grant_ov, interlocks, policy)
    check("an authentic, granted, together-voted UNKNOWN action is REFUSEd (C5 has no bounds for it)",
          r["decision"] == gg.REFUSE and r["failed_check"] == "C2-action")
    p_nc = gg.build_command(9, "breaker_open", "Z1", {}, "ACTUATION", fpr["controller"])
    del p_nc["class"]
    nc = gg.sign_command(p_nc, keys["controller"][0])
    nc["payload"]["authz_tokens"] = [gg.make_authz_token(p_nc, fpr[r_], keys[r_][0]) for r_ in ("operator", "tetsu")]
    check("a payload carrying NO class is judged by the derived class (together-voted -> PERMIT)",
          A(nc, signers, interlocks, policy)["decision"] == gg.PERMIT)
    p_nc2 = {k: v for k, v in p_nc.items() if k != "authz_tokens"}   # sign_command keeps the dict
    nc_tok = gg.sign_command(p_nc2, keys["controller"][0])
    check("  ...and with no tokens it is REFUSEd at C6 (the derived class still needs the vote)",
          A(nc_tok, signers, interlocks, policy)["failed_check"] == "C6")

    # ----- lifetime cap: a backdated long-TTL command is not "fresh" (review HIGH)
    p = gg.build_command(9, "breaker_open", "Z1", {}, "ACTUATION", fpr["controller"], ttl_s=4000,
                         now=gg._now() - 3700)
    back = gg.sign_command(p, keys["controller"][0])
    back["payload"]["authz_tokens"] = [gg.make_authz_token(p, fpr[r], keys[r][0], ttl_s=4000, now=gg._now() - 3700)
                                       for r in ("operator", "tetsu")]
    r = A(back, signers, interlocks, policy)
    check("backdated command with ttl 4000 REFUSEd at C3", r["decision"] == gg.REFUSE and r["failed_check"] == "C3")
    ok_ttl = actuation(keys, fpr, signers, policy, seq=9)
    check("  (control: the same command at ttl 300 PERMITs)", A(ok_ttl, signers, interlocks, policy)["decision"] == gg.PERMIT)
    p2 = gg.build_command(9, "breaker_open", "Z1", {}, "ACTUATION", fpr["controller"], ttl_s=300)
    longtok = gg.sign_command(p2, keys["controller"][0])
    longtok["payload"]["authz_tokens"] = [gg.make_authz_token(p2, fpr["operator"], keys["operator"][0], ttl_s=99999),
                                          gg.make_authz_token(p2, fpr["tetsu"], keys["tetsu"][0])]
    check("an authz token with an over-cap lifetime does not count",
          A(longtok, signers, interlocks, policy)["failed_check"] == "C6")

    # ----- magnitude: negative / non-numeric shed refused, never an exception
    for bad_pct in (-100, "lots", None, float("nan"), 101):
        e = actuation(keys, fpr, signers, policy, seq=9, action="load_shed", magnitude={"pct": bad_pct})
        r = A(e, signers, interlocks, policy)
        check("load_shed pct=%r REFUSEd at C5" % (bad_pct,), r["decision"] == gg.REFUSE and r["failed_check"] == "C5")

    # ----- '_note' string entry in the allowlist never crashes a lookup
    note_tok = actuation(keys, fpr, signers, policy, seq=9)
    note_tok["payload"]["authz_tokens"].append({"issuer_fpr": "_note"})
    check("token issuer '_note' ignored, no crash", A(note_tok, signers, interlocks, policy)["decision"] == gg.PERMIT)
    note_cmd = actuation(keys, fpr, signers, policy, seq=9)
    note_cmd["payload"]["signer_fpr"] = "_note"
    check("signer_fpr '_note' REFUSEd at C2, no crash", A(note_cmd, signers, interlocks, policy)["failed_check"] == "C2")

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

    # ----- heartbeat must be SIGNED by an authority-holder (review MEDIUM)
    _write_hb({"expires_utc": 9999999999, "issued_utc": gg._now()})
    check("unsigned far-future heartbeat is NOT fresh", not gg.heartbeat_fresh(path=gg.HEARTBEAT))
    fresh_heartbeat(role="controller")
    check("heartbeat signed by a controller (not an authority-holder) is NOT fresh",
          not gg.heartbeat_fresh(path=gg.HEARTBEAT))
    _write_hb(gg.make_heartbeat(FPR["operator"], KEYS["operator"][0], ttl_s=99999))
    check("authority-signed heartbeat with lifetime > limit is NOT fresh", not gg.heartbeat_fresh(path=gg.HEARTBEAT))
    forged = gg.make_heartbeat(FPR["operator"], KEYS["operator"][0])
    forged["issued_utc"] += 5          # lifetime unchanged: only the SIGNATURE can catch this
    forged["expires_utc"] += 5
    _write_hb(forged)
    check("heartbeat edited after signing is NOT fresh", not gg.heartbeat_fresh(path=gg.HEARTBEAT))
    fresh_heartbeat(role="tetsu")
    check("heartbeat signed by tetsu is fresh", gg.heartbeat_fresh(path=gg.HEARTBEAT))
    fresh_heartbeat()
    check("heartbeat signed by the operator is fresh", gg.heartbeat_fresh(path=gg.HEARTBEAT))

    # ----- the latch is on DISK: a new gateway object cannot resume (review MEDIUM)
    gw3 = gg.GridEffectorGateway(ledger=gg.LEDGER, chain=gg.CHAIN, heartbeat=gg.HEARTBEAT)
    check("a fresh gateway after the halt is still latched", gw3.latched_hold)
    e_l = actuation(keys, fpr, signers, policy, seq=4)
    n_rows = len(gg._honored_rows(gg.LEDGER))
    r = gw3.submit(e_l)
    check("latched: a valid actuation HOLDs, nothing actuated",
          r["decision"] == gg.HOLD and r["failed_check"] == "LATCHED" and gw3.effector.actuated == [])
    last = gg._honored_rows(gg.LEDGER)[-1]
    check("latched: the row says HOLD, never PERMIT", len(gg._honored_rows(gg.LEDGER)) == n_rows + 1
          and last["decision"] == gg.HOLD)
    check("latched: the nonce was not consumed", e_l["payload"]["nonce"] not in gg._seen_nonces(gg.LEDGER))
    lid = gw3.latch_id()
    # a FULL together-vote, but bound to an earlier latch: only the latch binding can refuse it
    stale_resume = [gg.make_resume_token("some-earlier-latch", fpr[r_], keys[r_][0]) for r_ in ("operator", "tetsu")]
    check("resume bound to an EARLIER latch is refused", gw3.clear_hold(stale_resume) is False and gw3.latched_hold)
    ctrl_resume = gg.make_resume_token(lid, fpr["controller"], keys["controller"][0])
    check("resume signed by a controller is refused", gw3.clear_hold(ctrl_resume) is False and gw3.latched_hold)
    check("resume from '_note' refused, no crash", gw3.clear_hold({"issuer_fpr": "_note"}) is False)
    t_res = gg.make_resume_token(lid, fpr["tetsu"], keys["tetsu"][0])
    o_res = gg.make_resume_token(lid, fpr["operator"], keys["operator"][0])
    check("resume from tetsu ALONE is refused (resume restores actuation: together-vote)",
          gw3.clear_hold(t_res) is False and gw3.latched_hold)
    check("resume from the operator ALONE is refused", gw3.clear_hold([o_res]) is False and gw3.latched_hold)
    check("two resumes from the SAME role do not make a vote",
          gw3.clear_hold([t_res, gg.make_resume_token(lid, fpr["tetsu"], keys["tetsu"][0])]) is False)
    with open(gg.POLICY) as f:
        pol_saved = f.read()
    try:
        with open(gg.POLICY, "w") as f:
            json.dump(dict(policy, RESUME=[]), f)
        check("a declared EMPTY resume policy still needs the together-vote (never automatic)",
              gw3.clear_hold([o_res]) is False and gw3.latched_hold)
    finally:
        with open(gg.POLICY, "w") as f:
            f.write(pol_saved)
    check("resume from operator + tetsu, both bound to THIS latch, clears it",
          gw3.clear_hold([o_res, t_res]) is True)
    check("  ...and a new gateway object sees it cleared",
          not gg.GridEffectorGateway(ledger=gg.LEDGER, chain=gg.CHAIN, heartbeat=gg.HEARTBEAT).latched_hold)
    check("after resume the held command PERMITs (its nonce was free)", gw3.submit(e_l)["decision"] == gg.PERMIT)
    with open(gg.SAFE_STATE, "w") as f:
        f.write("{not json")
    check("an unreadable latch file reads LATCHED (fail closed)", gg.GridEffectorGateway().latched_hold)
    os.remove(gg.SAFE_STATE)

    # ----- a crashing input is REFUSEd AND recorded (every attempt appends a row)
    n_rows = len(gg._honored_rows(gg.LEDGER))
    hn = gg.sign_command(gg.build_command(0, "halt", "Z1", {}, "ACTUATION", fpr["controller"]), keys["controller"][0])
    hn["payload"]["signer_fpr"] = "_note"
    r = gw3.submit(hn)
    check("halt from signer '_note' REFUSEd and recorded",
          r["decision"] == gg.REFUSE and len(gg._honored_rows(gg.LEDGER)) == n_rows + 1)
    r = gw3.submit({"payload": "not a dict"})
    check("a malformed envelope REFUSEd and recorded",
          r["decision"] == gg.REFUSE and len(gg._honored_rows(gg.LEDGER)) == n_rows + 2)
    real_authorize = gg.authorize
    try:
        def boom(*a, **k):
            raise RuntimeError("injected fault inside a check")
        gg.authorize = boom
        r = gw3.submit(actuation(keys, fpr, signers, policy, seq=50))
    finally:
        gg.authorize = real_authorize
    check("a check that CRASHES is REFUSEd at C0 and still recorded",
          r["decision"] == gg.REFUSE and r["failed_check"] == "C0"
          and len(gg._honored_rows(gg.LEDGER)) == n_rows + 3)

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

    # ----- the C5 window counts by HONORED time, not the signer's issued_utc
    d2 = tempfile.mkdtemp(prefix="gg1w_")
    L2, C2 = os.path.join(d2, "l.jsonl"), os.path.join(d2, "c.jsonl")
    with open(gg.INTERLOCKS) as f:
        il_saved = f.read()
    with open(gg.INTERLOCKS, "w") as f:
        json.dump(dict(interlocks, WINDOW_S=60), f)
    try:
        gw4 = gg.GridEffectorGateway(ledger=L2, chain=C2, heartbeat=gg.HEARTBEAT,
                                     safe_state=os.path.join(d2, "s.json"))
        res = [gw4.submit(actuation(keys, fpr, signers, policy, seq=i, now=gg._now() - 200))["decision"]
               for i in range(4)]
        check("3 breaker ops dated 200s ago (window 60s): the 4th is REFUSEd",
              res == [gg.PERMIT, gg.PERMIT, gg.PERMIT, gg.REFUSE])
    finally:
        with open(gg.INTERLOCKS, "w") as f:
            f.write(il_saved)

    # ----- gateway-signed rows pass the STANDALONE verifier (both ways)
    import verify_grid_ledger as V
    d3 = tempfile.mkdtemp(prefix="gg1s_")
    L3, C3 = os.path.join(d3, "l.jsonl"), os.path.join(d3, "c.jsonl")
    pubf = os.path.join(d3, "gw.pem")
    with open(pubf, "w") as f:
        f.write(keys["gateway"][1])
    gw5 = gg.GridEffectorGateway(gateway_priv_pem=keys["gateway"][0], ledger=L3, chain=C3,
                                 heartbeat=gg.HEARTBEAT, safe_state=os.path.join(d3, "s.json"))
    # seq 100: above anything in the main ledger, so a snapshot that wrongly read
    # the main ledger would see neither a reused nonce nor a stale seq.
    e5 = actuation(keys, fpr, signers, policy, seq=100)
    check("signed gateway PERMITs", gw5.submit(e5)["decision"] == gg.PERMIT)
    gw5.submit(e5)   # a replay: a REFUSE row, also signed
    code, lines = V.run(L3, C3, pubf)
    check("verify_grid_ledger PASSes every gateway-signed row", code == 0 and "2 gateway sigs valid" in lines[0])
    with open(L3, encoding="utf-8") as f:
        raw = f.read()
    rows = raw.splitlines()
    obj = json.loads(rows[0]); obj["reason"] = obj["reason"] + "!"
    with open(L3 + ".edit", "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n" + "\n".join(rows[1:]) + "\n")
    code_bad, _ = V.run(L3 + ".edit", C3, pubf)
    check("  (an edited row FAILs the verifier)", code_bad == 1)

    # ----- the gateway's detector snapshot describes ITS OWN ledger
    snap_row = gg._honored_rows(L3)[-1]["detector_snapshot"]
    check("replay row's snapshot reads replay PRESENT from the gateway's own ledger",
          snap_row.get("grid_command_replay") == gg.PRESENT)
    empty = os.path.join(d3, "empty.jsonl")
    check("  (the same envelope over an empty ledger reads ABSENT)",
          gg.snapshot_detectors(e5, ledger=empty)["grid_command_replay"] == gg.ABSENT)

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
