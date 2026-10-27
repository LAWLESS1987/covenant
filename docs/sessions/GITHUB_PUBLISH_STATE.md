# Publishing to GitHub — state as of 2026-08-27

Everything is built, committed and clean. `main` at `be25991`, working tree
empty, all eleven branches merged, CI workflow in place. **One step remains and
it is not one Claude can take.**

## The blocker, precisely

`gh` **is** installed — the PATH checks were wrong, and only a real filesystem
scan found it:

    %USERPROFILE%\AppData\Local\copilot-desktop-gh-2.96.0\gh.exe

It is the copy **bundled inside Copilot Desktop**, which is why it is not on
PATH and why `gh auth login` typed bare does not resolve. It is not
authenticated.

Authenticating issues a credential in L's name. Claude does not type, see or
store credentials — and separately cannot: terminals on this device are
grantable only at "click" tier, so Claude can see a console window and click in
it but cannot send a single keystroke. Both reasons stand on their own.

`GH_LOGIN.bat` was written to make this one double-click. It locates the
bundled binary, runs `gh auth login --hostname github.com --git-protocol https
--web`, **verifies with `gh auth status` afterwards rather than assuming**, and
only then chains into `github_push.py`. It is currently sitting at gh's
"Press Enter to open github.com in your browser" prompt in a Command Prompt
window, waiting for a keystroke.

## Two ways to finish, either is fine

**A — the console that is already open.** Click it, press Enter, paste the
one-time code in the browser, approve. It publishes by itself from there.

**B — GitHub Desktop, no terminal at all.** Already installed and already
OAuth-authorized:

    File -> Add local repository -> %USERPROFILE%\covenant
    Publish repository
    LEAVE "Keep this code private" TICKED -> Publish

**Private either way.** `holdings.txt` and `TRADING_POLICY.json` are untracked
as of `2dfe018` but remain in the *history*, so a public repo would expose ten
positions with quantities and average buy prices. `github_push.py` defaults to
`--private` and makes `--public` require a typed acknowledgement.

## Once it is up

* GitHub Actions runs `covenant_one.py --ci` on every push and PR, 3.11 and
  3.12 — the same file that runs on the box.
* A green tick is **not** a launch: it is the Linux half only. Run `ONE.bat` on
  the box first. A refused TCP connect costs 0.0 ms in CI and 2,045 ms there.
* `START_HERE.md` names the six launchers worth knowing; `UNISON.md` is the
  convention for two people working the same repo.

## Still outstanding

* Rewrite the history if this ever needs to be public.
* Nikolas Patrick Joseph Shoff — **no GitHub account found under that name.**
  The near matches ([nikolas](https://github.com/nikolas),
  [shoff](https://github.com/shoff), [hshoff](https://github.com/hshoff)) are
  different people. A branch was requested for his work; it needs a handle or a
  repo link first, and no one was contacted.
* The two false `/health` warnings, the A23/A12 backoff re-key, and the
  unpropagated v8.38/v8.39 core — see `docs/sessions/GITHUB_IMPROVEMENTS_2026-08-27.md`.
