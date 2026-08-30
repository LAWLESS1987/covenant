#!/usr/bin/env python3
"""test_d1_preflight_deps.py -- D1: the missing part must NAME ITSELF.

WHAT D1 PINS, and the run that caused it to exist.

On 2026-08-30 covenant_one.py --ci reported four unclean suites across three
sections -- one of them a SECURITY suite reading 14/16, which is what a
security regression looks like. There was no regression. All four failed on
one line: xrpl-py not importable. The package is DECLARED in requirements.txt
and simply was not installed. The runner named four symptoms and zero causes,
having never once asked whether its own declared dependencies were present.

preflight_deps.py asks. This suite pins the properties that make its answer
worth having:

  P*  requirements.txt is parsed as it is actually written -- constraints,
      prose comments that are not requirements, and the commented-out
      requirement that means DECLARED OPTIONAL rather than absent.
  T*  THE REGRESSION. Casualties are found TRANSITIVELY. The first version of
      suites_needing searched for the import name in the suites and answered
      "test_xrp_live.py" -- while the four suites that had just failed for want
      of xrpl-py were not in its answer, because not one of them mentions xrpl.
      They import covenant_xrp_mainnet, which does. A missing part does its
      damage wherever something that needed it was used, not where it is named,
      and a tool that only looks one level deep will confidently miss the
      actual casualties.
  V*  a version older than the constraint is reported, and an unparseable
      constraint says so rather than guessing.
  R*  IT ONLY REPORTS. No install, no subprocess, no network. A preflight that
      changes the machine hides the drift it exists to expose.
  F*  it fails SAFE. Unreadable or absent requirements.txt is reported, never
      raised -- a preflight that crashes takes down the run it precedes, which
      is worse than the problem it was added to catch.

Pure. No network, no install, no subprocess.
"""
import ast
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preflight_deps as p   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def _tree(files):
    """Write a throwaway package tree; return its path."""
    d = tempfile.mkdtemp(prefix="d1_")
    for name, body in files.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    return d


def main():
    print("D1 -- the missing dependency names itself, and its casualties\n")

    # ---- P: parsing what requirements.txt actually says --------------------
    d = _tree({"requirements.txt": (
        "# Covenant runtime dependencies\n"
        "flask>=2.3\n"
        "\n"
        "# W1 -- prose about waitress that is NOT a requirement line at all,\n"
        "# and must not be parsed as one just because it mentions waitress.\n"
        "waitress>=2.1\n"
        "xrpl-py>=4.0\n"
        "# brainflow>=5.10\n")})
    try:
        got = p.declared(os.path.join(d, "requirements.txt"))
        names = [g[0] for g in got]
        check("P1 every real requirement is found, and prose commentary is "
              "not mistaken for one",
              names == ["flask", "waitress", "xrpl-py", "brainflow"], names)
        check("P2 the version constraint is carried, not discarded -- it is "
              "the difference between 'installed' and 'new enough'",
              dict((g[0], g[1]) for g in got)["flask"] == ">=2.3", got)
        check("P3 a COMMENTED-OUT requirement is declared-optional, not "
              "invisible: a capability nobody can find must never be "
              "confused with one deliberately switched off",
              dict((g[0], g[2]) for g in got) ==
              {"flask": False, "waitress": False, "xrpl-py": False,
               "brainflow": True}, got)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ---- T: THE REGRESSION -- casualties are transitive --------------------
    # Synthetic, so this keeps pinning the property even if the real repo's
    # XRP wiring changes shape entirely.
    d = _tree({
        "requirements.txt": "leafpkg>=1.0\n",
        "mid_layer.py":     "import leafpkg\n",
        "deeper_layer.py":  "import mid_layer\n",
        "test_far.py":      "import deeper_layer\n",     # two hops from leafpkg
        "test_near.py":     "import leafpkg\n",          # names it directly
        "test_unrelated.py": "import os\n",
    })
    try:
        got = p.suites_needing("leafpkg", d)
        check("T1 a suite that names the import directly is found",
              "test_near.py" in got, got)
        check("T2 THE REGRESSION: a suite TWO hops away is found too. The "
              "first version answered only T1's case and missed every suite "
              "that actually failed, because none of them mentions the "
              "package -- they import a module that does",
              "test_far.py" in got, got)
        check("T3 ...and an unrelated suite is NOT dragged in. A blast radius "
              "that includes everything tells the operator nothing",
              "test_unrelated.py" not in got, got)
        check("T4 only suites are reported, not the intermediate modules -- "
              "the operator is being told what will FAIL, not what imports",
              all(g.startswith(("test_", "probe_")) for g in got), got)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ---- T5: the real incident, against the real tree ----------------------
    real = p.suites_needing("xrpl-py", HERE)
    incident = {"test_k3_p9_owner_only_guard.py", "probe_final_pass.py",
                "test_xrp_signer.py", "test_xrp_mainnet.py"}
    on_disk = {s for s in incident if os.path.isfile(os.path.join(HERE, s))}
    check("T5 THE ACTUAL INCIDENT: every suite that failed on 2026-08-30 for "
          "want of xrpl-py is named by this check, so the same outage would "
          "now report its cause instead of four unrelated-looking symptoms",
          on_disk and on_disk.issubset(set(real)),
          sorted(on_disk - set(real)))

    # ---- V: version constraints -------------------------------------------
    check("V1 a version at the floor satisfies >=", p.satisfies("2.3", ">=2.3")[0])
    check("V2 a version BELOW the floor does not -- 'installed' and 'new "
          "enough' are different questions",
          not p.satisfies("2.2", ">=2.3")[0])
    check("V3 multi-part versions compare by number, not by string, so 4.10 "
          "is not treated as older than 4.9",
          p.satisfies("4.10.0", ">=4.9")[0])
    ok, note = p.satisfies("1.0", "~=1.0,!=1.1")
    check("V4 an unparseable constraint is ADMITTED, not guessed. A preflight "
          "that blocks a good run on a bad guess gets switched off, and then "
          "it catches nothing at all", ok and note, (ok, note))
    check("V5 no constraint is not a failure", p.satisfies("1.0", "")[0])

    # ---- R: it only reports ------------------------------------------------
    # BY AST, not by string search. The first version of R1 searched the source
    # text and failed on preflight_deps' own DOCSTRING, which contains the
    # words "no subprocess" and prints "pip install" as advice. A grep cannot
    # tell a promise not to do something from doing it; the parse tree can.
    src = open(os.path.join(HERE, "preflight_deps.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
    banned_imports = imported & {"subprocess", "urllib", "socket", "http",
                                 "ftplib", "shutil", "pip", "ctypes"}
    banned_calls = called & {"system", "Popen", "run", "check_call",
                             "check_output", "urlopen", "connect", "remove",
                             "unlink", "rmtree", "write"}
    check("R1 IT ONLY LOOKS, proven by AST rather than by grep: it imports no "
          "subprocess, no network and no filesystem-mutating module, and "
          "calls nothing that runs, fetches, deletes or writes. A preflight "
          "that quietly fixes things hides the drift it exists to expose",
          not banned_imports and not banned_calls,
          (sorted(banned_imports), sorted(banned_calls)))
    check("R2 it PRINTS the install command instead of running it, so the "
          "operator acts knowingly", "pip install" in src)
    check("R3 stdlib only -- it must run before anything is installed, on any "
          "platform, which is the one moment a dependency of its own would "
          "make it useless",
          "import requests" not in src and "import flask" not in src)

    # ---- F: fails safe -----------------------------------------------------
    check("F1 an ABSENT requirements.txt returns empty, never raises",
          p.declared(os.path.join(tempfile.gettempdir(), "nope_d1.txt")) == [])
    d = _tree({"requirements.txt": "\x00\xff not a requirement \x00\n"})
    try:
        p.declared(os.path.join(d, "requirements.txt"))
        check("F2 junk in requirements.txt does not raise -- the preflight "
              "must never be the thing that takes down the run it precedes",
              True)
    except Exception as e:                                   # noqa: BLE001
        check("F2 junk in requirements.txt does not raise", False, e)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    try:
        p.suites_needing("anything", os.path.join(tempfile.gettempdir(),
                                                  "no_such_dir_d1"))
        check("F3 an unreadable tree yields no casualties rather than an "
              "exception", True)
    except Exception as e:                                   # noqa: BLE001
        check("F3 an unreadable tree does not raise", False, e)
    check("F4 a distribution that is not installed reports None, not a crash",
          p.installed_version("definitely-not-installed-d1") is None)
    check("F5 ...and is reported as not importable rather than assumed absent "
          "for some other reason",
          p.importable("definitely-not-installed-d1") is False)

    n = len(results)
    ok = sum(results)
    print(f"\nD1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
