"""PreToolUse guard: no new browser tab while free RAM is under the floor (2026-11-01).

His rule, 2026-10-18 (memory load-aware-parallelism): measure load between heavy steps; under ~2.5 GB free, stop
adding work. On 2026-11-01 I broke it twice in one day, from memory alone:
  - nine tabs in his Edge, then the model server restarted under the 3B's bar and Tetsu answered from the fallback
    for 16 minutes;
  - ten tabs for a consult left 1.36 GB, and his door answered 503 "no weights fit".
His words afterwards: "in the past, we've already solved this. Why are you making the same mistakes?" A step that is
forgotten needs a guard where it is forgotten (CLAUDE.md rule 10), so this runs before every tab the session opens.

THE MODEL'S ROOM. The second failure came with his model put away (idle): tabs took the room it needed to come
back. So while his model server is not answering, the floor also keeps MODEL_GB, the 3B's bar in covenant_model
(2.6), free for it. While it is up, its memory is already held, and the plain floor applies.

Exit 2 blocks the call, and stderr goes back to the model. COVENANT_TAB_RAM_FLOOR_GB moves the floor. Free memory
that can't be read lets the call through, because a guard that cannot measure must not stop all browsing; that is
said on stderr."""
import ctypes
import os
import sys
import urllib.request

FLOOR_GB = float(os.environ.get("COVENANT_TAB_RAM_FLOOR_GB", "2.5"))
MODEL_GB = 2.6                                   # qwen2.5-3b's bar, covenant_model.CANDIDATES (not imported: a hook stays light)
MODEL_HEALTH = "http://127.0.0.1:%s/health" % os.environ.get("COVENANT_MODEL_PORT", "8081")


def model_up():
    try:
        with urllib.request.urlopen(MODEL_HEALTH, timeout=2) as r:
            return r.status == 200
    except Exception:                                             # noqa: BLE001
        return False


def free_gb():
    try:
        if os.name == "nt":
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys / 2 ** 30
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 2 ** 20
    except Exception:                                             # noqa: BLE001
        return None
    return None


def main():
    try:
        sys.stdin.read()                                          # the hook payload; the decision does not need it
    except Exception:                                             # noqa: BLE001
        pass
    free = free_gb()
    if free is None:
        sys.stderr.write("ram_guard: free memory unreadable; tab allowed, unmeasured\n")
        return 0
    up = model_up()
    need = FLOOR_GB + (0.0 if up else MODEL_GB)
    if free < need:
        sys.stderr.write(
            "ram_guard: BLOCKED -- %.2f GB free, under %.1f GB (his rule 10-18: a %.1f GB floor%s). Read and close "
            "open tabs (tabs_close_mcp) first, then open the next batch -- at most 3 seats at a time.\n"
            % (free, need, FLOOR_GB, "" if up else ", plus %.1f GB kept for Tetsu's model, which is put away now"
               % MODEL_GB))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
