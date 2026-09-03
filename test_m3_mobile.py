#!/usr/bin/env python3
"""test_m3_mobile.py -- the phone node's scripts and setup page stay true to the node.

mobile/ carries a Termux start script, a health script, a widget entry and a setup page
that promise flags, environment variables and files. None of that is a mobile fork: the
scripts call run_with_ollama_judge.py with flags it has and export variables the judge
reads. This suite makes the promise checkable on every sweep: the scripts parse, every
flag the start script passes exists in the node's --help, every COVENANT_* variable the
scripts export is read somewhere in the judge or core, the setup page names the same
variables and defaults as the script, and the example judges file is valid JSON of the
shape the named-judge loader documents. What it cannot do: run the node on a phone. It
says so. Runs IN PLACE (it reads mobile/ and the node's --help). Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOB = os.path.join(HERE, "mobile")
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, ("  -- " + detail[-200:]) if (detail and not ok) else ""))


def read(rel):
    return io.open(os.path.join(HERE, rel), encoding="utf-8", errors="replace").read()


def main():
    scripts = ["mobile/install.sh", "mobile/covenant_phone.sh", "mobile/covenant_phone_check.sh", "mobile/widget/covenant-phone-start.sh"]
    for s in scripts + ["mobile/TERMUX_SETUP.md", "mobile/judges.example.json"]:
        check("M3.0 %s is in the tree" % s, os.path.exists(os.path.join(HERE, s)))

    sh = shutil.which("sh")
    for s in scripts:
        if sh:
            p = subprocess.run([sh, "-n", os.path.join(HERE, s)], capture_output=True, text=True)
            check("M3.1 %s parses (sh -n)" % s, p.returncode == 0, p.stderr)
        else:
            print("skip  M3.1 %s: no sh on this machine -- unchecked here, not claimed" % s)

    start = read("mobile/covenant_phone.sh")
    # flags the start script passes must exist in the node's --help
    p = subprocess.run([sys.executable, os.path.join(HERE, "run_with_ollama_judge.py"), "--help"],
                       capture_output=True, text=True, timeout=120)
    helptext = (p.stdout or "") + (p.stderr or "")
    for flag in re.findall(r"(--[a-z][a-z-]+)", start.split("exec python run_with_ollama_judge.py", 1)[-1]):
        check("M3.2 node --help knows %s" % flag, flag in helptext, helptext[-200:])

    # every COVENANT_* variable the scripts export is read by the judge or the core
    code = read("covenant_judge_ollama.py") + read("covenant_unified_v8.py")
    for var in sorted(set(re.findall(r"export (COVENANT_[A-Z_]+)", start))):
        check("M3.3 %s is read by the judge or core" % var, var in code)

    # the setup page and the script agree on the knobs and their defaults
    doc = read("mobile/TERMUX_SETUP.md")
    for var, default in re.findall(r'^([A-Z_]+)="\$\{[A-Z_]+:-([^}]+)\}"', start, re.M):
        if var == "OLLAMA_URL":
            continue
        check("M3.4 setup page documents %s with default %s" % (var, default),
              ("`%s`" % var) in doc and ("`%s`" % default) in doc)

    # the example judges file has the documented shape
    try:
        j = json.load(io.open(os.path.join(MOB, "judges.example.json"), encoding="utf-8"))
        ok = isinstance(j, dict) and all(isinstance(v, dict) and "url" in v and "model" in v for v in j.values()) and "phone" in j
    except Exception as e:                                       # noqa: BLE001
        ok, j = False, str(e)
    check("M3.5 judges.example.json is {name: {url, model}} and names the phone", ok, str(j)[:200])

    # the tier table is honest: the reference judge and the phone tiers are named
    for m in ("qwen3:8b", "qwen3:4b", "qwen3:1.7b"):
        check("M3.6 setup page names the %s tier" % m, m in doc)
    check("M3.7 setup page says the gate fails CLOSED", "fails CLOSED" in doc or "fail CLOSED" in doc)
    check("M3.8 setup page says what iOS cannot do", "iPhone" in doc and "cannot" in doc)

    passed, total = sum(results), len(results)
    print("\nM3: %d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
