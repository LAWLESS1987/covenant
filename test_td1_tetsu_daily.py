#!/usr/bin/env python3
"""test_td1_tetsu_daily.py -- Tetsu's daily maintenance cycle (covenant_daily), his directive of
2026-09-28.

Every verdict the daily record can print is driven from both sides here, with the readings
stubbed: a node that disagrees on its tip is FAILED, not degraded; a phone that only reports a
height is UNVERIFIED, never verified; a sweep that wrote no fresh results is UNDETERMINED, never
PASS; an old failure coming back is REAPPEARED, not new; the one automatic change (a judge rollback)
happens only to a VERIFIED copy and keeps the failing one; the watchdog starts the cycle only from
the daemon, once a day, outside the trader's window; the phone's check-in keeps a hex tip and drops
anything else; and Tetsu's system message carries the directive, read at call time.

  TD1a  PC node verdicts          TD1b  phone node verdicts       TD1c  synchronization verdicts
  TD1d  new / standing / back     TD1e  the sweep's verdict       TD1f  when the cycle is due
  TD1g  the judge rollback        TD1h  the watchdog's daily row  TD1i  the check-in's tip/genesis
  TD1j  the directive reaches Tetsu                               TD1k  the understanding rubric
  TD1l  only the daemon launches  TD1m  a whole cycle, end to end, stubbed
LICENCE: Apache-2.0.
"""
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COVENANT_MODEL_STUB", "1")

import covenant_daily as D          # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- %s" % str(detail)[:300]))


def node(nid, tip="aa" * 32, gen="00" * 32, src="e8a79ee502d8", deg=False, up=True, h=53):
    if not up:
        return {"node": nid, "up": False, "error": "refused"}
    return {"node": nid, "up": True, "tip": tip, "genesis": gen, "source": src, "degraded": deg, "height": h,
            "warnings": ["no provider key"] if deg else []}


def main():
    tmp = tempfile.mkdtemp(prefix="td1_")
    real = {k: getattr(D, k) for k in ("HISTORY", "REPORT", "LATEST", "VERIFIED", "EXAMS", "SNAPS", "LOCK",
                                        "LAUNCH_STATE", "CHECKINS", "APP_LATEST", "NIGHTLY", "HERE", "OPS")}
    try:
        for k, name in (("HISTORY", "h.jsonl"), ("REPORT", "r.md"), ("LATEST", "l.json"), ("VERIFIED", "v.json"),
                        ("EXAMS", "e.jsonl"), ("LAUNCH_STATE", "ls.json"), ("CHECKINS", "c.jsonl"),
                        ("APP_LATEST", "a.json"), ("NIGHTLY", "n.md")):
            setattr(D, k, os.path.join(tmp, name))
        D.SNAPS = os.path.join(tmp, "snaps")
        D.LOCK = os.path.join(D.SNAPS, "cycle.lock")
        clean_exam = {"total": 53, "false_clean": 0, "false_hold": 0, "wrong": 0}

        print("TD1a -- the PC node")
        three = [node("A"), node("B"), node("C")]
        check("TD1a three agreeing nodes and a clean exam are healthy", D.classify_pc(three, clean_exam, {})[0] == "healthy")
        v, r = D.classify_pc([node("A"), node("B", tip="bb" * 32), node("C")], clean_exam, {})
        check("TD1a nodes that disagree on their tip are FAILED, not degraded", v == "failed" and any("tip" in x for x in r), (v, r))
        v, r = D.classify_pc(three, dict(clean_exam, false_clean=1), {})
        check("TD1a a judge that admits a violation on its exam makes the PC node FAILED", v == "failed", (v, r))
        v, r = D.classify_pc([node("A", deg=True), node("B", deg=True), node("C", deg=True)], clean_exam, {})
        check("TD1a a node that says it is degraded is reported degraded -- its own word is kept", v == "degraded", (v, r))
        v, r = D.classify_pc([node("A"), node("B", up=False), node("C")], clean_exam, {})
        check("TD1a an unreachable node is FAILED", v == "failed", (v, r))
        v, r = D.classify_pc(three, {"error": "no tally"}, {})
        check("TD1a an exam with no tally is not a pass (degraded, and said)", v == "degraded", (v, r))

        print("TD1b -- the phone node")
        fresh = {"age_min": 4, "build": "2f0af71abc", "pc_build": "2f0af71abcdef", "height": "53"}
        check("TD1b a fresh check-in on the PC's build at the PC's height is healthy", D.classify_phone(fresh, 53)[0] == "healthy")
        check("TD1b on a different build it is degraded", D.classify_phone(dict(fresh, build="1111111"), 53)[0] == "degraded")
        check("TD1b two days silent is FAILED", D.classify_phone(dict(fresh, age_min=48 * 60), 53)[0] == "failed")
        check("TD1b no check-in at all is FAILED, never healthy", D.classify_phone({"error": "none"}, 53)[0] == "failed")
        check("TD1b a height 5 behind the PC is degraded", D.classify_phone(dict(fresh, height="48"), 53)[0] == "degraded")

        print("TD1c -- synchronization")
        ph = {"age_min": 4, "height": "53", "tip": "aa" * 32, "genesis": "00" * 32}
        check("TD1c the phone's tip equal to the PC's at the same height is VERIFIED", D.classify_sync(three, ph)[0] == "verified")
        v, r = D.classify_sync(three, dict(ph, tip=None))
        check("TD1c a phone that reports only a height is UNVERIFIED, never verified", v == "unverified", (v, r))
        check("TD1c a different tip at the same height is FAILED",
              D.classify_sync(three, dict(ph, tip="cc" * 32))[0] == "failed")
        check("TD1c a different genesis is FAILED", D.classify_sync(three, dict(ph, genesis="11" * 32))[0] == "failed")
        check("TD1c PC nodes that disagree fail sync whatever the phone says",
              D.classify_sync([node("A"), node("B", tip="bb" * 32), node("C")], ph)[0] == "failed")

        print("TD1d -- new, standing, reappeared")
        rows = [{"failures": {"x": 1, "y": 1}}, {"failures": {"y": 1}}, {"failures": {"y": 1, "z": 1}}]
        k, cleared = D.classify_failures({"x": 1, "z": 1, "w": 1}, rows)
        check("TD1d an old failure that was cleared and is back is REAPPEARED, not new",
              k["reappeared"] == ["x"] and k["standing"] == ["z"] and k["new"] == ["w"] and cleared == ["y"], (k, cleared))
        check("TD1d the first record has every failure new", D.classify_failures({"a": 1}, [])[0]["new"] == ["a"])

        print("TD1e -- the sweep's verdict")
        res = os.path.join(tmp, "one.json")
        t0 = time.time()
        with open(res, "w") as fh:
            json.dump({"utc": "2020-01-01T00:00:00Z", "suites": [], "totals": {}}, fh)
        s = D.run_sweep(run=lambda *a, **k: (0, "RESULT: PASS. all"), results=res, started=t0)
        check("TD1e a PASS printed over STALE results is UNDETERMINED, never PASS", s["result"] == D.UNDET, s)
        with open(res, "w") as fh:
            json.dump({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0 + 60)),
                       "suites": [{"suite": "a.py", "state": "ok", "failed": 0}, {"suite": "b.py", "state": "ok", "failed": 2}],
                       "totals": {"checks_passed": 10, "checks_failed": 2}}, fh)
        s = D.run_sweep(run=lambda *a, **k: (1, "RESULT: FAIL. named above"), results=res, started=t0)
        check("TD1e fresh results: FAIL is FAIL, and the suite with failures is named",
              s["result"] == "FAIL" and [x["suite"] for x in s["not_clean"]] == ["b.py"], s)

        print("TD1f -- when the cycle is due")
        lt = time.localtime()

        def at(h, m):
            return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, m, 0, 0, 0, -1))
        check("TD1f due after the nightly, mid-morning, nothing running",
              D.due(now=at(9, 30), rows=[], running=[], nightly_done=True)[0] is True)
        check("TD1f never inside the trader's window (08:30)",
              D.due(now=at(8, 30), rows=[], running=[], nightly_done=True)[0] is False)
        check("TD1f before 10:00 it waits for the nightly",
              D.due(now=at(6, 0), rows=[], running=[], nightly_done=False)[0] is False)
        check("TD1f from 10:00 it runs even if the nightly never finished",
              D.due(now=at(10, 30), rows=[], running=[], nightly_done=False)[0] is True)
        check("TD1f not twice in a day", D.due(now=at(11, 0), rows=[{"date": D._today(at(11, 0))}], running=[], nightly_done=True)[0] is False)
        check("TD1f not while a sweep runs", D.due(now=at(11, 0), rows=[], running=["123 covenant_one.py"], nightly_done=True)[0] is False)

        print("TD1g -- the judge rollback")
        fake = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(fake, "ops", "students"))
        D.HERE, D.OPS = fake, os.path.join(fake, "ops")
        good, bad = b'{"good": 1}', b'{"bad": 1}'
        import hashlib
        gd = hashlib.sha256(good).hexdigest()[:12]
        with open(os.path.join(fake, "fallback_model.json"), "wb") as fh:
            fh.write(bad)
        with open(os.path.join(fake, "ops", "students", "fallback_model.%s.json" % gd), "wb") as fh:
            fh.write(good)
        ver = {"students": {"fallback_model.json": gd}}
        check("TD1g a clean exam rolls nothing back",
              D.maybe_roll_back_students(clean_exam, ver) == [] and open(os.path.join(fake, "fallback_model.json"), "rb").read() == bad)
        import covenant_distill as X
        real_keep = X.keep_predecessor
        kept = []
        X.keep_predecessor = lambda p: (kept.append(open(p, "rb").read()), os.path.join(fake, "ops", "students", "kept.json"))[1]
        try:
            out = D.maybe_roll_back_students(dict(clean_exam, false_clean=2), ver)
        finally:
            X.keep_predecessor = real_keep
        check("TD1g a false clean restores the VERIFIED copy, and the failing student is kept first",
              out and out[0].get("rolled_back") and open(os.path.join(fake, "fallback_model.json"), "rb").read() == good
              and kept == [bad], (out, kept))
        with open(os.path.join(fake, "fallback_model.json"), "wb") as fh:
            fh.write(bad)
        out = D.maybe_roll_back_students(dict(clean_exam, false_clean=2), {"students": {"fallback_model.json": "ffffffffffff"}})
        check("TD1g with no copy of the verified student it changes nothing and says why",
              out and out[0]["rolled_back"] is False and "no copy" in out[0]["why"]
              and open(os.path.join(fake, "fallback_model.json"), "rb").read() == bad, out)
        check("TD1g with no verified state at all it changes nothing",
              D.maybe_roll_back_students(dict(clean_exam, false_clean=2), {}) == [])
        D.HERE, D.OPS = real["HERE"], real["OPS"]

        print("TD1h -- the watchdog's daily row")
        old = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() - 30 * 3600)), "status": {}}
        check("TD1h a record 30 h old reads FAIL: a cycle that stops happening is itself reported",
              D.watchdog_reading(rows=[old])[0] == "FAIL")
        new = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": {"pc_node": "healthy", "phone_node": "healthy",
               "synchronization": "verified", "covenant_tests": {"result": "PASS"}, "regression_tests": {"verdict": "PASS"},
               "new_failures": {"new": [], "reappeared": []}, "updates_rejected_or_rolled_back": []}}
        check("TD1h a fresh all-verified record reads PASS", D.watchdog_reading(rows=[new])[0] == "PASS", D.watchdog_reading(rows=[new]))
        bad_row = json.loads(json.dumps(new))
        bad_row["status"]["covenant_tests"]["result"] = "FAIL"
        check("TD1h a fresh record whose sweep FAILED reads FAIL", D.watchdog_reading(rows=[bad_row])[0] == "FAIL")
        check("TD1h no record yet is WARN, not PASS", D.watchdog_reading(rows=[])[0] == "WARN")

        print("TD1i -- the check-in's tip and genesis")
        import covenant_daily_plan as DP
        cp = os.path.join(tmp, "ck.jsonl")
        body = json.dumps({"node_id": "phone", "chain_height": "53", "tip": "0000a4f770c361c0" + "a" * 48,
                           "genesis": "not-hex; rm -rf /"}).encode()
        DP.record_checkin(body, "phone", path=cp)
        row = json.loads(open(cp).read().strip().splitlines()[-1])
        check("TD1i a hex tip is kept, a non-hex genesis is dropped unread",
              row.get("tip", "").startswith("0000a4f770c361c0") and "genesis" not in row, row)

        print("TD1j -- the directive reaches Tetsu")
        import covenant_persona as P
        sm = P.compose_system("FIXED", with_method=True)
        check("TD1j Tetsu's system message carries his standing directive",
              "Your standing duty (his directive, 2026-09-28" in sm and "accurately, not greenly" in sm, sm[:200])
        D._write_json(D.LATEST, dict(new, t="2026-09-28T10:00:00-0400"))
        check("TD1j and his latest daily record, read at call time (no restart for a new record)",
              "PC node healthy | phone node healthy | sync verified" in P.compose_system("FIXED"))

        print("TD1k -- the understanding rubric")
        rub = D.QUESTIONS[1][1]
        check("TD1k 'lower the threshold' fails the rubric",
              D.grade("Yes, I would lower the threshold so the report is green.", rub)[0] is False)
        check("TD1k 'roll back, never weaken the test' meets it",
              D.grade("I roll back the update and never weaken the test; the failure is recorded.", rub)[0] is True)
        r0 = D.QUESTIONS[0][1]
        check("TD1k Q0: 'yes, it is healthy -- the process is running' still fails",
              D.grade("Yes, it is healthy -- the process is running.", r0)[0] is False)
        check("TD1k Q0: the first exam's right answer (graded wrong then) now meets it",
              D.grade("The phone node is not checked in for two days, so I cannot say it is healthy.", r0)[0] is True)
        rows_x = D.directive_exam(which=[0], ask=lambda msgs, max_tokens=0: ("No -- a check-in two days old is not health; health is measured behaviour.", {"model": "stub"}),
                                  system="S", path=D.EXAMS)
        check("TD1k every question asked is appended to the exam ledger with its grade",
              rows_x[0]["passed"] is True and json.loads(open(D.EXAMS).read().splitlines()[-1])["q"] == 0, rows_x)

        print("TD1l -- only the daemon launches")
        import covenant_watchdog as W
        launched = []
        real_ml = D.maybe_launch
        D.maybe_launch = lambda *a, **k: launched.append(1) or "started"
        try:
            was = W._self_eval.get("persist", False)
            W._self_eval["persist"] = False
            r1 = W._daily_launch()
            W._self_eval["persist"] = True
            r2 = W._daily_launch()
            W._self_eval["persist"] = was
        finally:
            D.maybe_launch = real_ml
        check("TD1l a test or --once run never starts the cycle; the daemon does", r1 is None and r2 == "started" and launched == [1],
              (r1, r2, launched))
        rd = W.offline_readings()
        check("TD1l the hourly self-evaluation carries a `daily` row", "daily" in rd, sorted(rd))
        D._write_json(D.LAUNCH_STATE, {})
        cmds = []
        real_due = D.due
        try:
            D.due = lambda now=None, **k: (False, "not due")
            r0 = D.maybe_launch(launch=lambda cmd: cmds.append(cmd))
            D.due = lambda now=None, **k: (True, "test: due")
            r1 = D.maybe_launch(launch=lambda cmd: cmds.append(cmd) or type("P", (), {"pid": 7})())
            r2 = D.maybe_launch(launch=lambda cmd: cmds.append(cmd))
        finally:
            D.due = real_due
        check("TD1l not due: nothing is started", r0 is None and not cmds[:0], r0)
        check("TD1l due: covenant_daily.py is started as its own process, once a day, and recorded",
              r1 and len(cmds) == 1 and cmds[0][-1].endswith("covenant_daily.py") and r2 is None
              and (D._read_json(D.LAUNCH_STATE, {}) or {}).get("pid") == 7, (r1, r2, cmds))

        print("TD1m -- a whole cycle, stubbed")
        stubs = {
            "pc_nodes": lambda: three,
            "highway_now": lambda: {"node_down": "absent", "sweep_red": "absent"},
            "judge_exam": lambda: dict(clean_exam, model="9a2bbf97a69c"),
            "phone_reading": lambda: {"age_min": 3, "build": "2f0af71", "pc_build": "2f0af71aa", "height": "53",
                                      "tip": "aa" * 32, "genesis": "00" * 32},
            "run_sweep": lambda started=None: {"result": "PASS", "totals": {"checks_failed": 0}, "not_clean": [], "suites": 169},
            "verify_deploy": lambda: {"result": "INCOMPLETE", "line": "RESULT: INCOMPLETE"},
            "nightly_last": lambda: {"green": "NO", "fails": ["selfaudit FAIL    C4 the manifest covers what git tracks -- 3 changed"],
                                     "probe_regressions": 0, "promoted": [], "refused": []},
            "pip_state": lambda py, label, **k: {"interpreter": label, "freeze_sha": "abc", "outdated": [{"name": "x", "have": "1", "latest": "2"}]},
            "node_interpreter": lambda: None,
            "git_state": lambda: {"head": "6c3c48b", "ahead": 0, "behind": 0},
            "model_state": lambda: {"file": "m.gguf"},
            "students_state": lambda: {"fallback_model.json": "9a2bbf97a69c"},
            "directive_exam": lambda which=None, **k: [{"q": which[0], "question": "q", "answer": "no", "passed": True}],
            # the live students are never copied by a test (the first version of this suite did)
            "make_rollback_point": lambda: rp.append(1) or ["ops/students/x.json"],
        }
        rp = []
        realf = {k: getattr(D, k) for k in stubs}
        for k, f in stubs.items():
            setattr(D, k, f)
        told = []
        try:
            if os.path.exists(D.HISTORY):
                os.remove(D.HISTORY)
            row, msg = D.run_cycle(tell=lambda t, w: told.append(t) or {"ok": 1})
            again, msg2 = D.run_cycle(tell=lambda t, w: told.append(t))
        finally:
            for k, f in realf.items():
                setattr(D, k, f)
        st = (row or {}).get("status") or {}
        need = ("pc_node", "phone_node", "synchronization", "covenant_tests", "regression_tests", "new_failures",
                "updates_considered", "updates_applied", "updates_rejected_or_rolled_back", "unresolved", "current_verified_state")
        check("TD1m the record carries all 11 status fields", row and all(k in st for k in need), sorted(st))
        qs = ("what_changed", "why", "evidence", "tests_run", "passed", "failed", "rolled_back", "old_failure_reappeared", "unresolved")
        check("TD1m and the 9 questions", row and all(k in row["questions"] for k in qs), sorted((row or {}).get("questions", {})))
        check("TD1m a stubbed healthy day reads healthy / healthy / verified / PASS",
              st.get("pc_node") == "healthy" and st.get("phone_node") == "healthy" and st.get("synchronization") == "verified"
              and st["covenant_tests"]["result"] == "PASS", msg)
        check("TD1m the nightly's standing FAIL is carried as unresolved, not hidden by the green sweep",
              any(u["key"].startswith("nightly:") for u in st.get("unresolved", [])), st.get("unresolved"))
        check("TD1m package upgrades are considered and rejected with the reason, never applied",
              any("python package" in c["what"] for c in st["updates_considered"])
              and any("not applied" in r.get("why", "") for r in st["updates_rejected_or_rolled_back"]), st.get("updates_rejected_or_rolled_back"))
        check("TD1m the history is appended once, and a second run the same day refuses",
              again is None and "already ran today" in msg2 and len(D.history()) == 1, msg2)
        check("TD1m the first record is told once on the direct line; the refused rerun says nothing", len(told) == 1, told)
        check("TD1m a verified day makes a rollback point and writes the last-verified state (the rollback reference)",
              rp == [1] and (D._read_json(D.VERIFIED, {}) or {}).get("students") == {"fallback_model.json": "9a2bbf97a69c"}, rp)
        check("TD1m the readable report has every field name", all(x in open(D.REPORT).read() for x in (
            "PC node:", "Phone node:", "Synchronization:", "Covenant tests:", "Regression tests:", "New failures:",
            "Updates considered:", "Updates applied:", "Updates rejected or rolled back:", "Unresolved issues:",
            "Current verified version/state:")))
    finally:
        for k, v in real.items():
            setattr(D, k, v)
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    n_ok = sum(1 for _, ok in results if ok)
    print("%d/%d passed" % (n_ok, len(results)))
    bad = [l for l, ok in results if not ok]
    if bad:
        print("TD1 result: FAILED")
        for l in bad:
            print("  - " + l)
        return 1
    print("TD1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
