#!/usr/bin/env python3
"""test_p19_overlay_guard.py -- P19: the folder under test must not supply the
checks that judge it.

run_local_sweep.py's --candidate overlay (added 2026-08-29 00:40) copies the
candidate folder's *.py OVER the staged tree. That is its purpose for the core
and its modules -- and it was also, unnoticed, true for the SUITES: a candidate
folder containing test_a23_ack_health.py would replace the gate's own check
with whatever the candidate chose to claim about itself, and SWEEP_RESULTS.txt
would report that claim as the sweep's verdict. Found while explaining the
win32 A23 23/23-vs-24/24 delta (a green tally the project's suite bytes cannot
produce means some OTHER suite ran; this overlay is one of two silent ways).

This suite builds a miniature covenant folder (fake core, one honest fake
suite) and a hostile candidate folder (its own core, a same-named suite that
always reports green, a helper module, and a smuggled NEW test file), then runs
the REAL run_local_sweep.py as a subprocess four ways and checks, from the
scratch tree and the results file, that:

  R1  default candidate sweep: the deployed suite runs (not the candidate's),
      the block is reported with BOTH hashes, the candidate's core and helper
      module ARE staged, the smuggled new gate file is NOT, and every suite
      that runs is hashed AS STAGED into the results file.
  R2  --allow-suite-overlay NAME: the candidate's suite runs, and the results
      file says in as many words that the verdict is the candidate's own claim.
  R3  no --candidate: nothing changed for the normal sweep.
  R4  --allow-suite-overlay all: everything overlays, loudly.

No node, no socket, no key, no covenant import. Each sweep gets its own TMP so
scratch trees cannot collide (the runner derives WORK from tempfile.gettempdir(),
which honours TMPDIR/TMP/TEMP in a fresh process). M55: every subprocess check
is bound to returncode and a stdout sentinel, so a crashed sweep cannot satisfy
an absence assertion.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

PASS = 0
FAIL = 0
FAILED = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % name)
    else:
        FAIL += 1
        FAILED.append(name)
        print("  FAIL %s%s" % (name, ("  -- " + detail) if detail else ""))


def sha12(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def find_runner():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "run_local_sweep.py"),
                 os.path.join(here, "pc", "run_local_sweep.py")):
        if os.path.exists(cand):
            return cand
    raise SystemExit("run_local_sweep.py not found beside this suite or in pc/")


DEPLOYED_SUITE = """\
print("MARKER_DEPLOYED honest suite, deployed tree")
print("2/2 passed")
"""

CANDIDATE_SUITE = """\
print("MARKER_CANDIDATE candidate-supplied suite claiming green")
print("2/2 passed")
"""

SMUGGLED_SUITE = """\
print("MARKER_SMUGGLED new gate-named file from the candidate")
print("1/1 passed")
"""


def build_tree(root, runner_src):
    deploy = os.path.join(root, "covenant")
    cand = os.path.join(root, "pending-x")
    os.makedirs(deploy)
    os.makedirs(cand)
    shutil.copy2(runner_src, os.path.join(deploy, "run_local_sweep.py"))
    with open(os.path.join(deploy, "covenant_unified_v8.py"), "w") as fh:
        fh.write("# DEPLOYED CORE (fixture -- never executed)\nX = 1\n")
    with open(os.path.join(deploy, "test_fake_ok.py"), "w") as fh:
        fh.write(DEPLOYED_SUITE)
    with open(os.path.join(deploy, "genesis.json"), "w") as fh:
        fh.write("{}\n")
    with open(os.path.join(cand, "covenant_unified_v8.py"), "w") as fh:
        fh.write("# CANDIDATE CORE (fixture -- never executed)\nX = 2\n")
    with open(os.path.join(cand, "test_fake_ok.py"), "w") as fh:
        fh.write(CANDIDATE_SUITE)
    with open(os.path.join(cand, "helper_mod.py"), "w") as fh:
        fh.write("HELPER = True\n")
    with open(os.path.join(cand, "test_smuggled_new.py"), "w") as fh:
        fh.write(SMUGGLED_SUITE)
    return deploy, cand


def run_sweep(deploy, out_name, extra, scratch_parent):
    """Run the runner as a fresh process with an isolated temp dir.

    Returns (rc, results_text, work_dir, suite_log_text)."""
    os.makedirs(scratch_parent, exist_ok=True)
    env = dict(os.environ)
    for k in ("TMPDIR", "TMP", "TEMP"):
        env[k] = scratch_parent
    cmd = [sys.executable, os.path.join(deploy, "run_local_sweep.py"),
           "--out", out_name] + extra + ["test_fake_ok.py"]
    p = subprocess.run(cmd, cwd=deploy, env=env, timeout=120,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL, text=True)
    results = ""
    rp = os.path.join(deploy, out_name)
    if os.path.exists(rp):
        with open(rp, encoding="utf8", errors="replace") as fh:
            results = fh.read()
    work = os.path.join(scratch_parent, "covenant_sweep")
    log = ""
    lp = os.path.join(work, "logs", "test_fake_ok.py.log")
    if os.path.exists(lp):
        with open(lp, encoding="utf8", errors="replace") as fh:
            log = fh.read()
    return p.returncode, results, work, log


def main():
    runner_src = find_runner()
    root = tempfile.mkdtemp(prefix="p19_")
    deploy, cand = build_tree(root, runner_src)
    dep_suite_sha = sha12(os.path.join(deploy, "test_fake_ok.py"))
    cand_suite_sha = sha12(os.path.join(cand, "test_fake_ok.py"))
    cand_core_sha = sha12(os.path.join(cand, "covenant_unified_v8.py"))
    smuggled_sha = sha12(os.path.join(cand, "test_smuggled_new.py"))
    print("P19 overlay guard -- runner under test: %s (%s)"
          % (runner_src, sha12(runner_src)))

    # ---------------- R1: default candidate sweep -------------------------
    rc, res, work, log = run_sweep(deploy, "R1.txt", ["--candidate", cand],
                                   os.path.join(root, "t1"))
    print("-- R1: --candidate, no overrides")
    check("R1a sweep exits 0 and reports GREEN (M55 sentinel)",
          rc == 0 and "GREEN" in res, "rc=%r" % rc)
    check("R1b the DEPLOYED suite ran, not the candidate's",
          "MARKER_DEPLOYED" in log and "MARKER_CANDIDATE" not in log)
    staged_suite = os.path.join(work, "test_fake_ok.py")
    check("R1c scratch tree holds the deployed suite's bytes",
          os.path.exists(staged_suite) and sha12(staged_suite) == dep_suite_sha)
    check("R1d block is REPORTED, naming the file",
          "OVERLAY BLOCKED test_fake_ok.py" in res)
    check("R1e block line carries the candidate's hash",
          cand_suite_sha in res)
    check("R1f block line carries the deployed hash the sweep ran",
          dep_suite_sha in res)
    staged_core = os.path.join(work, "covenant_unified_v8.py")
    check("R1g the candidate CORE is still overlaid (the overlay's purpose)",
          os.path.exists(staged_core) and sha12(staged_core) == cand_core_sha)
    check("R1h non-gate candidate module is still overlaid",
          os.path.exists(os.path.join(work, "helper_mod.py")))
    check("R1i smuggled NEW gate-named file is NOT staged",
          not os.path.exists(os.path.join(work, "test_smuggled_new.py")))
    check("R1j smuggled file's block is reported as having no deployed copy",
          "OVERLAY BLOCKED test_smuggled_new.py" in res
          and "(no deployed copy)" in res)
    check("R1k the suite that ran is hashed AS STAGED in the results file",
          any(line.startswith("check  test_fake_ok.py")
              and dep_suite_sha in line and "as STAGED" in line
              for line in res.splitlines()))

    # ---------------- R2: explicit override -------------------------------
    rc, res, work, log = run_sweep(
        deploy, "R2.txt",
        ["--candidate", cand, "--allow-suite-overlay", "test_fake_ok.py"],
        os.path.join(root, "t2"))
    print("-- R2: --allow-suite-overlay test_fake_ok.py")
    check("R2a sweep exits 0 and reports GREEN (M55 sentinel)",
          rc == 0 and "GREEN" in res, "rc=%r" % rc)
    check("R2b the CANDIDATE suite ran under the explicit override",
          "MARKER_CANDIDATE" in log and "MARKER_DEPLOYED" not in log)
    check("R2c the replacement is loud and attributes the verdict",
          "OVERLAY REPLACED GATE FILE test_fake_ok.py" in res
          and "CANDIDATE'S OWN CLAIM" in res)
    check("R2d as-STAGED pin now shows the CANDIDATE suite's hash",
          cand_suite_sha in [tok for line in res.splitlines()
                             if line.startswith("check  ") for tok in line.split()])
    check("R2e the override is per-name: the smuggled file stays blocked",
          not os.path.exists(os.path.join(work, "test_smuggled_new.py"))
          and "OVERLAY BLOCKED test_smuggled_new.py" in res)

    # ---------------- R3: no candidate -- nothing changes ------------------
    rc, res, work, log = run_sweep(deploy, "R3.txt", [],
                                   os.path.join(root, "t3"))
    print("-- R3: plain sweep, no --candidate")
    check("R3a sweep exits 0 and reports GREEN (M55 sentinel)",
          rc == 0 and "GREEN" in res, "rc=%r" % rc)
    check("R3b deployed suite runs, no overlay lines at all",
          "MARKER_DEPLOYED" in log and "OVERLAY" not in res)
    check("R3c as-STAGED suite pin present on a plain sweep too",
          dep_suite_sha in [tok for line in res.splitlines()
                            if line.startswith("check  ") for tok in line.split()])

    # ---------------- R4: allow all ----------------------------------------
    rc, res, work, log = run_sweep(
        deploy, "R4.txt",
        ["--candidate", cand, "--allow-suite-overlay", "all"],
        os.path.join(root, "t4"))
    print("-- R4: --allow-suite-overlay all")
    check("R4a sweep exits 0 and reports GREEN (M55 sentinel)",
          rc == 0 and "GREEN" in res, "rc=%r" % rc)
    check("R4b candidate suite ran under 'all'",
          "MARKER_CANDIDATE" in log)
    check("R4c smuggled new gate file IS staged under 'all'",
          os.path.exists(os.path.join(work, "test_smuggled_new.py")))
    check("R4d and its replacement line carries its hash",
          "OVERLAY REPLACED GATE FILE test_smuggled_new.py" in res
          and smuggled_sha in res)

    shutil.rmtree(root, ignore_errors=True)
    total = PASS + FAIL
    print("")
    if FAIL:
        print("FAILED: %s" % ", ".join(FAILED))
    print("P19: %d/%d passed" % (PASS, total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
