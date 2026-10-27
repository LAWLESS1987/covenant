#!/usr/bin/env python3
"""
test_g6_sentinels_fail.py -- G6 (2026-09-16): can the sentinels ALERT?

WHY. `test_sentinels.py` is twenty-seven lines that run `covenant_sentinels.py`
and check it exits clean. That proves the program runs; it proves nothing about
the only property that matters, which is whether a sentinel can be made to
refuse. A tamper-detector nobody has ever watched detect tampering is a
reassuring log line.

So each sentinel is driven BOTH WAYS against a temp tree: a state it must pass,
and the specific damage it exists to catch. Nothing real is touched --
covenant_sentinels.HERE, STATE_DIR and LOGDIR are all pointed at a temp
directory for the duration, and the anchors are handed in as a dict rather than
read from ops/RECORD_ANCHORS.json.

WHAT IS DRIVEN
  G6.1  RecordSentinel: unchanged document passes.
  G6.2  ...a document whose correction markers were REMOVED alerts. That is the
        sentinel's stated rule -- markers going down means the record of being
        wrong is being erased.
  G6.3  ...a document that is gone entirely does not pass.
  G6.4  MemorySentinel: a ledger that grew passes.
  G6.5  ...a ledger that SHRANK alerts.
  G6.6  ...a ledger that vanished alerts.
  G6.7  NodeWatchdogSentinel is observed only, and this suite says so: it reads
        a live watchdog log, and a faked one measures the fake.
  G6.8  the real anchors, state directory and log directory are untouched.

    python test_g6_sentinels_fail.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile

import covenant_sentinels as S

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return p


def main():
    real = (S.HERE, S.STATE_DIR, S.LOGDIR)
    tmp = tempfile.mkdtemp(prefix="g6_")
    # A document with three correction markers, and the same document with one
    # of them cut out. The marker is whatever MARKER matches in the real code;
    # it is taken from the module rather than guessed at here.
    # THE FIXTURE MUST PROVE ITSELF BEFORE IT PROVES ANYTHING ELSE. My first
    # two tries guessed the marker text ("CORRECTION"), MARKER never matched
    # it, both documents scored zero markers, and G6.2 failed with "1 changed,
    # 0 alerts" -- the sentinel was right and the fixture was empty. MARKER is
    # `^[*_]{1,2}\(?(?:Corrected|Added|Superseded|Retracted)\b`, so the lines
    # below are written to satisfy it, and the counts are asserted with the
    # module's own regex before either document is handed to the sentinel.
    full = "\n".join(["a line", "**Corrected 2026-09-01.** one", "b line",
                      "**Retracted.** two", "c line", "*Superseded* three"])
    cut = "\n".join(["a line", "**Corrected 2026-09-01.** one", "b line", "c line"])
    n_full, n_cut = len(S.MARKER.findall(full)), len(S.MARKER.findall(cut))
    check("G6.0 the fixture itself carries markers the module recognises, and cutting removes some",
          n_full == 3 and n_cut == 1, "full=%d cut=%d" % (n_full, n_cut))

    try:
        S.HERE = tmp
        S.STATE_DIR = os.path.join(tmp, "state")
        S.LOGDIR = os.path.join(tmp, "logs")

        rel = "docs/THING.md"
        write(tmp, rel, full)
        rs = S.RecordSentinel(documents=[rel])
        # THE ANCHOR COMES FROM THE SENTINEL'S OWN measure(), not from a shape
        # I guessed. My first version invented {"sha256","markers","lines"} by
        # reading the source with my eyes, and G6.1 failed -- an unchanged
        # document alerted, because a hand-built anchor is a different object
        # from the one the code writes. Ask the code for its own baseline.
        anchors = {"documents": {rel: rs.measure(rel)}}

        rep = rs.check(anchors)
        check("G6.1 an unchanged document passes", rep.ok, rep.summary[:90])

        write(tmp, rel, cut)
        rep = rs.check(anchors)
        check("G6.2 a document with a correction marker REMOVED alerts",
              not rep.ok and rep.alerts, "%s | %s" % (rep.summary[:60], str(rep.alerts)[:80]))

        os.unlink(os.path.join(tmp, rel))
        rep = rs.check(anchors)
        check("G6.3 a document that is gone does not pass", not rep.ok,
              "%s | %s" % (rep.summary[:60], str(rep.alerts)[:70]))

        # ---- the memory sentinel: a ledger may grow, never shrink
        led = "ops/led.jsonl"
        # LONGER THAN PREFIX_LINES on purpose. The memory sentinel anchors the
        # HEAD of a ledger -- its first 200 lines -- and alerts when that head
        # changes, which is right: an append-only file's history must not be
        # rewritten. My first fixture was 20 lines, so growing it to 30 rewrote
        # the head and the sentinel correctly complained. The fixture was
        # testing rewriting while calling itself growth.
        n0 = S.PREFIX_LINES + 50
        write(tmp, led, "\n".join('{"i": %d}' % i for i in range(n0)) + "\n")
        ms = S.MemorySentinel(ledgers=[led])
        rep = ms.check({})                                   # first sighting
        rep = ms.check({})                                   # now it has a baseline
        check("G6.4 a ledger that has not shrunk passes", rep.ok, rep.summary[:90])

        write(tmp, led, "\n".join('{"i": %d}' % i for i in range(n0 + 40)) + "\n")
        rep = ms.check({})
        check("G6.4b ...and one that GREW beyond its anchored head passes",
              rep.ok, rep.summary[:90])

        write(tmp, led, "\n".join('{"i": %d}' % i for i in range(5)) + "\n")
        rep = ms.check({})
        check("G6.5 a ledger that SHRANK alerts",
              not rep.ok and rep.alerts, "%s | %s" % (rep.summary[:60], str(rep.alerts)[:80]))

        os.unlink(os.path.join(tmp, led))
        rep = ms.check({})
        check("G6.6 a ledger that vanished alerts",
              not rep.ok and rep.alerts, "%s | %s" % (rep.summary[:60], str(rep.alerts)[:80]))

        # ---- what is NOT driven, said plainly
        check("G6.7 NodeWatchdogSentinel is observed, not driven -- it reads a live log",
              hasattr(S, "NodeWatchdogSentinel"),
              "faking a watchdog log would measure the fake")
    finally:
        S.HERE, S.STATE_DIR, S.LOGDIR = real

    # ---- nothing real was touched
    check("G6.8 the real anchors file is still where it was",
          os.path.exists(os.path.join(HERE, "ops", "RECORD_ANCHORS.json")))
    check("G6.8b the module's own roots are restored",
          (S.HERE, S.STATE_DIR, S.LOGDIR) == real, str(S.HERE)[:60])

    failed = [n for n, ok in results if not ok]
    print(f"\nG6: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
