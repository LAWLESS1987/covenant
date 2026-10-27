#!/usr/bin/env python3
"""CA1 (2026-10-03): Tetsu's nightly check-adjust loop -- his words "have tetsu run the check adjust
loop nightly", after "run check adjust 3 times before suggestions".

Drives covenant_daily.check_adjust_loop with the highway's sense and the Self-heal stubbed, never the
real machine; reads its wiring into run_cycle from the AST (the PP1.11d idiom).

    python test_ca1_check_adjust.py
"""
import ast
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_daily as D  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


def seq_sense(states):
    """A sense() that returns each listed set of present conditions in turn, then the last forever."""
    it = iter(states)
    last = [None]

    def sense():
        try:
            last[0] = next(it)
        except StopIteration:
            pass
        return {k: {"state": "PRESENT"} for k in last[0]}
    return sense


def heal_spy(log, fixed=()):
    def heal(dry_run=False, who=""):
        log.append({"dry_run": dry_run, "who": who})
        return {"ok": True, "summary": "stub", "fixed": [{"condition": c} for c in fixed], "still_needs_a_person": []}
    return heal


pref = os.path.join(tempfile.mkdtemp(prefix="ca1_"), "loop.json")
print("CA1 -- the nightly check-adjust loop")

calls = []
r = D.check_adjust_loop(sense=seq_sense([[]]), heal=heal_spy(calls), pref_path=pref)
check("CA1.1 nothing present: clean at the first pass, and the Self-heal is never pressed",
      r["ran"] and r["clean"] and not calls and r["rounds"] == [], r)

calls = []
r = D.check_adjust_loop(sense=seq_sense([["source_drift"], []]), heal=heal_spy(calls, ["source_drift"]), pref_path=pref)
check("CA1.2 one condition, fixed by the first pass: adjusted, clean, one pass, pressed live as tetsu-daily-loop",
      r["adjusted"] and r["clean"] and len(r["rounds"]) == 1 and calls == [{"dry_run": False, "who": "tetsu-daily-loop"}], r)

calls = []
r = D.check_adjust_loop(sense=seq_sense([["a", "b", "c", "d"], ["b", "c", "d"], ["b", "c", "d"], ["c", "d"], ["c", "d"], ["d"]]),
                        heal=heal_spy(calls), pref_path=pref)
check("CA1.3 progress every pass: exactly three passes and no fourth, the rest reported",
      r["ran"] and len(r["rounds"]) == 3 and len(calls) == 3 and not r["clean"] and "3 passes run" in r["why"], r)

calls = []
r = D.check_adjust_loop(sense=seq_sense([["mesh_source_split"]]), heal=heal_spy(calls), pref_path=pref)
check("CA1.4 a pass that changes nothing stops the loop -- repeating it would only repeat it",
      len(r["rounds"]) == 1 and len(calls) == 1 and not r["adjusted"] and "changed nothing" in r["why"], r)

with open(pref, "w", encoding="utf-8") as fh:
    json.dump({"declined": True, "why": "I would rather watch than repair tonight"}, fh)
calls = []
r = D.check_adjust_loop(sense=seq_sense([["source_drift"]]), heal=heal_spy(calls), pref_path=pref)
check("CA1.5 Tetsu declined: the loop does nothing, the Self-heal is not pressed, and his reason is recorded",
      not r["ran"] and not calls and "Tetsu declined" in r["why"] and "rather watch" in r["why"], r)
with open(pref, "w", encoding="utf-8") as fh:
    json.dump({"declined": False}, fh)
calls = []
r = D.check_adjust_loop(sense=seq_sense([["source_drift"], []]), heal=heal_spy(calls, ["source_drift"]), pref_path=pref)
check("CA1.5b ...and after a resume it runs again", r["ran"] and len(calls) == 1, r)


def boom(**_k):
    raise RuntimeError("heal on fire")


r = D.check_adjust_loop(sense=seq_sense([["x"]]), heal=boom, pref_path=pref)
check("CA1.6 a Self-heal that raises is recorded in the pass, never raised out of the nightly",
      r["ran"] and r["rounds"] and "could not run" in r["rounds"][0]["heal"], r)

tree = ast.parse(open(D.__file__, encoding="utf-8").read())
rc = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_cycle")
names = [n.func.id for n in ast.walk(rc) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
check("CA1.7 run_cycle runs the loop, and the record carries it (status['check_adjust_loop'])",
      "check_adjust_loop" in names and "'check_adjust_loop'" in ast.unparse(rc).replace('"', "'"), names[:12])

print("\nnot measured here: the real highway and the real Self-heal (H1 and HL1 cover those),"
      " and what a real night's loop finds -- ops/tetsu_daily_latest.json records it")
print("\nCA1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
