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


REGISTRY = os.path.join(HERE, "docs", "ANUMBER_GAPS.json")


def gaps(text, through):
    """A-numbers 1..THROUGH with no primary header (A477). Sub-entries (A84b) do not fill a gap."""
    have = set(primaries(text))
    return {n for n in range(1, int(through) + 1) if n not in have}


def load_registry(path=None):
    """docs/ANUMBER_GAPS.json, or None when it is absent or unreadable."""
    import json
    try:
        with open(path or REGISTRY, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def registry_problems(text, reg):
    """Every way the record disagrees with the gap registry (A477). Empty means they agree."""
    if not isinstance(reg, dict) or "checked_through" not in reg:
        return ["no gap registry (docs/ANUMBER_GAPS.json) to check the record against"]
    out = []
    listed = {int(k[1:]) for k in (reg.get("gaps") or {})}
    real = gaps(text, reg["checked_through"])
    for n in sorted(real - listed):
        out.append("A%d has no entry and is not a listed gap (an entry lost, or a number skipped)" % n)
    for n in sorted(listed - real):
        out.append("A%d is listed as a gap but now has an entry (trim the registry)" % n)
    heads = re.findall(r"^### A\d+\..*$", text, re.M)
    for key, copies in sorted((reg.get("duplicates") or {}).items()):
        for c in copies:
            if not any(h.startswith(c.get("header_starts", "\0")) for h in heads):
                out.append("%s: the copy headed %r is gone" % (key, c.get("header_starts", "")[:60]))
    return out


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
