#!/usr/bin/env python3
"""
test_a464_hwy_report_profile.py -- A464 (2026-11-21): what a node OFFERS the mesh is read with its own machine's
profile, and so is what it does with a peer's offer.

WHAT WAS MEASURED. On the second PC (node D only; ops/machine.json marks 28 of the 42 detectors as not applying
there and says the highway does not repair there) the watchdog's pass, which hands the profile to run_once(),
read 2 conditions PRESENT and 1 UNKNOWN in 3.7 s. The same node's GET /hwy/state, at the same hour, reported 9
PRESENT and 17 UNKNOWN in 17.0 s -- other_pc_only, sweep_red, sync_task_missing and others that describe the first
PC. report() called sense() with no profile, and ingest() entered a peer-named detector the same way. The page
answers the whole tailnet, so the wrong reading was the one a peer or a panel would be given.

WHAT THIS DRIVES, both ways, on fixture detectors only (no real detector, remedy, ledger or node is touched):
  R  report(): a detector the profile marks as not applying is not entered and reads ABSENT; the report names it
     under not_applicable_here; with no profile argument it reads this machine's own profile (the route's call
     shape); with the home profile, or no file, everything applies as before; an unreadable file hides nothing;
     a takeover guard cannot be switched off by a profile.
  I  ingest(): a peer-named condition that does not apply here is declined without entering its detector; on a
     machine whose profile says the highway does not repair, a condition present here too is raised and NO
     remedy is entered, dry or not; the home profile acts as before.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import covenant_highway as H

HERE = os.path.dirname(os.path.abspath(__file__))
results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def call(fn, *a, **k):
    """(value, None) or (None, 'Type: text'): a signature that does not take `machine` yet is a FAIL, not a crash."""
    try:
        return fn(*a, **k), None
    except Exception as e:                                        # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, str(e)[:120])


def main():
    os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = tempfile.mktemp(suffix="_a464_last_sense.json")
    work = tempfile.mkdtemp(prefix="a464_")
    led = os.path.join(work, "highway.jsonl")
    entered, ran = [], []

    def det(name, state):
        def fn(health=None, **kwargs):
            entered.append(name)
            return {"state": state, "measured": {"fixture": name}}
        return fn

    def spy(measured, dry_run=True):
        ran.append({"dry_run": dry_run})
        return True, "spy ran"

    real_detectors, real_remedy = dict(H.DETECTORS), dict(H.REMEDIES["rotate_log"])
    old_env = os.environ.get("COVENANT_MACHINE_PROFILE")
    NOT_HERE = {"acts_here": False, "not_applicable": {"other_pc_only": "this PC hosts node D only"}, "source": "file",
                "refused": [], "sha": "fixture", "why": "a second PC: sensing only"}
    HOME = {"acts_here": True, "not_applicable": {}, "why": "", "source": "none", "refused": [], "sha": ""}
    try:
        H.DETECTORS.clear()
        H.DETECTORS.update({"other_pc_only": det("other_pc_only", H.PRESENT), "log_bloat": det("log_bloat", H.PRESENT),
                            "head_commitment_broken": det("head_commitment_broken", H.ABSENT)})
        H.REMEDIES["rotate_log"] = dict(real_remedy, fn=spy)
        # A fixture detector must reach no real remedy (a fixture named after a real condition once walked into the
        # real restart; here the suite checks that itself before anything is driven).
        reach = sorted(rn for rn, r in H.REMEDIES.items() if set(r["for"]) & set(H.DETECTORS) and r["fn"] is not spy)
        check("A464.S0 the only remedy any fixture detector can reach is this suite's spy", not reach, str(reach))
        if reach:
            raise SystemExit("A464: a fixture detector can reach a real remedy; nothing was driven")

        # ---- R: report()
        del entered[:]
        rep, err = call(H.report, node_id="t", health={}, ledger=led, machine=NOT_HERE)
        rep = rep or {}
        cond = rep.get("conditions") or {}
        check("A464.R1 a detector the profile marks as not applying is NOT ENTERED by report()",
              err is None and "other_pc_only" not in entered, err or str(entered))
        check("A464.R1 ...and reads ABSENT, while one that applies is still measured",
              cond.get("other_pc_only") == H.ABSENT and cond.get("log_bloat") == H.PRESENT, json.dumps(cond))
        check("A464.R2 the report NAMES what does not apply here, so ABSENT is not read as 'measured and clear'",
              rep.get("not_applicable_here") == ["other_pc_only"], str(rep.get("not_applicable_here")))
        check("A464.R2 ...names only: the profile's reasons are not sent",
              "hosts node D" not in json.dumps(rep), json.dumps(rep)[:160])
        check("A464.R2 ...and the conditions are still state words only",
              bool(cond) and all(v in (H.PRESENT, H.ABSENT, H.UNKNOWN) for v in cond.values()), json.dumps(cond))

        # the route's call shape: no machine argument at all -> this machine's own profile
        prof = os.path.join(work, "machine.json")
        with open(prof, "w", encoding="utf-8") as fh:
            json.dump({"acts_here": False, "why": "a second PC: sensing only",
                       "not_applicable": {"other_pc_only": "this PC hosts node D only"}}, fh)
        os.environ["COVENANT_MACHINE_PROFILE"] = prof
        del entered[:]
        rep2, err = call(H.report, node_id="t", health={}, ledger=led)
        cond2 = (rep2 or {}).get("conditions") or {}
        check("A464.R3 with NO machine argument (how /hwy/state calls it) report() reads this machine's own profile",
              err is None and "other_pc_only" not in entered and cond2.get("other_pc_only") == H.ABSENT
              and (rep2 or {}).get("not_applicable_here") == ["other_pc_only"], err or json.dumps(cond2))

        # mutation, in the suite: the home profile, handed in, makes everything apply again
        del entered[:]
        rep3, err = call(H.report, node_id="t", health={}, ledger=led, machine=HOME)
        check("A464.R4 mutation: with the home profile the same detector IS entered and reads what it measures",
              err is None and "other_pc_only" in entered and ((rep3 or {}).get("conditions") or {}).get("other_pc_only") == H.PRESENT
              and (rep3 or {}).get("not_applicable_here") == [], err or str(entered))

        os.environ["COVENANT_MACHINE_PROFILE"] = os.path.join(work, "no-such-file.json")
        del entered[:]
        rep4, err = call(H.report, node_id="t", health={}, ledger=led)
        check("A464.R5 no profile file is the machine this was written for: everything applies, as before",
              err is None and sorted(set(entered)) == ["head_commitment_broken", "log_bloat", "other_pc_only"]
              and (rep4 or {}).get("not_applicable_here") == [], err or str(entered))

        broken = os.path.join(work, "broken.json")
        with open(broken, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        os.environ["COVENANT_MACHINE_PROFILE"] = broken
        del entered[:]
        rep5, err = call(H.report, node_id="t", health={}, ledger=led)
        check("A464.R6 a profile that cannot be read hides NOTHING: every detector is entered",
              err is None and "other_pc_only" in entered and (rep5 or {}).get("not_applicable_here") == [], err or str(entered))

        guard = os.path.join(work, "guard.json")
        with open(guard, "w", encoding="utf-8") as fh:
            json.dump({"acts_here": False, "why": "w", "not_applicable": {
                "head_commitment_broken": "switched off by a file", "other_pc_only": "this PC hosts node D only"}}, fh)
        os.environ["COVENANT_MACHINE_PROFILE"] = guard
        del entered[:]
        rep6, err = call(H.report, node_id="t", health={}, ledger=led)
        check("A464.R7 a profile cannot switch off a takeover guard in a report either: it is measured",
              err is None and "head_commitment_broken" in entered
              and "head_commitment_broken" not in ((rep6 or {}).get("not_applicable_here") or ["head_commitment_broken"]),
              err or str(entered))

        # ---- I: ingest()
        peer = {"node": "peer", "conditions": {"other_pc_only": H.PRESENT, "log_bloat": H.PRESENT, "made_up": H.PRESENT}}
        del entered[:], ran[:]
        out, err = call(H.ingest, peer, dry_run=False, ledger=led, cooldown_s=0, machine=NOT_HERE)
        did = {d["condition"]: d for d in (out or {}).get("did", [])}
        check("A464.I1 a peer's condition that does not apply here is declined WITHOUT entering its detector",
              err is None and did.get("other_pc_only", {}).get("action") == "declined" and "other_pc_only" not in entered
              and "does not apply" in did.get("other_pc_only", {}).get("why", ""), err or json.dumps(did.get("other_pc_only")))
        check("A464.I2 on a machine that does not repair, a condition present here too is RAISED",
              err is None and did.get("log_bloat", {}).get("action") == "raised", err or json.dumps(did.get("log_bloat")))
        check("A464.I2 ...and no remedy is entered, though the caller said dry_run=False", not ran, str(ran))
        check("A464.I2 ...and nothing is written to the ledger for it", not os.path.exists(led) or not H.read_ledger(led),
              str(os.path.exists(led)))
        check("A464.I3 a detector this tree does not have is ignored, as before",
              did.get("made_up", {}).get("action") == "ignored", json.dumps(did.get("made_up")))

        os.environ["COVENANT_MACHINE_PROFILE"] = prof
        del entered[:], ran[:]
        out, err = call(H.ingest, peer, dry_run=True, ledger=led)
        did = {d["condition"]: d for d in (out or {}).get("did", [])}
        check("A464.I4 with NO machine argument (how /hwy/report calls it) ingest() reads this machine's own profile",
              err is None and "other_pc_only" not in entered and did.get("other_pc_only", {}).get("action") == "declined"
              and did.get("log_bloat", {}).get("action") == "raised" and not ran, err or json.dumps(did))

        del entered[:], ran[:]
        out, err = call(H.ingest, peer, dry_run=False, ledger=led, cooldown_s=0, machine=HOME)
        did = {d["condition"]: d for d in (out or {}).get("did", [])}
        check("A464.I5 mutation: with the home profile this node measures the condition itself and acts on ITS reading",
              err is None and "log_bloat" in entered and bool(ran) and ran[0]["dry_run"] is False,
              err or json.dumps(did.get("log_bloat")))
        check("A464.I5 ...a condition with no reversible remedy is raised there, as before",
              err is None and "other_pc_only" in entered and did.get("other_pc_only", {}).get("action") == "raised",
              err or json.dumps(did.get("other_pc_only")))

        # An outside read (2026-11-21) found the first form tested truthiness: a profile handed in by a caller with
        # acts_here "no" (a string, so truthy) repaired. machine_profile() only ever returns True or False, so the
        # wire was not affected; a caller's own dict was.
        for odd in ("no", "false", 1, "True", [True], {"yes": 1}):
            del entered[:], ran[:]
            out, err = call(H.ingest, peer, dry_run=False, ledger=led, cooldown_s=0,
                            machine=dict(HOME, acts_here=odd))
            did = {d["condition"]: d for d in (out or {}).get("did", [])}
            check("A464.I6 acts_here=%r is not True: the condition is raised and no remedy is entered" % (odd,),
                  err is None and did.get("log_bloat", {}).get("action") == "raised" and not ran,
                  err or json.dumps(did.get("log_bloat")))
    finally:
        H.DETECTORS.clear()
        H.DETECTORS.update(real_detectors)
        H.REMEDIES["rotate_log"] = real_remedy
        if old_env is None:
            os.environ.pop("COVENANT_MACHINE_PROFILE", None)
        else:
            os.environ["COVENANT_MACHINE_PROFILE"] = old_env

    # ---- W: the two routes call them with no profile of their own, so the default above is what the wire gets
    with open(os.path.join(HERE, "covenant_unified_v8.py"), encoding="utf-8") as fh:
        core = fh.read()
    check("A464.W1 /hwy/state calls report() with no machine override",
          core.count("_hw.report(") == 1 and "_hw.report(node_id=self.node.node_id)" in core)
    check("A464.W1 /hwy/report calls ingest() dry and with no machine override",
          core.count("_hw.ingest(") == 1 and "_hw.ingest(peer, dry_run=True)" in core)

    failed = [n for n, ok in results if not ok]
    print(f"\nA464: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
