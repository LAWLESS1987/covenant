#!/usr/bin/env python3
"""test_r1_retracted.py -- R1: a retracted claim must not come back.

WHY THIS EXISTS. On 2026-09-15 the conformance claim was refuted (A121) and
corrected in eleven files. It survived in five more -- including the README
FRONT PAGE, which went on telling every visitor that the root was "a claim that
an independent build, in any language, sharing none of this code, produces the
same number" while docs/KNOWN_ISSUES.md said the opposite. The sweep that missed
it was a hand-written grep over the phrasings its author happened to think of,
which is the same defect as A74's fake guards and as A121 itself:

    A CHECK THAT CONFIRMS A CLAIM IS STATED CONSISTENTLY IS NOT A CHECK THAT
    THE CLAIM IS TRUE -- AND A GREP THAT FINDS THE PHRASINGS YOU THOUGHT OF
    IS NOT A SWEEP.

WHAT IT PINS.

  L*  LIVENESS. Every pattern must still match inside the RECORD (the allowed
      files that keep retracted wording verbatim). A pattern matching nothing
      anywhere is a dead pattern, and a dead pattern is a silent green -- the
      exact false comfort this file exists to prevent. This also means deleting
      the record breaks the build, which is the intent: the record is load
      bearing, not decorative.
  C*  CONTAINMENT. A retracted phrasing may appear anywhere, in any framing, on
      one condition -- the retraction's id (e.g. "A121") must appear within
      `window` lines of it. A regex cannot separate an assertion from a
      description of an assertion; this project's own judge cannot either
      (roundtable, 2026-09-09). So this does not try. It demands the citation,
      which IS checkable, and which a reintroduced claim will not carry.
  V*  COVERAGE, MEASURED AND ASSERTED. The scan reports how many files it read
      and fails below a floor. A guard that silently reads nothing passes
      forever: `conformance_indep/` is NOT in covenant_one.py's staging list,
      so a check written against the working tree can scan less where the
      runner runs it and never say so. Absent directories are named, not
      assumed clean.

WHAT IT DOES NOT CATCH, found by mutating it rather than by reasoning about it.
Text inserted WITHIN `window` lines of an existing citation is exempt, because
the rule is proximity. Mutation M1 on 2026-09-15 added the full retracted claim
immediately above a paragraph that already cited A121 and this suite stayed
green; moved 380 lines away (M1b) it failed with both patterns naming it. So
this guards ACCIDENTAL REINTRODUCTION -- a new section, a rewritten front page,
a fresh letter that restates the old claim with no correction in sight, which is
exactly what happened to the README -- and it does not guard a claim planted
beside its own retraction, where a reader sees the retraction anyway.

MUTATIONS RUN, serially on one tree, 2026-09-15:
  M1   claim reintroduced next to an existing A121 citation ....... PASSED (limit above)
  M1b  same claim 380 lines from any citation .................... FAILED as designed
  M2   one pattern typo'd so it matches nothing .................. FAILED as designed (L)
  M3   scan extension list emptied so it reads 0 files ........... FAILED as designed (V1, V2)

Pure: no network, no node, no database.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "docs", "RETRACTED.json")
SCAN_EXT = {".md", ".py", ".sh", ".ps1", ".json", ".txt", ".bat", ".html"}
SKIP_DIR = {".git", "__pycache__", "node_modules", "logs", ".pytest_cache",
            "venv", ".venv", "realdata"}

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:300]), flush=True)


def rel(path):
    return os.path.relpath(path, HERE).replace(os.sep, "/")


def allowed(relpath, allow):
    return any(relpath == a or relpath.startswith(a) for a in allow)


def walk_files():
    for dp, dn, fn in os.walk(HERE):
        dn[:] = [d for d in dn if d not in SKIP_DIR]
        for f in fn:
            if os.path.splitext(f)[1].lower() in SCAN_EXT:
                yield os.path.join(dp, f)


def main():
    print("R1 -- a retracted claim must not come back\n")

    if not os.path.isfile(LEDGER):
        check("R1.0 docs/RETRACTED.json exists", False, LEDGER)
        return 1
    led = json.load(open(LEDGER, encoding="utf-8"))
    window = int(led.get("window", 10))
    floor = int(led.get("coverage_floor", 1))
    retractions = led.get("retractions", [])
    check("R1.0 ledger loads and names at least one retraction",
          bool(retractions), len(retractions))

    # ---- read the tree once -------------------------------------------------
    files = {}
    for p in walk_files():
        try:
            files[p] = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            pass

    # V* -- coverage, asserted rather than assumed.
    check("R1.V1 the scan actually read the tree (floor %d files)" % floor,
          len(files) >= floor, "%d files read" % len(files))
    present = {rel(p).split("/")[0] for p in files}
    missing = [d for d in led.get("expect_dirs", []) if d not in present]
    check("R1.V2 every directory the ledger expects was present to scan -- an "
          "absent one is reported, never counted clean",
          not missing, "missing: %s" % missing)
    absent_opt = [d for d in led.get("optional_dirs", []) if d not in present]
    print("      scanned %d files across %d top-level entries%s"
          % (len(files), len(present),
             ("; optional not staged here: " + ", ".join(absent_opt))
             if absent_opt else ""))

    # ---- per retraction -----------------------------------------------------
    for r in retractions:
        rid = r["id"]
        allow = r.get("allow", [])
        pats = [(p, re.compile(p, re.I)) for p in r.get("patterns", [])]
        check("R1.%s.0 declares patterns, allow-list and the true statement"
              % rid,
              bool(pats) and bool(allow) and bool(r.get("truth")))

        dead, violations = [], []
        for src, rx in pats:
            in_record = 0
            for p, text in files.items():
                rp = rel(p)
                hit = rx.search(text)
                if hit and allowed(rp, allow):
                    in_record += 1
                if not hit or allowed(rp, allow):
                    continue
                lines = text.splitlines()
                for m in rx.finditer(text):
                    ln = text[:m.start()].count("\n")
                    lo, hi = max(0, ln - window), min(len(lines), ln + window + 1)
                    if rid in "\n".join(lines[lo:hi]):
                        continue
                    violations.append((rp, ln + 1,
                                       lines[ln].strip()[:110], src))
            if in_record == 0:
                dead.append(src)

        # L* -- a pattern that matches nothing is a silent green.
        check("R1.%s.L every pattern still matches inside the record, so none "
              "is a dead regex quietly passing" % rid,
              not dead, "dead patterns: %s" % dead)

        # C* -- the actual guard.
        if violations:
            for rp, ln, line, src in violations[:12]:
                print("        %s:%d  [%s]  %s" % (rp, ln, src, line))
        check("R1.%s.C no live file restates this retracted claim without "
              "citing %s within %d lines" % (rid, rid, window),
              not violations, "%d violation(s)" % len(violations))

    ok = sum(1 for r in results if r)
    print("\nR1: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
