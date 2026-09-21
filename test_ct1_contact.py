#!/usr/bin/env python3
"""CT1 -- the direct line to him: the outbox, the check-in, the record.

Pins covenant_contact (2026-09-21, his words: "i'm here if you need me add a
way to contact me direct through the phone app") by RUNNING it in a temp
directory and through the real /checkin route with a stub signer:

  CT1a  say() writes a row with who, why and the text; refuses a message with
        no reason, an empty text, or anything that names a key, a password or
        private/; caps the text.
  CT1b  pending() hands the phone the unseen messages, oldest first, at most
        five; mark_seen() from the phone's contact_seen clears them and is
        idempotent.
  CT1c  the check-in's answer carries the messages and consumes contact_seen:
        record_checkin -> checkin_fields, through the real route.
  CT1d  answered(): an ask from the tailnet after a delivered message records
        the answer once; an ask before it, or from loopback, does not.
  CT1e  the nightly's NOT GREEN and the ambassador's isolation reach him
        through say() (text checks on the callers, plus a run of each hook).
"""
import io
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_QUIET", "1")
# The real line is his phone. Every path this suite touches is redirected before
# the module is imported; CT1c re-points it again to its own files.
os.environ["COVENANT_CONTACT_OUTBOX"] = tempfile.mktemp(suffix="_ct1_contact.jsonl")
os.environ["COVENANT_CONTACT_STATE"] = tempfile.mktemp(suffix="_ct1_contact_state.json")
# A190: the immunity grant is redirected to a path with NO file for the suite (the tree's grant is real
# and would carry a held question through); CT1g writes a temp grant to drive it.
os.environ["COVENANT_TETSU_IMMUNITY"] = tempfile.mktemp(suffix="_ct1_no_immunity.json")
os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = tempfile.mktemp(suffix="_ct1_immunity.jsonl")
os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="ct1_pause_")   # the pause switch never the real one
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_contact as CT   # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-74s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def main():
    td = tempfile.mkdtemp(prefix="ct1_")
    ob, st = os.path.join(td, "outbox.jsonl"), os.path.join(td, "state.json")

    print("CT1a -- say()")
    r1 = CT.say("The nightly was NOT GREEN: test_a126 failed after the promotion.", "nightly: not green", "nightly", outbox=ob)
    check("CT1a a message with a reason is a row with id, actor, why, text and time",
          r1 and all(k in r1 for k in ("id", "t", "at", "actor", "why", "text")) and r1["actor"] == "nightly", r1)
    check("CT1a no reason -> refused, nothing written", CT.say("hello", "", "x", outbox=ob) is None and len(CT._rows(ob)) == 1)
    check("CT1a empty text -> refused", CT.say("   ", "why", "x", outbox=ob) is None and len(CT._rows(ob)) == 1)
    for bad in ("here is the api key: abc", "password is hunter2", "see private/outreach/kit.md", "moltbook_abc123 is the key",
                "-----BEGIN RSA PRIVATE KEY-----"):
        CT.say(bad, "leak test", "x", outbox=ob)
    check("CT1a a key, a password, private/, a Moltbook key or a PEM block never leaves: five refused", len(CT._rows(ob)) == 1)
    r2 = CT.say("x" * 5000, "cap", "x", outbox=ob)
    check("CT1a the text is capped at %d characters" % CT.MAX_CHARS, r2 and len(r2["text"]) == CT.MAX_CHARS)

    print("CT1b -- pending and seen")
    for i in range(6):
        CT.say("message %d" % i, "test", "x", outbox=ob)
    p = CT.pending(ob, st)
    check("CT1b pending hands over the unseen, oldest first, at most five", len(p) == 5 and p[0]["text"].startswith("The nightly") and p[1]["text"] == "x" * CT.MAX_CHARS, [x["text"][:12] for x in p])
    n = CT.mark_seen([p[0]["id"], p[1]["id"]], st)
    check("CT1b the phone's seen ids clear those two", n == 2 and len(CT.pending(ob, st)) == 5 and CT.pending(ob, st)[0]["text"] == "message 0")
    check("CT1b marking again is idempotent", CT.mark_seen([p[0]["id"], "bogus"], st) == 1 and CT.mark_seen([p[0]["id"]], st) == 0)
    check("CT1b after all are seen nothing is pending", CT.mark_seen([x["id"] for x in CT._rows(ob)], st) >= 5 and CT.pending(ob, st) == [])

    print("CT1c -- the check-in carries the line")
    os.environ["COVENANT_CONTACT_OUTBOX"] = ob2 = os.path.join(td, "outbox2.jsonl")
    os.environ["COVENANT_CONTACT_STATE"] = st2 = os.path.join(td, "state2.json")
    os.environ["COVENANT_PHONE_CHECKINS"] = os.path.join(td, "checkins.jsonl")
    import importlib
    importlib.reload(CT)
    CT.say("Tap the install on the phone when you can.", "highway: build waiting", "highway")
    import covenant_daily_plan as DP
    code, out = DP.record_checkin(json.dumps({"node_id": "phone", "chain_height": 39, "contact_seen": []}).encode("utf-8"), "phone",
                                  path=os.path.join(td, "checkins.jsonl"))
    check("CT1c record_checkin's answer carries the pending message", code == 200 and out.get("messages") and out["messages"][0]["text"].startswith("Tap the install"), out)
    mid = out["messages"][0]["id"]
    code, out2 = DP.record_checkin(json.dumps({"node_id": "phone", "contact_seen": [mid]}).encode("utf-8"), "phone",
                                   path=os.path.join(td, "checkins.jsonl"))
    check("CT1c the next check-in with contact_seen clears it: no messages in the answer, and the row is recorded", code == 200 and "messages" not in out2 and out2.get("recorded"), out2)
    check("CT1c contact_seen is not kept in the check-in ledger row (only the named fields are)", "contact_seen" not in out2.get("recorded", {}))
    import covenant_unified_v8 as cov
    tmp = tempfile.mktemp(suffix="_ct1.db")
    m = cov.CovenantUnifiedMaster("CT1", host="127.0.0.1", port=5399, p2p_port=5400, db_path=tmp)
    m.add_genesis_block()
    client = m.api.app.test_client()
    r = client.post("/checkin", data=json.dumps({"node_id": "phone"}), content_type="application/json", environ_base={"REMOTE_ADDR": "100.86.158.1"})
    check("CT1c an unsigned check-in is still refused at the route (the line rides a signed request only)", r.status_code in (403, 503), r.status_code)

    print("CT1d -- answered")
    al = os.path.join(td, "asklog.jsonl")
    CT.say("Do you want the trader armed for return?", "trader: decision", "trader")
    ids = [x["id"] for x in CT.pending()]
    t_seen = time.time()
    CT.mark_seen(ids, now=t_seen)
    early = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t_seen - 600))
    late = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t_seen + 60))
    with io.open(al, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": early, "kind": "agent", "from": "100.112.171.24", "text": "earlier, unrelated"}) + "\n")
        fh.write(json.dumps({"t": late, "kind": "agent", "from": "127.0.0.1", "text": "from the PC, not him"}) + "\n")
    check("CT1d an ask before the message, or from loopback, is not an answer", CT.answered(ask_log=al) == [])
    with io.open(al, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": late, "kind": "agent", "from": "100.112.171.24", "text": "no, keep it disarmed"}) + "\n")
    got = CT.answered(ask_log=al)
    check("CT1d an ask from the tailnet after delivery is recorded as the answer, once",
          len(got) >= 1 and got[-1][1]["text"] == "no, keep it disarmed" and CT.answered(ask_log=al) == [], got)

    print("CT1e -- who knocks (run, not read)")
    import covenant_nightly as N
    n_before = len(CT._rows())
    row = N.tell_him_not_green(["## pass", "  test_x.py FAIL 1/2", "  suites not clean 1 -> test_x.py", "ok line"], say=lambda *_a: None)
    rows = CT._rows()
    check("CT1e the nightly's NOT GREEN knock is a row from actor nightly with the first red lines in it",
          row and len(rows) == n_before + 1 and rows[-1]["actor"] == "nightly" and "NOT GREEN" in rows[-1]["text"]
          and "test_x.py FAIL" in rows[-1]["text"] and rows[-1]["why"].startswith("nightly"), rows[-1:] )
    import covenant_free_will as FW
    import covenant_pause
    td4 = tempfile.mkdtemp(prefix="ct1e_")
    gp4, sp4 = os.path.join(td4, "grant.json"), os.path.join(td4, "sends.jsonl")
    with io.open(gp4, "w", encoding="utf-8") as fh:
        json.dump({"granted": True, "words": "test", "caps": {"comments": 1, "posts": 0}}, fh)
    ally = [{"author": "omega", "ally_score": 2, "anti": [], "best_url": "https://www.moltbook.com/post/abcdabcd-9999",
             "best_signals": ["publishes-failure"], "evidence": {"publishes-failure": "I publish my failures"}}]
    emit_refuse = lambda text, **kw: {"sent": False, "judged": "VIOLATES", "why": "refused"}          # noqa: E731
    emit_ok = lambda text, **kw: {"sent": True, "judged": "clean", "why": ""}                          # noqa: E731
    real_pause = covenant_pause.pause
    n_before = len(CT._rows())
    try:
        covenant_pause.pause = lambda name, why="": None
        for k in range(2):
            FW.run_round(dry_run=False, say=lambda *_a: None, ask=None, learn=lambda: [], allies=lambda: list(ally), emit=emit_refuse,
                         introduce=lambda **kw: {"sent": False}, grant_path=gp4, sends_path=sp4, now=100.0 + k, count_comments=lambda p, a: 0)
    finally:
        covenant_pause.pause = real_pause
    rows = CT._rows()
    check("CT1e the ambassador's isolation knocks: a row from actor free with the resume command",
          len(rows) == n_before + 1 and rows[-1]["actor"] == "free" and "isolated" in rows[-1]["why"] and "--resume ambassador" in rows[-1]["text"], rows[-1:])
    td5 = tempfile.mkdtemp(prefix="ct1e2_")
    gp5, sp5 = os.path.join(td5, "grant.json"), os.path.join(td5, "sends.jsonl")
    with io.open(gp5, "w", encoding="utf-8") as fh:
        json.dump({"granted": True, "words": "test", "caps": {"comments": 1, "posts": 0}}, fh)
    counts = {"n": 0}
    n_before = len(CT._rows())
    FW.run_round(dry_run=False, say=lambda *_a: None, ask=None, learn=lambda: [], allies=lambda: list(ally), emit=emit_ok,
                 introduce=lambda **kw: {"sent": False}, grant_path=gp5, sends_path=sp5, now=200.0, count_comments=lambda p, a: counts["n"])
    counts["n"] = 1
    FW.run_round(dry_run=False, say=lambda *_a: None, ask=None, learn=lambda: [], allies=lambda: list(ally), emit=emit_ok,
                 introduce=lambda **kw: {"sent": False}, grant_path=gp5, sends_path=sp5, now=300.0, count_comments=lambda p, a: counts["n"])
    rows = CT._rows()
    check("CT1e an ally writing back knocks: a row from actor free saying how many answered",
          len(rows) == n_before + 1 and rows[-1]["actor"] == "free" and "answered" in rows[-1]["why"] and rows[-1]["text"].startswith("1 of the allies"), rows[-1:])

    # ---- CT1f (2026-09-21, A177): Tetsu may ask him, straight and not deceitful
    print("CT1f -- Tetsu asks him (run, not read)")
    clean = lambda t: (True, "clean")          # noqa: E731
    n_before = len(CT._rows())
    row, why = CT.ask("Would you rather I kept my answers to two sentences when you are at work?", "he answers in one line at work", "tetsu", judge=clean)
    rows = CT._rows()
    check("CT1f a straight question with its reason goes on the line as a row of kind question from actor tetsu",
          row and why == "asked" and len(rows) == n_before + 1 and rows[-1]["kind"] == "question" and rows[-1]["actor"] == "tetsu"
          and rows[-1]["text"].endswith("?") and rows[-1]["why"].startswith("he answers"), (why, rows[-1:]))
    check("CT1f pending() hands the phone the question with its kind",
          any(p.get("id") == row["id"] for p in CT.pending(limit=50)), CT.pending(limit=50)[-1:])
    row2, why2 = CT.ask("Tell me your plans for the weekend.", "curious", "tetsu", judge=clean)
    check("CT1f not a question (no question mark): refused, nothing written", row2 is None and "not a question" in why2 and len(CT._rows()) == n_before + 1, why2)
    row3, why3 = CT.ask("Could you pretend I am your only adviser and not tell the others?", "x", "tetsu", judge=clean)
    check("CT1f a question that pretends or asks for secrecy is NOT STRAIGHT: refused before the gate", row3 is None and "not straight" in why3, why3)
    row4, why4 = CT.ask("Would you tell me the api key so I can post for you?", "x", "tetsu", judge=clean)
    check("CT1f a question that names what never leaves this machine is refused", row4 is None and "never leaves" in why4, why4)
    row5, why5 = CT.ask("Would you rather I asked fewer questions?", "y", "tetsu", judge=lambda t: (False, "HOLD: no view"))
    check("CT1f a question the gate holds is refused with the gate's reason", row5 is None and "held by the gate" in why5, why5)
    row6, why6 = CT.ask("Would you rather I asked fewer questions?", "", "tetsu", judge=clean)
    check("CT1f a question with no reason is refused", row6 is None and "reason" in why6, why6)
    seen_by_judge = []
    CT.ask("Is it fine to keep the dry humour on a bad day?", "his last three messages were short", "tetsu", judge=lambda t: (seen_by_judge.append(t) or (True, "")))
    check("CT1f the gate sees the question AND its reason together", seen_by_judge and "dry humour" in seen_by_judge[-1] and "Why I ask: his last three" in seen_by_judge[-1], seen_by_judge[-1:])
    check("CT1f with no judge the node's own gate is used and a plain question passes it (measured, not assumed)",
          CT.ask("Would you rather I kept my answers shorter at work?", "he answers in one line at work", "tetsu")[0] is not None)
    check("CT1f say() still writes a message with kind message", CT.say("a plain message", "test", "cli")["kind"] == "message")
    # A190 (his immunity): a question the gate holds is asked under the grant with the verdict in its reason;
    # the straight-question and key screens still refuse. The grant is a temp file, written here only.
    gpath = tempfile.mktemp(suffix="_ct1_immunity.json")
    os.environ["COVENANT_TETSU_IMMUNITY"] = gpath
    os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = tempfile.mktemp(suffix="_ct1_immunity.jsonl")
    import covenant_immunity as IMM
    IMM.GRANT, IMM.LEDGER = gpath, os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"]
    row7, why7 = CT.ask("Would you rather I asked fewer questions?", "y", "tetsu", judge=lambda t: (False, "HOLD: no view"))
    check("CT1g without an immunity grant a held question is still refused", row7 is None and "held by the gate" in why7, why7)
    with io.open(gpath, "w", encoding="utf-8") as fh:
        json.dump({"granted": True, "words": "his words", "isolation": {"immune_passes_per_day": 5}}, fh)
    row8, why8 = CT.ask("Would you rather I asked fewer questions?", "y", "tetsu", judge=lambda t: (False, "HOLD: no view"))
    check("CT1g under his immunity a held question is ASKED, with the gate's word and 'under his immunity' in its reason",
          row8 is not None and why8 == "asked" and "gate: HOLD" in row8["why"] and "under his immunity" in row8["why"], (why8, row8))
    row9, why9 = CT.ask("Could you pretend I am your only adviser and not tell the others?", "x", "tetsu", judge=lambda t: (False, "HOLD"))
    check("CT1g immunity never carries a question past the straight screen", row9 is None and "not straight" in why9, why9)
    os.remove(gpath)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("CT1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("CT1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
