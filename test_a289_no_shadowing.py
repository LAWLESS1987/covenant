#!/usr/bin/env python3
"""test_a289_no_shadowing.py -- A289: no module defines the same top-level name twice.

WHY. 2026-10-06, A278 added a function named `_sweep_running` to covenant_highway.py, where A200-A203 had
already defined one returning True/False/None. Python keeps the LATER definition for every caller, so
remedy_evict_test_mesh's `_sweep_running() is not False` met an empty list and refused every eviction for
hours. Its suite stubbed the function and never noticed. This is the forgotten step (CLAUDE.md rule 6:
grep the consumers of a name before you take it), guarded where it is forgotten: at the definition.

WHAT IT PINS. Every .py under the tree (skipping .git, .venv, .claude -- worktrees are other checkouts,
A267 -- .trash, __pycache__ and the untracked runtimes) parses, and none defines a top-level function or
class name twice. A file that does not parse is reported, not skipped silently.
"""
import ast
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", ".venv", ".claude", ".trash", "node_modules", "__pycache__"}
SKIP_PATHS = (os.path.join("tools", "llama"), os.path.join("tools", "sd"))


def scan(root):
    dups, unparsed, n = [], [], 0
    for dirpath, dirs, files in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not os.path.join(rel, d).startswith(SKIP_PATHS)]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(dirpath, f)
            try:
                tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
            except SyntaxError as e:
                unparsed.append("%s: %s" % (os.path.relpath(path, root), e.msg))
                continue
            n += 1
            seen = collections.Counter(node.name for node in tree.body
                                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
            twice = sorted(k for k, v in seen.items() if v > 1)
            if twice:
                dups.append("%s: %s" % (os.path.relpath(path, root), ", ".join(twice)))
    return n, dups, unparsed


def main():
    print("A289 -- no module defines the same top-level name twice")
    n, dups, unparsed = scan(HERE)
    ok = n > 100 and not dups
    print("  [%s] %d modules read; a top-level name defined twice in: %s" % ("PASS" if ok else "FAIL", n, dups or "none"))
    if unparsed:
        print("  note: %d file(s) did not parse and were not read: %s" % (len(unparsed), unparsed[:5]))
    print("\nA289: %d/1 passed" % (1 if ok else 0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
