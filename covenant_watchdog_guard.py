#!/usr/bin/env python3
"""covenant_watchdog_guard.py -- C3: the one supervisor the watchdog itself
has. Run every few minutes by the OS scheduler; heals ONLY the watchdog.

WHY THIS EXISTS. The watchdog heals nodes (3 strikes, start_node) and nothing
heals the watchdog: at 2026-08-24T08:03:12Z it died silently and the last line
it ever wrote said both nodes were healthy. Until now the only remedy was the
full restart chain -- stop everything, verify, start everything -- which is a
sledgehammer for a dead monitor beside a healthy chain. The operator's
direction (2026-08-29): "nodes and watchdog should heal each other to avoid
restarts." So: watchdog heals nodes, THIS heals the watchdog, and the OS
scheduler -- the one layer that survives everything short of the machine --
runs this. No layer restarts the whole chain.

HOW DEATH IS DETECTED. P16's way, the only honest way: the timestamp gap in
logs/watchdog.log against the watchdog's own stated silence contract. The
last line of a dead watchdog always looks ordinary (measured, 08-24), so the
GAP is the signal, never the content. The gap threshold here (GAP_DEAD_S) is
deliberately far above the contract floor: a guard that revives a slow
watchdog creates the duplicate it exists to prevent.

WHAT IT WILL NOT DO, and the guards that make each refusal stick:
  * spawn a second watchdog  -- logs/watchdog.pid names the process; if that
    PID is alive and is a python running covenant_watchdog.py, the gap is
    something else (a wedged disk, a stopped clock) and is REPORTED, not
    "fixed" by doubling the restarts-per-death.
  * crash-loop               -- one attempt per COOLDOWN_S, recorded in
    logs/guard_state.json BEFORE the attempt, so even a guard that dies
    mid-spawn cannot retry hot.
  * revive garbage           -- the watchdog source must py_compile first.
    Reviving a watchdog that dies at import turns one death into a loop.
  * touch a node, a database, a key, or the chain -- ever. The watchdog it
    revives does the node-healing, with its own 3-strike judgment.

Output: logs/guard.log (append; the watchdog's own log is never written by
anything but the watchdog -- polluting the P16 signal to announce a rescue
would corrupt the very channel death is read from).

Run:  python covenant_watchdog_guard.py            one check, exit 0/1
      python covenant_watchdog_guard.py --status   report only, never acts
"""
import json
import os
import py_compile
import re
import subprocess
import covenant_quiet                                    # no console window on Windows
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
LOGDIR = os.path.join(HERE, "logs")
WD_LOG = os.path.join(LOGDIR, "watchdog.log")
WD_PID = os.path.join(LOGDIR, "watchdog.pid")
WD_SRC = os.path.join(HERE, "covenant_watchdog.py")
GUARD_LOG = os.path.join(LOGDIR, "guard.log")
STATE = os.path.join(LOGDIR, "guard_state.json")

# 180s, not 300s. The watchdog writes at least every 60s in this
# deployment (its own silence contract says so), and 300s meant tolerating
# five missed rounds before believing it. Retuned 2026-08-29 after a real
# outage: the nodes AND the watchdog died together, so the chain that heals
# nodes was itself the casualty, and every second of detection lag was a
# second the whole system was unattended. Three missed rounds is still well
# clear of a slow round and halves the blind window.
GAP_DEAD_S = int(os.environ.get("COVENANT_GUARD_GAP_DEAD_S", "180"))
COOLDOWN_S = int(os.environ.get("COVENANT_GUARD_COOLDOWN_S", "900"))
# Production API ports, read ONLY to report. See node_report().
NODE_PORTS = (5000, 5020, 5060)

# The watchdog stamps every line "YYYY-MM-DDTHH:MM:SSZ LEVEL ..." (UTC).
_TS = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z ")


def node_report():
    """Are the nodes answering? REPORTED, NEVER ACTED ON.

    Why look at all: this guard heals the WATCHDOG, and the watchdog heals
    the NODES. That chain assumed the watchdog dies alone. It does not --
    covenant_prod.bat starts nodes and watchdog in one console group, so a
    single window close or Ctrl+C takes the healer and the healed together
    (measured 2026-08-29: all four gone, ^C in the node log). When that
    happens the guard's log was the only thing still being written, and it
    said nothing about the chain being down.

    Why it does not ACT: restarting nodes is the watchdog's job, with its own
    3-strike judgement and its own knowledge of which node is which. A second
    process restarting nodes on a different rule is two supervisors
    disagreeing about the same machine, which is worse than a slow recovery.
    So this only writes down what it saw, so the log tells the truth about
    the whole system rather than about one process in it.
    """
    import urllib.error
    import urllib.request
    up, down = [], []
    for port in NODE_PORTS:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=4):
                up.append(port)
        except (urllib.error.URLError, OSError, ValueError):
            down.append(port)
    return up, down


def glog(msg):
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + msg
    print(line)
    try:
        os.makedirs(LOGDIR, exist_ok=True)
        with open(GUARD_LOG, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


# ------------------------------------------------------------ pure sensing --
def last_stamp(text):
    """Newest parseable UTC timestamp in the log text, as epoch seconds, or
    None. Scans from the END: the newest line is the only one that matters
    and a rotated log can be megabytes."""
    for line in reversed(text.splitlines()[-200:]):
        m = _TS.match(line)
        if m:
            y, mo, d, h, mi, s = (int(g) for g in m.groups())
            try:
                import calendar
                return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0))
            except (ValueError, OverflowError):
                continue
    return None


def decide(gap_s, gap_dead_s, pid_alive, last_attempt_age_s, cooldown_s,
           source_compiles):
    """(action, why) -- the whole decision, pure so it is testable.

    action is one of: "healthy", "hold", "report-only", "revive".
    """
    if gap_s is None:
        return ("report-only", "watchdog log absent or carries no parseable "
                               "timestamp -- nothing to measure a gap against")
    if gap_s <= gap_dead_s:
        return ("healthy", f"last line {int(gap_s)}s old, under the "
                           f"{gap_dead_s}s death threshold")
    if pid_alive:
        return ("report-only", f"gap {int(gap_s)}s but the recorded watchdog "
                               f"PID is alive -- a wedged process is not a "
                               f"dead one; doubling it doubles every restart "
                               f"it might still make")
    if last_attempt_age_s is not None and last_attempt_age_s < cooldown_s:
        return ("hold", f"gap {int(gap_s)}s and no live PID, but the last "
                        f"revival attempt was {int(last_attempt_age_s)}s ago "
                        f"(< {cooldown_s}s) -- a guard without a cooldown is "
                        f"a crash-loop amplifier")
    if not source_compiles:
        return ("report-only", "covenant_watchdog.py does not compile -- "
                               "reviving it turns one death into a loop; a "
                               "human or a session must fix the source")
    return ("revive", f"gap {int(gap_s)}s, no live watchdog PID, cooldown "
                      f"clear, source compiles")


# --------------------------------------------------------------- os probes --
def pid_alive_windows(pid):
    """Is PID alive AND a python process? tasklist, stdlib only."""
    try:
        out = covenant_quiet.run(
            ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV",
             "/NH"], capture_output=True, text=True, timeout=30).stdout
        return "python" in out.lower()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def read_state():
    try:
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_state(d):
    try:
        with open(STATE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(d, fh, indent=1)
    except OSError:
        pass


def revive():
    """Spawn the watchdog exactly as covenant_prod does: detached, its own
    process group, stdout to its own file. Never waits on it."""
    py = os.path.join(HERE, ".venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        py = sys.executable
    out = open(os.path.join(LOGDIR, "watchdog-stdout.log"), "a",
               encoding="utf-8", errors="replace")
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    if os.name == "nt":
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    p = subprocess.Popen([py, WD_SRC], cwd=HERE, stdout=out, stderr=out,
                         creationflags=flags)
    return p.pid


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    status_only = "--status" in argv

    text = ""
    try:
        with open(WD_LOG, encoding="utf-8", errors="replace") as fh:
            try:
                fh.seek(0, 2)
                fh.seek(max(0, fh.tell() - 65536))
            except OSError:
                pass
            text = fh.read()
    except OSError:
        pass
    stamp = last_stamp(text)
    gap = (time.time() - stamp) if stamp is not None else None

    pid, alive = None, False
    try:
        with open(WD_PID, encoding="utf-8") as fh:
            pid = int(fh.read().strip())
        alive = pid_alive_windows(pid)
    except (OSError, ValueError):
        pass

    state = read_state()
    last_attempt = state.get("last_attempt_epoch")
    attempt_age = (time.time() - last_attempt) if last_attempt else None

    compiles = True
    if gap is not None and gap > GAP_DEAD_S and not alive:
        try:
            py_compile.compile(WD_SRC, doraise=True)
        except Exception as e:                              # noqa: BLE001
            compiles = False
            glog(f"WATCHDOG SOURCE BROKEN: {type(e).__name__}: {e}")

    action, why = decide(gap, GAP_DEAD_S, alive, attempt_age, COOLDOWN_S,
                         compiles)

    # What the nodes are doing, on every pass, whatever the verdict about
    # the watchdog. A guard that reports the supervisor as healthy while the
    # three things it supervises are dead is technically correct and
    # practically useless.
    up, down = node_report()
    if down:
        glog(f"NODES DOWN {down} (up {up or 'none'}) -- not this guard's to "
             f"restart; the watchdog owns that, with its 3-strike judgement")

    if action == "healthy":
        # Quiet on the console, one line in the file: a guard that logs
        # nothing cannot prove IT ran, and a dead guard beside a dead
        # watchdog is the 08-24 silence one layer up.
        glog(f"ok: {why}" + (f" | nodes up {up}" if up else " | NO node up"))
        return 0 if not down else 1
    if status_only or action in ("hold", "report-only"):
        glog(f"{action.upper()}: {why}")
        return 0 if action == "hold" else 1
    # revive
    state["last_attempt_epoch"] = time.time()
    state["attempts"] = int(state.get("attempts", 0)) + 1
    write_state(state)                     # BEFORE the spawn: a guard that
    new_pid = revive()                     # dies mid-spawn must not retry hot
    glog(f"REVIVED the watchdog (pid {new_pid}): {why} -- attempt "
         f"#{state['attempts']}. The revived process heals the nodes itself; "
         f"this guard touched nothing else.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
