#!/usr/bin/env python3
"""AN1 -- the A-number guard (2026-10-22). The record gives each work item an A-number; a session must claim the
NEXT FREE one, not guess. On 2026-10-22 this session first committed new work as "A376", colliding with the 10-19
highway fixes (A376/A377) -- a claim in flight. This guard reads docs/KNOWN_ISSUES.md and fails on any NEW duplicate
primary A-number; a few pre-existing duplicates are grandfathered, a new collision is not. Driven both ways.

Run: python test_an1_anumbers.py   (public domain)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tools import next_anumber as AN  # noqa: E402

n_fail = 0


def check(name, ok, detail=""):
    global n_fail
    print(("ok   " if ok else "FAIL ") + name + (("  -- %s" % (detail,)) if detail else ""))
    if not ok:
        n_fail += 1


real = AN._read()

# AN1.1: the real record has NO duplicate primary A-number beyond the grandfathered set.
bad = AN.ungrandfathered_dups(real)
check("AN1.1 the record has no un-grandfathered duplicate primary A-number", bad == set(), sorted(bad))

# AN1.2: the grandfathered set is honest -- every number in it is actually a duplicate on the record right now
# (so the allowlist cannot silently grandfather a number that is unique or absent; trim it when one is resolved).
real_dups = AN.duplicates(AN.primaries(real))
check("AN1.2 every grandfathered number is still a real duplicate (allowlist not stale)",
      AN.GRANDFATHERED <= real_dups, sorted(AN.GRANDFATHERED - real_dups))

# AN1.3 both ways: a NEW duplicate primary is caught.
planted = real + "\n### A99901.\n- body\n\n### A99901.\n- body again (a collision)\n"
check("AN1.3 a planted duplicate primary is flagged", 99901 in AN.ungrandfathered_dups(planted), "planted A99901 twice")

# AN1.3b the other way: one of that pair alone is clean.
one = real + "\n### A99901.\n- body\n"
check("AN1.3b a single new primary is NOT flagged", 99901 not in AN.ungrandfathered_dups(one))

# AN1.4: next_free is highest + 1, and strictly above every primary on the record (so a session claims unused ground).
nums = AN.primaries(real)
nf = AN.next_free(real)
check("AN1.4 next_free == highest + 1 and exceeds every primary", nf == AN.highest(real) + 1 and all(nf > n for n in nums),
      "next=A%d highest=A%d" % (nf, AN.highest(real)))

# AN1.5: a sub-entry (A<n><letter>.) does NOT count as a primary, so it never reads as a duplicate of its parent.
sub = "### A500.\n- parent\n\n### A500b.\n- a sub-entry, not a duplicate\n"
check("AN1.5 a lettered sub-entry is not a duplicate of its parent", AN.duplicates(AN.primaries(sub)) == set(),
      AN.primaries(sub))

print("\nAN1: %d checks, %d failed" % (5 + (1 if True else 0), n_fail))
sys.exit(1 if n_fail else 0)
