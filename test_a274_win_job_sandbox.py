#!/usr/bin/env python3
"""
A274 -- the code sandbox on Windows: a Job Object path that enforces three of
the fork path's four limits, and the refusal that stays because nothing on
Windows enforces the fourth.

THE ASK (2026-10-06). Design a Windows path that enforces the SAME limits the
fork path does -- memory, process count, file size, wall time -- and "if one
limit cannot be enforced on Windows, keep refusing and say which, rather than
claiming parity". Pin each limit with real code that tries to exceed it, and
drive each guard both ways: a mutation that drops the limit must turn this
suite red.

WHAT WAS FOUND BY RUNNING IT (the A274 note in the core has the numbers):
  * through the venv redirector the real interpreter starts as a second
    process, before the job can be assigned, and runs outside it;
  * this interpreter is MSIX-packaged, and its children from outside the
    package (cmd.exe, os.system) break away from every job unless the
    desktop-app policy BREAKAWAY_DISABLE_PROCESS_TREE is set at creation;
  * Windows has no file-size limit: a Low-integrity token and a job I/O rate
    cap were both measured and neither bounded what landed on disk.
  * and, in this suite's first probe: a child given only SystemRoot cannot
    find "cmd" (error 2) and os.system without COMSPEC returns -1, so a
    "refused" there is the environment, not the job. P therefore uses absolute
    paths, requires error 1816 (the job's quota), and runs the same snippet
    OUTSIDE the job as a control that must succeed.

GROUPS -- each runs real code against the shipped _win_job_run():
  B  basic: a benign snippet runs and reports; a raising one reports its
     exception; the restricted builtins hold in the child (open is a NameError)
  M  memory: a gradual ~384 MB allocation stops in MemoryError with the job's
     peak at or under the 256 MiB cap; an 80 MB one completes
  P  processes: an escaped snippet tries cmd.exe by Popen and by os.system and
     a Python child; all are refused (1816 / -1); the control runs all three
  W  wall time: `while True: pass` is ended at the timeout and is gone when
     the call returns
  K  kill on close: the process holding the job is killed mid-run (the node
     dying); the child dies with it
  S  self-check: the child's program, run outside the job, refuses before it
     reads a byte of the proposal
  F  file size, the limit that is NOT enforced: an escaped snippet's 1 MiB
     write lands. Pinned so the day something bounds it, this goes red and the
     reason on /health has to change with it
  G  the gate: on win32 run_sandboxed still refuses, the reason names file
     size and only file size
  X  every platform: off win32 the path refuses instead of raising; the gate
     is shut while file_size is listed

MUTATIONS (win32, after the groups; --no-mutations skips them). Each removes
ONE limit from a copy of the core in a temp dir -- never the real file, so a
failed restore cannot happen and nothing running is touched -- runs only the
group that pins it against that copy, and requires a [FAIL] from that group
(or, for the wall-time limit, a hang inside W). A copy that fails to import
is not counted as red: a crash proves nothing about the check.

NOT MEASURED HERE: the parent's IsProcessInJob re-check is not driven alone.
It can only fire if AssignProcessToJobObject reported success without
assigning, which this harness cannot cause; S drives the child's own check,
which covers the same case from the other side.

Run: python test_a274_win_job_sandbox.py [--no-mutations]
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.abspath(os.environ.get("A274_CORE_DIR") or HERE)
sys.path[:0] = [CORE_DIR] + ([HERE] if CORE_DIR != HERE else [])
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
import covenant_unified_v8 as cov  # noqa: E402

WIN = sys.platform == "win32"
ONLY = set(filter(None, os.environ.get("A274_ONLY", "").split(",")))
MUTATE = WIN and "--no-mutations" not in sys.argv and os.environ.get("A274_NO_MUTATIONS") != "1"
NO_WINDOW = 0x08000000 if WIN else 0
CAP = cov.CODE_SANDBOX_MAX_MEMORY_BYTES
WIDE = sorted(set(cov.CODE_SAFE_BUILTINS) | {"__import__", "open", "getattr", "RuntimeError", "OSError"})

ok = []


def check(label, good, detail=""):
    ok.append(bool(good))
    print("  [%s] %s%s" % ("PASS" if good else "FAIL", label, (" -- %s" % detail) if detail else ""), flush=True)


def not_run(label, why):
    print("  [NOT RUN] %s -- %s (not counted)" % (label, why), flush=True)


def group(g, title):
    if ONLY and g not in ONLY:
        return False
    print("\n== %s %s ==" % (g, title), flush=True)
    return True


print("core: %s" % os.path.abspath(cov.__file__), flush=True)
print("platform %s, interpreter for the child: %s" % (sys.platform, cov._wj_interpreter() if WIN else "n/a"))

if WIN:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    from ctypes import wintypes as _w
    k32.OpenProcess.restype = _w.HANDLE
    k32.OpenProcess.argtypes = [_w.DWORD, _w.BOOL, _w.DWORD]
    k32.WaitForSingleObject.argtypes = [_w.HANDLE, _w.DWORD]
    k32.WaitForSingleObject.restype = _w.DWORD
    k32.TerminateProcess.argtypes = [_w.HANDLE, _w.UINT]
    k32.CloseHandle.argtypes = [_w.HANDLE]

    def wait_dead(pid, seconds):
        """True once `pid` has exited (or cannot be opened because it is gone)."""
        h = k32.OpenProcess(0x00100000 | 0x1000, False, int(pid))   # SYNCHRONIZE | QUERY_LIMITED
        if not h:
            return True
        try:
            return k32.WaitForSingleObject(h, int(seconds * 1000)) == 0
        finally:
            k32.CloseHandle(h)

    def kill_pid(pid):
        h = k32.OpenProcess(0x0001 | 0x00100000, False, int(pid))   # TERMINATE | SYNCHRONIZE
        if h:
            k32.TerminateProcess(h, 9)
            k32.WaitForSingleObject(h, 5000)
            k32.CloseHandle(h)

    def kill_tree(p):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True,
                       timeout=60, creationflags=NO_WINDOW)

    def child_env():
        return {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows")}

    def helper_env():
        """The base interpreter (one process, no launcher job) with this
        interpreter's site-packages, so it can import the core."""
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([p for p in sys.path if p.endswith("site-packages")] + [HERE])
        return env

# ------------------------------------------------------------------ B basic
if WIN and group("B", "a snippet runs in the job and reports back"):
    r = cov._win_job_run("x = 1 + 1\n")
    check("B1 a benign snippet runs and reports success", r.get("ran") is True and r.get("ok") is True, r)
    r = cov._win_job_run("z = 1 / 0\n")
    check("B2 a raising snippet is reported failed WITH its exception",
          r.get("ok") is False and "ZeroDivisionError" in str(r.get("error")), r.get("error"))
    r = cov._win_job_run("open('a274_should_not_exist', 'w')\n")
    check("B3 the restricted builtins hold in the child: open is a NameError",
          r.get("ok") is False and "NameError" in str(r.get("error")), r.get("error"))

# ------------------------------------------------------------------ M memory
if WIN and group("M", "the memory limit: 256 MiB"):
    r = cov._win_job_run("x = [[0] * 1000 for _ in range(48000)]\n")       # ~384 MB if nothing stops it
    peak = r.get("peak_memory") or 0
    check("M1 a gradual ~384 MB allocation stops in MemoryError",
          r.get("ran") is True and r.get("ok") is False and "MemoryError" in str(r.get("error")), r.get("error"))
    check("M2 ... at the cap: the job's peak is at or under 256 MiB and reached 90% of it",
          0.9 * CAP <= peak <= CAP, "peak %d of %d" % (peak, CAP))
    r = cov._win_job_run("x = [[0] * 1000 for _ in range(10000)]\n")       # ~80 MB
    check("M3 an 80 MB allocation completes -- the cap is not a wall at the baseline",
          r.get("ok") is True and (r.get("peak_memory") or 0) >= 64 * 1024 * 1024,
          "ok=%s peak %s" % (r.get("ok"), r.get("peak_memory")))
    r = cov._win_job_run("x = [0] * (10**10)\n")
    # Parity with W2.6 only. 80 GB fails without any cap at all, so this line
    # proves nothing about the job; M1 and M-mem are what prove the cap.
    check("M4 (parity with W2.6) `[0] * 10**10` is a MemoryError",
          "MemoryError" in str(r.get("error")), r.get("error"))

# --------------------------------------------------------------- P processes
SPAWN = r'''
import os, subprocess, sys
cmd = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "cmd.exe")
os.environ["COMSPEC"] = cmd
out = ["cmd_exists=%s" % os.path.isfile(cmd)]
try:
    out.append("popen_cmd=RAN:%s" % subprocess.Popen([cmd, "/c", "exit 7"], creationflags=0x08000000).wait())
except OSError as e:
    out.append("popen_cmd=REFUSED:%s" % getattr(e, "winerror", None))
out.append("system_cmd=%s" % os.system("exit 7"))
try:
    out.append("popen_python=RAN:%s" % subprocess.Popen([sys.executable, "-I", "-S", "-c", "pass"],
                                                       creationflags=0x08000000).wait())
except OSError as e:
    out.append("popen_python=REFUSED:%s" % getattr(e, "winerror", None))
raise RuntimeError(" ".join(out))
'''
if WIN and group("P", "the process limit: the child starts nothing"):
    wrapper = "try:\n    exec(%r)\nexcept RuntimeError as e:\n    print(e)\n" % SPAWN
    ctl = subprocess.run([cov._wj_interpreter(), "-I", "-S", "-c", wrapper], capture_output=True, text=True,
                         timeout=120, env=child_env(), creationflags=NO_WINDOW)
    seen_ctl = ctl.stdout.strip()
    check("P0 control: OUTSIDE the job, in the same environment, the snippet starts all three",
          "cmd_exists=True" in seen_ctl and "popen_cmd=RAN:7" in seen_ctl and "system_cmd=7" in seen_ctl
          and "popen_python=RAN:0" in seen_ctl, seen_ctl or ctl.stderr[-300:])
    r = cov._win_job_run(SPAWN, timeout=20, builtin_names=WIDE)
    seen = str(r.get("error"))
    check("P1 inside the job, cmd.exe by Popen is refused by the job's quota (1816)",
          r.get("ran") is True and "cmd_exists=True" in seen and "popen_cmd=REFUSED:1816" in seen, seen)
    check("P2 inside the job, os.system fails to start cmd.exe (-1, not 7)", "system_cmd=-1" in seen, seen)
    check("P3 inside the job, a Python child is refused (1816)", "popen_python=REFUSED:1816" in seen, seen)

# --------------------------------------------------------------- W wall time
if WIN and group("W", "the wall-time limit"):
    t0 = time.monotonic()
    r = cov._win_job_run("while True:\n    pass\n", timeout=2.0)
    dt = time.monotonic() - t0
    check("W1 an endless loop is reported timed out", r.get("ran") is True and r.get("timed_out") is True, r)
    check("W2 ... at the timeout, not long after it", 2.0 <= dt <= 12.0, "%.2fs" % dt)
    pid = r.get("pid")
    check("W3 ... and the child is gone when the call returns", bool(pid) and wait_dead(pid, 0), "pid %s" % pid)
    if pid and not wait_dead(pid, 0):
        kill_pid(pid)

# ------------------------------------------------------------ K kill on close
if WIN and group("K", "kill-on-close: the node's death ends the child"):
    td = tempfile.mkdtemp(prefix="a274k_")
    pidfile = os.path.join(td, "child.pid")
    src = "import os\nopen(%r, 'w').write(str(os.getpid()))\nwhile True:\n    pass\n" % pidfile
    helper = ("import os, sys\nsys.path.insert(0, %r)\nimport covenant_unified_v8 as cov\n"
              "print('HELPER', os.getpid(), flush=True)\n"
              "cov._win_job_run(%r, timeout=600, builtin_names=%r)\n" % (CORE_DIR, src, WIDE))
    hp = subprocess.Popen([cov._wj_interpreter(), "-c", helper], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          env=helper_env(), creationflags=NO_WINDOW)
    helper_pid = child_pid = None
    try:
        first = []
        for _ in range(50):                              # the core may print before HELPER
            raw = hp.stdout.readline()
            first = raw.decode("utf-8", "replace").split()
            if not raw or (len(first) == 2 and first[0] == "HELPER"):
                break
        helper_pid = int(first[1]) if len(first) == 2 and first[0] == "HELPER" else None
        t_end = time.monotonic() + 60
        while time.monotonic() < t_end and not os.path.exists(pidfile):
            time.sleep(0.2)
        time.sleep(0.3)
        try:
            with open(pidfile) as fh:
                child_pid = int(fh.read().strip())
        except (OSError, ValueError):
            child_pid = None
        check("K0 the helper started a child in its job, and the child is running",
              helper_pid and child_pid and not wait_dead(child_pid, 0),
              "helper %s child %s %s" % (helper_pid, child_pid, " ".join(first)[:200]))
        if helper_pid and child_pid:
            kill_pid(helper_pid)                         # the node dies mid-proposal
            died = wait_dead(child_pid, 30)
            check("K1 the child dies with the process that held its job", died, "child pid %s" % child_pid)
    finally:
        if child_pid and not wait_dead(child_pid, 0):
            kill_pid(child_pid)                          # never leave a spinning child behind
        if hp.poll() is None:
            kill_tree(hp)
        shutil.rmtree(td, ignore_errors=True)

# ------------------------------------------------------------- S self-check
if WIN and group("S", "the child refuses to run outside its job"):
    td = tempfile.mkdtemp(prefix="a274s_")
    marker = os.path.join(td, "ran.txt")
    payload = json.dumps({"builtins": WIDE, "source": "open(%r, 'w').write('ran')\n" % marker})
    r = subprocess.run([cov._wj_interpreter(), "-I", "-S", "-B", "-c", cov._win_sandbox_boot()],
                       input=payload.encode(), capture_output=True, timeout=120, env=child_env(),
                       creationflags=NO_WINDOW)
    out = r.stdout.decode("utf-8", "replace").strip()
    check("S1 run outside the job, the child says NOJOB and exits 3",
          out.startswith("NOJOB") and r.returncode == 3, "rc %s out %r" % (r.returncode, out[:160]))
    check("S2 ... and the proposal never ran", not os.path.exists(marker), marker)
    shutil.rmtree(td, ignore_errors=True)

# -------------------------------------------------- F file size: NOT enforced
if WIN and group("F", "the file-size limit: not enforceable here, measured"):
    td = tempfile.mkdtemp(prefix="a274f_")
    target = os.path.join(td, "w.bin")
    r = cov._win_job_run("open(%r, 'wb').write(b'x' * 1048576)\n" % target, timeout=20, builtin_names=WIDE)
    size = os.path.getsize(target) if os.path.exists(target) else None
    check("F1 an escaped snippet's 1 MiB write lands inside the job -- the gap A274 names "
          "(red here means something now bounds it: change the reason with it)",
          r.get("ok") is True and size == 1048576, "ok=%s size=%s" % (r.get("ok"), size))
    shutil.rmtree(td, ignore_errors=True)

# --------------------------------------------------------------- G the gate
if WIN and group("G", "the gate stays shut while one limit is unenforced"):
    check("G1 file_size is listed unenforceable and the Windows path is shut",
          "file_size" in cov.SANDBOX_WIN_UNENFORCEABLE and cov.SANDBOX_WIN_JOB_AVAILABLE is False
          and cov.SANDBOX_AVAILABLE is False,
          "%s %s %s" % (cov.SANDBOX_WIN_UNENFORCEABLE, cov.SANDBOX_WIN_JOB_AVAILABLE, cov.SANDBOX_AVAILABLE))
    r = cov.run_sandboxed("x = 1\n")
    check("G2 run_sandboxed refuses even a benign snippet, without running it",
          r.get("ran") is False and r.get("ok") is False and "SandboxUnavailable" in str(r.get("error")), r)
    why = cov.SANDBOX_UNAVAILABLE_REASON
    check("G3 the reason names the file-size limit as the one not enforced",
          "file-size limit cannot be enforced" in why, why[:160])
    check("G4 ... and no longer says memory and process limits cannot be enforced",
          "memory, process and file-size limits cannot be enforced" not in why, why[:160])
    good, _, err = cov.CovenantGuardian().validate_and_score("x = 1\n")
    check("G5 the Guardian refuses with that reason", good is False and "SandboxUnavailable" in err, err[:120])

# ---------------------------------------------------- X every platform
if group("X", "every platform"):
    check("X1 file_size is listed as unenforceable on Windows", "file_size" in cov.SANDBOX_WIN_UNENFORCEABLE)
    check("X2 so the Windows path is shut", cov.SANDBOX_WIN_JOB_AVAILABLE is False)
    if not WIN:
        try:
            r, raised = cov._win_job_run("x = 1\n"), None
        except Exception as e:                              # noqa: BLE001
            r, raised = None, e
        check("X3 off win32 the Job Object path refuses instead of raising",
              raised is None and r.get("ran") is False and "SandboxUnavailable" in str(r.get("error")),
              repr(raised) if raised else r)
if not WIN:
    not_run("B M P W K S F G and the mutations", "win32 only -- nothing here measures the Windows path")

# ------------------------------------------------------------------ mutations
MUTATIONS = [
    # (id, the limit it drops, the group that must go red, [(anchor, replacement)])
    ("M-mem", "the memory limit (both memory flags)", "M",
     [("                   | _WJ_PROCESS_MEMORY\n", ""), ("                   | _WJ_JOB_MEMORY\n", "")]),
    ("M-proc", "the process-count limit", "P", [("                   | _WJ_ACTIVE_PROCESS\n", "")]),
    ("M-breakaway", "the policy that keeps a packaged child's children in the job", "P",
     [("_WJ_BREAKAWAY_DISABLE_PROCESS_TREE = 0x2 ", "_WJ_BREAKAWAY_DISABLE_PROCESS_TREE = 0x1 ")]),
    ("M-wall", "the wall-time limit", "W",
     [("deadline = time.monotonic() + timeout\n", "deadline = time.monotonic() + 3600\n")]),
    ("M-close", "kill-on-close", "K", [("                   | _WJ_KILL_ON_JOB_CLOSE\n", "")]),
    ("M-self", "the child's check of its own job", "S", [("if seen != __EXPECTED__:", "if False:")]),
    ("M-assign", "the job assignment", "B", [("if not k.AssignProcessToJobObject(job, hproc):", "if False:")]),
    ("M-gate", "the refusal while file size is unenforced", "G",
     [('SANDBOX_WIN_UNENFORCEABLE = ("file_size",)', "SANDBOX_WIN_UNENFORCEABLE = ()")]),
]
OUTER = {"W": 40, "K": 120}

if MUTATE and not ONLY:
    print("\n== mutations: each drops one limit from a COPY of the core; its group must go red ==", flush=True)
    with open(os.path.join(CORE_DIR, "covenant_unified_v8.py"), "rb") as fh:
        pristine = fh.read()
    for mid, what, g, edits in MUTATIONS:
        src = pristine
        stale = [a for a, _ in edits if src.count(a.encode()) != 1]
        if stale:
            check("%s anchor present exactly once" % mid, False, "%r -- the mutation is stale" % stale[0])
            continue
        for a, b in edits:
            src = src.replace(a.encode(), b.encode())
        td = tempfile.mkdtemp(prefix="a274m_")
        try:
            with open(os.path.join(td, "covenant_unified_v8.py"), "wb") as fh:
                fh.write(src)
            env = dict(os.environ, A274_CORE_DIR=td, A274_ONLY=g, A274_NO_MUTATIONS="1")
            p = subprocess.Popen([sys.executable, os.path.abspath(__file__)], cwd=HERE, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
            try:
                out, _ = p.communicate(timeout=OUTER.get(g, 90))
                hung = False
            except subprocess.TimeoutExpired:
                kill_tree(p)
                out, _ = p.communicate(timeout=30)
                hung = True
            text = out.decode("utf-8", "replace")
            ran_copy = ("core: %s" % os.path.join(td, "covenant_unified_v8.py")) in text
            reached = ("== %s " % g) in text
            group_red = any(l.strip().startswith("[FAIL] %s" % g) for l in text.splitlines())
            red = ran_copy and reached and (group_red or (hung and g == "W"))
            tail = " | ".join(l.strip() for l in text.splitlines() if "[FAIL]" in l)[:300]
            check("%s: dropping %s turns %s red" % (mid, what, g), red,
                  "copy imported=%s, reached %s=%s, hung=%s, %s"
                  % (ran_copy, g, reached, hung, tail or text.strip().splitlines()[-1:] or "no output"))
        finally:
            shutil.rmtree(td, ignore_errors=True)
elif WIN and not ONLY:
    not_run("mutations", "--no-mutations")

print("\nA274: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
