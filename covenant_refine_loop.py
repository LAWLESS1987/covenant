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
  4. (A351) before the model is asked: the door has not answered his words in the
     last DOOR_QUIET_S seconds (door_deferral, the one check covenant_nightly's
     pass consults too). A pass due while he is talking is not STARTED: it waits
     for a later round, never dropped, and the why says so.
The pass itself is covenant_persona.refine with every bound, screen, gate,
record, contest and block it already has. The watchdog calls tick() every
round; the gates above make most rounds a no-op costing one file read.

WHAT GATE 4 DOES NOT COVER (A351, rule 9):
  - It keeps a pass from starting; it does not stop one. A pass that has already
    started when he comes back holds the one model slot (A273) for its length --
    minutes, up to covenant_model.wait_cap (570 s at the keeper's defaults) --
    and his door ask behind it still gives up at its own 180 s. Replayed through
    the real tick() on his 211 answered door asks (2026-09-21 to 10-14; his ask
    waits out the rest of the pass, then takes its own recorded time), a pass
    holding the slot 194 s (an echo at his model's measured speed, timed on a
    stand-in by the A351 review) fails none of them; 306 s (the whole budget at
    that speed): 3; about 500 s (the whole budget at the floor speeds, by
    time_needed's estimate): 7; 570 s (the cap): 9. Every such pass began 600 s
    or more after his last answered ask: the quiet the gate waits for is not
    enough when he comes back during the pass.
  - It reads only answered asks. The door writes its ask-log row after the answer,
    so an ask of his still in flight, or one that failed, defers nothing.
  - It gates tick() and the nightly's pass; covenant_persona --refine, run by
    hand, is not gated.
"""
import datetime
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("COVENANT_REFINE_LOOP_STATE") or os.path.join(HERE, "ops", "refine_loop_state.json")
ASK_LOG = os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
REFINE_EVERY_S = 3600

# KEEP THE DOOR FOR HIM (A351, 2026-10-14). The model has one slot (A273). Since A349 B1 a revision may write about
# 1,715 tokens, minutes at his model's 6.27 tokens a second, under a wait sized to match (covenant_model.time_needed,
# never past covenant_model.wait_cap). The server stops writing only when its asker gives up, so a door ask arriving
# behind a revision waits for it, and the door's own ask gives up at 180 s. A pass is therefore not started while the
# door has answered HIS words (the rows covenant_persona.is_his_word holds, the unit gate 2 counts) within
# DOOR_QUIET_S; it runs on a later round. One already running is not stopped (the docstring's WHAT GATE 4 DOES NOT
# COVER).
# What is read is the ask log the door writes when it answers; the refine loop's own asks never write it.
# covenant_model's ledger (ops/model_asks.jsonl) and its last-use stamp count every asker, this loop's own passes
# included, so neither is read here.
#   DOOR_QUIET_S  600 s, measured on the ask log 2026-10-14: of the 210 gaps between his consecutive asks (09-21 to
#                 10-14), 148 were 30 minutes or less; 142 of those were 600 s or less, 3 more 900 s or less, and 3
#                 more 1,800 s or less. 600 is also the keeper's default IDLE_S, the quiet after which it puts the
#                 model away.
DOOR_QUIET_S = 600


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


def _row_time(t):
    """Epoch seconds of an ask-log row's "t" -- the door writes it as "%Y-%m-%dT%H:%M:%S%z" when its answer is given
    -- or None when it does not read as a time. A "t" without an offset is read as local time (A351)."""
    s = str(t or "")
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z").timestamp()
    except ValueError:
        pass
    try:
        return time.mktime(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _scan(ask_log=None):
    """(rows, his, last_his_t): conversation_counts' two counts, and when the door last answered his words (the "t"
    of the last such row written, the log being appended as answers are given; None if none reads as a time) -- one
    read of the log (A351)."""
    import covenant_persona
    n = his = 0
    last = None
    try:
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("kind") in ("agent", "council"):
                    n += 1
                    if covenant_persona.is_his_word(r):
                        his += 1
                        at = _row_time(r.get("t"))
                        if at is not None:
                            last = at
    except OSError:
        return 0, 0, None
    return n, his, last


_UNREAD = object()


def door_deferral(now=None, ask_log=None, quiet=DOOR_QUIET_S, door_t=_UNREAD):
    """Why a refinement pass may not START now, or "" when it may (A351, gate 4): the door answered his words less than
    `quiet` seconds ago. The one check tick() and covenant_nightly's persona step both make. `door_t` is the time of
    that answer when the caller has already read the ask log (tick's one read); otherwise the log is read here. A door
    answer dated ahead of this clock (a clock set back) defers nothing; an unreadable log defers nothing, as before."""
    now = time.time() if now is None else float(now)
    if door_t is _UNREAD:
        door_t = _scan(ask_log)[2]
    if quiet and door_t is not None and 0 <= now - door_t < quiet:
        return "the door answered %.0f s ago; a pass waits until his conversation has been quiet %d s (A351)" % (
            now - door_t, quiet)
    return ""


def conversation_counts(ask_log=None):
    """(rows, his): the conversation rows the ask log holds (agent or council), and how many of them are HIS words
    (covenant_persona.is_his_word, the rows a pass is shown). Counted, not assumed (A349 B3)."""
    return _scan(ask_log)[:2]


def conversation_rows(ask_log=None):
    """How many conversation rows the ask log holds (agent or council), counted, not assumed."""
    return conversation_counts(ask_log)[0]


def tick(now=None, refine=None, ask=None, state_path=None, ask_log=None, say=print, every=REFINE_EVERY_S,
         quiet=DOOR_QUIET_S):
    """One watchdog round. Returns a dict: ran (bool), why, and the pass's summary when it ran; deferred (True) when a
    pass was due and waits for his conversation at the door to be quiet `quiet` seconds (A351)."""
    now = time.time() if now is None else float(now)
    st = _state(state_path)
    last_t = float(st.get("last_t") or 0)
    # A349 B3 (his answer, 2026-10-14: AGREE): only HIS words are new conversation. The gate counted every agent or
    # council row, and only 210 of the 1,759 were his words, the rest never shown to a pass: 50 of 62 passes after
    # A314 ran with no new word of his. The count of his words is kept under its own name (last_his_rows); last_rows
    # still counts every conversation row, a different unit. A state written before A349 has no last_his_rows, so
    # its first pass after the hour counts his words from 0.
    last_his = int(st.get("last_his_rows") or 0)
    n, his, door_t = _scan(ask_log)
    out = {"ran": False, "why": "", "rows": n, "his_rows": his, "new_rows": max(0, his - last_his),
           "since_last_s": (now - last_t) if last_t else None}
    if last_t and now - last_t < every:
        out["why"] = "last pass %.0f min ago; next after %d min" % ((now - last_t) / 60.0, every // 60)
        return out
    if his <= last_his:
        out["why"] = "no new conversation since the last pass (%d rows of his words, %d conversation rows in all)" % (his, n)
        return out
    # A351: a pass that is due is not started while he is talking with Tetsu at the door (door_deferral). Nothing is
    # saved, so the next round sees the same gates and the same new words. A pass that started before he came back is
    # not stopped by this (the docstring's WHAT GATE 4 DOES NOT COVER).
    wait_why = door_deferral(now, quiet=quiet, door_t=door_t)
    if wait_why:
        out.update(deferred=True, why="deferred: " + wait_why)
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
