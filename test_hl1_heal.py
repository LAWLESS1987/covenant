#!/usr/bin/env python3
"""test_hl1_heal.py -- A215: one press repairs what can be repaired and NAMES
what cannot, at either end of the wire.

His words, 2026-09-21: "I need to be able to have the system fix itself for any
issues that arise" -- "Give me a one click self heal button on the pc and phone
apps that can fix eachother".

Fixtures throughout: the highway's sense and run_once are stubbed so the checks
drive the button's own logic -- what it calls fixed, what it hands back to him,
and the reason it gives -- without repairing this machine. One check reads the
REAL highway to prove the registry the reason text depends on is the shape this
module thinks it is.
LICENCE: public domain.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_heal as H                                             # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:220]) if note and not cond else ""))


LEDGER = os.path.join(tempfile.mkdtemp(prefix="hl1_"), "heal.jsonl")


def rows():
    try:
        return [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
    except OSError:
        return []


print("HL1 -- the self-heal button")

# ---- a condition that clears counts as fixed; one that stays comes back to him
STATE = {"n": 0}
BEFORE = {"a_fixable": {"state": "PRESENT", "measured": {"x": 1}},
          "b_stuck": {"state": "PRESENT", "measured": {"y": 2}},
          "c_fine": {"state": "ABSENT", "measured": {}}}
AFTER = {"a_fixable": {"state": "ABSENT", "measured": {}},
         "b_stuck": {"state": "PRESENT", "measured": {"y": 2}},
         "c_fine": {"state": "ABSENT", "measured": {}}}


def fake_sense(**_k):
    STATE["n"] += 1
    return BEFORE if STATE["n"] == 1 else AFTER


CALLS = []


def fake_run(dry_run=False, **kw):
    CALLS.append(dict(kw, dry_run=dry_run))
    return (["highway: a_fixable repaired"], ["highway: b_stuck still present"])


out = H.heal(ledger_path=LEDGER, run=fake_run, sense=fake_sense)
check("HL1.1 a condition that is gone on the second look is 'fixed'; one still present comes back to him",
      [x["condition"] for x in out["fixed"]] == ["a_fixable"]
      and [x["condition"] for x in out["still_needs_a_person"]] == ["b_stuck"], out)
check("HL1.2 a condition that was never present is neither fixed nor blamed on him",
      all(x["condition"] != "c_fine" for x in out["fixed"] + out["still_needs_a_person"]))
check("HL1.3 it looked at every condition, not only the broken ones", out["looked_at"] == 3)
check("HL1.4 the measurement is carried, so he is not told a name with no evidence",
      out["fixed"][0]["measured"] == {"x": 1} and out["still_needs_a_person"][0]["measured"] == {"y": 2})

# ---- THE THING THAT MADE IT USELESS THE FIRST TIME
check("HL1.5 a person's press waives the noise cooldown (measured 2026-09-21: without it a real "
      "press repaired NOTHING and blamed six conditions on him, five of which had a remedy merely cooling down)",
      CALLS and CALLS[0].get("cooldown_s") == 0, CALLS)

# ---- it says what it did, in one line, and writes it down
check("HL1.6 the summary names both halves in a line he can read without opening anything",
      "fixed 1" in out["summary"] and "1 still needs a person" in out["summary"], out["summary"])
check("HL1.7 every press is on the record", rows() and rows()[-1]["kind"] == "heal" and rows()[-1]["ok"] is True)

# ---- a dry run repairs nothing and SAYS that is why
STATE["n"] = 0
CALLS.clear()
d = H.heal(dry_run=True, ledger_path=LEDGER, run=fake_run, sense=fake_sense)
check("HL1.8 a dry run passes dry_run through and never claims a remedy ran",
      CALLS[0]["dry_run"] is True and all("dry run" in x["why_no_fix"] for x in d["still_needs_a_person"]),
      [x["why_no_fix"] for x in d["still_needs_a_person"]])

# ---- broken the other way: the engine failing is reported, never raised
def boom(**_k):
    raise RuntimeError("the highway is on fire")


bad = H.heal(ledger_path=LEDGER, run=boom, sense=fake_sense)
check("HL1.9 an engine that raises gives an honest failure, not a traceback: a button that throws is not a button",
      bad["ok"] is False and "on fire" in bad.get("error", "") and "could not run" in bad["summary"], bad)

# ---- the reason text depends on the REAL registry's shape
import covenant_highway as HW                                         # noqa: E402
check("HL1.10 remedies_for reads the real registry: a condition with a remedy names it",
      "rehash_bundle" in H.remedies_for(HW, "manifest_stale"), H.remedies_for(HW, "manifest_stale"))
check("HL1.11 and a condition with NO remedy is told apart from one whose remedy did not settle it",
      H.remedies_for(HW, "mesh_source_split") == []
      and "no automatic remedy exists" in H._no_remedy_reason(HW, "mesh_source_split")
      and "rehash_bundle" in H._no_remedy_reason(HW, "manifest_stale"))

# ---- the other end of the wire: press its button, never reach into it
POSTED = []


def fake_post(host, port, path, payload, timeout):
    POSTED.append((host, port, path, payload))
    return 200, json.dumps({"ok": True, "summary": "looked at 17 condition(s); nothing was wrong",
                            "fixed": [], "still_needs_a_person": []})


p = H.heal_peer("100.86.158.1", 5000, ledger_path=LEDGER, post=fake_post)
check("HL1.12 heal_peer presses the PEER'S OWN button (/m/heal) and passes no remedy of its own",
      POSTED == [("100.86.158.1", 5000, "/m/heal", {"dry_run": False})], POSTED)
check("HL1.13 and reports back what the peer said it did", p["ok"] is True and "nothing was wrong" in p["summary"])


def dead_post(*_a, **_k):
    raise OSError("no route to host")


p2 = H.heal_peer("10.0.0.9", 5000, ledger_path=LEDGER, post=dead_post)
check("HL1.14 a peer that cannot be reached is said plainly and never raises",
      p2["ok"] is False and "could not be reached" in p2["summary"])
check("HL1.15 both directions are on the same record", [r["kind"] for r in rows()][-2:] == ["heal_peer", "heal_peer"])

print("\nnot measured here: the real repairs on this machine (that is covenant_highway's own suites, H1); "
      "and the phone's button, which needs an app build")
print("\nHL1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
