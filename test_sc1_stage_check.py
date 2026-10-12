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
                           paths_run=lambda: PROBE + "\0",
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

# SC4 (A323, 2026-10-10): 63c6747 added tools/discourse_seat_eval.py and two tracked .jsonl files, carried
# no suite that reads them, and CI failed A284 FC10 and A255 C1. A266's rule A, asked for one extension,
# is now asked for the extension of every path the commit touches.
print("\nSC4 -- a commit runs the suites that walk the tree for what it touches (A323)")
got = S.staged_paths(run=lambda: "tools/new.py\0ops/run.jsonl\0gone.py\0docs/X.md\0")
check("SC4.1 every path in the commit is taken, whatever its status", got ==
      ["tools/new.py", "ops/run.jsonl", "gone.py", "docs/X.md"], got)

SRC4 = {
    "test_walk_py.py": "import os\nfor d, s, f in os.walk('.'):\n    [n for n in f if n.endswith('.py')]\n",
    "test_lsfiles_jsonl.py": "import subprocess\nsubprocess.run(['git', 'ls-files'])\n"
                             "x = [p for p in out if p.endswith(('.jsonl', '.json'))]\n",
    "test_docstring_py.py": "'''walks the tree for *.py'''\nimport os\nos.walk('.')\n",
    "test_no_walk.py": "EXT = ('.py',)\nopen('a.py')\n",
    "test_ast_walk_py.py": "import ast\nEXT = ('.py',)\nast.walk(tree)\n",
}
r = S.walker_readers([".py", ".jsonl"], population=sorted(SRC4), read=SRC4.__getitem__)
check("SC4.2 parsed, not grepped: a tree walk filtering .py (endswith) or .jsonl (an extension tuple) is "
      "selected; '*.py' in a docstring, a filter with no walk, and ast.walk select nothing",
      r == {"test_walk_py.py": "walks the tree for .py", "test_lsfiles_jsonl.py": "walks the tree for .jsonl"}, r)
real_py, real_jsonl = S.walker_readers([".py"]), S.walker_readers([".jsonl"])
check("SC4.3 over the runner's real registry, .py selects A284 and .jsonl selects A255 -- the two that "
      "failed on 63c6747", "test_a284_fresh_context.py" in real_py and "test_a255_runtime_outputs.py" in real_jsonl,
      (sorted(real_py), sorted(real_jsonl)))
asked = []
names = S.selection(["test_own.py"], [], paths=["tools/x.py", "ops/y.jsonl", "docs/Z.md", "LICENSE", "test_own.py"],
                    walkers=lambda exts: asked.append(exts) or {"test_own.py": "w", "test_w.py": "w"},
                    say=lambda s: None)
check("SC4.4 the extensions asked are the commit's own (.md left to rule A, no extension skipped), and a "
      "suite already chosen is not run twice", asked == [[".jsonl", ".py"]] and names == ["test_own.py", "test_w.py"],
      (asked, names))

# SC4.5-4.7: end to end in a REAL staged copy with the REAL A284 run there. The probe caller is written
# into the staged copy only -- never into the tree being committed.
A284 = "test_a284_fresh_context.py"
PROBE4 = "tools/_sc4_probe.py"
work = C1.stage(lambda m: None)
try:
    C1.clean_dbs(work)
    probe_path = os.path.join(work, *PROBE4.split("/"))
    with open(probe_path, "w", encoding="utf-8") as fh:
        fh.write("import tetsu_work as TW\nTW.ask('a question', fresh=True)\n")

    def only_a284(t, w):
        if t == A284:
            return subprocess.run([sys.executable, t], cwd=w, capture_output=True, text=True, timeout=180,
                                  env=S.suite_env())
        p = P()
        p.returncode, p.stdout = 0, "(not run by SC4)"
        return p

    def commit4(walkers=None):
        said = []
        res = S.for_commit(tests_run=lambda: "", docs_run=lambda: "", paths_run=lambda: PROBE4 + "\0",
                           walkers=walkers, stage=lambda say: work, clean=lambda w: None, run=only_a284,
                           say=said.append)
        return res, said

    res, said = commit4()
    check("SC4.5 a commit that only adds a tool calling tetsu_work.ask, undeclared, runs A284, and the real "
          "A284 in the staged copy reports it FAIL, the commit said NOT blocked -- the 63c6747 commit",
          res.get(A284, (True,))[0] is False and any("FAIL " + A284 in s for s in said)
          and any("NOT blocked" in s for s in said), (res.get(A284), said[-3:]))
    os.remove(probe_path)
    res2, _ = commit4()
    check("SC4.6 the same commit with the probe gone passes A284 there -- the FAIL above is the probe",
          res2.get(A284, (False,))[0] is True, res2.get(A284))
    with open(probe_path, "w", encoding="utf-8") as fh:
        fh.write("import tetsu_work as TW\nTW.ask('a question', fresh=True)\n")
    res3, said3 = commit4(walkers=lambda exts: {})
    check("SC4.7 mutation: with the walker selection removed, the same probe is NOT caught -- the hook as it "
          "was, which is why SC4.5 can fire", A284 not in res3 and not any("FAIL" in s for s in said3), (res3, said3))
finally:
    shutil.rmtree(work, ignore_errors=True)

# SC5 (A338, 2026-10-12): the commit-time copy ran staged suites under the hook's environment and the sweep
# under its mock judge, so A327's OE1 passed at commit and failed OE1.11 in the sweep (A335), as RG1 had in
# A223. Both now take covenant_one's one definition. The same probe suite is run by the REAL runner and by the
# REAL check() -- staged (phase_sweep) and in place (phase_integrity) -- and must see the same environment.
# The caller carries the deployed gate's provider and COVENANT_WSGI, and no mock, so a check() that passes
# the caller's environment through (the code before A338) sees something the runner does not.
print("\nSC5 -- a suite runs under the runner's own wiring, staged and in place (A338)")
import json      # noqa: E402
import tempfile  # noqa: E402

base5 = {"GIT_DIR": "x", "COVENANT_WSGI": "1", "COVENANT_JUDGE_PROVIDERS": "deferring,semantic",
         "COVENANT_SILENCE_IS_NOT_DISSENT": "1", "PATH": os.environ.get("PATH", ""), "SC5_KEEP": "kept"}
st = S.run_env(False, base5)
check("SC5.1 a staged suite's environment is covenant_one.staged_env, without GIT_*: the sweep's mock judge, "
      "COVENANT_WSGI dropped, the rest kept",
      st == C1.staged_env(S.suite_env(base5)) and st.get("COVENANT_JUDGE_PROVIDERS") == "mock"
      and st.get("COVENANT_INSECURE_MOCK_JUDGE") == "1" and "GIT_DIR" not in st and "COVENANT_WSGI" not in st
      and st.get("SC5_KEEP") == "kept", sorted(st.items()))
ip = S.run_env(True, base5)
check("SC5.2 an in-place suite's environment is covenant_one.in_place_env, without GIT_*: the deployed gate's "
      "wiring removed, no mock added",
      ip == C1.in_place_env(S.suite_env(base5)) and "COVENANT_JUDGE_PROVIDERS" not in ip
      and "COVENANT_SILENCE_IS_NOT_DISSENT" not in ip and "COVENANT_INSECURE_MOCK_JUDGE" not in ip
      and "GIT_DIR" not in ip and ip.get("SC5_KEEP") == "kept", sorted(ip.items()))

SEEN = "_sc5_env.json"
PROBE5 = ("import json, os\n"
          "json.dump({k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')},\n"
          "          open(%r, 'w', encoding='utf-8'))\n"
          "print(%s)\n")
# The staged probe prints U+0101, C4 81 in UTF-8; 0x81 is undefined in cp1252, so it reads only as UTF-8.
STAGED5 = PROBE5 % (SEEN, "'SC5 probe \\u0101: 1/1 passed'")
INPLACE5 = PROBE5 % (SEEN, "'SC5 probe: 1/1 passed'")                  # in place there is no PYTHONIOENCODING


def seen(d):
    try:
        with open(os.path.join(d, SEEN), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def put(d, name, src):
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
        fh.write(src)


CALLER5 = {"COVENANT_JUDGE_PROVIDERS": "deferring,semantic", "COVENANT_WSGI": "1"}
UNSET5 = ("COVENANT_INSECURE_MOCK_JUDGE", "PYTHONIOENCODING")
saved_env = {k: os.environ.get(k) for k in list(CALLER5) + list(UNSET5)}
saved_c1 = (C1.HERE, C1.IN_PLACE, C1.stage)
saved_s = (S.HERE, S.in_place_names)
lines5 = []
say5 = lines5.append
try:
    os.environ.update(CALLER5)
    for k in UNSET5:
        os.environ.pop(k, None)
    caller = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    with tempfile.TemporaryDirectory() as tmp:
        here, sweep, commit = (os.path.join(tmp, n) for n in ("here", "sweep", "commit"))
        name = "test_sc5_probe.py"
        for d in (here, sweep, commit):
            put(d, name, STAGED5)
        C1.HERE, C1.stage = here, (lambda say: sweep)
        C1.phase_sweep(say5, only=[name])
        C1.HERE, C1.stage = saved_c1[0], saved_c1[2]
        r5 = S.check([name], stage=lambda say: commit, clean=lambda w: None, say=say5)
        by_sweep, by_commit = seen(sweep), seen(commit)
        check("SC5.3 staged: the real check() gives a suite exactly the environment the real phase_sweep gives it, "
              "and that is not the caller's (the code before A338 passed the caller's through)",
              by_sweep is not None and by_sweep == by_commit and by_sweep != caller,
              sorted(set((by_sweep or {}).items()) ^ set((by_commit or {}).items()))[:6])
        check("SC5.4 ...and its UTF-8 output is read as UTF-8: the last line is the suite's (the locale codec "
              "killed subprocess's reader thread on Windows, and check() read an empty line)",
              r5.get(name) == (True, "SC5 probe ā: 1/1 passed"), r5.get(name))

        ipname = "test_sc5_inplace_probe.py"
        put(here, ipname, INPLACE5)
        C1.HERE, C1.IN_PLACE = here, [(ipname, 60, "SC5 probe")]
        out5 = dict(C1.phase_integrity(say5))
        by_integrity = seen(here)
        if os.path.exists(os.path.join(here, SEEN)):
            os.remove(os.path.join(here, SEEN))
        C1.HERE, C1.IN_PLACE = saved_c1[0], saved_c1[1]
        S.HERE, S.in_place_names = here, (lambda: {ipname})
        r5i = S.check([ipname], stage=lambda say: commit, clean=lambda w: None, say=say5)
        S.HERE, S.in_place_names = saved_s
        by_commit_ip = seen(here)
        check("SC5.5 in place: the real check() gives a suite exactly the environment the real phase_integrity "
              "gives it, without the caller's deployed provider",
              out5.get(ipname) == "ok" and r5i.get(ipname, (False,))[0] is True and by_integrity is not None
              and by_integrity == by_commit_ip and "COVENANT_JUDGE_PROVIDERS" not in by_integrity,
              (out5.get(ipname), r5i.get(ipname),
               sorted(set((by_integrity or {}).items()) ^ set((by_commit_ip or {}).items()))[:6]))
finally:
    C1.HERE, C1.IN_PLACE, C1.stage = saved_c1
    S.HERE, S.in_place_names = saved_s
    for k, v in saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

print("\nSC2: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
