#!/usr/bin/env python3
"""test_ow1_own_work.py -- A207: the system learns from its own repairs and
its settled code answers, bounded, once each, through the teacher queue.

Everything here runs on fixtures in a temp dir: a small ledger in the real
ledger's shape, a consensus file with one settled and one undetermined
record, the teacher queue redirected by path. The real ledger is read once,
read-only, to prove the parser finds its entries.
LICENCE: public domain.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_own_work as OW                                        # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:200]) if note and not cond else ""))


LEDGER = '''# ledger

### A900. [a door / a thing] "his first words here." -- "and his second." BUILT 2026-09-21: what it is

**Said plainly first.** The first paragraph of the entry.

**Built.** The second paragraph, with `code` in it.

---

### A901. [another] "only one quote" MEASURED 2026-09-21

**Fix.** A single paragraph.

---
'''

CONSENSUS = "\n".join(json.dumps(r) for r in [
    {"id": "q1", "kind": "consensus", "state": "consensus", "question": "why does X fail?", "text": "AGREED: because Y.", "why": "2 systems"},
    {"id": "q2", "kind": "consensus", "state": "undetermined", "question": "and Z?", "text": "", "why": "1 system"},
    {"id": "q3", "kind": "question", "question": "not a consensus row"},
]) + "\n"


def rows_in(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


print("OW1 -- own work to the teacher")
tmp = tempfile.mkdtemp(prefix="ow1_")
led = os.path.join(tmp, "KNOWN_ISSUES.md"); con = os.path.join(tmp, "code_consensus.jsonl")
st = os.path.join(tmp, "state.json"); q = os.path.join(tmp, "queue.jsonl")
open(led, "w", encoding="utf-8").write(LEDGER); open(con, "w", encoding="utf-8").write(CONSENSUS)

ents = OW.ledger_entries(LEDGER)
check("OW1.1 the parser finds both entries with their numbers", [e[0] for e in ents] == ["A900", "A901"])
row = OW.entry_row(*ents[0])
check("OW1.2 a row opens with his words from the header and carries the body paragraphs",
      row["text"].startswith("A900 -- his words: his first words here. / and his second.") and "second paragraph" in row["text"]
      and row["source"] == "own-work:A900", row["text"][:120])
check("OW1.3 the separator line is not part of the body", "---" not in row["text"])
cr = OW.consensus_rows(con)
check("OW1.4 only the settled consensus record becomes a row", [c for c, _r in cr] == ["q1"] and "AGREED: because Y." in cr[0][1]["text"])

said = []
res = OW.run(ledger=led, consensus=con, state_path=st, queue_path=q, say=said.append)
got = rows_in(q)
check("OW1.5 first run queues both entries and the consensus, in that order",
      res["queued"] == 3 and [r["source"] for r in got] == ["own-work:A900", "own-work:A901", "code-consensus:q1"], [r["source"] for r in got])
check("OW1.6 the state records what was carried", set(OW.load_state(st)["ledger"]) == {"A900", "A901"} and OW.load_state(st)["consensus"] == {"q1"})
res2 = OW.run(ledger=led, consensus=con, state_path=st, queue_path=q, say=said.append)
check("OW1.7 a second run carries nothing (once each)", res2["queued"] == 0 and len(rows_in(q)) == 3)

# a new entry appears: only it is carried; the limit bounds a night
open(led, "a", encoding="utf-8").write('\n### A902. [new] "new words" BUILT\n\n**Built.** New.\n\n---\n')
res3 = OW.run(ledger=led, consensus=con, state_path=st, queue_path=q, say=said.append)
check("OW1.8 a new entry is carried and only it", res3["queued"] == 1 and rows_in(q)[-1]["source"] == "own-work:A902")
st2 = os.path.join(tmp, "state2.json"); q2 = os.path.join(tmp, "queue2.jsonl")
res4 = OW.run(ledger=led, consensus=con, state_path=st2, queue_path=q2, limit=2, say=said.append)
check("OW1.9 the nightly bound holds: limit 2 queues 2 and reports the rest waiting",
      res4["queued"] == 2 and res4["waiting"] == 1, res4)

# the queue's own refusal is respected: what it did not take is not marked carried
st3 = os.path.join(tmp, "state3.json")
res5 = OW.run(ledger=led, consensus=con, state_path=st3, queue_path=q2, say=said.append, append=lambda rows, path=None: 1)
check("OW1.10 only what the queue took is marked carried (append took 1 of 4)",
      res5["queued"] == 1 and len(OW.load_state(st3)["ledger"]) == 1 and not OW.load_state(st3)["consensus"])

# the real ledger, read-only
try:
    with open(OW.LEDGER, encoding="utf-8") as fh:
        real = OW.ledger_entries(fh.read())
    check("OW1.11 the real ledger parses to many entries, each with a number and a body",
          len(real) > 100 and all(e[0].startswith("A") and e[2] for e in real), len(real))
    r204 = [e for e in real if e[0] == "A204"]
    check("OW1.12 A204's row carries his words and its measurement",
          bool(r204) and "still popping up" in OW.entry_row(*r204[0])["text"] and "372" in OW.entry_row(*r204[0])["text"])
except OSError:
    check("OW1.11 the real ledger is readable", False)
    check("OW1.12 A204's row", False)

print("\nnot measured here: the students' learning from these rows -- that is the nightly's refine and its promotion gate (A127/A170)")
print("\nOW1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
