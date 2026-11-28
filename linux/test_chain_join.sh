#!/usr/bin/env bash
# ============================================================================
#  linux/test_chain_join.sh -- can a fresh Linux node join an existing chain? (A498)
#
#  Two throwaway nodes on this machine, on spare ports, in a temp folder:
#    A serves a COPY of a chain database (its stored peer list emptied, so it
#      can reach nobody), started with the given genesis.json;
#    B starts EMPTY with the same genesis.json and lists only A.
#  B must reach A's length with the same tip hash. Both start through
#  run_node.py with the production judge settings (as linux/covenant_prod.sh),
#  and both get a throwaway HOME, so no real identity key is read or written.
#  Nothing outside this machine is contacted; the database given is only read.
#
#  USAGE
#    bash linux/test_chain_join.sh <chain.db> <genesis.json> [A_PORT] [B_PORT]
#  e.g. on a tower, with copies brought from the running install:
#    bash linux/test_chain_join.sh ~/nodeA_prod.db.copy ~/covenant/genesis.json
#  Take the copy with SQLite's backup (python3 -c "import sqlite3; ...backup...")
#  or from a stopped node: a plain cp of a live database can be torn.
#
#  Exit 0 only when B converged on A's exact tip.
# ============================================================================
set -u
DB="${1:?usage: test_chain_join.sh <chain.db> <genesis.json> [A_PORT] [B_PORT]}"
GEN="${2:?usage: test_chain_join.sh <chain.db> <genesis.json> [A_PORT] [B_PORT]}"
AP="${3:-19900}"; BP="${4:-19912}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [ -x "$HERE/.venv/bin/python" ]; then PY="$HERE/.venv/bin/python"; else PY="$(command -v python3)"; fi
X="$(mktemp -d /tmp/chainjoin.XXXX)"; mkdir -p "$X/homeA" "$X/homeB"
cp "$DB" "$X/A.db" && cp "$GEN" "$X/genesis.json" || { echo "cannot read $DB or $GEN"; exit 2; }
"$PY" - "$X/A.db" <<'PY'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
n = c.execute("select count(*) from peer_registrations").fetchone()[0]
c.execute("delete from peer_registrations"); c.commit()
print("A: a copy with %d blocks; %d stored peer registration(s) emptied" % (c.execute("select count(*) from blocks").fetchone()[0], n))
PY
# A throwaway HOME hides a per-user package folder, so keep pointing Python at the real one.
USERBASE="$("$PY" -c 'import site; print(site.getuserbase())')"
ENVV=(COVENANT_JUDGE_PROVIDERS=deferring,semantic COVENANT_LOCAL_JUDGE_TIMEOUT=600 COVENANT_JUDGE_TIMEOUT=600
      COVENANT_TIP_GOSSIP_INTERVAL=3 PYTHONUNBUFFERED=1 PYTHONUSERBASE="$USERBASE")
cd "$HERE" || exit 2
env "${ENVV[@]}" HOME="$X/homeA" COVENANT_DB_PATH="$X/A.db" "$PY" run_node.py --port "$AP" --node-id A --genesis "$X/genesis.json" > "$X/A.log" 2>&1 &
PA=$!
cleanup() { kill "$PA" "${PB:-}" 2>/dev/null; wait 2>/dev/null; }
trap cleanup EXIT
tip() { curl -s -m 10 "http://127.0.0.1:$1/chain" | "$PY" -c 'import json,sys; d=json.load(sys.stdin); c=d.get("chain", d); print(len(c), c[-1].get("hash"))' 2>/dev/null; }
for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$AP/health" >/dev/null && break; sleep 2; done
TA="$(tip "$AP")"; [ -n "$TA" ] || { echo "A did not start; see $X/A.log"; exit 1; }
echo "A: length/tip $TA"
env "${ENVV[@]}" HOME="$X/homeB" COVENANT_DB_PATH="$X/B.db" "$PY" run_node.py --port "$BP" --node-id B --genesis "$X/genesis.json" --peers "127.0.0.1:$((AP + 1))" > "$X/B.log" 2>&1 &
PB=$!
for i in $(seq 1 150); do TB="$(tip "$BP")"; [ "$TB" = "$TA" ] && break; sleep 3; done
echo "B: length/tip ${TB:-none}"
if [ "${TB:-}" = "$TA" ]; then
    echo "RESULT: PASS -- a fresh node joined the chain: same length, same tip hash ($X)"
    exit 0
fi
echo "RESULT: FAIL -- B did not converge on A; refusals in B's log:"
grep -aE 'SYNC REFUSED|Traceback|Error' "$X/B.log" | tail -5
exit 1
