#!/usr/bin/env python3
"""test_g2_promised_commands.py -- G2: a document that promises a command must
be able to run it, and the command must describe the code that exists.

THE BUG THIS EXISTS TO CATCH, found on 2026-09-02 at the start of a session,
by `git status` rather than by any check.

CONSTITUTION.md II.1 says, of the one clause that concerns money: "Do not take
that on trust ... it is reported by a checker rather than asserted by a
document: python money_posture.py". README.md, GOVERNANCE.md (twice) and
SAFEGUARD.bat step 7 of 7 say the same. That file was DELETED from the working
tree -- uncommitted, unexplained -- and four documents plus the safeguard
script went on promising it. SAFEGUARD.bat would have printed Python's
"can't open file" and carried on to "STILL OPEN". G1 checks that explanations
do not contradict rules; nothing checked that a promised command exists.

Then, restored, the checker was found to have been wrong the day it was
written: it named two venues by hand (Kraken, Coinbase) and said "both default
to the venue's own dry-run endpoint". venues.py had held a THIRD adapter
(Robinhood) since the day before, with no venue-side dry run at all -- and
every document making the money claim named two venues and one uniform
guarantee. Code and documents did not contradict each other; the guarantee
was narrower than the sentence, and no check compared them.

WHAT G2 PINS.

  E*  every `python X.py` a governing document or safeguard script promises
      resolves to a file that exists and compiles. Not "is mentioned" --
      exists, and would at least parse if run.
  R*  the money checker the constitution names actually RUNS and can
      DETERMINE the posture. Exit 2 ("could not determine") is a failure
      here: the documents point a reader at a checker that cannot see.
  D*  every document that describes the money posture names every order
      adapter venues.py holds, and does not promise a venue-side dry run of
      "every order" when the weakest adapter's dry run is local.
  M*  the checks above are not vacuous: the regex really finds the
      constitution's own reference, and the venue list really has entries.

Reads documents and code. Runs money_posture.py (read-only by contract).
Places nothing, opens no credential.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The documents that promise commands. A .bat is a document too: it is the
# one a non-technical successor double-clicks, and the one that carried on
# past the missing file without a word.
DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    os.path.join("docs", "CONSTITUTION.md"),
    os.path.join("docs", "GOVERNANCE.md"),
    os.path.join("docs", "SUCCESSION.md"),
    "SAFEGUARD.bat",
    "GO.bat",
]

# Where a bare `python X.py` may resolve, in order. Root first. The memory
# store is its own package with its own main.py, and SUCCESSION.md promises
# `python main.py verify` from inside it. Anything that needs a THIRD entry
# here is a document that should say where it means.
SEARCH = ["", "ai_memory_system"]

# The documents that make the money claim, and therefore must name every
# adapter. money_posture.py is included on purpose: it is a document that
# happens to be executable, and it was the one that was wrong first.
MONEY_DOCS = [
    "README.md",
    os.path.join("docs", "CONSTITUTION.md"),
    os.path.join("docs", "GOVERNANCE.md"),
    "money_posture.py",
]

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:200]}", flush=True)


def read(rel):
    try:
        with open(os.path.join(HERE, rel), "r", encoding="utf-8",
                  errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def norm(t):
    t = t.replace("—", "-").replace("–", "-").replace("’", "'")
    return re.sub(r"\s+", " ", t).lower()


PROMISE = re.compile(r'(?:python|"%PY%")\s+([A-Za-z0-9_][A-Za-z0-9_.-]*\.py)\b')


def promised(rel):
    """Every script a document tells someone to run, with the line it is on."""
    out = []
    for n, line in enumerate(read(rel).splitlines(), 1):
        for m in PROMISE.finditer(line):
            out.append((m.group(1), n))
    return out


def resolve(name):
    for d in SEARCH:
        p = os.path.join(HERE, d, name)
        if os.path.isfile(p):
            return p, d or "."
    return None, None


def main():
    print("G2 -- a document that promises a command must be able to run it\n")

    # ---- E: promised commands exist and compile -----------------------------
    seen = {}
    for rel in DOCS:
        if not read(rel):
            # GO.bat is optional; the rest are not.
            check(f"E0 {rel} is readable", rel == "GO.bat", "missing")
            continue
        for name, line in promised(rel):
            seen.setdefault(name, []).append(f"{rel}:{line}")
    check("E1 the documents promise at least one command (else E* is vacuous)",
          len(seen) >= 5, sorted(seen))
    for name in sorted(seen):
        path, where = resolve(name)
        refs = ", ".join(seen[name][:4])
        check(f"E:{name:<28} exists -- promised at {refs}",
              path is not None, f"searched {SEARCH}")
        if path is None:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                compile(fh.read(), path, "exec")
            ok, why = True, ""
        except SyntaxError as e:
            ok, why = False, f"{e.__class__.__name__}: {e}"
        check(f"E:{name:<28} compiles (found in {where})", ok, why)

    # ---- M: the regex is not vacuous ---------------------------------------
    const_refs = [n for n, _ in promised(os.path.join("docs", "CONSTITUTION.md"))]
    check("M1 the regex finds money_posture.py in CONSTITUTION.md II.1 -- the "
          "reference this test was written for. If it cannot, E* passed on "
          "nothing", "money_posture.py" in const_refs, const_refs)
    check("M2 SAFEGUARD.bat step 7's \"%PY%\" money_posture.py is found too, so "
          "the .bat form of a promise is covered",
          "money_posture.py" in [n for n, _ in promised("SAFEGUARD.bat")])

    # ---- R: the named checker runs and can determine the posture -----------
    mp = os.path.join(HERE, "money_posture.py")
    rc, out = None, ""
    if os.path.isfile(mp):
        try:
            p = subprocess.run([sys.executable, mp], capture_output=True,
                               text=True, timeout=90, cwd=HERE)
            rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
        except Exception as e:                               # noqa: BLE001
            out = str(e)
    check("R1 money_posture.py runs to completion", rc is not None, out[-200:])
    check("R2 ...and DETERMINES the posture: exit 0 (disarmed) or 1 (armed). "
          "Exit 2 is 'could not determine', and four documents pointing a "
          "reader at a checker that cannot see is the failure G2 exists for",
          rc in (0, 1), f"rc={rc}")
    check("R3 ...and prints the one line a reader is told to look for",
          "DISARMED" in out or "ARMED" in out, out[-300:])

    # ---- D: money documents describe the code that exists ------------------
    try:
        import venues as V                                   # noqa: N812
        vs = list(V.all_venues())
        names = [v.name.lower() for v in vs]
        modes = {v.name: getattr(v, "DRY_RUN", None) for v in vs}
    except Exception as e:                                   # noqa: BLE001
        vs, names, modes = [], [], {}
        check("D0 venues.py imports", False, str(e))
    check("D0 venues.py holds at least three adapters (M: not vacuous)",
          len(vs) >= 3, names)
    weakest = "local" if "local" in modes.values() else "venue"
    check("D1 every adapter declares what its dry run reaches (DRY_RUN in "
          "{venue, local}) -- an adapter that declares nothing gets no "
          "adjective from any document",
          vs and all(m in ("venue", "local") for m in modes.values()), modes)

    universal = re.compile(r"every order[^.]{0,120}venue'?s own dry-run endpoint")
    for rel in MONEY_DOCS:
        doc = norm(read(rel))
        missing = [n for n in names if n not in doc]
        check(f"D:{rel:<24} names every adapter venues.py holds",
              doc and not missing, f"missing {missing}")
        m = universal.search(doc)
        check(f"D:{rel:<24} does not promise a venue-side dry run of 'every "
              f"order' while the weakest adapter's dry run is {weakest}",
              not (m and weakest == "local"),
              (m.group(0)[:100] if m else ""))

    n, ok = len(results), sum(results)
    print(f"\nG2: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
