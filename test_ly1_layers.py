#!/usr/bin/env python3
"""LY1 -- the layers are declared by rule, every file lands in exactly one, and the map
refuses nothing (2026-09-25; his words: "Separate the governing rules, verification
harness, and experimental logs into clear layers so others can reproduce results without
the author's interpretation" and "finish this without adding any new restrictions").

Runs where the sweep runs it: the staged copy has no .git, so tools/layers.py walks the
disk there, and these checks are invariants, never counts.

  LY1a  every file gets exactly one of the seven layers
  LY1b  what the rules say lands where it must: the constitution's protected files and his
        grants in rules; the Sentinel Witness record checkers in verifier; every test_ in
        harness; the core file in core
  LY1c  a grant is found by CONTENT: a json with "granted" and "words" under ops/ is rules,
        the same file without them is not (both ways, in a temp tree)
  LY1d  the map refuses nothing: --imports reports core -> system imports and exits 0
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
sys.path.insert(0, HERE)
import layers as L  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  -- %s" % (str(detail)[:300],)) if detail and not ok else ""))


def main():
    m = L.build(HERE)
    check("LY1a every file gets exactly one of the seven layers",
          m and all(v in L.LAYERS for v in m.values()), sorted({v for v in m.values() if v not in L.LAYERS}))
    prot = L.protected_files(HERE)
    present = [f for f in prot if f in m]
    check("LY1b the constitution's protected files present here are in rules",
          present and all(m[f] == "rules" for f in present), {f: m.get(f) for f in prot})
    grants = [f for f in m if f.startswith("ops/") and f.endswith("_grant.json")]
    check("LY1b his grant files present here are in rules", all(m[f] == "rules" for f in grants), {f: m[f] for f in grants})
    sw = [f for f in ("sentinel_witness/verify_record.py", "sentinel_witness/order_claims.py") if f in m]
    check("LY1b the Sentinel Witness record checkers are the verifier",
          sw and all(m[f] == "verifier" for f in sw), {f: m.get(f) for f in sw})
    tests = [f for f in m if os.path.basename(f).startswith("test_") and f.endswith(".py")]
    check("LY1b every test_ file is harness", tests and all(m[f] == "harness" for f in tests),
          [f for f in tests if m[f] != "harness"][:5])
    check("LY1b the node's core file is core", m.get("covenant_unified_v8.py") == "core", m.get("covenant_unified_v8.py"))

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "ops"))
        with open(os.path.join(td, "ops", "some_new.json"), "w", encoding="utf-8") as fh:
            json.dump({"granted": True, "words": "his words", "by": "him"}, fh)
        with open(os.path.join(td, "ops", "some_state.json"), "w", encoding="utf-8") as fh:
            json.dump({"at": 1, "count": 3}, fh)
        a = L.layer_of("ops/some_new.json", td, set())
        b = L.layer_of("ops/some_state.json", td, set())
        check("LY1c a grant is found by its content (granted + words), and a state file is not",
              a == "rules" and b != "rules", (a, b))

    rc = L.main(["--imports"])
    check("LY1d the map refuses nothing: --imports reports and exits 0", rc == 0, rc)

    n, ok = len(results), sum(results)
    print("\nLY1: %d/%d passed" % (ok, n))
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
