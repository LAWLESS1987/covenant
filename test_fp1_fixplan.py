#!/usr/bin/env python3
"""test_fp1_fixplan.py -- A420: a condition the heal leaves always comes with what will fix it.

His words, 2026-11-10: "I often get there's nothing here to fix it on the phone.
I want you to have something there that can fix it. Root it in mutual benefit
of all intelligence."

  F1  COVERAGE. Every detector in the REAL highway that has no remedy the
      machine may run by itself has a complete card. Driven both ways: a
      detector added without a card turns it red, and so does a card with its
      cost removed.
  F2  THE CARD. Step, owner, gain AND cost, and marked as a claim. An unknown
      condition still gets a step. A remedy that ran and did not settle it
      gets the remedy's own last ledger line, not a guess.
  F3  THE HEAL. What it hands back carries the step in the field the phone
      shows, and keeps the reason it always gave. A condition that was fixed
      carries no card.
  F4  THE LINE. What reaches him names the next step, and a heal with no card
      module still works as it did.
  F5  THE BOUNDARY. No card tells the machine to act: nothing here is
      registered as a remedy, and the cards for the NEVER_AUTOMATIC subjects
      name an owner rather than a command the engine runs.

WHAT THIS CANNOT SEE. Whether a step WORKS. F1 counts cards against detectors;
it reads no card for truth. A step is prose until someone runs it and the
condition is measured again. The heal checks use a stubbed sense and run_once,
so nothing on this machine is repaired or told.
LICENCE: public domain.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
os.environ["COVENANT_HEAL_TOLD"] = os.path.join(tempfile.mkdtemp(prefix="fp1_told_"), "heal_told.json")
import covenant_fixplan as FP                                         # noqa: E402
import covenant_heal as H                                             # noqa: E402
import covenant_highway as HW                                         # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:300]) if note and not cond else ""))


print("FP1 -- what will fix it")
FIELDS = ("owner", "step", "gains", "cost", "why_not_automatic")

# ---- F1 coverage, on the real registry ------------------------------------------
need = FP.needs_card(HW)
check("F1a the real highway has detectors with no automatic remedy (the population is not empty)",
      len(need) >= 10, len(need))
check("F1b every one of them has a complete card", FP.missing(HW) == [], FP.missing(HW))
check("F1c no card is on file for a detector that does not exist (a card for nothing is a stale card)",
      sorted(set(FP.FIX) - set(HW.DETECTORS)) == [], sorted(set(FP.FIX) - set(HW.DETECTORS)))

# both ways: a NEW detector with no card is caught
HW.DETECTORS["zz_fp1_probe"] = lambda health=None: {"state": HW.ABSENT, "measured": {}}
try:
    check("F1d a detector added with no card and no remedy turns the guard red",
          FP.missing(HW) == ["zz_fp1_probe"], FP.missing(HW))
    HW.REMEDIES["zz_fp1_fix"] = {"fn": lambda m, dry_run=True: (True, ""), "klass": HW.AUTO_REVERSIBLE,
                                 "for": ["zz_fp1_probe"], "kind": "stateless"}
    check("F1e ...and one the machine CAN repair by itself needs no card", FP.missing(HW) == [], FP.missing(HW))
    HW.REMEDIES["zz_fp1_fix"]["klass"] = HW.PROPOSE_ONLY
    check("F1f ...but a remedy that only PROPOSES does not count as a repair",
          FP.missing(HW) == ["zz_fp1_probe"], FP.missing(HW))
finally:
    HW.DETECTORS.pop("zz_fp1_probe", None)
    HW.REMEDIES.pop("zz_fp1_fix", None)
check("F1g the probe is gone and the guard is green again", FP.missing(HW) == [], FP.missing(HW))

# both ways: a card that states a gain with no cost is not complete
some = need[0]
kept = FP.FIX[some]["cost"]
FP.FIX[some]["cost"] = "  "
try:
    check("F1h a card with its COST blanked is incomplete (every gain stated with its cost)",
          FP.missing(HW) == [some], FP.missing(HW))
finally:
    FP.FIX[some]["cost"] = kept
check("F1i ...restored, green", FP.missing(HW) == [], FP.missing(HW))

# ---- F2 the card ------------------------------------------------------------------
c = FP.card(HW, "mesh_source_split")
check("F2a an owner card carries step, owner, gain, cost and the reason it is not automatic",
      c["kind"] == "owner" and all(c.get(k) for k in FIELDS), c)
check("F2b ...is marked a claim, not a finding", c.get("claimed_by") == "claude, not ratified", c)
check("F2c ...and its owner is whoever holds the device, not always the operator",
      "whoever holds" in c["owner"], c["owner"])
u = FP.card(HW, "zz_never_heard_of_it")
check("F2d a condition nobody wrote a card for still gets a step, and says so",
      u["kind"] == "unknown" and "fix zz_never_heard_of_it" in u["step"] and all(u.get(k) for k in FIELDS), u)

auto_name = next(n for n in sorted(HW.DETECTORS) if FP._auto_remedies(HW, n))
auto_rem = FP._auto_remedies(HW, auto_name)[0]
ROWS = [{"detector": auto_name, "remedy": auto_rem, "outcome": "fixed", "why": "older line"},
        {"detector": auto_name, "remedy": auto_rem, "outcome": "did not fix", "why": "the real reason"},
        {"detector": auto_name, "remedy": auto_rem, "outcome": "would run", "why": "a rehearsal", "dry_run": True},
        {"detector": "another", "remedy": auto_rem, "outcome": "fixed", "why": "not this condition"}]
s = FP.card(HW, auto_name, rows=ROWS)
check("F2e a remedy that ran and did not settle it: the card quotes the remedy's NEWEST REAL line",
      s["kind"] == "unsettled" and "did not fix -- the real reason" in s["step"] and auto_rem in s["step"], s["step"])
check("F2f ...never a rehearsal's line, and never another condition's",
      "a rehearsal" not in s["step"] and "not this condition" not in s["step"], s["step"])
s0 = FP.card(HW, auto_name, rows=[])
check("F2g ...and with no line on record it says there is none, it does not invent one",
      "left no line in the ledger" in s0["step"], s0["step"])
ln = FP.line(c)
check("F2h the phone line leads with the step and carries whose, gain and cost",
      ln.startswith("NEXT: ") and "whose:" in ln and "Gain:" in ln and "Cost:" in ln, ln)
check("F2i the direct-line form is cut to length and never empty",
      0 < len(FP.short(c, 60)) <= 60 and FP.short(c, 60).endswith("…"), FP.short(c, 60))

# ---- F3 the heal --------------------------------------------------------------------
STATE = {"n": 0}
BEFORE = {"mesh_source_split": {"state": "PRESENT", "measured": {"why": "peer on older bytes"}},
          auto_name: {"state": "PRESENT", "measured": {}},
          "zz_cleared": {"state": "PRESENT", "measured": {}}}
AFTER = dict(BEFORE, zz_cleared={"state": "ABSENT", "measured": {}})


def fake_sense(**_k):
    STATE["n"] += 1
    return BEFORE if STATE["n"] == 1 else AFTER


LEDGER = os.path.join(tempfile.mkdtemp(prefix="fp1_"), "heal.jsonl")
out = H.heal(who="fp1", ledger_path=LEDGER, sense=fake_sense, run=lambda **_k: ([], []))
left = {x["condition"]: x for x in out["still_needs_a_person"]}
check("F3a the heal ran and left the two that stayed", out["ok"] and sorted(left) == sorted(["mesh_source_split", auto_name]), out)
m = left.get("mesh_source_split", {})
check("F3b what it hands back keeps the reason it always gave",
      "no automatic remedy exists" in m.get("why_no_fix", ""), m.get("why_no_fix"))
check("F3c ...and now carries the step, in the field the phone already shows",
      "NEXT: " in m.get("why_no_fix", "") and FP.FIX["mesh_source_split"]["step"] in m.get("why_no_fix", ""),
      m.get("why_no_fix"))
check("F3d ...with the whole card beside it", (m.get("fix") or {}).get("owner") and (m.get("fix") or {}).get("cost"), m)
a = left.get(auto_name, {})
check("F3e a remedy that ran and did not settle it carries a step too",
      "NEXT: " in a.get("why_no_fix", "") and (a.get("fix") or {}).get("kind") == "unsettled", a)
check("F3f a condition that was FIXED carries no card", all("fix" not in x for x in out["fixed"]) and
      [x["condition"] for x in out["fixed"]] == ["zz_cleared"], out["fixed"])

# ---- F4 the line ----------------------------------------------------------------------
said = []
H.tell_left(out, lambda text, why: said.append(text) or {"ok": True}, who="fp1")
check("F4a what reaches him names the next step for each one left",
      len(said) == 1 and said[0].count("Next: ") == 2 and "mesh_source_split -- peer on older bytes. Next:" in said[0],
      said)

# both ways: with the card module unreadable, the heal still answers as it did before A420
keep = H._fix_card
H._fix_card = lambda HW_, name: None
try:
    STATE["n"] = 0
    out2 = H.heal(who="fp1", ledger_path=LEDGER, sense=fake_sense, run=lambda **_k: ([], []))
    m2 = next(x for x in out2["still_needs_a_person"] if x["condition"] == "mesh_source_split")
    check("F4b with no card readable the heal still answers, with the reason alone (the step is why F3c is green)",
          out2["ok"] and "NEXT: " not in m2["why_no_fix"] and "fix" not in m2, m2)
finally:
    H._fix_card = keep

# ---- F5 the boundary ---------------------------------------------------------------------
check("F5a the card module registers no remedy: nothing in it can be run by the engine",
      not any(getattr(r.get("fn"), "__module__", "") == "covenant_fixplan" for r in HW.REMEDIES.values()))
for n in ("head_commitment_broken", "consent_chain_broken", "model_drift", "moltbook_strikes"):
    check("F5b %s: the card names an owner and says why the machine does not act" % n,
          FP.FIX[n]["owner"].startswith("you") and len(FP.FIX[n]["why_not_automatic"]) > 20, FP.FIX[n])
check("F5c no card's step tells anyone to place an order or move money",
      not any(w in (v["step"] + v["gains"]).lower() for v in FP.FIX.values()
              for w in ("buy ", "sell ", "place an order", "withdraw", "transfer funds")))

print("\nFP1 fix plan: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
