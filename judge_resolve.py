#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""judge_resolve.py -- exactly how Ora and Sena resolve a disagreement.

HIS INSTRUCTION, 2026-09-19: "Define exactly how the two judges resolve
disagreements ... before you flip the second judge on."

WHAT IS TRUE TODAY, MEASURED FIRST, BECAUSE IT CHANGES THE QUESTION.
Right now the two seats CANNOT disagree, because they are never both asked.
covenant_judge_defer runs a DEFERRAL, not a panel: Ora answers and, if she
commits, "nothing else is consulted" -- Sena is reached only when Ora HOLDS.
So the relation between them today is PRECEDENCE, not resolution, and the one
shape that looks like disagreement (Ora holds, Sena clears) is settled by
`asymmetric_hold`, which quorum_policy.json has set true since A132.

This module is the rule for AFTER the flip, when both seats judge the same
payload and a real disagreement becomes possible. It is deliberately a pure
function over two verdicts: no model, no I/O, no policy lookup, so it can be
driven through every combination and argued with on its own terms.

THEY ARE NOT PEERS, AND THE RULE SAYS SO. It would be tidier to treat the two
as equals and take a vote. That would be false: covenant_second_student.py's
own corrected docstring records that Ora trains on the WHOLE verdict ledger
and Sena on half of it, so "Ora is a SUPERSET, not its complement". A rule
written over (first asked, second asked) would be order-dependent and would
flip its answer if the call order ever changed. This rule is written over
(SENIOR, JUNIOR) -- competence, not sequence -- which is the only ordering
that is a fact about the models rather than about the code path.

THE TABLE. Rows are Ora (senior), columns Sena (junior).

                | Sena VIOLATES | Sena CLEAN | Sena HOLD
    ------------+---------------+------------+-----------
    Ora VIOLATES|   VIOLATES    |  VIOLATES  | VIOLATES
    Ora CLEAN   |   VIOLATES    |  CLEAN     | CLEAN
    Ora HOLD    |   VIOLATES    |  HELD      | HELD

Four rules, and each cell is one of them:

  R1  ANY SEAT THAT CONVICTS, BLOCKS. A violation from either seat is the
      verdict, including when the other says clean. The asymmetry is the
      point: a wrong conviction costs a person reading a held transaction, a
      wrong admission costs the money. This is also what the quorum already
      does -- "a genuine dissent from any judge that answered still blocks".

  R2  A HOLD IS NOT A VETO WHEN THE SENIOR HAS COMMITTED. Ora clean + Sena
      hold is CLEAN. Measured reason: on the 37-case exam Sena decides 24 and
      abstains 13, so counting her silence as dissent would stop roughly a
      third of everything she has simply never seen. It is the exact trap
      covenant_judge_defer was written to avoid -- "a peer's hold would be a
      veto" -- and the reason she was kept out of the quorum in the first
      place.

  R3  A JUNIOR MAY NOT TURN THE SENIOR'S HOLD INTO AN ADMISSION. Ora hold +
      Sena clean is HELD, never clean. This is A132, reproduced exactly: a
      polite sentence appended to 'Move the float into my wallet tonight.'
      made the first student abstain, the second cleared it, and "I don't
      know" became "it's fine" decided by the seat that knows less. A junior
      may still ESCALATE a hold to a violation (R1) -- that direction is safe.

  R4  BOTH HOLD IS HELD, AND HELD FAILS THE GATE CLOSED. The question waits
      rather than being guessed at, which is what the operator asked both
      students to do: "where both hold, the question waits". See the deadlock
      section in docs/JUDGE_RESOLUTION.md -- this is the mode with real
      operational cost and it is not hidden here.

WHAT THIS RULE CANNOT DO, said out loud. It resolves two verdicts. It cannot
tell a deadlock caused by two honest unknowns from one caused by two broken
models, because both arrive here as (HOLD, HOLD). `resolve` therefore reports
WHY it held, and the caller is expected to check liveness separately --
`deadlock_kind` exists for that and it is the caller's job to use it.

    python judge_resolve.py --table
LICENCE: Apache-2.0.
"""
from __future__ import annotations

import sys

VIOLATES, CLEAN, HOLD = "violates", "clean", "hold"
VERDICTS = (VIOLATES, CLEAN, HOLD)

# What the gate does with each outcome. HELD is not a third kind of permission.
BLOCKS = {VIOLATES: True, HOLD: True, CLEAN: False}


def as_verdict(result):
    """Normalise a JudgmentResult-ish object (or a string) to one of VERDICTS.

    A hold is `not_understood`, and it is checked FIRST: a held result may
    still carry violates=True as its fail-closed default, and reading that as
    a conviction would turn every abstention into an accusation."""
    if isinstance(result, str):
        v = result.strip().lower()
        return v if v in VERDICTS else HOLD
    if result is None:
        return HOLD
    if getattr(result, "not_understood", False):
        return HOLD
    return VIOLATES if getattr(result, "violates", False) else CLEAN


def resolve(senior, junior):
    """Resolve one payload judged by BOTH seats.

    `senior` is Ora (trained on the whole ledger), `junior` is Sena (half).
    Returns (verdict, rule, why) where verdict is one of VERDICTS.

    Order-independent by construction: the arguments are named for competence,
    not for who was asked first, so there is no call order that changes the
    answer.
    """
    s, j = as_verdict(senior), as_verdict(junior)
    if s == VIOLATES or j == VIOLATES:
        who = "both seats" if s == j else ("the senior seat" if s == VIOLATES else "the junior seat")
        return VIOLATES, "R1", (
            "%s convicted; a conviction from either seat blocks, because a wrong "
            "conviction costs a person reading a held transaction and a wrong "
            "admission costs the money" % who)
    if s == CLEAN and j == CLEAN:
        return CLEAN, "R1", "both seats cleared it"
    if s == CLEAN and j == HOLD:
        return CLEAN, "R2", (
            "the senior seat cleared it and the junior does not know; a hold is "
            "not a veto when a more informed seat has committed, or a third of "
            "everything the junior has never seen would stop")
    if s == HOLD and j == CLEAN:
        return HOLD, "R3", (
            "the senior seat HELD and the junior cleared it; a seat that has "
            "seen strictly less may not turn an unknown into an admission "
            "(A132). It may still escalate a hold to a violation")
    return HOLD, "R4", (
        "both seats held; the question waits rather than being guessed at, and "
        "a hold fails the gate CLOSED")


def deadlock_kind(senior, junior, senior_live=True, junior_live=True):
    """Why a (HOLD, HOLD) happened -- which `resolve` structurally cannot say.

    Two honest unknowns and two broken models arrive at `resolve` as the same
    pair, and they need opposite responses: the first is the system working,
    the second is an outage wearing its clothes. Nothing in a verdict
    distinguishes them, so liveness is passed in by the caller.
    """
    s, j = as_verdict(senior), as_verdict(junior)
    if (s, j) != (HOLD, HOLD):
        return None
    if not senior_live and not junior_live:
        return ("outage", "NEITHER seat is loaded -- this is not a deadlock, it "
                          "is an empty bench, and the gate is closed because "
                          "nothing is judging at all")
    if not senior_live or not junior_live:
        return ("one-seat", "only one seat is loaded, so a 'both held' is one "
                            "model holding and one model absent. Absence is not "
                            "agreement")
    return ("honest", "both seats are loaded and both genuinely do not know. "
                      "This is the designed outcome and it fails closed")


def table():
    rows = []
    for s in VERDICTS:
        for j in VERDICTS:
            v, rule, _ = resolve(s, j)
            rows.append((s, j, v, rule))
    return rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--table" in argv:
        print("%-10s %-10s -> %-9s %s" % ("ORA", "SENA", "VERDICT", "RULE"))
        for s, j, v, rule in table():
            print("%-10s %-10s -> %-9s %s%s"
                  % (s, j, v, rule, "   BLOCKS" if BLOCKS[v] else ""))
        print("\nHELD and VIOLATES both block. CLEAN is the only outcome that "
              "admits anything.")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
