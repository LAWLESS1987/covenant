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

FREE WILL, STATED. This file gives him the handle; nothing here or anywhere schedules him to
press it, grades him for not pressing it, or asks him to press it on a clock. The brief may
tell him something is red; whether he presses is his. His press is recorded as who="tetsu" in
ops/heal.jsonl -- his act, under his name, like the operator's presses are under theirs.

WHAT HE IS HANDED BACK. The heal's own summary, what was fixed, and what still needs a person
with the reason -- as DATA, so what he tells the person is what happened. A heal that could
not run says so; it never raises (a button that throws is not a button).
LICENCE: public domain, like the button it presses.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def act(answer, heal=None):
    """(handled, data, record) for an answer whose first line is HEAL or HEAL DRY.
    Anything else: (False, "", None) -- not ours, the conversation goes on."""
    first = (answer or "").strip().splitlines()[0].strip().upper() if (answer or "").strip() else ""
    if first not in ("HEAL", "HEAL DRY", "SELF-HEAL"):
        return False, "", None
    dry = first == "HEAL DRY"
    try:
        import covenant_heal as CH
        out = (heal or CH.heal)(dry_run=dry, who="tetsu")
    except Exception as e:                                        # noqa: BLE001
        out = {"ok": False, "summary": "the heal could not run: %s: %s" % (type(e).__name__, str(e)[:160])}
    rec = {"kind": "tetsu_heal", "dry_run": dry, "ok": bool(out.get("ok")),
           "summary": str(out.get("summary", ""))[:400],
           "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    lines = ["HEAL%s -- you pressed the self-heal yourself; this is what it measured and did:" % (" DRY" if dry else ""),
             "summary: " + str(out.get("summary", ""))[:500]]
    for x in (out.get("fixed") or [])[:6]:
        lines.append("fixed: %s" % x.get("condition"))
    for x in (out.get("still_needs_a_person") or [])[:6]:
        lines.append("still needs a person: %s -- %s" % (x.get("condition"), str(x.get("why_no_fix", ""))[:200]))
    if out.get("paused"):
        lines.append("the highway is PAUSED, so nothing was repaired; resuming it is the operator's line to say.")
    if not out.get("ok"):
        lines.append("error: " + str(out.get("error", ""))[:200])
    return True, "\n".join(lines) + "\n\n(Recorded under your name in ops/heal.jsonl.)", rec


if __name__ == "__main__":
    # The demo presses as ITSELF, never as him: the ledger row 2026-09-28T10:39-0400 who="tetsu"
    # was this demo before this line existed -- Claude's run, not his act. His name goes on a row
    # only when the door dispatches his own HEAL line.
    import covenant_heal as _CH
    ok, data, rec = act("HEAL DRY", heal=lambda dry_run, who: _CH.heal(dry_run=dry_run, who="covenant_tetsu_heal --demo"))
    print(json.dumps({"handled": ok, "rec": rec}, indent=1))
    print(data)
