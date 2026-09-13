# Covenant Node for Android (mobile/app)

**The phone's rule (the operator, 2026-09-12): a phone is private to the
person holding it.** Nothing on it is readable by anyone else -- not the PC
operator, not another node, not the assistant -- unless that person sends it.
Every design choice below is measured against that sentence; "What leaves the
phone" further down is the list.

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

## Using your other apps (phase 1, 2026-09-12)

The operator asked for "access and use of all my apps if I green-light it".
Phase 1 is the consent layer and a local actuator, nothing remote:

- **Apps Covenant may use** lists every launchable app with a switch, all
  OFF. A switch on is the green light; the actuator refuses any app that is
  not on the list, every time.
- **The actuator** is an Android Accessibility service. Only you can enable
  it, in Android's Accessibility settings; the app can only send you there.
  It requests no gestures.
- **Use an app...** picks a green-lit app, takes a text and whether to press
  its Send/Post/Submit button. The text goes through the node's own gate
  first (a REFUSED text never leaves; a hold that alleges nothing is logged
  and passes), then the app is opened and the text put into its field.
- **Every action and every refusal** is one line in the app's
  `files/actions.log` (read it with `adb shell run-as org.covenant.node cat
  files/actions.log` over a cable, or from the phone's log tail).

What is deliberately NOT here: any way to drive this from the PC or the
network. This APK is signed with a public debug-class key; an accessibility
grant on an app anyone can install over yours would hand your phone to
whoever did. Remote driving waits for a signing key only you hold
(`docs/KNOWN_ISSUES.md` A104).

## What leaves the phone, and what does not (2026-09-12)

- **No analytics, no crash reporter, no third-party SDK, no account.** The
  app has no `dependencies` block; it is the platform, Chaquopy's Python and
  this repository's own files.
- **The node's HTTP API binds to 127.0.0.1 on the phone** (`COVENANT_API_HOST`):
  `/health`, the dashboard and every route answer only the app itself and a
  USB tunnel. Nothing on the Wi-Fi can read or poke them.
- **The peer port (API port + 1) is open** so the PC node can talk to the
  phone. Peer traffic is the covenant's protocol over plain TCP on your own
  network: every transaction is signed and every block hashed, so nothing can
  be forged in transit, but a device on the same network could read payload
  text. Encrypting the peer link is a protocol change for the group, not a
  phone setting.
- **The actuator reads a screen only when a job for that app is pending and
  the app is green-lit**; it never reads other apps' screens, never sends
  anything anywhere, and logs every action locally. Its grant is yours to give
  and to withdraw in Android settings.
- **What this app cannot promise:** anything above it. Android, Samsung,
  Google services and the carrier see what they see regardless of any app;
  the APK's public debug key means only builds you trust should be installed
  (`mobile/app/signing/README.md`).

## The preliminary brain (phase 2, 2026-09-12)

Asked: "build a preliminary brain that learns ... let it watch ... and have
access to the other AI apps on my phone". Under the phone's rule, the brain
lives on the phone and learns from the person holding it -- no model, no
network, no screen leaves.

- **A recipe is a demonstration.** Record one: pick a green-lit app, name it,
  do the thing once while the actuator watches (taps, text, scrolls), come
  back and tap Stop. It is kept as `files/recipes/<name>.json`, readable.
- **It learns which locator to trust.** Every step keeps four ways to find
  its target (view id, text, description, class + position) with a score
  each; a replay tries the best first and scores up what worked, down what
  missed -- so a relabelled button or a moved control is survived, and each
  run leaves the recipe surer.
- **Typed text is a slot.** One demonstration of "post this" serves every
  later post: the run asks for the text, the node's gate judges it (REFUSED
  never goes in; a hold that alleges nothing is logged and passes), then it
  is typed.
- **It reads the answer back.** When a run finishes, what the app shows --
  an AI app's reply, a confirmation -- is kept as the recipe's last answer,
  on the phone, with a Share button for the owner. This is how the phone's
  other AI apps become tools it can consult without an API or a key: green-
  light the app, record "ask it something", run it with a slot.
- **Every run is written down** (`actions.log`, and the recipe's own run
  list), and a recipe can be deleted the moment it learned something wrong.

What it is not: it does not plan. It repeats what it was shown, better each
time, in the apps it was allowed. "Watch the assistant" -- recording what I
do over the cable so the phone can repeat it without me -- waits, like any
remote driving, for a signing key only the operator holds.
