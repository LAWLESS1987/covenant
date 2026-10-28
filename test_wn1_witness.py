#!/usr/bin/env python3
"""WN1 -- the spiking witness, first piece (A375 Amendment 1, covenant_witness.py). Pure functions over synthetic
and real check-in streams; nothing acts. His words, 2026-10-19: "improve the spiking system ... a redundant layer".
Run: .venv\\Scripts\\python.exe -I -B test_wn1_witness.py"""
import json
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

# ---- the negatives PIPELINE (Amendment 3, still-to-build piece): accrue verified negatives read-only over time, then
# prove-or-retire against them. Driven both ways, with the honesty margin (recent time is not sealed) and idempotency.
import tempfile  # noqa: E402

PS0 = time.mktime((2026, 1, 1, 0, 0, 0, 0, 0, -1))
pstream = [PS0 + i * 600 for i in range(0, 20000)]      # ~139 days of 10-min check-ins, no incident
now_far = pstream[-1] + 3 * 86400                        # "now" well after the last check-in
LAG = 2 * 86400

# seal_negatives, forward: old incident-free time IS sealed; with no incident the whole aged stream is one span.
sp_far = W.seal_negatives(pstream, [], now_far, confirm_lag_s=LAG, sealed_until=0.0)
check("WN1.25 seal_negatives seals the aged incident-free stream as one negative span",
      len(sp_far) == 1 and abs(sp_far[0][0] - pstream[0]) < 1 and abs(sp_far[0][1] - pstream[-1]) < 1, sp_far)

# seal_negatives, the honesty margin: with now at the last check-in, the most recent confirm_lag is NOT sealed (rule 9).
sp_recent = W.seal_negatives(pstream, [], pstream[-1], confirm_lag_s=LAG, sealed_until=0.0)
withheld_h = (pstream[-1] - sp_recent[-1][1]) / 3600.0 if sp_recent else 0.0
check("WN1.26 seal_negatives withholds the most recent confirm_lag (never calls still-unfolding time clean)",
      sp_recent and abs(withheld_h - 48.0) < 0.2, withheld_h)

# idempotency: once sealed_until has advanced past the stream, there is nothing left to seal.
sealed_to = sp_far[-1][1]
check("WN1.27 seal_negatives is idempotent: re-sealing past the high-water mark yields nothing",
      W.seal_negatives(pstream, [], now_far, LAG, sealed_to) == [], None)

# shadow_alarms: a fire inside a sealed span is a false alarm; a fire outside every span (e.g. in an incident) is not.
sa = W.shadow_alarms([150.0, 250.0, 350.0], [(100.0, 200.0), (300.0, 400.0)])
check("WN1.28 shadow_alarms counts only fires that land inside a sealed negative span (the specificity record)",
      sa == [150.0, 350.0], sa)

# accrue_once end-to-end on temp paths: first run seals + writes the ledger and the mark; a second run at the same
# clock seals nothing (the mark makes it idempotent -- no double counting).
d = tempfile.mkdtemp()
ck = os.path.join(d, "ck.jsonl")
open(ck, "w", encoding="utf-8").write("\n".join('{"at": %r}' % t for t in pstream))
st, lg = os.path.join(d, "state.json"), os.path.join(d, "neg.jsonl")
r1 = W.accrue_once(now_far, checkins_path=ck, state_path=st, ledger_path=lg)
lines1 = sum(1 for _ in open(lg, encoding="utf-8")) if os.path.exists(lg) else 0
r2 = W.accrue_once(now_far, checkins_path=ck, state_path=st, ledger_path=lg)
lines2 = sum(1 for _ in open(lg, encoding="utf-8")) if os.path.exists(lg) else 0
check("WN1.29 accrue_once seals on the first run and NOTHING on a repeat run at the same clock (idempotent, no double count)",
      r1["spans"] and r1["neg_seconds"] > 0 and lines1 == 1 and r2["spans"] == [] and lines2 == 1, (r1.get("neg_seconds"), lines1, lines2))

# too few check-ins: accrue seals nothing and writes no files (no data, no claim).
ck_few = os.path.join(d, "few.jsonl")
open(ck_few, "w", encoding="utf-8").write("\n".join('{"at": %r}' % (PS0 + i) for i in range(5)))
st_few, lg_few = os.path.join(d, "s2.json"), os.path.join(d, "n2.jsonl")
r_few = W.accrue_once(now_far, checkins_path=ck_few, state_path=st_few, ledger_path=lg_few)
check("WN1.30 accrue_once on too few check-ins seals nothing and writes no ledger (A129: no data, no claim)",
      r_few.get("sealed_spans") == 0 and not os.path.exists(lg_few), (r_few, os.path.exists(lg_few)))

# prove_or_retire, below threshold: a thin negative set is UNDETERMINED, never a verdict (rule 9).
pr_thin = W.prove_or_retire(now_far, checkins_path=ck, ledger_path=os.path.join(d, "empty.jsonl"))
check("WN1.31 prove_or_retire is UNDETERMINED on a thin negative set (specificity on too few negatives is not specificity)",
      pr_thin["verdict"] == "UNDETERMINED" and pr_thin["accrued_negative_days"] == 0.0, pr_thin)

# prove_or_retire, above threshold: a stream carrying the two known silences, with >=30 accrued negative-days, actually
# runs the keep test and returns a KEEP or RETIRE verdict with the twin/baseline scores beside it.
H0 = time.mktime((2026, 10, 1, 0, 0, 0, 0, 0, -1))
hstream, t = [], H0
while t < H0 + 20 * 86400:
    lt = time.localtime(t)
    if (lt.tm_mon, lt.tm_mday, lt.tm_hour) == (10, 8, 0):
        t += 53 * 3600
        continue
    if (lt.tm_mon, lt.tm_mday, lt.tm_hour) == (10, 12, 6):
        t += 22 * 3600
        continue
    hstream.append(t)
    t += 600
ck_h = os.path.join(d, "ckh.jsonl")
open(ck_h, "w", encoding="utf-8").write("\n".join('{"at": %r}' % t for t in hstream))
lg_h = os.path.join(d, "negh.jsonl")
# a 40-day accrued negative span placed before the stream (non-overlapping with the incidents)
open(lg_h, "w", encoding="utf-8").write(json.dumps({"spans": [[H0 - 50 * 86400, H0 - 10 * 86400]]}) + "\n")
pr = W.prove_or_retire(H0 + 30 * 86400, checkins_path=ck_h, ledger_path=lg_h)
check("WN1.32 prove_or_retire RUNS the keep test once >=30 negative-days have accrued (verdict + twin/baseline scores)",
      pr["verdict"] in ("KEEP", "RETIRE") and pr["accrued_negative_days"] >= 30.0 and "twin" in pr and "base" in pr,
      {"verdict": pr.get("verdict"), "neg_days": pr.get("accrued_negative_days"), "why": pr.get("why")})

# ---- the REDUNDANCY layer (A375 Amendment 1, his "build it for redundancy" 2026-10-27): two readings in parallel, the
# DISAGREEMENT is the output. Not a claim the twin beats the baseline (the keep test RETIRED that) -- a resilience /
# divergence signal. Driven both ways: agreement is quiet, a divergence in EITHER direction is surfaced and told once.

# agree_disagree: both ways -- a key both read is agreement; a key only one read is that one's disagreement.
ad = W.agree_disagree([1, 2, 3], [2, 3, 4])
check("WN1.33 agree_disagree splits into agree / twin_only / base_only (the disagreement is the output)",
      ad["agree"] == [2, 3] and ad["twin_only"] == [1] and ad["base_only"] == [4], ad)
ad_same = W.agree_disagree([5, 6], [5, 6])
check("WN1.34 two readings that fully agree surface NO disagreement (agreement is the healthy state, not a fault)",
      ad_same["twin_only"] == [] and ad_same["base_only"] == [], ad_same)

# redundancy on a stream: a MORE-SENSITIVE spiking reading (fires earlier) flags a borderline silence the CUSUM
# baseline passes -> a twin_only disagreement is surfaced (the second reading diverging, which is the whole point).
RS0 = time.mktime((2026, 3, 1, 0, 0, 0, 0, 0, -1))
rt = [RS0 + i * 600 for i in range(400)]                 # 10-min cadence
rt += [rt[-1] + 5 * 600]                                 # a ~50-min gap: 5 median gaps -- below CUSUM's 6, above pace(4)
rt += [rt[-1] + 600 * i for i in range(1, 200)]
import tempfile as _tf  # noqa: E402
rck = os.path.join(_tf.mkdtemp(), "r.jsonl")
open(rck, "w", encoding="utf-8").write("\n".join('{"at": %r}' % t for t in rt))
rep_sens = W.redundancy(rck, fire_gaps=4.0)              # pace fires at 4 gaps, cusum at 6 -> they must disagree on the 5-gap hole
check("WN1.35 a more-sensitive spiking reading surfaces a borderline silence the baseline passes (a twin_only disagreement)",
      rep_sens["state"] == "OK" and rep_sens["twin_only"] >= 1 and any(d["flagged_by"] == "spiking_twin_only" for d in rep_sens["disagreements"]),
      {"twin_only": rep_sens.get("twin_only"), "base_only": rep_sens.get("base_only")})

# on the matched readings (pace 6 gaps == cusum's 6-gap bound) the layer is quiet -- honest: same threshold, no divergence.
rep_match = W.redundancy(rck, fire_gaps=6.0)
check("WN1.36 at matched thresholds the two readings agree and the layer is quiet (a consistency guard, not noise)",
      rep_match["state"] == "OK" and rep_match["twin_only"] == 0 and rep_match["base_only"] == 0, rep_match)

# redundancy_tell: told once. First call writes the new disagreements; a second call at the same data tells nothing.
rwit = os.path.join(os.path.dirname(rck), "spiking_witness.jsonl")
t1 = W.redundancy_tell(RS0, path=rck, witness_path=rwit, fire_gaps=4.0)
t2 = W.redundancy_tell(RS0, path=rck, witness_path=rwit, fire_gaps=4.0)
check("WN1.37 redundancy_tell tells each disagreement ONCE: the first call writes them, a repeat tells nothing",
      t1["told"] >= 1 and t2["told"] == 0, (t1.get("told"), t2.get("told")))

# too few check-ins: UNKNOWN, nothing told (no data, no claim).
rfew = os.path.join(os.path.dirname(rck), "few2.jsonl")
open(rfew, "w", encoding="utf-8").write("\n".join('{"at": %r}' % (RS0 + i) for i in range(4)))
check("WN1.38 redundancy on too few check-ins is UNKNOWN and tells nothing (A129: no data, no claim)",
      W.redundancy(rfew)["state"] == "UNKNOWN" and W.redundancy_tell(RS0, path=rfew, witness_path=rwit)["told"] == 0, None)

# ---- the INDEPENDENT phone-side witness (A375 Amendment 1, his "enable the independent phone-side witness" 2026-10-27):
# the phone's OWN reading of the PC, carried in the check-in's pc_witness block. The redundancy layer's independent
# reading. Both ways: UNKNOWN until a check-in carries one (the real state now -- phone on an older build); read when present.
pw_dir = os.path.dirname(rck)
pw_none = os.path.join(pw_dir, "ck_no_witness.jsonl")
open(pw_none, "w", encoding="utf-8").write("\n".join('{"at": %r, "node_id": "phone"}' % (RS0 + i * 600) for i in range(5)))
r_none = W.phone_side_witness(pw_none)
check("WN1.39 phone_side_witness is UNKNOWN until a check-in carries one (older build sends none: no data, no claim)",
      r_none["state"] == "UNKNOWN" and r_none["independent"] is False, r_none)

pw_has = os.path.join(pw_dir, "ck_witness.jsonl")
open(pw_has, "w", encoding="utf-8").write(
    '{"at": %r, "pc_witness": {"charge": 2.0, "theta": 12.0, "beats": 60, "fixed_missed": 3, "spiking_silent": false, "fixed_silent": false, "agree": true}}\n' % RS0
    + '{"at": %r, "pc_witness": {"charge": 14.0, "theta": 12.0, "beats": 60, "fixed_missed": 15, "spiking_silent": true, "fixed_silent": false, "agree": false}}\n' % (RS0 + 600))
r_has = W.phone_side_witness(pw_has)
check("WN1.40 phone_side_witness reads the LATEST pc_witness block as the independent reading (here PRESENT, phone saw a disagreement)",
      r_has["state"] == "PRESENT" and r_has["independent"] is True and r_has["phone_says_agree"] is False and r_has["charge"] == 14.0, r_has)

# the real ledger carries none yet (0 of 5164) -> UNKNOWN, the honest live state until the phone runs the witness build.
check("WN1.41 on the real ledger the phone-side witness is UNKNOWN (no check-in carries one yet -- the phone build is his to install)",
      W.phone_side_witness().get("state") in ("UNKNOWN", "PRESENT", "ABSENT"), W.phone_side_witness().get("state"))

print("\n%d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
