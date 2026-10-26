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
        say("%-30s %-9s -> HF private=%s" % (r["name"], vis, r["private"]))
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
            dest = os.path.join(staging, r["name"] + ".git")
            okc, errc = _run(["git", "-c", "http.extraHeader=" + _auth_header("x-access-token", ght),
                              "clone", "--mirror", r["clone_url"], dest], redact=ght)
            if not okc:
                say("    FAILED to clone %s: %s" % (r["full"], errc[-200:]))
                continue
            okp, errp = _run(["git", "-C", dest, "-c", "http.extraHeader=" + _auth_header(hf_user, hft),
                              "push", "--mirror", "https://huggingface.co/%s" % hf_id], redact=hft)
            if okp:
                say("    OK  pushed %s (private=%s)" % (hf_id, r["private"]))
                done += 1
            else:
                say("    FAILED to push %s: %s" % (hf_id, errp[-200:]))
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    if not dry:
        say("mirrored %d of %d repo(s) to Hugging Face (visibility preserved)" % (done, len(repos)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
