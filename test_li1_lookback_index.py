#!/usr/bin/env python3
"""LI1 (A363, 2026-10-17): docs/LOOKBACK_INDEX.md is whole, current, and points at the right lines.

The operator: "start some type of indexing system including for the tombstones to make look back more
efficient for yourself and other systems." tools/lookback_index.py generates the index from
docs/KNOWN_ISSUES.md and docs/RETRACTED.json. This suite fails if any of these is false:
  - the committed file is out of date;
  - a record header or a tombstone is missing from it;
  - a tombstone is not tied to its entry;
  - `find` points at a line that is not the header it names.
The stale and missing shapes are driven on synthetic text, never on the real files.

    python test_li1_lookback_index.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import lookback_index as LI  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


text, ledger = LI._load()
want = LI.render(text, ledger)
try:
    with open(LI.INDEX, encoding="utf-8") as f:
        have = f.read()
except OSError:
    have = ""

check("LI1.1 docs/LOOKBACK_INDEX.md is what the tool generates from today's record and ledger",
      have == want, "stale or missing -- run python tools/lookback_index.py --write")

es = LI.entries(text)
_ids = {e["id"] for e in es}
ts = LI.tombstones(ledger, _ids)
check("LI1.2 the record has headers to index (a zero means the header pattern broke, not an empty record)",
      len(es) >= 300, "%d headers" % len(es))
missing_e = sorted({e["id"] for e in es if ("| %s |" % e["id"]) not in want})
check("LI1.3 every record header id is in the index", not missing_e, missing_e[:5])
missing_t = [t["id"] for t in ts if ("| %s |" % t["id"]) not in want]
check("LI1.4 every tombstone is in the index", len(ts) > 0 and not missing_t, missing_t[:5])

untied = [t["id"] for t in ts if t["entry"] in _ids
          and not any(r.startswith("| %s |" % t["entry"]) and t["id"] in r for r in want.splitlines())]
check("LI1.5 every tombstone is tied to the row of the entry that made it", not untied, untied[:5])

lines = text.splitlines()
bad = [e["id"] for e in es if not lines[e["line"] - 1].startswith("### %s." % e["id"])]
check("LI1.6 each entry's live line number is the line holding its header", not bad, bad[:5])

# ---- driven both ways, on synthetic text --------------------------------------------------------------
syn = "intro\n### A2. [second thing] 2026-10-02. OPEN\nbody\n### A1. [first thing] 2026-10-01. FIXED\n"
syn_led = {"retractions": [{"id": "A2-WORD", "claim": "c", "truth": "t"}]}
r1 = LI.render(syn, syn_led)
r2 = LI.render(syn.replace("intro\n", "intro\n### A3. [new] 2026-10-03.\n"), syn_led)
check("LI1.7 a new record entry makes the old index stale (the check can go red)", r1 != r2)
check("LI1.8 synthetic: both entries, dates, statuses and the tombstone tie are rendered",
      "| A2 | 2026-10-02 | OPEN | A2-WORD | second thing |" in r1 and "| A1 | 2026-10-01 | FIXED | - | first thing |" in r1,
      r1[-300:])
hits = LI.find(["second"], syn, syn_led)
check("LI1.9 find gives the live line of the header", hits and "line 2 " in hits[0], hits)
r3 = LI.render(syn, {"retractions": syn_led["retractions"] + [{"id": "A1-NEW", "claim": "x", "truth": "y"}]})
check("LI1.10 a new tombstone makes the old index stale", r1 != r3 and "A1-NEW" in r3)

sub = LI.tombstones({"retractions": [{"id": "A2b-X"}, {"id": "A9-Y"}]}, {"A1", "A2"})
check("LI1.11 a sub-id tombstone (A2b-...) ties to its parent entry, and one with no header is marked, not hidden",
      sub[0]["entry"] == "A2" and sub[1]["entry"] == "A9 (no header)", sub)

print("LI1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
