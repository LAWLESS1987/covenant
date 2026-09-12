#!/usr/bin/env python3
"""test_m3_mobile.py -- the phone node's scripts and setup page stay true to the node.

mobile/ carries a Termux start script, a health script, a widget entry and a setup page
that promise flags, environment variables and files. None of that is a mobile fork: the
scripts call run_node.py with flags it has and export variables the judge
reads. This suite makes the promise checkable on every sweep: the scripts parse, every
flag the start script passes exists in the node's --help, every COVENANT_* variable the
scripts export is read somewhere in the judge or core, the setup page names the same
variables and defaults as the script, and -- since 2026-09-12, "no Ollama anywhere" --
no live line of any script names a model server. What it cannot do: run the node on a phone. It
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
    for s in scripts + ["mobile/TERMUX_SETUP.md", "mobile/USB.md"]:
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
    p = subprocess.run([sys.executable, os.path.join(HERE, "run_node.py"), "--help"],
                       capture_output=True, text=True, timeout=120)
    helptext = (p.stdout or "") + (p.stderr or "")
    for flag in re.findall(r"(--[a-z][a-z-]+)", start.split("exec python run_node.py", 1)[-1]):
        check("M3.2 node --help knows %s" % flag, flag in helptext, helptext[-200:])

    # every COVENANT_* variable the scripts export is read by something the phone
    # actually runs.
    #
    # A93 (2026-09-12): this read covenant_judge_ollama.py and covenant_unified_v8.py
    # only, and reported COVENANT_JUDGE_PROVIDERS_OVERRIDE as unread -- while the one
    # file that reads it is the launcher (run_node.py), the program the start script
    # execs on the last line. The check was not wrong about its two files; its
    # population was missing the launcher. Counting what a check reads before
    # believing what it says is the standing lesson here.
    READS = ["run_node.py", "covenant_judge_ollama.py", "covenant_unified_v8.py"]
    code = "".join(read(f) for f in READS)
    for var in sorted(set(re.findall(r"export (COVENANT_[A-Z_]+)", start))):
        check("M3.3 %s is read by one of the %d files the phone runs"
              % (var, len(READS)), var in code)

    # the setup page and the script agree on the knobs and their defaults
    doc = read("mobile/TERMUX_SETUP.md")
    for var, default in re.findall(r'^([A-Z_]+)="\$\{[A-Z_]+:-([^}]+)\}"', start, re.M):
        if var == "OLLAMA_URL":
            continue
        check("M3.4 setup page documents %s with default %s" % (var, default),
              ("`%s`" % var) in doc and ("`%s`" % default) in doc)


    # NO OLLAMA ANYWHERE (2026-09-12). Until today this checked that the page named
    # three qwen3 tiers. Now it checks the opposite, and on the scripts' LIVE lines
    # rather than their prose: a comment may say "Ollama was deleted"; a line that
    # runs may not start it, pull it, probe it or export a knob for it.
    live_bad = []
    for sname in scripts:
        for n, line in enumerate(read(sname).split("\n"), 1):
            code = line.split("#", 1)[0]
            if re.search(r"(?i)ollama|qwen|11434|JUDGE_MODEL", code):
                live_bad.append("%s:%d" % (sname, n))
    check("M3.6 no live line of any phone script names a model server (ollama/qwen/11434/JUDGE_MODEL)",
          not live_bad, ", ".join(live_bad))
    check("M3.6b the setup page's variable table has no JUDGE_MODEL row", "| `JUDGE_MODEL`" not in doc)
    check("M3.6c the setup page states the judge is the same as the PC's and names the exam record",
          "The judge, stated plainly" in doc and "ops/DISTILL.md" in doc)
    check("M3.7 setup page says the gate fails CLOSED", "fails CLOSED" in doc or "fail CLOSED" in doc)
    check("M3.8 setup page says what iOS cannot do", "iPhone" in doc and "cannot" in doc)

    passed, total = sum(results), len(results)
    print("\nM3: %d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
