"""covenant_eligibility.py -- A471: the highway's detectors earn credit from outcomes, and a detector whose alarms keep
clearing by themselves waits one pass before its remedy runs.

HIS WORDS, 2026-11-22: "The system should be expanding to work like a neural network even better. Like a neural network
and a nervous system", then "Build it active, not read-only". Design: docs/NERVOUS_SYSTEM_MAP_2026-11-22.md.

WHAT THE LAB TAUGHT THAT THIS USES (spiking lab exp18-25). One diffuse outcome signal cannot say which part was
wrong; credit needs a LOCAL trace at each part (an eligibility trace) multiplied by the outcome (exp20's rule, the
one that passed). Here the parts are the highway's detectors, the trace is how recently a detector read PRESENT, and
the outcome is what happened to the condition it raised:
  - PRESENT, then ABSENT with a remedy of its own having run since: the alarm was real            +1
  - PRESENT on two passes running: it persisted, so it was real                                   +0.5
  - PRESENT, then ABSENT with nothing of its own having run: it cleared by itself (a false alarm) -1
Credit c <- clip(0.99 c + 0.25 x outcome x trace, -1, 1), trace = exp(-(now - last PRESENT) / 1 h).

WHAT CREDIT DOES (active, and only toward caution). A detector at c <= -0.5 that reads PRESENT this pass but did NOT
read PRESENT on the last pass has its remedies held for ONE pass; if it is still PRESENT next pass, they run as
before. Only automatic action waits: the reading is still reported, logged and on the page exactly as it was.

WHAT IT NEVER DOES.
  - It never hides, softens or relabels a reading.
  - It never makes a remedy run that would not have run; good credit only stops a hold.
  - It never touches the takeover guards (covenant_highway.ALWAYS_APPLIES): they are never held.
  - It never touches Tetsu's leg or arms: he was asked on 2026-11-22 and said NO (ops/tetsu_consent.jsonl,
    kind leg_credit_consent).
  - KILL SWITCH: COVENANT_ELIGIBILITY_OFF=1 stops every hold and every credit update. A pause of the highway
    already stops every remedy before this is reached.

State: logs/eligibility_state.json (gitignored, like every log); COVENANT_ELIGIBILITY_STATE overrides the path.
"""
from __future__ import annotations

import json
import math
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "logs", "eligibility_state.json")
TRACE_S = 3600.0
ETA = 0.25
FORGET = 0.99
HOLD_BELOW = -0.5
OUTCOME_REAL, OUTCOME_PERSISTED, OUTCOME_SELF_CLEARED = 1.0, 0.5, -1.0
ACTED = ("fixed", "started", "held")            # a remedy of its own ran (held = ran and the condition stayed)
PRESENT, ABSENT = "PRESENT", "ABSENT"


def off():
    return os.environ.get("COVENANT_ELIGIBILITY_OFF", "") not in ("", "0", "false", "False")


def _path(path=None):
    return path or os.environ.get("COVENANT_ELIGIBILITY_STATE") or STATE


def load(path=None):
    try:
        with open(_path(path), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) and isinstance(d.get("detectors"), dict) else {"detectors": {}}
    except (OSError, ValueError):
        return {"detectors": {}}


def save(state, path=None):
    p = _path(path)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(state, fh, indent=1, sort_keys=True)
        os.replace(tmp, p)
    except OSError:
        pass


def recent_rows(path, tail_bytes=262144):
    """The ledger's last rows only (its tail), since a pass needs rows since the previous pass, not the whole file
    (5 MB and growing when written). Never raises."""
    out = []
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - tail_bytes))
            chunk = fh.read().decode("utf-8", "replace")
        lines = chunk.splitlines()
        if size > tail_bytes:
            lines = lines[1:]                        # the first line may be cut
        for line in lines:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


def _acted_since(ledger_rows, detector, since):
    return any(r.get("detector") == detector and r.get("outcome") in ACTED and not r.get("dry_run")
               and float(r.get("at") or 0) >= since for r in ledger_rows)


def observe(prev, conditions, ledger_rows, state, now=None, prev_at=None):
    """Update credit from one pass. prev: {detector: state} of the last pass (None if unknown); conditions: this
    pass's {detector: {"state": ...}}. Returns the list of (detector, outcome) credited. Never raises."""
    if off() or not prev:
        return []
    now = time.time() if now is None else now
    since = prev_at if prev_at is not None else now - 900
    out = []
    for name, c in (conditions or {}).items():
        st = (c or {}).get("state")
        d = state["detectors"].setdefault(name, {"credit": 0.0, "last_present_at": None,
                                                 "real": 0, "persisted": 0, "self_cleared": 0})
        was = prev.get(name)
        outcome = None
        if was == PRESENT and st == ABSENT:
            outcome = OUTCOME_REAL if _acted_since(ledger_rows, name, since) else OUTCOME_SELF_CLEARED
        elif was == PRESENT and st == PRESENT:
            outcome = OUTCOME_PERSISTED
        if outcome is not None:
            last = d.get("last_present_at") or now
            trace = math.exp(-max(0.0, now - last) / TRACE_S)
            d["credit"] = max(-1.0, min(1.0, FORGET * d["credit"] + ETA * outcome * trace))
            d[{OUTCOME_REAL: "real", OUTCOME_PERSISTED: "persisted", OUTCOME_SELF_CLEARED: "self_cleared"}[outcome]] += 1
            out.append((name, outcome))
        if st == PRESENT:
            d["last_present_at"] = now
    return out


def hold(name, prev, state, exempt=()):
    """None, or the reason this detector's remedies wait one pass. Caution only; never raises."""
    if off() or name in exempt:
        return None
    d = state.get("detectors", {}).get(name)
    if not d or d.get("credit", 0.0) > HOLD_BELOW:
        return None
    if prev and prev.get(name) == PRESENT:
        return None                                  # it persisted: act now, as before
    return ("its alarms have cleared by themselves %d times (credit %.2f, A471): remedies wait one pass and run "
            "if it is still present then" % (d.get("self_cleared", 0), d["credit"]))


def report(path=None):
    """Every detector's credit, lowest first -- what the active rule reads."""
    st = load(path)
    return sorted(((n, round(d.get("credit", 0.0), 3), d.get("self_cleared", 0), d.get("real", 0), d.get("persisted", 0))
                   for n, d in st["detectors"].items()), key=lambda x: x[1])


if __name__ == "__main__":
    for row in report():
        print("%-32s credit %+.3f  self-cleared %d  real %d  persisted %d" % row)
