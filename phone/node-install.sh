#!/data/data/com.termux/files/usr/bin/bash
# ---------------------------------------------------------------------------
# node-install.sh -- run a Covenant node on the phone.
#
# The node is the third copy of the ledger. Its job is survival: if the PC dies
# or the cloud goes away, the chain still exists here.
#
# PORT ARITHMETIC (this is what breaks multi-node setups):
#   a node started with --port N occupies THREE ports:  N (API), N+1 (P2P),
#   N+11 (bridge). So nodes must be at least 12 apart, and --peers must be
#   given each peer's P2P port -- their API port PLUS ONE.
#   Phone uses 5041 -> its P2P port is 5042.
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
echo " COVENANT NODE -- phone install"
echo "======================================================================"

[ -d "/data/data/com.termux" ] || { bad "not Termux"; exit 1; }

echo; echo "[1/5] packages"
pkg install -y python openssl libffi rust binutils >/dev/null 2>&1
# `cryptography` has a Rust extension; on Termux it must be built, and it needs
# these env vars or the build fails halfway through with a linker error.
export CARGO_BUILD_TARGET="$(uname -m)-linux-android"
export RUSTFLAGS="-C link-arg=-Wl,-z,max-page-size=16384"
python -c "import cryptography" 2>/dev/null && ok "cryptography already present" || {
    echo "     building cryptography (this is the slow part, 5-15 min)..."
    pip install --no-cache-dir cryptography >/dev/null 2>&1 \
        && ok "cryptography built" \
        || { bad "cryptography failed to build"
             echo "     try:  pkg install python-cryptography"
             echo "     the node cannot sign anything without it."; exit 1; }
}

echo; echo "[2/5] files"
mkdir -p "$HERE"
for f in covenant_unified_v8.py covenant_client.py genesis.json; do
    if [ -f "$HOME/storage/downloads/$f" ]; then cp "$HOME/storage/downloads/$f" "$HERE/$f"; ok "$f"
    elif [ -f "$HERE/$f" ]; then ok "$f (already here)"
    else bad "$f missing from Downloads"; MISSING=1; fi
done
[ "${MISSING:-0}" = "1" ] && { bad "download the missing files first"; exit 1; }

echo; echo "[3/5] peer configuration"
cat > "$HERE/node-peers.conf" <<'CONF'
# Each line: HOST:P2P_PORT   (the peer's API port + 1)
# PC on the same wifi, api 5001 -> p2p 5002. Replace with your PC's LAN IP:
# 192.168.1.50:5002
#
# Over cellular your phone is behind carrier NAT and cannot reach a home PC
# directly, nor be reached. Install Tailscale on BOTH and use the 100.x.y.z
# addresses here instead -- that works from anywhere.
CONF
ok "wrote node-peers.conf (edit it with: nano ~/covenant/node-peers.conf)"

echo; echo "[4/5] runner"
cat > "$HERE/node-run.sh" <<'RUN'
#!/data/data/com.termux/files/usr/bin/bash
HERE="$HOME/covenant"; cd "$HERE" || exit 1
PEERS=$(grep -vE '^\s*#|^\s*$' node-peers.conf 2>/dev/null | paste -sd, -)
termux-wake-lock 2>/dev/null
export COVENANT_DB_PATH="$HERE/phone.db"
echo "$(date '+%F %T') node starting (peers: ${PEERS:-none})" >> "$HERE/state/node.log"
exec python covenant_unified_v8.py --port 5041 --node-id PHONE \
     --genesis "$HERE/genesis.json" ${PEERS:+--peers "$PEERS"} \
     >> "$HERE/state/node.log" 2>&1
RUN
chmod +x "$HERE/node-run.sh"; mkdir -p "$HERE/state"; ok "node-run.sh"

echo; echo "[5/5] survive reboot"
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/start-covenant-node" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sleep 20
$HOME/covenant/node-run.sh &
BOOT
chmod +x "$HOME/.termux/boot/start-covenant-node"; ok "boot script"

echo
echo "======================================================================"
echo "  start it :  ~/covenant/node-run.sh &"
echo "  check it :  curl -s localhost:$API_PORT/chain | head -c 200"
echo "  this node:  API $API_PORT   P2P $P2P_PORT   bridge $((P2P_PORT+10))"
echo
warn "Battery: Settings > Apps > Termux > Battery > Unrestricted."
warn "Without it Android kills the node within days, silently."
echo "======================================================================"
