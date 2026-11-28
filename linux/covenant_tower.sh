#!/usr/bin/env bash
# ============================================================================
#  linux/covenant_tower.sh -- start/stop/status ONE covenant node on a Debian
#  tower, under the tower's OWN identity, listening on one address. A500.
#
#  linux/covenant_prod.sh is the laptop's three production nodes (A, B, C):
#  it needs covenant_A.db.key, the founder key, and its nodes listen on every
#  interface. Run on a tower, it would make every tower a clone of node A on
#  the office network. This script is the tower's launcher instead.
#
#  USAGE (from anywhere; it works from the repository root)
#    linux/covenant_tower.sh            start (idempotent - safe to re-run)
#    linux/covenant_tower.sh stop
#    linux/covenant_tower.sh status
#
#  SETTINGS (environment, or one line each in ops/tower.env as NAME=value)
#    COVENANT_TOWER_ID     one capital letter, E to Z. A, B, C (the laptop)
#                          and D (the main PC) are refused.
#    COVENANT_TOWER_BIND   the address to listen on: the tower's tailnet
#                          address. Default: `tailscale ip -4`. Empty,
#                          0.0.0.0 and :: are refused.
#    COVENANT_TOWER_PEERS  host:p2p-port,... the nodes to dial (the main PC's
#                          node D is its tailnet address with port 5081).
#    COVENANT_TOWER_PORT   API port, default 5000 (peer port = API + 1).
#
#  It NEVER deletes a database or a key, and refuses to start while a
#  production key (the founder key, or node A-D's) is on this machine.
#  The node makes its own key on first start (nodeX_prod.db.key, mode 600).
#
#  WHAT IT DOES NOT DO: start at boot, schedule anything, or run a watchdog
#  (covenant_watchdog.py watches A, B and C by name). See linux/README.md.
#
#  COVENANT_DRY_RUN=1 prints the launch and stop instead of doing them.
# ============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$HERE" || exit 1
mkdir -p logs
LOG="logs/tower.log"
DRY="${COVENANT_DRY_RUN:-}"

stamp() {
    printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG"
    printf '%s\n' "$1"
}
abort() { stamp "ABORT: $1"; exit 1; }

# ops/tower.env: NAME=value lines for the four settings only; the environment wins.
if [ -f ops/tower.env ]; then
    while IFS='=' read -r k v; do
        k="$(printf '%s' "$k" | tr -d ' \r')"; v="$(printf '%s' "$v" | tr -d '\r')"
        case "$k" in
            COVENANT_TOWER_ID|COVENANT_TOWER_BIND|COVENANT_TOWER_PEERS|COVENANT_TOWER_PORT)
                [ -z "${!k:-}" ] && export "$k=$v" ;;
        esac
    done < ops/tower.env
fi

if [ -x ".venv/bin/python" ]; then PY="$HERE/.venv/bin/python"; else PY="$(command -v python3)"; fi
[ -n "$PY" ] || { echo "python3 not found - install it (sudo apt install python3 python3-venv)"; exit 1; }

ID="${COVENANT_TOWER_ID:-}"
PORT="${COVENANT_TOWER_PORT:-5000}"
case "$PORT" in ''|*[!0-9]*) echo "COVENANT_TOWER_PORT must be a number"; exit 2 ;; esac

valid_id() {
    case "$ID" in
        A|B|C|D) echo "COVENANT_TOWER_ID=$ID is a production node (A, B, C on the laptop; D on the main PC). A tower is E to Z."; return 1 ;;
        [E-Z]) return 0 ;;
        *) echo "COVENANT_TOWER_ID must be one capital letter E to Z (got '$ID')."; return 1 ;;
    esac
}

bind_addr() {
    local b="${COVENANT_TOWER_BIND:-}"
    if [ -z "$b" ] && command -v tailscale >/dev/null 2>&1; then
        b="$(tailscale ip -4 2>/dev/null | head -n 1 | tr -d '\r ')"
    fi
    printf '%s' "$b"
}

healthy() {   # healthy HOST PORT -> 0 if /health answers within 5 s
    if command -v curl >/dev/null 2>&1; then
        curl -s -m 5 "http://$1:$2/health" >/dev/null 2>&1
    else
        "$PY" -c "import sys,urllib.request;urllib.request.urlopen('http://%s:%s/health'%(sys.argv[1],sys.argv[2]),timeout=5)" "$1" "$2" >/dev/null 2>&1
    fi
}

pids_here() {  # this checkout's processes whose command line matches $1
    local pid
    for pid in $(pgrep -f -- "$1" 2>/dev/null); do
        [ "$pid" = "$$" ] && continue
        [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$HERE" ] && printf '%s\n' "$pid"
    done
}

PATTERN() { printf 'run_node_bound.py --port %s --node-id %s' "$PORT" "$ID"; }

do_status() {
    local b; b="$(bind_addr)"
    if [ -n "$b" ] && "$PY" -c "import json,sys,urllib.request;d=json.load(urllib.request.urlopen('http://%s:%s/health'%(sys.argv[1],sys.argv[2]),timeout=6));print('  node',sys.argv[3],'on',sys.argv[1]+':'+sys.argv[2]+':','height',d.get('chain_height'),'peers',d.get('peers'),'judge',d.get('judge'),'insecure',d.get('judge_insecure'))" "$b" "$PORT" "$ID" 2>/dev/null; then :
    else echo "  node $ID on ${b:-?}:$PORT: DOWN"; fi
    return 0
}

do_stop() {
    local pids i
    stamp "stop requested (node $ID)"
    pids="$(pids_here "$(PATTERN)")"
    if [ -z "$pids" ]; then echo "  node $ID: not running"
    elif [ -n "$DRY" ]; then echo "DRY-RUN stop node $ID: TERM $pids"
    else
        kill -TERM $pids 2>/dev/null
        for i in 1 2 3 4 5 6 7 8 9 10; do pids="$(pids_here "$(PATTERN)")"; [ -z "$pids" ] && break; sleep 1; done
        if [ -n "$pids" ]; then kill -KILL $pids 2>/dev/null; echo "  node $ID: forced (KILL)"; else echo "  node $ID: stopped"; fi
    fi
    stamp "stopped. Database and key untouched."
    echo "Stopped. Nothing was deleted."
}

valid_id || exit 2
case "${1:-start}" in
    stop)   do_stop; exit 0 ;;
    status) do_status; exit 0 ;;
    start)  ;;
    *)      echo "usage: linux/covenant_tower.sh [start|stop|status]"; exit 2 ;;
esac

# ------------------------------------------------------------------ start --
stamp "start requested (node $ID)"
[ -f genesis.json ] || abort "genesis.json missing (copy it from the main PC; it is public)"

# A production key on this machine is a clone waiting to happen: refuse, name it, delete nothing.
for f in covenant_A.db.key nodeA_prod.db.key nodeB_prod.db.key nodeC_prod.db.key nodeD_prod.db.key \
         "$HOME/.covenant-keys/covenant_A.db.key"; do
    [ -e "$f" ] && abort "$f is here: it is a production node's key (the founder key or node A-D's). A tower must not hold it. Move it off this machine, then start again."
done

BIND="$(bind_addr)"
case "$BIND" in
    ''|0.0.0.0|::|'[::]') abort "no single address to listen on (got '${BIND}'). Join the tailnet first, or set COVENANT_TOWER_BIND." ;;
esac
PEERS="${COVENANT_TOWER_PEERS:-}"
[ -n "$PEERS" ] || abort "COVENANT_TOWER_PEERS is empty: a tower with no peers would hold a chain nobody else sees."

export COVENANT_LOCAL_JUDGE_TIMEOUT=600
export COVENANT_JUDGE_TIMEOUT=600
export COVENANT_JUDGE_PROVIDERS=deferring,semantic
unset COVENANT_INSECURE_MOCK_JUDGE

DB="node${ID}_prod.db"
if [ -f "$DB" ]; then stamp "resuming existing $DB"
else stamp "first run - $DB will be created by adopting genesis.json; the node makes its own key $DB.key"; fi

if [ -n "$(pids_here "$(PATTERN)")" ]; then
    # A node still loading answers no /health yet; a second copy would fight it for the database.
    stamp "node $ID already running (process $(pids_here "$(PATTERN)" | tr '\n' ' '))"
elif healthy "$BIND" "$PORT"; then
    stamp "node $ID already up on $BIND:$PORT"
else
    stamp "starting node $ID on $BIND:$PORT (peers $PEERS)"
    if [ -n "$DRY" ]; then
        echo "DRY-RUN launch: env COVENANT_DB_PATH=$DB COVENANT_BIND=$BIND $PY linux/run_node_bound.py --port $PORT --node-id $ID --genesis genesis.json --peers $PEERS >> logs/node$ID.log"
    else
        # umask 077: the key the node writes on first start is readable by this account only.
        ( umask 077; COVENANT_DB_PATH="$DB" COVENANT_BIND="$BIND" setsid nohup "$PY" linux/run_node_bound.py \
            --port "$PORT" --node-id "$ID" --genesis genesis.json --peers "$PEERS" >> "logs/node$ID.log" 2>&1 < /dev/null & )
        sleep "${COVENANT_TOWER_WAIT:-20}"
    fi
fi
stamp "start complete"
do_status
