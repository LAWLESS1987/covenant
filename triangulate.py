#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""triangulate.py -- three witnesses, one truth, and nobody deciding it alone.

THE SHAPE. The same state lives in three places that fail independently:

    PC       the working disk -- the deployment, and the only place that
             runs anything
    GITHUB   the published history -- durable, dated, visible to others
    CLOUD    the shared surface -- reachable by systems that cannot see
             either of the other two

Each can produce a ROOT: one hash standing for everything it holds. Agreement
is then a fact anyone can check, and divergence names WHICH witness is the
odd one out rather than declaring a winner.

THE SAME MECHANISM AT EVERY SCALE, which is the point. A root is a root:

    micro    one memory        sha256 of its bytes
    small    one memory store  the merkle root over its files
    mid      the repository    covenant_seal's merkle root
    macro    the chain         the block hash

attest() does not know or care which of those it was handed. Growth adds
scales; it does not add mechanisms, and a system whose integrity check has to
be reinvented every time it grows is a system that will eventually grow past
its check.

WHAT THIS HONESTLY PROVIDES -- and the line matters more than the feature.

It detects DIVERGENCE: corruption, a half-finished sync, a silent overwrite,
one system compromised, a push that did not land. Two witnesses agreeing
against a third is strong evidence about the third, and that is worth having.

IT IS NOT BYZANTINE CONSENSUS, and calling it that would be a lie with a
security label on it. Consensus among mutually distrusting parties requires
parties that actually distrust each other. Here one person holds all three
accounts: the PC, the GitHub repo and the cloud project answer to one
operator, who can change all three -- and today, in this very repository, a
force-push rewrote the entire published history in one command. Three
witnesses under one hand are three copies, not three opinions.

So: 2-of-3 catches ACCIDENT and SINGLE-POINT COMPROMISE. It does not stop a
determined owner, and it must never be described as if it does. What makes
the guarantee real is independence, and independence here is partial: it
grows the moment a witness is held by someone else, and the mechanism does
not change when that happens -- only the strength of what it proves.

Usage:
    python triangulate.py                 report every scale it can reach
    python triangulate.py --scale repo    just one
    python triangulate.py --json          machine-readable
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__)) or "."

AGREE = "AGREE"
DIVERGED = "DIVERGED"
UNPROVEN = "UNPROVEN"


# --------------------------------------------------------------- the core --
def attest(roots: Dict[str, Optional[str]], scale: str = "",
           quorum: Optional[int] = None) -> Dict[str, Any]:
    """The whole judgement, pure. `roots` maps witness -> root, or None for a
    witness that could not be reached.

    A WITNESS THAT DID NOT ANSWER IS NOT A WITNESS THAT DISAGREED. They are
    different facts and collapsing them is how a check starts lying: an
    unreachable cloud would otherwise read as two-against-one agreement and
    report a clean bill of health for a system nobody actually checked.
    """
    present = {k: v for k, v in roots.items() if v}
    silent = sorted(k for k, v in roots.items() if not v)

    # THE DEFAULT QUORUM IS A MAJORITY OF THE WITNESSES ASKED -- not a
    # constant, and deliberately not a majority of those who ANSWERED.
    #
    # The constant 2 was the defect. It does not grow with the question: put a
    # hundred witnesses to this function and two of them agreeing establishes
    # agreement for all hundred, which is a claim far stronger than its
    # evidence and a ready-made route for a small colluding subset to speak
    # for everyone.
    #
    # "A majority of those PRESENT" is the worse repair, and it is worth
    # naming because it is the one that looks reasonable: it means SILENCING
    # WITNESSES MAKES AGREEMENT EASIER. Knock enough witnesses offline and the
    # survivors clear a smaller bar. A mechanism in which one party gains by
    # suppressing others is exactly the transaction this project exists to
    # refuse.
    #
    # So the bar is set by the question asked, and silence can only ever make
    # a verdict harder to reach. An explicitly passed quorum is honoured
    # unchanged: a caller who knows its own topology outranks a default. At
    # the three-witness scale this file was written for, this is still 2.
    if quorum is None:
        # A FLOOR OF TWO, and it is derived rather than chosen. The pure
        # majority rule gives a majority of one witness = one, so a lone
        # witness would AGREE with itself -- a verdict with nothing behind
        # it, and a claim stronger than its evidence. This project already
        # says so in its own words, in test_v1's N1: "One implementation
        # agreeing with itself is not agreement." A caller relying on that
        # AGREE is harmed for the benefit of whoever produced it, which is
        # the shape of transaction the one condition forbids.
        #
        # Nothing else moves: max(2, n//2+1) is 2 at n=2 and n=3, and 3 at
        # n=5, so the majority-of-asked rule still binds everywhere it was
        # the larger number.
        quorum = max(2, len(roots) // 2 + 1)

    tally: Dict[str, List[str]] = {}
    for who, root in present.items():
        tally.setdefault(root, []).append(who)
    for holders in tally.values():
        holders.sort()

    ranked = sorted(tally.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    # A ROOT IS THE REFERENCE ONLY IF IT HAS A STRICT PLURALITY -- strictly
    # more holders than any other root.
    #
    # This code used to take ranked[0] unconditionally, which on {x:A, y:B,
    # z:C} made x's root the reference and reported y and z as outliers. That
    # is a winner declared by nothing but the alphabet, and the vector pinning
    # this case says in its own words that the function "declares no winner by
    # luck of ordering". The comment was right and the code was not.
    #
    # On a tie for top there is therefore NO reference, and no tie-break is
    # invented here: choosing between equally-held roots is a decision, and
    # this function reports evidence and decides nothing. With no reference
    # `outliers` is EMPTY -- an outlier is a witness that differs FROM THE
    # REFERENCE, and where there is no reference the word names nothing.
    #
    # A quorum that was not met is likewise no reference: under UNPROVEN
    # nothing was compared, so there is nothing for a witness to differ from.
    quorum_met = len(present) >= quorum
    reference: Optional[str] = None
    if quorum_met and ranked and (len(ranked) == 1
                                  or len(ranked[0][1]) > len(ranked[1][1])):
        reference = ranked[0][0]
    held_by = tally[reference] if reference else []
    outliers = (sorted(w for r, hs in tally.items() if r != reference
                       for w in hs) if reference else [])

    if len(present) < quorum:
        verdict, agreed = UNPROVEN, False
        why = (f"only {len(present)} witness(es) answered and {quorum} are "
               f"required. Silent: {silent or 'none'}. This is NOT agreement "
               f"-- nothing has been compared.")
    elif len(tally) == 1:
        verdict, agreed = AGREE, True
        why = (f"all {len(present)} answering witnesses hold the same root"
               + (f"; {silent} did not answer, so this agreement covers "
                  f"{sorted(present)} only" if silent else ""))
    elif reference is None:
        verdict, agreed = DIVERGED, False
        why = (f"{len(tally)} different roots and no strict plurality among "
               f"them, so NO root is the reference and nothing here is an "
               f"outlier -- a witness can only be an outlier against a "
               f"reference. Breaking the tie would be a decision, and nothing "
               f"here decides or overwrites anybody.")
    else:
        verdict, agreed = DIVERGED, False
        why = (f"{len(tally)} different roots. {held_by} hold "
               f"{str(reference)[:12]}...; {outliers} differ. The majority is "
               f"EVIDENCE about the outlier, not a decision -- nothing here "
               f"overwrites anybody.")

    return {
        "scale": scale, "verdict": verdict, "agreed": agreed,
        "quorum": quorum, "answered": sorted(present), "silent": silent,
        "roots": {k: (v[:16] if v else None) for k, v in roots.items()},
        "majority": {"root": (reference[:16] if reference else None),
                     "held_by": held_by},
        # THE REFERENCE, STATED OUTRIGHT AND IN FULL. Every other root in this
        # report is truncated for reading; this one is not, because it is the
        # only field meant to be COMPARED rather than read. A party handed a
        # verdict must be able to check it against its own view instead of
        # trusting the verdict's word for it, and 16 characters cannot be
        # checked against anything.
        #
        # It also closes a gap nothing else covers: which root an agreeing
        # level speaks upward was never stated anywhere, so an implementation
        # that returned a hardcoded constant upward would have passed every
        # test in this repository.
        "reference": reference,
        "outliers": outliers,
        "why": why,
        "limits": ("detects divergence, corruption and single-point "
                   "compromise. NOT byzantine consensus: these three "
                   "witnesses answer to one operator, so this catches "
                   "accident, not a determined owner."),
    }


# ------------------------------------------------------------- witnesses --
def pc_root_repo() -> Optional[str]:
    """The working tree, through the seal's own merkle tree."""
    try:
        sys.path.insert(0, HERE)
        import covenant_seal as cs
        return cs.merkle_root(cs.build_manifest())
    except Exception:                                          # noqa: BLE001
        return None


def current_branch() -> Optional[str]:
    try:
        out = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                             cwd=HERE, capture_output=True, text=True,
                             timeout=30)
        b = out.stdout.strip()
        return b if out.returncode == 0 and b and b != "HEAD" else None
    except (OSError, subprocess.SubprocessError):
        return None


def github_root_repo() -> Optional[str]:
    """What the remote has ON THIS BRANCH. The COMMIT is GitHub's root: a
    hash over the whole tree, the same idea one layer down.

    THE BRANCH MATTERS, and getting it wrong makes this check useless. The
    first version asked for `ls-remote origin HEAD`, which resolves to the
    remote's DEFAULT branch -- so working on dev compared dev-local against
    main-remote and reported DIVERGED every single time. A check that cries
    wolf on a healthy system is worse than no check: it trains its reader to
    ignore it, and it will be ignored on the day it is right.
    """
    br = current_branch()
    if not br:
        return None
    try:
        out = subprocess.run(["git", "ls-remote", "origin", br],
                             cwd=HERE, capture_output=True, text=True,
                             timeout=60)
        if out.returncode != 0:
            return None
        parts = out.stdout.split()
        return parts[0] if parts else None
    except (OSError, subprocess.SubprocessError):
        return None


def pc_head() -> Optional[str]:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE,
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def cloud_root(url: str = "", token: str = "") -> Optional[str]:
    """The cloud surface's own view. Absent config is SILENT, never a
    disagreement -- see attest()."""
    url = url or os.environ.get("AI_MEMORY_URL", "")
    token = token or os.environ.get("AI_MEMORY_TOKEN", "")
    if not url:
        return None
    try:
        req = urllib.request.Request(url.rstrip("/") + "/mycelium")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        fp = data.get("fingerprint") or {}
        return fp.get("weighted") or fp.get("topology")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def memory_root(root_dir: str = "") -> Optional[str]:
    """The memory store, hashed the same way at its own scale."""
    root_dir = root_dir or os.environ.get(
        "AI_MEMORY_ROOT", os.path.join(os.path.expanduser("~"), "ai_memory"))
    if not os.path.isdir(root_dir):
        return None
    h = hashlib.sha256()
    for fn in sorted(os.listdir(root_dir)):
        if not fn.endswith(".md") or fn.startswith("."):
            continue
        p = os.path.join(root_dir, fn)
        try:
            with open(p, "rb") as fh:
                h.update(fn.encode() + b"\x00"
                         + hashlib.sha256(fh.read()).digest())
        except OSError:
            continue
    return h.hexdigest()


def file_root(path: str) -> Optional[str]:
    """The micro scale. Identical mechanism, one file."""
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


# ----------------------------------------------------------------- scales --
def scale_repo() -> Dict[str, Any]:
    """PC tree vs GitHub. Deliberately compares COMMITS, not the merkle root:
    GitHub does not compute our tree hash, and inventing a comparison the
    remote cannot actually make would be a check that only ever passes."""
    br = current_branch() or "?"
    return attest({"pc": pc_head(), "github": github_root_repo()},
                  scale=f"repo({br})", quorum=2)


def scale_memory() -> Dict[str, Any]:
    return attest({"pc": memory_root(), "cloud": cloud_root()},
                  scale="memory-store", quorum=2)


def scale_seal() -> Dict[str, Any]:
    """The working tree against the root last published in SEAL_MERKLE.txt --
    the PC as its own second witness, across TIME rather than across
    machines. Same mechanism; the independence is temporal."""
    published = None
    try:
        with open(os.path.join(HERE, "SEAL_MERKLE.txt"),
                  encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("merkle_root"):
                    published = line.split()[1]
                    break
    except OSError:
        pass
    return attest({"pc-now": pc_root_repo(), "sealed-then": published},
                  scale="seal(merkle)", quorum=2)


SCALES = {"repo": scale_repo, "memory": scale_memory, "seal": scale_seal}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scale", choices=sorted(SCALES), default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    names = [a.scale] if a.scale else sorted(SCALES)
    reports = [SCALES[n]() for n in names]

    if a.json:
        print(json.dumps(reports, indent=1))
    else:
        for r in reports:
            print(f"\n  {r['scale']:16s} {r['verdict']}")
            for who, root in r["roots"].items():
                mark = "  " if root else "??"
                print(f"    {mark} {who:12s} {root or '(silent)'}")
            print(f"    {r['why']}")
        print(f"\n  {reports[0]['limits']}\n")

    # UNPROVEN is not success. A check that exits 0 when it could not check
    # teaches its caller that silence is health, which is the failure this
    # whole repository keeps finding in itself.
    return 0 if all(r["agreed"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
