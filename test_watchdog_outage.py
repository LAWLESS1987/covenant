#!/usr/bin/env python3
"""
test_watchdog_outage.py -- what the watchdog does when the mesh is gone, and
which warnings it has agreed not to shout about.

Both behaviours were found by a real outage on 2026-09-06 and both are the
kind that fail silently: a watchdog that never quite reaches its third strike
looks identical to a watchdog that is working, and a suppression pattern that
stops matching turns a documented non-event into permanent noise, which is how
an operator learns to ignore alerts.

Offline: `health` and `start_node` are stubbed, no node is contacted and none
is started.

Run:  python test_watchdog_outage.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_watchdog as W          # noqa: E402

FAILS = []
RAN = []


def check(cond, label):
    RAN.append(bool(cond))
    print(("ok    " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


_started = []
W.start_node = lambda n: _started.append(n["id"])
W.log = lambda level, msg: None
OK = {"warnings": [], "chain_height": 9, "peers": 1, "version": "v8.40", "judge": "quorum(x)"}


def run(health):
    W.health = health
    _started.clear()
    W.one_pass()
    return sorted(_started)


# --- O: a total outage is not a blip ---------------------------------------
W._fail_counts = {n["id"]: 0 for n in W.NODES}
got = run(lambda port, timeout=8: (None, "connection refused"))
check(got == sorted(n["id"] for n in W.NODES),
      "O1 every node unreachable in one pass restarts all of them immediately")

W._fail_counts = {n["id"]: 0 for n in W.NODES}
one_down = lambda port, timeout=8: ((None, "refused") if port == W.NODES[0]["port"] else (dict(OK), None))
first = run(one_down)
second = run(one_down)
third = run(one_down)
check(first == [] and second == [],
      "O2 a single node blipping is NOT restarted on the first two misses")
check(third == [W.NODES[0]["id"]],
      "O3 ...and is restarted on the third, which is what the strike rule is for")

W._fail_counts = {n["id"]: 0 for n in W.NODES}
run(one_down)
run(lambda port, timeout=8: (dict(OK), None))
check(run(one_down) == [], "O4 a node that comes back resets its own counter")

# --- F: the suppression list, matched as substrings ------------------------
LIVE = [
    ("no provider key: the ethics seat is the deferring chain (the distilled students, then HELD unless the policy seats a runner) plus "
     "the semantic judge; a hold fails CLOSED, a clean verdict admits", True,
     "F1 the CURRENT keyless-seat wording is suppressed"),
    ("ethics gate has no provider key and is failing CLOSED -- this node will reject "
     "every transaction", True,
     "F2 ...and so is the wording it replaced, so an old node is not noisy either"),
    ("code sandbox unavailable -- no usable 'fork' start method on this platform (win32)",
     True, "F3 a platform fact that fails closed is suppressed, not shouted every pass"),
    # F4 INVERTED 2026-09-14 (A114). This asserted that "node minted its OWN
    # genesis" is SUPPRESSED, and it was, because /health raised it permanently
    # on the founder: own_genesis asked who SIGNED the genesis rather than
    # whether this node's genesis IS the canonical one, so node A -- whose key
    # signed the genesis B and C adopted -- declared itself unable to converge
    # for ever while running a chain identical to theirs. The mute was the right
    # answer to a false alarm and the wrong answer to a true one.
    #
    # The false alarm is fixed upstream now, so the mute is gone, and this check
    # has to say the opposite or it pins the bug. A node that raises this today
    # genuinely cannot converge with its peers, and the watchdog must alert.
    # The suite was shipped RED by the commit that removed the mute (450bd06):
    # it is registered in covenant_one, it went from green to exit 1, and
    # nothing noticed until an adversarial review ran it. Deleting a
    # suppression is a behaviour change, and the test that named it is part of
    # the change.
    ("node minted its OWN genesis -- it cannot converge with peers", False,
     "F4 the genesis warning ALERTS again (A114: it is no longer a false positive)"),
    ("anomaly spike: ['peer_message_error']", False, "F5 a real anomaly still alerts"),
    ("INSECURE mock judge active -- ethics gate is keyword matching", False,
     "F6 an insecure judge still alerts -- suppression must never reach a safety claim"),
]
for text, want_suppressed, label in LIVE:
    got = any(fp in text for fp in W.FALSE_POSITIVE_WARNINGS)
    check(got is want_suppressed, label)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print(f"WATCHDOG OUTAGE: {len(RAN)}/{len(RAN)} passed (offline; no node contacted, none started)")
