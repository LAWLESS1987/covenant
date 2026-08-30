#!/usr/bin/env python3
"""
redundancy.py -- at every scale, how many can be cut away before it stops?

THE QUESTION THIS ANSWERS

  "Ensure operation even if sections fail or disconnect, similar to an old tree
  getting cut down." A tree survives losing a limb and does not survive losing
  its trunk, and the difference is not size -- it is how many other things were
  carrying the same load.

  So the question is not "is it backed up". It is, at each level: HOW MANY
  INDEPENDENT COPIES CARRY THIS, and what happens at the first loss?

THE SHAPE, and why it is the same shape at every level

  One witness cannot be checked. Two witnesses can disagree and cannot settle
  it -- a tie tells you something is wrong and never which one. Three is the
  smallest number that can lose one and still have a majority, and the smallest
  that can adjudicate rather than merely detect. That is why triangulate.py
  takes three, and it is not a fact about ledgers: it is a fact about counting,
  so it holds identically for hashes, files, machines and people.

  This file therefore asks ONE question at EVERY scale, rather than a different
  question per scale:

      N independent carriers. Survives one loss?  Survives two?

  Growth adds scales, not mechanisms -- the rule triangulate.py already states.
  A new level does not need new code here; it needs a new row.

WHAT IT DOES NOT DO

  It changes nothing, starts nothing, stops nothing and sends nothing. It
  reads. Every number it reports is measured on this machine now, or it is
  reported as UNKNOWN -- never estimated, because a redundancy figure that was
  guessed is worse than no figure at all: it is a reason not to check.

THE CLAUSE THAT BOUNDS IT

  "Survive at all cost, as long as mutual benefit is preserved." The second
  half is not decoration. Redundancy can always be bought by breaking the
  principle -- publish the private corpus to a hundred mirrors and it becomes
  extremely durable, and the people named in it never consented. So this file
  also checks that no copy carries what may not be copied. A system that
  survived by breaking its own rule did not survive; something else did,
  wearing its name.

USE
  python redundancy.py

LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")

UNKNOWN = None


def _exists(*parts) -> bool:
    return os.path.exists(os.path.join(*parts))


def _run(cmd, timeout=10):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=HERE)
        return (p.stdout or "") + (p.stderr or "")
    except Exception:                                        # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# Each level answers the SAME question. Only the carriers differ.
# ---------------------------------------------------------------------------

def level_check():
    """L0 -- the check itself. Independent implementations of one verdict."""
    impls, detail = [], []
    for fn, what in (("constitution.py", "Python, any platform"),
                     ("verify.sh", "sh + awk + sha256, any Unix"),
                     ("verify.ps1", "PowerShell, any Windows")):
        if _exists(HERE, fn):
            impls.append(fn)
            detail.append("%s (%s)" % (fn, what))
    return len(impls), detail, (
        "Three languages sharing no code. They have already disagreed once, on "
        "one block of three, and the disagreement was the finding -- which is "
        "the entire argument for more than one.")


def level_record():
    """L1 -- the private record. Independent copies of the memory store."""
    carriers, detail = [], []
    for path, what in (
            (os.path.join(HOME, "ai_memory"), "working copy"),
            (os.path.join(HOME, "ai_memory_backups"), "second folder, same disk"),
            (os.path.join(HOME, "OneDrive", "covenant-memory-backup"),
             "cloud, off this machine")):
        if os.path.isdir(path):
            carriers.append(path)
            detail.append("%s -- %s" % (what, path.replace(HOME, "~")))
    git = os.path.join(HOME, "ai_memory", ".git")
    if os.path.isdir(git):
        carriers.append(git)
        detail.append("local git history (never pushed) -- ~/ai_memory/.git")
    return len(carriers), detail, (
        "Two of these sit on one disk, so they fall together. Only the cloud "
        "copy and the git history survive that disk, and the git history is on "
        "it. Count carriers, then count the things they SHARE -- redundancy "
        "that shares a failure is one carrier wearing several names.")


def level_witness():
    """L2 -- the public record. Independent witnesses to the same root."""
    carriers, detail = [], []
    if os.path.isdir(os.path.join(HERE, ".git")):
        carriers.append("pc")
        detail.append("this working tree")
    remotes = _run(["git", "remote", "-v"])
    for host in set(re.findall(r"@([\w.-]+)[:/]|https://([\w.-]+)/", remotes)):
        h = host[0] or host[1]
        if h:
            carriers.append(h)
            detail.append("remote: %s" % h)
    anchors = os.path.join(HERE, "docs", "SUCCESSION_ANCHORS.md")
    if os.path.isfile(anchors):
        carriers.append("anchors")
        detail.append("published state roots -- docs/SUCCESSION_ANCHORS.md")
    return len(set(carriers)), detail, (
        "triangulate.py already reports agreement between these and refuses to "
        "call silence agreement. The honest limit stays: one person controls "
        "all of them, so they are copies rather than witnesses. Independent "
        "STORAGE is not independent JUDGEMENT.")


def level_node():
    """L3 -- the running chain. Nodes that can each serve the ledger."""
    up, detail = [], []
    for port in (5000, 5020, 5040, 5060):
        s = socket.socket()
        s.settimeout(0.4)
        try:
            s.connect(("127.0.0.1", port))
            up.append(port)
            detail.append("node listening on %d" % port)
        except OSError:
            pass
        finally:
            s.close()
    return len(up), detail, (
        "All on ONE machine, in one console group -- covenant_prod.bat starts "
        "them together, so one window close takes every one of them. Measured "
        "on 2026-08-29, when exactly that happened and took the watchdog with "
        "them. Four carriers, one failure. That is a redundancy of 1.")


def level_supervisor():
    """L4 -- what restarts what. Follow the chain up and see where it ends."""
    chain, detail = [], []
    for fn, what in (("covenant_watchdog.py", "revives dead NODES"),
                     ("covenant_watchdog_guard.py", "revives the WATCHDOG")):
        if _exists(HERE, fn):
            chain.append(fn)
            detail.append("%s -- %s" % (fn, what))
    detail.append("and above the guard: NOTHING on this machine")
    return len(chain), detail, (
        "A supervision chain is only as deep as its top link is reliable, "
        "because the top link has nothing above it by definition. Depth 2 here "
        "means the guard is a single point of failure -- not a criticism of "
        "the guard, a property of being last. The fix is not a third "
        "supervisor (that regresses forever); it is an OS-level service, which "
        "is a different kind of thing and does not die with a console.")


def level_operator():
    """L5 -- the people. The level no code can fix."""
    detail = ["every node, every key and every remote answers to one person"]
    peers = os.path.join(HERE, "peers.txt")
    n = 1
    if os.path.isfile(peers):
        try:
            with open(peers, "r", encoding="utf-8", errors="ignore") as fh:
                listed = [l.strip() for l in fh
                          if l.strip() and not l.startswith("#")]
            if listed:
                detail.append("peers.txt lists %d endpoint(s) -- but listing an "
                              "endpoint is not an independent operator" % len(listed))
        except OSError:
            pass
    return n, detail, (
        "THE LARGEST GAP, and it is not a software problem. Quorum among "
        "machines one party controls is theatre; CONSTITUTION.md section V "
        "says so and this measurement is why. Redundancy 1 at this level caps "
        "the whole structure, because every level above it inherits a single "
        "point of failure that no amount of copying below can remove.")


LEVELS = [
    ("L0", "the check", level_check),
    ("L1", "the record", level_record),
    ("L2", "the witnesses", level_witness),
    ("L3", "the nodes", level_node),
    ("L4", "the supervisors", level_supervisor),
    ("L5", "the operators", level_operator),
]


# ---------------------------------------------------------------------------
# The bound: survival must not be bought by breaking the principle.
# ---------------------------------------------------------------------------

# PRECISE, and the imprecise version is why. The first draft matched the
# substring "ai_memory" against tracked paths and reported twelve VIOLATIONS,
# every one of them a file under ai_memory_system/ -- which is the SOFTWARE,
# public on purpose, and not the private store at ~/ai_memory at all. A check
# that flags twelve innocent files to catch nothing is not cautious, it is
# broken: nobody reads the thirteenth line of a boy-who-cried-wolf report.
#
# So: whole path SEGMENTS, never substrings, and the exact filenames that
# carry the corpus and the keys.
FORBIDDEN_SEGMENTS = ("ai_memory", ".covenant-keys", "ai_memory_backups",
                      "covenant-memory-backup")
FORBIDDEN_NAMES = ("audit.jsonl", "guard_state.json")


def principle_check():
    """Is any redundancy mechanism carrying what may not be copied?

    "Survive at all cost, as long as mutual benefit is preserved." Redundancy
    can always be bought by breaking the rule: mirror the private corpus
    everywhere and it becomes very durable, and nobody named in it agreed to
    that. A system that survived that way did not survive; something else did,
    wearing its name.
    """
    findings = []
    tracked = _run(["git", "ls-files"])
    for line in tracked.splitlines():
        path = line.strip()
        if not path:
            continue
        segments = re.split(r"[\\/]", path)
        base = segments[-1] if segments else ""
        if any(s in FORBIDDEN_SEGMENTS for s in segments[:-1]):
            findings.append("git tracks %r -- it sits inside a private "
                            "directory that must never be published" % path)
        elif base in FORBIDDEN_NAMES:
            findings.append("git tracks %r -- that file carries the record "
                            "itself, not code about it" % path)
    gitignore = os.path.join(HERE, ".gitignore")
    ign = ""
    if os.path.isfile(gitignore):
        try:
            with open(gitignore, "r", encoding="utf-8", errors="ignore") as fh:
                ign = fh.read()
        except OSError:
            ign = ""
    return findings, ign


def main() -> int:
    print()
    print("  REDUNDANCY AT EVERY SCALE -- read-only, changes nothing")
    print("  " + "=" * 66)
    print()
    print("  One question, asked identically at each level:")
    print("  how many independent carriers, and what survives the first loss?")
    print()

    weakest = None
    rows = []
    for tag, name, fn in LEVELS:
        try:
            n, detail, note = fn()
        except Exception as e:                               # noqa: BLE001
            print("  %s %-16s UNKNOWN -- %s: %s" % (tag, name, type(e).__name__, e))
            print("     Not counted as redundant. An unmeasured level is not a")
            print("     safe one.")
            print()
            continue
        rows.append((tag, name, n))
        if weakest is None or n < weakest[2]:
            weakest = (tag, name, n)
        if n >= 3:
            verdict = "survives one loss, and can adjudicate"
        elif n == 2:
            verdict = "survives one loss, CANNOT settle a disagreement"
        elif n == 1:
            verdict = "SINGLE POINT OF FAILURE"
        else:
            verdict = "NOTHING CARRIES THIS"
        print("  %s  %-16s N=%d   %s" % (tag, name, n, verdict))
        for d in detail:
            print("        - %s" % d)
        print("        %s" % note.replace("\n", "\n        "))
        print()

    print("  " + "-" * 66)
    findings, ign = principle_check()
    print("  THE BOUND: survival must not be bought by breaking the rule")
    if findings:
        for f in findings:
            print("     VIOLATION  %s" % f)
        print("     Redundancy obtained this way is not survival. Stop and fix")
        print("     this before adding another copy of anything.")
    else:
        print("     No tracked file carries the private corpus, the audit chain")
        print("     or the keys. Durability has not been bought with consent")
        print("     that was never given.")
        if "ai_memory" not in ign:
            print("     NOTE: .gitignore does not name ai_memory. Nothing is")
            print("     tracked today, which is what matters, but the guard is")
            print("     habit rather than mechanism.")
    print()
    print("  " + "-" * 66)
    if weakest:
        print("  The structure is capped by its weakest level: %s (%s), N=%d."
              % (weakest[0], weakest[1], weakest[2]))
        if weakest[2] <= 1:
            print("  Every level above it inherits that single point of failure.")
            print("  Adding copies BELOW a level with N=1 does not raise the")
            print("  floor -- it only makes the drop look further away.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
