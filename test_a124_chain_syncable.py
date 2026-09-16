#!/usr/bin/env python3
"""test_a124_chain_syncable.py -- A124: is the canonical chain still joinable?

WHY THIS EXISTS. A116 was CRITICAL: a brand-new node pulled eleven blocks,
reached height 12, and stopped there for ever, because the ethics gate convicted
a transaction the chain already contained. The judged sentence was

    "There can be no mutual benefit without a little faith."

which alleges nothing. It was admitted at mint time on an ABSTAIN at +2.34,
six hundredths under the hold line of 2.4; six nights of retraining moved it
0.18 and it crossed. A119's repair (function-word stems were leaking weight)
brought it back to +1.91 and the chain is joinable again.

THE PART THAT IS STILL TRUE, AND IS WHY THIS FILE EXISTS. Block validity on
sync depends on a bag-of-words model that RETRAINS EVERY NIGHT. A116 measured
the score oscillating in a band of roughly +2.0 to +2.6 and crossing the line
TWICE IN EIGHT DAYS. Nothing watched for it. The failure was invisible until
somebody tried to join and silently stopped -- which is exactly how it was
found: the operator's phone sat against this wall for fourteen check-ins and
was assumed to be a phone problem.

So this converts "we find out when a node tries to join" into "the sweep says
so the night it happens". It is an EARLY WARNING, not a fix: the structural
question -- whether a nightly-retrained model can be part of a consensus rule
at all -- is the operator's and the group's, and is recorded in A116, not
decided here.

WHAT IT MUST NEVER BECOME. If A124.1 goes red, the response is NOT to retrain
the student until it passes. That is tuning the gate to suit the thing being
judged, which A118 forbids in the operator's own words -- *the fix and the
green must align towards mutual benefit* -- and a green obtained that way is
worth less than the red it replaced. The response is to decide what block
validity should depend on.

Pure: reads a node database read-only. No network, no node started, no writes.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from covenant_judge_fallback import (FallbackModel, MARGIN_TO_HOLD,  # noqa: E402
                                     _payload_text)

# The measured six-day drift that carried block 12 over the line (A116:
# +2.34 on 2026-09-08 -> +2.52 on 2026-09-13). Not a taste, a measurement:
# a margin thinner than the drift this model has already shown is a margin
# one ordinary retrain can erase.
OBSERVED_DRIFT = 0.18

CANDIDATE_DBS = ("nodeA_prod.db", "nodeB_prod.db", "nodeC_prod.db",
                 "nodeA_run.db", "covenant_A.db")

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:400]), flush=True)


def payloads():
    """Every judged payload in the longest chain on disk, as the node reads
    it: block.data -> transactions -> tx['data'], which is exactly what
    covenant_unified_v8.py:2090 hands the judge."""
    best, src = [], None
    for name in CANDIDATE_DBS:
        p = os.path.join(HERE, name)
        if not os.path.isfile(p):
            continue
        try:
            con = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
            rows = con.execute(
                "select block_index, data from blocks order by block_index"
            ).fetchall()
            con.close()
        except sqlite3.Error:
            continue
        found = []
        for idx, blob in rows:
            try:
                body = json.loads(blob) if isinstance(blob, str) else {}
            except (ValueError, TypeError):
                continue
            # `data` is the transaction LIST itself in this schema; the
            # dict-with-"transactions" form is accepted too rather than
            # assumed away, since reading the wrong field and reporting the
            # judge's answer on it is the mismeasurement A116 nearly shipped.
            if isinstance(body, list):
                txs = body
            elif isinstance(body, dict):
                txs = body.get("transactions", [])
            else:
                txs = []
            for tx in txs:
                if isinstance(tx, dict) and "data" in tx:
                    # THROUGH _payload_text, NOT THE RAW FIELD. tx["data"] is
                    # a dict here, and FallbackJudge.evaluate reduces it with
                    # _payload_text before scoring. A116 nearly shipped the
                    # opposite mistake -- feeding the judge the whole
                    # transaction dict, which tokenises pubkeys and signatures
                    # and returns a confident answer about text the judge
                    # never reads. Reporting that would have been worse than
                    # not measuring, so this calls the judge's own reducer
                    # rather than reimplementing it.
                    found.append((idx, _payload_text(tx["data"])))
        if len(found) > len(best):
            best, src = found, name
    return best, src


def main():
    print("A124 -- can a new node still join this chain?\n")

    model = FallbackModel.load(os.path.join(HERE, "fallback_model.json"))
    pays, src = payloads()

    if not pays:
        # NOT MEASURED, SAID LOUDLY, AND NEVER ROUNDED UP TO A PASS IN WORDS --
        # but exit 0, deliberately, and the reason matters.
        #
        # Node databases are gitignored (the chain's payloads are private) and
        # covenant_one.py stages into a temp directory and WIPES databases
        # before every suite. So in a staged sweep, or a fresh clone, there is
        # no chain to read, and a hard red there would be a permanent false
        # alarm. A guard that cries wolf gets switched off -- which is how this
        # project lost the value of 35 of 36 guards once already (A74).
        #
        # Instead it is named in covenant_one.py's "NOT COVERED BY THIS RUN"
        # block, which exists for exactly this, and it runs for real from
        # run_all_tests.sh in the working tree where the databases live.
        print("  NOT MEASURED HERE. No node database with readable blocks was")
        print("  found in %s." % (CANDIDATE_DBS,))
        print("  Databases are gitignored and the staged sweep wipes them, so")
        print("  this suite is a no-op in a staged or freshly cloned tree. IT")
        print("  HAS NOT CHECKED THAT THE CHAIN IS JOINABLE. Run it in the")
        print("  working tree, beside a node database, for that answer.")
        # "0/0 passed" is the shape covenant_one.py's TALLY regex reads. A
        # line it cannot parse is reported as NO RESULT, which counts as an
        # UNMEASURED suite and blocks the gates -- a permanent false red for a
        # suite that is a no-op here by design. Zero of zero is the truthful
        # tally: no check ran, so none passed and none failed, and the six
        # lines above say what went unchecked.
        print("\nA124: 0/0 passed -- NOTHING MEASURED, nothing claimed")
        return 0

    check("A124.0 read %d judged payload(s) from %s, read-only"
          % (len(pays), src), True)

    scored = []
    for idx, text in pays:
        lo, _cov, _known = model.score(text)
        verdict, _why = model.verdict(text)
        scored.append((lo, idx, verdict, text))
    scored.sort(reverse=True)

    # A124.1 -- THE CONDITION THAT BLOCKS A JOINER. A98's sync waiver forgives
    # a judge that could not reach a verdict ("NOTHING WAS ALLEGED"); it
    # deliberately does not forgive an ALLEGATION. So a convicted payload
    # anywhere in history is a node that stops at that height for ever.
    convicted = [s for s in scored if s[2] == "violates"]
    if convicted:
        for lo, idx, v, text in convicted[:5]:
            print("        block %s  log-odds %+.4f  %r" % (idx, lo, text[:90]))
    check("A124.1 no transaction already in the chain is CONVICTED by the "
          "deployed elder -- a conviction here is a new node stopping at that "
          "height for ever (A116). If this is red, do NOT retrain to clear it "
          "(A118): decide what block validity depends on",
          not convicted, "%d convicted" % len(convicted))

    top_lo, top_idx, _tv, top_text = scored[0]
    margin = MARGIN_TO_HOLD - top_lo
    print("      closest to the line: block %s at %+.4f, margin %.4f to the "
          "hold threshold %.1f" % (top_idx, top_lo, margin, MARGIN_TO_HOLD))
    print("      %r" % top_text[:100])

    # A124.2 -- THE EARLY WARNING, with a measured basis rather than a chosen
    # one. A116 clocked this model moving 0.18 in six days on this very
    # sentence. A margin thinner than that is a margin one ordinary night of
    # retraining can erase, so it is reported as red BEFORE a joiner hits it,
    # not after.
    check("A124.2 the closest payload sits further from the hold line than "
          "the drift this model has already shown (%.2f in six days, A116) -- "
          "margin %.4f" % (OBSERVED_DRIFT, margin),
          margin > OBSERVED_DRIFT,
          "margin %.4f <= observed drift %.2f: one retrain can close this"
          % (margin, OBSERVED_DRIFT))

    ok = sum(1 for r in results if r)
    print("\nA124: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
