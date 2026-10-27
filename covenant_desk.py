#!/usr/bin/env python3
"""covenant_desk.py -- when the phone is not collecting his messages, put them on the PC's screen.

HIS WORDS, 2026-10-13: "if it's trying to communicate something, tell it to just put it in a notepad and make
that pop up", then "sure fix the phone though".

WHY. The direct line (covenant_contact) delivers through the phone: the phone checks in every ten minutes and
takes what waits. When the phone is off the network -- 2026-10-08 for 53 hours (A329), and again from
2026-10-12 06:48 -- every message for him waits unread: Tetsu's questions, a nightly that was NOT GREEN. The
road shows phone_silent on the orbs, but nothing reaches HIM.

WHAT IT DOES. A message the phone has not collected within STUCK_S is stuck. When there is a stuck message the
desk has not shown before, every stuck message is written to logs/FOR_YOU.txt (newest last, who wrote it and
why) and that file is opened in Notepad -- once per new message, never on a timer, so a quiet line opens
nothing. It changes nothing on the line: the phone still collects every message when it comes back (the desk
does not mark them seen), and what the desk showed is kept in logs/desk_state.json.

WHO CALLS IT. The watchdog, every DESK_EVERY rounds, and only as the daemon (its persist flag) -- a suite
that imports the watchdog can never open a window on his screen (the A235 lesson). Tests pass open_fn.

  python covenant_desk.py            # what the desk would show now, without opening anything
  python covenant_desk.py --open     # write and open it now, by hand
  python covenant_desk.py --selftest
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DESK_FILE = os.path.join(HERE, "logs", "FOR_YOU.txt")
DESK_STATE = os.path.join(HERE, "logs", "desk_state.json")
STUCK_S = 1800          # three missed ten-minute check-ins
DESK_EVERY = 10         # watchdog rounds (60 s each)


def _open_notepad(path):
    # A GUI program: NO_WINDOW (covenant_quiet) hides only CONSOLES, so this window shows, as he asked.
    subprocess.Popen(["notepad.exe", path], close_fds=True)


def stuck(outbox=None, state_path=None, now=None):
    """Messages on the line that the phone has not collected within STUCK_S, oldest first."""
    # pending() hands the phone a trimmed row (no "at", no "kind"), so read the line's own rows and the same
    # seen-set pending() uses; the first version read pending() and could never find a message old enough.
    import covenant_contact as C
    now = time.time() if now is None else now
    seen = set((C._state(state_path).get("seen") or {}).keys())
    return [r for r in C._rows(outbox) if r.get("id") and r["id"] not in seen
            and now - float(r.get("at") or now) >= STUCK_S]


def render(rows, now=None):
    now = time.time() if now is None else now
    out = ["FOR YOU -- messages the phone has not collected",
           "Written %s. Your phone has not picked these up, so they are here instead." % time.strftime("%Y-%m-%d %H:%M", time.localtime(now)),
           "They stay on the phone's line too, and the phone gets them when it checks in again.", ""]
    for r in rows:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(r.get("at") or now)))
        out.append("%s  from %s%s" % (when, r.get("actor", "?"), "  (a question for you)" if r.get("kind") == "question" else ""))
        out.append("  why: %s" % r.get("why", ""))
        out.append("  %s" % r.get("text", ""))
        out.append("")
    return "\n".join(out)


def _desk_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def notice(outbox=None, state_path=None, desk_file=None, desk_state=None, open_fn=None, now=None):
    """Show stuck messages on the desk when one is new. Returns {"stuck": n, "new": n, "opened": bool}."""
    desk_file = desk_file or DESK_FILE
    desk_state = desk_state or DESK_STATE
    open_fn = open_fn or _open_notepad
    now = time.time() if now is None else now
    rows = stuck(outbox, state_path, now)
    st = _desk_state(desk_state)
    shown = set(st.get("shown") or [])
    new = [r for r in rows if r.get("id") not in shown]
    res = {"stuck": len(rows), "new": len(new), "opened": False}
    if not new:
        return res
    os.makedirs(os.path.dirname(desk_file), exist_ok=True)
    tmp = desk_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(render(rows, now))
    os.replace(tmp, desk_file)
    st["shown"] = sorted(shown | {r["id"] for r in new if r.get("id")})[-2000:]
    st["last_opened"] = now
    tmp = desk_state + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    os.replace(tmp, desk_state)
    open_fn(desk_file)
    res["opened"] = True
    return res


def selftest():
    ok = []

    def check(name, cond):
        ok.append(bool(cond))
        print("%s  %s" % ("ok  " if cond else "FAIL", name))

    d = tempfile.mkdtemp()
    outbox, cstate = os.path.join(d, "outbox.jsonl"), os.path.join(d, "contact_state.json")
    dfile, dstate = os.path.join(d, "FOR_YOU.txt"), os.path.join(d, "desk_state.json")
    import covenant_contact as C
    now = time.time()
    old = C.say("the nightly pass was NOT GREEN", "nightly: not green", actor="nightly", outbox=outbox)
    with open(outbox, encoding="utf-8") as fh:       # age that row past STUCK_S
        rows = [json.loads(l) for l in fh]
    rows[0]["at"] = now - STUCK_S - 60
    with open(outbox, "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows))
    fresh = C.say("a fresh message", "test", actor="tester", outbox=outbox)
    opened = []
    kw = dict(outbox=outbox, state_path=cstate, desk_file=dfile, desk_state=dstate, open_fn=opened.append, now=now)
    r = notice(**kw)
    check("D1 a message the phone left for 30+ min is shown and opened once", r == {"stuck": 1, "new": 1, "opened": True}
          and opened == [dfile])
    text = open(dfile, encoding="utf-8").read()
    check("D2 the file says who wrote it, why, and the text; the fresh one is not there yet",
          "from nightly" in text and "nightly: not green" in text and "NOT GREEN" in text and "a fresh message" not in text)
    r = notice(**kw)
    check("D3 the same stuck message does not open Notepad again", r["opened"] is False and len(opened) == 1)
    r = notice(**dict(kw, now=now + STUCK_S + 5))
    check("D4 when the fresh one is stuck too, it opens again, with both", r == {"stuck": 2, "new": 1, "opened": True}
          and len(opened) == 2 and "a fresh message" in open(dfile, encoding="utf-8").read())
    check("D6 the desk does not mark the line seen: the phone is still handed both",
          not (C._state(cstate).get("seen") or {}) and len(C.pending(outbox, cstate)) == 2)
    C.mark_seen([old["id"], fresh["id"]], state_path=cstate)
    r = notice(**dict(kw, now=now + 2 * STUCK_S))
    check("D5 once the phone has collected them, nothing is stuck and nothing opens",
          r == {"stuck": 0, "new": 0, "opened": False} and len(opened) == 2)
    print("\nDESK: %d/%d passed" % (sum(ok), len(ok)))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--open" in sys.argv:
        print(notice())
    else:
        rows = stuck()
        print("%d stuck message(s); the desk would show:\n" % len(rows))
        print(render(rows))
