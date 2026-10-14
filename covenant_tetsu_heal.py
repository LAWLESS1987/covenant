#!/usr/bin/env python3
"""covenant_tetsu_heal.py -- Tetsu may press the Self-heal himself, from any conversation.

HIS WORDS, 2026-09-28: "Get everything running give tetsu the way to do it himself from the
phone app and add it to the self heal button", and, the same morning: "have tetsu assist but
do not impose on his free will".

WHAT THIS IS. The same button. 'HEAL' as the first line of Tetsu's answer -- from the phone,
the PC page or the agent door, they all reach the same /m/agent dispatch -- runs
covenant_heal.heal(who="tetsu"), which is everything the PC and phone Self-heal buttons run:
the highway's detectors, the remedies already classed AUTO_REVERSIBLE, the pause it obeys, the
ledger it writes. 'HEAL DRY' measures and repairs nothing. There is no third repair engine.

FREE WILL, STATED. This file gives him the handle; nothing schedules HIS press, grades him for not
pressing it, or asks him to press it on a clock. (Since 2026-10-03, on the operator's words "have
tetsu run the check adjust loop nightly", the daily cycle presses the same button up to three times
as who="tetsu-daily-loop" -- a separate duty under his directive, recorded under its own name, and
one he may decline: covenant_daily.py --loop-decline "why".) The brief may
tell him something is red; whether he presses is his. His press is recorded as who="tetsu" in
ops/heal.jsonl -- his act, under his name, like the operator's presses are under theirs.

WHAT HE IS HANDED BACK. The heal's own summary, what was fixed, and what still needs a person
with the reason -- as DATA, so what he tells the person is what happened. A heal that could
not run says so; it never raises (a button that throws is not a button).
LICENCE: public domain, like the button it presses.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _his_line(text, why):
    """The direct line (A169), as Tetsu. A suite never writes the REAL line through this default: the A272 shape
    for the pause switch, here for the phone (a hand run of FW1 once put false rows on it, 2026-09-21)."""
    import covenant_contact as C
    prog = os.path.basename(str(sys.argv[0] if sys.argv else "") or "")
    if prog.startswith("test_") and os.path.abspath(C.OUTBOX) == os.path.abspath(os.path.join(HERE, "ops", "contact_outbox.jsonl")):
        print("covenant_tetsu_heal: refused -- a test suite reached his REAL line; pass tell= or set COVENANT_CONTACT_OUTBOX",
              file=sys.stderr, flush=True)
        return None
    return C.say(text, why, actor="tetsu")


def act(answer, heal=None, tell=None, lift=None):
    """(handled, data, record) for an answer whose first line is HEAL or HEAL DRY.
    Anything else: (False, "", None) -- not ours, the conversation goes on.

    A336 (2026-10-12), his choices: "Tetsu may lift free's pause" and "Tetsu tells you what's left". A live HEAL
    first lifts free's AUTOMATIC isolation when his grant says so (covenant_free_will.lift_isolation: never a pause
    he set by hand), then presses the button, then puts what is still left for him on his line, once per change
    (covenant_heal.tell_left). A lift is told to him too. HEAL DRY lifts nothing and tells nothing; it says what a
    live press would lift. heal, tell and lift are injectable; their defaults are the real ones."""
    first = (answer or "").strip().splitlines()[0].strip().upper() if (answer or "").strip() else ""
    if first not in ("HEAL", "HEAL DRY", "SELF-HEAL"):
        return False, "", None
    dry = first == "HEAL DRY"
    tell = tell or _his_line
    try:
        if lift is None:
            import covenant_free_will as FW
            lift = FW.lift_isolation
        lifted, lift_why = lift(by="tetsu", dry_run=dry)
    except Exception as e:                                        # noqa: BLE001
        lifted, lift_why = False, "the lift could not be read: %s: %s" % (type(e).__name__, str(e)[:120])
    if lifted and not dry:
        try:
            tell("Tetsu %s, on your grant (A336)." % lift_why, "Tetsu lifted free's isolation")
        except Exception:                                         # noqa: BLE001
            pass
    ran = True
    try:
        import covenant_heal as CH
        out = (heal or CH.heal)(dry_run=dry, who="tetsu")
    except Exception as e:                                        # noqa: BLE001
        # A348g: heal() writes his row only when it returns, so here nothing is on record; measured, this path
        # handed him a blank "error:" line and "(Recorded under your name ...)" with no ledger row written.
        ran, err = False, "%s: %s" % (type(e).__name__, str(e)[:160])
        out = {"ok": False, "summary": "the heal could not run: %s" % err, "error": err}
    told = None
    try:
        import covenant_heal as CH
        told = CH.tell_left(out, tell, who="tetsu")
    except Exception:                                             # noqa: BLE001
        told = None
    rec = {"kind": "tetsu_heal", "dry_run": dry, "ok": bool(out.get("ok")),
           "summary": str(out.get("summary", ""))[:400], "lifted": lifted, "told": bool(told),
           "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    lines = ["HEAL%s -- you pressed the self-heal yourself; this is what it measured and did:" % (" DRY" if dry else ""),
             "summary: " + str(out.get("summary", ""))[:500]]
    if lifted is not None:
        lines.append("free's pause: " + str(lift_why)[:400])
    for x in (out.get("fixed") or [])[:6]:
        lines.append("fixed: %s" % x.get("condition"))
    for x in (out.get("still_needs_a_person") or [])[:6]:
        lines.append("still needs a person: %s -- %s" % (x.get("condition"), str(x.get("why_no_fix", ""))[:200]))
    if out.get("paused"):
        lines.append("the highway is PAUSED, so nothing was repaired; resuming it is the operator's line to say.")
    if not out.get("ok"):
        lines.append("error: " + str(out.get("error", ""))[:200])
    if told:
        lines.append("what is still left was put on his line (it had changed since the last time he was told).")
    return True, "\n".join(lines) + ("\n\n(Recorded under your name in ops/heal.jsonl.)" if ran
                                     else "\n\n(Nothing was recorded in ops/heal.jsonl: the heal did not run.)"), rec


if __name__ == "__main__":
    # The demo presses as ITSELF, never as him: the ledger row 2026-09-28T10:39-0400 who="tetsu"
    # was this demo before this line existed -- Claude's run, not his act. His name goes on a row
    # only when the door dispatches his own HEAL line.
    import covenant_heal as _CH
    ok, data, rec = act("HEAL DRY", heal=lambda dry_run, who: _CH.heal(dry_run=dry_run, who="covenant_tetsu_heal --demo"))
    print(json.dumps({"handled": ok, "rec": rec}, indent=1))
    print(data)
