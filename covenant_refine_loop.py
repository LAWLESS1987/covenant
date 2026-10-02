#!/usr/bin/env python3
"""covenant_refine_loop.py -- Tetsu refines himself CONSTANTLY, not once a night:
one pass an hour, and only when he has talked with someone since the last one.

HIS WORDS, 2026-09-21: "refine both constantly". Both are the register and
voice Tetsu revises (covenant_persona.refine, A174) and the PC that speaks
with the same register by construction (A189); the student judge's own
refinement runs in its own loop already (covenant_refine_check, A127).

WHAT GATES A PASS, measured, never guessed:
  1. at least REFINE_EVERY_S seconds since the last pass (ops/refine_loop_state.json);
  2. at least one new eligible conversation row since the last inspected pass;
     failed attempts preserve the feedback and retry with delayed backoff;
  3. the local model answers (covenant_model.ask; no model, no pass, said).
The pass itself is covenant_persona.refine with every bound, screen, gate,
record, contest and block it already has. The watchdog calls tick() every
round; the gates above make most rounds a no-op costing one file read.
"""
import json
import hashlib
import math
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("COVENANT_REFINE_LOOP_STATE") or os.path.join(HERE, "ops", "refine_loop_state.json")
ASK_LOG = os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
REFINE_EVERY_S = 3600
RETRY_BASE_S = 300
RETRY_MAX_S = 3600


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


def _conversation_scan(ask_log=None):
    """Count eligible rows and retain an opaque newest-row cursor, never chat contents."""
    import covenant_persona
    out = {"rows": 0, "cursor": "", "blocked": covenant_persona.blocked("conversations")}
    if out["blocked"]:
        return out
    try:
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if (not isinstance(r, dict) or r.get("kind") not in ("agent", "council")
                        or r.get("from") in covenant_persona.WORK_CALLERS
                        or not isinstance(r.get("text"), str) or not r["text"].strip()):
                    continue
                out["rows"] += 1
                out["cursor"] = hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    except FileNotFoundError:
        pass
    except (OSError, UnicodeError) as e:
        out["error"] = type(e).__name__
    return out


def conversation_rows(ask_log=None):
    """Eligible human conversation rows; blocked records and batch work stay excluded."""
    return _conversation_scan(ask_log)["rows"]


def _number(value, default=0):
    try:
        number = float(value)
        return max(0, number) if math.isfinite(number) else default
    except (TypeError, ValueError, OverflowError):
        return default


def tick(now=None, refine=None, ask=None, state_path=None, ask_log=None, say=print, every=REFINE_EVERY_S):
    """One watchdog round. Returns a dict: ran (bool), why, and the pass's summary when it ran."""
    now = time.time() if now is None else float(now)
    st = _state(state_path)
    last_t = _number(st.get("last_t"))
    last_n = int(_number(st.get("last_rows")))
    scan = _conversation_scan(ask_log)
    n, cursor = scan["rows"], scan["cursor"]
    last_cursor = st.get("last_cursor") or ""
    pending = st.get("pending_retry") is True
    changed_cursor = bool(cursor and last_cursor and cursor != last_cursor)
    out = {"ran": False, "attempted": False, "why": "", "rows": n,
           "new_rows": max(0, n - last_n) if n >= last_n else None,
           "since_last_s": (now - last_t) if last_t else None,
           "log_rotated": n < last_n}
    if scan["blocked"]:
        out["why"] = "conversation feedback is closed; no refinement requested"
        return out
    if scan.get("error"):
        out["why"] = "conversation record unavailable: " + scan["error"]
        return out
    # Rotation retaining the last inspected exchange is not new evidence. Reset
    # the count so the next genuinely appended exchange cannot be stranded.
    if n < last_n and cursor == last_cursor:
        st["last_rows"] = last_n = n
        _save(st, state_path)
        out["new_rows"] = 0
    retry_at = _number(st.get("retry_at"))
    if pending and now < retry_at:
        out.update(why="retry delayed for %.0f s after an unsuccessful attempt" % (retry_at - now), retry_at=retry_at)
        return out
    if not pending and last_t and now - last_t < every:
        out["why"] = "last pass %.0f min ago; next after %d min" % ((now - last_t) / 60.0, every // 60)
        return out
    if not n or (not pending and n <= last_n and not changed_cursor):
        out["why"] = "no new conversation since the last pass (%d rows)" % n
        # Populate the cursor for old state files without replaying old evidence.
        if cursor and not last_cursor and n == last_n:
            st["last_cursor"] = cursor
            _save(st, state_path)
        return out
    if changed_cursor and n <= last_n:
        out["new_rows"] = None
    out["attempted"] = True
    def defer(why):
        failures = min(12, int(_number(st.get("retry_failures"))) + 1)
        delay = min(RETRY_MAX_S, RETRY_BASE_S * 2 ** min(4, failures - 1))
        retry_at = now + delay
        st.update(last_attempt_t=now, pending_retry=True, retry_at=retry_at,
                  retry_failures=failures, last_why=why)
        _save(st, state_path)
        out.update(why=why, retryable=True, retry_at=retry_at)
        say("refine loop: %s; retry in %d s" % (why, delay))
        return out
    try:
        if refine is None:
            import covenant_persona
            def refine(ask, say=print):
                return covenant_persona.refine(ask, log_path=ask_log, now=now, say=say)
        if ask is None:
            import covenant_model
            ask = covenant_model.ask
        res = refine(ask, say=say)
        if not isinstance(res, dict):
            raise ValueError("refinement returned no result record")
    except Exception as e:                                        # noqa: BLE001
        return defer("the pass could not run: %s: %s" % (type(e).__name__, str(e)[:120]))
    out.update(ran=True, result={k: res.get(k) for k in ("proposed", "applied", "why", "feedback_inspected", "retryable", "decision")})
    if res.get("retryable") is True or (res.get("feedback_inspected") is False and res.get("decision") not in ("declined", "blocked")):
        return defer("feedback was not inspected: " + str(res.get("why") or "invalid proposal")[:160])
    out["why"] = ("inspected feedback on %d new row(s)" % out["new_rows"] if out["new_rows"] is not None
                  else "inspected feedback from a changed conversation record; new-row count unknown")
    st.update(last_t=now, last_attempt_t=now, last_rows=n, last_cursor=cursor, last_why=out["why"],
              pending_retry=False, retry_at=0, retry_failures=0, passes=int(_number(st.get("passes"))) + 1)
    _save(st, state_path)
    say("refine loop: %s -- %s" % (out["why"], res.get("why", "")))
    return out


if __name__ == "__main__":
    print(json.dumps(tick(), indent=1))
