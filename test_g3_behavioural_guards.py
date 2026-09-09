#!/usr/bin/env python3
"""test_g3_behavioural_guards.py -- G3: a check that reads the source is not a
check, and this counts them so the number can only go down.

THE DEFECT, measured 2026-09-09 and written up as A74. Thirty-six suspected
guards were tested by mutation, each in its own git worktree: break the
behaviour the guard names, re-run, and see whether the suite notices. Thirty-five
did not. One mechanism accounts for almost all of them --

    src = inspect.getsource(mod)          # or io.open(...).read()
    check("the planner clamps the sell quantity", "sell trimmed" in src)

-- the check asserts that a STRING is present in the file. Delete the code and
leave the log line, and the check is still green. The worst instance was
`covenant_trader.plan()`: its two `qty = sellable` clamps are the only
enforcement of the 50% reserve and of the frozen HOLD_ONLY floor, and deleting
them left test_f5_reserve at 35/35 while the planner emitted a 75-unit sell of
an asset that must never be sold.

WHAT THIS FILE DOES. It parses every suite with `ast` and counts three shapes
that cannot fail for the reason their label claims:

  SOURCE-TEXT   `"literal" in src`, where src was bound from inspect.getsource()
                or from a file read. The assertion is about the file's bytes,
                not about what the program does.
  FIND-ORDER    `src.find(a) < src.find(b)`. str.find returns -1 when absent, and
                -1 is less than every real index, so the comparison is SATISFIED
                BY ABSENCE. Found live in test_a3s_send_bounds (S8d).
  SELF-OR       `(x and ...) or x`, which is just `x`. Found live in
                test_k3_p9_owner_only_guard (B2).

WHAT IT DOES NOT DO. It does not fail on the debt that exists today, because
the debt is real, documented in A74, and worth more as a ratchet than as a
blocked pipeline. It fails when the count RISES above the recorded baseline --
that is, when somebody adds a new one. Lowering the baseline is the reward for
fixing one; the file refuses to let it drift up quietly.

It also does not claim these three shapes are always wrong. A source-text
assertion is the RIGHT tool for a few things -- "this docstring still promises
X", "no line in the core imports Y" -- and those live in the baseline as
accepted. The claim is narrower and it is enough: a check of this shape cannot
tell you the code RUNS correctly, so it must never be the only guard on
behaviour.

HOW MUCH OF THE PROBLEM THIS CATCHES: 7 OF 28, AND THAT IS THE HONEST NUMBER.
It was 10 until the false positive below was fixed; three of those ten were
flagged only because the scan mistook a program's OUTPUT for its SOURCE, which
is not catching anything. Measured against the 28 files whose guards were
confirmed fake by mutation, this scan flags 7. (The measurement is taken after
those files were repaired, so it is rough in both directions -- a repaired file
may no longer carry the grep that would have flagged it.) It misses the rest,
because they fail SEMANTICALLY rather than syntactically, and no AST pattern can
see the difference:

    the test re-implements its subject and checks the copy   (test_r2's flagged())
    the fixture is hand-copied from the answer               (sem5's FORMAL tuple)
    only the except-branch ever runs, so the gate is never
      once observed ADMITTING anything                       (b2's E3)
    the assertion is real but aimed at the wrong region      (a22's P1)

So this file is a ratchet on ONE shape -- the commonest, and the only one a
machine can find -- and it must not be read as coverage of A74. The other
mechanisms are caught by mutation testing, which is slow, needs a worktree per
mutant, and is a person's decision to run. Nothing here replaces it.

What it did earn on its first run: 18 files that nobody had audited, including a
FIND-ORDER in test_sentinel_gate.py:188 of exactly the shape that made A3s's S8d
satisfiable by absence. Those are leads, not findings -- a flag here means
"prove this one by mutation", never "this one is broken".

Run:  python test_g3_behavioural_guards.py            count, compare, exit 0/1
      python test_g3_behavioural_guards.py --report   per-file listing
      python test_g3_behavioural_guards.py --accept   rewrite the baseline
LICENCE: public domain.
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "ops", "G3_BASELINE.json")

# Suites are test_*.py, plus the module selftests the 15-minute check runs.
EXTRA = ("covenant_moltbook.py", "covenant_moltbook_release.py",
         "covenant_judge_defer.py", "covenant_sentinels.py",
         "trader_freshness.py", "covenant_selfaudit.py")


def _reads_python(call):
    """True if this .read() is reading PROGRAM TEXT rather than program OUTPUT.

    FALSE POSITIVE FOUND ON THIS FILE'S FIRST LIVE RUN, 2026-09-09. The first
    version counted every `x = <anything>.read()` and then flagged
    `"NODES DOWN" in wrote`, where `wrote` was guard.log -- the log the program
    under test had just WRITTEN. That is a behavioural assertion of the best
    kind: run the thing, read what it actually emitted, check the content. The
    ratchet would have marked it as debt and pushed the author back toward a
    grep, which is the exact opposite of what this file is for. A guard that
    punishes the right answer is worse than no guard.

    So the test is narrow: the path being opened must name a .py file, or
    __file__. Reading a log, a ledger, a JSON artefact or a captured stdout is
    evidence and is left alone.
    """
    for sub in ast.walk(call):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            if sub.value.endswith(".py"):
                return True
        if isinstance(sub, ast.Name) and sub.id == "__file__":
            return True
    return False


def _source_names(tree):
    """Names bound to the TEXT of a source file.

    Two shapes, both live in this repo:
        src = inspect.getsource(mod)
        src = io.open(os.path.join(HERE, "thing.py"), encoding="utf-8").read()
    """
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        v = node.value
        got = False
        if isinstance(v, ast.Call):
            fn = v.func
            # inspect.getsource(...) / getsource(...) -- always program text
            if isinstance(fn, ast.Attribute) and fn.attr == "getsource":
                got = True
            elif isinstance(fn, ast.Name) and fn.id == "getsource":
                got = True
            # <open(...)>.read() -- program text only if it opens a .py
            elif isinstance(fn, ast.Attribute) and fn.attr == "read":
                got = _reads_python(v)
        if not got:
            continue
        for t in node.targets:
            if isinstance(t, ast.Name):
                out.add(t.id)
    return out


def _base(node):
    """The root Name of an expression like src.find(x) -> 'src'."""
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else None


def scan(path):
    """-> list of (lineno, kind, snippet)."""
    try:
        text = io.open(path, encoding="utf-8").read()
        tree = ast.parse(text)
    except (OSError, SyntaxError):
        return []
    lines = text.splitlines()
    names = _source_names(tree)
    hits = []

    def snip(n):
        i = getattr(n, "lineno", 1) - 1
        return lines[i].strip()[:100] if 0 <= i < len(lines) else ""

    for node in ast.walk(tree):
        # SELF-OR: (x and ...) or x
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            plain = {v.id for v in node.values if isinstance(v, ast.Name)}
            for v in node.values:
                if isinstance(v, ast.BoolOp) and isinstance(v.op, ast.And):
                    inner = {w.id for w in v.values if isinstance(w, ast.Name)}
                    if inner & plain:
                        hits.append((node.lineno, "SELF-OR", snip(node)))
                        break
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        op, right = node.ops[0], node.comparators[0]
        # FIND-ORDER: a.find(..) < b.find(..)  -- true when either is absent
        if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            def isfind(x):
                return (isinstance(x, ast.Call)
                        and isinstance(x.func, ast.Attribute)
                        and x.func.attr in ("find", "rfind"))
            if isfind(node.left) and isfind(right):
                hits.append((node.lineno, "FIND-ORDER", snip(node)))
                continue
        # SOURCE-TEXT: "literal" in src
        if isinstance(op, ast.In) and _base(right) in names:
            if isinstance(node.left, (ast.Constant, ast.JoinedStr)):
                hits.append((node.lineno, "SOURCE-TEXT", snip(node)))
    return hits


def survey():
    files = sorted(f for f in os.listdir(HERE)
                   if (f.startswith("test_") and f.endswith(".py")) or f in EXTRA)
    return {f: scan(os.path.join(HERE, f)) for f in files if scan(os.path.join(HERE, f))}


def main():
    found = survey()
    per = {f: len(h) for f, h in sorted(found.items())}
    total = sum(per.values())

    if "--report" in sys.argv[1:]:
        for f, hits in sorted(found.items()):
            print("\n%s  (%d)" % (f, len(hits)))
            for ln, kind, s in hits:
                print("  %-11s :%-5d %s" % (kind, ln, s))
        print("\ntotal %d across %d files" % (total, len(found)))
        return 0

    if "--accept" in sys.argv[1:]:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        io.open(BASELINE, "w", encoding="utf-8").write(
            json.dumps({"total": total, "per_file": per}, indent=1, sort_keys=True))
        print("baseline written: %d across %d files" % (total, len(per)))
        return 0

    try:
        base = json.load(io.open(BASELINE, encoding="utf-8"))
    except OSError:
        print("G3: no baseline at %s -- run --accept once" % BASELINE)
        return 1

    fails = []
    if total > base.get("total", 0):
        fails.append("total rose %d -> %d" % (base.get("total", 0), total))
    for f, n in sorted(per.items()):
        was = base.get("per_file", {}).get(f, 0)
        if n > was:
            fails.append("%s rose %d -> %d" % (f, was, n))

    if fails:
        print("G3: FAIL -- a check that reads the source is not a check (A74)")
        for x in fails:
            print("   %s" % x)
        print("   run --report to see them; if one is deliberate and correct,")
        print("   run --accept to move the baseline and say why in the commit")
        return 1
    drop = base.get("total", 0) - total
    print("G3: %d source-text/tautology assertions across %d files, baseline %d%s"
          % (total, len(per), base.get("total", 0),
             " (DOWN %d -- rerun --accept to lock it in)" % drop if drop > 0 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
