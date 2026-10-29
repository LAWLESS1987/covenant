#!/usr/bin/env python3
"""test_im7_recurrence_precision.py -- the pattern-based recurrence instrument + its circle-back coverage, both ways.

    python test_im7_recurrence_precision.py   -> "IM7: n/n passed", then LIMIT lines

A 'recurrence' used to fire when any TWO >=6-char non-stopword terms co-occurred on ONE line of 18,858 lines of
prose (RETRACTED.json + KNOWN_ISSUES.md + LOOKBACK_INDEX.md). MEASURED on the dedup benchmark it fired on 6 of 10
candidates and ALL SIX were false (function words slipped the length filter; the real gap 'mobile push on a verdict
flip' was SILENTLY DISCARDED). A391 (2026-10-29) replaces it with the DESIGNED instrument -- docs/RETRACTED.json's
narrow per-claim patterns, what test_r1_retracted.py enforces -- so a recurrence = RE-STATING a refuted claim. And
because that instrument is re-runnable (unlike a 'have's justification) the circle-back now re-verifies every
recurrence: one that still matches is reconfirmed, one that no longer matches (a legacy prose verdict, or a
retraction since restated) is surfaced for re-vet -- a false recurrence can no longer silently discard a real gap.

Driven both ways: an injected temp ledger with one narrow pattern proves the mechanism deterministically (fires /
does not fire; reconfirmed / stale / cleared-by-disposition), then a LIVE measurement shows the benchmark now
yields ZERO recurrence and no benchmark idea re-states a real retraction.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve as CI   # noqa: E402

R = []


def check(name, ok, detail=""):
    R.append(bool(ok))
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  -- %s" % (str(detail)[:300],)))


def write_ledger(dirpath, retractions, name="RETRACTED.json"):
    p = os.path.join(dirpath, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"retractions": retractions}, f)
    return p


def rec(cid, idea, why, t="2026-11-05T07:00:00Z"):
    return {"id": cid, "idea": idea, "kind": "gap", "vet": "recurrence", "why": why, "t": t}


def main():
    print("IM7 -- pattern-based recurrence + circle-back coverage, both ways\n")

    with tempfile.TemporaryDirectory() as td:
        led = write_ledger(td, [{"id": "ZTEST1", "claim": "that the moon is made of cheese",
                                 "patterns": [r"moon\s+is\s+made\s+of\s+cheese"]}])

        # ---- _tombstoned: fires on a restated retracted claim, silent on a benign idea ----
        hit = CI._tombstoned("the old claim that the moon is made of cheese, again", path=led)
        check("IM7.1 a restated retracted claim fires recurrence, naming the retraction id",
              bool(hit) and "ZTEST1" in hit, hit)
        check("IM7.2 a benign unrelated idea does NOT fire recurrence",
              CI._tombstoned("a mobile push notification when a verdict flips sign", path=led) is None)
        check("IM7.3 an empty ledger (no patterns) fires nothing",
              CI._tombstoned("moon is made of cheese", path=write_ledger(td, [], name="EMPTY.json")) is None)

        # ---- id parsing: a real hit carries the id; a legacy prose 'why' does not ----
        check("IM7.4 recurrence_retraction_id parses the id from a hit", CI.recurrence_retraction_id(hit) == "ZTEST1")
        check("IM7.5 a legacy prose why (named a FILE, never an id) parses to None",
              CI.recurrence_retraction_id("KNOWN_ISSUES.md: **Evidence:** some old line") is None)

        # ---- re-verification, both ways ----
        check("IM7.6 _recurrence_still_matches True when the idea still matches the named retraction",
              CI._recurrence_still_matches("the moon is made of cheese", "ZTEST1", path=led))
        check("IM7.7 False when there is no id (a legacy verdict)",
              not CI._recurrence_still_matches("the moon is made of cheese", None, path=led))
        check("IM7.8 False when the idea no longer matches that id",
              not CI._recurrence_still_matches("something entirely unrelated", "ZTEST1", path=led))

        # ---- circle-back coverage of recurrence, both ways ----
        good = rec("r1", "the moon is made of cheese", "RETRACTED ZTEST1: that the moon is made of cheese")
        cbo = CI.circle_back(rows=[good], dispositions={}, retracted=led, today="2026-11-06")
        check("IM7.9 a recurrence that STILL matches its pattern is reconfirmed -> ok (no human needed)",
              cbo["ok"] and len(cbo["reconfirmed"]) == 1 and not cbo["stale_recurrence"], cbo)

        legacy = rec("r2", "a mobile push on a verdict flip", "KNOWN_ISSUES.md: ... re-judges inbound blocks")
        cbl = CI.circle_back(rows=[legacy], dispositions={}, retracted=led, today="2026-11-06")
        check("IM7.10 a legacy prose 'recurrence' (no live pattern match) is STALE -> not ok (the silent-drop hole)",
              not cbl["ok"] and len(cbl["stale_recurrence"]) == 1 and not cbl["reconfirmed"], cbl)

        disp = {"r2": {"candidate_id": "r2", "outcome": "false_match", "term": "verdict",
                       "rationale": "the old prose scan mis-fired; return the candidate for a real look",
                       "author": "t", "t": "2026-11-05"}}
        cbd = CI.circle_back(rows=[legacy], dispositions=disp, retracted=led, today="2026-11-06")
        check("IM7.11 a false_match disposition CLEARS a stale recurrence -> ok, the candidate returns",
              cbd["ok"] and len(cbd["cleared"]) == 1 and not cbd["stale_recurrence"], cbd)

    # ---- LIVE measurement: the hole is closed on the real ledger ----
    b = CI.benchmark()
    nrec = b["by_status"].get("recurrence", 0)
    check("IM7.12 LIVE: the dedup benchmark now yields 0 recurrence verdicts (was 6 of 10, all false)",
          nrec == 0, b["by_status"])
    bm_rows = CI._load_backlog(CI.BENCHMARK)
    anyhit = [(r["id"], CI._tombstoned(r["idea"])) for r in bm_rows if CI._tombstoned(r["idea"])]
    check("IM7.13 LIVE: no benchmark idea re-states a RETRACTED claim (0 of %d)" % len(bm_rows), not anyhit, anyhit)

    ok = sum(R)
    print("\nIM7: %d/%d passed" % (ok, len(R)))
    print("  LIMIT recurrence now = re-stating a RETRACTED claim (RETRACTED.json's narrow patterns, what R1 runs); "
          "the old 2-word prose scan over %d lines is gone." % (18858,))
    print("  LIMIT the live benchmark/ledger numbers are indicative scaffolding; the mechanism + circle-back "
          "coverage are what is pinned here (NO RESULT is not a pass).")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
