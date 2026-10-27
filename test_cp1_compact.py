#!/usr/bin/env python3
"""CP1 (2026-10-03): the nightly keeps the repository compact, and deletes nothing doing it.

His words: "efficency is important as is compactness". Measured that day: 133.0 MB -> 17.4 MB from one
`git gc --prune=never`. These checks drive covenant_nightly.compact_step with git stubbed both ways, read
its wiring into main() from the AST (the PP1.11d idiom), and run the real compaction on a SCRATCH repo
to prove --prune=never keeps an unreachable object.

    python test_cp1_compact.py
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_nightly as N  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


print("CP1 -- the repository stays compact, nothing deleted")
check("CP1.1 the command compacts and never prunes", N.COMPACT_ARGV[:2] == ["git", "gc"]
      and "--prune=never" in N.COMPACT_ARGV and not any(a.startswith("--prune=") and a != "--prune=never" for a in N.COMPACT_ARGV),
      N.COMPACT_ARGV)
said, seen = [], []
sizes = iter([133.0, 17.4])
r = N.compact_step(said.append, run=lambda argv: seen.append(argv) or 0, measure=lambda: next(sizes))
check("CP1.2 a good run reports before -> after and runs exactly the never-prune command",
      r == (133.0, 17.4) and seen == [N.COMPACT_ARGV] and any("133.0 MB -> 17.4 MB" in s for s in said), (r, said))
said2 = []
r2 = N.compact_step(said2.append, run=lambda argv: 128, measure=lambda: 50.0)
check("CP1.3 git failing is said as FAILED with the size unchanged, never raised",
      r2 is None and any("compact FAILED: git gc exited 128" in s for s in said2), said2)
said3 = []
r3 = N.compact_step(said3.append, run=lambda argv: (_ for _ in ()).throw(OSError("no git")), measure=lambda: 1.0)
check("CP1.4 an exception is said, not raised -- a nightly step must not end the pass",
      r3 is None and any("compact FAILED: OSError" in s for s in said3), said3)

tree = ast.parse(open(N.__file__, encoding="utf-8").read())
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
direct = [s for s in main.body if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
          and getattr(s.value.func, "id", "") == "compact_step"]
check("CP1.5 main() calls compact_step unconditionally, at its own top level (AST)", len(direct) == 1, len(direct))

if shutil.which("git"):
    td = tempfile.mkdtemp(prefix="cp1_")
    try:
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
        g = lambda *a: subprocess.run(["git", "-C", td] + list(a), capture_output=True, text=True, env=env)  # noqa: E731
        g("init", "-q")
        open(os.path.join(td, "a.txt"), "w").write("kept\n")
        g("add", "a.txt")
        g("commit", "-q", "-m", "one")
        p = subprocess.run(["git", "-C", td, "hash-object", "-w", "--stdin"], input="unreachable but kept\n",
                           capture_output=True, text=True, env=env)
        orphan = p.stdout.strip()
        rc = subprocess.run(["git", "-C", td] + N.COMPACT_ARGV[1:], capture_output=True, env=env).returncode
        still = g("cat-file", "-e", orphan).returncode == 0
        check("CP1.6 on a real scratch repo the command succeeds and an UNREACHABLE object survives it",
              rc == 0 and still, (rc, still))
    finally:
        shutil.rmtree(td, ignore_errors=True)
else:
    print("  NOT RUN CP1.6: no git on this machine")

print("\nCP1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
