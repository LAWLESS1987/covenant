#!/usr/bin/env python3
"""test_m5_app.py -- M5: the Android app (mobile/app) ships the SAME core, by
staging it outside the checkout, and its manifest and workflow say what they
must.

Pure file, AST and text checks: no Gradle, no SDK, so it is green on the
ubuntu runner and on the Windows box. Runs IN PLACE because it reads mobile/app
and .github/workflows, which the sweep's scratch copy does not carry. Where git
is absent a check reports N/A with its reason rather than passing vacuously.
Exit 0 only when nothing failed. Tally: `M5: n/n passed`.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "mobile", "app")
LIST = os.path.join(APP, "python_sources.txt")
WF = os.path.join(HERE, ".github", "workflows", "android.yml")
MANIFEST = os.path.join(APP, "app", "src", "main", "AndroidManifest.xml")
ENTRY = os.path.join(APP, "app", "src", "main", "python", "entry.py")
LAUNCHER = "run_with_ollama_judge.py"
EXCLUDED = {"covenant_github_judge.py": "policy-only import, needs a token, drags covenant_quiet.py"}
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("ok    " if ok else "FAIL  ") + name + (("  -- " + str(detail)[:220]) if (detail and not ok) else ""))


def read(p):
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def allowlist():
    names = []
    for line in read(LIST).splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.append(line)
    return names


def git_tracked():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=HERE, capture_output=True, timeout=30).stdout
        return {n for n in out.decode("utf-8", "replace").split("\0") if n}
    except Exception:                                             # noqa: BLE001
        return None


def import_closure(start):
    """Root-level covenant_*.py modules reachable from START by import statements
    at any depth (inside functions and try/except too), names as files."""
    seen, todo = set(), [start]
    while todo:
        f = todo.pop()
        if f in seen or not os.path.isfile(os.path.join(HERE, f)):
            continue
        seen.add(f)
        try:
            tree = ast.parse(read(os.path.join(HERE, f)))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods = [node.module]
            for m in mods:
                top = m.split(".")[0]
                if top.startswith("covenant_") and os.path.isfile(os.path.join(HERE, top + ".py")):
                    todo.append(top + ".py")
    seen.discard(start)
    return seen


def main():
    names = allowlist()
    tracked = git_tracked()

    # M5.1 every listed name exists at the root and is tracked
    missing = [n for n in names if not os.path.isfile(os.path.join(HERE, n))]
    check("M5.1 every python_sources.txt name exists at the repo root", not missing, missing)
    if tracked is None:
        print("n/a   M5.1b git not available here -- tracked-ness not measured, not claimed")
    else:
        untracked = [n for n in names if n not in tracked]
        check("M5.1b ...and every one is git-tracked (a gitignored policy file can never be listed)", not untracked, untracked)

    # M5.2 the launcher's import closure == the .py names listed, minus the documented exclusion
    closure = import_closure(LAUNCHER)
    listed_py = {n for n in names if n.endswith(".py") and n != LAUNCHER}
    expected = {f for f in closure if f not in EXCLUDED}
    check("M5.2 the launcher's transitive import closure (AST) equals the listed .py names minus the documented exclusion",
          listed_py == expected, "listed-not-needed=%s needed-not-listed=%s" % (sorted(listed_py - expected), sorted(expected - listed_py)))

    # M5.3 the data files the shipped modules open beside themselves are listed
    for d in ("genesis.json", "semantic_judge_model.json", "fallback_model.json", "fallback_model_2.json", "judges.json"):
        check("M5.3 data file listed: %s" % d, d in names)

    # M5.4 nothing under mobile/app at ANY depth is a copy of the core or a secret
    bad = []
    for root, dirs, files in os.walk(APP):
        dirs[:] = [d for d in dirs if d not in ("build", ".gradle", ".kotlin", ".idea")]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), APP).replace("\\", "/")
            if re.match(r"covenant_.*\.py$", f) or f.endswith((".db", ".key", ".apk", ".aab")) or (
                    f.endswith((".jks", ".keystore", ".p12")) and rel != "signing/debug.p12"):
                bad.append(rel)
    check("M5.4 no copy of the core, no db/key/apk, and no keystore but signing/debug.p12 under mobile/app at any depth", not bad, bad)

    # M5.5 exactly one Python source file is packaged from src/main/python
    pydir = os.path.join(APP, "app", "src", "main", "python")
    pyfiles = sorted(os.listdir(pydir)) if os.path.isdir(pydir) else []
    check("M5.5 src/main/python contains exactly entry.py", pyfiles == ["entry.py"], pyfiles)

    # M5.6 entry.py sets no provider variables and only known flags
    src = read(ENTRY)
    tree = ast.parse(src)
    forbidden = ("COVENANT_JUDGE_PROVIDERS", "COVENANT_JUDGE_PROVIDERS_OVERRIDE", "COVENANT_LOCAL_JUDGE")
    assigns = []
    for node in ast.walk(tree):
        # os.environ["X"] = ...
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
                    if any(t.slice.value.startswith(k) for k in forbidden):
                        assigns.append(t.slice.value)
        # os.environ.setdefault("X", ...) / os.putenv("X", ...)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("setdefault", "putenv"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                if any(node.args[0].value.startswith(k) for k in forbidden):
                    assigns.append(node.args[0].value)
    check("M5.6 entry.py never assigns a judge-provider or local-judge variable", not assigns, assigns)
    check("M5.6b entry.py sets COVENANT_FORCE_NO_SANDBOX (no fork sandbox inside ART)", 'os.environ["COVENANT_FORCE_NO_SANDBOX"] = "1"' in src)
    flags = set(re.findall(r'"(--[a-z][a-z-]*)"', src))
    check("M5.6c every flag entry.py builds is one the node's --help knows (the set M3.2 proves)",
          flags <= {"--real", "--port", "--node-id", "--genesis", "--peers"}, sorted(flags))

    # M5.7 the manifest
    m = read(MANIFEST)
    check("M5.7 service is foregroundServiceType=specialUse with the mandatory subtype property",
          'android:foregroundServiceType="specialUse"' in m and "PROPERTY_SPECIAL_USE_FGS_SUBTYPE" in m)
    check("M5.7b service runs in its own process and is not exported", 'android:process=":node"' in m and re.search(r'<service[^>]*android:exported="false"', m, re.S))
    check("M5.7c allowBackup=false (the node's identity never rides auto-backup)", 'android:allowBackup="false"' in m)
    perms = set(re.findall(r'uses-permission android:name="android\.permission\.([A-Z_]+)"', m))
    allowed = {"INTERNET", "ACCESS_NETWORK_STATE", "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_SPECIAL_USE",
               "POST_NOTIFICATIONS", "WAKE_LOCK", "RECEIVE_BOOT_COMPLETED", "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS"}
    check("M5.7d no permission outside the eight the design verified", perms <= allowed, sorted(perms - allowed))
    check("M5.7e share-in: the Activity accepts ACTION_SEND text/plain", 'android.intent.action.SEND' in m and 'android:mimeType="text/plain"' in m)

    # M5.8 the nested .gitignore keeps outputs and keys out (git's own answer when available)
    gi = read(os.path.join(APP, ".gitignore"))
    for pat in ("build/", ".gradle/", "local.properties", "*.apk", "*.jks", "*.keystore", "*.p12", "keystore.properties"):
        check("M5.8 mobile/app/.gitignore lists %s" % pat, pat in gi.split())
    check("M5.8b ...and un-ignores signing/debug.p12", "!signing/debug.p12" in gi.split())
    if tracked is not None:
        p = subprocess.run(["git", "check-ignore", "-q", "mobile/app/app/build/x.apk"], cwd=HERE, capture_output=True)
        check("M5.8c git itself ignores a build output under mobile/app", p.returncode == 0)
        p = subprocess.run(["git", "check-ignore", "-q", "mobile/app/signing/debug.p12"], cwd=HERE, capture_output=True)
        check("M5.8d git itself does NOT ignore signing/debug.p12", p.returncode == 1)

    # M5.9 the workflow's posture
    y = read(WF)
    top = y.split("\njobs:", 1)[0]
    check("M5.9 top-level permissions are exactly contents: read", re.search(r"^permissions:\n  contents: read\n", top, re.M) is not None)
    jobs = y.split("\njobs:", 1)[1] if "\njobs:" in y else ""
    # split into job blocks at two-space-indented keys, then read each block's OWN
    # permissions -- a single regex ran across job boundaries and blamed 'build'
    blocks = re.split(r"\n(?=  \w+:\n)", "\n" + jobs)
    writes = []
    for blk in blocks:
        head = re.match(r"\n?  (\w+):\n", blk)
        if head and re.search(r"\n    permissions:\n      contents: write", blk):
            writes.append(head.group(1))
    check("M5.9b only the job named release holds contents: write", writes == ["release"], writes)
    secrets = set(re.findall(r"secrets\.([A-Za-z_]+)", y))
    check("M5.9c the only secret referenced is GITHUB_TOKEN", secrets == {"GITHUB_TOKEN"}, sorted(secrets))
    check("M5.9d concurrency group starts with android- (never the sweep's group)", re.search(r"group: android-", y) is not None)
    check("M5.9e the workflow runs no sweep and installs no requirements.txt", "covenant_one.py" not in y and "pip install -r requirements.txt" not in y)
    uses = re.findall(r"uses: ([^\s]+)", y)
    check("M5.9f every action is pinned to a major tag", all(re.search(r"@v\d+$", u) for u in uses), [u for u in uses if not re.search(r"@v\d+$", u)])

    # M5.10 the scripts parse, and say what they must
    sh = __import__("shutil").which("sh")
    # A92's E6 scans every .py in the tree for this flag as a literal -- so this
    # suite must not spell it either, or it fails the very check it enforces.
    push_flag = "--" + "push"
    for s in ("stage.sh", "build.sh", "ci_check.sh"):
        p = os.path.join(APP, s)
        if sh:
            r = subprocess.run([sh, "-n", p], capture_output=True, text=True)
            check("M5.10 %s parses (sh -n)" % s, r.returncode == 0, r.stderr)
        else:
            print("n/a   M5.10 %s: no sh on this machine" % s)
        check("M5.10b %s contains no literal %s (A92 E6)" % (s, push_flag), push_flag not in read(p))
    check("M5.10c ci_check.sh asserts the canonical genesis", "00009b31c6c654d79bbeae0bcc9c82a7af224c87b19c92973f0011ade3e032f3" in read(os.path.join(APP, "ci_check.sh")))
    check("M5.10d stage.sh refuses a destination inside the checkout", "inside the checkout" in read(os.path.join(APP, "stage.sh")))

    # M5.11 the workflow's paths filter names every allowlisted file
    paths = set(re.findall(r'^\s+- "([^"]+)"', y.split("workflow_dispatch", 1)[0], re.M))
    absent = [n for n in names if n not in paths]
    check("M5.11 every python_sources.txt name is in android.yml's push.paths (a core change rebuilds the APK)", not absent, absent)

    # M5.12 the Android pip set
    req = read(os.path.join(APP, "app", "requirements-android.txt"))
    live = [l.split("#", 1)[0] for l in req.splitlines()]
    check("M5.12 requirements-android.txt pins cryptography below 43 and lists no xrpl-py (live lines; a comment may say it is absent)",
          any("cryptography>=41.0,<43" in l for l in live) and not any("xrpl" in l for l in live))

    n, good = len(results), sum(results)
    print("\nM5: %d/%d passed" % (good, n))
    return 0 if good == n else 1


if __name__ == "__main__":
    sys.exit(main())
