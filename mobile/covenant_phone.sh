#!/bin/sh
# covenant_phone.sh -- start a covenant node with a local judge on an Android phone (Termux).
#
# Same node as the PC (run_with_ollama_judge.py), a smaller judge, peered to the PC.
# Configure by environment or edit the defaults below. See mobile/TERMUX_SETUP.md.
#
#   PC_PEER      a peer's P2P address: its API port plus one (e.g. 10.0.0.174:5001).
#                Empty (the default) = no peer: the node runs alone from the canonical
#                genesis and converges when a peer appears. No peer is invented for you.
#   PHONE_PORT   this node's API port (default 5000; it also uses PHONE_PORT+1 and +11)
#                Corrected 2026-09-09: this said +10. The core takes N, N+1 and N+11 --
#                launch_check gate G7 measures exactly that, and 5010 is closed while
#                5011 listens. A firewall rule written from the old line opened nothing.
#   JUDGE_MODEL  the phone judge (default qwen3:1.7b; qwen3:4b on an 8 GB phone)
#   NODE_ID      the name this node signs with (default phone)
#
# Everything the script exports is what the node already understands; nothing here is
# a mobile fork. The gate fails CLOSED when nothing competent answers -- but the
# shipped distilled student always answers, so that is not the usual state.

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

# 2. the judge server -- OPTIONAL SINCE 2026-09-08, and it used to say otherwise.
#
# This block used to tell you the node would "fail CLOSED until a judge answers"
# and then spend most of the install pulling a multi-gigabyte model. Both halves
# were wrong by the time anyone read them. Ollama was deleted from this project
# on 2026-09-07 and is out of the ethics quorum by policy
# (ops/quorum_policy.json: ollama_in_chain false), so the pull bought nothing.
#
# What actually judges on a fresh clone is the distilled student -- a 130 KB
# JSON file, tracked in this repo, read into the node's own process, no socket
# and no model server. Measured on a clean clone with no Ollama, no GITHUB_TOKEN
# and no API key (KNOWN_ISSUES A37): the node came up in ONE SECOND, admitted an
# ordinary send and rejected every theft, deception and coercion case offline.
#
# So skipping Ollama is the normal path, not a degraded one. If you have it
# installed anyway the block below still starts it, which costs nothing.
if [ "${COVENANT_PHONE_SKIP_OLLAMA:-1}" = "1" ]; then
    say "skipping ollama -- the shipped distilled student judges offline (A37)"
    say "set COVENANT_PHONE_SKIP_OLLAMA=0 if you want the old behaviour"
elif ! command -v ollama >/dev/null 2>&1; then
    say "ollama missing, and that is fine: the shipped student judges without it"
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
#
# A93, closed 2026-09-12. For one day this block exported
# COVENANT_JUDGE_PROVIDERS_OVERRIDE=deferring,semantic, because the launcher's
# no-policy fallback was hard-coded to "local,semantic" (an Ollama seat no phone
# runs) and OVERRIDE was the only variable it could not discard. That worked and
# it was wrong in a way that would have bitten the next operator: OVERRIDE beats
# EVERYTHING, including ops/quorum_policy.json -- so a phone operator who wrote
# their own standing policy would have had it silently ignored by this script.
#
# The operator changed the fallback itself ("change the fallback to
# deferring,semantic"), so this script now exports nothing about providers.
# Resolution is the same as on any node: the operator's ops/quorum_policy.json
# if present, else the launcher's default, which is the distilled student plus
# the deterministic semantic judge. Measured on a clone-equivalent tree with no
# policy and no override: seat 0 = DeferringJudge (test_a93).
#
# The two exports below are read by the optional Ollama seat only; harmless.
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
