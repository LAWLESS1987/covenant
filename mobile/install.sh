#!/bin/sh
# install.sh -- one command, in Termux on Android, installs and starts a covenant node
# with a local judge. Idempotent: run it again to update and restart.
#
#   curl -sL https://raw.githubusercontent.com/LAWLESS1987/covenant/main/mobile/install.sh | sh
#
# Or, the way this project prefers: download it, read it, then run it.
#   curl -sLO https://raw.githubusercontent.com/LAWLESS1987/covenant/main/mobile/install.sh
#   less install.sh && sh install.sh
#
# Knobs (environment, all optional):
#   PC_PEER      a peer's P2P address (API port + 1), e.g. 10.0.0.174:5001. Empty = no
#                peer: the node runs alone from the canonical genesis and converges when
#                a peer appears. Nothing here invents a peer for you.
#   JUDGE_MODEL  qwen3:1.7b (default, 6 GB phones) | qwen3:4b (8 GB) | qwen3:8b (12 GB)
#   NODE_ID      the name the node signs with (default phone)
#   NO_START=1   install only; do not start the node
#
# What it never does: ask for a password or a key, touch anything outside $HOME/covenant
# and the Termux shortcut folder, or open any port but the node's own.

set -u
REPO="https://github.com/LAWLESS1987/covenant"
DEST="$HOME/covenant"
say() { printf '%s\n' "$*"; }

say "covenant on this phone: install/update, then start (Ctrl-C to stop the node later)"

# 1. packages from Termux's own repo (python-cryptography avoids compiling on the phone)
if command -v pkg >/dev/null 2>&1; then
    pkg update -y >/dev/null 2>&1 || true
    pkg install -y python git python-cryptography ollama || {
        say "pkg install failed -- is this Termux from F-Droid? (the Play Store build is broken)"; exit 2; }
else
    say "no 'pkg' here: this script is for Termux on Android"; exit 2
fi

# 2. the repository, cloned or updated
if [ -d "$DEST/.git" ]; then
    git -C "$DEST" pull --ff-only || say "update failed; keeping the copy you have"
else
    git clone "$REPO" "$DEST" || { say "clone failed"; exit 2; }
fi
cd "$DEST" || exit 2

# 3. pure-Python dependencies (waitress optional; xrpl-py deliberately not installed)
pip install --quiet flask requests waitress || say "pip install had trouble; the node may still start"

# 4. a home-screen button (Termux:Widget) and boot entry (Termux:Boot), if those apps exist
mkdir -p "$HOME/.shortcuts" && cp mobile/widget/covenant-phone-start.sh "$HOME/.shortcuts/" \
    && chmod +x "$HOME/.shortcuts/covenant-phone-start.sh" && say "home-screen button installed (Termux:Widget)"
[ -d "$HOME/.termux" ] && mkdir -p "$HOME/.termux/boot" \
    && cp mobile/widget/covenant-phone-start.sh "$HOME/.termux/boot/" 2>/dev/null && true

# 5. tell the truth about what was checked
say ""
say "installed. Not run here: the ten-minute check (sh check.sh) -- run it when you want to see"
say "the constitution hash agree two ways on this phone; the node does not depend on it."
say ""

[ "${NO_START:-0}" = "1" ] && { say "NO_START=1: not starting. Later: cd ~/covenant && sh mobile/covenant_phone.sh"; exit 0; }
exec sh mobile/covenant_phone.sh
