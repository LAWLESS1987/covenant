#!/usr/bin/env bash
# ============================================================================
#  linux/covenant_prod.sh -- production start/stop/status on Linux (Debian).
#  The Linux port of covenant_prod.bat. NOT a test rig.
#
#  Like the .bat, it NEVER deletes a database: it creates one only if none
#  exists, and otherwise resumes. It does not prompt and does not wipe.
#
#  USAGE (from anywhere; it works from the repository root)
#    linux/covenant_prod.sh            start (idempotent - safe to re-run)
#    linux/covenant_prod.sh stop
#    linux/covenant_prod.sh status
#
#  WHAT IT DOES NOT DO: install itself to start at boot, or schedule anything.
#  Nothing here outlives a reboot unless you set that up yourself
#  (see linux/README.md, "Starting at boot", and A14 in docs/KNOWN_ISSUES.md).
#
#  Where it deliberately differs from covenant_prod.bat, and why:
#   * stop finds processes by command line AND by working directory, not by
#     window title. The .bat's title match cannot see a node the watchdog
#     restarted (that node has no titled window); the command line can. The
#     working-directory check keeps it from stopping another checkout's nodes.
#   * stop ends the watchdog FIRST, then the nodes, so the watchdog cannot
#     revive a node in the gap.
#   * stop sends TERM, waits up to 10 s, then KILL. The .bat used taskkill /f.
#
#  COVENANT_DRY_RUN=1 prints every launch and kill instead of doing it, so
#  the script can be exercised without starting or stopping anything.
# ============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$HERE" || exit 1
mkdir -p logs
LOG="logs/prod.log"
DRY="${COVENANT_DRY_RUN:-}"

stamp() {
    printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG"
    printf '%s\n' "$1"
}

if [ -x ".venv/bin/python" ]; then PY="$HERE/.venv/bin/python"; else PY="$(command -v python3)"; fi
if [ -z "$PY" ]; then echo "python3 not found - install it (sudo apt install python3 python3-venv)"; exit 1; fi

# The three production nodes: id, port, peers. Same values as covenant_prod.bat.
NODES="A:5000 B:5020 C:5060"
peers_for() {
    case "$1" in
        A) printf '127.0.0.1:5021%s' "$A_EXTRA" ;;
        B) printf '127.0.0.1:5001,127.0.0.1:5061' ;;
        C) printf '127.0.0.1:5021' ;;
    esac
}

healthy() {   # healthy PORT -> 0 if /health answers within 5 s
    curl -s -m 5 "http://127.0.0.1:$1/health" >/dev/null 2>&1
}

# PIDs of processes whose command line matches $1 AND whose working directory
# is this checkout. pgrep alone would also match another checkout's nodes.
pids_here() {
    local pid
    for pid in $(pgrep -f -- "$1" 2>/dev/null); do
        [ "$pid" = "$$" ] && continue
        [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$HERE" ] && printf '%s\n' "$pid"
    done
}

launch() {    # launch LOGFILE CMD... -> detached, survives this shell
    local out="$1"; shift
    if [ -n "$DRY" ]; then echo "DRY-RUN launch: $* >> $out"; return 0; fi
    setsid nohup "$@" >> "$out" 2>&1 < /dev/null &
}

end_procs() { # end_procs LABEL PATTERN
    local label="$1" pids i
    pids="$(pids_here "$2")"
    [ -z "$pids" ] && { echo "  $label: not running"; return 0; }
    if [ -n "$DRY" ]; then echo "DRY-RUN stop $label: TERM $pids"; return 0; fi
    kill -TERM $pids 2>/dev/null
    for i in 1 2 3 4 5 6 7 8 9 10; do
        pids="$(pids_here "$2")"; [ -z "$pids" ] && break; sleep 1
    done
    if [ -n "$pids" ]; then kill -KILL $pids 2>/dev/null; echo "  $label: forced (KILL)"; else echo "  $label: stopped"; fi
}

do_status() {
    local id port tmp
    tmp="$(mktemp)"
    for n in $NODES; do
        id="${n%%:*}"; port="${n##*:}"
        if curl -s -m 6 "http://127.0.0.1:$port/health" > "$tmp" 2>/dev/null; then
            printf '  node %s on %s: ' "$id" "$port"
            "$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));print('height',d.get('chain_height'),'peers',d.get('peers'),'judge',d.get('judge'),'insecure',d.get('judge_insecure'))" "$tmp" 2>/dev/null || echo "answered, but not as JSON"
        else
            echo "  node $id on $port: DOWN"
        fi
    done
    rm -f "$tmp"
    # --once only reports: in strict mode nothing is restarted (covenant_watchdog.py, one_pass).
    if [ -n "$DRY" ]; then echo "DRY-RUN: $PY covenant_watchdog.py --once"; return 0; fi
    if "$PY" covenant_watchdog.py --once; then echo "  >> all checks passed."; else echo "  >> ALERTS above."; fi
    return 0
}

do_stop() {
    stamp "stop requested"
    end_procs "watchdog" "covenant_watchdog.py --interval"
    for n in $NODES; do
        id="${n%%:*}"; port="${n##*:}"
        end_procs "node $id" "run_node.py --port $port --node-id $id"
    done
    stamp "stopped. Databases untouched - covenant_prod.sh resumes them."
    echo "Stopped. Nothing was deleted."
}

case "${1:-start}" in
    stop)   do_stop; exit 0 ;;
    status) do_status; exit 0 ;;
    start)  ;;
    *)      echo "usage: linux/covenant_prod.sh [start|stop|status]"; exit 2 ;;
esac

# ------------------------------------------------------------------ start --
export COVENANT_LOCAL_JUDGE_TIMEOUT=600
export COVENANT_JUDGE_TIMEOUT=600
export COVENANT_JUDGE_PROVIDERS=deferring,semantic
unset COVENANT_INSECURE_MOCK_JUDGE
stamp "start requested"

[ -f genesis.json ]      || { stamp "ABORT: genesis.json missing"; exit 1; }
[ -f covenant_A.db.key ] || { stamp "ABORT: covenant_A.db.key missing"; exit 1; }

KEYS="$HOME/.covenant-keys"
if [ -z "$DRY" ]; then
    mkdir -p "$KEYS" && chmod 700 "$KEYS"
    if [ ! -f "$KEYS/covenant_A.db.key" ]; then cp covenant_A.db.key "$KEYS/covenant_A.db.key" && chmod 600 "$KEYS/covenant_A.db.key"; fi
    if [ ! -f nodeA_prod.db.key ]; then cp covenant_A.db.key nodeA_prod.db.key && chmod 600 nodeA_prod.db.key; fi
fi

for n in $NODES; do
    id="${n%%:*}"
    if [ -f "node${id}_prod.db" ]; then stamp "resuming existing node${id}_prod.db"
    else stamp "first run - node${id}_prod.db will be created by adopting genesis.json"; fi
done

A_EXTRA=""
if [ -f ops/local_peers.txt ]; then
    A_EXTRA="$(head -n 1 ops/local_peers.txt | tr -d '\r\n')"
    [ -n "$A_EXTRA" ] && A_EXTRA=",$A_EXTRA"
fi

for n in $NODES; do
    id="${n%%:*}"; port="${n##*:}"
    if healthy "$port"; then
        stamp "node $id already up"
    else
        stamp "starting node $id on $port"
        launch "logs/node$id.log" env "COVENANT_DB_PATH=node${id}_prod.db" \
            "$PY" run_node.py --port "$port" --node-id "$id" --genesis genesis.json --peers "$(peers_for "$id")"
    fi
done

[ -z "$DRY" ] && sleep 20
if [ -n "$(pids_here "covenant_watchdog.py --interval")" ]; then
    stamp "watchdog already running"
else
    stamp "starting watchdog"
    launch "logs/watchdog-stdout.log" "$PY" "$HERE/covenant_watchdog.py" --interval 60
fi
[ -z "$DRY" ] && sleep 5
stamp "start complete"
do_status
