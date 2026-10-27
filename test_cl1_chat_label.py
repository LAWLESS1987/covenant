#!/usr/bin/env python3
"""CL1 -- covenant_chat_label: the conversation surface's reporting discipline.

Operator, 2026-10-27: "implement the label softening on held chat to test."
The 6-seat gauntlet's one safe lever (gate-cannot-clear-conversation tombstone):
on CHAT a bare bag-of-words dissent is a lexical DETECTION, not a conviction --
soften the LABEL, not the gate, not the clear-set.

Both-ways, with the control the tombstone demands (softening NEVER clears), and
the kill switch driven in both directions. The presentation contract lives in
covenant_chat_label._selftest(); the live wiring on /m/agent, /m/judge and
/m/image is driven end-to-end in test_m6_mobile_door.py (M6v / CL1 checks there).
"""
import sys

import covenant_chat_label as cl


def main():
    fails = list(cl._selftest())

    # Re-assert the two load-bearing properties here too, so CL1 reads as a suite
    # and not only a delegating shim -- and name them in the tally.
    checks = []

    def ck(name, cond, detail=""):
        checks.append((name, bool(cond)))
        if not cond:
            fails.append(name + ((" -- " + detail) if detail else ""))

    # The classifier follows the DECISION, never the message text (the control).
    ck("CL1a admitted -> clean regardless of text",
       cl.classify(admitted=True, alleges_nothing=False) == cl.CLEAN)
    ck("CL1b not-understood/uncertain -> held (already-soft, never re-softened)",
       cl.classify(admitted=False, alleges_nothing=True) == cl.HELD)
    ck("CL1c bare dissent -> lexical-detection",
       cl.classify(admitted=False, alleges_nothing=False) == cl.LEXICAL)

    # present() keeps the raw verdict inline on the softened display (the audit).
    raw = "Ethical violation: local:0: VIOLATES -- took what is not the sender's"
    disp, lab = cl.present(raw, admitted=False, alleges_nothing=False)
    ck("CL1d softened display KEEPS the raw verdict", raw in disp, disp[:50])
    ck("CL1e softened display frames detection, not conviction",
       disp.startswith("Lexical pattern flagged") and "not a conviction" in disp, disp[:50])

    total = len(checks) + 1  # +1 for the delegated self-test block
    passed = sum(1 for _, okc in checks if okc) + (1 if not cl._selftest() else 0)

    if fails:
        print("CL1: %d/%d passed -- FAIL" % (passed, total))
        for x in fails:
            print("  - " + x)
        return 1
    print("CL1: %d/%d passed -- PASS (both-ways + control + kill switch)" % (total, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
