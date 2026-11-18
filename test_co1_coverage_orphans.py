#!/usr/bin/env python3
"""CO1 -- a suite nobody runs is called an orphan wherever the sweep carries it (A425).

covenant_one.phase_coverage asks whether the runner's list matches the disk. Until 2026-11-14 it asked the
root only, and it skipped any name holding ".PRE-" without saying so. So a suite in a folder the sweep stages
could be in no list and never be named: ai_memory_system/test_intent_provenance.py (32 checks) was run by
nobody, a second instance of A419, which had listed the two suites it found and left the search as it was.

This drives the REAL phase_coverage against a scratch tree, with the runner's lists swapped for small ones, and
reads what it returns and what it prints. Nothing is written outside the scratch tree, which is removed.

  O1  the control: at the root an unlisted suite is an orphan and a listed one is not (true before and after)
  O2  a root file with ".PRE-" in its name is an orphan                              (hidden before A425)
  O3  an unlisted suite in a staged folder is an orphan, named by its path           (unseen before A425)
  O4  ...at any depth, and with ".PRE-" in its name
  O5  listed by path, or on the off-record by path, it is not an orphan; a file that matches no suite pattern
      is not one either
  O6  what the copy leaves out of a staged folder is not searched (tools/llama, __pycache__, eval/outside/raw)
  O7  the orphans are exactly the planted ones, and the transcript names each on its own ORPHAN line
  O8  the other way: put each on a list or the off-record and the phase reports none
  O9  THIS tree: none of the six paths A425 wrote down is an orphan, and each is named when taken off its list

NOT MEASURED, and pinned so it is not read as covered (O6b): a folder the sweep does not stage (NOT_STAGED:
mobile, .claude, ...) is not searched, so an unrun suite there is still not named. Nor does this read what a
suite checks: a listed suite that measures nothing is still listed.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_one as C  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (str(note)[:300],)))


def coverage(tree, suites, in_place, off):
    """The real phase_coverage, pointed at `tree` with these lists. Returns (orphans, transcript). The runner's
    own folder and lists are put back whatever happens."""
    saved = (C.HERE, C.SUITES, C.IN_PLACE, C.DELIBERATELY_OFF)
    said = []
    try:
        C.HERE, C.SUITES, C.IN_PLACE, C.DELIBERATELY_OFF = tree, suites, in_place, off
        _absent, orphans, _deps, _ignored = C.phase_coverage(lambda line="": said.append(str(line)))
    finally:
        C.HERE, C.SUITES, C.IN_PLACE, C.DELIBERATELY_OFF = saved
    return list(orphans), "\n".join(said)


def plant(tree, rel):
    p = os.path.join(tree, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("print('planted by CO1: %s')\n" % rel)


print("CO1 -- an unrun suite is an orphan wherever the sweep carries it")
check("O0 the folders this test plants in are folders the runner stages",
      all(d in C.STAGE_DIRS for d in ("ai_memory_system", "tools", "pending-v8.38", "eval"))
      and "mobile" not in C.STAGE_DIRS, C.STAGE_DIRS)

tree = tempfile.mkdtemp(prefix="co1_tree_")
try:
    LISTED = ["test_listed_root.py", "ai_memory_system/test_listed_sub.py"]
    IN_PLACE = ["test_in_place.py"]
    OFF = {"probe_off_root.py": "planted: off the record at the root",
           "tools/test_off_sub.py": "planted: off the record by path"}
    WANT = ["ai_memory_system/deep/er/verify_deep.py",      # O4: any depth
            "ai_memory_system/test_unlisted_sub.py",        # O3: the A425 shape
            "pending-v8.38/test_snap.PRE-HELD.py",          # O4: ".PRE-" inside a staged folder
            "test_snapshot.PRE-FIX.py",                     # O2: ".PRE-" at the root
            "test_unlisted_root.py",                        # O1: the control
            "tools/sim_unlisted.py"]                        # O3: another staged folder, another pattern
    QUIET = ["helper.py", "ai_memory_system/notes.py",                  # match no suite pattern
             "ai_memory_system/__pycache__/test_cached.py",             # the copy leaves these three out
             "tools/llama/test_runtime.py", "eval/outside/raw/test_bulk.py",
             "mobile/test_not_staged.py"]                               # a folder the sweep does not stage
    for rel in LISTED + IN_PLACE + list(OFF) + WANT + QUIET:
        plant(tree, rel)

    suites = [(s, 60, "PLANTED") for s in LISTED]
    in_place = [(s, 60, "planted") for s in IN_PLACE]
    orphans, said = coverage(tree, suites, in_place, OFF)

    check("O1 control: an unlisted suite at the root is an orphan, a listed one and an in-place one are not",
          "test_unlisted_root.py" in orphans and "test_listed_root.py" not in orphans
          and "test_in_place.py" not in orphans, orphans)
    check("O2 a root file with '.PRE-' in its name is an orphan, not skipped by its name",
          "test_snapshot.PRE-FIX.py" in orphans, orphans)
    check("O3 an unlisted suite in a staged folder is an orphan, named by its path",
          "ai_memory_system/test_unlisted_sub.py" in orphans and "tools/sim_unlisted.py" in orphans, orphans)
    check("O4 ...at any depth, and with '.PRE-' in its name",
          "ai_memory_system/deep/er/verify_deep.py" in orphans
          and "pending-v8.38/test_snap.PRE-HELD.py" in orphans, orphans)
    check("O5 listed by path or off the record by path is not an orphan; a file matching no pattern is not one",
          not [o for o in orphans if o in LISTED or o in OFF or o in ("helper.py", "ai_memory_system/notes.py")],
          orphans)
    check("O6 what the copy leaves out of a staged folder is not searched",
          not [o for o in orphans if "__pycache__" in o or "llama" in o or "/raw/" in o], orphans)
    check("O6b NOT MEASURED, pinned: a folder the sweep does not stage is not searched",
          "mobile/test_not_staged.py" not in orphans, orphans)
    check("O7 the orphans are exactly the %d planted ones" % len(WANT), orphans == sorted(WANT), orphans)
    named = [w for w in WANT if ("ORPHAN   %s" % w) in said]
    check("O7 the transcript names each orphan on its own ORPHAN line, and does not say 'none'",
          named == WANT and "ORPHAN   none" not in said, [w for w in WANT if w not in named])

    # ---- the other way: every planted orphan goes on a list or the off-record, and the phase reports none
    suites2 = suites + [(w, 60, "PLANTED") for w in WANT[:3]]
    off2 = dict(OFF, **{w: "planted: now on the record" for w in WANT[3:]})
    orphans2, said2 = coverage(tree, suites2, in_place, off2)
    check("O8 listed or put on the off-record, none is an orphan and the transcript says so",
          orphans2 == [] and "ORPHAN   none" in said2, orphans2)
    check("O8 the runner's own folder and lists were put back after each call",
          C.HERE == HERE and len(C.SUITES) > 100 and "test_e3_witness_loop.py" in C.DELIBERATELY_OFF)
finally:
    shutil.rmtree(tree, ignore_errors=True)

# ---- THIS tree, with the runner's real lists. Whether the whole tree has no orphan is the runner's own phase 1,
# asked in the folder on every run; here it is the six paths A425 wrote down, both ways. (This suite runs in the
# scratch copy, where an earlier suite may have left a file behind, so it does not assert on the rest.)
A425_PATHS = ["ai_memory_system/test_intent_provenance.py", "pending-v8.38/test_competence.py",
              "pending-v8.38/test_sem5_register_coverage.py", "pending-v8.38/test_semantic_judge.py",
              "quant/test_backtest_guardrails.py", "sentinel_witness/verify_record.py"]
present = [p for p in A425_PATHS if os.path.isfile(os.path.join(HERE, p.replace("/", os.sep)))]
check("O9 the six paths A425 wrote down are on this disk (a population, not nothing)", present == A425_PATHS,
      [p for p in A425_PATHS if p not in present])
real, _said = coverage(HERE, C.SUITES, C.IN_PLACE, C.DELIBERATELY_OFF)
check("O9 with the runner's real lists none of the six is an orphan on this tree",
      not [p for p in A425_PATHS if p in real], real)
missed = []
for p in present:
    got, _ = coverage(HERE, [s for s in C.SUITES if s[0] != p], C.IN_PLACE,
                      {k: v for k, v in C.DELIBERATELY_OFF.items() if k != p})
    if p not in got:
        missed.append((p, got))
check("O9 taken off its list, each of the six is named an orphan on this tree", not missed, missed)
check("O9 each reason on the off-record is written out, not blank",
      all(str(C.DELIBERATELY_OFF.get(p) or "").strip() for p in A425_PATHS[1:]),
      [p for p in A425_PATHS[1:] if not str(C.DELIBERATELY_OFF.get(p) or "").strip()])

print("\nCO1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
