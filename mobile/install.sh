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

LOG="$HOME/covenant-install.log"
: >"$LOG" 2>/dev/null || LOG=/dev/null

# 1. packages from Termux's own repo (python-cryptography avoids compiling on the phone)
#
# CORRECTED 2026-09-10: this line used to read "... python-cryptography ollama".
# d81f808 took Ollama out of covenant_phone.sh and TERMUX_SETUP.md on 2026-09-09 and
# missed the one file a new operator actually pastes. Ollama is out of the ethics
# quorum (ops/quorum_policy.json: local_in_chain false, the default since 2026-09-12), so the pull bought
# a component the gate does not consult -- and `|| exit 2` aborted the whole install
# over it. What judges here is the distilled student, read into the node's own process.
#
# CORRECTED AGAIN, same day, after "repo not working" from the first person to run it:
# `pkg update` ran as `>/dev/null 2>&1 || true`, so apt's actual complaint was DELETED,
# and then the failure below blamed F-Droid -- one guess, printed as if it were a
# diagnosis. A broken Termux mirror (the common case; the mirror set rotates and a
# stale one 404s on dists/stable/Release) produced the identical message as the Play
# Store build, which is a different problem with a different fix. Now apt's own words
# are kept and shown, and both causes are named instead of one being asserted.
if command -v pkg >/dev/null 2>&1; then
    pkg update -y >>"$LOG" 2>&1 || say "pkg update reported trouble; continuing -- full output in $LOG"
    if ! pkg install -y python git python-cryptography >>"$LOG" 2>&1; then
        say "pkg install failed. apt's own last 20 lines:"
        say "---"
        tail -n 20 "$LOG" 2>/dev/null || say "(no log kept)"
        say "---"
        say "The two causes that produce this, in the order they happen:"
        say "  1. a stale Termux mirror. Run:  termux-change-repo"
        say "     pick a different mirror, then run this installer again."
        say "  2. Termux from the Play Store, which is abandoned and cannot install"
        say "     these packages. Uninstall it and take the F-Droid build:"
        say "     https://f-droid.org/packages/com.termux/"
        exit 2
    fi
else
    say "no 'pkg' here: this script is for Termux on Android."
    say "If you are in a terminal that is not Termux, nothing below will work."
    exit 2
fi

# 2. the repository, cloned or updated
# Same correction as above: "clone failed" was a fact with the reason thrown away.
# The repository is public and needs no credentials, so a clone that fails here is
# almost always the phone's network (captive Wi-Fi portal, no DNS) rather than GitHub.
if [ -d "$DEST/.git" ]; then
    git -C "$DEST" pull --ff-only || say "update failed; keeping the copy you have"
else
    if ! git clone "$REPO" "$DEST" 2>>"$LOG"; then
        say "clone failed. git's own last 10 lines:"
        say "---"
        tail -n 10 "$LOG" 2>/dev/null
        say "---"
        say "This repository is PUBLIC and asks for no login. A failure here is"
        say "normally the phone's network: try  ping -c2 github.com  and check you"
        say "are not behind a Wi-Fi sign-in page."
        exit 2
    fi
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
