#!/usr/bin/env python3
"""A298 -- the scratch copy carries every folder the repository tracks, or says why not.

covenant_one.stage() copies the folder into a scratch directory and the sweep (public CI included) runs from
there. Four times a folder the code needed was not copied, and each time a suite measured the copy instead of
the repository: root .md files (2026-09-10), CONTRIBUTING.md for G1, conformance_indep/ for N2, and on
2026-10-07 ai_memory_system/, which A294's threefold witness imports -- H1tf read UNKNOWN in the copy and
public CI went red from 2512aec on, while H1 passed in the folder.

  S1  every top-level folder git tracks is in STAGE_DIRS or NOT_STAGED (with a reason), discovered by
      git ls-files, never by a list
  S2  the check names a planted folder that is in neither (the check can fail)
  S3  a real stage() copy carries every STAGE_DIRS folder that exists here, and IN THAT COPY the threefold
      witness's chain check runs (_verify_chain_text on an empty ledger verifies)

In place: S1 needs git, which the copy does not have. Not measured: whether a suite in the copy reads a file
inside an excused folder and passes vacuously -- that is G1's P4 lesson, and each reason says what is known.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_one as C  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


def uncovered(tracked, staged, not_staged):
    """Tracked top-level folders in neither list, and excused ones without a reason."""
    return sorted(d for d in tracked if d not in staged and not str(not_staged.get(d) or "").strip())


print("A298 -- the scratch copy carries every tracked folder, or says why not")
r = subprocess.run(["git", "--no-optional-locks", "ls-files"], cwd=HERE, capture_output=True, text=True, timeout=60)
tracked = sorted({p.split("/", 1)[0] for p in r.stdout.splitlines() if "/" in p}) if r.returncode == 0 else []
check("S1 git names the tracked folders (a population, not nothing)", len(tracked) >= 5, (r.returncode, r.stderr[:200]))
missing = uncovered(tracked, C.STAGE_DIRS, C.NOT_STAGED)
check("S1 every tracked top-level folder is staged or excused with a reason (%d tracked)" % len(tracked),
      not missing, "in neither list: %s -- stage it in covenant_one.STAGE_DIRS or say why in NOT_STAGED" % missing)
check("S1 ai_memory_system/ is staged (the threefold witness imports it)", "ai_memory_system" in C.STAGE_DIRS)

check("S2 a planted folder in neither list is named; an excused one with an empty reason is named too",
      uncovered(tracked + ["planted_dir"], C.STAGE_DIRS, C.NOT_STAGED) == ["planted_dir"]
      and uncovered(["x"], (), {"x": "  "}) == ["x"])

work = None
try:
    work = C.stage(lambda *a: None)
    carried = [d for d in C.STAGE_DIRS if os.path.isdir(os.path.join(HERE, d))]
    absent = [d for d in carried if not os.path.isdir(os.path.join(work, d))]
    check("S3 the staged copy carries every STAGE_DIRS folder that exists here (%d)" % len(carried), not absent, absent)
    p = subprocess.run([sys.executable, "-c", "import covenant_highway as H; r = H._verify_chain_text(''); "
                        "print('OK' if r.get('ok') is True and r.get('entries') == 0 else 'BAD %r' % (r,))"],
                       cwd=work, capture_output=True, text=True, timeout=180,
                       env=dict(os.environ, PYTHONPATH=""))
    check("S3 in the staged copy the threefold witness's chain check runs (the path that failed on public CI)",
          p.stdout.strip().endswith("OK"), (p.stdout[-300:], p.stderr[-400:]))
finally:
    if work and os.path.basename(work).startswith("covenant_one_"):
        shutil.rmtree(work, ignore_errors=True)

print("\nnot measured here: whether a staged suite passes vacuously on a file inside an excused folder.")
print("\nA298: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
