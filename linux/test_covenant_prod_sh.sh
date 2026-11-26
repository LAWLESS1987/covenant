#!/usr/bin/env bash
# Exercises linux/covenant_prod.sh in a throwaway copy with FAKE nodes.
# Nothing real is started or stopped. Each check is driven both ways.
set -u
SRC="$1"
T="$(mktemp -d /tmp/covprod.XXXX)"; OTHER="$(mktemp -d /tmp/covother.XXXX)"
pass=0; fail=0
ok()  { echo "PASS  $1"; pass=$((pass+1)); }
bad() { echo "FAIL  $1"; fail=$((fail+1)); }

mkdir -p "$T/linux"; cp "$SRC/linux/covenant_prod.sh" "$T/linux/"; S="$T/linux/covenant_prod.sh"
cat > "$T/run_node.py" <<'EOF'
import time
time.sleep(600)
EOF
cat > "$T/covenant_watchdog.py" <<'EOF'
import sys, time
if "--once" in sys.argv: print("fake watchdog --once"); sys.exit(0)
time.sleep(600)
EOF
cp "$T/run_node.py" "$OTHER/run_node.py"

bash -n "$S" && ok "syntax" || bad "syntax"

# 1. missing genesis -> ABORT, exit 1   (and the other way: present -> no ABORT)
out="$(COVENANT_DRY_RUN=1 bash "$S" 2>&1)"; rc=$?
[ $rc -eq 1 ] && grep -q "ABORT: genesis.json missing" <<<"$out" && ok "abort without genesis (rc=$rc)" || bad "abort without genesis (rc=$rc)"
echo '{}' > "$T/genesis.json"
out="$(COVENANT_DRY_RUN=1 bash "$S" 2>&1)"; rc=$?
[ $rc -eq 1 ] && grep -q "ABORT: covenant_A.db.key missing" <<<"$out" && ok "abort without key once genesis exists" || bad "abort without key"
echo 'dummy' > "$T/covenant_A.db.key"

# 2. dry run launches 3 nodes with the .bat's peers, then the watchdog; touches no keys
out="$(HOME="$T/home" COVENANT_DRY_RUN=1 bash "$S" 2>&1)"; rc=$?
n=$(grep -c "^DRY-RUN launch: .*run_node.py" <<<"$out")
[ "$n" -eq 3 ] && ok "dry run: 3 node launches" || bad "dry run: $n node launches"
grep -q -- "--node-id A --genesis genesis.json --peers 127.0.0.1:5021 " <<<"$out" && ok "peers A" || bad "peers A"
grep -q -- "--node-id B --genesis genesis.json --peers 127.0.0.1:5001,127.0.0.1:5061 " <<<"$out" && ok "peers B" || bad "peers B"
grep -q -- "--node-id C --genesis genesis.json --peers 127.0.0.1:5021 " <<<"$out" && ok "peers C" || bad "peers C"
grep -q "COVENANT_DB_PATH=nodeB_prod.db" <<<"$out" && ok "node B db path" || bad "node B db path"
grep -q "DRY-RUN launch: .*covenant_watchdog.py --interval 60" <<<"$out" && ok "watchdog launch" || bad "watchdog launch"
[ ! -e "$T/home/.covenant-keys" ] && [ ! -e "$T/nodeA_prod.db.key" ] && ok "dry run wrote no key files" || bad "dry run wrote key files"

# 3. local_peers.txt is appended to A only (both ways: with CRLF line ending)
printf '10.0.0.7:5000\r\n' > "$T/ops_tmp"; mkdir -p "$T/ops"; mv "$T/ops_tmp" "$T/ops/local_peers.txt"
out="$(HOME="$T/home" COVENANT_DRY_RUN=1 bash "$S" 2>&1)"
grep -q -- "--node-id A --genesis genesis.json --peers 127.0.0.1:5021,10.0.0.7:5000 >>" <<<"$out" && ok "local peer appended to A, CR stripped" || bad "local peer for A"
grep -q -- "--node-id C .*10.0.0.7" <<<"$out" && bad "local peer leaked to C" || ok "local peer not given to C"
rm -rf "$T/ops"

# 4. REAL start with fake nodes: keys copied with tight permissions, processes running
out="$(HOME="$T/home" bash "$S" 2>&1)"
[ "$(stat -c %a "$T/home/.covenant-keys")" = 700 ] && ok "key dir 700" || bad "key dir mode"
[ "$(stat -c %a "$T/home/.covenant-keys/covenant_A.db.key")" = 600 ] && ok "key file 600" || bad "key file mode"
running=$(pgrep -fc "run_node.py --port")
[ "$running" -ge 3 ] && ok "fake nodes running after start ($running)" || bad "fake nodes running ($running)"
pgrep -f "covenant_watchdog.py --interval" >/dev/null && ok "fake watchdog running" || bad "fake watchdog not running"
grep -q "node A on 5000: DOWN" <<<"$out" && ok "status reports silent node as DOWN" || bad "status DOWN line"

# 5. second start must not launch a second watchdog
HOME="$T/home" bash "$S" >/dev/null 2>&1
wd=$(pgrep -fc "covenant_watchdog.py --interval")
[ "$wd" -eq 1 ] && ok "re-run: still one watchdog" || bad "re-run: $wd watchdogs"

# 6. a matching process from ANOTHER directory must survive stop
( cd "$OTHER" && setsid nohup python3 run_node.py --port 5000 --node-id A >/dev/null 2>&1 & )
sleep 1
other_pid="$(for p in $(pgrep -f 'run_node.py --port 5000 --node-id A'); do [ "$(readlink /proc/$p/cwd)" = "$OTHER" ] && echo $p; done)"
out="$(HOME="$T/home" bash "$S" stop 2>&1)"
grep -n "watchdog" <<<"$out" | head -1 | grep -q "watchdog: stopped" && ok "watchdog stopped first" || bad "watchdog order: $(head -3 <<<"$out")"
left=$(for p in $(pgrep -f 'run_node.py --port|covenant_watchdog.py --interval'); do [ "$(readlink /proc/$p/cwd)" = "$T" ] && echo $p; done | wc -l)
[ "$left" -eq 0 ] && ok "stop ended all fake processes here" || bad "stop left $left here"
[ -n "$other_pid" ] && kill -0 "$other_pid" 2>/dev/null && ok "other checkout's node survived stop" || bad "other checkout's node was killed"
grep -q "Nothing was deleted" <<<"$out" && ok "stop message" || bad "stop message"
[ -f "$T/genesis.json" ] && [ -f "$T/covenant_A.db.key" ] && ok "stop deleted nothing" || bad "stop deleted files"

# cleanup of the test's own fakes
[ -n "$other_pid" ] && kill "$other_pid" 2>/dev/null
echo "RESULT: $pass passed, $fail failed  (copy at $T)"
