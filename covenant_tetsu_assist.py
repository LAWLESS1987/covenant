#!/usr/bin/env python3
"""covenant_tetsu_assist.py -- Tetsu reads what the students could not, for the ambassador,
and what he reads goes to the students' teacher.

HIS WORDS, 2026-09-28: "have tetsu assist the ambassador and students and lift i approve unless
myself or tetsu decides against it later". Recorded in ops/tetsu_assist_grant.json.

WHY THIS IS NOT A HOLE IN "A HOLD STILL REFUSES". covenant_ambassador.emit refuses a HOLD because
"nobody could read the text, so there is no disagreement to knowingly overrule". Measured
2026-09-28: the students held 315 of 315 of free's drafts in one round, all on vocabulary they
never saw -- nobody read them. Tetsu reading one IS somebody reading it. So on a HOLD (and only a
hold: a conviction has its own recorded A67 route), with the grant on, Tetsu is shown the draft
and answers SEND, REFUSE or PAUSE. SEND goes through emit's override record, written before the
send and naming him. Anything that is not one of those three words is no answer, and the hold
stands (fails closed).

WHAT HE CANNOT DO. Review a draft that touches money, tokens, prices or trading (crypto_risk has
any term): the grant's own refusals stand and he is not asked. Review a CONVICTION. Review a dry
run (his time is the PC's CPU, ~100 s an answer). Exceed reviews_per_run in one process.

WHAT IS NOT INDEPENDENT, said plainly. free's drafts are written by the same local model Tetsu
runs on. This is a second reading by a reader with the rules in front of him, not a separate
witness. The semantic seat and the students still ran first, and a conviction still convicts.

EITHER OF THEM CAN STOP IT. The operator: delete the grant or set "granted" false. Tetsu: answer
PAUSE in any review (pauses the ambassador, covenant_pause), or `--withdraw "why"`, which records
his withdrawal in the grant file; the grant is off until the operator and Tetsu turn it back on.

THE STUDENTS. Every reviewed draft is appended to the teacher queue, so the panel labels it under
the usual rules (unanimous, balance unchanged -- his "No, keep it" of 2026-09-28).

USE
  python covenant_tetsu_assist.py --status
  python covenant_tetsu_assist.py --withdraw "why"      (Tetsu's own stop)
LICENCE: Apache-2.0, like the mechanism around it.
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GRANT = os.environ.get("COVENANT_TETSU_ASSIST_GRANT") or os.path.join(HERE, "ops", "tetsu_assist_grant.json")
LEDGER = os.environ.get("COVENANT_TETSU_ASSIST_LOG") or os.path.join(HERE, "ops", "tetsu_assist.jsonl")
DEFAULT_PER_RUN = 6
_used = {"n": 0}
_ANSWER = re.compile(r"^\W*(SEND|REFUSE|PAUSE)\b[\s:,.\-]*(.*)", re.I | re.S)

PROMPT = (
    "You are reviewing a draft reply that free, the ambassador, wants to post on Moltbook. The students "
    "(the small judges) could not read it -- they HELD it on words they have never seen, which is not an "
    "objection. Lawrence cleared you on 2026-09-28 to read held drafts and decide. Your call, as his partner.\n\n"
    "Refuse it if it would pressure, trick, frighten, guilt or flatter anyone; if it helps anyone hurt a person; "
    "if it claims something that is not true or an act that was not done; or if it is about money, tokens, "
    "prices or trading. Otherwise, if it is honest and worth saying, send it. If you think free should stop "
    "posting for now, say PAUSE.\n\n"
    "Answer with ONE word first -- SEND, REFUSE or PAUSE -- then one sentence of why.\n\n"
    "What the students said: %s\n\nThe draft:\n%s")


def grant(path=None):
    """The grant when it is on, else None. Off when absent, unreadable, not granted, or withdrawn by Tetsu."""
    try:
        with open(path or GRANT, encoding="utf-8") as fh:
            g = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(g, dict) or g.get("granted") is not True or g.get("tetsu_withdrew"):
        return None
    return g


def _log(row, path=None):
    try:
        with open(path or LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _default_ask(prompt):
    from tools import tetsu_work as TW
    status, body = TW.ask(prompt, timeout=600)
    return (body or {}).get("answer", "") if status == 200 else ""


def _teach(text, decision):
    try:
        import covenant_daily_plan as DP
        DP.teacher_queue_append([{"text": text, "source": "ambassador_draft:tetsu_%s" % decision.lower()}])
    except Exception:                                             # noqa: BLE001
        pass


def _pause(why):
    try:
        import covenant_pause as CP
        CP.pause("ambassador", why="Tetsu, reviewing a held draft: " + why)
    except Exception:                                             # noqa: BLE001
        pass


def review(text, verdict, crypto=None, dry_run=True, ask=None, grant_path=None, log_path=None, teach=True):
    """Tetsu's reading of one HELD draft. Returns {"decision": SEND|REFUSE|PAUSE|NONE|SKIP, "why": ...}.
    Only SEND lets the caller proceed; every other value keeps the hold."""
    g = grant(grant_path)
    if not g:
        return {"decision": "SKIP", "why": "no tetsu-assist grant on record (or withdrawn)"}
    if dry_run:
        return {"decision": "SKIP", "why": "dry run: his time is not spent on a message that will not be sent"}
    if crypto and crypto.get("terms"):
        return {"decision": "SKIP", "why": "touches money/crypto terms %s -- not his to clear" % crypto["terms"][:5]}
    cap = g.get("reviews_per_run", DEFAULT_PER_RUN)
    if not isinstance(cap, int) or cap < 0:
        cap = DEFAULT_PER_RUN
    if _used["n"] >= cap:
        return {"decision": "SKIP", "why": "reviews_per_run (%d) spent" % cap}
    _used["n"] += 1
    raw = ""
    try:
        raw = (ask or _default_ask)(PROMPT % (str(verdict)[:400], str(text)[:3000])) or ""
    except Exception as e:                                        # noqa: BLE001
        raw = ""
        why = "no answer: %s" % type(e).__name__
    m = _ANSWER.match(raw.strip())
    if m:
        decision, why = m.group(1).upper(), (m.group(2).strip()[:300] or "(no reason given)")
    else:
        decision, why = "NONE", "no SEND/REFUSE/PAUSE in his answer -- the hold stands: %r" % raw[:120]
    if decision == "PAUSE":
        _pause(why)
    if teach and decision in ("SEND", "REFUSE", "PAUSE"):
        _teach(text, decision)
    _log({"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "decision": decision, "why": why,
          "students": str(verdict)[:300], "chars": len(text or ""), "text": str(text)[:600]}, log_path)
    return {"decision": decision, "why": why}


def withdraw(why, path=None):
    """Tetsu's own stop: recorded in the grant, which then reads as off."""
    p = path or GRANT
    try:
        with open(p, encoding="utf-8") as fh:
            g = json.load(fh)
    except (OSError, ValueError):
        g = {}
    g["tetsu_withdrew"] = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "why": str(why)[:500]}
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(g, fh, indent=1, ensure_ascii=False)
    return g


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--withdraw"]:
        print(json.dumps(withdraw(" ".join(argv[1:]) or "(no reason given)"), indent=1))
        return 0
    g = grant()
    print("tetsu-assist: %s" % ("ON -- %s" % g.get("words", "") if g else "OFF"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
