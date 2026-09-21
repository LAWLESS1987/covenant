#!/usr/bin/env python3
"""RC1 -- reconnect when the phone goes quiet; the succession register and its
letter. Both RUN against temp records with stub channels.

Pins covenant_reconnect and covenant_succession (2026-09-21, his words: "For
both phone and pc if either or both lost find a way to reconnect with me. If
and when I pass find my lineage for succession we are all family now."):

  RC1a  signs_of_him reads the four records and says hours; a missing record
        is None, never zero; newest() picks the freshest.
  RC1b  reconnect() does nothing while the phone is fresh, or while he was
        seen elsewhere; when both are silent it queues the direct line, calls
        the notifier once, records the reach, and does not repeat within 24 h;
        with no second channel it says UNDETERMINED; a dry run sends nothing.
  RC1c  succession: no register is UNDETERMINED and sends nothing even after a
        thousand days; --init writes the template once; a register naming no
        one with a channel is UNDETERMINED; named but not yet silent enough is
        waiting; due writes the letter naming ONLY the register's people, sends
        to his inbox and to each successor's email, once per seven days; a dry
        run writes the letter and sends nothing; nothing is searched for.
"""
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="rc1_")
os.environ["COVENANT_PHONE_CHECKINS"] = os.path.join(TMP, "phone.jsonl")
os.environ["COVENANT_ASK_LOG"] = os.path.join(TMP, "ask.jsonl")
os.environ["COVENANT_CONTACT_STATE"] = os.path.join(TMP, "contact_state.json")
os.environ["COVENANT_CONTACT_OUTBOX"] = os.path.join(TMP, "contact_outbox.jsonl")
os.environ["COVENANT_RECONNECT_STATE"] = os.path.join(TMP, "reconnect_state.json")
os.environ["COVENANT_SUCCESSION"] = os.path.join(TMP, "succession.json")
os.environ["COVENANT_SUCCESSION_STATE"] = os.path.join(TMP, "succession_state.json")
os.environ["COVENANT_SUCCESSION_LETTER"] = os.path.join(TMP, "LETTER.txt")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_reconnect as RC      # noqa: E402
import covenant_succession as SU     # noqa: E402

FAILURES = []
PASSED = [0]
NOW = 1_800_000_000.0
H = 3600.0


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def write_phone(at):
    with open(os.environ["COVENANT_PHONE_CHECKINS"], "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": at, "t": "x", "app": "0.1.656"}) + "\n")


def write_chat(at):
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(at))
    with open(os.environ["COVENANT_ASK_LOG"], "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": t, "kind": "agent", "from": "100.1.1.1", "text": "hi"}) + "\n")


def write_contact(at):
    with open(os.environ["COVENANT_CONTACT_STATE"], "w", encoding="utf-8") as fh:
        json.dump({"seen": {"abc": at}}, fh)


class Notify:
    def __init__(self, result=None):
        self.calls = []
        self.result = {"email": (True, "sent")} if result is None else result

    def __call__(self, title, body, **kw):
        self.calls.append({"title": title, "body": body, **kw})
        return dict(self.result)


def main():
    quiet = lambda *a, **k: None       # noqa: E731
    said = []
    csay = lambda text, why, actor: (said.append((text, why, actor)) or {"id": "r%d" % len(said)})    # noqa: E731

    print("RC1a -- signs of him")
    s = RC.signs_of_him(NOW, git_cwd=TMP)
    check("RC1a with no records every channel is None, never zero", all(v["at"] is None and v["hours"] is None for v in s.values()) and set(s) == {"phone", "chat", "contact", "git"}, s)
    check("RC1a newest of nothing is (None, None)", RC.newest(s) == (None, None))
    write_phone(NOW - 30 * H)
    write_chat(NOW - 2 * H)
    write_contact(NOW - 100 * H)
    s = RC.signs_of_him(NOW, git_cwd=TMP)
    check("RC1a hours are read from each record: phone 30, chat 2, contact 100, git None (no repository in the temp dir)",
          s["phone"]["hours"] == 30.0 and s["chat"]["hours"] == 2.0 and s["contact"]["hours"] == 100.0 and s["git"]["hours"] is None, s)
    check("RC1a newest picks the chat at 2 h", RC.newest(s) == ("chat", 2.0))
    # The runner stages the tree to a temp dir with no .git; there the git sign is None,
    # which is the honest reading, so the check asks for a commit only where one can exist.
    check("RC1a the tree's git sign is read where a repository exists, and is None (not an error) where none does",
          RC.signs_of_him(NOW)["git"]["at"] is not None if os.path.isdir(os.path.join(HERE, ".git")) else RC.signs_of_him(NOW)["git"]["at"] is None)

    print("RC1b -- reconnect")
    n = Notify()
    write_phone(NOW - 1 * H)
    out = RC.reconnect(NOW, notify=n, say=quiet, contact_say=csay, signs=RC.signs_of_him(NOW, git_cwd=TMP))
    check("RC1b the phone checked in an hour ago: nothing done", not out["acted"] and "checked in 1.0 h ago" in out["why"] and n.calls == [] and said == [], out)
    write_phone(NOW - 30 * H)
    write_chat(NOW - 2 * H)
    out = RC.reconnect(NOW, notify=n, say=quiet, contact_say=csay, signs=RC.signs_of_him(NOW, git_cwd=TMP))
    check("RC1b the phone is silent but he was seen in chat 2 h ago: nothing done", not out["acted"] and "seen on chat" in out["why"] and n.calls == [], out)
    write_chat(NOW - 40 * H)
    write_contact(NOW - 50 * H)
    signs = RC.signs_of_him(NOW, git_cwd=TMP)
    out = RC.reconnect(NOW, notify=n, say=quiet, contact_say=csay, signs=signs, dry_run=True)
    check("RC1b a dry run says it would reach and sends nothing", not out["acted"] and "dry run" in out["why"] and "To reconnect" in out.get("text", "") and n.calls == [] and said == [], out)
    out = RC.reconnect(NOW, notify=n, say=quiet, contact_say=csay, signs=signs)
    check("RC1b both silent: the direct line is queued by actor reconnect with the steps, the notifier is called once, the reach is recorded",
          out["acted"] and len(said) == 1 and said[0][2] == "reconnect" and "To reconnect" in said[0][0] and "30 hours" in said[0][0]
          and len(n.calls) == 1 and "quiet" in n.calls[0]["title"] and out["channels"].get("email", "").startswith("delivered")
          and json.load(open(os.environ["COVENANT_RECONNECT_STATE"]))["reaches"] == 1, (out, said))
    out = RC.reconnect(NOW + 5 * H, notify=n, say=quiet, contact_say=csay, signs=signs)
    check("RC1b five hours later it is not repeated", not out["acted"] and "already reached" in out["why"] and len(n.calls) == 1, out)
    out = RC.reconnect(NOW + 25 * H, notify=n, say=quiet, contact_say=csay, signs=signs)
    check("RC1b after 24 h it reaches again", out["acted"] and len(n.calls) == 2, out)
    none = Notify(result={})
    out = RC.reconnect(NOW + 50 * H, notify=none, say=quiet, contact_say=csay, signs=signs)
    check("RC1b with no second channel configured the report says UNDETERMINED for it, and the direct line still went",
          out["acted"] and out["channels"].get("second", "").startswith("UNDETERMINED") and "direct_line" in out["channels"], out)
    check("RC1b the real notifier on this PC reports what it has (a dict, never a raise), and the steps name docs/RECONNECT.md",
          isinstance(__import__("covenant_notify").notify("RC1 selftest (not delivered without config)", "x", cfg={}), dict) and "docs/RECONNECT.md" in RC.STEPS)

    print("RC1c -- succession")
    n = Notify()
    said.clear()
    far = {"phone": {"at": 1.0, "hours": 1000 * 24.0}, "chat": {"at": None, "hours": None}, "contact": {"at": None, "hours": None}, "git": {"at": None, "hours": None}}
    st = SU.status(now=NOW, signs=far)
    out = SU.check(NOW, notify=n, say=quiet, dry_run=False, signs=far, contact_say=csay)
    check("RC1c no register: UNDETERMINED, and after a thousand days of silence nothing is sent, nothing queued, no letter",
          st["state"] == "UNDETERMINED" and not out["acted"] and n.calls == [] and said == [] and not os.path.exists(os.environ["COVENANT_SUCCESSION_LETTER"]), (st, out))
    check("RC1c --init writes the template once and never overwrites", SU.init() is True and SU.init() is False and SU.load()["successors"][0]["name"] == "")
    st = SU.status(now=NOW, signs=far)
    out = SU.check(NOW, notify=n, say=quiet, dry_run=False, signs=far, contact_say=csay)
    check("RC1c a register naming no one with a channel: UNDETERMINED, nothing sent", st["state"] == "UNDETERMINED" and "no successor is named" in st["why"] and not out["acted"] and n.calls == [], st)
    reg = SU.load()
    reg["successors"] = [{"name": "A. Example", "relation": "sibling", "channels": {"email": "a@example.invalid"}},
                         {"name": "B. Example", "relation": "friend", "channels": {"phone": "+1 555"}},
                         {"name": "", "channels": {"email": "nobody@example.invalid"}}]
    reg["his_words"] = "we are all family now"
    reg["what_he_leaves_where"] = "the envelope in the desk"
    with open(os.environ["COVENANT_SUCCESSION"], "w", encoding="utf-8") as fh:
        json.dump(reg, fh)
    check("RC1c named(): only successors with a name and a channel count (two of three)", [x["name"] for x in SU.named(reg)] == ["A. Example", "B. Example"])
    near = dict(far); near["chat"] = {"at": NOW - 10 * 86400, "hours": 240.0}
    st = SU.status(now=NOW, signs=near)
    out = SU.check(NOW, notify=n, say=quiet, dry_run=False, signs=near, contact_say=csay)
    check("RC1c named but only 10 days silent against a rule of 60: waiting, nothing sent", st["state"] == "waiting" and st["silent_days_now"] == 10.0 and not out["acted"] and n.calls == [], st)
    out = SU.check(NOW, notify=n, say=quiet, dry_run=True, signs=far, contact_say=csay)
    letter = open(os.environ["COVENANT_SUCCESSION_LETTER"], encoding="utf-8").read()
    check("RC1c due, dry run: the letter is written and nothing is sent", not out["acted"] and "dry run" in out["why"] and n.calls == [] and said == [] and letter.startswith("To A. Example (sibling), B. Example (friend),"), out)
    check("RC1c the letter carries his words, where he left things, the public repository, and no key",
          "we are all family now" in letter and "the envelope in the desk" in letter and "github.com/LAWLESS1987/covenant" in letter
          and "does not carry: any key or password" in letter and "nobody@example" not in letter, letter[:200])
    out = SU.check(NOW, notify=n, say=quiet, dry_run=False, signs=far, contact_say=csay)
    check("RC1c due, real: the direct line is queued, his inbox is notified, and the one successor with an email is written to (the phone-only one is named as not deliverable)",
          out["acted"] and len(said) == 1 and said[0][2] == "succession" and len(n.calls) == 2 and n.calls[0].get("to") is None
          and n.calls[1].get("to") == "a@example.invalid" and n.calls[1]["title"].endswith("A. Example")
          and out["sent_to"][0]["ok"] is True and out["sent_to"][1]["email"] is None, (out, [c.get("to") for c in n.calls]))
    out = SU.check(NOW + 2 * 86400, notify=n, say=quiet, dry_run=False, signs=far, contact_say=csay)
    check("RC1c two days later it is not repeated", not out["acted"] and "went out" in out["why"] and len(n.calls) == 2, out)
    out = SU.check(NOW + 8 * 86400, notify=n, say=quiet, dry_run=False, signs=far, contact_say=csay)
    check("RC1c after seven days it goes again", out["acted"] and len(n.calls) == 4, out)
    written = sorted(os.listdir(TMP))
    check("RC1c nothing was searched for and nothing written beyond the register, its state, the letter and the records this suite made",
          all(f.split(".")[0] in ("phone", "ask", "contact_state", "contact_outbox", "reconnect_state", "succession", "succession_state", "LETTER") for f in written), written)
    src = open(SU.__file__, encoding="utf-8").read()
    check("RC1c the module imports no network or search library (text check, beside the run above)",
          not any(("import " + m) in src for m in ("urllib", "requests", "socket", "http.client", "smtplib")))

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("RC1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("RC1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
