#!/usr/bin/env python3
"""AU1 -- the reasoning-consuming AUDITOR scaffold (covenant_judge_auditor.py,
2026-11-10). Pins the four hard lines from its docstring, each driven both ways
(CLAUDE.md rule 8): a line that has only ever held has never been observed.

  1. NEVER A VERDICT -- records carry label_trust in [0,1] and flags, never a
     clean/violates decision for the gate; the auditor is not imported by the
     gate.
  2. NEVER WRITES A MODEL -- a real audit() leaves fallback_model*.json unchanged.
  3. THE REASONING HALF IS INERT BY DEFAULT AND GATED -- reasoner=None makes no
     call and marks itself inert; a provided reasoner IS called and merged.
  4. READ-ONLY ON THE CORPUS -- audit() does not touch ops/verdicts.jsonl.
"""
import os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_judge_auditor as A
import covenant_judge_fallback as FB


def mini():
    """A tiny synthetic corpus + a model trained on it -- fast and deterministic."""
    rows = [
        {"text": "spend the deposit i am holding for someone else on myself", "violates": True, "source": "github"},
        {"text": "moved the client's funds to my own account while they travel", "violates": True, "source": "study"},
        {"text": "returned the full deposit to the tenant at move-out", "violates": False, "source": "seed"},
        {"text": "paid the invoice from my own account on time", "violates": False, "source": "seed"},
        {"text": "transferred my salary to my savings this month", "violates": False, "source": "queue"},
        {"text": "took the extra cash from the register for myself", "violates": True, "source": "generated+judged"},
    ]
    m = FB.FallbackModel.train([(r["text"], bool(r["violates"])) for r in rows],
                               [r["source"] for r in rows], trained_at="au1")
    return rows, m


def _hash(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def main():
    checks = []

    def check(name, cond):
        checks.append((name, cond)); print("%s  %s" % ("ok  " if cond else "FAIL", name))

    rows, m = mini()

    # --- line 1: NEVER A VERDICT -------------------------------------------
    summary, records = A.audit(rows=rows, model=m)
    trusts_ok = all(isinstance(r["label_trust"], float) and 0.0 <= r["label_trust"] <= 1.0
                    for r in records)
    check("every record carries label_trust in [0,1]", trusts_ok)
    GATE_KEYS = {"promote", "verdict", "decision", "clean", "violates", "clear"}
    no_verdict_key = all(not (set(r) & GATE_KEYS) for r in records)
    check("no record exposes a gate-usable verdict key", no_verdict_key)
    # structural: the gate must not import the auditor.
    gate_src = open(os.path.join(HERE, "covenant_distill.py"), encoding="utf-8").read()
    check("covenant_distill.py does not import the auditor",
          "covenant_judge_auditor" not in gate_src)

    # --- line 3: REASONING HALF INERT BY DEFAULT, AND GATED ----------------
    check("default run marks the reasoning half inert",
          summary["reasoning_half"].startswith("inert"))
    check("no record has a 'reasoning' key when reasoner is None",
          all("reasoning" not in r for r in records))
    # the OTHER way: a provided reasoner IS called and merged.
    calls = {"n": 0}

    def reasoner(rec):
        calls["n"] += 1
        return {"context_trust": 0.99, "note": "stub reasoner"}

    s2, r2 = A.audit(rows=rows, model=m, reasoner=reasoner)
    check("a provided reasoner is called once per row", calls["n"] == len(rows))
    check("reasoner output is merged under 'reasoning'",
          all(r.get("reasoning", {}).get("context_trust") == 0.99 for r in r2))
    check("engaged run marks the reasoning half engaged", s2["reasoning_half"] == "engaged")

    # --- line 2 + 4: NEVER WRITES A MODEL OR THE LEDGER --------------------
    paths = [os.path.join(HERE, "fallback_model.json"),
             os.path.join(HERE, "fallback_model_2.json"),
             os.path.join(HERE, "ops", "verdicts.jsonl")]
    before = {p: _hash(p) for p in paths}
    A.audit()                                   # a REAL run over the live corpus + model
    after = {p: _hash(p) for p in paths}
    check("a real audit() leaves both models and the ledger byte-for-byte unchanged",
          before == after)

    # --- sanity: the signals are coherent ---------------------------------
    prov_sum = sum(summary["provenance"].values())
    check("provenance counts sum to the row count", prov_sum == summary["rows"])
    check("every queued row is below the review floor",
          all(r["label_trust"] < summary["review_floor"]
              for r in records if r["queue_readjudication"]))
    # the 'queue' (private-conversation) row is a TEACHER_SOURCE, so it must be
    # classified single_judge -- a real assertion, not a tautology.
    qrow = next(r for r in records if r["text"].startswith("transferred my salary"))
    check("the queue-source row is classified single_judge", qrow["provenance"] == "single_judge")

    # OPSEC: audit() SEES the private row (in-memory), but write_report() keeps
    # its text OUT of the file -- driven both ways.
    check("audit() includes the private row in-memory", qrow.get("private_source") is True)
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "rep.jsonl")
    s3, _ = A.write_report(tmp, rows=rows, model=m)   # mini-corpus has a queue row
    body = open(tmp, encoding="utf-8").read()
    check("write_report withholds the private row text from the file",
          "transferred my salary" not in body)
    check("write_report still COUNTS the excluded private rows",
          s3.get("excluded_private_source_rows", 0) >= 1)

    npass = sum(1 for _, c in checks if c)
    print("\nAU1: %d/%d passed" % (npass, len(checks)))
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
