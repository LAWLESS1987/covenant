#!/usr/bin/env python3
"""CI1 (A326, 2026-10-10): every retraction in docs/RETRACTED.json is listed in docs/CORRECTIONS.md.

lawless1987.com links CORRECTIONS.md as the correction index. That day it named 4 of 44 retractions and
nothing after 2026-09-27, because adding a retraction never touched it. tools/corrections_index.py now
generates the full list from the ledger; this suite fails while the file is missing a retraction or the
generated list is stale, and drives both failure shapes on synthetic copies (never on the real files).

    python test_ci1_corrections_index.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import corrections_index as CI  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


print("CI1 -- the correction index lists every retraction")
ledger = json.load(open(CI.LEDGER, encoding="utf-8"))
text = open(CI.INDEX, encoding="utf-8").read()
ids = [r["id"] for r in ledger["retractions"]]
miss = CI.missing_ids(text, ledger)
check("CI1.1 every id in docs/RETRACTED.json appears in docs/CORRECTIONS.md (%d ids)" % len(ids), not miss, miss[:10])
check("CI1.2 the generated list is current (tools/corrections_index.py --write leaves the file unchanged)",
      CI.render(text, CI.section(ledger)) == text, "run: python tools/corrections_index.py --write")
check("CI1.3 the generated list sits between its markers, once", text.count(CI.BEGIN) == 1 and text.count(CI.END) == 1
      and text.index(CI.BEGIN) < text.index(CI.END))

# Driven both ways, on copies.
grown = copy.deepcopy(ledger)
grown["retractions"].append({"id": "CI1-PROBE-NEW", "claim": "A probe claim added to the ledger and to nothing else."})
check("CI1.4 mutation: a retraction added to the ledger only is reported missing, and the list reads stale",
      CI.missing_ids(text, grown) == ["CI1-PROBE-NEW"] and CI.render(text, CI.section(grown)) != text,
      CI.missing_ids(text, grown))
row = next((l for l in text.splitlines() if l.startswith("| `%s` |" % ids[-1])), None)
shrunk = text.replace(row + "\n", "", 1) if row else text
check("CI1.5 mutation: deleting the last retraction's row (%s) reads as missing and as stale" % ids[-1],
      row is not None and ids[-1] in CI.missing_ids(shrunk, ledger) and CI.render(shrunk, CI.section(ledger)) != shrunk,
      (row is not None, CI.missing_ids(shrunk, ledger)[-1:]))
check("CI1.6 a claim with a pipe or a long sentence still renders as one table cell",
      CI.first_sentence("a | b " + "x" * 300).count("\\|") == 1 and len(CI.first_sentence("y" * 400)) <= CI.MAX_CHARS)


# CI1.7-CI1.10 (A347): the real pre-commit hook regenerates the index when a commit stages the ledger. A345 and
# A346 each committed retractions without it and CI1 read 2/6 in the sweep after both were pushed. Driven in a
# throwaway repository with the hook installed; git runs under verify_bundle.repo_env(), so a hook's GIT_DIR
# can never reach the real repository (A255).
def hook_checks():
    import shutil
    import subprocess
    import tempfile
    sys.path.insert(0, HERE)
    import verify_bundle as VB
    root = tempfile.mkdtemp(prefix="ci1_hook_")
    env = dict(VB.repo_env())
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")

    def git(*a):
        return subprocess.run(["git", "-c", "user.name=ci1", "-c", "user.email=ci1@invalid", "-c", "core.autocrlf=false"]
                              + list(a), cwd=root, capture_output=True, text=True, timeout=300, env=env)

    def entry(i):
        return {"id": "CI1-HOOK-%d" % i, "claim": "Hook probe claim %d." % i}

    def write_ledger(n):
        with open(os.path.join(root, "docs", "RETRACTED.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"retractions": [entry(i) for i in range(1, n + 1)]}, fh, indent=1)

    def head_index():
        return git("show", "HEAD:docs/CORRECTIONS.md").stdout

    try:
        os.makedirs(os.path.join(root, "docs"))
        os.makedirs(os.path.join(root, "tools"))
        shutil.copy2(os.path.join(HERE, "tools", "corrections_index.py"), os.path.join(root, "tools"))
        git("init", "-q")
        write_ledger(1)
        with open(os.path.join(root, "docs", "CORRECTIONS.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Corrections\n\n" + CI.section({"retractions": [entry(1)]}) + "\n")
        git("add", "-A")
        if git("commit", "-qm", "base").returncode != 0:
            print("  not measured: the scratch base commit failed -- CI1.7-CI1.10 did not run")
            return
        hook = os.path.join(root, ".git", "hooks", "pre-commit")
        shutil.copy2(os.path.join(HERE, "ops", "pre-commit.synchold"), hook)
        os.chmod(hook, 0o755)

        write_ledger(2)                                     # a retraction staged alone, the A345 commit
        git("add", "docs/RETRACTED.json")
        c = git("commit", "-m", "ledger only")
        said = (c.stdout or "") + (c.stderr or "")
        check("CI1.7 the installed hook ran (its 'pre-commit:' lines are in the commit's output)",
              c.returncode == 0 and "pre-commit:" in said, said[-240:])
        check("CI1.8 a commit that stages only the ledger carries the regenerated index with the new id",
              "`CI1-HOOK-2`" in head_index() and "staged docs/CORRECTIONS.md" in said, said[-240:])

        with open(os.path.join(root, "docs", "CORRECTIONS.md"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\nA hand note not meant for this commit.\n")
        write_ledger(3)
        git("add", "docs/RETRACTED.json")
        c = git("commit", "-m", "ledger over an unstaged index edit")
        said = (c.stdout or "") + (c.stderr or "")
        check("CI1.9 an index with unstaged changes is NOT regenerated or staged, the hook says so, and the hand "
              "note is still on disk", "`CI1-HOOK-3`" not in head_index() and "hand note" not in head_index()
              and "NOT regenerated" in said and "hand note" in open(os.path.join(root, "docs", "CORRECTIONS.md"),
                                                                      encoding="utf-8").read(), said[-240:])
        git("checkout", "--", "docs/CORRECTIONS.md")
        write_ledger(4)
        git("add", "docs/RETRACTED.json")
        write_ledger(5)                                     # a fifth retraction on disk, NOT staged
        c = git("commit", "-m", "ledger with an unstaged fifth")
        said = (c.stdout or "") + (c.stderr or "")
        check("CI1.10 a ledger with unstaged entries is not read into the index (A255): no unstaged id is committed",
              "`CI1-HOOK-5`" not in head_index() and "NOT regenerated" in said, said[-240:])
    finally:
        shutil.rmtree(root, ignore_errors=True)


hook_checks()
print("\nCI1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
