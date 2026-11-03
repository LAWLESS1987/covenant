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
said on stderr.

COVERS EVERY TAB-OPENING DOOR (A160-shaped coverage gap found 2026-11-02): the first version matched only
tabs_create / tabs_create_mcp / preview_start, so `navigate` (which opens the pane when none is open) and
`tabs_context_mcp` with createIfEmpty opened a tab AROUND the guard and could still starve the model. The matcher
in .claude/settings.json now also lists both navigate tools and tabs_context_mcp, and this hook is PAYLOAD-AWARE:
it RAM-checks a call only when that call would actually open a tab, so a read-only tabs_context_mcp (listing tabs,
which is exactly how the model is told to recover by closing them) is never blocked, floor or no floor."""
import ctypes
import json
import os
import sys
import urllib.request

FLOOR_GB = float(os.environ.get("COVENANT_TAB_RAM_FLOOR_GB", "2.5"))
MODEL_GB = 2.6                                   # qwen2.5-3b's bar, covenant_model.CANDIDATES (not imported: a hook stays light)
MODEL_HEALTH = "http://127.0.0.1:%s/health" % os.environ.get("COVENANT_MODEL_PORT", "8081")

# Tools that ALWAYS put a new page in memory when called.
_ALWAYS_OPEN = frozenset((
    "mcp__Claude_Browser__tabs_create", "mcp__claude-in-chrome__tabs_create_mcp",
    "mcp__Claude_Browser__preview_start",
    "mcp__Claude_Browser__navigate", "mcp__claude-in-chrome__navigate",
))
# Tools that open a tab only on a flag in their input (else they are read-only).
_CONDITIONAL_OPEN = {"mcp__claude-in-chrome__tabs_context_mcp": ("createIfEmpty",)}


def would_open_tab(tool_name, tool_input):
    """True iff invoking `tool_name` with `tool_input` would put a new page in memory. A
    read-only call (listing tabs, reading a page) is False, so the floor never blocks the
    very calls the model needs to SEE and CLOSE tabs and recover. Unknown tool -> False
    (the matcher decides what reaches this hook; this only refines the ones that do)."""
    if tool_name in _ALWAYS_OPEN:
        return True
    flags = _CONDITIONAL_OPEN.get(tool_name)
    if flags and isinstance(tool_input, dict):
        return any(bool(tool_input.get(f)) for f in flags)
    return False


def decide(free, up, opening):
    """Pure decision: (exit_code, message). Only an OPENING call is ever blocked. free is
    GB free or None (unreadable -> allow, unmeasured). `up` is whether the model answers."""
    if not opening:
        return 0, ""
    if free is None:
        return 0, "ram_guard: free memory unreadable; tab allowed, unmeasured\n"
    need = FLOOR_GB + (0.0 if up else MODEL_GB)
    if free < need:
        return 2, (
            "ram_guard: BLOCKED -- %.2f GB free, under %.1f GB (his rule 10-18: a %.1f GB floor%s). Read and close "
            "open tabs (tabs_close_mcp) first, then open the next batch -- at most 3 seats at a time.\n"
            % (free, need, FLOOR_GB, "" if up else ", plus %.1f GB kept for Tetsu's model, which is put away now"
               % MODEL_GB))
    return 0, ""


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
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:                                             # noqa: BLE001
        pass
    # PreToolUse payload: {"tool_name": ..., "tool_input": {...}}. If it cannot be parsed,
    # fall back to treating the call as opening (the matcher mostly lists openers) so the
    # model's room is protected even without the payload.
    tool_name, tool_input = None, {}
    try:
        d = json.loads(raw) if raw else {}
        tool_name = d.get("tool_name")
        tool_input = d.get("tool_input") or {}
    except Exception:                                             # noqa: BLE001
        pass
    opening = would_open_tab(tool_name, tool_input) if tool_name else True
    code, msg = decide(free_gb(), model_up(), opening)
    if msg:
        sys.stderr.write(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
