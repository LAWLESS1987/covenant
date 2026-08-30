#!/usr/bin/env python3
"""
preflight_deps.py -- name the missing dependency BEFORE it becomes four
mysterious failures.

WHY THIS EXISTS, from a real run on 2026-08-30

  covenant_one.py --ci reported:

      suites not clean 4 -> test_k3_p9_owner_only_guard.py, probe_final_pass.py,
                            test_xrp_signer.py, test_xrp_mainnet.py
      RESULT: FAIL

  Four suites, in three different sections, one of them a SECURITY suite
  reading 14/16. That looks like a security regression. It was not. Every one
  of the four failed on the same line:

      MainnetGuardError: xrpl-py not importable (No module named 'xrpl')

  xrpl-py is DECLARED in requirements.txt. It simply was not installed on the
  machine. One absent package, four failures, and a report that named the
  symptoms in four places and the cause in none. The runner ran fifty-four
  suites without ever asking whether its own declared dependencies were
  present.

  That is the shape this file exists to prevent: a part is cut away, and
  instead of the system saying "this part is missing", unrelated things start
  failing in ways that read as defects in themselves. The signal has to name
  the cause, or the operator spends an evening auditing a security suite that
  was never broken.

WHAT IT DOES

  Reads requirements.txt -- the file that already declares the truth, so there
  is no second list to go stale -- and reports for each requirement whether it
  is installed, at what version, and whether the declared version constraint is
  actually satisfied. Where something is missing it also names the suites that
  will fail because of it, found by searching the suites themselves rather than
  from a hand-kept list.

WHAT IT DOES NOT DO

  It does not install anything. Reporting and acting are separate here for the
  same reason they are separate everywhere else in this project: an operator
  who is told what is wrong can decide; a tool that silently fixes things
  teaches nobody, and hides the drift that caused it.

PORTABLE ON PURPOSE

  Standard library only. No network. Nothing platform-specific, no shell, no
  subprocess. It gives the same answer on Windows, on Linux, on a CI runner and
  on a phone, because the whole point of a preflight is that it runs BEFORE you
  know anything is wrong, and it must never be the thing that fails.

USE
  python preflight_deps.py            # report, exit 0 if nothing is missing
  python preflight_deps.py --quiet    # only complain

LICENCE: public domain.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQ = os.path.join(HERE, "requirements.txt")

# Distribution name -> the name you actually `import`. Only needed where the
# two differ; anything absent from here is assumed to import as itself with
# hyphens turned into underscores, which covers the ordinary case.
IMPORT_NAME = {
    "xrpl-py": "xrpl",
}

# Requirement line: name, then an optional version constraint.
_REQ_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$")


def declared(path: str = REQ):
    """[(distribution, constraint, optional)] from requirements.txt.

    A requirement commented out with a '#' is read as DECLARED-BUT-OPTIONAL
    rather than ignored, because this file's own comments use that to mean
    "supported, not installed by default" (brainflow). Silently skipping those
    would hide a category the operator deliberately created.
    """
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return out
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        optional = False
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            # Only a commented line that looks like a REQUIREMENT counts; the
            # file is mostly prose commentary and that must not be parsed.
            if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*\s*[<>=!~]{1,2}\s*[0-9]", body):
                continue
            line, optional = body, True
        m = _REQ_LINE.match(line)
        if not m:
            continue
        name = m.group(1)
        constraint = m.group(2).strip()
        out.append((name, constraint, optional))
    return out


def installed_version(dist: str):
    """Version string, or None. Distribution name, not import name."""
    try:
        from importlib import metadata
    except ImportError:                                      # pragma: no cover
        return None
    try:
        return metadata.version(dist)
    except Exception:                                        # noqa: BLE001
        return None


def importable(dist: str) -> bool:
    """Can it actually be imported? Installed and importable are not the same.

    A distribution can be recorded as installed and still fail to import -- a
    partial install, a broken compiled extension, a shadowing file in the
    working directory. Since the failure that motivated this file was an
    IMPORT error, the import is the thing worth testing.
    """
    mod = IMPORT_NAME.get(dist, dist.replace("-", "_"))
    try:
        __import__(mod)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def _version_tuple(v: str):
    return tuple(int(p) for p in re.findall(r"\d+", v)[:4]) or (0,)


def satisfies(version: str, constraint: str):
    """(ok, note). Handles >=, >, ==, <=, < and a bare name.

    Deliberately small. A full PEP 440 implementation belongs in a packaging
    library, not here; this only needs to catch the case where an installed
    version is OLDER than what the project says it needs. Anything it cannot
    parse returns ok=True with a note saying it was not checked, because a
    preflight that guesses wrong and blocks a good run is worse than one that
    admits the limit.
    """
    if not constraint or version is None:
        return True, ""
    m = re.match(r"^\s*(>=|<=|==|!=|~=|>|<)\s*([0-9][0-9A-Za-z._-]*)", constraint)
    if not m:
        return True, "constraint %r not checked" % constraint
    op, want = m.group(1), m.group(2)
    have_t, want_t = _version_tuple(version), _version_tuple(want)
    if op == ">=":
        return have_t >= want_t, ""
    if op == ">":
        return have_t > want_t, ""
    if op == "<=":
        return have_t <= want_t, ""
    if op == "<":
        return have_t < want_t, ""
    if op == "==":
        return have_t == want_t, ""
    if op == "!=":
        return have_t != want_t, ""
    return True, "constraint %r not checked" % constraint


def _local_imports(src: str, known: set):
    """Which LOCAL modules this source imports (by module name, no .py)."""
    found = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)",
                         src, re.M):
        name = m.group(1)
        if name in known:
            found.add(name)
    # importlib.import_module("covenant_xrp_mainnet") and __import__("...")
    for m in re.finditer(r"""import_module\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""",
                         src):
        if m.group(1) in known:
            found.add(m.group(1))
    return found


def suites_needing(dist: str, root: str = HERE):
    """Which test files fail if this distribution is absent -- TRANSITIVELY.

    Found by searching, not from a hand-kept list. This project's recurring
    failure is a second list that goes stale: run_all_tests.sh once named
    eleven suites that were not on disk. A list derived from the files cannot
    drift from the files.

    WHY TRANSITIVE, learned by this function being WRONG on its first real
    test. Asked which suites needed xrpl-py, the first version answered
    "test_xrp_live.py" -- and the four suites that had actually just failed for
    want of xrpl-py were not among them. None of the four mentions xrpl at all.
    They import covenant_xrp_mainnet and covenant_xrp_signer, and THOSE import
    xrpl. The dependency reaches the suite through the project's own modules,
    which is exactly how a missing part does its damage: not where it is named,
    but wherever something that needed it was used.

    So: start from the modules that name the import directly, then repeatedly
    add anything importing those, until nothing new appears. Then report the
    suites in the closure.
    """
    mod = IMPORT_NAME.get(dist, dist.replace("-", "_"))
    try:
        names = sorted(f for f in os.listdir(root) if f.endswith(".py"))
    except OSError:
        return []

    known = {f[:-3] for f in names}
    src = {}
    for fn in names:
        try:
            with open(os.path.join(root, fn), "r", encoding="utf-8",
                      errors="ignore") as fh:
                src[fn[:-3]] = fh.read()
        except OSError:
            src[fn[:-3]] = ""

    direct = re.compile(r"^\s*(?:from|import)\s+%s\b" % re.escape(mod), re.M)
    alt = re.compile(r"""(?:import_module|__import__)\(\s*["']%s"""
                     % re.escape(mod))
    tainted = {name for name, body in src.items()
               if direct.search(body) or alt.search(body)}

    # Fixpoint: anything importing something tainted is itself tainted.
    changed = True
    while changed:
        changed = False
        for name, body in src.items():
            if name in tainted:
                continue
            if _local_imports(body, known) & tainted:
                tainted.add(name)
                changed = True

    return sorted(n + ".py" for n in tainted
                  if n.startswith("test_") or n.startswith("probe_"))


def check(root: str = HERE):
    """[(dist, constraint, optional, version, importable, ok, note)]."""
    rows = []
    for dist, constraint, optional in declared(os.path.join(root, "requirements.txt")):
        ver = installed_version(dist)
        imp = importable(dist)
        ok, note = satisfies(ver, constraint)
        rows.append((dist, constraint, optional, ver, imp, ok, note))
    return rows


def report(say=print, root: str = HERE, quiet: bool = False) -> int:
    """Print the state. Returns the number of REQUIRED items that are missing."""
    rows = check(root)
    if not rows:
        say("  requirements.txt not found or declared nothing -- NOT a pass, "
            "it means this check could not run.")
        return 0

    missing = [r for r in rows if not r[4] and not r[2]]
    stale = [r for r in rows if r[4] and not r[5]]
    optional_absent = [r for r in rows if not r[4] and r[2]]

    if not quiet:
        for dist, constraint, optional, ver, imp, ok, note in rows:
            if imp and ok:
                state = "ok"
            elif imp and not ok:
                state = "OLD"
            elif optional:
                state = "absent (optional)"
            else:
                state = "MISSING"
            say("    %-16s %-10s %-18s %s"
                % (dist, constraint or "(any)", ver or "-", state)
                + (("   " + note) if note else ""))

    for dist, constraint, optional, ver, imp, ok, note in missing:
        say("")
        say("    MISSING: %s is declared in requirements.txt and is NOT" % dist)
        say("    importable. Install it with:")
        say("        python -m pip install \"%s%s\"" % (dist, constraint))
        casualties = suites_needing(dist, root)
        if casualties:
            say("    Until then these will fail, and the failure will look")
            say("    like a defect in them rather than a missing package:")
            for c in casualties:
                say("        %s" % c)

    for dist, constraint, optional, ver, imp, ok, note in stale:
        say("")
        say("    OLD: %s %s is installed but requirements.txt asks for %s."
            % (dist, ver, constraint))

    for dist, constraint, optional, ver, imp, ok, note in optional_absent:
        say("")
        say("    %s is absent, and that is DECLARED OPTIONAL in "
            "requirements.txt." % dist)
        say("    Nothing here treats that as a fault. It is named so that a")
        say("    capability nobody can find is never mistaken for one that")
        say("    is merely switched off.")

    return len(missing)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    quiet = "--quiet" in argv
    print()
    print("  DECLARED DEPENDENCIES -- read from requirements.txt, changes nothing")
    print("  " + "-" * 62)
    n = report(print, HERE, quiet=quiet)
    print()
    if n:
        print("  %d declared dependency/ies MISSING. Install before trusting a"
              % n)
        print("  sweep: a suite that cannot import what it tests is not a")
        print("  failing suite, it is an unmeasured one.")
        return 1
    print("  Every declared dependency is present and importable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
