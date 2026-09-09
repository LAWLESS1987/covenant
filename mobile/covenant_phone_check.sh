#!/bin/sh
# covenant_phone_check.sh -- is the phone node up, and does it have a judge?
#
# CORRECTED 2026-09-09. This script used to treat a missing Ollama as a failure:
# it printed "the node will fail CLOSED" and exited 1. On a correctly working
# node in the shipped configuration that was simply wrong, and it was wrong in
# the worst direction -- the second operator runs the health check, sees a
# failure line and a non-zero exit, and concludes the node is broken when the
# gate is judging perfectly well.
#
# Ollama was deleted from this project on 2026-09-07 and ops/quorum_policy.json
# sets ollama_in_chain false, so a node started today does not consult it. What
# judges is the distilled student, in-process, no socket. Ollama is now reported
# as an optional extra and never decides the exit code.
#
# Nothing here changes anything.

PHONE_PORT="${PHONE_PORT:-5000}"
ok=0
say() { printf '%s\n' "$*"; }

# --- the judge that actually decides -----------------------------------------
if [ -f "$(dirname "$0")/../fallback_model.json" ]; then
    say "judge: distilled student present (fallback_model.json) -- judges in-process"
else
    say "judge: fallback_model.json MISSING -- the gate has no local judge"; ok=1
fi

# --- optional, and not part of the verdict -----------------------------------
if curl -s -m 3 http://127.0.0.1:11434/api/tags >/tmp/covenant_tags.json 2>/dev/null; then
    say "ollama: up (optional; out of the quorum by policy, so it changes nothing)"
    say "  models: $(tr -d '\n' </tmp/covenant_tags.json | sed 's/[{}"]//g' | tr ',' '\n' | grep '^name:' | sed 's/name://' | tr '\n' ' ')"
else
    say "ollama: absent -- expected, and not a problem. The student judges without it."
fi

# --- the node ----------------------------------------------------------------
if curl -s -m 5 "http://127.0.0.1:$PHONE_PORT/health" >/tmp/covenant_health.json 2>/dev/null; then
    say "node: up on port $PHONE_PORT (it also holds $((PHONE_PORT + 1)) and $((PHONE_PORT + 11)))"
    cut -c1-600 /tmp/covenant_health.json; echo
else
    say "node: NOT answering on 127.0.0.1:$PHONE_PORT"; ok=1
fi

[ "$ok" -eq 0 ] && say "healthy" || say "something is down -- see above"
exit $ok
