"""RR1 -- two rolling restarts never run at once (A459).

2026-11-19: a rolling_restart.py started by hand and the highway's remedy_restart_nodes (which starts the same
script detached on source drift) began within two seconds of each other. Both restarted node A, and node A ran
as two processes on one database for about an hour and three quarters. The script had no lock at all.

Every check here runs against a temp lock file. Nothing reaches a node: probe, restart_one and status are
replaced in the module before main() is called, and the replacement records any call so the test can see it."""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolling_restart as RR  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -- %s" % (detail,)))


def tmp_lock():
    return os.path.join(tempfile.mkdtemp(prefix="rr1_"), "rolling_restart.lock")


def plant(path, pid, age=0, raw=None):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(raw if raw is not None else json.dumps({"pid": pid, "t": "planted"}))
    if age:
        t = time.time() - age
        os.utime(path, (t, t))


def pid_in(path):
    """The pid a lock file names, or None when there is no such file or it cannot be read: a broken lock makes a
    check FAIL by name, never crash the suite."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("pid")
    except (OSError, ValueError, AttributeError):
        return None


def gone(path):
    try:
        os.remove(path)
    except OSError:
        pass


ALIVE, DEAD = (lambda _pid: True), (lambda _pid: False)

# 1. one holder at a time
p = tmp_lock()
ok1, _ = RR.take_lock(p, alive=ALIVE)
ok2, who = RR.take_lock(p, alive=ALIVE)
check("RR1.1 the first run takes the lock and a second is refused, naming the holder",
      ok1 and not ok2 and ("pid %d" % os.getpid()) in who, (ok1, ok2, who))
check("RR1.2 the lock file says which process holds it",
      pid_in(p) == os.getpid())

# 2. release: only the holder releases, and then the next run may take it
q = tmp_lock()
plant(q, os.getpid() + 1)
check("RR1.3 a run never releases another run's lock", RR.release_lock(q) is False and os.path.exists(q))
check("RR1.4 the holder releases it, and the next run takes it",
      RR.release_lock(p) is True and not os.path.exists(p) and RR.take_lock(p, alive=ALIVE)[0])
RR.release_lock(p)

# 3. a lock left by a run that died is taken over, and kept aside, not deleted
d = tmp_lock()
plant(d, 999999)
okd, _ = RR.take_lock(d, alive=DEAD)
check("RR1.5 a lock whose holder is gone is taken over", okd)
check("RR1.6 ...and the old lock is moved to <lock>.stale, not lost",
      pid_in(d + ".stale") == 999999)
RR.release_lock(d)

# 4. a live holder's lock is respected until it is older than LOCK_STALE_S
f = tmp_lock()
plant(f, 424242, age=60)
check("RR1.7 a fresh lock with a live holder is respected", RR.take_lock(f, alive=ALIVE)[0] is False)
plant(f, 424242, age=RR.LOCK_STALE_S + 60)
check("RR1.8 a lock older than LOCK_STALE_S is taken over even if its pid looks alive (pid reuse)",
      RR.take_lock(f, alive=ALIVE)[0] is True)
RR.release_lock(f)

# 5. an unreadable lock is held, never guessed at, until it is that old
u = tmp_lock()
plant(u, None, age=60, raw="{not json")
oku, whou = RR.take_lock(u, alive=DEAD)
check("RR1.9 a lock that cannot be read is treated as held", oku is False and "could not be read" in whou, whou)
plant(u, None, age=RR.LOCK_STALE_S + 60, raw="{not json")
check("RR1.10 ...until it is older than LOCK_STALE_S", RR.take_lock(u, alive=DEAD)[0] is True)
RR.release_lock(u)

# 6. main() refuses before touching any node while another run holds the lock, and runs when it is free
calls = []
saved = {k: getattr(RR, k) for k in ("probe", "restart_one", "status", "LOCK")}
RR.probe = lambda port, timeout=4: (calls.append(("probe", port)), ("down", "patched"))[1]
RR.restart_one = lambda node, want, say: (calls.append(("restart", node["id"])), True)[1]
RR.status = lambda say=print: 0
held = tmp_lock()
try:
    RR.LOCK = held
    plant(held, os.getpid())                                      # held by a live process: this one, as "another run"
    rc = RR.main(["--all"])
    check("RR1.11 main() exits %d and restarts nothing while another run holds the lock" % RR.LOCKED_EXIT,
          rc == RR.LOCKED_EXIT and calls == [], (rc, calls))
    check("RR1.12 ...and leaves that run's lock where it was", os.path.exists(held))
    gone(held)
    calls.clear()
    rc = RR.main(["--all"])
    check("RR1.13 with the lock free, main() runs (the control: the patched restart is reached)",
          rc == 0 and [c for c in calls if c[0] == "restart"] == [("restart", i) for i in RR.ORDER], (rc, calls))
    check("RR1.14 ...and releases its own lock when it finishes", not os.path.exists(held))
    calls.clear()
    rc = RR.main(["--status"])
    check("RR1.15 --status takes no lock and changes nothing", rc == 0 and not os.path.exists(held) and calls == [])
finally:
    for k, v in saved.items():
        setattr(RR, k, v)

# 7. the highway's restart remedy runs this same script, so the lock covers both callers
import covenant_highway as H  # noqa: E402
import inspect  # noqa: E402
src = inspect.getsource(H.remedy_restart_nodes)
check("RR1.16 the highway's remedy_restart_nodes starts rolling_restart.py, the script that holds the lock "
      "[source text only]", src.count('"rolling_restart.py"') >= 2, src[:120])

passed = sum(1 for _, o in RESULTS if o)
print("RR1: %d/%d passed" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
