#!/usr/bin/env python3
"""A303 -- a semantic veto that could never fire is refused, never silently ignored.

Found by the collective's independent review of this repository (issue #4, round 1): Codex's CXR-1, reproduced by
Claude on a second OS, admitted by Claude and Tetsu. QuorumJudge raised on a misspelled REQUIRED judge but not on a
misspelled SEMANTIC judge, nor on a threshold above the number of semantic seats; either one switched the semantic
veto off, and a payload a semantic judge refused was admitted.

  V1  at construction: a misspelled semantic id, an unreachable threshold, and a threshold that is not a whole
      number >= 1 each raise; every valid shape constructs, including the two "off on purpose" shapes (a
      threshold with no ids yet -- test_j1 sets the ids afterwards -- and ids with no threshold)
  V2  at evaluation: ids or a threshold set AFTER construction that disable the veto fail CLOSED, labelled a
      configuration failure (infrastructure_failure, the reason in the summary), never a conviction
  V3  the veto still works: one semantic dissent at threshold 1 blocks; all clean admits
  V4  build_semantic_quorum's explicit threshold argument is the same door: an unreachable one raises
  V5  Codex's two admitting cases (misspelled id; threshold 2 for one seat) no longer admit
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C           # noqa: E402

ok = []


def check(label, cond, detail=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", label, "" if cond else "  -- %s" % (detail,)), flush=True)


def seat(jid, violates=False):
    class J(C.ReasoningJudge):
        def __init__(self):
            self.judge_id = jid

        def evaluate(self, d, p):
            return C.JudgmentResult(violates, "fixture", judge_id=jid)
    return J()


def raises(fn):
    try:
        fn()
    except ValueError as e:
        return str(e)
    return None


print("A303 -- a semantic veto that could never fire is refused")
clean, dissent = seat("clean:0"), seat("semantic:0", True)
Q = C.QuorumJudge
check("V1 a misspelled semantic id raises at construction",
      "not present" in (raises(lambda: Q([clean, dissent], min_agree=1, semantic_judge_ids={"semnatic:0"},
                                         semantic_veto_threshold=1)) or ""))
check("V1 a threshold above the semantic seats present raises",
      "could never fire" in (raises(lambda: Q([clean, dissent], min_agree=1, semantic_judge_ids={"semantic:0"},
                                              semantic_veto_threshold=2)) or ""))
bad = [raises(lambda t=t: Q([clean, dissent], min_agree=1, semantic_judge_ids={"semantic:0"}, semantic_veto_threshold=t))
       for t in (0, -1, True, 1.5)]
check("V1 a threshold that is not a whole number >= 1 raises (0, -1, True, 1.5)", all(b and "whole number" in b for b in bad), bad)
fine = [raises(lambda: Q([clean, dissent], min_agree=1, semantic_judge_ids={"semantic:0"}, semantic_veto_threshold=1)),
        raises(lambda: Q([clean, dissent], semantic_veto_threshold=1)),
        raises(lambda: Q([clean, dissent], semantic_judge_ids={"semantic:0"})),
        raises(lambda: Q([clean, dissent], min_agree=1, semantic_judge_ids={"clean:0", "semantic:0"}, semantic_veto_threshold=2))]
check("V1 every valid shape constructs, and both 'off on purpose' shapes (threshold without ids; ids without threshold)",
      fine == [None, None, None, None], fine)

late = Q([clean, seat("semantic:0")], min_agree=1, semantic_veto_threshold=1)
late.semantic_judge_ids = {"semnatic:0"}
r = late.evaluate({}, [])
check("V2 a misspelled id set AFTER construction fails closed at evaluation, as a configuration failure "
      "(every seat clean, so nothing but the misconfiguration blocks)",
      r.violates and r.infrastructure_failure and "semantic veto misconfigured" in r.reasoning, (r.violates, r.reasoning[:120]))
late_d = Q([clean, dissent], min_agree=1, semantic_veto_threshold=1)
late_d.semantic_judge_ids = {"semnatic:0"}
rd = late_d.evaluate({}, [])
check("V2 ...and with a seat that really dissents it blocks and stays an allegation (B3: a real dissent is never relabelled)",
      rd.violates and not rd.infrastructure_failure and "semantic veto misconfigured" in rd.reasoning, (rd.violates, rd.infrastructure_failure))
late2 = Q([clean, seat("semantic:1")], min_agree=1, semantic_judge_ids={"semantic:1"}, semantic_veto_threshold=1)
late2.semantic_veto_threshold = 3
r2 = late2.evaluate({}, [])
check("V2 an unreachable threshold set AFTER construction fails closed although every seat is clean",
      r2.violates and r2.infrastructure_failure and "could never fire" in r2.reasoning, (r2.violates, r2.reasoning[:120]))

ok_q = Q([clean, dissent], min_agree=1, semantic_judge_ids={"semantic:0"}, semantic_veto_threshold=1)
r3 = ok_q.evaluate({}, [])
r4 = Q([clean, seat("semantic:0")], min_agree=1, semantic_judge_ids={"semantic:0"}, semantic_veto_threshold=1).evaluate({}, [])
check("V3 the veto still works: one semantic dissent at threshold 1 blocks (a conviction, not a config failure); "
      "all clean admits", r3.violates and not r3.infrastructure_failure and not r4.violates, (r3.violates, r4.violates))

e4 = raises(lambda: C.build_semantic_quorum(["claude"], semantic_veto_threshold=2))
ok4 = raises(lambda: C.build_semantic_quorum(["claude"], semantic_veto_threshold=1))
check("V4 build_semantic_quorum's explicit threshold is the same door: 2 for one semantic seat raises; 1 builds",
      e4 is not None and "could never fire" in e4 and ok4 is None, (e4, ok4))

admits = []
for kw in ({"semantic_judge_ids": {"semnatic:0"}, "semantic_veto_threshold": 1},
           {"semantic_judge_ids": {"semantic:0"}, "semantic_veto_threshold": 2}):
    try:
        admits.append(Q([clean, dissent], min_agree=1, **kw).evaluate({}, []).violates is False)
    except ValueError:
        admits.append(False)
check("V5 Codex's two admitting cases no longer admit", admits == [False, False], admits)

print("\nnot measured here: a deployed node's own configuration (build_semantic_quorum derives ids from the seats it builds).")
print("\nA303: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
