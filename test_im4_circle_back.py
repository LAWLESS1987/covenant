#!/usr/bin/env python3
"""test_im4_circle_back.py -- the circle-back guard for the improve-miner's 'have' verdicts, both ways.

    python test_im4_circle_back.py   -> "IM4: n/n passed"

A 'have' verdict names a killing term Y but nothing read it back (operator 2026-10-28). After two outside
reviews (ChatGPT, DeepSeek) the guard clears a 'have' ONLY by an explicit DISPOSITION keyed to the candidate
id (verified_have / false_match / unresolved), never by a commit coincidentally mentioning the keyword; N runs
is an escalation window, a term-less have is a miner defect, grandfathered rows get a sunset, and a term that
false-matches repeatedly is a dedup-vocabulary bug. Driven both ways with injected rows and dispositions; it
reads only and resurrects nothing.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve as CI   # noqa: E402

R = []


def check(name, ok, detail=""):
    R.append(bool(ok))
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  -- %s" % (str(detail)[:300],)))


WHY = "a capability keyword already appears in source (dedup): %s @ %s"
# distinct run-days so _runs_after(the first) is controllable -- POST the term-naming fix (so not grandfathered)
D = tuple("2026-11-%02dT07:00:00Z" % d for d in range(1, 16))   # Nov 1..15, all after the 2026-10-28 fix


def have(cid, term, file, t, why=None):
    return {"id": cid, "idea": cid, "kind": "gap", "vet": "have",
            "why": why if why is not None else (WHY % (term, file)), "t": t}


def fillers(n, start=1):
    """n have-rows on distinct later days, to push _runs_after of a day-10 row to >= n."""
    return [have("f%d" % i, "alpha%d" % i, "y.py", D[start + i]) for i in range(n)]


def main():
    print("IM4 -- circle-back guard (disposition model), both ways\n")
    TODAY = "2026-10-24"

    # ---- parsing ----
    check("IM4.1 have_killing_term parses '<term> @ <file>'",
          CI.have_killing_term(WHY % ("joins", "build_semantic_model.py")) == ("joins", "build_semantic_model.py"))
    check("IM4.1 a have with no named term parses to (None, None)",
          CI.have_killing_term("a capability keyword already appears in source (dedup)") == (None, None))

    old = have("c1", "joins", "x.py", D[0])
    rows = [old] + fillers(3)                                   # _runs_after(old) == 3 (meets n_runs)

    # ---- CLEARED only by a well-formed disposition keyed to the candidate id ----
    verified = {"c1": {"candidate_id": "c1", "outcome": "verified_have", "anchor": "covenant_improve.py:118",
                       "rationale": "the dedup already lives in vet()", "author": "t", "t": D[4]}}
    check("IM4.2 a verified_have disposition (real anchor + rationale) CLEARS -> ok",
          CI.circle_back(rows=rows, dispositions=verified, today=TODAY)["ok"], None)
    fmatch = {"c1": {"candidate_id": "c1", "outcome": "false_match", "term": "joins",
                     "rationale": "generic word; spurious", "author": "t", "t": D[4]}}
    check("IM4.3 a false_match disposition (term + rationale) CLEARS -> ok",
          CI.circle_back(rows=rows, dispositions=fmatch, today=TODAY)["ok"], None)
    held = {"c1": {"candidate_id": "c1", "outcome": "unresolved", "recheck": "2026-12-01",
                   "rationale": "needs review", "author": "t", "t": D[4]}}
    check("IM4.4 an unresolved disposition with a FUTURE recheck HOLDS -> ok",
          CI.circle_back(rows=rows, dispositions=held, today=TODAY)["ok"], None)
    stale = {"c1": {"candidate_id": "c1", "outcome": "unresolved", "recheck": "2026-10-01",
                    "rationale": "x", "author": "t", "t": D[4]}}
    check("IM4.5 an unresolved disposition PAST its recheck no longer holds -> escalate (not ok)",
          not CI.circle_back(rows=rows, dispositions=stale, today=TODAY)["ok"], None)
    bad = {"c1": {"candidate_id": "c1", "outcome": "verified_have", "anchor": "no_such_file_zzz.py:1",
                  "rationale": "r", "author": "t", "t": D[4]}}
    check("IM4.6 a verified_have whose anchor FILE is missing does NOT clear -> escalate",
          not CI.circle_back(rows=rows, dispositions=bad, today=TODAY)["ok"], None)

    # ---- no disposition: escalate past the window, grace within it ----
    check("IM4.7 a have with no disposition, >=3 runs old -> ESCALATE (not ok)",
          not CI.circle_back(rows=rows, dispositions={}, today=TODAY)["ok"], None)
    check("IM4.8 a have within the grace window (<3 later runs) is NOT escalated",
          CI.circle_back(rows=[old] + fillers(1), dispositions={}, today=TODAY)["ok"], None)

    # ---- miner defect vs grandfathering ----
    noterm_new = [have("c2", None, None, "2026-11-01T07:00:00Z",
                       why="a capability keyword already appears in source (dedup)")]
    check("IM4.9 a term-less have AFTER the fix is a MINER DEFECT (not ok)",
          not CI.circle_back(rows=noterm_new, dispositions={}, fix_iso="2026-10-28T13:29:21Z", today=TODAY)["ok"], None)
    gf = [have("c3", None, None, "2026-10-28T07:59:47Z",
               why="a capability keyword already appears in source (dedup)")]
    check("IM4.10 a term-less have BEFORE the fix is grandfathered within sunset -> ok",
          CI.circle_back(rows=gf, dispositions={}, fix_iso="2026-10-28T13:29:21Z", sunset_runs=30, today=TODAY)["ok"], None)
    gf_old = [have("c3", None, None, "2026-10-20T07:00:00Z",
                   why="a capability keyword already appears in source (dedup)")] + fillers(3)
    check("IM4.11 a grandfathered have PAST sunset must be dispositioned -> escalate",
          not CI.circle_back(rows=gf_old, dispositions={}, fix_iso="2026-10-28T13:29:21Z", sunset_runs=2, today=TODAY)["ok"], None)

    # ---- repeated false_match on a term = a dedup-vocabulary bug to demote ----
    many = {"d%d" % i: {"candidate_id": "d%d" % i, "outcome": "false_match", "term": "joins",
                        "rationale": "generic", "author": "t", "t": D[4]} for i in range(3)}
    demote = CI.circle_back(rows=[], dispositions=many, today=TODAY)["demote_terms"]
    check("IM4.12 a term with >=%d false_match dispositions is flagged for stopword demotion" % CI.FALSE_MATCH_STOPWORD_K,
          "joins" in demote, demote)

    # ---- the LIVE backlog passes (legacy grandfathered or dispositioned) ----
    check("IM4.13 the live backlog passes the guard", CI.circle_back()["ok"], CI.circle_back())

    ok = sum(R)
    print("\nIM4: %d/%d passed" % (ok, len(R)))
    print("LIMIT: dispositions are injected here. The live guard (python covenant_improve.py --circle-back and "
          "the nightly soft report) reads ops/have_dispositions.jsonl + the backlog. This tests the enforcement "
          "logic, not any finding.")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
