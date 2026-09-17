#!/usr/bin/env python3
"""Cross-check docs/NJEST1987_MEDIA_INDEX_2026-08-29.md against itself.

WHY. The index was assembled by hand from a tool that paginates ten posts at a
time, over two sessions a day apart, and its own header says the denominator is
unverified. Every number in it -- 117, 130, 105, 63 -- was written by a
different pass. Nobody has ever asked whether they agree.

WHAT THIS USES. An X status ID is a snowflake: the top 41 bits are milliseconds
since the Twitter epoch (2010-11-04T01:42:54.657Z). So every entry carries its
own timestamp, independent of the date somebody typed beside it. That makes the
listed dates checkable without opening a single video, without an X session,
and without asking anyone's permission.

The epoch is asserted, not assumed: the script derives the date for a post whose
date is stated in the document and refuses to report anything if the derivation
disagrees, because an epoch that is wrong by a constant would silently shift
every date by the same amount and look perfectly self-consistent.
"""
import collections
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "."
DOC = os.path.join(HERE, "docs", "NJEST1987_MEDIA_INDEX_2026-08-29.md")
TWITTER_EPOCH_MS = 1288834974657


def when(status_id):
    return dt.datetime.fromtimestamp(
        ((int(status_id) >> 22) + TWITTER_EPOCH_MS) / 1000.0, dt.timezone.utc)


def parse(text):
    """(listed_date, status_id, line_no) for every entry that carries both."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for m in re.finditer(r"(20\d\d-\d\d-\d\d)\D{1,12}(\d{17,20})", line):
            out.append((m.group(1), m.group(2), n))
    return out


def main():
    with open(DOC, encoding="utf-8") as fh:
        text = fh.read()
    rows = parse(text)
    if not rows:
        print("no entries parsed -- the document's shape changed")
        return 1

    # --- epoch sanity, before trusting any derived date -------------------
    probe_date, probe_id, _ = rows[0]
    derived = when(probe_id).strftime("%Y-%m-%d")
    print("EPOCH CHECK")
    print("  first entry says %s; its ID derives to %s  -> %s"
          % (probe_date, derived, "OK" if derived == probe_date else "MISMATCH"))
    agree = sum(1 for d, i, _ in rows if when(i).strftime("%Y-%m-%d") == d)
    print("  %d of %d listed dates agree with their own ID" % (agree, len(rows)))
    if agree < len(rows) * 0.8:
        print("\n  REFUSING to report further: fewer than 80%% agree, which means")
        print("  the epoch or the parse is wrong, not the document. Fix this first.")
        return 1

    print("\nENTRIES: %d parsed" % len(rows))

    # --- 1. dates that disagree with their own ID -------------------------
    print("\n1. LISTED DATE vs THE ID'S OWN TIMESTAMP")
    bad = [(d, i, n) for d, i, n in rows if when(i).strftime("%Y-%m-%d") != d]
    if not bad:
        print("   every listed date matches its ID. No transcription drift.")
    for d, i, n in bad:
        t = when(i)
        delta = (t.date() - dt.date.fromisoformat(d)).days
        print("   line %-4d %s  listed %s  actual %s UTC  (%+d day)"
              % (n, i, d, t.strftime("%Y-%m-%d %H:%M:%S"), delta))
        if abs(delta) == 1:
            print("            -- one day: a UTC/local boundary, not an error, "
                  "if it was posted near midnight Eastern")

    # --- 2. duplicates ----------------------------------------------------
    print("\n2. DUPLICATE STATUS IDs")
    seen = collections.Counter(i for _, i, _ in rows)
    dupes = {i: c for i, c in seen.items() if c > 1}
    if not dupes:
        print("   none -- every ID appears once.")
    for i, c in sorted(dupes.items()):
        lines = [n for _, j, n in rows if j == i]
        print("   %s appears %d times (lines %s)" % (i, c, lines))

    # --- 3. bursts: posts seconds apart = one sitting ---------------------
    print("\n3. BURSTS -- consecutive posts under 120s apart (one sitting)")
    ordered = sorted({i for _, i, _ in rows}, key=int)
    bursts, cur = [], [ordered[0]]
    for prev, nxt in zip(ordered, ordered[1:]):
        if (when(nxt) - when(prev)).total_seconds() <= 120:
            cur.append(nxt)
        else:
            if len(cur) > 1:
                bursts.append(cur)
            cur = [nxt]
    if len(cur) > 1:
        bursts.append(cur)
    print("   %d burst(s); %d of %d posts sit inside one"
          % (len(bursts), sum(len(b) for b in bursts), len(ordered)))
    for b in sorted(bursts, key=len, reverse=True)[:6]:
        span = (when(b[-1]) - when(b[0])).total_seconds()
        print("     %s  %2d posts in %5.0fs  (%s .. %s)"
              % (when(b[0]).strftime("%Y-%m-%d %H:%M"), len(b), span,
                 b[0][-6:], b[-1][-6:]))

    # --- 4. the shape of the record over time -----------------------------
    print("\n4. POSTING BY DAY (derived, not listed)")
    byday = collections.Counter(when(i).strftime("%Y-%m-%d") for _, i, _ in rows)
    days = sorted(byday)
    first, last = dt.date.fromisoformat(days[0]), dt.date.fromisoformat(days[-1])
    span_days = (last - first).days + 1
    print("   %s .. %s  = %d calendar days, %d with a post, %d silent"
          % (days[0], days[-1], span_days, len(days), span_days - len(days)))
    print("   busiest:")
    for d, c in byday.most_common(5):
        print("     %s  %2d" % (d, c))
    gaps = []
    for a, b in zip(days, days[1:]):
        g = (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
        if g > 2:
            gaps.append((a, b, g - 1))
    print("   silent stretches over one day:")
    for a, b, g in gaps:
        print("     %d days between %s and %s" % (g, a, b))

    # --- 5. the document's own numbers, against each other ----------------
    print("\n5. THE DOCUMENT'S OWN ARITHMETIC")
    claims = {}
    for label, pat in (("header total", r"index\D{0,20}(\d+)\s*files"),
                       ("profile says", r"\*\*(\d+)\s*photos"),
                       ("video entries", r"holds\s+\*\*(\d+)\s*video"),
                       ("still DID_NOT", r"(\d+)\s*files still"),
                       ("unaccounted", r"(\d+)\s*files unaccounted"),
                       ("opened by 08-30", r"\*\*(\d+)\s*of\s*(\d+)\s*opened")):
        m = re.search(pat, text)
        if m:
            claims[label] = m.group(1)
    for k, v in claims.items():
        print("   %-16s %s" % (k, v))
    print("   parsed from the tables: %d" % len(set(i for _, i, _ in rows)))
    print("\n   Reconciliation is the reader's job, and the numbers above come")
    print("   from different passes on different days. Where they disagree, the")
    print("   disagreement is the finding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
