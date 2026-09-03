#!/bin/sh
# covenant_phone_check.sh -- is the phone node up, and does it have a judge?
# Asks Ollama for its models, the node for /health, and prints what it sees. Exit 0 only
# when both answer. Nothing here changes anything.

PHONE_PORT="${PHONE_PORT:-5000}"
ok=0
say() { printf '%s\n' "$*"; }

if curl -s -m 3 http://127.0.0.1:11434/api/tags >/tmp/covenant_tags.json 2>/dev/null; then
    say "ollama: up"
    say "  models: $(tr -d '\n' </tmp/covenant_tags.json | sed 's/[{}"]//g' | tr ',' '\n' | grep '^name:' | sed 's/name://' | tr '\n' ' ')"
else
    say "ollama: NOT answering on 127.0.0.1:11434 -- the node will fail CLOSED"; ok=1
fi

if curl -s -m 5 "http://127.0.0.1:$PHONE_PORT/health" >/tmp/covenant_health.json 2>/dev/null; then
    say "node: up on port $PHONE_PORT"
    cut -c1-600 /tmp/covenant_health.json; echo
else
    say "node: NOT answering on 127.0.0.1:$PHONE_PORT"; ok=1
fi

[ "$ok" -eq 0 ] && say "both answering" || say "something is down -- see above"
exit $ok
