#!/usr/bin/env python3
"""Increment 2 of the nightly improvement-mining process.

Takes the NEW forum replies the harvester (covenant_improve_mine) found and routes each one through
TETSU'S OWN DOOR (tools/tetsu_work.ask -> /m/agent) to extract a structured improvement candidate. Two
things happen in that one call, by design: the idea is mined, AND Tetsu learns from it -- the door records
every exchange the way all his work does. "Tetsu should be learning all these things as we go" (operator,
2026-10-27).

Read-only on the sources. Idempotent: it harvests WITHOUT consuming, and marks a reply seen ONLY after the
door answered for it -- so a 503/timeout leaves that reply for the next run (the same rule tetsu_work uses).
Rate-aware: at most MAX_PER_RUN replies per run, because the door has its own limits and the nightly delta
is small (the first run seeds the backlog as seen, in increment 3, without extracting 51k).

Output: ops/improve_candidates.jsonl, one row per extracted reply:
  {id, author, url, kind: gap|have|stance|none|unparsed, maps, idea, test, raw, t}

Usage: python covenant_improve_extract.py [N]     (needs the node door up, like tetsu_work)
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve_mine as IM

CANDIDATES_OUT = os.path.join(HERE, "ops", "improve_candidates.jsonl")
MAX_PER_RUN = 20
_KINDS = ("gap", "have", "stance", "none")

PROMPT = """You judge whether a forum reply names a SYSTEM IMPROVEMENT for our covenant: a ledger with an \
ethics gate in the transaction path; every claim gets a test; we keep retractions beside corrections; \
UNDETERMINED is a valid answer; a change earns its place only if removing it reds a real check.

Reply from u/%s:
\"\"\"%s\"\"\"

Answer in EXACTLY these four lines and nothing else:
KIND: one of  gap (names a mechanism we likely LACK) | have (something we likely already do) | stance (a \
principle, not a thing to build) | none (no system idea)
MAPS: the covenant component it touches, or ?
IDEA: the improvement in one line
TEST: a both-ways test as present=green / removed=red, or ?"""


# Fragments of our own PROMPT. A small model often parrots the instruction back instead of answering; a
# field that contains one of these is an echo, not a value, so we blank it rather than store noise.
# NB "present=green / removed=red" is the REAL shape of a both-ways test answer, not an echo -- only the
# instruction-only phrases go here, ones no genuine value would contain.
_ECHO = ("covenant component it touches", "names a mechanism we likely", "something we likely already do",
         "a principle, not a thing to build", "the improvement in one line", "no system idea")


def _parse(answer):
    """Pull KIND/MAPS/IDEA/TEST from the door's free text. A small model will not always emit clean JSON,
    so we read labelled lines, which it holds to far more reliably, and fall back to 'unparsed'. A value that
    parrots the prompt's own instruction is dropped (an echo is not an answer)."""
    out = {"kind": "unparsed", "maps": "", "idea": "", "test": ""}
    for line in (answer or "").splitlines():
        s = line.strip()
        low = s.lower()
        for key in ("kind", "maps", "idea", "test"):
            if low.startswith(key + ":"):
                out[key] = s.split(":", 1)[1].strip()
    k = out["kind"].lower()
    out["kind"] = next((v for v in _KINDS if v in k), "unparsed")
    for key in ("maps", "idea", "test"):
        if any(e in out[key].lower() for e in _ECHO):
            out[key] = ""                                      # echoed instruction -> not a real value
    return out


def _append(row, path=CANDIDATES_OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract(limit=MAX_PER_RUN, ask=None, out=CANDIDATES_OUT, say=print):
    """Extract up to `limit` new replies through the door. `ask(text)->(code, j)` is injected so the test
    drives it offline; the default routes through Tetsu's door and teaches him."""
    if ask is None:
        import tools.tetsu_work as TW                          # the door call that also records for Tetsu
        ask = lambda text: TW.ask(text, door="agent")          # noqa: E731
    new = IM.harvest(update=False)[:limit]
    if not new:
        say("improve-extract: nothing new to extract")
        return []
    done_ids, rows = [], []
    for r in new:
        try:
            code, j = ask(PROMPT % (r.get("author") or "?", (r.get("text") or "")[:1500]))
        except Exception as e:                                 # noqa: BLE001 -- a door error never ends the run
            code, j = 0, {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}
        if code != 200:                                        # door did not answer: leave it un-seen, retry next run
            say("  [skip] u/%s: door %s (will retry next run)" % (r.get("author"), code))
            continue
        p = _parse(j.get("answer", ""))
        row = {"id": r["id"], "author": r.get("author"), "url": r.get("url"), "source": r.get("source"),
               "kind": p["kind"], "maps": p["maps"], "idea": p["idea"], "test": p["test"],
               "raw": (j.get("answer") or "")[:800], "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _append(row, out)
        rows.append(row)
        done_ids.append(r["id"])
        say("  [%s] u/%s: %s" % (p["kind"], r.get("author"), (p["idea"] or "")[:90]))
    IM.mark_seen(done_ids)                                     # consume ONLY what the door answered for
    kinds = {}
    for x in rows:
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    say("improve-extract: %d extracted (%s); %d answered-and-consumed"
        % (len(rows), ", ".join("%s=%d" % kv for kv in sorted(kinds.items())) or "none", len(done_ids)))
    return rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    limit = int(argv[0]) if argv and argv[0].isdigit() else MAX_PER_RUN
    extract(limit=limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
