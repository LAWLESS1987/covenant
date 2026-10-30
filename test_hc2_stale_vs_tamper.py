#!/usr/bin/env python3
"""
test_hc2_stale_vs_tamper.py -- HC2. The head-commitment verifier must tell a
LEGITIMATELY ADVANCED tree (benign STALE) from a real TAMPER. This guard exists
because the first cut did not: it verified the newest commitment against the
CURRENT HEAD instead of the commit it NAMES, so any commit made after a commitment
read as a tamper (a false alarm that fired the moment ac35ad3 landed, 2026-10-29).

Driven in a throwaway GIT repo:
  - a commitment at the tip verifies PASS;
  - after another commit (HEAD advances) it verifies STALE, exit 0 -- NOT a tamper;
  - a fabricated/rewritten named commit, or a changed bound digest, is FAIL.
Rule 8: the red (STALE must not be FAIL) is the exact bug this guards.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_head_commit as hc        # noqa: E402
import verify_head_commitment as vhc     # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + detail) if detail and not cond else ''}")


def _git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, env=env)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        # a minimal git repo with two of the bound files present
        _git(tmp, "init", "-q")
        _git(tmp, "config", "commit.gpgsign", "false")
        open(os.path.join(tmp, "MANIFEST.sha256"), "w").write("aa  x.py\n")
        json.dump({"hash": "0000beef"}, open(os.path.join(tmp, "genesis.json"), "w"))
        _git(tmp, "add", "-A")
        _git(tmp, "commit", "-q", "-m", "c1")
        c1 = _git(tmp, "rev-parse", "HEAD").stdout.strip()

        key = os.path.join(tmp, ".k", "k.key")
        pub = os.path.join(tmp, "pub.pem")
        led = os.path.join(tmp, "hc.jsonl")
        hc.make_commitment(repo=tmp, key_path=key, pubkey_path=pub, ledger=led, now=1700000000)

        # S1: at the tip -> PASS (not stale)
        code, lines = vhc.run(led, pub, tmp)
        txt = " ".join(lines)
        check("HC2 a commitment at the tip verifies PASS", code == 0 and "STALE" not in txt, f"code={code} {txt[:160]}")

        # S2 (THE REGRESSION): advance HEAD, same commitment -> STALE, exit 0, NOT a tamper
        open(os.path.join(tmp, "note.txt"), "w").write("later work\n")
        _git(tmp, "add", "-A")
        _git(tmp, "commit", "-q", "-m", "c2")
        c2 = _git(tmp, "rev-parse", "HEAD").stdout.strip()
        code, lines = vhc.run(led, pub, tmp)
        txt = " ".join(lines)
        check("HC2 after HEAD advances, the SAME commitment is STALE not FAIL (exit 0)",
              code == 0 and "STALE" in txt and c2 != c1, f"code={code} {txt[:200]}")

        # S3: a fabricated named commit (history rewritten away) -> FAIL
        rows = [json.loads(x) for x in open(led, encoding="utf-8") if x.strip()]
        p = copy.deepcopy(rows[-1]["payload"])
        p["head"] = "0" * 40
        st, f = vhc.verify_binding(p, tmp)
        check("HC2 a named commit absent from history -> FAIL",
              st == "FAIL" and any("not in this history" in m for m in f), f"{st} {f}")

        # S4: a changed bound digest -> FAIL
        p2 = copy.deepcopy(rows[-1]["payload"])
        p2["bound"]["MANIFEST.sha256"] = "deadbeef" * 8
        st2, f2 = vhc.verify_binding(p2, tmp)
        check("HC2 a changed bound digest -> FAIL",
              st2 == "FAIL" and any("digest mismatch" in m for m in f2), f"{st2} {f2}")

        # S5: an honest STALE binding re-reads as STALE (idempotent, not drifting to FAIL)
        st3, _ = vhc.verify_binding(rows[-1]["payload"], tmp)
        check("HC2 the honest advanced-tree binding is STALE", st3 == "STALE", st3)

    passed, total = sum(_results), len(_results)
    print(f"\nHC2: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
