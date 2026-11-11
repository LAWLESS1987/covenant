"""VC1 -- the version is SINGLE-SOURCED (the live-readiness review's defect #4).

COVENANT_VERSION in covenant_unified_v8.py is the one truth. HANDOFF.md's "Current version"
line must state the same string, so preflight, the banner and the hand-off can never disagree
again. They had: the code was v8.40 while HANDOFF.md still said v8.18 ("266 checks") -- and
preflight printed the stale one.

Driven both ways: the extractors and the compare are exercised on matching AND mismatching
fixtures (a drift is CAUGHT), then the REAL files are asserted to agree (the live guard). Run:

    python test_vc1_version_consistency.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("ok   " if ok else "FAIL ") + name + (("  -- " + detail) if detail and not ok else ""))


def code_version(src):
    m = re.search(r'COVENANT_VERSION\s*=\s*["\']([^"\']+)["\']', src)
    return m.group(1) if m else None


def handoff_version(text):
    m = re.search(r'Current version:\s*\*\*\s*(v[0-9][^*]*?)\s*\*\*', text)
    return m.group(1).strip() if m else None


# --- both ways on the extractors + compare (hermetic fixtures) ---
check("VC1 code_version parses the constant", code_version('x\nCOVENANT_VERSION = "v9.9"\n') == "v9.9")
check("VC1 handoff_version parses the line", handoff_version("Current version: **v9.9**. ok") == "v9.9")
check("VC1 a DRIFT is caught (code v9.9 vs HANDOFF v8.1)",
      code_version('COVENANT_VERSION="v9.9"') != handoff_version("Current version: **v8.1**."))
check("VC1 a MATCH is seen (both v9.9)",
      code_version('COVENANT_VERSION="v9.9"') == handoff_version("Current version: **v9.9**."))

# --- the live guard: the real files must agree ---
with open(os.path.join(HERE, "covenant_unified_v8.py"), encoding="utf-8") as fh:
    cv = code_version(fh.read())
with open(os.path.join(HERE, "HANDOFF.md"), encoding="utf-8") as fh:
    hv = handoff_version(fh.read())
check("VC1 COVENANT_VERSION is present in the code", bool(cv), "no COVENANT_VERSION found")
check("VC1 HANDOFF.md states a 'Current version'", bool(hv), "no 'Current version: **vX**' line")
check("VC1 HANDOFF.md version == COVENANT_VERSION (single source)", cv == hv,
      "code=%r HANDOFF=%r" % (cv, hv))

n, good = len(results), sum(results)
print("\nVC1: %d/%d passed" % (good, n))
sys.exit(0 if good == n else 1)
