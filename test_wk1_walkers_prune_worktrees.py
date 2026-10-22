#!/usr/bin/env python3
"""WK1 -- the class guard the record kept asking for: a tree-walker must prune .claude/worktrees.

A267 (memory walkers-prune-worktrees): SIX times a repo walker absorbed the full second checkout under
.claude/worktrees/ and read it as the tree -- covenant_seal's manifest grew 45x (24,638 of 25,859 entries
were worktree copies), R1 read 2,438 files and flagged 33 "violations" that were the record itself, C4 and
others the same shape. Each break was fixed in its own walker; no single guard watched the CLASS. This is it.

Every tree-walker rolls its OWN os.walk with its own skip set -- there is no shared primitive to test once
(confirmed 2026-10-22). So this is a RATCHET over the walkers' real enumerators: it RUNS each one against the
real tree (where .claude/worktrees/ holds many full repo copies right now) and asserts it yields NOTHING under
.claude -- not by reading the walker's source (that would be the exact "checked the text, not the behaviour"
fake this project retracts), but by driving the walker and inspecting what it actually returns. If a walker
ever drops ".claude" from its skip set, its count balloons into the thousands and .claude/worktrees paths
appear -- and this turns red.

Covered here: verify_bundle.shipped() and covenant_seal.walk() -- the two that had the catastrophic blowups and
are NOT otherwise self-tested for it (R1 and C4 already self-test their own worktree pruning: r1 A236, c4 C4.5).
Extensible: a284/a289/a92/g7/p18 expose importable enumerators too (f5's A2b walk is inline in main(), worth
refactoring to a scan_arming(root) helper first) -- add them here as they are factored.

    python test_wk1_walkers_prune_worktrees.py
LICENCE: public domain.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# A walk that forgot to prune would read every worktree copy -- tens of thousands of files. A real tree walk
# yields hundreds. These bounds are loose enough for ordinary tree growth and tight enough to catch the blowup.
MIN_FILES = 100
MAX_FILES = 5000

checks = []


def ok(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


def under_claude(rel):
    rel = str(rel).replace("\\", "/")
    return rel == ".claude" or rel.startswith(".claude/")


def _run_walker(name, paths_iter):
    """paths_iter: an iterable of repo-relative path strings the walker actually enumerated."""
    paths = [str(p).replace("\\", "/") for p in paths_iter]
    claude = sorted(p for p in paths if under_claude(p))
    ok("%s prunes .claude (0 paths under it)" % name, not claude,
       "%d leaked, first: %s" % (len(claude), claude[:3]))
    ok("%s walked the tree, not the worktrees (%d <= files <= %d)" % (name, MIN_FILES, MAX_FILES),
       MIN_FILES <= len(paths) <= MAX_FILES, "enumerated %d files" % len(paths))
    return len(paths)


# --- verify_bundle.shipped(): yields repo-relative strings; SKIP_DIR drops .claude by name ---------------
try:
    import verify_bundle
    _run_walker("verify_bundle.shipped", verify_bundle.shipped())
except Exception as e:                                           # noqa: BLE001
    ok("verify_bundle.shipped runs", False, "%s: %s" % (type(e).__name__, str(e)[:160]))

# --- covenant_seal.walk(): yields (rel, full) tuples; EXCLUDE_DIRS drops .claude by name + git-ignore -----
try:
    import covenant_seal
    _run_walker("covenant_seal.walk", (rel for rel, _full in covenant_seal.walk()))
except Exception as e:                                           # noqa: BLE001
    ok("covenant_seal.walk runs", False, "%s: %s" % (type(e).__name__, str(e)[:160]))

# ------------------------------------------------------------------------------------- tally
passed = sum(1 for _n, c, _d in checks if c)
total = len(checks)
for name, c, detail in checks:
    if not c:
        print("  FAIL %s -- %s" % (name, detail))
print("WK1 %d/%d passed" % (passed, total))
sys.exit(0 if passed == total else 1)
