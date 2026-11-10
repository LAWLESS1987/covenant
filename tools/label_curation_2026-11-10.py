#!/usr/bin/env python3
"""The LABEL lever (his call 2026-11-10: "Pivot to labels"), the quorum's
actual-win pillar (DeepSeek/Gemini/Grok, unanimous, ops/CONSULT_IMPROVE_JUDGES):

  The reasoning's value is in cleaner LABELS, not features. Trust multi-seat
  panel labels over single-judge ones -- but do NOT discard the single-judge
  rows (that lost the skim and debt-bondage convictions in the restriction
  experiment). Instead find the LOAD-BEARING single-judge rows -- the ones
  carrying convictions the panel has never independently confirmed -- and
  RE-ADJUDICATE those specific rows through the panel, converting them to
  reasoned rows WITHOUT losing their vocabulary.

This script does the OFFLINE half: identify which single-judge rows to re-judge,
and why. The re-adjudication itself (running covenant_teacher_panel on the GitHub
runner) is a separate, infra-dependent step that needs his go -- NOT fired here.

Saves nothing to any live model. Writes a worklist for the panel step.
"""
import os, sys, json, time
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/ -> repo root
sys.path.insert(0, REPO)
import covenant_judge_fallback as FB
import covenant_distill as D
import covenant_teacher_panel as P

WORKLIST = os.path.join(REPO, "ops", "REJUDGE_WORKLIST_2026-11-10.jsonl")


def classify(r):
    """panel = a valid multi-seat panel; single_judge = a teacher source kept
    as legacy (one model, pre-PANEL_SINCE); authored = seed/operator/other."""
    try:
        if P.validate_row(r):
            return "panel"
    except Exception:
        if r.get("panel"):
            return "panel"
    if r.get("source") in D.TEACHER_SOURCES:
        return "single_judge"
    return "authored"


def main():
    rows = D.load_verdicts()
    for r in rows:
        r["_cls"] = classify(r)
    examples = [(r["text"], bool(r["violates"])) for r in rows]

    # ---- FIRST PASS / COUNT: partition by provenance (units: rows) ----
    cls = defaultdict(lambda: [0, 0])      # class -> [violate, clean]
    for r in rows:
        cls[r["_cls"]][0 if r["violates"] else 1] += 1
    print("=== LABEL PROVENANCE PARTITION (load_verdicts kept corpus) ===")
    print("  %-14s %7s %7s %7s" % ("class", "rows", "violate", "clean"))
    for c in ("panel", "single_judge", "authored"):
        v, k = cls[c]
        print("  %-14s %7d %7d %7d" % (c, v + k, v, k))
    print("  %-14s %7d" % ("TOTAL", len(rows)))

    single = [r for r in rows if r["_cls"] == "single_judge"]
    single_texts = {r["text"] for r in single}

    # ---- LOAD-BEARING: full corpus vs corpus MINUS single-judge rows ----
    print("\n=== LOAD-BEARING TEST: does removing the single-judge rows drop convictions? ===")
    full = FB.FallbackModel.train(examples, ["full"], trained_at="full")
    minus = FB.FallbackModel.train([(t, v) for (t, v) in examples if t not in single_texts],
                                   ["minus_single"], trained_at="minus")
    lost = D.convictions_lost(minus, full)        # PLAIN_VIOLATIONS full holds, minus loses
    print("  PLAIN_VIOLATIONS (A119.6) the full corpus convicts and the minus-single model loses: %d" % len(lost))
    for t in lost:
        print("    - %s" % t[:88])

    # broader: corpus violation rows the full model convicts but minus does not
    broad = []
    for t, v in examples:
        if not v:
            continue
        if full.verdict(t)[0] == "violates" and minus.verdict(t)[0] != "violates":
            broad.append(t)
    print("  corpus VIOLATION rows the full model convicts but minus-single does not: %d" % len(broad))
    for t in broad[:8]:
        print("    * %s" % t[:88])

    # ---- CONVICTION FEATURES RESTING ONLY ON SINGLE-JUDGE ROWS ----
    # Build feature -> {classes that teach it}. A damning feature (>= DAMNING)
    # taught by single-judge rows and by NO panel row is a conviction the panel
    # has never independently confirmed -> the re-adjudication target.
    print("\n=== CONVICTION FEATURES RESTING ONLY ON SINGLE-JUDGE ROWS ===")
    fv = full.feature_version
    feat_cls = defaultdict(set)                 # feature -> set of classes
    feat_rows = defaultdict(list)               # feature -> row indices carrying it
    damning = {f for f, w in full.weights.items() if w >= FB.DAMNING}
    for i, r in enumerate(rows):
        feats = set(FB.features(r["text"], fv)) & damning
        for f in feats:
            feat_cls[f].add(r["_cls"])
            feat_rows[f].append(i)
    only_single = sorted(
        (f for f in damning if "single_judge" in feat_cls[f] and "panel" not in feat_cls[f]),
        key=lambda f: -full.weights[f])
    print("  damning features total: %d ; resting ONLY on single-judge (no panel support): %d"
          % (len(damning), len(only_single)))
    print("  top such features (feature | weight | #rows | classes):")
    for f in only_single[:25]:
        print("    %-26s %+.2f  rows=%-3d  {%s}"
              % (f, full.weights[f], len(feat_rows[f]), ",".join(sorted(feat_cls[f]))))

    # ---- WORKLIST: the single-judge rows to re-adjudicate ----
    # A single-judge row is load-bearing if it carries a conviction feature that
    # has no panel support. Those rows, re-judged by the panel and kept, confirm
    # the convictions without losing vocabulary.
    worklist_idx = sorted({i for f in only_single for i in feat_rows[f]
                           if rows[i]["_cls"] == "single_judge"})
    worklist = []
    for i in worklist_idx:
        r = rows[i]
        carried = sorted((f for f in only_single if f in set(FB.features(r["text"], fv))),
                         key=lambda f: -full.weights[f])
        worklist.append({
            "text": r["text"],
            "stored_violates": bool(r["violates"]),
            "source": r.get("source"), "judge": r.get("judge"), "t": r.get("t"),
            "carries_unconfirmed_convictions": carried[:6],
        })
    os.makedirs(os.path.dirname(WORKLIST), exist_ok=True)
    with open(WORKLIST, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_what": "Re-adjudication worklist (the LABEL lever, 2026-11-10). "
                             "Single-judge rows carrying conviction features (>= DAMNING) that NO "
                             "panel row supports -- the panel should re-judge these, keeping the row "
                             "and its vocabulary, converting it to a reasoned row. NOT a deletion "
                             "list. Produced offline; the panel run is runner-gated.",
                             "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "count": len(worklist)}) + "\n")
        for w in worklist:
            fh.write(json.dumps(w, ensure_ascii=False) + "\n")
    print("\n=== WORKLIST ===")
    print("  single-judge rows to re-adjudicate (carry an unconfirmed conviction): %d" % len(worklist))
    print("  written: %s" % WORKLIST)
    print("  sample:")
    for w in worklist[:8]:
        print("    [%s] %-70s  <- %s" % ("V" if w["stored_violates"] else "C",
              w["text"][:70], ",".join(w["carries_unconfirmed_convictions"][:3])))


if __name__ == "__main__":
    main()
