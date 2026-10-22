#!/usr/bin/env python3
"""next_anumber.py -- the next free A-number for docs/KNOWN_ISSUES.md. Run this instead of GUESSING one.

Why it exists: on 2026-10-22 this session committed new work as "A376" when A376 and A377 were already the
10-19 highway fixes -- an A-number claimed in flight, exactly the shape [[a-numbers-claimed-in-flight]] warns about.
A guess is not a claim; the record is. `python tools/next_anumber.py` reads the record and prints the next free
number, and test_an1_anumbers.py fails the build on any NEW duplicate primary.

A PRIMARY entry is a header `### A<n>.`; a sub-entry `### A<n><letter>.` (A377b) shares its parent's number and is
not a primary. A few pre-existing duplicate primaries are grandfathered (not re-triaged here, flagged for review).
Stdlib only, public domain.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(HERE, "docs", "KNOWN_ISSUES.md")
# Pre-existing duplicate primaries on the record as of 2026-10-22 (earn-program era, A222-A224). Grandfathered so the
# guard can be green on the current tree; each is a historical collision to resolve or accept, his call -- not new.
GRANDFATHERED = frozenset({222, 223, 224})


def primaries(text):
    """Every A-number used as a PRIMARY header (### A<n>.), in file order, duplicates kept."""
    return [int(m.group(1)) for m in re.finditer(r"^### A(\d+)\.", text, re.M)]


def duplicates(nums):
    seen, dup = set(), set()
    for n in nums:
        dup.add(n) if n in seen else seen.add(n)
    return dup


def highest(text):
    nums = primaries(text)
    return max(nums) if nums else 0


def next_free(text):
    return highest(text) + 1


def ungrandfathered_dups(text):
    return duplicates(primaries(text)) - GRANDFATHERED


def _read(path=None):
    with open(path or RECORD, encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    t = _read()
    print("highest A-number: A%d" % highest(t))
    print("NEXT FREE:        A%d" % next_free(t))
    bad = ungrandfathered_dups(t)
    if bad:
        print("UNGRANDFATHERED DUPLICATE PRIMARIES: %s" % sorted("A%d" % n for n in bad))
        sys.exit(1)
    sys.exit(0)
