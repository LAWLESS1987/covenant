#!/usr/bin/env python3
"""covenant_own_work.py -- the system learns from its own repairs and its own
settled code answers: recursion, bounded and recorded.

HIS WORDS, 2026-09-21: "refine and improve all apps towards recursive learning
coding and mutual benefit" -- and, the same evening, "as of midnight they will
not have you to help get them self sufficient baby birds leaving the nest".

WHAT WAS THERE. The students learn from his conversations and from his AI
apps' screens through the teacher queue (A166: covenant_daily_plan.
teacher_queue_append, consumed by the nightly, panel-labelled, once each).
The code door (A177, covenant_code_consensus) records a question, the
council's answer and the seats' answers, and a consensus when two or more
systems answered. Neither fed the other, and nothing the machine learned
about its OWN code -- every entry in docs/KNOWN_ISSUES.md is his words, what
was measured, what was built and how it was proved -- ever reached a student.

WHAT THIS ADDS. Once a night, before the queue is consumed:
  1. every ledger entry not yet carried (by its A-number, kept in
     ops/own_work_state.json) becomes ONE teacher row: his words from the
     header, then the entry's first paragraphs, cut to the queue's size;
     source "own-work:A<n>";
  2. every code-consensus record in state "consensus" not yet carried
     becomes one row: the question and the agreed text; source
     "code-consensus:<id>".
Bounded: at most MAX_PER_NIGHT rows a night, oldest first, so the queue
stays his conversations first. The queue's own rules still apply (the panel
labels, balance, once each) -- this is a SOURCE, not a shortcut past the gate.

WHAT IT DOES NOT DO. It does not write code, change a check, or retrain
anything itself: the nightly's refine (A127) is the only learner, and its
promotion gate (A170) still refuses a regressing student. It reads two files
this repository already keeps and appends to a queue that already exists.
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LEDGER = os.path.join(HERE, "docs", "KNOWN_ISSUES.md")
CONSENSUS = os.path.join(HERE, "ops", "code_consensus.jsonl")
STATE = os.path.join(HERE, "ops", "own_work_state.json")
# A211 (2026-09-21, his words: "Now sift back through for any caps on learning
# other than mutual benefit and remove them"). These were 12 and 3200 -- numbers
# the assistant picked. At 12 a night the system needed seventeen nights to read
# its own 207-entry history, and 3200 characters cut most entries off mid-record.
# What is left is a runtime bound and nothing else: the nightly has to finish and
# the queue has to fit on his disk. Both are overridable from the environment.
MAX_PER_NIGHT = int(os.environ.get("COVENANT_OWN_WORK_PER_NIGHT") or 250)
ROW_CHARS = int(os.environ.get("COVENANT_OWN_WORK_ROW_CHARS") or 12000)

_HEAD = re.compile(r"^### (A\d+[a-z]?)\. (.+)$", re.M)


def ledger_entries(text):
    """[(a_number, header, body)] in file order, from the ledger's markdown."""
    heads = list(_HEAD.finditer(text))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end]
        body = body.split("\n---", 1)[0]
        out.append((m.group(1), m.group(2).strip(), body.strip()))
    return out


def entry_row(a, header, body):
    """One teaching row: his words (the quotes in the header), then the body's
    first paragraphs, whole paragraphs only, within ROW_CHARS."""
    quotes = re.findall(r'"([^"]{8,400})"', header)
    words = " / ".join(q.strip() for q in quotes[:4])
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    text = "%s -- his words: %s\n\n" % (a, words) if words else "%s -- %s\n\n" % (a, header[:300])
    for p in paras:
        p = re.sub(r"\s+", " ", p)
        if len(text) + len(p) + 2 > ROW_CHARS:
            break
        text += p + "\n\n"
    return {"text": text.strip(), "source": "own-work:%s" % a}


def consensus_rows(path=CONSENSUS):
    """[(id, row)] for every settled consensus record, in file order."""
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("kind") == "consensus" and r.get("state") == "consensus" and r.get("text"):
                    q = str(r.get("question", ""))[:600]
                    out.append((str(r.get("id")), {"text": ("CODE QUESTION: %s\n\nAGREED BY %s: %s"
                                                             % (q, str(r.get("why", ""))[:120], str(r["text"])[:ROW_CHARS - 800])).strip(),
                                                    "source": "code-consensus:%s" % str(r.get("id"))[:40]}))
    except OSError:
        pass
    return out


def load_state(path=STATE):
    try:
        with open(path, encoding="utf-8") as fh:
            s = json.load(fh)
        return {"ledger": set(s.get("ledger", [])), "consensus": set(s.get("consensus", []))}
    except (OSError, ValueError):
        return {"ledger": set(), "consensus": set()}


def save_state(state, path=STATE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "ledger": sorted(state["ledger"]),
                   "consensus": sorted(state["consensus"])}, fh, indent=1)


def run(ledger=LEDGER, consensus=CONSENSUS, state_path=STATE, queue_path=None, limit=MAX_PER_NIGHT,
        say=print, append=None):
    """Carry what is new to the teacher queue. Returns the counts."""
    if append is None:
        from covenant_daily_plan import teacher_queue_append as append
    state = load_state(state_path)
    rows, carried = [], {"ledger": [], "consensus": []}
    try:
        with open(ledger, encoding="utf-8") as fh:
            entries = ledger_entries(fh.read())
    except OSError as e:
        say("own-work: ledger unreadable: %s" % e)
        entries = []
    for a, header, body in entries:
        if a in state["ledger"] or len(rows) >= limit:
            continue
        rows.append(entry_row(a, header, body)); carried["ledger"].append(a)
    for cid, row in consensus_rows(consensus):
        if cid in state["consensus"] or len(rows) >= limit:
            continue
        rows.append(row); carried["consensus"].append(cid)
    kept = append(rows, path=queue_path) if rows else 0
    # only what the queue actually took is marked carried; the rest waits
    took = rows[:kept]
    for r in took:
        src = r["source"]
        if src.startswith("own-work:"):
            state["ledger"].add(src.split(":", 1)[1])
        elif src.startswith("code-consensus:"):
            state["consensus"].add(src.split(":", 1)[1])
    save_state(state, state_path)
    waiting = max(0, len(entries) - len(state["ledger"]))
    say("own-work: %d row(s) queued for the teacher (%d ledger entries, %d code consensus), %d ledger entries waiting"
        % (kept, sum(1 for r in took if r["source"].startswith("own-work:")),
           sum(1 for r in took if r["source"].startswith("code-consensus:")), waiting))
    return {"queued": kept, "ledger": [a for a in carried["ledger"] if a in state["ledger"]],
            "consensus": [c for c in carried["consensus"] if c in state["consensus"]], "waiting": waiting}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the system learns from its own repairs and settled code answers")
    ap.add_argument("--limit", type=int, default=MAX_PER_NIGHT)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args(argv)
    if a.status:
        st = load_state()
        with open(LEDGER, encoding="utf-8") as fh:
            n = len(ledger_entries(fh.read()))
        print(json.dumps({"ledger_entries": n, "carried": len(st["ledger"]), "consensus_carried": len(st["consensus"]),
                          "settled_consensus": len(consensus_rows())}, indent=1))
        return 0
    run(limit=a.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
