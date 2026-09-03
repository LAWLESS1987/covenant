#!/bin/sh
# covenant_phone.sh -- start a covenant node with a local judge on an Android phone (Termux).
#
# Same node as the PC (run_with_ollama_judge.py), a smaller judge, peered to the PC.
# Configure by environment or edit the defaults below. See mobile/TERMUX_SETUP.md.
#
#   PC_PEER      a peer's P2P address: its API port plus one (e.g. 10.0.0.174:5001).
#                Empty (the default) = no peer: the node runs alone from the canonical
#                genesis and converges when a peer appears. No peer is invented for you.
#   PHONE_PORT   this node's API port (default 5000; it also uses PHONE_PORT+1 and +10)
#   JUDGE_MODEL  the phone judge (default qwen3:1.7b; qwen3:4b on an 8 GB phone)
#   NODE_ID      the name this node signs with (default phone)
#
# Everything the script exports is what the node already understands; nothing here is
# a mobile fork. The gate still fails CLOSED if the judge is unreachable.

set -u
PC_PEER="${PC_PEER:-}"
PHONE_PORT="${PHONE_PORT:-5000}"
JUDGE_MODEL="${JUDGE_MODEL:-qwen3:1.7b}"
NODE_ID="${NODE_ID:-phone}"
OLLAMA_URL="${COVENANT_OLLAMA_URL:-http://127.0.0.1:11434/v1/chat/completions}"

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE" || exit 1

say() { printf '%s\n' "$*"; }

# 0. where we are, plainly
say "covenant phone node: $NODE_ID  port $PHONE_PORT  judge $JUDGE_MODEL  peer ${PC_PEER:-(none: standalone until a peer appears)}"
[ -f genesis.json ] || { say "no genesis.json here -- run this from the covenant clone"; exit 2; }
command -v python >/dev/null 2>&1 || { say "python missing: pkg install python"; exit 2; }

# 1. keep the phone from sleeping the node (Termux only; harmless elsewhere)
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock

# 2. the judge server
if ! command -v ollama >/dev/null 2>&1; then
    say "ollama missing: pkg install ollama (or run any OpenAI-compatible server on 11434)"
    say "continuing: the node will start and fail CLOSED until a judge answers"
else
    if ! curl -s -m 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        say "starting ollama serve in the background (log: $HOME/ollama.log)"
        nohup ollama serve >"$HOME/ollama.log" 2>&1 &
        i=0
        while [ $i -lt 20 ]; do
            curl -s -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
            i=$((i + 1)); sleep 1
        done
    fi
    if ! ollama list 2>/dev/null | grep -q "^$JUDGE_MODEL"; then
        say "pulling $JUDGE_MODEL (first time only; this is the big download)"
        ollama pull "$JUDGE_MODEL" || say "pull failed -- the node will fail CLOSED until it succeeds"
    fi
fi

# 3. the node, with the judge the phone has
export COVENANT_JUDGE_PROVIDERS=local
export COVENANT_LOCAL_JUDGE_MODEL="$JUDGE_MODEL"
export COVENANT_OLLAMA_URL="$OLLAMA_URL"
say "health when up: http://127.0.0.1:$PHONE_PORT/health"
if [ -n "$PC_PEER" ]; then
    exec python run_with_ollama_judge.py --real --port "$PHONE_PORT" --node-id "$NODE_ID" \
        --genesis genesis.json --peers "$PC_PEER"
else
    exec python run_with_ollama_judge.py --real --port "$PHONE_PORT" --node-id "$NODE_ID" \
        --genesis genesis.json
fi
