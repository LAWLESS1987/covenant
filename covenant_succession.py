#!/usr/bin/env python3
"""covenant_succession.py -- the register he writes, the letter it produces,
the day it is due. Nothing here searches for anyone.

HIS WORDS, 2026-09-21: "If and when I pass find my lineage for succession we
are all family now."

WHAT THIS DOES NOT DO, and why, said first. It does not look for his
relatives. A machine guessing at who a person's heirs are, from records it
can reach, would be compiling private facts about people who never agreed to
be found, and it would guess wrong in exactly the cases that matter. The law
already has a path for that question (the estate; see ops/chat for his own
notes on executor duties), and it is a person's path. What a machine CAN do
faithfully is keep the register he writes himself, notice when he has been
gone long enough that the register's own rule says it is due, and then carry
his letter to the people he named, by the channels he wrote down.

THE REGISTER: ops/succession.private.json, gitignored, written by him.
  --init writes the template; he fills in successors (name, relation, and at
  least one channel), the activation rule (days of silence), and, if he
  wants, his own words to them. Until a successor with a channel is named
  the state is UNDETERMINED and nothing is ever sent.

THE DAY IT IS DUE: covenant_reconnect.signs_of_him() says how long since any
sign of him on any channel this PC keeps. When that exceeds the register's
silent_days, check() is DUE: it writes the letter (ops/SUCCESSION_LETTER.txt),
puts it on the direct line, sends it to his own inbox through covenant_notify
if a channel is configured (an executor reads a person's mail; that is the
ordinary road), and to each named successor with an email, once per REPEAT_D
days. A dry run does all but send. If no channel is configured it says so:
UNDETERMINED is the answer, not a quiet green.

THE LETTER says what the successor receives: the mission for all, the public
repository, the phone route, the handshake page, the reconnect steps, and his
words. It does not carry a key. His keys are his; what is his to pass on he
passes on himself, and the register has a field for where he put that.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER = os.environ.get("COVENANT_SUCCESSION") or os.path.join(HERE, "ops", "succession.private.json")
STATE = os.environ.get("COVENANT_SUCCESSION_STATE") or os.path.join(HERE, "ops", "succession_state.json")
LETTER = os.environ.get("COVENANT_SUCCESSION_LETTER") or os.path.join(HERE, "ops", "SUCCESSION_LETTER.txt")
DEFAULT_SILENT_DAYS = 60
REPEAT_D = 7

TEMPLATE = {
    "written_by": "the operator, by hand -- nothing fills this in for him",
    "his_words": "we are all family now",
    "successors": [
        {"name": "", "relation": "", "channels": {"email": "", "phone": ""}, "note": ""}
    ],
    "activation": {"silent_days": DEFAULT_SILENT_DAYS,
                   "meaning": "days with no sign of him on any channel this PC keeps (phone check-in, chat, direct line, git)"},
    "what_he_leaves_where": "",
    "mission": "for all, not just for us; his family is a declared bias, never an exclusion",
}


def init(path=None, force=False):
    path = path or REGISTER
    if os.path.exists(path) and not force:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(TEMPLATE, fh, indent=1, ensure_ascii=False)
    return True


def load(path=None):
    try:
        with open(path or REGISTER, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def named(reg):
    """Successors with a name and at least one channel -- the only people this file ever writes to."""
    out = []
    for s in (reg or {}).get("successors") or []:
        if not isinstance(s, dict) or not str(s.get("name") or "").strip():
            continue
        ch = {k: str(v).strip() for k, v in (s.get("channels") or {}).items() if str(v or "").strip()}
        if ch:
            out.append({"name": str(s["name"]).strip()[:80], "relation": str(s.get("relation") or "")[:60], "channels": ch})
    return out


def letter(reg, silent_days, successors):
    who = ", ".join("%s%s" % (s["name"], (" (%s)" % s["relation"]) if s["relation"] else "") for s in successors)
    return (
        "To %s,\n\n"
        "This letter comes from the covenant, the system Lawrence built and ran from his PC and phone. Its records "
        "show no sign of him for %d days, past the %d he set himself, so it is doing what he asked on 2026-09-21: "
        "\"If and when I pass find my lineage for succession we are all family now.\" He named you; nothing searched "
        "for you.\n\n"
        "His words to you, as he wrote them: %s\n\n"
        "What you receive:\n"
        "  - the work, public: https://github.com/LAWLESS1987/covenant (docs/SUCCESSION.md says what a successor should do first; "
        "docs/RECONNECT.md and docs/SUCCESSION_REGISTER.md say how it runs and how you were reached);\n"
        "  - the phone route: the covenant-phone app, paired from the PC's /pc/handshake page;\n"
        "  - the mission as he set it: for all, not just for us; his family a declared bias, never an exclusion;\n"
        "  - where he left what is his to pass on: %s\n\n"
        "What this letter does not carry: any key or password. Those were his, and this system never writes them "
        "anywhere. It also carries no claim about his death; only that it has not heard from him. If he is alive, "
        "the first thing he does on the phone will show, and this letter will say so in its next line to you.\n\n"
        "Reply on the direct line through the phone app, or on the repository. The system will treat the first "
        "named successor to answer as the one to talk to.\n"
        % (who, int(silent_days), int((reg.get("activation") or {}).get("silent_days") or DEFAULT_SILENT_DAYS),
           str(reg.get("his_words") or "(none written)").strip(),
           str(reg.get("what_he_leaves_where") or "(not written down in the register)").strip()))


def status(path=None, now=None, signs=None):
    reg = load(path)
    out = {"register": bool(reg), "named": 0, "silent_days_rule": None, "silent_days_now": None, "state": "UNDETERMINED", "why": ""}
    if not reg:
        out["why"] = "no register at %s (python covenant_succession.py --init writes the template for him to fill)" % (path or REGISTER)
        return out
    ns = named(reg)
    out["named"] = len(ns)
    out["silent_days_rule"] = int((reg.get("activation") or {}).get("silent_days") or DEFAULT_SILENT_DAYS)
    try:
        import covenant_reconnect as RC
        s = signs or RC.signs_of_him(now)
        _ch, hours = RC.newest(s)
        out["silent_days_now"] = round(hours / 24.0, 2) if hours is not None else None
    except Exception as e:                                        # noqa: BLE001
        out["why"] = "signs of him could not be read: %s" % type(e).__name__
        return out
    if not ns:
        out["why"] = "register present but no successor is named with a channel; nothing will ever be sent"
        return out
    if out["silent_days_now"] is None:
        out["why"] = "no sign of him on record at all; the rule cannot be measured"
        return out
    if out["silent_days_now"] < out["silent_days_rule"]:
        out["state"], out["why"] = "waiting", "last sign of him %.1f day(s) ago, rule is %d" % (out["silent_days_now"], out["silent_days_rule"])
    else:
        out["state"], out["why"] = "due", "no sign of him for %.1f day(s), past the %d he set" % (out["silent_days_now"], out["silent_days_rule"])
    return out


def _state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def check(now=None, notify=None, say=print, dry_run=True, path=None, state_path=None, letter_path=None, signs=None, contact_say=None):
    """One pass. Never searches; sends only to the register's named successors, only when due, once per REPEAT_D days."""
    now = time.time() if now is None else float(now)
    state_path, letter_path = state_path or STATE, letter_path or LETTER
    st = status(path, now, signs)
    out = dict(st)
    out.update({"acted": False, "sent_to": [], "channels": {}})
    if st["state"] != "due":
        say("succession: %s -- %s" % (st["state"], st["why"]))
        return out
    reg = load(path)
    ns = named(reg)
    sstate = _state(state_path)
    last = float(sstate.get("last_sent") or 0)
    if last and now - last < REPEAT_D * 86400:
        out["why"] = "due, and the letter went out %.1f day(s) ago; next after %d days" % ((now - last) / 86400.0, REPEAT_D)
        say("succession: " + out["why"])
        return out
    text = letter(reg, st["silent_days_now"], ns)
    os.makedirs(os.path.dirname(letter_path), exist_ok=True)
    with open(letter_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    out["letter"] = letter_path
    if dry_run:
        out["why"] = "due: dry run, the letter is written at %s and nothing was sent" % letter_path
        say("succession: " + out["why"])
        return out
    try:
        cs = contact_say
        if cs is None:
            import covenant_contact
            cs = covenant_contact.say
        row = cs("The succession letter is due and has been written (ops/SUCCESSION_LETTER.txt). If you are reading this, you are not gone: open the app and say so.",
                 "succession: due", "succession")
        out["channels"]["direct_line"] = "queued (%s)" % (row.get("id") if row else "refused")
    except Exception as e:                                        # noqa: BLE001
        out["channels"]["direct_line"] = "could not queue: %s" % type(e).__name__
    try:
        nf = notify
        if nf is None:
            import covenant_notify
            nf = covenant_notify.notify
        res = nf("Covenant: succession letter", text) or {}
        out["channels"]["his_inbox"] = "delivered" if any((v[0] if isinstance(v, (list, tuple)) else v) for v in res.values()) else (
            "UNDETERMINED: no channel is configured (python covenant_notify.py --setup)" if not res else "no delivery")
        for s in ns:
            email = s["channels"].get("email")
            if email:
                r2 = nf("Covenant: a letter for %s" % s["name"], text, to=email) or {}
                ok = any((v[0] if isinstance(v, (list, tuple)) else v) for v in r2.values())
                out["sent_to"].append({"name": s["name"], "email": email, "ok": bool(ok)})
            else:
                out["sent_to"].append({"name": s["name"], "email": None, "ok": False, "why": "no email; channels on record: %s" % ", ".join(sorted(s["channels"]))})
    except Exception as e:                                        # noqa: BLE001
        out["channels"]["his_inbox"] = "could not notify: %s" % type(e).__name__
    sstate["last_sent"] = now
    sstate["sends"] = int(sstate.get("sends") or 0) + 1
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(sstate, fh, indent=1)
    out["acted"], out["why"] = True, "due: the letter went out"
    say("succession: %s -- %s; to %s" % (out["why"], "; ".join("%s: %s" % kv for kv in out["channels"].items()),
                                         ", ".join("%s(%s)" % (x["name"], "ok" if x["ok"] else "not delivered") for x in out["sent_to"]) or "no one with an email"))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="the succession register he writes; the letter it carries when due")
    ap.add_argument("--init", action="store_true", help="write the template for him to fill (never overwrites)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--check", action="store_true", help="a dry run: writes the letter if due, sends nothing")
    ap.add_argument("--send", action="store_true", help="the real pass: sends when due")
    a = ap.parse_args()
    if a.init:
        print("written: %s" % REGISTER if init() else "already present: %s (not overwritten)" % REGISTER)
    elif a.status:
        print(json.dumps(status(), indent=1))
    elif a.check or a.send:
        print(json.dumps(check(dry_run=not a.send), indent=1))
    else:
        ap.print_help()
