#!/usr/bin/env python3
"""tools/stage_check.py -- every test file being committed is run where the runner runs it, at commit time.

WHY. "Run it in the staged copy" has been step 4 of adding a test since 2026-09-10 (the staged copy has
no .git, no databases, no keys). It was a note, and notes are forgotten: on 2026-10-03 E12r was checked
only in the working tree, with .git present, and CI went red on the next two pushes (9a1ff52, bb227ca).
Rule 10: a forgotten step gets a guard where it is forgotten. The pre-commit hook calls this.

WHAT IT DOES. For each test_*.py added or changed in the commit: stage the tree exactly as
covenant_one does (covenant_one.stage, then clean_dbs), run the suite there, and print one line per
suite. A failure is said loudly. It NEVER blocks the commit -- the hook's first rule.

WHAT IT DOES NOT SEE, said plainly: the runner's ENVIRONMENT (CI exports variables the working
machine does not), and a fresh clone's lack of hooks and local config. Those are still the full
`python covenant_one.py --ci` on a fresh clone; this catches the .git-less directory, which is the
case that recurred.

PUBLISHED MARKDOWN (A266, 2026-10-06). A commit can turn CI red without carrying a test file:
2f6b184 changed only docs/SENTINEL_WITNESS.md (and a tool), no suite ran at commit time, and both
CI runners failed C4.2 -- the document named a private file and stated account facts without
saying a reader cannot check them. Fixed in b502ba5, after the push. So when a published .md is
staged (any .md not under ops/, private/ or .claude/, deleted and renamed ones included), the
suites that READ published Markdown run too, in the same staged copy. They are found by what
their code does, never by a list (CLAUDE.md rule 2), among the suites the runner registers:
  A. the suite walks the tree (os.walk, os.listdir, rglob, a ** glob, git ls-files) AND filters
     on .md (endswith(".md"), an extension set holding ".md", a "*.md" glob) -- it reads every
     published document;
  B. a string in the suite's code (docstrings excluded) is the staged document's path or file
     name -- it reads that document by name (G1 and G2 read README.md and docs/CONSTITUTION.md
     this way, and walk nothing).
Parsed with ast, not grepped: ".md" in a docstring, or in a fixture name built with +, is not a
filter. What the rule CANNOT see, said plainly: a suite that hands the reading to a module (OS1
reads through tools/opsec_scan.py; the rule reads the suite's own code only); a path built at run
time or read from data; Markdown under ops/, which R1 and A92 do read, so a retracted wording that
comes back through ops/*.md is still caught only by CI; and a .md outside the directories
covenant_one stages (mobile/, phone/ ...), which no staged suite sees here or in CI. Rule B
over-selects -- a fixture named README.md selects its suite -- which costs seconds, never a miss.

TREE WALKERS, ANY EXTENSION (A323, 2026-10-10). A266's shape again, through code and ledgers rather than
Markdown: 63c6747 (A322) added tools/discourse_seat_eval.py and two tracked .jsonl files, carried no
suite that reads them, and both CI runners failed -- A284 FC10 (a tetsu_work.ask caller nobody declared)
and A255 C1 (a tracked .jsonl in neither OUTPUTS nor INPUT_LEDGERS). A266 had fixed its instance's
class for one extension. So rule A is now asked for the extension of EVERY path the commit touches
(added, changed, deleted or renamed -- a deleted file leaves a registry's declaration stale): the
registered suites that walk the tree AND filter on that extension run too. Measured that day over the
runner's 200 suites: 9 walk for .py (about 70 s with A255, R1 alone 42 s, and R1 already runs for most
commits through docs/KNOWN_ISSUES.md), 2 walk for .jsonl. The same blind spots as rule A, said plainly:
a suite that hands its walk or its filter to a module, and a filter built at run time.

    python tools/stage_check.py                 # the staged (index) test files and documents
    python tools/stage_check.py test_x.py       # named files
    python tools/stage_check.py docs/X.md       # the suites that read a named document
"""
import ast
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

#: Markdown under these directories (at any depth) does not trigger the document suites: ops/
#: holds the running system's records (C4 skips it too), private/ is never published, and .claude/
#: is the assistant's. The scope is his call (rule 5), named in the A266 request.
DOC_SKIP = {"ops", "private", ".claude"}


def staged_tests(run=None):
    run = run or (lambda: subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
                                         cwd=HERE, capture_output=True, text=True).stdout)
    return [p for p in run().split() if os.path.basename(p).startswith("test_") and p.endswith(".py") and "/" not in p]


def staged_docs(run=None):
    """Published .md paths in the commit, whatever their status: a deleted or renamed document breaks
    a suite that reads it by name as surely as an edited one (--no-renames lists both sides)."""
    run = run or (lambda: subprocess.run(["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
                                         cwd=HERE, capture_output=True, text=True).stdout)
    return [p for p in run().split("\0") if p.endswith(".md") and not set(p.split("/")[:-1]) & DOC_SKIP]


def runner_suites():
    """The test suites covenant_one runs (SUITES and IN_PLACE) that are on disk here -- CI's population,
    which needs no .git. Tracked suites the runner does not register are never run by CI."""
    try:
        import covenant_one as C1
        names = [n for n, _, _ in C1.SUITES] + [n for n, _, _ in C1.IN_PLACE]
    except Exception:                                            # noqa: BLE001
        return []
    return [n for n in dict.fromkeys(names) if n.startswith("test_") and os.path.isfile(os.path.join(HERE, n))]


def _prose(tree):
    """ids of string constants that are statements -- docstrings -- which describe, never read."""
    return {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}


def _const(n, prose=()):
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in prose else None


def _walks_tree(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            owner = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
            if name in ("walk", "listdir", "scandir") and owner in ("os", ""):      # not ast.walk
                return True
            if name == "rglob":
                return True
            if name in ("glob", "iglob") and any("**" in (_const(a) or "") for a in n.args):
                return True
        if isinstance(n, (ast.List, ast.Tuple)) and any(_const(e) == "ls-files" for e in n.elts):
            return True
    return False


def _filters_ext(tree, prose, ext):
    for n in ast.walk(tree):
        if isinstance(n, (ast.Set, ast.Tuple, ast.List)) and any(_const(e) == ext for e in n.elts):
            return True
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "endswith"
                and any(_const(a) == ext for a in n.args)):
            return True
        if isinstance(n, ast.Compare) and any(_const(c) == ext for c in [n.left] + n.comparators):
            return True
        if (_const(n, prose) or "").endswith("*" + ext):
            return True
    return False


def _filters_md(tree, prose):
    return _filters_ext(tree, prose, ".md")


def staged_paths(run=None):
    """Every path in the commit, whatever its status (A323): added, changed, deleted, and both sides of a
    rename (--no-renames)."""
    run = run or (lambda: subprocess.run(["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
                                         cwd=HERE, capture_output=True, text=True).stdout)
    return [p for p in run().split("\0") if p]


def walker_readers(exts, population=None, read=None):
    """{suite: why} -- the registered suites whose CODE walks the tree and filters on one of these extensions
    (A323: rule A for any extension). Unreadable or unparseable suites are skipped: they fail their own run."""
    read = read or (lambda t: open(os.path.join(HERE, t), encoding="utf-8").read())
    out = {}
    for t in (runner_suites() if population is None else population):
        try:
            tree = ast.parse(read(t))
        except (OSError, SyntaxError, ValueError, UnicodeDecodeError):
            continue
        if not _walks_tree(tree):
            continue
        prose = _prose(tree)
        hit = [e for e in exts if _filters_ext(tree, prose, e)]
        if hit:
            out[t] = "walks the tree for " + ", ".join(hit)
    return out


def doc_readers(docs, population=None, read=None):
    """{suite: why} -- the registered suites whose CODE reads the given published Markdown (rules A and
    B in the module docstring). An unreadable or unparseable suite is skipped: it fails its own run."""
    read = read or (lambda t: open(os.path.join(HERE, t), encoding="utf-8").read())
    out = {}
    for t in (runner_suites() if population is None else population):
        try:
            tree = ast.parse(read(t))
        except (OSError, SyntaxError, ValueError, UnicodeDecodeError):
            continue
        prose = _prose(tree)
        if _walks_tree(tree) and _filters_md(tree, prose):
            out[t] = "reads every published .md"
            continue
        strs = {s for s in (_const(n, prose) for n in ast.walk(tree)) if s}
        named = [d for d in docs if any(s == d or s == d.rsplit("/", 1)[-1] or s.endswith("/" + d.rsplit("/", 1)[-1])
                                        for s in strs)]
        if named:
            out[t] = "names " + ", ".join(named)
    return out


def selection(tests, docs, readers=None, say=print, paths=(), walkers=None):
    """The suites this commit runs: its own test files, then (A266) the suites that read its published
    Markdown, then (A323) the suites that walk the tree for the extension of any path it touches, each once."""
    names = list(tests)
    if docs:
        found = (readers or doc_readers)(docs)
        shown = ", ".join(docs[:4]) + (" and %d more" % (len(docs) - 4) if len(docs) > 4 else "")
        if found:
            say("stage-check: published markdown in this commit (%s) -- also running the %d suite(s) that read it: %s"
                % (shown, len(found), "; ".join("%s (%s)" % (t, why) for t, why in sorted(found.items()))))
        else:
            say("stage-check: published markdown in this commit (%s), and NO registered suite was found that "
                "reads it -- nothing checked it here" % shown)
        names += [t for t in sorted(found) if t not in names]
    exts = sorted({os.path.splitext(p)[1].lower() for p in paths} - {"", ".md"})    # .md: rule A above
    if exts:
        found = {t: why for t, why in (walkers or walker_readers)(exts).items() if t not in names}
        if found:
            say("stage-check: this commit touches %s files -- also running the %d suite(s) that walk the tree "
                "for them: %s" % (", ".join(exts), len(found), "; ".join(sorted(found))))
        names += sorted(found)
    return names


def suite_env(base=None):
    """The environment a suite runs under: the hook's, WITHOUT git's repository-pinning variables.

    A255, 2026-10-04. Git exports GIT_DIR, GIT_INDEX_FILE ... to the hook, and this passed them to
    every suite. "Where the runner runs it" was then false for any suite that calls git: in the
    .git-less staged copy, `git ls-files` answered about the repository being committed, and a
    suite's scratch `git init` re-initialized that repository's linked-worktree gitdir -- the
    shared config read core.bare = true and the main working tree stopped working. The runner
    (covenant_one) never has those variables; now neither does a suite run from here."""
    try:
        import verify_bundle as VB
        return VB.repo_env(base)
    except Exception:                                            # noqa: BLE001 -- stricter fallback
        return {k: v for k, v in (os.environ if base is None else base).items() if not k.startswith("GIT_")}


def in_place_names():
    """Suites covenant_one runs IN THE FOLDER (IN_PLACE), never in the staged copy."""
    try:
        import covenant_one as C1
        return {n for n, _, _ in C1.IN_PLACE}
    except Exception:                                            # noqa: BLE001
        return set()


def check(tests, stage=None, clean=None, run=None, say=print, timeout=300):
    """{test: (ok, last_line)}. Never raises."""
    out = {}
    if not tests:
        return out
    work = None
    try:
        import covenant_one as C1
        work = (stage or C1.stage)(lambda m: None)
        (clean or C1.clean_dbs)(work)
        in_place = in_place_names()
        for t in tests:
            # A255: an IN_PLACE suite measures THE FOLDER (git, the manifest, the hook), so the
            # runner runs it there; staging it produced a false "CI will be red".
            where = HERE if t in in_place else work
            try:
                p = (run or (lambda t, w: subprocess.run([sys.executable, t], cwd=w, capture_output=True,
                                                         text=True, timeout=timeout,
                                                         env=suite_env())))(t, where)
                last = ((p.stdout or "").strip().splitlines() or [""])[-1][:160]
                out[t] = (p.returncode == 0, last)
            except Exception as e:                               # noqa: BLE001
                out[t] = (False, "did not run: %s" % type(e).__name__)
            ok, last = out[t]
            say("stage-check: %s %s%s -- %s" % ("ok  " if ok else "FAIL", t,
                                               " (in place, as the runner runs it)" if where == HERE else "",
                                               last))
        if any(not ok for ok, _ in out.values()):
            say("stage-check: a suite FAILS where the runner runs it (no .git, no databases). CI will be red "
                "on this push unless it is fixed. The commit is NOT blocked.")
    except Exception as e:                                       # noqa: BLE001
        say("stage-check: could not stage (%s: %s) -- nothing was checked" % (type(e).__name__, str(e)[:120]))
    finally:
        if work and os.path.isdir(work) and stage is None:
            shutil.rmtree(work, ignore_errors=True)
    return out


def for_commit(tests_run=None, docs_run=None, readers=None, say=print, paths_run=None, walkers=None, **kw):
    """The hook's whole path: what the commit stages, selected, then run where the runner runs it."""
    return check(selection(staged_tests(tests_run), staged_docs(docs_run), readers, say,
                           staged_paths(paths_run), walkers), say=say, **kw)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        check(selection([a for a in args if not a.endswith(".md")], [a for a in args if a.endswith(".md")],
                        paths=args))
    else:
        for_commit()
    sys.exit(0)
