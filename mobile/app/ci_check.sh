#!/bin/sh
# ci_check.sh -- the CI proof that the APK actually runs the node: install it
# on the emulator, start the service, forward the API port, wait for /health,
# assert the canonical genesis and the judge shape, prove it still answers
# after forced idle, prove Stop stops it and a second Start works.
#   usage: sh mobile/app/ci_check.sh <apk>      (android.yml's verify job)
# `adb root` first (2026-09-12): NodeService is not exported -- nothing but this
# app may start it -- and the adb shell user is refused with "Requires permission
# not exported from uid ...": the first run died on that line. Root may start
# it, and the emulator's google_apis image allows root. So this proves
# service + Python + node, not the user's tap path. Only a phone proves the button.
# Evidence is written HERE, on every exit (logcat.txt, app_files.txt): the
# action kills the emulator at the end of its own step, so a later step's
# `adb logcat` waits for a device that is gone.
set -eu
APK="$1"; PKG=org.covenant.node; PORT=5000
evidence() {
  adb logcat -d > logcat.txt 2>/dev/null || true
  adb shell "cat /data/data/$PKG/files/last_exit.txt 2>/dev/null; echo; echo '--- node.log ---'; tail -n 120 /data/data/$PKG/files/node.log 2>/dev/null" > app_files.txt 2>/dev/null || true
}
dump() {
  echo '--- logcat (python, runtime, covenant) ---'
  adb logcat -d -s python.stdout python.stderr AndroidRuntime covenant 2>/dev/null | tail -200
  echo '--- app files ---'; tail -n 80 app_files.txt 2>/dev/null || true
}
on_exit() { rc=$?; evidence; if [ "$rc" -ne 0 ]; then echo "ci_check FAILED (exit $rc)"; dump; fi; }
trap on_exit EXIT
wait_health() { i=0; while [ $i -lt 60 ]; do curl -s -m 5 "http://127.0.0.1:$PORT/health" -o "$1" && return 0; i=$((i+1)); sleep 3; done; return 1; }
adb root; sleep 3; adb wait-for-device; adb shell getprop sys.boot_completed
adb install -r "$APK"
adb shell am start -n $PKG/.MainActivity                    # the Activity must not crash on launch
adb shell am start-foreground-service -n $PKG/.NodeService  # no settings.json -> port 5000, node_id phone, no peer
adb forward tcp:$PORT tcp:$PORT
wait_health health.json
python3 - <<'PYEOF'
import json
h = json.load(open('health.json'))
print(json.dumps({k: h.get(k) for k in ('node_id','chain_height','peers','own_genesis','genesis','judge','wsgi','version','source_sha256','warnings')}, indent=1))
assert h['own_genesis'] is False, 'node minted its own genesis'
assert h['genesis'] == '00009b31c6c654d79bbeae0bcc9c82a7af224c87b19c92973f0011ade3e032f3', h['genesis']
assert h['node_id'] == 'phone' and h['peers'] == 0, (h['node_id'], h['peers'])
assert str(h['judge']).startswith('quorum(') and 'semantic' in str(h['judge']), h['judge']
PYEOF
echo "repo core sha256: $(sha256sum covenant_unified_v8.py)"
adb shell dumpsys activity services $PKG | grep -q 'isForeground=true'
adb shell input keyevent KEYCODE_SLEEP; adb shell dumpsys deviceidle force-idle || true; sleep 30
curl -sf -m 5 "http://127.0.0.1:$PORT/health" -o health2.json       # still answering, screen off, idle forced
adb shell am stopservice -n $PKG/.NodeService; sleep 5
if curl -s -m 3 "http://127.0.0.1:$PORT/health" >/dev/null; then echo 'still answering after Stop'; exit 1; fi
adb shell am start-foreground-service -n $PKG/.NodeService; wait_health health3.json   # a second start, fresh :node process
if adb logcat -d AndroidRuntime:E '*:S' | grep -q 'FATAL EXCEPTION'; then echo 'FATAL in logcat'; exit 1; fi
echo 'emulator check passed'
