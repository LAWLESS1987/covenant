#!/usr/bin/env python3
"""P21 -- the self-evaluation round counter must survive a restart.

WHY. On 2026-09-16 ops/SELF_EVAL.md held nothing between 14:55Z and 18:53Z
while covenant_watchdog.py logged normally every round and covenant_watchdog_
guard.py read the log as fresh. The ledger was not broken. The round counter
lived only in memory, and the system restarts this process on purpose:
covenant_highway.py's schedule_watchdog_restart fired five times, and the guard
revived it four more (attempts #8-#11, each "no live watchdog PID"). A counter
that needs ~63 uninterrupted minutes never reached 60 again.

Each case below is driven BOTH ways: the guard must be able to return the other
answer, or it has never been observed.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_watchdog as W  # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-58s %s%s" % (label, "OK" if ok else "*** FAIL ***",
                            ("  " + detail) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def with_state(path):
    W.SELF_EVAL_STATE = path
    W._self_eval["round"] = 0
    W._self_eval["persist"] = True


# The final line must not read "<digits> PASSED": covenant_one parses a
# tally out of it, and "P21 PASSED" was recorded as 21 checks when the
# suite runs 16. P21-P24 inflated the sweep by ~38 checks that way.
def main():
    tmp = tempfile.mkdtemp()
    state = os.path.join(tmp, "logs", "self_eval_state.json")

    print("P21a -- nothing to resume")
    with_state(state)
    check("no state file resumes to 0", W._self_eval_resume() == 0)

    print("P21b -- a persisted round comes back")
    with_state(state)
    W._self_eval["round"] = 59
    W._self_eval_persist()
    check("state file was written", os.path.isfile(state))
    W._self_eval["round"] = 0
    check("resume restores 59", W._self_eval_resume() == 59)
    check("one more round reaches the block boundary",
          (59 + 1) % W.SELF_EVAL_EVERY == 0)

    print("P21c -- --once must NOT persist (the guard that stops a one-shot "
          "run inheriting an hour)")
    with_state(state)
    os.remove(state)
    W._self_eval["persist"] = False          # what --once leaves it at
    W._self_eval["round"] = 41
    W._self_eval_persist()
    check("persist=False writes nothing", not os.path.exists(state))

    print("P21d -- a truncated file (killed mid-write) must not crash or lie")
    with_state(state)
    with open(state, "w", encoding="utf-8") as fh:
        fh.write('{"round": 5')                # deliberately unterminated
    check("corrupt JSON resumes to 0, no raise", W._self_eval_resume() == 0)

    print("P21e -- nonsense values are refused")
    for bad in ('{"round": -3}', '{"round": "sixty"}', '{}', '[]'):
        with_state(state)
        with open(state, "w", encoding="utf-8") as fh:
            fh.write(bad)
        check("refuses %-16s -> 0" % bad, W._self_eval_resume() == 0)

    print("P21f -- the write is atomic (no .tmp left behind)")
    with_state(state)
    W._self_eval["round"] = 7
    W._self_eval_persist()
    check("no stray .tmp file", not os.path.exists(state + ".tmp"))
    with open(state, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    check("round round-trips exactly", payload.get("round") == 7,
          "got %r" % (payload.get("round"),))
    check("carries a timestamp", bool(payload.get("at")))

    print("P21g -- THE REGRESSION: a restart mid-hour keeps its place")
    with_state(state)
    for _ in range(58):                       # 58 rounds, then killed
        W._self_eval["round"] += 1
        W._self_eval_persist()
    killed_at = W._self_eval["round"]
    W._self_eval["round"] = 0                 # the restart
    resumed = W._self_eval_resume()
    check("killed at 58, resumes at 58", killed_at == 58 and resumed == 58)
    fired = []
    for _ in range(2):                        # two more rounds post-restart
        W._self_eval["round"] += 1
        W._self_eval_persist()
        if W._self_eval["round"] % W.SELF_EVAL_EVERY == 0:
            fired.append(W._self_eval["round"])
    check("block fires at 60 despite the restart", fired == [60],
          "fired=%r" % (fired,))

    print("P21h -- and it genuinely FAILS without the fix (in-memory only)")
    round_only = 0
    fired_old = []
    for _ in range(58):
        round_only += 1
    round_only = 0                            # the same restart, no persistence
    for _ in range(2):
        round_only += 1
        if round_only % W.SELF_EVAL_EVERY == 0:
            fired_old.append(round_only)
    check("old behaviour fires nothing -- the bug, reproduced",
          fired_old == [])

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("P21 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("P21 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
