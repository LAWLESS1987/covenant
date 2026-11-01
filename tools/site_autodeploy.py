#!/usr/bin/env python3
"""tools/site_autodeploy.py -- keep lawless1987.com/repos in step with GitHub, from the laptop (2026-10-31).

His words: "the site should be synced auto too", and his choice of where it runs: "Laptop job". The feed is
TETSU's unison checker (tailnet only; its URL is in the gitignored ops/local_unison_feed.txt or the env var
COVENANT_UNISON_FEED -- his network addresses never go in this public repo). Its `site_deploy_due` lists the repos
whose website copy is behind GitHub, counted only once GitHub has reached the unison target.

ONE PASS, and every step can refuse:
  1. The feed. Unreachable, empty or without `site_deploy_due`: NOTHING is done, and the log says so. It never
     deploys blind.
  2. Nothing due: done.
  3. For every repo it names, GitHub main is read HERE (git ls-remote) and must equal the feed's target. A feed
     that is wrong or stale cannot publish a half-sync.
  4. scripts/mirror-repos.py regenerates every repo copy from GitHub.
  5. His opsec scan over the FULL history of every regenerated .git, excluding nothing (the site serves clones).
     Any hit refuses the deploy, and that is the step that would have caught the Wi-Fi name.
  6. The site's own build and tests.
  7. wrangler deploy, through the cached login (his OAuth, made once).
  8. Verify: for every repo, the site's advertised main equals GitHub's main.
Each pass appends one line to ops/site_autodeploy.jsonl (gitignored) with what it did or why it refused.

    python tools/site_autodeploy.py            # one pass
    python tools/site_autodeploy.py --dry-run  # steps 1-3 only; never regenerates or deploys
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_FEED = os.path.join(HERE, "ops", "local_unison_feed.txt")


def feed_url():
    """The feed's URL: env COVENANT_UNISON_FEED, else the first line of the gitignored ops/local_unison_feed.txt.
    None when neither is set -- then the feed is 'not ready' and nothing is done (same rule as ops/local_peers.txt:
    his addresses live in a private file, never in this public repo)."""
    url = os.environ.get("COVENANT_UNISON_FEED", "").strip()
    if url:
        return url
    try:
        with open(LOCAL_FEED, encoding="utf-8") as fh:
            return fh.readline().strip() or None
    except OSError:
        return None
SITE = r"C:\Users\Lawre\site\lawless1987-website-backup\website"
NODE_DIR = r"C:\Users\Lawre\site\nodejs\node-v24.22.1-win-x64"
LEDGER = os.path.join(HERE, "ops", "site_autodeploy.jsonl")
OWNER = "LAWLESS1987"
SITE_ORIGIN = "https://lawless1987.com/repos"


def read_feed(url=None, timeout=15):
    """The feed's JSON, or None when it cannot be read (or no URL is configured)."""
    url = url or feed_url()
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:                                           # noqa: BLE001 -- unreadable is "feed down"
        return None


def repo_entry(feed, name):
    """The feed's entry for one repo, whichever of the two layouts it uses."""
    repos = feed.get("repos")
    if isinstance(repos, dict) and isinstance(repos.get(name), dict):
        return repos[name]
    if isinstance(repos, list):
        for r in repos:
            if isinstance(r, dict) and r.get("name") == name:
                return r
    return feed.get(name) if isinstance(feed.get(name), dict) else None


def github_main(name):
    out = subprocess.run(["git", "ls-remote", "https://github.com/%s/%s.git" % (OWNER, name), "refs/heads/main"],
                         capture_output=True, text=True, timeout=120)
    return out.stdout.split()[0] if out.returncode == 0 and out.stdout.strip() else None


def site_main(name):
    out = subprocess.run(["git", "ls-remote", "%s/%s.git" % (SITE_ORIGIN, name), "refs/heads/main"],
                         capture_output=True, text=True, timeout=120)
    return out.stdout.split()[0] if out.returncode == 0 and out.stdout.strip() else None


def opsec_full_history(git_dir, remote=None):
    """(clean, detail): his opsec scan over what this deploy would PUBLISH: every object reachable from git_dir's
    refs that `remote` (the live site's copy of that repo) does not already hold -- the push guard's question.
    remote=None excludes nothing and scans the whole history.

    Why not always the whole history: covenant's history carries 3,923 of his identifiers from before the guard
    existed. They are already public on GitHub and on the site. A whole-history rule would refuse every deploy
    for ever and so publish nothing new either. After a history REWRITE (threefold-memory, 2026-10-31) the site
    holds none of the new objects, so the whole new history is scanned -- the case that matters."""
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import opsec_scan as O
    toks = O.gather(O.ROOT)
    if not toks or O.UNREADABLE:
        return False, "his private sources could not be read: NOT MEASURED"
    refs = subprocess.run(["git", "-C", git_dir, "for-each-ref", "--format=%(objectname)"],
                          capture_output=True, text=True).stdout.split()
    if not refs:
        return False, "no refs in %s" % git_dir
    out = []
    rc = O.pre_push(["refs/heads/x %s refs/heads/x %s" % (r, "0" * 40) for r in refs], root=git_dir, toks=toks,
                    remote=remote, say=out.append)
    return rc == 0, (out[0] if out else "no output")[:300]


def run_site(args, timeout=1500):
    env = dict(os.environ, PATH=NODE_DIR + os.pathsep + os.environ.get("PATH", ""))
    p = subprocess.run(args, cwd=SITE, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode == 0, ((p.stdout or "") + (p.stderr or ""))[-600:]


def regenerate():
    return run_site([os.path.join(HERE, ".venv", "Scripts", "python.exe"), "scripts/mirror-repos.py"])


def site_tests():
    node = os.path.join(NODE_DIR, "node.exe")
    ok, out = run_site([node, "scripts/build.mjs"])
    if not ok:
        return False, "build failed: " + out
    for s in ("check-links", "check-standalone", "check-spaces", "check-proposals"):
        ok, out = run_site([node, "scripts/%s.mjs" % s])
        if not ok:
            return False, "%s failed: %s" % (s, out)
    return True, "build and 4 checks passed"


def deploy():
    """(ok, text) -- text starts with wrangler's "Current Version ID" line, read from the WHOLE output (run_site
    keeps only the tail, and the version line can fall before it)."""
    node = os.path.join(NODE_DIR, "node.exe")
    env = dict(os.environ, PATH=NODE_DIR + os.pathsep + os.environ.get("PATH", ""))
    p = subprocess.run([node, "node_modules/wrangler/bin/wrangler.js", "deploy", "--config", "wrangler.json"],
                       cwd=SITE, capture_output=True, text=True, timeout=1500, env=env)
    out = (p.stdout or "") + (p.stderr or "")
    version = [ln.strip() for ln in out.splitlines() if "Version ID" in ln][-1:]
    return p.returncode == 0, "\n".join(version + [out[-600:]])


def one_pass(dry_run=False, feed_reader=read_feed, gh=github_main, site=site_main, regen=regenerate,
             scan=opsec_full_history, tests=site_tests, do_deploy=deploy, repos_dir=None):
    """One pass. Returns the ledger record. Every step can refuse, and nothing is published past a refusal."""
    rec = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "dry_run": dry_run}
    feed = feed_reader()
    # Only a COMPLETED pass counts: the feed reads {"status": "starting"} between a restart and its first pass.
    if (not isinstance(feed, dict) or feed.get("status") != "ok"
            or not isinstance(feed.get("site_deploy_due"), list)):
        rec.update(result="feed_not_ready", why="the unison feed was unreachable, not status ok, or had no "
                                                "site_deploy_due: nothing done (never deploy blind)")
        return rec
    due = [d for d in feed["site_deploy_due"] if isinstance(d, str)]
    rec["due"] = due
    if not due:
        rec.update(result="nothing_due")
        return rec
    for name in due:
        entry = repo_entry(feed, name) or {}
        target = str(entry.get("target") or "")
        actual = gh(name) or ""
        same = bool(target and actual) and (actual == target or (len(target) >= 7 and actual.startswith(target)))
        if not same:
            rec.update(result="refused_half_sync",
                       why="%s: GitHub main %s is not the feed's target %s -- not deploying a half-sync"
                           % (name, (actual or "?")[:12], str(target)[:12]))
            return rec
    if dry_run:
        rec.update(result="dry_run_ok")
        return rec
    ok, out = regen()
    if not ok:
        rec.update(result="refused_regenerate", why=out[-300:])
        return rec
    repos_dir = repos_dir or os.path.join(SITE, "public", "repos")
    for d in sorted(os.listdir(repos_dir)):
        if d.endswith(".git"):
            clean, detail = scan(os.path.join(repos_dir, d), remote="%s/%s" % (SITE_ORIGIN, d))
            if not clean:
                rec.update(result="refused_opsec", why="%s: %s" % (d, detail))
                return rec
    ok, out = tests()
    if not ok:
        rec.update(result="refused_tests", why=out[-300:])
        return rec
    ok, out = do_deploy()
    if not ok:
        rec.update(result="deploy_failed", why=out[-300:])
        return rec
    rec["deploy"] = [ln for ln in out.splitlines() if "Version ID" in ln][-1:] or ["(no version line)"]
    behind = [n for n in due if site(n) != gh(n)]
    rec.update(result="deployed" if not behind else "deployed_but_behind", behind=behind)
    return rec


LOCK = os.path.join(HERE, "ops", "site_autodeploy.lock")
LOCK_STALE_S = 3600


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    # One pass at a time: a scheduled pass that finds another still running does nothing and says so.
    # A lock older than an hour is from a pass that died; it is taken over, and that is recorded too.
    took_over = False
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        import time
        if time.time() - os.path.getmtime(LOCK) < LOCK_STALE_S:
            print(json.dumps({"result": "another_pass_running"}))
            return 0
        os.replace(LOCK, LOCK + ".stale")
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        took_over = True
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        rec = one_pass(dry_run="--dry-run" in argv)
    finally:
        os.replace(LOCK, LOCK + ".last")
    if took_over:
        rec["took_over_stale_lock"] = True
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))
    return 0 if rec["result"] in ("deployed", "nothing_due", "feed_not_ready", "dry_run_ok") else 1


if __name__ == "__main__":
    sys.exit(main())
