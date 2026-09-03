#!/usr/bin/env python3
"""test_n2_independent_root.py -- the conformance root, reproduced by builds that
share no code with this tree, on every sweep.

check.sh's Check 3 prints the root of docs/CONFORMANCE_SPEC.json and, since it was
written, said that nobody had reproduced THIS root. On 2026-09-03 two implementations
written from the spec alone (conformance_indep/, one PowerShell, one Python; see the
README there for how "alone" was enforced and audited) reproduced it over all 23
vectors. A reproduction that happened once is a story; this suite makes it a
measurement: it copies the CURRENT spec beside unmodified copies of both builds in a
fresh directory, runs them, and compares the root each prints to the root in the spec.

What it proves: the builds and the spec still agree. What it does not prove: that the
builds are correct in the parts no vector pins (conformance_indep/README.md lists ten).
If someone adds a vector, this suite fails until the builds agree with it -- which is
the point; a spec that drifts from its independent builds is worse than no spec.
Runs IN PLACE (covenant_one.py IN_PLACE), not from the scratch copy: it is a claim
about THE FOLDER's spec and builds, and the scratch copy carries neither the .ps1
build nor conformance_indep/ (from a scratch copy it crashed; CI found that on
2026-09-03). Exit 0 = all checks pass; 1 = a check failed.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "docs", "CONFORMANCE_SPEC.json")
BUILDS = os.path.join(HERE, "conformance_indep")
HEX64 = re.compile(r"\b([0-9a-f]{64})\b")

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, ("  -- " + detail[-200:]) if (detail and not ok) else ""))


def run(cmd, cwd, timeout=120):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def roots_in(text, label):
    """Every 64-hex string on a line that names a root of the build's OWN outputs."""
    out = []
    for line in text.splitlines():
        low = line.lower()
        if ("my outputs" in low or "root_computed" in low) and "spec" not in low.split(":")[0]:
            out += HEX64.findall(low)
    return out


def main():
    spec = json.load(io.open(SPEC, encoding="utf-8"))
    published = spec["root"]
    n = len(spec["vectors"])
    check("N2.0 spec has a 64-hex root and vectors", bool(HEX64.fullmatch(published)) and n > 0, "%s %d" % (published, n))
    for f in ("conformance_py.py", "conformance_ps.ps1", "README.md"):
        check("N2.1 %s is in the tree" % f, os.path.exists(os.path.join(BUILDS, f)))

    # independence, cheaply: neither build names a covenant module or leaves its directory
    for f in ("conformance_py.py", "conformance_ps.ps1"):
        src = io.open(os.path.join(BUILDS, f), encoding="utf-8", errors="replace").read()
        code = "\n".join(l for l in src.splitlines() if not l.strip().startswith(("#", "//", "<#")))
        bad = re.findall(r"(?i)covenant_[a-z0-9_]+|conformance\.py|import-module|sys\.path|Lawre", code)
        check("N2.2 %s references no covenant module and no path outside itself" % f, not bad, ", ".join(bad[:4]))

    tmp = tempfile.mkdtemp(prefix="c3_indep_")
    try:
        for f in ("conformance_py.py", "conformance_ps.ps1"):
            shutil.copy(os.path.join(BUILDS, f), os.path.join(tmp, f))
        shutil.copy(SPEC, os.path.join(tmp, "CONFORMANCE_SPEC.json"))

        rc, out = run([sys.executable, os.path.join(tmp, "conformance_py.py")], tmp)
        roots = roots_in(out, "py")
        check("N2.3 python build exits 0", rc == 0, out)
        check("N2.4 python build prints a root over its own outputs", bool(roots), out)
        check("N2.5 python build's root equals the published root", bool(roots) and all(r == published for r in roots), "%s vs %s" % (roots[:1], published))
        m = re.search(r"(\d+)\s*/\s*(\d+)", out)
        check("N2.6 python build matched every vector (%d)" % n, bool(m) and m.group(1) == m.group(2) == str(n), m.group(0) if m else out[-200:])

        if sys.platform == "win32" and shutil.which("powershell"):
            rc, out = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(tmp, "conformance_ps.ps1")], tmp, timeout=300)
            roots = roots_in(out, "ps")
            check("N2.7 powershell build ran", rc == 0, out)
            check("N2.8 powershell build's root equals the published root", bool(roots) and all(r == published for r in roots), "%s vs %s" % (roots[:1], published))
            m = re.search(r"(\d+)\s*/\s*(\d+)", out)
            check("N2.9 powershell build matched every vector (%d)" % n, bool(m) and m.group(1) == m.group(2) == str(n), m.group(0) if m else out[-200:])
        else:
            print("skip  N2.7-9 powershell build (not win32 or no powershell) -- unchecked here, not claimed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed, total = sum(results), len(results)
    print("\nN2: %d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
