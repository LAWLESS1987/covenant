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
  - a fabricated/rewritten named commit, or a changed bound digest, is FAIL;
  - (S6-S8) a commitment older than a BOUND_FILES addition stays STALE, while a
    bound gitignored file is still checked on disk and its tamper FAILs.
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


def _older_commitment_newer_bound_file():
    """S6-S8 (2026-10-30). A file added to BOUND_FILES AFTER a commitment was made
    (the grid-guard config) is not tracked at the commit that commitment names. The
    verifier fell back to the ON-DISK copy and reported it "present at the named
    commit but not bound" -> BINDING UNDETERMINED, where origin/main read STALE on the
    same live ledger (head b4d9887). It must be skipped. The fallback stays for what
    it really serves: a bound file that is never tracked (ops/model_pin.json is
    gitignored and bound from disk) -- a tamper of it must still FAIL."""
    grid = ("ops/grid_signers.json", "ops/grid_interlocks.json", "ops/grid_policy.json")
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as keys:
        _git(repo, "init", "-q")
        _git(repo, "config", "commit.gpgsign", "false")
        os.makedirs(os.path.join(repo, "ops"))
        open(os.path.join(repo, "MANIFEST.sha256"), "w").write("aa  x.py\n")
        json.dump({"hash": "0000beef"}, open(os.path.join(repo, "genesis.json"), "w"))
        open(os.path.join(repo, ".gitignore"), "w").write("ops/model_pin.json\n")
        pin = os.path.join(repo, "ops", "model_pin.json")
        open(pin, "w").write('{"pin": "a"}\n')                 # gitignored, bound from disk
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "c1 (no grid files)")

        key, pub, led = (os.path.join(keys, "k.key"), os.path.join(keys, "pub.pem"),
                         os.path.join(keys, "hc.jsonl"))
        hc.make_commitment(repo=repo, key_path=key, pubkey_path=pub, ledger=led, now=1700000100)
        row = [json.loads(x) for x in open(led, encoding="utf-8") if x.strip()][-1]
        p_none = copy.deepcopy(row["payload"])                # grid files bound None
        p_absent = copy.deepcopy(row["payload"])              # older BOUND_FILES: keys absent
        for g in grid:
            p_absent["bound"].pop(g, None)

        # the grid files arrive LATER, committed and on disk
        for g in grid:
            open(os.path.join(repo, g), "w").write('{"later": true}\n')
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "c2 adds grid files")

        for label, p in (("bound None", p_none), ("keys absent, as on the live ledger", p_absent)):
            st, f = vhc.verify_binding(p, repo)
            check(f"HC2 an older commitment whose named commit lacks a bound file is STALE ({label})",
                  st == "STALE" and not any("not bound" in m for m in f), f"{st} {f}")

        # S7: a file the commitment DID bind from disk (gitignored) -- tamper still FAILs
        st, f = vhc.verify_binding(p_none, repo)
        check("HC2 the gitignored bound file is checked against disk (honest -> no finding)",
              not any("model_pin" in m for m in f), f"{st} {f}")
        open(pin, "w").write('{"pin": "TAMPERED"}\n')
        st, f = vhc.verify_binding(p_none, repo)
        check("HC2 a tamper of a bound, never-tracked file still FAILs",
              st == "FAIL" and any("ops/model_pin.json: digest mismatch" in m for m in f), f"{st} {f}")
        open(pin, "w").write('{"pin": "a"}\n')

        # S8: a grid file a commitment DID bind (digest) but that is absent at the named
        # commit is not skipped -- it is checked, and a mismatch FAILs
        p_claim = copy.deepcopy(p_none)
        p_claim["bound"]["ops/grid_policy.json"] = "ab" * 32
        st, f = vhc.verify_binding(p_claim, repo)
        check("HC2 a bound digest for a file absent at the named commit is not silently skipped",
              st == "FAIL" and any("ops/grid_policy.json" in m for m in f), f"{st} {f}")


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

    _older_commitment_newer_bound_file()

    passed, total = sum(_results), len(_results)
    print(f"\nHC2: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
