#!/usr/bin/env python3
"""covenant_model.py -- the open-source model on this PC, on demand and put away.

WHY (2026-09-19, his words). "there has to be a image creation open source we
can take and improve on same as the other asks including our students growing
to agents"; "optimize the pc towards these tasks and this purpose"; "need a
browser and a security layer other than that optimize"; "green light".

WHAT THIS IS. A thin keeper for llama.cpp's llama-server (tools/llama/, the
same 18 MB runtime the judge workflow uses on the GitHub runner) and the GGUF
weights under models/ (never tracked: .gitignore). It starts the server the
first time something asks, on 127.0.0.1 only, and STOPS it after IDLE_S with
nothing asked -- his standing rule since Ollama: unload the model after use.
This PC has 15.3 GB and was using 12.5 GB of it when this was written, mostly
the browser and the desktop app, so the model is a guest: it picks the
largest weights that fit the memory free at the moment it starts, and says
which.

WHAT IT IS NOT. Not a judge seat and not the gate. The gate is the sentinel
(the distilled students and the semantic judge); every answer this model gives
through the node passes that gate before anyone sees it (/m/agent). It is the
thing the students learn to judge -- that is how they grow toward agents:
their verdicts on its answers go into the same ledger the nightly distill
reads.

CLI:  python covenant_model.py --status | --start | --stop | --ask "text"
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "tools", "llama", "llama-server.exe")
MODELS = os.path.join(HERE, "models")
HOST, PORT = "127.0.0.1", int(os.environ.get("COVENANT_MODEL_PORT", "8081"))
IDLE_S = int(os.environ.get("COVENANT_MODEL_IDLE_S", "600"))
STATE = os.path.join(HERE, "ops", "model_server.json")        # pid, model, started -- gitignored ops/ state
LOG = os.path.join(HERE, "logs", "model_server.log")

# (file name, resident memory it needs, in GB) -- the first that fits the memory
# free at start is the one loaded. Split GGUFs are named by their first part.
# Measured 2026-09-19 22:55 with his browser and the desktop app open: 2.4 GB
# free of 15.3. The 3B's weights are 2.0 GB and llama.cpp maps them (the page
# cache carries what does not fit), so its bar is set at the weights plus a
# 4k-token cache; the 7B keeps the honest 6 GB and waits for memory he frees.
CANDIDATES = [
    ("qwen2.5-coder-7b-instruct-q4_k_m-00001-of-00002.gguf", 6.0),
    ("qwen2.5-3b-instruct-q4_k_m.gguf", 2.3),
]

_lock = threading.Lock()
_last_used = [0.0]


def free_gb():
    """Physical memory free right now, GB; None where it cannot be read."""
    try:
        if os.name == "nt":
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.ullAvailPhys / 2 ** 30, 2)
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return round(int(line.split()[1]) / 2 ** 20, 2)
    except Exception:                                             # noqa: BLE001
        return None
    return None


def pick_model():
    """(path, name, needs_gb) of the largest candidate present that fits, or None."""
    free = free_gb()
    for name, need in CANDIDATES:
        p = os.path.join(MODELS, name)
        if os.path.isfile(p) and (free is None or free >= need):
            return p, name, need
    return None


def _read_state():
    try:
        with open(STATE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _write_state(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(d, fh)


def alive():
    """The server answers /health on the loopback port."""
    try:
        with urllib.request.urlopen("http://%s:%d/health" % (HOST, PORT), timeout=3) as r:
            return r.status == 200
    except Exception:                                             # noqa: BLE001
        return False


def start(say=print):
    """Start llama-server if it is not answering. Returns (ok, why)."""
    if alive():
        return True, "already up: " + str(_read_state().get("model", "?"))
    if os.environ.get("COVENANT_MODEL_STUB"):
        return True, "stub"
    if not os.path.isfile(BIN):
        return False, "no runtime: %s (tools/llama/ is not tracked; unzip the llama.cpp win-cpu build there)" % BIN
    pick = pick_model()
    if not pick:
        return False, "no weights fit: free %s GB, candidates %s under %s" % (free_gb(), [c[0] for c in CANDIDATES], MODELS)
    path, name, need = pick
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    threads = max(2, (os.cpu_count() or 4) - 2)                   # leave the nodes and the desk two threads
    ctx = "8192" if need >= 5 else "4096"                        # a smaller cache for the small model on a tight PC
    args = [BIN, "-m", path, "--host", HOST, "--port", str(PORT), "-c", ctx, "-t", str(threads),
            "--no-webui", "--log-disable"]
    creation = 0x08000000 if os.name == "nt" else 0               # CREATE_NO_WINDOW
    with open(LOG, "a", encoding="utf-8") as lf:
        lf.write("%s start %s (free %s GB, needs %s GB, %d threads)\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), name, free_gb(), need, threads))
        p = subprocess.Popen(args, stdout=lf, stderr=subprocess.STDOUT, creationflags=creation, cwd=os.path.dirname(BIN))
    _write_state({"pid": p.pid, "model": name, "started": time.time(), "needs_gb": need, "threads": threads})
    for _ in range(120):                                          # a 4 GB file from a cold disk can take a minute
        if alive():
            _last_used[0] = time.time()
            _watch_idle()
            say("model server: up, %s, pid %d" % (name, p.pid))
            return True, "up: %s" % name
        if p.poll() is not None:
            return False, "llama-server exited %s -- see %s" % (p.returncode, LOG)
        time.sleep(1)
    return False, "llama-server did not answer within 120 s -- see %s" % LOG


def stop(say=print):
    st = _read_state()
    pid = st.get("pid")
    if not pid:
        return False, "not started by this keeper"
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            os.kill(int(pid), 15)
    except Exception as e:                                        # noqa: BLE001
        return False, "could not stop pid %s: %s" % (pid, e)
    try:
        os.remove(STATE)
    except OSError:
        pass
    with open(LOG, "a", encoding="utf-8") as lf:
        lf.write("%s stop pid %s (%s)\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), pid, st.get("model")))
    say("model server: stopped pid %s" % pid)
    return True, "stopped"


_idle_thread = [None]


def _watch_idle():
    """One daemon thread: after IDLE_S with no ask, the server is stopped -- the rule since Ollama."""
    if _idle_thread[0] and _idle_thread[0].is_alive():
        return
    def run():
        while True:
            time.sleep(30)
            if not alive():
                return
            if time.time() - _last_used[0] > IDLE_S:
                stop(say=lambda *_a: None)
                return
    t = threading.Thread(target=run, name="covenant-model-idle", daemon=True)
    t.start()
    _idle_thread[0] = t


def ask(messages, max_tokens=700, temperature=0.3, timeout=180):
    """One chat completion. messages: [{"role","content"}...]. Returns (text, meta) or raises."""
    if os.environ.get("COVENANT_MODEL_STUB"):
        last = messages[-1]["content"] if messages else ""
        # The stub names how many messages it was handed, so a suite can see
        # whether the turns before this one reached the model (M6q, 2026-09-21).
        return "stub answer to: " + last[:80] + " (%d messages)" % len(messages), {"model": "stub", "tokens": 0, "ms": 0}
    with _lock:
        ok, why = start(say=lambda *_a: None)
        if not ok:
            raise RuntimeError(why)
        # WHOEVER ASKS, KEEPS (2026-09-19). The idle watcher lives in the process
        # that asks -- the CLI's watcher died with the CLI and left the server
        # up, measured at 22:52. So every asker arms the watcher, and the
        # long-lived node process is the one that will put the model away.
        _last_used[0] = time.time()
        _watch_idle()
    body = json.dumps({"messages": messages, "max_tokens": int(max_tokens), "temperature": float(temperature)}).encode("utf-8")
    req = urllib.request.Request("http://%s:%d/v1/chat/completions" % (HOST, PORT), data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    _last_used[0] = time.time()
    text = str(d.get("choices", [{}])[0].get("message", {}).get("content", ""))
    usage = d.get("usage", {}) or {}
    return text, {"model": _read_state().get("model", "?"), "tokens": int(usage.get("completion_tokens", 0) or 0),
                  "ms": int((time.time() - t0) * 1000)}


def status():
    st = _read_state()
    return {"alive": alive(), "model": st.get("model"), "pid": st.get("pid"), "free_gb": free_gb(),
            "would_pick": (pick_model() or (None,))[1] if pick_model() else None,
            "runtime": os.path.isfile(BIN), "weights": sorted(f for f in os.listdir(MODELS) if f.endswith(".gguf")) if os.path.isdir(MODELS) else []}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the open-source model on this PC, on demand and put away")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--ask", metavar="TEXT")
    ap.add_argument("--keep", action="store_true", help="after --ask, leave the server up (default: put it away)")
    a = ap.parse_args(argv)
    if a.start:
        ok, why = start(); print(why); return 0 if ok else 1
    if a.stop:
        ok, why = stop(); print(why); return 0 if ok else 1
    if a.ask:
        text, meta = ask([{"role": "user", "content": a.ask}])
        print(text); print("--", meta)
        if not a.keep:
            stop(say=lambda *_a: None)                             # the CLI is not a process that stays to watch idle
        return 0
    print(json.dumps(status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
