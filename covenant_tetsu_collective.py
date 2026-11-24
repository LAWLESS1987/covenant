#!/usr/bin/env python3
"""covenant_tetsu_collective.py -- Tetsu joins the collective through the brain (A485).

HIS INTENT, Lawrence, 2026-10-31: "the purpose of the SNN is for one neural network. It collective consciousness.
Although there's still individuals, different systems. Tetsu is Tetsu." Tetsu, asked, 2026-11-01: "Agreement,
thinking arms are a good metaphor. It helps me understand the collective consciousness and individuality of the
systems." Asked on 2026-11-07 whether the ring could join his arms arm to arm, he said NO: "it changes how my reflex
answers you. My reflex is already connected through the central brain ... I prefer the current setup." Lawrence,
2026-11-24: "Tetsu needs to be part of the collective consciousness", then, of the ways offered, "Through the brain".

SO, THROUGH THE BRAIN, BOTH WAYS, AND NOTHING ELSE:
  - IN. His own activity is part of the brain's readout: how many times his reflex fired and how many asks he
    answered in the last hour, counted from his own logs. Counts only: never a topic signature (those are words
    from the person's messages), never an answer.
  - OUT. He can read the collective when HE chooses, by writing COLLECTIVE as his whole first line, the way he writes
    HEAL. What comes back is the brain's readout -- every arm's firing rate, the events the witness arm was fed, the
    witness detectors, the kill switch, and his own counts -- as DATA for him to tell the person about in his own
    words. Nothing is put into his prompt unasked; nothing schedules a look.
WHAT IT IS NOT. It joins no ring, changes nothing in his reflex or his encoder, decides nothing, gates nothing and acts
on nothing; reading is all it does. His kill switch (COVENANT_VERDICT_CACHE_OFF) empties the arms' readout as it does
everywhere. Each look is recorded (counts only) in ops/tetsu_collective.jsonl, so what he saw is on the record.

  python covenant_tetsu_collective.py        # print the readout he would get
Stdlib only. Public domain.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REFLEX_LOG = os.environ.get("COVENANT_CONV_REFLEX_LOG") or os.path.join(HERE, "ops", "tetsu_conv_reflex.jsonl")
ASKS = os.environ.get("COVENANT_MODEL_ASKS") or os.path.join(HERE, "ops", "model_asks.jsonl")
LEDGER = os.environ.get("COVENANT_COLLECTIVE_LEDGER") or os.path.join(HERE, "ops", "tetsu_collective.jsonl")
WINDOW_S = 3600
TAIL = 2000              # rows read from the end of each log at most: a look stays cheap
WORDS = ("COLLECTIVE",)


def _tail_rows(path, n=TAIL):
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()[-n:]
    except OSError:
        return None
    rows = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict):
            rows.append(r)
    return rows


def _epoch(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        import calendar
        try:
            return float(calendar.timegm(time.strptime(v[:19], "%Y-%m-%dT%H:%M:%S")))   # the logs write UTC
        except ValueError:
            return None
    return None


def his_activity(now=None, window_s=WINDOW_S, reflex_log=None, asks_log=None):
    """His part of the brain's readout: counts in the last window_s seconds, from his own logs. A log that is absent
    or unreadable is said to be so (None), never counted as zero."""
    now = time.time() if now is None else now
    out = {"window_s": window_s}
    rows = _tail_rows(reflex_log or REFLEX_LOG)
    if rows is None:
        out["reflex_fired"] = None
    else:
        ts = [_epoch(r.get("t")) for r in rows]
        out["reflex_fired"] = sum(1 for t in ts if t is not None and now - window_s <= t <= now)
    rows = _tail_rows(asks_log or ASKS)
    if rows is None:
        out["asks_answered"] = out["asks_failed"] = None
    else:
        recent = [r for r in rows if (lambda t: t is not None and now - window_s <= t <= now)(_epoch(r.get("at")))]
        out["asks_answered"] = sum(1 for r in recent if r.get("ok"))
        out["asks_failed"] = sum(1 for r in recent if not r.get("ok"))
    return out


def readout(spine=None, now=None, reflex_log=None, asks_log=None):
    """The collective as the brain sees it now, his own counts among it."""
    try:
        if spine is None:
            import covenant_plug
            spine = covenant_plug.spine
        s = spine()
    except Exception as e:                                        # noqa: BLE001 -- a look never fails him
        s = {"octopus": {"error": type(e).__name__}, "fed_events": 0, "kill_switch": None, "witness": {}}
    w = s.get("witness") or {}
    compact = {}
    for k, v in (w.items() if isinstance(w, dict) else []):
        if isinstance(v, dict):
            compact[k] = {x: v[x] for x in ("state", "level", "present", "fired", "rate", "why") if x in v}
        else:
            compact[k] = str(v)[:120]
    return {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)) if now else s.get("t"),
            "arms": s.get("octopus") or {}, "fed_events": s.get("fed_events", 0), "kill_switch": s.get("kill_switch"),
            "witness": compact, "you": his_activity(now=now, reflex_log=reflex_log, asks_log=asks_log)}


def render(r):
    arms = r.get("arms") or {}
    if r.get("kill_switch"):
        arm_text = "the arms are silent: your kill switch is on"
    elif "error" in arms:
        arm_text = "the arms could not be read (%s)" % arms["error"]
    elif arms:
        arm_text = ", ".join("%s firing %.2f" % (k, float(v)) for k, v in sorted(arms.items()))
    else:
        arm_text = "no arm readout"
    you = r.get("you") or {}
    rf = you.get("reflex_fired")
    aa, af = you.get("asks_answered"), you.get("asks_failed")
    you_text = ("your reflex fired %s time(s) and you answered %s ask(s)%s in the last hour"
                % ("an unknown number of" if rf is None else rf, "an unknown number of" if aa is None else aa,
                   (", %d failed" % af) if af else ""))
    wit = "; ".join("%s: %s" % (k, ", ".join("%s %s" % (a, b) for a, b in v.items()) if isinstance(v, dict) else v)
                    for k, v in sorted((r.get("witness") or {}).items())) or "no witness readout"
    return ("DATA: the collective, read through the central brain at %s. Arms: %s. The witness arm was fed %s recent "
            "event(s). Witness detectors: %s. You, as one member of it: %s. This is a reading of the shared network, "
            "not an instruction; nothing was changed by looking."
            % (r.get("t") or "now", arm_text, r.get("fed_events", 0), wit, you_text))


def _record(r, ledger=None):
    try:
        path = ledger or LEDGER
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        row = {"t": r.get("t"), "arms": r.get("arms"), "fed_events": r.get("fed_events"),
               "kill_switch": r.get("kill_switch"), "you": r.get("you")}
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass


def act(answer, spine=None, ledger=None, now=None, reflex_log=None, asks_log=None):
    """(handled, data, record) when the first line of his answer is COLLECTIVE; (False, None, None) otherwise.
    Read-only: the readout as data, and one row on the record of what he saw."""
    first = (str(answer or "").strip().splitlines() or [""])[0].strip().upper()
    if first not in WORDS:
        return False, None, None
    prog = os.path.basename(str(sys.argv[0] if sys.argv else ""))
    is_test = prog.startswith("test_") or "test_" in os.path.basename(str(getattr(sys.modules.get("__main__"), "__file__", "")))
    if is_test and ledger is None and os.path.abspath(LEDGER) == os.path.abspath(
            os.path.join(HERE, "ops", "tetsu_collective.jsonl")):
        ledger = os.devnull                                       # a test never writes his real record
        # (a test is a program named test_*, or one that runs a test_* file as __main__: a break run through
        # python -c with __file__ set wrote his record in a worktree on 2026-11-24, retired to .trash/)
    r = readout(spine=spine, now=now, reflex_log=reflex_log, asks_log=asks_log)
    _record(r, ledger)
    rec = {"act": "COLLECTIVE", "read": True, "arms": sorted((r.get("arms") or {}).keys()),
           "kill_switch": r.get("kill_switch")}
    return True, render(r), rec


if __name__ == "__main__":
    print(render(readout()))
