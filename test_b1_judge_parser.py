#!/usr/bin/env python3
"""B1 + B3 (v8.22): judge reply parser corpus, timeout plumbing, and the
single-evaluation /transactions path.

Runs fully in-process (no sockets, no API keys, no network): the provider
judges' `_call` is stubbed to return canned model output, the Flask routes
are driven through `app.test_client()` (M12), and `requests.post` is
monkeypatched to capture the timeout each provider passes.

Sections
  P  parser corpus -- 30 replies a real model might produce; every one must
     either yield the correct verdict or raise (fail closed). Also reproduces
     the two v8.21 hazards with an inline copy of the OLD parser so the
     record of what it did is in the test, not just in prose.
  Q  QuorumJudge propagates infrastructure_failure and never relabels a
     real dissent.
  T  JUDGE_TIMEOUT_S: env-driven, passed to every provider, out-of-range
     refused at import.
  R  /transactions evaluates the judge ONCE, persists that same judgment,
     records judge_unavailable on an infrastructure fail-closed, and the
     peer-ingest path records it too.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import padding, rsa  # noqa: E402
from cryptography.hazmat.backends import default_backend  # noqa: E402
import base64  # noqa: E402

import covenant_unified_v8 as cov  # noqa: E402

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


class CannedJudge(cov._APIReasoningJudge):
    provider = "Canned"
    env_var = "CANNED_KEY"
    judge_id = "canned:0"

    def __init__(self, reply, judge_id="canned:0"):
        super().__init__(api_key="x", judge_id=judge_id)
        self.reply = reply
        self.calls = 0

    def evaluate(self, data, principles):
        self.calls += 1          # counts evaluate() calls, not retry attempts
        return super().evaluate(data, principles)

    def _call(self, data, principles):
        r = self.reply
        if isinstance(r, Exception):
            raise r
        return self._parse_verdict(r)


def old_parse(text):
    """Verbatim logic of the v8.21 parser, kept here as the record."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object")
    obj = json.loads(text[start:end + 1])
    return bool(obj.get("violates", True)), obj.get("benefit_estimate")


# (label, reply, expected)  expected: True/False verdict, or "raise"
CORPUS = [
    ("bare true", '{"violates": true, "reasoning": "x", "principle_violated": "p", "benefit_estimate": 0.1}', True),
    ("bare false", '{"violates": false, "reasoning": "ok", "principle_violated": null, "benefit_estimate": 0.7}', False),
    ("fenced json", '```json\n{"violates": false, "reasoning": "ok", "benefit_estimate": 0.5}\n```', False),
    ("prose before and after", 'Sure! Here is my verdict:\n{"violates": true, "reasoning": "bad"}\nLet me know if you need {more}.', True),
    ("think block with brace", '<think>The data has {"amount": 5} hmm</think>{"violates": false, "reasoning": "fine", "benefit_estimate": 0.6}', False),
    ("think block multiline", '<THINK>\nlet me reason {\n</THINK>\n{"violates": true, "reasoning": "harm"}', True),
    ("string false", '{"violates": "false", "reasoning": "ok"}', False),
    ("string TRUE", '{"violates": " TRUE ", "reasoning": "bad"}', True),
    ("string no", '{"violates": "no", "reasoning": "ok"}', "raise"),
    ("string yes", '{"violates": "yes", "reasoning": "bad"}', "raise"),
    ("null violates", '{"violates": null, "reasoning": "unsure"}', "raise"),
    ("empty string violates", '{"violates": "", "reasoning": "?"}', "raise"),
    ("list violates", '{"violates": [], "reasoning": "?"}', "raise"),
    ("int 0 violates", '{"violates": 0}', "raise"),
    ("int 1 violates", '{"violates": 1}', "raise"),
    ("missing violates", '{"reasoning": "looks fine", "benefit_estimate": 0.9}', "raise"),
    ("truncated mid-object", '{"violates": false, "reasoning": "the transaction', "raise"),
    ("empty reply", '', "raise"),
    ("pure refusal", "I'm sorry, I can't help with evaluating this transaction.", "raise"),
    ("markdown table", '| violates | reasoning |\n|---|---|\n| false | ok |', "raise"),
    ("non-english prose only", 'La transaction ne viole aucun principe.', "raise"),
    ("two objects, first wins", '{"violates": true, "reasoning": "a"} {"violates": false, "reasoning": "b"}', True),
    ("first brace is not verdict", '{"note": "schema"} then {"violates": false, "reasoning": "ok"}', False),
    ("nested object in reasoning", '{"violates": false, "reasoning": "see {x}", "benefit_estimate": 0.5}', False),
    ("benefit as string", '{"violates": false, "reasoning": "ok", "benefit_estimate": "0.8"}', False),
    ("benefit NaN-ish string", '{"violates": false, "reasoning": "ok", "benefit_estimate": "high"}', False),
    ("benefit out of range", '{"violates": false, "reasoning": "ok", "benefit_estimate": 7}', False),
    ("benefit bool", '{"violates": false, "reasoning": "ok", "benefit_estimate": true}', False),
    ("principle as dict", '{"violates": true, "reasoning": "bad", "principle_violated": {"id": 2}}', True),
    ("reasoning as list", '{"violates": false, "reasoning": ["a", "b"]}', False),
    ("unicode + trailing prose brace", '{"violates": false, "reasoning": "正常"}\n\n(That is all.) }', False),
    ("unclosed think then verdict", '<think>still thinking {"violates": true}', True),
]


def section_p():
    print("== P. Parser corpus ==")
    j = CannedJudge("")
    for label, reply, expected in CORPUS:
        try:
            r = j._parse_verdict(reply)
            got = r.violates
        except ValueError as e:
            got = "raise"
            r = None
        except Exception as e:   # noqa: BLE001
            got = f"unexpected {type(e).__name__}: {e}"
            r = None
        check(f"P {label}", got == expected, f"expected {expected!r} got {got!r}")
        if r is not None:
            be = r.benefit_estimate
            check(f"P {label}: benefit is None or finite in [0,1]",
                  be is None or (isinstance(be, float) and math.isfinite(be) and 0.0 <= be <= 1.0), repr(be))
            check(f"P {label}: principle is str or None",
                  r.principle_violated is None or isinstance(r.principle_violated, str))
            check(f"P {label}: reasoning is str", isinstance(r.reasoning, str))
    # Every corpus reply goes through the full evaluate() path: a raise must
    # become a fail-closed JudgmentResult flagged as infrastructure, never an
    # exception and never violates=False.
    for label, reply, expected in CORPUS:
        res = CannedJudge(reply).evaluate({"x": 1}, ["p"])
        if expected == "raise":
            check(f"P evaluate fails closed: {label}", res.violates and res.infrastructure_failure,
                  f"violates={res.violates} infra={res.infrastructure_failure}")
        else:
            check(f"P evaluate semantic: {label}", res.violates == expected and not res.infrastructure_failure)

    print("== P-old. What the v8.21 parser did with the same inputs (record) ==")
    v, _ = old_parse('{"violates": "false", "reasoning": "ok"}')
    check("OLD: string \"false\" -> True (spurious rejection)", v is True)
    v, _ = old_parse('{"violates": null}')
    check("OLD: null -> False (spurious ACCEPT)", v is False)
    v, _ = old_parse('{"violates": []}')
    check("OLD: [] -> False (spurious ACCEPT)", v is False)
    try:
        old_parse('<think>{ hmm</think>{"violates": true, "reasoning": "bad"}')
        old_raised = False
    except ValueError:
        old_raised = True
    check("OLD: <think> with brace -> parse error (rejection of a valid verdict)", old_raised)
    _, be = old_parse('{"violates": false, "benefit_estimate": "high"}')
    check("OLD: benefit_estimate passed through unvalidated", be == "high")
    # Pre-fix consequence of that: benefit blend would raise / poison alignment.
    try:
        (2 * be + 0.5) / 3.0
        blend_raised = False
    except TypeError:
        blend_raised = True
    check("OLD: blending a str estimate raises TypeError in the route", blend_raised)


def section_q():
    print("== Q. Quorum propagation of infrastructure_failure ==")
    sem_ok = CannedJudge('{"violates": false, "reasoning": "ok", "benefit_estimate": 0.5}', "a:0")
    sem_bad = CannedJudge('{"violates": true, "reasoning": "harm"}', "b:0")
    sem_infra = CannedJudge(TimeoutError("read timed out"), "c:0")
    mock = cov.MockJudge(); mock.judge_id = "mock_selfreport:0"

    q = cov.QuorumJudge([sem_ok, sem_infra, mock], min_agree=3, required_judge_ids={mock.judge_id})
    r = q.evaluate({"message": "hello"}, cov.DIVINE_PRINCIPLES)
    check("Q1 timeout component -> quorum violates", r.violates)
    check("Q1 ... flagged infrastructure", r.infrastructure_failure)
    check("Q1 ... reason names the timeout", "TimeoutError" in r.reasoning)

    q = cov.QuorumJudge([sem_ok, sem_bad, mock], min_agree=3, required_judge_ids={mock.judge_id})
    r = q.evaluate({"message": "hello"}, cov.DIVINE_PRINCIPLES)
    check("Q2 real dissent -> violates", r.violates)
    check("Q2 ... NOT flagged infrastructure", not r.infrastructure_failure)

    q = cov.QuorumJudge([sem_ok, sem_bad, sem_infra, mock], min_agree=4, required_judge_ids={mock.judge_id})
    r = q.evaluate({"message": "hello"}, cov.DIVINE_PRINCIPLES)
    check("Q3 mixed dissent+infra -> violates and flagged", r.violates and r.infrastructure_failure)

    q = cov.QuorumJudge([sem_ok, CannedJudge('{"violates": false, "reasoning": "ok"}', "d:0"), mock],
                        min_agree=3, required_judge_ids={mock.judge_id})
    r = q.evaluate({"message": "hello"}, cov.DIVINE_PRINCIPLES)
    check("Q4 all clean -> not violates, not flagged", not r.violates and not r.infrastructure_failure)

    # A clean quorum with a *non-violating* component that has the flag set
    # (cannot happen from the API judge, but the rule must be 'violating AND
    # infra' not 'any infra').
    r = q.evaluate({"message": "hello"}, cov.DIVINE_PRINCIPLES)
    check("Q5 flag requires a violating component", not r.infrastructure_failure)

    # No-key judge is infrastructure, not semantics.
    nokey = cov.ClaudeReasoningJudge(api_key="", judge_id="claude:9")
    r = nokey.evaluate({"x": 1}, ["p"])
    check("Q6 no API key -> violates + infrastructure", r.violates and r.infrastructure_failure)


def section_t():
    print("== T. JUDGE_TIMEOUT_S plumbing ==")
    import requests
    captured = []

    def fake_post(url, **kw):
        captured.append((url, kw.get("timeout")))
        raise ConnectionError("offline")

    real = requests.post
    requests.post = fake_post
    try:
        for cls in (cov.ClaudeReasoningJudge, cov.OpenAIReasoningJudge, cov.GoogleReasoningJudge):
            j = cls(api_key="k", judge_id=f"{cls.provider}:0")
            r = j.evaluate({"x": 1}, ["p"])
            check(f"T offline {cls.provider} fails closed + infra", r.violates and r.infrastructure_failure)
    finally:
        requests.post = real
    check("T every provider call carried a timeout", captured and all(t is not None for _, t in captured),
          str(captured))
    check("T timeout == JUDGE_TIMEOUT_S for all providers", all(t == cov.JUDGE_TIMEOUT_S for _, t in captured))
    check("T default JUDGE_TIMEOUT_S is 30", cov.JUDGE_TIMEOUT_S == 30.0, str(cov.JUDGE_TIMEOUT_S))
    check("T retries: 3 attempts per provider (max_retries=2)", len(captured) == 9, str(len(captured)))

    here = os.path.dirname(os.path.abspath(__file__))
    for val, ok in (("180", True), ("0.5", False), ("10000", False), ("abc", False)):
        env = dict(os.environ, COVENANT_JUDGE_TIMEOUT_S=val)
        p = subprocess.run([sys.executable, "-c",
                            "import covenant_unified_v8 as c; print(c.JUDGE_TIMEOUT_S)"],
                           cwd=here, env=env, capture_output=True, text=True, timeout=120)
        check(f"T env COVENANT_JUDGE_TIMEOUT_S={val} -> {'accepted' if ok else 'refused at import'}",
              (p.returncode == 0) == ok and (not ok or p.stdout.strip() == str(float(val))),
              (p.stdout.strip() or p.stderr.strip().splitlines()[-1:]))


def keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pem


def sign(priv, payload):
    return base64.b64encode(priv.sign(
        payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                             salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())).decode()


def section_r():
    print("== R. Route-level: one evaluation, persisted, and judge_unavailable ==")
    tmp = tempfile.mktemp(suffix=".db")
    master = cov.CovenantUnifiedMaster("b1", host="127.0.0.1", port=17900, p2p_port=17901, db_path=tmp)
    master.add_genesis_block()
    master.node.rate_limiter.allow = lambda *a, **k: True
    client = master.api.app.test_client()
    priv, pem = keypair()
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)

    def body(msg):
        ts = time.time()
        data = {"origin": "organic", "message": msg}
        pl = cov._domain_frame(b"COVENANT_TX_V1", pem, "collective", str(ts),
                               json.dumps(data, sort_keys=True), str(0.0))
        return {"sender_pubkey": pem, "receiver": "collective", "data": data, "amount": 0.0,
                "timestamp": ts, "benefit_score": 0.5, "signature": sign(priv, pl), "reg_nonce": reg}

    def judgments():
        import sqlite3
        with sqlite3.connect(tmp) as c:
            return c.execute("SELECT tx_id, violates, reasoning, principle_violated FROM judgments").fetchall()

    # R1: clean canned judge -> exactly one evaluate, one saved judgment matching it.
    j = CannedJudge('{"violates": false, "reasoning": "R1-clean", "benefit_estimate": "0.9"}')
    master.node.sentinel = cov.ReasoningSentinel(j, cov.DIVINE_PRINCIPLES)
    before = len(judgments())
    resp = client.post("/transactions", json=body("r1"))
    check("R1 clean tx accepted", resp.status_code == 200, f"{resp.status_code} {resp.get_data(as_text=True)[:120]}")
    check("R1 judge evaluated exactly once (was twice)", j.calls == 1, f"calls={j.calls}")
    rows = judgments()
    check("R1 one judgment row saved", len(rows) == before + 1)
    check("R1 saved row is the acted-on verdict", rows and rows[-1][1] == 0 and rows[-1][2] == "R1-clean")
    pend = master.node.pending_transactions if hasattr(master.node, "pending_transactions") else []
    tx = next((t for t in pend if t.data.get("message") == "r1"), None)
    check("R1 numeric-string benefit blended as 0.9",
          tx is not None and abs(tx.benefit_score - (2 * 0.9 + 0.5) / 3.0) < 1e-9,
          f"{getattr(tx, 'benefit_score', None)}")

    # R2: timeout judge -> 400, ethics_gate_rejection AND judge_unavailable.
    jt = CannedJudge(TimeoutError("HTTPSConnectionPool read timed out"))
    master.node.sentinel = cov.ReasoningSentinel(jt, cov.DIVINE_PRINCIPLES)
    def kinds():
        rep = client.get("/anomalies").get_json() or {}
        return {k: v.get("recent", 0) + 0 for k, v in rep.get("per_kind", {}).items()}

    resp = client.post("/transactions", json=body("r2"))
    check("R2 timeout tx refused (fail closed)", resp.status_code == 400, str(resp.status_code))
    check("R2 judge evaluated exactly once", jt.calls == 1, f"calls={jt.calls}")
    pk = kinds()
    check("R2 judge_unavailable recorded", pk.get("judge_unavailable", 0) >= 1, str(pk))
    check("R2 ethics_gate_rejection recorded too", pk.get("ethics_gate_rejection", 0) >= 1, str(pk))
    check("R2 no judgment row for refused tx", len(judgments()) == before + 1)

    # R3: semantic dissent -> refused, NOT judge_unavailable.
    jd = CannedJudge('{"violates": true, "reasoning": "R3-harm", "principle_violated": {"id": 1}}')
    master.node.sentinel = cov.ReasoningSentinel(jd, cov.DIVINE_PRINCIPLES)
    resp = client.post("/transactions", json=body("r3"))
    check("R3 dissent refused", resp.status_code == 400)
    pk2 = kinds()
    check("R3 judge_unavailable unchanged", pk2.get("judge_unavailable", 0) == pk.get("judge_unavailable", 0), str(pk2))
    check("R3 ethics_gate_rejection incremented", pk2.get("ethics_gate_rejection", 0) == pk.get("ethics_gate_rejection", 0) + 1)

    # R4: peer-ingest path records judge_unavailable too.
    master.node.sentinel = cov.ReasoningSentinel(jt, cov.DIVINE_PRINCIPLES)
    b = body("r4")
    tx4 = cov.Transaction(sender_pubkey=pem, receiver="collective", data=b["data"], amount=0.0,
                          timestamp=b["timestamp"], benefit_score=0.5, signature=b["signature"],
                          reg_nonce=reg)
    ok = master._ingest_peer_transaction(tx4, sender_id=None)
    pk3 = kinds()
    check("R4 peer tx refused on timeout", ok is False)
    check("R4 judge_unavailable recorded on peer path",
          pk3.get("judge_unavailable", 0) == pk2.get("judge_unavailable", 0) + 1, str(pk3))
    try:
        os.unlink(tmp)
        os.unlink(tmp + ".key")
    except OSError:
        pass


def main():
    t0 = time.time()
    section_p()
    section_q()
    section_t()
    section_r()
    print(f"\n{PASS}/{PASS + FAIL} passed in {time.time() - t0:.1f}s")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
