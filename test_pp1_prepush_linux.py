#!/usr/bin/env python3
"""
test_pp1_prepush_linux.py -- PP1. The Linux pre-push guard (tools/prepush_linux.py, A392), driven BOTH ways.

Every reason it refuses a push is shown refusing, and its absence shown letting the push through. The verdict is
read from the runner's VERDICT block and results.json, and a failing suite's echoed "RESULT: INCOMPLETE" ahead of
it cannot turn a FAIL green (the review's first finding). Every cause of a non-zero exit is red, except a suite that
fails on the ModuleNotFoundError of a declared package not installed HERE, which is UNMEASURED here. The selection
reaches a changed suite of any prefix, a suite importing a changed module directly or through the tree's modules,
and a suite reading a changed document, and NOT a bystander. The decision is driven with stubs: red refuses; his
override passes and is logged; NOT RUN passes and says so; nothing recurses; a red base, or one this guard let
through unmeasured, runs the whole sweep; a verdict is reused for the same commit and selection. Then linux_run end
to end on a scratch repository with a stub covenant_one: a real mirror, a clone of its own with history, branch and
the python shim, green, red, a timeout that is UNMEASURED not red, the clone removed and the transcripts kept. Then
the real hook through sh: opsec first, the Linux stage refusing, and standing down where the tool is absent.

Offline. Temp dirs only. No WSL, no network; the stub runner is this python.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import prepush_linux as P                  # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


def not_run(label, why):
    print(f"NOT RUN {label} -- {why}")


def clean_env():
    """No GIT_* (A255: a hook's GIT_DIR would point the scratch repos at the real one), and not inside a guard."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != P.INSIDE}
    env.update({"GIT_AUTHOR_NAME": "pp1", "GIT_AUTHOR_EMAIL": "pp1@example.invalid",
                "GIT_COMMITTER_NAME": "pp1", "GIT_COMMITTER_EMAIL": "pp1@example.invalid"})
    return env


def git(cwd, *args, env=None):
    return subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false"] + list(args),
                          cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", env=env or clean_env())


def T(rows="", counts=None, result="PASS", deps=""):
    """A transcript shaped like covenant_one's: suite rows (with their echoes), then the VERDICT block."""
    c = {"suites not clean": "0", "suites unmeasured": "0", "runner list absent": "0", "orphaned on disk": "0",
         "listed but NOT SHIPPED": "0", "declared deps missing": "0"}
    c.update(counts or {})
    body = deps + "\n  --- SWEEP ---\n" + rows + "\n" + "=" * 74 + "\n  VERDICT\n" + "=" * 74 + "\n"
    body += "".join("  %s %s\n" % (k, v) for k, v in c.items())
    return body + "  RESULT: %s. ...\n" % result


def R(suites=(), in_place=(), code=0):
    return {"suites": [{"suite": s, "state": st} for s, st in suites],
            "in_place": [{"name": n, "state": st} for n, st in in_place], "exit_code": code}


def part_parse():
    a, b = "a" * 40, "b" * 40
    got = P.parse_lines(["refs/heads/x %s refs/heads/x %s" % (a, b), "(delete) %s refs/heads/y %s" % (P.ZERO, b),
                         "refs/heads/z not-a-sha refs/heads/z %s" % b, "refs/tags/v1 %s refs/tags/v1 %s" % (a, P.ZERO), ""])
    check("PP1a a branch line is kept", got == [("refs/heads/x", a, "refs/heads/x", b)], got)
    check("PP1a a deletion, a malformed line and a TAG (CI runs on branches only) are dropped", len(got) == 1, got)
    check("PP1b an ordinary push runs the selection", P.mode_for({}, "green")[0] == "selected")
    check("PP1b ...a push onto a base public CI shows RED runs the whole sweep", P.mode_for({}, "red")[0] == "full")
    check("PP1b ...so does one onto a base this guard let through unmeasured",
          P.mode_for({}, "green", base_unmeasured=True)[0] == "full")
    check("PP1b ...and COVENANT_PREPUSH_FULL=1 forces it", P.mode_for({"COVENANT_PREPUSH_FULL": "1"}, "green")[0] == "full")
    check("PP1b ...an UNKNOWN base does not, and is said by the caller", P.mode_for({}, "unknown")[0] == "selected")


def part_ci_state():
    url = "https://github.com/O/R.git"
    runs = lambda *c: (lambda u: {"check_runs": [{"name": "sweep (py %d)" % i, "status": "completed",   # noqa: E731
                                                   "conclusion": x} for i, x in enumerate(c)]})
    check("PP1j CI state green when every sweep job succeeded", P.ci_state("s", url, runs("success", "success")) == "green")
    check("PP1j ...red when one failed", P.ci_state("s", url, runs("success", "failure")) == "red")
    check("PP1j ...unknown while one runs", P.ci_state("s", url, lambda u: {"check_runs": [
        {"name": "sweep a", "status": "in_progress"}]}) == "unknown")

    def boom(u):
        raise OSError("offline")
    check("PP1j ...unknown when GitHub cannot be asked, and for a remote that is not GitHub",
          P.ci_state("s", url, boom) == "unknown" and P.ci_state("s", "/srv/bare.git", runs("success")) == "unknown")


def part_verdict():
    red, warn, _ = P.verdict(T(), R())
    check("PP1c a clean PASS is not red", red == [] and warn == [], (red, warn))
    for label, files in (("orphaned on disk", "1  -> test_new.py"), ("runner list absent", "1  -> test_gone.py"),
                         ("listed but NOT SHIPPED", "1  -> test_ign.py")):
        r, _, _ = P.verdict(T(counts={label: files}, result="INCOMPLETE"), R(code=2))
        check("PP1c %s 1 is red, naming the file" % label, len(r) == 1 and label in r[0] and "test_" in r[0], r)
    trap = ("    test_p25_sweep_red.py   FAIL   1.0s  P25: 9/10 passed\n"
            "        | FAIL  P25.D8 a --check transcript (RESULT: INCOMPLETE) is NOT a sweep verdict\n")
    r, w, _ = P.verdict(T(rows=trap, counts={"suites not clean": "1  -> test_p25_sweep_red.py"}, result="FAIL"),
                        R([("test_p25_sweep_red.py", "FAIL")], code=1))
    check("PP1c a failing suite whose echo carries 'RESULT: INCOMPLETE' is still RED (the verdict block is read)",
          len(r) == 1 and "test_p25_sweep_red.py" in r[0], (r, w))
    r, _, _ = P.verdict(T(rows=trap, counts={"suites not clean": "1  -> test_p25_sweep_red.py"}, result="FAIL"),
                        None, exit_code=1)
    check("PP1c ...and the same without results.json, from the VERDICT block alone",
          len(r) == 1 and "test_p25_sweep_red.py" in r[0], r)
    r, _, _ = P.verdict(T(), R(in_place=[("test_a117.py", "FAIL rc=1"), ("constitution.py", "ABSENT")], code=1))
    check("PP1c a folder-integrity FAIL and an ABSENT in-place check are red", len(r) == 2, r)
    r, _, _ = P.verdict(T(counts={"suites unmeasured": "1  -> test_q.py"}, result="INCOMPLETE"),
                        R([("test_q.py", "ABSENT")], code=2))
    check("PP1c a suite unmeasured is red (CI reads INCOMPLETE, exit 2)", len(r) == 1 and "test_q.py" in r[0], r)
    r, _, _ = P.verdict("  orphaned on disk    0\n(the runner died here)\n")
    check("PP1c a transcript with no VERDICT is red (a runner that died measured nothing)", len(r) == 1, r)
    r, _, _ = P.verdict(T(result="INCOMPLETE"), R(code=2))
    check("PP1c an exit 2 nothing names is red, never waved through (the backstop)",
          len(r) == 1 and "exited 2" in r[0], r)
    deps = "    MISSING: eth-account is declared in requirements.txt and is NOT\n"
    gone = ("    test_a114.py   NO RESULT   0.1s  (no tally line)\n"
            "        | Traceback (most recent call last):\n        | ModuleNotFoundError: No module named 'eth_account'\n")
    r, w, here = P.verdict(T(rows=gone, deps=deps, counts={"suites not clean": "1  -> test_a114.py",
                                                         "declared deps missing": "1"}, result="FAIL"),
                           R([("test_a114.py", "NO RESULT")], code=1), {"eth_account": "eth-account"})
    check("PP1c a suite failing on a declared package missing HERE is UNMEASURED here, not red",
          r == [] and here == ["test_a114.py"] and any("UNMEASURED" in x for x in w), (r, w, here))
    real = ("    test_a114.py   FAIL   0.1s  A114: 3/4\n        | FAIL  A114.2 the genesis hash moved\n")
    r, _, _ = P.verdict(T(rows=real, deps=deps, counts={"suites not clean": "1  -> test_a114.py",
                                                      "declared deps missing": "1"}, result="FAIL"),
                        R([("test_a114.py", "FAIL")], code=1), {"eth_account": "eth-account"})
    check("PP1c ...but the same suite failing for ANOTHER reason while the package is missing is red",
          len(r) == 1 and "test_a114.py" in r[0], r)
    r, _, _ = P.verdict(T(deps="    MISSING: PyYAML is declared in requirements.txt and is NOT\n",
                          counts={"declared deps missing": "1"}, result="INCOMPLETE"), R(code=2), {})
    check("PP1c a declared package that IS installed here yet reads MISSING is red (CI reads it MISSING too)",
          len(r) == 1 and "PyYAML" in r[0], r)


def part_select(tmp):
    tree = os.path.join(tmp, "sel")
    os.makedirs(tree)
    files = {
        "mod_x.py": "VALUE = 1\n",
        "mod_y.py": "import mod_x\n",
        "test_a_imports.py": "import mod_x\nprint(mod_x.VALUE)\n",
        "test_b_bystander.py": "import json\nprint(json.dumps(1))\n",
        "test_c_changed.py": "print('c')\n",
        "test_d_reads_doc.py": "DOC = 'GUIDE.md'\nprint(open(DOC).read())\n",
        "test_e_via.py": "import mod_y\n",
        "sim_f_changed.py": "print('f')\n",
    }
    for n, body in files.items():
        with open(os.path.join(tree, n), "w", encoding="utf-8") as fh:
            fh.write(body)
    pop = sorted(n for n in files if n.startswith(("test_", "sim_")))
    read = lambda t: open(os.path.join(tree, t), encoding="utf-8").read()      # noqa: E731
    quiet = lambda *_a: None                                                    # noqa: E731
    graph = P.tree_graph(tree)
    got = P.select(["mod_x.py", "test_c_changed.py", "GUIDE.md", "sim_f_changed.py"], pop, read, say=quiet, graph=graph)
    check("PP1d a changed suite is selected", "test_c_changed.py" in got, got)
    check("PP1d ...of any prefix the runner registers (sim_, probe_, ...)", "sim_f_changed.py" in got, got)
    check("PP1d a suite that imports a changed module is selected", "test_a_imports.py" in got, got)
    check("PP1d ...and one that reaches it through another module of the tree", "test_e_via.py" in got, got)
    check("PP1d a suite that reads a changed published document is selected", "test_d_reads_doc.py" in got, got)
    check("PP1d ...and a suite that does none of those is NOT", "test_b_bystander.py" not in got, got)
    got = P.select(["notes.xyz"], pop, read, say=quiet, graph=graph)
    check("PP1d a push touching nothing a suite reads selects nothing", got == [], got)


def part_imports(tmp):
    d = os.path.join(tmp, "imp")
    os.makedirs(d)
    src = {
        "bare.py": "import numpy as np\n",
        "guarded.py": "try:\n    import numpy\nexcept ImportError:\n    numpy = None\n",
        "in_handler.py": "try:\n    import json\nexcept ImportError:\n    import numpy\n",
        "broad.py": "try:\n    from numpy import array\nexcept Exception:\n    array = None\n",
        "std.py": "import json, os\nfrom collections import OrderedDict\n",
        "local.py": "import mod_local\n",
        "absent.py": "import notinstalledanywhere\n",
        "declared.py": "import flask\n",
    }
    for n, body in src.items():
        with open(os.path.join(d, n), "w", encoding="utf-8") as fh:
            fh.write(body)
    read = lambda t: open(os.path.join(d, t), encoding="utf-8").read()         # noqa: E731
    pk = {"numpy": ["numpy"], "flask": ["Flask"], "mod_local": ["mod-local"]}

    def flagged(f, closure=frozenset({"flask"})):
        return P.undeclared_imports([f], read, set(closure), {"mod_local"}, pk)

    check("PP1e an UNGUARDED import of a package CI will not install is red (GS1/numpy)",
          flagged("bare.py") == [("bare.py", "numpy", "numpy")], flagged("bare.py"))
    check("PP1e ...the same import inside try/except ImportError is not", flagged("guarded.py") == [])
    check("PP1e ...nor inside try/except Exception", flagged("broad.py") == [])
    check("PP1e ...but one in the HANDLER is, because it raises like any other", len(flagged("in_handler.py")) == 1,
          flagged("in_handler.py"))
    check("PP1e ...and the bare one is NOT red once requirements.txt pulls numpy in",
          flagged("bare.py", {"flask", "numpy"}) == [])
    check("PP1e the standard library, a module of the tree, a declared package and one installed nowhere are not red",
          all(flagged(f) == [] for f in ("std.py", "local.py", "declared.py", "absent.py")))

    class Meta:
        reqs = {"flask": ["click>=8", "blinker"], "click": ["colorama; platform_system == 'Windows'"],
                "blinker": [], "colorama": [], "requests": ["pysocks; extra == 'socks'", "idna"], "idna": []}

        @classmethod
        def requires(cls, d):
            if d not in cls.reqs:
                raise LookupError(d)
            return cls.reqs[d]
    got = P.declared_closure("# deps\nflask>=2.3\nrequests>=2.31  # http\n", Meta)
    check("PP1f the declared closure follows what requirements.txt pulls in",
          {"flask", "click", "blinker", "colorama", "requests", "idna"} <= got, sorted(got))
    check("PP1f ...and does not follow an extra", "pysocks" not in got, sorted(got))
    g = {"a": {"b"}, "b": {"c"}, "c": set(), "z": {"json"}}
    check("PP1f a changed module reaches what imports it through the tree, and not a bystander",
          P.reached({"c"}, g) == {"a", "b", "c"}, P.reached({"c"}, g))


def part_decision(tmp):
    a, b = "a" * 40, "b" * 40
    lines = ["refs/heads/feature %s refs/heads/feature %s" % (a, b)]
    calls = []
    led = os.path.join(tmp, "ledger", "prepush_linux.jsonl")

    def runner_with(res):
        def run(sha, branch, mode, paths, say=print):
            calls.append((sha, branch, mode, paths))
            return dict(res)
        return run
    said = []
    kw = dict(paths_of=lambda *_a: ["test_x.py"], base=lambda *_a: b, ci=lambda *_a: "green", ledger=led)
    red = {"status": "ran", "red": ["orphaned on disk 1 (on disk, in no runner) -- test_x.py"], "warn": [],
           "mode": "selected", "transcript": "/x"}
    rc = P.pre_push(lines, env={}, say=said.append, runner=runner_with(red), **kw)
    check("PP1g a red Linux run REFUSES the push", rc == 1 and any("REFUSED" in s for s in said), said[-2:])
    saved = P.OVERRIDES
    P.OVERRIDES = os.path.join(tmp, "ops", "prepush_overrides.jsonl")
    try:
        said.clear()
        rc = P.pre_push(lines, env={"COVENANT_PREPUSH_ALLOW": "1"}, say=said.append, runner=runner_with(red),
                        **dict(kw, ledger=os.path.join(tmp, "l2.jsonl")))
        logged = open(P.OVERRIDES, encoding="utf-8").read() if os.path.isfile(P.OVERRIDES) else ""
        check("PP1g his override lets it through, and is logged with the red reasons",
              rc == 0 and a in logged and "orphaned" in logged, (rc, logged[:200]))
    finally:
        P.OVERRIDES = saved
    green = {"status": "ran", "red": [], "warn": ["declared dependency eth-account is not installed HERE"],
             "mode": "selected", "result_line": "RESULT: PASS", "seconds": 3}
    said.clear()
    lg = dict(kw, ledger=os.path.join(tmp, "l3.jsonl"))
    calls.clear()
    check("PP1g a green run lets the push through",
          P.pre_push(lines, env={}, say=said.append, runner=runner_with(green), **lg) == 0)
    check("PP1g ...and its notes are said, not swallowed", any("not installed HERE" in s for s in said), said)
    P.pre_push(lines, env={}, say=said.append, runner=runner_with(green), **lg)
    check("PP1g the same commit and selection reuse the verdict (post-commit pushes it three times)",
          len(calls) == 1 and any("reusing" in s for s in said), (calls, said[-2:]))
    said.clear()
    rc = P.pre_push(lines, env={}, say=said.append, runner=runner_with({"status": "not_run", "reason": "no WSL",
                                                                       "red": [], "warn": []}),
                    **dict(kw, ledger=os.path.join(tmp, "l4.jsonl")))
    check("PP1g NOT RUN lets the push through, and says it is UNMEASURED",
          rc == 0 and any("NOT RUN" in s and "UNMEASURED" in s for s in said), said)
    calls.clear()
    rc = P.pre_push(lines, env={P.INSIDE: "1"}, say=said.append, runner=runner_with(red), **kw)
    check("PP1g inside the Linux run a suite's scratch push never recurses", rc == 0 and calls == [], calls)
    calls.clear()
    rc = P.pre_push(["(delete) %s refs/heads/feature %s" % (P.ZERO, b)], env={}, say=said.append,
                    runner=runner_with(red), **kw)
    check("PP1g a deletion pushes no commit and runs nothing", rc == 0 and calls == [], calls)
    calls.clear()
    P.pre_push(lines, env={}, say=said.append, runner=runner_with(green),
               **dict(kw, ci=lambda *_a: "red", ledger=os.path.join(tmp, "l5.jsonl")))
    check("PP1g a push onto a base public CI shows red hands the runner mode full",
          calls and calls[-1][2] == "full", calls)
    calls.clear()
    l6 = os.path.join(tmp, "l6.jsonl")
    P._ledger_add({"at": 1, "sha": b, "status": "not_run"}, l6)
    P.pre_push(lines, env={}, say=said.append, runner=runner_with(green), **dict(kw, ledger=l6))
    check("PP1g ...and so does a push onto a base this guard let through unmeasured",
          calls and calls[-1][2] == "full", calls)
    calls.clear()
    said.clear()
    P.pre_push(lines, env={}, say=said.append, runner=runner_with(green),
               **dict(kw, paths_of=lambda *_a: [], ledger=os.path.join(tmp, "l7.jsonl")))
    check("PP1g a push bringing no new commit still runs coverage and integrity (an empty selection)",
          calls and calls[-1][3] == [], calls)


STUB_RUNNER = r'''import json, os, shutil, subprocess, sys, time
SUITES = [("test_x.py", 60, "JUDGE")]
IN_PLACE = []
if __name__ == "__main__":
    if os.path.exists("SLEEP"):
        time.sleep(30)
    out = sys.argv[sys.argv.index("--out") + 1]
    hist = subprocess.run(["git", "rev-list", "--count", "HEAD"], capture_output=True, text=True).stdout.strip()
    br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
    orig = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True).stdout.split()
    orph = open("ORPHANS").read().strip() if os.path.exists("ORPHANS") else "0"
    code = 0 if orph == "0" else 2
    with open(out, "w") as fh:
        fh.write("argv %s\n" % json.dumps(sys.argv[1:]))
        fh.write("history %s branch %s python %s inside %s cwd %s remotes %s\n"
                 % (hist, br, shutil.which("python"), os.environ.get("COVENANT_PREPUSH_INSIDE"), os.getcwd(),
                    ",".join(orig)))
        fh.write("\n  VERDICT\n  suites not clean    0\n  orphaned on disk    %s\n  runner list absent  0\n" % orph)
        fh.write("  RESULT: %s\n" % ("PASS. ok" if orph == "0" else "INCOMPLETE. Nothing failed"))
    with open(os.path.splitext(out)[0] + ".results.json", "w") as fh:
        json.dump({"suites": [{"suite": "test_x.py", "state": "ok"}], "in_place": [], "exit_code": code}, fh)
    sys.exit(code)
'''


def part_end_to_end(tmp):
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    git(repo, "init", "-q")
    for n, body in (("covenant_one.py", STUB_RUNNER), ("test_x.py", "print('x')\n"), ("requirements.txt", "")):
        with open(os.path.join(repo, n), "w", encoding="utf-8") as fh:
            fh.write(body)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "one")
    with open(os.path.join(repo, "test_x.py"), "a", encoding="utf-8") as fh:
        fh.write("print('again')\n")
    git(repo, "commit", "-q", "-am", "two")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")        # origin's branch, as a fetch leaves it
    git(repo, "checkout", "-q", "-b", "side")
    sha = git(repo, "rev-parse", "HEAD").stdout.strip()
    state = os.path.join(tmp, "state")
    quiet = lambda *_a: None                                                    # noqa: E731
    res = P.linux_run(repo, sha, "side", "selected", ["test_x.py"], state=state, say=quiet)
    text = open(res["transcript"], encoding="utf-8").read() if res.get("transcript") else ""
    check("PP1h end to end: a green tree runs and is not red", res.get("status") == "ran" and res.get("red") == [], res)
    check("PP1h ...the changed suite is handed to --only", '"--only", "test_x.py"' in text, text[:200])
    check("PP1h ...in a clone WITH its history and its branch (what actions/checkout fetch-depth 0 gives)",
          "history 2 branch side" in text, text[:300])
    check("PP1h ...whose remote branches are ORIGIN's, not this clone's local ones", "origin/main" in text
          and "origin/side" not in text, text[:400])
    check("PP1h ...in a folder of its own for this run", "%strees%s" % (os.sep, os.sep) in text or "/trees/" in text,
          text[:400])
    check("PP1h ...with the guard's marker set, so nothing inside recurses", "inside 1" in text, text[:300])
    if os.name == "posix":
        shim = os.path.join(state, "bin", "python")
        check("PP1h ...and `python` on PATH is the guard's own shim, first", "python %s " % shim in text, text[:300])
    else:
        not_run("PP1h `python` on PATH is the shim", "the shim is made on Linux only")
    with open(os.path.join(repo, "ORPHANS"), "w", encoding="utf-8") as fh:
        fh.write("1  -> test_y.py\n")
    git(repo, "add", "ORPHANS")
    git(repo, "commit", "-q", "-m", "three")
    sha2 = git(repo, "rev-parse", "HEAD").stdout.strip()
    res2 = P.linux_run(repo, sha2, "side", "selected", ["ORPHANS"], state=state, say=quiet)
    check("PP1h end to end the other way: the same tree with an orphan is red",
          res2.get("status") == "ran" and any("orphaned on disk 1" in r for r in res2.get("red", [])), res2)
    with open(os.path.join(repo, "SLEEP"), "w", encoding="utf-8") as fh:
        fh.write("1\n")
    git(repo, "add", "SLEEP")
    git(repo, "commit", "-q", "-m", "four")
    sha3 = git(repo, "rev-parse", "HEAD").stdout.strip()
    res4 = P.linux_run(repo, sha3, "side", "selected", ["SLEEP"], state=state, say=quiet, timeout=3)
    check("PP1h a runner past its time limit is NOT RUN -- UNMEASURED, never red",
          res4.get("status") == "not_run" and res4.get("red") == [] and "UNMEASURED" in res4.get("reason", ""), res4)
    runs = os.listdir(os.path.join(state, "runs")) if os.path.isdir(os.path.join(state, "runs")) else []
    trees = os.listdir(os.path.join(state, "trees")) if os.path.isdir(os.path.join(state, "trees")) else []
    check("PP1h every transcript is kept, none overwritten, and each run's clone is removed after",
          len(runs) == 3 and trees == [], (runs, trees))
    res3 = P.linux_run(repo, "c" * 40, "side", "selected", ["test_x.py"], state=state, say=quiet)
    check("PP1h a commit the mirror cannot fetch is NOT RUN, with the reason, never green",
          res3.get("status") == "not_run" and "fetched" in res3.get("reason", ""), res3)


def part_hook(tmp):
    src = os.path.join(HERE, "ops", "pre-push.opsec")
    body = open(src, encoding="utf-8").read()
    i_ops = body.find("python \"$tool\" --pre-push")
    check("PP1i the hook runs the Linux stage, and only after opsec",
          0 < i_ops < body.find("python \"$lt\" --pre-push") and '[ "$rc" -eq 0 ] || exit $rc' in body)
    pc = open(os.path.join(HERE, "ops", "post-commit.autosync"), encoding="utf-8").read()
    check("PP1i the post-commit report names the Linux guard's refusal and its reasons, not 'offline'",
          "REFUSED by the Linux pre-push guard" in pc and "prepush-linux: (RED|REFUSED)" in pc)
    if not shutil.which("sh") or not shutil.which("python"):
        # the hook calls `python`, as CI's runner and the guard's own Linux run (its shim) provide
        not_run("PP1i the real hook through sh", "no sh, or no `python` on PATH, on this machine")
        return
    bare = os.path.join(tmp, "bare.git")
    git(tmp, "init", "-q", "--bare", bare)
    hk = os.path.join(tmp, "hk")
    git(tmp, "init", "-q", hk)
    git(hk, "remote", "add", "origin", bare)
    os.makedirs(os.path.join(hk, "tools"))
    mark = os.path.join(tmp, "linux_ran")
    with open(os.path.join(hk, "tools", "opsec_scan.py"), "w", encoding="utf-8") as fh:
        fh.write("import os, sys\nsys.stdin.read()\nsys.exit(int(os.environ.get('PP1_OPSEC_RC', '0')))\n")
    with open(os.path.join(hk, "a.md"), "w", encoding="utf-8") as fh:
        fh.write("a\n")
    git(hk, "add", "-A")
    git(hk, "commit", "-q", "-m", "a")
    hook = os.path.join(hk, ".git", "hooks", "pre-push")
    shutil.copyfile(src, hook)
    os.chmod(hook, 0o755)
    p = git(hk, "push", "-q", "origin", "main")
    check("PP1i where the Linux tool is absent the hook stands down: the push goes through and says NOT RUN",
          p.returncode == 0 and "prepush-linux: NOT RUN" in p.stderr, (p.returncode, p.stderr[-300:]))
    with open(os.path.join(hk, "tools", "prepush_linux.py"), "w", encoding="utf-8") as fh:
        fh.write("import sys\nopen(%r, 'w').write(sys.stdin.read())\nprint('prepush-linux: RED (stub)')\n"
                 "sys.exit(1)\n" % mark)
    with open(os.path.join(hk, "b.md"), "w", encoding="utf-8") as fh:
        fh.write("b\n")
    git(hk, "add", "-A")
    git(hk, "commit", "-q", "-m", "b")
    p = git(hk, "push", "-q", "origin", "main")
    got = open(mark, encoding="utf-8").read() if os.path.isfile(mark) else ""
    check("PP1i a red Linux stage REFUSES the push", p.returncode != 0, (p.returncode, p.stderr[-300:]))
    check("PP1i ...and it was handed git's ref lines (both guards read them)", "refs/heads/main" in got, got[:200])
    if os.path.exists(mark):
        os.remove(mark)
    env = clean_env()
    env["PP1_OPSEC_RC"] = "1"
    p = git(hk, "push", "-q", "origin", "main", env=env)
    check("PP1i when opsec refuses, the push is refused and the Linux stage never runs",
          p.returncode != 0 and not os.path.exists(mark), (p.returncode, os.path.exists(mark)))


def main():
    tmp = tempfile.mkdtemp(prefix="pp1_")
    try:
        part_parse()
        part_ci_state()
        part_verdict()
        part_select(tmp)
        part_imports(tmp)
        part_decision(tmp)
        part_end_to_end(tmp)
        part_hook(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    passed, total = sum(_results), len(_results)
    print(f"\nPP1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
