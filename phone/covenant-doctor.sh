#!/data/data/com.termux/files/usr/bin/bash
# ---------------------------------------------------------------------------
# covenant-doctor.sh -- did the scheduled job actually keep running?
#
# This is the whole reason the phone version is trustworthy. Android's battery
# manager kills background work without telling anyone. A missed morning looks
# identical to a quiet morning. This reads the run log and says which it was.
#
#   ./covenant-doctor.sh
# ---------------------------------------------------------------------------
set -uo pipefail
STATE="$HOME/covenant/state"
LOG="$STATE/runs.log"

echo "======================================================================"
echo " COVENANT PHONE JOB -- HEALTH"
echo "======================================================================"

if [ ! -f "$LOG" ]; then
    echo "  No run log at all. The job has NEVER run."
    echo "  -> run ./covenant-run.sh by hand once to prove it works,"
    echo "     then check that crond is alive:  pgrep crond || crond"
    exit 1
fi

LAST_EPOCH=$(cat "$STATE/last_run_epoch" 2>/dev/null || echo 0)
NOW=$(date +%s)
AGE_H=$(( (NOW - LAST_EPOCH) / 3600 ))

echo "  last run    : $(tail -1 "$LOG")"
echo "  hours ago   : ${AGE_H}"
echo "  total runs  : $(wc -l < "$LOG")"
echo "  failures    : $(grep -c ' FAIL ' "$LOG" || true)"
echo "  warnings    : $(grep -c ' WARN ' "$LOG" || true)"
echo

# --- the actual question: are there gaps? ----------------------------------
echo "  MISSED DAYS (a gap means Android killed the job):"
python - "$LOG" <<'PY'
import sys, datetime
days=set()
for line in open(sys.argv[1]):
    p=line.split()
    if len(p)>=3 and p[2] in ("OK","FAIL"):
        days.add(p[0])
if not days:
    print("    no completed runs recorded yet")
    raise SystemExit
d=sorted(datetime.date.fromisoformat(x) for x in days)
first,last=d[0],d[-1]
have=set(d)
missing=[]
cur=first
while cur<=last:
    if cur not in have: missing.append(cur.isoformat())
    cur+=datetime.timedelta(days=1)
span=(last-first).days+1
print(f"    window {first} .. {last}  ({span} days, {len(have)} ran, {len(missing)} missed)")
if missing:
    print("    missed:", ", ".join(missing))
    print(f"    -> {len(missing)}/{span} days lost. That is the failure mode:")
    print("       silence that looks like 'nothing to report'.")
else:
    print("    none. Every day in the window has a run.")
PY

echo
if [ "$AGE_H" -gt 30 ]; then
    echo "  VERDICT: STALE. Nothing has run in ${AGE_H}h."
    echo "    1. is cron alive?          pgrep crond || crond"
    echo "    2. is Termux battery-exempt?  Settings > Apps > Termux >"
    echo "       Battery > Unrestricted   (this is the usual culprit)"
    echo "    3. did the phone reboot?   Termux:Boot app must be installed"
    echo "       AND opened once, or nothing restarts after a reboot."
else
    echo "  VERDICT: alive. Last run ${AGE_H}h ago."
fi
echo "======================================================================"
