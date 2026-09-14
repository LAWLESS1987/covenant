#!/usr/bin/env python3
"""covenant_actuator_learn.py -- what the phone's on-device "brain" (the
Accessibility actuator, phase 2, CovenantActuator.java + Recipe.java in the
private app repo) has learned, synced back to this PC.

The operator's ask, 2026-09-14: "the phone app should send back info to learn
from and learn itself." The phone already keeps everything locally
(files/recipes/*.json, files/actions.log); nothing about that changes -- this
just gives the PC its own copy, the same way daily_plan and phone_checkins
already do, so the record survives a lost phone and the operator (or this
assistant, in a session, never unattended) can look at what a recipe has
learned without touching the device.

WHAT ARRIVES. One recipe's summary per sync: its name, the app it runs in,
how many steps, the run history lines (outcome + timing, never the raw typed
text -- a slot's CONTENT is not sent, only that a slot exists), and
`last_answer` -- what the recipe read back from the screen when it finished,
capped at 6000 chars on the phone already. That last field is the actual
"info to learn from": an AI app's answer, a confirmation, whatever the
green-lit app showed. It goes through judge_learned_text() before it is kept,
for the same reason covenant_moltbook judges what arrives from outside this
machine: a payload from a different trust boundary should not be trusted
just because the channel authenticated the SENDER.

THE LEDGER. ops/actuator_learning.jsonl (gitignored), append-only, one row
per synced recipe, written after the signed request verifies and the content
judges clean. A row that failed judging is recorded too -- as a HELD or
REFUSED row with the reason, never silently dropped -- so a HELD/REFUSED sync
is visible the same way a refused sealed-mail block is.

Run:
  python covenant_actuator_learn.py --log [N]     the last N synced rows (default 20)
  python covenant_actuator_learn.py --explain      this, in the module's words
"""
import hashlib
import io
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.environ.get("COVENANT_ACTUATOR_LEDGER") or os.path.join(HERE, "ops", "actuator_learning.jsonl")
MAX_ANSWER_CHARS = 6000           # matches the phone's own cap; nothing bigger is trusted regardless
MAX_RUNS_KEPT = 40                # matches Recipe.save()'s own cap


def _sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def judge_learned_text(text):
    """(clean, reasons) for one recipe's last_answer -- the same secret/leak
    patterns covenant_ai_consult checks for the opposite direction (outbound
    to another AI app); the risk here is symmetric: a screen the phone read
    could just as easily have shown a key or a token as an AI app's answer.

    Deliberately NOT covenant_ai_consult._deterministic_check(): that
    function's length cap (MAX_QUESTION_CHARS, 2000) exists because an
    outbound QUESTION that long is itself suspicious -- a giant paste, not a
    question. A read-back ANSWER is expected to run longer (up to the
    phone's own 6000-char cap on Recipe.lastAnswer) and is not the thing
    being judged as a question, so the secret-pattern scan here runs over
    the FULL text, not a truncated head -- a first version of this function
    scanned only the first 2000 chars and a secret placed later slipped
    through untested until AL1.9 caught it. The theft/deception semantic
    quorum is asked over a bounded excerpt and logged as advisory, for the
    same measured reason as covenant_ai_consult.py (2026-09-14: that quorum
    has no useful opinion on ordinary text of this kind); it does not get a
    vote here either."""
    import covenant_ai_consult as AC
    t = text or ""
    hits = [p.pattern for p in AC._SECRET_PATTERNS if p.search(t)]
    if hits:
        reasons = ["refused: matches a secret/internal-data pattern (%d pattern(s), not shown), scanned all %d chars" % (len(hits), len(t))]
        clean = False
    else:
        reasons = ["deterministic check: clean (no secret pattern, all %d chars scanned)" % len(t)]
        clean = True
    reasons.append(AC._quorum_opinion(t[:2000]))
    return clean, reasons


def record_sync(body_bytes, who, path=None, now=None):
    """One phone's learning sync: {recipes: [{name, pkg, steps, slots, runs,
    last_answer}, ...]}. Returns (http_status, payload) in this project's
    usual route shape. Every recipe in the body gets its own ledger row,
    judged independently -- one bad recipe does not sink the others."""
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return 400, {"status": "error", "message": "body is not JSON"}
    if not isinstance(data, dict) or not isinstance(data.get("recipes"), list):
        return 400, {"status": "error", "message": "body must be {\"recipes\": [...]}"}
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kept, held_or_refused = [], []
    with open(path, "a", encoding="utf-8") as fh:
        for r in data["recipes"]:
            if not isinstance(r, dict) or not str(r.get("name", "")).strip():
                continue
            name = str(r.get("name", ""))[:200]
            pkg = str(r.get("pkg", ""))[:200]
            answer = str(r.get("last_answer", "") or "")[:MAX_ANSWER_CHARS]
            runs = [str(x)[:200] for x in (r.get("runs") or [])][-MAX_RUNS_KEPT:]
            clean, reasons = judge_learned_text(answer) if answer else (True, ["no last_answer to judge"])
            row = {
                "t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
                "at": round(now if now is not None else time.time(), 1),
                "signer": who,
                "recipe": name,
                "pkg": pkg,
                "steps": int(r.get("steps") or 0),
                "slots": int(r.get("slots") or 0),
                "runs": runs,
                "clean": bool(clean),
                "reasons": reasons,
                "last_answer": answer if clean else None,
                "last_answer_sha256": _sha(answer) if answer else None,
                "last_answer_chars": len(answer),
            }
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            (kept if clean else held_or_refused).append(name)
    return 200, {"status": "success", "recorded": len(kept) + len(held_or_refused),
                "kept": kept, "held_or_refused": held_or_refused}


def last_rows(path=None):
    out = []
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


EXPLAIN = __doc__.split("Run:")[0].strip()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="what the phone's actuator has learned, synced to this PC")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--log", nargs="?", const=20, type=int, metavar="N")
    g.add_argument("--explain", action="store_true")
    a = ap.parse_args(argv)
    if a.log is not None:
        rows = last_rows()
        for r in rows[-a.log:]:
            print(json.dumps(r))
        if not rows:
            print("(no actuator-learning sync yet)")
        return 0
    if a.explain:
        print(EXPLAIN)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
