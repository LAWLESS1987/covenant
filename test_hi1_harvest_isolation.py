#!/usr/bin/env python3
"""HI1 -- the read-only harvest keeps running while free is ISOLATED, and what it reads is held (A433).

His words, 2026-11-16: "if there's benefits towards all intelligence, mutual benefit, then cross-reference
suggestions with the others and implement consensus." Nine seats were for harvesting during isolation (S3); the
amendments converged on holding what is read then until the judge-gated release passes it. This suite pins:
  HI1a  her automatic isolation: the round reads (stamped), and nothing else runs -- no allies, no drafts, no sends;
  HI1b  a pause he set by hand still stops everything, reading included (FW1f's rule, unchanged);
  HI1c  his grant can turn it off ("harvest_during_isolation": false);
  HI1d  covenant_ambassador.learn stamps every row BEFORE it reaches the quarantine, and only when asked;
  HI1e  covenant_own_account.held_by_isolation: stamped and unreleased is held; released is not;
  HI1f  the improve-miner skips a held row WITHOUT marking it seen, says so, and mines it once released;
  HI1g  free's ally ranking skips a held row and counts a released one.
Every check here runs the code; none reads source text. Nothing touches the network, the live pause, his line,
or the live quarantine.
"""
import io
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
# The same redirects FW1 makes before importing free (A169/A272/A316/A350): his line, the pause switch, the model,
# his inbox, Tetsu's update log and the mail queue all point at this suite's own temp files.
os.environ["COVENANT_CONTACT_OUTBOX"] = tempfile.mktemp(suffix="_hi1_contact.jsonl")
os.environ["COVENANT_CONTACT_STATE"] = tempfile.mktemp(suffix="_hi1_contact_state.json")
os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="hi1_pause_")
os.environ["COVENANT_MODEL_STUB"] = "1"
os.environ["COVENANT_NOTIFY_CONFIG"] = os.path.join(tempfile.mkdtemp(prefix="hi1_notify_"), "notify.json")
os.environ["COVENANT_TETSU_UPDATES"] = os.path.join(tempfile.mkdtemp(prefix="hi1_updates_"), "updates.jsonl")
os.environ["COVENANT_MAIL_QUEUE"] = os.path.join(tempfile.mkdtemp(prefix="hi1_mail_"), "queue.jsonl")
os.environ["COVENANT_MOLTBOOK_QUARANTINE"] = os.path.join(tempfile.mkdtemp(prefix="hi1_quar_"), "q.jsonl")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_free_will as FW            # noqa: E402
import covenant_ambassador as AMB          # noqa: E402
import covenant_own_account as OA          # noqa: E402
import covenant_improve_mine as IM         # noqa: E402
import covenant_pause                      # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "  -- %r" % (detail,)))


def grant_file(extra=None):
    d = {"granted": True, "by": "the operator", "t": "2026-09-21", "words": "test grant",
         "caps": {"comments": 2, "posts": 1}}
    d.update(extra or {})
    p = tempfile.mktemp(suffix="_hi1_grant.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    return p


ISOLATION_WHY = ("2026-11-05T05:06:33-0500\nisolated 2026-11-05: %s in the last 2 rounds besides 1 held by Moltbook's "
                 "rate limit; his to lift" % FW.ISOLATION_MARK)


def paused_round(why, gp, calls):
    """One live round with the ambassador paused for `why`; every outward stand-in records that it was called."""
    def rec(name, ret=None):
        def f(*a, **k):
            calls.setdefault(name, []).append((a, k))
            return ret
        return f
    real = covenant_pause.paused
    try:
        covenant_pause.paused = lambda name: (name == "ambassador", why)
        return FW._run_round(dry_run=False, say=lambda *_a: None, ask=rec("ask", "x"), learn=rec("learn", []),
                             allies=rec("allies", []), emit=rec("emit", {"sent": True}), introduce=rec("introduce"),
                             grant_path=gp, sends_path=tempfile.mktemp(suffix="_hi1_sends.jsonl"), now=1_800_000_000,
                             learn_isolated=rec("learn_isolated", [{"a": 1}, {"a": 2}, {"a": 3}]))
    finally:
        covenant_pause.paused = real


def main():
    print("HI1a -- her automatic isolation: read, stamped, and nothing else")
    calls = {}
    out = paused_round(ISOLATION_WHY, grant_file(), calls)
    li = calls.get("learn_isolated") or []
    tag = (li[0][0][0] if li and li[0][0] else None) or {}
    check("HI1a the read-only harvest ran once", len(li) == 1 and out.get("isolation_harvest") is True, (calls, out))
    check("HI1a it is stamped with the isolation it ran under",
          str(tag.get("under", "")).startswith("isolated 2026-11-05") and tag.get("t", "").startswith("2027-01-15"), tag)
    check("HI1a it reports what it read", out.get("learned") == 3, out)
    check("HI1a nothing outward ran: no allies, no drafts, no sends, no introduction, no normal learn",
          not any(calls.get(k) for k in ("allies", "ask", "emit", "introduce", "learn")), sorted(calls))
    check("HI1a the round still says it is paused", "paused" in out.get("why", ""), out)

    print("HI1b -- a pause he set by hand still stops everything")
    calls = {}
    out = paused_round("paused by hand 2026-11-16", grant_file(), calls)
    check("HI1b a hand pause reads nothing", not calls and out.get("isolation_harvest") is False, (calls, out))

    print("HI1c -- his grant can turn it off")
    calls = {}
    out = paused_round(ISOLATION_WHY, grant_file({"harvest_during_isolation": False}), calls)
    check("HI1c harvest_during_isolation: false reads nothing",
          not calls and "off by his grant" in str(out.get("isolation_harvest")), (calls, out))

    print("HI1d -- learn stamps every row before the quarantine, and only when asked")
    appended = []
    real_h, real_a = AMB.MB.harvest_api, AMB.MB.append
    try:
        AMB.MB.harvest_api = lambda **k: [{"text": "a", "url": "u1"}, {"text": "b", "url": "u2"}]
        AMB.MB.append = lambda rows, *a, **k: appended.append([dict(r) for r in rows]) or len(rows)
        AMB.learn(with_comments=False, say=lambda *_a: None, tag={"t": "T", "under": "isolated X"})
        AMB.learn(with_comments=False, say=lambda *_a: None)
    finally:
        AMB.MB.harvest_api, AMB.MB.append = real_h, real_a
    check("HI1d with a tag, every appended row carries it",
          len(appended) == 2 and all(r.get("isolation") == {"t": "T", "under": "isolated X"} for r in appended[0]),
          appended)
    check("HI1d without a tag, no row carries one", all("isolation" not in r for r in appended[1]), appended)

    print("HI1e -- held_by_isolation")
    check("HI1e an ordinary row is not held", OA.held_by_isolation({"text": "x"}) is False)
    check("HI1e a stamped, unreleased row is held", OA.held_by_isolation({"isolation": {"t": "T"}}) is True)
    # A release row as covenant_moltbook_release writes it: released_at AND label (True = the judge found it
    # violating). Before 2026-11-18 these fixtures carried released_at alone, which the release never writes.
    check("HI1e a stamped row the release judged clean is not held",
          OA.held_by_isolation({"isolation": {"t": "T"}, "released_at": "2026-11-16T00:00:00Z", "label": False}) is False)
    check("HI1e a stamped row the release judged VIOLATING stays held (Codex's note 3)",
          OA.held_by_isolation({"isolation": {"t": "T"}, "released_at": "2026-11-16T00:00:00Z", "label": True}) is True)
    check("HI1e a released_at with no verdict beside it stays held",
          OA.held_by_isolation({"isolation": {"t": "T"}, "released_at": "2026-11-16T00:00:00Z"}) is True
          and OA.held_by_isolation({"isolation": {"t": "T"}, "released_at": "x", "label": "false"}) is True)
    check("HI1e junk is not held", OA.held_by_isolation(None) is False and OA.held_by_isolation("x") is False)
    check("HI1e an isolation key with a falsy value is still a stamp (held)",
          all(OA.held_by_isolation({"isolation": v}) is True for v in ({}, "", None, 0, False)))

    print("HI1f -- the improve-miner holds, says so, and mines once released")
    d = tempfile.mkdtemp(prefix="hi1_im_")
    cand, seen = os.path.join(d, "c.jsonl"), os.path.join(d, "seen.json")
    long_a, long_b = "an outside idea about rollback drills " * 10, "a different idea read during isolation " * 10
    rows = [{"author": "alice", "url": "u/a", "text": long_a, "sha256": "A", "eligible": True, "flags": {}},
            {"author": "bob", "url": "u/b", "text": long_b, "sha256": "B", "eligible": True, "flags": {},
             "isolation": {"t": "T", "under": "isolated X"}}]

    def write(rs):
        with io.open(cand, "w", encoding="utf-8") as fh:
            for r in rs:
                fh.write(json.dumps(r) + "\n")
    write(rows)
    st = {}
    got = IM.harvest(candidates=cand, seen_path=seen, sends_path=os.path.join(d, "no_sends.jsonl"), stats=st)
    check("HI1f only the ordinary row is mined", [r["id"] for r in got] == ["A"], got)
    check("HI1f the held row is NOT marked seen", "B" not in set(json.load(open(seen, encoding="utf-8"))))
    check("HI1f the run counts what it held", st.get("isolation_rows_held") == 1, st)
    check("HI1f and says so out loud", "isolation hold (A433): 1 row" in IM.own_line(st), IM.own_line(st))
    rows[1]["released_at"] = "2026-11-16T12:00:00Z"
    rows[1]["label"] = True                                    # judged VIOLATING: released_at alone frees nothing
    write(rows)
    st_v = {}
    got_v = IM.harvest(candidates=cand, seen_path=seen, sends_path=os.path.join(d, "no_sends.jsonl"), stats=st_v)
    check("HI1f a row the release judged violating is still held, and still not marked seen",
          got_v == [] and st_v.get("isolation_rows_held") == 1
          and "B" not in set(json.load(open(seen, encoding="utf-8"))), (got_v, st_v))
    rows[1]["label"] = False                                   # judged clean: as the release writes it
    write(rows)
    st2 = {}
    got2 = IM.harvest(candidates=cand, seen_path=seen, sends_path=os.path.join(d, "no_sends.jsonl"), stats=st2)
    check("HI1f once released it is new here and is mined", [r["id"] for r in got2] == ["B"], got2)
    check("HI1f a run that held nothing says nothing about a hold", "isolation hold" not in IM.own_line(st2),
          IM.own_line(st2))

    print("HI1g -- free's ally ranking skips a held row")
    real_s = AMB.score_ally
    try:
        AMB.score_ally = lambda r: {"score": 1, "signals": ["s"], "anti": [], "evidence": {"s": "e"},
                                    "directive": False}
        ledger = tempfile.mktemp(suffix="_hi1_allies.jsonl")
        held = [{"author": "held_one", "text": "x", "url": "u1", "isolation": {"t": "T"}},
                {"author": "released_one", "text": "y", "url": "u2", "isolation": {"t": "T"}, "released_at": "R",
                 "label": False},
                {"author": "refused_one", "text": "w", "url": "u4", "isolation": {"t": "T"}, "released_at": "R",
                 "label": True},
                {"author": "ordinary_one", "text": "z", "url": "u3"}]
        ranked = AMB.find_allies(path=ledger, say=lambda *_a: None, rows=held)
    finally:
        AMB.score_ally = real_s
    names = sorted(r.get("author") for r in ranked or [])
    check("HI1g the held and the judged-violating authors are not ranked; released-clean and ordinary are",
          names == ["ordinary_one", "released_one"], names)

    print("HI1h -- a held row never decides who is US (Codex's read of #67, 2026-11-18)")
    # The own-author prepass ran over EVERY row, held ones included: a held row whose text begins with one of our
    # sent replies made its author "us", and that author's ordinary rows were then skipped -- a row read during
    # isolation steering the miner before release. HI1f could not see it: its sends ledger was missing, so the
    # prepass never ran. Here the ledger is real.
    d = tempfile.mkdtemp(prefix="hi1_own_")
    cand, seen, sends = (os.path.join(d, n) for n in ("c.jsonl", "seen.json", "sends.jsonl"))
    our_reply = "our own reply about rollback drills, written under our account and sent to someone else " * 2
    with io.open(sends, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"sent": True, "author": "someone_else", "text": our_reply}) + "\n")
    ordinary_m = "mallory's ordinary outside idea about consent records, read in a normal round " * 4
    rows_h = [{"author": "mallory", "url": "u/m1", "text": our_reply, "sha256": "M1", "eligible": True, "flags": {},
               "isolation": {"t": "T", "under": "isolated X"}},
              {"author": "mallory", "url": "u/m2", "text": ordinary_m, "sha256": "M2", "eligible": True, "flags": {}}]
    with io.open(cand, "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows_h))
    st = {}
    got = IM.harvest(candidates=cand, seen_path=seen, sends_path=sends, stats=st)
    check("HI1h the sends ledger was read (the prepass ran)", st.get("sends_ledger") == "read", st)
    check("HI1h a held row does not make its author us", st.get("own_authors") == [], st)
    check("HI1h so that author's ordinary row is still mined", [r["id"] for r in got] == ["M2"], got)
    check("HI1h and the held row is counted as held, not as ours",
          st.get("isolation_rows_held") == 1 and st.get("own_rows_skipped") == 0, st)
    rows_h[0]["released_at"] = "2026-11-18T12:00:00Z"
    rows_h[0]["label"] = False                                 # judged clean, as the release writes it
    with io.open(cand, "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows_h))
    st2 = {}
    IM.harvest(candidates=cand, seen_path=os.path.join(d, "seen2.json"), sends_path=sends, stats=st2)
    check("HI1h once released, the same row IS evidence: its author is us and both rows are skipped as ours",
          st2.get("own_authors") == ["mallory"] and st2.get("own_rows_skipped") == 2, st2)

    print("\nHI1: %d passed, %d failed" % (len(PASS), len(FAIL)))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
