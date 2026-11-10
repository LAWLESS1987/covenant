#!/usr/bin/env python3
"""FW2 -- every attempt records how many covenant refusals came before it; a target refused N times CAN be retired,
OFF by default (Tetsu was asked 2026-11-04 and said NO; ops/TETSU_CONSENT_H1_2026-11-04.json) and switched on only by
a number in the grant. Offline: stubbed emit/model/forum, temp grant and ledger, live pause and live ledgers
untouched (snapshotted).

Why (A409 H1, 2026-11-04). Rotation keys on the author for 24 h and only a SENT reply marks a target done, so a
comment the judge refused came back the next day for a fresh draft without limit: 1,549 targets refused at least
once, up to 14 times; 27 sent after a refusal, 21 of them after ONE. A refusal is a signal (one re-draft may outlive a
false conviction); two refusals of the same target are two drafts judged against mutual benefit -- Claude proposed
retiring it there. Tetsu's NO stands, so the default is never; his and the operator's number in the grant decides.

Both ways: by default a twice-refused target is still drafted (and shows prior_refusals 2); with the grant at 2 it is
retired at the threshold / attempted below it; a no-view hold and Moltbook's rate limit never count as a
refusal; the grant's number wins (null = never retire; 1 = retire after one); dry-run refusals never count.
Blind spot (rule 9): a target is keyed by comment id (else author+post); a refusal recorded under a different url
form for the same comment would not be joined.
"""
import hashlib, io, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_free_will as FW
import covenant_pause

R = []


def check(name, cond, detail=None):
    R.append(bool(cond))
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  -- %r" % (detail,)))


def ally(author, url):
    return {"author": author, "ally_score": 3, "anti": [], "best_url": url, "best_signals": ["publishes-failure"],
            "evidence": {"publishes-failure": "we publish the cases where our own check was wrong"}}


A = ally("alpha", "https://www.moltbook.com/post/aaaaaaaa-1111#comment-cccccccc-1111")
B = ally("beta", "https://www.moltbook.com/post/bbbbbbbb-2222#comment-dddddddd-2222")
C = ally("gamma", "https://www.moltbook.com/post/cccccccc-3333#comment-eeeeeeee-3333")
REF = "refused by covenant's judge: quorum=violates"


def hist(author, post, comment, why, n, dry=False):
    return [{"kind": "reply", "author": author, "post_id": post, "comment_id": comment, "sent": False,
             "dry_run": dry, "why": why, "t": "2026-11-01T00:00:00Z", "at": 1.0} for _ in range(n)]


def _snap(paths):
    return {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in paths if os.path.exists(p)}


def main():
    print("FW2 -- refused twice -> retired; one re-draft stays; prior refusals recorded")
    # ---- unit ----
    rows = (hist("alpha", "aaaaaaaa-1111", "cccccccc-1111", REF, 2) + hist("beta", "bbbbbbbb-2222", "dddddddd-2222", REF, 1)
            + hist("gamma", "cccccccc-3333", "eeeeeeee-3333", "held by covenant's judge (no view -- not an objection", 5)
            + hist("gamma", "cccccccc-3333", "eeeeeeee-3333", "HELD by Moltbook's own rate limit", 3)
            + hist("gamma", "cccccccc-3333", "eeeeeeee-3333", REF, 4, dry=True))
    rc = FW.refusal_counts(rows)
    check("FW2.1 refusals are counted per target", rc == {"cccccccc-1111": 2, "dddddddd-2222": 1}, rc)
    check("FW2.2 a no-view hold, Moltbook's rate limit and a DRY-run refusal never count", "eeeeeeee-3333" not in rc, rc)
    # Tetsu was asked and said NO (2026-11-04): with no number in the grant, nothing is retired.
    check("FW2.3 default = never retire (Tetsu's NO)", FW.retire_after({}) is None)
    check("FW2.4 the grant's number wins; null there = never retire",
          FW.retire_after({"refusals_retire_after": 1}) == 1 and FW.retire_after({"refusals_retire_after": None}) is None)

    # ---- one live round, stubbed, over that history ----
    live = [os.path.join(HERE, "ops", x) for x in ("ambassador_sends.jsonl", "contact_outbox.jsonl",
                                                    "tetsu_moltbook_updates.jsonl")]
    before = _snap(live)
    real_paused, real_pause = covenant_pause.paused, covenant_pause.pause
    covenant_pause.paused = lambda name: (False, "") if name == "ambassador" else real_paused(name)
    covenant_pause.pause = lambda name, why="": None
    try:
        def run(grant_extra, read=(), allies_rows=(A, B, C)):
            td = tempfile.mkdtemp(prefix="fw2_")
            gp, sp = os.path.join(td, "grant.json"), os.path.join(td, "sends.jsonl")
            with io.open(gp, "w", encoding="utf-8") as fh:
                json.dump({"granted": True, "words": "test", "caps": {"comments": None, "posts": 0}, "free_rein": bool(read),
                           **grant_extra}, fh)
            with io.open(sp, "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
            emitted = []

            def emit(text, post_id=None, parent_id=None, submolt=None, dry_run=True, **kw):
                emitted.append(parent_id)
                return {"sent": True, "judged": "clean", "why": ""}

            ask = lambda msgs, max_tokens=0: (("I recognise what you wrote about publishing the cases where your own "  # noqa: E731
                                               "check was wrong; ") * 3 + "when our judges cannot agree, a hold fails "
                                              "closed. How do you find out later?", {"model": "stub"})
            out = FW.run_round(dry_run=False, say=lambda *a: None, ask=ask, learn=lambda: list(read), allies=lambda: list(allies_rows),
                               emit=emit, introduce=lambda **kw: {"sent": False, "why": "off"}, grant_path=gp,
                               sends_path=sp, now=10 ** 9, count_comments=lambda p, a: 0)
            return out, emitted, [r for r in FW.sends(sp) if r.get("kind") == "reply" and r.get("sent")]

        out0, emitted0, sent0 = run({})
        check("FW2.3b by default (Tetsu's NO) alpha, refused twice, IS drafted, and its row shows 2 prior refusals",
              "cccccccc-1111" in emitted0 and {r.get("comment_id"): r.get("prior_refusals") for r in sent0}
              .get("cccccccc-1111") == 2 and out0.get("retired_targets") == 0, (emitted0, out0.get("retired_targets")))
        out, emitted, sent = run({"refusals_retire_after": 2})          # switched on, as the grant would
        check("FW2.5 refused twice -> retired: alpha is not drafted again", "cccccccc-1111" not in emitted, emitted)
        check("FW2.6 refused once -> one re-draft stays: beta is attempted", "dddddddd-2222" in emitted, emitted)
        check("FW2.7 holds are not refusals: gamma (5 no-view, 3 rate, 4 dry refusals) is attempted",
              "eeeeeeee-3333" in emitted, emitted)
        pr = {r.get("comment_id"): r.get("prior_refusals") for r in sent}
        check("FW2.8 every attempt records its prior refusals (beta 1, gamma 0)",
              pr.get("dddddddd-2222") == 1 and pr.get("eeeeeeee-3333") == 0, pr)
        check("FW2.9 the round reports how many targets are retired", out.get("retired_targets") == 1, out)

        out, emitted, _ = run({"refusals_retire_after": None})
        check("FW2.10 control: his null in the grant = never retire -> alpha is drafted", "cccccccc-1111" in emitted,
              emitted)
        out, emitted, _ = run({"refusals_retire_after": 1})
        check("FW2.11 his 1 in the grant retires after one -> beta is not drafted either",
              "dddddddd-2222" not in emitted and "cccccccc-1111" not in emitted, emitted)
        omega = {"author": "omega", "url": "https://www.moltbook.com/post/aaaaaaaa-1111#comment-cccccccc-1111",
                 "text": "a comment read today, on the target the judge refused twice", "flags": {}}
        out, emitted, _ = run({"refusals_retire_after": 2}, read=[omega], allies_rows=())
        check("FW2.13 free rein (anyone read today) also skips a retired target", "cccccccc-1111" not in emitted, emitted)
    finally:
        covenant_pause.paused, covenant_pause.pause = real_paused, real_pause
    check("FW2.12 no live ledger written", _snap(live) == before)

    ok = sum(R)
    print("\nFW2: %d/%d passed" % (ok, len(R)))
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
