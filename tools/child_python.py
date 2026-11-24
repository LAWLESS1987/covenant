#!/usr/bin/env python3
"""tools/child_python.py -- start a child Python and learn the pid of the process that actually runs its code (A479).

WHY. On Windows a venv's python.exe is a launcher: it starts the real interpreter as a SECOND process. So
subprocess.Popen([sys.executable, ...]).pid is the launcher's pid, not the pid of the process running the code. A274
(2026-10-06) recorded this in prose for the sandbox; it came back on 2026-11-23 in RR1.7, which compared a lock
holder's pid with Popen's pid and failed on every Windows venv while Linux CI stayed green. Prose did not stop the
second instance, so this is the one place a test starts a child Python whose pid it means to compare, and
test_ch1_child_python.py fails on a test that compares Popen's pid with a pid a child reported.

HOW. The child's first line is a handshake carrying os.getpid() and os.getppid(), so the caller learns the real pid
and can check the relationship (the real process is the Popen child itself, or that child's child) instead of
assuming it. kill() ends the real process first and the launcher after, then waits, so a test can say that the
process it named is gone rather than infer it from a lock coming free.

    from child_python import start, readline, kill, alive
    p, pid, ppid = start("import time; print('ready', flush=True); time.sleep(60)")
    readline(p, 30)  -> 'ready'
    kill(p, pid); alive(pid) -> False

Stdlib only. Public domain.
"""
import os
import signal
import subprocess
import sys
import threading
import time

TAG = "child_python"
_PREAMBLE = "import os as _o; print('%s pid %%d ppid %%d' %% (_o.getpid(), _o.getppid()), flush=True)\n" % TAG


def readline(p, timeout=30.0):
    """The child's next line of output, stripped, or None if none arrives within TIMEOUT seconds (never hangs)."""
    box = {}

    def _read():
        box["line"] = p.stdout.readline().decode("utf-8", "replace").strip()

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)
    return box.get("line")


def start(src, timeout=30.0, **popen_kw):
    """(proc, pid, ppid). PROC is the Popen object; PID is the process running SRC (on a Windows venv the launcher's
    child, so not proc.pid); PPID is its parent. Raises TimeoutError, killing what it started, if the handshake does
    not arrive within TIMEOUT seconds, and RuntimeError if the first line is not the handshake."""
    popen_kw.setdefault("stdout", subprocess.PIPE)
    popen_kw.setdefault("stderr", subprocess.STDOUT)
    p = subprocess.Popen([sys.executable, "-c", _PREAMBLE + src], **popen_kw)
    line = readline(p, timeout)
    parts = (line or "").split()
    if line is None:
        kill(p, None)
        raise TimeoutError("no handshake from the child within %.0f s" % timeout)
    if len(parts) != 5 or parts[0] != TAG or parts[1] != "pid" or parts[3] != "ppid":
        kill(p, None)
        raise RuntimeError("the child's first line was not the handshake: %r" % line[:120])
    return p, int(parts[2]), int(parts[4])


def alive(pid):
    """True while process PID exists and has not exited."""
    if pid is None or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong(0)
            ok = k.GetExitCodeProcess(h, ctypes.byref(code))
            return bool(ok) and code.value == 259           # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                                    # a zombie child of ours has exited
        wpid, _ = os.waitpid(pid, os.WNOHANG)
        return wpid == 0
    except ChildProcessError:
        return True


def kill(p, pid, wait=30.0):
    """End the real process PID first (when known), then the Popen child, and wait for both. Returns True when PID
    is gone afterwards (or was not given)."""
    if pid is not None and pid != p.pid:
        try:
            os.kill(pid, signal.SIGTERM)                     # TerminateProcess on Windows
        except OSError:
            pass
    try:
        p.kill()
    except OSError:
        pass
    try:
        p.wait(timeout=wait)
    except subprocess.TimeoutExpired:
        pass
    deadline = time.time() + wait
    while pid is not None and alive(pid) and time.time() < deadline:
        time.sleep(0.1)
    return pid is None or not alive(pid)
