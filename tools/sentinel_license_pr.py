#!/usr/bin/env python3
"""Open a PR adding the Apache-2.0 LICENSE to Sentinel-Witness (its branch-protection rule blocks a direct
push to main). Pushes a branch via the system git credential, then opens the PR via the GitHub API; if the
API token can't be read non-interactively, prints the one-click compare URL instead. One-off, not committed."""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request as U

sys.path.insert(0, r"C:\Users\Lawre\covenant\tools")
import hf_mirror as M

OWNER, REPO, BRANCH, BASE = "LAWLESS1987", "Sentinel-Witness", "add-apache-2.0-license", "main"


def main():
    with U.urlopen("https://raw.githubusercontent.com/%s/covenant/main/LICENSE" % OWNER, timeout=20) as r:
        apache = r.read().decode("utf-8", "replace")
    d = tempfile.mkdtemp(prefix="selic-")
    work = os.path.join(d, REPO)
    env = dict(os.environ); env["GIT_TERMINAL_PROMPT"] = "0"
    c = subprocess.run(["git", "clone", "--depth", "1", "--single-branch", "--branch", BASE,
                        "https://github.com/%s/%s.git" % (OWNER, REPO), work], capture_output=True, text=True)
    if c.returncode != 0:
        print("clone FAILED:", (c.stderr or "")[-200:]); return 1
    if os.path.exists(os.path.join(work, "LICENSE")):
        print("already has LICENSE on GitHub -- nothing to do"); return 0
    with open(os.path.join(work, "LICENSE"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(apache)
    subprocess.run(["git", "-C", work, "checkout", "-b", BRANCH], capture_output=True, text=True)
    subprocess.run(["git", "-C", work, "add", "LICENSE"], capture_output=True, text=True)
    subprocess.run(["git", "-C", work, "commit", "-m", "Add Apache-2.0 LICENSE"], capture_output=True, text=True)
    p = subprocess.run(["git", "-C", work, "push", "-u", "origin", BRANCH], capture_output=True, text=True, env=env)
    if p.returncode != 0:
        print("branch push FAILED:", (p.stderr or "")[-250:]); return 1
    print("branch pushed:", BRANCH)

    tok = M._gh_token()
    if tok:
        body = json.dumps({"title": "Add Apache-2.0 LICENSE",
                           "head": BRANCH, "base": BASE,
                           "body": "Adds the Apache-2.0 LICENSE to match the other public repos in the system. "
                                   "(A direct push to main is blocked by this repo's branch-protection rule, "
                                   "so this comes as a PR.)"}).encode()
        req = U.Request("https://api.github.com/repos/%s/%s/pulls" % (OWNER, REPO), data=body,
                        headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                                 "User-Agent": "covenant-pr", "Content-Type": "application/json"})
        try:
            with U.urlopen(req, timeout=30) as r:
                pr = json.loads(r.read())
            print("PR OPENED:", pr.get("html_url"))
        except Exception as e:                                  # noqa: BLE001
            print("PR API failed (%s); open it here:" % str(e)[-120:])
            print("  https://github.com/%s/%s/compare/%s...%s?expand=1" % (OWNER, REPO, BASE, BRANCH))
    else:
        print("No API token non-interactively; branch is pushed -- open the PR with one click here:")
        print("  https://github.com/%s/%s/compare/%s...%s?expand=1" % (OWNER, REPO, BASE, BRANCH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
