#!/usr/bin/env bash
# Exercises linux/covenant_tower.sh and linux/run_node_bound.py (A500) in a throwaway copy with a FAKE core and a
# FAKE run_node.py. Nothing real is started or stopped. Each refusal is driven both ways.
#   bash linux/test_covenant_tower_sh.sh REPO_ROOT        -> must end "0 failed"
set -u
SRC="$1"
T="$(mktemp -d /tmp/covtower.XXXX)"; OTHER="$(mktemp -d /tmp/covtother.XXXX)"; H="$T/home"; mkdir -p "$H"
pass=0; fail=0
ok()  { echo "PASS  $1"; pass=$((pass+1)); }
bad() { echo "FAIL  $1"; fail=$((fail+1)); }

mkdir -p "$T/linux"; cp "$SRC/linux/covenant_tower.sh" "$SRC/linux/run_node_bound.py" "$T/linux/"
S="$T/linux/covenant_tower.sh"
# The fake core keeps the real class shape: a host default of "0.0.0.0" that the wrapper must replace.
cat > "$T/covenant_unified_v8.py" <<'EOF'
class CovenantUnifiedMaster:
    def __init__(self, node_id, host="0.0.0.0", port=5000):
        pass
EOF
# The fake run_node.py writes what the node would listen on, makes its key the way the core does (a new file), sleeps.
cat > "$T/run_node.py" <<'EOF'
import os, sys, time
import covenant_unified_v8 as cov
host = cov.CovenantUnifiedMaster.__init__.__defaults__[0]
db = os.environ["COVENANT_DB_PATH"]
open(db + ".host", "w").write("%s %s" % (host, os.environ.get("COVENANT_API_HOST")))
if not os.path.exists(db + ".key"):
    open(db + ".key", "w").write("fresh key %s" % time.time())
time.sleep(600)
EOF
run() { ( cd "$T" && HOME="$H" COVENANT_TOWER_WAIT=2 "$@" bash "$S" ${ARG:-} 2>&1 ); }
base=(COVENANT_TOWER_ID=E COVENANT_TOWER_BIND=127.0.0.1 COVENANT_TOWER_PEERS=127.0.0.9:5081 COVENANT_TOWER_PORT=5390)

bash -n "$S" && ok "syntax" || bad "syntax"

# 1. node id: A-D refused, E accepted, junk refused
for id in A B C D; do
    out="$(run env "${base[@]}" COVENANT_TOWER_ID=$id COVENANT_DRY_RUN=1)"; rc=$?
    [ $rc -eq 2 ] && grep -q "is a production node" <<<"$out" && ok "id $id refused" || bad "id $id not refused (rc=$rc)"
done
for id in e EE 1 ""; do
    out="$(run env "${base[@]}" COVENANT_TOWER_ID="$id" COVENANT_DRY_RUN=1)"; rc=$?
    [ $rc -eq 2 ] && ok "id '$id' refused" || bad "id '$id' not refused (rc=$rc)"
done

# 2. genesis: missing -> ABORT, present -> on to the next check
out="$(run env "${base[@]}" COVENANT_DRY_RUN=1)"; rc=$?
[ $rc -eq 1 ] && grep -q "ABORT: genesis.json missing" <<<"$out" && ok "abort without genesis" || bad "genesis (rc=$rc)"
echo '{}' > "$T/genesis.json"

# 3. production keys on the machine -> ABORT naming the file; removed -> no ABORT
for f in covenant_A.db.key nodeA_prod.db.key nodeD_prod.db.key; do
    echo founder > "$T/$f"
    out="$(run env "${base[@]}" COVENANT_DRY_RUN=1)"; rc=$?
    [ $rc -eq 1 ] && grep -q "ABORT: $f is here" <<<"$out" && ok "abort with $f present" || bad "no abort with $f (rc=$rc)"
    rm -f "$T/$f"
done
mkdir -p "$H/.covenant-keys"; echo founder > "$H/.covenant-keys/covenant_A.db.key"
out="$(run env "${base[@]}" COVENANT_DRY_RUN=1)"; rc=$?
[ $rc -eq 1 ] && grep -q "covenant-keys/covenant_A.db.key is here" <<<"$out" && ok "abort with ~/.covenant-keys founder key" || bad "home founder key (rc=$rc)"
rm -f "$H/.covenant-keys/covenant_A.db.key"

# 4. bind: every-interface refused, one address accepted
for b in 0.0.0.0 :: ; do
    out="$(run env "${base[@]}" COVENANT_TOWER_BIND="$b" COVENANT_DRY_RUN=1)"; rc=$?
    [ $rc -eq 1 ] && grep -q "no single address" <<<"$out" && ok "bind $b refused" || bad "bind $b (rc=$rc)"
done
out="$(PATH="/usr/bin:/bin" run env "${base[@]}" COVENANT_TOWER_BIND= COVENANT_DRY_RUN=1)"; rc=$?
if command -v tailscale >/dev/null 2>&1; then ok "bind empty: tailscale present here, not judged"
else [ $rc -eq 1 ] && grep -q "no single address" <<<"$out" && ok "bind empty and no tailscale refused" || bad "empty bind (rc=$rc)"; fi

# 5. peers: empty refused
out="$(run env "${base[@]}" COVENANT_TOWER_PEERS= COVENANT_DRY_RUN=1)"; rc=$?
[ $rc -eq 1 ] && grep -q "PEERS is empty" <<<"$out" && ok "empty peers refused" || bad "empty peers (rc=$rc)"

# 6. dry run: one launch through the wrapper, own db, the bind, the peers; no files written
out="$(run env "${base[@]}" COVENANT_DRY_RUN=1)"; rc=$?
n=$(grep -c "^DRY-RUN launch: .*run_node_bound.py" <<<"$out")
[ $rc -eq 0 ] && [ "$n" -eq 1 ] && ok "dry run: one launch" || bad "dry run: rc=$rc launches=$n"
grep -q "COVENANT_DB_PATH=nodeE_prod.db COVENANT_BIND=127.0.0.1 .*--port 5390 --node-id E --genesis genesis.json --peers 127.0.0.9:5081 " <<<"$out" && ok "launch line" || bad "launch line: $(grep DRY <<<"$out")"
[ ! -e "$T/nodeE_prod.db.key" ] && ok "dry run wrote no key" || bad "dry run wrote a key"

# 7. ops/tower.env supplies settings; the environment wins
printf 'COVENANT_TOWER_ID=F\r\nCOVENANT_TOWER_BIND=127.0.0.1\r\nCOVENANT_TOWER_PEERS=127.0.0.8:5081\r\nCOVENANT_TOWER_PORT=5391\r\n' > "$T/ops_env"
mkdir -p "$T/ops"; mv "$T/ops_env" "$T/ops/tower.env"
out="$( cd "$T" && HOME="$H" COVENANT_DRY_RUN=1 bash "$S" 2>&1 )"
grep -q -- "--port 5391 --node-id F --genesis genesis.json --peers 127.0.0.8:5081 " <<<"$out" && ok "tower.env read, CR stripped" || bad "tower.env: $(grep DRY <<<"$out")"
out="$( cd "$T" && HOME="$H" COVENANT_DRY_RUN=1 COVENANT_TOWER_ID=G bash "$S" 2>&1 )"
grep -q -- "--node-id G " <<<"$out" && ok "environment beats tower.env" || bad "env precedence"
printf 'COVENANT_TOWER_ID=E\nPATH=/nowhere\nCOVENANT_TOWER_BIND=127.0.0.1\nCOVENANT_TOWER_PEERS=127.0.0.9:5081\nCOVENANT_TOWER_PORT=5390\n' > "$T/ops/tower.env"
out="$( cd "$T" && HOME="$H" COVENANT_DRY_RUN=1 bash "$S" 2>&1 )"; rc=$?
[ $rc -eq 0 ] && ok "tower.env cannot set other variables (PATH ignored)" || bad "tower.env set PATH (rc=$rc)"
rm -rf "$T/ops"

# 8. the wrapper on its own: refuses every interface, a missing db name, a production key name, a copied key
W="$T/linux/run_node_bound.py"
# each must EXIT 1 with a reason; a broken wrapper would start the fake node instead (exit 124 at the time limit)
wrc() { ( cd "$T" && HOME="$H" timeout 5 env "$@" python3 "$W" >/dev/null 2>&1 ); echo $?; }
[ "$(wrc COVENANT_BIND=0.0.0.0 COVENANT_DB_PATH=nodeW_prod.db)" = 1 ] && ok "wrapper refuses 0.0.0.0" || bad "wrapper took 0.0.0.0"
[ "$(wrc COVENANT_BIND=127.0.0.1 COVENANT_DB_PATH=)" = 1 ] && ok "wrapper refuses a missing COVENANT_DB_PATH" || bad "wrapper took no db"
[ "$(wrc COVENANT_BIND=127.0.0.1 COVENANT_DB_PATH=nodeA_prod.db)" = 1 ] && ok "wrapper refuses node A's key name" || bad "wrapper took node A's db"
rm -f "$T"/nodeW_prod.db* "$T"/nodeA_prod.db.host "$T"/.db*
echo "same bytes" > "$T/nodeK_prod.db.key"; mkdir -p "$H/.covenant-keys"; echo "same bytes" > "$H/.covenant-keys/covenant_A.db.key"
out="$(cd "$T" && HOME="$H" COVENANT_BIND=127.0.0.1 COVENANT_DB_PATH=nodeK_prod.db timeout 5 python3 "$W" 2>&1)"; rc=$?
[ $rc -eq 1 ] && grep -q "copy of" <<<"$out" && ok "wrapper refuses a key copied from the founder key" || bad "copied key (rc=$rc)"
echo "different" > "$H/.covenant-keys/covenant_A.db.key"
out="$(cd "$T" && HOME="$H" COVENANT_BIND=127.0.0.1 COVENANT_DB_PATH=nodeK_prod.db timeout 3 python3 "$W" 2>&1)"; rc=$?
[ $rc -eq 124 ] && ok "wrapper starts the node when the key is its own (ran until stopped)" || bad "own key refused (rc=$rc: $out)"
rm -f "$H/.covenant-keys/covenant_A.db.key" "$T/nodeK_prod.db"*

# 9. REAL start with the fake core: one process, listening on the bind (not 0.0.0.0), key 600
out="$(run env "${base[@]}")"; rc=$?
running=$(pgrep -fc "run_node_bound.py --port 5390 --node-id E")
[ "$running" -eq 1 ] && ok "one node running after start" || bad "running: $running ($out)"
sleep 1
read -r host api < "$T/nodeE_prod.db.host" 2>/dev/null
[ "${host:-}" = 127.0.0.1 ] && [ "${api:-}" = 127.0.0.1 ] && ok "peer and API listeners on the bind ($host/$api)" || bad "listen host '${host:-}' api '${api:-}'"
[ "$(stat -c %a "$T/nodeE_prod.db.key" 2>/dev/null)" = 600 ] && ok "own key made with mode 600" || bad "key mode $(stat -c %a "$T/nodeE_prod.db.key" 2>/dev/null)"
key1="$(cat "$T/nodeE_prod.db.key")"

# 10. re-run does not start a second copy, even though the fake answers no /health (a node still loading)
out="$(run env "${base[@]}")"
running=$(pgrep -fc "run_node_bound.py --port 5390 --node-id E")
[ "$running" -eq 1 ] && grep -q "already running" <<<"$out" && ok "re-run: still one node" || bad "re-run: $running"

# 11. stop: ends this checkout's node only; another checkout's survives; nothing deleted; key unchanged
mkdir -p "$OTHER/linux"; cp "$T/linux/run_node_bound.py" "$OTHER/linux/"; cp "$T/covenant_unified_v8.py" "$T/run_node.py" "$OTHER/"
( cd "$OTHER" && COVENANT_BIND=127.0.0.1 COVENANT_DB_PATH="$OTHER/nodeE_prod.db" setsid nohup python3 linux/run_node_bound.py --port 5390 --node-id E >/dev/null 2>&1 & )
sleep 1
other_pid="$(for p in $(pgrep -f 'run_node_bound.py --port 5390 --node-id E'); do [ "$(readlink /proc/$p/cwd)" = "$OTHER" ] && echo $p; done | head -1)"
[ -n "$other_pid" ] && ok "another checkout's node is running (pid $other_pid)" || bad "the other checkout's node did not start"
out="$(ARG=stop run env "${base[@]}")"
left=$(for p in $(pgrep -f 'run_node_bound.py --port 5390'); do [ "$(readlink /proc/$p/cwd)" = "$T" ] && echo $p; done | wc -l)
[ "$left" -eq 0 ] && ok "stop ended this checkout's node" || bad "stop left $left"
[ -n "$other_pid" ] && kill -0 "$other_pid" 2>/dev/null && ok "other checkout's node survived" || bad "other checkout's node was killed"
grep -q "Nothing was deleted" <<<"$out" && [ -f "$T/nodeE_prod.db.key" ] && [ "$(cat "$T/nodeE_prod.db.key")" = "$key1" ] && ok "stop deleted nothing; key unchanged" || bad "stop: files"

# 12. restart keeps the same identity (the key is reused, not remade)
run env "${base[@]}" >/dev/null; sleep 1
[ "$(cat "$T/nodeE_prod.db.key")" = "$key1" ] && ok "restart keeps the same key" || bad "key changed on restart"
ARG=stop run env "${base[@]}" >/dev/null

[ -n "$other_pid" ] && kill "$other_pid" 2>/dev/null
echo "RESULT: $pass passed, $fail failed  (copy at $T)"
[ "$fail" -eq 0 ]
