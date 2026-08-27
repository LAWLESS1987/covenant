#!/data/data/com.termux/files/usr/bin/bash
# ---------------------------------------------------------------------------
# covenant-run.sh -- the morning check, on the phone.
#
# Runs daily.py, records that it ran, and notifies you. The recording is the
# important part: Android may kill this job at any time, and a job that dies
# quietly looks exactly like a job that ran and found nothing. The run log is
# what tells those two apart.
#
# Nothing here trades. It reads public prices and prints a suggestion.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$HOME/covenant"
STATE="$HERE/state"
LOG="$STATE/runs.log"
OUT="$STATE/last_output.txt"
mkdir -p "$STATE"

now_epoch() { date +%s; }
stamp()     { date '+%Y-%m-%d %H:%M:%S'; }

# Keep the CPU awake for the ~20s this takes. Without it Android can suspend
# us mid-fetch and we half-finish, which is worse than not running at all.
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock
cleanup() { command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock; }
trap cleanup EXIT

cd "$HERE" || { echo "$(stamp) FAIL no $HERE" >> "$LOG"; exit 1; }

START=$(now_epoch)
if python daily.py > "$OUT" 2>&1; then
    STATUS="OK"
else
    STATUS="FAIL"
fi
ELAPSED=$(( $(now_epoch) - START ))

# --- the run log: one line per attempt, success or failure ------------------
echo "$(stamp) $STATUS ${ELAPSED}s" >> "$LOG"
echo "$(now_epoch)" > "$STATE/last_run_epoch"

# --- build a short human line from the output ------------------------------
if [ "$STATUS" = "OK" ]; then
    TOTAL=$(grep -E '^\s+TOTAL' "$OUT" | awk '{print $2}')
    ACTIONS=$(grep -cE '^\s+\* (TRIM|CASH)' "$OUT")
    if [ "${ACTIONS:-0}" -gt 0 ]; then
        WHICH=$(grep -E '^\s+\* (TRIM|CASH)' "$OUT" | sed 's/^ *\* //' | cut -d: -f1 | paste -sd, -)
        MSG="Portfolio \$${TOTAL:-?} - ${ACTIONS} action(s): ${WHICH}"
    else
        MSG="Portfolio \$${TOTAL:-?} - no action, all rules satisfied"
    fi
else
    MSG="Check FAILED to run. Open Termux and read state/last_output.txt"
fi

# --- notify ----------------------------------------------------------------
# termux-notification needs the Termux:API *app* plus `pkg install termux-api`.
# If it is missing we do not fail silently -- we say so in the log, because a
# check you never see is the same as no check.
if command -v termux-notification >/dev/null 2>&1; then
    termux-notification \
        --title "Covenant daily check" \
        --content "$MSG" \
        --priority high \
        --id covenant-daily 2>/dev/null \
      || echo "$(stamp) WARN termux-notification failed" >> "$LOG"
else
    echo "$(stamp) WARN no termux-notification (install Termux:API app + pkg install termux-api)" >> "$LOG"
fi

# --- optional second channel ----------------------------------------------
# If NTFY_TOPIC is set in ~/.covenant_env this also pushes over the internet,
# which leaves a record OUTSIDE the phone. Useful precisely because a dead
# phone job cannot report its own death.
[ -f "$HOME/.covenant_env" ] && . "$HOME/.covenant_env"
if [ -n "${NTFY_TOPIC:-}" ]; then
    curl -fsS -m 15 -H "Title: Covenant daily check" \
         -d "$MSG" "https://ntfy.sh/${NTFY_TOPIC}" >/dev/null 2>&1 \
      || echo "$(stamp) WARN ntfy push failed" >> "$LOG"
fi

echo "$MSG"
