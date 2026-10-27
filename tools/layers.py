#!/usr/bin/env python3
"""tools/layers.py -- every tracked file in exactly one layer, by rule, with nothing moved.

HIS WORDS, 2026-09-19: "separate the Covenant core, the Sentinel Witness verifier, and the
experimental record into cleaner layers" and "Prioritize testability over persuasion.
Separate the governing rules, verification harness, and experimental logs into clear
layers so others can reproduce results without the author's interpretation". And
2026-09-25: "finish this without adding any new restrictions".

WHY NOTHING MOVES (measured 2026-09-25 by five readers; docs/LAYERS.md carries the
counts). The phone build refuses a subpath; the pre-commit hook, the watchdog and the
sweep name root paths; 139 suites import the core flat; and two moves would be NEW
RESTRICTIONS in effect -- a grant file read at a fixed path means refusal when it is
missing, and the issue register moved away means the students silently learn nothing
from our own work. So the layers are declared, and each file's layer is decided here.

THE LAYERS, first rule that matches wins:
  rules         what the system is bound by: the constitution's protected files, the
                licences, genesis, the conformance spec, and his grants and policies
  verifier      what checks a record or the rules from outside: the constitution
                verifiers and anchor, the Sentinel Witness record checkers, the bundle
                manifest and seals, the retraction ledger, the conformance tools
  harness       what runs the checks: every test_/sim_/probe_ file, the sweep runner,
                launch_check, CI workflows
  core          the node: the chain, the gate, the judge seats and their models
  system        everything else that runs: the apps, Tetsu, money, the watchdog and
                self-repair, the learning pipeline, operator tools and scripts
  record-data   what the running system measured: ledgers, run transcripts, price
                series, reports
  record-prose  what we wrote about it: write-ups, findings, the issue register

It REPORTS; it refuses nothing. `--imports` lists core modules that import from the
system layer (a leak worth knowing, not a failure).

    python tools/layers.py            counts per layer
    python tools/layers.py --list L   the files in layer L
    python tools/layers.py --json     the whole map
    python tools/layers.py --imports  core -> system imports, reported
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = ("rules", "verifier", "harness", "core", "system", "record-data", "record-prose")

RULE_FILES = {"LICENSE", "NOTICE", "LICENSE-TETSU.md", "genesis.json", "docs/SEMANTICS.md",
              "docs/CONFORMANCE_SPEC.json", "spec_reference.py", "ops/quorum_policy.example.json"}
VERIFIER_FILES = {"constitution.py", "verify.sh", "verify.ps1", "check.sh", "check.ps1", "federation.py", "mfn.py",
                  "docs/CONSTITUTION_ANCHOR.json", "docs/RETRACTED.json", "MANIFEST.sha256", "SEAL_ANCHOR.json",
                  "SEAL_ROOT.txt", "ops/RECORD_ANCHORS.json", "ops/known_artifacts.json", "ops/G3_BASELINE.json",
                  "verify_bundle.py", "verify_deploy.py", "verify_csv.py", "exposure_check.py", "covenant_seal.py",
                  "covenant_anchor.py", "covenant_sentinels.py", "covenant_selfaudit.py",
                  "sentinel_witness/verify_record.py", "sentinel_witness/order_claims.py",
                  "tools/spec_conformance.py", "tools/sentinel_baseline.py", "tools/layers.py"}
VERIFIER_GLOBS = ("conformance*.py", "conformance_indep/*")
HARNESS_FILES = {"covenant_one.py", "run_local_sweep.py", "launch_check.py", "preflight.py", "preflight_deps.py",
                 "run_all_tests.sh", "readme_totals.py", ".github/workflows/covenant.yml"}
HARNESS_BASENAME = ("test_*.py", "sim_*.py", "probe_*.py")
CORE_FILES = {"run_node.py", "covenant_unified_v8.py", "covenant_path_pattern.py", "covenant_semantic_judge.py",
              "judge_resolve.py", "semantic_judge_model.json", "fallback_core.json"}
CORE_GLOBS = ("covenant_judge_*.py", "fallback_model*.json", "pending-v8.38/*")
DATA_EXT = (".jsonl", ".csv", ".txt", ".log", ".tsv")
DATA_DIRS = ("ops/", "realdata/", "quant/", "docs/results/", "docs/semantic/")


def tracked(root=HERE):
    """Tracked files by git; on a copy with no .git (the staged sweep), every file on disk."""
    try:
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            return sorted(l for l in out.stdout.splitlines() if l)
    except (OSError, subprocess.SubprocessError):
        pass
    files = []
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in (".git", ".venv", "__pycache__", "node_modules")]
        for f in fs:
            files.append(os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"))
    return sorted(files)


def protected_files(root=HERE):
    """The files the constitution hashes, read from constitution.PROTECTED, never a copy of it."""
    try:
        sys.path.insert(0, root)
        import constitution
        return {str(p["file"] if isinstance(p, dict) else p[0]).replace("\\", "/") for p in constitution.PROTECTED}
    except Exception:                                             # noqa: BLE001
        return set()


def _is_grant(path, root):
    if not (path.startswith("ops/") and path.endswith(".json")):
        return False
    if "policy" in os.path.basename(path) or os.path.basename(path).endswith("_grant.json"):
        return True
    try:
        with open(os.path.join(root, path), encoding="utf-8") as fh:
            d = json.load(fh)
        return isinstance(d, dict) and "granted" in d and "words" in d
    except (OSError, ValueError):
        return False


def layer_of(path, root=HERE, protected=None):
    base = os.path.basename(path)
    protected = protected_files(root) if protected is None else protected
    if path in protected or path in RULE_FILES or _is_grant(path, root):
        return "rules"
    if path in VERIFIER_FILES or any(fnmatch.fnmatch(path, g) for g in VERIFIER_GLOBS):
        return "verifier"
    if path in HARNESS_FILES or any(fnmatch.fnmatch(base, g) for g in HARNESS_BASENAME):
        return "harness"
    if path in CORE_FILES or any(fnmatch.fnmatch(path, g) for g in CORE_GLOBS):
        return "core"
    if path.endswith(DATA_EXT) or (path.startswith(DATA_DIRS) and not path.endswith((".py", ".bat", ".ps1", ".sh"))):
        return "record-data" if not (path.endswith(".md") and not path.startswith("ops/")) else "record-prose"
    if path.endswith(".md"):
        return "record-prose"
    return "system"


def build(root=HERE):
    prot = protected_files(root)
    m = {}
    for f in tracked(root):
        m[f] = layer_of(f, root, prot)
    return m


def core_imports_from_system(m, root=HERE):
    """(core file, module) where a core file imports a module the map puts in the system layer."""
    mods = {os.path.splitext(f)[0]: lay for f, lay in m.items() if f.endswith(".py") and "/" not in f}
    out = []
    for f, lay in m.items():
        if lay != "core" or not f.endswith(".py") or "/" in f:
            continue
        try:
            text = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        names = set(re.findall(r'^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)', text, re.M))
        names |= set(re.findall(r'import_module\("([A-Za-z_][A-Za-z0-9_]*)"\)', text))
        out += [(f, n) for n in sorted(names) if mods.get(n) == "system"]
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="every tracked file in exactly one layer, by rule")
    ap.add_argument("--list", metavar="LAYER", choices=LAYERS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--imports", action="store_true")
    a = ap.parse_args(argv)
    m = build()
    if a.json:
        print(json.dumps(m, indent=1, sort_keys=True))
        return 0
    if a.list:
        print("\n".join(f for f, lay in sorted(m.items()) if lay == a.list))
        return 0
    if a.imports:
        rows = core_imports_from_system(m)
        for f, n in rows:
            print("core %-28s imports system module %s" % (f, n))
        print("%d core -> system import(s), reported, not refused" % len(rows))
        return 0
    counts = {lay: sum(1 for v in m.values() if v == lay) for lay in LAYERS}
    print("%d files, each in exactly one layer:" % len(m))
    for lay in LAYERS:
        print("  %-13s %4d" % (lay, counts[lay]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
