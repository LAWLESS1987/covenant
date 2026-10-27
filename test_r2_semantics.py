#!/usr/bin/env python3
"""test_r2_semantics.py -- R2: the specification, checked EXHAUSTIVELY.

WHAT THIS ANSWERS. On 2026-09-15 Jens Egholm Pedersen (DTU) refuted this
project's conformance claim (A121). The conformance suite is an ANSWER KEY --
23 questions with their answers -- and his point was that a test-vector suite
pins the computation only at the points it samples, so no number of vectors
turns it into a specification. Five wrong readings once passed all eleven.

The answer is not more vectors. It is:

    docs/SEMANTICS.md   the rules, written independently of any implementation
    spec_reference.py   an implementation written from those rules and nothing
                        else -- forbidden to read triangulate.py or scale.py
    this file           the two compared over an input space ENUMERATED IN
                        FULL, not sampled

Inside the bound this is not a sample; it is every point. Outside the bound it
proves nothing, which is why the bound is PRINTED WITH THE RESULT. A claim
about tens of thousands of cases and a claim about 23 are different claims, and
quoting one as the other is the failure this project keeps finding.

WHAT IT PINS.
  A*  attest: every assignment of roots and silence over 0..5 witnesses, at
      every quorum in range plus the default. Compared on the semantic fields.
  C*  climb: every tree shape within the bound, at every leaf assignment, plus
      the named edge cases -- empty children, name collision, explicit quorum,
      and the depth limit.
  X*  the 23 published vectors reproduce from the spec alone, so SEMANTICS.md
      is at least as strong as the artefact it replaces.

A DISAGREEMENT IS A FINDING, not a failure to hide: it means the document and
the code differ, and one of them is wrong.

Pure: no network, no node, no database.
"""
from __future__ import annotations

import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import spec_reference as SPEC          # noqa: E402
import triangulate as LIVE_T           # noqa: E402
import scale as LIVE_S                 # noqa: E402

A, B, C = "a" * 64, "b" * 64, "c" * 64
VALUES = [None, "", A, B, C]           # "" is absent too -- falsy, not a root
LEAFVALS = [None, A, B, C]

results = []
counts = {"attest": 0, "climb": 0, "vectors": 0}


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:400]), flush=True)


# --------------------------------------------------------------- attest ----
ATTEST_FIELDS = ("verdict", "agreed", "quorum", "answered", "silent",
                 "reference", "outliers")


def attest_core(d):
    return {k: d[k] for k in ATTEST_FIELDS}


def enumerate_attest(max_witnesses=5):
    """EVERY assignment over 0..max_witnesses witnesses, at every quorum in
    range plus the default. Not a sample."""
    bad = []
    for n in range(0, max_witnesses + 1):
        names = ["w%d" % i for i in range(n)]
        for combo in itertools.product(VALUES, repeat=n):
            roots = dict(zip(names, combo))
            for q in [None] + list(range(0, n + 2)):
                counts["attest"] += 1
                mine = attest_core(SPEC.attest(roots, quorum=q))
                theirs = attest_core(LIVE_T.attest(dict(roots), quorum=q))
                if mine != theirs and len(bad) < 5:
                    bad.append({"roots": roots, "quorum": q,
                                "spec": mine, "live": theirs})
    return bad


# ---------------------------------------------------------------- climb ----
def shapes(depth_left, max_children, max_leaves):
    """Every tree shape within the bound, as nested tuples. () is a leaf."""
    out = [()]
    if depth_left <= 0:
        return out
    for k in range(1, max_children + 1):
        for combo in itertools.product(
                shapes(depth_left - 1, max_children, max_leaves), repeat=k):
            if sum(max(1, leaves_in(c)) for c in combo) <= max_leaves:
                out.append(combo)
    return out


def leaves_in(shape):
    return 1 if shape == () else sum(leaves_in(c) for c in shape)


def build(shape, vals, counter, prefix="n"):
    """Materialise a shape with the next leaf values off `vals`."""
    if shape == ():
        i = counter[0]
        counter[0] += 1
        return {"name": "%s%d" % (prefix, i), "root": vals[i]}
    i = counter[0]
    kids = [build(c, vals, counter, prefix) for c in shape]
    return {"name": "L%d" % i, "children": kids}


CLIMB_FIELDS = ("verdict", "reference", "silent_diverged", "silent_unproven")
LEVEL_FIELDS = ("answered", "silent", "outliers", "speaks_upward")


def climb_core(rep, is_root=True):
    """The semantic core both implementations publish. Live leaf reports carry
    fewer fields than level reports, so leaves are compared on what a leaf
    actually has -- comparing absent fields would test the harness, not the
    semantics."""
    core = {k: rep.get(k) for k in CLIMB_FIELDS}
    core["name"] = rep.get("name")
    core["depth"] = rep.get("depth")
    core["ndiv"] = len(rep.get("divergences", []))
    if not rep.get("leaf"):
        for k in LEVEL_FIELDS:
            core[k] = rep.get(k)
    core["children"] = [climb_core(c, False) for c in rep.get("children", [])]
    return core


def compare_tree(tree):
    up_s, rep_s = SPEC.climb(json.loads(json.dumps(tree)))
    up_l, rep_l = LIVE_S.climb(json.loads(json.dumps(tree)))
    return (up_s == up_l and climb_core(rep_s) == climb_core(rep_l),
            {"up_spec": up_s, "up_live": up_l})


def enumerate_climb(max_depth=3, max_children=3, max_leaves=4):
    bad = []
    for shape in shapes(max_depth, max_children, max_leaves):
        nleaf = leaves_in(shape)
        for vals in itertools.product(LEAFVALS, repeat=nleaf):
            tree = build(shape, list(vals), [0])
            counts["climb"] += 1
            ok, why = compare_tree(tree)
            if not ok and len(bad) < 5:
                bad.append({"tree": tree, **why})
    return bad


def main():
    print("R2 -- docs/SEMANTICS.md, checked against the live code "
          "EXHAUSTIVELY inside a stated bound\n")

    # ---- I: the independence the whole exercise rests on -------------------
    # If spec_reference.py may read triangulate.py or scale.py, then the two
    # sides of every comparison below are one implementation wearing two hats,
    # and 100,000 agreeing cases mean nothing. Asserted, not promised.
    src = open(os.path.join(HERE, "spec_reference.py"), encoding="utf-8").read()
    body = "\n".join(ln for ln in src.splitlines()
                     if not ln.lstrip().startswith("#"))
    body = body.split('"""', 2)[-1]          # drop the module docstring
    leaked = [w for w in ("triangulate", "scale", "conformance", "covenant")
              if w in body]
    check("R2.I1 spec_reference.py names no implementation module in its code "
          "-- without this, both sides of every comparison are the same code "
          "and the agreement below is worth nothing",
          not leaked, "references: %s" % leaked)

    # ---- A: attest ---------------------------------------------------------
    bad = enumerate_attest(5)
    check("R2.A1 attest: EVERY assignment of roots and silence over 0..5 "
          "witnesses, at every quorum in range and the default -- %d cases, "
          "enumerated in full, not sampled" % counts["attest"],
          not bad, bad[:2])

    # ---- C: climb ----------------------------------------------------------
    bad = enumerate_climb()
    check("R2.C1 climb: EVERY tree shape to depth 3, up to 3 children a level "
          "and 4 leaves, at every leaf assignment -- %d cases, enumerated in "
          "full" % counts["climb"], not bad, bad[:1])

    # ---- C: the named edge cases the enumeration cannot reach --------------
    edges = {
        "empty children is a LEVEL, not a leaf":
            {"name": "e", "children": []},
        "name collision -- later child replaces earlier in the map":
            {"name": "e", "children": [{"name": "dup", "root": A},
                                       {"name": "dup", "root": B},
                                       {"name": "z", "root": A}]},
        "explicit quorum 0":
            {"name": "e", "quorum": 0, "children": [{"name": "x", "root": A}]},
        "explicit quorum larger than the witnesses":
            {"name": "e", "quorum": 9, "children": [{"name": "x", "root": A},
                                                    {"name": "y", "root": A}]},
        "explicit negative quorum":
            {"name": "e", "quorum": -1, "children": [{"name": "x",
                                                      "root": None}]},
        "leaf with no name":
            {"children": [{"root": A}, {"root": A}]},
        "nested silence: a DIVERGED child and an UNPROVEN child":
            {"name": "top", "children": [
                {"name": "d", "children": [{"name": "p", "root": A},
                                           {"name": "q", "root": B}]},
                {"name": "u", "children": [{"name": "r", "root": None}]},
                {"name": "ok", "root": A}]},
    }
    bad_edges = []
    for label, tree in edges.items():
        counts["climb"] += 1
        ok, why = compare_tree(tree)
        if not ok:
            bad_edges.append((label, why))
    check("R2.C2 the named edge cases agree (%d): empty children, name "
          "collision, quorum 0 / oversized / negative, unnamed leaf, and the "
          "two silences side by side" % len(edges),
          not bad_edges, bad_edges)

    # The depth limit, built directly -- 66 levels is past MAX_DEPTH.
    deep = {"name": "d0", "root": A}
    for i in range(1, 67):
        deep = {"name": "d%d" % i, "children": [deep]}
    ok, why = compare_tree(deep)
    check("R2.C3 the depth limit agrees -- 66 nested levels, refused rather "
          "than recursed into", ok, why)

    # ---- X: the artefact it replaces --------------------------------------
    spec_path = os.path.join(HERE, "docs", "CONFORMANCE_SPEC.json")
    if os.path.isfile(spec_path):
        pub = json.load(open(spec_path, encoding="utf-8"))
        table = pub.get("roots", {})
        mism = []
        for vec in pub.get("vectors", []):
            counts["vectors"] += 1
            inp, exp = vec["input"], vec["expected"]
            if inp.get("op") == "attest":
                r = SPEC.attest({k: (table.get(v) if v else None)
                                 for k, v in inp["roots"].items()},
                                quorum=inp.get("quorum"))
                got = {"verdict": r["verdict"], "agreed": r["agreed"],
                       "answered": r["answered"], "silent": r["silent"],
                       "reference": r["reference"], "outliers": r["outliers"]}
            else:
                def expand(n):
                    if "children" in n:
                        return {"name": n.get("level", n.get("name", "?")),
                                "children": [expand(c) for c in n["children"]],
                                **({"quorum": n["quorum"]}
                                   if "quorum" in n else {})}
                    return {"name": n.get("leaf", n.get("name", "?")),
                            "root": table.get(n.get("root"))
                            if n.get("root") else None}
                _, rep = SPEC.climb(expand(inp["tree"]))
                got = {"verdict": rep["verdict"],
                       "clean": SPEC.clean(rep),
                       "divergences": len(rep["divergences"]),
                       "reference": rep["reference"],
                       "silent_diverged": rep["silent_diverged"],
                       "silent_unproven": rep["silent_unproven"],
                       "speaks_upward": rep["speaks_upward"]}
            shared = {k: v for k, v in got.items() if k in exp}
            want = {k: v for k, v in exp.items() if k in shared}
            if shared != want:
                mism.append((vec["id"], shared, want))
        check("R2.X1 all %d published vectors reproduce FROM THE "
              "SPECIFICATION ALONE, so docs/SEMANTICS.md is at least as strong "
              "as the answer key it replaces" % counts["vectors"],
              not mism, mism[:2])
    else:
        check("R2.X1 docs/CONFORMANCE_SPEC.json present to cross-check",
              False, spec_path)

    # ---- S: DOES THE COMPARISON HAVE TEETH? --------------------------------
    # A differential test passes when both sides agree -- INCLUDING when the
    # comparison is vacuous. Emptying climb_core() would make every case
    # compare equal and this suite would report a serene green forever. That
    # is A74's fake guard and A121's own defect, and this project has already
    # shipped that shape twice, so it is not hypothetical.
    #
    # The harness is therefore made to catch known-wrong implementations on
    # EVERY run, permanently, rather than once by hand at review time. Each
    # mutant below is one rule of SEMANTICS.md, broken. Each MUST be detected.
    real_attest = SPEC.attest

    def m_floor(roots, quorum=None):            # 1.3 step 2: floor of 2 -> 1
        if quorum is None:
            q = max(1, len(roots) // 2 + 1)
            return real_attest(roots, quorum=q)
        return real_attest(roots, quorum=quorum)

    def m_loose(roots, quorum=None):            # 1.3 step 5: strict -> loose
        r = dict(real_attest(roots, quorum=quorum))
        if r["reference"] is None and r["verdict"] == "DIVERGED":
            tally = {}
            for w in r["answered"]:
                tally.setdefault(roots[w], []).append(w)
            top = sorted(tally.items(), key=lambda kv: (-len(kv[1]), kv[0]))
            if top:
                r["reference"] = top[0][0]
                r["outliers"] = sorted(w for w in r["answered"]
                                       if roots[w] != r["reference"])
        return r

    def m_order(roots, quorum=None):            # 1.3 step 7: rule 2 before 1
        r = dict(real_attest(roots, quorum=quorum))
        if r["verdict"] == "UNPROVEN" and r["answered"]:
            vals = {roots[w] for w in r["answered"]}
            if len(vals) == 1:
                r["verdict"], r["agreed"] = "AGREE", True
                r["reference"] = vals.pop()
        return r

    attest_mutants = {"quorum floor 2 -> 1": m_floor,
                      "strict plurality -> loose": m_loose,
                      "UNPROVEN checked after AGREE": m_order}
    undetected = []
    for label, mut in attest_mutants.items():
        found = False
        for n in (1, 2, 3, 4):
            names = ["w%d" % i for i in range(n)]
            for combo in itertools.product(VALUES, repeat=n):
                roots = dict(zip(names, combo))
                for q in [None] + list(range(0, n + 2)):
                    if (attest_core(mut(roots, quorum=q))
                            != attest_core(LIVE_T.attest(dict(roots),
                                                         quorum=q))):
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if not found:
            undetected.append(label)
    check("R2.S1 the attest comparison HAS TEETH: %d deliberately broken "
          "implementations of SEMANTICS.md rules are each caught"
          % len(attest_mutants), not undetected, undetected)

    def m_launder(node, depth=0):
        """2.4 step 5 broken: a DIVERGED level speaks its reference upward --
        the laundering that turns hidden disagreement into consensus."""
        up, rep = SPEC.climb(node, depth)
        if rep["verdict"] == "DIVERGED" and rep.get("reference"):
            return rep["reference"], rep
        return up, rep

    def m_merge(node, depth=0):
        """2.4 step 6 broken: the two silences merged into one list."""
        up, rep = SPEC.climb(node, depth)
        both = sorted(rep["silent_diverged"] + rep["silent_unproven"])
        rep = dict(rep, silent_diverged=both, silent_unproven=both)
        return up, rep

    climb_mutants = {"DIVERGED speaks its root upward": m_launder,
                     "the two silences merged": m_merge}
    undetected = []
    for label, mut in climb_mutants.items():
        found = False
        for shape in shapes(2, 3, 3):
            for vals in itertools.product(LEAFVALS, repeat=leaves_in(shape)):
                tree = build(shape, list(vals), [0])
                u_m, r_m = mut(json.loads(json.dumps(tree)))
                u_l, r_l = LIVE_S.climb(json.loads(json.dumps(tree)))
                if u_m != u_l or climb_core(r_m) != climb_core(r_l):
                    found = True
                    break
            if found:
                break
        if not found:
            undetected.append(label)
    check("R2.S2 the climb comparison HAS TEETH: %d deliberately broken "
          "implementations are each caught, including the laundering bug this "
          "whole mechanism exists to prevent" % len(climb_mutants),
          not undetected, undetected)

    ok = sum(1 for r in results if r)
    print("\n  BOUND, stated because it is the whole claim: attest over 0..5 "
          "witnesses x {absent, empty, A, B, C} x every quorum in range;")
    print("  climb over every shape to depth 3, <=3 children, <=4 leaves, "
          "x {absent, A, B, C} per leaf; plus %d edge cases and depth 66."
          % len(edges))
    print("  Inside it: every point. Outside it: nothing proven.")
    print("  attest cases %d | climb cases %d | published vectors %d"
          % (counts["attest"], counts["climb"], counts["vectors"]))
    print("\nR2: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
