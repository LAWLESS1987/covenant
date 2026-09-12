# Covenant Node for Android (mobile/app)

The same node the PC runs, inside a phone app. Asked 2026-09-12: "create an app
for this to run my phone ... use the git hub also for this ... give it the
ability to interact with my other apps".

## What you get

- The tracked launcher (`run_node.py` --
  it runs the distilled students plus the deterministic semantic judge, no
  model server), started with exactly the flags `mobile/covenant_phone.sh`
  passes, on CPython 3.12 inside a foreground service that Android 15 does
  not time out. Ports N, N+1 and N+11 on 0.0.0.0, N = 5000 by default.
- The node's files are staged from the repository at build time and carried
  as APK assets; nothing under `mobile/app` is a copy of the core.
- **Share in / share out.** Covenant appears in every app's Share sheet: share
  any text to it and the same gate the node uses judges it in the app, with a
  Share button to send the verdict on. "Share status" sends the node's health
  line and dashboard link. No new HTTP endpoint, nothing sent anywhere.
- Android only. iOS cannot host a node (see `mobile/TERMUX_SETUP.md`).

## Get it

- **Over a cable (recommended):** `mobile/USB.md`. `python mobile/usb_link.py install covenant-node.apk`,
  then `link` so the phone node peers with the PC at `127.0.0.1:15001`.
- **From GitHub:** every push to `main` that touches the app or the node's
  files rebuilds it, proves it on the emulator and publishes an immutable
  release `android-<commit>`; the newest is always at
  `https://github.com/LAWLESS1987/covenant/releases/latest/download/covenant-node.apk`
  (with `SHA256SUMS` beside it). Releases on this repository are immutable
  by setting, so a build is never replaced under its name -- a new one is
  added. Samsung: Settings > Security and privacy >
  Auto Blocker off for the install (re-arm after); allow "Install unknown apps"
  for the browser or My Files; expect Play Protect's "hasn't seen this app
  before" prompt.
- **Rebuild it yourself:** `sh mobile/app/build.sh` with JDK 17, Gradle 8.13,
  an Android SDK with platform 35 and licences accepted, and python3.12 on
  PATH -- or push and let `.github/workflows/android.yml` do it.

Updates install in place because every build is signed with the same
debug-class key in `mobile/app/signing/` (public by design -- read that
folder's README). Changing that key forces an uninstall, which deletes the
node's identity key and database.

## Keep it alive on a Galaxy

Settings > Apps > Covenant Node > Battery > **Unrestricted** (the app's
"Battery" button opens the system dialog); Settings > Battery > Background
usage limits > **Never sleeping apps** > add it; no Power saving mode (Samsung
documents that it cuts background apps off Wi-Fi); allow notifications so the
service's notification is visible; tick "Start at boot" if wanted. The
notification drawer's "Active apps" Stop button kills the app outright with no
callback; the UI then shows DOWN.

## Peering

- Cable: `python mobile/usb_link.py link` on the PC, PC peer `127.0.0.1:15001` in the app.
- Wi-Fi: PC peer `PC_IP:5001` (the PC's API port plus one; IPv4 or hostname),
  the inbound TCP 5001 rule on the PC, and `PHONE_IP:5001` added to the PC
  node's `--peers` (this version does not learn peers from inbound connections).

## Reading the status line

`degraded` is true on every keyless phone and the UI ignores it. What matters:
`own_genesis=false`, `genesis` equal to the PC's, `peers=1` when a PC peer is
set, `version` and `source_sha256` matching the PC. `last exit` under DOWN is
the launcher's own reason (a port taken, a missing file).

## What it deliberately is not

- No model server, no `JUDGE_MODEL`, nothing that reaches port 11434.
- No XRP settlement (`xrpl-py` is not shipped); the node runs without it.
- No key backup: uninstalling deletes the node's identity.
- No in-app restart loop: an OS kill restarts the service; a Stop stays stopped.
- Code proposals are refused on the phone (`COVENANT_FORCE_NO_SANDBOX=1`).

## What CI proves, and what only a phone proves

`android.yml` builds on the stock runner, checks that the APK's core is
byte-identical to the checkout's, boots the APK on an x86_64 API-35 emulator,
and asserts `/health` reports the canonical genesis and a `quorum(...)` judge,
still answers with the screen off and idle forced, stops on Stop and starts
again. Only a phone proves: the arm64 binaries load on the S25+; the Start
button's tap path; Samsung's sleep policy; the Share sheet from another app.
`test_m5_app.py` pins the allowlist, the manifest and the workflow from the
repository side.
