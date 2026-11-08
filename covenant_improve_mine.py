#!/usr/bin/env python3
"""Increment 1 of the nightly improvement-mining process (operator: "nightly is probably the right move.
Tetsu should be learning all these things as we go").

HARVEST ONLY, read-only on the sources, re-runnable. Reads the forum replies our agent collected
(ops/moltbook_candidates.jsonl -- structured {author,text,url,sha256,source}), diffs them against a
seen-set, and returns ONLY what is new since the last run. The next increments route each new reply
through Tetsu's door (tetsu_work) to extract candidate improvements -- which both mines ideas AND teaches
Tetsu -- then vet each under the ring/earn rule (it earns a slot only if removing it reds a real check)
before one capped weekly digest.

Why a seen-set and not a timestamp: the candidates log is appended by several rounds and a row's own time
is the forum comment's, not when we read it; a stable content id (the row's sha256, or a hash of url+text)
is the only thing that says "already mined." Idempotent by construction: a second run with no new rows
returns nothing.

Usage: python covenant_improve_mine.py            # print new replies since last run, update the seen-set
       python covenant_improve_mine.py --dry-run  # print them WITHOUT updating the seen-set (safe to re-run)
"""
import json, os, sys, hashlib, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = os.path.join(HERE, "ops", "moltbook_candidates.jsonl")
SEEN = os.path.join(HERE, "ops", "improve_mined_seen.json")
MIN_CHARS = 200          # a one-line "+1" carries no mechanism to mine; the substantive replies are long


def _row_id(row):
    """Stable id for a reply: its own sha256 when present, else sha256(url+text). Never the row's time."""
    sid = row.get("sha256")
    if isinstance(sid, str) and sid:
        return sid
    basis = (str(row.get("url") or "") + "\n" + str(row.get("text") or "")).encode("utf-8")
    return hashlib.sha256(basis).hexdigest()


def _load_seen(path):
    try:
        v = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
        return set(v) if isinstance(v, list) else set()
    except Exception:                                          # noqa: BLE001 -- unreadable seen-set => mine all, never crash
        return set()


def _save_seen(path, ids):
    """Atomic replace: a half-written seen-set must never make the next run re-mine or skip everything."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(sorted(ids), f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def mark_seen(ids, seen_path=None):
    """Record ids as mined (union into the seen-set). The extractor calls this with ONLY the replies it
    successfully processed, so a door failure leaves its reply un-seen and retried next run, never dropped."""
    if seen_path is None:
        seen_path = SEEN                                       # resolved at call time, so a reassigned global takes
    ids = set(ids)
    if ids:
        _save_seen(seen_path, _load_seen(seen_path) | ids)


# RE-QUEUE (2026-11-04, A409 follow-up). A reply the v1 extractor answered with our own prompt ("echo") was marked
# seen, so its REAL idea could never be mined again (Tien, Claude: "every echo loses that reply's real idea for
# good"). The re-queue is an APPEND-ONLY ledger, never an edit of the seen-set: {"id","reason","t"} puts a seen reply
# back in line; {"id","done":true,"t"} records that it was re-extracted. A reply is pending while its LAST row is not
# done. harvest() offers pending ones FIRST, ahead of new replies, even though they are in the seen-set.
REQUEUE = os.path.join(HERE, "ops", "improve_requeue.jsonl")


def _append_requeue(rows, path=None):
    if path is None:
        path = REQUEUE                                         # IM8: call time
    if not rows:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def requeue(ids, reason, path=None):
    """Put already-seen replies back in line for extraction. Returns how many were newly queued."""
    pend = pending_requeue(path)
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = [{"id": i, "reason": reason, "t": t} for i in dict.fromkeys(ids) if i not in pend]
    _append_requeue(rows, path)
    return len(rows)


def mark_requeue_done(ids, path=None):
    pend = pending_requeue(path)
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _append_requeue([{"id": i, "done": True, "t": t} for i in ids if i in pend], path)


def pending_requeue(path=None):
    """Ids whose last re-queue row is not 'done', in the order they were queued."""
    if path is None:
        path = REQUEUE
    last = {}
    for d in _rows(path):
        if d.get("id"):
            last.pop(d["id"], None)                            # re-insert so order = latest queueing
            last[d["id"]] = bool(d.get("done"))
    return [i for i, done in last.items() if not done]


def _rows(path):
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:                                      # noqa: BLE001 -- one torn line never drops the rest
            continue
        if isinstance(d, dict):
            yield d


def harvest(candidates=None, seen_path=None, min_chars=MIN_CHARS, update=True, requeue_first=False):
    """Return the list of NEW substantive replies since the last run. When update=True, record them as seen.

    'New' = its stable id is not in the seen-set. 'Substantive' = eligible, not a directive, >= min_chars.
    Dedupes within a single run too (the same comment can appear in more than one round)."""
    if candidates is None:                                     # resolved at call time, not frozen at def time, so a
        candidates = CANDIDATES                                # test (or a reassigned global) actually takes effect
    if seen_path is None:
        seen_path = SEEN
    seen = _load_seen(seen_path)
    pend = set(pending_requeue()) if requeue_first else set()
    back = {}                                                  # re-queued replies, offered ahead of new ones
    new, new_ids = [], set()
    for row in _rows(candidates):
        if pend and (row.get("eligible") is not False):
            rid0 = _row_id(row)
            if rid0 in pend and rid0 not in back:
                back[rid0] = {"id": rid0, "author": row.get("author"), "url": row.get("url"),
                              "source": row.get("source"), "text": str(row.get("text") or ""), "requeued": True}
        if row.get("eligible") is False:
            continue
        if (row.get("flags") or {}).get("directive") is True:
            continue
        text = str(row.get("text") or "")
        if len(text) < min_chars:
            continue
        rid = _row_id(row)
        if rid in seen or rid in new_ids:
            continue
        new_ids.add(rid)
        new.append({"id": rid, "author": row.get("author"), "url": row.get("url"),
                    "source": row.get("source"), "text": text})
    if update and new_ids:
        _save_seen(seen_path, seen | new_ids)
    order = [i for i in pending_requeue() if i in back] if back else []
    return [back[i] for i in order] + [x for x in new if x["id"] not in back]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    dry = "--dry-run" in argv
    new = harvest(update=not dry)
    print("improve-mine: %d new substantive repl%s since last run%s"
          % (len(new), "y" if len(new) == 1 else "ies", " (dry run: seen-set unchanged)" if dry else ""))
    for r in new[:40]:
        who = r["author"] or "?"
        print("  - u/%s  %s" % (who, (r["text"][:140].replace("\n", " "))))
    if len(new) > 40:
        print("  ... and %d more" % (len(new) - 40))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
