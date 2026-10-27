#!/data/data/com.termux/files/usr/bin/sh
# Termux:Widget / Termux:Boot entry: one tap (or boot) starts the covenant phone node.
# Copy to ~/.shortcuts/ (widget) or ~/.termux/boot/ (boot) and chmod +x.
cd "$HOME/covenant" || exit 1
exec sh mobile/covenant_phone.sh
