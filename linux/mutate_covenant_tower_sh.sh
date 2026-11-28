#!/usr/bin/env bash
# Breaks linux/covenant_tower.sh and linux/run_node_bound.py on purpose (A500); test_covenant_tower_sh.sh must FAIL
# on every break. A break it passes is a guard that was never observed working (rule 8).
#   bash linux/mutate_covenant_tower_sh.sh REPO_ROOT     -> every line CAUGHT
set -u
SRC="$1"; caught=0; missed=0
mutate() {   # mutate NAME FILE SED-EXPRESSION
    local M; M="$(mktemp -d /tmp/covtmut.XXXX)"; mkdir -p "$M/linux"
    cp "$SRC/linux/covenant_tower.sh" "$SRC/linux/run_node_bound.py" "$SRC/linux/test_covenant_tower_sh.sh" "$M/linux/"
    sed -i "$3" "$M/linux/$2"
    if cmp -s "$SRC/linux/$2" "$M/linux/$2"; then echo "BROKEN MUTANT  $1 (sed changed nothing)"; missed=$((missed+1)); return; fi
    if timeout 300 bash "$M/linux/test_covenant_tower_sh.sh" "$M" >/dev/null 2>&1; then echo "MISSED  $1"; missed=$((missed+1))
    else echo "CAUGHT  $1"; caught=$((caught+1)); fi
    pkill -f "$M" 2>/dev/null; pkill -f "run_node_bound.py --port 539" 2>/dev/null
}
mutate "production ids A-D accepted"          covenant_tower.sh  's/A|B|C|D) echo/Q9) echo/'
mutate "production key on the machine ignored" covenant_tower.sh 's/\[ -e "\$f" \] \&\& abort/[ -e "$f" ] \&\& true/'
mutate "0.0.0.0 accepted by the launcher"      covenant_tower.sh  "s/''|0.0.0.0|::|'\[::\]')/'')/"
mutate "every interface accepted by the wrapper" run_node_bound.py 's/if bind in EVERY_INTERFACE:/if False:/'
mutate "copied founder key accepted by the wrapper" run_node_bound.py 's/== mine:/== b"never":/'
mutate "key written without umask 077"         covenant_tower.sh  's/umask 077; //'
mutate "a second copy started on re-run"       covenant_tower.sh  's/if \[ -n "\$(pids_here "\$(PATTERN)")" \]; then/if false; then/'
echo "RESULT: $caught caught, $missed missed"
[ "$missed" -eq 0 ]
