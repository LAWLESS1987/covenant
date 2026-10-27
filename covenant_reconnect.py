#!/usr/bin/env python3
"""covenant_reconnect.py -- when the phone or the PC goes quiet, reach for him
by every channel this machine has, and say which ones it does not have.

HIS WORDS, 2026-09-21: "For both phone and pc if either or both lost find a
way to reconnect with me."

WHAT THE PC CAN SEE OF HIM, each a record it already keeps:
  phone    ops/phone_checkins.jsonl   the app's ten-minute check-in ("at")
  chat     ops/chat/ask_log.jsonl     his conversations with Tetsu ("t")
  contact  ops/contact_state.json     the direct line: what he was shown
  git      the last commit on this tree (he is its author)
signs_of_him() reads all four and says how many hours ago each last spoke;
a record that does not exist is None, never zero.

THE RULE. When the phone has been silent for PHONE_SILENT_H and NOTHING from
him has arrived on any channel for HIM_SILENT_H, the PC reaches out, once per
REPEAT_H:
  1. a message on the direct line (so the phone shows it the moment it is back);
  2. every second channel covenant_notify has configured (ntfy, email);
  3. and it says, in its own report, which channels it did NOT have. On this
     PC today (measured 2026-09-21) covenant_notify has no configuration, so
     step 2 is UNDETERMINED until `python covenant_notify.py --setup` is run:
     the PC's only road to him is the phone, and that is the road that is lost.
     This file does not pretend otherwise.

THE PHONE'S SIDE is in the app (covenant-phone NodeService: after 24 hours of
failed check-ins it shows one notification with the steps below). The steps
themselves are in docs/RECONNECT.md, which is public, so a rebuilt PC or a
new phone can read them without either side.
"""
import json
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PHONE_CHECKINS = os.environ.get("COVENANT_PHONE_CHECKINS") or os.path.join(HERE, "ops", "phone_checkins.jsonl")
ASK_LOG = os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
CONTACT_STATE = os.environ.get("COVENANT_CONTACT_STATE") or os.path.join(HERE, "ops", "contact_state.json")
STATE = os.environ.get("COVENANT_RECONNECT_STATE") or os.path.join(HERE, "ops", "reconnect_state.json")
PHONE_SILENT_H = 24.0
HIM_SILENT_H = 24.0
REPEAT_H = 24.0

STEPS = ("To reconnect: (1) on the phone, open Covenant, Settings, and check the PC peer and that Tailscale is up; "
         "(2) on the PC, run python rolling_restart.py and python covenant_reconnect.py --status; "
         "(3) if the PC is gone, a fresh clone of github.com/LAWLESS1987/covenant plus your private/ and ops/ copies "
         "rebuilds it, and the phone finds it by the same Tailscale name; (4) if the phone is gone, install the app "
         "from the covenant-phone release and pair it from the PC's /pc/handshake page. The full page: docs/RECONNECT.md.")


def _parse_t(s):
    s = str(s or "")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            st = time.strptime(s[:24] if fmt.endswith("%z") else s[:20], fmt)
            if fmt.endswith("Z"):
                import calendar
                return float(calendar.timegm(st))
            import datetime
            return datetime.datetime.strptime(s[:24], fmt).timestamp()
        except (ValueError, OverflowError):
            continue
    return None


def _tail(path, n=200):
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 200_000))
            return fh.read().decode("utf-8", "replace").splitlines()[-n:]
    except OSError:
        return []


def _last_phone(path):
    for line in reversed(_tail(path)):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        at = r.get("at")
        if isinstance(at, (int, float)):
            return float(at)
        t = _parse_t(r.get("t"))
        if t:
            return t
    return None


def _last_chat(path):
    for line in reversed(_tail(path)):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") in ("agent", "ask", "council") and r.get("text"):
            t = _parse_t(r.get("t"))
            if t:
                return t
    return None


def _last_contact(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        vals = [float(v) for v in (d.get("seen") or {}).values() if isinstance(v, (int, float))]
        return max(vals) if vals else None
    except (OSError, ValueError, TypeError):
        return None


def _last_git(cwd):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct"], cwd=cwd, capture_output=True, text=True, timeout=20)
        return float(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def signs_of_him(now=None, phone=None, chat=None, contact=None, git_cwd=None):
    """{channel: {'at': epoch or None, 'hours': float or None}} -- a missing record is None, never zero."""
    now = time.time() if now is None else float(now)
    found = {"phone": _last_phone(phone or PHONE_CHECKINS), "chat": _last_chat(chat or ASK_LOG),
             "contact": _last_contact(contact or CONTACT_STATE), "git": _last_git(git_cwd or HERE)}
    return {k: {"at": v, "hours": (round((now - v) / 3600.0, 2) if v is not None else None)} for k, v in found.items()}


def newest(signs):
    """(channel, hours) of the most recent sign, or (None, None)."""
    best = [(v["hours"], k) for k, v in signs.items() if v.get("hours") is not None]
    if not best:
        return None, None
    h, k = min(best)
    return k, h


def _state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_state(d, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, path)


def reconnect(now=None, notify=None, say=print, state_path=None, signs=None, dry_run=False, contact_say=None):
    """One pass. Returns a dict saying what was measured, what was done and what could not be."""
    now = time.time() if now is None else float(now)
    state_path = state_path or STATE
    s = signs or signs_of_him(now)
    ch, him_h = newest(s)
    phone_h = s.get("phone", {}).get("hours")
    out = {"phone_silent_h": phone_h, "him_silent_h": him_h, "him_last_on": ch, "acted": False, "channels": {}, "why": ""}
    if phone_h is None:
        out["why"] = "no phone check-in on record at all: nothing to compare (UNDETERMINED)"
    elif phone_h < PHONE_SILENT_H:
        out["why"] = "the phone checked in %.1f h ago" % phone_h
    elif him_h is not None and him_h < HIM_SILENT_H:
        out["why"] = "the phone is silent (%.1f h) but he was seen on %s %.1f h ago" % (phone_h, ch, him_h)
    else:
        st = _state(state_path)
        last = float(st.get("last_reach") or 0)
        if last and now - last < REPEAT_H * 3600:
            out["why"] = "already reached for him %.1f h ago; next after %d h" % ((now - last) / 3600.0, REPEAT_H)
        else:
            text = ("The PC has not heard from your phone for %d hours and nothing from you on any channel for %s. %s"
                    % (int(phone_h), ("%d hours" % int(him_h)) if him_h is not None else "as long as it has records", STEPS))
            if dry_run:
                out["why"] = "dry run: would reach for him now"
                out["text"] = text
            else:
                try:
                    cs = contact_say
                    if cs is None:
                        import covenant_contact
                        cs = covenant_contact.say
                    row = cs(text, "reconnect: the phone is silent", "reconnect")
                    out["channels"]["direct_line"] = "queued for the phone (%s)" % (row.get("id") if row else "refused")
                except Exception as e:                            # noqa: BLE001
                    out["channels"]["direct_line"] = "could not queue: %s" % type(e).__name__
                try:
                    nf = notify
                    if nf is None:
                        import covenant_notify
                        nf = covenant_notify.notify
                    res = nf("Covenant: the phone has gone quiet", text) or {}
                    if res:
                        for k, v in res.items():
                            out["channels"][k] = "%s (%s)" % ("delivered" if (v[0] if isinstance(v, (list, tuple)) else v) else "no delivery",
                                                                 (v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ""))
                    else:
                        out["channels"]["second"] = "UNDETERMINED: no second channel is configured (python covenant_notify.py --setup)"
                except Exception as e:                            # noqa: BLE001
                    out["channels"]["second"] = "could not notify: %s" % type(e).__name__
                st["last_reach"] = now
                st["reaches"] = int(st.get("reaches") or 0) + 1
                _save_state(st, state_path)
                out["acted"], out["why"] = True, "reached for him"
    say("reconnect: phone %s, him %s (%s) -- %s%s" % (
        ("%.1f h silent" % phone_h) if phone_h is not None else "no record",
        ("%.1f h" % him_h) if him_h is not None else "no record", ch or "-", out["why"],
        ("; " + "; ".join("%s: %s" % kv for kv in out["channels"].items())) if out["channels"] else ""))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="reach for him when the phone goes quiet; say which channels this PC lacks")
    ap.add_argument("--status", action="store_true", help="hours since each sign of him")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.status:
        print(json.dumps(signs_of_him(), indent=1))
        try:
            import covenant_notify
            print("second channels configured:", sorted(k for k in (covenant_notify.load() or {}) if k in ("ntfy_topic", "smtp_host")) or "NONE (python covenant_notify.py --setup)")
        except Exception as e:                                    # noqa: BLE001
            print("second channels: could not read (%s)" % type(e).__name__)
    elif a.run or a.dry_run:
        print(json.dumps(reconnect(dry_run=a.dry_run), indent=1))
    else:
        ap.print_help()
