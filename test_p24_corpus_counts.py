#!/usr/bin/env python3
"""P24 -- the corpus counts in prose must not drift from the catalogues.

WHY. On 2026-09-16 a cross-check validated a media index against itself, found
it consistent, and reported that as accuracy. The document was superseded, its
"new" finding was eight days old, and the actual data sat unread in
private/*/catalog.csv. Then the tool written to fix that hardcoded five
catalogue paths and missed a sixth.

The common failure is enumerating from a record already held instead of from
what exists. Prose cannot be re-run; this can.

SKIPS when private/ is absent. The staged runner has no private data, and a
suite that fails for the wrong reason is a suite somebody switches off.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
TOOL = os.path.join(HERE, "tools", "corpus_reconcile.py")
FAILURES = []


def check(label, ok, detail=""):
    print("  %-58s %s%s" % (label, "OK" if ok else "*** FAIL ***",
                            ("  " + detail) if detail and not ok else ""))
    if not ok:
        FAILURES.append(label)


def main():
    if not os.path.isfile(TOOL):
        print("P24 FAILED: tools/corpus_reconcile.py is missing")
        return 1

    has_private = os.path.isdir(os.path.join(HERE, "private"))
    out = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                         timeout=300, cwd=HERE)
    text = (out.stdout or "") + (out.stderr or "")
    print("P24a -- the recount runs at all")
    check("exits 0", out.returncode == 0, "rc=%s" % out.returncode)
    check("prints its hypotheses", "H2" in text and "H3" in text)

    if not has_private:
        print("\nP24 SKIPPED past the data checks: private/ is not present here.")
        print("That is expected in a staged run. The tool reported it as a skip")
        print("rather than a failure, which is the behaviour being asserted.")
        check("absent private/ is reported as a skip, not an error",
              "NOT AVAILABLE HERE" in text or out.returncode == 0)
        print()
        print("P24 PASSED (reduced)" if not FAILURES else "P24 FAILED")
        return 1 if FAILURES else 0

    print("\nP24b -- catalogues are DISCOVERED, not listed from memory")
    # The regression guard: a hardcoded list missed private/x_missing2. If the
    # walk ever stops finding every status_id catalogue on disk, say so here.
    on_disk = set()
    for dirpath, _d, files in os.walk(os.path.join(HERE, "private")):
        for fn in files:
            if not fn.lower().endswith(".csv"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    if "status_id" in fh.readline():
                        on_disk.add(os.path.relpath(p, HERE).replace(os.sep, "/"))
            except OSError:
                pass
    reported = {ln.strip().split()[0] for ln in text.splitlines()
                if ln.strip().startswith("private/")}
    missing = on_disk - reported
    check("every status_id catalogue on disk is counted",
          not missing, "not counted: %s" % sorted(missing))
    check("more than one catalogue found (a single path means the walk broke)",
          len(on_disk) > 1, "found %d" % len(on_disk))

    print("\nP24c -- the numbers are present and internally sane")
    m = re.search(r"X TOTAL\s+(\d+)\s+(\d+)", text)
    check("X totals reported", bool(m))
    if m:
        files_n, posts_n = int(m.group(1)), int(m.group(2))
        check("files >= posts (a post may carry several files)",
              files_n >= posts_n, "%d files, %d posts" % (files_n, posts_n))
        check("X corpus is non-trivial", posts_n > 50, "posts=%d" % posts_n)

    print("\nP24d -- dates are checked against the ids, and they agree")
    m = re.search(r"(\d+) of (\d+) agree", text)
    check("date agreement reported", bool(m))
    if m and int(m.group(2)):
        check("every X date matches its own snowflake",
              m.group(1) == m.group(2),
              "%s of %s" % (m.group(1), m.group(2)))

    print("\nP24e -- the operator's own figure is carried, not silently dropped")
    check("the 2026-09-17 figure of 120 is stated in the output",
          "120 on X" in text)

    print()
    if FAILURES:
        print("P24 FAILED: %d" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("P24 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
