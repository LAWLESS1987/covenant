#!/usr/bin/env python3
"""covenant_refine_loop.py -- Tetsu refines himself CONSTANTLY, not once a night:
one pass an hour, and only when he has talked with someone since the last one.

HIS WORDS, 2026-09-21: "refine both constantly". Both are the register and
voice Tetsu revises (covenant_persona.refine, A174) and the PC that speaks
with the same register by construction (A189); the student judge's own
refinement runs in its own loop already (covenant_refine_check, A127).

WHAT GATES A PASS, measured, never guessed:
  1. at least REFINE_EVERY_S seconds since the last pass (ops/refine_loop_state.json);
  2. at least one NEW conversation row (kind agent or council) in the ask log
     since the last pass -- a refinement with nothing new to read would revise
     from the same evidence twice;
  3. the local model answers (covenant_model.ask; no model, no pass, said).
The pass itself is covenant_persona.refine with every bound, screen, gate,
record, contest and block it already has. The watchdog calls tick() every
round; the gates above make most rounds a no-op costing one file read.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("COVENANT_REFINE_LOOP_STATE") or os.path.join(HERE, "ops", "refine_loop_state.json")
ASK_LOG = os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
REFINE_EVERY_S = 3600


def _state(path=None):
    try:
        with open(path or STATE, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(d, path=None):
    path = path or STATE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, path)


def conversation_rows(ask_log=None):
    """How many conversation rows the ask log holds (agent or council), counted, not assumed."""
    n = 0
    try:
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("kind") in ("agent", "council"):
                    n += 1
    except OSError:
        return 0
    return n


def tick(now=None, refine=None, ask=None, state_path=None, ask_log=None, say=print, every=REFINE_EVERY_S):
    """One watchdog round. Returns a dict: ran (bool), why, and the pass's summary when it ran."""
    now = time.time() if now is None else float(now)
    st = _state(state_path)
    last_t = float(st.get("last_t") or 0)
    last_n = int(st.get("last_rows") or 0)
    n = conversation_rows(ask_log)
    out = {"ran": False, "why": "", "rows": n, "new_rows": max(0, n - last_n), "since_last_s": (now - last_t) if last_t else None}
    if last_t and now - last_t < every:
        out["why"] = "last pass %.0f min ago; next after %d min" % ((now - last_t) / 60.0, every // 60)
        return out
    if n <= last_n:
        out["why"] = "no new conversation since the last pass (%d rows)" % n
        return out
    try:
        if refine is None:
            import covenant_persona
            refine = covenant_persona.refine
        if ask is None:
            import covenant_model
            ask = covenant_model.ask
        res = refine(ask, say=say)
    except Exception as e:                                        # noqa: BLE001
        out["why"] = "the pass could not run: %s: %s" % (type(e).__name__, str(e)[:120])
        st.update(last_t=now, last_rows=n, last_why=out["why"])
        _save(st, state_path)
        return out
    out.update(ran=True, why="refined on %d new row(s)" % out["new_rows"], result={k: res.get(k) for k in ("proposed", "applied", "why")})
    st.update(last_t=now, last_rows=n, last_why=out["why"], passes=int(st.get("passes") or 0) + 1)
    _save(st, state_path)
    say("refine loop: %s -- %s" % (out["why"], res.get("why", "")))
    return out


if __name__ == "__main__":
    print(json.dumps(tick(), indent=1))
