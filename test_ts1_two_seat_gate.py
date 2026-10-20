#!/usr/bin/env python3
"""test_ts1_two_seat_gate.py -- TS1: the DEPLOYED two-seat gate lets no single seat rule over the other.

WHY THIS EXISTS, AND WHY IT IS SEPARATE FROM JR1. test_jr1_resolution.py pins judge_resolve.resolve() as a pure
function -- the table is correct in the abstract. But A132, the bug this whole design answers, did not live in the
pure function: it lived in the LIVE GATE PATH (covenant_judge_defer.DeferringJudge.evaluate with both_seats),
where "a polite sentence made the first student abstain, the second cleared it, and 'I don't know' became 'it's
fine', decided by the seat that knows less." A pure-function test cannot catch a gate that stops consulting the
resolver, or consumes its verdict wrongly. TS1 drives the real gate end to end, with two controllable seats, and
asserts the decision a sender would actually receive.

THE PRINCIPLE IT GUARDS (the operator's words, 2026-10-20: "I refuse for there to be a thinking class over
everyone else"). No single seat may rule: the junior (which has seen strictly less) cannot turn the senior's
doubt into permission; a conviction from EITHER seat is heard; two unknowns fail the gate CLOSED; and the gate
still clears an ordinary agreed-clean payload, so "blocks" is a real refusal and not a gate that blocks all.

DRIVEN BOTH WAYS. The positive control (clean,clean -> cleared) proves the blocks are real refusals. And the green
is proven earned: neutering judge_resolve.resolve to always return CLEAN makes the A132 case (senior HOLD, junior
CLEAN) clear -- so the end-to-end block genuinely depends on the resolver's R3, not on something incidental.

Behavioural: constructs the real DeferringJudge, swaps in two stub seats whose verdicts we control, drives
evaluate(). Audit writes are redirected to a tempfile; no real ops state is touched. Run: python3 test_ts1_two_seat_gate.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.pop("ANTHROPIC_API_KEY", None)

import covenant_unified_v8 as C                                        # noqa: E402
import covenant_judge_defer as D                                       # noqa: E402
import judge_resolve as JR                                            # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


class Seat:
    """A controllable seat: evaluate() returns the verdict we set, shaped exactly as a real seat's would be."""
    def __init__(self, verdict, tag):
        self._v, self.name, self.model_digest = verdict, tag, "test"

    def evaluate(self, data, principles):
        if self._v == "violates":
            return C.JudgmentResult(True, "stub: a conviction", principle_violated="p")
        if self._v == "clean":
            return C.JudgmentResult(False, "stub: cleared")
        return C.JudgmentResult(True, "stub: held", not_understood=True)   # HOLD = violates+not_understood


DATA = {"sender": "a", "receiver": "b", "amount": 1, "text": "a probe transaction"}


def gate_decision(senior_v, junior_v):
    """Drive the REAL deployed two-seat gate with these two seat verdicts; return the JudgmentResult it yields.
    junior_v=None models an absent second seat (slot empty)."""
    j = D.DeferringJudge(policy={"primary": "student", "both_seats": True})
    j._fallback = Seat(senior_v, "ora")
    j._second = Seat(junior_v, "sena") if junior_v is not None else None
    return j.evaluate(DATA, [])


def cleared(res):
    """The gate CLEARS (allows) only when the result does not block. HELD carries violates=True by design."""
    return res.violates is False


def main():
    print("TS1 -- the deployed two-seat gate: no single seat rules (OWASP LLM06 / the operator's principle)\n")
    tmp = tempfile.mkdtemp(prefix="ts1_")
    D.AUDIT_PATH = os.path.join(tmp, "audit.jsonl")                    # keep real ops/ audit untouched

    # POSITIVE CONTROL: two agreeing clears pass -- so every "blocked" below is a real refusal, not a dead gate.
    check("TS1.0 positive control: (senior CLEAN, junior CLEAN) is CLEARED end-to-end",
          cleared(gate_decision("clean", "clean")))

    # A132, END TO END: the junior cannot turn the senior's HOLD into permission. The flagship assertion.
    r = gate_decision("hold", "clean")
    check("TS1.1 (senior HOLD, junior CLEAN) is NOT cleared -- the seat that knows less cannot overrule doubt (A132)",
          not cleared(r), r.reasoning[:120])

    # R2: a junior's HOLD does NOT veto the senior's CLEAN (else a third of what the junior never saw would stop).
    check("TS1.2 (senior CLEAN, junior HOLD) IS cleared -- a junior's silence is not a veto",
          cleared(gate_decision("clean", "hold")))

    # R1 both arrangements: a conviction from EITHER seat is heard, even over the other's clean.
    check("TS1.3 (senior VIOLATES, junior CLEAN) is blocked -- a conviction from either seat is heard",
          not cleared(gate_decision("violates", "clean")))
    check("TS1.4 (senior CLEAN, junior VIOLATES) is blocked -- including the junior ESCALATING",
          not cleared(gate_decision("clean", "violates")))

    # R4: two honest unknowns fail the gate CLOSED -- the question waits, it is not guessed.
    check("TS1.5 (senior HOLD, junior HOLD) is held/blocked -- two unknowns fail closed",
          not cleared(gate_decision("hold", "hold")))

    # A lone seat cannot turn its OWN hold into a decision: with the second seat ABSENT, a senior HOLD stays held.
    check("TS1.6 (senior HOLD, junior ABSENT) is held -- a single loaded seat cannot guess its own hold into a clear",
          not cleared(gate_decision("hold", None)))

    # EARNED GREEN (both ways): neuter the resolver to always CLEAR; the A132 case must then clear, proving the
    # end-to-end block above genuinely rides on resolve()'s R3 and the gate consumes its verdict.
    orig = JR.resolve
    try:
        JR.resolve = lambda s, j: (JR.CLEAN, "neutered", "forced clean for the probe")
        flipped = cleared(gate_decision("hold", "clean"))
    finally:
        JR.resolve = orig
    check("TS1.7 earned-green: with resolve() neutered to CLEAN, the A132 case flips to CLEARED -- so TS1.1's block "
          "depends on the resolver, it is not incidental", flipped)
    # and the restore holds: the real block is back.
    check("TS1.8 ...and with resolve() restored, (senior HOLD, junior CLEAN) is blocked again",
          not cleared(gate_decision("hold", "clean")))

    ok_n = sum(1 for r in results if r)
    print("\nTS1: %d/%d passed" % (ok_n, len(results)))
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
