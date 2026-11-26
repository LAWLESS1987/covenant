#!/usr/bin/env bash
# ============================================================================
#  linux/install_timers.sh -- the eight Windows scheduled tasks Covenant runs,
#  as systemd user timers (A492). Installing writes the unit files; it ENABLES
#  NOTHING unless you name the timers to enable (A14: nothing starts by itself).
#
#  USAGE
#    linux/install_timers.sh install                 write units, enable none
#    linux/install_timers.sh install --enable all    write units, enable all eight
#    linux/install_timers.sh enable guard,distill    enable named timers
#    linux/install_timers.sh disable trader          stop and disable named timers
#    linux/install_timers.sh status                  what is installed and when it runs next
#    linux/install_timers.sh remove                  disable all, move the unit files aside
#
#  NAMES   guard  refine-check  ambassador  distill  trader
#          hf-mirror  site-autodeploy  adopt
#
#  The schedules are the Windows tasks' own, read from Task Scheduler on
#  2026-11-25/26 (local time; set the tower's time zone to match):
#    guard           every 2 min            limit 10 min     (CovenantGuard)
#    refine-check    every 15 min, at :03   limit 10 min     (CovenantRefineCheck)
#    ambassador      every 3 h, from 02:00  limit 2 h 50 min (CovenantAmbassador: 11:00 + 3 h steps)
#    distill         daily 02:30            limit 6 h        (CovenantDistill)
#    trader          daily 09:00            limit 72 h       (CovenantTrader)
#    hf-mirror       every 2 h, at :05 on odd hours  72 h    (CovenantHFMirror: 11:05 + 2 h steps)
#    site-autodeploy every 15 min, at :07   limit 72 h       (CovenantSiteAutoDeploy: 22:52 + 15 min steps)
#    adopt           daily 05:00            limit 72 h       (covenant-adopt; runs ~/covenant-adopt/linux/run_adopt.sh)
#  72 h is Task Scheduler's default where the task set no limit. All eight ran
#  with "do not start a new instance": a systemd timer never starts a service
#  that is still running, which is the same rule.
#
#  ambassador SENDS messages, trader TRADES, site-autodeploy PUBLISHES the
#  website, hf-mirror PUSHES to Hugging Face, and adopt MERGES origin/main into
#  this checkout and restarts the nodes. Enable them knowingly. hf-mirror and
#  site-autodeploy run on the operator's laptop today: enable them on ONE
#  machine, or two machines will deploy and push the same thing.
#
#  User timers run only while you are logged in, unless lingering is on:
#    loginctl enable-linger "$USER"
#  This script does not turn that on for you.
#
#  For the tests: COVENANT_UNIT_DIR overrides the unit folder, and
#  COVENANT_SYSTEMCTL replaces the systemctl command, COVENANT_LOGINCTL the loginctl one.
# ============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
UNIT_DIR="${COVENANT_UNIT_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}"
SYSTEMCTL="${COVENANT_SYSTEMCTL:-systemctl}"
if [ -x "$HERE/.venv/bin/python" ]; then PY="$HERE/.venv/bin/python"; else PY="$(command -v python3)"; fi
case "$HERE$PY" in
    *[[:space:]]*) echo "the repository path or python path contains a space; systemd's ExecStart would split it. Move the checkout (e.g. ~/covenant)." >&2; exit 2 ;;
esac

ALL="guard refine-check ambassador distill trader hf-mirror site-autodeploy adopt"
BASH_BIN="$(command -v bash)"
# covenant-adopt is this host's config, kept outside the repository by design (its README); the timer runs its
# Linux wrapper from there.
ADOPT_HOME="${COVENANT_ADOPT_HOME:-$HOME/covenant-adopt}"

# name | OnCalendar | time limit | windows task | Environment= (or empty) | command
spec() {
    case "$1" in
        guard)        echo "*-*-* *:00/2:00|10min|CovenantGuard||$PY $HERE/covenant_watchdog_guard.py" ;;
        refine-check) echo "*-*-* *:03/15:00|10min|CovenantRefineCheck||$PY $HERE/covenant_refine_check.py" ;;
        ambassador)   echo "*-*-* 02/3:00:00|2h 50min|CovenantAmbassador||$PY $HERE/covenant_free_will.py --round --send --log $HERE/logs/ambassador.log" ;;
        distill)      echo "*-*-* 02:30:00|6h|CovenantDistill||$PY $HERE/covenant_nightly.py --study 24 --cycle 8 --audit 48" ;;
        # through bash: a file committed from Windows has no executable bit, and ExecStart would refuse it
        trader)       echo "*-*-* 09:00:00|72h|CovenantTrader||$BASH_BIN $HERE/linux/trader_task.sh" ;;
        # site\hf_mirror.vbs: COVENANT_GH_READ=1 lets it clone through git's stored credential
        hf-mirror)    echo "*-*-* 01/2:05:00|72h|CovenantHFMirror|COVENANT_GH_READ=1|$PY -B $HERE/tools/hf_mirror.py" ;;
        site-autodeploy) echo "*-*-* *:07/15:00|72h|CovenantSiteAutoDeploy||$PY -B $HERE/tools/site_autodeploy.py" ;;
        adopt)        echo "*-*-* 05:00:00|72h|covenant-adopt|COVENANT_ADOPT_REPO=$HERE|$BASH_BIN $ADOPT_HOME/linux/run_adopt.sh" ;;
        *)            return 1 ;;
    esac
}

names_from() {   # names_from "a,b" | "all" -> validated, space separated
    local list="$1" n out=""
    [ "$list" = "all" ] && { echo "$ALL"; return 0; }
    for n in ${list//,/ }; do
        spec "$n" >/dev/null || { echo "unknown timer: $n (names: $ALL)" >&2; return 1; }
        out="$out $n"
    done
    [ -n "$out" ] || { echo "no timer named (names: $ALL)" >&2; return 1; }
    echo $out
}

write_units() {
    local n s cal limit task envv cmd extra
    mkdir -p "$UNIT_DIR" "$HERE/logs"
    for n in $ALL; do
        IFS='|' read -r cal limit task envv cmd <<< "$(spec "$n")"
        extra=""; [ -n "$envv" ] && extra="Environment=$envv"
        cat > "$UNIT_DIR/covenant-$n.service" <<EOF
# Written by linux/install_timers.sh (A492). Port of the Windows task $task.
[Unit]
Description=Covenant $n (port of Windows task $task)

[Service]
Type=oneshot
WorkingDirectory=$HERE
Environment=PYTHONUNBUFFERED=1
$extra
ExecStart=$cmd
TimeoutStartSec=$limit
EOF
        cat > "$UNIT_DIR/covenant-$n.timer" <<EOF
# Written by linux/install_timers.sh (A492). Port of the Windows task $task.
[Unit]
Description=Covenant $n schedule (port of Windows task $task)

[Timer]
OnCalendar=$cal
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF
    done
    echo "wrote $(echo $ALL | wc -w) services and timers to $UNIT_DIR (none enabled by this step)"
}

enable_names() {
    local n
    for n in $1; do "$SYSTEMCTL" --user enable --now "covenant-$n.timer" && echo "enabled covenant-$n.timer"; done
    linger_check
}

# The quorum's Q5 (2026-11-26, A492): a user timer stops when its user logs out and does not start after a reboot
# unless lingering is on, and nothing said so -- on a headless tower every timer would be silently dead. This says
# so, loudly, wherever timers are installed, enabled or listed. It does not turn lingering on.
LOGINCTL="${COVENANT_LOGINCTL:-loginctl}"
linger_check() {
    local v
    v="$("$LOGINCTL" show-user "${USER:-$(id -un)}" -p Linger --value 2>/dev/null)"
    if [ "$v" = "yes" ]; then
        echo "lingering: on (timers run with nobody logged in, and after a reboot)"
    else
        echo "WARNING: lingering is OFF for ${USER:-$(id -un)} (loginctl said: ${v:-nothing})." >&2
        echo "WARNING: these timers stop at logout and do NOT start after a reboot. To fix: loginctl enable-linger \"\$USER\"" >&2
    fi
}

case "${1:-}" in
    install)
        write_units
        "$SYSTEMCTL" --user daemon-reload
        if [ "${2:-}" = "--enable" ]; then
            names="$(names_from "${3:-}")" || exit 2
            enable_names "$names"
        else
            echo "Nothing is enabled. To enable:  linux/install_timers.sh enable guard,refine-check   (or: all)"
            linger_check
        fi
        ;;
    enable)
        names="$(names_from "${2:-}")" || exit 2
        enable_names "$names"
        ;;
    disable)
        names="$(names_from "${2:-}")" || exit 2
        for n in $names; do "$SYSTEMCTL" --user disable --now "covenant-$n.timer" && echo "disabled covenant-$n.timer"; done
        ;;
    status)
        "$SYSTEMCTL" --user list-timers --all 'covenant-*'
        linger_check
        ;;
    remove)
        for n in $ALL; do "$SYSTEMCTL" --user disable --now "covenant-$n.timer" >/dev/null 2>&1; done
        aside="$HERE/logs/retired-units/$(date '+%Y%m%d-%H%M%S')"
        moved=0
        for f in "$UNIT_DIR"/covenant-*.service "$UNIT_DIR"/covenant-*.timer; do
            [ -e "$f" ] || continue
            mkdir -p "$aside" && mv "$f" "$aside/" && moved=$((moved+1))
        done
        "$SYSTEMCTL" --user daemon-reload
        if [ "$moved" -gt 0 ]; then echo "disabled all; moved $moved unit files to $aside"; else echo "nothing installed"; fi
        ;;
    *)
        awk 'NR > 2 && /^# ====/ { exit } NR > 2' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
        exit 2
        ;;
esac
