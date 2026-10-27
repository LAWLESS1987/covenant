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
  blind             this tool's id count disagreeing with the suite's own tally.
                    MUST be 0, because every other number here is meaningless
                    while it is not -- see THE PATTERN below.

WHY IT RUNS THE SUITE instead of grepping it. The ids are read from the suite's
OUTPUT, not from its source. Grepping the source would count a check that is
defined and never reached -- and this repository has shipped exactly that
(35 of 36 suspected guards once grepped source text instead of running the
code). An id only counts here if a check actually printed it.

THE PATTERN WAS WRONG THREE TIMES, so it is worth the paragraph:

  1. `[SJ]\\d+\\b` -- dropped the suffixed ids (J3b, J3c), reporting 26 checks
     where there were 28. That fed a spec table which counted
     ids-matching-a-pattern and called them checks: two denominators, one
     number.
  2. `[SJ]...` -- hardcoded the two prefixes that existed on the day. The
     moment abstention added AB1-AB9 and WS1-WS3, this went blind to 12 of 40
     checks WHILE REPORTING "ghost citations 0" -- a clean bill of health from
     a checker that could not see the subject. Caught only because `check`
     prints the suite's own tally beside its id count; that comparison is an
     assertion now (`blind`), so the next widened namespace fails loudly.
  3. `[A-Z]\\d{1,2}` -- one letter, so it read "AB1" as "B1" and invented ten
     ghost citations that were really its own mis-parse. Hence {1,3}, and hence
     word boundaries on BOTH scans: without them a multi-letter id matches from
     its second letter.

  python tools/spec_conformance.py           check; exit 1 on a ghost or blindness
  python tools/spec_conformance.py --list    print the id sets
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(HERE, "docs", "SENTINEL_WITNESS_SPEC.md")

#: EVERY suite the spec may cite, not just the first one (2026-09-18). The spec
#: gained X1-X5 citing JA1-JA5 in test_x1_judge_adversarial.py, and with only
#: the gate suite listed here all five would have read as ghost citations --
#: this tool reporting the spec as dishonest when it was the tool that was
#: narrow. A list, so adding a suite is one line and forgetting to is visible:
#: the per-suite tally is printed, and a suite whose output cannot be parsed
#: counts as blindness rather than as zero checks.
SUITES = [
    (os.path.join(HERE, "test_sentinel_gate.py"), r"SENTINEL-GATE:\s*(\d+)/(\d+)"),
    (os.path.join(HERE, "test_x1_judge_adversarial.py"), r"JUDGE-ATTACK:\s*(\d+)/(\d+)"),
]

#: A check id: one to three uppercase letters, one or two digits, an optional
#: lowercase suffix. S19, J3c, AB7, WS1 are all ids. Requirement ids in the spec
#: use prefixes the suite does not (E*, F*, W1-W4, X*), which is what keeps a
#: [VERIFIED by ...] tag from being read as pointing at another requirement.
ID = r"[A-Z]{1,3}\d{1,2}[a-z]?"
CITED = re.compile(r"\b(" + ID + r")\b")
TAG = re.compile(r"\[VERIFIED by ([^\]]+)\]")
LINE = re.compile(r"^\s*(?:PASS|FAIL)\s+(" + ID + r")\b", re.M)
TALLY = re.compile(r"SENTINEL-GATE:\s*(\d+)/(\d+)")
PARTS = re.compile(r"([A-Z]+)(\d+)([a-z]?)")


def _key(s):
    """Sort key for an id, tolerant of any prefix because ID is.

    This hardcoded [SJ] too, and raised AttributeError on the first A-prefixed
    id -- the same assumption as the pattern, in the function that sorts the
    pattern's output. Widening one and not the other turned a silent blind spot
    into a crash: the better failure, but the same bug twice in one file.
    """
    m = PARTS.match(str(s))
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (str(s), 0, "")


def suite_ids(timeout=300):
    """(ids every suite PRINTED, (passed, total) summed, [per-suite rows]).

    Each suite is RUN and its printed ids collected; the tally is read from its
    own summary line. A suite that prints no parseable tally yields None for it,
    which `check` treats as blindness -- the same rule as an id the pattern
    cannot see, for the same reason.
    """
    ids, rows, passed, total = set(), [], 0, 0
    seen_all = True
    for path, tally_re in SUITES:
        name = os.path.basename(path)
        if not os.path.exists(path):
            rows.append((name, None, 0, "absent"))
            seen_all = False
            continue
        r = subprocess.run([sys.executable, path], capture_output=True, text=True,
                           timeout=timeout, cwd=HERE)
        out = r.stdout + r.stderr
        found = set(LINE.findall(out))
        m = re.search(tally_re, out)
        t = (int(m.group(1)), int(m.group(2))) if m else None
        if t is None:
            seen_all = False
        else:
            passed += t[0]
            total += t[1]
        ids |= found
        rows.append((name, t, len(found), "ok" if t else "no tally line"))
    return ids, ((passed, total) if seen_all else None), rows


def spec_ids():
    """(cited, mentioned). CITED means inside a [VERIFIED by ...] tag.

    The distinction is load-bearing. Section 10 names J3b, J3c and J7 in prose
    precisely to say they are NOT cited; counting a prose mention as a citation
    would let the sentence admitting a gap be read as closing it.
    """
    with open(SPEC, encoding="utf-8") as fh:
        text = fh.read()
    cited = set()
    for tag in TAG.findall(text):
        cited.update(CITED.findall(tag))
    return cited, set(CITED.findall(text))


def check(say=print, timeout=300):
    real, tally, rows = suite_ids(timeout)
    cited, mentioned = spec_ids()
    ghosts = sorted(cited - real, key=_key)
    uncited = sorted(real - cited, key=_key)
    # AN UNREADABLE TALLY IS BLINDNESS, not a missing nicety. This read
    # `bool(tally) and ...`, so a suite whose summary line could not be parsed
    # set tally to None, blind to False, and the tool exited 0 while printing
    # "TALLY UNREADABLE" -- a pass with the cross-check switched off, which is
    # the third time in this file that a guard has been absent exactly where its
    # subject was unmeasurable. No tally, no verdict.
    blind = (tally is None) or len(real) != tally[1]

    say("Sentinel-Witness spec conformance")
    for name, t2, n, note in rows:
        say("    %-34s %-9s %3d id(s)  %s"
            % (name, ("%d/%d" % t2) if t2 else "-", n, note))
    say("  suites emit            %3d check id(s)%s"
        % (len(real), "  (tally %d/%d)" % tally if tally else "  (TALLY UNREADABLE)"))
    say("  spec CITES             %3d  (inside a [VERIFIED by ...] tag)" % len(cited))
    say("  spec mentions in prose %3d" % len(mentioned))
    say("")
    if blind:
        if tally is None:
            say("  BLIND: at least one suite printed no tally this tool could read,")
            say("  so there is nothing to cross-check the id count against. Fix the")
            say("  suite's summary line or this tool's pattern for it.")
        else:
            say("  BLIND: found %d id(s), the suites counted %d check(s) -- %d unseen."
                % (len(real), tally[1], tally[1] - len(real)))
            say("  Every number above is void while this is true. Widen ID.")
        say("")
    if ghosts:
        say("  GHOST CITATIONS -- the spec claims a check that does not exist:")
        for g in ghosts:
            say("      %s" % g)
        say("  Section 9's failure: a requirement asserting a measurement it does")
        say("  not have. Either the id is a typo or the check was removed.")
    else:
        say("  ghost citations          0  -- every cited check exists and ran")
    if uncited:
        say("  uncited checks          %2d  -> %s" % (len(uncited), ", ".join(uncited)))
        say("      Not a failure: the suite may be broader than the spec. It means")
        say("      the spec is narrower by exactly these, and says so in section 10.")
    else:
        say("  uncited checks           0")
    if tally and tally[0] != tally[1]:
        say("")
        say("  NOTE: the suite is RED (%d/%d). A citation to a failing check is a"
            % tally)
        say("  citation to a measurement that did not pass.")
    return not ghosts and not blind


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print the id sets and exit")
    a = ap.parse_args(argv)
    if a.list:
        real, tally, _rows = suite_ids()
        cited, mentioned = spec_ids()
        print("suite (%d):" % len(real), ", ".join(sorted(real, key=_key)))
        print("cited (%d):" % len(cited), ", ".join(sorted(cited, key=_key)))
        print("prose (%d):" % len(mentioned), ", ".join(sorted(mentioned, key=_key)))
        return 0
    return 0 if check() else 1


if __name__ == "__main__":
    sys.exit(main())
