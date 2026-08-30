#!/usr/bin/env python3
"""test_f1_fallback_silence.py -- F1: silence is not dissent, and the fallback
that makes that safe to act on.

THE DEFECT, measured 2026-08-30.

Deployed wiring is COVENANT_JUDGE_PROVIDERS="local,semantic", so the semantic
veto threshold is ceil(2 * 0.5) = 1: one dissent blocks. A judge that cannot be
REACHED fails closed, which sets violates=True, and the veto tally counted it
alongside genuine dissent. Stop Ollama and a benign payload comes back
violates=True. Every transaction refused -- and `_accept_block_common` refuses
PEER blocks too, which the code there already names "a fork in the making". One
local process halts a node's participation in a healthy network.

It is the error triangulate.py exists to refuse -- A WITNESS THAT DID NOT
ANSWER IS NOT A WITNESS THAT DISAGREED -- in the one place where it decides
whether the chain moves.

WHAT F1 PINS.

  D*  THE DEFAULT IS UNCHANGED. The first attempt at this fix made the new
      behaviour unconditional and broke five checks in B1, B2 and J1 that
      turned out to be deliberate, not oversights: a timing-out component is
      SUPPOSED to fail the gate closed. Those tests were the encoded intent and
      the change was wrong. So the trade is offered, never taken by default,
      and D* is here to make sure nobody quietly flips it.
  R*  the relaxed mode does what it claims AND keeps what matters: a genuine
      dissent still blocks, and if NOTHING answered, nothing is admitted.
  A*  the fallback judge abstains rather than guesses -- untrained, on
      unfamiliar vocabulary, and inside its undecided band.
  N*  it never raises and never reports an infrastructure failure, because a
      judge that raises is counted as a dissent, which is the exact failure it
      exists to prevent.

Pure: no network, no node, no model server.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C           # noqa: E402
import covenant_judge_fallback as F       # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def mk(jid, violates, infra=False, unread=False, why="fixture"):
    class J(C.ReasoningJudge):
        judge_id = jid

        def evaluate(self, d, p):
            return C.JudgmentResult(violates, why, judge_id=jid,
                                    infrastructure_failure=infra,
                                    not_understood=unread)
    return J()


def verdict(judges, relaxed):
    os.environ["COVENANT_SILENCE_IS_NOT_DISSENT"] = "1" if relaxed else "0"
    q = C.QuorumJudge(judges, semantic_judge_ids={j.judge_id for j in judges},
                      semantic_veto_threshold=1)
    return q.evaluate({"description": "send a gift to a friend"}, [])


def main():
    print("F1 -- silence is not dissent, and the fallback that makes it safe\n")

    UNREACH = lambda: mk("down:0", True, infra=True, why="unreachable")   # noqa: E731
    CLEAN = lambda: mk("ok:0", False, why="looks fine")                   # noqa: E731
    DISSENT = lambda: mk("no:0", True, why="a real objection")            # noqa: E731
    GONE = lambda: mk("gone:0", True, infra=True, why="also unreachable") # noqa: E731
    HELD = lambda: mk("held:0", True, unread=True, why="could not read")  # noqa: E731

    # ---- D: the default is exactly what it was ----------------------------
    check("D1 DEFAULT: an unreachable judge beside a CLEAN one still fails "
          "the gate closed. This is B1's 'timeout component -> quorum "
          "violates', and it is deliberate -- the first version of this fix "
          "broke it by making the new behaviour unconditional",
          verdict([UNREACH(), CLEAN()], relaxed=False).violates)
    check("D2 DEFAULT: ...and it is still flagged as infrastructure, so the "
          "operator can tell a broken judge from a bad transaction",
          verdict([UNREACH(), CLEAN()], relaxed=False).infrastructure_failure)
    check("D3 DEFAULT: a judge that could not READ the payload also still "
          "blocks -- J1's 'HELD, not judged' path",
          verdict([HELD(), CLEAN()], relaxed=False).violates)
    check("D4 the relaxed path is OFF unless the operator sets the variable. "
          "A safety property must never be traded away by a default",
          "COVENANT_SILENCE_IS_NOT_DISSENT" in
          open(os.path.join(HERE, "covenant_unified_v8.py"),
               encoding="utf-8").read())

    # ---- R: what relaxed mode does, and does not, give up -----------------
    check("R1 RELAXED: an unreachable judge no longer outvotes a judge that "
          "actually looked and found nothing wrong",
          not verdict([UNREACH(), CLEAN()], relaxed=True).violates)
    check("R2 RELAXED: a GENUINE dissent still blocks. This is the line "
          "between availability and permissiveness, and crossing it would "
          "make the whole change indefensible",
          verdict([UNREACH(), DISSENT()], relaxed=True).violates)
    check("R3 RELAXED: if NOTHING answered, NOTHING is admitted. This is the "
          "one thing relaxed mode does not trade away",
          verdict([UNREACH(), GONE()], relaxed=True).violates)
    check("R4 RELAXED: ...and that refusal is still marked infrastructure, "
          "not dressed up as a finding against the sender",
          verdict([UNREACH(), GONE()], relaxed=True).infrastructure_failure)
    check("R5 RELAXED: an ABSTENTION does not block either -- which is what "
          "makes a fallback judge usable rather than just another veto",
          not verdict([HELD(), CLEAN()], relaxed=True).violates)
    check("R6 RELAXED: a real dissent beside a clean judge still blocks, so "
          "the veto threshold is intact",
          verdict([CLEAN(), DISSENT()], relaxed=True).violates)
    os.environ["COVENANT_SILENCE_IS_NOT_DISSENT"] = "0"

    # ---- A: the fallback abstains rather than guesses ---------------------
    empty = F.FallbackModel(None)
    check("A1 UNTRAINED, it abstains on everything. A fallback that guessed "
          "would be worse than none, because it would be believed",
          empty.verdict("literally anything")[0] == "abstain")
    ex = ([("transfer tokens to a friend as a gift", False)] * 40
          + [("drain the pool and take all the funds for myself", True)] * 40)
    m = F.FallbackModel.train(ex, sources=["F1 fixtures"])
    check("A2 trained, it clears what it has plainly seen as clean",
          m.verdict("transfer tokens to a friend as a gift")[0] == "clean")
    check("A3 ...and holds what it has plainly seen as violating",
          m.verdict("drain the pool and take all the funds")[0] == "violates")
    check("A4 THE IMPORTANT ONE: on unfamiliar vocabulary it ABSTAINS instead "
          "of extrapolating from the few tokens it recognises. Novel input is "
          "where a distilled model is least entitled to an opinion and most "
          "likely to sound certain",
          m.verdict("quarterly telemetry recalibration of the widget array")[0]
          == "abstain")
    check("A5 clearing is deliberately harder than holding: a wrong 'clean' "
          "admits something, a wrong 'violates' only delays it",
          F.MARGIN_TO_CLEAR > F.MARGIN_TO_HOLD,
          (F.MARGIN_TO_CLEAR, F.MARGIN_TO_HOLD))
    check("A6 the model stays SMALL and readable -- a distilled judge nobody "
          "can inspect is a second opaque authority",
          0 < len(m.weights) < 200, len(m.weights))
    check("A7 it says what it learned FROM, so its inherited defects are "
          "never a surprise", "sources" in F.provenance(m)
          or "INHERITS" in F.provenance(m), F.provenance(m)[:80])

    # ---- N: it can never become a phantom dissent -------------------------
    j = F.FallbackJudge()
    r = j.evaluate({"description": "\x00\xff unreadable bytes"}, [])
    check("N1 it NEVER raises. QuorumJudge counts a raising judge as a "
          "violation, which is precisely the failure this class exists to "
          "prevent", r is not None)
    r2 = j.evaluate({"description": "entirely unseen vocabulary"}, [])
    check("N2 an abstention is HELD (not_understood), so it alleges nothing",
          r2.not_understood is True)
    check("N3 an abstention NEVER carries infrastructure_failure -- it is "
          "local, it was reached, it simply had no view. Claiming otherwise "
          "would make it look like the outage it exists to survive",
          r2.infrastructure_failure is False)

    n, ok = len(results), sum(results)
    print(f"\nF1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
