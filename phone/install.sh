#!/data/data/com.termux/files/usr/bin/bash
# ---------------------------------------------------------------------------
# install.sh -- one-time Termux setup for the daily check.
#
#   bash install.sh
#
# Installs what is needed, copies your files off Downloads, schedules the job
# for 07:55 daily, and makes it survive a reboot.
# ---------------------------------------------------------------------------
set -uo pipefail
HERE="$HOME/covenant"
GREEN=$'\033[32m'; RED=$'\033[31m'; YEL=$'\033[33m'; OFF=$'\033[0m'
ok()   { echo "${GREEN}  ok${OFF}   $*"; }
warn() { echo "${YEL}  warn${OFF} $*"; }
bad()  { echo "${RED}  X${OFF}    $*"; }

echo "======================================================================"
echo " COVENANT -- phone setup"
echo "======================================================================"

# --- 0. is this actually Termux, and the RIGHT Termux? ---------------------
if [ ! -d "/data/data/com.termux" ]; then
    bad "This is not Termux. Run it inside the Termux app."; exit 1
fi
# The Google Play build of Termux was frozen years ago and its package repo is
# broken -- `pkg install` fails or installs binaries that segfault. This is the
# single most common reason a Termux setup mysteriously does not work.
if ! pkg update -y >/dev/null 2>&1; then
    bad "pkg update failed."
    echo "     Almost always this means Termux came from the Google Play Store."
    echo "     Uninstall it and install Termux from F-Droid instead:"
    echo "       https://f-droid.org/en/packages/com.termux/"
    echo "     Install Termux:API and Termux:Boot from F-Droid too -- they must"
    echo "     come from the SAME source or Android rejects them (signature)."
    exit 1
fi
ok "Termux package repo reachable"

# --- 1. packages -----------------------------------------------------------
echo; echo "[1/6] packages"
for p in python cronie termux-api curl; do
    if pkg install -y "$p" >/dev/null 2>&1; then ok "$p"
    else warn "$p failed to install"; fi
done
python -c "import urllib.request, json, statistics" 2>/dev/null \
    && ok "python stdlib complete (daily.py needs nothing else)" \
    || bad "python is broken"

# --- 2. storage ------------------------------------------------------------
echo; echo "[2/6] storage access"
if [ ! -d "$HOME/storage" ]; then
    echo "     Android will now ask for file permission -- tap Allow."
    termux-setup-storage
    sleep 3
fi
[ -d "$HOME/storage/downloads" ] && ok "Downloads reachable" \
    || { bad "no ~/storage/downloads -- rerun: termux-setup-storage"; }

# --- 3. copy the files off Downloads --------------------------------------
echo; echo "[3/6] your files"
mkdir -p "$HERE/state"
COPIED=0
for f in daily.py holdings.txt; do
    SRC="$HOME/storage/downloads/$f"
    if [ -f "$SRC" ]; then
        cp "$SRC" "$HERE/$f"; ok "$f"; COPIED=$((COPIED+1))
    elif [ -f "$HERE/$f" ]; then
        ok "$f (already here)"; COPIED=$((COPIED+1))
    else
        bad "$f NOT FOUND in Downloads"
    fi
done
if [ "$COPIED" -lt 2 ]; then
    echo
    bad "Download daily.py and holdings.txt from the chat first, then rerun."
    exit 1
fi
cp -f covenant-run.sh covenant-doctor.sh "$HERE/" 2>/dev/null
chmod +x "$HERE/covenant-run.sh" "$HERE/covenant-doctor.sh"

# --- 4. prove it works BEFORE scheduling it -------------------------------
echo; echo "[4/6] test run (this hits the network, ~20s)"
if (cd "$HERE" && timeout 120 python daily.py >/dev/null 2>&1); then
    ok "daily.py ran clean"
else
    bad "daily.py failed. Run it by hand to see why:  cd ~/covenant && python daily.py"
    echo "     Not scheduling a job that does not work."
    exit 1
fi

# --- 5. schedule ----------------------------------------------------------
echo; echo "[5/6] schedule (07:55 daily)"
LINE="55 7 * * * $HERE/covenant-run.sh >> $HERE/state/cron.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'covenant-run.sh' ; echo "$LINE" ) | crontab -
crontab -l | grep -q covenant-run && ok "crontab entry installed"
pgrep crond >/dev/null 2>&1 || crond
pgrep crond >/dev/null 2>&1 && ok "crond running" || warn "crond not running -- start with: crond"

# --- 6. survive a reboot --------------------------------------------------
echo; echo "[6/6] reboot persistence"
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/start-covenant" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
crond
BOOT
chmod +x "$HOME/.termux/boot/start-covenant"
ok "boot script written"
warn "Termux:Boot must be INSTALLED from F-Droid and OPENED once,"
echo "       or nothing restarts after a reboot. That is an Android rule,"
echo "       not something a script can do for you."

echo
echo "======================================================================"
echo " DONE"
echo "======================================================================"
echo "  runs      : 07:55 every day"
echo "  check it  : cd ~/covenant && ./covenant-doctor.sh"
echo "  run now   : cd ~/covenant && ./covenant-run.sh"
echo
echo "  ONE MORE STEP, and it is the one that decides whether this survives:"
echo "    Android Settings > Apps > Termux > Battery > ${GREEN}Unrestricted${OFF}"
echo "  On stock Android the battery manager kills background work within a"
echo "  few days. Unrestricted is what prevents that."
echo
echo "  Nothing here places a trade. It reads prices and prints a suggestion."
echo "======================================================================"
