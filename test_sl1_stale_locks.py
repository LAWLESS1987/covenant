#!/usr/bin/env python3
"""SL1 -- A482: no lock in the tree is reclaimed by its age any more where two takers could both win (the A459
shape, A459-STALE-TAKEOVER). covenant_oslock holds A459's method once: a non-blocking exclusive OS lock on a file
that is never moved or removed, dropped by the OS when its holder exits or dies. The free-will round and the daily
cycle use it, and the daily launch check asks whether the lock is HELD, not how old a file is. The guard at the end
walks the tree and fails on any new function with the old shape (O_EXCL create + an age read + a remove/rename),
so the next copy is caught where it is written, not found by a reviewer. Driven both ways. Stdlib only."""
import ast
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

fails = []
n = [0]


def check(name, cond, detail=""):
    n[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:200]))
    if not cond:
        fails.append(name)


try:
    import covenant_oslock as OL
except ImportError as e:
    check("SL1.0 covenant_oslock exists", False, e)
    print("\nSL1: %d/%d passed" % (n[0] - len(fails), n[0]))
    sys.exit(1)

tmp = tempfile.mkdtemp(prefix="sl1-")

# ---- the shared lock
p = os.path.join(tmp, "a.lock")
h = OL.acquire(p)
check("SL1.1 a free lock is taken", h is not None)
check("SL1.2 a second taker is refused while it is held", OL.acquire(p) is None)
held, note = OL.held_by_other(p)
check("SL1.3 held_by_other says held, and names the holder's pid", held and str(os.getpid()) in str(note.get("pid")),
      (held, note))
check("SL1.4 releasing drops it; the file stays", OL.release(h) and os.path.exists(p))
check("SL1.5 after release it is free again (and held_by_other takes nothing)",
      OL.held_by_other(p)[0] is False and OL.acquire(p) is not None)
OL.release_path(p)
check("SL1.6 a process that holds no handle cannot release the lock", OL.release(None) is False)

# a leftover file from a dead holder, whatever its age, is not a holder (the hub's A459 case)
left = os.path.join(tmp, "left.lock")
with open(left, "w") as fh:
    fh.write('{"pid": 999999, "t": "long ago"}')
os.utime(left, (time.time() - 10 * 3600,) * 2)
h1 = OL.acquire(left)
h2 = OL.acquire(left)
check("SL1.7 a dead holder's leftover file: one taker wins, the next is refused, nothing moved aside",
      h1 is not None and h2 is None and os.listdir(tmp).count("left.lock") == 1
      and not [f for f in os.listdir(tmp) if "stale" in f], os.listdir(tmp))
OL.release(h1)

# a real second process holds it and is killed without releasing
child = subprocess.Popen([sys.executable, "-c",
                          "import sys,time; sys.path.insert(0, %r); import covenant_oslock as O; h=O.acquire(%r); "
                          "print('held' if h else 'refused', flush=True); time.sleep(60)" % (HERE, left)],
                         stdout=subprocess.PIPE, text=True)
line = child.stdout.readline().strip()
check("SL1.8 a second process takes the lock", line == "held", line)
check("SL1.9 ... and we are refused while it lives", OL.acquire(left) is None)
child.kill()
child.wait(timeout=15)
got = None
for _ in range(30):
    got = OL.acquire(left)
    if got:
        break
    time.sleep(0.5)
check("SL1.10 killed without releasing, the OS drops its lock and the next taker gets it", got is not None)
OL.release(got)

# ---- the free-will round
import covenant_free_will as FW
fw_release = getattr(FW, "_release_lock", lambda path: None)   # absent before A482
fwl = os.path.join(tmp, "ambassador_round.lock")
with open(fwl, "w") as fh:
    fh.write("old")
os.utime(fwl, (time.time() - FW.LOCK_STALE_S - 600,) * 2)
a = FW._take_lock(fwl)
b = FW._take_lock(fwl)
check("SL1.11 free will: a leftover lock is taken by one round and refused to the next (both cannot win)",
      a is True and b is False, (a, b))
check("SL1.12 free will: nothing is moved aside or removed", os.path.exists(fwl)
      and not [f for f in os.listdir(tmp) if f.startswith("ambassador_round.lock.")], os.listdir(tmp))
os.utime(fwl, (time.time() - FW.LOCK_STALE_S - 600,) * 2)          # the holder is alive, just slow
check("SL1.12b free will: a LIVE round past the old age limit is not evicted (the HUB's finding)",
      FW._take_lock(fwl) is False)
xl = os.path.join(tmp, "x.lock")
holder = subprocess.Popen([sys.executable, "-c",
                           "import sys,time; sys.path.insert(0, %r); import covenant_oslock as O; h=O.acquire(%r); "
                           "print('held' if h else 'refused', flush=True); time.sleep(60)" % (HERE, xl)],
                          stdout=subprocess.PIPE, text=True)
hl = holder.stdout.readline().strip()
check("SL1.13 free will: a round that does not hold the lock cannot release another's (it stays held)",
      hl == "held" and fw_release(xl) is False and OL.acquire(xl) is None, hl)
holder.kill()
holder.wait(timeout=15)
check("SL1.14 free will: the holder's release frees it", fw_release(fwl) is True and FW._take_lock(fwl) is True)
fw_release(fwl)

# ---- the daily cycle
import covenant_daily as D
D.SNAPS = os.path.join(tmp, "snaps")
D.LOCK = os.path.join(D.SNAPS, "cycle.lock")
os.makedirs(D.SNAPS, exist_ok=True)
with open(D.LOCK, "w") as fh:
    fh.write("1")
os.utime(D.LOCK, (time.time() - 5 * 3600,) * 2)
first, second = D._lock(), D._lock()
check("SL1.15 daily: a leftover lock is taken by one cycle and refused to the next", first is True and second is False,
      (first, second))
os.utime(D.LOCK, (time.time() - D.LOCK_STALE_S - 600,) * 2)        # the cycle is alive, just slow
check("SL1.15b daily: a LIVE cycle past the old age limit is not evicted", D._lock() is False)
lt = time.localtime()
ref = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 11, 0, 0, 0, 0, -1))
ok_h, why_h = D.due(now=ref, rows=[], running=[], nightly_done=True)
check("SL1.16 daily: the launch check refuses while a cycle HOLDS the lock, and removes nothing",
      ok_h is False and "lock" in why_h and os.path.exists(D.LOCK), why_h)
D._unlock()
ok_f, why_f = D.due(now=ref, rows=[], running=[], nightly_done=True)
check("SL1.17 daily: a lock file nobody holds does not stop the launch, and is not removed",
      ok_f is True and os.path.exists(D.LOCK), (ok_f, why_f))
check("SL1.18 daily: after the cycle's unlock the next cycle can take it", D._lock() is True)
D._unlock()

# ---- the site deploy's pass lock (A486)
sys.path.insert(0, os.path.join(HERE, "tools"))
import site_autodeploy as SA
SA.LOCK = os.path.join(tmp, "site_autodeploy.lock")
SA.LEDGER = os.path.join(tmp, "site_autodeploy.jsonl")
passes = []
real_pass = SA.one_pass
SA.one_pass = lambda dry_run=False: passes.append(dry_run) or {"result": "dry_run_ok"}
import io
import json
import contextlib
try:
    blocker = subprocess.Popen([sys.executable, "-c",
                                "import sys,time; sys.path.insert(0, %r); import covenant_oslock as O; h=O.acquire(%r); "
                                "print('held' if h else 'refused', flush=True); time.sleep(60)" % (HERE, SA.LOCK)],
                               stdout=subprocess.PIPE, text=True)
    bl = blocker.stdout.readline().strip()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = SA.main(["--dry-run"])
    check("SL1.22 site deploy: while another pass holds the lock, a second does nothing and says so",
          bl == "held" and rc == 0 and "another_pass_running" in out.getvalue() and not passes, (bl, out.getvalue()))
    blocker.kill()
    blocker.wait(timeout=15)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        SA.main(["--dry-run"])
    rec = json.loads(out.getvalue().strip().splitlines()[-1])
    check("SL1.23 site deploy: a pass that died without releasing is recorded as taken over, and the next pass runs",
          passes == [True] and rec.get("took_over_stale_lock") is True, rec)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        SA.main(["--dry-run"])
    rec2 = json.loads(out.getvalue().strip().splitlines()[-1])
    check("SL1.24 site deploy: after a pass that finished, the next is not flagged, the lock file stays and is free",
          len(passes) == 2 and "took_over_stale_lock" not in rec2 and os.path.exists(SA.LOCK)
          and not OL.held_by_other(SA.LOCK)[0] and os.path.exists(SA.LOCK + ".last"), rec2)
finally:
    SA.one_pass = real_pass

# ---- the guard: the old shape, anywhere in the tree
SKIP = {".git", ".trash", "pending-v8.38", "node_modules", ".venv", "__pycache__", "logs"}
# Known, named, not changed by A482 (each a decision, not an oversight):
KNOWN = {
    # A486 converted paper_run.AppendLock and tools/site_autodeploy.main to covenant_oslock; they left this list, so a
    # return of the old shape in either now turns SL1.19 red.
    ("pairstore_excl.py", "prune"): "same window, but a double prune of expired pairs is harmless; shared with an "
                                    "outside project's adopted copy",
}


def age_lock_shapes(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith("sl1-")]
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dp, fn)
            try:
                tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                attrs = {x.attr for x in ast.walk(node) if isinstance(x, ast.Attribute)}
                # code, not words: os.O_EXCL used, an age read (getmtime / .st_mtime), and os.remove / unlink /
                # replace / rename called on os itself (a str.replace is not a file being moved)
                rm = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
                         and x.func.attr in ("remove", "unlink", "replace", "rename")
                         and isinstance(x.func.value, ast.Name) and x.func.value.id == "os" for x in ast.walk(node))
                if "O_EXCL" in attrs and ({"getmtime", "st_mtime"} & attrs) and rm:
                    out.append((os.path.relpath(path, root).replace(os.sep, "/"), node.name))
    return out


found = age_lock_shapes(HERE)
unknown = [f for f in found if f not in KNOWN]
check("SL1.19 GUARD: no function in the tree reclaims an O_EXCL lock by its age except the one named (three until A486)",
      not unknown, unknown)
check("SL1.20 the free-will round, the daily cycle, the paper ledger and the site deploy are no longer of that shape",
      not [f for f in found if f[0] in ("covenant_free_will.py", "covenant_daily.py", "paper_run.py", "tools/site_autodeploy.py")], found)
probe_dir = tempfile.mkdtemp(prefix="sl1probe-")
with open(os.path.join(probe_dir, "new_lock.py"), "w", encoding="utf-8") as fh:
    fh.write("import os, time\ndef take(p):\n    try:\n        os.open(p, os.O_CREAT | os.O_EXCL)\n"
             "    except FileExistsError:\n        if time.time() - os.path.getmtime(p) > 60:\n"
             "            os.remove(p)\n")
check("SL1.21 the guard is seen RED: a new age-reclaimed lock is found", age_lock_shapes(probe_dir) ==
      [("new_lock.py", "take")])

print("\nSL1: %d/%d passed" % (n[0] - len(fails), n[0]))
sys.exit(1 if fails else 0)
