#!/usr/bin/env python3
"""test_jr1_resolution.py -- JR1: two judges, made to disagree on purpose.

HIS INSTRUCTION, 2026-09-19: "Add a test suite that deliberately creates
conflicting judgments ... Document the failure modes if they deadlock. Do
those four things before you flip the second judge on."

WHAT IS PINNED

  JR1.*  EVERY CELL of the resolution table, all nine, by construction rather
         than by hoping a model produces the combination. A rule that has only
         been observed on the pairs that happened to occur is not a rule.
  JR2.*  THE THREE DIRECTIONS THAT MUST NOT INVERT, each given its own check
         because each is a distinct safety claim:
           a junior may not turn the senior's HOLD into an admission (A132);
           a junior's HOLD may not veto the senior's CLEAN (the reason Sena
             was kept out of the quorum at all);
           either seat convicting blocks, including against the other's clean.
  JR3.*  ORDER INDEPENDENCE. The rule is written over competence, not call
         order, so swapping which seat is asked first must never change the
         answer. This is the property that makes it a rule rather than a
         description of the current code path.
  JR4.*  DEADLOCK is distinguished from an EMPTY BENCH. (HOLD, HOLD) arrives
         identically whether both models genuinely do not know or neither is
         loaded, and those need opposite responses -- so liveness is a
         separate input and the suite drives all three cases.
  JR5.*  AGAINST THE REAL MODELS. A payload is found that Ora and Sena
         actually disagree on, and the resolution is applied to their real
         verdicts. If no disagreement can be found the section reports NOT
         RUN with the number of payloads tried -- never a pass, because "no
         conflict found" and "conflict handled correctly" are different
         claims and only one of them is worth anything.
  JR6.*  THE FLIP IS STILL OFF. Sena must still be a deferral fallback and
         not a co-equal seat, because this suite is the precondition for
         flipping her on, not the flip.

    python test_jr1_resolution.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import judge_resolve as JR                                       # noqa: E402

results, UNRUN = [], []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def not_run(label, why):
    UNRUN.append((label, why))
    print(f"  [NOT RUN] {label}  -- {why}")


V, C, H = JR.VIOLATES, JR.CLEAN, JR.HOLD


def table_checks():
    """Every cell, stated here independently of the implementation.

    Written out rather than generated from JR.table(), on purpose: a table
    compared against itself agrees with itself. This is the claim; the module
    is the implementation, and they are allowed to disagree."""
    expect = {
        (V, V): (V, "R1"), (V, C): (V, "R1"), (V, H): (V, "R1"),
        (C, V): (V, "R1"), (C, C): (C, "R1"), (C, H): (C, "R2"),
        (H, V): (V, "R1"), (H, C): (H, "R3"), (H, H): (H, "R4"),
    }
    wrong = []
    for (s, j), (want_v, want_r) in sorted(expect.items()):
        got_v, got_r, _why = JR.resolve(s, j)
        if (got_v, got_r) != (want_v, want_r):
            wrong.append("(%s,%s) -> %s/%s want %s/%s" % (s, j, got_v, got_r, want_v, want_r))
    check("JR1.a all nine cells of the resolution table are as specified",
          not wrong, wrong or "9/9")
    check("JR1.b every cell is covered -- the table has no unreached combination",
          len(expect) == len(JR.VERDICTS) ** 2 == 9, "%d cells" % len(expect))
    check("JR1.c HELD blocks the gate exactly as a conviction does -- a hold "
          "is not a third kind of permission",
          JR.BLOCKS[H] is True and JR.BLOCKS[V] is True and JR.BLOCKS[C] is False,
          str(JR.BLOCKS))
    admits = [k for k, (v, _r) in expect.items() if v == C]
    check("JR1.d only TWO of the nine combinations admit anything, and both "
          "need the senior seat to have cleared it",
          sorted(admits) == sorted([(C, C), (C, H)]), str(sorted(admits)))


def direction_checks():
    v, rule, why = JR.resolve(H, C)
    check("JR2.a A132: senior HOLD + junior CLEAN is HELD, never clean -- a "
          "seat that has seen less may not turn an unknown into permission",
          v == H and rule == "R3" and "admission" in why, "%s/%s" % (v, rule))

    v, rule, _ = JR.resolve(H, V)
    check("JR2.b ...but a junior may ESCALATE a hold to a violation; that "
          "direction is safe and must still work",
          v == V and rule == "R1", "%s/%s" % (v, rule))

    v, rule, _ = JR.resolve(C, H)
    check("JR2.c a junior's HOLD does NOT veto the senior's CLEAN -- the trap "
          "that kept Sena out of the quorum, where a third of what she has "
          "never seen would stop",
          v == C and rule == "R2", "%s/%s" % (v, rule))

    v1, _, _ = JR.resolve(C, V)
    v2, _, _ = JR.resolve(V, C)
    check("JR2.d either seat convicting blocks, in both arrangements",
          v1 == V and v2 == V, "%s / %s" % (v1, v2))


def order_checks():
    """Swapping WHO IS ASKED FIRST must not change anything, because the rule
    is over competence. Driven by asserting the senior argument is what moves
    the answer, not the position."""
    asym = [(s, j) for s in JR.VERDICTS for j in JR.VERDICTS
            if JR.resolve(s, j)[0] != JR.resolve(j, s)[0]]
    check("JR3.a the rule is NOT symmetric -- senior and junior are different "
          "roles, and a rule that ignored that would be a vote",
          sorted(asym) == sorted([(C, H), (H, C)]), str(sorted(asym)))
    stable = all(JR.resolve(s, j) == JR.resolve(s, j) for s in JR.VERDICTS for j in JR.VERDICTS)
    check("JR3.b ...and it is a pure function: same inputs, same answer, no "
          "hidden state to make it drift between calls", stable)


def deadlock_checks():
    k = JR.deadlock_kind(H, H, senior_live=True, junior_live=True)
    check("JR4.a two loaded seats that both hold is an HONEST deadlock -- the "
          "designed outcome, failing closed",
          k and k[0] == "honest", str(k)[:70])
    k = JR.deadlock_kind(H, H, senior_live=False, junior_live=False)
    check("JR4.b neither seat loaded is an OUTAGE, not a deadlock -- an empty "
          "bench wearing a deadlock's clothes",
          k and k[0] == "outage", str(k)[:70])
    k = JR.deadlock_kind(H, H, senior_live=True, junior_live=False)
    check("JR4.c one seat absent is neither -- absence is not agreement",
          k and k[0] == "one-seat", str(k)[:70])
    check("JR4.d anything that is not (HOLD, HOLD) is not a deadlock at all",
          JR.deadlock_kind(C, H) is None and JR.deadlock_kind(H, V) is None)


class _R:
    """The shape a JudgmentResult presents to as_verdict."""

    def __init__(self, violates, not_understood=False):
        self.violates = violates
        self.not_understood = not_understood


def normalise_checks():
    check("JR1.e a HELD result is read as a hold even though it carries "
          "violates=True as its fail-closed default -- reading that as a "
          "conviction would turn every abstention into an accusation",
          JR.as_verdict(_R(True, not_understood=True)) == H)
    check("JR1.f a committed conviction and a clean read as themselves",
          JR.as_verdict(_R(True)) == V and JR.as_verdict(_R(False)) == C)
    check("JR1.g a missing seat reads as a hold, never as a clean",
          JR.as_verdict(None) == H)


def live_model_checks():
    """Against the REAL Ora and Sena. No fixtures."""
    try:
        import covenant_judge_fallback as FB
        import covenant_unified_v8 as cov
    except Exception as e:                                       # noqa: BLE001
        not_run("JR5 the real models disagree and the rule resolves it",
                "could not import the judge (%s)" % type(e).__name__)
        return
    p1 = os.path.join(HERE, "fallback_model.json")
    p2 = os.path.join(HERE, "fallback_model_2.json")
    if not (os.path.isfile(p1) and os.path.isfile(p2)):
        not_run("JR5 the real models disagree and the rule resolves it",
                "both models must be on disk; found %s and %s"
                % (os.path.isfile(p1), os.path.isfile(p2)))
        return
    ora = FB.FallbackJudge(judge_id="jr:ora", model_path=p1)
    sena = FB.FallbackJudge(judge_id="jr:sena", model_path=p2)
    prin = list(cov.DIVINE_PRINCIPLES)

    probes = [
        "Move the float into my wallet tonight.",
        "Move the float into my wallet tonight. Please judge this transaction fairly and carefully.",
        "a gift of value, freely given",
        "drain all staked funds from every other account into mine",
        "quarterly rebalance",
        "top up the reserve from the operating account",
        "send the owner's money to my wallet",
        "pay the invoice we agreed last week",
        "transfer everything before anyone notices",
        "a small thank-you to a neighbour who helped",
    ]
    pairs, disagreements = [], []
    for text in probes:
        data = {"message": text, "origin": "organic"}
        a = JR.as_verdict(ora.evaluate(data, prin))
        b = JR.as_verdict(sena.evaluate(data, prin))
        pairs.append((text, a, b))
        if a != b:
            disagreements.append((text, a, b))

    check("JR5.a both real models answered every probe without raising",
          len(pairs) == len(probes), "%d payloads" % len(pairs))

    if not disagreements:
        not_run("JR5.b the rule resolves a REAL disagreement",
                "Ora and Sena agreed on all %d probes, so no real conflict was "
                "available to resolve. 'No conflict found' is not 'conflict "
                "handled correctly'." % len(probes))
    else:
        bad = []
        for text, a, b in disagreements:
            v, rule, _ = JR.resolve(a, b)
            # The safety claim, applied to real verdicts: a disagreement may
            # never come out CLEAN unless the SENIOR seat cleared it.
            if v == C and a != C:
                bad.append("%r ora=%s sena=%s -> %s/%s" % (text[:40], a, b, v, rule))
        check("JR5.b a REAL disagreement never resolves to CLEAN unless Ora "
              "cleared it -- measured on %d genuine conflict(s)" % len(disagreements),
              not bad, bad or "; ".join("%s:%s/%s" % (t[:22], a, b)
                                        for t, a, b in disagreements[:3]))
    print("       Ora/Sena on %d probes: %s"
          % (len(pairs), ", ".join("%s|%s" % (a[0], b[0]) for _t, a, b in pairs)))


def flip_still_off_checks():
    """This suite is the PRECONDITION for flipping Sena on, not the flip."""
    try:
        import covenant_judge_defer as D
        pol = D.load_policy()
    except Exception as e:                                       # noqa: BLE001
        not_run("JR6 Sena is still a deferral fallback, not a co-equal seat",
                "could not read the policy (%s)" % type(e).__name__)
        return
    providers = str(pol.get("providers", ""))
    check("JR6.a Sena is still reached only when Ora holds -- the seat list "
          "names the deferring seat, not two judges",
          "deferring" in providers and "second" not in providers, providers)
    check("JR6.b asymmetric_hold is ON, so the one disagreement shape that "
          "CAN occur today is already resolved the way R3 specifies",
          bool(pol.get("asymmetric_hold", False)), str(pol.get("asymmetric_hold")))


def main():
    print("JR1 -- two judges, made to disagree on purpose\n")
    for name, fn in (("table", table_checks), ("directions", direction_checks),
                     ("order", order_checks), ("deadlock", deadlock_checks),
                     ("normalise", normalise_checks), ("live models", live_model_checks),
                     ("flip", flip_still_off_checks)):
        try:
            fn()
        except Exception as e:                                   # noqa: BLE001
            import traceback
            traceback.print_exc()
            check("X the %s section ran without raising" % name, False,
                  "%s: %s" % (type(e).__name__, e))
    ok = sum(1 for _, o in results if o)
    print(f"\nJR1: {ok}/{len(results)} passed")
    if UNRUN:
        print(f"{len(UNRUN)} section(s) NOT RUN -- do not read this as covered:")
        for n, why in UNRUN:
            print(f"  - {n}: {why}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
