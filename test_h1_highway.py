#!/usr/bin/env python3
"""
test_h1_highway.py -- H1 (2026-09-16): the mycelial highway's five invariants.

WHAT THE HIGHWAY IS. covenant_highway.py senses conditions on this machine,
repairs the ones it is allowed to repair, and shares what worked as an OFFER to
peers over the tailnet. The whole design rests on five promises about what it
will not do. A promise in a docstring is worth nothing, so each one here is
mutation-tested: the guard is removed and the refusal must DISAPPEAR, then put
back and the refusal must return. A guard nobody has watched fail is not a
guard (M31, and the 35-of-36 fake guards of 2026-09-09).

THE FIVE
  H1a  class. The ENGINE refuses PROPOSE_ONLY -- it does not trust each remedy
       to refuse on its own. The refused remedy's function is never entered.
  H1b  an operator's explicit choice (ops/OPERATOR_CHOICES.json) is untouchable.
       A125: a fix of mine silently overrode a scope he had chosen, and only a
       full sweep found it.
  H1c  stateless, or an undo on record. Anything else is refused.
  H1d  no node may be COMMANDED. A peer reporting a condition changes nothing:
       the receiving node measures for itself and declines when it is absent.
  H1e  a remedy measured failing twice is quarantined, and a later success
       clears it. The "bot that learns" is this counter and nothing more.

AND TWO AUDITS OF THE REGISTRY ITSELF
  H1f  every AUTO_REVERSIBLE remedy is stateless or carries an undo, and every
       remedy declares mutual benefit with BOTH gains and cost. A benefit
       block listing only gains is advertising.
  H1g  a refusal under H1a is not a dead end: the row carries what was
       measured, the mutual-benefit block, and what the covenant's own running
       seat said about doing it -- including HELD reported as held, because an
       "I don't know" read as a No is an abstention turned into a veto.
  H1h  a report shares detector names, states and outcome counts -- no paths,
       no file contents, no money, no people.

    python test_h1_highway.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import covenant_highway as H

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def tmp_ledger():
    return tempfile.mktemp(suffix="_highway.jsonl")


def present(measured=None):
    return {"state": H.PRESENT, "measured": measured or {"why": "a fixture"}}


def spy_remedy(calls, ok=True):
    def fn(measured, dry_run=True):
        calls.append({"measured": measured, "dry_run": dry_run})
        return ok, "spy ran"
    return fn


def main():
    # ---- H1a: the engine refuses the class, and the function is never entered
    calls = []
    real = dict(H.REMEDIES["install_on_phone"])
    try:
        H.REMEDIES["install_on_phone"] = dict(real, fn=spy_remedy(calls))
        led = tmp_ledger()
        row = H.apply_remedy("install_on_phone", present(), "app_build_gap",
                             dry_run=False, ledger=led)
        check("H1a a PROPOSE_ONLY remedy is not executed", row["outcome"] == "proposed", row["outcome"])
        check("H1a ...and its function is never entered", not calls, str(calls))

        # MUTATION: the same remedy, same function, class changed.
        H.REMEDIES["install_on_phone"] = dict(real, fn=spy_remedy(calls), klass=H.AUTO_REVERSIBLE,
                                              kind="stateless")
        row = H.apply_remedy("install_on_phone", present(), "app_build_gap",
                             dry_run=False, ledger=led)
        check("H1a mutation: class flipped -> the engine runs it", bool(calls) and row["outcome"] != "proposed",
              "%s calls=%d" % (row["outcome"], len(calls)))
    finally:
        H.REMEDIES["install_on_phone"] = real

    # ---- H1b: an operator's choice is untouchable
    calls = []
    real_rl = dict(H.REMEDIES["rotate_log"])
    try:
        H.REMEDIES["rotate_log"] = dict(real_rl, fn=spy_remedy(calls))
        led = tmp_ledger()
        row = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, ledger=led,
                             choices={"logs": "I want the full log kept for the audit"})
        check("H1b a remedy that touches an operator's choice refuses",
              row["outcome"] == "refused" and "operator chose" in row.get("why", ""), row.get("why", ""))
        check("H1b ...without entering the remedy", not calls, str(calls))
        # MUTATION: the choice is withdrawn.
        row = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, ledger=led, choices={})
        check("H1b mutation: choice withdrawn -> it proceeds", bool(calls), row["outcome"])
    finally:
        H.REMEDIES["rotate_log"] = real_rl

    # ---- H1c: stateless, or an undo on record
    calls = []
    H.REMEDIES["_fixture_no_undo"] = {"fn": spy_remedy(calls), "klass": H.AUTO_REVERSIBLE,
                                      "for": ["log_bloat"], "kind": "undoable", "touches": [],
                                      "benefit": {"gains": ["x"], "cost": ["y"], "irreversible": []}}
    try:
        led = tmp_ledger()
        row = H.apply_remedy("_fixture_no_undo", present(), "log_bloat", dry_run=False,
                             ledger=led, choices={})
        check("H1c a state-changing remedy with no undo refuses",
              row["outcome"] == "refused" and "undo" in row.get("why", ""), row.get("why", ""))
        check("H1c ...without entering the remedy", not calls, str(calls))
        H.REMEDIES["_fixture_no_undo"]["undo"] = "put it back"
        row = H.apply_remedy("_fixture_no_undo", present(), "log_bloat", dry_run=False,
                             ledger=led, choices={})
        check("H1c mutation: an undo on record -> it proceeds", bool(calls), row["outcome"])
    finally:
        H.REMEDIES.pop("_fixture_no_undo", None)

    # ---- H1d: no node may be commanded
    calls = []
    real_det = H.DETECTORS.get("log_bloat")
    real_rl = dict(H.REMEDIES["rotate_log"])
    try:
        H.REMEDIES["rotate_log"] = dict(real_rl, fn=spy_remedy(calls))
        H.DETECTORS["log_bloat"] = lambda health=None: {"state": H.ABSENT, "measured": {"fixture": True}}
        led = tmp_ledger()
        out = H.ingest({"node": "peer", "conditions": {"log_bloat": H.PRESENT}},
                       dry_run=False, ledger=led)
        did = out["did"][0]
        check("H1d a peer's PRESENT is declined when this node measures ABSENT",
              did["action"] == "declined", json.dumps(did))
        check("H1d ...and nothing ran on the peer's word", not calls, str(calls))
        # MUTATION: the condition really is present here.
        H.DETECTORS["log_bloat"] = lambda health=None: {"state": H.PRESENT, "measured": {"fixture": True}}
        out = H.ingest({"node": "peer", "conditions": {"log_bloat": H.PRESENT}},
                       dry_run=False, ledger=led)
        check("H1d mutation: present HERE too -> this node acts, on its own measurement",
              bool(calls), json.dumps(out["did"]))
    finally:
        H.REMEDIES["rotate_log"] = real_rl
        if real_det:
            H.DETECTORS["log_bloat"] = real_det

    # ---- H1e: quarantine after two measured failures, cleared by a success
    led = tmp_ledger()
    for _ in range(2):
        H.write_ledger({"remedy": "rotate_log", "outcome": "did not fix"}, led)
    check("H1e two measured failures quarantine a remedy", H.quarantined("rotate_log", led))
    row = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=True, ledger=led, choices={})
    check("H1e ...and the engine refuses it, saying why",
          row["outcome"] == "refused" and "quarantin" in row.get("why", ""), row.get("why", ""))
    H.write_ledger({"remedy": "rotate_log", "outcome": "fixed"}, led)
    check("H1e mutation: a later success clears the quarantine", not H.quarantined("rotate_log", led))

    # ---- H1f: the registry audits
    bad_undo = [n for n, r in H.REMEDIES.items()
                if r["klass"] == H.AUTO_REVERSIBLE and r.get("kind") != "stateless" and not r.get("undo")]
    check("H1f every AUTO_REVERSIBLE remedy is stateless or has an undo", not bad_undo, str(bad_undo))
    thin = [n for n, r in H.REMEDIES.items()
            if not (r.get("benefit", {}).get("gains") and r.get("benefit", {}).get("cost"))]
    check("H1f every remedy declares BOTH gains and cost", not thin, str(thin))
    no_det = [n for n, r in H.REMEDIES.items() if not set(r["for"]) & set(H.DETECTORS)]
    check("H1f every remedy answers a detector that exists", not no_det, str(no_det))

    # ---- H1g: the refusal is a referral, with the running seat's own words
    led = tmp_ledger()
    row = H.apply_remedy("install_on_phone", present({"alerts": ["the phone is two builds behind"]}),
                         "app_build_gap", dry_run=True, ledger=led, choices={})
    cov = row.get("covenant", {})
    check("H1g the proposal carries what was measured", bool(row.get("measured")), json.dumps(row.get("measured"))[:80])
    check("H1g ...the mutual benefit, cost included",
          bool(row.get("mutual_benefit", {}).get("cost")), json.dumps(row.get("mutual_benefit"))[:80])
    check("H1g ...and the covenant's own seat, named and quoted",
          bool(cov.get("seat")) and bool(cov.get("said")) and cov.get("principles_put_to_it", 0) > 0,
          json.dumps(cov)[:120])
    check("H1g a HELD seat is reported as held, never as a refusal",
          cov.get("verdict") in ("held -- no finding", "clean", "flagged for review", H.UNKNOWN),
          str(cov.get("verdict")))

    # ---- H1h: a report is narrow
    rep = H.report(node_id="test", health={"A": None, "B": None, "C": None}, ledger=led)
    blob = json.dumps(rep)
    leaks = [w for w in (os.sep + "Users", "holdings", "balance", "pubkey", "BEGIN ", ".db", ".key")
             if w in blob]
    check("H1h a report carries no path, key, database or money word", not leaks, str(leaks))
    check("H1h ...and says out loud that it is an offer",
          "not an instruction" in rep.get("offer", ""), rep.get("offer", ""))
    check("H1h ...naming states only, not measurements",
          all(v in (H.PRESENT, H.ABSENT, H.UNKNOWN) for v in rep["conditions"].values()),
          json.dumps(rep["conditions"]))

    failed = [n for n, ok in results if not ok]
    print(f"\nH1: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
