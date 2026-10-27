#!/usr/bin/env python3
"""IM2 -- the improvement-extractor (covenant_improve_extract.py), driven BOTH WAYS, offline, no network.

The door is stubbed; nothing leaves the machine. The property that must never break: a reply is extracted
ONCE and only after the door answered for it. A door failure (code != 200) records nothing and leaves the
reply UN-seen, so the next run retries it; a success consumes it so it is not re-mined. A control with an
empty seen-set re-surfaces all, proving the consume step is the real guard. Parsing of the labelled answer
is pinned too.
"""
import json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve_mine as IM
import covenant_improve_extract as EX


def _row(author, text, sha):
    return {"author": author, "text": text, "sha256": sha, "url": "u/" + sha,
            "source": "moltbook/comment", "eligible": True, "flags": {"directive": False}}


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _out_ids(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l)["id"] for l in open(path, encoding="utf-8") if l.strip()]


def main():
    fails = []
    long = "x" * 250
    orig_cand, orig_seen = IM.CANDIDATES, IM.SEEN
    try:
        with tempfile.TemporaryDirectory() as d:
            IM.CANDIDATES = os.path.join(d, "candidates.jsonl")
            IM.SEEN = os.path.join(d, "seen.json")
            out = os.path.join(d, "improve_candidates.jsonl")
            _write(IM.CANDIDATES, [_row("alice", "ALICE " + long, "a1"),
                                   _row("bob",   "BOB "   + long, "b2"),
                                   _row("carl",  "CARL "  + long, "c3")])

            # Stub door: alice -> a parseable GAP, bob -> HAVE, carl -> the door does not answer (503).
            def stub(text):
                if "alice" in text:
                    return 200, {"answer": "KIND: gap\nMAPS: the gate\nIDEA: bind a policy epoch\n"
                                           "TEST: present=green / removed=red"}
                if "bob" in text:
                    return 200, {"answer": "KIND: have\nMAPS: VC1\nIDEA: already covered\nTEST: ?"}
                if "carl" in text:
                    return 503, {}
                return 200, {"answer": "KIND: none"}

            rows1 = EX.extract(limit=20, ask=stub, out=out, say=lambda *a: None)

            # 1. Only the two the door answered for are recorded, with parsed kinds.
            got = {r["id"]: r["kind"] for r in rows1}
            if got != {"a1": "gap", "b2": "have"}:
                fails.append("run1 should record a1=gap,b2=have, got %r" % got)
            if _out_ids(out) != ["a1", "b2"]:
                fails.append("run1 out file should hold [a1,b2], got %r" % _out_ids(out))
            # parse detail
            alice = next((r for r in rows1 if r["id"] == "a1"), {})
            if alice.get("maps") != "the gate" or not alice.get("test"):
                fails.append("run1 parse of a1 wrong: %r" % alice)

            # 2. BOTH WAYS -- a1,b2 are consumed (seen); carl is NOT (door failed), so it remains to harvest.
            remaining = sorted(x["id"] for x in IM.harvest(update=False))
            if remaining != ["c3"]:
                fails.append("after run1 only c3 should remain un-mined, got %r" % remaining)

            # 3. Retry: the door now answers carl -> it is extracted, nothing re-extracts a1/b2.
            def stub2(text):
                if "carl" in text:
                    return 200, {"answer": "KIND: gap\nMAPS: distill\nIDEA: keep join keys\nTEST: ?"}
                return stub(text)
            rows2 = EX.extract(limit=20, ask=stub2, out=out, say=lambda *a: None)
            if [r["id"] for r in rows2] != ["c3"]:
                fails.append("run2 should extract only the retried c3, got %r" % [r["id"] for r in rows2])
            if _out_ids(out) != ["a1", "b2", "c3"]:
                fails.append("out file should now hold [a1,b2,c3], got %r" % _out_ids(out))

            # 4. CONTROL -- an empty seen-set re-surfaces all three, proving the consume step is the guard.
            IM.SEEN = os.path.join(d, "fresh.json")
            ctrl = sorted(x["id"] for x in IM.harvest(update=False))
            if ctrl != ["a1", "b2", "c3"]:
                fails.append("control (empty seen) should re-surface all three, got %r" % ctrl)

            # 5. ECHO GUARD -- the live 3B parroted the prompt into MAPS; a parroted field must be dropped,
            #    while the real KIND still parses. (Regression from the 2026-10-27 live smoke.)
            echoed = EX._parse("KIND: gap\nMAPS: the covenant component it touches, or ?\n"
                               "IDEA: a real idea here\nTEST: present=green / removed=red")
            if echoed["kind"] != "gap":
                fails.append("echo guard dropped the KIND too: %r" % echoed)
            if echoed["maps"] != "":
                fails.append("echo guard should blank the parroted MAPS, got %r" % echoed)
            if echoed["idea"] != "a real idea here":
                fails.append("echo guard wrongly blanked a genuine IDEA: %r" % echoed)
            if echoed["test"] != "present=green / removed=red":
                fails.append("echo guard wrongly blanked a genuine both-ways TEST: %r" % echoed)
    finally:
        IM.CANDIDATES, IM.SEEN = orig_cand, orig_seen

    if fails:
        print("IM2 FAIL:")
        for x in fails:
            print("  -", x)
        return 1
    print("IM2 OK: door stubbed (offline); a reply is extracted once, only after the door answered; "
          "a door failure is retried not dropped; empty-seen control re-surfaces all; labelled parse pinned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
