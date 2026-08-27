#!/usr/bin/env python3
"""github_push.py -- publish this repository to GitHub. 2026-08-27.

IT USES YOUR CREDENTIALS, NEVER ANYONE ELSE'S. This script runs on your
machine and authenticates as you, through the GitHub CLI if you have it or
through Git Credential Manager if you don't. No token is typed into it, stored
by it, or visible to it.

BEFORE IT PUSHES ANYTHING IT REFUSES ON THREE CONDITIONS, and each one is a
thing that cannot be undone afterwards:

  1. THE WORKING TREE MUST BE CLEAN. Pushing a dirty tree publishes a state
     that was never committed and never tested. `git --no-optional-locks
     status --porcelain` must be empty -- the kernel's own dirty check, and
     --no-optional-locks so a read-only check takes no write lock.

  2. THE PORTFOLIO IS STILL IN THE HISTORY. holdings.txt and
     TRADING_POLICY.json were untracked on 2026-08-27, which protects every
     future commit and does NOTHING about the past. Anyone who clones this
     repository can read the exact quantities and average buy prices of ten
     holdings out of the old commits. PRIVATE is therefore the default, and
     --public requires typing a sentence that says you know this.

  3. IT WILL NOT CREATE AN ACCOUNT OR HANDLE A PASSWORD. If `gh` is not
     authenticated it stops and tells you the one command to run yourself.

Usage:
    python github_push.py                     private repo named after the folder
    python github_push.py --name covenant     choose the repository name
    python github_push.py --remote <url>      push to a repo you already made
    python github_push.py --public            requires the typed acknowledgement
    python github_push.py --dry-run           say exactly what it would do, do nothing
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
ACK = "I know the portfolio is in the history"
TRANSCRIPT = os.path.join(HERE, "GITHUB_PUSH.txt")
_fh = None

# gh is frequently installed somewhere PATH does not reach -- winget puts a
# shim under Links, the MSI puts the real binary under Program Files, and a
# cmd window opened BEFORE the install still carries the old PATH. Checking
# only shutil.which() reported "not installed" on a machine where it was.
GH_CANDIDATES = [
    r"C:\Program Files\GitHub CLI\gh.exe",
    r"C:\Program Files (x86)\GitHub CLI\gh.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\gh.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\GitHubCLI\gh.exe"),
    os.path.expandvars(r"%ProgramFiles%\GitHub CLI\gh.exe"),
    os.path.expandvars(r"%USERPROFILE%\scoop\shims\gh.exe"),
    r"C:\ProgramData\chocolatey\bin\gh.exe",
]


def find_gh():
    """PATH first, then the places installers actually put it."""
    found = shutil.which("gh")
    if found:
        return found, "on PATH"
    for c in GH_CANDIDATES:
        if c and os.path.isfile(c):
            return c, "not on PATH, found at %s" % c
    return None, "not on PATH and not at any known install location"


def run(args, check=False, capture=True):
    p = subprocess.run(args, cwd=HERE, capture_output=capture, text=True,
                       encoding="utf8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError("%s -> exit %d\n%s"
                           % (" ".join(args), p.returncode,
                              (p.stdout or "") + (p.stderr or "")))
    return p


def say(s=""):
    print(s, flush=True)
    if _fh:
        _fh.write(s + "\n")
        _fh.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=os.path.basename(os.path.abspath(HERE)))
    ap.add_argument("--remote", default=None)
    ap.add_argument("--public", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    say("github_push -- publish this repository, as you, deliberately")
    say("  folder: %s" % HERE)
    say()

    # ---------------------------------------------------------------- 1. clean
    say("1. Is the working tree clean?")
    p = run(["git", "--no-optional-locks", "status", "--porcelain"])
    dirty = [l for l in (p.stdout or "").splitlines() if l.strip()]
    if p.returncode != 0:
        say("   Could not ask git. Is this a repository?")
        return 1
    if dirty:
        say("   NO -- %d entry(ies). Pushing now would publish a state that was" % len(dirty))
        say("   never committed and never tested. Commit or ignore these first:")
        for l in dirty[:25]:
            say("     " + l)
        if len(dirty) > 25:
            say("     ... %d more" % (len(dirty) - 25))
        say()
        say("   Run GIT_SETUP.bat if these are today's changes.")
        return 1
    head = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    tree = run(["git", "rev-parse", "--short", "HEAD^{tree}"]).stdout.strip()
    say("   yes. %s at %s (tree %s)" % (branch, head, tree))

    # ------------------------------------------------------------ 2. visibility
    say()
    say("2. Visibility")
    if a.public:
        say("   YOU ASKED FOR PUBLIC, and the portfolio is still in the history.")
        say("   holdings.txt and TRADING_POLICY.json were untracked today; every")
        say("   commit before that still contains them, and a public repo means")
        say("   anyone can read the exact quantities and average buy prices of")
        say("   ten holdings. This cannot be undone by deleting the repo later --")
        say("   forks and caches outlive it.")
        say()
        say("   To go ahead, type this sentence exactly:")
        say("       %s" % ACK)
        try:
            typed = input("   > ").strip()
        except EOFError:
            typed = ""
        if typed != ACK:
            say("   Not matched. Nothing was pushed. Rewrite the history first if")
            say("   you want this public -- that is the real fix, not this prompt.")
            return 1
        visibility = "--public"
    else:
        visibility = "--private"
        say("   private (the default, and the right one while the history carries")
        say("   the portfolio).")

    # ------------------------------------------------------------- 3. transport
    say()
    say("3. How this authenticates")
    existing = run(["git", "remote", "get-url", "origin"])
    origin = existing.stdout.strip() if existing.returncode == 0 else None
    gh, gh_where = find_gh()
    say("   gh: %s" % gh_where)
    git_v = run(["git", "--version"])
    say("   git: %s" % (git_v.stdout or git_v.stderr or "?").strip())

    if a.remote:
        plan = ("set-remote", a.remote)
        say("   You gave a remote: %s" % a.remote)
        say("   Git Credential Manager will authenticate you on push.")
    elif origin:
        plan = ("push-existing", origin)
        say("   origin already set: %s" % origin)
        say("   Git Credential Manager will authenticate you on push.")
    elif gh:
        auth = run([gh, "auth", "status"])
        if auth.returncode != 0:
            say("   gh is installed but NOT authenticated. Run this yourself --")
            say("   it opens your browser and I never see the token:")
            say("       gh auth login")
            say("   then re-run this script.")
            return 1
        plan = ("gh-create", a.name)
        say("   gh is installed and authenticated. It will create the repository")
        say("   as you and push in one step.")
    else:
        say("   No remote, and gh could not be located. Two ways forward:")
        say("     0) if you just installed gh, this window's PATH predates it --")
        say("        close this window, open a NEW one, and re-run.")
        say("     a) create an empty repo on github.com, then re-run:")
        say("          python github_push.py --remote <url>")
        say("     b) install the GitHub CLI, run `gh auth login`, re-run this.")
        say("   I will not create an account or handle a password.")
        return 1

    # ----------------------------------------------------------------- 4. act
    say()
    say("4. Plan")
    kind, target = plan
    if kind == "gh-create":
        cmd = [gh, "repo", "create", target, visibility, "--source=.",
               "--remote=origin", "--push"]
    elif kind == "set-remote":
        cmd = ["git", "remote", "add", "origin", target]
    else:
        cmd = ["git", "push", "-u", "origin", branch]
    say("   %s" % " ".join(cmd))
    if kind == "set-remote":
        say("   git push -u origin %s" % branch)
    say("   pushing branch %s only. Other branches stay local until you say so." % branch)

    if a.dry_run:
        say()
        say("   --dry-run: nothing was done.")
        return 0

    say()
    say("5. Doing it")
    p = run(cmd, capture=False)
    if p.returncode != 0:
        say("   FAILED (exit %d). Nothing further was attempted." % p.returncode)
        return 1
    if kind == "set-remote":
        p = run(["git", "push", "-u", "origin", branch], capture=False)
        if p.returncode != 0:
            say("   push FAILED (exit %d). The remote is set; fix and re-run."
                % p.returncode)
            return 1

    say()
    url = run(["git", "remote", "get-url", "origin"]).stdout.strip()
    say("   pushed %s at %s to %s" % (branch, head, url or "origin"))
    say()
    say("   The other branches are still local. Push them deliberately:")
    say("       git push origin --all")
    say("   And the history still carries the portfolio. If this ever needs to")
    say("   be public, rewrite it FIRST.")
    say()
    say("   transcript: %s" % TRANSCRIPT)
    return 0


if __name__ == "__main__":
    _fh = open(TRANSCRIPT, "w", encoding="utf8", errors="replace")
    try:
        sys.exit(main())
    except Exception as e:
        say()
        say("STOPPED: %s" % e)
        sys.exit(1)
    finally:
        try:
            _fh.close()
        except Exception:
            pass
