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

import inspect
import json
import os
import sys
import tempfile
import time

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
    # Every pass this suite drives saves its sensed states (save_last_sense, 2026-09-25); they go
    # to a temp file, never the live ops/highway_last_sense.json the PC page reads.
    os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = tempfile.mktemp(suffix="_h1_last_sense.json")
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
    #
    # A160 (2026-09-20): THIS CHECK WAS KILLING THE PRODUCTION WATCHDOG. Two
    # remedies are registered for watchdog_stale and only one was a stub; the
    # other, schedule_watchdog_restart, ran for real from the sweep's staged
    # copy, and its detached restarter stopped every process whose command
    # line carried the bare filename -- the production watchdog included --
    # then started a replacement from the temporary directory the sweep was
    # about to delete. Seven watchdog deaths sat in the last ninety seconds of
    # a sweep before anyone looked. So now: EVERY remedy for the condition is
    # a spy, subprocess is fenced so nothing can spawn even if a future remedy
    # is added unstubbed, and the fence is checked, not assumed.
    import subprocess as _sp
    calls, sched, spawned = [], [], []

    class _NoSpawn(object):
        def __init__(self, args, **kw):
            spawned.append(("Popen", args))
            self.pid = 0

        def poll(self):
            return None

    def _no_run(args, **kw):
        spawned.append(("run", args))
        return _sp.CompletedProcess(args, 0, "", "")

    real_rw = dict(H.REMEDIES["restart_watchdog"])
    real_sw = dict(H.REMEDIES["schedule_watchdog_restart"])
    real_det = H.DETECTORS.get("watchdog_stale")
    real_popen, real_run = _sp.Popen, _sp.run
    try:
        H.REMEDIES["restart_watchdog"] = dict(real_rw, fn=spy_remedy(calls))
        H.REMEDIES["schedule_watchdog_restart"] = dict(real_sw, fn=spy_remedy(sched))
        _sp.Popen, _sp.run = _NoSpawn, _no_run
        H.DETECTORS["watchdog_stale"] = lambda health=None: {"state": H.PRESENT, "measured": {"fixture": True}}
        led = tmp_ledger()
        only = {"watchdog_stale": H.DETECTORS["watchdog_stale"]}
        saved, H.DETECTORS = H.DETECTORS, only
        try:
            H.run_once(dry_run=False, ledger=led, cooldown_s=0)
            check("H1j run_once excludes the watchdog's own restart by default", not calls, str(calls))
            check("H1j the scheduled (detached) restart is the one it may use on itself", bool(sched), str(len(sched)))
            H.run_once(dry_run=False, exclude=(), ledger=led, cooldown_s=0)
            check("H1j mutation: asked for explicitly, it runs", bool(calls), str(len(calls)))
            unstubbed = [n for n, r in H.REMEDIES.items()
                         if "watchdog_stale" in r["for"] and r["fn"].__name__ != "fn"]
            check("H1j every remedy registered for watchdog_stale is a stub in this test",
                  not unstubbed, str(unstubbed))
            check("H1j nothing real was spawned by either pass -- the production watchdog "
                  "is not this test's to stop", not spawned, str(spawned)[:200])
        finally:
            H.DETECTORS = saved
    finally:
        _sp.Popen, _sp.run = real_popen, real_run
        H.REMEDIES["restart_watchdog"] = real_rw
        H.REMEDIES["schedule_watchdog_restart"] = real_sw
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
        # H1m2 (2026-09-25): a DRY RUN is not an attempt. A rehearsal row held the real
        # node restart for an hour on the live ledger (18:45:50). Both ways: a dry row does
        # not hold a real run; it still holds another dry run, so rehearsals stay quiet.
        led2 = tmp_ledger()
        H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=True, ledger=led2, choices={})
        n0 = len(calls)
        real_after_dry = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=False, ledger=led2, choices={})
        check("H1m2 a real repair is not held by a rehearsal's row: it runs",
              len(calls) == n0 + 1 and not real_after_dry.get("repeat"), "calls=%d repeat=%s" % (len(calls) - n0, real_after_dry.get("repeat")))
        led3 = tmp_ledger()
        H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=True, ledger=led3, choices={})
        dry_again = H.apply_remedy("rotate_log", present(), "log_bloat", dry_run=True, ledger=led3, choices={})
        check("H1m2 ...while a second rehearsal inside the hour is still held (no second row)",
              dry_again.get("repeat") is True and len(H.read_ledger(led3)) == 1, dry_again.get("repeat"))
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

        # ---- H1x (2026-09-19): a remedy that DECLINES is graded "held", never
        # "did not fix". Every quarantine in the live ledger that day was a
        # correct refusal graded as a failure (rehash_bundle: "uncommitted
        # tracked changes"; restart_nodes: "already on the disk source").
        H.REMEDIES["_fixture_decline"] = {"fn": lambda m, dry_run=False: (False, "declined: the tree is dirty"),
                                          "klass": H.AUTO_REVERSIBLE, "for": ["log_bloat"], "kind": "stateless",
                                          "touches": ["nothing"],
                                          "benefit": {"gains": ["x"], "cost": ["y"], "irreversible": []}}
        led2 = tmp_ledger()
        d1 = H.apply_remedy("_fixture_decline", present(), "log_bloat", dry_run=False, ledger=led2, choices={}, cooldown_s=0)
        d2 = H.apply_remedy("_fixture_decline", present(), "log_bloat", dry_run=False, ledger=led2, choices={}, cooldown_s=0)
        check("H1x a remedy that returns ran=False is graded 'held', with the condition still on the record",
              d1["outcome"] == "held" and d2["outcome"] == "held" and d1.get("after") == H.PRESENT and d1.get("ran") is False,
              (d1.get("outcome"), d1.get("after"), d1.get("ran")))
        check("H1x ...and two declines do not quarantine it", not H.quarantined("_fixture_decline", led2))
        # MUTATION: the same remedy claiming it RAN (True) with the condition still
        # PRESENT is the real failure, graded as before, and two of them quarantine.
        H.REMEDIES["_fixture_decline"]["fn"] = lambda m, dry_run=False: (True, "ran, changed nothing")
        m1 = H.apply_remedy("_fixture_decline", present(), "log_bloat", dry_run=False, ledger=led2, choices={}, cooldown_s=0)
        H.apply_remedy("_fixture_decline", present(), "log_bloat", dry_run=False, ledger=led2, choices={}, cooldown_s=0)
        check("H1x mutation: ran=True with the condition still PRESENT is 'did not fix', and two of them quarantine",
              m1["outcome"] == "did not fix" and H.quarantined("_fixture_decline", led2), m1.get("outcome"))
        H.REMEDIES.pop("_fixture_decline", None)

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
    # H1aa (2026-09-25, "everything we do must be designed to run independently"): a node on the
    # right core whose imports changed under it is drift too, so the watchdog restarts it
    # without a person. Both ways, against the real disk fingerprints.
    import covenant_watchdog as _W
    _disk, _imp = _W.disk_source_sha12(), _W.disk_imports_sha12()
    _same = {"source_sha256": _disk, "imports_sha12": _imp, "chain_height": 5}
    _stale = dict(_same, imports_sha12="000000000000")
    d_same = H.detect_source_drift({"A": _same, "B": _same, "C": _same})
    d_imp = H.detect_source_drift({"A": _same, "B": _stale, "C": _same})
    check("H1aa a node on the disk core whose imports changed under it is drift (PRESENT, that node only)",
          d_imp["state"] == H.PRESENT and d_imp["measured"]["imports_drifted"] == ["B"] and d_imp["measured"]["drifted"] == ["B"],
          json.dumps(d_imp["measured"])[:160])
    check("H1aa ...and three nodes current on core and imports are ABSENT", d_same["state"] == H.ABSENT, json.dumps(d_same["measured"])[:160])
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
    # A255 (2026-10-04): "clean" is now verify_bundle's own answer
    # (--write-if-clean=HEAD: every HASHED file as HEAD holds it), not a
    # `git status` count that included the outputs it never hashes. H1r pins
    # that the highway OBEYS that answer; test_a255_runtime_outputs.py U*
    # pins that the answer is right, against real git in a scratch repository.
    import subprocess
    real_run = subprocess.run
    seen = {}

    def fake_run(cmd, *a, **k):
        seen.setdefault("calls", []).append(list(cmd))
        rc, out = seen.get("answer", (0, "wrote MANIFEST.sha256"))
        if rc == 0 and "--dry" not in cmd:
            seen["wrote"] = seen.get("wrote", 0) + 1
        class R:
            returncode, stdout, stderr = rc, out, ""
        return R()

    try:
        subprocess.run = fake_run
        seen["answer"] = (3, "left alone: 2 hashed file(s) on disk differ from HEAD (covenant_highway.py, "
                             "docs/HIGHWAY.md) -- a manifest written now would describe content no commit contains")
        ok, why = H.remedy_rehash_bundle({}, dry_run=False)
        check("H1r a dirty tree refuses the rehash -- a manifest would describe nothing that exists",
              not ok and "left alone" in why and "covenant_highway.py" in why and not seen.get("wrote"), why[:90])
        check("H1r ...and it asks verify_bundle against HEAD, not against an index no commit is using",
              any("--write-if-clean=HEAD" in c for c in seen["calls"]), str(seen["calls"][-1:])[:120])
        seen["answer"] = (0, "wrote MANIFEST.sha256 over 900 files")
        ok, why = H.remedy_rehash_bundle({}, dry_run=False)
        check("H1r mutation: a clean tree -> it writes, exactly once",
              ok and seen.get("wrote") == 1, why[:90])
        seen["calls"] = []
        ok, why = H.remedy_rehash_bundle({}, dry_run=True)
        check("H1r a dry run passes --dry and writes nothing",
              ok and seen.get("wrote") == 1 and all("--dry" in c for c in seen["calls"]), str(seen["calls"])[:120])
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
    r = client.get("/hwy/state", environ_base={"REMOTE_ADDR": "100.72.0.10"})
    body = r.get_json() or {}
    check("H1k /hwy/state answers the tailnet", r.status_code == 200, str(r.status_code))
    check("H1k ...with states and a recent-row shape, nothing wider",
          isinstance(body.get("state", {}).get("conditions"), dict)
          and all(set(row) <= {"t", "remedy", "detector", "outcome", "why"}
                  for row in body.get("recent", [])),
          json.dumps(body)[:120])

    r = client.post("/hwy/report", data=json.dumps({"node": "peer", "conditions": {}}),
                    environ_base={"REMOTE_ADDR": "100.72.0.10"})
    check("H1l /hwy/report refuses an unsigned offer", r.status_code == 403, str(r.status_code))

    seen = {}
    real_ingest, real_verify = H.ingest, dp.verify_signed
    try:
        H.ingest = lambda peer, dry_run=True, ledger=None: seen.update(dry_run=dry_run, peer=peer) or {"did": []}
        dp.verify_signed = lambda *a, **k: (True, "test-peer")
        import base64 as _b64
        hdrs = {"X-Operator-Pubkey": _b64.b64encode(b"-----BEGIN PUBLIC KEY-----\\n").decode()}
        r = client.post("/hwy/report", data=json.dumps({"node": "peer", "conditions": {"log_bloat": H.PRESENT}}),
                        headers=hdrs, environ_base={"REMOTE_ADDR": "100.72.0.10"})
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
        # A214b: this detector no longer shells out -- it was 2.20 s of the
        # highway's 10.78 s of sensing, nearly all of it re-parsing thirteen
        # copies of a 12,700-line core, every sixty seconds. It calls
        # held_core_check() in process now, so this drives THAT seam, the
        # detector's own. A stub of subprocess.run would pass here while
        # measuring nothing, which is exactly the A65 shape this file exists
        # to refuse.
        d1 = H.detect_held_core_drift(check=lambda: (1, "held copies: OUT OF SYNC"))
        d0 = H.detect_held_core_drift(check=lambda: (0, "held copies: in sync"))
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

    # ---- H1ci: public_ci_red (A232), with a stub API and a fixed clock -----
    # H1v drives the real one against the network; these pin its behaviour
    # without it, each way.
    _t0 = 1790000000.0

    def _run(i, concl, hours_ago, status="completed"):
        return {"id": i, "head_sha": "%07x" % i + "0" * 33, "event": "push", "status": status,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_t0 - hours_ago * 3600)),
                "conclusion": concl, "html_url": "https://example.test/run/%d" % i}

    def _api(runs, lines, calls):
        def get(path):
            calls.append(path)
            if "/actions/workflows/" in path:
                return {"workflow_runs": runs}
            if path.endswith("/jobs"):
                return {"jobs": [{"id": 11, "conclusion": "success"}, {"id": 12, "conclusion": "failure"}]}
            if "/check-runs/12/annotations" in path:
                return [{"title": "", "message": "Node.js 20 is deprecated"},
                        {"title": "covenant_one.py --ci", "message": "~".join(lines)}]
            return []
        return get

    def _down(path):
        raise OSError("offline")

    # Every call below passes a stub `tell`: the real one writes the direct line to his phone.
    _told = []

    def _tell(text, why):
        _told.append(text)
        return {"id": "stub"}

    _cdir = tempfile.mkdtemp(prefix="h1ci_")
    _red = [_run(9, "cancelled", 0.1), _run(8, "failure", 0.5), _run(7, "failure", 1.5),
            _run(6, "success", 3.0), _run(5, "failure", 4.0)]
    _ann = ["RESULT: FAIL. Something is wrong and it is named above.",
            "suites not clean    1  -> test_pv1_provenance.py",
            "      | FAIL  PV1.6 a file outside the tree entirely is foreign"]
    # A260, second cycle (2026-10-05): a change of verdict is told only when a SECOND read, CI_RETRY_S later,
    # agrees. Every check below that expects him to be told now takes two reads; the first read alone is pinned.
    _R = H.CI_RETRY_S + 1
    _calls = []
    r_one = H.detect_public_ci_red(get=_api(_red, _ann, _calls), now=_t0,
                                   cache=os.path.join(_cdir, "red.json"), tell=_tell)
    check("H1ci A260 ONE read of red tells him nothing: the confirmed state (green, none told) stands, the change "
          "is pending and the next read is brought forward",
          r_one["state"] == H.ABSENT and "unconfirmed" in r_one["measured"] and not _told
          and json.load(open(os.path.join(_cdir, "red.json")))["next_at"] <= _t0 + H.CI_RETRY_S,
          (r_one["state"], r_one["measured"].get("unconfirmed"), _told))
    r_ci = H.detect_public_ci_red(get=_api(_red, _ann, _calls), now=_t0 + _R,
                                  cache=os.path.join(_cdir, "red.json"), tell=_tell)
    m_ci = r_ci["measured"]
    check("H1ci the newest FINISHED run on main failed -> PRESENT: the cancelled one skipped, the failing check named "
          "from the public annotation, the red counted back to the last green",
          r_ci["state"] == H.PRESENT and m_ci["newest"]["sha"] == "0000008"
          and "FAIL  PV1.6 a file outside the tree entirely is foreign" in m_ci["failing"] and m_ci["red_runs"] == 2
          and m_ci["red_since_sha"] == "0000007" and m_ci["red_since_is"] == "exact", m_ci)
    check("H1ci ...and it tells him on the direct line, naming the check",
          len(_told) == 1 and "red on main" in _told[0] and "PV1.6" in _told[0], _told)
    _n = len(_calls)
    r_ci2 = H.detect_public_ci_red(get=_api(_red, [], _calls), now=_t0 + _R + 60,
                                   cache=os.path.join(_cdir, "red.json"), tell=_tell)
    check("H1ci within its 30 minutes it asks the API nothing, the annotation was fetched once, and he is not told twice",
          len(_calls) == _n and r_ci2["state"] == H.PRESENT and len(_told) == 1
          and sum(1 for c in _calls if "/annotations" in c) == 1
          and any("PV1.6" in x for x in r_ci2["measured"]["failing"]), (_calls, _told))
    for _dt in (_R + H.CI_EVERY_S + 1, 2 * _R + H.CI_EVERY_S + 1):
        r_ci = H.detect_public_ci_red(get=_api([_run(11, "success", 0.1)] + _red, [], _calls), now=_t0 + _dt,
                                      cache=os.path.join(_cdir, "red.json"), tell=_tell)
    check("H1ci broken the other way: when main turns green (and the next read agrees) he is told once that it is green again",
          r_ci["state"] == H.ABSENT and len(_told) == 2 and "green again" in _told[1], _told)
    for _dt in (0, _R):
        r_ci = H.detect_public_ci_red(get=_api([_run(4, "failure", 0.5), _run(3, "failure", 1.0)], [], []),
                                      now=_t0 + _dt, cache=os.path.join(_cdir, "allred.json"), tell=_tell)
    check("H1ci no green run in the page: the start of the red is said as 'at least', not as exact -- to him too",
          r_ci["state"] == H.PRESENT and r_ci["measured"]["red_since_is"] == "at least"
          and any("at least 2 finished run(s) since 0000003 or earlier" in t for t in _told[-1:]),
          (r_ci["measured"], _told[-1:]))
    _green = [_run(10, "success", 0.5), _run(8, "failure", 1.0)]
    _k = len(_told)
    r_ci = H.detect_public_ci_red(get=_api(_green, [], []), now=_t0, cache=os.path.join(_cdir, "green.json"),
                                  tell=_tell)
    check("H1ci broken the other way: the newest finished run green -> ABSENT, whatever came before it, and nothing said",
          r_ci["state"] == H.ABSENT and len(_told) == _k, r_ci["measured"])
    for _dt in (0, _R):
        r_ci = H.detect_public_ci_red(get=_api([_run(10, "success", 7.0)], [], []), now=_t0 + _dt,
                                      cache=os.path.join(_cdir, "silent.json"), tell=_tell)
    check("H1ci green, but nothing on main finished for over 6 h -> PRESENT: a missing run is not a passing run",
          r_ci["state"] == H.PRESENT and "missing run" in r_ci["measured"].get("why", ""), r_ci["measured"])
    r_ci = H.detect_public_ci_red(get=_down, now=_t0, cache=os.path.join(_cdir, "none.json"), tell=_tell)
    check("H1ci an API that cannot be read -> UNKNOWN, never ABSENT",
          r_ci["state"] == H.UNKNOWN and "offline" in str(r_ci["measured"].get("error")), r_ci["measured"])
    H.detect_public_ci_red(get=_api(_green, [], []), now=_t0, cache=os.path.join(_cdir, "old.json"), tell=_tell)
    r_ci = H.detect_public_ci_red(get=_down, now=_t0 + 3 * 3600, cache=os.path.join(_cdir, "old.json"), tell=_tell)
    check("H1ci broken the other way: a green read three hours old with the API down is UNKNOWN, not the cached green",
          r_ci["state"] == H.UNKNOWN, r_ci["measured"])
    # A260 (2026-10-05): the API answered this query with a page from nine days earlier, twice in two hours,
    # and he was told "red on main" on a run 215.8 h old. Time on main only moves forward.
    _k = len(_told)
    H.detect_public_ci_red(get=_api([_run(21, "success", 0.5), _run(20, "failure", 1.0)], [], []), now=_t0,
                           cache=os.path.join(_cdir, "stale.json"), tell=_tell)
    r_ci = H.detect_public_ci_red(get=_api([_run(5, "failure", 215.8), _run(4, "success", 216.0)], [], []),
                                  now=_t0 + H.CI_EVERY_S + 1, cache=os.path.join(_cdir, "stale.json"), tell=_tell)
    check("H1ci A260 a page whose newest finished run is OLDER than one already read is refused: the fresher green "
          "stands, the read is named stale, and he is told nothing",
          r_ci["state"] == H.ABSENT and r_ci["measured"]["newest"]["sha"] == "0000015" and len(_told) == _k
          and "stale page" in str(json.load(open(os.path.join(_cdir, "stale.json"))).get("error")),
          (r_ci["state"], r_ci["measured"].get("newest"), _told[_k:]))
    for _dt in (2 * (H.CI_EVERY_S + H.CI_RETRY_S), 2 * (H.CI_EVERY_S + H.CI_RETRY_S) + _R):
        r_ci = H.detect_public_ci_red(get=_api([_run(22, "failure", 0.1), _run(21, "success", 0.5)], [], []),
                                      now=_t0 + _dt, cache=os.path.join(_cdir, "stale.json"), tell=_tell)
    check("H1ci A260 broken the other way: a NEWER red is not stale -- PRESENT once the next read agrees, and he is told",
          r_ci["state"] == H.PRESENT and r_ci["measured"]["newest"]["sha"] == "0000016" and len(_told) == _k + 1,
          (r_ci["state"], r_ci["measured"].get("newest"), _told[_k:]))
    # THE 09:28Z CASE: the guard's seed was itself a stale page, so a second stale page that was NEWER than the
    # seed -- but still a day old -- passed it, and "nothing has finished" was told. Each stale page now stays
    # pending; the fresh read that follows agrees with what he was told, and nothing is said.
    _k = len(_told)
    _s = os.path.join(_cdir, "seed.json")
    _seen_states = []
    for _dt, _page in ((0, [_run(30, "success", 216.0)]), (_R, [_run(31, "success", 31.0)]),
                       (2 * _R, [_run(32, "success", 0.2), _run(31, "success", 31.0)])):
        _seen_states.append(H.detect_public_ci_red(get=_api(_page, [], []), now=_t0 + _dt, cache=_s,
                                                   tell=_tell)["state"])
    check("H1ci A260 two stale pages in a row, each a different 'nothing finished', then a fresh green: never told, "
          "never PRESENT, and nothing left pending",
          len(_told) == _k and _seen_states == [H.ABSENT, H.ABSENT, H.ABSENT]
          and not json.load(open(_s)).get("pending"), (_seen_states, _told[_k:]))
    check("H1ci public_ci_red has no remedy: the fix is a change to the code, and PRESENT reaches him as an alert",
          not [n for n, rr in H.REMEDIES.items() if "public_ci_red" in (rr.get("for") or [])])

    # ---- H1pb: phone_build_failed (2026-09-27), the same stub API and clock --
    # dispatch_phone_build was told "accepted (HTTP 204)" and nothing ever read
    # whether the build it asked for arrived: three failed on a full artifact
    # quota while the highway looked busy.
    def _papi(runs, calls, steps=("Run actions/upload-artifact@v4",),
              reason="Failed to CreateArtifact: Artifact storage quota has been hit."):
        def get(path):
            calls.append(path)
            if "/actions/workflows/android.yml/runs" in path:
                return {"workflow_runs": runs}
            if path.endswith("/jobs"):
                return {"jobs": [{"id": 21, "conclusion": "success", "steps": []},
                                 {"id": 22, "conclusion": "failure",
                                  "steps": [{"name": "Build APK", "conclusion": "success"}]
                                  + [{"name": s, "conclusion": "failure"} for s in steps]}]}
            if "/check-runs/22/annotations" in path:
                return [{"annotation_level": "warning", "message": "Node.js 20 is deprecated"},
                        {"annotation_level": "failure", "message": reason}]
            return []
        return get

    _pbr = [_run(9, "cancelled", 0.1), _run(8, "failure", 0.5), _run(7, "failure", 24.5),
            _run(6, "success", 110.0), _run(5, "failure", 120.0)]
    _pc = []
    _k = len(_told)
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_papi(_pbr, _pc), now=_t0, cache=os.path.join(_cdir, "pb.json"), tell=_tell)
    m_pb = r_pb["measured"]
    check("H1pb the newest FINISHED phone build failed -> PRESENT: the cancelled one skipped, the failing step and "
          "the runner's own reason named, the failures counted back to the last success",
          r_pb["state"] == H.PRESENT and m_pb["newest"]["sha"] == "0000008"
          and m_pb["failing_steps"] == ["Run actions/upload-artifact@v4"]
          and m_pb["reasons"] == ["Failed to CreateArtifact: Artifact storage quota has been hit."]
          and m_pb["failed_runs"] == 2 and m_pb["failing_since_is"] == "exact"
          and m_pb["last_success"] == _run(6, "success", 110.0)["created_at"], m_pb)
    check("H1pb ...and it tells him once on the direct line, naming the reason and that rebuilds change nothing",
          len(_told) == _k + 1 and "quota has been hit" in _told[-1] and "change nothing" in _told[-1], _told[_k:])
    _n = len(_pc)
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_papi(_pbr, _pc), now=_t0 + 60, cache=os.path.join(_cdir, "pb.json"),
                                       tell=_tell)
    check("H1pb within its 30 minutes it asks the API nothing, and he is not told twice",
          len(_pc) == _n and r_pb["state"] == H.PRESENT and len(_told) == _k + 1
          and r_pb["measured"]["reasons"], (_pc[_n:], _told[_k:]))
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_papi([_run(12, "failure", 0.2)] + _pbr, _pc),
                                       now=_t0 + H.CI_EVERY_S + 1, cache=os.path.join(_cdir, "pb.json"), tell=_tell)
    check("H1pb another failure in the SAME streak is not a new episode: he is not told again",
          r_pb["state"] == H.PRESENT and r_pb["measured"]["failed_runs"] == 3 and len(_told) == _k + 1, _told[_k:])
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_papi([_run(13, "success", 0.1), _run(12, "failure", 0.2)] + _pbr, _pc),
                                       now=_t0 + 2 * H.CI_EVERY_S + 2, cache=os.path.join(_cdir, "pb.json"), tell=_tell)
    check("H1pb broken the other way: a build succeeds -> ABSENT, and he is told once that it succeeded again",
          r_pb["state"] == H.ABSENT and len(_told) == _k + 2 and "succeeded again" in _told[-1], _told[_k:])
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_papi([_run(4, "failure", 0.5), _run(3, "failure", 1.0)], []),
                                       now=_t0, cache=os.path.join(_cdir, "pball.json"), tell=_tell)
    check("H1pb no success in the page: the start of the failures is said as 'at least'",
          r_pb["state"] == H.PRESENT and r_pb["measured"]["failing_since_is"] == "at least"
          and "at least 2 time(s)" in _told[-1], (r_pb["measured"], _told[-1:]))
    _k = len(_told)
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_papi([_run(10, "success", 0.5), _run(8, "failure", 1.0)], []),
                                       now=_t0, cache=os.path.join(_cdir, "pbgreen.json"), tell=_tell)
    check("H1pb broken the other way: the newest finished build succeeded -> ABSENT, and nothing said",
          r_pb["state"] == H.ABSENT and len(_told) == _k, r_pb["measured"])
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_down, now=_t0, cache=os.path.join(_cdir, "pbnone.json"), tell=_tell)
    check("H1pb an API that cannot be read (or no credential) -> UNKNOWN, never ABSENT",
          r_pb["state"] == H.UNKNOWN and "offline" in str(r_pb["measured"].get("error")), r_pb["measured"])
    H.detect_phone_build_failed(pipeline=True, get=_papi([_run(10, "success", 0.5)], []), now=_t0,
                                cache=os.path.join(_cdir, "pbold.json"), tell=_tell)
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_down, now=_t0 + 3 * 3600, cache=os.path.join(_cdir, "pbold.json"),
                                       tell=_tell)
    check("H1pb broken the other way: a success read three hours old with the API down is UNKNOWN, not the cache",
          r_pb["state"] == H.UNKNOWN, r_pb["measured"])
    # The mutation review of 2026-09-27 found each of the following could be broken with H1pb still green.
    _k = len(_told)
    _pc = []
    _seq = [_run(8, "failure", 0.5), _run(6, "success", 110.0)]
    H.detect_phone_build_failed(pipeline=True, get=_papi(_seq, _pc), now=_t0, cache=os.path.join(_cdir, "pb2.json"),
                                tell=_tell)
    H.detect_phone_build_failed(pipeline=True, get=_papi([_run(13, "success", 0.1)] + _seq, _pc),
                                now=_t0 + H.CI_EVERY_S + 1, cache=os.path.join(_cdir, "pb2.json"), tell=_tell)
    H.detect_phone_build_failed(pipeline=True, get=_papi([_run(14, "success", 0.05), _run(13, "success", 0.1)] + _seq,
                                _pc), now=_t0 + 2 * H.CI_EVERY_S + 2, cache=os.path.join(_cdir, "pb2.json"), tell=_tell)
    check("H1pb after 'succeeded again' a second success says nothing more (told is reset, not left on the streak)",
          len(_told) == _k + 2 and "succeeded again" in _told[-1], _told[_k:])
    _refused = []

    def _no(text, why):
        _refused.append(text)
        return None
    for i in range(3):
        H.detect_phone_build_failed(pipeline=True, get=_papi(_pbr, []), now=_t0 + i * (H.CI_EVERY_S + 1),
                                    cache=os.path.join(_cdir, "pbref.json"), tell=_no)
    check("H1pb a direct line that REFUSES is tried once per episode, not every round",
          len(_refused) == 1, _refused)
    _raised = []

    def _boom(text, why):
        _raised.append(text)
        raise OSError("outbox unwritable")
    r_pb = None
    for i in range(3):
        r_pb = H.detect_phone_build_failed(pipeline=True, get=_papi(_pbr, []), now=_t0 + i * (H.CI_EVERY_S + 1),
                                           cache=os.path.join(_cdir, "pbboom.json"), tell=_boom)
    check("H1pb a direct line that RAISES is caught, counted as a refusal, and not retried every round",
          len(_raised) == 1 and r_pb["state"] == H.PRESENT, (_raised, r_pb and r_pb["measured"]))
    _blocker = os.path.join(_cdir, "notadir")
    with open(_blocker, "w") as _fh:
        _fh.write("a file where the cache's directory should be")
    _pc, _k = [], len(_told)
    for i in range(4):
        H.detect_phone_build_failed(pipeline=True, get=_papi(_pbr, _pc), now=_t0 + 60 * i,
                                    cache=os.path.join(_blocker, "pb.json"), tell=_tell)
    check("H1pb a cache that cannot be written: four rounds a minute apart still read the API once and tell once",
          len([c for c in _pc if "/workflows/" in c]) == 1 and len(_told) == _k + 1, (_pc, _told[_k:]))
    _long = [_run(100 - i, "failure", 0.1 + i) for i in range(25)]
    _k = len(_told)
    for i in range(3):
        _page = ([_run(200 + j, "failure", 0.01 * (j + 1)) for j in range(i)] + _long)[:20]
        H.detect_phone_build_failed(pipeline=True, get=_papi(_page, []), now=_t0 + i * (H.CI_EVERY_S + 1),
                                    cache=os.path.join(_cdir, "pblong.json"), tell=_tell)
    check("H1pb a failing streak longer than the page is ONE episode: new failures pushing the oldest off the page "
          "do not tell him again", len(_told) == _k + 1, _told[_k:])
    _jc = []

    def _jobs_down(path):
        _jc.append(path)
        if "/actions/workflows/" in path:
            return {"workflow_runs": _pbr}
        raise OSError("jobs endpoint down")
    for i in range(5):
        H.detect_phone_build_failed(pipeline=True, get=_jobs_down, now=_t0 + 60 * i,
                                    cache=os.path.join(_cdir, "pbjobs.json"), tell=_tell)
    check("H1pb a jobs read that fails waits CI_RETRY_S: five rounds a minute apart ask the jobs endpoint once",
          len([c for c in _jc if c.endswith("/jobs")]) == 1, _jc)
    _pc = []
    r_pb = H.detect_phone_build_failed(pipeline=False, get=_papi(_pbr, _pc), now=_t0,
                                       cache=os.path.join(_cdir, "pbclone.json"), tell=_tell)
    check("H1pb on a PC that never fetched a build of the app repo (a second operator's clone) -> UNKNOWN, and the "
          "API and the credential are never touched (A142)",
          r_pb["state"] == H.UNKNOWN and not _pc and "not this operator" in r_pb["measured"]["why"], r_pb["measured"])
    import covenant_github_judge as _gj
    import urllib.request as _ur
    _seen = {}

    class _Resp:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.body

    def _open(req, timeout=None):
        _seen["auth"] = req.get_header("Authorization")
        return _Resp(b'{"workflow_runs": []}')
    _real = (_gj.token, _ur.urlopen, dict(_gj._CREDENTIAL_STORE_OK), dict(_gj._CACHE))
    try:
        _gj._CREDENTIAL_STORE_OK["allowed"] = False
        _gj._CACHE.pop("token", None)

        def _tok():
            _seen["allowed_during"] = _gj._CREDENTIAL_STORE_OK["allowed"]
            _gj._CACHE["token"] = "stubtok"
            return "stubtok"
        _gj.token, _ur.urlopen = _tok, _open
        H._phone_get("/x")
        check("H1pb the real _phone_get sends his credential as a Bearer header (a dropped header reads UNKNOWN "
              "forever against a private repository)", _seen.get("auth") == "Bearer stubtok", _seen)
        check("H1pb ...and leaves the process as it found it: the credential opt-in back to shut and nothing cached, "
              "so the NODE, which also runs sense(), is not opened by a detector (A21)",
              _seen.get("allowed_during") is True and _gj._CREDENTIAL_STORE_OK["allowed"] is False
              and "token" not in _gj._CACHE, (_seen, _gj._CREDENTIAL_STORE_OK))
        _gj.token = lambda: ""
        try:
            H._phone_get("/x")
            _raised_nc = False
        except RuntimeError as e:
            _raised_nc = "no GitHub credential" in str(e)
        check("H1pb broken the other way: with no credential _phone_get RAISES (so the reading is UNKNOWN), never "
              "an empty answer taken as a good read", _raised_nc)
    finally:
        _gj.token, _ur.urlopen = _real[0], _real[1]
        _gj._CREDENTIAL_STORE_OK.clear()
        _gj._CREDENTIAL_STORE_OK.update(_real[2])
        _gj._CACHE.clear()
        _gj._CACHE.update(_real[3])
    # ---- the second review (2026-09-27): each of these was a mutation that left H1 green ----
    import covenant_app_update as _AU
    _real_latest, _real_daemon = _AU.latest, H.DAEMON_READS
    try:
        _pc = []
        H.DAEMON_READS = False
        _AU.latest = lambda: {"run_url": "https://github.com/%s/actions/runs/1" % _AU.REPO}
        r_pb = H.detect_phone_build_failed(get=_papi(_pbr, _pc), now=_t0, cache=os.path.join(_cdir, "pbd0.json"),
                                           tell=_tell)
        check("H1pb outside the watchdog daemon (DAEMON_READS off) -> UNKNOWN, the API and his credential untouched "
              "-- so a node's request threads and every test (H1v too) never read it",
              r_pb["state"] == H.UNKNOWN and not _pc and "not the watchdog daemon" in r_pb["measured"]["why"],
              r_pb["measured"])
        H.DAEMON_READS = True
        r_pb = H.detect_phone_build_failed(get=_papi(_pbr, _pc), now=_t0, cache=os.path.join(_cdir, "pbd1.json"),
                                           tell=lambda t, w: {"id": "stub"})
        check("H1pb ...in the daemon, on the PC whose build record names the app repository, it reads",
              r_pb["state"] == H.PRESENT and _pc, r_pb["measured"])
        _pc = []
        _AU.latest = lambda: {"run_url": "https://github.com/someone-else/app/actions/runs/1",
                              "url": "https://github.com/%s" % _AU.REPO}
        r_pb = H.detect_phone_build_failed(get=_papi(_pbr, _pc), now=_t0, cache=os.path.join(_cdir, "pbd2.json"),
                                           tell=_tell)
        check("H1pb ...and in the daemon on a PC whose build came from another repository -> UNKNOWN, unread "
              "(the gate reads run_url, the field the fetch writes)",
              r_pb["state"] == H.UNKNOWN and not _pc, r_pb["measured"])
    finally:
        _AU.latest, H.DAEMON_READS = _real_latest, _real_daemon

    # Two processes share one cache (the watchdog and, before DAEMON_READS, a node): a memo that always
    # wins would replay a stale "told" over what the other process wrote.
    _k = len(_told)
    _p2 = os.path.join(_cdir, "pb2proc.json")
    _seqf = [_run(8, "failure", 0.5), _run(6, "success", 110.0)]
    _seqg = [_run(13, "success", 0.1)] + _seqf
    H.detect_phone_build_failed(pipeline=True, get=_papi(_seqf, []), now=_t0, cache=_p2, tell=_tell)
    _memo_a = dict(H._PHONE_MEMO[os.path.abspath(_p2)])
    H._PHONE_MEMO.pop(os.path.abspath(_p2))                        # process B: no memo of its own
    H.detect_phone_build_failed(pipeline=True, get=_papi(_seqg, []), now=_t0 + H.CI_EVERY_S + 1, cache=_p2,
                                tell=_tell)
    H._PHONE_MEMO[os.path.abspath(_p2)] = _memo_a                   # process A again, with its older memo
    H.detect_phone_build_failed(pipeline=True, get=_papi(_seqg, []), now=_t0 + 2 * H.CI_EVERY_S + 2, cache=_p2,
                                tell=_tell)
    check("H1pb two processes on one cache: after B said 'succeeded again', A's older memo does not say it again "
          "(the file wins unless this process failed to write it)",
          len(_told) == _k + 2 and "succeeded again" in _told[-1], _told[_k:])

    import stat as _stat
    _ro = os.path.join(_cdir, "pbro.json")
    with open(_ro, "w", encoding="utf-8") as _fh:
        json.dump({"runs": [{"id": 6, "sha": "0000006", "status": "completed", "conclusion": "success",
                             "created": _run(6, "success", 110.0)["created_at"]}],
                   "ok_at": _t0 - 10, "next_at": 0, "told": None}, _fh)
    os.chmod(_ro, _stat.S_IREAD)
    _k = len(_told)
    try:
        for i in range(121):
            H.detect_phone_build_failed(pipeline=True, get=_papi(_pbr, []), now=_t0 + 60 * i, cache=_ro, tell=_tell)
    finally:
        os.chmod(_ro, _stat.S_IREAD | _stat.S_IWRITE)
    check("H1pb a cache that can be READ but not written (a stale success in it): two hours of rounds tell him "
          "once, never alternating 'failed' and a false 'succeeded again'", len(_told) == _k + 1, _told[_k:])
    _k = len(_told)
    _bl2 = os.path.join(_cdir, "notadir2")
    with open(_bl2, "w") as _fh:
        _fh.write("x")
    for i in range(121):
        H.detect_phone_build_failed(pipeline=True, get=_papi(_pbr, []), now=_t0 + 60 * i,
                                    cache=os.path.join(_bl2, "pb.json"), tell=_tell)
    check("H1pb a cache that cannot be written at all: two hours of rounds (four API reads) still tell him once",
          len(_told) == _k + 1, _told[_k:])

    _jup = {"down": True}

    def _jobs_flaky(path):
        if "/actions/workflows/" in path:
            return {"workflow_runs": _pbr}
        if _jup["down"] and path.endswith("/jobs"):
            raise OSError("jobs endpoint down")
        return _papi(_pbr, [])(path)
    H.detect_phone_build_failed(pipeline=True, get=_jobs_flaky, now=_t0, cache=os.path.join(_cdir, "pbflaky.json"),
                                tell=lambda t, w: {"id": "stub"})
    _jup["down"] = False
    r_pb = H.detect_phone_build_failed(pipeline=True, get=_jobs_flaky, now=_t0 + H.CI_RETRY_S + 1,
                                       cache=os.path.join(_cdir, "pbflaky.json"), tell=lambda t, w: {"id": "stub"})
    check("H1pb broken the other way: after CI_RETRY_S a failed jobs read IS retried, and the step and reason arrive",
          r_pb["measured"]["failing_steps"] == ["Run actions/upload-artifact@v4"] and r_pb["measured"]["reasons"],
          r_pb["measured"])

    _k = len(_told)
    _ns = os.path.join(_cdir, "pbnew.json")
    H.detect_phone_build_failed(pipeline=True, get=_papi([_run(8, "failure", 5.0), _run(6, "success", 110.0)], []),
                                now=_t0, cache=_ns, tell=_tell)
    H.detect_phone_build_failed(pipeline=True, get=_papi([_run(10, "failure", 0.2), _run(9, "success", 1.0),
                                                          _run(8, "failure", 5.0), _run(6, "success", 110.0)], []),
                                now=_t0 + H.CI_EVERY_S + 1, cache=_ns, tell=_tell)
    check("H1pb a success BETWEEN two reads ends the streak: the next failure is a new episode and is told",
          len(_told) == _k + 2 and "failed 1 time(s)" in _told[-1], _told[_k:])

    _real2 = (_gj.token, _ur.urlopen, dict(_gj._CREDENTIAL_STORE_OK), dict(_gj._CACHE))
    try:
        _gj._CREDENTIAL_STORE_OK["allowed"] = True
        _gj._CREDENTIAL_STORE_OK["why"] = "an earlier opt-in of someone else's"
        _gj._CACHE["token"] = "pre"
        _gj.token = lambda: _gj._CACHE.get("token", "")
        _ur.urlopen = _open
        H._phone_get("/x")
        check("H1pb _phone_token restores what it FOUND, not a fixed state: an opt-in already open stays open with "
              "its reason, and a token cached before it stays cached",
              _gj._CREDENTIAL_STORE_OK == {"allowed": True, "why": "an earlier opt-in of someone else's"}
              and _gj._CACHE.get("token") == "pre", (_gj._CREDENTIAL_STORE_OK, _gj._CACHE))
    finally:
        _gj.token, _ur.urlopen = _real2[0], _real2[1]
        _gj._CREDENTIAL_STORE_OK.clear()
        _gj._CREDENTIAL_STORE_OK.update(_real2[2])
        _gj._CACHE.clear()
        _gj._CACHE.update(_real2[3])

    check("H1pb phone_build_failed is registered, and has no remedy: the fix is in his repository and account",
          H.DETECTORS.get("phone_build_failed") is H.detect_phone_build_failed
          and not [n for n, rr in H.REMEDIES.items() if "phone_build_failed" in (rr.get("for") or [])])

    # mesh_source_split arrived 2026-09-18 and H1v caught it with no coverage
    # here, which is again exactly what H1v is for. Its behaviour is pinned in
    # test_h2_update_witness.py (S1-S6, R1-R3); what is driven HERE is the one
    # property this file is about -- the class boundary. It is the first
    # registered detector with NO remedy on purpose, because the condition is a
    # peer's bytes and nothing on this PC may change those (rule 5: the phone is
    # asked, never pushed). If a remedy is ever pointed at it, that is a remedy
    # graded against a condition it cannot clear, and the fetch_build quarantine
    # is what that costs.
    def _mesh_health(local, peer_src):
        return {"A": {"source_sha256": local, "mesh": {
            "tracked": 1, "by_source": {peer_src: ["phone:5001"]},
            "heard_s_ago": {"phone:5001": 9.0}}}}

    r_ms = H.detect_mesh_source_split(health=_mesh_health("aaaaaaaaaaaa", "ffffffffffff"))
    check("H1w mesh_source_split is PRESENT for a peer off the running mesh, "
          "and carries the peer, its bytes and the age of the reading",
          r_ms["state"] == H.PRESENT
          and r_ms["measured"]["drifted"] == ["phone:5001"]
          and r_ms["measured"]["heard_s_ago"] == {"phone:5001": 9.0}, r_ms["measured"])
    r_ms2 = H.detect_mesh_source_split(health=_mesh_health("aaaaaaaaaaaa", "aaaaaaaaaaaa"))
    check("H1w ...and ABSENT when the peer matches, so the condition can clear",
          r_ms2["state"] == H.ABSENT and r_ms2["measured"]["drifted"] == [],
          r_ms2["measured"])
    check("H1w mesh_source_split has NO remedy pointed at it -- a condition "
          "this machine cannot clear must not grade one",
          [n for n, r in H.REMEDIES.items()
           if "mesh_source_split" in (r.get("for") or [])] == [],
          str({n: r.get("for") for n, r in H.REMEDIES.items()}))
    # A TEMP LEDGER (2026-09-25): this pass used to write its dry-run rows into the LIVE
    # ops/highway.jsonl, where one held the real node restart for an hour (18:45:50).
    a_ms, _i_ms = H.run_once(dry_run=True, health=_mesh_health("aaaaaaaaaaaa", "ffffffffffff"), ledger=tmp_ledger())
    check("H1w ...and run_once still ALERTS on it, with the numbers -- a finding "
          "with no remedy is not a finding nobody is told about",
          any("mesh_source_split" in a and "phone:5001" in a for a in a_ms),
          str([a[:120] for a in a_ms if "mesh_source_split" in a]))

    # app_install_futile arrived 2026-09-18 (A147) and H1v caught it with no
    # coverage here, third in a row, which is the whole argument for that
    # guard. Its behaviour is pinned in test_h2_update_witness.py (F1-F12,
    # driven both ways and mutation-tested); what is driven HERE is this
    # file's own subject -- the class boundary, and the one property that
    # matters about this condition: the ONLY remedy pointed at it is the one
    # that needs a person. The fix for a phone whose installer throws is on
    # the phone, so anything automatic graded against this would be graded
    # against a condition it cannot clear, which is what quarantined
    # fetch_build in this file's first live hour.
    _paired = [n for n, r in H.REMEDIES.items()
               if "app_install_futile" in (r.get("for") or [])]
    check("H1w app_install_futile is paired ONLY with the PROPOSE_ONLY remedy "
          "-- nothing on this PC can clear a phone's installer",
          _paired == ["install_on_phone"]
          and H.REMEDIES["install_on_phone"]["klass"] == H.PROPOSE_ONLY,
          str(_paired))

    import covenant_app_update as _AU
    _real_if = _AU.install_futility
    try:
        _AU.install_futility = lambda *a, **k: {
            "futile": True, "complete": 3, "proved": 3, "bytes": 135490068,
            "want": "0.1.568+2e61e52", "have": "0.1.475+13b946a",
            "why": "delivered whole 3 times and still on 0.1.475+13b946a"}
        r_fu = H.detect_app_install_futile()
        _AU.install_futility = lambda *a, **k: {
            "futile": False, "complete": 0, "proved": 0, "bytes": 0,
            "want": "0.1.568+2e61e52", "have": "0.1.568+2e61e52",
            "why": "phone is on 0.1.568+2e61e52 -- installed"}
        r_fu0 = H.detect_app_install_futile()
        _AU.install_futility = lambda *a, **k: {
            "futile": False, "why": "could not be measured: OSError: nope"}
        r_fuU = H.detect_app_install_futile()
    finally:
        _AU.install_futility = _real_if
    check("H1w app_install_futile is PRESENT on a proved-futile delivery and "
          "carries the count, the bytes and both versions",
          r_fu["state"] == H.PRESENT and r_fu["measured"]["proved"] == 3
          and r_fu["measured"]["bytes"] == 135490068
          and r_fu["measured"]["have"] == "0.1.475+13b946a", r_fu["measured"])
    check("H1w ...ABSENT once the phone reports the build, so it can clear",
          r_fu0["state"] == H.ABSENT, r_fu0["measured"])
    check("H1w ...and UNKNOWN when the measurement could not be taken -- an "
          "unreadable ledger is not evidence that the phone is fine",
          r_fuU["state"] == H.UNKNOWN, r_fuU["measured"])

    # judge_seat_missing arrived 2026-09-19 (A151) -- the fourth detector H1v
    # has met without coverage, and the fourth time it earned its keep. Driven
    # HERE both ways, because the point of this one is that an absent seat is
    # LOUD: a policy naming a file that is not there must read PRESENT, and the
    # real tree -- both models on disk -- must read ABSENT.
    import covenant_judge_defer as _D
    _real_lp = _D.load_policy
    try:
        _D.load_policy = lambda *a, **k: {"second_student": "no_such_model_here.json", "both_seats": True}
        r_js = H.detect_judge_seat_missing()
        _D.load_policy = lambda *a, **k: {"second_student": "fallback_model_2.json", "both_seats": True}
        r_js0 = H.detect_judge_seat_missing()
    finally:
        _D.load_policy = _real_lp
    check("H1w judge_seat_missing is PRESENT when the policy seats a judge whose "
          "model file is not on disk -- the silence A151 named",
          r_js["state"] == H.PRESENT and "second_student" in r_js["measured"]["missing"],
          str(r_js["measured"])[:90])
    check("H1w ...and ABSENT when every seated judge has its model on disk",
          r_js0["state"] == H.ABSENT, str(r_js0["measured"])[:60])
    check("H1w judge_seat_missing has NO remedy -- a missing model is a person's "
          "or the nightly distill's to restore, never this engine's",
          [n for n, r in H.REMEDIES.items()
           if "judge_seat_missing" in (r.get("for") or [])] == [])

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
    # stale_test_mesh / evict_test_mesh arrived 2026-09-21 (A187, his words: "Fix the test
    # nodes but tetsu needs to begin handling these fixes also well between him and pc").
    # Driven here with the two measurements stubbed: ports answering, and whether a
    # covenant_one.py sweep is running. The remedy is never run for real in a suite.
    # A214b: REAL listeners on ephemeral ports, not a mock of urlopen. The
    # detector now asks the SOCKET whether anything is there before it asks
    # HTTP -- a dropped SYN to a closed 60x0 port cost ~2.0 s, three times a
    # minute, 56% of all sensing -- so a urlopen mock alone would short-circuit
    # before reaching the fake and pass while measuring nothing. These bind and
    # answer /health for real. The ports are ephemeral, so a sweep's own test
    # nodes on 6000/6020/6060 can never collide with this check.
    import http.server as _hs
    import json as _json
    import threading as _th

    class _HealthOK(_hs.BaseHTTPRequestHandler):
        def do_GET(self):                                         # noqa: N802
            b = _json.dumps({"node_id": "TESTMESH"}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *_a):
            return

    _real_sr = H._sweep_running
    _servers, _ports = [], []
    for _i in range(3):
        _srv = _hs.HTTPServer(("127.0.0.1", 0), _HealthOK)
        _th.Thread(target=_srv.serve_forever, daemon=True).start()
        _servers.append(_srv)
        _ports.append(_srv.server_address[1])
    try:
        H._sweep_running = lambda: False
        r_tm = H.detect_stale_test_mesh(ports=tuple(_ports))
        H._sweep_running = lambda: True
        r_tm_owned = H.detect_stale_test_mesh(ports=tuple(_ports))
        H._sweep_running = lambda: None
        r_tm_unk = H.detect_stale_test_mesh(ports=tuple(_ports))
    finally:
        for _srv in _servers:
            _srv.shutdown()
        H._sweep_running = _real_sr
    try:
        H._sweep_running = lambda: False
        r_tm_none = H.detect_stale_test_mesh(ports=tuple(_ports))   # same ports, now closed
    finally:
        H._sweep_running = _real_sr
    check("H1x stale_test_mesh: REAL listeners with no sweep running is PRESENT, naming the ports",
          r_tm["state"] == H.PRESENT and sorted(r_tm["measured"]["test_ports_up"]) == sorted(_ports), str(r_tm)[:150])
    check("H1x stale_test_mesh: the same ports with a sweep running is ABSENT (a sweep owns its nodes)",
          r_tm_owned["state"] == H.ABSENT and "owns them" in r_tm_owned["measured"].get("note", ""), str(r_tm_owned)[:150])
    check("H1x stale_test_mesh: the process list unreadable is UNKNOWN, never ABSENT",
          r_tm_unk["state"] == H.UNKNOWN and "error" in r_tm_unk["measured"], str(r_tm_unk)[:150])
    check("H1x stale_test_mesh: nothing listening on those ports is ABSENT, so the condition can clear",
          r_tm_none["state"] == H.ABSENT and r_tm_none["measured"]["test_ports_up"] == [], str(r_tm_none)[:150])
    ok_dry, note_dry = H.remedy_evict_test_mesh({"test_ports_up": [6000, 6020]}, dry_run=True)
    ok_no, note_no = H.remedy_evict_test_mesh({"test_ports_up": []}, dry_run=False)
    try:
        H._sweep_running = lambda: None
        ok_unk, note_unk = H.remedy_evict_test_mesh({"test_ports_up": [6000]}, dry_run=False)
    finally:
        H._sweep_running = _real_sr
    check("H1x evict_test_mesh: a dry run names the ports and ends nothing; nothing up ends nothing; an unreadable process list ends nothing",
          ok_dry and "6000, 6020" in note_dry and not ok_no and not ok_unk and "nothing ended" in note_unk, (note_dry, note_no, note_unk))
    check("H1x evict_test_mesh is AUTO_REVERSIBLE, stateless, paired only with stale_test_mesh, and its pattern carries the test port range, never a bare script name",
          H.REMEDIES["evict_test_mesh"]["klass"] == H.AUTO_REVERSIBLE and H.REMEDIES["evict_test_mesh"]["for"] == ["stale_test_mesh"]
          and "60[0-9]0" in inspect.getsource(H.remedy_evict_test_mesh) and "'*run_node.py*'" not in inspect.getsource(H.remedy_evict_test_mesh))

    # defender_threat arrived 2026-09-21 (A201, his words: "virus protection showed a trojan ensure spyware
    # cannot survive our enviroment and we can track where it came from"). Driven with Defender's reader
    # stubbed and the threat ledger redirected; no remedy is paired, on purpose (the quarantine is
    # Defender's and the false-positive call is a person's).
    _real_dd, _real_thr = H._defender_detections, H.THREATS
    _thr = os.path.join(tempfile.mkdtemp(prefix="h1_thr_"), "threats.jsonl")
    try:
        H.THREATS = _thr
        H._defender_detections = lambda hours=24: [{"t": "2026-09-21T15:05:37", "id": "2147735505", "ok": True,
                                                    "process": "C:\\x\\python3.12.exe", "resources": "file:_C:\\Temp\\covenant_one_1\\tools\\llama\\llama-gguf-split.exe"}]
        r_dt = H.detect_defender_threat()
        r_dt2 = H.detect_defender_threat()
        H._defender_detections = lambda hours=24: []
        r_dt0 = H.detect_defender_threat()
        H._defender_detections = lambda hours=24: None
        r_dtU = H.detect_defender_threat()
    finally:
        H._defender_detections, H.THREATS = _real_dd, _real_thr
    _thr_rows = [json.loads(l) for l in open(_thr, encoding="utf-8")] if os.path.exists(_thr) else []
    check("H1y defender_threat: a detection in the last day is PRESENT, naming the file, the writing process and whether Defender acted",
          r_dt["state"] == H.PRESENT and r_dt["measured"]["detections_24h"] == 1 and "llama-gguf-split" in r_dt["measured"]["newest"]["resources"]
          and r_dt["measured"]["newest"]["acted"] is True and "python3.12" in r_dt["measured"]["newest"]["process"], str(r_dt)[:200])
    check("H1y the same detection is kept ONCE in the threat ledger across two reads", len(_thr_rows) == 1 and _thr_rows[0]["threat_id"] == "2147735505", _thr_rows)
    check("H1y no detection is ABSENT; an unreadable history is UNKNOWN, never ABSENT", r_dt0["state"] == H.ABSENT and r_dtU["state"] == H.UNKNOWN and "error" in r_dtU["measured"], (r_dt0, r_dtU))
    check("H1y no remedy is paired with defender_threat (the quarantine is Defender's; the false-positive call is a person's)",
          not [n for n, r in H.REMEDIES.items() if "defender_threat" in (r.get("for") or [])])

    # defense_lapse arrived 2026-09-21 (A202, his words: "need the most advanced defender and anti spyware
    # defense that will ever exist ensure it constantly adapts to protect the mycelal network"). Driven with
    # Defender's status stubbed and the wire's ledger redirected; no remedy is paired, on purpose.
    import covenant_mycelium as _MY
    _real_ds, _real_myl = H._defender_status, _MY.LEDGER
    _myl = os.path.join(tempfile.mkdtemp(prefix="h1_my_"), "mycelium.jsonl")
    try:
        _MY.LEDGER = _myl
        fine = {"RealTimeProtectionEnabled": True, "AMServiceEnabled": True, "AntivirusSignatureAge": 1, "QuickScanAge": 3, "FullScanAge": 20}
        H._defender_status = lambda: dict(fine)
        r_ok = H.detect_defense_lapse()
        H._defender_status = lambda: dict(fine, RealTimeProtectionEnabled=False)
        r_off = H.detect_defense_lapse()
        H._defender_status = lambda: dict(fine, AntivirusSignatureAge=9, QuickScanAge=30, FullScanAge=40)
        r_stale = H.detect_defense_lapse()
        H._defender_status = lambda: None
        r_unk = H.detect_defense_lapse()
        with open(_myl, "w", encoding="utf-8") as fh:
            now_s = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            for _i in range(25):
                fh.write(json.dumps({"kind": "refused", "addr": "192.168.1.77", "path": "/m/agent", "why": "unsigned", "t": now_s}) + "\n")
            fh.write(json.dumps({"kind": "admitted", "addr": "192.168.1.50", "path": "/m/agent", "who": "phone", "t": now_s}) + "\n")
        H._defender_status = lambda: dict(fine)
        r_noisy = H.detect_defense_lapse()
    finally:
        H._defender_status, _MY.LEDGER = _real_ds, _real_myl
    check("H1z defense_lapse: protection on, fresh signatures, a recent scan, a quiet wire -> ABSENT with the readings", r_ok["state"] == H.ABSENT and r_ok["measured"]["real_time"] is True and r_ok["measured"]["lapses"] == [], str(r_ok)[:200])
    check("H1z real-time protection OFF -> PRESENT, named", r_off["state"] == H.PRESENT and any("OFF" in x for x in r_off["measured"]["lapses"]), r_off["measured"]["lapses"])
    check("H1z stale signatures and no scan in a fortnight -> PRESENT, both named", r_stale["state"] == H.PRESENT and len(r_stale["measured"]["lapses"]) == 2, r_stale["measured"]["lapses"])
    check("H1z an unreadable status is UNKNOWN, never ABSENT", r_unk["state"] == H.UNKNOWN)
    check("H1z twenty-five refusals from one address in a day -> PRESENT naming the address and its count; the admitted row is not counted",
          r_noisy["state"] == H.PRESENT and any("192.168.1.77 x25" in x for x in r_noisy["measured"]["lapses"]) and r_noisy["measured"]["wire_refusals_24h"] == {"192.168.1.77": 25}, r_noisy["measured"])
    _paired_dl = [n for n, r in H.REMEDIES.items() if "defense_lapse" in (r.get("for") or [])]
    ok_rt, why_rt = H.remedy_refresh_defender({"lapses": ["real-time protection is OFF"]}, dry_run=False)
    ok_dry, why_dry = H.remedy_refresh_defender({"lapses": ["signatures are 9 days old", "no scan in 30 days"]}, dry_run=True)
    ok_none, why_none = H.remedy_refresh_defender({"lapses": []}, dry_run=False)
    check("H1z defense_lapse is paired ONLY with refresh_defender (AUTO_REVERSIBLE): signatures and a quick scan, never a setting",
          _paired_dl == ["refresh_defender"] and H.REMEDIES["refresh_defender"]["klass"] == H.AUTO_REVERSIBLE, _paired_dl)
    check("H1z the remedy refuses real-time OFF (a person's setting), names both mendable lapses in a dry run, and does nothing with no lapse",
          ok_rt is False and "mine to mend" in why_rt and ok_dry and "signatures are 9 days old" in why_dry and "no scan in 30 days" in why_dry and ok_none is False, (why_rt, why_dry, why_none))

    # ---- H1sc: the sweep measured THIS core (A278, 2026-10-06, his words: "keep expanding the highway").
    # A temp tree with its own core file and transcripts; the remedy's process list and launcher are
    # stand-ins, so no test can start a real sweep.
    import hashlib as _hl
    _sc = tempfile.mkdtemp(prefix="h1sc_")
    with open(os.path.join(_sc, "covenant_unified_v8.py"), "wb") as _fh:
        _fh.write(b"# core v2\n")
    _disk = _hl.sha256(b"# core v2\n").hexdigest()[:12]

    def _transcript(name, core, verdict="PASS", partial=False):
        with open(os.path.join(_sc, name), "w", encoding="utf-8") as fh:
            fh.write(("# scope: PARTIAL\n" if partial else "") + "  core  covenant_unified_v8.py  10 bytes  sha256 %s\n"
                     "  suites run  178\n  checks failed  0\n  RESULT: %s. ...\n" % (core, verdict))
    r_none = H.detect_sweep_not_current(here=_sc)["state"]
    _transcript("OLD.txt", "0123456789ab")
    r_old = H.detect_sweep_not_current(here=_sc)
    _transcript("ONLY.txt", _disk, partial=True)
    r_partial = H.detect_sweep_not_current(here=_sc)["state"]
    _transcript("NEW.txt", _disk, verdict="FAIL")
    r_new = H.detect_sweep_not_current(here=_sc)
    check("H1sc sweep_not_current: no sweep UNKNOWN; a sweep of another core PRESENT (naming both); a partial "
          "run of this core does not count; a full sweep of this core ABSENT even when it says FAIL (that is sweep_red's)",
          r_none == H.UNKNOWN and r_old["state"] == H.PRESENT and r_old["measured"]["transcript_core"] == "0123456789ab"
          and r_old["measured"]["disk_core"] == _disk and r_partial == H.PRESENT and r_new["state"] == H.ABSENT,
          (r_none, r_old, r_partial, r_new))
    _rs = H.REMEDIES.get("run_full_sweep") or {}
    check("H1sc run_full_sweep is paired with sweep_not_current alone: AUTO_REVERSIBLE, stateless, async, at most once in 6 h",
          _rs.get("for") == ["sweep_not_current"] and _rs.get("klass") == H.AUTO_REVERSIBLE and _rs.get("kind") == "stateless"
          and _rs.get("async") is True and _rs.get("cooldown_s", 0) >= 6 * 3600, _rs)
    _real_sc = (H._sweep_running, H._sweep_launch, sys.argv[0],
                {k: os.environ.get(k) for k in ("COVENANT_ONE_TRANSCRIPT", "COVENANT_INSECURE_MOCK_JUDGE")})
    _launched = []
    try:
        H._sweep_launch = lambda cmd, log: (_launched.append(cmd), type("P", (), {"pid": 4242})())[1]
        H._sweep_running = lambda: []
        ok_test, why_test = H.remedy_run_full_sweep({"disk_core": _disk}, dry_run=False)   # argv[0] is this suite
        sys.argv[0] = "covenant_watchdog.py"
        for k in _real_sc[3]:
            os.environ.pop(k, None)
        H._sweep_running = lambda: ["4711 python covenant_one.py"]
        ok_busy, why_busy = H.remedy_run_full_sweep({"disk_core": _disk}, dry_run=False)
        H._sweep_running = lambda: None
        ok_blind, why_blind = H.remedy_run_full_sweep({"disk_core": _disk}, dry_run=False)
        H._sweep_running = lambda: []
        ok_dry, why_dry = H.remedy_run_full_sweep({"disk_core": _disk}, dry_run=True)
        n_before = len(_launched)
        ok_go, why_go = H.remedy_run_full_sweep({"disk_core": _disk}, dry_run=False)
    finally:
        H._sweep_running, H._sweep_launch, sys.argv[0] = _real_sc[0], _real_sc[1], _real_sc[2]
        for k, v in _real_sc[3].items():
            if v is not None:
                os.environ[k] = v
    if os.name == "nt":
        check("H1sc the remedy declines from a test, beside a running sweep, and when it cannot look; a dry run starts nothing",
              ok_test is False and "test" in why_test and ok_busy is False and "already running" in why_busy
              and ok_blind is False and ok_dry is True and n_before == 0, (why_test, why_busy, why_blind, why_dry, _launched))
        check("H1sc ...and with the way clear it starts exactly one covenant_one.py",
              ok_go is True and len(_launched) == 1 and _launched[0][-1].endswith("covenant_one.py") and "4242" in why_go, (why_go, _launched))
    else:
        check("H1sc off Windows the remedy declines (it cannot see a running sweep) and starts nothing",
              ok_go is False and not _launched, (why_go, _launched))

    # ---- H1am: free granted and silent (A279, 2026-10-06). Every input is a stand-in.
    _n = 1_900_000_000.0
    _g = {"granted": True}
    am = {
        "no_grant": H.detect_ambassador_stalled(grant=None or {}, paused=(False, ""), rounds=[], now=_n)["state"],
        "paused": H.detect_ambassador_stalled(grant=_g, paused=(True, "isolated 2026-10-04: ..."), rounds=[{"at": _n - 600}], now=_n),
        "fresh": H.detect_ambassador_stalled(grant=_g, paused=(False, ""), rounds=[{"at": _n - 3 * 3600}], now=_n)["state"],
        "stale": H.detect_ambassador_stalled(grant=_g, paused=(False, ""), rounds=[{"at": _n - 9 * 3600}, {"t": "2001-01-01T00:00:00Z"}], now=_n),
        "never": H.detect_ambassador_stalled(grant=_g, paused=(False, ""), rounds=[], now=_n)["state"],
    }
    check("H1am ambassador_stalled: no grant ABSENT (his choice); paused PRESENT with the pause's own words; a round 3 h ago "
          "ABSENT; none in 9 h PRESENT; no round ever on record UNKNOWN",
          am["no_grant"] == H.ABSENT and am["paused"]["state"] == H.PRESENT and "isolated" in am["paused"]["measured"]["why"]
          and am["fresh"] == H.ABSENT and am["stale"]["state"] == H.PRESENT and am["stale"]["measured"]["last_live_round_h"] == 9.0
          and am["never"] == H.UNKNOWN, am)
    _am_paired = [n for n, r in H.REMEDIES.items() if "ambassador_stalled" in (r.get("for") or [])]
    check("H1am no remedy: lifting a pause is his, and a round speaks in public", _am_paired == [], _am_paired)

    # ---- H1ak: Tetsu up and failing (A282, 2026-10-06). Stand-in rows, a fixed clock.
    _ta = 1_900_000_000.0
    _okr = lambda ago: {"at": _ta - ago, "ok": True, "ms": 900}                                    # noqa: E731
    _bad = lambda ago: {"at": _ta - ago, "ok": False, "ms": 34500, "error": "HTTPError: HTTP Error 500"}  # noqa: E731
    ak = {
        "failing": H.detect_tetsu_asks_failing(rows=[_bad(60), _bad(120), _okr(180), _bad(240)], now=_ta),
        "healthy": H.detect_tetsu_asks_failing(rows=[_okr(60), _okr(120), _bad(180), _okr(240)], now=_ta)["state"],
        "too_few": H.detect_tetsu_asks_failing(rows=[_bad(60), _bad(120)], now=_ta)["state"],
        "old": H.detect_tetsu_asks_failing(rows=[_bad(3 * 3600), _bad(3 * 3600 + 5), _bad(3 * 3600 + 9)], now=_ta)["state"],
    }
    check("H1ak tetsu_asks_failing: 3 of 4 recent asks failed PRESENT naming the error; 1 of 4 ABSENT; 2 asks too few to "
          "judge ABSENT; failures older than the window ABSENT",
          ak["failing"]["state"] == H.PRESENT and "500" in ak["failing"]["measured"]["last_error"]
          and ak["healthy"] == H.ABSENT and ak["too_few"] == H.ABSENT and ak["old"] == H.ABSENT, ak)
    import covenant_model as _CMk
    _real_asks = _CMk.ASKS
    try:
        _CMk.ASKS = os.path.join(tempfile.mkdtemp(prefix="h1ak_"), "absent.jsonl")
        r_noledger = H.detect_tetsu_asks_failing(now=_ta)["state"]
    finally:
        _CMk.ASKS = _real_asks
    check("H1ak no ledger here is UNKNOWN, never ABSENT", r_noledger == H.UNKNOWN, r_noledger)

    # ---- H1st: Moltbook strikes (A283, 2026-10-06). Stand-in ledger rows.
    _ts = 1_900_000_000.0
    _v = lambda req, sol, ab=False, ago=3600: {"t": "x", "at": _ts - ago, "author": "a", "verification":  # noqa: E731
                                               {"required": req, "solved": sol, "abstained": ab}}
    st_ = {
        "clean": H.detect_moltbook_strikes(rows=[_v(True, True), _v(False, False), {"kind": "reply"}], now=_ts)["state"],
        "wrong": H.detect_moltbook_strikes(rows=[_v(True, True), _v(True, False)], now=_ts),
        "abstained": H.detect_moltbook_strikes(rows=[_v(True, False, ab=True)], now=_ts)["state"],
        "old": H.detect_moltbook_strikes(rows=[_v(True, False, ago=8 * 86400)], now=_ts)["state"],
        "none": H.detect_moltbook_strikes(rows=[{"kind": "reply", "sent": True}], now=_ts)["state"],
    }
    check("H1st moltbook_strikes: every challenge solved ABSENT; a wrong answer PRESENT and counted; an abstention spends "
          "nothing (ABSENT); a strike older than a week out of the window (UNKNOWN: nothing in it); nothing on record UNKNOWN",
          st_["clean"] == H.ABSENT and st_["wrong"]["state"] == H.PRESENT and st_["wrong"]["measured"]["wrong_answers_7d"] == 1
          and st_["abstained"] == H.ABSENT and st_["old"] == H.UNKNOWN and st_["none"] == H.UNKNOWN, st_)
    check("H1st no remedy: the account is his", [n for n, r in H.REMEDIES.items() if "moltbook_strikes" in (r.get("for") or [])] == [])

    # ---- H1sk: the schedule is alive (A281, 2026-10-06). Stand-in task lists; the scheduler is never read here.
    _t = 1_900_000_000.0
    _ok = {"name": "CovenantGuard", "state": "Ready", "last_run": _t - 120, "next_run": _t + 60, "missed": 0}
    sk = {
        "alive": H.detect_schedule_stalled(tasks=[_ok], now=_t)["state"],
        "late": H.detect_schedule_stalled(tasks=[_ok, dict(_ok, name="CovenantDistill", next_run=_t - 2 * 3600)], now=_t),
        "missed": H.detect_schedule_stalled(tasks=[dict(_ok, missed=2)], now=_t)["state"],
        "disabled": H.detect_schedule_stalled(tasks=[dict(_ok, state="Disabled", next_run=_t - 9 * 3600)], now=_t),
        "unread": H.detect_schedule_stalled(tasks=None if False else [], now=_t)["state"],
    }
    check("H1sk schedule_stalled: firing ABSENT; a task 2 h overdue PRESENT naming it; missed runs PRESENT; a DISABLED task "
          "listed and not flagged (his choice); no task here UNKNOWN",
          sk["alive"] == H.ABSENT and sk["late"]["state"] == H.PRESENT and "CovenantDistill" in sk["late"]["measured"]["stalled"][0]
          and sk["missed"] == H.PRESENT and sk["disabled"]["state"] == H.ABSENT and sk["disabled"]["measured"]["disabled"] == ["CovenantGuard"]
          and sk["unread"] == H.UNKNOWN, sk)
    check("H1sk no remedy: the scheduler's configuration is his",
          [n for n, r in H.REMEDIES.items() if "schedule_stalled" in (r.get("for") or [])] == [])

    # ---- H1tt: Tetsu on the road (A276, 2026-10-06, his words: "get the road green and start expanding
    # the highway"). Two READS of covenant_model.readiness(), driven with a stand-in, each way. No remedy
    # may be paired with either: the model is NEVER_AUTOMATIC and freeing memory is his (A252).
    _mem = lambda: {"verdict": "FAIL", "why": "Tetsu cannot answer: free 1.4 GB", "free_gb": 1.4, "needs_gb": 2.1,  # noqa: E731
                    "smallest": "Qwen3.5-2B-Q4_K_M.gguf"}
    _up = lambda: {"verdict": "PASS", "why": "up: qwen2.5-3b-instruct-q4_k_m.gguf", "free_gb": 0.8}  # noqa: E731
    _orphan = lambda: {"verdict": "UNDETERMINED", "managed": False, "why": "a server answers ... no state (A265)"}  # noqa: E731
    _noruntime = lambda: {"verdict": "FAIL", "why": "no runtime at tools/llama/llama-server.exe"}  # noqa: E731
    _broken = lambda: (_ for _ in ()).throw(OSError("keeper unreadable"))  # noqa: E731
    tc = {n: H.detect_tetsu_cannot_answer(ready=f)["state"] for n, f in
          (("mem", _mem), ("up", _up), ("orphan", _orphan), ("noruntime", _noruntime), ("broken", _broken))}
    check("H1tt tetsu_cannot_answer: the memory case PRESENT; up ABSENT; unmanaged, no runtime (a clone) and an "
          "unreadable keeper UNKNOWN -- never ABSENT for what it could not read",
          tc == {"mem": H.PRESENT, "up": H.ABSENT, "orphan": H.UNKNOWN, "noruntime": H.UNKNOWN, "broken": H.UNKNOWN}, tc)
    mu = {n: H.detect_model_unmanaged(ready=f)["state"] for n, f in
          (("orphan", _orphan), ("up", _up), ("mem", _mem), ("broken", _broken))}
    check("H1tt model_unmanaged: a server the keeper has no record of PRESENT; managed or nothing up ABSENT; "
          "unreadable UNKNOWN", mu == {"orphan": H.PRESENT, "up": H.ABSENT, "mem": H.ABSENT, "broken": H.UNKNOWN}, mu)
    _tt_paired = [n for n, r in H.REMEDIES.items() if set(r.get("for") or []) & {"tetsu_cannot_answer", "model_unmanaged"}]
    check("H1tt neither Tetsu condition has a remedy: they are read and reported, a person acts", _tt_paired == [], _tt_paired)
    check("H1tt both are registered, so sense() runs them every pass",
          H.DETECTORS.get("tetsu_cannot_answer") is H.detect_tetsu_cannot_answer
          and H.DETECTORS.get("model_unmanaged") is H.detect_model_unmanaged)

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

    # ---- H1o2: what was STARTED is judged, and only when it can be -----------
    # 2026-09-27, his instruction "get ... self healing right". apply_remedy's
    # async branch wrote outcome="started" with the note "the condition is
    # re-measured next pass" and nothing implemented the next pass: measured from
    # the live ledger that morning, 252 starts with 0 outcomes, while --standing
    # printed UNPROVEN and explained that nothing checks what they started. Each
    # promise grade_started() now makes is driven BOTH ways below.
    print("\nH1o2 -- an asynchronous start is graded, late, and only when it can be")
    ASYNC = "dispatch_phone_build"          # async: True in the real table
    WINDOW = float((H.REMEDIES[ASYNC].get("grade_after_s") or H.GRADE_AFTER_S))

    def started_row(led, at, before=H.PRESENT, detector="phone_build_behind_core",
                    remedy=ASYNC):
        return H.write_ledger({"t": "fixture", "at": at, "remedy": remedy,
                               "detector": detector, "dry_run": False,
                               "before": before, "after": before,
                               "outcome": "started"}, led)

    NOW = 1_000_000.0
    ABSENT_NOW = {"phone_build_behind_core": {"state": H.ABSENT, "measured": {}}}
    PRESENT_NOW = {"phone_build_behind_core": present()}
    UNKNOWN_NOW = {"phone_build_behind_core": {"state": H.UNKNOWN, "measured": {}}}

    led = tmp_ledger()
    started_row(led, NOW - WINDOW - 60)
    got = H.grade_started(ABSENT_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o2 a start past its window, condition now ABSENT -> fixed",
          len(got) == 1 and got[0]["outcome"] == "fixed" and got[0]["graded_late"],
          str([(g["outcome"], g.get("graded_late")) for g in got]))

    led = tmp_ledger()
    started_row(led, NOW - WINDOW - 60)
    got = H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o2 ...still PRESENT -> did not fix", len(got) == 1
          and got[0]["outcome"] == "did not fix", str([g["outcome"] for g in got]))

    # THE ORIGINAL CAUTION, KEPT. Grading a ten-minute build one second after the
    # dispatch is what quarantined fetch_build in this file's first live hour.
    led = tmp_ledger()
    started_row(led, NOW - 5)
    got = H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o2 a start INSIDE its window is not graded at all", got == [], str(got))

    # mutation: shrink the window and the same row must now be graded, which
    # proves the check above is the window and not an accident of the fixture.
    _keep = H.REMEDIES[ASYNC].get("grade_after_s")
    try:
        H.REMEDIES[ASYNC]["grade_after_s"] = 1.0
        got = H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True)
        check("H1o2 mutation: window shrunk -> that same row IS graded",
              len(got) == 1 and got[0]["outcome"] == "did not fix", str(got))
    finally:
        H.REMEDIES[ASYNC]["grade_after_s"] = _keep

    # A READ THAT FAILED IS NOT A VERDICT. Calling UNKNOWN "did not fix" would
    # quarantine a remedy for the reader's blindness -- rule 9 in one branch.
    led = tmp_ledger()
    started_row(led, NOW - WINDOW - 60)
    got = H.grade_started(UNKNOWN_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o2 the condition UNKNOWN now -> left ungraded, never a failure",
          got == [], str(got))

    # A259-GRADE (2026-10-05). schedule_watchdog_restart restarted the watchdog twice
    # that night, a watched file was written inside each grading window, the condition
    # was PRESENT again as a new instance, both were graded "did not fix", and two of
    # those quarantined a remedy that had worked. Driven both ways with the real table.
    WREM = "schedule_watchdog_restart"
    WWIN = float(H.REMEDIES[WREM].get("grade_after_s") or H.GRADE_AFTER_S)
    t0 = NOW - WWIN - 60

    def wd_now(process_started, written):
        return {"watchdog_stale": {"state": H.PRESENT, "measured": {
            "newest_file": "covenant_earn.py", "written": written,
            "process_started": process_started, "running": 2}}}

    led = tmp_ledger()
    started_row(led, t0, detector="watchdog_stale", remedy=WREM)
    got = H.grade_started(wd_now(t0 + 8, t0 + 200), ledger=led, now=NOW, dry_run=True)
    check("H1o3 PRESENT again but the watchdog restarted after the remedy started -> fixed, marked recurred",
          len(got) == 1 and got[0]["outcome"] == "fixed" and got[0].get("recurred") is True,
          str([(g["outcome"], g.get("recurred")) for g in got]))
    led = tmp_ledger()
    started_row(led, t0, detector="watchdog_stale", remedy=WREM)
    got = H.grade_started(wd_now(t0 - 500, t0 + 200), ledger=led, now=NOW, dry_run=True)
    check("H1o3 mutation: the old watchdog is still the oldest running -> did not fix (the remedy did not work)",
          len(got) == 1 and got[0]["outcome"] == "did not fix" and not got[0].get("recurred"),
          str([(g["outcome"], g.get("recurred")) for g in got]))
    led = tmp_ledger()
    for k in range(2):
        started_row(led, t0 - 7200 * (1 - k), detector="watchdog_stale", remedy=WREM)
        for g in H.grade_started(wd_now(t0 - 7200 * (1 - k) + 8, t0 + 200), ledger=led, now=NOW):
            pass
    check("H1o3 two recurrences in a row do not quarantine the remedy (two misgrades did, 2026-10-05)",
          not H.quarantined(WREM, led), [r.get("outcome") for r in H.read_ledger(led)])
    led = tmp_ledger()
    started_row(led, NOW - WINDOW - 60, detector="phone_build_behind_core", remedy=ASYNC)   # ITS window, not WWIN
    got = H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o3 a detector with no recurrence test keeps the old rule (still PRESENT -> did not fix)",
          len(got) == 1 and got[0]["outcome"] == "did not fix", str([g["outcome"] for g in got]))

    # A261 (2026-10-05): the build runner's day is spent by a dispatch that RAN, and its grading window
    # covers the fetch that clears the condition. Both misgrades and the refusal that held the day were
    # measured in the live ledger; each check below runs the real engine.
    DREM, DDET = "dispatch_phone_build", "phone_build_behind_core"

    def _drow(led, ago, outcome, ran=None):
        rw = {"t": "fixture", "at": time.time() - ago, "remedy": DREM, "detector": DDET,
              "dry_run": False, "outcome": outcome}
        if ran is not None:
            rw["ran"] = ran
        H.write_ledger(rw, led)
    led = tmp_ledger()
    _drow(led, 7200, "refused")
    got = H.apply_remedy(DREM, present(), DDET, dry_run=True, ledger=led)
    check("H1o4 a refusal two hours ago does not hold the build runner's day: nothing was spent",
          not got.get("repeat") and got.get("outcome") == "dry run", {k: got.get(k) for k in ("outcome", "repeat")})
    led = tmp_ledger()
    _drow(led, 7200, "started", ran=True)
    got = H.apply_remedy(DREM, present(), DDET, dry_run=True, ledger=led)
    check("H1o4 broken the other way: a dispatch that RAN two hours ago does hold it",
          got.get("repeat") is True, {k: got.get(k) for k in ("outcome", "repeat")})
    led = tmp_ledger()
    _drow(led, 600, "refused")
    got = H.apply_remedy(DREM, present(), DDET, dry_run=True, ledger=led)
    check("H1o4 a refusal ten minutes ago is still inside the hour's noise cooldown: the ledger stays quiet",
          got.get("repeat") is True, {k: got.get(k) for k in ("outcome", "repeat")})
    led = tmp_ledger()
    started_row(led, NOW - 40 * 60, detector=DDET, remedy=DREM)
    got = H.grade_started({DDET: present()}, ledger=led, now=NOW, dry_run=True)
    check("H1o4 A261-WINDOW: a dispatch 40 minutes old is not graded yet -- the fetch that clears the "
          "condition can be an hour away", got == [], str(got))
    _keep = H.REMEDIES[DREM]["grade_after_s"]
    try:
        H.REMEDIES[DREM]["grade_after_s"] = 1800.0
        got = H.grade_started({DDET: present()}, ledger=led, now=NOW, dry_run=True)
        check("H1o4 mutation: the old thirty-minute window grades that same dispatch 'did not fix' -- "
              "the misgrade of 09-28 and 10-03", len(got) == 1 and got[0]["outcome"] == "did not fix", str(got))
    finally:
        H.REMEDIES[DREM]["grade_after_s"] = _keep

    # A RECALIBRATION IS A BARRIER. Re-grading history across it would put back
    # the failures it was written to set aside, and invisibly.
    led = tmp_ledger()
    started_row(led, NOW - WINDOW - 600)
    H.recalibrate(ASYNC, "fixture: the count no longer applies", led)
    got = H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o2 a start BEFORE a recalibration is never graded", got == [], str(got))
    started_row(led, NOW - WINDOW - 60)
    got = H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o2 ...and a start AFTER it is", len(got) == 1, str(got))

    # dry_run writes nothing: the grader must be safe to print before it acts.
    led = tmp_ledger()
    started_row(led, NOW - WINDOW - 60)
    n_before = len(H.read_ledger(led))
    H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True)
    check("H1o2 dry_run grades on screen and writes no row",
          len(H.read_ledger(led)) == n_before, "%d rows" % len(H.read_ledger(led)))
    H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=False)
    check("H1o2 ...and with dry_run=False it does write one",
          len(H.read_ledger(led)) == n_before + 1, "%d rows" % len(H.read_ledger(led)))

    # AND THE DECLINE PATH: an async remedy that returned ran=False started
    # nothing, so there is nothing to wait for. 16 fetch_build rows saying
    # "already have build 2ab1ba5" were filed "started" and then graded failures.
    led = tmp_ledger()
    calls = []
    H.REMEDIES["_spy_async"] = {"fn": spy_remedy(calls, ok=False), "klass": H.AUTO_REVERSIBLE,
                                "for": ["phone_build_behind_core"], "kind": "stateless",
                                "async": True, "benefit": {"gains": [], "cost": [], "irreversible": []}}
    try:
        row = H.apply_remedy("_spy_async", present(), "phone_build_behind_core",
                             dry_run=False, ledger=led, cooldown_s=0)
        check("H1o2 an async remedy that DECLINED is held, not 'started'",
              row["outcome"] == "held", row["outcome"])
        check("H1o2 ...so grade_started has nothing to judge for it",
              H.grade_started(PRESENT_NOW, ledger=led, now=NOW, dry_run=True) == [], "")
        H.REMEDIES["_spy_async"]["fn"] = spy_remedy(calls, ok=True)
        row = H.apply_remedy("_spy_async", present(), "phone_build_behind_core",
                             dry_run=False, ledger=led, cooldown_s=0)
        check("H1o2 mutation: the same remedy returning ok -> 'started'",
              row["outcome"] == "started", row["outcome"])
    finally:
        H.REMEDIES.pop("_spy_async", None)

    failed = [n for n, ok in results if not ok]
    print(f"\nH1: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
