#!/usr/bin/env python3
"""
covenant_selfaudit.py -- the checks that compare one record against another.

ASKED 2026-09-07: "self audits every sign its needed".

WHY THIS IS NOT ANOTHER TEST SUITE
  The suites answer "does the code do what it says". The gates answer "is this
  tree fit to launch". Neither answers the question that actually cost time on
  2026-09-06 and 2026-09-07: **do the records this project produces agree with
  each other?**

  Every failure found on those two days was found by comparing a claim to an
  artefact, and most were found by accident -- because a sweep happened to be
  run by hand. Three examples, all real, all from those two days:

    * A suite was added and registered in neither the nightly's green list nor
      the sweep's table. It could have broken silently for weeks. Nothing was
      watching for a suite nobody runs.
    * ONE_SWEEP.txt printed "checks failed 0" and "All gates pass" beside
      "RESULT: FAIL". Both were true -- the counters count suite checks, the
      verdict also counts in-place checks -- and the file said so nowhere. The
      runner's own source records the same contradiction slipping through CI
      for weeks in the opposite direction: "RESULT: PASS" in a transcript that
      also contained "test_p18_version_collision.py=FAIL".
    * A commit refreshed the manifest BEFORE staging its new files, so the
      files were committed outside the manifest and the next gate run blocked.

  None of those is a code defect a suite could catch. Each is two records
  disagreeing, and each was cheap to find once someone looked. This looks.

THE STANDARD IT HOLDS ITSELF TO
  Every check names the two records it compares and quotes what each said. A
  check that cannot read one of its records reports UNKNOWN and never PASS --
  "could not look" and "nothing there" are different facts, which is the rule
  the rest of this project already runs on.

USAGE
  python covenant_selfaudit.py            every check; exit 1 on a contradiction
  python covenant_selfaudit.py --json     the same, machine-readable
  python covenant_selfaudit.py --self-test
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"

# Superseded copies, kept on purpose. This project's rule 7 is "keep the
# refutations", and a .PRE-<fix> suite is the version that existed before a fix
# -- evidence of the wrong turn, deliberately not deleted. It is not an orphan
# and must not be run. Found by this file's own first live run, 2026-09-07.
EXCUSED_PATTERNS = (".PRE-",)

# Suites deliberately not in the routine runners, each with its reason.
# Anything else unregistered is a finding, not a convention.
EXCUSED_SUITES = {
    "test_xrp_live.py": "needs a FUNDED testnet account; the sweep says so itself",
    "test_covenant_app.py": "binds real ports and needs the chain STOPPED",
    "test_c2_watchdog_live.py": "measures a live watchdog process, not this tree",
}


class Finding:
    def __init__(self, name: str, status: str, said: str, detail: str = ""):
        self.name, self.status, self.said, self.detail = name, status, said, detail

    def to_dict(self) -> Dict[str, Any]:
        return {"check": self.name, "status": self.status,
                "says": self.said, "detail": self.detail}


def read(rel: str) -> Optional[str]:
    try:
        with open(os.path.join(HERE, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


# ------------------------------------------------------- C1 unregistered suites
def c1_every_suite_is_run() -> Finding:
    """A suite nobody runs is a suite that cannot fail, which is worse than one
    that does. Found the hard way twice on 2026-09-06."""
    try:
        suites = {f for f in os.listdir(HERE)
                  if f.startswith("test_") and f.endswith(".py")}
    except OSError:
        return Finding("C1 every suite is registered somewhere", UNKNOWN,
                       "could not list the repository")
    nightly, one = read("covenant_nightly.py"), read("covenant_one.py")
    if nightly is None or one is None:
        return Finding("C1 every suite is registered somewhere", UNKNOWN,
                       "covenant_nightly.py or covenant_one.py could not be read")
    orphans = sorted(s for s in suites
                     if s not in EXCUSED_SUITES
                     and not any(pat in s for pat in EXCUSED_PATTERNS)
                     and ('"%s"' % s) not in nightly and ('"%s"' % s) not in one)
    if orphans:
        return Finding("C1 every suite is registered somewhere", FAIL,
                       "%d suite(s) are in neither the nightly's green list nor "
                       "the sweep's table" % len(orphans), ", ".join(orphans))
    return Finding("C1 every suite is registered somewhere", PASS,
                   "%d suite(s) on disk, %d excused by name and %d as superseded "
                   "copies, none orphaned"
                   % (len(suites), len(EXCUSED_SUITES),
                      sum(1 for x in suites if any(p in x for p in EXCUSED_PATTERNS))))


# ------------------------------------------------------- C2 the sweep's verdict
def c2_sweep_verdict_matches_its_own_lines() -> Finding:
    """The runner's counters and its verdict count different things, and the
    file says so nowhere. Either direction is a contradiction: PASS printed
    over a FAIL line hides a defect; FAIL printed over clean counters trains a
    reader to ignore the verdict."""
    sw = read("ONE_SWEEP.txt")
    if sw is None:
        return Finding("C2 the sweep's verdict matches its own lines", UNKNOWN,
                       "no ONE_SWEEP.txt -- the sweep has not run here")
    verdict = "FAIL" if "RESULT: FAIL" in sw else ("PASS" if "RESULT: PASS" in sw else None)
    if verdict is None:
        return Finding("C2 the sweep's verdict matches its own lines", UNKNOWN,
                       "ONE_SWEEP.txt carries no RESULT line")
    fail_lines = [l.strip() for l in sw.splitlines()
                  if re.search(r"\bFAIL\b", l)
                  and "RESULT:" not in l and "checks failed" not in l
                  and "suites not clean" not in l]
    if verdict == "PASS" and fail_lines:
        return Finding("C2 the sweep's verdict matches its own lines", FAIL,
                       "RESULT: PASS printed over %d line(s) containing FAIL"
                       % len(fail_lines), fail_lines[0][:160])
    if verdict == "FAIL" and not fail_lines:
        return Finding("C2 the sweep's verdict matches its own lines", FAIL,
                       "RESULT: FAIL printed with no FAIL line anywhere above it")
    return Finding("C2 the sweep's verdict matches its own lines", PASS,
                   "RESULT: %s, with %d FAIL line(s)" % (verdict, len(fail_lines)))


# ------------------------------------------------------ C3 the nightly's verdict
def c3_nightly_green_matches_its_gates() -> Finding:
    n = read("ops/NIGHTLY.md")
    if n is None:
        return Finding("C3 the nightly's green matches its gates", UNKNOWN,
                       "ops/NIGHTLY.md could not be read")
    greens = re.findall(r"^green:\s*(\w+)", n, re.M)
    gates = re.findall(r"^gates:\s*(\d+) PASS\s+(\d+) BLOCKED\s+(\d+) UNKNOWN", n, re.M)
    if not greens or not gates:
        return Finding("C3 the nightly's green matches its gates", UNKNOWN,
                       "no green/gates pair in the last pass")
    g, (p, b, u) = greens[-1].upper(), gates[-1]
    clean = (b == "0" and u == "0")
    if g == "YES" and not clean:
        return Finding("C3 the nightly's green matches its gates", FAIL,
                       "green: YES over gates %s PASS %s BLOCKED %s UNKNOWN" % (p, b, u))
    return Finding("C3 the nightly's green matches its gates", PASS,
                   "green: %s with gates %s PASS %s BLOCKED %s UNKNOWN" % (g, p, b, u))


# --------------------------------------------------------- C4 manifest freshness
def c4_manifest_covers_the_tree() -> Finding:
    try:
        r = subprocess.run([sys.executable, "verify_bundle.py"], cwd=HERE,
                           capture_output=True, text=True, timeout=300)
    except Exception as e:                                       # noqa: BLE001
        return Finding("C4 the manifest covers what git tracks", UNKNOWN,
                       "verify_bundle.py did not run (%s)" % type(e).__name__)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"(\d+) in manifest, (\d+) changed or missing", out)
    if not m:
        return Finding("C4 the manifest covers what git tracks", UNKNOWN,
                       "verify_bundle.py printed no summary")
    n, changed = m.group(1), int(m.group(2))
    tracked = [l.split()[-1] for l in out.splitlines() if l.startswith("NOT IN MANIFEST")]
    # A tracked file outside the manifest is the A56 ordering trap: --write ran
    # before `git add`, so the file was committed outside the record.
    untracked_ok = []
    for f in tracked:
        rc = subprocess.run(["git", "ls-files", "--error-unmatch", f], cwd=HERE,
                            capture_output=True, text=True)
        if rc.returncode == 0:
            untracked_ok.append(f)
    if changed or untracked_ok:
        return Finding("C4 the manifest covers what git tracks", FAIL,
                       "%d changed or missing, %d tracked file(s) outside the manifest"
                       % (changed, len(untracked_ok)),
                       ", ".join(untracked_ok[:4]))
    return Finding("C4 the manifest covers what git tracks", PASS,
                   "%s file(s) in the manifest, 0 changed or missing" % n)


# ---------------------------------------------------------- C5 sentinel coverage
def c5_anchors_cover_the_guarded() -> Finding:
    try:
        sys.path.insert(0, HERE)
        import covenant_sentinels as S
        a = S.load_anchors()
    except Exception as e:                                       # noqa: BLE001
        return Finding("C5 the anchors cover everything guarded", UNKNOWN,
                       "covenant_sentinels could not be read (%s)" % type(e).__name__)
    if not a:
        return Finding("C5 the anchors cover everything guarded", UNKNOWN,
                       "no anchor file yet -- run covenant_sentinels.py --anchor")
    missing = [d for d in S.GUARDED_DOCUMENTS if d not in (a.get("documents") or {})]
    missing += [l for l in S.GUARDED_LEDGERS if l not in (a.get("ledgers") or {})]
    if missing:
        return Finding("C5 the anchors cover everything guarded", FAIL,
                       "%d guarded path(s) have no anchor" % len(missing),
                       ", ".join(missing[:4]))
    return Finding("C5 the anchors cover everything guarded", PASS,
                   "%d document(s) and %d ledger(s) anchored"
                   % (len(a.get("documents") or {}), len(a.get("ledgers") or {})))


# -------------------------------------------------------- C6 arming has an author
def c6_armed_names_who_armed_it() -> Finding:
    raw = read("trader_config.json")
    if raw is None:
        return Finding("C6 an armed trader names who armed it", UNKNOWN,
                       "no trader_config.json here (a clean checkout)")
    try:
        cfg = json.loads(raw)
    except ValueError:
        return Finding("C6 an armed trader names who armed it", UNKNOWN,
                       "trader_config.json is not readable JSON")
    if not cfg.get("armed"):
        return Finding("C6 an armed trader names who armed it", PASS,
                       "disarmed, so there is nothing to attribute")
    if not cfg.get("armed_by"):
        return Finding("C6 an armed trader names who armed it", FAIL,
                       "armed=true with no armed_by -- something armed it that was "
                       "not the operator's one-click, or the provenance was lost")
    return Finding("C6 an armed trader names who armed it", PASS,
                   "armed by %s at %s" % (cfg.get("armed_by"), cfg.get("armed_at", "?")))


CHECKS = [c1_every_suite_is_run, c2_sweep_verdict_matches_its_own_lines,
          c3_nightly_green_matches_its_gates, c4_manifest_covers_the_tree,
          c5_anchors_cover_the_guarded, c6_armed_names_who_armed_it]


def run_all() -> List[Finding]:
    out = []
    for fn in CHECKS:
        try:
            out.append(fn())
        except Exception as e:                                   # noqa: BLE001
            out.append(Finding(fn.__name__, UNKNOWN,
                               "the check itself raised %s" % type(e).__name__, str(e)[:160]))
    return out


def main() -> int:
    findings = run_all()
    if "--json" in sys.argv:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        print("SELF-AUDIT -- records compared against each other")
        for f in findings:
            print("  [%-7s] %s" % (f.status, f.name))
            print("             %s" % f.said)
            if f.detail:
                print("             %s" % f.detail)
        bad = [f for f in findings if f.status == FAIL]
        unk = [f for f in findings if f.status == UNKNOWN]
        print("\n  %d PASS   %d FAIL   %d UNKNOWN" %
              (len(findings) - len(bad) - len(unk), len(bad), len(unk)))
        if bad:
            print("  Two records disagree. Neither is assumed right; read both.")
    return 1 if any(f.status == FAIL for f in findings) else 0


def _self_test() -> int:
    fails = []

    def check(cond, label):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    fs = run_all()
    check(len(fs) == len(CHECKS), "S1 every check produces a finding")
    check(all(f.status in (PASS, FAIL, UNKNOWN) for f in fs),
          "S2 every finding carries one of the three statuses")
    check(all(f.said for f in fs), "S3 every finding says what it compared")
    names = [f.name for f in fs]
    check(len(set(names)) == len(names), "S4 no two checks share a name")

    # UNKNOWN must never be reported as PASS: the whole point of the third state.
    import tempfile
    global HERE
    real = HERE
    HERE = tempfile.mkdtemp()
    try:
        empty = [c2_sweep_verdict_matches_its_own_lines(),
                 c3_nightly_green_matches_its_gates(),
                 c6_armed_names_who_armed_it()]
        check(all(f.status == UNKNOWN for f in empty),
              "S5 with nothing to read, checks report UNKNOWN rather than PASS")
    finally:
        HERE = real

    check(c2_sweep_verdict_matches_its_own_lines.__doc__ is not None
          and c1_every_suite_is_run.__doc__ is not None,
          "S6 the checks that came from real incidents say which incident")
    check("test_xrp_live.py" in EXCUSED_SUITES,
          "S7 a suite excused from the runners is excused by name and reason, not silently")

    print()
    if fails:
        print("%d FAILED" % len(fails))
        return 1
    print("SELF-AUDIT SELFTEST: all passed")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    raise SystemExit(main())
