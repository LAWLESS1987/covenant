#!/usr/bin/env python3
"""
GS3 -- both-ways guard for gg.reverify_ledger_decisions (CLAUDE.md rule 8). The
in-tree audit re-runs C1..C7 over the honored ledger IN ORDER (A392 open item
"verify_grid_ledger does not re-run C1..C7"). This suite proves it BITES:

  * a clean ledger of valid actuations re-verifies (ok, every authorize() row
    replayed, no divergence);
  * a row recorded PERMIT that replay proves OVER-CAP (C5) is an INTEGRITY fault
    (ok=False) -- the record contradicts itself; removing it restores ok;
  * a signer revoked AFTER the fact makes those rows diverge at C2 as POLICY, NOT
    integrity (ok stays True) -- a mutable-policy change is named, never convicted;
  * halt / latched rows are NOT replayed (re-deciding them would be a false
    divergence), and the standalone verify_grid_ledger.py is untouched (still
    imports no covenant code).

Offline, no real grid. Run:  python test_gs3_ledger_reverify.py   (exit 0 = pass)
"""
import json
import os
import sys
import tempfile
import time

PASS = [0]
FAIL = [0]


def check(name, cond, detail=""):
    if cond:
        PASS[0] += 1
        print("  ok  ", name)
    else:
        FAIL[0] += 1
        print("  FAIL", name, "--", detail)


def main():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import covenant_grid_guard as gg
        import covenant_consent_chain as cc
    except Exception as e:  # noqa: BLE001
        # Degrade like GS1/GG1 when cryptography/numpy are absent: the boundary facts
        # that need no crypto still run, so a Linux archive without deps reads a real
        # (small) count, never a false green.
        print("  ..  cryptography/guard unavailable (%s) -- boundary-only" % type(e).__name__)
        import covenant_grid_guard as gg  # noqa: F401  (import itself is the check)
        check("GS3 boundary: reverify_ledger_decisions exists and is not wired into authorize()",
              hasattr(gg, "reverify_ledger_decisions")
              and "reverify" not in gg.authorize.__code__.co_names)
        print("\nGS3: %d passed, %d failed" % (PASS[0], FAIL[0]))
        return 1 if FAIL[0] else 0

    def _key():
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return (priv.private_bytes(serialization.Encoding.PEM,
                                   serialization.PrivateFormat.PKCS8,
                                   serialization.NoEncryption()).decode(),
                priv.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo).decode())

    d = tempfile.mkdtemp(prefix="gs3_")
    gg.LEDGER = os.path.join(d, "grid_commands.jsonl")
    gg.CHAIN = os.path.join(d, "grid_commands.chain.jsonl")
    gg.SIGNERS = os.path.join(d, "grid_signers.json")
    gg.INTERLOCKS = os.path.join(d, "grid_interlocks.json")
    gg.POLICY = os.path.join(d, "grid_policy.json")
    gg.HEARTBEAT = os.path.join(d, "grid_authz_heartbeat.jsonl")
    gg.SAFE_STATE = os.path.join(d, "GRID_SAFE_STATE.json")

    keys = {r: _key() for r in ("controller", "operator", "tetsu")}
    fpr = {r: gg._fpr(keys[r][1]) for r in keys}
    signers = {
        fpr["controller"]: {"role": "controller", "pubkey_pem": keys["controller"][1],
                            "allowed_actions": ["breaker_open", "load_shed", "halt"],
                            "zones": ["Z1"], "revoked": False},
        fpr["operator"]: {"role": "operator", "pubkey_pem": keys["operator"][1], "revoked": False},
        fpr["tetsu"]: {"role": "tetsu", "pubkey_pem": keys["tetsu"][1], "revoked": False},
    }
    interlocks = {"MAX_SHED_PCT": 20, "MAX_BREAKER_OPS": 3, "WINDOW_S": 3600,
                  "setpoint_ranges": {"Z1": [40, 60]}, "zone_allowlist": ["Z1"]}
    policy = {"ACTUATION": ["operator", "tetsu"], "MONITOR": [], "ADVISORY": []}

    def _write_signers(s):
        with open(gg.SIGNERS, "w") as f:
            json.dump(s, f)
    _write_signers(signers)
    with open(gg.INTERLOCKS, "w") as f:
        json.dump(interlocks, f)
    with open(gg.POLICY, "w") as f:
        json.dump(policy, f)

    T0 = gg._now()

    def _fresh_hb():
        with open(gg.HEARTBEAT, "w") as f:
            f.write(json.dumps(gg.make_heartbeat(fpr["operator"], keys["operator"][0],
                                                 ttl_s=600, now=T0)) + "\n")
    _fresh_hb()

    def _breaker(seq, now):
        p = gg.build_command(seq, "breaker_open", "Z1", {}, "ACTUATION", fpr["controller"], now=now)
        env = gg.sign_command(p, keys["controller"][0])
        env["payload"]["authz_tokens"] = [
            gg.make_authz_token(p, fpr["operator"], keys["operator"][0], now=now),
            gg.make_authz_token(p, fpr["tetsu"], keys["tetsu"][0], now=now)]
        return env

    # ---- clean ledger: 3 valid breaker_opens (at the cap, none over) all PERMIT
    gw = gg.GridEffectorGateway(ledger=gg.LEDGER, chain=gg.CHAIN, heartbeat=gg.HEARTBEAT,
                                safe_state=gg.SAFE_STATE)
    for s in range(3):
        dec = gw.submit(_breaker(s, T0), now=T0)
        if dec["decision"] != gg.PERMIT:
            check("GS3 setup: breaker %d PERMITs" % s, False, str(dec));
    rep = gg.reverify_ledger_decisions()
    check("GS3 a clean ledger re-verifies: ok, every authorize() row replayed, no divergence",
          rep["ok"] and rep["replayed"] == 3 and not rep["integrity"] and not rep["policy"], str(rep))

    # ---- INTEGRITY both-ways: forge a 4th row RECORDED PERMIT that is over the C5
    # breaker cap (3 already in window). Replay re-decides C5 REFUSE -> integrity.
    before = gg.reverify_ledger_decisions()
    check("GS3 ...and before the forged row, ok is True (both-ways anchor)", before["ok"], str(before))
    env4 = _breaker(3, T0)
    utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(T0))
    forged = {"seq": 3, "utc": utc, "t": utc, "honored_utc": T0, "command": env4,
              "signer_fpr": fpr["controller"], "decision": gg.PERMIT, "failed_check": None,
              "reason": "FORGED over-cap PERMIT", "detector_snapshot": {}}
    cc.append_consent(forged, ledger_path=gg.LEDGER, chain_path=gg.CHAIN)
    after = gg.reverify_ledger_decisions()
    check("GS3 a recorded PERMIT the record itself proves over the C5 cap is INTEGRITY (ok=False)",
          after["ok"] is False and any(i == 3 and "C5" in why for i, why in after["integrity"]),
          str(after))
    check("GS3 ...and it is NOT filed as mere policy drift (the record contradicts itself)",
          not any(i == 3 for i, _ in after["policy"]), str(after["policy"]))

    # remove the forged row -> ok restored (the other way)
    rows = cc.read_ledger_lines(gg.LEDGER)
    with open(gg.LEDGER, "wb") as f:
        f.write(b"\n".join(rows[:3]) + b"\n")
    restored = gg.reverify_ledger_decisions()
    check("GS3 broken the other way: removing the forged row restores ok",
          restored["ok"] and restored["replayed"] == 3, str(restored))

    # ---- POLICY both-ways: revoke the controller NOW. The 3 recorded PERMITs re-decide
    # C2 REFUSE -> POLICY divergence, ok STAYS True (a mutable-policy change, not a verdict).
    revoked = json.loads(json.dumps(signers))
    revoked[fpr["controller"]]["revoked"] = True
    _write_signers(revoked)
    pol = gg.reverify_ledger_decisions()
    check("GS3 a signer revoked AFTER the fact -> POLICY divergence at C2, never integrity, ok stays True",
          pol["ok"] and len(pol["policy"]) == 3 and not pol["integrity"]
          and all("C2" in why for _, why in pol["policy"]), str(pol))
    _write_signers(signers)      # restore
    back = gg.reverify_ledger_decisions()
    check("GS3 broken the other way: un-revoking the signer clears the divergence",
          back["ok"] and not back["policy"], str(back))

    # ---- SKIP: halt / pre-authorize rows are NOT replayed (no false divergence)
    d2 = tempfile.mkdtemp(prefix="gs3b_")
    gw2 = gg.GridEffectorGateway(ledger=os.path.join(d2, "l.jsonl"),
                                 chain=os.path.join(d2, "c.jsonl"),
                                 heartbeat=gg.HEARTBEAT, safe_state=os.path.join(d2, "s.json"))
    gw2.submit(_breaker(0, T0), now=T0)          # one real authorize() PERMIT
    halt_p = gg.build_command(0, "halt", "Z1", {}, "ACTUATION", fpr["controller"], now=T0)
    gw2.submit(gg.sign_command(halt_p, keys["controller"][0]), now=T0)   # halt: HOLD/HALT, latches
    skp = gg.reverify_ledger_decisions(ledger=gw2.ledger)
    check("GS3 halt (and the latched row after it) are not replayed; only the authorize() row is",
          skp["ok"] and skp["replayed"] == 1 and not skp["integrity"] and not skp["policy"], str(skp))

    # ---- the standalone verifier stays dependency-free (design invariant)
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "verify_grid_ledger.py"), encoding="utf-8").read()
    check("GS3 verify_grid_ledger.py still imports NO covenant code (reverify did not couple it)",
          "import covenant" not in src and "from covenant" not in src)
    check("GS3 reverify is an audit, never wired into the gate: authorize() never calls it",
          "reverify_ledger_decisions" not in gg.authorize.__code__.co_names)

    print("\nGS3: %d passed, %d failed" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
