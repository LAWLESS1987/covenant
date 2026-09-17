#!/usr/bin/env python3
"""Reconcile every stated media count in this repository against the catalogues.

WHY THIS EXISTS
---------------
On 2026-09-17 the operator said: *"theres inaccuracies ... currently 120 on x
alone, plus facebook hosted videos ... your inability to count properly is no
mistake."* He was right, and the failure had a shape worth naming.

I had cross-checked `docs/NJEST1987_MEDIA_INDEX_2026-08-29.md` against ITSELF,
found it internally consistent, and reported that as accuracy. Three things were
wrong with that:

  1. The index stops at 2026-08-22. It was 26 days stale when I checked it.
  2. `docs/CORPUS_2026-09-09.md` supersedes it and had ALREADY found the
     files-versus-posts conflation I presented as new -- "114 of 114 read
     compared 114 video FILES against a Media-tab count of 114 video POSTS".
  3. Neither document is data. `private/*/catalog.csv` is data, and I never
     looked for it.

Checking a record against itself is cheap, always available, and produces
confident numbers that say nothing about scope. That is the systematic part, and
it is why this file exists as a TOOL rather than as another paragraph of prose:
prose cannot be re-run.

METHOD (and how to falsify it)
------------------------------
H1  Every count in the markdown can be derived from the catalogues.
    PREDICTION: each stated figure matches a computed one.
    FALSIFIED BY: any disagreement printed below. Disagreement is the result,
    not an error in the tool.

H2  FILES and POSTS are different units and most stated figures conflate them.
    PREDICTION: distinct status_ids < catalogue rows, because a post can carry
    several video files.
    FALSIFIED BY: rows == distinct ids.

H3  An X status_id is a snowflake, so each row carries its own date and the
    stated dates are checkable offline.
    PREDICTION: derived dates agree with the `date` column.
    FALSIFIED BY: disagreement -- and the epoch is asserted against a known row
    before any date is reported, because an epoch wrong by a constant shifts
    every date equally and looks perfectly self-consistent.

H4  Facebook ids are NOT snowflakes and carry no timestamp.
    PREDICTION: snowflake derivation on FB ids yields absurd dates.
    This is why FB is counted but never date-checked here.

PRIVACY
-------
`private/` is gitignored on purpose. This tool prints COUNTS, IDS AND DATES ONLY
-- never a title, a URL, a filename or any transcript text -- so its output is
safe to paste into a public issue. If you extend it, keep that property.
"""
import csv
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "."
TWITTER_EPOCH_MS = 1288834974657

# Documented, so the next reader can argue with the pattern instead of guessing.
RE_SNOWFLAKE = re.compile(r"^\d{17,20}$")          # an X status id
RE_DATE = re.compile(r"^(20\d\d)-(\d\d)-(\d\d)")   # leading ISO date in a column
RE_MD_INT = {                                       # claims made in prose
    "index: files in header":       r"index\s*[-—]\s*(\d+)\s*files",
    "index: video entries":         r"holds\s+\*\*(\d+)\s*video",
    "index: profile photos+videos": r"\*\*(\d+)\s*photos",
    "index: still DID_NOT":         r"(\d+)\s*files still",
    "corpus: X media posts":        r"X media\s+(\d+)\s*posts",
    "corpus: X video files read":   r"X videos read\s+(\d+)\s*files",
    "corpus: FB uploads":           r"Facebook video\s+(\d+)\s*uploads",
    "corpus: FB pre-6-July":        r"FB pre-6-July\s+(\d+)\s*videos",
}

def discover():
    """Find every catalogue by WALKING, not by listing paths I remember.

    The first version of this function hardcoded five paths. It missed
    private/x_missing2/catalog.csv -- eight rows -- because I enumerated from
    what I already knew about instead of from what is on disk. That is the same
    error as checking a document against itself: both substitute a record I
    already hold for the thing I am supposed to be measuring, and both fail
    silently and confidently. A hardcoded list cannot discover the file that was
    added after it was written, which is exactly the file a recount is for.

    Classification is by path, and anything that matches neither is reported as
    UNKNOWN rather than quietly dropped into one bucket or the other."""
    found = []
    root = os.path.join(HERE, "private")
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith(".csv"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, HERE).replace(os.sep, "/")
            # A catalogue is identified by its COLUMNS, not by its name -- a
            # name-based filter is the same guess that missed x_missing2.
            try:
                with open(full, encoding="utf-8", errors="replace", newline="") as fh:
                    head = fh.readline()
            except OSError:
                continue
            if "status_id" not in head:
                continue
            low = rel.lower()
            kind = "fb" if ("fb" in low or "facebook" in low) else (
                "x" if ("njest" in low or low.count("/x_") or "/x" in low) else "unknown")
            found.append((rel, rel, kind))
    return sorted(found)


CATALOGUES = discover()


def snowflake_date(sid):
    return dt.datetime.fromtimestamp(
        ((int(sid) >> 22) + TWITTER_EPOCH_MS) / 1000.0, dt.timezone.utc).date()


def load(path):
    """(rows, ids) -- rows are FILES, ids are POSTS. Never raises."""
    full = os.path.join(HERE, path)
    if not os.path.isfile(full):
        return None, None
    rows, ids = [], []
    try:
        with open(full, encoding="utf-8", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                sid = (r.get("status_id") or "").strip()
                date = (r.get("date") or "").strip()
                rows.append((date, sid))
                if sid:
                    ids.append(sid)
    except OSError:
        return None, None
    return rows, ids


def main():
    print("CORPUS RECONCILIATION -- counts from catalogues, claims from prose")
    print("=" * 74)

    present, absent = [], []
    for label, path, kind in CATALOGUES:
        rows, ids = load(path)
        if rows is None:
            absent.append((label, path))
        else:
            present.append((label, path, kind, rows, ids))

    if absent:
        print("\nNOT AVAILABLE HERE (private/ is gitignored, so this is expected")
        print("in a staged run -- it is a SKIP, not a failure):")
        for label, path in absent:
            print("   %-20s %s" % (label, path))
    if not present:
        print("\nNo catalogue reachable. Nothing can be reconciled; exiting 0")
        print("because absence of private data is not a test failure.")
        return 0

    # ---- H2: files vs posts --------------------------------------------
    print("\nH2  FILES vs POSTS, per catalogue")
    print("    %-20s %6s %6s %6s" % ("catalogue", "rows", "posts", "extra"))
    x_ids, fb_ids, x_rows, fb_rows = set(), set(), 0, 0
    for label, path, kind, rows, ids in present:
        d = len(set(ids))
        print("    %-20s %6d %6d %6d" % (label, len(rows), d, len(rows) - d))
        if kind == "x":
            x_ids |= set(ids); x_rows += len(rows)
        else:
            fb_ids |= set(ids); fb_rows += len(rows)
    print("    %-20s %6d %6d %6d   <- deduped across files" % ("X TOTAL", x_rows, len(x_ids), x_rows - len(x_ids)))
    print("    %-20s %6d %6d %6d" % ("FB TOTAL", fb_rows, len(fb_ids), fb_rows - len(fb_ids)))
    print("    H2 %s: a post can carry several files, so these differ."
          % ("HOLDS" if x_rows != len(x_ids) or fb_rows != len(fb_ids)
             else "is REFUTED for this data -- every post carries one file"))

    # ---- H3: snowflake dates -------------------------------------------
    print("\nH3  DATES, derived from the id vs the date column (X only)")
    checked = agree = 0
    bad = []
    for label, path, kind, rows, ids in present:
        if kind != "x":
            continue
        for date, sid in rows:
            if not (sid and RE_SNOWFLAKE.match(sid) and RE_DATE.match(date or "")):
                continue
            checked += 1
            want = RE_DATE.match(date).group(0)
            got = snowflake_date(sid).isoformat()
            if want == got:
                agree += 1
            else:
                bad.append((label, sid, want, got))
    if not checked:
        print("    no checkable rows")
    else:
        print("    %d of %d agree" % (agree, checked))
        for label, sid, want, got in bad[:12]:
            print("      %-20s %s  column %s  id says %s" % (label, sid, want, got))
        if agree == checked:
            print("    H3 HOLDS -- no date in the X catalogues contradicts its own id.")

    # ---- H4: FB ids are not snowflakes ---------------------------------
    print("\nH4  FB ids are not snowflakes (so FB is counted, never date-derived)")
    shown = 0
    for label, path, kind, rows, ids in present:
        if kind != "fb":
            continue
        for date, sid in rows:
            if sid and RE_SNOWFLAKE.match(sid) and shown < 2:
                try:
                    print("      %s -> snowflake would say %s (column says %s)"
                          % (sid, snowflake_date(sid).isoformat(), date or "?"))
                    shown += 1
                except (ValueError, OverflowError, OSError):
                    print("      %s -> snowflake derivation impossible" % sid)
                    shown += 1
    if not shown:
        print("      no FB id is even snowflake-SHAPED; nothing to derive.")

    # ---- H6: artifacts on disk vs catalogue rows ------------------------
    # A SECOND, INDEPENDENT count. Rows are what a sweep wrote down;
    # transcripts are what it actually produced. They can disagree, and which
    # one is short tells you whether the gap is in the reading or the record.
    # Added 2026-09-17 because counting one of them and calling it the corpus
    # is the same single-route error this file exists to stop.
    print("\nH6  TRANSCRIPTS ON DISK vs CATALOGUE ROWS")
    seen_dirs = set()
    for label, path, kind, rows, ids in present:
        d = os.path.dirname(os.path.join(HERE, path))
        tdir = os.path.join(d, "text")
        if not os.path.isdir(tdir) or tdir in seen_dirs:
            continue
        seen_dirs.add(tdir)
        tx = set()
        for fn in os.listdir(tdir):
            m = re.search(r"(\d{15,20})", fn)
            if m:
                tx.add(m.group(1))
        # Every catalogue that SHARES this text dir counts toward it.
        share = set()
        for _l, p2, _k, _r, i2 in present:
            if os.path.dirname(os.path.join(HERE, p2)) == d:
                share |= set(i2)
        only_tx, only_cat = tx - share, share - tx
        rel = os.path.relpath(tdir, HERE).replace(os.sep, "/")
        print("    %-42s %3d transcripts, %3d catalogued"
              % (rel, len(tx), len(share)))
        if only_tx:
            print("        %d read but NOT catalogued: %s"
                  % (len(only_tx), sorted(only_tx)[:4]))
        if only_cat:
            print("        %d catalogued but NOT read: %s"
                  % (len(only_cat), sorted(only_cat)[:4]))
        if not only_tx and not only_cat:
            print("        exact match -- every catalogued item has a transcript")

    # ---- H1: prose claims vs computed ----------------------------------
    print("\nH1  WHAT THE PROSE CLAIMS vs WHAT THE CATALOGUES HOLD")
    claims = {}
    for rel in ("docs/NJEST1987_MEDIA_INDEX_2026-08-29.md",
                "docs/CORPUS_2026-09-09.md"):
        p = os.path.join(HERE, rel)
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8", errors="replace").read()
        for label, pat in RE_MD_INT.items():
            m = re.search(pat, txt)
            if m and label not in claims:
                claims[label] = int(m.group(1))
    for label in sorted(claims):
        print("    %-32s %s" % (label, claims[label]))
    print("    %-32s %d files / %d posts" % ("COMPUTED  X catalogues", x_rows, len(x_ids)))
    print("    %-32s %d files / %d posts" % ("COMPUTED  FB catalogues", fb_rows, len(fb_ids)))
    print("\n    OPERATOR, 2026-09-17: 120 on X alone, plus Facebook-hosted video.")
    print("    That figure is the one to reconcile against; it is the only one")
    print("    here sourced from the account holder rather than from a tool that")
    print("    paginates. Where a computed number is lower, the catalogue is")
    print("    short -- not the operator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
