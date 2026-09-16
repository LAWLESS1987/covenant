#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""spec_reference.py -- `attest` and `climb` implemented from docs/SEMANTICS.md
and from nothing else.

THE RULE THIS FILE IS WRITTEN UNDER, and it is the only thing that makes it
worth having: it may read docs/SEMANTICS.md. It may NOT read triangulate.py or
scale.py, import them, or copy a line from them. Every rule below is traceable
to a numbered step in that document, and the step is named in a comment.

WHY. Until 2026-09-15 this project's conformance evidence was 23 vectors and a
root hashed over their expected outputs -- an answer key, and one that could be
reproduced without doing any of the work (A121). A test-vector suite pins the
computation only where it samples. A specification plus a second implementation
checked against the first over an EXHAUSTIVELY ENUMERATED input space pins it
everywhere inside the bound. test_r2_semantics.py does that comparison.

If this file and triangulate/scale disagree, one of them is a defect and the
disagreement is a finding worth reporting. Neither is authoritative over the
other by fiat; docs/SEMANTICS.md is.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

AGREE = "AGREE"
DIVERGED = "DIVERGED"
UNPROVEN = "UNPROVEN"

# SEMANTICS.md 2.2 -- deeper than this is refused, not recursed into.
MAX_DEPTH = 64


def attest(roots: Dict[str, Optional[str]],
           quorum: Optional[int] = None) -> Dict[str, Any]:
    """SEMANTICS.md section 1."""
    # 1.3 step 1 -- partition. "Absent" is null, empty, or anything falsy.
    answered = sorted(k for k, v in roots.items() if v)
    silent = sorted(k for k, v in roots.items() if not v)

    # 1.3 step 2 -- quorum. A supplied quorum is used UNCHANGED, including
    # zero, negative, or larger than the number of witnesses. The default
    # counts every witness ASKED, not those present.
    if quorum is None:
        quorum = max(2, len(roots) // 2 + 1)

    # 1.3 step 3 -- tally: distinct root -> sorted holders.
    tally: Dict[str, List[str]] = {}
    for who in answered:
        tally.setdefault(roots[who], []).append(who)
    for holders in tally.values():
        holders.sort()

    # 1.3 step 4 -- rank by descending holder count, then ascending root.
    ranked = sorted(tally.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    # 1.3 step 5 -- a reference needs quorum met, at least one answered root,
    # and either a single distinct root or a STRICT plurality. No tie-break is
    # invented: choosing between equally-held roots would be a decision.
    quorum_met = len(answered) >= quorum
    reference: Optional[str] = None
    if quorum_met and ranked:
        if len(ranked) == 1 or len(ranked[0][1]) > len(ranked[1][1]):
            reference = ranked[0][0]

    # 1.3 step 6 -- an outlier is a witness that differs FROM A REFERENCE. With
    # no reference the word names nothing, for either reason it can be absent.
    outliers = (sorted(w for w in answered if roots[w] != reference)
                if reference is not None else [])

    # 1.3 step 7 -- first matching rule decides. Rule 1 precedes rule 2, so a
    # quorum not met is UNPROVEN even when every answering witness agreed.
    if len(answered) < quorum:
        verdict, agreed = UNPROVEN, False
    elif len(tally) == 1:
        verdict, agreed = AGREE, True
    else:
        verdict, agreed = DIVERGED, False

    return {
        "verdict": verdict,
        "agreed": agreed,
        "quorum": quorum,
        "answered": answered,
        "silent": silent,
        "reference": reference,
        "outliers": outliers,
        "held_by": tally.get(reference, []) if reference is not None else [],
    }


def climb(node: Dict[str, Any],
          depth: int = 0) -> Tuple[Optional[str], Dict[str, Any]]:
    """SEMANTICS.md section 2."""
    name = node.get("name", "?")            # 2.1 -- a missing name is "?"

    # 2.2 -- the depth limit, refused rather than followed. A refused level
    # judged nothing, so every field is the honest value for that: it answered
    # nobody, heard nobody, has no outliers, did not agree, and speaks silence.
    # (Until A123 was fixed on 2026-09-15 the live code omitted five of these,
    # making the over-depth report a third shape. This file's first draft
    # reproduced the omission, because a specification describes what runs.)
    if depth > MAX_DEPTH:
        return None, {"name": name, "verdict": UNPROVEN, "agreed": False,
                      "answered": [], "silent": [], "outliers": [],
                      "reference": None, "divergences": [], "children": [],
                      "depth": depth, "speaks_upward": False,
                      "silent_diverged": [], "silent_unproven": []}

    # 2.3 -- a LEAF is a node with no `children` KEY. `children: []` is a level
    # with no children, not a leaf.
    if "children" not in node:
        held = node.get("root")
        return held, {"name": name,
                      "verdict": AGREE if held else UNPROVEN,
                      "agreed": bool(held),
                      "answered": [], "silent": [], "outliers": [],
                      "reference": held, "divergences": [], "children": [],
                      "depth": depth, "speaks_upward": held is not None,
                      "leaf": True,
                      "silent_diverged": [], "silent_unproven": []}

    # 2.4 step 1 -- descend in order; record under the CHILD'S OWN reported
    # name. A repeated name replaces the earlier entry in this map.
    spoken: Dict[str, Optional[str]] = {}
    child_reports: List[Dict[str, Any]] = []
    divergences: List[str] = []
    for child in node["children"]:
        up, rep = climb(child, depth + 1)
        spoken[rep["name"]] = up
        child_reports.append(rep)
        # 2.4 step 2 -- children's divergences are carried first, in order.
        divergences.extend(rep.get("divergences", []))

    # 2.4 step 3 -- attest over what the children spoke.
    v = attest(spoken, quorum=node.get("quorum"))

    # 2.4 step 4 -- ONE ENTRY PER DISSENTING WITNESS, only when DIVERGED, and
    # each carrying the denominator -- which is reported, never divided by.
    if v["verdict"] == DIVERGED:
        asked = len(v["answered"]) + len(v["silent"])
        if v["reference"] is None:
            for w in v["answered"]:
                divergences.append(
                    "%s/%s: party to a split with no strict plurality, so no "
                    "root here is the reference [%d of %d asked at this level]"
                    % (name, w, len(v["answered"]), asked))
        else:
            for w in v["outliers"]:
                divergences.append(
                    "%s/%s: differs from the reference held by %s "
                    "[%d of %d asked at this level]"
                    % (name, w, v["held_by"], len(v["outliers"]), asked))

    # 2.4 step 5 -- only AGREE speaks, and it speaks the reference UNCHANGED.
    # DIVERGED and UNPROVEN both speak silence.
    up = v["reference"] if v["verdict"] == AGREE else None

    # 2.4 step 6 -- the two silences partition the silent children.
    silent_diverged = sorted(r["name"] for r in child_reports
                             if spoken.get(r["name"]) is None
                             and r["verdict"] == DIVERGED)
    silent_unproven = sorted(r["name"] for r in child_reports
                             if spoken.get(r["name"]) is None
                             and r["verdict"] != DIVERGED)

    return up, {"name": name, "verdict": v["verdict"], "agreed": v["agreed"],
                "answered": v["answered"], "silent": v["silent"],
                "outliers": v["outliers"], "reference": v["reference"],
                "silent_diverged": silent_diverged,
                "silent_unproven": silent_unproven,
                "divergences": divergences, "children": child_reports,
                "depth": depth, "speaks_upward": up is not None}


def clean(report: Dict[str, Any]) -> bool:
    """SEMANTICS.md 2.5 -- both conditions, and the first is the point."""
    return not report.get("divergences") and report.get("verdict") == AGREE
