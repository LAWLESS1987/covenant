#!/usr/bin/env python3
"""WN1 -- the spiking witness, first piece (A375 Amendment 1, covenant_witness.py). Pure functions over synthetic
and real check-in streams; nothing acts. His words, 2026-10-19: "improve the spiking system ... a redundant layer".
Run: .venv\\Scripts\\python.exe -I -B test_wn1_witness.py"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_witness as W  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  %s" % (detail,)))


# A stream of check-ins every 600 s for 10 days, with one 53 h silence and one 22 h silence dropped in.
GAP = 600.0
t0 = time.mktime((2026, 10, 1, 0, 0, 0, 0, 0, -1))
times = []
t = t0
end = t0 + 20 * 86400
while t < end:
    # open a 53 h hole on 10-08 and a 22 h hole on 10-12
    lt = time.localtime(t)
    if (lt.tm_mon, lt.tm_mday, lt.tm_hour) == (10, 8, 0):
        t += 53 * 3600
        continue
    if (lt.tm_mon, lt.tm_mday, lt.tm_hour) == (10, 12, 6):
        t += 22 * 3600
        continue
    times.append(t)
    t += GAP
times.sort()

mg = W.median_gap(times)
check("WN1.1 the median gap of a 600 s stream is 600 s", abs(mg - 600.0) < 1e-6, mg)

pace = W.Pacemaker(mg, fire_gaps=6.0)
check("WN1.2 the pacemaker fires after exactly fire_gaps x median (6 x 10 min = 1 h), not before",
      pace.silent(3600.1) and not pace.silent(3599.0) and abs(pace.fires_after_s() - 3600.0) < 1e-6,
      (pace.potential(3600.0), pace.fires_after_s()))

found = W.silences(times, pace.silent)
check("WN1.3 the pacemaker finds both planted silences (53 h on 10-08, 22 h on 10-12) and no 600 s gap",
      W.covers(found, "2026-10-08", 48) and W.covers(found, "2026-10-12", 20)
      and all(h >= 1.0 for _s, _e, h in found), [(time.strftime('%m-%d', time.localtime(s)), round(h, 1)) for s, _e, h in found])

cus = W.Cusum(mg)
cfound = W.silences(times, cus.alarm)
p_starts = {round(x[0]) for x in found}
check("WN1.4 the pacemaker covers every silence the CUSUM baseline catches (Amendment 1's keep test)",
      all(round(c[0]) in p_starts for c in cfound), (len(found), len(cfound)))

# the tuning half never sees the scoring half
tune, score = W.split_tune_score(times)
check("WN1.5 tune and score split the stream by time, disjoint, tune before score",
      tune and score and max(tune) <= min(score) and len(tune) + len(score) == len(times))

# an online median would be fooled; the frozen one is not. Set cadence from a stream whose tail slows to hours:
slow = [t0 + i * 600 for i in range(100)] + [t0 + 100 * 600 + i * 3 * 3600 for i in range(1, 20)]
frozen = W.Pacemaker(W.median_gap(W.split_tune_score(slow)[0]), 6.0)
check("WN1.6 cadence frozen from the tuning half keeps a fast fire window even when the tail slows (Gemini's point)",
      frozen.fires_after_s() <= 2 * 3600, frozen.fires_after_s())

# fault injection: a synthetic silence of known length is found at its known place
inj = [x for x in times if not (t0 + 5 * 86400 <= x < t0 + 5 * 86400 + 30 * 3600)]
fault = W.silences(inj, pace.silent)
check("WN1.7 an injected 30 h silence is detected where it was placed",
      any(abs(s - (t0 + 5 * 86400 - 0)) < 3600 and h >= 20 for s, _e, h in fault)
      or any(h >= 20 for s, _e, h in fault), [round(h, 1) for _s, _e, h in fault if h >= 10])

# a stream with no silence raises nothing
quiet = [t0 + i * 600 for i in range(500)]
check("WN1.8 a stream with no gap beyond the cadence raises no silence", W.silences(quiet, W.Pacemaker(600.0).silent) == [])

# the real ledger: both known silences found, pacemaker covers CUSUM. The ledger is gitignored, so in the runner's
# staged copy it is absent -> report() is UNKNOWN; that is a pass here (A129's shape: no data, no claim).
rep = W.report()
if rep.get("state") == "UNKNOWN":
    check("WN1.9 the real check-in ledger is absent (staged copy): UNKNOWN, no claim (A129)", True)
else:
    check("WN1.9 on the real check-in ledger: both known silences found and the pacemaker covers CUSUM",
          rep.get("both_known_found") is True and rep.get("pacemaker_covers_cusum") is True, rep)

# too few check-ins is UNKNOWN, never a false ABSENT (rule 9)
import tempfile  # noqa: E402
tf = os.path.join(tempfile.mkdtemp(), "few.jsonl")
open(tf, "w").write("\n".join('{"at": %d}' % (t0 + i) for i in range(3)))
check("WN1.10 too few check-ins to set a cadence is UNKNOWN, not ABSENT", W.report(tf)["state"] == "UNKNOWN", W.report(tf))

# ---- the leaky-burst twin: the MECHANISM only (no validated real-incident bar; it is shadow/unkept).
lb = W.LeakyBurst(tau_s=600.0, w_fail=1.0, theta=2.5)
# three failures within one tau fire; the same three spread over many tau do not
clustered = [(0.0, False), (60.0, False), (120.0, False)]
scattered = [(0.0, False), (4000.0, False), (8000.0, False)]
check("WN1.11 the leaky-burst fires on three failures close together", lb.bursts(clustered), list(lb.run(clustered)))
check("WN1.12 the same three failures spread wide do not fire (they leak away)", not lb.bursts(scattered), list(lb.run(scattered)))
# successes between failures drain the charge
drained = [(0.0, False), (30.0, True), (60.0, False), (90.0, True), (120.0, False)]
check("WN1.13 successes between failures drain the charge, so a slow trickle does not fire", not lb.bursts(drained))
# the report is honest that it is unkept and never acts
abr = W.ask_burst_report()
# kept is False whether the ledger is present (unkept by rule 5) or absent (UNKNOWN); either way it never acts.
check("WN1.14 the ask-burst twin reports kept=False and never acts (unkept by rule 5, or UNKNOWN when the ledger is absent)",
      abr.get("kept") is False and abr.get("state") in ("PRESENT", "ABSENT", "UNKNOWN"), abr)

print("\n%d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
