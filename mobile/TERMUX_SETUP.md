# The covenant on a phone: a node and a local judge, in Termux (Android)

What you get: a real covenant node running on the phone, with its own ethics judge
running on the phone, peered to your PC node. The node is the same `run_with_ollama_judge.py`
the PC runs; nothing is forked for mobile. The judge is a smaller model than the PC's, and
that is stated on the node's own terms below, not hidden.

What you do not get: an iPhone version. iOS does not allow a background Python server or a
local model server that other programs can call, so an iPhone can only be a client of the PC
node (its dashboard in Safari over Tailscale) and cannot carry a judge. This page is Android.

## Requirements

- Android 8 or newer, arm64, at least 6 GB RAM (8 GB to run the 4B judge).
- Termux from F-Droid (the Play Store build is abandoned and breaks packages):
  https://f-droid.org/packages/com.termux/ . Optional: Termux:Widget (home-screen button)
  and Termux:Boot (start at boot), also from F-Droid.
- Your PC node reachable from the phone: same Wi-Fi, or Tailscale on both. The PC node A
  listens for peers on port 5001 (API port 5000 plus one); Windows Firewall must allow
  inbound TCP 5001 for python.

## Install (once, about fifteen minutes on Wi-Fi; the model is the big download)

```bash
pkg update && pkg upgrade
pkg install python git python-cryptography ollama
git clone https://github.com/LAWLESS1987/covenant && cd covenant
pip install flask requests waitress
```

`python-cryptography` comes from Termux's package repo so nothing is compiled on the phone.
`waitress` is optional and pure Python; with it the node serves through a bounded pool.
`xrpl-py` is not installed: XRP settlement is not for a phone, and the node runs without it.

If `pkg install ollama` is not available on your Termux, any server that speaks the
OpenAI chat-completions API on port 11434 will do (llama.cpp's server, for example); the
judge tries Ollama's `/api/chat` first and falls back to `/v1/chat/completions` by itself.

## The judge tier, stated plainly

| where | model | RAM it needs | what that means |
|---|---|---|---|
| PC | `qwen3:8b` (the digest the nodes have always pinned) | about 5 GB | the reference judge |
| phone, 8 GB | `qwen3:4b` | about 3 GB | close to the PC's verdicts in the alignment set; slower |
| phone, 6 GB | `qwen3:1.7b` | about 1.5 GB | a weaker gate: it still fails CLOSED when it cannot decide, but its verdicts are coarser |

The gate's promise does not change with the model: no reachable judge, or no verdict, means
every transaction is rejected. What changes is the quality of the verdicts, and the phone
node prints which model it is using at boot (the `[ollama-judge]` banner). If you want the phone to be as
strict as the PC, do not run a judge on it at all and point its `COVENANT_OLLAMA_URL` at the
PC's Ollama over Tailscale; then the phone node is a peer with the PC's judge.

## Run (every time)

```bash
cd ~/covenant && sh mobile/covenant_phone.sh
```

The script starts Ollama if it is not running, pulls the judge model the first time, sets the
environment, and starts the node. Configure it with environment variables, or edit the
defaults at the top of the script:

| variable | default | meaning |
|---|---|---|
| `PC_PEER` | `192.168.1.10:5001` | your PC node's P2P address (API port plus one) |
| `PHONE_PORT` | `5000` | the phone node's API port; it also takes 5001 and 5010 |
| `JUDGE_MODEL` | `qwen3:1.7b` | the phone judge; `qwen3:4b` on an 8 GB phone |
| `NODE_ID` | `phone` | the name the node signs with |

Under the hood the script exports what the node already understands:
`COVENANT_JUDGE_PROVIDERS=local`, `COVENANT_LOCAL_JUDGE_MODEL=$JUDGE_MODEL`,
`COVENANT_OLLAMA_URL=http://127.0.0.1:11434/v1/chat/completions`, and runs
`python run_with_ollama_judge.py --real --port $PHONE_PORT --node-id $NODE_ID --genesis genesis.json --peers $PC_PEER`.
The shared `genesis.json` in the clone is the canonical one; a node that mints its own
cannot converge with anyone.

Check it from the phone's browser: http://127.0.0.1:5000/health . Or run
`sh mobile/covenant_phone_check.sh`, which asks Ollama for its models, the node for its
health, and reports the judge it sees.

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
