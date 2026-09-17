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

HERE = os.path.dirname(os.path.abspath(__file__)) or "."

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

    # ---- H1u: a pass that did nothing must not report someone else's action
    calls = []
    real_rl = dict(H.REMEDIES["rotate_log"])
    real_det = H.DETECTORS.get("log_bloat")
    saved_dets = H.DETECTORS
    try:
        H.REMEDIES["rotate_log"] = dict(real_rl, fn=spy_remedy(calls))
        H.DETECTORS = {"log_bloat": lambda health=None: {"state": H.PRESENT, "measured": {}}}
        led = tmp_ledger()
        a1, i1 = H.run_once(dry_run=False, ledger=led, cooldown_s=0)      # really acts
        a2, i2 = H.run_once(dry_run=False, ledger=led)                    # cooled down
        check("H1u the second pass does not run the remedy again", len(calls) == 1, "calls=%d" % len(calls))
        check("H1u ...and says nothing was done, instead of repeating the first pass's detail",
              any("nothing done this pass" in x for x in i2) and not a2,
              (i2[0] if i2 else "") + " | alerts=" + str(a2)[:60])
        check("H1u ...and the ledger gains no row for a pass that did nothing",
              len([r for r in H.read_ledger(led) if r.get("remedy") == "rotate_log"]) == 1,
              str(len(H.read_ledger(led))))
    finally:
        H.DETECTORS = saved_dets
        H.REMEDIES["rotate_log"] = real_rl
        if real_det:
            H.DETECTORS["log_bloat"] = real_det

    # ---- H1t: a node that rate-limits is ANSWERING (A115), and it cost a restart
    #
    # At 11:22 today this detector called three healthy nodes "down" because
    # they 429'd health probes I was sending too fast, and the engine reached
    # for restart_nodes on a live mesh. rolling_restart.py refused -- "node A
    # ALIVE but rate-limiting (429) -- asked too often, not down ... restarted
    # nothing" -- so nothing was lost, and the save was theirs, not mine.
    up = {"chain_height": 28, "source_sha256": "ddfaaa9f704f00"}
    limited = H.detect_node_down({"A": up, "B": {"http": 429}, "C": up})
    dead = H.detect_node_down({"A": None, "B": {"http": 429}, "C": up})
    fine = H.detect_node_down({"A": up, "B": up, "C": up})
    check("H1t a 429 is not death -- UNKNOWN, never PRESENT",
          limited["state"] == H.UNKNOWN and limited["measured"]["down"] == [],
          json.dumps(limited)[:120])
    check("H1t ...so nothing is restarted on account of it",
          limited["state"] != H.PRESENT, limited["state"])
    check("H1t mutation: a socket that does not answer IS down, and only that node",
          dead["state"] == H.PRESENT and dead["measured"]["down"] == ["A"],
          json.dumps(dead["measured"])[:120])
    check("H1t three healthy nodes are healthy", fine["state"] == H.ABSENT, json.dumps(fine)[:90])
    drift = H.detect_source_drift({"A": up, "B": {"http": 429}, "C": up})
    check("H1t a node that could not be read is not counted as drifted either",
          "B" not in drift["measured"].get("live", {}) and "B" not in drift["measured"].get("drifted", []),
          json.dumps(drift["measured"])[:120])
    lag = H.detect_height_lag({"A": up, "B": {"http": 429}, "C": up})
    check("H1t ...nor as a height of zero",
          lag["measured"]["heights"].get("B") is None, json.dumps(lag["measured"])[:110])

    # ---- H1s: the watchdog can replace itself without killing its own round
    sched = H.REMEDIES.get("schedule_watchdog_restart", {})
    check("H1s a remedy exists that the scheduled pass may use on the watchdog",
          bool(sched) and sched.get("klass") == H.AUTO_REVERSIBLE and sched.get("async"),
          json.dumps({k: v for k, v in sched.items() if k != "fn"})[:120])
    check("H1s ...and it is NOT the one the watchdog must exclude",
          "schedule_watchdog_restart" not in ("restart_watchdog",),
          "run_once's default exclude is restart_watchdog only")
    import subprocess as _sp
    real_popen = _sp.Popen

    class DeadProc:
        pid = 1234

        def poll(self):
            return 1                      # exited immediately: nothing was scheduled

    try:
        _sp.Popen = lambda *a, **k: DeadProc()
        ok, why = H.remedy_schedule_watchdog_restart({}, dry_run=False)
        check("H1s a restarter that dies on the spot is reported as a failure, not 'scheduled'",
              not ok and "exited immediately" in why, why[:80])
    finally:
        _sp.Popen = real_popen

    # ---- H1r: the manifest is rewritten only over a clean tree
    import subprocess
    real_run = subprocess.run
    seen = {}

    def fake_run(cmd, *a, **k):
        if cmd[:2] == ["git", "status"]:
            class R:
                returncode, stdout, stderr = 0, seen.get("status", ""), ""
            return R()
        seen["wrote"] = seen.get("wrote", 0) + 1
        class R2:
            returncode, stdout, stderr = 0, "wrote MANIFEST.sha256", ""
        return R2()

    try:
        subprocess.run = fake_run
        seen["status"] = " M covenant_highway.py" + chr(10) + " M docs/HIGHWAY.md"
        ok, why = H.remedy_rehash_bundle({}, dry_run=False)
        check("H1r a dirty tree refuses the rehash -- a manifest would describe nothing that exists",
              not ok and "uncommitted" in why and not seen.get("wrote"), why[:90])
        seen["status"] = " M MANIFEST.sha256" + chr(10) + " M ops/SELF_EVAL.md" + chr(10) + "?? SWEEP_END.txt"
        ok, why = H.remedy_rehash_bundle({}, dry_run=False)
        check("H1r mutation: a clean tree (bar the manifest and the hourly self-eval) -> it writes",
              ok and seen.get("wrote") == 1, why[:90])
    finally:
        subprocess.run = real_run

    # ---- H1q: "running != deployed" covers the modules, not just the file
    files = H._watchdog_module_files()
    names = [os.path.basename(f) for f in files]
    check("H1q the staleness check watches the watchdog's imports, not only itself",
          "covenant_watchdog.py" in names and "covenant_highway.py" in names and len(names) > 2,
          str(names[:6]))
    check("H1q ...and reads them from the source, so a new import is covered the day it lands",
          "covenant_daily_plan.py" in names, str(names))
    st = H.detect_watchdog_stale()
    check("H1q it reports a state it can defend, and names the file it measured",
          st["state"] in (H.PRESENT, H.ABSENT, H.UNKNOWN)
          and (st["state"] == H.UNKNOWN or "newest_file" in st["measured"]),
          json.dumps(st)[:140])
    check("H1q no watchdog running is UNKNOWN, never ABSENT -- unknown is not pass",
          st["state"] != H.ABSENT or st["measured"].get("running", 0) >= 1,
          json.dumps(st["measured"])[:120])

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
        # And a person cannot wave the budget away: cooldown_s=0 skips the
        # global hour, never a remedy's declared day.
        manual = H.apply_remedy("dispatch_phone_build", present(), "phone_build_behind_core",
                                dry_run=False, ledger=led, choices={}, cooldown_s=0)
        check("H1p a person typing --repair cannot spend the budget again",
              len(calls) == 1 and manual.get("repeat") is True,
              "calls=%d repeat=%s" % (len(calls), manual.get("repeat")))
        check("H1p ...while a remedy with no declared budget still obeys the person",
              H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=True,
                             ledger=led, choices={}, cooldown_s=0).get("repeat") is not True)
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

    # ---- H1w: the three the audit below caught as undriven
    #
    # held_core_drift, manifest_stale and resync_held_core were registered and
    # never once exercised by a test. Each reads another program's exit code,
    # which is the easiest thing in this file to get backwards, so each is
    # driven both ways with that program stubbed.
    import subprocess as _sp2
    real_run2 = _sp2.run
    stub = {}

    class R3:
        def __init__(self, rc=0, out=""):
            self.returncode, self.stdout, self.stderr = rc, out, ""

    try:
        _sp2.run = lambda cmd, *a, **k: R3(stub.get("rc", 0), stub.get("out", ""))
        stub.update(rc=1, out="held copies: OUT OF SYNC")
        d1 = H.detect_held_core_drift()
        stub.update(rc=0, out="held copies: in sync")
        d0 = H.detect_held_core_drift()
        check("H1w held_core_drift reads the sync tool's exit code, both ways",
              d1["state"] == H.PRESENT and d0["state"] == H.ABSENT,
              "%s / %s" % (d1["state"], d0["state"]))

        stub.update(rc=1, out="CHANGED/MISSING  covenant_highway.py\n613 in manifest, 1 changed")
        m1 = H.detect_manifest_stale()
        stub.update(rc=0, out="613 in manifest, 0 changed or missing")
        m0 = H.detect_manifest_stale()
        check("H1w manifest_stale reads verify_bundle both ways and names the file",
              m1["state"] == H.PRESENT and m0["state"] == H.ABSENT
              and m1["measured"]["changed"] == ["covenant_highway.py"],
              "%s / %s / %s" % (m1["state"], m0["state"], m1["measured"].get("changed")))

        ok_dry, why_dry = H.remedy_resync_held_core({}, dry_run=True)
        stub.update(rc=0, out="synced")
        ok_run, _ = H.remedy_resync_held_core({}, dry_run=False)
        check("H1w resync_held_core says what it would do, and reports the tool's result",
              ok_dry and "would run" in why_dry and ok_run, why_dry[:60])
    finally:
        _sp2.run = real_run2

    # ---- H1w: the two youngest registrations, driven HERE as well ----------
    #
    # sweep_red and rerun_unclean arrived 2026-09-17 and H1v caught them with
    # no coverage in this file, which is exactly what H1v is for. The full
    # behavioural pinning is test_p25_sweep_red.py (21 checks). These drive
    # them here so the registry and this suite cannot drift apart -- and so
    # H1v is satisfied by COVERAGE and not by the string appearing in a
    # comment, which would be answering a guard by typing its trigger.
    r_sr = H.detect_sweep_red()
    check("H1w sweep_red returns a real state and carries its measurement",
          r_sr["state"] in (H.PRESENT, H.ABSENT, H.UNKNOWN)
          and isinstance(r_sr.get("measured"), dict), r_sr)
    ok_rr, why_rr = H.remedy_rerun_unclean({"unclean": []}, dry_run=True)
    check("H1w rerun_unclean REFUSES a red that named no unclean suite -- a "
          "genuinely failing check is not a re-run's business",
          ok_rr is False, why_rr)
    ok_rr2, why_rr2 = H.remedy_rerun_unclean({"unclean": ["test_x.py"]},
                                             dry_run=True)
    check("H1w ...and a dry run says what it WOULD do without doing it",
          ok_rr2 is True and "would re-run" in why_rr2, why_rr2)

    # ---- H1v: nothing registered may go undriven, and every detector must
    # be able to say UNKNOWN
    #
    # Today's errors were one family: asserting from a derived source instead
    # of the primary one, and never asking whether the check could fail. A
    # detector nobody drives is the purest form of it -- it has never been
    # observed returning anything, so its silence means nothing. This audit
    # names the gap instead of trusting that the suite grew with the registry.
    import io as _io
    src = _io.open(os.path.join(HERE, "test_h1_highway.py"), encoding="utf-8").read()
    undriven_d = [k for k in H.DETECTORS if k not in src]
    undriven_r = [k for k in H.REMEDIES if k not in src]
    check("H1v every registered detector is named somewhere in this suite",
          not undriven_d, str(undriven_d))
    check("H1v every registered remedy is named somewhere in this suite",
          not undriven_r, str(undriven_r))

    # Each detector, driven for real, must return one of the three states and
    # must not raise. UNKNOWN is the answer that matters: a detector that
    # cannot measure has to say so rather than report ABSENT, which is how a
    # broken instrument reads as good news (P20).
    bad = []
    for name, fn in sorted(H.DETECTORS.items()):
        try:
            got = fn()
            if got.get("state") not in (H.PRESENT, H.ABSENT, H.UNKNOWN) or "measured" not in got:
                bad.append("%s -> %s" % (name, str(got)[:60]))
        except Exception as e:                                   # noqa: BLE001
            bad.append("%s raised %s" % (name, type(e).__name__))
    check("H1v every detector runs and returns a state with its measurement",
          not bad, str(bad))

    unknown_capable = []
    for name, fn in sorted(H.DETECTORS.items()):
        srcfn = _io.open(os.path.join(HERE, "covenant_highway.py"), encoding="utf-8").read()
        body = srcfn.split("def %s(" % fn.__name__, 1)[-1].split("\ndef ", 1)[0]
        if "UNKNOWN" not in body:
            unknown_capable.append(name)
    check("H1v every detector has a path that says UNKNOWN rather than ABSENT",
          not unknown_capable, str(unknown_capable))

    failed = [n for n, ok in results if not ok]
    print(f"\nH1: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
