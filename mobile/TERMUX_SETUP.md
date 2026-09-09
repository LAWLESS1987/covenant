# The covenant on a phone: a node and a local judge, in Termux (Android)

What you get: a real covenant node running on the phone, with its own ethics judge
running on the phone, peered to your PC node. The node is the same `run_with_ollama_judge.py`
the PC runs; nothing is forked for mobile. The judge is a smaller model than the PC's, and
that is stated on the node's own terms below, not hidden.

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

- Android 8 or newer, arm64, at least 6 GB RAM (8 GB to run the 4B judge).
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

Installing Ollama anyway is harmless and changes nothing about the verdict you
get; it is simply no longer part of the install.

`python-cryptography` comes from Termux's package repo so nothing is compiled on the phone.
`waitress` is optional and pure Python; with it the node serves through a bounded pool.
`xrpl-py` is not installed: XRP settlement is not for a phone, and the node runs without it.

You do not need a model server at all. If you choose to run one anyway, any server
speaking the OpenAI chat-completions API on port 11434 will do (llama.cpp's, for
example) and the judge tries Ollama's `/api/chat` first, falling back to
`/v1/chat/completions` by itself — but under the shipped policy that seat is not
consulted, so it changes nothing.

## The judge tier, stated plainly

| where | model | RAM it needs | what that means |
|---|---|---|---|
| PC | `qwen3:8b` (the digest the nodes have always pinned) | about 5 GB | the reference judge |
| phone, 8 GB | `qwen3:4b` | about 3 GB | close to the PC's verdicts in the alignment set; slower |
| phone, 6 GB | `qwen3:1.7b` | about 1.5 GB | a weaker gate: it still fails CLOSED when it cannot decide, but its verdicts are coarser |
| phone, 12 GB (Galaxy S25+) | `qwen3:8b` | about 5 GB | the same model and digest as the PC: the same gate, a few times slower on a phone CPU; `qwen3:4b` if you want verdicts in seconds rather than a minute |

For a Galaxy S25+ (12 GB), start with `JUDGE_MODEL=qwen3:4b sh mobile/covenant_phone.sh` and
move to `qwen3:8b` once it runs clean; Samsung's One UI puts background apps to "deep sleep",
so add Termux to Settings > Battery > Never sleeping apps, or the node stops when the
screen does.

The gate fails CLOSED when **nothing competent answers** — but on a fresh clone something
always does, so this is not the state you will be in. **Corrected 2026-09-09:** this said
"no reachable judge, or no verdict, means every transaction is rejected", which has been
false since the distilled student shipped. Measured with no Ollama and nothing on 11434:
an ordinary send and a gift ADMIT; theft, deception and coercion REJECT. The table above
describes an optional extra model, not the judge that decides.

## Run (every time)

```bash
cd ~/covenant && sh mobile/covenant_phone.sh
```

The script sets the environment and starts the node. **It no longer touches Ollama by
default** (`COVENANT_PHONE_SKIP_OLLAMA=0` restores the old behaviour); the student judges
in-process. Configure it with environment variables, or edit the
defaults at the top of the script:

| variable | default | meaning |
|---|---|---|
| `PC_PEER` | empty | a peer's P2P address (API port plus one), e.g. `10.0.0.174:5001`; empty runs the node alone until a peer appears |
| `PHONE_PORT` | `5000` | the phone node's API port; it also takes 5001 and **5011** |
| `JUDGE_MODEL` | `qwen3:1.7b` | the phone judge; `qwen3:4b` on an 8 GB phone |
| `NODE_ID` | `phone` | the name the node signs with |

Under the hood the script exports `COVENANT_JUDGE_PROVIDERS=local`,
`COVENANT_LOCAL_JUDGE_MODEL=$JUDGE_MODEL`,
`COVENANT_OLLAMA_URL=http://127.0.0.1:11434/v1/chat/completions`, and runs

**Those exports are decorative and this page used to imply otherwise.**
`run_with_ollama_judge.py` applies `ops/quorum_policy.json` OVER the
environment, and `covenant_judge_defer.apply_policy` overwrites the providers
variable unconditionally — only `COVENANT_JUDGE_PROVIDERS_OVERRIDE` wins. Proven:

```bash
COVENANT_JUDGE_PROVIDERS=local python -c \
  "import run_with_ollama_judge, os; print(os.environ['COVENANT_JUDGE_PROVIDERS'])"
# -> deferring,semantic
```

The gate you actually get is the deferring seat (both distilled students) plus
the deterministic semantic judge. See KNOWN_ISSUES A38. The command run is
`python run_with_ollama_judge.py --real --port $PHONE_PORT --node-id $NODE_ID --genesis genesis.json --peers $PC_PEER`.
The shared `genesis.json` in the clone is the canonical one; a node that mints its own
cannot converge with anyone.

Check it from the phone's browser: http://127.0.0.1:5000/health . Or run
`sh mobile/covenant_phone_check.sh`, which asks Ollama for its models, the node for its
health, and reports the judge it sees. That check no longer treats a missing Ollama as a
failure — until 2026-09-09 it printed "the node will fail CLOSED" and exited 1 on a
perfectly healthy node, which is the worst thing a health check can do.

## Make it feel like an app

- **Home-screen button:** install Termux:Widget, then
  `mkdir -p ~/.shortcuts && cp mobile/widget/covenant-phone-start.sh ~/.shortcuts/ && chmod +x ~/.shortcuts/*.sh`.
  Add the Termux:Widget to your home screen; tapping the entry starts the node.
- **Start at boot:** install Termux:Boot, open it once, then
  `mkdir -p ~/.termux/boot && cp mobile/widget/covenant-phone-start.sh ~/.termux/boot/`.
- **Keep it alive:** run `termux-wake-lock` (the script does) and exclude Termux from battery
  optimisation in Android settings, or the node dies when the screen sleeps.
- **The dashboard** is the node's own pages in the phone browser; nothing else to install.

## Let the PC use the phone's judge too

The PC nodes can count the phone's judge as one more provider, so the quorum sees a
genuinely different model in a different place. On the PC, create `judges.json` from
`mobile/judges.example.json`, put the phone's Tailscale address in it, and set
`COVENANT_JUDGE_PROVIDERS=pc_qwen,phone`. How many judges is the whole question, and the
answer is not "more": read the paragraph above the named-judge table in
`covenant_judge_ollama.py` before you do this.

## What can go wrong

- `pip install cryptography` starts compiling Rust: you skipped `pkg install python-cryptography`.
- The node prints "minted its OWN genesis": you ran it outside the clone or without `--genesis`.
- The phone never sees the PC: the PC's firewall, or the PC node was started without the
  phone in its peer list and your version does not learn peers from inbound connections;
  add `PHONE_IP:5001` to the PC node's `--peers`.
- `/health` says the judge is unreachable and everything is rejected: that is the gate
  failing closed, as designed. Check `ollama ps` and that the model finished pulling.
- Ollama is killed by Android for memory: use the 1.7B model, close other apps, or move the
  judge to the PC as described above.
