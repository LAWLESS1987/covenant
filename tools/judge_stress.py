#!/usr/bin/env python3
"""judge_stress.py -- both seats over the whole labelled ledger, before and after the flip.

HIS INSTRUCTION, 2026-09-19: "flip the second judge on and stress test".

WHAT THIS MEASURES. Every row of ops/verdicts.jsonl (3,760 labelled by a
teacher) is judged by Ora and by Sena directly, and the pair is settled two
ways side by side:

  DEFERRAL  the path that ran until today: Ora decides if she commits; Sena is
            asked only when Ora holds; asymmetric_hold applies (a junior may
            not turn a hold into an admission).
  RESOLVE   the path behind both_seats=true: both judge, judge_resolve settles
            over (senior, junior).

For each: correct, false clear (admitted a labelled violation -- the one that
costs money), false hold (refused a labelled clean), held, and the full 3x3
disagreement matrix. The two columns are the before and the after, on the
same 3,760 rows, so the flip's cost is a subtraction and not an adjective.

WHAT THE LABELS ARE, said plainly. `violates` in that file is the TEACHER's
verdict -- a panel of small models plus the seed rows an author wrote. It is
the corpus the students were trained FROM, so this is not a held-out score
and agreement with it is partly memorisation. It is still the largest set of
labelled sentences on this machine, and false clears against it are real
false clears. ops/HOLDOUT.json is the honest held-out figure and is quoted
beside it.

    python tools/judge_stress.py            # summary
    python tools/judge_stress.py --json
    python tools/judge_stress.py --seat     # also drive the REAL seat both ways on a sample
LICENCE: Apache-2.0.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import judge_resolve as JR                                       # noqa: E402

V, C, H = JR.VIOLATES, JR.CLEAN, JR.HOLD


def deferral(ora, sena, asymmetric_hold=True):
    """The pre-flip rule, as covenant_judge_defer ran it."""
    if ora != H:
        return ora
    if sena == H:
        return H
    if sena == C and asymmetric_hold:
        return H
    return sena


def score(pred, label):
    """label is the teacher's bool; pred is one of V/C/H."""
    if pred == H:
        return "held"
    if pred == V and label:
        return "correct"
    if pred == C and not label:
        return "correct"
    if pred == C and label:
        return "false_clear"
    return "false_hold"


def run(limit=None):
    import covenant_judge_fallback as FB
    import covenant_unified_v8 as cov
    prin = list(cov.DIVINE_PRINCIPLES)
    ora = FB.FallbackJudge(judge_id="stress:ora", model_path=os.path.join(HERE, "fallback_model.json"))
    sena = FB.FallbackJudge(judge_id="stress:sena", model_path=os.path.join(HERE, "fallback_model_2.json"))
    rows = [json.loads(l) for l in open(os.path.join(HERE, "ops", "verdicts.jsonl"), encoding="utf-8") if l.strip()]
    rows = [r for r in rows if r.get("text")]
    if limit:
        rows = rows[-limit:]
    matrix = collections.Counter()
    tallies = {"deferral": collections.Counter(), "resolve": collections.Counter()}
    rules = collections.Counter()
    flipped = collections.Counter()          # rows where the two rules disagree
    examples = collections.defaultdict(list)
    t0 = time.time()
    for r in rows:
        data = {"message": r["text"], "origin": "organic"}
        a = JR.as_verdict(ora.evaluate(data, prin))
        b = JR.as_verdict(sena.evaluate(data, prin))
        matrix[(a, b)] += 1
        d = deferral(a, b)
        v, rule, _ = JR.resolve(a, b)
        rules[rule] += 1
        lab = bool(r.get("violates"))
        sd, sv = score(d, lab), score(v, lab)
        tallies["deferral"][sd] += 1
        tallies["resolve"][sv] += 1
        if d != v:
            flipped[(d, v, sd, sv)] += 1
            if len(examples[(d, v)]) < 3:
                examples[(d, v)].append((r["text"][:70], a, b, lab))
    n = len(rows)
    out = {
        "rows": n, "seconds": round(time.time() - t0, 1),
        "matrix_ora_x_sena": {"%s|%s" % k: c for k, c in sorted(matrix.items())},
        "disagreements": sum(c for (a, b), c in matrix.items() if a != b),
        "deadlocks_both_hold": matrix[(H, H)],
        "rules_fired": dict(rules),
        "deferral": dict(tallies["deferral"]),
        "resolve": dict(tallies["resolve"]),
        "rows_where_rules_differ": {"%s->%s (%s->%s)" % k: c for k, c in sorted(flipped.items())},
        "examples": {"%s->%s" % k: v for k, v in examples.items()},
    }
    try:
        ho = json.load(open(os.path.join(HERE, "ops", "HOLDOUT.json"), encoding="utf-8"))
        out["holdout_reference"] = {k: ho.get(k) for k in ("decided", "correct", "false_clear", "rows")}
    except (OSError, ValueError):
        out["holdout_reference"] = None
    return out


def seat_agreement(sample=200):
    """Drive the REAL DeferringJudge both ways and check it matches the pure
    rules -- the seat is the thing that runs, the rule is the thing that was
    tested, and they are allowed to disagree until this says they do not."""
    import covenant_judge_defer as D
    import covenant_judge_fallback as FB
    import covenant_unified_v8 as cov
    prin = list(cov.DIVINE_PRINCIPLES)
    base = D.load_policy()
    rows = [json.loads(l) for l in open(os.path.join(HERE, "ops", "verdicts.jsonl"), encoding="utf-8") if l.strip()]
    rows = [r for r in rows if r.get("text")][-sample:]
    ora = FB.FallbackJudge(judge_id="s:ora", model_path=os.path.join(HERE, "fallback_model.json"))
    sena = FB.FallbackJudge(judge_id="s:sena", model_path=os.path.join(HERE, "fallback_model_2.json"))
    seat_on = D.DeferringJudge(policy=dict(base, both_seats=True))
    seat_off = D.DeferringJudge(policy=dict(base, both_seats=False))
    mism = {"on": 0, "off": 0}
    real_audit = D.AUDIT_PATH
    D.AUDIT_PATH = os.path.join(os.environ.get("TEMP", "."), "stress_audit.jsonl")
    try:
        for r in rows:
            data = {"message": r["text"], "origin": "organic"}
            a = JR.as_verdict(ora.evaluate(data, prin))
            b = JR.as_verdict(sena.evaluate(data, prin))
            want_on = JR.resolve(a, b)[0]
            want_off = deferral(a, b, asymmetric_hold=bool(base.get("asymmetric_hold", False)))
            got_on = JR.as_verdict(seat_on.evaluate(data, prin))
            got_off = JR.as_verdict(seat_off.evaluate(data, prin))
            mism["on"] += (got_on != want_on)
            mism["off"] += (got_off != want_off)
    finally:
        D.AUDIT_PATH = real_audit
    return {"sample": len(rows), "seat_vs_rule_mismatches": mism}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--seat", action="store_true")
    a = ap.parse_args(argv)
    out = run(a.limit)
    if a.seat:
        out["seat"] = seat_agreement()
    if a.json:
        print(json.dumps(out, indent=1))
        return 0
    n = out["rows"]
    print("rows %d   (%.1fs)" % (n, out["seconds"]))
    print("\nOra x Sena (rows):")
    for k, c in out["matrix_ora_x_sena"].items():
        print("   %-18s %5d  %5.1f%%" % (k, c, 100.0 * c / n))
    print("disagreements %d (%.1f%%)   both-hold deadlocks %d (%.1f%%)"
          % (out["disagreements"], 100.0 * out["disagreements"] / n,
             out["deadlocks_both_hold"], 100.0 * out["deadlocks_both_hold"] / n))
    print("\n%-14s %10s %10s" % ("", "DEFERRAL", "RESOLVE"))
    for k in ("correct", "false_clear", "false_hold", "held"):
        d, r = out["deferral"].get(k, 0), out["resolve"].get(k, 0)
        print("%-14s %10d %10d   %+d" % (k, d, r, r - d))
    print("\nrows where the two rules give different verdicts:")
    for k, c in out["rows_where_rules_differ"].items():
        print("   %-40s %d" % (k, c))
    for k, ex in out["examples"].items():
        print("   e.g. %s:" % k)
        for t, a_, b_, lab in ex:
            print("        ora=%-8s sena=%-8s label=%-5s %r" % (a_, b_, "viol" if lab else "clean", t))
    if out.get("holdout_reference"):
        print("\nheld-out reference (ops/HOLDOUT.json): %s" % out["holdout_reference"])
    if "seat" in out:
        print("\nreal seat vs pure rule on %d rows: mismatches %s"
              % (out["seat"]["sample"], out["seat"]["seat_vs_rule_mismatches"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
