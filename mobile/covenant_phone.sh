#!/bin/sh
# covenant_phone.sh -- start a covenant node on an Android phone (Termux).
#
# The SAME node as the PC (run_node.py: the distilled students plus the
# deterministic semantic judge, in-process, no model server). Peered to the PC
# if you say so.
# Configure by environment or edit the defaults below. See mobile/TERMUX_SETUP.md.
#
#   PC_PEER      a peer's P2P address: its API port plus one. Over Wi-Fi that is
#                the PC's address, e.g. 10.0.0.174:5001; over a USB-C cable with
#                mobile/usb_link.py it is 127.0.0.1:15001 (see mobile/USB.md).
#                Empty (the default) = no peer: the node runs alone from the
#                canonical genesis and converges when a peer appears.
#   PHONE_PORT   this node's API port (default 5000; it also uses PHONE_PORT+1 and +11)
#                Corrected 2026-09-09: this said +10. The core takes N, N+1 and N+11 --
#                launch_check gate G7 measures exactly that, and 5010 is closed while
#                5011 listens. A firewall rule written from the old line opened nothing.
#   NODE_ID      the name this node signs with (default phone)
#
# NO OLLAMA, NO MODEL SERVER, NO JUDGE_MODEL (2026-09-12). Until today this
# script carried a JUDGE_MODEL knob, a block that would start Ollama and pull a
# multi-gigabyte model, and two exports read only by that seat. Ollama was
# deleted from this project on 2026-09-07 and the operator's direction is that
# nothing on a phone reaches a model server: the online AIs are TEACHERS that
# train the local semantic judges, and the phone runs those judges alone. The
# exam that says how well they do is in ops/DISTILL.md; nothing here pretends
# they are better than that record says.
#
# Nothing here is a mobile fork. The script exports nothing about judge
# providers either: resolution is the same as on any node -- the operator's
# ops/quorum_policy.json if present, else the launcher's default,
# deferring,semantic (A93, closed 2026-09-12). The gate fails CLOSED when
# nothing competent answers; the shipped student always answers.

set -u
PC_PEER="${PC_PEER:-}"
PHONE_PORT="${PHONE_PORT:-5000}"
NODE_ID="${NODE_ID:-phone}"

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE" || exit 1

say() { printf '%s\n' "$*"; }

# 0. where we are, plainly
say "covenant phone node: $NODE_ID  port $PHONE_PORT  peer ${PC_PEER:-(none: standalone until a peer appears)}"
[ -f genesis.json ] || { say "no genesis.json here -- run this from the covenant clone"; exit 2; }
[ -f fallback_model.json ] || { say "no fallback_model.json here -- the distilled student is missing; this is not a covenant clone"; exit 2; }
command -v python >/dev/null 2>&1 || { say "python missing: pkg install python"; exit 2; }

# 1. keep the phone from sleeping the node (Termux only; harmless elsewhere)
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock

# 2. the node
say "health when up: http://127.0.0.1:$PHONE_PORT/health"
if [ -n "$PC_PEER" ]; then
    exec python run_node.py --real --port "$PHONE_PORT" --node-id "$NODE_ID" \
        --genesis genesis.json --peers "$PC_PEER"
else
    exec python run_node.py --real --port "$PHONE_PORT" --node-id "$NODE_ID" \
        --genesis genesis.json
fi
