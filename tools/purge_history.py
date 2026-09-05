#!/usr/bin/env python3
"""purge_history.py -- remove the owner's portfolio from every commit, and prove it.

WHAT AND WHY. holdings.txt and TRADING_POLICY.json stopped being TRACKED at
2dfe018 / a8d9a5c. They are still IN THE HISTORY, so they are still readable
at any older SHA -- and, measured on 2026-09-05, GitHub serves commits by
SHA that no branch or tag reaches, so a force-push of rewritten history
unpublishes nothing. Only delete-and-recreate of the GitHub repository (or a
GitHub Support purge) closes the public copy. See docs/sessions/PUBLIC_PATH.md.

WHAT THE 2026-09-05 AUDIT ADDED (16 agents, each finding reproduced by a
skeptic before it counted). The first version of this tool rewrote five
paths and would have reported "clean" while the portfolio stayed public:

  * docs/DAILY_CHECK.md (and the launch/ copy inside the release zip) carries
    the ten locked positions with exact quantity and average buy -- the same
    table as holdings.txt -- and it is in EVERY commit. A path filter cannot
    fix a file that must stay; its contents have to be rewritten.
  * PLAN.md, docs/TRADING_READINESS.md, docs/IMPROVEMENT_LOG.md,
    covenant_scenarios.py and strategy_validate.py quote the locked book value
    or the sleeve amount in prose.
  * docs/results/daily_state.SAMPLE.json holds one equity row of uncertain
    provenance.
  * holdings.txt.bak-* was committed once in a reflog-only commit.
  * 110 of 280 commits carry the owner's personal email address as author.

So this version does four things, with either backend git offers:

  1. PATHS: deletes the portfolio files, their launch/ copies, the release
     zip that holds them inside it, any holdings.txt.bak-*, anything under
     private/.
  2. CONTENT: rewrites text blobs -- the holdings table rows become
     "<qty> <avg_buy>", the prose amounts become neutral phrases, and every
     distinctive number taken from the ignored private files on disk (and
     from the historical portfolio blobs) is replaced by "<redacted>". The
     number list is BUILT AT RUN TIME from files that are not in git; this
     script contains no figure and prints none (tokens are shown masked).
  3. IDENTITY: maps every non-noreply author/committer email to the noreply
     address git is configured with. The addresses are never printed.
  4. PROOF: after the rewrite it scans EVERY blob reachable from EVERY ref
     for the paths, the table rows, the prose patterns, the tokens and the
     email, expires the reflog and prunes, and refuses to call the result
     clean if a single hit remains.

BACKENDS. git-filter-repo if it is installed (fast, and it removes 'origin'
so a rewrite cannot be pushed by reflex). Otherwise git's own filter-branch,
which every git ships: slower (it checks out each commit into a scratch
directory outside the tree) but needs no install -- on 2026-09-05 the
install was refused by the environment's policy, and that must not be the
reason the portfolio stays public. The known filter-branch pitfalls are
handled here: scratch dir outside the work tree, tags rewritten, refs/original
deleted, reflog expired, objects pruned.

THIS SCRIPT DOES NOT PUSH AND DOES NOT TOUCH THE REMOTE. Publishing the
result is a separate, deliberate act -- delete-and-recreate, never force-push.

    python tools/purge_history.py                       # dry run: report only
    python tools/purge_history.py --run --backup DIR    # rewrite; DIR is a mirror
                                                        # clone OUTSIDE this tree
    python tools/purge_history.py --verify              # scan only, no rewrite

--run refuses a dirty tree, a missing or stale backup, and other worktrees
(filter-branch will not update their checkouts; remove them first).
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATHS = ["holdings.txt", "TRADING_POLICY.json",
         "launch/covenant-v8.37/holdings.txt",
         "launch/covenant-v8.37/TRADING_POLICY.json",
         "launch/covenant-v8.37-launch.zip",
         # 2026-09-05: found by a shape scan (quantity-then-symbol,
         # symbol-then-dollar, "portfolio $"), not by the audit's number
         # method. ALERTS.md is the owner's 2026-08-19 alert levels: position
         # values, quantities, a cost basis and the portfolio total, in
         # prose and tables. A file that is portfolio advice from end to end
         # is removed, not patched; a stub at HEAD keeps INDEX.md's links.
         "ALERTS.md", "launch/covenant-v8.37/ALERTS.md"]
PATH_GLOBS = ["holdings.txt.bak-*", "launch/*/holdings.txt.bak-*"]
PREFIXES = ["private/"]

# Content rules: (regex, replacement). Global -- specific enough that they
# cannot hit anything but the sentences they were written for.
TABLE_ROW = r"^(XLM|SOL|WLFI|XRP|ADA|CC|CRO|ONDO|HBAR|PEPE|CASH)([ \t]+)[0-9][0-9.,]*([ \t]+)[0-9][0-9.,]*"
RULES = [
    (TABLE_ROW, r"\1\2<qty>\3<avg_buy>"),
    (r"At \$[0-9][0-9,]*(\.[0-9]+)?\s+of capital", "At this scale of capital"),
    (r"the \$[0-9][0-9,]*(\.[0-9]+)?\s+sleeve", "the sleeve"),
    (r"exceeds \$[0-9][0-9,]*(\.[0-9]+)?/year", "exceeds the sleeve's size per year"),
    (r"a ~\$[0-9]+(\.[0-9]+)?k book", "a small book"),
    (r'"equity":\s*\[\s*\[\s*([0-9]+)(?:\.[0-9]+)?,\s*[0-9]+(?:\.[0-9]+)?\s*\]', r'"equity": [[\1, 1000.0]'),
    # 2026-09-05 shape scan: portfolio totals in logs, trim amounts, and an
    # execution note that names real Kraken quantities.
    (r"([Pp]ortfolio )(\*\*)?\$[0-9][0-9,]*(\.[0-9]+)?(\*\*)?", r"\1<total>"),
    (r"XLM ~\$[0-9][0-9,]*(\.[0-9]+)?, SOL ~\$[0-9][0-9,]*(\.[0-9]+)?", "XLM and SOL by the Rule-1 amounts"),
    (r"sell ~[0-9][0-9,]*(\.[0-9]+)? (XLM|SOL) ≈ \$[0-9][0-9,]*(\.[0-9]+)?", r"sell ~<qty> \2 ≈ $<value>"),
    (r"sized a sell for [0-9][0-9,]*(\.[0-9]+)? XLM", "sized a sell for <qty> XLM"),
    (r"SELL [0-9][0-9,]*(\.[0-9]+)? XLM(\s+\[clamped: rule wants )[0-9][0-9,]*(\.[0-9]+)?( but Kraken holds )[0-9][0-9,]*(\.[0-9]+)?\]",
     r"SELL <qty> XLM\2<qty>\4<qty>]"),
    (r"\*\*TRIM (XLM|SOL)\*\* [0-9]+(\.[0-9]+)?% → [0-9]+(\.[0-9]+)?%", r"**TRIM \1** <share> → <cap>"),
    # The verified price baseline keeps its price table (public data) and
    # loses its "Portfolio at these prices" section -- total, cash, value and
    # share per position, and the actions those implied -- as a block.
    (r"(?s)(## Portfolio at these prices\n).*?(?=## Provenance)",
     r"\1\n(Removed 2026-09-05: the owner's position values at these prices and the actions"
     r" they implied. The prices above are public; the positions were not the project's"
     r" to publish. See docs/KNOWN_ISSUES.md issue 15.)\n\n"),
]
PLACEHOLDER = "<redacted>"
MIN_SIG_DIGITS = 5

NUM = re.compile(r"(?<![\w.])[0-9][0-9,]*(?:\.[0-9]+)?(?![\w])")
# Where the NUMBER rules must not run: market data, vendored libraries, the
# study corpus, the model, manifests of hashes. A price that equals an
# average buy to five digits is a coincidence, not a leak, and rewriting a
# candle series to hide one would destroy public data to protect nothing.
# The sentence rules (RULES) still run everywhere. The first dry run on
# 2026-09-05 would have touched 193 files, mostly these; it is why this
# list exists.
NO_TOKENS_UNDER = ("realdata/", "vendor/", "ops/study/", "docs/semantic/",
                   "launch/covenant-v8.37/realdata/")
NO_TOKENS_GLOB = ("*.csv", "*.min.js", "fallback_model.json", "*.png", "*.jpg",
                  "*.zip", "*.pyc")


# Files no content rule may touch: the tool's own test, whose invented
# sentences exist to match the rules, and the tool, whose patterns are not
# text. Rewriting either would break the thing that proves the rewrite.
NO_RULES_FILES = ("test_purge_tool.py", "tools/purge_history.py")


def _rel(path):
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def rules_allowed(path):
    return _rel(path) not in NO_RULES_FILES


def tokens_allowed(path):
    p = _rel(path)
    if not rules_allowed(p) or p.startswith(NO_TOKENS_UNDER):
        return False
    base = p.rsplit("/", 1)[-1]
    return not any(glob.fnmatch.fnmatch(base, g) for g in NO_TOKENS_GLOB)


# ------------------------------------------------------------------ helpers
def git(*a, check=True, cwd=None, binary=False):
    r = subprocess.run(["git", *a], capture_output=not binary, text=not binary,
                       cwd=cwd or HERE, stdout=subprocess.PIPE if binary else None,
                       stderr=subprocess.PIPE if binary else None)
    if check and r.returncode:
        err = r.stderr if isinstance(r.stderr, str) else r.stderr.decode("utf-8", "replace")
        sys.exit("git %s failed:\n%s" % (" ".join(a), err.strip()))
    return r.stdout if binary else r.stdout.strip()


def say(s=""):
    print(s, flush=True)


def sig_digits(tok):
    return len(tok.replace(",", "").replace(".", "").lstrip("0"))


def generic(tok):
    t = tok.replace(",", "")
    if re.fullmatch(r"(19|20)[0-9]{2}(\.0+)?", t):
        return True                                   # a year
    if re.fullmatch(r"[1-9]0{3,}(\.0+)?", t):
        return True                                   # a round thousand
    if re.fullmatch(r"(5000|5001|5011|5020|5021|5031|5060|5061|5071|11434|8080|443|65536|86400|3600)", t):
        return True                                   # ports, seconds, powers
    if len(t.replace(".", "").replace("0", "")) <= 2:
        return True                                   # 100.00, 2500.0, 0.0500: shape, not identity
    return False


def mask(tok):
    """First two characters, one star per hidden digit, the last digit, and
    the count of significant digits. Never the value."""
    b = tok.replace(",", "")
    digits = b.replace(".", "")
    return b[:2] + "*" * max(1, len(digits) - 3) + b[-1:] + " (%dd)" % sig_digits(tok)


def mask_email(e):
    if "@" not in e:
        return "?"
    u, d = e.split("@", 1)
    return u[:1] + "***@" + d


# ------------------------------------------------------------------ tokens
def tokens_from_text(text):
    out = set()
    for m in NUM.finditer(text):
        tok = m.group(0).rstrip(".")
        if sig_digits(tok) >= MIN_SIG_DIGITS and not generic(tok):
            out.add(tok)
            bare = tok.replace(",", "")
            if bare != tok:
                out.add(bare)
    return out


def private_sources(commits_with_paths):
    """The ignored files on disk, plus every historical version of the
    target paths. Read, never printed."""
    srcs = {}
    # Position files only. The venue exports under private/ hold thousands
    # of prices and timestamps that coincide with public market data; the
    # positions they carry are already in holdings.txt.
    for p in ["holdings.txt", "TRADING_POLICY.json"] \
            + glob.glob(os.path.join(HERE, "holdings.txt.bak-*")) \
            + [os.path.join(HERE, "private", "RESERVE.json")]:
        p = p if os.path.isabs(p) else os.path.join(HERE, p)
        if os.path.isfile(p):
            try:
                srcs[os.path.relpath(p, HERE)] = io.open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                pass
    seen_blobs = set()
    for c in commits_with_paths:
        for p in PATHS[:4]:
            r = subprocess.run(["git", "rev-parse", "--verify", "-q", "%s:%s" % (c, p)],
                               cwd=HERE, capture_output=True, text=True)
            if r.returncode or r.stdout.strip() in seen_blobs:
                continue
            seen_blobs.add(r.stdout.strip())
            srcs["%s:%s" % (c[:7], p)] = git("show", "%s:%s" % (c, p), check=False)
    return srcs


def build_tokens(commits_with_paths, exclude):
    srcs = private_sources(commits_with_paths)
    toks = {}
    for name, text in srcs.items():
        for t in tokens_from_text(text):
            if t not in exclude and t.replace(",", "") not in exclude:
                toks.setdefault(t, set()).add(name)
    return toks, sorted(srcs)


def token_regex(toks):
    if not toks:
        return None
    alts = sorted(toks, key=len, reverse=True)
    return re.compile(r"(?<![\w.])(?:" + "|".join(re.escape(t) for t in alts) + r")(?![\w])")


# ------------------------------------------------------------------ rewriting text
def rewrite_text(text, tok_re, path="", detail=None):
    n = 0
    if path and not rules_allowed(path):
        return text, 0
    for pat, rep in RULES:
        text, k = re.subn(pat, rep, text, flags=re.M)
        n += k
        if k and detail is not None:
            detail.append("rule:" + pat[:24])
    if tok_re is not None and tokens_allowed(path):
        if detail is not None:
            for m in tok_re.finditer(text):
                detail.append("token:" + mask(m.group(0)))
        text, k = tok_re.subn(PLACEHOLDER, text)
        n += k
    return text, n


def is_text(raw):
    return b"\0" not in raw[:4096]


# ------------------------------------------------------------------ the tree
def commits_containing():
    """Every commit whose TREE contains a target path, glob or prefix."""
    hits = []
    for c in git("rev-list", "--all").splitlines():
        names = git("ls-tree", "-r", "--name-only", c, check=False).split("\n")
        if any(n in PATHS or n.startswith(tuple(PREFIXES)) or
               any(glob.fnmatch.fnmatch(n, g) for g in PATH_GLOBS) for n in names):
            hits.append(c)
    return hits


def emails():
    out = {}
    for line in git("log", "--all", "--format=%ae%x00%ce").splitlines():
        for e in line.split("\0"):
            if e:
                out[e] = out.get(e, 0) + 1
    return out


def email_map():
    """Every non-noreply address -> the configured noreply address. Refuses
    if git is not configured with a noreply address."""
    target = git("config", "user.email", check=False)
    if "noreply" not in target:
        return None, target
    return {e: target for e in emails() if "noreply" not in e}, target


# ------------------------------------------------------------------ dry-run scan of HEAD
def scan_head(tok_re):
    files = [p for p in git("ls-files", "-z").split("\0") if p]
    report = []
    for f in files:
        p = os.path.join(HERE, f)
        try:
            raw = open(p, "rb").read()
        except OSError:
            continue
        if not is_text(raw):
            continue
        text = raw.decode("utf-8", "replace")
        detail = []
        new, n = rewrite_text(text, tok_re, f, detail)
        if n:
            seen = []
            for d in detail:
                if d not in seen:
                    seen.append(d)
            report.append((f, n, seen))
    return files, report


# ------------------------------------------------------------------ the worker (filter-branch --tree-filter)
def worker(rules_path):
    """Runs inside each checked-out commit: delete target paths, rewrite text."""
    spec = json.load(open(rules_path, encoding="utf-8"))
    tok_re = re.compile(spec["token_regex"]) if spec.get("token_regex") else None
    for p in PATHS:
        if os.path.exists(p):
            os.remove(p)
    for g in PATH_GLOBS:
        for p in glob.glob(g):
            os.remove(p)
    for pre in PREFIXES:
        if os.path.isdir(pre):
            shutil.rmtree(pre, ignore_errors=True)
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            p = os.path.join(root, name)
            try:
                raw = open(p, "rb").read()
            except OSError:
                continue
            if not is_text(raw):
                continue
            text = raw.decode("utf-8", "surrogateescape")
            new, n = rewrite_text(text, tok_re, p)
            if n:
                with open(p, "wb") as fh:
                    fh.write(new.encode("utf-8", "surrogateescape"))
    return 0


# ------------------------------------------------------------------ verification over every blob
def verify(tok_re, emap):
    say("VERIFY -- every object reachable from every ref")
    bad = 0
    after = commits_containing()
    say("  commits whose tree contains a target path: %d" % len(after))
    bad += len(after)
    objs = git("rev-list", "--all", "--objects")
    blobs = []
    for line in objs.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            blobs.append(parts)
    say("  objects with a path: %d" % len(blobs))
    seen = set()
    hits = {}
    rules_re = [re.compile(p, re.M) for p, _ in RULES]
    for sha, path in blobs:
        if sha in seen:
            continue
        seen.add(sha)
        typ = git("cat-file", "-t", sha, check=False)
        if typ != "blob":
            continue
        raw = git("cat-file", "-p", sha, binary=True)
        if not is_text(raw):
            continue
        text = raw.decode("utf-8", "replace")
        why = []
        if not rules_allowed(path):
            continue
        for r in rules_re:
            if r.search(text):
                why.append("rule:" + r.pattern[:28])
        if tok_re is not None and tokens_allowed(path):
            m = tok_re.search(text)
            if m:
                why.append("token:" + mask(m.group(0)))
        if why:
            hits[path] = why
    for path, why in sorted(hits.items()):
        say("  HIT  %-50s %s" % (path, "; ".join(why)[:80]))
    bad += len(hits)
    say("  blobs with a hit: %d" % len(hits))
    em = emails()
    left = [e for e in em if emap and e in emap]
    say("  personal addresses still signing commits: %d" % len(left))
    bad += len(left)
    orig = git("for-each-ref", "refs/original", check=False)
    say("  refs/original left behind: %d" % (len(orig.splitlines()) if orig else 0))
    bad += len(orig.splitlines()) if orig else 0
    say("  RESULT: %s" % ("CLEAN" if not bad else "*** NOT CLEAN -- DO NOT PUBLISH ***"))
    return 0 if not bad else 1


# ------------------------------------------------------------------ backends
def have_filter_repo():
    return subprocess.run(["git", "filter-repo", "--version"], capture_output=True).returncode == 0


def run_filter_repo(tok_re, emap, scratch):
    expr = os.path.join(scratch, "replace.txt")
    with io.open(expr, "w", encoding="utf-8") as fh:
        for pat, rep in RULES:
            fh.write("regex:%s==>%s\n" % (pat, rep.replace("\\", "\\")))
        if tok_re is not None:
            fh.write("regex:%s==>%s\n" % (tok_re.pattern, PLACEHOLDER))
    args = ["filter-repo", "--force", "--invert-paths", "--replace-text", expr]
    for p in PATHS:
        args += ["--path", p]
    for g in PATH_GLOBS:
        args += ["--path-glob", g]
    for pre in PREFIXES:
        args += ["--path", pre]
    if emap:
        mm = os.path.join(scratch, "mailmap")
        with io.open(mm, "w", encoding="utf-8") as fh:
            for old, new in emap.items():
                fh.write("<%s> <%s>\n" % (new, old))
        args += ["--mailmap", mm]
    git(*args)


def run_filter_branch(tok_re, emap, scratch):
    rules = os.path.join(scratch, "rules.json")
    with io.open(rules, "w", encoding="utf-8") as fh:
        json.dump({"token_regex": tok_re.pattern if tok_re else ""}, fh)
    me = os.path.abspath(__file__).replace("\\", "/")
    py = sys.executable.replace("\\", "/")
    tree_filter = '"%s" "%s" --worker "%s"' % (py, me, rules.replace("\\", "/"))
    env_filter = ""
    if emap:
        lines = []
        for old, new in emap.items():
            lines.append('if [ "$GIT_AUTHOR_EMAIL" = "%s" ]; then export GIT_AUTHOR_EMAIL="%s"; fi' % (old, new))
            lines.append('if [ "$GIT_COMMITTER_EMAIL" = "%s" ]; then export GIT_COMMITTER_EMAIL="%s"; fi' % (old, new))
        env_filter = "\n".join(lines)
    tmp = os.path.join(scratch, "fb-tmp")
    args = ["filter-branch", "-f", "-d", tmp.replace("\\", "/"),
            "--tree-filter", tree_filter, "--tag-name-filter", "cat"]
    if env_filter:
        args += ["--env-filter", env_filter]
    args += ["--", "--all"]
    env = dict(os.environ, FILTER_BRANCH_SQUELCH_WARNING="1")
    r = subprocess.run(["git", *args], cwd=HERE, env=env)
    if r.returncode:
        sys.exit("filter-branch failed (exit %d)" % r.returncode)
    for ref in git("for-each-ref", "--format=%(refname)", "refs/original", check=False).splitlines():
        if ref:
            git("update-ref", "-d", ref)


def cleanup_objects():
    git("reflog", "expire", "--expire=now", "--all")
    git("gc", "--prune=now", "--quiet", check=False)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--verify", action="store_true", help="scan only")
    ap.add_argument("--backup", help="a mirror clone OUTSIDE this tree, made before --run")
    ap.add_argument("--exclude-token", action="append", default=[],
                    help="a number from the private files that is also a legitimate constant elsewhere")
    ap.add_argument("--allow-worktrees", action="store_true")
    ap.add_argument("--worker", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.worker:
        return worker(a.worker)

    os.chdir(HERE)
    if git("rev-parse", "--is-inside-work-tree") != "true":
        sys.exit("not a git work tree")

    before = commits_containing()
    toks, srcs = build_tokens(before, set(a.exclude_token))
    tok_re = token_regex(toks)
    emap, target = email_map()
    say("private sources read (never printed): %d" % len(srcs))
    say("distinctive numbers to redact: %d  (min %d significant digits; %d excluded)"
        % (len(toks), MIN_SIG_DIGITS, len(a.exclude_token)))
    say("commits whose tree contains a target path: %d" % len(before))
    em = emails()
    say("author/committer addresses: %d distinct; personal (to be mapped): %d -> %s"
        % (len(em), len(emap or {}), mask_email(target)))

    if a.verify:
        return verify(tok_re, emap)

    files, report = scan_head(tok_re)
    say("\nHEAD tracked files the content rules would change: %d of %d" % (len(report), len(files)))
    for f, n, detail in sorted(report, key=lambda r: -r[1])[:40]:
        say("  %-52s %4d  %s" % (f, n, "; ".join(detail[:6])[:110]))
    if len(report) > 40:
        say("  ... %d more" % (len(report) - 40))

    wts = [l for l in git("worktree", "list").splitlines()[1:] if l.strip()]
    dirty = git("status", "--porcelain")
    say("\nworktrees besides this one: %d" % len(wts))
    say("working tree: %s" % ("clean" if not dirty else "DIRTY (%d lines)" % len(dirty.splitlines())))
    say("backend: %s" % ("git-filter-repo" if have_filter_repo() else "git filter-branch (built in)"))

    if not a.run:
        say("\nDRY RUN. Nothing written. Re-run with --run --backup DIR to rewrite.")
        say("Publishing is still a separate act: docs/sessions/PUBLIC_PATH.md step 3")
        say("(delete-and-recreate the GitHub repository, NOT force-push).")
        return 0

    # --------------------------------------------------------- refusals
    if dirty:
        sys.exit("working tree is dirty. Commit or stash first -- a rewrite over "
                 "uncommitted work is how work disappears.")
    if wts and not a.allow_worktrees:
        sys.exit("other worktrees exist; filter-branch will not update their checkouts. "
                 "Remove them (git worktree remove) or pass --allow-worktrees.")
    if not a.backup or not os.path.isdir(a.backup):
        sys.exit("--backup DIR is required and must exist: a mirror clone outside this tree "
                 "(git clone --mirror . DIR).")
    inside = os.path.normcase(os.path.abspath(a.backup)).startswith(
        os.path.normcase(os.path.abspath(HERE)).rstrip(os.sep) + os.sep)
    if inside:
        sys.exit("the backup must live OUTSIDE this tree; a rewrite here would rewrite it too.")
    ours = int(git("rev-list", "--all", "--count"))
    theirs = git("rev-list", "--all", "--count", cwd=a.backup, check=False)
    if not theirs.isdigit() or int(theirs) < ours:
        sys.exit("backup at %s is not a git repository with at least our %d commits (has %s)."
                 % (a.backup, ours, theirs or "?"))
    if emap is None:
        sys.exit("git user.email is not a noreply address; refusing to choose one. "
                 "Set git config user.email to the noreply address first.")
    say("\nbackup verified: %s holds %s commits (we have %d)" % (a.backup, theirs, ours))
    say("every SHA is about to change; the backup is the way back.\n")

    scratch = os.path.join(os.path.dirname(os.path.abspath(a.backup)), "purge-scratch-%d" % int(time.time()))
    os.makedirs(scratch, exist_ok=True)
    t0 = time.time()
    if have_filter_repo():
        run_filter_repo(tok_re, emap, scratch)
    else:
        run_filter_branch(tok_re, emap, scratch)
    say("rewrite done in %.0f s; expiring reflog and pruning objects" % (time.time() - t0))
    cleanup_objects()
    shutil.rmtree(scratch, ignore_errors=True)
    say("")
    rc = verify(tok_re, emap)
    if rc == 0:
        say("\nNext: docs/sessions/PUBLIC_PATH.md step 3 -- delete and recreate the GitHub "
            "repository, then push main, dev and the tags. Never force-push a rewrite.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
