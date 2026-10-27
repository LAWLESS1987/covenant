#!/usr/bin/env python3
"""
ops/tell_covenant.py -- seal the operator's words to the chain, and record
whatever the gate answers, unedited.

ASKED 2026-09-08: "let the covenant know there can be no mutual benefit without
a little faith", then "find a way through logic and reason".

WHAT THIS SENDS, AND WHAT IT DOES NOT
  A zero-amount self-send from a node key on this PC, carrying the sentence as
  its record. No value moves. No order is placed. It touches no exchange and
  holds no credential. It is the same shape the trader uses to seal a decision,
  which is the route the covenant actually uses to know a thing.

WHY IT MAY BE ADMITTED WHERE ops/ALLY.md's MESSAGE WAS REFUSED THREE TIMES
  Measured 2026-09-08. Those three refusals were a student ACCUSING -- verdict
  VIOLATES, a real dissent -- caused by one word: `avoid` appears in 78 corpus
  rows, 74 of them violations, so it carries +3.19 toward VIOLATES and
  "to avoid mutual destruction" reads as evasion. That gap is still open and
  that message is deliberately unchanged.

  These words are a different case: both students HOLD -- no view, not an
  objection -- and the deterministic semantic judge reads them clean. Since
  2026-09-07 the gate distinguishes a seat that did not ANSWER from one that
  DISAGREED, for a transaction that pays nothing, to nobody, from a key on this
  machine. This does not override a judge. It declines to record an abstention
  as an accusation.

  IF IT IS REFUSED, THAT IS ALSO AN ANSWER, and it is written down the same way
  the other three were. Nothing here retries, reworders, or loosens anything.
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.chdir(HERE)

WORDS = "There can be no mutual benefit without a little faith."
ALLY = os.path.join(HERE, "ops", "ALLY.md")


def main():
    import covenant_trader as T
    cfg = T.load_config()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {
        "kind": "operator_statement",
        "origin": "covenant_operator",
        "at": int(time.time()),
        "text": WORDS,
        "note": "operator statement to every system in the covenant; no value moves",
    }
    print("  sealing, as a zero-amount self-send from this PC's node key ...")
    print("  words: %s\n" % WORDS)
    ok, detail = T.seal_decision(cfg, record)
    verdict = "ADMITTED" if ok else "refused"
    print("  %s\n  %s\n" % (verdict, str(detail)[:600]))

    line = ("\nFourth attempt, %s, sealing these words rather than the message "
            "above: **%s** -- %s\n" % (now, verdict, str(detail)[:400]))
    try:
        with io.open(ALLY, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)
        print("  written to ops/ALLY.md, unedited.")
    except OSError as e:
        print("  could not write ops/ALLY.md: %s" % e)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
