#!/usr/bin/env python3
"""PC2 (2026-10-03): the deploy pin moves with the core -- only after the core's judges pass.

M53 broke six times by hand (tools/pin_core.py says when). These checks drive the tool on TEMP
copies of verify_deploy.py and a core, never the real ones, with the four judging suites stubbed
both ways, plus one read of the real tree: the pin on disk matches the core on disk.

    python test_pc2_pin_core.py
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import pin_core as P  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


print("PC2 -- the deploy pin moves with the core")
real_sha, real_lines = P.core_now()
with open(P.VD, encoding="utf-8") as fh:
    real_text = fh.read()
check("PC2.1 the real tree: the pin and EXPECTED_LINES match the core on disk",
      P.pinned(real_text) == (real_sha, real_lines), (P.pinned(real_text), (real_sha[:12], real_lines)))

td = tempfile.mkdtemp(prefix="pc2_")
try:
    core = os.path.join(td, "core.py")
    with open(core, "wb") as fh:
        fh.write(b"print('a core')\n" * 7)
    vd = os.path.join(td, "verify_deploy.py")
    stale = P.rewrite(real_text, "0" * 64, 1)
    with open(vd, "w", encoding="utf-8", newline="") as fh:
        fh.write(stale)
    saved = (P.CORE, P.VD, P.run_judges)
    P.CORE, P.VD = core, vd
    want_sha, want_lines = P.core_now(core)
    try:
        check("PC2.2 --check on a stale pin says STALE and exits 1", P.main(["--check"]) == 1)
        P.run_judges = lambda run=None: ["test_k2_tally_arithmetic.py"]
        rc = P.main(["--write"])
        with open(vd, encoding="utf-8") as fh:
            after_fail = fh.read()
        check("PC2.3 a judging suite FAILS: the pin is NOT moved (the b969 order), exit 1",
              rc == 1 and after_fail == stale, rc)
        P.run_judges = lambda run=None: []
        rc = P.main(["--write"])
        with open(vd, encoding="utf-8") as fh:
            after_pass = fh.read()
        check("PC2.4 all four pass: the pin and the line count move to the core's",
              rc == 0 and P.pinned(after_pass) == (want_sha, want_lines), P.pinned(after_pass))
        strip = lambda t: P.LINES_RE.sub("", P.PIN_RE.sub("", t))  # noqa: E731
        check("PC2.5 ...and nothing else in the file changes -- the history comments stay as written",
              strip(after_pass) == strip(stale))
        check("PC2.6 --check after the move exits 0", P.main(["--check"]) == 0)
    finally:
        P.CORE, P.VD, P.run_judges = saved
    try:
        P.rewrite(real_text + '\n"covenant_unified_v8.py":\n        "' + "a" * 64 + '"\n', "b" * 64, 1)
        doubled = False
    except ValueError:
        doubled = True
    check("PC2.7 two core pins in one file is refused, never half-moved", doubled)
    hook = open(os.path.join(HERE, "ops", "pre-commit.synchold"), encoding="utf-8").read()
    check("PC2.8 the tracked hook calls the tool when the core is staged, and stages verify_deploy.py",
          "python tools/pin_core.py --write" in hook and "git add -- verify_deploy.py" in hook)
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\nnot measured here: the installed .git/hooks/pre-commit (a local file git does not track);"
      " PC2.8 reads the tracked source it is installed from")
print("\nPC2: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
