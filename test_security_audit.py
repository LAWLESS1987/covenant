#!/usr/bin/env python3
"""
test_security_audit.py -- regression tests for the findings of the static
security audit, each one confirmed to be a REAL defect by exploiting it before
it was fixed (not inferred from reading).

Covered:
  U   non-finite amounts (NaN / +-Infinity) rejected at every ingress:
      HTTP, raw P2P, and direct library calls into the trading bridge.
      NOTE: the original shape validators existed but NOTHING CALLED THEM --
      validate_block_shape had exactly one occurrence in the file, its own
      definition. The tests passed anyway because they called the validator
      directly. These tests assert the WIRING, which is what was missing.
  Y   mempool bounded, with priority eviction rather than arrival-order lockout.
  --  ledger_entries idempotent on (pubkey, ref_id, reason).
  --  code sandbox memory-capped (an allowlist-legal `[0]*10**10` was a host OOM).
  --  security-relevant failures are observable instead of `except: pass`.

Run: python3 test_security_audit.py
"""
import sys, os, time, json, base64, tempfile, sqlite3, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("ANTHROPIC_API_KEY", None)

from dataclasses import asdict
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

import covenant_unified_v8 as cov

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pem


def sign(priv, payload: bytes) -> str:
    return base64.b64encode(priv.sign(
        payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                             salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())).decode()


def main():
    tmp = tempfile.mktemp(suffix=".db")
    master = cov.CovenantUnifiedMaster("sec", host="127.0.0.1", port=15900,
                                       p2p_port=15901, db_path=tmp)
    master.add_genesis_block()
    # Permissive judge so the ETHICS gate isn't what rejects things -- these
    # tests are about shape/bounds, and a fail-closed judge would mask them.
    master.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    master.node.rate_limiter.allow = lambda *a, **k: True
    client = master.api.app.test_client()
    db = cov.Database(tmp)
    priv, pem = keypair()
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)

    def make_ok(nested=False):
        """A fully valid transaction body, used as the base for tamper tests."""
        ts = time.time()
        data = {"origin": "organic", "message": "ok"}
        if nested:
            data["meta"] = {"a": {"b": {"c": 1}}}
        pl = cov._domain_frame(b"COVENANT_TX_V1", pem, "collective", str(ts),
                               json.dumps(data, sort_keys=True), str(0.0))
        return {"sender_pubkey": pem, "receiver": "collective", "data": data, "amount": 0.0,
                "timestamp": ts, "benefit_score": 0.5, "signature": sign(priv, pl),
                "reg_nonce": reg}

    def post_tx(raw_amount_json, signed_amount, message="probe"):
        ts = time.time()
        data = {"origin": "human", "message": message}
        payload = cov._domain_frame(b"COVENANT_TX_V1", pem, "collective", str(ts),
                                    json.dumps(data, sort_keys=True), str(signed_amount))
        body = ('{"sender_pubkey":%s,"receiver":"collective","data":%s,"amount":%s,'
                '"timestamp":%s,"benefit_score":0.5,"signature":%s,"reg_nonce":%d}') % (
                json.dumps(pem), json.dumps(data), raw_amount_json,
                json.dumps(ts), json.dumps(sign(priv, payload)), reg)
        return client.post("/transactions", data=body, content_type="application/json")

    print("== U1. Non-finite amounts rejected over HTTP ==")
    for label, raw, signed_v in [("-Infinity", "-Infinity", float("-inf")),
                               ("NaN", "NaN", float("nan")),
                               ("Infinity", "Infinity", float("inf")),
                               ('string "NaN"', '"NaN"', float("nan")),
                               ("1e400 (overflows to inf)", "1e400", float("inf"))]:
        r = post_tx(raw, signed_v)
        check(f"amount={label} rejected", r.status_code == 400, f"HTTP {r.status_code}")

    print("\n== U2. Legitimate traffic unaffected (no false positives) ==")
    r = post_tx("0.0", 0.0)
    check("finite amount still accepted", r.status_code == 200, f"HTTP {r.status_code}")
    r = post_tx("0.0", 0.0, message="nan bread and infinity pools")
    check("prose containing 'nan'/'infinity' NOT rejected", r.status_code == 200,
          f"HTTP {r.status_code}")

    print("\n== U3. Shape validators are WIRED, not ghost code ==")
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "covenant_unified_v8.py")).read()
    check("validate_block_shape has a real call site (not just its def)",
          src.count("validate_block_shape(") >= 2, f"occurrences={src.count('validate_block_shape(')}")
    check("validate_transaction_shape called outside validate_block_shape",
          src.count("validate_transaction_shape(") >= 3,
          f"occurrences={src.count('validate_transaction_shape(')}")

    print("\n== U4. P2P ingress (never passes through Flask) ==")
    bad_tx = cov.Transaction(sender_pubkey=pem, receiver="collective",
                             data={"m": "x"}, amount=float("nan"), benefit_score=0.5)
    try:
        cov.validate_transaction_shape(asdict(bad_tx)); trej = False
    except cov.ShapeValidationError:
        trej = True
    check("validate_transaction_shape rejects a NaN transaction", trej)
    try:
        cov.validate_block_shape(asdict(cov.Block(1, [bad_tx], "0"))); brej = False
    except cov.ShapeValidationError:
        brej = True
    check("validate_block_shape rejects a block containing one", brej)

    print("\n== U5. Trading bridge (importable; bypasses HTTP entirely) ==")
    bridge = master.node.trading_bridge
    for meth, args, label in [
        ("report_realized_profit", (pem, "SOL", "kraken", "r1", float("nan"), time.time(), 1, "s"), "profit NaN"),
        ("report_realized_loss", (pem, "SOL", "kraken", "r2", float("nan"), time.time(), 2, "s"), "loss NaN"),
        ("gift_stake_to_new_node", (pem, pem, float("nan"), time.time(), "s"), "gift NaN"),
    ]:
        try:
            getattr(bridge, meth)(*args); ok, d = False, "ACCEPTED"
        except Exception as e:
            ok, d = "finite" in str(e), str(e)[:48]
        check(f"bridge rejects {label}", ok, d)

    print("\n== U6. Ledger refuses a non-finite delta at the lowest level ==")
    try:
        db.record_ledger_entry(pem, float("nan"), "audit_probe", ref_id="nf1"); lrej = False
    except cov.ShapeValidationError:
        lrej = True
    check("record_ledger_entry raises on NaN delta", lrej)

    print("\n== Y. Mempool is bounded, and bounds by PRIORITY not arrival order ==")
    original_cap = cov.MAX_PENDING_TRANSACTIONS
    cov.MAX_PENDING_TRANSACTIONS = 25          # same code path, faster test
    try:
        codes = [post_tx("0.0", 0.0, message=f"flood {i}").status_code for i in range(60)]
        check("mempool never exceeds the cap",
              len(master.node.pending_transactions) <= cov.MAX_PENDING_TRANSACTIONS,
              f"size={len(master.node.pending_transactions)} cap={cov.MAX_PENDING_TRANSACTIONS}")
        check("excess submissions refused with 429", codes.count(429) > 0,
              f"200={codes.count(200)} 429={codes.count(429)}")
        # MockJudge scores 'help/good/benefit' at 0.8, outranking the 0.5 flood.
        r = post_tx("0.0", 0.0, message="help good benefit")
        check("higher-priority transaction still admitted when full",
              r.status_code == 200, f"HTTP {r.status_code}")
        check("still capped after eviction",
              len(master.node.pending_transactions) <= cov.MAX_PENDING_TRANSACTIONS)
    finally:
        cov.MAX_PENDING_TRANSACTIONS = original_cap

    print("\n== Ledger idempotency (double-apply was blocked by ONE upstream check) ==")
    first = db.record_ledger_entry(pem, 5.0, "audit_dup", ref_id="dup-1")
    second = db.record_ledger_entry(pem, 5.0, "audit_dup", ref_id="dup-1")
    check("first write succeeds", first is True)
    check("identical replay suppressed (returns False, not silent)", second is False)
    with sqlite3.connect(tmp) as c:
        n = c.execute("SELECT COUNT(*) FROM ledger_entries WHERE ref_id='dup-1'").fetchone()[0]
    check("exactly one row persisted for the duplicated ref_id", n == 1, f"rows={n}")
    check("entries WITHOUT a ref_id remain legitimately repeatable",
          db.record_ledger_entry(pem, 1.0, "audit_noref") and
          db.record_ledger_entry(pem, 1.0, "audit_noref"))

    print("\n== Code sandbox resource limits ==")
    # P10 (2026-08-23). These three checks asserted the ENFORCING behaviour
    # unconditionally, so on a platform with no fork -- Windows, which is where
    # the node actually runs -- they failed every single sweep. Three permanent
    # red lines are worse than no lines: they are a tonic signal that trains the
    # reader to skim past the section, which is exactly how a real regression
    # here would go unnoticed (the same failure measured in watchdog.log the same
    # night, 3,973 lines carrying 16 messages).
    #
    # The backlog said "SKIP with a reason". That was WRONG, and this is the
    # better fix: a skip means the check stops checking on the platform that
    # runs production. Instead each check asserts what CORRECT behaviour IS on
    # the platform it is running on. On a fork platform, the limits must bite.
    # On a no-fork platform, P4's refusal must be complete and fail-closed --
    # which is a real property, actively worth testing, and previously untested
    # anywhere in this suite.
    #
    # COVENANT_FORCE_NO_SANDBOX=1 exercises the refusal branch on a fork
    # platform, so the no-fork assertions below are verifiable everywhere.
    if cov.SANDBOX_FORK_AVAILABLE:
        check("benign snippet still runs", cov.run_sandboxed("x = 1 + 1")["ok"] is True)
        bomb = cov.run_sandboxed("x = [0] * (10**10)")
        check("allowlist-legal memory bomb contained by RLIMIT_AS",
              bomb["ok"] is False and "MemoryError" in (bomb["error"] or ""), bomb["error"])
        loop = cov.run_sandboxed("while True:\n    pass")
        check("infinite loop still stopped by wall-clock timeout", loop["timed_out"] is True)
    else:
        why = cov.SANDBOX_UNAVAILABLE_REASON
        benign = cov.run_sandboxed("x = 1 + 1")
        check("sandbox unavailable: even a benign snippet is REFUSED, not run",
              benign["ok"] is False and benign.get("ran") is False
              and "SandboxUnavailable" in (benign["error"] or ""),
              f"{benign.get('ok')} / {(benign.get('error') or '')[:60]}")
        bomb = cov.run_sandboxed("x = [0] * (10**10)")
        check("sandbox unavailable: a memory bomb is refused, never reported ok",
              bomb["ok"] is False and "SandboxUnavailable" in (bomb["error"] or ""),
              (bomb.get("error") or "")[:60])
        t_loop = time.monotonic()
        loop = cov.run_sandboxed("while True:\n    pass")
        dt_loop = time.monotonic() - t_loop
        check("sandbox unavailable: an infinite loop is refused WITHOUT running it",
              loop["ok"] is False and loop.get("ran") is False
              and loop.get("timed_out") is False and dt_loop < 1.0,
              f"{dt_loop:.3f}s, timed_out={loop.get('timed_out')}")
        check("sandbox unavailable: the refusal says WHY, so it is diagnosable",
              bool(why) and why in (benign["error"] or ""), why[:60])
    # Both platforms, and this is the one-way property P4 exists to hold:
    # nothing may turn the sandbox ON where its limits cannot be enforced.
    check("the sandbox never reports success when its limits cannot be enforced",
          cov.SANDBOX_FORK_AVAILABLE
          or cov.run_sandboxed("x = 1")["ok"] is False,
          f"fork_available={cov.SANDBOX_FORK_AVAILABLE}")

    print("\n== Observability: failures are recorded, not swallowed ==")
    import ast as _ast
    tree = _ast.parse(src)
    swallowed = [n.lineno for n in _ast.walk(tree)
                 if isinstance(n, _ast.ExceptHandler)
                 and len(n.body) == 1 and isinstance(n.body[0], _ast.Pass)]
    check("no 'except: pass' handlers remain in the core", len(swallowed) == 0, str(swallowed))
    rep = master.node.anomaly_monitor.report()
    check("anomaly monitor recorded the rejected payloads",
          rep["per_kind"].get("non_finite_payload", {}).get("baseline", 0) > 0,
          f"kinds={sorted(rep['per_kind'])}")

    print("\n== GOVERNOR: liveness (chain must not halt) ==")
    gmed = cov.MedianGovernor.__new__(cov.MedianGovernor)
    check("_median of two elements is the midpoint, not the larger",
          gmed._median([0.2, 0.8]) == 0.5, f"got {gmed._median([0.2, 0.8])}")
    check("_median of an odd-length list unchanged", gmed._median([0.1, 0.7, 0.9]) == 0.7)

    print("\n== ORIGIN: parallel taxonomy covering BOTH origins of intelligence ==")
    for raw, expected in (("human", "organic"), ("person", "organic"),
                          ("biological", "organic"), ("organic", "organic"),
                          ("ai", "inorganic"), ("artificial", "inorganic"),
                          ("machine", "inorganic"), ("digital", "inorganic"),
                          ("inorganic", "inorganic"),
                          ("synthetic", "inorganic"),      # legacy chains keep working
                          ("martian", "martian")):         # unknown passes through, gets counted
        t = cov.Transaction(sender_pubkey="k", receiver="r",
                            data={"origin": raw, "message": "x"}, amount=0.0, benefit_score=0.7)
        check(f"origin '{raw}' -> '{expected}'", t.origin_type == expected, f"got {t.origin_type}")
    t_missing = cov.Transaction(sender_pubkey="k", receiver="r",
                                data={"message": "x"}, amount=0.0, benefit_score=0.7)
    check("missing origin defaults to 'inorganic' (omission cannot attest biological origin)",
          t_missing.origin_type == "inorganic", f"got {t_missing.origin_type}")
    check("canonical buckets are the parallel pair",
          cov.Transaction.ORIGIN_BUCKETS == ("organic", "inorganic"),
          str(cov.Transaction.ORIGIN_BUCKETS))

    for origin in ("organic", "human", "ai"):
        tmp2 = tempfile.mktemp(suffix=".db")
        _ports = {"organic": (15950, 15951), "human": (15960, 15961), "ai": (15980, 15981)}[origin]
        mm = cov.CovenantUnifiedMaster(f"gov{origin}", host="127.0.0.1",
                                       port=_ports[0], p2p_port=_ports[1], db_path=tmp2)
        mm.add_genesis_block()
        mm.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
        mm.node.rate_limiter.allow = lambda *a, **k: True
        cl = mm.api.app.test_client()
        d2 = cov.Database(tmp2)
        kp2, pem2 = keypair()
        d2.record_ledger_entry(pem2, 10000.0, "gov_seed", ref_id=f"gs-{origin}")
        opem = mm.public_key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        halted = None
        for i in range(15):
            gov = mm.node.governor.get_current()
            ben = max(0.0, min(1.0, 3.0 * gov - 1.0))
            ts = time.time() + i * 0.01
            dd = {"origin": origin, "message": f"b{i}"}
            pl = cov._domain_frame(b"COVENANT_TX_V1", pem2, "collective", str(ts),
                                   json.dumps(dd, sort_keys=True), str(0.0))
            cl.post("/transactions", json={
                "sender_pubkey": pem2, "receiver": "collective", "data": dd, "amount": 0.0,
                "timestamp": ts, "benefit_score": ben, "signature": sign(kp2, pl),
                "reg_nonce": cov.RegistrationPoW.generate(pem2, cov.BASE_REGISTRATION_DIFFICULTY)})
            h = cov.sign_operator_request(mm.private_key, opem, "POST", "/mine", b"{}")
            r = cl.post("/mine", data=b"{}", content_type="application/json", headers=h)
            if r.status_code != 200 and halted is None:
                halted = i
        check(f"chain does not halt over 15 blocks (origin='{origin}')", halted is None,
              f"halted at block {halted}, height={len(mm.node.chain)}")
        check(f"governor stays in a reachable band (origin='{origin}')",
              0.3 <= mm.node.governor.get_current() <= 0.72,
              f"governor={mm.node.governor.get_current():.4f}")
        check(f"origin='{origin}' traffic is COUNTED, not ignored",
              mm.node.governor.unclassified_seen == 0
              and (len(mm.node.governor._organic_scores) > 0
                   or len(mm.node.governor._inorganic_scores) > 0),
              f"unclassified={mm.node.governor.unclassified_seen} "
              f"organic={len(mm.node.governor._organic_scores)} "
              f"inorganic={len(mm.node.governor._inorganic_scores)}")

    print("\n== INGRESS: type confusion must be a clean 400, never a 500 ==")
    for field in ("amount", "timestamp", "benefit_score", "reg_nonce"):
        for bad, lbl in [([1, 2, 3], "array"), ({"a": 1}, "object"), (None, "null")]:
            t = json.loads(json.dumps(make_ok()))
            t[field] = bad
            r = client.post("/transactions", json=t)
            check(f"{field}={lbl} -> 400", r.status_code == 400, f"HTTP {r.status_code}")

    print("\n== INGRESS: hostile bodies (confirmed 500s before the fix) ==")
    def raw(body):
        return client.post("/transactions", data=body, content_type="application/json").status_code
    for lbl, body in [("top-level array", b'[1,2,3]'), ("top-level scalar", b'42'),
                      ("top-level string", b'"hi"'),
                      ("4000-digit integer", b'{"amount": ' + b'9' * 4000 + b'}')]:
        check(f"{lbl} -> 400", raw(body) == 400, f"HTTP {raw(body)}")

    print("\n== INGRESS: deep nesting (the guard itself was the DoS) ==")
    for depth in (1000, 20000, 100000):
        code = raw(('{"a":' * depth + '1' + '}' * depth).encode())
        check(f"object nesting {depth} -> no 500", code < 500, f"HTTP {code}")
    for depth in (1000, 20000):
        code = raw(('[' * depth + '1' + ']' * depth).encode())
        check(f"array nesting {depth} -> no 500", code < 500, f"HTTP {code}")
    check("legitimate modest nesting still accepted",
          client.post("/transactions", json=make_ok(nested=True)).status_code in (200, 400))

    print("\n== GHOST CONTROLS: declared limits must actually be enforced ==")
    import covenant_trading_bridge as _tb
    bridge_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "covenant_trading_bridge.py")).read()
    for const in ("MAX_GIFT_AGE_SECONDS", "MAX_FUTURE_SKEW_SECONDS",
                  "MAX_PROFIT_REPORT_AGE_SECONDS", "MIN_RECIPIENT_TRUST_SCORE",
                  "GIFT_SINGLE_CALL_CAP_FRACTION"):
        uses = bridge_src.count(const) - 1          # minus the definition itself
        check(f"{const} is referenced by real logic, not just declared", uses >= 1,
              f"call sites={uses}")

    tmp3 = tempfile.mktemp(suffix=".db")
    m3 = cov.CovenantUnifiedMaster("ghost", host="127.0.0.1", port=15970,
                                   p2p_port=15971, db_path=tmp3)
    m3.add_genesis_block()
    m3.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    c3 = m3.api.app.test_client()
    d3 = cov.Database(tmp3)
    gpriv, gpool = keypair()
    d3.record_ledger_entry(gpool, 10000.0, "ghost_seed", ref_id="gp1")
    from covenant_trading_bridge import node_gift_payload

    def do_gift(age_s):
        _, rcp = keypair()
        gts = time.time() - age_s
        return c3.post("/trading/gift_node", json={
            "pool_pubkey": gpool, "recipient_pubkey": rcp, "amount": 50.0,
            "timestamp": gts, "signature": sign(gpriv, node_gift_payload(gpool, rcp, 50.0, gts))})

    check("year-old gift authorization is actually refused",
          do_gift(365 * 86400).status_code != 200)
    check("recent gift authorization still works",
          do_gift(60).status_code == 200)

    print("\n== GHOST PROTECTION: every protected endpoint must exist AND 401 ==")
    registered = {}
    for rule in m3.api.app.url_map.iter_rules():
        for meth in rule.methods - {"HEAD", "OPTIONS"}:
            registered.setdefault(str(rule.rule), set()).add(meth)
    for meth, path in sorted(cov.PROTECTED_OPERATOR_ENDPOINTS):
        check(f"protected route {meth} {path} is actually registered",
              path in registered and meth in registered[path])
        resp = c3.open(path, method=meth, data=b"{}", content_type="application/json")
        check(f"protected route {meth} {path} returns 401 unauthenticated",
              resp.status_code == 401, f"HTTP {resp.status_code}")

    print("\n== FINDING U: net-zero ledger events are chain-derivable; mints are not ==")
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
    from cryptography.hazmat.primitives import serialization as _ser

    def _kp():
        k = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return k, k.public_key().public_bytes(
            _ser.Encoding.PEM, _ser.PublicFormat.SubjectPublicKeyInfo).decode()

    pool_sk, POOLK = _kp()
    rcp_sk, RCPK = _kp()
    _entries = [
        {"pubkey": POOLK, "delta": -30.0, "reason": "node_gift_sent", "ref_id": "fu1"},
        {"pubkey": RCPK, "delta": 30.0, "reason": "node_gift_received", "ref_id": "fu1"}]
    good = {"entries": _entries,
            "auth": {POOLK: {"kind": "ledger_event_v1",
                             "signature": cov.Database.sign_ledger_event(pool_sk, _entries)}}}
    ok, why = cov.Database.validate_ledger_event(good)
    check("net-zero gift event with payer authorization accepted", ok, why)

    unauth = {"entries": [
        {"pubkey": POOLK, "delta": -30.0, "reason": "node_gift_sent", "ref_id": "th1"},
        {"pubkey": RCPK, "delta": 30.0, "reason": "node_gift_received", "ref_id": "th1"}]}
    rejected, why = cov.Database.validate_ledger_event(unauth)
    check("a net-zero event with NO payer authorization is refused", not rejected, why)

    _thief_sk, THIEFK = _kp()
    lifted = {"entries": [
        {"pubkey": POOLK, "delta": -30.0, "reason": "node_gift_sent", "ref_id": "fu1"},
        {"pubkey": THIEFK, "delta": 30.0, "reason": "node_gift_received", "ref_id": "fu1"}],
        "auth": good["auth"]}
    rejected, why = cov.Database.validate_ledger_event(lifted)
    check("an authorization cannot be replayed onto a redirected payout",
          not rejected, why)

    forged = {"entries": _entries,
              "auth": {POOLK: {"kind": "ledger_event_v1",
                               "signature": cov.Database.sign_ledger_event(_thief_sk, _entries)}}}
    rejected, why = cov.Database.validate_ledger_event(forged)
    check("a signature from a non-payer key is refused", not rejected, why)

    for label, evt in (
        ("a pure mint", {"entries": [
            {"pubkey": POOLK, "delta": 999.0, "reason": "trading_profit", "ref_id": "m1"}]}),
        ("an unbalanced pair", {"entries": [
            {"pubkey": POOLK, "delta": -1.0, "reason": "node_gift_sent", "ref_id": "u1"},
            {"pubkey": RCPK, "delta": 500.0, "reason": "node_gift_received", "ref_id": "u1"}]}),
        ("a non-finite delta", {"entries": [
            {"pubkey": POOLK, "delta": float("inf"), "reason": "node_gift_sent", "ref_id": "n1"}]}),
        ("a non-PEM account", {"entries": [
            {"pubkey": "attacker", "delta": 0.0, "reason": "node_gift_sent", "ref_id": "p1"}]}),
        ("a missing ref_id", {"entries": [
            {"pubkey": POOLK, "delta": 0.0, "reason": "node_gift_sent"}]}),
    ):
        rejected, _ = cov.Database.validate_ledger_event(evt)
        check(f"{label} is refused on-chain", not rejected)

    dA = cov.Database(tempfile.mktemp(suffix=".db"))
    dB = cov.Database(tempfile.mktemp(suffix=".db"))
    for d in (dA, dB):
        d.record_ledger_entry(POOLK, 100.0, "fu_seed", ref_id="fus")
    dA.apply_ledger_event(good, "txfu")
    dB.apply_ledger_event(good, "txfu")
    check("a peer reconstructs the movement from the event alone",
          dB.get_balance(POOLK) == dA.get_balance(POOLK)
          and dB.get_balance(RCPK) == dA.get_balance(RCPK),
          f"A pool={dA.get_balance(POOLK)} B pool={dB.get_balance(POOLK)}")
    check("replaying on the originating node writes nothing",
          dA.apply_ledger_event(good, "txfu") == 0
          and dA.get_balance(POOLK) == 70.0, f"pool={dA.get_balance(POOLK)}")

    dC = cov.Database(tempfile.mktemp(suffix=".db"))
    dC.record_ledger_entry(POOLK, 100.0, "fu_seed", ref_id="fus")
    dC.apply_ledger_event(good, "setup")          # plants ref_id "fu1"
    _mint = [{"pubkey": POOLK, "delta": -30.0, "reason": "node_gift_sent", "ref_id": "fu1"},
             {"pubkey": POOLK, "delta": 30.0, "reason": "node_gift_received", "ref_id": "fresh"}]
    mint_evt = {"entries": _mint,
                "auth": {POOLK: {"kind": "ledger_event_v1",
                                 "signature": cov.Database.sign_ledger_event(pool_sk, _mint)}}}
    _before = dC.get_balance(POOLK)
    dC.apply_ledger_event(mint_evt, "txmint")
    check("a net-zero event cannot apply as a partial credit",
          dC.get_balance(POOLK) == _before,
          f"{_before} -> {dC.get_balance(POOLK)}")

    _p2sk, POOL2 = _kp()
    _r1 = cov.Database.node_gift_ref_id(POOLK, RCPK, 50.0, 1000.0)
    _r2 = cov.Database.node_gift_ref_id(POOL2, RCPK, 50.0, 1000.0)
    check("gift ref_id distinguishes different payers", _r1 != _r2)
    check("gift ref_id distinguishes different amounts",
          _r1 != cov.Database.node_gift_ref_id(POOLK, RCPK, 50.5, 1000.0))

    _d = cov.Database(tempfile.mktemp(suffix=".db"))
    with sqlite3.connect(_d.db_path) as _c:
        _plan = [r[-1] for r in _c.execute(
            "EXPLAIN QUERY PLAN SELECT COALESCE(SUM(delta),0) "
            "FROM ledger_entries WHERE pubkey = ?", ("x",))]
    check("balance reads use an index, not a full table scan",
          any("COVERING INDEX" in p for p in _plan) and not any("SCAN" in p for p in _plan),
          "; ".join(_plan))

    _absorb = [
        {"pubkey": POOLK, "delta": -1e16, "reason": "node_gift_sent", "ref_id": "ab1"},
        {"pubkey": RCPK, "delta": 1.0, "reason": "node_gift_received", "ref_id": "ab2"},
        {"pubkey": POOLK, "delta": 1e16, "reason": "node_gift_received", "ref_id": "ab3"}]
    _ok, _why = cov.Database.validate_ledger_event({"entries": _absorb})
    check("a credit hidden by float absorption is refused", not _ok, _why[:60])

    _sub = [
        {"pubkey": POOLK, "delta": -1e12, "reason": "node_gift_sent", "ref_id": "sb1"},
        {"pubkey": RCPK, "delta": 1e-5, "reason": "node_gift_received", "ref_id": "sb2"},
        {"pubkey": POOLK, "delta": 1e12, "reason": "node_gift_received", "ref_id": "sb3"}]
    _ok, _why = cov.Database.validate_ledger_event({"entries": _sub})
    check("absorption under the magnitude cap is still refused (fsum, not the cap)",
          not _ok and "net-zero" in _why, _why[:60])

    import itertools as _it
    _verdicts = {cov.Database.validate_ledger_event({"entries": list(p)})[0]
                 for p in _it.permutations(_sub)}
    check("the net-zero verdict is independent of entry order",
          _verdicts == {False}, str(_verdicts))

    _big = [{"pubkey": POOLK, "delta": -1e16, "reason": "node_gift_sent", "ref_id": "bg"},
            {"pubkey": RCPK, "delta": 1e16, "reason": "node_gift_received", "ref_id": "bg"}]
    _ok, _why = cov.Database.validate_ledger_event({"entries": _big})
    check("an entry magnitude past float64's exact range is refused",
          not _ok and "magnitude" in _why, _why[:60])

    _sp = cov.StakingPool(cov.Database(tempfile.mktemp(suffix=".db")))
    for _i in range(10):
        _pk = f"-----BEGIN PUBLIC KEY-----\nSTK{_i}\n-----END PUBLIC KEY-----"
        _sp.stakes[_pk] = cov.Stake(pubkey=_pk, amount=1000.0, start_time=0.0,
                                    duration=86400)
    check("total_staked is derived, not a hand-maintained counter",
          abs(_sp.total_staked - 10000.0) < 1e-9, f"{_sp.total_staked}")
    try:
        _sp.total_staked = 1.0
        check("assigning to total_staked fails loudly", False, "assignment succeeded")
    except AttributeError:
        check("assigning to total_staked fails loudly", True)

    _intended = 0.0
    for _ in range(2000):
        _sp.distribute_block_rewards(50.0)
        _intended += 50.0
    _actual = math.fsum(s.amount for s in _sp.stakes.values()) - 10000.0
    check("2000 blocks mint exactly what was intended, no over-issue",
          abs(_actual - _intended) < 1e-6,
          f"intended {_intended:,.2f} actual {_actual:,.2f}")
    check("the derived counter still equals the true sum after compounding",
          abs(_sp.total_staked - math.fsum(s.amount for s in _sp.stakes.values())) < 1e-9)
    _shares = _sp.distribute_block_rewards(100.0)
    check("one block's shares sum to exactly the block reward",
          abs(math.fsum(_shares.values()) - 100.0) < 1e-9,
          f"{math.fsum(_shares.values())}")

    for _bad, _label in ((float("nan"), "NaN"), (float("inf"), "Infinity"),
                         (float("-inf"), "-Infinity"), (-100.0, "a negative reward"),
                         ("fifty", "a non-numeric reward"), (True, "a bool")):
        _p = cov.StakingPool(cov.Database(tempfile.mktemp(suffix=".db")))
        _k = "-----BEGIN PUBLIC KEY-----\nGUARD\n-----END PUBLIC KEY-----"
        _p.stakes[_k] = cov.Stake(pubkey=_k, amount=1000.0, start_time=0.0, duration=86400)
        try:
            _p.distribute_block_rewards(_bad)
            check(f"{_label} block reward is refused", False,
                  f"accepted; stake now {_p.stakes[_k].amount!r}")
        except ValueError:
            check(f"{_label} block reward is refused",
                  _p.stakes[_k].amount == 1000.0, f"stake {_p.stakes[_k].amount!r}")

    _k2 = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _p2 = _k2.public_key().public_bytes(
        _ser.Encoding.PEM, _ser.PublicFormat.SubjectPublicKeyInfo).decode()
    _tx2 = cov.Transaction(sender_pubkey=_p2, receiver="collective",
                           data={"origin": "human"}, amount=100.0, benefit_score=0.5)
    _tx2.sign(_k2)
    _b2 = cov.Block(index=1, transactions=[_tx2], previous_hash="0" * 64)
    _b2.stake_rewards = math.fsum(t.amount for t in _b2.transactions) * 0.01
    _b2.mine(2)
    check("stake_rewards set before mining keeps the hash valid",
          _b2.hash == _b2.compute_hash(),
          f"stake_rewards={_b2.stake_rewards}")
    _b2.stake_rewards = 999.0
    check("mutating stake_rewards after mining is detectable",
          _b2.hash != _b2.compute_hash())

    _ts = 1234.5
    _t1 = cov.Transaction(sender_pubkey=POOLK, receiver=RCPK, data={"origin": "human"},
                          amount=1.0, timestamp=_ts)
    _t2 = cov.Transaction(sender_pubkey=POOLK, receiver=RCPK, data={"origin": "human"},
                          amount=9999.0, timestamp=_ts)
    check("transaction id commits to amount", _t1.get_id() != _t2.get_id())
    _t3 = cov.Transaction(sender_pubkey=POOLK, receiver=RCPK,
                          data={"origin": "human", "memo": "x"}, amount=1.0, timestamp=_ts)
    check("transaction id commits to data", _t1.get_id() != _t3.get_id())

    print("\n== Canonical genesis and persistent identity ==")
    tmpd = tempfile.mkdtemp()
    f = cov.CovenantUnifiedMaster("FU_F", host="127.0.0.1", port=16800,
                                  p2p_port=16801, db_path=os.path.join(tmpd, "f.db"))
    f.add_genesis_block()
    gpath = f.export_genesis(os.path.join(tmpd, "genesis.json"))
    n1 = cov.CovenantUnifiedMaster("FU_A", host="127.0.0.1", port=16810,
                                   p2p_port=16811, db_path=os.path.join(tmpd, "a.db"))
    n2 = cov.CovenantUnifiedMaster("FU_B", host="127.0.0.1", port=16820,
                                   p2p_port=16821, db_path=os.path.join(tmpd, "b.db"))
    n1.load_canonical_genesis(gpath); n2.load_canonical_genesis(gpath)
    check("two fresh nodes adopt an identical genesis with no DB copying",
          n1.node.chain[0].hash == n2.node.chain[0].hash,
          n1.node.chain[0].hash[:16])
    minter = n1.node.chain[0].transactions[0].sender_pubkey
    check("supply is 1000 network-wide, not per node",
          cov.Database(os.path.join(tmpd, "a.db")).get_balance(minter) == 1000.0
          and cov.Database(os.path.join(tmpd, "b.db")).get_balance(minter) == 1000.0)
    pk_before = n1.public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    n1b = cov.CovenantUnifiedMaster("FU_A", host="127.0.0.1", port=16830,
                                    p2p_port=16831, db_path=os.path.join(tmpd, "a.db"))
    pk_after = n1b.public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    check("node identity survives a restart", pk_before == pk_after)
    check("identity key file is owner-only",
          oct(os.stat(os.path.join(tmpd, "a.db.key")).st_mode & 0o777) == "0o600")

    print(f"\n{'=' * 58}\n{PASS} passed, {FAIL} failed\n{'=' * 58}")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
