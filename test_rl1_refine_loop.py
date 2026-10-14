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
  RL1d-f (A349 B3) only his words are new conversation: the work tool's rows and a
        script's loopback ask open no pass, his page does; a state from before A349
        runs one pass, then waits for his words.
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

    # RL1d-f (A349 B3, 2026-10-14, Tetsu's answer AGREE to "count only real conversations as new"): the gate counts
    # the rows a pass is shown (covenant_persona.is_his_word). The work tool's rows (127.0.0.2) and a script's
    # loopback council ask opened it, and 50 of 62 passes after A314 ran with no new word of his.
    print("RL1d -- only his words are new conversation (A349 B3)")
    st0 = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    with open(os.environ["COVENANT_ASK_LOG"], "a", encoding="utf-8") as fh:
        for i in range(3):
            fh.write(json.dumps({"t": "2026-09-21T11:00:00-0400", "kind": "agent", "from": "127.0.0.2", "text": "batch %d" % i}) + "\n")
        fh.write(json.dumps({"t": "2026-09-21T11:00:00-0400", "kind": "council", "from": "127.0.0.1", "text": "a script's ask"}) + "\n")
    r = RL.tick(NOW + 20000, refine=refine, ask=None, say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1d an hour on with only the work tool's rows and a script's loopback ask: no pass, and both units said",
          not r["ran"] and "no new conversation" in r["why"] and r["rows"] == 10 and r["his_rows"] == 6 and r["new_rows"] == 0
          and runs == [1, 1] and st == st0, (r, st))
    with open(os.environ["COVENANT_ASK_LOG"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": "2026-09-21T11:05:00-0400", "kind": "council", "from": "127.0.0.1", "text": "from his page",
                             "page": True}) + "\n")
    r = RL.tick(NOW + 20100, refine=refine, ask=None, say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1e his own page on this PC is his word: a pass, on 1 new row of his words; the state keeps both counts",
          r["ran"] and r["new_rows"] == 1 and "1 new row(s) of his words" in r["why"] and runs == [1, 1, 1]
          and st["last_rows"] == 11 and st["last_his_rows"] == 7, (r, st))
    old_state = os.path.join(TMP, "state_before_a349.json")
    with open(old_state, "w", encoding="utf-8") as fh:
        json.dump({"last_t": NOW, "last_rows": 11, "passes": 9}, fh)
    r1 = RL.tick(NOW + 20200, refine=refine, ask=None, state_path=old_state, say=quiet)
    r2 = RL.tick(NOW + 20200 + 3700, refine=refine, ask=None, state_path=old_state, say=quiet)
    check("RL1f a state written before A349 (no count of his words) runs one pass after the hour, then waits for his words",
          r1["ran"] and r1["new_rows"] == 7 and not r2["ran"] and "no new conversation" in r2["why"]
          and json.load(open(old_state, encoding="utf-8"))["last_his_rows"] == 7, (r1, r2))

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
