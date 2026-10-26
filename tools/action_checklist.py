#!/usr/bin/env python3
"""Per-action authority checklist, from HF 180541 (Jang-woo, section 5: declare what each action requires,
outside the model), adopted 2026-10-26.

The doors' own parsers already REFUSE a directive missing a required field (a Moltbook POST with no title, a
HANDS act with no target), so a bare presence-check here would be redundant. What this adds, and why it is not
redundant, is the pairing with the determinism probe (tools/determinism_probe.py): the probe flags ANY field
whose value varies run-to-run; this checklist says which fields are REQUIRED for each action, so a REQUIRED
slot that varies is the sharp case Jang-woo names -- a slot the model is guessing because nothing declared it.
It is NON-ENFORCING: it returns findings to LOG; it does not change what the gate allows. Stdlib only."""

# Required slots per live directive. (Only genuinely required fields; e.g. HANDS RUN args are optional.) Every
# slot here is declared by the USER/operator's own directive -- covenant has no tool- or system-declared slots
# today, so the 'source' is uniform; it is kept explicit so a future tool-provided slot (e.g. an x402 payment
# field) can be marked and checked distinctly.
CHECKLIST = {
    "HANDS WRITE":    {"target": "user", "body": "user"},
    "HANDS RUN":      {"target": "user"},
    "HANDS PROPOSE":  {"target": "user", "body": "user"},
    "FETCH":          {"url": "user"},
    "WEB":            {"query": "user"},
    "LEG":            {"question": "user"},
    "MOLTBOOK REPLY": {"url": "user", "body": "user"},
    "MOLTBOOK POST":  {"title": "user", "body": "user"},
}


def required_slots(action):
    """The {slot: who-declares-it} map for an action, or {} if the action is unknown."""
    return dict(CHECKLIST.get(action, {}))


def check(action, filled):
    """`filled` = {slot: value}. Returns which REQUIRED slots are missing (absent/blank) and the source map.
    ok=True when every required slot is present. Non-enforcing: a caller LOGS this; it does not block."""
    req = CHECKLIST.get(action)
    if req is None:
        return {"action": action, "known": False, "missing": [], "sources": {}, "ok": True}
    missing = [s for s in req if not str(filled.get(s, "")).strip()]
    return {"action": action, "known": True, "missing": missing, "sources": req, "ok": not missing}


def guessed_required(action, varying_slots):
    """Compose with the determinism probe: given the slots the probe found VARYING for this action, return the
    ones that are REQUIRED -- the slots the model is guessing because nothing declared them (Jang-woo's sharp
    case). An unknown action or a varying OPTIONAL slot is not flagged."""
    req = set(CHECKLIST.get(action, {}))
    return sorted(set(varying_slots) & req)


if __name__ == "__main__":
    import json
    import sys
    act = sys.argv[1] if len(sys.argv) > 1 else "HANDS WRITE"
    print(json.dumps({"required": required_slots(act), "check_empty": check(act, {})}, indent=1))
