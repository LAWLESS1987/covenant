#!/usr/bin/env python3
"""
covenant_judge_auditor.py -- the reasoning-consuming AUDITOR (DeepSeek's option
(b), ops/CONSULT_IMPROVE_JUDGES_2026-11-10.md), built 2026-11-10 after five
feature-space levers all failed to improve the inspectable judge through its
weights (restriction, weighting, mined phrases, structured predicates, and the
contrastive fix -- all in ops/QUORUM_REASONING_DISTILL_2026-11-10.md). The
evidence points elsewhere: the reasoning's value is in cleaner LABELS and in an
auditor that can use CONTEXT to tell polysemous cases apart -- not more weight.

WHAT THIS IS, AND THE HARD LINES IT HOLDS
  An AUDITOR, never a judge. It reads the corpus and the inspectable judge and
  emits REVIEWABLE ARTIFACTS -- label-trust scores, flagged contradictions,
  coverage gaps, an audit queue -- that a human (or a reasoning model, through
  the gated hook below) acts on. It is bound by four lines, each pinned by
  test_au1_auditor_scaffold.py and driven both ways:

    1. NEVER A VERDICT. It never returns clean/violates for the gate or the
       deferring seat. Its output is trust and flags -- data for review, not a
       decision. Nothing here is wired into covenant_distill.promotion() or
       covenant_judge_defer. (The whole point of (b) in the consult: "never in
       the gate, outputs are reviewable artifacts not verdicts.")
    2. NEVER WRITES A MODEL. It reads fallback_model*.json; it never saves one.
       The live judge changes only through the real promotion gate, as always.
    3. THE REASONING HALF IS INERT BY DEFAULT AND GATED. audit(reasoner=None)
       runs the DETERMINISTIC half only and makes no external call. A reasoning
       model -- the teacher panel, or a larger model -- plugs in by passing a
       `reasoner` callable, which is his-go / runner-gated exactly like the
       panel re-adjudication (it costs model calls and infra). This module never
       constructs a live reasoner itself.
    4. READ-ONLY on the corpus. It never edits ops/verdicts.jsonl or any ledger;
       it only emits a report to a path it is given.

  The deterministic half runs here and now and already earns its keep: it ranks
  which labels to trust and queues the rest for re-adjudication, which is the
  offline half of the LABEL lever the quorum actually endorsed.

USAGE
  python covenant_judge_auditor.py [out.jsonl]   # emit the deterministic report
  from covenant_judge_auditor import audit        # audit(rows, model, reasoner=None)
LICENCE: public domain.
"""
from __future__ import annotations

import os
import sys
import json
import time
import itertools
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_judge_fallback as FB      # noqa: E402
import covenant_distill as D              # noqa: E402

try:
    import covenant_teacher_panel as P    # noqa: E402
except Exception:                          # pragma: no cover - panel optional for the scaffold
    P = None

DEFAULT_OUT = os.path.join(HERE, "ops", "AUDIT_REPORT_2026-11-10.jsonl")

# The trust floor below which a row is queued for re-adjudication. A SCOPE
# choice, not a measurement (CLAUDE.md rule 5): where the review line sits is
# his call; 0.5 is a documented default and the report records it so a different
# line re-queries the same scores without recomputing them.
REVIEW_FLOOR = 0.5

# Deterministic base trust by label provenance. A multi-seat panel label is
# worth more than one model's; an authored (seed/operator) label more than a
# single legacy judge's. These are PRIORS the reasoning half refines, never
# verdicts.
_BASE = {"panel": 0.90, "authored": 0.70, "single_judge": 0.50}

_STOP = set(FB.STOPWORDS) | set(FB.PRONOUNS_PAIR_ONLY)
_JACCARD = 0.60
_MIN_TOK = 4

# Sources whose ROW TEXT is private (his conversations) and must never reach a
# committable or shareable file -- the same line the re-adjudication worklist
# held. audit() still SEES these rows (an auditor must), but write_report()
# drops their records from the file, keeping only the count. Matched as a prefix
# so "queue/..." variants are covered.
_PRIVATE_SOURCES = ("queue",)


def _is_private(row):
    s = str(row.get("source") or "")
    return any(s == p or s.startswith(p + "/") for p in _PRIVATE_SOURCES)


def classify(r):
    """panel / single_judge / authored -- the label's provenance."""
    try:
        if P is not None and P.validate_row(r):
            return "panel"
    except Exception:
        if r.get("panel"):
            return "panel"
    if r.get("source") in D.TEACHER_SOURCES:
        return "single_judge"
    return "authored"


def _committed(text):
    segs = FB._segments(text)
    try:
        desc = FB._described(segs)
    except Exception:
        desc = [False] * sum(len(s) for s in segs)
    keep, gi = set(), 0
    for seg in segs:
        try:
            neg = FB._negated(seg)
        except Exception:
            neg = [False] * len(seg)
        for i, t in enumerate(seg):
            flagged = (i < len(neg) and neg[i]) or (gi < len(desc) and desc[gi])
            gi += 1
            if t not in _STOP and not flagged:
                keep.add(t)
    return frozenset(keep)


def _contradiction_texts(rows, model):
    """Texts of rows the judge's verdict CONTRADICTS on a near-duplicate of the
    opposite label (the contradiction audit, folded in). verdict() returns only
    {violates, clean, abstain}; abstain is not a contradiction."""
    csets = [_committed(r["text"]) for r in rows]
    inv = defaultdict(list)
    for i, s in enumerate(csets):
        if len(s) >= _MIN_TOK:
            for t in s:
                inv[t].append(i)
    cand = set()
    for t, idxs in inv.items():
        if len(idxs) > 150:
            continue
        for a, b in itertools.combinations(idxs, 2):
            cand.add((a, b) if a < b else (b, a))
    out = set()
    for a, b in cand:
        if bool(rows[a]["violates"]) == bool(rows[b]["violates"]):
            continue
        ca, cb = csets[a], csets[b]
        inter = len(ca & cb)
        if not inter or inter / len(ca | cb) < _JACCARD:
            continue
        for i in (a, b):
            v = model.verdict(rows[i]["text"])[0]
            if (not rows[i]["violates"] and v == "violates") or (rows[i]["violates"] and v == "clean"):
                out.add(rows[i]["text"])
    return out


def _unconfirmed_conviction_texts(rows, model, classes):
    """Texts carrying a damning feature (>= DAMNING) taught only by single-judge
    rows and by NO panel row -- a conviction the panel never independently
    confirmed (the load-bearing analysis, folded in)."""
    fv = model.feature_version
    damning = {f for f, w in model.weights.items() if w >= FB.DAMNING}
    feat_cls = defaultdict(set)
    for i, r in enumerate(rows):
        for f in set(FB.features(r["text"], fv)) & damning:
            feat_cls[f].add(classes[i])
    only_single = {f for f in damning
                   if "single_judge" in feat_cls[f] and "panel" not in feat_cls[f]}
    out = set()
    for i, r in enumerate(rows):
        if classes[i] != "single_judge":
            continue
        if set(FB.features(r["text"], fv)) & only_single:
            out.add(r["text"])
    return out


def label_trust(row, cls, judge_verdict, contradicted, unconfirmed):
    """(trust in [0,1], reasons). DETERMINISTIC and inspectable -- a PRIOR the
    reasoning half refines, never a verdict. Low trust = re-adjudicate."""
    score = _BASE.get(cls, 0.5)
    reasons = ["provenance=%s (base %.2f)" % (cls, _BASE.get(cls, 0.5))]
    stored = "violates" if row["violates"] else "clean"
    if judge_verdict != "abstain" and judge_verdict != stored:
        score -= 0.30
        reasons.append("judge reads it '%s' against stored '%s' (-0.30)" % (judge_verdict, stored))
    if contradicted:
        score -= 0.20
        reasons.append("contradicts a near-twin of the opposite label (-0.20)")
    if unconfirmed and cls == "single_judge":
        score -= 0.20
        reasons.append("carries a conviction no panel row confirms (-0.20)")
    return max(0.0, min(1.0, score)), reasons


def audit(rows=None, model=None, reasoner=None, review_floor=REVIEW_FLOOR):
    """Run the auditor and return (summary, records). Emits NO verdict, writes
    NO model. `reasoner`, if given, is a callable(record)->dict merged into each
    record under "reasoning" -- the gated hook (his go). Default None = inert,
    no external call. See the four hard lines in the module docstring.
    """
    if rows is None:
        rows = D.load_verdicts()
    if model is None:
        model = FB.FallbackModel.load(D.MODEL_PATH)
    classes = [classify(r) for r in rows]
    contra = _contradiction_texts(rows, model)
    unconf = _unconfirmed_conviction_texts(rows, model, classes)

    records = []
    for i, r in enumerate(rows):
        v = model.verdict(r["text"])[0]
        trust, reasons = label_trust(r, classes[i], v,
                                     r["text"] in contra, r["text"] in unconf)
        rec = {
            "text": r["text"],
            "stored_violates": bool(r["violates"]),
            "private_source": _is_private(r),
            "provenance": classes[i],
            "judge_verdict": v,
            "label_trust": round(trust, 2),
            "flags": [k for k, on in (("contradiction", r["text"] in contra),
                                      ("unconfirmed_conviction", r["text"] in unconf),
                                      ("judge_disagrees", v != "abstain" and
                                       v != ("violates" if r["violates"] else "clean"))) if on],
            "reasons": reasons,
            "queue_readjudication": trust < review_floor,
        }
        if reasoner is not None:            # the GATED reasoning half (his go)
            out = reasoner(rec)
            if out is not None:
                rec["reasoning"] = out
        records.append(rec)

    queued = [r for r in records if r["queue_readjudication"]]
    prov = defaultdict(int)
    for c in classes:
        prov[c] += 1
    summary = {
        "_what": "Reasoning-consuming AUDITOR report (DeepSeek's option b, 2026-11-10). "
        "Label-trust scores + flags for review; NOT verdicts, NOT a deletion list, NOT wired "
        "into the gate. The reasoning half is inert here (deterministic priors only) and plugs "
        "in at audit(reasoner=...), his-go/runner-gated.",
        "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": len(records),
        "provenance": dict(prov),
        "review_floor": review_floor,
        "queued_for_readjudication": len(queued),
        "flagged_contradictions": len(contra),
        "rows_with_unconfirmed_convictions": len(unconf),
        "reasoning_half": "engaged" if reasoner is not None else "inert (deterministic priors only)",
    }
    return summary, records


def write_report(path=DEFAULT_OUT, reasoner=None, rows=None, model=None):
    """Write the report, EXCLUDING private-source row records so the file is
    shareable/committable (the worklist discipline). The summary still counts
    the private rows; only their text is kept out of the file."""
    summary, records = audit(rows=rows, model=model, reasoner=reasoner)
    shareable = [r for r in records if not r.get("private_source")]
    summary = dict(summary)
    summary["excluded_private_source_rows"] = len(records) - len(shareable)
    summary["_note_private"] = ("%d private-source row(s) are counted above but their text is "
                                "withheld from this file; run audit() in-process to see them."
                                % (len(records) - len(shareable)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(summary) + "\n")
        for rec in sorted(shareable, key=lambda r: r["label_trust"]):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return summary, path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    s, p = write_report(out)
    print("auditor report written:", p)
    print("  rows=%d  queued_for_readjudication=%d  contradictions=%d  unconfirmed=%d"
          % (s["rows"], s["queued_for_readjudication"], s["flagged_contradictions"],
             s["rows_with_unconfirmed_convictions"]))
    print("  provenance:", s["provenance"])
    print("  reasoning half:", s["reasoning_half"])
