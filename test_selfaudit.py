#!/usr/bin/env python3
"""
test_selfaudit.py -- the self-audit's own checks, as a suite the loop runs.

Same shape as test_sentinels.py and test_xrpl_record.py: the bare module runs
a LIVE audit whose result depends on the state of this machine's records,
which is a different question from "is the auditor correct". This wrapper runs
the module's offline selftest, then the checks below, and carries both exit
codes. The live audit is `python covenant_selfaudit.py`, and the nightly runs
it every pass.

WHY THERE ARE CHECKS IN THIS FILE AND NOT ONLY IN THE MODULE
  2026-09-09, found by mutation. The module's own S1-S7 ask whether every
  check PRODUCES a finding, whether the finding carries one of three statuses,
  whether the status is UNKNOWN when a record cannot be read -- and never once
  whether a check REPORTS the contradiction it was written to report. So the
  whole detection body of C1, C4 and C5 was replaced with an unconditional
  `Finding(<same name>, PASS, "ok")`, and `python test_selfaudit.py` printed
  the same seven ok lines and exited 0, byte for byte. C1 exists because "a
  suite nobody runs is a suite that cannot fail"; under the mutant C1 was
  itself a check that could not fail -- the failure mode it was written to
  prevent, reproduced inside it.

  S8-S13 below close that: one per check, each one SHOWS the check two records
  that disagree and asserts it says FAIL, then makes the same two records
  agree and asserts it says PASS. Both directions, because a check hard-wired
  to FAIL is as useless as one hard-wired to PASS. They read nothing off this
  machine -- each builds the records it needs in a temp directory and points
  the auditor at it -- so they answer "is the auditor correct" whatever state
  the tree is in. S3b turns the module's own written standard ("every check
  names the two records it compares and quotes what each said") into an
  assertion, because S3 accepts the literal word "ok" as evidence and the
  mutant's evidence was the literal word "ok".

Run:  python test_selfaudit.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_selfaudit as SA          # noqa: E402

RAN, FAILS = [], []


def check(cond, label):
    print(("ok    " if cond else "FAIL  ") + label)
    RAN.append(label)
    if not cond:
        FAILS.append(label)


_ABSENT = object()


class _records:
    """A tree of records we wrote ourselves, with the auditor pointed at it.

    Every check in covenant_selfaudit reads its records through the module
    global HERE, so moving HERE moves the whole auditor onto a tree we
    control. C4 shells out to verify_bundle.py with cwd=HERE and C5 imports
    covenant_sentinels, so this also lets the caller drop a stub
    verify_bundle.py in the directory and stand a fake sentinels module in
    front of the import. Everything is put back on the way out, including
    sys.path -- C5 appends to it -- so nothing here can colour the live audit
    the module's own S1-S5 run.
    """

    def __enter__(self):
        self._here = SA.HERE
        self._path = list(sys.path)
        self._sentinels = sys.modules.get("covenant_sentinels", _ABSENT)
        self.dir = tempfile.mkdtemp(prefix="selfaudit_probe_")
        SA.HERE = self.dir
        return self

    def write(self, rel, body):
        p = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)

    def sentinels(self, guarded, anchors):
        m = types.ModuleType("covenant_sentinels")
        m.GUARDED_DOCUMENTS = list(guarded)
        m.GUARDED_LEDGERS = []
        m.load_anchors = lambda: anchors
        sys.modules["covenant_sentinels"] = m
        return m

    def __exit__(self, *exc):
        SA.HERE = self._here
        sys.path[:] = self._path
        if self._sentinels is _ABSENT:
            sys.modules.pop("covenant_sentinels", None)
        else:
            sys.modules["covenant_sentinels"] = self._sentinels
        shutil.rmtree(self.dir, ignore_errors=True)
        return False


def behavioural_checks():
    """Drive each check into a real contradiction and read what it reports."""

    # S8 -- C1, and the 2026-09-06 incident itself: a suite on disk that
    # neither runner names. The mutant answered PASS to exactly this tree.
    with _records() as r:
        r.write("test_orphan_probe.py", "")
        r.write("covenant_nightly.py", "GREEN_SUITES = []\n")
        r.write("covenant_one.py", "SUITES = []\n")
        orphaned = SA.c1_every_suite_is_run()
        r.write("covenant_one.py", 'SUITES = [("test_orphan_probe.py", 90, "X")]\n')
        registered = SA.c1_every_suite_is_run()
    check(orphaned.status == SA.FAIL and registered.status == SA.PASS,
          "S8 a suite in neither runner is FAIL, the same suite listed in one is PASS")

    # S9 -- C2, both directions of the sweep's verdict. First: the CI history
    # quoted in the module docstring, "RESULT: PASS" over a FAIL line. Second:
    # 2026-09-06, "RESULT: FAIL" printed over counters that were all clean.
    with _records() as r:
        r.write("ONE_SWEEP.txt",
                "  test_p18_version_collision.py=FAIL rc=1\n\nRESULT: PASS\n")
        pass_over_fail = SA.c2_sweep_verdict_matches_its_own_lines()
        r.write("ONE_SWEEP.txt",
                "  checks failed 0\n  All gates pass\n\nRESULT: FAIL\n")
        fail_over_clean = SA.c2_sweep_verdict_matches_its_own_lines()
        r.write("ONE_SWEEP.txt",
                "  test_p18_version_collision.py=ok\n\nRESULT: PASS\n")
        agreed = SA.c2_sweep_verdict_matches_its_own_lines()
    check(pass_over_fail.status == SA.FAIL and fail_over_clean.status == SA.FAIL
          and agreed.status == SA.PASS,
          "S9 a verdict that contradicts the lines above it is FAIL, either direction")

    # S10 -- C3. green: YES printed over a blocked gate.
    with _records() as r:
        r.write("ops/NIGHTLY.md", "green: YES\ngates: 11 PASS 1 BLOCKED 0 UNKNOWN\n")
        blocked = SA.c3_nightly_green_matches_its_gates()
        r.write("ops/NIGHTLY.md", "green: YES\ngates: 12 PASS 0 BLOCKED 0 UNKNOWN\n")
        clean = SA.c3_nightly_green_matches_its_gates()
    check(blocked.status == SA.FAIL and clean.status == SA.PASS,
          "S10 green: YES over a BLOCKED gate is FAIL, over 0 BLOCKED 0 UNKNOWN is PASS")

    # S11 -- C4. The stub verify_bundle.py in the temp tree is the seam: this
    # asks the check what it does with the summary line, and touches no
    # manifest, no git and no network. The mutant answered PASS to a manifest
    # with three files changed or missing.
    with _records() as r:
        r.write("verify_bundle.py", "print('412 in manifest, 3 changed or missing')\n")
        drifted = SA.c4_manifest_covers_the_tree()
        r.write("verify_bundle.py", "print('412 in manifest, 0 changed or missing')\n")
        fresh = SA.c4_manifest_covers_the_tree()
    check(drifted.status == SA.FAIL and fresh.status == SA.PASS,
          "S11 a manifest with changed or missing files is FAIL, a clean one is PASS")

    # S12 -- C5. A guarded document with no anchor is a guard that cannot fire,
    # which is the same shape of hole as the mutation this file was fixed for.
    with _records() as r:
        r.sentinels(["ops/PROBE.md"], {"documents": {}, "ledgers": {}})
        unanchored = SA.c5_anchors_cover_the_guarded()
        r.sentinels(["ops/PROBE.md"],
                    {"documents": {"ops/PROBE.md": "sha256:probe"}, "ledgers": {}})
        anchored = SA.c5_anchors_cover_the_guarded()
    check(unanchored.status == SA.FAIL and anchored.status == SA.PASS,
          "S12 a guarded path with no anchor is FAIL, the same path anchored is PASS")

    # S13 -- C6. armed=true with nobody named on it.
    with _records() as r:
        r.write("trader_config.json", json.dumps({"armed": True}))
        anonymous = SA.c6_armed_names_who_armed_it()
        r.write("trader_config.json", json.dumps(
            {"armed": True, "armed_by": "operator one-click", "armed_at": "2026-09-06"}))
        attributed = SA.c6_armed_names_who_armed_it()
    check(anonymous.status == SA.FAIL and attributed.status == SA.PASS,
          "S13 armed with no armed_by is FAIL, armed with an author is PASS")

    # S3b -- the module's own standard, which S3 does not enforce: S3 accepts
    # any non-empty `said`, so the mutant reported the word "ok" as the
    # evidence for three checks and S3 passed it. A finding that cannot spare
    # three words has not named two records and quoted what each said.
    thin = [f.name for f in SA.run_all() if len(f.said.split()) < 3]
    check(not thin,
          "S3b every finding quotes what it compared, not a bare token%s"
          % ("" if not thin else " -- thin: " + ", ".join(thin)))


def main():
    # The module's S1-S7 first, echoed verbatim, then the checks above, then
    # ONE tally covering both. That tally is the line covenant_one.py and
    # covenant_nightly.py read off this suite, and it must not say "all
    # passed" while the exit code says otherwise: a verdict that contradicts
    # the lines above it is the exact fault C2 exists to catch, and a suite
    # that commits it has no standing to report it.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        inner_rc = SA._self_test()
    body = buf.getvalue()
    sys.stdout.write(body)
    inner_ok = sum(1 for l in body.splitlines() if l.startswith("ok    "))
    inner_bad = sum(1 for l in body.splitlines() if l.startswith("FAIL  "))
    if inner_ok + inner_bad == 0:            # the module changed how it prints
        inner_ok, inner_bad = (0, 1) if inner_rc else (1, 0)

    behavioural_checks()

    total = inner_ok + inner_bad + len(RAN)
    passed = total - inner_bad - len(FAILS)
    print()
    for label in FAILS:
        print("  failed: %s" % label)
    print("SELF-AUDIT SELFTEST: %d/%d checks passed" % (passed, total))
    return 1 if (inner_rc or FAILS) else 0


if __name__ == "__main__":
    raise SystemExit(main())
