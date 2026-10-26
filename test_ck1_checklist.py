#!/usr/bin/env python3
"""CK1 -- the per-action authority checklist (tools/action_checklist.py, Jang-woo 180541), driven BOTH ways
(rule 8): a required slot present -> ok; a required slot missing/blank -> flagged; an unknown action is not
flagged (we don't know its slots); and -- the non-redundant part -- composing with the determinism probe, a
REQUIRED slot that VARIES run-to-run is flagged as guessed while a varying OPTIONAL/unknown slot is not. Stdlib
only; no model."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import action_checklist as C

fails = []


def ok(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:160]))
    if not cond:
        fails.append(name)


ok("CK1.1 a known action with every required slot present is ok",
   C.check("HANDS WRITE", {"target": "a.py", "body": "print(1)"})["ok"] is True)
r_missing = C.check("HANDS WRITE", {"target": "a.py"})
ok("CK1.2 a missing required slot is flagged (not ok), and named",
   r_missing["ok"] is False and r_missing["missing"] == ["body"], r_missing)
ok("CK1.3 a blank required slot counts as missing",
   C.check("MOLTBOOK POST", {"title": "   ", "body": "x"})["missing"] == ["title"])
r_unknown = C.check("DANCE", {})
ok("CK1.4 an unknown action is NOT flagged (its slots are not ours to assume)",
   r_unknown["known"] is False and r_unknown["ok"] is True and r_unknown["missing"] == [], r_unknown)
ok("CK1.5 an optional slot absent is fine (HANDS RUN needs only target, args optional)",
   C.check("HANDS RUN", {"target": "go.py"})["ok"] is True)

# the non-redundant part: compose with the determinism probe's varying slots
ok("CK1.6 a REQUIRED slot that varies run-to-run is flagged as guessed (checklist x determinism)",
   C.guessed_required("FETCH", ["url", "note"]) == ["url"])
ok("CK1.7 a varying OPTIONAL/unknown slot is NOT flagged as a guessed-required slot",
   C.guessed_required("HANDS RUN", ["args", "seed"]) == [] and C.guessed_required("DANCE", ["x"]) == [])
ok("CK1.8 required_slots carries the who-declares source map",
   C.required_slots("MOLTBOOK REPLY") == {"url": "user", "body": "user"})

print("\nCK1: %d/8 passed" % (8 - len(fails)))
raise SystemExit(1 if fails else 0)
