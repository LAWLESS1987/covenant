#!/usr/bin/env python3
"""tools/replay_challenges.py -- replay every kept Moltbook challenge text through the solver in this tree.

WHY (A334, 2026-10-11). A333 changed covenant_ambassador.solve_challenge, and its coverage on the challenges
actually met was UNDETERMINED: 43 rows on record (8 solved, 30 abstained, 5 unsolved) and none could be replayed,
because covenant_free_will._ver kept the outcome and not the text. _ver keeps the text now (first 400
characters). This replays what is kept and sets each reading beside the outcome on record.

    python tools/replay_challenges.py                 the ledger at covenant_free_will.SENDS
    python tools/replay_challenges.py --sends PATH    another ledger
    python tools/replay_challenges.py --json          one JSON object instead of lines

THE UNIT is a ledger row whose `verification` says required, as the ledger recorded it. Not a post: several
replies under one post are several rows. Not always a distinct challenge either: a hand answer written as its
own row (kind "verify") repeats the challenge its create row abstained on. On 2026-10-11 the 18:05:08Z
own_post (abstained) and the 18:05:30Z verify (49.00) are one challenge in two rows, so the 43 rows of A333
are at most 42 challenges.

WHAT IT CANNOT SEE.
  * A row with no kept text is UNDETERMINED, never replayed. solve_challenge("") abstains, and an abstention
    printed for a row nobody can replay would read as a measurement. Every row before A334 is one of these.
  * Correctness is known only where Moltbook accepted an answer (recorded solved). Where the replay answers a
    challenge that was abstained or not solved, whether that answer is right is UNDETERMINED.
  * Only challenges that reached the ledger through _ver: free's replies, introductions and own posts.
    Tetsu's forum sends (covenant_tetsu_forum.say) keep no verification, and a hand emit or a hand
    `covenant_ambassador.py --verify` records only what the person writes down.
  * A text cut at 400 characters replays as cut.

It never touches the network: solve_challenge is pure, and nothing is submitted or answered.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

UNDETERMINED = "UNDETERMINED"


def _recorded(v):
    """('solved'|'abstained'|'unsolved', the answer on record or None)."""
    if v.get("solved"):
        return "solved", v.get("answer")
    if v.get("abstained"):
        return "abstained", None
    return "unsolved", v.get("answer")


def replay(rows, solve=None):
    """One result per row whose verification says required, in ledger order, and the counts."""
    if solve is None:
        import covenant_ambassador
        solve = covenant_ambassador.solve_challenge
    out = []
    for r in rows or []:
        v = r.get("verification")
        if not isinstance(v, dict) or not v.get("required"):
            continue
        rec, rec_answer = _recorded(v)
        item = {"t": r.get("t"), "kind": r.get("kind"), "author": r.get("author"), "recorded": rec,
                "recorded_answer": rec_answer}
        text = v.get("challenge_text")
        if not text:
            item.update(replay=None, verdict=UNDETERMINED, why="no challenge text was kept for this row")
            out.append(item)
            continue
        answer, why = solve(text)
        item.update(text=text, replay=answer, replay_why=why)
        if rec == "solved":
            if answer is None:
                item["verdict"] = "abstains where %s was accepted" % rec_answer
            elif rec_answer is not None and answer == rec_answer:
                item["verdict"] = "same as the accepted answer"
            elif rec_answer is None:
                item["verdict"] = "answers %s; the accepted answer was not kept" % answer
            else:
                item["verdict"] = "WRONG: answers %s where %s was accepted" % (answer, rec_answer)
        elif rec == "unsolved":
            if answer is None:
                item["verdict"] = "abstains where %s was not solved" % (rec_answer or "an answer not kept")
            elif answer == rec_answer:
                item["verdict"] = "same answer, which was not solved"
            else:
                item["verdict"] = ("answers %s where %s was not solved; whether %s is right is %s"
                                   % (answer, rec_answer or "an answer not kept", answer, UNDETERMINED))
        else:
            item["verdict"] = ("still abstains" if answer is None else
                               "answers %s where it abstained; whether that is right is %s" % (answer, UNDETERMINED))
        out.append(item)
    replayed = [i for i in out if i["verdict"] != UNDETERMINED]
    counts = {"required_rows": len(out), "with_text": len(replayed), "undetermined": len(out) - len(replayed),
              "replay_answered": sum(1 for i in replayed if i["replay"] is not None),
              "replay_abstained": sum(1 for i in replayed if i["replay"] is None),
              "same_as_accepted": sum(1 for i in replayed if i["verdict"] == "same as the accepted answer"),
              "wrong_against_accepted": sum(1 for i in replayed if i["verdict"].startswith("WRONG")),
              "abstains_where_accepted": sum(1 for i in replayed if i["verdict"].startswith("abstains where")
                                             and i["recorded"] == "solved"),
              "newly_answered_correctness_undetermined": sum(1 for i in replayed if i["recorded"] != "solved"
                                                             and i["replay"] is not None
                                                             and i["verdict"] != "same answer, which was not solved")}
    return {"rows": out, "counts": counts}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sends", help="the sends ledger (default: covenant_free_will.SENDS)")
    ap.add_argument("--json", action="store_true", help="print one JSON object")
    a = ap.parse_args(argv)
    import covenant_free_will as FW
    path = a.sends or FW.SENDS
    if not os.path.exists(path):
        print("no ledger at %s -- nothing replayed, and nothing is known about it" % path)
        return 2
    res = replay(FW.sends(path))
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    for i in res["rows"]:
        print("%s %-8s u/%-20s recorded %-9s %-6s -> %s" % (
            i["t"], i["kind"], str(i["author"])[:20], i["recorded"], i["recorded_answer"] or "",
            i["verdict"] if i["verdict"] == UNDETERMINED else "%s: %s" % (i["replay"] or "abstain", i["verdict"])))
    c = res["counts"]
    print()
    print("ledger: %s" % path)
    print("rows whose verification says required: %d; with kept text: %d; %s (no text): %d"
          % (c["required_rows"], c["with_text"], UNDETERMINED, c["undetermined"]))
    print("replayed: answered %d, abstained %d. Against an accepted answer: same %d, WRONG %d, abstains %d. "
          "Newly answered, correctness %s: %d"
          % (c["replay_answered"], c["replay_abstained"], c["same_as_accepted"], c["wrong_against_accepted"],
             c["abstains_where_accepted"], UNDETERMINED, c["newly_answered_correctness_undetermined"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
