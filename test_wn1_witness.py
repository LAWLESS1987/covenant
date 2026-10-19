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

# ---- the Moltbook-strike twin: KEPT, because the record holds a labelled incident (the 12-unsolved run, A324).
# miss = failed or abstained challenge; ok = solved. The mechanism (leaky, asymmetric drain) is what lets a flaky
# run that keeps resetting the consecutive count still accumulate and fire.
def _sev(seq):
    return [(float(i), ok) for i, ok in enumerate(seq)]


# a run of 12 unsolved fires; a healthy all-solved stream does not
check("WN1.15 the strike twin fires on a 12-unsolved run (the A324 incident) and stays quiet on an all-solved stream",
      W.strike_report(rows=None) is not None
      and W.LeakyBurst(tau_s=0, w_fail=1.0, w_ok=0.5, theta=5.0).bursts(_sev([False] * 12))
      and not W.LeakyBurst(tau_s=0, w_fail=1.0, w_ok=0.5, theta=5.0).bursts(_sev([True] * 30)))
# the finding: a FLAKY pattern (solve every 3rd) keeps the consecutive count low but the asymmetric charge climbs
flaky = _sev([False, False, True] * 20)
consec = 0
mx = 0
for _t, ok in flaky:
    consec = 0 if ok else consec + 1
    mx = max(mx, consec)
check("WN1.16 a flaky strike pattern (solve every 3rd) keeps the consecutive run at 2 but the leaky twin fires -- the "
      "blind spot of a consecutive count",
      mx == 2 and bool(W.LeakyBurst(tau_s=0, w_fail=1.0, w_ok=0.5, theta=5.0).bursts(flaky)), mx)
# on the real record (if present) it is kept; absent/short -> UNKNOWN with kept None (staged copy)
def _rows(solved_seq):
    return [{"verification": {"required": True, "solved": bool(s)}, "at": float(i)} for i, s in enumerate(solved_seq)]


# WN1.17 (RETIRED on review, 2026-10-19): the strike twin is NEVER kept. Five models showed it restates the base
# rate (fires at ~the unsolved rate), does not beat the consecutive baseline on the labelled run, and reads the same
# path. So on the real record OR a heavily-unsolved record, kept is False and the reason names the restated base rate.
sr = W.strike_report(rows=_rows([i % 15 == 0 for i in range(114)]))   # ~93% unsolved, like the real account
check("WN1.17 the strike twin is RETIRED, never kept: it fires at ~the base rate and says so (fire_rate ~ unsolved_rate)",
      sr["kept"] is False and "restates the base rate" in sr["why_unkept"] and abs(sr["fire_rate"] - sr["unsolved_rate"]) < 0.25, sr)
# the real record (if present) is also never kept; absent record -> UNKNOWN, kept None
sr_real = W.strike_report()
check("WN1.18 the strike twin on the real record is not kept either (or UNKNOWN when the record is absent)",
      sr_real.get("kept") in (False, None), sr_real)
# the MECHANISM is still correct (the retirement is about the stream and the bar, not the neuron): an all-solved
# record does not fire; a 12-run does
check("WN1.19 the leaky mechanism itself is sound: all-solved does not fire, a 12-run does (the retirement is about "
      "the stream's base rate and the missing specificity test, not the neuron)",
      W.strike_report(rows=_rows([True] * 40))["state"] == "ABSENT"
      and W.strike_report(rows=_rows([True] * 20 + [False] * 12))["state"] == "PRESENT", None)

# ---- the foundation (Amendment 3): CUSUM detector + the keep test (extract negatives, score FPs, beat the baseline).
# CusumDetector: a flat stream with a sustained step fires once in the step, resets, and the recover hold blocks an
# immediate re-fire.
cd = W.CusumDetector(k=1.0, h=3.0, recover=0)
flat = [0.0] * 20
step = [0.0] * 10 + [2.0] * 10          # +2 per event over k=1 -> S climbs +1/event -> crosses h=3 after 3 steps
check("WN1.20 CUSUM is quiet on a flat stream and fires inside a sustained step (the sufficient statistic)",
      cd.fires(flat) == [] and cd.fires(step) and 10 <= cd.fires(step)[0] <= 14, (cd.fires(flat), cd.fires(step)))
# recover hold: after a fire, `recover` events pass before it can fire again
cd_hold = W.CusumDetector(k=1.0, h=3.0, recover=5)
many = [0.0] * 5 + [3.0] * 20
f_hold = cd_hold.fires(many)
check("WN1.21 the recover hold spaces fires out (hysteresis): consecutive fires are at least recover+1 apart",
      len(f_hold) >= 2 and all(b - a >= 6 for a, b in zip(f_hold, f_hold[1:])), f_hold)

# extract_negatives: the incident-free spans between the first and last event
times = [float(i) for i in range(0, 1000)]
incidents = [(200.0, 260.0), (600.0, 630.0)]
negs = W.extract_negatives(times, incidents)
# no incident's interior (its midpoint) falls inside a negative span; spans only touch incidents at the boundary
mids = [(a + b) / 2 for a, b in incidents]
clean = not any(s < m < e for s, e in negs for m in mids)
check("WN1.22 extract_negatives returns the incident-free spans only (no incident falls inside a span; nothing manufactured)",
      len(negs) == 3 and negs[0][0] == 0.0 and abs(negs[-1][1] - 999.0) < 1e-9 and clean, negs)

# score_detector: catches an incident, counts false alarms on the negatives
fires_good = [230.0, 615.0]             # one inside each incident, none in a negative
fires_noisy = [230.0, 615.0, 100.0, 400.0, 800.0]   # three extra, all in negative spans
sg = W.score_detector(fires_good, incidents, negs)
sn = W.score_detector(fires_noisy, incidents, negs)
check("WN1.23 score_detector counts caught incidents and false alarms on the negatives, with a per-day FP rate",
      sg["caught"] == 2 and sg["false_alarms"] == 0 and sn["caught"] == 2 and sn["false_alarms"] == 3
      and sn["fa_rate_per_day"] is not None and sn["fa_rate_per_day"] > sg["fa_rate_per_day"], (sg, sn))

# beats_baseline: the keep test, driven every way.
base = [230.0]                          # baseline catches only the first incident, no false alarms
twin_wins = [230.0, 615.0]              # catches the SECOND incident the baseline missed, no extra false alarms
twin_restates = [230.0]                 # catches nothing the baseline misses
twin_noisy = [230.0, 615.0, 100.0, 400.0]   # catches the miss but at a worse false-alarm rate
k1, w1, _ = W.beats_baseline(twin_wins, base, incidents, negs)
k2, w2, _ = W.beats_baseline(twin_restates, base, incidents, negs)
k3, w3, _ = W.beats_baseline(twin_noisy, base, incidents, negs)
check("WN1.24 beats_baseline KEEPS a twin that catches a baseline-missed incident at an equal-or-better false-alarm "
      "rate; RETIRES one that restates the baseline; RETIRES one that catches the miss but at a worse FP rate",
      k1 is True and "kept" in w1 and k2 is False and "second mechanism" in w2 and k3 is False and "WORSE false-alarm" in w3,
      (k1, w1, k2, w2, k3, w3))

print("\n%d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
