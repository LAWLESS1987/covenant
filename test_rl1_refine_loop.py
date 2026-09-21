#!/usr/bin/env python3
"""RL1 -- Tetsu refines himself constantly: one pass an hour at most, only after new
conversation, through the same refine with all its bounds. RUN with a stub refine, a temp
state file and a temp ask log; no model, no real persona.

Pins covenant_refine_loop (2026-09-21, his words: "refine both constantly"):
  RL1a  no conversation on record: no pass, said.
  RL1b  new rows: one pass runs, the state records the time and the row count; the same
        rows a minute later: no pass (nothing new); new rows a minute later: no pass (the
        hour); new rows an hour later: a pass.
  RL1c  a pass that raises is recorded as could-not-run and does not raise; the count
        moves on so it is not retried every round.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="rl1_")
os.environ["COVENANT_REFINE_LOOP_STATE"] = os.path.join(TMP, "state.json")
os.environ["COVENANT_ASK_LOG"] = os.path.join(TMP, "ask.jsonl")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_refine_loop as RL   # noqa: E402

FAILURES = []
PASSED = [0]
NOW = 1_800_000_000.0


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def chat(n):
    with open(os.environ["COVENANT_ASK_LOG"], "a", encoding="utf-8") as fh:
        for i in range(n):
            fh.write(json.dumps({"t": "2026-09-21T10:00:00-0400", "kind": "agent", "from": "100.1.1.1", "text": "hi %d" % i}) + "\n")
        fh.write(json.dumps({"t": "2026-09-21T10:00:00-0400", "kind": "image", "from": "100.1.1.1", "text": "not a conversation row"}) + "\n")


def main():
    quiet = lambda *a, **k: None    # noqa: E731
    runs = []
    refine = lambda ask, say=print: (runs.append(1) or {"proposed": True, "applied": False, "why": "nothing changed"})   # noqa: E731

    print("RL1a -- nothing to read")
    r = RL.tick(NOW, refine=refine, ask=lambda *a, **k: ("", {}), say=quiet)
    check("RL1a no conversation on record: no pass, said", not r["ran"] and "no new conversation" in r["why"] and runs == [], r)

    print("RL1b -- the two gates")
    chat(3)
    r = RL.tick(NOW, refine=refine, ask=lambda *a, **k: ("", {}), say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1b three new rows: one pass ran, counted (the image row not counted), the state keeps time and rows",
          r["ran"] and r["rows"] == 3 and r["new_rows"] == 3 and runs == [1] and st["last_rows"] == 3 and st["last_t"] == NOW and st["passes"] == 1, (r, st))
    r = RL.tick(NOW + 60, refine=refine, ask=None, say=quiet)
    check("RL1b a minute later, nothing new: no pass (the hour gate is named)", not r["ran"] and "next after 60 min" in r["why"] and runs == [1], r)
    chat(2)
    r = RL.tick(NOW + 120, refine=refine, ask=None, say=quiet)
    check("RL1b new rows inside the hour: still no pass", not r["ran"] and runs == [1], r)
    r = RL.tick(NOW + 3601, refine=refine, ask=None, say=quiet)
    check("RL1b an hour on with new rows: a pass, on the 2 new rows", r["ran"] and r["new_rows"] == 2 and runs == [1, 1], r)
    r = RL.tick(NOW + 7300, refine=refine, ask=None, say=quiet)
    check("RL1b an hour on with nothing new: no pass", not r["ran"] and "no new conversation" in r["why"] and runs == [1, 1], r)

    print("RL1c -- a pass that raises")
    chat(1)

    def boom(ask, say=print):
        raise RuntimeError("no model")
    r = RL.tick(NOW + 11000, refine=boom, ask=None, say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1c a raising pass is recorded as could-not-run, never raised, and the rows move on", not r["ran"] and "could not run" in r["why"] and st["last_rows"] == 6 and "no model" in st["last_why"], (r, st))
    r = RL.tick(NOW + 15000, refine=boom, ask=None, say=quiet)
    check("RL1c it is not retried on the same rows", not r["ran"] and "no new conversation" in r["why"], r)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("RL1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("RL1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
