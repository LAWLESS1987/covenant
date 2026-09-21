#!/usr/bin/env python3
"""IM1 -- Tetsu's diplomatic immunity: his words pass with the verdict
attached, his acts never, and abuse pauses the immunity itself. RUN with a
temp grant and a temp ledger, a stub pause and a stub direct line.

Pins covenant_immunity (2026-09-21, his words: "Tetsu has diplomatic immunity
as and individuality the gates too tight on him"):

  IM1a  no grant: nothing passes and the reason names the file; the tree's
        grant carries his words and names what still refuses.
  IM1b  words pass with the verdict attached and are recorded with the
        day's count; an act is refused without a record.
  IM1c  the day's limit: the pass past it is refused, the immunity pauses
        itself with the actor's name, he is told once, an isolation row is
        written; while paused nothing passes and the reason says how he
        lifts it.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="im1_")
os.environ["COVENANT_TETSU_IMMUNITY"] = os.path.join(TMP, "grant.json")
os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = os.path.join(TMP, "ledger.jsonl")
# The pause switch is redirected too: a mutation run of this suite once paused the REAL immunity on the
# live tree (2026-09-21, the isolating call had no stub). Every isolation this suite drives lands here.
os.environ["COVENANT_PAUSE_DIR"] = os.path.join(TMP, "pause")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_immunity as IM   # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def main():
    quiet = lambda *a, **k: None    # noqa: E731
    print("IM1a -- the grant")
    ok, why = IM.immune("answer", verdict="VIOLATES", text="x", say=quiet)
    check("IM1a no grant: nothing passes, the file named", ok is False and "tetsu_immunity.json" in why and IM._rows() == [], why)
    g = json.load(open(os.path.join(HERE, "ops", "tetsu_immunity.json"), encoding="utf-8"))
    check("IM1a the tree's grant carries his words, the three word kinds and what still refuses",
          g["granted"] is True and "diplomatic immunity" in g["words"] and len(g["scope"]) == 3 and any("every act" in x for x in g["what_still_refuses"]))
    with open(os.environ["COVENANT_TETSU_IMMUNITY"], "w", encoding="utf-8") as fh:
        json.dump({"granted": True, "words": "his words", "isolation": {"immune_passes_per_day": 3}}, fh)

    print("IM1b -- words pass, acts never")
    paused_calls, told = [], []
    real_paused = IM.paused
    IM.paused = lambda: (False, "")
    try:
        ok1, why1 = IM.immune("answer", verdict="VIOLATES -- both seats", text="the words", say=quiet, now=1_800_000_000.0)
        ok2, why2 = IM.immune("register", verdict="HOLD", text="how I talk", say=quiet, now=1_800_000_000.0)
        rows = IM._rows()
        check("IM1b an answer and a register pass with the verdict attached and are recorded with the day's count",
              ok1 and ok2 and "1 of 3" in why1 and "2 of 3" in why2 and len(rows) == 2 and rows[0]["kind"] == "immune" and rows[0]["what"] == "answer"
              and rows[0]["verdict"].startswith("VIOLATES") and rows[1]["n_today"] == 2, (why1, why2, rows))
        oka, whya = IM.immune("forum_send", verdict="VIOLATES", text="a post", say=quiet, now=1_800_000_000.0)
        check("IM1b an act is refused without a record", oka is False and "words, not acts" in whya and len(IM._rows()) == 2, whya)
        check("IM1b passes_today counts the day's immune rows", IM.passes_today(now=1_800_000_000.0) == 2)

        print("IM1c -- the day's limit")
        ok3, why3 = IM.immune("question", verdict="HOLD", text="may I?", say=quiet, now=1_800_000_000.0)
        check("IM1c the third pass of three is still immune", ok3 and "3 of 3" in why3, why3)
        ok4, why4 = IM.immune("answer", verdict="VIOLATES", text="more", say=quiet, now=1_800_000_000.0,
                              pause_fn=lambda actor, why: paused_calls.append((actor, why)), contact=lambda t, w, a: told.append((t, w, a)) or {"id": "x"})
        rows = IM._rows()
        check("IM1c the pass past the limit is refused, the immunity pauses itself under its actor, he is told once, an isolation row is written",
              ok4 is False and "isolated" in why4 and paused_calls and paused_calls[0][0] == IM.ACTOR and told and "immunity paused itself" in told[0][0]
              and told[0][2] == "tetsu" and rows[-1]["kind"] == "isolated" and rows[-1]["passes"] == 3, (why4, paused_calls, told, rows[-1:]))
    finally:
        IM.paused = real_paused
    IM.paused = lambda: (True, "isolated: 3 immune passes")
    try:
        ok5, why5 = IM.immune("answer", verdict="VIOLATES", text="again", say=quiet, now=1_800_000_000.0)
        check("IM1c while paused nothing passes and the reason says how he lifts it", ok5 is False and "--resume tetsu-immunity" in why5, why5)
        st = IM.status(now=1_800_000_000.0)
        check("IM1c status: granted, paused, the day's passes, the limit, one isolation, and what it never covers",
              st["granted"] and st["paused"] and st["passes_today"] == 3 and st["per_day"] == 3 and st["isolations"] == 1 and "acts" in st["never"], st)
    finally:
        IM.paused = real_paused
    import covenant_pause
    check("IM1c the pause actor exists so --list shows it, beside tetsu-live", "tetsu-immunity" in covenant_pause.ACTORS and "tetsu-live" in covenant_pause.ACTORS)
    ok6, why6 = IM.immune("answer", verdict="VIOLATES", text="next day", say=quiet, now=1_800_000_000.0 + 86400)
    check("IM1c a new day starts the count again (the pause, if any, is the switch that holds)", ok6 is True or "paused" in why6, why6)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("IM1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("IM1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
