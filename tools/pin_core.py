#!/usr/bin/env python3
"""tools/pin_core.py -- the core's deploy pin moves in the SAME commit as the core (M53, for good).

WHY. verify_deploy.py pins covenant_unified_v8.py by digest and line count, and "the pins move in
the SAME change as the files" has been its rule since 2026-09-02. It was broken six times by hand:
09-02, 09-11, 09-20, 09-21 (moved on time), 09-27 and 10-03 -- the last one Claude's own, after
acc64d7 moved the core and the hourly self-eval read "repo FAIL" for five days. A rule that relies
on remembering is the tombstone this project keeps re-digging. So the pre-commit hook calls this
whenever the core is in a commit.

THE ORDER (the b969 lesson, kept): a pin proves WHICH bytes arrived, never that they are right, so
the suites that judge these bytes -- K1, K2, P19, A3s -- are run FIRST. The pin moves only if all
four pass. If any fails the pin is left where it was and that is said, so verify_deploy reads red
and a person looks: refusing the commit is not this tool's call (the hook never blocks).

    python tools/pin_core.py --check     # does the pin match the core on disk? exit 0/1
    python tools/pin_core.py --write     # run the four suites; on PASS, move the pin and line count
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(HERE, "covenant_unified_v8.py")
VD = os.path.join(HERE, "verify_deploy.py")
JUDGES = ("test_k1_runner_key_preservation.py", "test_k2_tally_arithmetic.py",
          "test_p19_overlay_guard.py", "test_a3s_send_bounds.py")
PIN_RE = re.compile(r'("covenant_unified_v8\.py":\s*\n\s*")([0-9a-f]{64})(")')
LINES_RE = re.compile(r"^(EXPECTED_LINES = )(\d+)", re.M)


def core_now(path=None):
    # Resolved at CALL time: a default of CORE would bind the module's value when this line was
    # read, and pointing the tool at another core would silently hash the real one (PC2.4 caught it).
    with open(path or CORE, "rb") as fh:
        raw = fh.read()
    return hashlib.sha256(raw).hexdigest(), raw.count(b"\n")


def pinned(text):
    m, n = PIN_RE.search(text), LINES_RE.search(text)
    return (m.group(2) if m else None), (int(n.group(2)) if n else None)


def rewrite(text, sha, lines):
    """The two values replaced in place; everything else -- the history comments -- untouched.
    Counted BEFORE replacing: subn(count=1) reports 1 even when a second pin exists, which would
    half-move the file (PC2.7 caught it)."""
    if len(PIN_RE.findall(text)) != 1 or len(LINES_RE.findall(text)) != 1:
        raise ValueError("verify_deploy.py no longer has exactly one core pin and one EXPECTED_LINES")
    out = PIN_RE.sub(lambda m: m.group(1) + sha + m.group(3), text, count=1)
    return LINES_RE.sub(lambda m: m.group(1) + str(lines), out, count=1)


def run_judges(run=None):
    run = run or (lambda t: subprocess.run([sys.executable, t], cwd=HERE, capture_output=True,
                                           text=True, timeout=600).returncode)
    return [t for t in JUDGES if run(t) != 0]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    sha, lines = core_now()
    with open(VD, encoding="utf-8") as fh:
        text = fh.read()
    have_sha, have_lines = pinned(text)
    if have_sha == sha and have_lines == lines:
        print("pin_core: the pin already matches the core (%s, %d lines)" % (sha[:12], lines))
        return 0
    if "--write" not in argv:
        print("pin_core: STALE -- pinned %s / %s lines, the core is %s / %d lines"
              % ((have_sha or "?")[:12], have_lines, sha[:12], lines))
        return 1
    failed = run_judges()
    if failed:
        print("pin_core: NOT moved -- the suites that judge these bytes failed: %s. verify_deploy will read "
              "FAIL until this is looked at; that is the point." % ", ".join(failed))
        return 1
    with open(VD, "w", encoding="utf-8", newline="") as fh:
        fh.write(rewrite(text, sha, lines))
    print("pin_core: moved %s -> %s, %s -> %d lines, after K1/K2/P19/A3s passed on these bytes"
          % ((have_sha or "?")[:12], sha[:12], have_lines, lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
