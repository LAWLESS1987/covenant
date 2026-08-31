#!/usr/bin/env python3
"""
conformance.py -- prove you compute the same thing, not that you have the same
file.

WHERE THIS CAME FROM

  The 2025 Misha Mahowald Prize shortlist, read for what it implies rather than
  for what it builds. Three works, and one idea underneath all of them:

    * Jens Egholm Pedersen (KTH), Neuromorphic Intermediate Representation --
      a standardised set of computational primitives so a model defined once
      runs on many backends. Its move is to stop comparing IMPLEMENTATIONS and
      start comparing a canonical description of the COMPUTATION.
    * Mark Iskarous (JHU), invariant neuromorphic representations of touch --
      a texture representation invariant to force and speed. The identity
      survives; the incidental variation is discarded.
    * OPUS Lab (Camsari, UCSB), probabilistic bits -- massive parallelism,
      asynchronous dynamics, sparsity. Agreement without a clock and without a
      centre.

  All three are the same lesson: CANONICAL MEANING SURVIVES INCIDENTAL FORM.
  It is also, exactly, the lesson this project learned twice in one day --
  verify.sh and constitution.py disagreeing over whether a heading's em dash
  was part of what was signed, and scale.py making a level's value depend on
  its height so a deep region could never agree with a shallow one beside it.
  Both were fixed by finding the canonical form. This file generalises that fix
  instead of applying it a third time by hand.

THE GAP IT CLOSES

  federation.py decides agreement with `theirs["hash"] == mine["hash"]`, where
  the hash is taken over the TEXT of the rules. That has two failure modes and
  they point in opposite directions:

    FALSE DIVERGENCE  a faithful reimplementation -- another language, the
                      constitution translated, the same rules reformatted --
                      reads DIVERGED, though it behaves identically.
    FALSE AGREEMENT   an instance that copied the text and changed the CODE
                      reads SAME CORE, though it behaves differently.

  The second is the dangerous one. The first is the limiting one: it means a
  "sovereign fork" must run this author's exact bytes to demonstrate that it
  agrees, which is the gatekeeper property GOVERNANCE.md section VI claims to
  have removed. A branch under its own law, by its own operators, cannot
  currently prove conformance at all.

WHAT IT DOES

  Runs a fixed set of vectors through this instance's governance primitives and
  hashes the SEMANTIC results -- verdicts, quorum outcomes, whether divergence
  survived a climb -- and never the prose that explains them. Prose is exactly
  the incidental form a reimplementation would differ on, and exactly what a
  text hash mistakes for meaning.

  Two instances sharing no source can then produce the same conformance root,
  and an instance that copied the text but broke the behaviour cannot.

WHAT IT IS NOT

  It is not a proof of correctness, and it cannot be. It says an implementation
  answers these vectors the way this one does. Vectors nobody thought to write
  are not covered, which is why the count is printed with the root -- a root
  over three vectors and a root over three hundred are different claims, and
  quoting one as the other is the failure this project keeps finding.

  It also decides nothing. Conformance is evidence about an implementation,
  never a licence to overwrite one. Divergence stays reported and unpunished.

USE
  python conformance.py             # this instance's root
  python conformance.py --detail    # every vector and its canonical result
  python conformance.py --json      # machine-readable results
  python conformance.py --spec      # THE ONE FOR SOMEBODY ELSE: inputs,
                                    # expected outputs and the hashing rule,
                                    # so the mechanism can be rebuilt in any
                                    # language without reading this file.
                                    # Committed at docs/CONFORMANCE_SPEC.json
                                    # and checked for drift by test N1 X5.

LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SPEC_VERSION = "covenant-conformance-v1"

A, B, C = "a" * 64, "b" * 64, "c" * 64


def _canon(obj: Any) -> str:
    """Stable text for a result. Sorted keys, no floats, no prose."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str)


# ---------------------------------------------------------------------------
# THE VECTORS, as DATA rather than as code.
#
# They were lambdas. That ran them perfectly and was useless for the one
# thing this file exists to enable: somebody reimplementing the mechanism in
# another language and finding out whether they get the same root. Under the
# old shape the inputs lived only inside closures, so --json published the
# ANSWERS and never the QUESTIONS, and a reimplementer had to read Python to
# learn what to reimplement. That is a dependency on this implementation
# smuggled into a mechanism whose whole purpose is not having one.
#
# So the inputs are a table, and --spec publishes it. The table is not a
# description OF what runs -- it IS what runs. There is no second copy to
# keep in step, which is the only arrangement in which two things stay in
# step.
#
# THE ENCODING, complete, so that nothing in this file needs reading to
# reimplement it:
#
#   root    "A" | "B" | "C" | null   three distinct 64-char roots; null is a
#                                    witness that did not answer
#   leaf    {"leaf": name, "root": root}
#   level   {"level": name, "children": [node, ...]}
#   sugar   {"level": name, "carriers": [root, ...]}   ==  children named
#           "n0", "n1", ... in order. --spec emits the EXPANDED form and
#           never the sugar, so the published artefact carries no rule a
#           reader has to be told about separately.
#   attest  {"op": "attest", "roots": {witness: root}, "quorum": int}
#   climb   {"op": "climb", "tree": node}
#
# Every vector asks about SEMANTICS: what verdict, which witnesses counted,
# did a divergence survive. None asks how any of it is worded, because
# wording is the thing a faithful reimplementation is entitled to change.
# ---------------------------------------------------------------------------

ROOTS = {"A": A, "B": B, "C": C, None: None}


def _expand(node):
    """Sugar to explicit. Leaves take the names the old helper gave them, so
    the expansion is a rewriting of notation and not a change of input."""
    if "carriers" in node:
        return {"level": node["level"],
                "children": [{"leaf": "n%d" % i, "root": r}
                             for i, r in enumerate(node["carriers"])]}
    if "children" in node:
        return {"level": node["level"],
                "children": [_expand(c) for c in node["children"]]}
    return dict(node)


def _expand_input(inp):
    if inp.get("op") == "climb":
        return {"op": "climb", "tree": _expand(inp["tree"])}
    return dict(inp)


def _build(node, S):
    n = _expand(node)
    if "leaf" in n:
        return S.leaf(n["leaf"], ROOTS[n["root"]])
    return S.level(n["level"], [_build(c, S) for c in n["children"]])


def _run(inp):
    """Interpret one vector. Returns SEMANTICS only -- "why" and "limits" are
    prose and are dropped on purpose: another language will phrase them
    differently and be no less conformant for it."""
    import triangulate as T
    import scale as S

    op = inp.get("op")
    if op == "attest":
        r = T.attest({k: ROOTS[v] for k, v in inp["roots"].items()},
                     scale="", quorum=inp.get("quorum", 2))
        return {"verdict": r["verdict"], "agreed": r["agreed"],
                "answered": r["answered"], "silent": r["silent"],
                "outliers": r["outliers"]}
    if op == "climb":
        up, rep = S.climb(_build(inp["tree"], S))
        return {"verdict": rep["verdict"],
                "speaks_upward": bool(up),
                "divergences": len(rep.get("divergences", [])),
                "clean": S.overall(rep)[0]}
    raise ValueError("unknown op %r -- a vector this build cannot run is a "
                     "vector it must not silently pass" % (op,))


VECTORS = [
    # -- agreement, and what silence is not --------------------------------
    {"id": "T.agree.all",
     "why": "three witnesses holding one root agree",
     "input": {"op": "attest", "roots": {"x": "A", "y": "A", "z": "A"}}},
    {"id": "T.agree.one-silent",
     "why": "a witness that did not answer is not a witness that disagreed; "
            "it is named, never counted as an outlier",
     "input": {"op": "attest", "roots": {"x": "A", "y": "A", "z": None}}},
    {"id": "T.unproven.too-few",
     "why": "fewer answers than the quorum is UNPROVEN, never agreement with "
            "itself",
     "input": {"op": "attest", "roots": {"x": "A", "y": None, "z": None}}},
    {"id": "T.diverged.one-outlier",
     "why": "one differing witness is DIVERGED and the outlier is named",
     "input": {"op": "attest", "roots": {"x": "A", "y": "A", "z": "B"}}},
    {"id": "T.diverged.three-way",
     "why": "three-way disagreement declares no winner by luck of ordering",
     "input": {"op": "attest", "roots": {"x": "A", "y": "B", "z": "C"}}},
    {"id": "T.quorum.raised",
     "why": "a raised quorum is honoured",
     "input": {"op": "attest", "roots": {"x": "A", "y": "A", "z": "A"},
               "quorum": 4}},

    # -- composition, and the invariant that makes it safe -----------------
    {"id": "S.compose.agree",
     "why": "a level whose carriers agree, agrees, and speaks upward",
     "input": {"op": "climb",
               "tree": {"level": "L", "carriers": ["A", "A", "A"]}}},
    {"id": "S.compose.height-invariant",
     "why": "THE INVARIANCE: a bare carrier, a one-deep level and a "
            "three-deep sub-federation holding the same content all agree. A "
            "level's value must not depend on how deep it sits",
     "input": {"op": "climb", "tree": {"level": "MH", "children": [
         {"leaf": "bare", "root": "A"},
         {"level": "one", "carriers": ["A", "A", "A"]},
         {"level": "three", "children": [
             {"level": "d", "carriers": ["A", "A", "A"]},
             {"level": "e", "carriers": ["A", "A", "A"]}]}]}}},
    {"id": "S.silence.upward",
     "why": "a DIVERGED level speaks silence upward, never its majority root "
            "-- the rule that stops disagreement laundering itself into "
            "consensus one level at a time",
     "input": {"op": "climb",
               "tree": {"level": "D", "carriers": ["A", "B", "A"]}}},
    {"id": "S.divergence.survives-climb",
     "why": "a divergence three levels down is still counted at the summit, "
            "and the summit refuses to call itself clean",
     "input": {"op": "climb", "tree": {"level": "top", "children": [
         {"level": "k1", "carriers": ["A", "A", "A"]},
         {"level": "k2", "carriers": ["A", "B", "A"]},
         {"level": "k3", "carriers": ["A", "A", "A"]}]}}},
    {"id": "S.clean.is-reachable",
     "why": "a genuinely clean tree DOES report clean, or the check is only a "
            "machine for saying no",
     "input": {"op": "climb", "tree": {"level": "ok", "children": [
         {"level": "k1", "carriers": ["A", "A", "A"]},
         {"level": "k2", "carriers": ["A", "A", "A"]},
         {"level": "k3", "carriers": ["A", "A", "A"]}]}}},
]


def run_vectors() -> List[Dict[str, Any]]:
    out = []
    for v in VECTORS:
        try:
            result = _run(v["input"])
            err = None
        except Exception as e:                               # noqa: BLE001
            result, err = None, "%s: %s" % (type(e).__name__, e)
        out.append({"id": v["id"], "why": v["why"],
                    "result": result, "error": err})
    return out


def conformance_root(results: List[Dict[str, Any]]) -> str:
    """Domain-separated hash over (id, canonical result) pairs, sorted by id.

    Sorted so that the ORDER vectors happen to be listed in cannot change the
    root -- the same reason constitution.py sorts its block digests. A root
    that moved when someone reordered a list would be a root about the list.
    """
    h = hashlib.sha256()
    h.update(SPEC_VERSION.encode())
    for r in sorted(results, key=lambda x: x["id"]):
        h.update(b"\x00")
        h.update(r["id"].encode())
        h.update(b"\x00")
        h.update(_canon(r["result"] if r["error"] is None
                        else {"error": r["error"]}).encode())
    return h.hexdigest()


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    results = run_vectors()
    root = conformance_root(results)
    failed = [r for r in results if r["error"]]

    if "--spec" in argv:
        # Everything a reimplementer needs and nothing that would let them
        # copy: the QUESTIONS, the expected answers, and the root over both.
        # Trees are emitted expanded, so the sugar in the table above is a
        # convenience of this file and never a rule anyone else must learn.
        by_id = {r["id"]: r for r in results}
        print(json.dumps(
            {"spec": SPEC_VERSION, "root": root, "vectors": [
                {"id": v["id"], "why": v["why"],
                 "input": _expand_input(v["input"]),
                 "expected": by_id[v["id"]]["result"]}
                for v in sorted(VECTORS, key=lambda v: v["id"])],
             "roots": {"A": A, "B": B, "C": C},
             "note": "Reproduce `root` from `input` -> `expected` in any "
                     "language, sharing none of this code. Hash: sha256 over "
                     "spec, then for each vector sorted by id, a NUL byte, "
                     "the id, a NUL byte, and the canonical JSON of expected "
                     "(sorted keys, no spaces). A differing root is a finding "
                     "worth reporting, not a failure to hide."},
            indent=1, sort_keys=True, default=str))
        return 1 if failed else 0

    if "--json" in argv:
        print(json.dumps({"spec": SPEC_VERSION, "root": root,
                          "vectors": len(results),
                          "results": results}, indent=1, sort_keys=True,
                         default=str))
        return 1 if failed else 0

    print()
    print("  CONFORMANCE -- does this instance BEHAVE like the covenant?")
    print("  " + "=" * 62)
    print("  spec    : %s" % SPEC_VERSION)
    print("  vectors : %d" % len(results))
    print("  root    : %s" % root)
    print()

    if "--detail" in argv:
        for r in sorted(results, key=lambda x: x["id"]):
            mark = "ERROR" if r["error"] else "ok   "
            print("  %s %s" % (mark, r["id"]))
            print("        %s" % r["why"])
            print("        -> %s" % (r["error"] or _canon(r["result"]))[:110])
        print()

    if failed:
        print("  %d vector(s) could not run. This instance does NOT conform,"
              % len(failed))
        print("  and an implementation that cannot answer is not one that")
        print("  answered differently -- the same distinction the vectors")
        print("  themselves are about.")
        for r in failed:
            print("      %-28s %s" % (r["id"], r["error"]))
        return 1

    print("  Publish this root beside the constitution hash. Another instance")
    print("  matching it computes what this one computes -- in any language,")
    print("  with any wording, on any hardware. That is what a fork needs in")
    print("  order to prove it agrees WITHOUT running these exact bytes.")
    print()
    print("  What it does not say: that either instance is CORRECT, or that")
    print("  vectors nobody wrote are covered. A root over %d vectors is a"
          % len(results))
    print("  claim about %d vectors, and quoting it as more is the failure"
          % len(results))
    print("  this project keeps finding in its own reports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
