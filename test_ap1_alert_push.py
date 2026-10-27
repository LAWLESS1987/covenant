#!/usr/bin/env python3
"""AP1 (A367, 2026-10-17): what the watchdog pushes to his phone is a held-down state change, not a log line.

His words: "yes turn alert push on". Pushing each rendered ALERT line would have sent about 1,250 a day. These checks
pin the gate that makes push worth having: one identity per condition, a 3-round hold-down each way, the phone's
heartbeat backoff left out, and delivery that never breaks a round. Pure: no node, no network, no outbox written.

    python test_ap1_alert_push.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_watchdog as W  # noqa: E402

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"   -- {detail}"))


def main():
    print("AP1 -- alert push sends starts and clears, held down")
    sr = "highway: sweep_red is present and run_full_sweep held -- no targeted re-run since this sweep"
    sr2 = "highway: sweep_red is present and rerun_unclean refused -- quarantined: measured not fixing it 2 times"
    check("AP1.1 one identity per highway condition, whatever its remedy note says",
          W.alert_identity(sr) == W.alert_identity(sr2) == "highway: sweep_red", (W.alert_identity(sr), W.alert_identity(sr2)))
    check("AP1.2 node lines keep their node and kind, digits ignored",
          W.alert_identity("node C: silent for 3612 s") == W.alert_identity("node C: silent for 3672 s")
          and W.alert_identity("node C: silent for 3612 s") != W.alert_identity("node B: silent for 3612 s"))

    g = W.PushGate(hold=3)
    out = [g.observe([sr]), g.observe([sr2])]
    check("AP1.3 under the hold-down nothing is sent (2 rounds present)", out == [[], []], out)
    third = g.observe([sr])
    check("AP1.4 the third round present sends exactly one 'started'", len(third) == 1 and third[0].startswith("ALERT started: "), third)
    more = [g.observe([sr2]) for _ in range(40)]
    check("AP1.5 a standing condition is not repeated (40 more rounds, wording changing: nothing sent)",
          all(m == [] for m in more), [m for m in more if m])
    gone = [g.observe([]) for _ in range(3)]
    check("AP1.6 cleared only after 3 rounds absent, once", gone[:2] == [[], []] and gone[2] == ["CLEARED: highway: sweep_red"], gone)

    g2 = W.PushGate(hold=3)
    flap = []
    for i in range(30):                            # present 2 rounds, gone 1: a rolling restart pattern
        flap += g2.observe(["node C down"] if i % 3 != 2 else [])
    check("AP1.7 a condition that never lasts 3 rounds is never sent (30 rounds of flapping)", flap == [], flap)

    g3 = W.PushGate(hold=3)
    backoff = "node A: 1 peer(s) unreachable -- heartbeats backed off"
    sent = [g3.observe([backoff]) for _ in range(10)]
    check("AP1.8 the phone peer's heartbeat backoff is left out (phone_silent is its alert)", all(s == [] for s in sent), sent)

    g4 = W.PushGate(hold=3)
    twice = [g4.observe(["node C down"]) for _ in range(3)] + [g4.observe([]) for _ in range(3)] + [g4.observe(["node C down"]) for _ in range(3)]
    check("AP1.9 a condition that clears and returns is told again", sum(len(x) for x in twice) == 3
          and twice[2] and twice[5] and twice[8], twice)

    said, posted = [], []
    say = lambda text, why, actor: said.append((text, why, actor)) or {"id": "x"}                 # noqa: E731
    post = lambda msg: posted.append(msg) or ("disabled", "no url")                               # noqa: E731
    r = W.deliver(["ALERT started: node C down"], cfg={"direct_line": True}, say=say, post=post)
    check("AP1.10 direct_line on: the message goes to the direct line with a reason and the watchdog as actor",
          said == [("ALERT started: node C down", "watchdog alert (A367)", "watchdog")] and r == [("direct_line", "sent", "")], (said, r))
    said.clear()
    r = W.deliver(["ALERT started: node C down"], cfg={}, say=say, post=post)
    check("AP1.11 direct_line off: nothing goes to the direct line", said == [] and r == [], (said, r))
    boom = lambda text, why, actor: 1 / 0                                                          # noqa: E731
    r = W.deliver(["x"], cfg={"direct_line": True}, say=boom, post=post)
    check("AP1.12 a failing channel never raises (a round is never broken by its alerting)", r == [("direct_line", "failed", "ZeroDivisionError")], r)
    check("AP1.13 the config reader treats a missing or broken file as off",
          W.push_config(os.path.join(HERE, "no_such_alert_push.json")) == {})

    n, good = len(RESULTS), sum(RESULTS)
    print(f"AP1: {good}/{n} passed")
    return 0 if good == n else 1


if __name__ == "__main__":
    sys.exit(main())
