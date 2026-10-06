#!/usr/bin/env python3
"""SC2 (2026-10-03): the pre-commit stage-check runs committed suites where the runner runs them.

Stubs git, staging and the suite runs; the real end-to-end proof (the old E12r test fails in the
staged copy) was run by hand the day this landed and is recorded in its commit.

    python test_sc1_stage_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import stage_check as S  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


print("SC2 -- committed suites run in the runner's copy")
got = S.staged_tests(run=lambda: "test_a.py\ncovenant_x.py\ndocs/test_b.py\ntest_c.py\ntools/test_d.py\nREADME.md\n")
check("SC2.1 only top-level test_*.py files in the commit are taken", got == ["test_a.py", "test_c.py"], got)

said = []
P = type("P", (), {})


def runner(results):
    def run(t, w):
        p = P()
        p.returncode, p.stdout = results[t]
        return p
    return run


r = S.check(["test_a.py", "test_c.py"], stage=lambda say: "/tmp/w", clean=lambda w: None,
            run=runner({"test_a.py": (0, "A: 5/5 passed\n"), "test_c.py": (1, "C: 4/5 passed\n")}), say=said.append)
check("SC2.2 each suite is reported with its own last line, pass and fail told apart",
      r == {"test_a.py": (True, "A: 5/5 passed"), "test_c.py": (False, "C: 4/5 passed")}, r)
check("SC2.3 a failure is said loudly, and the commit is said NOT blocked",
      any("FAIL test_c.py" in s for s in said) and any("NOT blocked" in s for s in said), said)
said2 = []
r2 = S.check(["test_a.py"], stage=lambda say: "/tmp/w", clean=lambda w: None,
             run=runner({"test_a.py": (0, "A ok\n")}), say=said2.append)
check("SC2.4 all passing: no failure line at all", r2 == {"test_a.py": (True, "A ok")}
      and not any("FAIL" in s for s in said2), said2)


def boom(say):
    raise OSError("disk full")


said3 = []
r3 = S.check(["test_a.py"], stage=boom, say=said3.append)
check("SC2.5 staging that breaks is said ('nothing was checked'), never raised into the hook",
      r3 == {} and any("could not stage" in s and "nothing was checked" in s for s in said3), said3)
check("SC2.6 no test files in the commit: nothing staged, nothing said", S.check([], say=said3.append) == {})
hook = open(os.path.join(HERE, "ops", "pre-commit.synchold"), encoding="utf-8").read()
check("SC2.7 the tracked pre-commit hook calls it", "python tools/stage_check.py" in hook)

# SC3 (A266, 2026-10-06): 2f6b184 staged only docs/SENTINEL_WITNESS.md and a tool, no suite ran, and
# both CI runners failed C4.2. A staged published .md now runs the suites that read published Markdown.
print("\nSC3 -- a commit of published markdown runs the suites that read it (A266)")
got = S.staged_docs(run=lambda: "docs/X.md\0README.md\0ops/NIGHTLY.md\0private/a.md\0.claude/n.md\0"
                    "tools/s.py\0docs/sub/ops/y.md\0")
check("SC3.1 published .md is taken; ops/, private/ and .claude/ at any depth, and non-.md, are not",
      got == ["docs/X.md", "README.md"], got)

SRC = {
    "test_walk_md.py": "import os\nfor d, s, f in os.walk('.'):\n    [n for n in f if n.endswith('.md')]\n",
    "test_lsfiles_ext.py": "import subprocess\nEXT = {'.md', '.py'}\nsubprocess.run(['git', 'ls-files'])\n",
    "test_docstring_only.py": "'''walks the tree for *.md'''\nimport os\nos.walk('.')\n",
    "test_docstring_names.py": "'''the guide is docs/GUIDE.md'''\nimport os\n",
    "test_fixture_name.py": "import os\nos.listdir('w')\nname = rec + '.md'\n",
    "test_ast_walk.py": "import ast\nEXT = ('.md',)\nast.walk(tree)\n",
    "test_names_doc.py": "import os\nopen(os.path.join(HERE, 'docs', 'GUIDE.md'))\n",
    "test_names_other.py": "import os\nopen(os.path.join(HERE, 'docs', 'OTHER.md'))\n",
}
r = S.doc_readers(["docs/GUIDE.md"], population=sorted(SRC), read=SRC.__getitem__)
check("SC3.2 parsed, not grepped: a tree walk with an .md filter (os.walk/endswith, git ls-files/extension "
      "set) reads every document; a document named in code reads that one; '.md' in a docstring, a fixture "
      "built with +, ast.walk, or another document's name selects nothing",
      r == {"test_walk_md.py": "reads every published .md", "test_lsfiles_ext.py": "reads every published .md",
            "test_names_doc.py": "names docs/GUIDE.md"}, r)

ROUTE_A = {"test_c4_uncheckable_claims.py", "test_r1_retracted.py"}
real = S.doc_readers(["docs/_sc3_probe.md"])
check("SC3.3 over the runner's real registry, a new document selects C4 and R1 (they walk the tree), "
      "and not G1 (it reads named documents)",
      ROUTE_A <= set(real) and "test_g1_doc_consistency.py" not in real, real)
readme = S.doc_readers(["README.md"])
check("SC3.4 ...and README.md also selects G1 and G2, which read it by name and walk nothing",
      {"test_g1_doc_consistency.py", "test_g2_promised_commands.py"} <= set(readme), readme)

# SC3.5-3.8: end to end in a REAL staged copy (covenant_one.stage), with the REAL C4 run there. The
# probe document is written into the staged copy only -- never into the tree being committed.
import shutil      # noqa: E402
import subprocess  # noqa: E402
import covenant_one as C1  # noqa: E402

C4 = "test_c4_uncheckable_claims.py"
PROBE = "docs/_sc3_probe.md"
BARE = "# SC3 probe\n\nThe reserve holds 400 units, per private/RESERVE.json.\n"
work = C1.stage(lambda m: None)
try:
    C1.clean_dbs(work)

    def write_probe(text):
        with open(os.path.join(work, *PROBE.split("/")), "w", encoding="utf-8") as fh:
            fh.write(text)

    def only_c4(t, w):
        """C4 runs for real where check() sends it; the other selected suites are not this test's subject."""
        if t == C4:
            return subprocess.run([sys.executable, t], cwd=w, capture_output=True, text=True, timeout=120,
                                  env=S.suite_env())
        p = P()
        p.returncode, p.stdout = 0, "(not run by SC3)"
        return p

    def commit(readers=None):
        said = []
        res = S.for_commit(tests_run=lambda: PROBE + "\n", docs_run=lambda: PROBE + "\0", readers=readers,
                           stage=lambda say: work, clean=lambda w: None, run=only_c4, say=said.append)
        return res, said

    write_probe(BARE)
    res, said = commit()
    check("SC3.5 staging only a .md selects the document suites (C4 and R1 among them)",
          ROUTE_A <= set(res) and any("published markdown in this commit" in s for s in said), (sorted(res), said[:1]))
    check("SC3.6 ...and a probe that cites private/ with no II.6 caveat is reported FAIL by the real C4 in the "
          "staged copy, the commit said NOT blocked",
          res.get(C4, (True,))[0] is False and any("FAIL " + C4 in s for s in said)
          and any("NOT blocked" in s for s in said), (res.get(C4), said))
    write_probe(BARE + "A reader cannot check this: private/ is never published.\n")
    res2, _ = commit()
    check("SC3.7 the same probe WITH the caveat passes C4 there -- the FAIL above is the caveat, not the copy",
          res2.get(C4, (False,))[0] is True, res2.get(C4))
    write_probe(BARE)
    res3, said3 = commit(readers=lambda docs: {})
    said4 = []
    res4 = S.check(S.staged_tests(run=lambda: PROBE + "\n"), stage=lambda say: work, clean=lambda w: None,
                   run=only_c4, say=said4.append)
    check("SC3.8 mutation: with the document selection removed (no readers; or the hook as it was, test files "
          "only) the same probe is NOT caught -- the 2f6b184 commit, which is why SC3.6 can fire",
          C4 not in res3 and res4 == {} and not any("FAIL" in s for s in said3 + said4)
          and any("NO registered suite" in s for s in said3), (res3, res4, said3, said4))
finally:
    shutil.rmtree(work, ignore_errors=True)

print("\nSC2: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
