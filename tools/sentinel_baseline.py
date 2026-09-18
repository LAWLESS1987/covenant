#!/usr/bin/env python3
"""sentinel_baseline.py -- the Sentinel-Witness baseline, in checkable form.

Step 1 of the operator's order of work, 2026-09-18: "first freeze the current
baseline." docs/SENTINEL_BASELINE.md is the readable record; this is the one a
machine can disagree with.

WHY A TOOL AND NOT JUST THE DOCUMENT. A table of hashes in a markdown file is a
DESCRIPTION of the bytes (rule 1). Nothing checks it, so six edits later it is
prose about a tree that has moved. This reads the tree.

WHAT IT REFUSES TO DO. It does not rewrite the baseline. A `--check` that could
silently re-record what it found would make every later comparison vacuous --
the same shape as a check moved to make it pass. Updating the frozen values is
an edit to this file, by a person, with a reason in the commit.

  python tools/sentinel_baseline.py --check    compare the tree to the freeze
  python tools/sentinel_baseline.py --show     print the current tree's digests
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# FROZEN 2026-09-18. Twelve files, 113,538 bytes.
#
# RE-FROZEN the same day, after the abstention work (spec A1-A6) deliberately
# changed three of them: seal_service.py 8305 -> 12261, tradeGate.js 5053 ->
# 6228, test_sentinel_gate.py 16829 -> 24867. The original freeze was at commit
# fa13845 and 100,369 bytes; this tool reported all three as UNACCOUNTED FOR,
# which is what it is for, and the accounting is the commit that moved them.
#
# guards.py is deliberately NOT frozen here even though it now carries
# ABSTENTION_REASONS and split_reasons. It is a shared money-path file covered
# by G4 and F7; freezing it in the sentinel baseline would turn every trader
# change into a red sentinel check, and a check that is red for reasons outside
# its subject is a check people learn to ignore.
FROZEN = {
    "sentinel_witness/AutomatedSetupModal.jsx": (9829, "3d6b422ec091189e0304f954943024d634892c23a22e700423640ea80a5eac86"),
    "sentinel_witness/Dashboard.jsx":           (7458, "18728c6119331a921d41efe12ddb31876a5d664fe2dbe162b50f33a69c01cc5c"),
    "sentinel_witness/README.md":               (8254, "66b3fdb14d97f101c0602126d656f41e0682cfc8036cb81bfa278758549ba65d"),
    "sentinel_witness/automatedLimits.js":      (2101, "d11adc598fb6465ffb9b63064eeacf3a588766ffacbd121bc339dc4ca9ab36ce"),
    "sentinel_witness/seal_service.py":         (12261, "b4ff95ba34d9d9df0410a8e4e19f357dae34f429dddb7a1bfacd0faa3866d268"),
    "sentinel_witness/tierNavigation.js":       (1864, "0283197c44b96d4b54e12c918f3787d78f2ee4d72c03b917cd392cd85524e700"),
    "sentinel_witness/tradeGate.js":            (6228, "9d4566f7f95cc81ade83ced10489859990fd889b7ff4b1991f12cfe148e5ba84"),
    "test_sentinel_gate.py":                    (24867, "beebfc7a4fd5c66e3d52f05c17abdda5c506cc0269e8ca5521dc564b587a6686"),
    "test_sentinels.py":                        (968, "f8c1ea4e1e026cff61aeb98d0be3d9c9b4c822cedf3b3cfe176e99fd44510710"),
    "test_g6_sentinels_fail.py":                (7138, "b0cbebc02d4d0e6bcbc1d301c61aea8e65191bee87392d3832cd948296d3a5e0"),
    "covenant_sentinels.py":                    (28343, "a762cd17624de25fa999fa48e15663d762b6f57dd6a5f5b0bdb0c102002e7926"),
    "docs/SENTINEL_WITNESS.md":                 (4227, "a829e95279cf90507eb6c08c6f8199e6ee50f853ae913b7e1d817476ec707928"),
}

# The suite tallies measured at the freeze. A CHANGE HERE IS NOT A FAILURE --
# more checks is the point of the work that follows -- so this is reported, never
# asserted. What it buys is that a delta has to be explained rather than noticed
# months later.
FROZEN_TALLIES = {
    "test_sentinel_gate.py": "40/40",
    "test_sentinels.py": "18/18",
    "test_g6_sentinels_fail.py": "11/11",
}


def digest(rel):
    """(bytes, sha256) for one tracked path, or None when it is gone."""
    p = os.path.join(HERE, rel)
    try:
        with open(p, "rb") as fh:
            b = fh.read()
    except OSError:
        return None
    return len(b), hashlib.sha256(b).hexdigest()


def check(say=print):
    """(ok, rows). ok is False when anything moved or vanished."""
    rows, ok = [], True
    for rel, (want_n, want_h) in sorted(FROZEN.items()):
        got = digest(rel)
        if got is None:
            rows.append(("MISSING", rel, "frozen at %d bytes" % want_n))
            ok = False
        elif got[1] != want_h:
            rows.append(("CHANGED", rel, "%d -> %d bytes, sha %s -> %s"
                         % (want_n, got[0], want_h[:12], got[1][:12])))
            ok = False
        else:
            rows.append(("same", rel, "%d bytes" % want_n))
    say("Sentinel-Witness baseline, frozen 2026-09-18 at fa13845")
    for state, rel, detail in rows:
        say("  %-8s %-46s %s" % (state, rel, detail))
    moved = [r for r in rows if r[0] != "same"]
    if moved:
        say("")
        say("  %d of %d file(s) no longer match the freeze." % (len(moved), len(rows)))
        say("  That is not automatically wrong -- it is UNACCOUNTED FOR. Either the")
        say("  edit is deliberate (say so in the commit, and update FROZEN here in")
        say("  the same one) or something landed that nobody meant.")
    else:
        say("")
        say("  all %d file(s) match the freeze." % len(rows))
    say("")
    say("  Suite tallies at the freeze (reported, never asserted -- more checks")
    say("  is the POINT of the work that follows this):")
    for k, v in sorted(FROZEN_TALLIES.items()):
        say("    %-28s %s" % (k, v))
    say("")
    # THIS NOTE WAS STALE WITHIN HOURS and had to be corrected: it still said
    # "there is NO ABSTENTION STATE in this path" after AB1-AB9 and WS1-WS3 had
    # added one. A tool that prints a fact about the system is making a claim,
    # and it decays exactly like prose in a document does.
    say("  NOT COVERED BY THE FROZEN SUITES, and do not read the tallies as")
    say("  covering them: NOTHING HERE ATTACKS THE JUDGE. S5-S8 attack the")
    say("  service's parser, which is a different subject; spec X1-X3 say so.")
    say("  (Abstention IS implemented as of 2026-09-18 -- AB1-AB9 for the three")
    say("  verdicts, WS1-WS3 for the witness separation.)")
    return ok, rows


def show(say=print):
    say("%-46s %8s  %s" % ("file", "bytes", "sha256"))
    for rel in sorted(FROZEN):
        got = digest(rel)
        say("%-46s %8s  %s" % (rel, got[0] if got else "-",
                               got[1] if got else "MISSING"))
    return True, []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="compare the tree to the freeze (default)")
    g.add_argument("--show", action="store_true", help="print the current tree's digests")
    a = ap.parse_args(argv)
    if a.show:
        show()
        return 0
    ok, _rows = check()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
