#!/usr/bin/env python3
"""covenant_teacher_queue.py -- the students learn from what he says to Tetsu.

His words, 2026-09-21: "apply the teacher queue patch so it actually learns
from me." Before this file, every conversation was memory (ops/chat/ask_log.jsonl,
read back by the agent door) and nothing more: the students' verdicts are not
labels (A159), and the only labelled rows the student trains on are the
teacher panel's. This is the missing half: rows that the phone and the agent
door queue for the teacher (ops/teacher_queue.jsonl, written by
covenant_daily_plan.teacher_queue_append) are carried to the PANEL by the
nightly, and the rows the panel labels unanimously enter the ledger the
student trains on, with the panel's provenance on each, under the same rules
every other teacher-labelled row obeys:

  * the panel rule (covenant_teacher_panel.admit): several models, two
    families, unanimous, the writer never alone -- a held row does not teach;
  * no duplicates: a text already in the ledger is not judged twice;
  * BALANCE: in one pass, no more clean rows are kept than violating rows.
    Conversation is mostly clean. Measured 2026-09-04 (covenant_distill.
    load_verdicts): a corpus fed almost pure CLEAN made the next student
    vaguer, and the promotion rule refused it. Clean rows past the balance are
    recorded as rejected with the reason "balance", not dropped silently, and
    are consumed -- the queue is a queue, not a reservoir.
  * every row consumed is recorded in ops/teacher_queue.state.json by line
    offset, so a row is judged once, whatever the outcome.

Nothing here runs unless the nightly asks (--queue N). Nothing here changes a
label: the panel labels, this file carries.
"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "ops", "teacher_queue.jsonl")
STATE = os.path.join(HERE, "ops", "teacher_queue.state.json")
MIN_WORDS, MAX_WORDS = 3, 120
SOURCE = "queue"


def _norm(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().lower()


def _read_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return int(d.get("consumed", 0)) if isinstance(d, dict) else 0
    except (OSError, ValueError):
        return 0


def _write_state(path, consumed, note):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"consumed": int(consumed), "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "note": str(note)[:200]}, fh)


def pending(queue_path=None, state_path=None):
    """(rows not yet consumed, their absolute line offsets). Malformed lines are skipped but counted as consumed."""
    queue_path = queue_path or QUEUE
    state_path = state_path or STATE
    start = _read_state(state_path)
    rows, offsets = [], []
    try:
        with open(queue_path, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i < start:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict) and str(d.get("text", "")).strip():
                    rows.append(d)
                    offsets.append(i)
    except OSError:
        return [], []
    return rows, offsets


def consume(limit, say=print, queue_path=None, state_path=None, verdicts_path=None,
            rejected_path=None, panel_rows=None, principles=None):
    """Carry up to `limit` queued rows to the panel; write the admitted ones to
    the ledger and the rest to the rejected file, balanced; advance the state.
    Returns {"seen", "judged", "kept", "kept_violates", "kept_clean", "rejected", "duplicates", "consumed"}."""
    import covenant_distill as X
    import covenant_judge_fallback as FB
    queue_path = queue_path or QUEUE
    state_path = state_path or STATE
    # PRIVATE BY DEFAULT (2026-09-26, his words: "protect operation security in all
    # we do by default"). His conversations and his phone's AI screens are not a
    # shareable source, so both outputs default to the gitignored halves. Before
    # this, the tracked ledgers took them, and 101 rows (his work address among
    # them) sat one `git add` from the public repository. The student reads both
    # halves (covenant_distill.corpus_paths), so it loses nothing.
    shared_ledger = verdicts_path is None
    verdicts_path = verdicts_path or X.LIVE_VERDICTS
    rejected_path = rejected_path or X.LIVE_REJECTED
    stats = {"seen": 0, "judged": 0, "kept": 0, "kept_violates": 0, "kept_clean": 0,
             "rejected": 0, "duplicates": 0, "consumed": _read_state(state_path)}
    rows, offsets = pending(queue_path, state_path)
    if not rows:
        say("queue: nothing waiting for the teacher")
        return stats
    rows, offsets = rows[:max(0, int(limit))], offsets[:max(0, int(limit))]
    stats["seen"] = len(rows)

    # what the ledger already holds, so nothing is judged twice
    known = set()
    for path in [verdicts_path] + ([X.VERDICTS] if shared_ledger else []):
        for d in X.load_verdicts(path, paired_only=False):
            known.add(_norm(d.get("text")))
    cases, meta = [], []
    for d, off in zip(rows, offsets):
        text = str(d.get("text", "")).strip()[:4000]
        words = len(text.split())
        if not (MIN_WORDS <= words <= MAX_WORDS) or _norm(text) in known:
            stats["duplicates"] += 1
            continue
        known.add(_norm(text))
        cases.append({"message": text, "expect": None})
        meta.append((d, off))
    last_offset = offsets[-1]
    if not cases:
        _write_state(state_path, last_offset + 1, "nothing new to judge")
        stats["consumed"] = last_offset + 1
        say("queue: %d row(s) seen, none new (duplicates or out of size); consumed" % stats["seen"])
        return stats

    if principles is None:
        import covenant_unified_v8 as _cov
        principles = list(_cov.DIVINE_PRINCIPLES)
    panel_rows = panel_rows or X.panel_rows
    judged = panel_rows(cases, principles, say=say)
    stats["judged"] = len(cases)

    # the balance: violating rows first, then as many clean rows as that
    admitted = {i: r for i, r in judged.items() if r.get("admitted") and r.get("violates") is not None}
    viol = [i for i in sorted(admitted) if admitted[i]["violates"]]
    clean = [i for i in sorted(admitted) if not admitted[i]["violates"]]
    keep = set(viol) | set(clean[:len(viol)])
    os.makedirs(os.path.dirname(verdicts_path), exist_ok=True)
    os.makedirs(os.path.dirname(rejected_path), exist_ok=True)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for i, c in enumerate(cases):
        d, off = meta[i]
        r = judged.get(i, {})
        rec = {"t": now, "text": FB._payload_text({"message": c["message"], "origin": "organic"}),
               "judge": r.get("judge", "panel"), "panel": r.get("panel"),
               "reason": str(r.get("reason", ""))[:240],
               "source": SOURCE, "queued_from": str(d.get("source", ""))[:80], "queue_offset": off}
        if i in keep:
            rec["violates"] = bool(r["violates"])
            with open(verdicts_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stats["kept"] += 1
            stats["kept_violates" if rec["violates"] else "kept_clean"] += 1
        else:
            rec["judged"] = r.get("violates")
            rec["held"] = bool(r.get("held", not r.get("admitted")))
            rec["why"] = "balance: clean rows past the pass's violating count" if i in admitted else str(r.get("why", "not admitted"))[:160]
            with open(rejected_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stats["rejected"] += 1
    _write_state(state_path, last_offset + 1, "kept %d, rejected %d" % (stats["kept"], stats["rejected"]))
    stats["consumed"] = last_offset + 1
    say("queue: %d seen, %d judged by the panel, %d kept (%d violating, %d clean), %d rejected, %d duplicate/out of size"
        % (stats["seen"], stats["judged"], stats["kept"], stats["kept_violates"], stats["kept_clean"],
           stats["rejected"], stats["duplicates"]))
    return stats


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="carry queued rows to the teacher panel")
    ap.add_argument("--limit", type=int, default=24)
    ap.add_argument("--pending", action="store_true", help="count what waits; judge nothing")
    a = ap.parse_args()
    if a.pending:
        rows, _ = pending()
        print("%d row(s) waiting for the teacher" % len(rows))
    else:
        consume(a.limit)
