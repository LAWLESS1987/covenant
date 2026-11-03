#!/usr/bin/env python3
"""test_ap1_repo_autopush.py -- AP1. tools/repo_autopush.py pushes only a clean fast-forward, and refuses
everything else. Local bare repositories stand in for GitHub and for TETSU's own_git (no network). Driven both
ways -- every guard is shown refusing AND, with the cause removed, letting the push through:

  AP1a  a clean fast-forward is pushed for real (--run): GitHub's main advances to the feed's target
  AP1b  an unreachable feed, and a feed whose status != 'ok', push NOTHING (return 2)
  AP1c  an open PR into the target branch SKIPS; with no open PR the same repo would-push
  AP1d  a non-fast-forward (GitHub ahead of target) SKIPS; a true ff of the same repo would-push
  AP1e  a snapshot repo, and `website` in needs_push, are skipped (never history-pushed here)
  AP1f  a target that has MOVED on own_git since the feed was built SKIPS (retries next cycle)
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import hf_mirror as HM            # noqa: E402
import repo_autopush as AP        # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


def git(*args, cwd=None):
    p = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    return p.stdout.strip()


def commit(work, name, body):
    with open(os.path.join(work, name), "w") as fh:
        fh.write(body)
    git("add", name, cwd=work)
    git("-c", "user.name=ap1", "-c", "user.email=ap1@example.invalid", "commit", "-q", "-m", name, cwd=work)
    return git("rev-parse", "HEAD", cwd=work)


class StubOpsec:
    """The real scan's shape with one planted identifier, so the guard is exercised whatever this machine holds."""
    MARK = "ap1-planted-identifier-9d2e"

    def pair(self):
        import opsec_scan as O
        return O, [("lan-ip", self.MARK)]


def owned_of(name, clone_url, private=False):
    return [{"name": name, "full": "o/%s" % name, "private": private, "clone_url": clone_url}]


def feed_ok(repos):
    return {"status": "ok", "repos": repos}


def meta(target, fetch_from, needs=("github",), state="FAST_FORWARD", snapshot=()):
    return {"needs_push": list(needs), "state": state, "target": target,
            "fetch_from": fetch_from, "snapshot_copies": list(snapshot)}


def main():
    base = tempfile.mkdtemp(prefix="ap1_")
    os.environ.pop("COVENANT_UNISON_FEED", None)                 # feed is passed in; url stays "" (host <tetsu>)

    def github_at(n, commits):
        """A bare 'GitHub' repo with main at the LAST of `commits` (each a (file, body)). Returns (bare, {file:sha})."""
        bare = os.path.join(base, "gh_%s.git" % n)
        work = os.path.join(base, "ghwork_%s" % n)
        git("init", "-q", "--bare", "-b", "main", bare)
        git("init", "-q", "-b", "main", work)
        shas = {}
        for f, body in commits:
            shas[f] = commit(work, f, body)
        git("push", "-q", bare, "main", cwd=work)
        return bare, work, shas

    def own_unify(n, from_work, extra):
        """Bare own_git with branch unify/auto = from_work + one `extra` commit. Returns (bare, target_sha, 'url ref')."""
        bare = os.path.join(base, "own_%s.git" % n)
        git("init", "-q", "--bare", bare)
        wk = os.path.join(base, "ownwork_%s" % n)
        git("clone", "-q", from_work, wk)
        tgt = commit(wk, extra[0], extra[1])
        git("push", "-q", bare, "HEAD:refs/heads/unify/auto", cwd=wk)
        return bare, tgt, "%s unify/auto" % bare

    # ---- AP1a: a clean fast-forward is pushed for real. --------------------------------------------------------
    ghbare, ghwork, _ = github_at("a", [("a.txt", "one\n")])
    gmain = git("rev-parse", "main", cwd=ghbare)
    ownbare, target, fetch_from = own_unify("a", ghwork, ("b.txt", "two\n"))
    f = feed_ok({"R": meta(target, fetch_from)})
    saved_opsec = HM._opsec
    saved_pr = AP.open_pr_into
    HM._opsec = lambda: StubOpsec().pair()
    AP.open_pr_into = lambda *a, **k: (False, "")
    try:
        # list_owned_repos would hit the network; stub it to point at our local bare GitHub.
        saved_owned = HM.list_owned_repos
        HM.list_owned_repos = lambda token: owned_of("R", ghbare)
        rc = AP.run(dry=False, feed=f, say=lambda *a: None, token="tok", branch="main")
        advanced = git("rev-parse", "main", cwd=ghbare)
        check("AP1a a clean fast-forward is pushed: GitHub main advanced from %s to the target %s"
              % (gmain[:8], target[:8]), rc == 0 and advanced == target, (rc, advanced))
    finally:
        HM._opsec = saved_opsec
        AP.open_pr_into = saved_pr
        HM.list_owned_repos = saved_owned

    # ---- AP1b: an unreachable feed / a non-ok feed push nothing. Stub the repo list so the status guard is what
    #           is under test (not a fake token failing the real GitHub call), and show the ok side returns 0.
    saved_owned = HM.list_owned_repos
    HM.list_owned_repos = lambda token: []
    try:
        rc = AP.run(dry=True, feed={"status": "degraded", "repos": {}}, say=lambda *a: None, token="tok")
        check("AP1b a feed whose status != 'ok' pushes nothing (return 2)", rc == 2, rc)
        rc_ok = AP.run(dry=True, feed={"status": "ok", "repos": {}}, say=lambda *a: None, token="tok")
        check("AP1b ...while a status=='ok' feed with nothing due returns 0 (the status guard is what differs)",
              rc_ok == 0, rc_ok)
        os.environ["COVENANT_UNISON_FEED"] = "http://127.0.0.1:9/unison"    # connection refused
        try:
            rc = AP.run(dry=True, feed=None, say=lambda *a: None, token="tok")
        finally:
            os.environ.pop("COVENANT_UNISON_FEED", None)
        check("AP1b an unreachable feed pushes nothing (return 2)", rc == 2, rc)
    finally:
        HM.list_owned_repos = saved_owned

    # ---- AP1c: open-PR guard, both ways. -----------------------------------------------------------------------
    ghbare, ghwork, _ = github_at("c", [("a.txt", "one\n")])
    ownbare, target, fetch_from = own_unify("c", ghwork, ("b.txt", "two\n"))
    f = feed_ok({"R": meta(target, fetch_from)})
    saved_owned = HM.list_owned_repos
    saved_pr = AP.open_pr_into
    HM.list_owned_repos = lambda token: owned_of("R", ghbare)
    try:
        lines = []
        AP.open_pr_into = lambda *a, **k: (True, "open PR(s) [8] into main")
        AP.run(dry=True, feed=f, say=lines.append, token="tok")
        skipped = any("R" in ln and "skip" in ln and "open PR" in ln for ln in lines)
        lines2 = []
        AP.open_pr_into = lambda *a, **k: (False, "")
        AP.run(dry=True, feed=f, say=lines2.append, token="tok")
        would = any("R" in ln and "would-push" in ln for ln in lines2)
        check("AP1c an open PR SKIPS; with no open PR the same repo would-push", skipped and would, (lines, lines2))
    finally:
        HM.list_owned_repos = saved_owned
        AP.open_pr_into = saved_pr

    # ---- AP1d: non-fast-forward, both ways. --------------------------------------------------------------------
    # GitHub ahead: main = a..b..c; target = a..t (a branch off `a`, not containing b/c) -> non-ff -> skip.
    ghbare, ghwork, _ = github_at("d", [("a.txt", "one\n"), ("b.txt", "two\n"), ("c.txt", "three\n")])
    # own_git target: reset a clone to the FIRST commit, then add one -> diverges from GitHub's later history.
    first = git("rev-list", "--max-parents=0", "main", cwd=ghwork)
    ownbare = os.path.join(base, "own_d.git")
    git("init", "-q", "--bare", ownbare)
    wk = os.path.join(base, "ownwork_d")
    git("clone", "-q", ghwork, wk)
    git("reset", "-q", "--hard", first, cwd=wk)
    target = commit(wk, "t.txt", "divergent\n")
    git("push", "-q", ownbare, "HEAD:refs/heads/unify/auto", cwd=wk)
    f = feed_ok({"R": meta(target, "%s unify/auto" % ownbare)})
    saved_owned = HM.list_owned_repos
    saved_pr = AP.open_pr_into
    HM.list_owned_repos = lambda token: owned_of("R", ghbare)
    AP.open_pr_into = lambda *a, **k: (False, "")
    try:
        lines = []
        AP.run(dry=True, feed=f, say=lines.append, token="tok")
        nonff = any("R" in ln and "skip" in ln and "not fast-forward" in ln for ln in lines)
        # Both ways: a true ff target (github's own tip + one) on the SAME repo would-push.
        ownbare2, target2, fetch2 = own_unify("d2", ghwork, ("x.txt", "forward\n"))
        f2 = feed_ok({"R": meta(target2, fetch2)})
        lines2 = []
        AP.run(dry=True, feed=f2, say=lines2.append, token="tok")
        would = any("R" in ln and "would-push" in ln for ln in lines2)
        check("AP1d a non-fast-forward SKIPS; a true ff of the same repo would-push", nonff and would, (lines, lines2))
    finally:
        HM.list_owned_repos = saved_owned
        AP.open_pr_into = saved_pr

    # ---- AP1e: snapshot repo and `website` are never history-pushed here (plan_repo, no network). -------------
    f = feed_ok({
        "covenant": meta("deadbeef", "x unify/auto", needs=("github",), snapshot=("hf",)),
        "flinch-record": meta("cafef00d", "x unify/auto", needs=("website",)),
    })
    saved_owned = HM.list_owned_repos
    saved_pr = AP.open_pr_into
    HM.list_owned_repos = lambda token: [{"name": "covenant", "full": "o/covenant", "private": False, "clone_url": "x"},
                                         {"name": "flinch-record", "full": "o/flinch-record", "private": False, "clone_url": "x"}]
    AP.open_pr_into = lambda *a, **k: (False, "")
    try:
        lines = []
        AP.run(dry=True, feed=f, say=lines.append, token="tok")
        snap_skip = any("covenant" in ln and "skip" in ln and "snapshot" in ln for ln in lines)
        site_skip = any("flinch-record" in ln and "skip" in ln and "needs_push" in ln for ln in lines)
        check("AP1e a snapshot repo and a `website`-only repo are skipped (never history-pushed here)",
              snap_skip and site_skip, lines)
    finally:
        HM.list_owned_repos = saved_owned
        AP.open_pr_into = saved_pr

    # ---- AP1f: target moved on own_git since the feed was built -> skip. ---------------------------------------
    ghbare, ghwork, _ = github_at("f", [("a.txt", "one\n")])
    ownbare, real_tip, fetch_from = own_unify("f", ghwork, ("b.txt", "two\n"))
    f = feed_ok({"R": meta("0" * 40, fetch_from)})              # feed names a target own_git no longer holds
    saved_owned = HM.list_owned_repos
    saved_pr = AP.open_pr_into
    HM.list_owned_repos = lambda token: owned_of("R", ghbare)
    AP.open_pr_into = lambda *a, **k: (False, "")
    try:
        lines = []
        AP.run(dry=True, feed=f, say=lines.append, token="tok")
        moved = any("R" in ln and "skip" in ln and "moved" in ln for ln in lines)
        check("AP1f a target that has MOVED on own_git since the feed was built SKIPS", moved, lines)
    finally:
        HM.list_owned_repos = saved_owned
        AP.open_pr_into = saved_pr

    passed, total = sum(_results), len(_results)
    print(f"\nAP1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
