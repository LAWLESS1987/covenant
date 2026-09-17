#!/usr/bin/env python3
"""readme_totals.py -- write the published totals FROM a sweep transcript, never by hand.

The README and docs/OUTREACH_INSTITUTIONAL.md carry lines marked <!--TOTALS-->.
test_g1_doc_consistency.py makes sure those lines agree with each other; nothing
made them agree with a measurement. On 2026-09-03 a reader (Grok, on its own clone)
found the marked lines saying 64 suites / 1,826 checks while a sentence in the
support section said 65 -- the cheap disagreement G1 exists to prevent, written by
hand around the markers. This tool reads the numbers out of the newest sweep
transcript (covenant_one.py --all writes ONE_SWEEP.txt / ONE_RUN.txt), the core
identity out of the core module, and rewrites every marked line and the dated
"re-measured" sentence. Prose elsewhere is left alone, and it says so.

USE
  python readme_totals.py                 # show what the transcript says and what the docs say
  python readme_totals.py --write         # rewrite the marked lines from the transcript
  python readme_totals.py --transcript ONE_RUN.txt --write
Exit 0 = docs match the transcript (after --write, or already); 1 = they differ and
--write was not given; 2 = no usable transcript.
LICENCE: public domain.
"""
from __future__ import annotations

import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MARK = "<!--TOTALS-->"
DOCS = ["README.md", os.path.join("docs", "OUTREACH_INSTITUTIONAL.md")]


def newest_transcript(explicit=None):
    """The newest transcript that measured something. ONE_RUN.txt is also written
    by --check runs that run no suites (a 2026-09-03 dry run of this tool would
    have published '0 suites, 0 checks' from one); a transcript with no suites
    is not a measurement and is skipped."""
    cands = [explicit] if explicit else ["ONE_SWEEP.txt", "ONE_RUN.txt"]
    best = None
    for c in cands:
        p = os.path.join(HERE, c)
        if not os.path.exists(p):
            continue
        suites = read_totals(p)[0]
        if not suites:
            continue
        if best is None or os.path.getmtime(p) > os.path.getmtime(best):
            best = p
    return best


def read_totals(path):
    """(suites, passed, failed, platform, date) from a covenant_one transcript."""
    t = io.open(path, encoding="utf-8", errors="replace").read()
    def num(label):
        m = re.search(r"^\s*%s\s+(\d+)\s*$" % re.escape(label), t, re.M)
        return int(m.group(1)) if m else None
    suites, passed, failed = num("suites run"), num("checks passed"), num("checks failed")
    m = re.search(r"platform\s*[:=]?\s*(win32|linux|darwin)", t)
    platform = m.group(1) if m else ("win32" if sys.platform == "win32" else sys.platform)
    date = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path)))
    return suites, passed, failed, platform, date


def core_identity():
    sys.path.insert(0, HERE)
    import covenant_unified_v8 as cov  # noqa: E402
    lines = sum(1 for _ in io.open(os.path.join(HERE, "covenant_unified_v8.py"), encoding="utf-8", errors="replace"))
    return cov.COVENANT_VERSION, cov.CORE_SOURCE_SHA12, lines


def rewrite_line(line, version, src, nlines, suites, checks, failed, platform, date):
    """Replace the numbers on one marked line, keeping its shape."""
    line = re.sub(r"source `[0-9a-f]{12}`", "source `%s`" % src, line)
    line = re.sub(r"\d[\d,]* lines", "{:,} lines".format(nlines), line)
    line = re.sub(r"\*\*v\d+\.\d+\*\*", "**%s**" % version, line)
    line = re.sub(r"\d[\d,]*\s+suites?", "%d suites" % suites, line, count=1)
    line = re.sub(r"\d[\d,]*\s+checks?", "{:,} checks".format(checks), line, count=1)
    line = re.sub(r"\d+\s+failed", "%d failed" % failed, line, count=1)
    line = re.sub(r"\b(win32|linux|darwin)\b", platform, line, count=1)
    line = re.sub(r"\d{4}-\d{2}-\d{2}", date, line, count=1)
    return line


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__); return 0
    explicit = args[args.index("--transcript") + 1] if "--transcript" in args else None
    tr = newest_transcript(explicit)
    if not tr:
        print("no transcript: run `python covenant_one.py --all` first"); return 2
    suites, passed, failed, platform, date = read_totals(tr)
    if suites is None or passed is None:
        print("transcript %s has no 'suites run' / 'checks passed' lines" % os.path.basename(tr)); return 2
    version, src, nlines = core_identity()
    print("transcript %s (%s): %d suites, %s checks, %d failed, %s" % (os.path.basename(tr), date, suites, "{:,}".format(passed), failed or 0, platform))
    print("core: %s source %s, %s lines" % (version, src, "{:,}".format(nlines)))
    changed, differs = 0, 0
    for rel in DOCS:
        p = os.path.join(HERE, rel)
        if not os.path.exists(p):
            continue
        out = []
        for line in io.open(p, encoding="utf-8").read().splitlines(True):
            if MARK in line:
                new = rewrite_line(line, version, src, nlines, suites, passed, failed or 0, platform, date)
                if new != line:
                    differs += 1
                    print("%s: %s" % (rel, line.strip()[:110]))
                    print("  -> %s" % new.strip()[:110])
                    if "--write" in args:
                        line = new; changed += 1
            elif line.startswith("Totals re-measured "):
                new = re.sub(r"\d{4}-\d{2}-\d{2}", date, line, count=1)
                if new != line:
                    differs += 1
                    if "--write" in args:
                        line = new; changed += 1
            out.append(line)
        if "--write" in args and changed:
            io.open(p, "w", encoding="utf-8", newline="\n").write("".join(out))
    if "--write" in args:
        print("rewrote %d line(s); prose that quotes totals elsewhere is NOT touched -- G1 lists marked lines only" % changed)
        return 0
    if differs:
        print("%d marked line(s) differ from the transcript; run with --write" % differs); return 1
    print("docs already match the transcript"); return 0


def check_prose():
    """--check: does UNMARKED prose restate the marked totals, and disagree?

    WHY (2026-09-17). This tool updates the two lines carrying <!--TOTALS-->
    and says so honestly: "prose that quotes totals elsewhere is NOT touched".
    That honesty did not stop the rot. README.md's own body said "the header
    line says 86 suites, 2,524 checks" while the header seven lines above said
    96 and 2,742, and "95 test files on disk" while there were 133. A number
    maintained in one place and copied into another is a second source, and the
    second source drifts silently because nothing points at it.

    So: any line that states "<n> suites" or "<n> checks" and does NOT carry the
    marker must agree with the marked line, or say no number at all. Prose that
    quotes a count it does not own is the defect, whichever way it disagrees."""
    marked_suites = marked_checks = None
    offenders = []
    for p in DOCS:
        try:
            lines = io.open(p, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        for line in lines:
            if MARK in line:
                m = re.search(r"\*\*(\d[\d,]*) suites?, (\d[\d,]*) checks?", line) \
                    or re.search(r"\*\*(\d[\d,]*) suites? . (\d[\d,]*) checks?", line)
                if m:
                    marked_suites = m.group(1).replace(",", "")
                    marked_checks = m.group(2).replace(",", "")
    if marked_suites is None:
        print("no marked TOTALS line found; nothing to check against")
        return 0
    for p in DOCS:
        try:
            lines = io.open(p, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if MARK in line:
                continue
            # A NUMBER IS NOT A CLAIM IF THE SENTENCE IS ABOUT THE PAST.
            # The first version of this check flagged seven lines and every one
            # was a deliberate record of what the README USED to say -- this
            # repository's whole habit is keeping corrections visible rather
            # than editing them away. It even convicted the paragraph written
            # minutes earlier to explain the rot. A guard that criminalises the
            # honest practice is a guard somebody switches off, which is the
            # argument docs/RETRACTED.json makes about its own patterns.
            #
            # So: a line narrating history is exempt, and <!--HISTORICAL--> is
            # the explicit escape for anything the heuristic misses. What is
            # still caught is the real defect -- prose asserting a CURRENT count
            # in the present tense, which is how "the runner registers 93
            # suites" outlived 93 by thirty-three.
            if "<!--HISTORICAL-->" in line or re.search(
                    r"\b(said|says|once|used to|until|was|were|reported|"
                    r"earlier|previously|rotted|opened with|had)\b", line, re.I):
                continue
            for m in re.finditer(r"(\d[\d,]*)\s+(suites?|checks?)\b", line):
                val = m.group(1).replace(",", "")
                want = marked_suites if m.group(2).startswith("suite") else marked_checks
                if val != want:
                    offenders.append((p, n, m.group(0), want, line.strip()[:90]))
    print("marked totals: %s suites, %s checks" % (marked_suites, marked_checks))
    if not offenders:
        print("no unmarked prose restates them. Clean.")
        return 0
    print("%d place(s) state a count that disagrees with the marked line:"
          % len(offenders))
    for p, n, got, want, ctx in offenders:
        print("  %s:%d  says %r, marked line says %s" % (p, n, got, want))
        print("        %s" % ctx)
    print("\nFIX: delete the number and point at the command, or move the marker.")
    print("Do not hand-edit it to agree -- it will drift again the next sweep.")
    return 1


if __name__ == "__main__":
    import sys as _sys
    if "--check" in _sys.argv:
        raise SystemExit(check_prose())
    raise SystemExit(main())
