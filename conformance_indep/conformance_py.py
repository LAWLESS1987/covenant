#!/usr/bin/env python3
"""
conformance_py.py -- clean-room reimplementation of "covenant-conformance-v1".

Written from CONFORMANCE_SPEC.json alone: its "note", and each vector's
"input", "expected" and "why".  No covenant source was read, imported or
searched for.  Standard library only (json, hashlib, os, sys).

=====================================================================
INFERRED SEMANTICS
=====================================================================

Root names
----------
Inputs name roots by a short key ("A", "B", "C").  Expected outputs carry
the 64-hex value listed under the spec's top-level "roots" table.  So a
root value from an input is looked up in that table; a value not in the
table is used verbatim.  null means "this witness did not answer".

op "attest"  -- one level of witnesses
--------------------------------------
input: {"roots": {witness: root|null, ...}, "quorum": int (optional)}

  asked     = every witness named in "roots"
  answered  = sorted witnesses whose root is not null
  silent    = sorted witnesses whose root is null
  quorum    = input "quorum" if present, else a MAJORITY OF THOSE ASKED:
              floor(len(asked) / 2) + 1     (3 asked -> 2, 5 asked -> 3)
              [T.quorum.default-scales-with-witnesses kills a constant and
               a majority-of-answerers; T.quorum.default-met-at-five and
               T.agree.one-silent fix the two brackets.]
  verdict   = "UNPROVEN"  if len(answered) < quorum
              "AGREE"     if every answered witness holds one same root
              "DIVERGED"  otherwise
  reference = when verdict is UNPROVEN: null.
              otherwise: the root held by STRICTLY more answered witnesses
              than any other root (a strict plurality; more than half is
              NOT required -- T.diverged.plurality-without-majority).  If
              no root is strictly most-held (three-way split, tie for top)
              the reference is null -- no tie-break of any kind.
  outliers  = sorted answered witnesses whose root != reference; empty
              whenever reference is null (nothing to differ from).
  agreed    = verdict == "AGREE"

op "climb"  -- a tree of levels
-------------------------------
A tree node is either a leaf   {"leaf": name, "root": root|null}
                 or a level    {"level": name, "children": [node, ...]}.

Each level attests (default quorum = majority of ITS children) over what
its children SPEAK UPWARD:
  * a leaf speaks its root (null if it did not answer);
  * a level speaks its reference if its verdict is AGREE, else nothing
    (null) -- DIVERGED and UNPROVEN levels are both silent upward.

Report for a level:
  verdict, reference  as attest over the children's spoken values.  A
                      DIVERGED level still REPORTS its reference while
                      speaking nothing upward.  UNPROVEN -> null.
  speaks_upward       verdict == "AGREE"
  divergences         this level's own dissenters + sum of every child's
                      divergences (so a divergence deep in the tree is
                      still counted at the summit).  Own dissenters:
                        DIVERGED with a reference   -> len(outliers)
                        DIVERGED with no reference  -> len(answered)
                          (every witness that answered into a split is
                           party to it: S.divergences.split-counts-...)
                        AGREE or UNPROVEN           -> 0
  silent_diverged     sorted names of DIRECT children that are levels
                      whose verdict is DIVERGED
  silent_unproven     sorted names of DIRECT children that are either
                      levels whose verdict is UNPROVEN, or leaves whose
                      root is null (a null-rooted leaf is a SILENT
                      witness, not a disagreeing one)
  clean               speaks_upward and divergences == 0
                      (an UNPROVEN summit is never clean; an UNPROVEN
                       child does not by itself make a summit unclean --
                       S.unproven.speaks-silence)

The op's output is the summit level's report.

Root hashing (from the spec "note")
-----------------------------------
  sha256( spec_name
          || for each vector sorted by id:
                 0x00 || id || 0x00 || canonical_json(output) )
  spec_name      = the value of the top-level "spec" field
  canonical_json = json.dumps(obj, sort_keys=True, separators=(',', ':'))
                   encoded as UTF-8, no trailing newline
The script computes the root over ITS OWN outputs (the real check) and,
separately, over the spec's expected values (which isolates whether the
hashing rule itself was understood correctly).
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_PATH = os.path.join(HERE, "CONFORMANCE_SPEC.json")


# ---------------------------------------------------------------- helpers

def canonical(obj):
    """Canonical JSON bytes: sorted keys, no spaces, UTF-8, no newline."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def expand_root(root, table):
    """Map a short root key through the spec's roots table; null stays null."""
    if root is None:
        return None
    return table.get(root, root)


def default_quorum(asked_count):
    """A majority of those asked: floor(n/2) + 1."""
    return asked_count // 2 + 1


# ---------------------------------------------------------------- attest

def attest(roots, quorum=None, table=None):
    table = table or {}
    held = {w: expand_root(r, table) for w, r in roots.items()}
    answered = sorted(w for w, r in held.items() if r is not None)
    silent = sorted(w for w, r in held.items() if r is None)
    q = quorum if quorum is not None else default_quorum(len(held))

    if len(answered) < q or not answered:
        verdict, reference, outliers = "UNPROVEN", None, []
    else:
        tally = {}
        for w in answered:
            tally[held[w]] = tally.get(held[w], 0) + 1
        if len(tally) == 1:
            verdict = "AGREE"
            reference = held[answered[0]]
            outliers = []
        else:
            verdict = "DIVERGED"
            counts = sorted(tally.values(), reverse=True)
            if counts[0] > counts[1]:
                # strict plurality: exactly one root has the top count
                reference = next(r for r, c in tally.items() if c == counts[0])
                outliers = sorted(w for w in answered if held[w] != reference)
            else:
                # tie for most-held: no reference, nothing is an outlier
                reference, outliers = None, []

    return {
        "agreed": verdict == "AGREE",
        "answered": answered,
        "outliers": outliers,
        "reference": reference,
        "silent": silent,
        "verdict": verdict,
    }


# ---------------------------------------------------------------- climb

def climb(node, table):
    """Return an internal record for a node; a level's public report is
    under ["report"]."""
    if "leaf" in node:
        return {
            "name": node["leaf"],
            "kind": "leaf",
            "spoken": expand_root(node.get("root"), table),
            "divergences": 0,
            "verdict": None,
        }

    name = node["level"]
    children = [climb(c, table) for c in node.get("children", [])]

    # attest over what each child speaks upward
    spoken = {c["name"]: c["spoken"] for c in children}
    att = attest(spoken, None, table)

    if att["verdict"] == "DIVERGED":
        if att["reference"] is not None:
            own = len(att["outliers"])
        else:
            own = len(att["answered"])
    else:
        own = 0
    divergences = own + sum(c["divergences"] for c in children)

    silent_diverged = sorted(
        c["name"] for c in children
        if c["kind"] == "level" and c["verdict"] == "DIVERGED"
    )
    silent_unproven = sorted(
        c["name"] for c in children
        if (c["kind"] == "level" and c["verdict"] == "UNPROVEN")
        or (c["kind"] == "leaf" and c["spoken"] is None)
    )

    speaks = att["verdict"] == "AGREE"
    report = {
        "clean": speaks and divergences == 0,
        "divergences": divergences,
        "reference": att["reference"],
        "silent_diverged": silent_diverged,
        "silent_unproven": silent_unproven,
        "speaks_upward": speaks,
        "verdict": att["verdict"],
    }
    return {
        "name": name,
        "kind": "level",
        "spoken": att["reference"] if speaks else None,
        "divergences": divergences,
        "verdict": att["verdict"],
        "report": report,
    }


# ---------------------------------------------------------------- driver

def run_op(inp, table):
    op = inp.get("op")
    if op == "attest":
        return attest(inp["roots"], inp.get("quorum"), table)
    if op == "climb":
        return climb(inp["tree"], table)["report"]
    raise ValueError("unknown op: %r" % (op,))


def compute_root(spec_name, pairs):
    h = hashlib.sha256()
    h.update(spec_name.encode("utf-8"))
    for vid, out in sorted(pairs, key=lambda p: p[0]):
        h.update(b"\x00" + vid.encode("utf-8") + b"\x00" + canonical(out))
    return h.hexdigest()


def main():
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    table = spec.get("roots", {})
    spec_name = spec["spec"]
    published = spec["root"]

    mine, theirs, mismatches = [], [], []
    for v in spec["vectors"]:
        vid = v["id"]
        try:
            out = run_op(v["input"], table)
        except Exception as e:  # report, never hide
            out = {"error": "%s: %s" % (type(e).__name__, e)}
        mine.append((vid, out))
        theirs.append((vid, v["expected"]))
        if canonical(out) == canonical(v["expected"]):
            print("MATCH     %-45s %s" % (vid, canonical(out).decode()))
        else:
            mismatches.append((vid, out, v["expected"]))
            print("MISMATCH  %s" % vid)
            print("   yours:    %s" % canonical(out).decode())
            print("   expected: %s" % canonical(v["expected"]).decode())

    total = len(spec["vectors"])
    matched = total - len(mismatches)
    root_mine = compute_root(spec_name, mine)
    root_theirs = compute_root(spec_name, theirs)

    print()
    print("vectors matching:            %d / %d" % (matched, total))
    print("root over MY outputs:        %s" % root_mine)
    print("root published in spec:      %s" % published)
    print("roots match:                 %s" % (root_mine == published))
    print("root over spec's expecteds:  %s   (hash-rule check: %s)"
          % (root_theirs, "OK" if root_theirs == published else "DIFFERS"))
    return 0 if (root_mine == published and not mismatches) else 1


if __name__ == "__main__":
    sys.exit(main())
