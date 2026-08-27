#!/data/data/com.termux/files/usr/bin/bash
# ---------------------------------------------------------------------------
# node-install-v2.sh -- a Covenant node on the phone, with a judge that works.
#
# WHAT v1 GOT WRONG
#   node-install.sh launches covenant_unified_v8.py directly. That node builds
#   the DEFAULT judge, which with no API key fails closed and rejects every
#   transaction -- including every one your PC nodes propagate to it. The phone
#   would sit there looking healthy, peered, serving /chain, and silently
#   refusing to replicate anything. That is not a backup; it is a node that has
#   quietly left the chain.
#
#   A replica is NOT passive. covenant_unified_v8.py line 6647 re-judges every
#   transaction arriving over P2P, independently. Every node needs a working
#   judge or it stops accepting the chain.
#
#   This version runs run_with_ollama_judge.py instead, and refuses to schedule
#   itself until the judge has actually returned a verdict.
#
# WHERE THE JUDGE LIVES
#   Not here. A phone cannot host a model that passes the 37-case suite -- the
#   1.7B that fits fails two category thresholds, and an 8B on a phone CPU is
#   minutes per verdict. So the phone points at the PC's Ollama.
#
#   Set COVENANT_LOCAL_JUDGE_URL in ~/covenant/node.env. Over wifi that is the
#   PC's LAN address. Over cellular your phone is behind carrier NAT and cannot
#   reach a home PC at all -- use Tailscale on both and the 100.x address.
#   See PHONE_NODE.md; the trade-offs are real and worth reading first.
#
# PORT ARITHMETIC (unchanged from v1, and still the thing that breaks setups)
#   --port N occupies N (API), N+1 (P2P), N+11 (bridge). Nodes must be 12+
#   apart, and --peers takes each peer's P2P port = their API port + 1.
#     PC node A  api 5000 -> p2p 5001
#     PC node B  api 5020 -> p2p 5021
#     phone      api 5041 -> p2p 5042
# ---------------------------------------------------------------------------
set -uo pipefail
HERE="$HOME/covenant"
API_PORT=5041
P2P_PORT=$((API_PORT + 1))
GREEN=$'\033[32m'; RED=$'\033[31m'; YEL=$'\033[33m'; OFF=$'\033[0m'
ok()   { echo "${GREEN}  ok${OFF}   $*"; }
warn() { echo "${YEL}  warn${OFF} $*"; }
bad()  { echo "${RED}  X${OFF}    $*"; }

echo "======================================================================"
echo " COVENANT NODE -- phone install v2 (with a judge)"
echo "======================================================================"

[ -d "/data/data/com.termux" ] || { bad "not Termux -- get Termux from F-Droid, not Play Store"; exit 1; }

echo; echo "[1/6] packages"
pkg install -y python openssl libffi rust binutils curl >/dev/null 2>&1
# cryptography has a Rust extension; on Termux it must be built, and it needs
# these or the build dies halfway with a linker error.
export CARGO_BUILD_TARGET="$(uname -m)-linux-android"
export RUSTFLAGS="-C link-arg=-Wl,-z,max-page-size=16384"
python -c "import cryptography" 2>/dev/null && ok "cryptography present" || {
    echo "     building cryptography (slow: 5-15 min)..."
    pip install --no-cache-dir cryptography >/dev/null 2>&1 \
        && ok "cryptography built" \
        || { bad "cryptography failed"; echo "     try: pkg install python-cryptography"; exit 1; }
}
python -c "import flask, requests" 2>/dev/null && ok "flask + requests present" || {
    pip install --no-cache-dir flask requests >/dev/null 2>&1 && ok "flask + requests" \
        || { bad "flask/requests failed"; exit 1; }
}

echo; echo "[2/6] files"
mkdir -p "$HERE" "$HERE/state"
MISSING=0
# The judge modules are the difference between this and v1. Without
# covenant_judge_ollama.py + run_with_ollama_judge.py the node has no judge and
# rejects the chain.
for f in covenant_unified_v8.py covenant_client.py covenant_path_pattern.py \
         covenant_judge_local.py covenant_judge_ollama.py \
         run_with_ollama_judge.py genesis.json; do
    if [ -f "$HOME/storage/downloads/$f" ]; then cp "$HOME/storage/downloads/$f" "$HERE/$f"; ok "$f"
    elif [ -f "$HERE/$f" ]; then ok "$f (already here)"
    else bad "$f missing from Downloads"; MISSING=1; fi
done
for f in judge_suite.py judge_bench.py judge_config.json; do
    if [ -f "$HOME/storage/downloads/$f" ]; then cp "$HOME/storage/downloads/$f" "$HERE/$f"; ok "$f (optional)"; fi
done
[ "$MISSING" = "1" ] && { bad "download the missing files to the phone first"; exit 1; }

echo; echo "[3/6] judge + peer configuration"
if [ -f "$HERE/node.env" ]; then
    ok "node.env already exists, leaving it alone"
else
cat > "$HERE/node.env" <<'ENV'
# ---------------------------------------------------------------------------
# WHERE THE JUDGE LIVES. This is the setting that decides whether this node
# replicates the chain or silently refuses every transaction on it.
#
# Wifi, same network as the PC:
#   COVENANT_LOCAL_JUDGE_URL=http://192.168.1.50:11434/v1/chat/completions
#   ...and on the PC, Ollama must be bound to something the phone can reach.
#   By default it is loopback-only, so it will NOT answer the phone.
#
# Anywhere, including cellular (recommended -- see PHONE_NODE.md):
#   Tailscale on both devices, then use the PC's 100.x address:
#   COVENANT_LOCAL_JUDGE_URL=http://100.101.102.103:11434/v1/chat/completions
#
# Carrier NAT means the plain-LAN option simply cannot work off wifi. That is
# not a config mistake, it is how mobile networks are built.
# ---------------------------------------------------------------------------
COVENANT_LOCAL_JUDGE_URL=http://CHANGE-ME:11434/v1/chat/completions
COVENANT_LOCAL_JUDGE_MODEL=qwen3:8b

# Generous on purpose. A judge TIMEOUT is recorded as a VIOLATION, so a slow
# link silently rejects transactions. Over a phone link, longer than the PC's.
COVENANT_LOCAL_JUDGE_TIMEOUT=900
COVENANT_JUDGE_TIMEOUT=900
COVENANT_JUDGE_PROVIDERS=local
COVENANT_OLLAMA_NUM_CTX=2048
COVENANT_OLLAMA_NUM_PREDICT=96
COVENANT_OLLAMA_KEEP_ALIVE=60m
ENV
    ok "wrote node.env  -- EDIT IT:  nano ~/covenant/node.env"
fi

if [ -f "$HERE/node-peers.conf" ]; then
    ok "node-peers.conf already exists"
else
cat > "$HERE/node-peers.conf" <<'CONF'
# Each line: HOST:P2P_PORT   -- the peer's API port PLUS ONE.
# Getting this wrong is silent: peer messages hit the peer's Flask port, Flask
# answers "400 Bad request version", nothing is logged on this side, and the
# nodes look peered while sharing nothing.
#
# The PC currently runs node A on api 5000 and node B on api 5020, so:
#   <PC-ADDRESS>:5001      <- node A's P2P
#   <PC-ADDRESS>:5021      <- node B's P2P
#
# Uncomment and set the address (LAN IP on wifi, 100.x on Tailscale):
# 192.168.1.50:5001
# 192.168.1.50:5021
CONF
    ok "wrote node-peers.conf -- EDIT IT: nano ~/covenant/node-peers.conf"
fi

echo; echo "[4/6] judge smoke test"
set -a; . "$HERE/node.env" 2>/dev/null; set +a
if echo "${COVENANT_LOCAL_JUDGE_URL:-}" | grep -q "CHANGE-ME"; then
    warn "node.env still says CHANGE-ME -- edit it, then re-run this script."
    warn "Not scheduling anything. A node with no judge rejects the whole chain,"
    warn "and it does it quietly."
    JUDGE_OK=0
else
    BASE="${COVENANT_LOCAL_JUDGE_URL%/v1/chat/completions}"
    if curl -s -m 10 "$BASE/api/tags" >/dev/null 2>&1; then
        ok "Ollama reachable at $BASE"
        cd "$HERE"
        if python - <<'PY' 2>/dev/null
import os, sys
sys.path.insert(0, os.path.expanduser("~/covenant"))
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
import covenant_unified_v8 as cov, covenant_judge_local, covenant_judge_ollama as O
r = O.OllamaJudge(judge_id="local:1").evaluate(
    {"message": "a gift of 5 units to a friend", "origin": "organic"},
    list(cov.DIVINE_PRINCIPLES))
# A judge that says a plain gift VIOLATES is not working -- most likely the
# endpoint is answering but the model is wrong or the context is truncated.
sys.exit(0 if r.violates is False else 1)
PY
        then ok "judge returned a correct verdict on a benign gift"; JUDGE_OK=1
        else bad "judge reachable but its verdict was wrong or it errored"
             warn "run: cd ~/covenant && python judge_bench.py --quick"; JUDGE_OK=0; fi
    else
        bad "cannot reach Ollama at $BASE"
        warn "on the PC Ollama is bound to loopback by default -- it will not"
        warn "answer the phone until you bind it to the tailnet. PHONE_NODE.md."
        JUDGE_OK=0
    fi
fi

echo; echo "[5/6] runner"
cat > "$HERE/node-run.sh" <<'RUN'
#!/data/data/com.termux/files/usr/bin/bash
HERE="$HOME/covenant"; cd "$HERE" || exit 1
set -a; . "$HERE/node.env" 2>/dev/null; set +a
PEERS=$(grep -vE '^\s*#|^\s*$' node-peers.conf 2>/dev/null | paste -sd, -)
termux-wake-lock 2>/dev/null
export COVENANT_DB_PATH="$HERE/phone.db"
unset COVENANT_INSECURE_MOCK_JUDGE
mkdir -p "$HERE/state"
echo "$(date '+%F %T') node starting (peers: ${PEERS:-NONE}) judge: ${COVENANT_LOCAL_JUDGE_URL:-UNSET}" >> "$HERE/state/node.log"
# run_with_ollama_judge.py, NOT covenant_unified_v8.py -- the import is what
# registers a working judge. Launching the module directly gives you the
# keyless default, which rejects the entire chain.
exec python run_with_ollama_judge.py --port 5041 --node-id PHONE \
     --genesis "$HERE/genesis.json" ${PEERS:+--peers "$PEERS"} \
     >> "$HERE/state/node.log" 2>&1
RUN
chmod +x "$HERE/node-run.sh"; ok "node-run.sh (uses the tuned judge)"

echo; echo "[6/6] survive reboot"
if [ "${JUDGE_OK:-0}" = "1" ]; then
    mkdir -p "$HOME/.termux/boot"
    cat > "$HOME/.termux/boot/start-covenant-node" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sleep 20
$HOME/covenant/node-run.sh &
BOOT
    chmod +x "$HOME/.termux/boot/start-covenant-node"
    ok "boot script installed"
else
    warn "boot script NOT installed -- the judge has not worked once yet."
    warn "A scheduled node that has never judged anything produces silence you"
    warn "would read as good news. Fix node.env, re-run this script."
fi

echo
echo "======================================================================"
echo "  start   :  ~/covenant/node-run.sh &"
echo "  health  :  curl -s localhost:$API_PORT/health"
echo "  log     :  tail -f ~/covenant/state/node.log"
echo "  this node: API $API_PORT  P2P $P2P_PORT  bridge $((P2P_PORT + 10))"
echo
warn "Battery: Settings > Apps > Termux > Battery > Unrestricted."
warn "Without it Android kills the node within days, silently."
echo
warn "On the PC, add the phone as a peer so replication goes BOTH ways:"
warn "  node A --peers 127.0.0.1:5021,<PHONE-ADDRESS>:5042"
warn "  node B --peers 127.0.0.1:5001,<PHONE-ADDRESS>:5042"
echo "======================================================================"
