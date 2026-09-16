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
                             dry_run=False, ledger=led, cooldown_s=0)
        check("H1a a PROPOSE_ONLY remedy is not executed", row["outcome"] == "proposed", row["outcome"])
        check("H1a ...and its function is never entered", not calls, str(calls))

        # MUTATION: the same remedy, same function, CLASS changed -- and its
        # subject changed too, because two separate guards refuse this remedy
        # and a mutation that isolates neither proves nothing. The class is
        # what H1a is about; the subject is H1i's, below.
        H.REMEDIES["install_on_phone"] = dict(real, fn=spy_remedy(calls), klass=H.AUTO_REVERSIBLE,
                                              kind="stateless", touches=["a temp file"])
        row = H.apply_remedy("install_on_phone", present(), "app_build_gap",
                             dry_run=False, ledger=led, cooldown_s=0)
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
        row = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, cooldown_s=0, ledger=led,
                             choices={"logs": "I want the full log kept for the audit"})
        check("H1b a remedy that touches an operator's choice refuses",
              row["outcome"] == "refused" and "operator chose" in row.get("why", ""), row.get("why", ""))
        check("H1b ...without entering the remedy", not calls, str(calls))
        # MUTATION: the choice is withdrawn.
        row = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, cooldown_s=0, ledger=led, choices={})
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
                             ledger=led, choices={}, cooldown_s=0)
        check("H1c a state-changing remedy with no undo refuses",
              row["outcome"] == "refused" and "undo" in row.get("why", ""), row.get("why", ""))
        check("H1c ...without entering the remedy", not calls, str(calls))
        H.REMEDIES["_fixture_no_undo"]["undo"] = "put it back"
        row = H.apply_remedy("_fixture_no_undo", present(), "log_bloat", dry_run=False,
                             ledger=led, choices={}, cooldown_s=0)
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
                       dry_run=False, ledger=led, cooldown_s=0)
        did = out["did"][0]
        check("H1d a peer's PRESENT is declined when this node measures ABSENT",
              did["action"] == "declined", json.dumps(did))
        check("H1d ...and nothing ran on the peer's word", not calls, str(calls))
        # MUTATION: the condition really is present here.
        H.DETECTORS["log_bloat"] = lambda health=None: {"state": H.PRESENT, "measured": {"fixture": True}}
        out = H.ingest({"node": "peer", "conditions": {"log_bloat": H.PRESENT}},
                       dry_run=False, ledger=led, cooldown_s=0)
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
    row = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=True, ledger=led, choices={}, cooldown_s=0)
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
                         "app_build_gap", dry_run=True, ledger=led, choices={}, cooldown_s=0)
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

    # ---- H1i: the line that does not move, whatever class a remedy claims
    calls = []
    real = dict(H.REMEDIES["install_on_phone"])
    try:
        # The class is flipped to the executable one AND made stateless, so the
        # only thing left refusing is what it TOUCHES.
        H.REMEDIES["install_on_phone"] = dict(real, fn=spy_remedy(calls),
                                              klass=H.AUTO_REVERSIBLE, kind="stateless")
        led = tmp_ledger()
        row = H.apply_remedy("install_on_phone", present(), "app_build_gap",
                             dry_run=False, cooldown_s=0, ledger=led, choices={})
        check("H1i a remedy touching the phone refuses even as AUTO_REVERSIBLE",
              row["outcome"] == "proposed" and not calls, "%s calls=%d" % (row["outcome"], len(calls)))
        check("H1i ...and says which subject it crossed",
              "phone" in row.get("why", ""), row.get("why", ""))
        # MUTATION: the same remedy, same class, touching something ordinary.
        H.REMEDIES["install_on_phone"] = dict(real, fn=spy_remedy(calls), klass=H.AUTO_REVERSIBLE,
                                              kind="stateless", touches=["a temp file"])
        row = H.apply_remedy("install_on_phone", present(), "app_build_gap",
                             dry_run=False, cooldown_s=0, ledger=led, choices={})
        check("H1i mutation: touching nothing protected -> it runs", bool(calls), row["outcome"])
        protected = [w for w in ("money", "trader", "rule", "judge", "phone", "key")
                     if w not in H.NEVER_AUTOMATIC]
        check("H1i money, the trader, the rules, the seats, the phone and keys are all on the line",
              not protected, str(protected))
    finally:
        H.REMEDIES["install_on_phone"] = real

    # ---- H1j: the pass does not kill its own caller
    calls = []
    real_rw = dict(H.REMEDIES["restart_watchdog"])
    real_det = H.DETECTORS.get("watchdog_stale")
    try:
        H.REMEDIES["restart_watchdog"] = dict(real_rw, fn=spy_remedy(calls))
        H.DETECTORS["watchdog_stale"] = lambda health=None: {"state": H.PRESENT, "measured": {"fixture": True}}
        led = tmp_ledger()
        only = {"watchdog_stale": H.DETECTORS["watchdog_stale"]}
        saved, H.DETECTORS = H.DETECTORS, only
        try:
            H.run_once(dry_run=False, ledger=led, cooldown_s=0)
            check("H1j run_once excludes the watchdog's own restart by default", not calls, str(calls))
            H.run_once(dry_run=False, exclude=(), ledger=led, cooldown_s=0)
            check("H1j mutation: asked for explicitly, it runs", bool(calls), str(len(calls)))
        finally:
            H.DETECTORS = saved
    finally:
        H.REMEDIES["restart_watchdog"] = real_rw
        if real_det:
            H.DETECTORS["watchdog_stale"] = real_det

    # ---- H1m: the hourly cooldown, learned from the first live hour
    calls = []
    real_rl = dict(H.REMEDIES["rotate_log"])
    try:
        H.REMEDIES["rotate_log"] = dict(real_rl, fn=spy_remedy(calls))
        led = tmp_ledger()
        H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, ledger=led, choices={})
        row2 = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, ledger=led, choices={})
        rows = [r for r in H.read_ledger(led) if r.get("remedy") == "rotate_log"]
        check("H1m an identical attempt inside the hour is not repeated",
              len(calls) == 1 and row2.get("repeat") is True, "calls=%d repeat=%s" % (len(calls), row2.get("repeat")))
        check("H1m ...and writes no second row -- the ledger records changes, not ticks",
              len(rows) == 1, "%d rows" % len(rows))
        row3 = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, ledger=led,
                              choices={}, cooldown_s=0)
        check("H1m mutation: asked for explicitly (cooldown_s=0) it runs again",
              len(calls) == 2 and not row3.get("repeat"), "calls=%d" % len(calls))
    finally:
        H.REMEDIES["rotate_log"] = real_rl

    # ---- H1o: a remedy whose effect is asynchronous is not graded on the spot
    calls = []
    H.REMEDIES["_fixture_async"] = {"fn": spy_remedy(calls), "klass": H.AUTO_REVERSIBLE,
                                    "for": ["log_bloat"], "kind": "stateless", "async": True,
                                    "touches": ["a build runner"],
                                    "benefit": {"gains": ["x"], "cost": ["y"], "irreversible": []}}
    real_det = H.DETECTORS.get("log_bloat")
    try:
        H.DETECTORS["log_bloat"] = lambda health=None: {"state": H.PRESENT, "measured": {}}
        led = tmp_ledger()
        r1 = H.apply_remedy("_fixture_async", present(), "log_bloat", dry_run=False,
                            ledger=led, choices={}, cooldown_s=0)
        r2 = H.apply_remedy("_fixture_async", present(), "log_bloat", dry_run=False,
                            ledger=led, choices={}, cooldown_s=0)
        check("H1o an async remedy records 'started', not a grade",
              r1["outcome"] == "started" and r2["outcome"] == "started",
              "%s, %s" % (r1["outcome"], r2["outcome"]))
        check("H1o ...so two runs do not quarantine a remedy that works",
              not H.quarantined("_fixture_async", led))
        # MUTATION: drop the async flag and the same two runs condemn it, which
        # is exactly what happened to fetch_build on its first live hour.
        H.REMEDIES["_fixture_async"].pop("async")
        H.apply_remedy("_fixture_async", present(), "log_bloat", dry_run=False,
                       ledger=led, choices={}, cooldown_s=0)
        H.apply_remedy("_fixture_async", present(), "log_bloat", dry_run=False,
                       ledger=led, choices={}, cooldown_s=0)
        check("H1o mutation: graded on the spot, two runs quarantine it",
              H.quarantined("_fixture_async", led))

        # The same function, graded differently per condition: synchronous for
        # one, asynchronous for the other. fetch_build is both -- it clears
        # build_stale_on_pc at once, and phone_build_behind_core only after the
        # runner has finished building.
        H.REMEDIES["_fixture_async"]["for"] = ["log_bloat", "height_lag"]
        H.REMEDIES["_fixture_async"]["async_for"] = ["height_lag"]
        led2 = tmp_ledger()
        sync_row = H.apply_remedy("_fixture_async", present(), "log_bloat", dry_run=False,
                                  ledger=led2, choices={}, cooldown_s=0)
        async_row = H.apply_remedy("_fixture_async", present(), "height_lag", dry_run=False,
                                   ledger=led2, choices={}, cooldown_s=0)
        check("H1o one remedy, graded synchronously for one condition and not the other",
              sync_row["outcome"] == "did not fix" and async_row["outcome"] == "started",
              "%s / %s" % (sync_row["outcome"], async_row["outcome"]))
    finally:
        H.REMEDIES.pop("_fixture_async", None)
        if real_det:
            H.DETECTORS["log_bloat"] = real_det

    # ---- H1p: a remedy that spends his money asks for a longer budget
    calls = []
    real_d = dict(H.REMEDIES["dispatch_phone_build"])
    try:
        H.REMEDIES["dispatch_phone_build"] = dict(real_d, fn=spy_remedy(calls))
        led = tmp_ledger()
        H.apply_remedy("dispatch_phone_build", present(), "phone_build_behind_core",
                       dry_run=False, ledger=led, choices={})
        # Two hours later by the ledger's own clock: the global hour would let
        # this through; the remedy's own day must not.
        rows = H.read_ledger(led)
        rows[-1]["at"] = rows[-1]["at"] - 7200
        with open(led, "w", encoding="utf-8") as fh:
            for r_ in rows:
                fh.write(json.dumps(r_) + chr(10))
        again = H.apply_remedy("dispatch_phone_build", present(), "phone_build_behind_core",
                               dry_run=False, ledger=led, choices={})
        check("H1p a CI dispatch is not repeated two hours later -- it has a daily budget",
              len(calls) == 1 and again.get("repeat") is True,
              "calls=%d repeat=%s" % (len(calls), again.get("repeat")))
        check("H1p ...and that budget is declared on the remedy, not hidden in the engine",
              H.REMEDIES["dispatch_phone_build"].get("cooldown_s", 0) >= 86400,
              str(real_d.get("cooldown_s")))
        check("H1p ...and its cost is declared where a person reads it",
              any("Actions" in c or "minute" in c for c in real_d["benefit"]["cost"]),
              str(real_d["benefit"]["cost"]))
    finally:
        H.REMEDIES["dispatch_phone_build"] = real_d

    # ---- H1n: a quarantine is cleared on the record, never by forgetting
    led = tmp_ledger()
    for _ in range(2):
        H.write_ledger({"remedy": "fetch_build", "outcome": "did not fix"}, led)
    check("H1n two failures quarantine it", H.quarantined("fetch_build", led))
    H.recalibrate("fetch_build", "graded against the wrong condition", led)
    check("H1n recalibrate() clears it", not H.quarantined("fetch_build", led))
    kept = [r for r in H.read_ledger(led) if r.get("outcome") == "did not fix"]
    said = [r for r in H.read_ledger(led) if r.get("outcome") == "recalibrated"]
    check("H1n ...and the failures are still in the file, with the reason beside them",
          len(kept) == 2 and len(said) == 1 and said[0].get("why"), "%d kept, %d notes" % (len(kept), len(said)))

    # ---- H1k / H1l: the wire
    import covenant_unified_v8 as cov
    import covenant_daily_plan as dp
    m = cov.CovenantUnifiedMaster("H1", host="127.0.0.1", port=5393, p2p_port=5394,
                                  db_path=tempfile.mktemp(suffix="_h1.db"))
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    client = m.api.app.test_client()

    r = client.get("/hwy/state", environ_base={"REMOTE_ADDR": "192.168.1.50"})
    check("H1k /hwy/state refuses a LAN address", r.status_code == 403, str(r.status_code))
    r = client.get("/hwy/state", environ_base={"REMOTE_ADDR": "100.86.158.1"})
    body = r.get_json() or {}
    check("H1k /hwy/state answers the tailnet", r.status_code == 200, str(r.status_code))
    check("H1k ...with states and a recent-row shape, nothing wider",
          isinstance(body.get("state", {}).get("conditions"), dict)
          and all(set(row) <= {"t", "remedy", "detector", "outcome", "why"}
                  for row in body.get("recent", [])),
          json.dumps(body)[:120])

    r = client.post("/hwy/report", data=json.dumps({"node": "peer", "conditions": {}}),
                    environ_base={"REMOTE_ADDR": "100.86.158.1"})
    check("H1l /hwy/report refuses an unsigned offer", r.status_code == 403, str(r.status_code))

    seen = {}
    real_ingest, real_verify = H.ingest, dp.verify_signed
    try:
        H.ingest = lambda peer, dry_run=True, ledger=None: seen.update(dry_run=dry_run, peer=peer) or {"did": []}
        dp.verify_signed = lambda *a, **k: (True, "test-peer")
        import base64 as _b64
        hdrs = {"X-Operator-Pubkey": _b64.b64encode(b"-----BEGIN PUBLIC KEY-----\\n").decode()}
        r = client.post("/hwy/report", data=json.dumps({"node": "peer", "conditions": {"log_bloat": H.PRESENT}}),
                        headers=hdrs, environ_base={"REMOTE_ADDR": "100.86.158.1"})
        check("H1l a signed offer is accepted", r.status_code == 200, str(r.status_code))
        check("H1l ...and is considered with dry_run FORCED true -- a packet cannot make this node act",
              seen.get("dry_run") is True, json.dumps(seen)[:120])
        check("H1l ...and the answer says so", "acted on nothing" in ((r.get_json() or {}).get("note", "")),
              (r.get_json() or {}).get("note", ""))
    finally:
        H.ingest, dp.verify_signed = real_ingest, real_verify

    failed = [n for n, ok in results if not ok]
    print(f"\nH1: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
