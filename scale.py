#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
scale.py -- governance with no top and no bottom.

WHAT WAS FINITE, AND WHY IT MATTERED

  triangulate.py already applies ONE mechanism at several scales -- a file, a
  memory store, a repository -- and that was the right idea. But its scales
  live in a hand-written dict of three. Adding a fourth means editing the file.
  A structure that needs its author to authorise each new level is not a
  structure that scales; it is a structure with a gatekeeper, and the
  gatekeeper is the thing federation exists to remove.

  The missing piece is small: A LEVEL'S VERDICT MUST ITSELF BE USABLE AS A
  WITNESS ONE LEVEL UP. With that, levels compose without limit and without
  new machinery. Three nodes attest to a ledger; three ledgers attest to a
  region; three regions attest to a federation; and the code that judges the
  federation is the code that judged the three nodes, unchanged.

  That is what "the same function at every scale" has to mean if it is to mean
  anything: not a list of scales someone thought of, but a relation that
  composes with itself.

THE ONE INVARIANT THAT MAKES IT TRUSTWORTHY

  **Divergence never disappears as you climb.**

  This is the whole design, and everything else is bookkeeping. The obvious
  implementation is the dangerous one: let a diverged level pass its MAJORITY
  root upward. Do that and disagreement launders itself into agreement with
  every level -- three regions each hiding a dissenting node report perfect
  consensus, and the higher you look the cleaner it appears, which is exactly
  backwards from what you want.

  So a level that DIVERGED contributes SILENCE upward, never a root. Silence
  is a fact triangulate.py already refuses to confuse with agreement: a silent
  witness is not a witness that agreed, and a level with too few answers is
  UNPROVEN rather than clean. Divergence then also travels sideways, in a list
  that accumulates all the way to the top, so a divergence eleven levels down
  is still named in the final report.

  A summit that reports AGREE while something beneath it diverged would be the
  single most dangerous output this system could produce. It cannot: `overall`
  is CLEAN only when the top agreed AND nothing anywhere below it diverged.

WHAT IT DOES NOT DO

  It never resolves a divergence, at any scale. The majority is evidence about
  the outlier and never a decision, and nothing here overwrites anybody --
  which is the property that lets a national branch adopt this without
  adopting anyone's authority. A mechanism that could settle disagreement
  between peers would be the one change that turns federation into
  administration.

  It is PURE. Roots come in as arguments; nothing here reaches a network, a
  disk or a clock. What to hash, and how to fetch it, belongs to the caller --
  which is also what lets a level be a machine, an institution, or a country
  without this file knowing the difference.

USE
  python scale.py            a worked example, including a hidden divergence

LICENCE: Apache-2.0.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from triangulate import AGREE, DIVERGED, UNPROVEN, attest   # noqa: E402

# A level nested deeper than this is far likelier to be a cycle someone built
# by accident than a real hierarchy. Refused loudly rather than recursed into,
# because a verifier that hangs is a verifier that gets switched off.
MAX_DEPTH = 64


def leaf(name: str, root: Optional[str]) -> Dict[str, Any]:
    """A carrier that holds a root directly. None means it did not answer."""
    return {"name": name, "root": root}


def level(name: str, children: List[Dict[str, Any]],
          quorum: Optional[int] = None) -> Dict[str, Any]:
    """A carrier whose root is the verdict of the carriers beneath it.

    QUORUM DEFAULTS TO NOTHING, not to 2. A constant here would silently
    defeat the default attest() derives -- a level with a hundred children
    would call two of them agreement for all hundred -- and it would do so
    from the one place a caller is least likely to look. None means "you
    decide", and attest decides by majority of the carriers asked. A caller
    that knows better still passes its own number and is obeyed.
    """
    return {"name": name, "children": children, "quorum": quorum}



def climb(node: Dict[str, Any], depth: int = 0) -> Tuple[Optional[str], Dict[str, Any]]:
    """Reduce a tree of any depth to (root_for_the_level_above, report).

    Returns None as the root whenever this level cannot honestly speak with one
    voice -- diverged, or too few answers. That None is read one level up as
    SILENCE, which attest already refuses to count as agreement.
    """
    if depth > MAX_DEPTH:
        return None, {"name": node.get("name", "?"), "verdict": UNPROVEN,
                      "why": "nesting deeper than %d levels; refused rather "
                             "than recursed into, because this is far more "
                             "likely to be a cycle than a hierarchy"
                             % MAX_DEPTH,
                      "divergences": [], "children": [], "depth": depth,
                      "reference": None, "silent_diverged": [],
                      "silent_unproven": []}

    if "children" not in node:
        # A leaf's reference is simply what it holds: the same field name for
        # the same thing at every scale, so a reader never has to know whether
        # they are looking at a leaf or a federation to find what it speaks.
        return node.get("root"), {"name": node.get("name", "?"),
                                  "verdict": AGREE if node.get("root") else UNPROVEN,
                                  "why": ("holds a root" if node.get("root")
                                          else "did not answer"),
                                  "divergences": [], "children": [],
                                  "depth": depth, "leaf": True,
                                  "reference": node.get("root"),
                                  "silent_diverged": [],
                                  "silent_unproven": []}

    roots: Dict[str, Optional[str]] = {}
    child_reports = []
    divergences: List[str] = []
    for child in node["children"]:
        root, rep = climb(child, depth + 1)
        roots[rep["name"]] = root
        child_reports.append(rep)
        # Carried sideways, not upward-as-agreement. A divergence found eleven
        # levels down is still named at the summit.
        divergences.extend(rep.get("divergences", []))

    # node.get("quorum") -- never a constant fallback. A level built by hand,
    # without the helper above, must get the same derived majority as one
    # built with it, or the defect just moves to whoever writes a dict.
    v = attest(roots, scale=node.get("name", ""), quorum=node.get("quorum"))

    if v["verdict"] == DIVERGED:
        # ONE ENTRY PER DISSENTING WITNESS, AND EACH ONE NAMED.
        #
        # This was one entry per diverged LEVEL, so `len(divergences)` counted
        # levels. Two dissenters in one ledger and one dissenter in another
        # both totalled the same number, which is the "outvoted into
        # invisibility" failure this file exists to prevent, happening at the
        # tally instead of at the vote. A count of levels answers "where",
        # never "how many", and the second question is the one a reader of a
        # summit report is actually asking.
        #
        # Named, not merely counted, for the same reason attest names its
        # outliers: a number cannot be checked by the party it is about.
        name = node.get("name", "?")

        # PER CAPITA, AND WHY IT IS NOT A THRESHOLD.
        #
        # A raw count across a tree is distorted in both directions. One
        # dissenter out of three is a split; one out of a hundred reads the
        # same in a total. Worse, a raw count REWARDS SIZE: an operator
        # running a hundred nodes generates a hundred times the dissent
        # volume of an operator running one, so the summit tally measures
        # who has more machines rather than who is right. That is an
        # advantage taken from others by being large rather than by being
        # correct, which is the shape of transaction the one condition
        # forbids -- so every dissent is reported WITH the population it
        # occurred in, and levels of different sizes become comparable.
        #
        # WHAT IT MUST NEVER DO. The proportion is never a threshold. There
        # is no fraction below which a dissent stops counting, and 1-of-100
        # leaves this level DIVERGED exactly as 1-of-3 does. Discounting a
        # lone dissenter for being lonely is the "outvoted into invisibility"
        # failure arriving through arithmetic instead of through a vote, and
        # arriving that way makes it harder to see, not more legitimate.
        # This reports the denominator. It never divides by it.
        asked = len(v["answered"]) + len(v["silent"])

        if v["reference"] is None:
            # No strict plurality, so attest names no outliers -- correctly,
            # since there is no reference to be an outlier from. But the level
            # DIVERGED, and a divergence that contributes nothing to the count
            # would vanish as the report climbs, which is the one thing this
            # file forbids. Every witness that answered is party to the split;
            # none of them holds a reference, because there is not one.
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
                    % (name, w, v["majority"]["held_by"],
                       len(v["outliers"]), asked))

    # THE INVARIANT. Only a level that genuinely agreed speaks upward, and what
    # it speaks is THE AGREED ROOT ITSELF, unchanged.
    #
    # Two wrong versions preceded this, both caught by tests rather than by
    # thought, and both wrong the same way -- putting something about the
    # SPEAKER into what is SAID:
    #
    #   1. Keyed by the level's name. Three ledgers all holding the same root
    #      produced three different values, so every region above them
    #      reported DIVERGED. Siblings could never agree about anything.
    #   2. Keyed by nothing but wrapped in a digest per level. Fixed (1), but
    #      made a level's value depend on its HEIGHT: a region three levels
    #      deep and a single ledger beside it could never agree, because one
    #      had been hashed three times and the other once. Structures composed
    #      only if perfectly balanced, which is not composition -- it is a
    #      shape requirement wearing composition's clothes.
    #
    # Passing the agreed root through unchanged makes height irrelevant. A
    # federation whose members are one node, one region and one whole country
    # composes exactly as well as three identical nodes, because all any of
    # them is saying is "the content is this". WHO said it is the tally's job,
    # and attest() already keeps that separately -- which is precisely why it
    # does not belong in the value.
    #
    # DIVERGED and UNPROVEN both speak SILENCE. Either one speaking its root
    # would let the parent read "we could not establish this" as "we
    # established this", a claim stronger than its evidence in the one
    # direction that matters. What a level speaks is now taken from attest's
    # `reference` rather than re-derived by scanning the children, so the root
    # that goes up is the same value the verdict published -- one source, and
    # nothing to drift.
    if v["verdict"] == AGREE:
        up = v["reference"]
    else:
        up = None

    # BUT THE TWO SILENCES ARE NOT THE SAME FACT, and the parent must be able
    # to tell them apart: "my child disagreed internally" and "my child could
    # not establish anything" call for different responses, and merging them
    # loses the difference at exactly the level where someone would act on it.
    # This is the distinction the project already draws between
    # not_understood and infrastructure_failure, drawn here for the same
    # reason. `silent` is kept whole as attest reported it; these two partition
    # it, so no reader has to choose which field to trust.
    silent_diverged = sorted(r["name"] for r in child_reports
                             if roots.get(r["name"]) is None
                             and r["verdict"] == DIVERGED)
    silent_unproven = sorted(r["name"] for r in child_reports
                             if roots.get(r["name"]) is None
                             and r["verdict"] != DIVERGED)

    rep = {
        "name": node.get("name", "?"),
        "verdict": v["verdict"],
        "agreed": v["agreed"],
        "why": v["why"],
        "answered": v["answered"],
        "silent": v["silent"],
        "silent_diverged": silent_diverged,
        "silent_unproven": silent_unproven,
        "outliers": v["outliers"],
        # Which root this level actually speaks upward, in full and stated
        # rather than inferred. A parent -- or a party reading the report --
        # can check the value against its own view instead of trusting that
        # the right one was passed along.
        "reference": v["reference"],
        "divergences": divergences,
        "children": child_reports,
        "depth": depth,
        "speaks_upward": up is not None,
    }
    return up, rep


def overall(report: Dict[str, Any]) -> Tuple[bool, str]:
    """CLEAN only if the top agreed AND nothing beneath it diverged.

    The second half is the point. A summit reporting AGREE over a hidden
    disagreement is the most dangerous output this system could produce, and
    it is the one that any naive implementation produces by default.
    """
    if report.get("divergences"):
        # The number is DISSENTING WITNESSES, not diverged levels. Two
        # dissenters are two, wherever they stand, and a reader who is told
        # "one divergence" when three witnesses dissented has been given the
        # smallest true-sounding number instead of the fact.
        return False, ("NOT CLEAN. The top-level verdict is %s, and %d "
                       "dissenting witness(es) below it are named. A clean "
                       "summit over a hidden disagreement is the one output "
                       "this must never produce."
                       % (report.get("verdict"), len(report["divergences"])))
    if report.get("verdict") != AGREE:
        return False, ("NOT CLEAN. Top-level verdict is %s -- %s"
                       % (report.get("verdict"), report.get("why", "")))
    return True, ("CLEAN. The top agreed and nothing beneath it diverged. "
                  "This says the witnesses match; it does not say they are "
                  "right, and it cannot, because they may all answer to one "
                  "person.")


def render(report: Dict[str, Any], out=print) -> None:
    pad = "  " + "   " * report.get("depth", 0)
    mark = {AGREE: "AGREE   ", DIVERGED: "DIVERGED", UNPROVEN: "UNPROVEN"}.get(
        report.get("verdict"), "?")
    if report.get("leaf"):
        out("%s%-8s %s" % (pad, mark, report["name"]))
        return
    up = "speaks upward" if report.get("speaks_upward") else "SILENT upward"
    out("%s%-8s %-28s %s" % (pad, mark, report["name"], up))
    for c in report.get("children", []):
        render(c, out)


def main() -> int:
    print()
    print("  GOVERNANCE THAT COMPOSES -- one relation, any depth")
    print("  " + "=" * 62)
    print()
    print("  A worked example. Three nodes make a ledger, three ledgers make a")
    print("  region, three regions make a federation -- and every one of those")
    print("  judgements is the SAME function. Region-2 hides a disagreement.")
    print()

    A, B = "a" * 64, "b" * 64

    def ledger(n, roots):
        return level("ledger-%s" % n, [leaf("node-%d" % i, r)
                                       for i, r in enumerate(roots)])

    region1 = level("region-1", [ledger("1a", [A, A, A]),
                                 ledger("1b", [A, A, A]),
                                 ledger("1c", [A, A, None])])
    # One node in one ledger of this region holds something else. Everything
    # above it will refuse to call itself clean.
    region2 = level("region-2", [ledger("2a", [A, A, A]),
                                 ledger("2b", [A, B, A]),
                                 ledger("2c", [A, A, A])])
    region3 = level("region-3", [ledger("3a", [A, A, A]),
                                 ledger("3b", [A, A, A]),
                                 ledger("3c", [A, A, A])])
    federation = level("federation", [region1, region2, region3])

    _, report = climb(federation)
    render(report)

    ok, why = overall(report)
    print()
    print("  " + "-" * 62)
    print("  %s" % why)
    if report["divergences"]:
        print()
        print("  Named, however far down they were:")
        for d in report["divergences"]:
            print("    - %s" % d)
    print()
    print("  Note what did NOT happen: ledger-2b diverged, so it went SILENT")
    print("  upward rather than passing its majority root along. Had it passed")
    print("  the majority, region-2 would have agreed, the federation would")
    print("  have agreed, and the disagreement would have vanished at exactly")
    print("  the scale where someone would have acted on it.")
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
