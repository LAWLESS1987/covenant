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


p = H.heal_peer("100.72.0.10", 5000, ledger_path=LEDGER, post=fake_post)
check("HL1.12 heal_peer presses the PEER'S OWN button (/m/heal) and passes no remedy of its own",
      POSTED == [("100.72.0.10", 5000, "/m/heal", {"dry_run": False})], POSTED)
check("HL1.13 and reports back what the peer said it did", p["ok"] is True and "nothing was wrong" in p["summary"])


def dead_post(*_a, **_k):
    raise OSError("no route to host")


p2 = H.heal_peer("10.0.0.9", 5000, ledger_path=LEDGER, post=dead_post)
check("HL1.14 a peer that cannot be reached is said plainly and never raises",
      p2["ok"] is False and "could not be reached" in p2["summary"])
check("HL1.15 both directions are on the same record", [r["kind"] for r in rows()][-2:] == ["heal_peer", "heal_peer"])

# ---- HL2 (2026-09-28, his words: "give tetsu the way to do it himself from the phone app"):
# Tetsu's HEAL line is the SAME button, his choice, recorded under his name.
import covenant_tetsu_heal as TH                                      # noqa: E402

CALLS = []


def fake_heal(dry_run=False, who=""):
    CALLS.append({"dry_run": dry_run, "who": who})
    return {"ok": True, "summary": "looked at 19 condition(s); fixed 1 (source_drift); 1 still needs a person (mesh_source_split)",
            "fixed": [{"condition": "source_drift"}],
            "still_needs_a_person": [{"condition": "mesh_source_split", "why_no_fix": "no automatic remedy exists for this one"}],
            "paused": False}


h1, d1, r1 = TH.act("HEAL", heal=fake_heal)
check("HL2.1 'HEAL' as his whole answer presses the one button, live, as who='tetsu'",
      h1 and CALLS == [{"dry_run": False, "who": "tetsu"}] and r1["kind"] == "tetsu_heal" and not r1["dry_run"], (CALLS, r1))
check("HL2.2 what he is handed is what happened: the summary, the fixed, and the still-needs-a-person with its reason",
      "fixed: source_drift" in d1 and "still needs a person: mesh_source_split" in d1 and "no automatic remedy" in d1, d1)
h2, d2, r2 = TH.act("heal dry\n", heal=fake_heal)
check("HL2.3 'HEAL DRY' measures without repairing, and says so in the record", h2 and CALLS[-1]["dry_run"] is True and r2["dry_run"], CALLS[-1:])
check("HL2.4 an ordinary answer is not a press: the conversation goes on untouched",
      TH.act("I checked the nodes, all fine.", heal=fake_heal) == (False, "", None) and len(CALLS) == 2)


def heal_on_fire(**_k):
    raise RuntimeError("engine on fire")


h3, d3, r3 = TH.act("HEAL", heal=heal_on_fire)
check("HL2.5 a heal that raises is handed to him as a plain failure, never a traceback up the door",
      h3 and r3["ok"] is False and "could not run" in d3, d3[:120])

# ---- A240: inside a node, the restart runs beside the pass instead of killing it
import covenant_quiet as CQ                                           # noqa: E402
import subprocess as _sp                                              # noqa: E402
SPAWNED = []
_real_popen = CQ.popen_survivor
CQ.popen_survivor = lambda cmd, **kw: SPAWNED.append(cmd) or type("P", (), {"pid": 9999})()
# BOTH branches are stubbed, so this check cannot reach the real nodes even if the
# guard it tests is broken (the first run of this mutant restarted the real mesh).
_real_run = _sp.run
_sp.run = lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "stubbed: no real restart from a test"})()
_fake_node_mod = sys.modules.get("covenant_unified_v8")
try:
    sys.modules.setdefault("covenant_unified_v8", type(sys)("covenant_unified_v8"))
    ok240, msg240 = HW.remedy_restart_nodes({}, dry_run=False)
    check("HL2.6 A240: with the node module loaded, the restart is DETACHED -- the pass it is inside survives it",
          ok240 and "detached" in msg240 and "A240" in msg240 and SPAWNED and "rolling_restart.py" in SPAWNED[0][1], (msg240, SPAWNED))
    ok241, msg241 = HW.remedy_restart_nodes({}, dry_run=True)
    check("HL2.7 and a dry run still only says what it would do", ok241 and msg241 == "would run rolling_restart.py")
finally:
    CQ.popen_survivor = _real_popen
    _sp.run = _real_run
    if _fake_node_mod is None:
        sys.modules.pop("covenant_unified_v8", None)
check("HL2.8 the registry grades the restart AFTER it has had time to finish, so a working remedy is not quarantined (A240)",
      set(HW.REMEDIES["restart_nodes"].get("async_for") or []) == {"source_drift", "node_down"}
      and (HW.REMEDIES["restart_nodes"].get("grade_after_s") or 0) >= 60.0, HW.REMEDIES["restart_nodes"].get("grade_after_s"))

# HL2.9: the door actually dispatches his HEAL line (the PP1.11d idiom: the AST, not a text grep --
# it proves the call is written into the door, not that a live conversation reaches it, and says so).
import ast                                                            # noqa: E402
_tree = ast.parse(open(os.path.join(HERE, "covenant_unified_v8.py"), encoding="utf-8").read())
_calls = [n for n in ast.walk(_tree) if isinstance(n, ast.Call)
          and getattr(n.func, "attr", "") == "import_module"
          and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "covenant_tetsu_heal"]
check("HL2.9 the agent door imports covenant_tetsu_heal to dispatch his HEAL line (AST; run-time reach is M6's job)",
      len(_calls) == 1, len(_calls))

print("\nnot measured here: the real repairs on this machine (that is covenant_highway's own suites, H1); "
      "the phone's button, which needs an app build; and how the real Tetsu answers after a press")
print("\nHL1+HL2: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
