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
But everything sent from here shares 127.0.0.2's history with everything else sent from here
(A284): batches, ad-hoc asks, and until 2026-10-06 his reviews of free's drafts and his round
updates, each read beside a tail of earlier reviews. An ask that must be read on its own passes
ask(fresh=True): no turns replayed into it, and it is replayed into none.

WHAT IT ADDS: NOTHING THAT LIMITS. It stays under the limits the doors already have (30
asks per 10 minutes per caller; the API limiter answers 429 on a burst) by pacing, and
on a 429 it waits and asks again. It changes nothing in Tetsu: no persona call, no
register, no voice. A withheld answer is recorded as withheld, not retried.

WHERE THE TEACHER IS (A263, 2026-10-05). The teacher queue is carried by the nightly to the
teacher PANEL, which runs on the PUBLIC repository's GitHub Actions runner, and the runner's job
summary is rendered publicly -- the A128 route. So an item handed here is published unless it is
marked private. A private item is answered by the model on this machine and nothing of it leaves
it: the door records it as withheld from the teacher (ops/teacher_queue.withheld.jsonl, with the
reason), does not replay it into ordinary asks, and makes no fetch, web search or forum act for it.
It does not teach him; that is the cost, and it is said rather than hidden.

An item is private when any of these holds:
  * --private (the whole batch), or {"private": true} on its line;
  * the --in file, or an item's "file", lies under a private/ tree -- by DEFAULT, because a
    transcript published by mistake cannot be taken back and a withheld one can be released by
    moving its line into the queue. --teach sends such a batch to the teacher anyway, announced;
  * COVENANT_HOLD_PRIVATE=1, as for covenant_route.py and x_video_text.py.
Before anything private is sent the door is asked whether it honours the marker (a core older than
A263 ignores the field and would queue the text); if it does not, nothing private is sent. Every
private answer must carry the door's withheld note, or the batch stops there.

Input: a JSONL file, one {"id": "...", "text": "..."} per line (or a .txt, one question per
line). Output: JSONL, one row per item with the door's answer, verdict and timing.

    python tools/tetsu_work.py --in questions.jsonl --out answers.jsonl [--door agent|council] [--private | --teach]
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


def ask(text, door="agent", host="127.0.0.1", port=5000, timeout=600, private=False, fresh=False):
    """One exchange. Returns (status_code, body_dict). `private` sends {"private": true} (A263);
    `fresh` sends {"fresh": true} (A284): the door replays none of this address's earlier turns into
    it, and replays it into none of theirs. The door's reply says "fresh": true when it honoured that."""
    payload = {"text": text}
    if private:
        payload["private"] = True
    if fresh:
        payload["fresh"] = True
    body = json.dumps(payload).encode("utf-8")
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


def under_private(path):
    """Is this path inside a private/ tree? Path-based and deliberately blunt, the same test as
    x_video_text._private: a check that tried to judge which private material is safe to publish
    would be one nobody could audit."""
    if not path:
        return False
    return "private" in os.path.abspath(str(path)).replace("\\", "/").lower().split("/")


def load(path):
    items = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            if path.endswith(".jsonl"):
                d = json.loads(line)
                it = {"id": str(d.get("id", i)), "text": str(d["text"])}
                if d.get("private") is True or under_private(d.get("file")):
                    it["private"] = True
                items.append(it)
            else:
                items.append({"id": str(i), "text": line})
    return items


def mark(items, inp=None, private=False, teach=False, env=None, say=print):
    """Decide which items are private (A263) and say why, once. Returns the items, marked."""
    env = os.environ if env is None else env
    hold = env.get("COVENANT_HOLD_PRIVATE") == "1"
    if private or hold:
        for it in items:
            it["private"] = True
        say("tetsu_work: every item is PRIVATE (%s): answered on this machine, withheld from the teacher (A263)"
            % ("COVENANT_HOLD_PRIVATE=1" if hold else "--private"))
    elif under_private(inp):
        if teach:
            say("tetsu_work: %s is under private/ and --teach was given: these items go to the teacher panel, which "
                "runs on the PUBLIC repository's runner, whose job summary is rendered publicly (A128)." % inp)
        else:
            for it in items:
                it["private"] = True
            say("tetsu_work: %s is under private/, so every item is PRIVATE by default: answered on this machine, "
                "withheld from the teacher (A263). --teach sends them to the public teacher panel instead." % inp)
    n = sum(1 for it in items if it.get("private"))
    if n:
        say("tetsu_work: %d of %d item(s) private" % (n, len(items)))
    return items


def door_honours_private(door="agent", host="127.0.0.1", port=5000, asker=None):
    """Ask the door, before anything private is sent, whether this core keeps a private ask off the
    public panel. An empty text is refused 400 by every core; one that honours the marker says so in
    that refusal. Costs no model call. Returns (bool, why)."""
    asker = asker or ask
    try:
        code, j = asker("", door, host, port, timeout=30, private=True)
    except (OSError, http.client.HTTPException) as e:
        return False, "the door did not answer: %s: %s" % (type(e).__name__, e)
    if code == 400 and j.get("honours_private") is True:
        return True, "the door honours the private marker"
    return False, ("the door at port %d answered %s without honours_private -- its core predates A263 and would "
                   "queue a private ask for the public panel" % (port, code))


def run(items, out, door="agent", host="127.0.0.1", port=5000, pace=PACE_S, say=print, asker=None):
    asker = asker or ask
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
    if any(it.get("private") for it in todo):
        ok, why = door_honours_private(door, host, port, asker=asker)
        if not ok:
            say("tetsu_work: REFUSED, nothing sent: %s. Restart the node on the current core, then run this again." % why)
            return 2
    last = 0.0
    for n, it in enumerate(todo, 1):
        private = bool(it.get("private"))
        while True:
            wait = pace - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.time()
            t0 = time.time()
            try:
                code, j = asker(it["text"], door, host, port, private=private)
            except (OSError, http.client.HTTPException) as e:
                code, j = 0, {"status": "error", "message": "%s: %s" % (type(e).__name__, e)}
            if code == 429:
                say("  %s: 429 -- the door's own limit; waiting 60 s and asking again" % it["id"])
                time.sleep(60)
                continue
            break
        teacher = j.get("teacher") or ("queued for the teacher panel (not marked private)" if code == 200 and not private else None)
        row = {"id": it["id"], "code": code, "status": j.get("status"), "answer": j.get("answer", ""),
               "withheld": j.get("withheld"), "admitted": j.get("admitted"), "held": j.get("alleges_nothing"),
               "message": str(j.get("message", ""))[:400], "model": j.get("model"), "ms": int((time.time() - t0) * 1000),
               "private": private, "teacher": teacher}
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        say("  [%d/%d] %s: %s %s%s" % (n, len(todo), it["id"], code, "withheld" if row["withheld"] else ("%d chars" % len(row["answer"] or "")),
                                       " (private, not queued)" if private and j.get("private") is True else ""))
        if private and code == 200 and j.get("private") is not True:
            # The door answered without its withheld note: the core changed under the batch, or a
            # proxy dropped the field. That item may be queued; stop before the next one is.
            say("tetsu_work: STOPPED after %s: the door answered a private item without confirming it was withheld "
                "(A263). Check ops/teacher_queue.jsonl for it before the nightly runs." % it["id"])
            return 2
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="hand Tetsu a batch of work through the node's doors")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--door", choices=sorted(DOORS), default="agent")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--pace", type=float, default=PACE_S)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--private", action="store_true",
                   help="every item is answered on this machine and withheld from the public teacher panel (A263)")
    g.add_argument("--teach", action="store_true",
                   help="an --in file under private/ goes to the teacher panel anyway (it runs on the PUBLIC repo's runner)")
    a = ap.parse_args(argv)
    items = mark(load(a.inp), inp=a.inp, private=a.private, teach=a.teach)
    return run(items, a.out, a.door, port=a.port, pace=a.pace)


if __name__ == "__main__":
    sys.exit(main())
