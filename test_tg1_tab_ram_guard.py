#!/usr/bin/env python3
"""
TG1 -- both-ways guard for the tab RAM guard (.claude/hooks/ram_guard.py). Closes the
coverage side-door found 2026-11-02: the PreToolUse matcher caught only tabs_create /
tabs_create_mcp / preview_start, so `navigate` (opens the pane when none is open) and
`tabs_context_mcp{createIfEmpty}` opened a tab AROUND the guard and could starve Tetsu's
model. Fix = widen the matcher to every opener AND make the hook payload-aware so a
read-only tabs_context_mcp (how the model is told to recover by closing tabs) is never
blocked.

Drives it both ways: every opener is gated and blocks under the floor; a read-only call
is allowed even under the floor; the floor keeps the model's room only while the model is
down; unreadable RAM fails open; and the live settings.json matcher actually lists every
opener (a regression there reopens the side-door).

Run:  python test_tg1_tab_ram_guard.py    (exit 0 = all pass)
"""
import importlib.util
import json
import os
import sys

PASS = [0]
FAIL = [0]


def check(name, cond, detail=""):
    if cond:
        PASS[0] += 1
        print("  ok  ", name)
    else:
        FAIL[0] += 1
        print("  FAIL", name, "--", detail)


HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, ".claude", "hooks", "ram_guard.py")
SETTINGS = os.path.join(HERE, ".claude", "settings.json")


def _load_hook():
    spec = importlib.util.spec_from_file_location("_ram_guard_probe", HOOK)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    rg = _load_hook()
    FLOOR = rg.FLOOR_GB
    MODEL = rg.MODEL_GB

    # ---- would_open_tab: openers vs read-only, both ways
    openers = ("mcp__Claude_Browser__tabs_create", "mcp__claude-in-chrome__tabs_create_mcp",
               "mcp__Claude_Browser__preview_start", "mcp__Claude_Browser__navigate",
               "mcp__claude-in-chrome__navigate")
    check("TG1 every always-open tool is seen as opening a tab",
          all(rg.would_open_tab(t, {}) for t in openers),
          str([t for t in openers if not rg.would_open_tab(t, {})]))
    check("TG1 tabs_context_mcp WITHOUT createIfEmpty is read-only (not an open)",
          rg.would_open_tab("mcp__claude-in-chrome__tabs_context_mcp", {}) is False)
    check("TG1 tabs_context_mcp WITH createIfEmpty IS an open (the side-door path)",
          rg.would_open_tab("mcp__claude-in-chrome__tabs_context_mcp", {"createIfEmpty": True}) is True)
    check("TG1 an unrelated tool never counts as opening a tab",
          rg.would_open_tab("mcp__Claude_Browser__tabs_close", {}) is False
          and rg.would_open_tab("Read", {}) is False)

    # ---- decide(): only an opening call is ever blocked, and only under the floor
    lo = FLOOR - 0.1          # just under the plain floor, model up
    code, msg = rg.decide(lo, True, True)
    check("TG1 under the floor, an OPENING call is BLOCKED (exit 2) with a reason", code == 2 and "BLOCKED" in msg, msg)
    code, _ = rg.decide(lo, True, False)
    check("TG1 broken the other way: the SAME low RAM allows a NON-opening call (exit 0)", code == 0)
    code, _ = rg.decide(FLOOR + 1.0, True, True)
    check("TG1 above the floor, an opening call is allowed (exit 0)", code == 0)

    # ---- the model's room: while the model is DOWN the floor also keeps MODEL_GB
    mid = FLOOR + MODEL - 0.1     # above the plain floor, below floor+MODEL
    up_code, _ = rg.decide(mid, True, True)     # model up -> plain floor -> allowed
    down_code, dmsg = rg.decide(mid, False, True)   # model down -> keep its room -> blocked
    check("TG1 the model's room: same RAM is allowed with the model UP but BLOCKED with it DOWN",
          up_code == 0 and down_code == 2 and "model" in dmsg.lower(), "up=%s down=%s" % (up_code, down_code))

    # ---- unreadable RAM fails OPEN (a guard that cannot measure must not stop all browsing)
    code, msg = rg.decide(None, False, True)
    check("TG1 unreadable free memory lets an opening call through, unmeasured (fail-open)",
          code == 0 and "unreadable" in msg)

    # ---- the LIVE matcher actually lists every opener (a regression here reopens the door)
    d = json.load(open(SETTINGS, encoding="utf-8"))
    matcher = None
    for h in (d.get("hooks") or {}).get("PreToolUse") or []:
        if any("ram_guard" in (c.get("command") or "") for c in (h.get("hooks") or [])):
            matcher = h.get("matcher")
    listed = set((matcher or "").split("|"))
    required = set(openers) | {"mcp__claude-in-chrome__tabs_context_mcp"}
    missing = required - listed
    check("TG1 the live settings.json matcher routes EVERY opener (incl. navigate + "
          "tabs_context_mcp) through the guard -- no side-door", not missing, "missing: %s" % sorted(missing))

    print("\nTG1: %d passed, %d failed" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
