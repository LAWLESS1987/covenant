#!/usr/bin/env bash
# linux/trader_task.sh -- the Linux port of TRADER_TASK.bat (A492).
# Same work: append a dated header to trader_log.txt, then run one trader pass
# into it. The systemd timer covenant-trader.timer runs this once a day, but
# only if the operator enabled it (linux/install_timers.sh).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$HERE" || exit 1
if [ -x ".venv/bin/python" ]; then PY="$HERE/.venv/bin/python"; else PY="$(command -v python3)"; fi
{ echo; echo "==== $(date '+%a %m/%d/%Y %H:%M:%S') ===="; } >> trader_log.txt
"$PY" covenant_trader.py --once >> trader_log.txt 2>&1
