"""RR1 -- one rolling restart at a time, held by the OS (A459).

2026-11-19: a rolling_restart.py started by hand and the highway's remedy_restart_nodes (which starts the same
script detached on source drift) began within two seconds of each other. Both restarted node A, and node A ran
as two processes on one database for about an hour and three quarters. The script had no lock at all.

The first lock (O_EXCL file, stale ones moved to .stale and taken over) let two runs both hold it after a crash
left a lock behind (tombstone A459-STALE-TAKEOVER). The lock is now an OS lock that the OS drops when its holder
dies, so there is no takeover. RR1.6 is that case; RR1.7 to RR1.9 use a real second process.

Every check runs against a temp lock file. Nothing reaches a node: probe, restart_one and status are replaced in
the module before main() is called, and the replacement records any call so the test can see it."""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rolling_restart as RR  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -- %s" % (detail,)))


def tmp_lock():
    return os.path.join(tempfile.mkdtemp(prefix="rr1_"), "rolling_restart.lock")


def note_pid(path):
    """The pid the lock file's note names, or None: a broken lock makes a check FAIL by name, never crash."""
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8")).get("pid")
    except (OSError, ValueError, AttributeError):
        return None


# 1. one holder at a time, and the refusal names it
p = tmp_lock()
ok1, _ = RR.take_lock(p)
ok2, who = RR.take_lock(p)
check("RR1.1 the first run takes the lock and a second is refused, naming the holder",
      ok1 and not ok2 and ("pid %d" % os.getpid()) in who, (ok1, ok2, who))
check("RR1.2 the lock file says which process holds it", note_pid(p) == os.getpid())
check("RR1.3 the handle the lock is held by is not inheritable, so a node this run starts never holds it",
      p in RR._HELD and not os.get_inheritable(RR._HELD[p].fileno()))

# 2. release: only a holder releases, and then the next run may take it; the file is never removed
other = tmp_lock()
check("RR1.4 a run that does not hold a lock cannot release it, and the holder still holds",
      RR.release_lock(other) is False and RR.take_lock(p)[0] is False)
rel = RR.release_lock(p)
check("RR1.5 the holder releases it, the file stays where it was, and the next run takes it",
      rel is True and os.path.exists(p) and RR.take_lock(p)[0])
RR.release_lock(p)

# 3. the hub's case: a lock file left behind by a run that died. Exactly one of two later runs gets it.
d = tmp_lock()
with open(d, "w", encoding="utf-8") as fh:
    json.dump({"pid": 999999, "t": "left by a crash"}, fh)
a_ok, _ = RR.take_lock(d)
b_ok, _ = RR.take_lock(d)
check("RR1.6 after a crash leaves a lock file behind, one run takes it and the next is refused; nothing is "
      "moved aside (the A459-STALE-TAKEOVER case)",
      a_ok and not b_ok and sorted(os.listdir(os.path.dirname(d))) == ["rolling_restart.lock"],
      (a_ok, b_ok, os.listdir(os.path.dirname(d))))
RR.release_lock(d)

# 4. a real second process: it holds the lock, we are refused; it dies without releasing, we take it
x = tmp_lock()
# A479 (2026-11-23): through tools/child_python.py. RR1.7 compared the holder's pid with Popen's pid; on a Windows venv
# Popen's pid is the launcher's and the holder is its child, so RR1.7 failed on every such machine while Linux CI was
# green. The child now reports its own pid, RR1.7b checks the relationship instead of assuming it, and RR1.7c says
# the named holder is gone, not only that the lock came free (11 of 12 quorum seats, 2026-11-23).
sys.path.insert(0, os.path.join(HERE, "tools"))
import child_python as CP  # noqa: E402
child_src = ("import sys, time; sys.path.insert(0, %r); import rolling_restart as RR; "
             "ok, _ = RR.take_lock(%r); print('held' if ok else 'refused', flush=True); time.sleep(120)" % (HERE, x))
child, holder, holder_parent = CP.start(child_src)
try:
    first = CP.readline(child, 30)
    okx, whox = RR.take_lock(x)
    check("RR1.7 while another process holds it, this one is refused and told that process's pid (the pid the "
          "holder reports itself)", first == "held" and not okx and ("pid %d" % holder) in whox, (first, okx, whox))
    check("RR1.7b the holder is the started child itself or that child's own child (a venv launcher), by the parent "
          "pid it reports", holder == child.pid or holder_parent == child.pid, (holder, holder_parent, child.pid))
finally:
    gone = CP.kill(child, holder)
check("RR1.7c the process that held the lock is gone after the kill", gone, holder)
deadline, okd = time.time() + 15, False
while time.time() < deadline and not okd:          # the OS drops a dead holder's lock; on Windows not always at once
    okd = RR.take_lock(x)[0]
    if not okd:
        time.sleep(0.2)
check("RR1.8 when that process dies without releasing, the OS drops its lock and the next run takes it",
      okd)
check("RR1.9 ...without anything moved aside or removed", sorted(os.listdir(os.path.dirname(x))) == ["rolling_restart.lock"],
      os.listdir(os.path.dirname(x)))
RR.release_lock(x)

# 5. main() refuses before touching any node while another run holds the lock, and runs when it is free
calls = []
saved = {k: getattr(RR, k) for k in ("probe", "restart_one", "status", "LOCK")}
RR.probe = lambda port, timeout=4: (calls.append(("probe", port)), ("down", "patched"))[1]
RR.restart_one = lambda node, want, say: (calls.append(("restart", node["id"])), True)[1]
RR.status = lambda say=print: 0
held = tmp_lock()
try:
    RR.LOCK = held
    other_ok = RR.take_lock(held)[0]                          # held through another handle, as another run would
    other_fh = RR._HELD.pop(held, None)                       # ...and not as main()'s own: main must not release it
    rc = RR.main(["--all"])
    check("RR1.10 main() exits %d and restarts nothing while another run holds the lock" % RR.LOCKED_EXIT,
          other_ok and rc == RR.LOCKED_EXIT and calls == [], (other_ok, rc, calls))
    check("RR1.11 ...and leaves that run's lock held", RR.take_lock(held)[0] is False)
    if other_fh is not None:
        RR._HELD[held] = other_fh
        RR.release_lock(held)
    calls.clear()
    rc = RR.main(["--all"])
    check("RR1.12 with the lock free, main() runs (the control: the patched restart is reached)",
          rc == 0 and [c for c in calls if c[0] == "restart"] == [("restart", i) for i in RR.ORDER], (rc, calls))
    after = RR.take_lock(held)[0]
    check("RR1.13 ...and releases its own lock when it finishes", after and held in RR._HELD)
    RR.release_lock(held)
    calls.clear()
    rc = RR.main(["--status"])
    check("RR1.14 --status takes no lock and changes nothing",
          rc == 0 and held not in RR._HELD and calls == [] and RR.take_lock(held)[0])
    RR.release_lock(held)
finally:
    for k, v in saved.items():
        setattr(RR, k, v)

# 6. the highway's restart remedy runs this same script, so the lock covers both callers
import covenant_highway as H  # noqa: E402
import inspect  # noqa: E402
src = inspect.getsource(H.remedy_restart_nodes)
check("RR1.15 the highway's remedy_restart_nodes starts rolling_restart.py, the script that holds the lock "
      "[source text only]", src.count('"rolling_restart.py"') >= 2, src[:120])

passed = sum(1 for _, o in RESULTS if o)
print("RR1: %d/%d passed" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
