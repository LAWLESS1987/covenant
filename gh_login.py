#!/usr/bin/env python3
"""gh_login.py -- authenticate the GitHub CLI, then publish. 2026-08-27 (v2).

WHY v2. v1 handed the terminal straight to `gh` and stopped dead at gh's
"Press Enter to open github.com in your browser" prompt, in a console window
that Claude cannot type into and cannot even read (terminals are visible-and-
clickable only, and screenshots mask them). So the one-time code was printed
somewhere nobody could act on: L had to find the window, and Claude could not
help because it could not see the code.

v2 fixes the observability, not the authority:

  * gh's stdin gets the newline it is waiting for, so the browser opens by
    itself and that prompt stops being a dead end;
  * every line gh prints is streamed to the console AND to GH_LOGIN.txt, and
    the ONE-TIME CODE is extracted and written to GH_CODE.txt on its own --
    a file can be read over the bridge, a masked console cannot;
  * afterwards it POLLS `gh auth status` instead of assuming, because a login
    that was abandoned in the browser still leaves the process exiting quietly.

WHAT IS STILL YOURS, and this part is not a limitation to be engineered around:
the browser asks YOU to approve, and the token is issued in YOUR name. Claude
does not type it, see it, or store it. All v2 does is put the code where you
can be told it.

Then, only if `gh auth status` actually passes, it chains into github_push.py.

Run: GH_LOGIN.bat
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
LOG = os.path.join(HERE, "GH_LOGIN.txt")
CODE_FILE = os.path.join(HERE, "GH_CODE.txt")
CODE_RE = re.compile(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b")
POLL_S = 240


def main():
    fh = open(LOG, "w", encoding="utf8", errors="replace")

    def say(s=""):
        print(s, flush=True)
        fh.write(s + "\n")
        fh.flush()

    try:
        from github_push import find_gh
    except Exception as e:
        say("  Could not import find_gh from github_push.py: %r" % (e,))
        return 1

    say("gh_login v2 -- authenticate the GitHub CLI as you, then publish")
    say("")
    gh, how = find_gh()
    if not gh:
        say("  gh could not be located (%s)." % how)
        say("  Use GitHub Desktop instead:")
        say("      File -> Add local repository -> %s" % HERE)
        say("      Publish repository, KEEPING \"private\" ticked.")
        return 1
    say("  gh: %s" % how)

    already = subprocess.run([gh, "auth", "status"], capture_output=True, text=True)
    if already.returncode == 0:
        say("  Already authenticated. Skipping the login.")
    else:
        say("")
        say("  " + "-" * 66)
        say("  Starting the web login. Your browser will open BY ITSELF --")
        say("  gh's Enter prompt is answered for you, because that prompt was")
        say("  a dead end in a window nobody could type into.")
        say("")
        say("  THE ONE-TIME CODE APPEARS BELOW and is also written to")
        say("  GH_CODE.txt. Paste it in the browser and approve. That approval")
        say("  is yours: the token is issued in your name.")
        say("  " + "-" * 66)
        say("")
        try:
            os.remove(CODE_FILE)
        except OSError:
            pass
        proc = subprocess.Popen(
            [gh, "auth", "login", "--hostname", "github.com",
             "--git-protocol", "https", "--web"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf8",
            errors="replace", bufsize=1, cwd=HERE)
        try:
            proc.stdin.write("\n")
            proc.stdin.flush()
        except Exception:
            pass
        code_seen = None
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    say("  gh| " + line)
                m = CODE_RE.search(line)
                if m and not code_seen:
                    code_seen = m.group(1)
                    with open(CODE_FILE, "w", encoding="utf8") as cf:
                        cf.write(code_seen + "\n")
                    say("")
                    say("  >>> ONE-TIME CODE: %s   (also in GH_CODE.txt)" % code_seen)
                    say("")
        except Exception as e:
            say("  (stopped reading gh output: %r)" % (e,))
        try:
            proc.wait(timeout=POLL_S)
        except subprocess.TimeoutExpired:
            say("  gh did not exit within %ds." % POLL_S)

        # VERIFY. An abandoned browser approval still lets the process exit.
        say("")
        say("  Checking whether the login actually took ...")
        ok = False
        deadline = time.time() + 60
        while time.time() < deadline:
            if subprocess.run([gh, "auth", "status"],
                              capture_output=True, text=True).returncode == 0:
                ok = True
                break
            time.sleep(3)
        if not ok:
            say("  NOT authenticated. Nothing was published.")
            say("  The code was %s -- if the browser is still open, approve it"
                % (code_seen or "not captured"))
            say("  and re-run GH_LOGIN.bat.")
            return 1
        say("  Authenticated.")

    say("")
    say("  " + "=" * 66)
    say("  Handing over to github_push.py -- private by default.")
    say("  " + "=" * 66)
    say("")
    fh.close()
    return subprocess.run([sys.executable, os.path.join(HERE, "github_push.py")]
                          + sys.argv[1:]).returncode


if __name__ == "__main__":
    sys.exit(main())
