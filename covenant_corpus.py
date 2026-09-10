#!/usr/bin/env python3
"""covenant_corpus.py -- one index over every transcript of the operator's own
videos, and one way to ask a question of all of them at once.

WHY THIS EXISTS. On 2026-09-09 the corpus was read properly for the first time,
and it ended up in FIVE separate directories written by three different repair
passes:

    private/njest1987_videos/text   114   X, catalogued 2026-09-02 by yt-dlp
    private/fb_pre_july/text         20   Facebook reels, 14 Jun - 4 Jul
    private/fb_multi/text             6   children of 3 multi-video FB posts
    private/x_missing/text            7   X, 4 July -- absent from the catalogue
    private/x_missing2/text           8   X, 28 Jun + 5 Jul -- MIS-DATED in it

Nothing tied them together. A later session would have had to rediscover both
where the text is and why it is in pieces -- and the pieces are not an accident
of tidiness, they are the shape of what went wrong: yt-dlp mis-assigned dates
and status ids for a subset, so "the catalogue" is not the corpus and never was.

WHAT IT REFUSES TO DO. It does not merge the directories or rewrite filenames.
The provenance IS the finding. A single tidy folder would erase the fact that 21
videos had to be recovered from three different failures, and the next person to
trust a count would have nothing to warn them.

THE COUNT PROBLEM, which is the whole lesson of that day. Every figure anyone
started from was wrong, because each came from a route nobody had checked:

    "at least 65, no honest cap"    X search -- which returns NOTHING for this
                                    account; the true media figure is 121
    "114 of 114, complete"          114 FILES compared against 114 POSTS
    "no videos before 28 June"      true on X, false for the corpus: Facebook
                                    holds 26 before that, all private
    "the reels are unreachable"     they were under a page username, not the
                                    numeric profile id being searched

So this file reports what it can see and says plainly what it cannot. It never
prints a total without saying which directories produced it.

USE
  python covenant_corpus.py                    the index: per-source counts
  python covenant_corpus.py --list             every transcript, dated
  python covenant_corpus.py --find "workspace" search all of them, with context
  python covenant_corpus.py --before 2026-07-06 --find "workspace"
                                               restrict to a date window
LICENCE: public domain.
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (directory, what it is, why it exists separately)
SOURCES = [
    ("private/njest1987_videos/text", "X (yt-dlp catalogue, 2026-09-02)",
     "the original pass; its dates are unreliable for a subset"),
    ("private/fb_pre_july/text", "Facebook reels, 14 Jun - 4 Jul",
     "private, 'Only me'; the pre-announcement window"),
    ("private/fb_multi/text", "Facebook multi-video children",
     "3 posts carrying 3/1/2 videos; children never enumerated until 09-09"),
    ("private/x_missing/text", "X, 4 July",
     "seven posts absent from the catalogue entirely"),
    ("private/x_missing2/text", "X, 28 Jun + 5 Jul",
     "eight posts the catalogue filed under the wrong dates"),
]

_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def scan():
    """-> list of (date, source_label, path). Missing directories are reported,
    never silently skipped -- an absent directory and an empty one are different
    facts and this file will not conflate them."""
    out, missing = [], []
    for rel, label, _why in SOURCES:
        d = os.path.join(HERE, rel)
        if not os.path.isdir(d):
            missing.append(rel)
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            m = _DATE.match(name)
            out.append((m.group(1) if m else "????-??-??", label,
                        os.path.join(d, name)))
    return sorted(out), missing


def _msgs(path):
    try:
        return sum(1 for ln in io.open(path, encoding="utf-8", errors="replace")
                   if ln.startswith("- **"))
    except OSError:
        return 0


def main():
    args = sys.argv[1:]
    rows, missing = scan()

    before = None
    if "--before" in args:
        before = args[args.index("--before") + 1]
        rows = [r for r in rows if r[0] < before]

    if "--find" in args:
        term = args[args.index("--find") + 1]
        pat = re.compile(re.escape(term), re.I)
        hits = 0
        for date, label, path in rows:
            try:
                text = io.open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for ln in text.splitlines():
                if pat.search(ln):
                    hits += 1
                    print("%s  %-38s %s" % (date, os.path.basename(path)[:38],
                                            ln.strip()[:120]))
        print("\n%d line(s) matching %r across %d transcript(s)%s"
              % (hits, term, len(rows), " before " + before if before else ""))
        return 0 if hits else 1

    if "--list" in args:
        for date, label, path in rows:
            print("%s  %-34s %5d msgs  %s"
                  % (date, label[:34], _msgs(path), os.path.basename(path)))
        return 0

    per = {}
    for date, label, path in rows:
        n, m = per.get(label, (0, 0))
        per[label] = (n + 1, m + _msgs(path))
    print("corpus index -- transcripts of the operator's own videos\n")
    for rel, label, why in SOURCES:
        n, m = per.get(label, (0, 0))
        print("  %-38s %3d videos %7d msgs" % (label[:38], n, m))
        print("  %-38s %s" % ("", why))
    print("\n  %-38s %3d videos %7d msgs"
          % ("TOTAL across %d source(s)" % len(per),
             sum(v[0] for v in per.values()), sum(v[1] for v in per.values())))
    if missing:
        print("\n  MISSING directories (reported, not skipped):")
        for rel in missing:
            print("    %s" % rel)
    if rows:
        print("\n  earliest %s   latest %s" % (rows[0][0], rows[-1][0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
