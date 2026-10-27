#!/usr/bin/env python3
"""IM1 -- the improvement-mining harvester (covenant_improve_mine.py), driven BOTH WAYS, offline, no network.

The property that must never break: a reply is returned ONCE. A second run over the same corpus returns
nothing (the seen-set suppresses it); a newly appended reply is returned; and a CONTROL with an empty
seen-set returns ALL of them -- which proves the suppression is a real guard, not the rows being absent.
Also pins the substance filters (eligible/directive/min-chars) and that --dry-run does not record.
"""
import json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve_mine as IM


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _row(author, text, sha, eligible=True, directive=False):
    return {"author": author, "text": text, "sha256": sha, "url": "u/" + sha,
            "source": "moltbook/comment", "eligible": eligible,
            "flags": {"directive": directive, "chars": len(text)}}


def main():
    fails = []
    long = "x" * 250                                          # >= MIN_CHARS (200)
    with tempfile.TemporaryDirectory() as d:
        cand = os.path.join(d, "candidates.jsonl")
        seen = os.path.join(d, "seen.json")

        # Two substantive replies + three that the filters must drop.
        _write(cand, [
            _row("alice", "ALICE " + long, "a1"),
            _row("bob",   "BOB "   + long, "b2"),
            _row("short", "too short", "s3"),                 # < MIN_CHARS
            _row("inel",  "INEL "  + long, "i4", eligible=False),
            _row("dir",   "DIR "   + long, "d5", directive=True),
        ])

        # 1. First run: exactly the two substantive, eligible, non-directive replies.
        r1 = IM.harvest(cand, seen)
        ids1 = sorted(x["id"] for x in r1)
        if ids1 != ["a1", "b2"]:
            fails.append("first run should return [a1,b2], got %r" % ids1)

        # 2. BOTH WAYS -- second run over the SAME corpus returns nothing (seen-set suppresses).
        r2 = IM.harvest(cand, seen)
        if r2:
            fails.append("second run leaked %d already-mined repl(ies): %r" % (len(r2), [x["id"] for x in r2]))

        # 3. CONTROL -- an empty seen-set returns ALL of them, proving #2 was the guard, not absence.
        fresh_seen = os.path.join(d, "fresh.json")
        rc = IM.harvest(cand, fresh_seen, update=False)
        if sorted(x["id"] for x in rc) != ["a1", "b2"]:
            fails.append("control (empty seen-set) should re-surface [a1,b2], got %r"
                         % sorted(x["id"] for x in rc))

        # 4. A newly appended reply is the ONLY thing the next run returns.
        with open(cand, "a", encoding="utf-8") as f:
            f.write(json.dumps(_row("carol", "CAROL " + long, "c6")) + "\n")
        r3 = IM.harvest(cand, seen)
        if sorted(x["id"] for x in r3) != ["c6"]:
            fails.append("after append, run should return only [c6], got %r" % sorted(x["id"] for x in r3))

        # 5. --dry-run must NOT record: a dry harvest then a real one both see the same new row.
        seen2 = os.path.join(d, "seen2.json")
        _write(cand, [_row("dave", "DAVE " + long, "d7")])
        dry = IM.harvest(cand, seen2, update=False)
        wet = IM.harvest(cand, seen2, update=True)
        if not (sorted(x["id"] for x in dry) == ["d7"] and sorted(x["id"] for x in wet) == ["d7"]):
            fails.append("dry-run must not record: dry=%r wet=%r"
                         % ([x["id"] for x in dry], [x["id"] for x in wet]))
        # ...and now that the wet run recorded it, the next run is empty.
        if IM.harvest(cand, seen2):
            fails.append("after a recording run, d7 should be suppressed")

    if fails:
        print("IM1 FAIL:")
        for x in fails:
            print("  -", x)
        return 1
    print("IM1: 6/6 passed -- harvest returns each reply once; seen-set suppresses re-mining; "
          "empty-seen control re-surfaces all (guard is real); filters and --dry-run pinned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
