#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
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

LICENCE: Apache-2.0.
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
#           `quorum` is OPTIONAL. When it is ABSENT the implementation must
#           supply its own default. That default is deliberately NOT restated
#           here -- a rule written in two places is a rule that drifts, which
#           is the failure this whole file exists to catch. It is PINNED BY
#           THE VECTORS instead, which is the only form of statement that
#           cannot go stale: T.unproven.too-few and T.agree.one-silent
#           bracket it at 2 for three witnesses,
#           T.quorum.default-scales-with-witnesses and
#           T.quorum.default-met-at-five bracket it at 3 for five, and
#           S.quorum.default-scales-at-a-level shows the same default is what
#           a climb level uses. No constant satisfies all five.
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
        # `quorum` is passed through EXACTLY as the vector gives it, absence
        # included. It used to default to 2 here, which meant a vector written
        # to exercise the implementation's own default was handed a constant
        # and tested nothing -- the harness quietly answering the question it
        # was built to ask.
        r = T.attest({k: ROOTS[v] for k, v in inp["roots"].items()},
                     scale="", quorum=inp.get("quorum"))
        return {"verdict": r["verdict"], "agreed": r["agreed"],
                "answered": r["answered"], "silent": r["silent"],
                # THE REFERENCE, IN FULL. Not decoration: without it, "which
                # root won" is never published, so an implementation that does
                # no tallying at all -- or one that names a root by the
                # alphabet -- is indistinguishable from one that counts. It
                # also makes the `roots` map load-bearing rather than
                # scenery: a checker comparing the bare symbols "A"/"B" now
                # produces a different value here.
                "reference": r["reference"],
                "outliers": r["outliers"]}
    if op == "climb":
        up, rep = S.climb(_build(inp["tree"], S))
        return {"verdict": rep["verdict"],
                "speaks_upward": bool(up),
                # What the level TALLIED, beside whether it SPOKE. They are
                # not the same fact: a DIVERGED level with a strict plurality
                # has a reference and still speaks silence, and publishing
                # only the boolean leaves which root an agreeing level speaks
                # entirely unconstrained.
                "reference": rep.get("reference"),
                "divergences": len(rep.get("divergences", [])),
                # The two silences, kept apart. "My child disagreed
                # internally" and "my child could not establish anything" are
                # different facts, and a parent that cannot tell them apart
                # cannot respond to either.
                "silent_diverged": rep.get("silent_diverged", []),
                "silent_unproven": rep.get("silent_unproven", []),
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
     "why": "three-way disagreement declares no winner by luck of ordering -- "
            "and now MEANS it. KILLS THE ORDERING READING that this vector "
            "used to enshrine: it once expected outliers ['y','z'], which "
            "silently made x's root the reference for no reason but that x "
            "sorts first, asserting the opposite of its own sentence. One "
            "holder each is no strict plurality, so there is NO reference, and "
            "with no reference nothing is an outlier -- the word means "
            "'differs from the reference' and there is nothing to differ from",
     "input": {"op": "attest", "roots": {"x": "A", "y": "B", "z": "C"}}},
    {"id": "T.quorum.raised",
     "why": "a raised quorum is honoured",
     "input": {"op": "attest", "roots": {"x": "A", "y": "A", "z": "A"},
               "quorum": 4}},

    # -- what the default quorum IS, since a constant answers every vector
    #    above and is wrong ---------------------------------------------------
    {"id": "T.quorum.default-scales-with-witnesses",
     "why": "KILLS THE CONSTANT-QUORUM READING, and the majority-of-those-"
            "PRESENT reading with it, in one case. Five witnesses asked, two "
            "answer and agree. A constant 2 calls that agreement for all five; "
            "so does a majority of the two who ANSWERED. A majority of the "
            "five ASKED is 3, so this is UNPROVEN. Two of a hundred witnesses "
            "must not be able to speak for the hundred, and silencing "
            "witnesses must never make agreement EASIER -- a mechanism where "
            "suppressing others is what wins you the verdict is exactly the "
            "transaction at another's expense this project refuses",
     "input": {"op": "attest",
               "roots": {"v": "A", "w": "A", "x": None, "y": None,
                         "z": None}}},
    {"id": "T.quorum.default-met-at-five",
     "why": "the far side of the same bracket, without which the rule above "
            "could be read as 'five witnesses can never agree'. Three of five "
            "answering DOES clear the derived quorum. With T.unproven.too-few "
            "and T.agree.one-silent fixing it at 2 for three witnesses, the "
            "two brackets together admit a majority of those asked and admit "
            "no constant, no unanimity rule, and no count of the answerers",
     "input": {"op": "attest",
               "roots": {"v": "A", "w": "A", "x": "A", "y": None,
                         "z": None}}},

    # -- that a tally actually happens, and what it may not invent ------------
    {"id": "T.diverged.reference-is-tallied",
     "why": "KILLS THE NO-TALLYING READING -- 'the reference is the root of "
            "the first answering witness'. Every other DIVERGED vector happens "
            "to seat the most-held root on the ordinally-first witness, so an "
            "implementation that counts nothing passes all of them and the "
            "word 'majority' is never once exercised AS a majority. Here the "
            "first witness is the lone dissenter: roots B,A,A, so the "
            "reference is A, held by y and z, and the outlier is x. An "
            "implementation that does not tally returns the exact inverse",
     "input": {"op": "attest", "roots": {"x": "B", "y": "A", "z": "A"}}},
    {"id": "T.diverged.plurality-without-majority",
     "why": "KILLS THE ABSOLUTE-MAJORITY READING of the reference. Four "
            "witnesses holding A,A,B,C: A has strictly more holders than any "
            "other root, but only two of four -- a strict plurality and not "
            "more than half. It is the reference, and BOTH dissenters are "
            "named. A rule demanding over half would report no reference and "
            "no outliers here, and a reader would learn nothing about who "
            "differs from whom",
     "input": {"op": "attest",
               "roots": {"w": "A", "x": "A", "y": "B", "z": "C"}}},
    {"id": "T.diverged.tie-for-top",
     "why": "KILLS EVERY INVENTED TIE-BREAK, including the ordinally-lowest-"
            "root rule both cold reimplementations independently chose. Five "
            "witnesses holding A,A,B,B,C: two roots tie for most-held. A "
            "tie-break would crown A and report three outliers. There is no "
            "strict plurality, so there is NO reference and nothing is an "
            "outlier. Choosing between equally-held roots would be a DECISION, "
            "and this mechanism reports evidence and decides nothing -- the "
            "same reason it never overwrites the party it disagrees with",
     "input": {"op": "attest",
               "roots": {"v": "A", "w": "A", "x": "B", "y": "B", "z": "C"}}},

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

    # -- the same four questions again, INSIDE the climb, where getting them
    #    wrong is worth more and shows less ------------------------------------
    {"id": "S.quorum.default-scales-at-a-level",
     "why": "KILLS THE CONSTANT-QUORUM READING WHERE IT COSTS MOST: inside a "
            "federation. Five children, two agreeing, three that never "
            "answered. Under a constant 2 this level AGREES and speaks "
            "upward, so a federation of any size speaks on the word of two of "
            "its members and every level above it reads that as the whole. "
            "Under a majority of the five ASKED it is UNPROVEN and silent. It "
            "also pins a null-rooted leaf, which the two cold "
            "reimplementations split three ways: it is a SILENT witness, not "
            "a disagreeing one",
     "input": {"op": "climb", "tree": {"level": "wide", "children": [
         {"level": "k1", "carriers": ["A", "A", "A"]},
         {"level": "k2", "carriers": ["A", "A", "A"]},
         {"leaf": "s3", "root": None},
         {"leaf": "s4", "root": None},
         {"leaf": "s5", "root": None}]}}},
    {"id": "S.divergences.two-outliers-one-level",
     "why": "SPLITS 'COUNT DIVERGED LEVELS' FROM 'COUNT DISSENTING "
            "WITNESSES', which every earlier climb vector left identical "
            "because each of its diverged levels held exactly one outlier. "
            "One level over four carriers A,A,B,C: two witnesses dissent from "
            "one reference. Counting levels says 1; counting dissenters says "
            "2. Two dissenters flattened into one number is the "
            "outvoted-into-invisibility failure happening at the tally instead "
            "of at the vote. It pins one thing more: a DIVERGED level still "
            "REPORTS its reference while SPEAKING nothing upward",
     "input": {"op": "climb",
               "tree": {"level": "four", "carriers": ["A", "A", "B", "C"]}}},
    {"id": "S.divergences.two-levels",
     "why": "the other half of that split, and the half that stops the count "
            "being read as 'outliers at the top level'. Two DIFFERENT levels "
            "with one dissenter each also total 2, so the number is over "
            "witnesses wherever in the tree they stand. Note what the summit "
            "does: it AGREES, and it still refuses to call itself clean",
     "input": {"op": "climb", "tree": {"level": "two-bad", "children": [
         {"level": "k1", "carriers": ["A", "A", "B"]},
         {"level": "k2", "carriers": ["A", "A", "B"]},
         {"level": "k3", "carriers": ["A", "A", "A"]},
         {"level": "k4", "carriers": ["A", "A", "A"]},
         {"level": "k5", "carriers": ["A", "A", "A"]}]}}},
    {"id": "S.divergences.split-counts-every-party",
     "why": "KILLS THE READING THAT A LEVEL WITH NO REFERENCE COUNTS FOR "
            "NOTHING -- the trap that the no-reference rule opens and that a "
            "naive count walks straight into. A three-way split names no "
            "outliers, correctly, since there is no reference to be an outlier "
            "FROM; so a tally taken from 'outliers' alone scores the whole "
            "split ZERO, it vanishes as the report climbs, and the summit "
            "reports clean over a hidden disagreement -- the one output this "
            "system must never produce. Every witness that answered into the "
            "split is party to it: three dissenters, and no clean summit",
     "input": {"op": "climb", "tree": {"level": "split", "children": [
         {"level": "k1", "carriers": ["A", "B", "C"]},
         {"level": "k2", "carriers": ["A", "A", "A"]},
         {"level": "k3", "carriers": ["A", "A", "A"]}]}}},
    {"id": "S.unproven.speaks-silence",
     "why": "PINS WHAT AN UNPROVEN LEVEL SPEAKS UPWARD, which no vector ever "
            "reached, so an implementation could have chosen anything. Child "
            "'u' has one carrier answering out of three: UNPROVEN, and it "
            "holds A. Its two siblings agree on B. If UNPROVEN spoke its root "
            "the parent would see A against B and report DIVERGED with a "
            "dissenter -- reading 'could not be established' as 'established', "
            "a claim stronger than its evidence. Speaking silence, the parent "
            "agrees on B over two of the three it asked, and u is reported "
            "under silent_unproven and never under silent_diverged. This is "
            "also a CLEAN climb containing two distinct roots",
     "input": {"op": "climb", "tree": {"level": "mixed", "children": [
         {"level": "u", "carriers": ["A", None, None]},
         {"level": "k2", "carriers": ["B", "B", "B"]},
         {"level": "k3", "carriers": ["B", "B", "B"]}]}}},
    {"id": "S.silence.two-kinds",
     "why": "KILLS THE READING THAT ONE SILENCE IS ENOUGH. A DIVERGED child "
            "and an UNPROVEN child both speak nothing upward, so a report that "
            "publishes only 'silent' makes them the same fact -- but 'my child "
            "disagreed internally' and 'my child could not establish anything' "
            "call for different responses, and merging them loses the "
            "difference at exactly the level where someone would act on it. "
            "This is the not_understood / infrastructure_failure distinction "
            "the project already draws, drawn here for the same reason. dv "
            "lands in silent_diverged, un in silent_unproven, and only dv's "
            "dissenter is counted -- silence is not disagreement",
     "input": {"op": "climb", "tree": {"level": "both", "children": [
         {"level": "dv", "carriers": ["A", "A", "B"]},
         {"level": "un", "carriers": ["A", None, None]},
         {"level": "k3", "carriers": ["A", "A", "A"]},
         {"level": "k4", "carriers": ["A", "A", "A"]},
         {"level": "k5", "carriers": ["A", "A", "A"]}]}}},
    {"id": "S.clean.distinct-root",
     "why": "KILLS THE CONSTANT-ROOT-UPWARD READING. Every other climb vector "
            "agrees on the single root A, so an implementation that speaks a "
            "hardcoded value upward -- or the first child's root, or the "
            "level's own name -- answers all of them identically to one that "
            "speaks what was actually agreed. This climb agrees on B and "
            "publishes, in full, the reference it speaks. A party handed a "
            "verdict must be able to check it against its own view rather than "
            "trust the verdict's word for it, and a boolean cannot be checked "
            "against anything",
     "input": {"op": "climb", "tree": {"level": "allB", "children": [
         {"level": "k1", "carriers": ["B", "B", "B"]},
         {"level": "k2", "carriers": ["B", "B", "B"]},
         {"level": "k3", "carriers": ["B", "B", "B"]}]}}},
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
