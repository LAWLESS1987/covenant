#!/usr/bin/env python3
"""tools/repo_autopush.py -- laptop consumer of TETSU's unison feed: push unify/auto targets to GitHub.

Built 2026-11-02 for his "Enable auto-push" + "as much redundancy as possible". The push semantics are
TETSU's unison.py design (recorded in ops/AUTOPUSH_DESIGN_2026-11-02.md). SAFE BY CONSTRUCTION, and every
step can refuse:

  - It reuses hf_mirror's TESTED primitives -- guarded_push() (fast-forward only, no --force, with his opsec
    scan over every object the push would send that GitHub does not already hold), _opsec(), list_owned_repos(),
    _auth_header(), _api(), and the one feed reader feed_url()/read_feed(). It does not reimplement the scanner,
    the push, or the feed source.
  - FF-ONLY against GitHub's CURRENT main (guarded_push re-reads GitHub at push time); never --force. The opsec
    scan that guarded_push runs over the objects GitHub does not already hold IS the scan of the range
    github_main..target -- commits authored off-laptop that never passed this guard.
  - The target is fetched from TETSU's own_git (the feed's fetch_from) and must equal the feed's `target`; a
    later unison pass or a hold may have moved it, so a mismatch SKIPS and re-reads next cycle.
  - Acts only on state FAST_FORWARD/UNIFIED with target non-null; NEEDS_HUMAN/ERROR/UNREACHABLE/SNAPSHOT_DUE
    and UNISON skip. `website` in needs_push is a site deploy (site_autodeploy owns it, keyed on the feed's
    top-level site_deploy_due), never a git push here. A repo whose feed snapshot_copies lists `hf`, or that is
    hf_mirror.SNAPSHOT_ONLY, is never history-pushed.
  - OPEN-PR GUARD (his "mutual benefit", 2026-11-02): if GitHub has an open PR whose base is the target branch,
    the repo is SKIPPED and logged -- a fast-forward under an open PR would force the operator's review to
    rebase. Error reading PR state is treated as an open PR (fail-safe). This holds Sentinel-Witness while its
    PR #8 is open and auto-resumes once the PR is merged or closed.
  - Private repos are pushed only to their OWN GitHub origin (same visibility); nothing is cross-posted to a
    public mirror here (that is hf_mirror's job, and it reads visibility from GitHub).

DRY-RUN BY DEFAULT. `--run` pushes. Each pass appends one JSON line to ops/repo_autopush.jsonl (gitignored).

  COVENANT_GH_READ=1 python tools/repo_autopush.py            # dry run: say what it WOULD push, touch nothing
  COVENANT_GH_READ=1 python tools/repo_autopush.py --run      # push the fast-forwardable targets

Feed URL: ops/local_unison_feed.txt or env COVENANT_UNISON_FEED (his network addresses never go in a tracked
file). The feed's `fetch_from` <tetsu> placeholder is filled from the feed URL's host.
LICENCE: public domain.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import hf_mirror as HM  # noqa: E402  -- tested primitives: _opsec, guarded_push, list_owned_repos, _auth_header,
#                                        _api, _git, SNAPSHOT_ONLY, feed_url, read_feed

LEDGER = os.path.join(HERE, "ops", "repo_autopush.jsonl")
PUSH_STATES = ("FAST_FORWARD", "UNIFIED")


def _host_of(url):
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0].split(":", 1)[0]


def is_snapshot(name, meta):
    """Fail-closed: a repo the feed marks hf-snapshot (snapshot_copies) OR in hf_mirror.SNAPSHOT_ONLY is never
    history-pushed. Both sources are honoured so a hold added on TETSU only cannot be missed."""
    return name in HM.SNAPSHOT_ONLY or "hf" in (meta.get("snapshot_copies") or [])


def open_pr_into(full, branch, token, api=None):
    """(has_open_pr, note). True if GitHub has an open PR whose base is `branch`. Error -> True (fail-safe: do
    not push under an unknown PR state)."""
    api = api or HM._api
    try:
        rows, _link = api("https://api.github.com/repos/%s/pulls?state=open&base=%s&per_page=10" % (full, branch),
                          token)
    except Exception as e:                                       # noqa: BLE001
        return True, "PR state unreadable (%s) -- not pushing under an unknown PR" % type(e).__name__
    nums = [d.get("number") for d in (rows or [])]
    return (bool(nums), ("open PR(s) %s into %s" % (nums, branch)) if nums else "")


def _git(args, cfg=()):
    return HM._git(args, cfg)


def plan_repo(name, meta):
    """Decide what to do with one repo from the feed, WITHOUT touching the network. (action, detail), action in
    {skip, push}. Pure and deterministic; the network checks (open PR, fetch, ancestry) happen in run()."""
    if "github" not in (meta.get("needs_push") or []):
        return "skip", "github not in needs_push"
    if is_snapshot(name, meta):
        return "skip", "snapshot repo (never history-pushed here)"
    if meta.get("state") not in PUSH_STATES:
        return "skip", "state %s not pushable" % meta.get("state")
    if not meta.get("target"):
        return "skip", "no target"
    if not meta.get("fetch_from"):
        return "skip", "no fetch_from"
    return "push", meta["target"]


def run(dry=True, feed=None, say=print, token=None, branch="main"):
    url = HM.feed_url()
    if feed is None:
        feed, err = HM.read_feed(url)
        if err:
            say("feed: " + err + " -- nothing pushed")
            return 2
    if feed.get("status") != "ok":
        say("feed status %r != ok -- nothing pushed" % feed.get("status"))
        return 2
    host = _host_of(url) if url else "<tetsu>"
    token = token if token is not None else HM._gh_token()
    if not token:
        say("no GitHub credential (COVENANT_GH_READ=1 or GITHUB_TOKEN) -- cannot push")
        return 2
    # Full names come from the owner's repo list; a repo not owned by this account is not ours to push.
    try:
        owned = {r["name"]: r for r in HM.list_owned_repos(token)}
    except Exception as e:                                       # noqa: BLE001
        say("could not list owned repos: %s" % e)
        return 2

    results, pushed, refused = [], 0, 0
    opsec = None
    for name, meta in sorted((feed.get("repos") or {}).items()):
        action, detail = plan_repo(name, meta)
        if action == "skip":
            results.append({"repo": name, "action": "skip", "why": detail})
            continue
        if name not in owned:
            results.append({"repo": name, "action": "skip", "why": "not an owned GitHub repo"})
            continue
        repo = owned[name]
        target = meta["target"]
        # Open-PR guard: never fast-forward main out from under an open PR (error reading state == treat as open).
        has_pr, pr_note = open_pr_into(repo["full"], branch, token)
        if has_pr:
            results.append({"repo": name, "action": "skip", "why": pr_note})
            continue
        fetch_url, _sp, fetch_ref = meta["fetch_from"].replace("<tetsu>", host).partition(" ")
        fetch_ref = fetch_ref.strip() or "unify/auto"
        clone_url = repo["clone_url"]
        auth = "http.extraheader=" + HM._auth_header("x-access-token", token)
        dest = tempfile.mkdtemp(prefix="autopush_%s_" % name)
        try:
            ok, _o, e = _git(["init", "-q", dest])
            if not ok:
                results.append({"repo": name, "action": "error", "why": "git init: " + e[-160:]}); refused += 1; continue
            # 1. Fetch the target from TETSU's own_git and require FETCH_HEAD == the feed's target (moved => skip).
            ok, _o, e = _git(["-C", dest, "fetch", "-q", fetch_url, fetch_ref],
                             cfg=["-c", "fetch.negotiationAlgorithm=noop"])
            if not ok:
                results.append({"repo": name, "action": "error", "why": "fetch own_git: " + e[-160:]}); refused += 1; continue
            ok, fh, _e = _git(["-C", dest, "rev-parse", "FETCH_HEAD"])
            fetched = fh.strip()
            if fetched != target:
                results.append({"repo": name, "action": "skip",
                                "why": "own_git head %s != feed target %s (moved; retry next cycle)"
                                       % (fetched[:8], target[:8])})
                continue
            # 2. Fetch GitHub's CURRENT main; require it is an ancestor of the target (fast-forward only).
            ok, _o, e = _git(["-C", dest, "fetch", "-q", clone_url, branch], cfg=["-c", auth])
            if not ok:
                results.append({"repo": name, "action": "error", "why": "fetch github: " + e[-160:]}); refused += 1; continue
            ok, gh, _e = _git(["-C", dest, "rev-parse", "FETCH_HEAD"])
            gh_main = gh.strip()
            if subprocess.run(["git", "-C", dest, "merge-base", "--is-ancestor", gh_main, target]).returncode != 0:
                results.append({"repo": name, "action": "skip",
                                "why": "not fast-forward: github main %s not an ancestor of target %s"
                                       % (gh_main[:8], target[:8])})
                continue
            if gh_main == target:
                results.append({"repo": name, "action": "skip", "why": "github already at target"})
                continue
            # 3. Only head on dest is `branch` = target, so guarded_push sends exactly that, no tags, never
            #    the unify/auto branch name. guarded_push re-reads GitHub and opsec-scans github_main..target.
            _git(["-C", dest, "branch", "-f", branch, target])
            if dry:
                results.append({"repo": name, "action": "would-push",
                                "why": "ff %s..%s to %s" % (gh_main[:8], target[:8], branch)})
                continue
            if opsec is None:
                opsec = HM._opsec()                              # scan his identifiers once; raises if unreadable
            pushed_ok, why = HM.guarded_push(dest, clone_url, cfg=["-c", auth], say=say, opsec=opsec, redact=token)
            results.append({"repo": name, "action": "pushed" if pushed_ok else "refused", "why": why})
            pushed += int(pushed_ok); refused += int(not pushed_ok)
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    row = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), "dry": dry,
           "pushed": pushed, "refused": refused, "results": results}
    try:
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass
    for r in results:
        say("%-24s %-11s %s" % (r["repo"], r["action"], r.get("why", "")))
    say("-- %s: %d pushed, %d refused/error, %d repos considered"
        % ("DRY RUN" if dry else "RUN", pushed, refused, len(results)))
    return 1 if refused else 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    return run(dry="--run" not in argv)


if __name__ == "__main__":
    sys.exit(main())
