#!/usr/bin/env python3
"""test_a130_peer_review.py -- A130: the reviewer's protocol cannot rot.

WHY. docs/PEER_REVIEW.md hands a stranger a table of claims, each with the thing
that would falsify it and the exact command that would show it. A document like
that is worse than nothing the moment a command in it stops existing: the
reviewer runs it, gets "no such file", and reasonably concludes the rest is
decoration too.

That is not hypothetical. Its own first draft cited `test_a1_fail_closed.py` for
the fail-closed claim. **No such file exists** -- the suite that actually pins it
is `test_f1_fallback_silence.py`, whose D1 reads "an unreachable judge beside a
CLEAN one still fails the gate closed". The wrong name was written and would have
shipped, in the one document whose entire purpose is that claims be checkable.

WHAT IT PINS.
  E*  EXISTS. Every file named in a command in the claims table is really there,
      and every suite named is registered with the runner. A protocol naming a
      suite nobody runs is a promise nobody keeps.
  F*  FALSIFIER. Every claim row states what would kill it. A row with a command
      and no falsifier is an assertion with a number attached, which is the exact
      thing A121 was.
  L*  LINKS. Every internal document link resolves.
  T*  TEETH. A planted bad command is caught.

Pure: reads only; runs no suite, no network, no node.
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "docs", "PEER_REVIEW.md")

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:300]), flush=True)


def claim_rows(text):
    """The rows of the standing-claims table: (id, claim, falsifier, command)."""
    rows = []
    for ln in text.split("\n"):
        if not ln.startswith("| C"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.match(r"^C\d+$", cells[0]):
            rows.append(tuple(cells[:4]))
    return rows


def named_files(command):
    """Files a command line refers to: `python x.py`, `sh y.sh`."""
    return re.findall(r"[\w./-]+\.(?:py|sh)", command)


def main():
    print("A130 -- the reviewer's protocol cannot rot\n")

    if not os.path.isfile(DOC):
        check("A130.0 docs/PEER_REVIEW.md exists", False, DOC)
        print("\nA130: 0/1 passed")
        return 1
    text = io.open(DOC, encoding="utf-8").read()
    rows = claim_rows(text)
    check("A130.0 the claims table parses and has rows", len(rows) >= 5, len(rows))

    # E1 -- every named file is really here.
    missing = []
    for cid, _claim, _fals, cmd in rows:
        for f in named_files(cmd):
            if not os.path.isfile(os.path.join(HERE, f)):
                missing.append((cid, f))
    check("A130.E1 every file named in a claim's command EXISTS. The first draft "
          "of this document named a suite that does not exist, in the one file "
          "whose purpose is that claims be checkable",
          not missing, missing)

    # E2 -- and the suites are actually registered, so a reviewer's run is the
    # same run the project makes of itself.
    try:
        runner = io.open(os.path.join(HERE, "covenant_one.py"),
                         encoding="utf-8").read()
    except OSError:
        runner = ""
    unregistered = []
    for cid, _c, _f, cmd in rows:
        for f in named_files(cmd):
            if f.startswith("test_") and f not in runner:
                unregistered.append((cid, f))
    check("A130.E2 every SUITE named is registered with the runner -- a protocol "
          "naming a suite nobody runs is a promise nobody keeps",
          not unregistered, unregistered)

    # F1 -- a claim with no falsifier is not a claim.
    weak = [(cid, fals) for cid, _c, fals, _cmd in rows
            if len(fals) < 12 or fals.lower() in ("", "-", "n/a", "none")]
    check("A130.F1 every claim states what would FALSIFY it. A row with a command "
          "and no falsifier is an assertion with a number attached",
          not weak, weak)

    # L1 -- internal links resolve.
    dead = []
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#")):
            continue
        base = target.split("#")[0]
        if base and not os.path.isfile(os.path.join(HERE, "docs", base)) \
                and not os.path.isfile(os.path.join(HERE, base)):
            dead.append(target)
    check("A130.L1 every internal link in the protocol resolves", not dead, dead)

    # T1 -- teeth. This suite greps a document, which is the shape A74 found
    # fake in 35 of 36 guards, so it is made to fail on purpose every run.
    planted = text + "\n| C99 | planted | planted falsifier text | `python no_such_suite_a130.py` |\n"
    caught = any(not os.path.isfile(os.path.join(HERE, f))
                 for _c, _cl, _fa, cmd in claim_rows(planted)
                 for f in named_files(cmd))
    check("A130.T1 a planted, non-existent command IS caught, so the green above "
          "is earned rather than a parser that matches nothing", caught)

    ok = sum(1 for r in results if r)
    print("\n  %d claim(s) checked, each with a falsifier and a runnable command."
          % len(rows))
    print("\nA130: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
