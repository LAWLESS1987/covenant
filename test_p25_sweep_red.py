#!/usr/bin/env python3
"""test_p25_sweep_red.py -- the self-heal loop can finally SEE green.

WHERE THIS CAME FROM. The operator, 2026-09-17: "Supposed to stay green and
self heal with the swarms of students working together to preserve token count.
This should be farther ahead."

He was right, and the gap was exact. covenant_highway.py had nine detectors and
nine remedies, every one of them watching INFRASTRUCTURE -- a node, a log, a
hash, the watchdog. Not one watched the sweep's verdict, the single signal that
defines whether this repository is green. So the sweep read FAIL at 11:48 and
FAIL again at 12:38, two suites measured nothing, and the loop noticed nothing,
because every remedy it owned was correctly reporting healthy.

The cause that day was a node dying at boot on an ACL check -- and this file
ALREADY HAD remedy_restart_nodes. It was never told.

WHAT THIS SUITE PINS.
  D*  the detector reads the MEASUREMENT, finds it by CONTENT not by filename,
      takes the newest, and says UNKNOWN when it cannot tell (rule 9).
  R*  the remedy is targeted, refuses what is not its business, and reports
      failure honestly instead of retrying red into green.
  S*  THE LINE. It may restart the world; it may never edit a check, and it may
      never overwrite G12's evidence of when the suites last ran.

Behavioural throughout: every check drives the real functions on real files in
a temp directory. Nothing here greps source text -- that is A65's defect, where
35 of 36 guards were fake because they read the code instead of running it.

Pure: no network, no node, no database.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_highway as H                                    # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:300]), flush=True)


SWEEP_TEMPLATE = """\
==========================================================================
  VERDICT
==========================================================================
  suites run          120
  checks passed       3160
  checks failed       %(failed)d
  suites not clean    %(n)d%(arrow)s
  gates               PASS

  RESULT: %(verdict)s. %(tail)s
"""


def write_sweep(d, name, verdict="FAIL", unclean=(), failed=0, age_s=0):
    n = len(unclean)
    arrow = ("  -> " + ", ".join(unclean)) if unclean else ""
    txt = SWEEP_TEMPLATE % {"verdict": verdict, "n": n, "arrow": arrow,
                            "failed": failed,
                            "tail": "Something is wrong and it is named above."
                                    if verdict == "FAIL" else
                                    "Everything this runner names was measured and correct."}
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(txt)
    if age_s:
        old = time.time() - age_s
        os.utime(p, (old, old))
    return p


def main():
    print("P25 -- the highway can see the sweep's verdict\n")
    tmp = tempfile.mkdtemp(prefix="p25_")
    real_here = H.HERE
    try:
        H.HERE = tmp

        # ---- D: the detector reads the measurement -------------------------
        r = H.detect_sweep_red()
        check("P25.D1 with NO sweep artifact the answer is UNKNOWN, not "
              "ABSENT -- an unread verdict is not a passing one (rule 9)",
              r["state"] == H.UNKNOWN, r)

        write_sweep(tmp, "ONE_SWEEP.txt", "FAIL",
                    unclean=["test_a.py", "test_b.py"])
        r = H.detect_sweep_red()
        check("P25.D2 a FAILING sweep is PRESENT -- the thing that was "
              "invisible to this loop all along",
              r["state"] == H.PRESENT and r["measured"]["verdict"] == "FAIL", r)
        check("P25.D3 and it names the suites that measured nothing",
              r["measured"]["unclean"] == ["test_a.py", "test_b.py"],
              r["measured"])

        write_sweep(tmp, "ONE_SWEEP.txt", "PASS")
        r = H.detect_sweep_red()
        check("P25.D4 a PASSING sweep is ABSENT -- the detector is driven BOTH "
              "ways, so a green here has been observed and not assumed",
              r["state"] == H.ABSENT, r)

        # Discovery by CONTENT, not by a filename list (rule 2).
        os.remove(os.path.join(tmp, "ONE_SWEEP.txt"))
        with open(os.path.join(tmp, "notes.txt"), "w", encoding="utf-8") as fh:
            fh.write("RESULT: PASS. but this is prose, it has no suite count\n")
        r = H.detect_sweep_red()
        check("P25.D5 a .txt that merely CONTAINS 'RESULT:' is not a sweep -- "
              "prose about data is not data (rule 1)",
              r["state"] == H.UNKNOWN, r)

        # A file the hardcoded list could never have known about.
        write_sweep(tmp, "SWEEP_INVENTED_TOMORROW.txt", "FAIL",
                    unclean=["test_z.py"])
        r = H.detect_sweep_red()
        check("P25.D6 an artifact whose NAME nobody wrote down is still found, "
              "because the filter is content -- the file added after the list "
              "was written is the one a freshness check exists to catch",
              r["state"] == H.PRESENT and r["measured"]["unclean"] == ["test_z.py"],
              r["measured"])

        write_sweep(tmp, "OLD_SWEEP.txt", "PASS", age_s=90000)
        r = H.detect_sweep_red()
        check("P25.D7 the NEWEST artifact decides -- a stale green cannot "
              "outvote a fresh red",
              r["state"] == H.PRESENT, r["measured"])

        # P25.D8 -- A REAL REGRESSION, 2026-09-18. The content filter asked only
        # whether "RESULT:" and "suites run" appeared. A
        # `covenant_one.py --check` transcript carries both and ends
        # `RESULT: INCOMPLETE` -- gates only, no sweep, no tally. Running the
        # gates for convenience therefore wrote the NEWEST matching file, D7's
        # rule preferred it, the verdict regex could not read it, and the one
        # detector that watches whether the sweep is green went UNKNOWN with a
        # perfectly good ONE_SWEEP.txt sitting beside it. The blinding lasted
        # about an hour and was found by asking why the system was failing.
        for n in ("ONE_SWEEP.txt", "SWEEP_INVENTED_TOMORROW.txt", "OLD_SWEEP.txt",
                  "notes.txt"):
            try:
                os.remove(os.path.join(tmp, n))
            except OSError:
                pass
        write_sweep(tmp, "ONE_SWEEP.txt", "FAIL", unclean=["test_a126.py"], failed=2)
        with open(os.path.join(tmp, "ONE_CHECK.txt"), "w", encoding="utf-8") as fh:
            fh.write("  suites run          0\n"
                     "  RESULT: INCOMPLETE. Nothing failed; something was not measured.\n")
        os.utime(os.path.join(tmp, "ONE_CHECK.txt"), None)   # the NEWEST file
        r = H.detect_sweep_red()
        check("P25.D8 a --check transcript (RESULT: INCOMPLETE) is NOT a sweep "
              "verdict, even though it is newest and contains both trigger "
              "phrases -- the real red is still read",
              r["state"] == H.PRESENT
              and r["measured"].get("artifact") == "ONE_SWEEP.txt"
              and r["measured"].get("unclean") == ["test_a126.py"],
              r["measured"])

        os.remove(os.path.join(tmp, "ONE_SWEEP.txt"))
        r = H.detect_sweep_red()
        check("P25.D8b ...and with ONLY a verdictless transcript the answer is "
              "UNKNOWN that NAMES what it skipped, never ABSENT",
              r["state"] == H.UNKNOWN
              and "ONE_CHECK.txt" in (r["measured"].get("skipped_no_verdict") or []),
              r["measured"])

        # ---- R: the remedy is targeted and honest --------------------------
        ok, why = H.remedy_rerun_unclean({"unclean": []}, dry_run=True)
        check("P25.R1 red with NO unclean suite is refused -- real failing "
              "checks are not a re-run's business",
              ok is False and "not the answer" in why, why)

        many = ["t%d.py" % i for i in range(H.MAX_TARGETED_RERUN + 1)]
        ok, why = H.remedy_rerun_unclean({"unclean": many}, dry_run=True)
        check("P25.R2 too many unclean suites is refused as a broken tree, "
              "not papered over", ok is False and "broken tree" in why, why)

        ok, why = H.remedy_rerun_unclean({"unclean": ["test_a.py"]}, dry_run=True)
        check("P25.R3 a dry run says what it WOULD do and does not do it",
              ok is True and "would re-run" in why, why)

        # ---- S: the line that must not move --------------------------------
        # Drive the real remedy with subprocess captured. Behavioural: we read
        # the argv it actually builds, not the source that builds it.
        seen = {}

        class _P:
            returncode = 0
            stdout = "  suites not clean    0\n  RESULT: PASS.\n"
            stderr = ""

        import subprocess as _sp
        real_run = _sp.run

        def fake_run(argv, **kw):
            seen["argv"] = list(argv)
            return _P()

        before = {}
        for f in ("test_a1a_a2.py", "test_p25_sweep_red.py"):
            p = os.path.join(real_here, f)
            if os.path.exists(p):
                before[f] = (os.path.getmtime(p), os.path.getsize(p))

        _sp.run = fake_run
        try:
            ok, why = H.remedy_rerun_unclean({"unclean": ["test_a1a_a2.py"]},
                                             dry_run=False)
        finally:
            _sp.run = real_run

        argv = seen.get("argv") or []
        check("P25.S1 it runs the RUNNER on ONLY the named suite -- never the "
              "whole ~14-minute sweep, which is the token cost the operator "
              "named",
              any("covenant_one.py" in str(a) for a in argv) and "--only" in argv
              and "test_a1a_a2.py" in argv, argv)

        out_val = argv[argv.index("--out") + 1] if "--out" in argv else ""
        check("P25.S2 it NEVER writes ONE_RUN.txt or ONE_SWEEP.txt -- those are "
              "G12's evidence of when the suites last ran, and a two-suite "
              "re-run is not that. Overwriting them destroyed that evidence once",
              os.path.basename(out_val) not in ("ONE_RUN.txt", "ONE_SWEEP.txt")
              and out_val != "", out_val)

        after = {}
        for f in before:
            p = os.path.join(real_here, f)
            after[f] = (os.path.getmtime(p), os.path.getsize(p))
        check("P25.S3 THE LINE: not one test file was touched. It may restart "
              "the world; it may never edit a check",
              before == after, (before, after))

        check("P25.S4 a clean re-run reports success AND still carries what was "
              "red -- both readings, so the loop cannot look good by forgetting",
              ok is True and "was unclean" in why, why)

        # And the honest failure path: still unclean afterwards.
        class _Q(_P):
            stdout = "  suites not clean    1  -> test_a1a_a2.py\n  RESULT: FAIL.\n"

        _sp.run = lambda argv, **kw: _Q()
        try:
            ok2, why2 = H.remedy_rerun_unclean({"unclean": ["test_a1a_a2.py"]},
                                               dry_run=False)
        finally:
            _sp.run = real_run
        check("P25.S5 still unclean after the re-run REPORTS FAILURE -- a loop "
              "that cannot fail honestly launders red into green by repetition",
              ok2 is False and "not transient" in why2, why2)

        # ---- M: mutual benefit rides EVERY row, not only the refusals ------
        # His correction, 2026-09-17: "Its only dangerous without mutual
        # benefit." A quiet repair is not dangerous for being quiet; it is
        # dangerous when it is ASYMMETRIC -- the system keeps running, the
        # operator carries a false belief and was never told the price. This
        # file refused with gains and cost attached and APPLIED with neither,
        # which is that asymmetry inside the mechanism built to prevent it.
        led = os.path.join(tmp, "ledger.jsonl")
        write_sweep(tmp, "ONE_SWEEP.txt", "FAIL", unclean=["test_a.py"])
        cond = H.detect_sweep_red()
        row = H.apply_remedy("rerun_unclean", cond, "sweep_red",
                             dry_run=True, ledger=led)
        b = row.get("benefit")
        check("P25.M1 an APPLIED row carries who gained and what it cost -- the "
              "price is stated when something happens, not only when it is "
              "refused",
              isinstance(b, dict) and bool(b.get("gains")) and bool(b.get("cost")),
              row.get("outcome"))
        check("P25.M2 and the cost is a real sentence, not an empty list "
              "standing in for one -- a gain with a blank price is the "
              "asymmetry wearing the accounting's clothes",
              isinstance(b, dict) and all(str(c).strip() for c in b.get("cost", [])),
              b)

        # ---- T: a student may surpass; it may never clear itself -----------
        # "Students surpass teachers children parents is ideal. But respect
        # remains." (operator, 2026-09-17). standing() makes my benefit claims
        # auditable against what actually happened, so ratification can be
        # informed instead of blind. The line it must not cross is the same one
        # A126.Z1 draws for a judge seat: a seat may hold, may differ, may be
        # right where the trunk is wrong -- and false clears stay at zero.
        st = H.standing(ledger=led)
        check("P25.T1 standing grades every registered remedy against the "
              "ledger, and UNPROVEN is a real answer rather than a bad one",
              set(st) == set(H.REMEDIES) and all(
                  v["verdict"] in ("EARNED", "MIXED", "FAILING", "UNPROVEN")
                  for v in st.values()), sorted(st))
        check("P25.T2 nothing ratifies ITSELF -- every entry reports "
              "ratified False, because ratification is the operator's act",
              all(v["ratified"] is False for v in st.values()))

        # THE LINE, driven: give every remedy a spotless record and show that
        # not one decision changes. A record that bought authority would be a
        # student grading its own theft.
        real_standing = H.standing
        H.standing = lambda ledger=None: {
            k: {"verdict": "EARNED", "graded": 99, "fixed": 99,
                "did_not_fix": 0, "started_ungraded": 0, "refused": 0,
                "claimed": [], "claimed_cost": [], "ratified": True}
            for k in H.REMEDIES}
        try:
            ok_a, why_a = H.remedy_rerun_unclean({"unclean": []}, dry_run=True)
            many2 = ["t%d.py" % i for i in range(H.MAX_TARGETED_RERUN + 1)]
            ok_b, why_b = H.remedy_rerun_unclean({"unclean": many2}, dry_run=True)
        finally:
            H.standing = real_standing
        check("P25.T3 a PERFECT record buys nothing: the same refusals stand, "
              "word for word. Standing is evidence for the operator, never "
              "authority the system grants itself",
              ok_a is False and "not the answer" in why_a
              and ok_b is False and "broken tree" in why_b, (why_a, why_b))

        # ---- registration: wired in, not merely written --------------------
        check("P25.W1 the detector is registered, so sense() actually runs it",
              H.DETECTORS.get("sweep_red") is H.detect_sweep_red)
        check("P25.W2 the remedy is registered FOR sweep_red, so a red sweep "
              "reaches a repair instead of sitting there",
              "sweep_red" in H.REMEDIES["rerun_unclean"]["for"])
        check("P25.W3 it is classed AUTO_REVERSIBLE and touches no money term",
              H.REMEDIES["rerun_unclean"]["klass"] == H.AUTO_REVERSIBLE
              and not any(t in H.NEVER_AUTOMATIC
                          for t in H.REMEDIES["rerun_unclean"]["touches"]))

        H.HERE = real_here
        s = H.sense(only=["sweep_red"])
        check("P25.W4 sense() reaches it on the REAL tree without raising",
              "sweep_red" in s and s["sweep_red"]["state"] in
              (H.PRESENT, H.ABSENT, H.UNKNOWN), s)

    finally:
        H.HERE = real_here
        shutil.rmtree(tmp, ignore_errors=True)

    ok_n = sum(1 for r in results if r)
    print("\nP25: %d/%d passed" % (ok_n, len(results)))
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
