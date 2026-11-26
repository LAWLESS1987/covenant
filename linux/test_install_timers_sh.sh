#!/usr/bin/env bash
# Exercises linux/install_timers.sh and linux/trader_task.sh in a throwaway copy.
# systemctl is replaced by a logger, so nothing is installed, enabled or run on
# this machine. systemd-analyze (when present) checks the generated units and
# the calendar expressions. Usage: bash linux/test_install_timers_sh.sh <repo root>
set -u
SRC="$1"
T="$(mktemp -d /tmp/covtimers.XXXX)"
pass=0; fail=0
ok()  { echo "PASS  $1"; pass=$((pass+1)); }
bad() { echo "FAIL  $1"; fail=$((fail+1)); }

mkdir -p "$T/linux"
cp "$SRC/linux/install_timers.sh" "$SRC/linux/trader_task.sh" "$T/linux/"
chmod -x "$T/linux/"*.sh   # as a clone of a Windows commit has them: no executable bit
for f in covenant_watchdog_guard.py covenant_refine_check.py covenant_free_will.py covenant_nightly.py; do echo "pass" > "$T/$f"; done
printf 'import sys\nprint("fake trader pass", " ".join(sys.argv[1:]))\n' > "$T/covenant_trader.py"
FAKE="$T/fake_systemctl"; CALLS="$T/systemctl_calls.log"
printf '#!/usr/bin/env bash\necho "$*" >> %q\n' "$CALLS" > "$FAKE"; chmod +x "$FAKE"
U="$T/units"
I="$T/linux/install_timers.sh"
LINGER="$T/linger_answer"; echo no > "$LINGER"
FAKEL="$T/fake_loginctl"
printf '#!/usr/bin/env bash\ncat %q\n' "$LINGER" > "$FAKEL"; chmod +x "$FAKEL"
export COVENANT_UNIT_DIR="$U" COVENANT_SYSTEMCTL="$FAKE" COVENANT_ADOPT_HOME="$T/adopt_home" COVENANT_LOGINCTL="$FAKEL"

bash -n "$I" && bash -n "$T/linux/trader_task.sh" && ok "syntax" || bad "syntax"

# 1. install writes 5+5 units and enables NOTHING (A14)  <->  install --enable all enables 5
out="$(bash "$I" install 2>&1)"
[ "$(ls "$U"/covenant-*.service 2>/dev/null | wc -l)" -eq 8 ] && [ "$(ls "$U"/covenant-*.timer 2>/dev/null | wc -l)" -eq 8 ] && ok "install wrote 8 services + 8 timers" || bad "install file count"
grep -q "enable" "$CALLS" && bad "plain install enabled something: $(grep enable "$CALLS")" || ok "plain install enabled nothing"
grep -q -- "--user daemon-reload" "$CALLS" && ok "install reloaded the user manager" || bad "no daemon-reload"
: > "$CALLS"
bash "$I" install --enable all >/dev/null 2>&1
[ "$(grep -c -- '--user enable --now covenant-' "$CALLS")" -eq 8 ] && ok "install --enable all enabled 8" || bad "enable all: $(grep -c enable "$CALLS")"

# 1b. lingering is said aloud (the quorum's Q5): OFF warns on install, enable and status; ON does not
echo no > "$LINGER"
for cmd in "install" "enable guard" "status"; do
    err="$(bash "$I" $cmd 2>&1 >/dev/null)"
    grep -q "WARNING: lingering is OFF" <<<"$err" && ok "lingering off -> warning on '$cmd'" || bad "no linger warning on '$cmd'"
done
echo yes > "$LINGER"
out="$(bash "$I" status 2>&1)"
grep -q "lingering: on" <<<"$out" && ! grep -q "WARNING" <<<"$out" && ok "lingering on -> said, no warning" || bad "linger on: $out"
echo no > "$LINGER"
: > "$CALLS"

# 2. names are validated, both ways
: > "$CALLS"
bash "$I" enable guard,distill >/dev/null 2>&1 && [ "$(grep -c 'enable --now' "$CALLS")" -eq 2 ] && grep -q "covenant-distill.timer" "$CALLS" && ok "enable two by name" || bad "enable by name"
bash "$I" enable guard,bogus >/dev/null 2>&1; rc=$?
[ $rc -eq 2 ] && ok "unknown name refused (rc=2)" || bad "unknown name rc=$rc"
[ "$(grep -c 'enable --now' "$CALLS")" -eq 2 ] && ok "a refused list enabled nothing more" || bad "refused list still enabled some"

# 3. the units say what the Windows tasks did
grep -q '^OnCalendar=\*-\*-\* 02/3:00:00$' "$U/covenant-ambassador.timer" && ok "ambassador calendar" || bad "ambassador calendar"
grep -q -- "covenant_free_will.py --round --send --log $T/logs/ambassador.log$" "$U/covenant-ambassador.service" && ok "ambassador command" || bad "ambassador command"
grep -q '^TimeoutStartSec=2h 50min$' "$U/covenant-ambassador.service" && ok "ambassador limit" || bad "ambassador limit"
grep -q '^OnCalendar=\*-\*-\* 02:30:00$' "$U/covenant-distill.timer" && grep -q -- "--study 24 --cycle 8 --audit 48$" "$U/covenant-distill.service" && ok "distill calendar + args" || bad "distill"
grep -q "^ExecStart=$(command -v bash) $T/linux/trader_task.sh$" "$U/covenant-trader.service" && grep -q '^OnCalendar=\*-\*-\* 09:00:00$' "$U/covenant-trader.timer" && ok "trader via trader_task.sh at 09:00" || bad "trader"
grep -q "^WorkingDirectory=$T$" "$U/covenant-guard.service" && grep -q '^Type=oneshot$' "$U/covenant-guard.service" && ok "guard runs oneshot in the repo" || bad "guard service"
grep -q '^Environment=COVENANT_GH_READ=1$' "$U/covenant-hf-mirror.service" && grep -q -- "-B $T/tools/hf_mirror.py$" "$U/covenant-hf-mirror.service" && ok "hf-mirror: GH read env + hf_mirror.py" || bad "hf-mirror service"
grep -q '^Environment=' "$U/covenant-guard.service" && [ "$(grep -c '^Environment=' "$U/covenant-guard.service")" -eq 1 ] && ok "a timer without its own setting gets only PYTHONUNBUFFERED" || bad "guard env lines"
grep -q -- "-B $T/tools/site_autodeploy.py$" "$U/covenant-site-autodeploy.service" && ok "site-autodeploy command" || bad "site-autodeploy service"
grep -q "^ExecStart=$(command -v bash) $T/adopt_home/linux/run_adopt.sh$" "$U/covenant-adopt.service" && grep -q "^Environment=COVENANT_ADOPT_REPO=$T$" "$U/covenant-adopt.service" && ok "adopt runs the host wrapper, pointed at this checkout" || bad "adopt service"
out="$(bash "$I" 2>&1)"; rc=$?
[ $rc -eq 2 ] && grep -q "hf-mirror  site-autodeploy  adopt" <<<"$out" && ! grep -q '^#!/usr/bin/env' <<<"$out" && ok "no argument prints the whole header, exit 2" || bad "usage text rc=$rc"

# 4. systemd's own checks, when systemd-analyze is here
if command -v systemd-analyze >/dev/null 2>&1; then
    v="$(systemd-analyze --user verify "$U"/covenant-*.timer "$U"/covenant-*.service 2>&1 | grep -v -i 'not found\|unit-file path' )"
    [ -z "$v" ] && ok "systemd-analyze verify: clean" || bad "systemd-analyze verify: $v"
    # The calendars are read FROM THE GENERATED TIMERS, so a wrong schedule in the installer is caught here.
    cal_of() { sed -n 's/^OnCalendar=//p' "$U/covenant-$1.timer"; }
    nxt() { systemd-analyze calendar --iterations="$2" --base-time="2026-11-26 00:00:00" "$(cal_of "$1")" 2>/dev/null | grep -E 'Next elapse|Iter' | grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}' | tr '\n' ' '; }
    [ "$(nxt ambassador 8)" = "02:00:00 05:00:00 08:00:00 11:00:00 14:00:00 17:00:00 20:00:00 23:00:00 " ] && ok "ambassador fires at 2,5,8,11,14,17,20,23 (Windows: 11:00 + 3 h)" || bad "ambassador hours: $(nxt ambassador 8)"
    [ "$(nxt refine-check 4)" = "00:03:00 00:18:00 00:33:00 00:48:00 " ] && ok "refine-check at :03 :18 :33 :48" || bad "refine-check: $(nxt refine-check 4)"
    # "Next elapse" is strictly after the base time, so from 00:00:00 the first is 00:02:00.
    [ "$(nxt guard 3)" = "00:02:00 00:04:00 00:06:00 " ] && ok "guard every 2 min (even minutes)" || bad "guard: $(nxt guard 3)"
    [ "$(nxt hf-mirror 4)" = "01:05:00 03:05:00 05:05:00 07:05:00 " ] && ok "hf-mirror at :05 on odd hours (Windows: 11:05 + 2 h)" || bad "hf-mirror: $(nxt hf-mirror 4)"
    [ "$(nxt site-autodeploy 4)" = "00:07:00 00:22:00 00:37:00 00:52:00 " ] && ok "site-autodeploy at :07 :22 :37 :52 (Windows: 22:52 + 15 min)" || bad "site-autodeploy: $(nxt site-autodeploy 4)"
    [ "$(nxt adopt 2)" = "05:00:00 05:00:00 " ] && ok "adopt daily at 05:00" || bad "adopt: $(nxt adopt 2)"
    [ "$(nxt distill 1)" = "02:30:00 " ] && [ "$(nxt trader 1)" = "09:00:00 " ] && ok "distill 02:30, trader 09:00 (from the timers)" || bad "distill/trader: $(nxt distill 1) / $(nxt trader 1)"
else
    echo "SKIP  systemd-analyze not installed: units and calendars not checked by systemd"
fi

# 5. trader_task.sh: dated header, then the trader's output, appended
bash "$T/linux/trader_task.sh"; bash "$T/linux/trader_task.sh"
[ "$(grep -c '^==== ' "$T/trader_log.txt")" -eq 2 ] && [ "$(grep -c 'fake trader pass --once' "$T/trader_log.txt")" -eq 2 ] && ok "trader_task appends header + one pass per run" || bad "trader_task log: $(cat "$T/trader_log.txt")"

# 6. remove disables all and MOVES the files aside (rule 10), never deletes
: > "$CALLS"
out="$(bash "$I" remove 2>&1)"
[ "$(grep -c -- '--user disable --now covenant-' "$CALLS")" -eq 8 ] && ok "remove disabled all 8" || bad "remove disable count"
[ -z "$(ls "$U"/covenant-* 2>/dev/null)" ] && ok "unit folder emptied of covenant units" || bad "units left behind"
[ "$(find "$T/logs/retired-units" -name 'covenant-*' | wc -l)" -eq 16 ] && ok "16 unit files kept in logs/retired-units" || bad "retired copies: $(find "$T/logs/retired-units" -name 'covenant-*' 2>/dev/null | wc -l)"

# 7. a checkout path with a space is refused before anything is written
S="$(mktemp -d "/tmp/cov space.XXXX")"; mkdir -p "$S/linux"; cp "$I" "$S/linux/"
COVENANT_UNIT_DIR="$S/units" bash "$S/linux/install_timers.sh" install >/dev/null 2>&1; rc=$?
[ $rc -eq 2 ] && [ ! -e "$S/units" ] && ok "path with a space refused, nothing written" || bad "space path rc=$rc"

echo "RESULT: $pass passed, $fail failed  (copy at $T)"
