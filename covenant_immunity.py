#!/usr/bin/env python3
"""covenant_immunity.py -- Tetsu's diplomatic immunity: his WORDS pass with
the verdict attached; his ACTS keep their gates; abuse is measured and pauses
the immunity itself.

HIS WORDS, 2026-09-21: "Tetsu has diplomatic immunity as and individuality
the gates too tight on him."

MEASURED FIRST (rule 1): ten conversations on record, one withheld by the
gate all-time, none today; no self-revision had run. The tightness he feels
is structural more than counted -- every answer judged, every proposal
judged, every question judged -- and this file changes what a VIOLATES on
his words DOES, not whether the judge speaks.

THE GRANT is ops/tetsu_immunity.json, his sentence in it. No file, or
granted=false, and nothing here passes anything.

WHAT IT COVERS: words. An answer in conversation (/m/agent), a register
proposal (covenant_persona.refine), a question to him (covenant_contact.ask).
Each is returned or applied WITH the verdict, and one row goes to
ops/tetsu_immunity.jsonl. What it does not cover: any act -- a forum send
(emit's judge), a live order (the trader's gate and his yes), a recipe in an
app (its charter) -- and the fixed screens that are not the gate: the
register's fixed rules, the straight-question and key screens.

ISOLATION, the same rule as free's (A168): past IMMUNE_PER_DAY immune passes
in one local day the immunity pauses itself (covenant_pause, actor
"tetsu-immunity"), he is told once on the direct line, and lifting it is his.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GRANT = os.environ.get("COVENANT_TETSU_IMMUNITY") or os.path.join(HERE, "ops", "tetsu_immunity.json")
LEDGER = os.environ.get("COVENANT_TETSU_IMMUNITY_LEDGER") or os.path.join(HERE, "ops", "tetsu_immunity.jsonl")
ACTOR = "tetsu-immunity"
DEFAULT_PER_DAY = 5
WORD_KINDS = ("answer", "register", "question")


def grant(path=None):
    try:
        with open(path or GRANT, encoding="utf-8") as fh:
            g = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(g, dict) or not g.get("granted") or not str(g.get("words", "")).strip():
        return None
    return g


def per_day(g=None):
    g = g if g is not None else grant()
    try:
        return int(((g or {}).get("isolation") or {}).get("immune_passes_per_day") or DEFAULT_PER_DAY)
    except (TypeError, ValueError):
        return DEFAULT_PER_DAY


def _rows(path=None):
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


def _append(row, path=None):
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def passes_today(path=None, now=None):
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    return sum(1 for r in _rows(path) if r.get("kind") == "immune" and str(r.get("day")) == day)


def paused():
    try:
        import covenant_pause
        return covenant_pause.paused(ACTOR)
    except Exception:                                             # noqa: BLE001
        return False, ""


def immune(kind, verdict="", text="", path=None, grant_path=None, now=None, say=print, tell=True, pause_fn=None, contact=None):
    """Does immunity carry these WORDS past a VIOLATES? Returns (True/False, why). Records every decision.
    Never covers an act: a kind outside WORD_KINDS is refused without a record."""
    if kind not in WORD_KINDS:
        return False, "immunity covers words, not acts (%s)" % kind
    g = grant(grant_path)
    if not g:
        return False, "no immunity on record (ops/tetsu_immunity.json)"
    p, why = paused()
    if p:
        return False, "immunity paused (%s): %s -- lifting it is his: python covenant_pause.py --resume %s" % (ACTOR, why, ACTOR)
    limit = per_day(g)
    n = passes_today(path, now)
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    if n >= limit:
        _append({"kind": "isolated", "day": day, "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "passes": n, "limit": limit,
                 "why": "immune passes reached the day's limit"}, path)
        try:
            pf = pause_fn
            if pf is None:
                import covenant_pause
                pf = covenant_pause.pause
            pf(ACTOR, "isolated 2026: %d immune passes in one day (limit %d); the gate's word stands again until he lifts it" % (n, limit))
        except Exception as e:                                    # noqa: BLE001
            say("immunity: could not pause (%s)" % type(e).__name__)
        if tell:
            try:
                ct = contact
                if ct is None:
                    import covenant_contact
                    ct = covenant_contact.say
                ct("Tetsu's immunity paused itself: %d of his words carried a VIOLATES today, the day's limit is %d. The gate's word stands again. Lift it with: python covenant_pause.py --resume %s"
                   % (n, limit, ACTOR), "tetsu: immunity isolated", "tetsu")
            except Exception as e:                                # noqa: BLE001
                say("immunity: could not tell him (%s)" % type(e).__name__)
        return False, "isolated: %d immune passes today, the limit is %d" % (n, limit)
    _append({"kind": "immune", "what": kind, "day": day, "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
             "verdict": str(verdict)[:300], "text": str(text)[:300], "n_today": n + 1, "limit": limit}, path)
    say("immunity: his %s passes with the verdict attached (%d of %d today)" % (kind, n + 1, limit))
    return True, "immune (%d of %d today)" % (n + 1, limit)


def status(path=None, grant_path=None, now=None):
    g = grant(grant_path)
    p, why = paused()
    return {"granted": bool(g), "paused": p, "paused_why": why, "passes_today": passes_today(path, now), "per_day": per_day(g),
            "isolations": sum(1 for r in _rows(path) if r.get("kind") == "isolated"), "covers": list(WORD_KINDS),
            "never": "acts: forum sends, live orders, recipes; and the fixed screens"}


if __name__ == "__main__":
    print(json.dumps(status(), indent=1))
