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


SCAN_ROOTS = [
    os.environ.get("ProgramFiles", r"C:\Program Files"),
    os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    os.environ.get("LOCALAPPDATA", ""),
    os.environ.get("APPDATA", ""),
    os.environ.get("ProgramData", r"C:\ProgramData"),
    os.path.expanduser("~"),
]
SCAN_SKIP = {"Windows", "WindowsApps", "node_modules", "__pycache__", ".git",
             ".venv", "Temp", "INetCache", "Package Cache", "Installer",
             "Microsoft SDKs", "dotnet", "Docker", "WSL"}


def scan_for_gh(deadline_s=25.0):
    """Walk the places software actually lands, bounded in time and depth.

    Written because the fast checks said "not installed" on a machine where
    the owner said it was. A check whose negative answer is not trustworthy is
    worse than no check: it sends you off fixing the wrong thing.
    """
    import time as _t
    t0 = _t.time()
    for root in SCAN_ROOTS:
        if not root or not os.path.isdir(root):
            continue
        base_depth = root.rstrip("\\/").count(os.sep)
        for dp, dns, fns in os.walk(root):
            if _t.time() - t0 > deadline_s:
                return None, "scan hit its %.0fs budget" % deadline_s
            if dp.count(os.sep) - base_depth >= 4:
                dns[:] = []
                continue
            dns[:] = [d for d in dns if d not in SCAN_SKIP
                      and not d.startswith(".")]
            for fn in fns:
                if fn.lower() == "gh.exe":
                    return os.path.join(dp, fn), "found by scan"
    return None, "not found by scan either"


def find_gh():
    """PATH, then known install paths, then an actual bounded filesystem scan."""
    found = shutil.which("gh")
    if found:
        return found, "on PATH (%s)" % found
    for c in GH_CANDIDATES:
        if c and os.path.isfile(c):
            return c, "not on PATH, found at %s" % c
    say("   gh not on PATH or at a known location -- scanning (up to 25s) ...")
    found, how = scan_for_gh()
    if found:
        return found, "%s: %s" % (how, found)
    return None, how


def find_github_desktop():
    for c in (os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop\GitHubDesktop.exe"),
              os.path.expandvars(r"%ProgramData%\%USERNAME%\GitHubDesktop"),
              r"C:\ProgramData\Lawre\GitHubDesktop"):
        if c and os.path.exists(c):
            return c
    return None


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
    # MEASURED FIRST, ACTED ON LAST. The first version refused here and
    # returned, which meant a dirty tree hid the answer to "is gh installed?"
    # -- the very question the run was for. Diagnose everything, then refuse
    # only the irreversible act. A check that suppresses a diagnosis is a
    # check that sends you off fixing the wrong thing.
    say("1. Is the working tree clean?")
    p = run(["git", "--no-optional-locks", "status", "--porcelain"])
    if p.returncode != 0:
        say("   Could not ask git. Is this a repository?")
        return 1
    dirty = [l for l in (p.stdout or "").splitlines() if l.strip()]
    if dirty:
        say("   NO -- %d entry(ies). Nothing will be pushed, but the rest of" % len(dirty))
        say("   this run still reports what it finds:")
        for l in dirty[:25]:
            say("     " + l)
        if len(dirty) > 25:
            say("     ... %d more" % (len(dirty) - 25))
        say("   Run GIT_SETUP.bat if these are today's changes.")
    else:
        say("   yes.")
    head = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    tree = run(["git", "rev-parse", "--short", "HEAD^{tree}"]).stdout.strip()
    say("   %s at %s (tree %s)" % (branch, head, tree))

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
        say("   No remote, and gh could not be located anywhere.")
        gd = find_github_desktop()
        if gd:
            say()
            say("   BUT GitHub Desktop IS here: %s" % gd)
            say("   GitHub Desktop and the GitHub CLI are different programs --")
            say("   Desktop does not provide `gh`. Desktop can publish this")
            say("   repository itself, in four clicks and no typing:")
            say("       1. open GitHub Desktop")
            say("       2. File -> Add local repository -> %s" % HERE)
            say("       3. Publish repository")
            say("       4. LEAVE \"Keep this code private\" TICKED, then Publish")
            say("   That is the shortest route from here.")
        say()
        say("   Or, without Desktop:")
        say("     0) if you JUST installed gh, this window's PATH predates it --")
        say("        close this window, open a new one, and re-run.")
        say("     a) create an empty repo at https://github.com/new, then:")
        say("          GITHUB_PUSH.bat --remote https://github.com/<you>/covenant.git")
        say("     b) install the GitHub CLI, `gh auth login`, re-run this.")
        say("   I will not create an account or handle a password.")
        say()
        say("   transcript: %s" % TRANSCRIPT)
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
        say("   transcript: %s" % TRANSCRIPT)
        return 0

    if dirty:
        say()
        say("   REFUSING TO PUSH: the working tree is dirty (listed above).")
        say("   Everything else in this report stands; only the push is refused.")
        say("   Run GIT_SETUP.bat, then re-run this.")
        say()
        say("   transcript: %s" % TRANSCRIPT)
        return 1

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
