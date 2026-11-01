#!/usr/bin/env python3
"""tools/hf_mirror.py -- mirror our GitHub repos to Hugging Face, PRESERVING VISIBILITY.

His instruction 2026-10-26: "put all of our repos on Hugging Face also" -> "Preserve visibility,
include everything." A GitHub-PUBLIC repo becomes a PUBLIC HF repo; a GitHub-PRIVATE repo becomes a
PRIVATE HF repo. Nothing is made newly public: visibility is READ from GitHub, never guessed, so a repo
that is private for a reason (water-food-air is HELD; the collective; the private artifact repo) can only
ever land as a PRIVATE HF mirror.

HOW IT STAYS FAITHFUL. It enumerates the account's OWN repos from the GitHub API (forks excluded -- an
upstream clone of someone else's project is not ours), then CLONES EACH FRESH from GitHub into a temp dir
and pushes that to HF. It does not trust a local working copy, which can be stale or (measured 2026-10-26
for the local covenant-satc dir) point at the wrong origin. The HF mirror therefore equals the GitHub
repo exactly.

NEEDS, to push:
  - an HF WRITE token: env HF_TOKEN, or a cached `hf auth login`.
  - GitHub read/clone: env GITHUB_TOKEN/GH_TOKEN, or COVENANT_GH_READ=1 to use the credential git already
    holds for github.com (opt-in, same pattern as covenant_github_judge).

USE
  COVENANT_GH_READ=1 python tools/hf_mirror.py --dry-run     # list repos + visibility, touch nothing
  HF_TOKEN=... COVENANT_GH_READ=1 python tools/hf_mirror.py   # clone each, create matching HF repo, push
Tokens are never printed and are passed to git via an Authorization header, not a logged URL.

FIXED 2026-10-31 (his words: "fix hf_mirror.py"). As first written this did `push --force` of every repo's FULL
history from a temporary clone with NO pre-push hook. That bypassed his opsec guard entirely: it would have
published covenant's 3,923 pre-guard identifiers and threefold-memory's personal Wi-Fi name on Hugging Face, and
erased every HF-only commit (model cards, LICENSE) -- measured in A396. Now:
  - guarded_push() reads what HF holds and refuses any branch or tag that would not FAST-FORWARD (HF diverged:
    unify first, never overwrite);
  - it runs his opsec scan over everything the push would send that HF does not already hold, and refuses on any
    hit;
  - it pushes WITHOUT --force;
  - SNAPSHOT_ONLY repos are never git-pushed. Their HF copy is a snapshot of GitHub main's files through the HF
    upload API (HF rejects binary files over git), opsec-scanned first, never their history.
Guard: test_hm1_hf_mirror.py.
LICENCE: public domain.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request


def _gh_token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t
    if os.environ.get("COVENANT_GH_READ", "").strip() not in ("1", "true", "yes"):
        return ""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    p = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n",
                       capture_output=True, text=True, env=env)
    for line in (p.stdout or "").splitlines():
        if line.startswith("password="):
            return line[9:].strip()
    return ""


def _api(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "User-Agent": "covenant-hf-mirror"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()), r.headers.get("Link", "")


def list_owned_repos(token):
    """Every repo the token's account OWNS, forks excluded. [{name, full, private, clone_url}]."""
    out, page = [], 1
    while True:
        batch, link = _api("https://api.github.com/user/repos?affiliation=owner&per_page=100&page=%d" % page, token)
        if not batch:
            break
        for d in batch:
            if d.get("fork"):
                continue                                        # an upstream clone of someone else's repo is not ours
            out.append({"name": d["name"], "full": d["full_name"],
                        "private": bool(d["private"]), "clone_url": d["clone_url"]})
        if 'rel="next"' not in (link or ""):
            break
        page += 1
    return out


def _auth_header(user, token):
    return "Authorization: Basic " + base64.b64encode(("%s:%s" % (user, token)).encode()).decode()


def _run(args, redact=None):
    p = subprocess.run(args, capture_output=True, text=True)
    err = (p.stderr or p.stdout or "")
    if redact:
        err = err.replace(redact, "***")
    return p.returncode == 0, err.strip()


def _hf_token():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if t:
        return t
    try:
        from huggingface_hub import get_token
        return get_token()
    except Exception:                                           # noqa: BLE001
        return None


# Repos whose HF copy is a SNAPSHOT of GitHub main's files, never their history (A396, 2026-10-31):
#   covenant          -- its history carries 3,923 of his identifiers from before the opsec guard existed;
#   threefold-memory  -- HF's history was squashed after his personal Wi-Fi name was removed, and the cleaned
#                        GitHub history still holds a (masked) binary that HF rejects over git.
SNAPSHOT_ONLY = {"covenant", "threefold-memory"}

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(args, cfg=()):
    p = subprocess.run(["git"] + list(cfg) + list(args), capture_output=True, text=True)
    return p.returncode == 0, (p.stdout or ""), (p.stderr or "")


def _opsec():
    """(opsec_scan module, his identifiers) or raises -- an unreadable private source is not 'nothing of his'."""
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import opsec_scan as O
    toks = O.gather(O.ROOT)
    if not toks or O.UNREADABLE:
        raise RuntimeError("his private identifier sources could not be read: NOT MEASURED")
    return O, toks


def guarded_push(dest, url, cfg=(), say=print, opsec=None, redact=None):
    """Push dest's branches and tags to url, FAST-FORWARD ONLY, behind his opsec scan. (pushed, reason).

    1. What url holds is read (ls-remote) and fetched into refs/hfmirror/*, so ancestry and the scan's exclusion
       are decided locally.
    2. A branch whose remote tip is not an ancestor of ours, or a tag that would move: REFUSED. HF diverged, so
       unify first; nothing on HF is overwritten.
    3. His opsec scan over every object the push would send that url does not already hold: any hit REFUSES.
    4. git push, never --force."""
    clean = (lambda s: s.replace(redact, "***")) if redact else (lambda s: s)
    cfg = list(cfg) + ["-c", "fetch.negotiationAlgorithm=noop"]
    ok, out, err = _git(["-C", dest, "ls-remote", url], cfg)
    if not ok:
        return False, "could not read what the remote holds: " + clean(err)[-200:]
    remote = {}
    for line in out.splitlines():
        sha, _t, ref = line.partition("\t")
        if ref.startswith(("refs/heads/", "refs/tags/")) and not ref.endswith("^{}"):
            remote[ref] = sha
    if remote:
        ok, _o, err = _git(["-C", dest, "fetch", "-q", url, "+refs/heads/*:refs/hfmirror/heads/*",
                            "+refs/tags/*:refs/hfmirror/tags/*"], cfg)
        if not ok:
            return False, "could not fetch what the remote holds: " + clean(err)[-200:]
    ok, out, _e = _git(["-C", dest, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/tags"])
    local = {ref: sha for ref, sha in (line.split(" ", 1) for line in out.splitlines() if " " in line)}
    lines = []
    for ref, sha in sorted(local.items()):
        rsha = remote.get(ref)
        if rsha and rsha != sha:
            if ref.startswith("refs/tags/"):
                return False, "tag %s would MOVE on the remote (%s -> %s): refused" % (ref, rsha[:8], sha[:8])
            anc = subprocess.run(["git", "-C", dest, "merge-base", "--is-ancestor", rsha, sha]).returncode == 0
            if not anc:
                return False, ("%s DIVERGED: the remote holds %s, which %s does not contain. Unify first; nothing "
                               "is overwritten" % (ref, rsha[:8], sha[:8]))
        lines.append("%s %s %s %s" % (ref, sha, ref, rsha or "0" * 40))
    if not lines:
        return False, "nothing to push"
    try:
        O, toks = opsec or _opsec()
    except Exception as e:                                       # noqa: BLE001
        return False, "opsec: %s" % e
    said = []
    if O.pre_push(lines, root=dest, toks=toks, remote=None, say=said.append) != 0:
        return False, "opsec REFUSED: " + " | ".join(s.strip() for s in said[:3])[:400]
    ok, _o, err = _git(["-C", dest, "push", url, "refs/heads/*:refs/heads/*", "refs/tags/*:refs/tags/*"], cfg)
    return (True, "pushed (fast-forward, opsec clean)") if ok else (False, "push failed: " + clean(err)[-200:])


def snapshot_to_hf(name, rev_dir, hf_id, token, say=print, opsec=None):
    """Upload the files in rev_dir (a checkout of GitHub main) as HF's tree for hf_id: files not in it are deleted
    on HF, HF's own .gitattributes is kept, and his opsec scan of every file runs first. Never history.
    (ok, reason)."""
    try:
        O, toks = opsec or _opsec()
    except Exception as e:                                       # noqa: BLE001
        return False, "opsec: %s" % e
    for dp, _d, fs in os.walk(rev_dir):
        for f in fs:
            data = open(os.path.join(dp, f), "rb").read()
            for c, v in toks:
                pat = O._pattern(c, v)
                if any(pat.search(data.decode(enc, "ignore")) for enc in ("utf-8", "utf-16-le")):
                    return False, "opsec REFUSED: %s carries a %s" % (os.path.relpath(os.path.join(dp, f), rev_dir), c)
    from huggingface_hub import HfApi, upload_folder
    api = HfApi(token=token)
    if ".gitattributes" in set(api.list_repo_files(hf_id, repo_type="model")) and \
            not os.path.exists(os.path.join(rev_dir, ".gitattributes")):
        with open(api.hf_hub_download(hf_id, ".gitattributes", repo_type="model", token=token), "rb") as src, \
                open(os.path.join(rev_dir, ".gitattributes"), "wb") as dst:
            dst.write(src.read())
    upload_folder(folder_path=rev_dir, repo_id=hf_id, repo_type="model", token=token, delete_patterns=["*"],
                  ignore_patterns=[".git", ".git/*"],
                  commit_message="Snapshot of %s main (full git history on GitHub)" % name)
    return True, "snapshot uploaded (files only, opsec clean)"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in argv
    say = print

    ght = _gh_token()
    if not ght:
        say("No GitHub token to read/clone repos. Set GITHUB_TOKEN, or COVENANT_GH_READ=1 to use git's "
            "stored github.com credential.")
        return 2
    try:
        repos = list_owned_repos(ght)
    except Exception as e:                                       # noqa: BLE001
        say("Could not list GitHub repos: %s: %s" % (type(e).__name__, str(e)[:160]))
        return 2
    repos.sort(key=lambda r: (r["private"], r["name"]))

    hft = hf_user = None
    if not dry:
        hft = _hf_token()
        if not hft:
            say("No HF token. Set HF_TOKEN or run `hf auth login`, then re-run. (Nothing was pushed.)")
            return 2
        from huggingface_hub import HfApi, create_repo
        hf_user = HfApi(token=hft).whoami().get("name")
        say("HF account: %s" % hf_user)

    say("%-30s %-9s -> HF" % ("REPO (%d owned, forks excluded)" % len(repos), "GITHUB"))
    done = 0
    for r in repos:
        vis = "private" if r["private"] else "public"
        how = "snapshot (files only)" if r["name"] in SNAPSHOT_ONLY else "fast-forward push"
        say("%-30s %-9s -> HF private=%s, %s" % (r["name"], vis, r["private"], how))
        if dry:
            continue
        from huggingface_hub import create_repo
        hf_id = "%s/%s" % (hf_user, r["name"])
        try:
            create_repo(hf_id, repo_type="model", private=r["private"], exist_ok=True, token=hft)
        except Exception as e:                                   # noqa: BLE001
            say("    FAILED to create %s: %s" % (hf_id, str(e)[:160]))
            continue
        staging = tempfile.mkdtemp(prefix="hfmirror-")
        try:
            auth_gh = "http.extraHeader=" + _auth_header("x-access-token", ght)
            if r["name"] in SNAPSHOT_ONLY:
                work = os.path.join(staging, r["name"])
                okc, errc = _run(["git", "-c", auth_gh, "clone", "--depth", "1", r["clone_url"], work], redact=ght)
                if not okc:
                    say("    FAILED to clone %s: %s" % (r["full"], errc[-200:]))
                    continue
                oks, why = snapshot_to_hf(r["name"], work, hf_id, hft, say=say)
            else:
                dest = os.path.join(staging, r["name"] + ".git")
                okc, errc = _run(["git", "-c", auth_gh, "clone", "--mirror", r["clone_url"], dest], redact=ght)
                if not okc:
                    say("    FAILED to clone %s: %s" % (r["full"], errc[-200:]))
                    continue
                # Real branches + tags only, NOT GitHub's internal refs/pull/* -- HF's pre-receive hook rejects
                # those (measured 2026-10-26). guarded_push sends refs/heads/* and refs/tags/* only.
                for ref in _git(["-C", dest, "for-each-ref", "--format=%(refname)", "refs/pull"])[1].split():
                    _git(["-C", dest, "update-ref", "-d", ref])
                oks, why = guarded_push(dest, "https://huggingface.co/%s" % hf_id,
                                        cfg=["-c", "http.extraHeader=" + _auth_header(hf_user, hft)],
                                        say=say, redact=hft)
            say("    %s %s: %s" % ("OK  " if oks else "HELD", hf_id, why))
            done += bool(oks)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    if not dry:
        say("mirrored %d of %d repo(s) to Hugging Face (visibility preserved)" % (done, len(repos)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
