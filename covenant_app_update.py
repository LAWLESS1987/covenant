#!/usr/bin/env python3
"""covenant_app_update.py -- the PC keeps the newest phone-app build so the
phone can update itself from the PC (asked 2026-09-13: "set it up to auto
update").

WHY THE PC AND NOT GITHUB. The app lives in the operator's PRIVATE
repository; fetching its build needs his GitHub credential, and that
credential belongs on this PC (git already holds it), never on the phone. So
the nightly pass -- or `--fetch` -- downloads the newest green build's
artifact with that credential, keeps it under ops/app/ (gitignored), and the
node serves it to a SIGNED GET from a registered signer: /app/latest (what
build, its sha256) and /app/apk (the bytes). The phone asks on its heartbeat,
downloads when the build's sha is not its own, checks the sha256, and hands
it to Android's installer, which asks the person holding the phone before
anything is installed. Nothing installs silently; nothing is served to an
unsigned caller.

USE
  python covenant_app_update.py --fetch     # newest green build of covenant-phone -> ops/app/
  python covenant_app_update.py --show
LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.environ.get("COVENANT_PHONE_REPO", "LAWLESS1987/covenant-phone")
ARTIFACT = "covenant-node-apk"
DIR = os.path.join(HERE, "ops", "app")
LATEST = os.path.join(DIR, "latest.json")
KEEP = 3


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _get_json(path, tok):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json", "User-Agent": "covenant-app-update"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _download(url, tok):
    """An artifact archive: a 302 to blob storage that rejects the token, so follow it bare."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok, "User-Agent": "covenant-app-update"})
    try:
        return opener.open(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            with urllib.request.urlopen(urllib.request.Request(e.headers["Location"], headers={"User-Agent": "covenant-app-update"}), timeout=300) as r:
                return r.read()
        raise


def latest():
    try:
        with open(LATEST, encoding="utf-8") as fh:
            d = json.load(fh)
        p = os.path.join(DIR, d.get("file", ""))
        if not os.path.isfile(p):
            return None
        d["path"] = p
        return d
    except (OSError, ValueError):
        return None


def fetch(say=print):
    """The newest green build's APK from the private repository, kept under ops/app/.
    Returns the latest.json dict, or None with the reason said."""
    import covenant_github_judge as gh
    tok = gh.token()
    if not tok:
        say("app update: no GitHub credential on this PC"); return None
    runs = _get_json("/repos/%s/actions/runs?status=success&branch=main&per_page=5" % REPO, tok).get("workflow_runs", [])
    for run in runs:
        arts = [a for a in _get_json("/repos/%s/actions/runs/%d/artifacts" % (REPO, run["id"]), tok).get("artifacts", []) if a["name"] == ARTIFACT and not a.get("expired")]
        if not arts:
            continue
        sha7 = run["head_sha"][:7]
        cur = latest()
        if cur and cur.get("sha") == run["head_sha"]:
            say("app update: already have the newest build %s" % sha7); return cur
        blob = _download(arts[0]["archive_download_url"], tok)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            apk = z.read("covenant-node.apk")
        os.makedirs(DIR, exist_ok=True)
        fname = "covenant-node-%s.apk" % sha7
        with open(os.path.join(DIR, fname), "wb") as fh:
            fh.write(apk)
        d = {"sha": run["head_sha"], "sha7": sha7, "run_id": run["id"], "run_url": run["html_url"], "built": run["updated_at"],
             "fetched": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "file": fname, "size": len(apk), "sha256": hashlib.sha256(apk).hexdigest()}
        tmp = LATEST + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1)
        os.replace(tmp, LATEST)
        for old in sorted((f for f in os.listdir(DIR) if f.startswith("covenant-node-") and f.endswith(".apk")), key=lambda f: os.path.getmtime(os.path.join(DIR, f)))[:-KEEP]:
            os.remove(os.path.join(DIR, old))
        say("app update: fetched build %s (%d bytes, sha256 %s)" % (sha7, len(apk), d["sha256"][:12]))
        return d
    say("app update: no green build with an artifact in the last five runs"); return None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--show", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        return 0 if fetch() else 2
    d = latest()
    print(json.dumps({k: v for k, v in d.items()} if d else {"latest": None, "hint": "python covenant_app_update.py --fetch"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
