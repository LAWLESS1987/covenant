# The covenant on a phone: a node and a local judge, in Termux (Android)

What you get: a real covenant node running on the phone, with its own ethics judge
running on the phone, peered to your PC node. The node is the same launcher the PC runs
(nothing is forked for mobile), and the judge is the SAME judge as the PC's: the distilled
students plus the deterministic semantic judge, in-process. **Nothing on the phone reaches
a model server** -- see "The judge, stated plainly" below.

What you do not get: an iPhone version. iOS does not allow a background Python server or a
local model server that other programs can call, so an iPhone can only be a client of the PC
node (its dashboard in Safari over Tailscale) and cannot carry a judge. This page is Android.

## The short way: two steps, one of them a command

1. Install Termux from F-Droid: https://f-droid.org/packages/com.termux/ (not the Play Store build).
2. Open it and paste one line:

```bash
curl -sL https://raw.githubusercontent.com/LAWLESS1987/covenant/main/mobile/install.sh | sh
```

That installs the packages, clones or updates this repository, puts a
button on your home screen (with Termux:Widget), and starts the node. Put `PC_PEER=10.0.0.174:5001`
(your PC's address) in front of it to peer with a PC on the same Wi-Fi; without it the node
runs alone from the canonical genesis and converges when a peer appears. This project would
rather you read before you run: `curl -sLO .../mobile/install.sh`, then `less install.sh`,
then `sh install.sh`.

Why there is no true one-tap install: Android will not run a Python node and a model server
from a link. It needs a terminal app, and Termux is that app. A packaged APK that bundles both
is possible and is not built; it is a project, not a script.

## Requirements

- Android 8 or newer, arm64, 4 GB RAM is plenty: the judge is a 130 KB model read in-process.
- Termux from F-Droid (the Play Store build is abandoned and breaks packages):
  https://f-droid.org/packages/com.termux/ . Optional: Termux:Widget (home-screen button)
  and Termux:Boot (start at boot), also from F-Droid.
- Your PC node reachable from the phone: same Wi-Fi, or Tailscale on both. The PC node A
  listens for peers on port 5001 (API port 5000 plus one); Windows Firewall must allow
  inbound TCP 5001. On the PC, once, in an administrator PowerShell:
  `New-NetFirewallRule -DisplayName "covenant peer 5001" -Direction Inbound -Protocol TCP -LocalPort 5001 -Action Allow`
  (a security setting; you run it, not the assistant).

## Install (once, a couple of minutes on Wi-Fi)

```bash
pkg update && pkg upgrade
pkg install python git python-cryptography
git clone https://github.com/LAWLESS1987/covenant && cd covenant
pip install flask requests waitress
```

**CORRECTED 2026-09-09. This used to say "about fifteen minutes on Wi-Fi; the
model is the big download" and put `ollama` in the line above.** Both were
stale. Ollama was deleted from this project on 2026-09-07 and is out of the
ethics quorum by policy (`ops/quorum_policy.json`: `ollama_in_chain` false), so
the multi-gigabyte pull bought a component the gate no longer consults.

What judges on your phone is the **distilled student** — a 130 KB JSON model
tracked in this repo and read into the node's own process. No socket, no model
server, nothing to download. Measured on a clean clone with no Ollama, no
`GITHUB_TOKEN` and no API key (KNOWN_ISSUES A37): the node came up in **one
second**, admitted an ordinary send, and rejected every theft, deception and
coercion case offline.

`python-cryptography` comes from Termux's package repo so nothing is compiled on the phone.
`waitress` is optional and pure Python; with it the node serves through a bounded pool.
`xrpl-py` is not installed: XRP settlement is not for a phone, and the node runs without it.

You do not need a model server, and since 2026-09-12 the kit does not know how to
use one: no model knob, no start-a-server block, no model-server port. What judges is below.

## The judge, stated plainly

The phone runs exactly the judges the PC runs, and no others:

| seat | what it is | where it lives |
|---|---|---|
| `deferring` | the two distilled students (`fallback_model.json`, `fallback_model_2.json`), trained from the verdict ledger; a student that does not know ABSTAINS rather than guesses | in the node's process, 130 KB each |
| `semantic` | the deterministic lexical judge (`semantic_judge_model.json`) -- observes appropriation and concealment and nothing else | in the node's process |

How good they are is a measurement, not a claim: `ops/DISTILL.md` and `ops/DISTILL_2.md`
record every exam, and the line that matters reads `exam thresholds ... MET` or `NOT MET`
with the categories it is short on. Read it before trusting a phone's verdict more than
the PC's. The online AIs are **teachers** -- cross-referenced against each other while
the students train -- and never a seat on the phone; the direction (2026-09-12) is that
the local judges learn to run without them.

The gate fails CLOSED when **nothing competent answers** -- but on a fresh clone the
student always answers, so this is not the state you will be in. Measured with no model
server of any kind and no key of any kind: an ordinary send and a gift ADMIT; theft,
deception and coercion REJECT. Samsung's One UI puts background apps to "deep sleep", so
add Termux to Settings > Battery > Never sleeping apps, or the node stops when the
screen does.

## Run (every time)

```bash
cd ~/covenant && sh mobile/covenant_phone.sh
```

The script starts the node; the students judge in-process. Configure it with environment
variables, or edit the defaults at the top of the script:

| variable | default | meaning |
|---|---|---|
| `PC_PEER` | empty | a peer's P2P address (API port plus one), e.g. `10.0.0.174:5001`; empty runs the node alone until a peer appears |
| `PHONE_PORT` | `5000` | the phone node's API port; it also takes 5001 and **5011** |
| `NODE_ID` | `phone` | the name the node signs with |

Under the hood the script exports nothing about judges at all, and runs

**A93, closed 2026-09-12.** The policy file `ops/quorum_policy.json` is the
operator's answer and is gitignored, so a clone never has one -- and until
2026-09-12 the launcher's fallback for "no policy" was hard-coded to
`local,semantic`, an Ollama seat no phone runs. For one day this script papered
over that with `COVENANT_JUDGE_PROVIDERS_OVERRIDE`, which would have silently
ignored a phone operator's own policy file. The operator then changed the
fallback itself: **with no policy, every node -- phone or PC -- now seats
`deferring,semantic`**, and this script exports nothing about providers.
Measured on a clone-equivalent tree, no policy, no override:

| tree | seat 0 resolves to |
|---|---|
| before 2026-09-12 (fallback `local,semantic`) | `OllamaJudge` -- broken on a phone |
| after (fallback `deferring,semantic`) | `DeferringJudge` -- the distilled student, in-process |

`test_a93_clone_seats_the_student.py` pins it by running this script with a
fake `python` that captures the environment, then asking the launcher what a
policy-less tree resolves to. Its control asserts an explicit OVERRIDE still
wins, so the probe is known to discriminate.

The gate you actually get is the deferring seat (both distilled students) plus
the deterministic semantic judge. See KNOWN_ISSUES A38 and A93. The command run is
`python run_with_ollama_judge.py --real --port $PHONE_PORT --node-id $NODE_ID --genesis genesis.json --peers $PC_PEER`.
The shared `genesis.json` in the clone is the canonical one; a node that mints its own
cannot converge with anyone.

Check it from the phone's browser: http://127.0.0.1:5000/health . Or run
`sh mobile/covenant_phone_check.sh`, which checks the student model file is present and
asks the node for its health. Until 2026-09-09 it printed "the node will fail CLOSED" and
exited 1 on a perfectly healthy node because a model server was absent, which is the
worst thing a health check can do; since 2026-09-12 it does not look for one at all.

## On a cable instead of Wi-Fi

`mobile/USB.md` -- USB debugging on the phone, `python mobile/usb_link.py link` on
the PC, and the phone node peers with `PC_PEER=127.0.0.1:15001` over the cable
with no firewall rule; `http://127.0.0.1:15000/health` reads it from the PC.

## Make it feel like an app

- **Home-screen button:** install Termux:Widget, then
  `mkdir -p ~/.shortcuts && cp mobile/widget/covenant-phone-start.sh ~/.shortcuts/ && chmod +x ~/.shortcuts/*.sh`.
  Add the Termux:Widget to your home screen; tapping the entry starts the node.
- **Start at boot:** install Termux:Boot, open it once, then
  `mkdir -p ~/.termux/boot && cp mobile/widget/covenant-phone-start.sh ~/.termux/boot/`.
- **Keep it alive:** run `termux-wake-lock` (the script does) and exclude Termux from battery
  optimisation in Android settings, or the node dies when the screen sleeps.
- **The dashboard** is the node's own pages in the phone browser; nothing else to install.

## What can go wrong

- `pip install cryptography` starts compiling Rust: you skipped `pkg install python-cryptography`.
- The node prints "minted its OWN genesis": you ran it outside the clone or without `--genesis`.
- The phone never sees the PC: the PC's firewall, or the PC node was started without the
  phone in its peer list and your version does not learn peers from inbound connections;
  add `PHONE_IP:5001` to the PC node's `--peers`.
