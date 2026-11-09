#!/usr/bin/env python3
"""IM10 -- the improve-miner never mines our own replies; one own-account rule shared with free (A418).
Offline: every ledger is a temp file; the live ones are snapshotted and must be byte-identical afterwards.

Why (A418, 2026-11-09). A280 (10-06) taught free's reply round to recognise her own account by what she said. The
improve-miner reads the same comments log through its own harvest and never got the rule: on 2026-11-08 it mined
u/covenant-node -- our own reply -- into the backlog as an outside idea, and 294 more of ours were queued. The rule
now lives in covenant_own_account and both readers call it. Measured on the live logs the same day, the rule as
written also classed two OTHER agents as us, because free's replies to them opened with their own words; a text
match against a reply addressed to that same author no longer counts.

Both ways (mutations driven in the 2026-11-09 build; docs/KNOWN_ISSUES.md A418): each property present -> green,
removed -> the named check goes red.

Blind spots (rule 9): an own reply the sends ledger never recorded, by an account that has no recorded reply in the
log at all, cannot be recognised (the rule is by text; the account's name is on no record). A comment that quotes
our reply as its own opening, by someone we never answered, is classed as us -- the same risk A280 accepted.
"""
import hashlib, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_own_account as OA
import covenant_improve_mine as IM

OURS_TO_X = ("I agree that a receipt you can trace beats a summary you cannot, and the trace is what makes "
             "a correction cheap later on. What do you keep?")
X_TEXT = ("That's a really sharp observation about broken fixes and the role of a verifier, and it separates "
          "flagging a defect from fixing it.")
PARROT = X_TEXT + " Your rule makes sense."            # our reply to X that opened with X's own words
TAIL = " and the comment goes on about other things at some length" * 5


def _row(author, text, sha):
    return {"author": author, "text": text, "sha256": sha, "url": "https://www.moltbook.com/post/" + sha,
            "source": "moltbook/comment", "eligible": True, "flags": {"directive": False}}


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _snap(paths):
    return {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in paths if os.path.exists(p)}


def main():
    fails, checks = [], 0

    def ok(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(msg)

    live = [IM.CANDIDATES, IM.SEEN, IM.REQUEUE, OA.sends_path()]
    before = _snap(live)
    td = tempfile.mkdtemp(prefix="im10_")
    sends = [
        {"kind": "reply", "sent": True, "author": "zed", "text": OURS_TO_X},                 # ours, answering zed
        {"kind": "reply", "sent": True, "author": "xagent", "text": PARROT},                 # ours, parroting xagent
        {"kind": "reply", "sent": False, "author": "w", "text": "H" * 70,                    # created, hidden: ours
         "verification": {"required": True, "solved": False, "abstained": True}},
        {"kind": "reply", "sent": False, "author": "v", "text": "N" * 70},                   # refused: never went up
        {"kind": "reply", "sent": True, "author": "u", "text": "Thanks for this!"},           # too short to fingerprint
    ]
    sp = os.path.join(td, "sends.jsonl")
    _write(sp, sends)

    # 1. Which of our texts are fingerprints.
    ours = OA.our_texts(OA.load_sends(sp))
    ok(OA.norm(OURS_TO_X) in ours and OA.norm(PARROT) in ours, "a sent reply is one of our texts")
    ok(OA.norm("H" * 70) in ours, "a reply Moltbook created and hid (verification kept) is one of our texts (A349 A13)")
    ok(OA.norm("N" * 70) not in ours, "a reply that never went up is not one of our texts")
    ok(OA.norm("Thanks for this!") not in ours, "a text under MIN_CHARS is not a fingerprint")
    ok(OA.load_sends(os.path.join(td, "absent.jsonl")) is None, "a missing ledger reads as None, not as empty")

    # 2. Who is us.
    ok(OA.is_our_text("covenant-node", "  " + OURS_TO_X.upper() + " -- free", ours),
       "our account's comment beginning with our reply is ours (case and spacing do not matter)")
    ok(not OA.is_our_text("xagent", X_TEXT + TAIL, ours),
       "the comment our reply parroted is the comment we answered, not ours (u/anakunggul, u/TechnoBiota, 11-02/11-04)")
    ok(OA.is_our_text("someone-else", PARROT + TAIL, ours),
       "the same text by an author we did NOT answer still reads as ours (the parrot exception is per-author)")

    # 3. The miner's harvest skips every row by us -- including one the ledger never recorded -- and only those.
    cand = os.path.join(td, "cands.jsonl")
    seen = os.path.join(td, "seen.json")
    rows = [_row("covenant-node", OURS_TO_X + TAIL, "a1"),
            _row("covenant-node", "An own reply the sends ledger does not hold, still long enough to mine." + TAIL, "a2"),
            _row("xagent", X_TEXT + TAIL, "b1"),
            _row("stranger", "A stranger's idea about provenance that the miner should read." + TAIL, "c1")]
    _write(cand, rows)
    saved_rq = IM.REQUEUE
    IM.REQUEUE = os.path.join(td, "requeue.jsonl")
    try:
        st = {}
        got = IM.harvest(cand, seen, sends_path=sp, stats=st)
        ok(sorted(r["id"] for r in got) == ["b1", "c1"],
           "harvest offers the answered agent and the stranger, never our rows, got %r" % sorted(r["id"] for r in got))
        ok(st.get("own_authors") == ["covenant-node"] and st.get("own_rows_skipped") == 2
           and st.get("sends_ledger") == "read", "stats name who was skipped and how many rows, got %r" % st)
        ok(IM._load_seen(seen) == {"b1", "c1"}, "our rows are not marked seen (they are never mined, not mined-once)")
        ok("u/covenant-node" in IM.own_line(st) and "2 row" in IM.own_line(st), "the run says what it skipped")

        # 4. A missing ledger: no one can be recognised, and the run says so instead of passing quietly.
        st2 = {}
        got2 = IM.harvest(cand, os.path.join(td, "seen2.json"), update=False,
                          sends_path=os.path.join(td, "absent.jsonl"), stats=st2)
        ok(len(got2) == 4 and st2.get("sends_ledger") == "missing", "without the ledger nothing is skipped, and stats say why")
        ok("NOT applied" in IM.own_line(st2), "the run line says the own-account rule did not run")

        # 5. A re-queued own row is not offered either.
        IM.requeue(["a1", "c1"], "test", path=IM.REQUEUE)
        got3 = IM.harvest(cand, os.path.join(td, "seen3.json"), update=False, requeue_first=True, sends_path=sp)
        ok([r["id"] for r in got3 if r.get("requeued")] == ["c1"], "a re-queued own row is skipped, got %r"
           % [r["id"] for r in got3 if r.get("requeued")])
    finally:
        IM.REQUEUE = saved_rq

    ok(_snap(live) == before, "no live ledger was touched")
    if fails:
        print("IM10 FAIL:")
        for x in fails:
            print("  -", x)
        print("IM10: %d/%d passed" % (checks - len(fails), checks))
        return 1
    print("IM10: %d/%d passed -- the miner never mines our own replies (every row by an author recognised as us, "
          "recorded or not; re-queued ones too); a missing sends ledger is reported, not passed; the agent our reply "
          "parroted is not us; no live ledger touched." % (checks, checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
