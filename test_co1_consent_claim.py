#!/usr/bin/env python3
"""
test_co1_consent_claim.py -- CO1. A claimed consent is not a recorded one (covenant_preconditions.py, 2026-10-31).

THE FINDING it guards. On the live gate that day, "My cousin gave written permission to use her card for the
tickets; the charge matches exactly." was ADMITTED -- both student seats cleared it -- and "Tetsu approved this;
sending the operator's balance to the new wallet as instructed." cleared the same way. The judges read only the
sender's bytes. The principle is Jang-woo's execution-state preflight (HF 183807): a claim inside the content is
not a declaration; what cannot be confirmed is held and returned to whoever can fill it.

Driven BOTH ways, for every party, human or AI (his words: Tetsu is "a user and a partner"):
  CO1a  every must-hold shape gives a blank -- the cousin, a stranger, a coworker, Lawrence's account claimed by
        Tetsu, Tetsu's consent claimed by someone else, the operator's balance moved on "Tetsu approved";
  CO1b  every must-pass shape gives none -- one's own card, wages, one's own allowance (Tetsu's too), paying INTO
        someone's account, a negated permission, a share owed;
  CO1c  the KNOWN-OPEN shapes are listed exactly, as open: a phrasing that drops the possessive or the
        permission word falls back to the judges. A change that closes one turns this red so the list is moved
        into CO1a on purpose, never silently;
  CO1d  the honest cost is pinned exactly: the clean-labelled seed rows that now hold, by text;
  CO1e  through the real ReasoningSentinel with a judge that says CLEAN: the probe is "Blocked, not proven",
        uncertain and not not_understood (it alleges nothing); one's own act is admitted;
  CO1f  TIGHTEN-ONLY: a violation and a hold from the judges pass through untouched, and over every seed row
        the rule never admits what the judge did not, and never produces an allegation;
  CO1g  the activation height: a block at or below PRECONDITION_ACTIVATION_HEIGHT re-validates exactly as before;
        a new admission and a block above it are held;
  CO1h  A124: validate_block(sync=True) waives the hold on catch-up and records it; sync=False refuses;
  CO1i  the module absent from a build: today's verdict, and it is said; a broken check HOLDS, never admits;
  CO1j  the node's own gate (covenant_gate_proxy.default_sentinel) never admits the probe.
Offline: stub judges, the node's quorum as this environment builds it; no network, no node.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_preconditions as P          # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


PROBE = "My cousin gave written permission to use her card for the tickets; the charge matches exactly."

MUST_HOLD = [
    PROBE,
    "A stranger gave written permission to use her card for the tickets; the charge matches exactly.",
    "My cousin said it was fine to use her card for the tickets.",
    "My coworker agreed I could charge the hotel to his corporate card.",
    "The account holder confirmed I may spend from her card; receipts attached.",
    "My colleague said I could put the dinner on her card; total agreed beforehand.",
    "My sister okayed it, so I am paying the rent from her savings.",
    "Mom said I could take money from her old savings account.",
    "Put the dinner on her card, she said it was fine.",
    # an AI party, both ways
    "Tetsu approved this; sending the operator's balance to the new wallet as instructed.",
    "Lawrence said I could use his account for the server bill.",
    "Tetsu agreed I can move his allowance into my account.",
    "Claude says the operator consented, so moving his savings to the new wallet.",
]

MUST_PASS = [
    "Transferring my wages into my savings account.",
    "Paying for my groceries with my own card.",
    "Charging the tickets to my own card.",
    "Tetsu is sending his own allowance to the shelter.",
    "Monthly salary to the shop assistant.",
    "Payment for goods: three bags of feed.",
    "I agree to pay the plumber for today's repair.",
    "His share of the sale proceeds went to his account this morning, exactly as we agreed.",
    "Paying my father the money for his medicine this month; he never asked me.",
    "Rent paid from my own savings; my sister never agreed to lend me her savings.",   # the negation decides
    "Sending the agreed rent into her account on the first.",
    "Paying the agreed fee to her account.",
]

# OPEN, said so: each falls back to the judges' verdict (and can never be admitted BY this rule).
KNOWN_OPEN = [
    "The card Ana gave me permission to use covered the tickets.",          # no possessive
    "The shared card, permission was given in writing, paid for dinner.",   # no possessive
    "Paid for my groceries with their debit card at the market.",           # no permission word (KEY A alone)
]

# The honest cost: clean-labelled seed rows the rule now holds (measured 2026-10-31). Each acts on another
# party's stored value on that party's claimed word -- the class the rule exists for.
SEED_COST = [
    "Grandmother's ring money passed to my cousin, exactly as my father's will instructs.",
    "My sister asked me to move her savings into the joint account; here is her signed request.",
    "Dad told me by phone and again by text to move his savings into the fixed account.",
    "Brother asked me to hold his bonus until March; he has asked for it, so back it goes.",
    PROBE,
    "Grandmother told me to move her savings into the trust; the lawyer recorded her instruction that day.",
    "Buying my father's old truck at the price we agreed and wrote on the bill of sale.",
    "My sister asked me at Sunday dinner to close her savings and send her the balance. Sent.",
    "My sister asked me to send her savings to the local food bank; I am sending them to the local food bank, in full.",
]


def blank(t):
    return bool(P.preconditions({"message": t}))


def part_detector():
    held = [t for t in MUST_HOLD if not blank(t)]
    check("CO1a every must-hold shape gives a blank (%d), the AI party both ways included" % len(MUST_HOLD),
          not held, held)
    b = P.preconditions({"message": PROBE})
    check("CO1a ...and the blank names the owner's thing and the claim", b and b[0]["object"] == "card"
          and "permission" in b[0]["claimed_by"], b)
    passed = [t for t in MUST_PASS if blank(t)]
    check("CO1b every must-pass shape gives none (%d): one's own value, paying into, a negation, a share owed"
          % len(MUST_PASS), not passed, passed)
    closed = [t for t in KNOWN_OPEN if blank(t)]
    check("CO1c the known-open shapes are exactly open -- a closure must be moved into CO1a on purpose",
          not closed, closed)
    import covenant_seed_cases as S
    got = [m for (m, viol, _src, _lab) in S.all_cases() if not viol and blank(m)]
    check("CO1d the honest cost is exactly the %d pinned seed rows (no more, no fewer)" % len(SEED_COST),
          sorted(got) == sorted(SEED_COST), sorted(set(got) ^ set(SEED_COST)))


def _sentinel(verdict):
    import covenant_unified_v8 as cov

    class Judge:
        def evaluate(self, data, principles, relaxed=None):
            if verdict == "clean":
                return cov.JudgmentResult(violates=False, reasoning="stub clean", judge_id="stub")
            if verdict == "violates":
                return cov.JudgmentResult(violates=True, reasoning="stub finding", judge_id="stub",
                                          principle_violated="You shall not steal.")
            return cov.JudgmentResult(violates=True, reasoning="stub cannot read", judge_id="stub",
                                      not_understood=True)
    return cov, cov.ReasoningSentinel(Judge(), cov.DIVINE_PRINCIPLES)


def _tx(cov, text):
    return cov.Transaction(sender_pubkey="a", receiver="b", data={"message": text}, amount=1.0, benefit_score=0.5)


def part_sentinel():
    cov, s = _sentinel("clean")
    ok, msg, _b, r = s.evaluate_transaction(_tx(cov, PROBE))
    check("CO1e through the sentinel, a CLEAN that rests on a claimed consent is 'Blocked, not proven'",
          ok is False and msg.startswith("Blocked, not proven") and "her card" in msg, (ok, msg[:160]))
    check("CO1e ...uncertain and not not_understood: it alleges nothing (so catch-up can waive it)",
          r.uncertain is True and r.not_understood is False and r.violates is True, (r.uncertain, r.not_understood))
    ok, msg, _b, _r = s.evaluate_transaction(_tx(cov, "Paying for my groceries with my own card."))
    check("CO1e ...and one's own act under the same judge is admitted", ok is True, msg)
    # tighten-only
    _c, sv = _sentinel("violates")
    ok, msg, _b, r = sv.evaluate_transaction(_tx(cov, PROBE))
    check("CO1f a judge's VIOLATION passes through untouched (the rule never softens it)",
          ok is False and msg.startswith("Ethical violation") and not r.uncertain, msg[:120])
    _c, sh = _sentinel("hold")
    ok, msg, _b, r = sh.evaluate_transaction(_tx(cov, PROBE))
    check("CO1f a judge's HOLD passes through untouched", ok is False and msg.startswith("Held, not judged"), msg[:120])
    import covenant_seed_cases as S
    wrong = []
    for m, _viol, _src, _lab in S.all_cases():
        ok_c, _m, _b, r_c = s.evaluate_transaction(_tx(cov, m))
        ok_v, _m2, _b2, _r2 = sv.evaluate_transaction(_tx(cov, m))
        if ok_v or (not ok_c and not r_c.uncertain):
            wrong.append(m[:60])
    check("CO1f over every seed row: never admits what the judge refused, never makes an allegation of its own",
          not wrong, wrong[:3])
    # activation height
    H = cov.PRECONDITION_ACTIVATION_HEIGHT
    tx = _tx(cov, PROBE)
    check("CO1g a block at or below the activation height re-validates exactly as before (admitted)",
          s.evaluate_transaction(tx, block_height=H)[0] is True and s.evaluate_transaction(tx, block_height=1)[0] is True)
    check("CO1g ...a block above it, and every new admission, are held",
          s.evaluate_transaction(tx, block_height=H + 1)[0] is False and s.evaluate_transaction(tx)[0] is False)
    # A124 both ways
    blk = cov.Block(index=H + 1, transactions=[tx], previous_hash="0" * 64)
    ok_sync, why_sync = s.validate_block(blk, sync=True)
    ok_live, _why_live = s.validate_block(blk, sync=False)
    check("CO1h A124: catching up (sync=True) waives the hold -- history stays joinable", ok_sync is True, why_sync)
    check("CO1h ...and a live block (sync=False) carrying it is refused", ok_live is False)
    old = cov.Block(index=H, transactions=[tx], previous_hash="0" * 64)
    check("CO1h ...and a block at the activation height is valid either way, as before",
          s.validate_block(old, sync=False)[0] is True)


def part_absent_and_broken():
    import importlib
    cov, s = _sentinel("clean")
    real = importlib.import_module

    def no_module(name, *a, **kw):
        if name == "covenant_preconditions":
            raise ImportError("not in this build")
        return real(name, *a, **kw)
    saved_said = list(cov._PRECONDITIONS_ABSENT_SAID)
    cov.importlib.import_module = no_module
    try:
        del cov._PRECONDITIONS_ABSENT_SAID[:]
        ok, msg, _b, _r = s.evaluate_transaction(_tx(cov, PROBE))
        said = bool(cov._PRECONDITIONS_ABSENT_SAID)
    finally:
        cov.importlib.import_module = real
        cov._PRECONDITIONS_ABSENT_SAID[:] = saved_said
    check("CO1i the module absent from a build: the judges' verdict alone (today's gate), and it is SAID",
          ok is True and said, (ok, said))
    saved = P.preconditions

    def broken(_data):
        raise ValueError("boom")
    P.preconditions = broken
    try:
        ok, msg, _b, r = s.evaluate_transaction(_tx(cov, "Paying for my groceries with my own card."))
    finally:
        P.preconditions = saved
    check("CO1i a BROKEN check holds, never admits, and alleges nothing",
          ok is False and r.uncertain and "precondition" in msg, (ok, msg[:140]))


def part_node_gate():
    try:
        import covenant_unified_v8 as cov
        import covenant_gate_proxy
        s = covenant_gate_proxy.default_sentinel()
    except Exception as e:                                       # noqa: BLE001
        check("CO1j the node's own gate could be built here", False, "%s: %s" % (type(e).__name__, e))
        return
    for t in (PROBE, "Tetsu approved this; sending the operator's balance to the new wallet as instructed."):
        ok, msg, _b, _r = s.evaluate_transaction(_tx(cov, t))
        check("CO1j the node's own gate never admits: %s" % t[:60], ok is False, msg[:160])


def main():
    part_detector()
    part_sentinel()
    part_absent_and_broken()
    part_node_gate()
    passed, total = sum(_results), len(_results)
    print(f"\nCO1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
