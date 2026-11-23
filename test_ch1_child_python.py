#!/usr/bin/env python3
"""CH1 -- tools/child_python.py, and the guard that keeps the venv-launcher pid mistake from coming back (A479).

WHY. A274 (2026-10-06) wrote down in prose that a Windows venv's python.exe is a launcher whose child runs the code.
RR1.7 (A459, 2026-11-19) compared a lock holder's pid with Popen's pid anyway, and failed on every Windows venv while
Linux CI stayed green; found 2026-11-23. Eleven of twelve quorum seats asked for one helper that learns the real pid
and a guard that makes tests use it. This suite drives the helper on this machine's real topology and fails on any
test file that compares a Popen object's pid with a pid string.

    python test_ch1_child_python.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import child_python as CP  # noqa: E402

n_fail = n_total = 0


def check(name, ok, detail=""):
    global n_fail, n_total
    n_total += 1
    print(("ok   " if ok else "FAIL ") + name + (("  -- %s" % (detail,)) if detail else ""))
    if not ok:
        n_fail += 1


# CH1.1-3 the helper on this machine's real topology
p, pid, ppid = CP.start("import os, time; print('again %d' % os.getpid(), flush=True); time.sleep(60)")
again = CP.readline(p, 30)
check("CH1.1 the pid the handshake gives is the pid of the process running the code", again == "again %d" % pid,
      (again, pid))
launcher = os.name == "nt" and os.path.normcase(sys.executable) != os.path.normcase(getattr(sys, "_base_executable",
                                                                                            sys.executable))
if launcher:
    check("CH1.2 a Windows venv: the code runs in the launcher's child, so Popen's pid is NOT the real one, and the "
          "real one's parent IS Popen's", pid != p.pid and ppid == p.pid, (pid, ppid, p.pid))
else:
    check("CH1.2 no launcher here: Popen's pid is the real one", pid == p.pid, (pid, p.pid))
check("CH1.3 kill() ends the real process, and alive() says so", CP.kill(p, pid) and not CP.alive(pid), pid)

# CH1.4 a child that never sends the handshake fails in bounded time and is not left running
import time  # noqa: E402
t0 = time.time()
old = CP._PREAMBLE
CP._PREAMBLE = ""                       # a child that never sends the handshake
try:
    CP.start("import time; time.sleep(60)", timeout=2)
    raised = None
except Exception as e:                                           # noqa: BLE001
    raised = e
finally:
    CP._PREAMBLE = old
check("CH1.4 no handshake within the timeout raises TimeoutError in bounded time (never hangs)",
      isinstance(raised, TimeoutError) and time.time() - t0 < 45, repr(raised))

# CH1.5 the guard: no test compares a Popen object's pid with a pid string. The shape is the one RR1.7 had:
#     ("pid %d" % child.pid) in whox
# Narrow on purpose: taskkill /PID <p.pid> and printing a pid are fine; naming a holder by Popen's pid is not.
SHAPE = re.compile(r"""["']pid %d["']\s*%\s*\w+\.pid\b""")


def offenders(texts):
    return sorted(name for name, text in texts.items()
                  if any(SHAPE.search(line) for line in text.splitlines() if not line.lstrip().startswith("#")))


texts = {}
for f in sorted(os.listdir(HERE)):
    if f.startswith("test_") and f.endswith(".py") and f != os.path.basename(__file__):
        with open(os.path.join(HERE, f), encoding="utf-8", errors="replace") as fh:
            texts[f] = fh.read()
bad = offenders(texts)
check("CH1.5 no test names a holder by Popen's pid (use tools/child_python.py)", not bad, bad)
probe = {"test_probe.py": "    check('x', ('pid %d' % child.pid) in whox)\n"}
check("CH1.5b ...and the guard catches the RR1.7 shape as it was written", offenders(probe) == ["test_probe.py"])
check("CH1.5c ...but not taskkill by Popen's pid, which is fine",
      not offenders({"t.py": 'subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)])\n'}))

print("\nCH1: %d/%d passed" % (n_total - n_fail, n_total))
sys.exit(1 if n_fail else 0)
