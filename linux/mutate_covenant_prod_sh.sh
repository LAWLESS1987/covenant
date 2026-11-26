#!/usr/bin/env bash
# Three deliberate breaks of covenant_prod.sh; each must turn the named check red.
SRC="$1"; TEST="$2"
run_mut() {  # name sed-expression expected-FAIL-text
  M="$(mktemp -d /tmp/covmut.XXXX)"; mkdir -p "$M/linux"
  sed "$2" "$SRC/linux/covenant_prod.sh" > "$M/linux/covenant_prod.sh"
  if cmp -s "$SRC/linux/covenant_prod.sh" "$M/linux/covenant_prod.sh"; then echo "MUTATION DID NOT APPLY: $1"; return; fi
  out="$(bash "$TEST" "$M" 2>&1)"
  pkill -f "/tmp/covprod" 2>/dev/null; for p in $(pgrep -f 'run_node.py --port|covenant_watchdog.py --interval'); do case "$(readlink /proc/$p/cwd)" in /tmp/cov*) kill -9 $p;; esac; done
  if grep -q "FAIL  $3" <<<"$out"; then echo "CAUGHT    $1  -> $(grep -m1 "FAIL  $3" <<<"$out")"; else echo "MISSED    $1"; fi
  grep RESULT <<<"$out"
}
run_mut "no working-directory check in stop" 's#\[ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$HERE" \] && ##' "other checkout"
run_mut "nodes stopped before watchdog" '/end_procs "watchdog" "covenant_watchdog.py --interval"/d' "watchdog order"
run_mut "wrong peers for B" 's#127.0.0.1:5001,127.0.0.1:5061#127.0.0.1:5001#' "peers B"
