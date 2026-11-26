#!/usr/bin/env bash
# Three deliberate breaks of linux/install_timers.sh; each must turn its check red.
# Usage: bash linux/mutate_install_timers_sh.sh <repo root>
SRC="$1"; TEST="$SRC/linux/test_install_timers_sh.sh"
run_mut() {  # name  sed-expression  expected-FAIL-text
  M="$(mktemp -d /tmp/covtmut.XXXX)"; mkdir -p "$M/linux"
  cp "$SRC/linux/trader_task.sh" "$M/linux/"
  sed "$2" "$SRC/linux/install_timers.sh" > "$M/linux/install_timers.sh"
  if cmp -s "$SRC/linux/install_timers.sh" "$M/linux/install_timers.sh"; then echo "MUTATION DID NOT APPLY: $1"; return; fi
  out="$(bash "$TEST" "$M" 2>&1)"
  if grep -q "FAIL  $3" <<<"$out"; then echo "CAUGHT    $1  -> $(grep -m1 "FAIL  $3" <<<"$out")"; else echo "MISSED    $1"; fi
  grep RESULT <<<"$out"
}
run_mut "plain install enables everything" 's#^            echo "Nothing is enabled.*#            enable_names "$ALL"#' "plain install enabled"
run_mut "ambassador every 3 h from 00:00" 's#02/3:00:00#00/3:00:00#' "ambassador calendar"
run_mut "remove deletes instead of moving aside" 's#mkdir -p "$aside" \&\& mv "$f" "$aside/"#rm -f "$f"#' "retired copies"
