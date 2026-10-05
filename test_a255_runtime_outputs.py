#!/usr/bin/env python3
"""test_a255_runtime_outputs.py -- A255: a ledger the system writes must not
be hashed as delivery.

WHY THIS EXISTS. verify_bundle.py's OUTPUTS list says it plainly: a manifest
must contain only inputs, and "adding a launcher that writes a report here
means adding its report to this list, always." That is a step a person has to
remember, and it was forgotten at least three times:

  A56     2026-09-06  the second student's outputs were not in OUTPUTS
  de33671 2026-09-28  nightly outputs committed by hand "so the manifest
                      repair can run"
  A255    2026-10-04  five tracked ledgers (ambassador_allies, moltbook_
                      candidates, outbound_overrides, tetsu_assist,
                      oa_sources) and RUN_WITHOUT.json, all written by
                      running processes, none in OUTPUTS

Each time G1 read BLOCKED, the highway's rehash_bundle refused (correctly --
the tree was dirty), and the sweep read RESULT: FAIL on zero failed checks.
Each fix added names and left nothing behind to catch the next one. This is
the thing left behind (CLAUDE.md rule 10: a forgotten step's tombstone is a
guard at the place it is forgotten).

WHAT IT PINS.

  P*  the population is real: git is reachable from this folder and tracks at
      least one .jsonl. With no git this suite says NOT RUN and exits 2 -- a
      population it cannot read is not a pass.
  C*  every tracked .jsonl the manifest would otherwise hash is classified:
      in OUTPUTS (written by the system, never hashed) or in INPUT_LEDGERS
      (hashed on purpose, with the reason).
  I*  every INPUT_LEDGERS entry names a tracked file and gives a reason, so
      the escape cannot rot into a list of names nobody can account for.
  E*  the consequence, measured the other way: verify_bundle.py run here
      reports no CHANGED/MISSING line for any .jsonl. C* reads the lists; E*
      reads what the gate actually does with them, so the two can disagree.
  M*  the checker is not vacuous: with one real ledger removed from OUTPUTS
      it flags that ledger, and it flags a planted unclassified one.

WHAT IT CANNOT SEE, said so it is not quoted as more. Only .jsonl is
classified, because every tracked .jsonl here was measured to be a ledger the
system appends. A generated report in another format -- RUN_WITHOUT.json was
one -- is invisible to C*, and still needs its name added to OUTPUTS by hand.
A .json policy and a .json report look the same to a filename; this does not
guess between them.

Run IN PLACE (covenant_one IN_PLACE): it is a claim about what git ships from
THIS folder, and the scratch copy has no .git.
Reads git and files; runs verify_bundle.py read-only (no --write). Changes
nothing.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:300]), flush=True)


def tracked_jsonl():
    """Tracked .jsonl paths (repo-relative, '/'), or None if git cannot answer."""
    try:
        r = subprocess.run(["git", "ls-files", "-z", "--", "*.jsonl"], cwd=HERE,
                           capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return sorted(p.decode("utf-8", "replace") for p in r.stdout.split(b"\0") if p)


def unclassified(paths, outputs, inputs, skip_dir):
    """The paths the manifest would hash that are in neither list."""
    out_names = {n.lower() for n in outputs}
    in_names = {os.path.basename(n).lower() for n in inputs}
    bad = []
    for p in paths:
        parts = p.split("/")
        if any(d in skip_dir for d in parts[:-1]):
            continue                      # never shipped, so never hashed
        b = parts[-1].lower()
        if b in out_names or b in in_names or p in inputs:
            continue
        bad.append(p)
    return bad


def gate_flags(cmd):
    """Run a verify_bundle command read-only; (stdout lines, CHANGED/MISSING paths).
    A parameter so the mutation harness can point it at another version of the gate."""
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=300)
    lines = (r.stdout or "").splitlines()
    flagged = [l.split(None, 1)[1].strip() for l in lines
               if l.strip().startswith("CHANGED/MISSING") and len(l.split(None, 1)) == 2]
    return r, lines, flagged


def _git(root, *args, env=None):
    return subprocess.run(["git", "-c", "user.name=a255", "-c", "user.email=a255@invalid",
                           "-c", "core.autocrlf=false", "-c", "core.hooksPath=.git/hooks"] + list(args),
                          cwd=root, capture_output=True, text=True, timeout=180, env=env)


def _manifest_matches_head(root):
    """(ok, detail): every entry of HEAD:MANIFEST.sha256 hashes HEAD's own blob."""
    import hashlib
    man = _git(root, "show", "HEAD:MANIFEST.sha256").stdout
    bad = []
    for line in man.splitlines():
        if not line or line.startswith("#"):
            continue
        h, rel = line.split("  ", 1)
        blob = subprocess.run(["git", "show", "HEAD:" + rel], cwd=root, capture_output=True).stdout
        if hashlib.sha256(blob.replace(b"\r\n", b"\n")).hexdigest() != h:
            bad.append(rel)
    return not bad, bad


def scratch_repo_checks(vb):
    """U*: uncommitted_inputs() against real git; K*: the real pre-commit hook,
    driven both ways. A throwaway repository under the temp dir -- never this
    folder, whose hooks and manifest are live."""
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="a255_")
    try:
        if _git(root, "init", "-q").returncode != 0:
            print("  not measured: git init failed in %s -- U* and K* did not run" % root)
            return
        os.makedirs(os.path.join(root, "ops"))
        os.makedirs(os.path.join(root, "logs"))
        files = {"a.py": "A = 1\n", "b.py": "B = 1\n", "ops/verdicts.jsonl": "{}\n",
                 "logs/x.txt": "log\n", "MANIFEST.sha256": "# empty\n"}
        for rel, text in files.items():
            with open(os.path.join(root, rel), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        shutil.copy2(os.path.join(HERE, "verify_bundle.py"), root)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "base")

        def ui(against):
            return vb.uncommitted_inputs(against, root=root)

        check("U1 a clean scratch tree has no uncommitted inputs", ui("index") == [] and ui("HEAD") == [],
              "%r / %r" % (ui("index"), ui("HEAD")))
        with open(os.path.join(root, "ops", "verdicts.jsonl"), "a", encoding="utf-8") as fh:
            fh.write('{"x": 1}\n')
        with open(os.path.join(root, "MANIFEST.sha256"), "a", encoding="utf-8") as fh:
            fh.write("# touched\n")
        check("U2 a dirty OUTPUT and a dirty manifest do not count -- the manifest never hashes them",
              ui("HEAD") == [], repr(ui("HEAD")))
        with open(os.path.join(root, "a.py"), "a", encoding="utf-8") as fh:
            fh.write("A = 2\n")
        check("U3 an unstaged change to a hashed file counts, against the index and against HEAD",
              ui("index") == ["a.py"] and ui("HEAD") == ["a.py"], "%r / %r" % (ui("index"), ui("HEAD")))
        _git(root, "add", "a.py")
        check("U4 once staged it is what the commit holds (index: clean) but still in flight (HEAD: a.py)",
              ui("index") == [] and ui("HEAD") == ["a.py"], "%r / %r" % (ui("index"), ui("HEAD")))
        _git(root, "reset", "-q", "a.py")
        with open(os.path.join(root, "b.py"), "a", encoding="utf-8") as fh:
            fh.write("B = 2\n")
        _git(root, "add", "b.py")
        check("U5 THE A255 CASE: b.py staged, a.py modified and NOT staged -> a.py is named",
              ui("index") == ["a.py"], repr(ui("index")))

        # K*: the real hook, installed in the scratch repo, committing the U5 state.
        hook_src = os.path.join(HERE, "ops", "pre-commit.synchold")
        hook_dst = os.path.join(root, ".git", "hooks", "pre-commit")
        shutil.copy2(hook_src, hook_dst)
        env = dict(os.environ)
        env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
        c = _git(root, "commit", "-m", "b only", env=env)
        said = (c.stdout or "") + (c.stderr or "")
        if c.returncode != 0:
            print("  not measured: the scratch commit failed (rc=%s) -- K* did not run: %s"
                  % (c.returncode, said[-200:]))
            return
        ok, bad = _manifest_matches_head(root)
        check("K1 the hook, committing b.py over an unstaged a.py, leaves the manifest alone and says why",
              "left alone" in said and "a.py" in said, said[-240:])
        check("K2 ...so the manifest that commit carries describes only committed bytes", ok,
              "entries hashing bytes no commit holds: %s" % ", ".join(bad))
        _git(root, "add", "a.py")
        c = _git(root, "commit", "-m", "a too", env=env)
        said = (c.stdout or "") + (c.stderr or "")
        ok, bad = _manifest_matches_head(root)
        man = _git(root, "show", "HEAD:MANIFEST.sha256").stdout
        check("K3 the other way: with everything staged the hook regenerates the manifest",
              "regenerated and staged" in said and "  a.py" in man and "  b.py" in man, said[-240:])
        check("K4 ...and it still describes only committed bytes, outputs and logs excluded",
              ok and "verdicts.jsonl" not in man and "logs/x.txt" not in man,
              "bad=%s; manifest names verdicts=%s logs=%s" % (bad, "verdicts.jsonl" in man, "logs/x.txt" in man))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    import verify_bundle as vb

    paths = tracked_jsonl()
    if paths is None:
        print("NOT RUN: git ls-files did not answer from %s -- this suite measures what git ships, "
              "and without git there is no population. Not a pass." % HERE)
        return 2
    check("P1 git answers and tracks at least one .jsonl here (%d tracked .jsonl files)" % len(paths),
          len(paths) >= 1, "git tracks no .jsonl -- nothing would be checked")

    bad = unclassified(paths, vb.OUTPUTS, vb.INPUT_LEDGERS, vb.SKIP_DIR)
    for p in bad:
        print("      unclassified: %s -- add its name to OUTPUTS in verify_bundle.py if the system writes it, "
              "or to INPUT_LEDGERS with the reason if it is hashed on purpose" % p)
    check("C1 every tracked .jsonl the manifest would hash is classified as OUTPUT or INPUT_LEDGER "
          "(%d of %d classified)" % (len(paths) - len(bad), len(paths)),
          not bad, "%d unclassified: %s" % (len(bad), ", ".join(bad)))

    tracked = set(paths)
    stale = [k for k in vb.INPUT_LEDGERS if k not in tracked]
    blank = [k for k, v in vb.INPUT_LEDGERS.items() if not str(v or "").strip()]
    check("I1 every INPUT_LEDGERS entry names a tracked .jsonl (%d entries)" % len(vb.INPUT_LEDGERS),
          not stale, "not tracked: %s" % ", ".join(stale))
    check("I2 every INPUT_LEDGERS entry gives its reason", not blank, "no reason: %s" % ", ".join(blank))

    try:
        r, lines, flagged = gate_flags([sys.executable, os.path.join(HERE, "verify_bundle.py")])
    except (OSError, subprocess.SubprocessError) as e:
        lines = None
        check("E1 verify_bundle.py ran here", False, "%s: %s" % (type(e).__name__, e))
    if lines is not None:
        ledgers = [f for f in flagged if f.lower().endswith(".jsonl")]
        compared = any(re.match(r"\s*(CHANGED/MISSING|NOT IN MANIFEST)\b", l) for l in lines) \
            or "MANIFEST" in (r.stdout or "")
        check("E1 verify_bundle.py ran here and produced a comparison", compared,
              "no comparison in its output (rc=%s): %s" % (r.returncode, (r.stdout or r.stderr or "")[-200:]))
        check("E2 G1 cannot be BLOCKED by a ledger write: no CHANGED/MISSING line names a .jsonl "
              "(%d CHANGED/MISSING line(s) in all)" % len(flagged),
              not ledgers, "flagged: %s" % ", ".join(ledgers))

    probe = "ops/verdicts.jsonl"
    if probe in tracked:
        minus = set(vb.OUTPUTS) - {"verdicts.jsonl"}
        check("M1 with verdicts.jsonl removed from OUTPUTS the checker flags %s" % probe,
              probe in unclassified(paths, minus, vb.INPUT_LEDGERS, vb.SKIP_DIR),
              "it did not -- C1 would pass on a forgotten ledger")
    else:
        check("M1 the mutation target %s is tracked" % probe, False,
              "pick another tracked ledger for M1 -- this one is gone")
    planted = "ops/a255_planted_ledger.jsonl"
    check("M2 a planted unclassified ledger is flagged",
          planted in unclassified(paths + [planted], vb.OUTPUTS, vb.INPUT_LEDGERS, vb.SKIP_DIR),
          "it was not")
    check("M3 ...and a planted one under a never-shipped directory is not (no false alarm)",
          "logs/a255_planted.jsonl" not in unclassified(["logs/a255_planted.jsonl"], vb.OUTPUTS,
                                                         vb.INPUT_LEDGERS, vb.SKIP_DIR),
          "logs/ is in SKIP_DIR, so the manifest never hashes it")

    scratch_repo_checks(vb)

    print("\n  not measured: generated files that are not .jsonl (RUN_WITHOUT.json was one). "
          "They still need a hand entry in OUTPUTS; see the docstring.")
    ok = sum(1 for x in results if x)
    print("\nA255: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
