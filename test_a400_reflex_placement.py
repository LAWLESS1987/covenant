#!/usr/bin/env python3
"""A400 -- Tetsu's reflex lines ride with the new message, never in the rules (2026-11-01).

His novelty/recall reflex fired on about 6 in 10 door asks, and each firing was appended to the end of the SYSTEM
message, so the model server's prefix cache held the rules but reprocessed the whole replayed history after them:
measured live with a phone-sized history, 1,773 tokens in 44.4 s per firing, against 28 tokens in 2.1 s now.
covenant_unified_v8.agent_messages now builds the turn; this runs it.

What it cannot see: that the door CALLS agent_messages. The door's turn needs a live node, model and gate; that the
call is there is said in the A400 ledger entry and was measured live (prompt_n with and without a firing). A future
edit that inlines the old `_system + line` would pass this suite. Run: python test_a400_reflex_placement.py
"""
import os
import sys

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_unified_v8 as U          # noqa: E402

FAILS = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-74s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    (PASSED.__setitem__(0, PASSED[0] + 1) if ok else FAILS.append(label))


RULES = "You are Tetsu. These are the rules." * 20
HIST = [{"role": "user", "content": "earlier question"}, {"role": "assistant", "content": "earlier answer"}]
LINE = "This input seems novel; consider carefully before proceeding."      # his words, 2026-10-22
RECALL = "This connects to something you discussed before."

quiet = U.agent_messages(RULES, HIST, "what is a volcano?")
fired = U.agent_messages(RULES, HIST, "what is a volcano?", [LINE])
both = U.agent_messages(RULES, HIST, "what is a volcano?", [LINE, RECALL])

check("A400.1 the rules message is byte-identical whether the reflex fires or not (the cached prefix holds)",
      quiet[0] == fired[0] == both[0] and quiet[0]["content"] == RULES, (quiet[0]["content"][-60:], fired[0]["content"][-60:]))
check("A400.2 ...and so is the replayed history, in order",
      quiet[1:-1] == fired[1:-1] == both[1:-1] == HIST, fired[1:-1])
check("A400.3 quiet reflex: the new message is the person's text exactly", quiet[-1] == {"role": "user", "content": "what is a volcano?"},
      quiet[-1])
check("A400.4 a firing: his words, unchanged, in brackets BEFORE the person's text, which ends the message intact",
      fired[-1]["role"] == "user" and fired[-1]["content"] == "[" + LINE + "]\n\nwhat is a volcano?", fired[-1]["content"])
check("A400.5 two lines (novelty + recall) both appear, in that order, before the text",
      both[-1]["content"].index(LINE) < both[-1]["content"].index(RECALL) < both[-1]["content"].index("what is a volcano?"),
      both[-1]["content"])
check("A400.6 an empty or None line adds nothing", U.agent_messages(RULES, HIST, "q", [None, ""])[-1]["content"] == "q")
check("A400.7 no history: rules then the message", [m["role"] for m in U.agent_messages(RULES, [], "q", [LINE])] == ["system", "user"])

print()
print("A400: %d/%d passed" % (PASSED[0], PASSED[0] + len(FAILS)))
sys.exit(1 if FAILS else 0)
