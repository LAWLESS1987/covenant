#!/usr/bin/env python3
"""CI1 (A326, 2026-10-10): every retraction in docs/RETRACTED.json is listed in docs/CORRECTIONS.md.

lawless1987.com links CORRECTIONS.md as the correction index. That day it named 4 of 44 retractions and
nothing after 2026-09-27, because adding a retraction never touched it. tools/corrections_index.py now
generates the full list from the ledger; this suite fails while the file is missing a retraction or the
generated list is stale, and drives both failure shapes on synthetic copies (never on the real files).

    python test_ci1_corrections_index.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import corrections_index as CI  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


print("CI1 -- the correction index lists every retraction")
ledger = json.load(open(CI.LEDGER, encoding="utf-8"))
text = open(CI.INDEX, encoding="utf-8").read()
ids = [r["id"] for r in ledger["retractions"]]
miss = CI.missing_ids(text, ledger)
check("CI1.1 every id in docs/RETRACTED.json appears in docs/CORRECTIONS.md (%d ids)" % len(ids), not miss, miss[:10])
check("CI1.2 the generated list is current (tools/corrections_index.py --write leaves the file unchanged)",
      CI.render(text, CI.section(ledger)) == text, "run: python tools/corrections_index.py --write")
check("CI1.3 the generated list sits between its markers, once", text.count(CI.BEGIN) == 1 and text.count(CI.END) == 1
      and text.index(CI.BEGIN) < text.index(CI.END))

# Driven both ways, on copies.
grown = copy.deepcopy(ledger)
grown["retractions"].append({"id": "CI1-PROBE-NEW", "claim": "A probe claim added to the ledger and to nothing else."})
check("CI1.4 mutation: a retraction added to the ledger only is reported missing, and the list reads stale",
      CI.missing_ids(text, grown) == ["CI1-PROBE-NEW"] and CI.render(text, CI.section(grown)) != text,
      CI.missing_ids(text, grown))
row = next((l for l in text.splitlines() if l.startswith("| `%s` |" % ids[-1])), None)
shrunk = text.replace(row + "\n", "", 1) if row else text
check("CI1.5 mutation: deleting the last retraction's row (%s) reads as missing and as stale" % ids[-1],
      row is not None and ids[-1] in CI.missing_ids(shrunk, ledger) and CI.render(shrunk, CI.section(ledger)) != shrunk,
      (row is not None, CI.missing_ids(shrunk, ledger)[-1:]))
check("CI1.6 a claim with a pipe or a long sentence still renders as one table cell",
      CI.first_sentence("a | b " + "x" * 300).count("\\|") == 1 and len(CI.first_sentence("y" * 400)) <= CI.MAX_CHARS)

print("\nCI1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
