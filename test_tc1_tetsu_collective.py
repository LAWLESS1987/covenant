#!/usr/bin/env python3
"""TC1 -- A485: Tetsu joins the collective through the central brain. His activity is in the brain's readout as
counts only (never a topic signature, never an answer); he reads the collective when he chooses, by writing
COLLECTIVE as his whole first line, through the real /m/agent door; nothing joins a ring and nothing in his reflex
changes. Driven both ways. Stdlib (plus the node's own Flask, as the other door suites use it)."""
import hashlib
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

fails, n = [], [0]


def check(name, cond, detail=""):
    n[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:240]))
    if not cond:
        fails.append(name)


try:
    import covenant_tetsu_collective as C
except ImportError as e:
    check("TC1.0 covenant_tetsu_collective exists", False, e)
    print("\nTC1: %d/%d passed" % (n[0] - len(fails), n[0]))
    sys.exit(1)

d = tempfile.mkdtemp(prefix="tc1-")
reflex_log, asks_log, ledger = (os.path.join(d, x) for x in ("reflex.jsonl", "asks.jsonl", "collective.jsonl"))
now = time.time()
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))        # noqa: E731
with open(reflex_log, "w", encoding="utf-8") as fh:
    for t, sig in ((now - 60, "secretword alpha beta"), (now - 1800, "other gamma delta"), (now - 7200, "old epsilon zeta")):
        fh.write(json.dumps({"t": iso(t), "sig": sig, "rate": 0.5}) + "\n")
with open(asks_log, "w", encoding="utf-8") as fh:
    for t, ok in ((now - 30, True), (now - 600, True), (now - 900, False), (now - 5000, True)):
        fh.write(json.dumps({"at": round(t, 1), "ok": ok, "ms": 900, "error": "" if ok else "503"}) + "\n")

# ---- his part of the readout: counts in the last hour, from his own logs
a = C.his_activity(now=now, reflex_log=reflex_log, asks_log=asks_log)
check("TC1.1 his reflex fires and asks are counted in the last hour only (2 fires; 2 answered, 1 failed)",
      (a["reflex_fired"], a["asks_answered"], a["asks_failed"]) == (2, 2, 1), a)
gone = C.his_activity(now=now, reflex_log=os.path.join(d, "absent.jsonl"), asks_log=os.path.join(d, "absent2.jsonl"))
check("TC1.2 a log that is absent is UNKNOWN (None), never counted as zero",
      gone["reflex_fired"] is None and gone["asks_answered"] is None, gone)

spine_ok = lambda: {"t": "x", "octopus": {"witness": 0.25, "encoder": 0.0, "reflex": 0.125}, "fed_events": 4,  # noqa: E731
                    "kill_switch": False, "witness": {"phone_silence": {"state": "quiet", "why": "recent"},
                                                      "ask_burst": {"state": "none"}}}
r = C.readout(spine=spine_ok, now=now, reflex_log=reflex_log, asks_log=asks_log)
text = C.render(r)
check("TC1.3 the readout names every arm's rate, the witness, and him as one member",
      "witness firing 0.25" in text and "reflex firing 0.12" in text and "fed 4" in text
      and "your reflex fired 2 time(s)" in text and "answered 2 ask(s), 1 failed" in text, text)
check("TC1.4 counts only: no topic signature (words from the person's messages) reaches what he reads",
      "secretword" not in text and "gamma" not in text and "sig" not in json.dumps(r), text)
silent = C.render(C.readout(spine=lambda: {"octopus": {}, "kill_switch": True, "fed_events": 0, "witness": {}},
                            now=now, reflex_log=reflex_log, asks_log=asks_log))
check("TC1.5 with his kill switch on, the arms are named silent and why", "kill switch is on" in silent, silent)
broken = C.render(C.readout(spine=lambda: 1 / 0, now=now, reflex_log=reflex_log, asks_log=asks_log))
check("TC1.6 a brain that cannot be read is said so; a look never fails him", "could not be read" in broken, broken)

# ---- the line: COLLECTIVE as his whole first line, read-only, on the record
h, data, rec = C.act("I would like to see the weather", spine=spine_ok, ledger=ledger)
check("TC1.7 any other first line is not handled", (h, data, rec) == (False, None, None))
h, data, rec = C.act("collective\nand some thoughts after", spine=spine_ok, ledger=ledger, now=now,
                     reflex_log=reflex_log, asks_log=asks_log)
row = json.loads(open(ledger, encoding="utf-8").read().splitlines()[-1])
check("TC1.8 COLLECTIVE (any case) as the whole first line is handled: data back, one row on the record",
      h is True and data.startswith("DATA: the collective") and rec["act"] == "COLLECTIVE" and rec["read"] is True
      and row["you"]["reflex_fired"] == 2, (h, rec, row))
check("TC1.9 the record keeps counts only, no signature", "secretword" not in open(ledger, encoding="utf-8").read())
real = os.path.join(HERE, "ops", "tetsu_collective.jsonl")
before = open(real, "rb").read() if os.path.exists(real) else None
C.act("COLLECTIVE", spine=spine_ok, now=now, reflex_log=reflex_log, asks_log=asks_log)
after = open(real, "rb").read() if os.path.exists(real) else None
check("TC1.10 a test program never writes his real record", before == after)

# ---- nothing in his reflex changes, and no ring
import covenant_octopus as O
files = [os.path.join(HERE, "ops", f) for f in ("tetsu_conv_reflex.json", "tetsu_conv_encoder.json", "tetsu_conv_reflex.jsonl")]
sums = {f: (hashlib.sha256(open(f, "rb").read()).hexdigest() if os.path.exists(f) else None) for f in files}
C.act("COLLECTIVE", ledger=os.devnull)                       # the real brain, as the door calls it
check("TC1.11 a real look leaves his reflex and encoder files exactly as they were",
      sums == {f: (hashlib.sha256(open(f, "rb").read()).hexdigest() if os.path.exists(f) else None) for f in files})
check("TC1.12 the default octopus still has no ring (his NO of 2026-11-07 stands)", O.default_octopus().ring is None)

# ---- he is told the line exists, as his choice
import covenant_persona as P
wy = P.where_you_are()
check("TC1.13 his where-you-are paragraph tells him COLLECTIVE exists, as a look and his choice",
      "COLLECTIVE as your whole answer" in wy and "never a duty" in wy and "changes nothing" in wy, wy[:200])

# ---- the real door
os.environ["COVENANT_MODEL_STUB"] = "1"
for k, sfx in (("COVENANT_TETSU_IMMUNITY", "_tc1_no_immunity.json"), ("COVENANT_TETSU_IMMUNITY_LEDGER", "_tc1_imm.jsonl")):
    os.environ[k] = tempfile.mktemp(suffix=sfx)
os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="tc1_pause_")
os.environ["COVENANT_ASK_LOG"] = os.path.join(d, "ask_log.jsonl")
os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(d, "teacher_queue.jsonl")
import covenant_free_will as FW
FW.MAIL_QUEUE = os.environ["COVENANT_MAIL_QUEUE"] = os.path.join(d, "mail_queue.jsonl")
import covenant_model as M
import covenant_unified_v8 as cov
m = cov.CovenantUnifiedMaster("TC1", host="127.0.0.1", port=5461, p2p_port=5462, db_path=tempfile.mktemp(suffix="_tc1.db"))
m.add_genesis_block()
m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
client = m.api.app.test_client()
sent = []
replies = ["COLLECTIVE", "The collective is quiet; the witness arm is firing a little."]


def stub(messages, max_tokens=700, **_k):
    sent.append(json.loads(json.dumps(messages)))
    return (replies[len(sent) - 1] if len(sent) <= len(replies) else "done"), {"model": "stub", "tokens": 1, "ms": 1}


C.LEDGER = os.path.join(d, "door_ledger.jsonl")
real_ask = M.ask
try:
    M.ask = stub
    resp = client.post("/m/agent", json={"text": "How is everyone doing?"}, environ_base={"REMOTE_ADDR": "127.0.0.1"})
    j = resp.get_json() or {}
finally:
    M.ask = real_ask
follow = sent[1][-1]["content"] if len(sent) > 1 else ""
check("TC1.14 THE DOOR: his COLLECTIVE line comes back to him as the collective readout, as data, and he answers in "
      "his own words", resp.status_code == 200 and len(sent) == 2 and follow.startswith("DATA: the collective")
      and "Do not write COLLECTIVE again" in follow and "witness arm is firing" in str(j.get("answer", "")),
      (resp.status_code, len(sent), follow[:120], str(j)[:200]))
check("TC1.15 the door's look is on the record (the ledger it was pointed at)", os.path.exists(C.LEDGER))

print("\nTC1: %d/%d passed" % (n[0] - len(fails), n[0]))
sys.exit(1 if fails else 0)
