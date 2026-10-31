#!/usr/bin/env python3
"""tools/prepush_linux.py -- before a push, the suites it touches run on LINUX, in a clean clone of the pushed commit.

WHY (A392, 2026-10-31; the A171/A232 shape for the third time). 97b676b went out green on this PC and red on
public CI: H1 read this PC's own Startup folder, GS1 imported numpy, which requirements.txt does not declare.
Its fix, 943b809, went out and CI was red again: four suites and two verifiers were in no runner ("orphaned on
disk 6"). The commit-time stage check (tools/stage_check.py) had run H1 and GS1 and passed them -- on Windows,
where the Startup folder and numpy both exist -- and it never asks the coverage question. A232's guard, read the
remote run after every push, caught both, but only after they were public. Rule 10: a forgotten step gets a guard
where it is forgotten, and the step was "run what CI runs, where CI runs it, before the push".

WHAT IT DOES. ops/pre-push.opsec calls this after the opsec guard passes. For every branch being pushed (deletions
and tags skipped: CI runs on branch pushes only), on Linux -- through WSL from Windows, directly on a Linux host:
  1. the pushed commit is fetched into a mirror (~/.covenant_prepush/mirror.git, locked while it is written) whose
     branches are origin's as this clone last saw them, plus its tags, pruned; then cloned into a folder of its own
     for this run, with its history and the branch named -- what actions/checkout with fetch-depth 0 gives;
  2. `python` is on PATH (a shim to this python3), because CI's runner has one and hooks call it;
  3. `python covenant_one.py --ci` runs in that clone, the pushed commit's own runner, --only the suites the push
     touches: the registered suites it changes, the suites that read its published Markdown or walk the tree for
     its extensions (stage_check's rules, reused, never copied), and the suites that import -- directly or through
     other modules of the tree -- a module it changes. With none, --check: the coverage and integrity phases still
     run, and they are what caught "orphaned on disk 6". The WHOLE sweep runs instead when public CI on the
     branch's old tip is red, or when this guard let that tip through unmeasured or on his override, because a
     selection measures what changed and an inherited red is not what changed. COVENANT_PREPUSH_FULL=1 forces it;
  4. the transcript and its results.json are kept, never overwritten: ~/.covenant_prepush/runs/<utc>_<sha7>_<mode>/.
     The run's clone is removed after; it is reproducible from its sha, the transcripts are not.
  The same commit with the same selection reuses a verdict from the last six hours (the post-commit hook pushes
  one commit as main, then pending/<sha>, then sentinel-witness; one measurement serves all three).

WHAT REFUSES THE PUSH -- every outcome that makes covenant_one exit non-zero, which is what turns CI red, read from
the runner's own results.json and its VERDICT block (never from the first "RESULT:" in the transcript: a failing
suite's echoed lines can carry those words): a suite FAIL, TIMEOUT, NO RESULT or ERROR; a folder-integrity FAIL or
ABSENT; a suite unmeasured; orphaned, absent or not-shipped suites; a declared dependency the runner cannot import
although it is installed here (CI cannot import it either); an unguarded import, in a file the run executes, of a
package installed here that requirements.txt neither declares nor pulls in (GS1/numpy); and, as a backstop, any
non-zero exit whose cause none of those names. ONE thing is excused, because it is this machine's and not the
code's: a declared dependency that is not installed HERE (eth-account, on this PC's WSL). A suite that fails with
that package's ModuleNotFoundError in its own output is UNMEASURED here, said, never passed. The commit stays local
and nothing is lost. COVENANT_PREPUSH_ALLOW=1 is his, for one push: the check still runs and reports, the push goes
through, and the override is logged to ops/prepush_overrides.jsonl (gitignored).

WHAT IT CANNOT SEE, said plainly (rule 9):
  - CI's PACKAGES. CI installs exactly requirements.txt; this Linux has what it has. A package this machine has and
    CI will not is caught only where the import is written in a file the run executes; one built at run time
    (importlib with a computed name) is not read. "Pulled in" is judged from the metadata installed HERE.
  - CI's TOOLS and INTERPRETERS. CI runs 3.11 and 3.12 on ubuntu-latest, which has pwsh; this runs the python3 it
    finds and, on this PC's WSL, has no pwsh -- so V1's PowerShell half (verify.ps1, check.ps1) is unmeasured here
    and a push touching a .ps1 file is told so.
  - The selection's reach: a suite that reads a changed file through a path built at run time, or imports a module
    under a computed name. The whole sweep (COVENANT_PREPUSH_FULL=1) has no such gap.
  - An inherited red when GitHub cannot be asked (offline, rate-limited): the base is UNKNOWN, said, and the push
    is measured on what it changes.
  - Without Linux (no WSL, no python3 inside it), or past its time limit, it says NOT RUN and lets the push through:
    an unmeasured push is named, never blocked by a machine's missing tool and never read as a pass.

    python tools/prepush_linux.py --pre-push <remote> <url>  < (git's ref lines)    # what the hook runs
    python tools/prepush_linux.py --run [--full] [SHA] [--since REV]                # by hand, HEAD by default
      (the paths are SHA's commits the remote lacks, or with --since those in REV..SHA)
"""
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(HERE, "tools")
OVERRIDES = os.path.join(HERE, "ops", "prepush_overrides.jsonl")
LEDGER = os.path.join(HERE, "ops", "prepush_linux.jsonl")     # every verdict, gitignored; reuse and the base rule
ZERO = "0" * 40
_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
INSIDE = "COVENANT_PREPUSH_INSIDE"          # set inside the Linux run: a suite's scratch push never recurses
RESULT_TAG = "PREPUSH-RESULT "
TIMEOUT = {"selected": 1500, "full": 2700}  # seconds for the runner; the whole sweep is ~10 min on Linux here
REUSE_S = 6 * 3600
BAD = ("FAIL", "TIMEOUT", "NO RESULT")


# ---------------------------------------------------------------- git's lines and the push's population

def parse_lines(lines):
    """[(local_ref, local_sha, remote_ref, remote_sha)] from git's pre-push stdin, branches only. A deletion (local
    sha all zero) pushes no commit; a tag push runs no CI (covenant.yml triggers on branches); a malformed line is
    dropped too (the opsec guard, which runs first, refuses it)."""
    out = []
    for ln in lines:
        parts = ln.split()
        if len(parts) != 4 or not (_SHA.match(parts[1]) and _SHA.match(parts[3])):
            continue
        if set(parts[1]) == {"0"} or parts[2].startswith("refs/tags/"):
            continue
        out.append(tuple(parts))
    return out


def _git(args, cwd=HERE, env=None, timeout=120):
    return subprocess.run(["git", "-c", "safe.directory=*"] + list(args), cwd=cwd, capture_output=True,
                          encoding="utf-8", errors="replace", env=env, timeout=timeout)


def _plain(name):
    return bool(name and re.match(r"^[A-Za-z0-9._-]+$", name))


def outgoing_paths(local_sha, remote_sha, remote_name, git=_git):
    """Every path touched by the commits this push brings: reachable from local_sha, not from the remote's branches
    this clone knows, nor from the ref's old tip. Both sides of a rename (--no-renames); merges by each parent (-m)."""
    args = ["log", "--name-only", "--format=", "--no-renames", "-m", local_sha, "--not",
            "--remotes=%s" % remote_name if _plain(remote_name) else "--remotes"]
    if remote_sha and set(remote_sha) != {"0"} and git(["cat-file", "-e", remote_sha + "^{commit}"]).returncode == 0:
        args.append(remote_sha)
    p = git(args)
    return sorted({ln.strip() for ln in (p.stdout or "").splitlines() if ln.strip()})


def base_of(local_sha, remote_sha, remote_name, git=_git):
    """The commit this push builds on, as CI last saw it: the ref's old tip, or for a new branch its merge-base with
    the remote's main."""
    if remote_sha and set(remote_sha) != {"0"} and git(["cat-file", "-e", remote_sha + "^{commit}"]).returncode == 0:
        return remote_sha
    r = remote_name if _plain(remote_name) else "origin"
    p = git(["merge-base", local_sha, "refs/remotes/%s/main" % r])
    return (p.stdout or "").strip() or None


def _repo_slug(url):
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url or "")
    return (m.group(1), m.group(2)) if m else None


def ci_state(sha, url, fetch=None):
    """'green' | 'red' | 'unknown' -- public CI's sweep jobs on this commit, asked of GitHub's public API."""
    slug = _repo_slug(url)
    if not sha or not slug:
        return "unknown"
    if fetch is None:
        import urllib.request

        def fetch(u):
            req = urllib.request.Request(u, headers={"Accept": "application/vnd.github+json",
                                                     "User-Agent": "covenant-prepush"})
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read().decode("utf-8"))
    try:
        runs = fetch("https://api.github.com/repos/%s/%s/commits/%s/check-runs?per_page=100" % (slug + (sha,)))
    except Exception:                                            # noqa: BLE001 -- offline is UNKNOWN, said
        return "unknown"
    sweeps = [c for c in (runs or {}).get("check_runs", []) if str(c.get("name", "")).startswith("sweep")]
    if not sweeps or any(c.get("status") != "completed" for c in sweeps):
        return "unknown"
    return "green" if all(c.get("conclusion") == "success" for c in sweeps) else "red"


def mode_for(env, base_state=None, base_unmeasured=False):
    """(mode, why). Full when forced, when the base is red on CI, or when this guard never measured it green."""
    if str(env.get("COVENANT_PREPUSH_FULL", "")) == "1":
        return "full", "COVENANT_PREPUSH_FULL=1"
    if base_state == "red":
        return "full", "public CI is red on the commit this push builds on; a selection would not see an inherited red"
    if base_unmeasured:
        return "full", "the commit this push builds on went out unmeasured or on an override"
    return "selected", None


# ---------------------------------------------------------------- what the push touches, in the pushed tree

def _imports_of(src):
    """Every dotted import name and each part of it, from a module's source; None when it does not parse."""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return None
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            names.add(n.module)
            names |= {"%s.%s" % (n.module, a.name) for a in n.names}
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "import_module"
              and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
            names.add(n.args[0].value)
    return {p for nm in names for p in nm.split(".")}


def reached(modules, graph, limit=8):
    """The changed modules plus every module of the tree that imports one of them, through up to `limit` hops.
    graph: {module_stem: set of names it imports}."""
    seen = set(modules)
    frontier = set(modules)
    for _ in range(limit):
        nxt = {m for m, imps in graph.items() if m not in seen and imps & frontier}
        if not nxt:
            break
        seen |= nxt
        frontier = nxt
    return seen


def importers(modules, population, read, graph=None):
    """{suite: why} -- suites whose code imports one of these modules, directly or (with graph) through modules of
    the tree that do. Any dotted part matches: suites put tools/ and the root on sys.path."""
    reach = reached(set(modules), graph) if graph else set(modules)
    out = {}
    for t in population:
        try:
            parts = _imports_of(read(t))
        except (OSError, UnicodeDecodeError):
            continue
        if not parts:
            continue
        direct = sorted(m for m in modules if m in parts)
        via = sorted(m for m in reach - set(modules) if m in parts)
        if direct:
            out[t] = "imports " + ", ".join(direct)
        elif via:
            out[t] = "imports %s, which reaches a changed module" % ", ".join(via[:3])
    return out


def tree_graph(tree):
    """{stem: imported names} for every .py of a tree (.git pruned)."""
    g = {}
    for root, dirs, files in os.walk(tree):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        for n in files:
            if n.endswith(".py"):
                try:
                    parts = _imports_of(open(os.path.join(root, n), encoding="utf-8").read())
                except (OSError, UnicodeDecodeError):
                    parts = None
                if parts:
                    g.setdefault(os.path.splitext(n)[0], set()).update(parts)
    return g


def select(paths, population, read, say=print, graph=None):
    """The suites this push runs, each once, in this order: the registered suites it changes, the suites that read
    its published Markdown, the suites that walk the tree for its extensions, the suites that import a module it
    changes (directly, or through the tree's own modules when graph is given)."""
    sys.path.insert(0, TOOLS)
    import stage_check as SC                                     # the commit-time rules, reused (rule: never copied)
    pop = list(population)
    names = [p for p in paths if p in pop]                       # registered suites the push touches, any prefix
    docs = SC.staged_docs(run=lambda: "\0".join(paths))
    ran = SC.selection(names, docs, readers=lambda d: SC.doc_readers(d, population=pop, read=read), say=say,
                       paths=paths, walkers=lambda e: SC.walker_readers(e, population=pop, read=read))
    mods = sorted({os.path.splitext(os.path.basename(p))[0] for p in paths if p.endswith(".py")})
    imp = {t: why for t, why in importers(mods, pop, read, graph).items() if t not in ran}
    if imp:
        say("prepush-linux: also running the %d suite(s) that import a changed module: %s"
            % (len(imp), "; ".join("%s (%s)" % (t, w) for t, w in sorted(imp.items())[:40])
               + (" ..." if len(imp) > 40 else "")))
    return [t for t in ran if t in pop] + sorted(imp)


# ---------------------------------------------------------------- reading the runner's verdict

def _verdict_block(text):
    """The text after the LAST VERDICT rule -- the only part that is the runner's own verdict."""
    i = text.rfind("\n  VERDICT\n")
    return text[i:] if i >= 0 else None


def _count(block, label):
    m = re.search(r"^\s*%s\s+(\d+)" % re.escape(label), block, re.M)
    return int(m.group(1)) if m else None


def _listed(block, label):
    m = re.search(r"^\s*%s\s+\d+\s+->\s*(.+)$" % re.escape(label), block, re.M)
    return m.group(1).strip()[:300] if m else ""


def _echo(text, suite):
    """The '        |' lines the runner echoed under a suite's row (its failing lines and its tail)."""
    m = re.search(r"^    %s\s+\S.*\n((?:        \|.*\n?)*)" % re.escape(suite), text, re.M)
    return m.group(1) if m else ""


def verdict(text, results=None, missing_here=(), exit_code=None):
    """(red, warn, unmeasured_here) from a covenant_one --ci transcript and its results.json.

    missing_here: {import_name: dist} of declared dependencies NOT installed on this machine. A failing suite whose
    own echoed output names one of them in a ModuleNotFoundError is this machine's, not the code's: unmeasured here.
    Everything else that makes the runner exit non-zero is red, with a backstop for a cause nothing here names."""
    red, warn, here = [], [], []
    block = _verdict_block(text)
    if block is None:
        return ["the runner wrote no VERDICT (it crashed or was cut off)"], warn, here
    res = re.findall(r"RESULT: (PASS|FAIL|INCOMPLETE)", block)
    if not res:
        return ["the runner wrote no RESULT line (it crashed or was cut off)"], warn, here
    if results and isinstance(results.get("suites"), list):
        bad = [s["suite"] for s in results["suites"] if s.get("state") in BAD or str(s.get("state")).startswith("ERROR")]
        unmeasured = [s["suite"] for s in results["suites"] if s.get("state") in ("ABSENT", "NOTRUN")]
        ip = [(e.get("name"), str(e.get("state"))) for e in results.get("in_place", [])]
        exit_code = results.get("exit_code", exit_code)
    else:
        bad = [s.strip() for s in _listed(block, "suites not clean").split(",") if s.strip()]
        unmeasured = [s.strip() for s in _listed(block, "suites unmeasured").split(",") if s.strip()]
        line = re.search(r"^\s*folder integrity\s+(.+)$", block, re.M)
        ip = [tuple(x.split("=", 1)) for x in (line.group(1).split(", ") if line else []) if "=" in x]
    for s in bad:
        echo = _echo(text, s)
        hit = [mod for mod in missing_here if re.search(r"No module named '%s(?:\.|')" % re.escape(mod), echo)]
        if hit:
            here.append(s)
            warn.append("%s failed on ModuleNotFoundError for %s, declared and not installed HERE -- UNMEASURED "
                        "here, not passed" % (s, ", ".join(missing_here[h] for h in hit)))
        else:
            red.append("%s did not pass (%s)" % (s, (re.search(r"^    %s\s+(\S+(?: RESULT)?)" % re.escape(s), text, re.M)
                                                    or [None, "not clean"])[1]))
    for name, st in ip:
        if st.startswith("FAIL") or st == "ABSENT":
            red.append("folder integrity %s=%s" % (name, st))
    if unmeasured:
        red.append("suites unmeasured %d -- %s (CI reads them INCOMPLETE)" % (len(unmeasured), ", ".join(unmeasured)[:300]))
    for label, why in (("orphaned on disk", "on disk, in no runner"), ("runner list absent", "named, not in the commit"),
                       ("listed but NOT SHIPPED", "kept out of the delivery by an ignore rule")):
        n = _count(block, label)
        if n:
            red.append("%s %d (%s) -- %s" % (label, n, why, _listed(block, label)))
    for dist in re.findall(r"MISSING: (\S+) is declared in requirements.txt", text):
        if dist in missing_here.values():
            warn.append("declared dependency %s is not installed HERE -- the suites needing it are UNMEASURED here, "
                        "not passed" % dist)
        else:
            red.append("declared dependency %s is installed here, yet the runner cannot import it -- CI will read it "
                       "MISSING too (preflight_deps' import name for it?)" % dist)
    explained = bool(here) or any(w.startswith("declared dependency") for w in warn)
    if exit_code not in (0, None) and not red and not explained:
        red.append("the runner exited %s, and nothing above names why -- read the transcript" % exit_code)
    if res[-1] == "INCOMPLETE" and not red:
        warn.append("RESULT: INCOMPLETE -- every cause is this machine's, named above")
    return red, warn, here


def _norm(s):
    return re.sub(r"[-_.]+", "-", s).lower()


def declared_closure(req_text, metadata=None):
    """requirements.txt's distributions and everything they pull in, as installed here (normalized names).
    CI installs the same names, so a package in this set is one CI has too; extras are not followed."""
    if metadata is None:
        from importlib import metadata
    todo = [_norm(re.split(r"[\s<>=!~;\[]", ln.strip(), maxsplit=1)[0]) for ln in req_text.splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    seen = set()
    while todo:
        d = todo.pop()
        if d in seen:
            continue
        seen.add(d)
        try:
            reqs = metadata.requires(d) or []
        except Exception:                                        # noqa: BLE001 -- not installed here: no children
            reqs = []
        for r in reqs:
            if "extra ==" in r.replace('"', "").replace("'", ""):
                continue
            todo.append(_norm(re.split(r"[\s<>=!~;\[(]", r.strip(), maxsplit=1)[0]))
    return seen


def _catches_import_error(try_node):
    """True when a try's handlers catch ImportError (or anything broader)."""
    for h in try_node.handlers:
        if h.type is None:
            return True
        names = [t.id if isinstance(t, ast.Name) else t.attr if isinstance(t, ast.Attribute) else ""
                 for t in (h.type.elts if isinstance(h.type, ast.Tuple) else [h.type])]
        if set(names) & {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}:
            return True
    return False


def undeclared_imports(files, read, closure, local, packages_of):
    """[(file, module, distribution)] -- an UNGUARDED import, in a file this run executes, of a third-party package
    installed here whose distribution requirements.txt does not bring in. That is GS1/numpy: it imports here and
    raises ImportError on CI. A module not installed here at all fails here too, so it is not this check's to name."""
    std = set(getattr(sys, "stdlib_module_names", ())) | set(sys.builtin_module_names)
    out = []
    for f in files:
        try:
            tree = ast.parse(read(f))
        except (OSError, SyntaxError, ValueError, UnicodeDecodeError):
            continue

        def visit(node, guarded):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and not (isinstance(node, ast.ImportFrom) and node.level):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for m in mods:
                    top = m.split(".")[0]
                    if not top or top in std or top in local or guarded:
                        continue
                    dists = [_norm(d) for d in packages_of.get(top, [])]
                    if dists and not set(dists) & closure:
                        out.append((f, top, dists[0]))
            if isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
                # only the try BODY is guarded; an import in a handler, else or finally raises like any other
                for child in node.body:
                    visit(child, guarded or _catches_import_error(node))
                for child in node.handlers + node.orelse + node.finalbody:
                    visit(child, guarded)
                return
            for child in ast.iter_child_nodes(node):
                visit(child, guarded)
        visit(tree, False)
    return sorted(set(out))


def _declared_import_names(tree):
    """{dist: import name} for requirements.txt, by preflight_deps' own IMPORT_NAME table when the tree has it."""
    table = {}
    p = os.path.join(tree, "preflight_deps.py")
    try:
        for n in ast.walk(ast.parse(open(p, encoding="utf-8").read())):
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "IMPORT_NAME" for t in n.targets):
                table = ast.literal_eval(n.value)
    except (OSError, SyntaxError, ValueError):
        pass
    req = os.path.join(tree, "requirements.txt")
    text = open(req, encoding="utf-8").read() if os.path.isfile(req) else ""
    dists = [re.split(r"[\s<>=!~;\[]", ln.strip(), maxsplit=1)[0] for ln in text.splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    return {d: table.get(d, d.replace("-", "_")) for d in dists}


# ---------------------------------------------------------------- the Linux side

class _Lock:
    """An exclusive lock on a file, on posix; elsewhere (the PP1 run on Windows) a no-op, said in the docstring."""
    def __init__(self, path):
        self.path, self.fh = path, None

    def __enter__(self):
        self.fh = open(self.path, "a")
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX)
        except ImportError:
            pass
        return self

    def __exit__(self, *_a):
        self.fh.close()


def _rmtree(path):
    # git's pack files are read-only, and Windows will not remove a read-only file (PP1h, measured).
    def _writable(fn, p, _exc):
        os.chmod(p, 0o700)
        fn(p)
    shutil.rmtree(path, **({"onexc": _writable} if sys.version_info >= (3, 12) else {"onerror": _writable}))


def _run_bounded(cmd, cwd, env, timeout):
    """(returncode or None on timeout). The runner and every suite it started are killed together on timeout."""
    kw = {"start_new_session": True} if os.name == "posix" else {}
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    try:
        return p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                import signal
                os.killpg(p.pid, signal.SIGKILL)
            else:
                p.kill()
        except OSError:
            pass
        p.wait()
        return None


def linux_run(repo, sha, branch, mode, paths, state=None, say=print, timeout=None, remote="origin"):
    """Clone sha fresh from repo, run its own covenant_one --ci there, return a result dict. Never raises."""
    t0 = time.time()
    state = state or os.path.join(os.path.expanduser("~"), ".covenant_prepush")
    res = {"status": "not_run", "sha": sha, "branch": branch, "mode": mode, "red": [], "warn": [], "selected": []}
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env[INSIDE] = "1"
    tree = None
    try:
        os.makedirs(state, exist_ok=True)
        mirror = os.path.join(state, "mirror.git")
        tree = os.path.join(state, "trees", "%s_%s_%d" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), sha[:7],
                                                         os.getpid()))
        os.makedirs(os.path.dirname(tree), exist_ok=True)
        with _Lock(os.path.join(state, "mirror.lock")):
            if not os.path.isdir(mirror):
                _git(["init", "-q", "--bare", mirror], cwd=state, env=env)
            # origin's branches become the mirror's (so the clone's refs/remotes/origin/* are origin's, as CI's
            # checkout has them), every local branch is kept apart under refs/local/* (its objects carry the
            # pushed commit), and tags come too; all pruned.
            rm = remote if _plain(remote) else "origin"
            f = _git(["fetch", "-q", "--force", "--prune", "--tags", repo,
                      "+refs/remotes/%s/*:refs/heads/*" % rm, "^refs/remotes/%s/HEAD" % rm,
                      "+refs/heads/*:refs/local/*"], cwd=mirror, env=env, timeout=600)
            if _git(["cat-file", "-e", sha + "^{commit}"], cwd=mirror, env=env).returncode != 0:
                res["reason"] = ("the pushed commit could not be fetched into the mirror: %s"
                                 % (f.stderr or "").strip()[:200])
                return res
            cl = _git(["clone", "-q", "--no-checkout", mirror, tree], cwd=state, env=env, timeout=600)
        if cl.returncode != 0:
            res["reason"] = "clone of the mirror failed: %s" % (cl.stderr or "").strip()[:200]
            return res
        co = _git(["checkout", "-q", "--force", "-B", branch or "prepush", sha], cwd=tree, env=env)
        if co.returncode != 0:
            res["reason"] = "checkout of %s failed: %s" % (sha[:7], (co.stderr or "").strip()[:200])
            return res
        if os.name == "posix":
            bindir = os.path.join(state, "bin")
            os.makedirs(bindir, exist_ok=True)
            shim = os.path.join(bindir, "python")
            if os.path.islink(shim) and os.readlink(shim) != sys.executable:
                os.unlink(shim)                                  # a link, re-pointed; nothing kept is lost
            if not os.path.lexists(shim):
                os.symlink(sys.executable, shim)
            env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
        py = sys.executable
        q = subprocess.run([py, "-c", "import json, covenant_one as C; print(json.dumps("
                            "[[n for n, _, _ in C.SUITES], [n for n, _, _ in C.IN_PLACE]]))"],
                           cwd=tree, capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=120)
        try:
            sweep, in_place = json.loads((q.stdout or "").strip().splitlines()[-1])
        except (ValueError, IndexError):
            sweep = sorted(n for n in os.listdir(tree) if n.startswith("test_") and n.endswith(".py"))
            in_place = []
            res["warn"].append("the pushed runner's suite list could not be read; selected from every test_*.py")
        read = lambda t: open(os.path.join(tree, t), encoding="utf-8").read()     # noqa: E731
        graph = tree_graph(tree)
        cmd = [py, "covenant_one.py", "--ci", "--out", "PREPUSH_RUN.txt"]
        if mode == "selected":
            # IN_PLACE suites run in the integrity phase of every run, --only or not; naming them to --only as
            # well would read them as unmeasured in the sweep phase.
            sel = [t for t in select(paths, sweep + in_place, read, say=say, graph=graph) if t not in in_place]
            res["selected"] = sel
            cmd += (["--only"] + sel) if sel else ["--check"]
        if any(p.lower().endswith(".ps1") for p in paths) and not shutil.which("pwsh"):
            res["warn"].append("this push touches a .ps1 file and this Linux has no pwsh: V1's PowerShell half runs "
                               "on CI and is UNMEASURED here")
        say("prepush-linux: %s on %s (%s), python %s -- %s"
            % (sha[:7], branch, mode, sys.version.split()[0],
               ("%d suite(s): %s" % (len(res["selected"]), " ".join(res["selected"][:60])
                                     + (" ..." if len(res["selected"]) > 60 else ""))) if res["selected"]
               else "the whole sweep" if mode == "full" else "no suite touched; coverage and integrity only"))
        limit = timeout or TIMEOUT[mode]
        rc = _run_bounded(cmd, tree, env, limit)
        keep = os.path.join(state, "runs", "%s_%s_%s" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), sha[:7], mode))
        os.makedirs(keep, exist_ok=True)
        for n in ("PREPUSH_RUN.txt", "PREPUSH_RUN.results.json"):
            if os.path.isfile(os.path.join(tree, n)):
                shutil.copyfile(os.path.join(tree, n), os.path.join(keep, n))
        res["transcript"] = os.path.join(keep, "PREPUSH_RUN.txt")
        if rc is None:
            res["reason"] = ("the runner did not finish in %ds -- UNMEASURED, not red (CI's own job limit is 45 min); "
                             "its partial transcript is kept" % limit)
            return res
        tpath = os.path.join(tree, "PREPUSH_RUN.txt")
        text = open(tpath, encoding="utf-8", errors="replace").read() if os.path.isfile(tpath) else ""
        rpath = os.path.join(tree, "PREPUSH_RUN.results.json")
        try:
            results = json.load(open(rpath, encoding="utf-8")) if os.path.isfile(rpath) else None
        except ValueError:
            results = None
        from importlib import metadata
        missing_here = {}
        for dist, mod in _declared_import_names(tree).items():
            try:
                metadata.version(dist)
            except metadata.PackageNotFoundError:
                missing_here[mod] = dist
        res["status"] = "ran"
        res["runner_exit"] = rc
        red, warn, here = verdict(text, results, missing_here, exit_code=rc)
        res["red"] += red
        res["warn"] += warn
        res["unmeasured_here"] = here
        block = _verdict_block(text) or ""
        rl = re.findall(r"RESULT: .*", block)
        res["result_line"] = rl[-1].strip() if rl else None
        # The GS1/numpy shape: an unguarded import, in a file this run executes, of a package CI will not install.
        # The files: the selected suites (all registered ones for the whole sweep), and the changed modules that
        # some selected suite reaches -- a changed file nothing runs cannot raise on CI.
        req = os.path.join(tree, "requirements.txt")
        closure = declared_closure(open(req, encoding="utf-8").read() if os.path.isfile(req) else "", metadata)
        local = set(graph) | {d for _r, ds, _f in os.walk(tree) for d in ds if d != ".git"}
        suites = res["selected"] if mode == "selected" else sweep
        reach = reached({os.path.splitext(os.path.basename(p))[0] for p in paths if p.endswith(".py")}, graph)
        used = set()
        for s in suites:
            try:
                used |= _imports_of(read(s)) or set()
            except (OSError, UnicodeDecodeError):
                pass
        changed_run = [p for p in paths if p.endswith(".py") and os.path.isfile(os.path.join(tree, p))
                       and os.path.splitext(os.path.basename(p))[0] in (reach & used)]
        for f_, top, dist in undeclared_imports(sorted(set(suites) | set(changed_run)), read, closure, local,
                                                metadata.packages_distributions()):
            res["red"].append("%s imports %s unguarded, and %s is not in requirements.txt nor pulled in by it -- it "
                              "imports here and raises ImportError on CI (the GS1/numpy shape)" % (f_, top, dist))
    except Exception as e:                                       # noqa: BLE001 -- said, never raised into the hook
        res["status"] = "not_run"
        res["reason"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        if tree and os.path.isdir(tree):
            try:
                _rmtree(tree)
            except OSError:
                pass
    return res


# ---------------------------------------------------------------- the Windows (or any) side

def _wsl_path(p):
    p = os.path.abspath(p).replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    return "/mnt/%s/%s" % (m.group(1).lower(), m.group(2)) if m else p


def run_on_linux(sha, branch, mode, paths, say=print, remote="origin"):
    """The result dict, from Linux: this process when it is Linux, WSL's python3 when this is Windows."""
    if sys.platform != "win32":
        return linux_run(HERE, sha, branch, mode, paths, say=say, remote=remote)
    wsl = shutil.which("wsl.exe") or shutil.which("wsl")
    if not wsl:
        return {"status": "not_run", "reason": "this is Windows and WSL is not installed", "red": [], "warn": []}
    payload = json.dumps({"repo": _wsl_path(HERE), "sha": sha, "branch": branch, "mode": mode, "paths": paths,
                          "remote": remote})
    box = {}
    try:
        p = subprocess.Popen([wsl, "-e", "python3", _wsl_path(os.path.abspath(__file__)), "--linux"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             encoding="utf-8", errors="replace")
        p.stdin.write(payload)
        p.stdin.close()

        def pump():
            for ln in p.stdout:
                ln = ln.rstrip("\r\n")
                if ln.startswith(RESULT_TAG):
                    box["result"] = json.loads(ln[len(RESULT_TAG):])
                elif ln.strip():
                    say(ln)
        th = threading.Thread(target=pump, daemon=True)
        th.start()
        th.join(TIMEOUT[mode] + 900)                              # a stalled wsl.exe never hangs the push
        if th.is_alive():
            p.kill()
            return {"status": "not_run", "reason": "WSL did not answer within %ds" % (TIMEOUT[mode] + 900),
                    "red": [], "warn": []}
        p.wait(timeout=30)
    except Exception as e:                                       # noqa: BLE001
        return {"status": "not_run", "reason": "WSL could not be run: %s: %s" % (type(e).__name__, str(e)[:160]),
                "red": [], "warn": []}
    return box.get("result") or {"status": "not_run", "red": [], "warn": [],
                                 "reason": "WSL ran but returned no result (exit %s)" % p.returncode}


def _ledger_rows(path=None):
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh if ln.strip()]
    except (OSError, ValueError):
        return []


def _ledger_add(row, path=None):
    try:
        os.makedirs(os.path.dirname(path or LEDGER), exist_ok=True)
        with open(path or LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass


def _key(sha, mode, sel_paths):
    return hashlib.sha256(json.dumps([sha, mode, sorted(sel_paths)]).encode()).hexdigest()[:16]


def pre_push(stdin_lines, remote_name=None, remote_url=None, env=None, say=print, runner=run_on_linux,
             paths_of=outgoing_paths, base=base_of, ci=ci_state, ledger=None, now=None):
    """0 to let the push through, 1 to refuse."""
    env = os.environ if env is None else env
    if str(env.get(INSIDE, "")) == "1":
        return 0                                                  # a suite's scratch push inside the Linux run
    refs = parse_lines(stdin_lines)
    if not refs:
        return 0
    now = time.time() if now is None else now
    allow = str(env.get("COVENANT_PREPUSH_ALLOW", "")) == "1"
    rows = _ledger_rows(ledger)
    refused = []
    for local_ref, local_sha, remote_ref, remote_sha in refs:
        branch = local_ref[len("refs/heads/"):] if local_ref.startswith("refs/heads/") else "prepush"
        b = base(local_sha, remote_sha, remote_name)
        b_state = ci(b, remote_url) if b else "unknown"
        b_unmeasured = bool(b) and any(r.get("sha") == b and (r.get("allowed") or r.get("status") != "ran")
                                       for r in rows) and not any(r.get("sha") == b and r.get("status") == "ran"
                                                                  and not r.get("red") for r in rows)
        mode, why = mode_for(env, b_state, b_unmeasured)
        if why:
            say("prepush-linux: the whole sweep for %s -- %s" % (local_sha[:7], why))
        elif b_state == "unknown":
            say("prepush-linux: note -- public CI's state on the base %s is UNKNOWN; an inherited red would not be "
                "seen here" % (b[:7] if b else "(none)"))
        paths = paths_of(local_sha, remote_sha, remote_name) if mode == "selected" else []
        key = _key(local_sha, mode, paths)
        hit = [r for r in rows if r.get("key") == key and r.get("status") == "ran" and now - r.get("at", 0) < REUSE_S]
        if hit:
            res = hit[-1]["result"]
            say("prepush-linux: reusing the Linux verdict of %s for this same commit and selection"
                % time.strftime("%H:%M", time.localtime(hit[-1]["at"])))
        else:
            res = runner(local_sha, branch, mode, paths, say=say)
        row = {"at": int(now), "key": key, "sha": local_sha, "ref": remote_ref, "mode": mode,
               "status": res.get("status"), "red": res.get("red", [])[:10], "result": res}
        if res.get("status") != "ran":
            say("prepush-linux: NOT RUN for %s -- %s. This push is UNMEASURED on Linux; read the remote CI run after "
                "it (A232)." % (local_sha[:7], res.get("reason", "no reason given")))
            if not hit:
                _ledger_add(row, ledger)
            continue
        for w in res.get("warn", []):
            say("prepush-linux: note -- %s" % w)
        if res.get("red"):
            for r in res["red"]:
                say("prepush-linux: RED -- %s" % r)
            say("prepush-linux: transcript kept at %s" % res.get("transcript"))
            refused.append((local_sha, res))
            row["allowed"] = allow
        else:
            say("prepush-linux: green on Linux for %s (%s, %.0fs) -- %s"
                % (local_sha[:7], res.get("mode"), res.get("seconds") or 0, res.get("result_line")))
        if not hit:
            _ledger_add(row, ledger)
    if not refused:
        return 0
    if allow:
        os.makedirs(os.path.dirname(OVERRIDES), exist_ok=True)
        with open(OVERRIDES, "a", encoding="utf-8") as fh:
            for sha, res in refused:
                fh.write(json.dumps({"at": int(now), "sha": sha, "red": res.get("red", [])[:10]}) + "\n")
        _ledger_add({"at": int(now), "sha": refused[0][0], "status": "allowed", "allowed": True}, ledger)
        say("prepush-linux: COVENANT_PREPUSH_ALLOW=1 -- let through on his say, and logged")
        return 0
    say("prepush-linux: REFUSED -- public CI would be red for the reason(s) above. Nothing was lost: the commit is "
        "still here. Fix it, commit, and push again. COVENANT_PREPUSH_ALLOW=1 is his, for one push.")
    return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    if "--linux" in argv:                                         # the WSL side: one JSON request on stdin
        req = json.loads(sys.stdin.read())
        res = linux_run(req["repo"], req["sha"], req["branch"], req["mode"], req["paths"],
                        say=lambda m: print(m, flush=True), remote=req.get("remote") or "origin")
        print(RESULT_TAG + json.dumps(res), flush=True)
        return 0
    if "--pre-push" in argv:
        rest = argv[argv.index("--pre-push") + 1:]               # git passes the hook: <remote name> <remote url>
        raw = sys.stdin.read()
        return pre_push(raw.split("\n"), remote_name=(rest[0] if rest else None),
                        remote_url=(rest[1] if len(rest) > 1 else None))
    if "--run" in argv:
        since = argv[argv.index("--since") + 1] if "--since" in argv and argv.index("--since") + 1 < len(argv) else None
        args = [a for a in argv if not a.startswith("--") and a != since]
        sha = _git(["rev-parse", args[0] if args else "HEAD"]).stdout.strip()
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() or "prepush"
        mode = "full" if "--full" in argv else "selected"
        if mode == "full":
            paths = []
        elif since:
            p = _git(["diff", "--name-only", "--no-renames", since, sha])
            paths = sorted({ln.strip() for ln in (p.stdout or "").splitlines() if ln.strip()})
        else:
            paths = outgoing_paths(sha, ZERO, "origin")
        res = run_on_linux(sha, branch, mode, paths)
        print(json.dumps(res, indent=1))
        return 1 if res.get("red") else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
