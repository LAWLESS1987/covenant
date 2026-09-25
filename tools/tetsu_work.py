#!/usr/bin/env python3
"""tools/tetsu_work.py -- hand Tetsu a batch of work on the PC, so the work teaches him.

HIS WORDS, 2026-09-25: "ensure we using pc tetsu for as much as we can so he learns while
limiting token burning". Work an assistant would otherwise spend its own tokens on --
classifying, summarising, a second independent count, a critique of a plan -- goes to the
local model through the node's own doors instead, where every exchange is judged by the
gate, written to the chat memory (ops/chat/ask_log.jsonl) and queued for the teacher
(ops/teacher_queue.jsonl). That is the path by which he learns from it.

THE ADDRESS. Each door replays the last turns of the SAME caller (agent_history). His own
conversations with Tetsu on this PC come from 127.0.0.1, so batch work is sent from
127.0.0.2 -- also loopback, also admitted by tailnet_ok -- and never crowds his history.

WHAT IT ADDS: NOTHING THAT LIMITS. It stays under the limits the doors already have (30
asks per 10 minutes per caller; the API limiter answers 429 on a burst) by pacing, and
on a 429 it waits and asks again. It changes nothing in Tetsu: no persona call, no
register, no voice. A withheld answer is recorded as withheld, not retried.

Input: a JSONL file, one {"id": "...", "text": "..."} per line (or a .txt, one question per
line). Output: JSONL, one row per item with the door's answer, verdict and timing.

    python tools/tetsu_work.py --in questions.jsonl --out answers.jsonl [--door agent|council]
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import sys
import time

PACE_S = 21.0          # 30 asks / 600 s allows one per 20 s; one more second of slack
SOURCE = "127.0.0.2"   # a loopback caller of its own (see THE ADDRESS above)
DOORS = {"agent": "/m/agent", "council": "/pc/council"}


class _SourceConn(http.client.HTTPConnection):
    """An HTTP connection whose socket is bound to SOURCE before it connects."""

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), self.timeout, source_address=(SOURCE, 0))


def ask(text, door="agent", host="127.0.0.1", port=5000, timeout=600):
    """One exchange. Returns (status_code, body_dict)."""
    body = json.dumps({"text": text}).encode("utf-8")
    c = _SourceConn(host, port, timeout=timeout)
    try:
        c.request("POST", DOORS[door], body=body, headers={"Content-Type": "application/json"})
        r = c.getresponse()
        raw = r.read().decode("utf-8", "replace")
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, {"status": "error", "message": raw[:300]}
    finally:
        c.close()


def load(path):
    items = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            if path.endswith(".jsonl"):
                d = json.loads(line)
                items.append({"id": str(d.get("id", i)), "text": str(d["text"])})
            else:
                items.append({"id": str(i), "text": line})
    return items


def run(items, out, door="agent", host="127.0.0.1", port=5000, pace=PACE_S, say=print):
    done = set()
    if os.path.exists(out):
        with open(out, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["id"])
                except (ValueError, KeyError):
                    pass
    todo = [it for it in items if it["id"] not in done]
    say("tetsu_work: %d item(s), %d already answered, %d to ask through %s from %s" % (len(items), len(done), len(todo), DOORS[door], SOURCE))
    last = 0.0
    for n, it in enumerate(todo, 1):
        while True:
            wait = pace - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.time()
            t0 = time.time()
            try:
                code, j = ask(it["text"], door, host, port)
            except (OSError, http.client.HTTPException) as e:
                code, j = 0, {"status": "error", "message": "%s: %s" % (type(e).__name__, e)}
            if code == 429:
                say("  %s: 429 -- the door's own limit; waiting 60 s and asking again" % it["id"])
                time.sleep(60)
                continue
            break
        row = {"id": it["id"], "code": code, "status": j.get("status"), "answer": j.get("answer", ""),
               "withheld": j.get("withheld"), "admitted": j.get("admitted"), "held": j.get("alleges_nothing"),
               "message": str(j.get("message", ""))[:400], "model": j.get("model"), "ms": int((time.time() - t0) * 1000)}
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        say("  [%d/%d] %s: %s %s" % (n, len(todo), it["id"], code, "withheld" if row["withheld"] else ("%d chars" % len(row["answer"] or ""))))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="hand Tetsu a batch of work through the node's doors")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--door", choices=sorted(DOORS), default="agent")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--pace", type=float, default=PACE_S)
    a = ap.parse_args(argv)
    return run(load(a.inp), a.out, a.door, port=a.port, pace=a.pace)


if __name__ == "__main__":
    sys.exit(main())
