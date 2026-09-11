#!/usr/bin/env python3
"""
A90 -- the chat's system prompt left this PC on every turn, carrying the
money posture, and the banner said it did not.

THE HAZARD, measured 2026-09-11. covenant_chat.py builds its system prompt from
system_prompt(state), where state is live_state(): the output of
money_posture.py, trader_freshness.py, launch_check.py and the last SELF_EVAL
block. It also embeds memory_text() -- ops/chat/MEMORY.md, the lines tagged
[Lawrence]. Ollama was deleted from this machine on 2026-09-07, so chat_tools
raises on EVERY turn, _ollama_dead matches the connection error, and the turn
goes to chat_github, which base64s the window into a workflow_dispatch input on
LAWLESS1987/covenant -- a PUBLIC repo (anonymous GET 200, private=false, 310
dispatch runs listable with no token). The opening banner meanwhile printed
"Conversation, memory and state stay on this PC" from a constant.

WHY THESE CHECKS ARE BEHAVIOURAL. A87 caught a guard that read one_pass's
SOURCE and so could not tell a live call from a dead one. The same trap is open
here twice over: a suite could grep covenant_chat.py for the word "redact" and
pass while the call site was commented out, and it could grep for the banner
sentence and pass while main() printed something else entirely. So:

  * E4 monkeypatches covenant_github_judge.ask and reads what chat_github
    ACTUALLY hands it. Nothing is grepped.
  * E5 then neuters _offsite_system to the identity function and asserts the
    secret DOES arrive. An instrument that cannot see the leak cannot prove its
    absence, so E4 without E5 proves nothing.
  * E6/E7 RUN _banner_lines with the local-model probe stubbed both ways.

Run: python test_a90_offsite_redaction.py
"""
import sys

import covenant_chat as cc

MARKER = "XYZZY-POSTURE-988-SECRET"
PASS = "PASS"
FAIL = "FAIL"

results = []


def check(ok, name, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % (PASS if ok else FAIL, name, ("  " + detail) if detail else ""))


def a_system_prompt():
    """A real system prompt, with a marker standing in for the live state."""
    return cc.system_prompt("LIVE STATE (measured now)" + chr(10) + MARKER + " armed TRUE")


class _Captured(Exception):
    pass


def capture_offsite_payload(messages):
    """Run chat_github for real, with the network replaced by a recorder.

    Returns the exact text chat_github handed the dispatcher. Nothing is
    grepped out of the source: this is what would have gone on the wire.
    """
    import covenant_github_judge as gh
    seen = {}
    real_ask = gh.ask

    def fake_ask(prompt, system="", model=None, json_only=False, timeout=900, messages=None):
        seen["messages"] = messages
        seen["prompt"] = prompt
        seen["system"] = system
        return {"content": "(recorded, not sent)", "seconds": 0}

    gh.ask = fake_ask
    try:
        cc.chat_github(messages, "test-model")
    finally:
        gh.ask = real_ask
    return seen


print("== the redactor itself ==")
sp = a_system_prompt()
red = cc._offsite_system(sp)

check(MARKER in sp, "E0 the fixture really does carry the live state",
      "%d chars before redaction" % len(sp))
check(MARKER not in red, "E1 the LIVE STATE block does not survive redaction",
      "%d chars after" % len(red))

# E2 supplies its own MEMORY rather than reading ops/chat/MEMORY.md. The sweep
# runs every suite in a STAGED copy that does not carry the operator's private
# files (A84b/A85c: a check that asks the staged tree a question it cannot
# answer fails there and passes here). Controlling the input also makes this a
# stronger check than reading whatever happens to be in the file today.
MEM_MARKER = "PLUGH-MEMORY-LINE-the-operator-said-something-private-here"
_mem = cc.memory_text
try:
    cc.memory_text = lambda limit=7000: "- [Lawrence] " + MEM_MARKER
    with_mem = a_system_prompt()
finally:
    cc.memory_text = _mem
check(MEM_MARKER in with_mem, "E2a the fixture really does carry a MEMORY line")
check(MEM_MARKER not in cc._offsite_system(with_mem),
      "E2b no MEMORY line survives redaction")

check("BINDING TEXT:" in red and "PRINCIPLE AND OPERATOR RULES:" in red,
      "E3 what is KEPT is the part already published in that public repo")

print()
print("== the call site: run it, do not read it ==")
msgs = [{"role": "system", "content": sp},
        {"role": "user", "content": "what is the gate doing?"}]
seen = capture_offsite_payload([dict(m) for m in msgs])
wire = str(seen.get("messages"))

check(seen.get("messages") is not None,
      "E4a chat_github reached the dispatcher at all (the recorder is wired in)")
check(MARKER not in wire,
      "E4b the live state does NOT reach the dispatcher when chat_github runs")
check(any(m.get("role") == "system" for m in (seen.get("messages") or [])),
      "E4c a system message is still sent -- redacted, not dropped")

_real = cc._offsite_system
try:
    cc._offsite_system = lambda t: t          # the mutation: no redaction at all
    bled = capture_offsite_payload([dict(m) for m in msgs])
finally:
    cc._offsite_system = _real
check(MARKER in str(bled.get("messages")),
      "E5 THE INSTRUMENT BITES: with the redactor neutered the marker DOES arrive",
      "so E4b is measuring the redaction and not an empty payload")

print()
print("== the banner: run it under both worlds ==")
_probe = cc._local_alive
_github_was = cc._GITHUB["on"]
try:
    cc._local_alive = lambda timeout=4: False
    cc._GITHUB["on"] = True
    dead_on = cc._banner_lines("qwen3:8b")

    cc._GITHUB["on"] = False
    dead_off = cc._banner_lines("qwen3:8b")

    cc._local_alive = lambda timeout=4: True
    cc._GITHUB["on"] = True
    alive = cc._banner_lines("qwen3:8b")
finally:
    cc._local_alive = _probe
    cc._GITHUB["on"] = _github_was

CLAIM = "stay on this PC"
check(CLAIM not in " ".join(dead_on),
      "E6a with no local model the banner does NOT claim the conversation stays here")
check("PUBLIC repo" in " ".join(dead_on),
      "E6b ...it says where the turn goes instead")
check(CLAIM not in " ".join(dead_off),
      "E6c with the fallback off it still makes no locality claim, and says it cannot answer")
check("no turn can be answered" in " ".join(dead_off).lower(),
      "E6d ...and says plainly that it cannot answer, rather than failing quietly")
check(CLAIM in " ".join(alive),
      "E7 THE INSTRUMENT BITES: with a local model alive the honest claim IS made",
      "so E6a is measuring the probe and not a deleted sentence")

worlds = [CLAIM in " ".join(w) for w in (dead_on, dead_off, alive)]
check(sum(worlds) == 1,
      "E8 the locality claim is conditional: true in exactly 1 of 3 worlds, not a constant")

print()
n_ok = sum(1 for r in results if r)
print("%d/%d passed" % (n_ok, len(results)))
sys.exit(0 if n_ok == len(results) else 1)
