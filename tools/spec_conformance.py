#!/usr/bin/env python3
"""spec_conformance.py -- does the Sentinel-Witness spec cite checks that exist?

Step 2 of the operator's order of work, 2026-09-18, needed something to keep it
honest. docs/SENTINEL_WITNESS_SPEC.md traces each requirement to a check id in
test_sentinel_gate.py. A citation to a check that does not exist is the exact
failure the spec's own section 9 warns about -- prose asserting a measurement it
does not have -- and nothing but this catches it.

WHAT IT MEASURES
  ghost citations   ids the spec cites that the suite does not emit.  MUST be 0.
  uncited checks    ids the suite emits that no requirement cites. Reported, not
                    failed: a suite is allowed to be broader than the spec, but
                    a reader should be told by how much.

WHY IT RUNS THE SUITE instead of grepping it. The ids are read from the suite's
OUTPUT, not from its source. Grepping the source would count a check that is
defined and never reached -- and this repository has shipped exactly that
(35 of 36 suspected guards once grepped source text instead of running the
code). An id only counts here if a check actually printed it.

THE REGEX IS THE PART THAT WAS WRONG FIRST. Ids carry optional letter suffixes
-- J3, J3b, J3c -- and a pattern of [SJ]\\d+\\b silently dropped the suffixed
ones, reporting 26 checks where there are 28. That produced a spec table that
counted ids-matching-a-pattern and called them checks: two denominators, one
number. The suffix is not optional in the pattern.

  python tools/spec_conformance.py           check, exit 1 on a ghost citation
  python tools/spec_conformance.py --list    print both id sets
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(HERE, "docs", "SENTINEL_WITNESS_SPEC.md")
SUITE = os.path.join(HERE, "test_sentinel_gate.py")

ID = r"[SJ]\d{1,2}[a-z]?"


def _key(s):
    return (s[0], int(re.match(r"[SJ](\d+)", s).group(1)), s)


def suite_ids(timeout=300):
    """The ids the suite actually PRINTS, plus its own tally line."""
    r = subprocess.run([sys.executable, SUITE], capture_output=True, text=True,
                       timeout=timeout, cwd=HERE)
    out = r.stdout + r.stderr
    ids = set(re.findall(r"^\s*(?:PASS|FAIL)\s+(%s)\b" % ID, out, re.M))
    m = re.search(r"SENTINEL-GATE:\s*(\d+)/(\d+)", out)
    tally = (int(m.group(1)), int(m.group(2))) if m else None
    return ids, tally


def spec_ids():
    with open(SPEC, encoding="utf-8") as fh:
        text = fh.read()
    # Only ids inside a [VERIFIED by ...] tag are CITATIONS. A bare id in prose
    # is discussion -- the correction note in section 10 names J3b, J3c and J7
    # precisely to say they are NOT cited, and counting those as citations would
    # make this tool report success for the sentence admitting the gap.
    cited = set()
    for tag in re.findall(r"\[VERIFIED by ([^\]]+)\]", text):
        cited.update(re.findall(ID, tag))
    return cited, set(re.findall(r"\b(%s)\b" % ID, text))


def check(say=print, timeout=300):
    real, tally = suite_ids(timeout)
    cited, mentioned = spec_ids()
    ghosts = sorted(cited - real, key=_key)
    uncited = sorted(real - cited, key=_key)

    say("Sentinel-Witness spec conformance")
    say("  suite emits            %3d check id(s)%s"
        % (len(real), "  (tally %d/%d)" % tally if tally else ""))
    say("  spec CITES             %3d  (inside a [VERIFIED by ...] tag)" % len(cited))
    say("  spec mentions in prose %3d" % len(mentioned))
    say("")
    if ghosts:
        say("  GHOST CITATIONS -- the spec claims a check that does not exist:")
        for g in ghosts:
            say("      %s" % g)
        say("")
        say("  This is section 9's failure: a requirement asserting a measurement")
        say("  it does not have. Either the id is a typo or the check was removed.")
    else:
        say("  ghost citations        0  -- every cited check exists and ran")
    if uncited:
        say("  uncited checks         %d  -> %s" % (len(uncited), ", ".join(uncited)))
        say("      Not a failure: the suite may be broader than the spec. It means")
        say("      the spec is narrower by exactly these, and says so in section 10.")
    else:
        say("  uncited checks         0")
    if tally and tally[0] != tally[1]:
        say("")
        say("  NOTE: the suite is RED (%d/%d). Citations to a failing check are" % tally)
        say("  citations to a measurement that did not pass." )
    return not ghosts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print both id sets and exit")
    a = ap.parse_args(argv)
    if a.list:
        real, tally = suite_ids()
        cited, mentioned = spec_ids()
        print("suite :", ", ".join(sorted(real, key=_key)))
        print("cited :", ", ".join(sorted(cited, key=_key)))
        print("prose :", ", ".join(sorted(mentioned, key=_key)))
        return 0
    return 0 if check() else 1


if __name__ == "__main__":
    sys.exit(main())
