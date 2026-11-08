#!/usr/bin/env python3
"""IM8 -- no improvement-miner function may bind a live ledger path as a FROZEN default argument.

The tombstone for a SHAPE, not an instance (CLAUDE.md rule 10: "a mistake that is a forgotten step ... its
tombstone is a guard at the place the step is forgotten, which runs every time, and is tested both ways").

History. `def f(path=SOME_PATH)` evaluates SOME_PATH once, when the module loads. A test that later reassigns
the module global to a temp file does NOT redirect f -- f still writes to the real file under ops/.
  * 2026-10-27: harvest() in covenant_improve_mine.py had it; a test hit the real file. Fixed (call-time
    resolution) -- the INSTANCE was repaired and nothing was left to stop the next one.
  * 2026-10-27..10-29: extract()/_append() in covenant_improve_extract.py had the same shape. test_im3 reached it
    through nightly() and appended 120 fixture rows (authors carol/dave/f0..f7, "keep join keys") to the LIVE
    ops/improve_candidates.jsonl while printing "15/15 passed". Reproduced 2026-11-04 (239 -> 249 rows on one run).

What this checks: every covenant_improve*.py module found ON DISK (rule 2: by discovery, not a list), parsed with
`ast`. A "path constant" is a module-level ALL_CAPS name assigned from os.path.join(...). A function default
that is a bare reference to one is a frozen path -> FAIL.

What it cannot see (rule 9): a frozen path reached any other way -- a default that is an attribute (mod.PATH), a
call (`_default()`), a path built inside a lambda default, a constant assigned from something other than
os.path.join, a lowercase constant, a constant assigned inside an if/try block rather than at module top level,
or a module outside the covenant_improve* family. Those would read green here (each driven in the 2026-11-04
stress pass and confirmed to read green, so this list is measured, not guessed).

Both ways: a synthetic module WITH a frozen path default must be flagged, a clean one must not, and the live
modules must be clean. Offline; reads source only.
"""
import ast, glob, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _is_join(node):
    """os.path.join(...) -- the shape every ledger constant in this family is built with."""
    f = getattr(node, "func", None)
    return (isinstance(node, ast.Call) and isinstance(f, ast.Attribute) and f.attr == "join"
            and isinstance(f.value, ast.Attribute) and f.value.attr == "path"
            and isinstance(f.value.value, ast.Name) and f.value.value.id == "os")


def frozen_path_defaults(source, name="<src>"):
    """[(module, function, param, constant)] for every function default that is a bare module path constant."""
    tree = ast.parse(source, filename=name)
    consts = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and _is_join(node.value):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper():
                    consts.add(t.id)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        a = node.args
        pos = a.posonlyargs + a.args
        pairs = list(zip(pos[len(pos) - len(a.defaults):], a.defaults))
        pairs += [(k, d) for k, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None]
        for arg, d in pairs:
            if isinstance(d, ast.Name) and d.id in consts:
                hits.append((name, node.name, arg.arg, d.id))
    return hits


def main():
    fails = []
    checks = 0

    # ---- way 1: the detector FIRES on the exact shape that leaked ----
    bad = ('import os\nHERE = "."\nOUT = os.path.join(HERE, "ops", "x.jsonl")\n'
           'def extract(limit=20, out=OUT):\n    pass\n'
           'def kw(*, path=OUT):\n    pass\n')
    checks += 1
    got = frozen_path_defaults(bad, "bad.py")
    if sorted((h[1], h[2]) for h in got) != [("extract", "out"), ("kw", "path")]:
        fails.append("detector must flag both a positional and a keyword-only frozen path default, got %r" % got)

    # ---- way 2: it stays QUIET on call-time resolution and on non-path defaults ----
    good = ('import os\nHERE = "."\nOUT = os.path.join(HERE, "ops", "x.jsonl")\nMAX = 20\n'
            'def extract(limit=MAX, out=None):\n    out = OUT if out is None else out\n')
    checks += 1
    got = frozen_path_defaults(good, "good.py")
    if got:
        fails.append("detector must not flag out=None or a non-path constant (MAX), got %r" % got)

    # ---- live: every covenant_improve*.py on disk, found by discovery ----
    mods = sorted(glob.glob(os.path.join(HERE, "covenant_improve*.py")))
    checks += 1
    if len(mods) < 3:
        fails.append("expected the miner family on disk (mine/extract/orchestrator), found %d: %r"
                     % (len(mods), [os.path.basename(m) for m in mods]))
    live = []
    for m in mods:
        with open(m, encoding="utf-8") as f:
            live += frozen_path_defaults(f.read(), os.path.basename(m))
    checks += 1
    for mod, fn, arg, const in live:
        fails.append("%s: %s(%s=%s) binds a live path at import; resolve it at call time (default None)"
                     % (mod, fn, arg, const))

    if fails:
        print("IM8 FAIL:")
        for x in fails:
            print("  -", x)
        return 1
    print("IM8: %d/%d passed -- %d covenant_improve*.py modules read, 0 frozen ledger-path defaults; detector "
          "fires on the leaked shape and stays quiet on call-time resolution. Blind to attribute/call/lambda "
          "defaults and to modules outside the family." % (checks, checks, len(mods)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
