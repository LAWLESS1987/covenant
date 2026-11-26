#!/usr/bin/env python3
"""LF1 -- A486: no function writes into logs/ without making the folder first. A fresh checkout has no logs/ (it is
ignored), so such a write fails there -- or, inside a try, is silently lost. Found twice: A479 (the watchdog guard's
revive) and A486 (the highway's restart remedy, where HL1 failed in a fresh checkout, and ops/hidden_task.py, whose
"fail LOUDLY" message was swallowed). Each fix repaired one instance; this guard is the tombstone for the forgotten
step, so the next one fails the build where it is written.

WHAT IT SEES: an open(...) for writing or appending whose path expression contains the literal "logs", with no
os.makedirs or Path.mkdir in the same function. WHAT IT CANNOT SEE: a log path built elsewhere and passed in as a
variable (a module-level LOG = ... then open(LOG, "a")); those are not covered. Driven both ways. Stdlib only."""
import ast
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {".git", ".trash", "pending-v8.38", "node_modules", ".venv", "__pycache__", "logs"}
fails, n = [], [0]


def check(name, cond, detail=""):
    n[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:240]))
    if not cond:
        fails.append(name)


def _opens_logs_for_write(call):
    if not (isinstance(call.func, ast.Name) and call.func.id == "open") or not call.args:
        return False
    mode = call.args[1] if len(call.args) > 1 else next((k.value for k in call.keywords if k.arg == "mode"), None)
    if not (isinstance(mode, ast.Constant) and isinstance(mode.value, str) and set(mode.value) & set("aw")):
        return False
    return any(isinstance(c, ast.Constant) and c.value == "logs" for c in ast.walk(call.args[0]))


def unguarded_log_writes(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith("lf1-")]
        for fn in fns:
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            path = os.path.join(dp, fn)
            try:
                tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                calls = [c for c in ast.walk(node) if isinstance(c, ast.Call)]
                if any(_opens_logs_for_write(c) for c in calls) and not any(
                        isinstance(c.func, ast.Attribute) and c.func.attr in ("makedirs", "mkdir") for c in calls):
                    out.append((os.path.relpath(path, root).replace(os.sep, "/"), node.name))
    return out


found = unguarded_log_writes(HERE)
check("LF1.1 GUARD: no function writes into logs/ without making the folder (A479, A486)", not found, found)

probe = tempfile.mkdtemp(prefix="lf1-")
with open(os.path.join(probe, "bad.py"), "w", encoding="utf-8") as fh:
    fh.write("import os\ndef w():\n    open(os.path.join('x', 'logs', 'a.log'), 'a').write('x')\n")
with open(os.path.join(probe, "good.py"), "w", encoding="utf-8") as fh:
    fh.write("import os\ndef w():\n    os.makedirs(os.path.join('x', 'logs'), exist_ok=True)\n"
             "    open(os.path.join('x', 'logs', 'a.log'), 'a').write('x')\n")
with open(os.path.join(probe, "read.py"), "w", encoding="utf-8") as fh:
    fh.write("import os\ndef r():\n    return open(os.path.join('x', 'logs', 'a.log')).read()\n")
check("LF1.2 the guard is seen RED on a write into logs/ with no folder made", unguarded_log_writes(probe) == [("bad.py", "w")],
      unguarded_log_writes(probe))
check("LF1.3 ...and quiet on the same write after os.makedirs, and on a plain read",
      ("good.py", "w") not in unguarded_log_writes(probe) and ("read.py", "r") not in unguarded_log_writes(probe))

print("\nLF1: %d/%d passed" % (n[0] - len(fails), n[0]))
sys.exit(1 if fails else 0)
