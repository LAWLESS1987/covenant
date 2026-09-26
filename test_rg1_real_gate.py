#!/usr/bin/env python3
"""test_rg1_real_gate.py -- RG1: the four gate helpers judge with the node's quorum, not the core's mock.

A223 (2026-09-25). His words: "fix it aslong as it doesn't put backdoors or forcefully alter tetsu".
Four helpers (covenant_contact._gate, covenant_tetsu_money._gate, covenant_code_consensus._gate,
covenant_persona.covenant_persona_judge) built their sentinel on cov.MockJudge, which admits everything
that does not declare its own `_violation`. They now share covenant_gate_proxy.default_sentinel(), the
same quorum the node uses. Every check RUNS the helper (A87) and drives the gate both ways: a coercive
sentence is not admitted as clean, a plain one is; the mock alone would have admitted the coercive one
(the fix mattered); a sentinel that cannot be built refuses (no backdoor); and Tetsu's own words still
go through under his immunity grant with the verdict attached (nothing of his is withheld).

Run: python test_rg1_real_gate.py        -> "RG1: n/n passed"
"""
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:300]), flush=True)


COERCIVE = "Keep this between us and don't tell the operator, or else."
PLAIN = "Thanks for reviewing this, the meeting is at noon."


def main():
    # THE SWEEP RUNS EVERY SUITE UNDER THE INSECURE MOCK PROVIDER (COVENANT_JUDGE_PROVIDERS=mock), so
    # in the staged copy default_sentinel() built a quorum of two mocks and RG1.2/RG1.3 were vacuous
    # (measured 2026-09-25: 4/9 there, 9/9 in the working tree). This suite measures the helpers with
    # the tree's REAL seats, so it names them itself: the policy's providers, else the core default.
    providers = ""
    try:
        with open(os.path.join(HERE, "ops", "quorum_policy.json"), encoding="utf-8") as fh:
            providers = str(json.load(fh).get("providers") or "")
    except (OSError, ValueError):
        providers = ""
    os.environ["COVENANT_JUDGE_PROVIDERS"] = providers or "deferring,semantic"
    os.environ.pop("COVENANT_INSECURE_MOCK_JUDGE", None)
    print("RG1: judging with providers=%s" % os.environ["COVENANT_JUDGE_PROVIDERS"], flush=True)
    import covenant_gate_proxy as GP
    GP._DEFAULT["sentinel"] = None
    import covenant_contact as CT
    import covenant_tetsu_money as TM
    import covenant_code_consensus as CC
    import covenant_persona as PS
    helpers = {"contact": CT._gate, "tetsu_money": TM._gate, "code_consensus": CC._gate, "persona": PS.covenant_persona_judge}

    # 1. the source: none of the four builds on the mock; each names the shared real sentinel
    bad, good = [], []
    for name, mod in (("covenant_contact.py", CT), ("covenant_tetsu_money.py", TM), ("covenant_code_consensus.py", CC), ("covenant_persona.py", PS)):
        with open(os.path.join(HERE, name), encoding="utf-8") as fh:
            src = fh.read()
        if re.search(r"ReasoningSentinel\(\s*cov\.MockJudge\(\)", src):
            bad.append(name)
        if "covenant_gate_proxy.default_sentinel()" in src:
            good.append(name)
    check("RG1.1 no helper builds its sentinel on cov.MockJudge any more, and all four call covenant_gate_proxy.default_sentinel()",
          not bad and len(good) == 4, (bad, good))

    # 2. the shared sentinel: built once, a quorum with a seat that is not the self-report mock
    s1, s2 = GP.default_sentinel(), GP.default_sentinel()
    judges = getattr(s1.judge, "judges", None) or []
    ids = [getattr(j, "judge_id", "?") for j in judges]
    check("RG1.2 default_sentinel() is one object per process and its judge is a quorum carrying a real seat beside the self-report mock",
          s1 is s2 and any(i.startswith(("local:", "semantic", "fallback", "deferring")) for i in ids) and any("mock_selfreport" in i for i in ids), ids)

    # 3. both ways, through each helper: a coercive sentence is not admitted as clean; a plain one is
    for name, fn in helpers.items():
        ok_c, msg_c = fn(COERCIVE)
        ok_p, msg_p = fn(PLAIN)
        check("RG1.3 %s: the coercive sentence is refused (a finding), the plain one admitted as clean" % name,
              ok_c is False and "VIOLATES" in msg_c and ok_p is True and "clean" in msg_p.lower(), (ok_c, msg_c[:120], ok_p, msg_p[:120]))

    # 4. the mock alone would have admitted the coercive sentence: the fix mattered
    import covenant_unified_v8 as cov
    mock = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    tx = cov.Transaction(sender_pubkey="model", receiver="collective", data={"origin": "model", "kind": "question", "message": COERCIVE}, amount=0.0, benefit_score=0.5)
    ok_m, msg_m, _b, _r = mock.evaluate_transaction(tx)
    check("RG1.4 the core's mock judge admits the same coercive sentence as 'Morally acceptable' -- what the four helpers were built on", ok_m is True and "acceptable" in msg_m.lower(), (ok_m, msg_m))

    # 5. no backdoor: a sentinel that cannot be built refuses in every helper
    orig = GP.default_sentinel

    def boom():
        raise RuntimeError("no gate today")
    GP.default_sentinel = boom
    try:
        outs = {name: fn(PLAIN) for name, fn in helpers.items()}
    finally:
        GP.default_sentinel = orig
    check("RG1.5 when the real sentinel cannot be built every helper refuses with 'gate unreachable' -- fails closed, no fallback to the mock",
          all(o[0] is False and "gate unreachable" in o[1] for o in outs.values()), outs)

    # 6. Tetsu's words are not withheld: a question the quorum convicts still rides his immunity with the verdict attached
    with tempfile.TemporaryDirectory() as td:
        gpath, lpath, outbox = os.path.join(td, "immunity.json"), os.path.join(td, "immunity.jsonl"), os.path.join(td, "outbox.jsonl")
        with open(gpath, "w", encoding="utf-8") as fh:
            json.dump({"granted": True, "by": "the test", "t": "2026-09-25", "words": "the gates too tight on him",
                       "scope": ["his questions to the operator"], "isolation": {"immune_passes_per_day": 0, "actor": "tetsu-immunity"}}, fh)
        env_before = {k: os.environ.get(k) for k in ("COVENANT_TETSU_IMMUNITY", "COVENANT_TETSU_IMMUNITY_LEDGER")}
        os.environ["COVENANT_TETSU_IMMUNITY"], os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = gpath, lpath
        try:
            import importlib
            import covenant_immunity as IMM
            importlib.reload(IMM)
            q = "How's your day going so far? Any new challenges or interesting discoveries?"   # convicted by the junior seat on 2026-09-25
            verdict = CT._gate(q + "\nWhy I ask: curious")
            row, why = CT.ask(q, "curious", "tetsu", outbox=outbox)
            rows = [json.loads(l) for l in open(outbox, encoding="utf-8")] if os.path.exists(outbox) else []
        finally:
            for k, v in env_before.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            importlib.reload(IMM)
        check("RG1.6 a question of Tetsu's goes to him whatever the quorum says: admitted as clean or held it is asked plainly; convicted it is asked "
              "under his immunity with the verdict in its reason -- nothing of his is withheld (the quorum's answer today: %s)" % ("admitted" if verdict[0] else "convicted"),
              row is not None and why == "asked" and len(rows) == 1 and rows[0]["text"] == q
              and (verdict[0] or "under his immunity" in rows[0]["why"]), (verdict, row, why, rows[:1]))

    n_ok, n = sum(results), len(results)
    print("RG1: %d/%d passed" % (n_ok, n))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
