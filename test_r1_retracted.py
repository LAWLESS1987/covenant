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
SCAN_EXT = {".md", ".py", ".sh", ".ps1", ".json", ".txt", ".bat", ".html",
            # A255 (2026-10-04): the tracked git hooks (ops/pre-commit.synchold,
            # ops/post-commit.autosync, ops/pre-push.opsec) carry claims too, and
            # the first claim retracted FROM a hook was invisible to this scan.
            ".synchold", ".autosync", ".opsec"}
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


_SPECIAL = set(".^$*+?{}[]\\|()")


def required_literal(pattern):
    """The substrings every match of `pattern` must contain, casefolded, or None when none can be proven.

    WHY (2026-10-31). R1 searched every pattern (about 250) across every scanned file (about 5,200), and on
    this PC took 386 s standalone -- three times its 120 s sweep budget, so the sweep read it TIMEOUT (red)
    before and after A393. Most of those searches cannot match. A plain substring test is far cheaper than
    the regex, so a file that lacks the literal is skipped WITHOUT the regex -- it could not have matched.
    The result is identical by construction: only the literal runs at the top level of the pattern, outside
    every group and class, not made optional by a quantifier, are used, and a pattern with any top-level
    alternation or a non-ASCII literal gets no shortcut at all (always searched in full)."""
    runs, cur, depth_paren, depth_class, i = [], [], 0, 0, 0
    while i < len(pattern):
        c = pattern[i]
        nxt = pattern[i + 1] if i + 1 < len(pattern) else ""
        if depth_class:
            if c == "\\":
                i += 2
                continue
            if c == "]":
                depth_class -= 1
            i += 1
            continue
        if c == "[":
            depth_class += 1
            runs.append(cur); cur = []
            i += 1
            continue
        if c == "(":
            depth_paren += 1
            runs.append(cur); cur = []
            i += 1
            continue
        if c == ")":
            depth_paren -= 1
            runs.append(cur); cur = []
            i += 1
            continue
        if depth_paren:
            if c == "\\":
                i += 2
                continue
            i += 1
            continue
        if c == "|":
            return None                                          # top-level alternation: no shortcut
        if c == "{":
            # a repetition count ("{0,30}") is not text: skip it whole. (Measured 2026-10-31: read as the literal
            # "0,30", it made the shortcut demand those digits; the ledger self-check below turned R1 red on it.)
            close = pattern.find("}", i)
            runs.append(cur); cur = []
            i = (close + 1) if close >= 0 else len(pattern)
            continue
        if c == "\\":
            esc = nxt
            if esc and not esc.isalnum():                        # an escaped punctuation mark is a literal
                lit, step = esc, 2
            else:                                                # \s \b \d ...: not a literal, ends the run
                runs.append(cur); cur = []
                i += 2
                continue
        elif c in _SPECIAL:
            runs.append(cur); cur = []
            i += 1
            continue
        else:
            lit, step = c, 1
        after = pattern[i + step] if i + step < len(pattern) else ""
        if after in ("?", "*", "{"):                             # this character may be absent
            runs.append(cur); cur = []
        elif after == "+":                                       # present at least once, then the run ends
            cur.append(lit)
            runs.append(cur); cur = []
        else:
            cur.append(lit)
        i += step
    runs.append(cur)
    # EVERY top-level run is required (each sits outside every group and is not optional), so all of them must
    # be present, not only the longest: "still\s+PRESENT\s+is\s+`did\s+not\s+fix`" needs "still", "present",
    # "`did" and "fix`" together (2026-10-31: the longest-run version still read 2,626 files for one pattern).
    # A non-ASCII LETTER has case forms re.I may match that casefold() does not, so a run holding one is not
    # used; a symbol such as an arrow has no case and is safe.
    import unicodedata
    out = []
    for r in runs:
        s = "".join(r)
        if len(s) < 3:
            continue
        if any(ord(ch) > 127 and unicodedata.category(ch).startswith("L") for ch in s):
            continue
        out.append(s.casefold())
    return tuple(out) if out and max(len(s) for s in out) >= 4 else None


def walk_files():
    for dp, dn, fn in os.walk(HERE):
        dn[:] = [d for d in dn if d not in SKIP_DIR]
        # A236 (2026-09-27): a git worktree the assistant's app keeps under
        # .claude/worktrees/ is a whole second copy of the tree at an OLDER
        # commit, git-excluded (.git/info/exclude). Walking it read 2438 files
        # instead of the tree, and every one of its hits was an allowed record
        # (docs/KNOWN_ISSUES.md, the sweep transcripts) whose relative path no
        # longer matched the allow-list -- 33 "violations" that were the record
        # itself, read through a copy. Pruned by PATH, not by name: the rest of
        # .claude/ (the hooks) is tree and stays scanned.
        if os.path.relpath(dp, HERE).replace(os.sep, "/") == ".claude":
            dn[:] = [d for d in dn if d != "worktrees"]
        for f in fn:
            if os.path.splitext(f)[1].lower() in SCAN_EXT:
                yield os.path.join(dp, f)


def main():
    print("R1 -- a retracted claim must not come back\n")

    if not os.path.isfile(LEDGER):
        check("R1.0 docs/RETRACTED.json exists", False, LEDGER)
        return 1
    ledger_text = open(LEDGER, encoding="utf-8").read()
    led = json.loads(ledger_text)
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
    rels = {p: rel(p) for p in files}
    # casefold, not lower: re.I treats the long s and the Kelvin sign as s and k, and so does casefold().
    lowered = {p: t.casefold() for p, t in files.items()}    # for the literal shortcut only (see required_literal)
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

        dead, violations, bad_lit = [], [], []
        for src, rx in pats:
            in_record = 0
            lit = required_literal(src)
            if lit is not None:
                # The shortcut's own guard: in the ledger itself, which holds every claim's verbatim wording, every
                # match is searched in full (no shortcut) and must contain the literal. A literal some match lacks
                # would hide files that DO match. (The ledger alone: the allow-lists also name whole transcripts and
                # private/, and searching those in full undid the speed-up -- 376 s, measured.)
                if any(any(piece not in m.group(0).casefold() for piece in lit) for m in rx.finditer(ledger_text)):
                    bad_lit.append(src)
            for p, text in files.items():
                if lit is not None and any(piece not in lowered[p] for piece in lit):
                    continue                                     # it cannot match here: the regex is not needed
                rp = rels[p]
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
              not dead and not bad_lit,
              "dead patterns: %s; shortcut literal absent from a match: %s" % (dead, bad_lit))

        # C* -- the actual guard.
        if violations:
            for rp, ln, line, src in violations[:12]:
                # backslashreplace: a violation line with a non-cp1252 character
                # (an arrow, 2026-10-30) crashed this print on a Windows console,
                # which lost the finding and skipped every later retraction.
                print(("        %s:%d  [%s]  %s" % (rp, ln, src, line))
                      .encode("ascii", "backslashreplace").decode("ascii"))
        check("R1.%s.C no live file restates this retracted claim without "
              "citing %s within %d lines" % (rid, rid, window),
              not violations, "%d violation(s)" % len(violations))

    ok = sum(1 for r in results if r)
    print("\nR1: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
