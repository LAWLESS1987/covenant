#!/usr/bin/env python3
"""covenant_refine_loop.py -- Tetsu refines himself CONSTANTLY, not once a night:
one pass an hour, and only when he has talked with someone since the last one.

HIS WORDS, 2026-09-21: "refine both constantly". Both are the register and
voice Tetsu revises (covenant_persona.refine, A174) and the PC that speaks
with the same register by construction (A189); the student judge's own
refinement runs in its own loop already (covenant_refine_check, A127).

WHAT GATES A PASS, measured, never guessed:
  1. at least REFINE_EVERY_S seconds since the last pass (ops/refine_loop_state.json);
  2. at least one NEW row of HIS words in the ask log since the last pass (a
     conversation row covenant_persona.is_his_word holds -- the rows a pass is
     shown; A349 B3) -- a refinement with nothing new to read would revise from
     the same evidence twice;
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


def conversation_counts(ask_log=None):
    """(rows, his): the conversation rows the ask log holds (agent or council), and how many of them are HIS words
    (covenant_persona.is_his_word, the rows a pass is shown). Counted, not assumed (A349 B3)."""
    import covenant_persona
    n = his = 0
    try:
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("kind") in ("agent", "council"):
                    n += 1
                    his += bool(covenant_persona.is_his_word(r))
    except OSError:
        return 0, 0
    return n, his


def conversation_rows(ask_log=None):
    """How many conversation rows the ask log holds (agent or council), counted, not assumed."""
    return conversation_counts(ask_log)[0]


def tick(now=None, refine=None, ask=None, state_path=None, ask_log=None, say=print, every=REFINE_EVERY_S):
    """One watchdog round. Returns a dict: ran (bool), why, and the pass's summary when it ran."""
    now = time.time() if now is None else float(now)
    st = _state(state_path)
    last_t = float(st.get("last_t") or 0)
    # A349 B3 (his answer, 2026-10-14: AGREE): only HIS words are new conversation. The gate counted every agent or
    # council row, and only 210 of the 1,759 were his words, the rest never shown to a pass: 50 of 62 passes after
    # A314 ran with no new word of his. The count of his words is kept under its own name (last_his_rows); last_rows
    # still counts every conversation row, a different unit. A state written before A349 has no last_his_rows, so
    # its first pass after the hour counts his words from 0.
    last_his = int(st.get("last_his_rows") or 0)
    n, his = conversation_counts(ask_log)
    out = {"ran": False, "why": "", "rows": n, "his_rows": his, "new_rows": max(0, his - last_his),
           "since_last_s": (now - last_t) if last_t else None}
    if last_t and now - last_t < every:
        out["why"] = "last pass %.0f min ago; next after %d min" % ((now - last_t) / 60.0, every // 60)
        return out
    if his <= last_his:
        out["why"] = "no new conversation since the last pass (%d rows of his words, %d conversation rows in all)" % (his, n)
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
        st.update(last_t=now, last_rows=n, last_his_rows=his, last_why=out["why"])
        _save(st, state_path)
        return out
    out.update(ran=True, why="refined on %d new row(s) of his words" % out["new_rows"], result={k: res.get(k) for k in ("proposed", "applied", "why")})
    st.update(last_t=now, last_rows=n, last_his_rows=his, last_why=out["why"], passes=int(st.get("passes") or 0) + 1)
    _save(st, state_path)
    say("refine loop: %s -- %s" % (out["why"], res.get("why", "")))
    return out


if __name__ == "__main__":
    print(json.dumps(tick(), indent=1))
