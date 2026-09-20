#!/usr/bin/env python3
"""test_a153_import_drift.py -- the import-set fingerprint sees what "disk
source" cannot (A153, 2026-09-19).

WHAT WAS MEASURED. All three PC nodes ran a 240-character cap on the phone's
`update` field for three hours after the file on disk said 600, because the
node imports covenant_daily_plan once at start, and rolling_restart --status
called every node "on the disk source": its fingerprint is of
covenant_unified_v8.py alone. That fingerprint keeps its meaning (the phone
ships a subset of the tree; a wider hash there would fake a mesh split). This
is a SECOND one, additive, over the modules the node file and launcher name.

WHAT THIS RUNS (no node, no network): the discovery and the hash over a temp
tree, both ways, and the restart tool's verdict line over fixture health.

WHAT IT DOES NOT MEASURE: that a live node's /health carries the field (that
needs a started node -- test_c2_watchdog_live's territory), and modules the
named modules import in turn (one level deep, by design and by docstring).
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_watchdog as W  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%-5s %s%s" % ("ok" if ok else "FAIL", name, ("  -- %s" % (detail,)) if (detail and not ok) else ""))


def tree(td, node_text, launcher_text="", modules=None):
    with open(os.path.join(td, "covenant_unified_v8.py"), "w", encoding="utf-8") as fh:
        fh.write(node_text)
    with open(os.path.join(td, "run_node.py"), "w", encoding="utf-8") as fh:
        fh.write(launcher_text)
    for n, body in (modules or {}).items():
        with open(os.path.join(td, n + ".py"), "w", encoding="utf-8") as fh:
            fh.write(body)


def main():
    with tempfile.TemporaryDirectory() as td:
        node = ('import os\nimport covenant_daily_plan\nfrom covenant_judge_defer import X\n'
                'def f():\n    m = importlib.import_module("covenant_app_update")\n')
        launcher = 'import covenant_invite\n'
        mods = {"covenant_daily_plan": "A = 240\n", "covenant_judge_defer": "B = 1\n",
                "covenant_app_update": "C = 1\n", "covenant_invite": "D = 1\n", "covenant_unrelated": "E = 1\n"}
        tree(td, node, launcher, mods)
        names = W.runtime_import_set(td)
        check("A153.1 discovery finds `import x`, `from x import`, and import_module(\"x\") in the node file, and the launcher's import",
              names == ["covenant_app_update", "covenant_daily_plan", "covenant_invite", "covenant_judge_defer"], names)
        check("A153.1b ...and never the node file itself or a module nobody names",
              "covenant_unified_v8" not in names and "covenant_unrelated" not in names, names)
        h0 = W.disk_imports_sha12(td)
        check("A153.2 the fingerprint is 12 hex over the named modules", isinstance(h0, str) and len(h0) == 12 and all(c in "0123456789abcdef" for c in h0), h0)

        # BOTH WAYS. The measured case: a named module's bytes change (240 -> 600).
        with open(os.path.join(td, "covenant_daily_plan.py"), "w", encoding="utf-8") as fh:
            fh.write("A = 600\n")
        h1 = W.disk_imports_sha12(td)
        check("A153.3 a change to a NAMED module changes the fingerprint (the 240 -> 600 case)", h1 != h0, (h0, h1))
        # ...and a module nobody names does not move it: the population is the named set.
        with open(os.path.join(td, "covenant_unrelated.py"), "w", encoding="utf-8") as fh:
            fh.write("E = 2\n")
        check("A153.3b a change to an UNNAMED module leaves it alone", W.disk_imports_sha12(td) == h1)
        # ...and the node file itself is not in this hash (that is disk_source_sha12's job).
        with open(os.path.join(td, "covenant_unified_v8.py"), "a", encoding="utf-8") as fh:
            fh.write("# comment only\n")
        check("A153.3c the node file's own bytes are not in this fingerprint (additive, not a replacement)", W.disk_imports_sha12(td) == h1)
        # ...but a NEW import line in the node file widens the population.
        with open(os.path.join(td, "covenant_unified_v8.py"), "a", encoding="utf-8") as fh:
            fh.write("import covenant_unrelated\n")
        check("A153.3d a new `import covenant_x` in the node file adds x to the population", W.disk_imports_sha12(td) != h1
              and "covenant_unrelated" in W.runtime_import_set(td))
        check("A153.4 an empty tree answers None, never a hash of nothing", W.disk_imports_sha12(os.path.join(td, "nope")) is None)

    # THE VERDICT LINE, both ways.
    src, imp = "abc123abc123", "def456def456"
    check("A153.5 source stale is still reported first, in the words rolling_restart always used",
          W.source_verdict({"source_sha256": "zzz"}, src, imp).startswith("STALE -- restart would pick up"))
    check("A153.5b source current and imports current",
          W.source_verdict({"source_sha256": src, "imports_sha12": imp}, src, imp) == "on the disk source, imports current")
    v = W.source_verdict({"source_sha256": src, "imports_sha12": "000000000000"}, src, imp)
    check("A153.5c source current, imports STALE: says so and names A153", "IMPORTS STALE" in v and "A153" in v, v)
    v2 = W.source_verdict({"source_sha256": src}, src, imp)
    check("A153.5d a node that reports NO imports field (a build before this one) is IMPORTS STALE, not silently current", "IMPORTS STALE" in v2, v2)
    check("A153.5e when the disk has no import set to compare (None), the old verdict stands unchanged",
          W.source_verdict({"source_sha256": src}, src, None) == "on the disk source")

    # LIVE, if a tree is here: the real node file names at least the module that bit.
    names = W.runtime_import_set()
    check("A153.6 the real tree's named set includes covenant_daily_plan (the module that bit on 2026-09-19)", "covenant_daily_plan" in names, names)

    n, good = len(results), sum(results)
    print("\nA153: %d/%d passed" % (good, n))
    return 0 if good == n else 1


if __name__ == "__main__":
    sys.exit(main())
