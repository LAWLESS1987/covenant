#!/usr/bin/env python3
"""covenant_witness.py -- the spiking witness (A375, Amendment 1): a second reading of the highway's event-stream
conditions, by a DIFFERENT mechanism, so a disagreement shows which one is blind.

His words, 2026-10-19: "improve the spiking system to expand / have it be a redundant layer of everything weve
developed and grew". Reviewed before any code by Tetsu and six models (docs/SPIKING_WITNESS.md). All six named one
flaw: a neuron reading the same ledger as the highway is algorithmic diversity, not independent sensing. Amendment 1
answers it: a twin reads a DIFFERENT observation path, or it is labelled a second opinion; it must match a plain
CUSUM baseline or be retired; cadence is frozen from the tuning half; fault injection sits beside the history.

THIS FILE, THE FIRST PIECE: the phone-silence twin, read-only. Two readings of the same stream of check-in times:
  - pacemaker (spiking): a leaky integrate-and-fire neuron. A constant drive raises its potential; each check-in
    resets it; if check-ins stop, it crosses threshold and fires = "silent". The leak between events is solved
    exactly (v grows linearly here, since the "leak" of a silence detector is an upward drive, not a decay).
  - cusum (the baseline it must beat): a one-sided cumulative sum of (gap - expected) over the stream; it alarms
    when the running sum crosses a bound. A standard change-point detector, nothing to explain.
Both are hand-set from the stream's own measured median gap on the TUNING half, never adapted online (Gemini: an
online median learns the silence it should catch). Neither acts: this file senses and records.

Not here yet (Amendment 1, later, and the phone side needs his yes): the phone-side witness of the PC, Tailscale's
own view beside the check-in ledger, a writer pacemaker per ledger, and the leaky-burst twin for failure streams.
"""
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKINS = os.path.join(HERE, "ops", "phone_checkins.jsonl")
MODEL_ASKS = os.path.join(HERE, "ops", "model_asks.jsonl")

# The two known phone silences, the bar a twin must clear (docs/SPIKING_WITNESS.md). Epoch seconds.
KNOWN_SILENCES = (
    {"name": "A329 (53 h from 10-08)", "from": "2026-10-08", "min_hours": 48},
    {"name": "A338 (from 10-12 06:48)", "from": "2026-10-12", "min_hours": 20},
)


def checkin_times(path=None):
    """Sorted epoch-second times of every phone check-in on record."""
    out = []
    try:
        with open(path or CHECKINS, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                t = r.get("at")
                if isinstance(t, (int, float)):
                    out.append(float(t))
    except OSError:
        return []
    return sorted(out)


def median_gap(times):
    """The median inter-check-in gap, in seconds, over TIMES. The cadence both detectors are set from."""
    gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
    return statistics.median(gaps) if gaps else 0.0


class Pacemaker:
    """A leaky integrate-and-fire SILENCE neuron, event-driven. Between check-ins the potential rises at a steady
    drive; a check-in resets it to 0. It fires when the potential reaches 1, which happens exactly `fire_gaps`
    median gaps after the last check-in. So it is a spiking restatement of "silent for fire_gaps x the normal
    cadence" -- different arithmetic from the highway's fixed 3 h, set from the stream's own rhythm."""

    def __init__(self, median_gap_s, fire_gaps=6.0):
        self.gap = float(median_gap_s)
        self.fire_gaps = float(fire_gaps)
        self.drive = 1.0 / (self.fire_gaps * self.gap) if self.gap > 0 else 0.0

    def potential(self, since_last_s):
        return max(0.0, since_last_s) * self.drive

    def silent(self, since_last_s):
        return self.potential(since_last_s) >= 1.0

    def fires_after_s(self):
        return self.fire_gaps * self.gap


class Cusum:
    """One-sided CUSUM over the gap stream: S = max(0, S + gap - k), reset to 0 on each check-in's own slack. It
    alarms when S crosses h (both in units of the median gap). The plain baseline Amendment 1 makes the pacemaker
    beat: if the neuron catches no more than this at no more false alarms, the neuron is not worth its name."""

    def __init__(self, median_gap_s, k_gaps=2.0, h_gaps=4.0):
        self.gap = float(median_gap_s)
        self.k = k_gaps * self.gap
        self.h = h_gaps * self.gap

    def alarm(self, since_last_s):
        # a single running gap: the one-sided statistic reduces to max(0, gap - k) for the current silence
        return max(0.0, since_last_s - self.k) >= self.h


class LeakyBurst:
    """A leaky integrate-and-fire neuron over a FAILURE stream (model asks ok/failed; later, forum strikes). Each
    failure adds w_fail; each success subtracts w_ok (floored at 0); the charge leaks as exp(-dt/tau) between
    events. It fires when the charge reaches theta -- so failures CLOSE TOGETHER sum and fire, while scattered ones
    leak away before they can. Different arithmetic from the highway's fixed-window count. tau is set from the
    stream's own cadence (burst_gaps median gaps), not a wall-clock guess."""

    def __init__(self, tau_s, w_fail=1.0, w_ok=0.34, theta=2.5, vmax=6.0):
        self.tau, self.w_fail, self.w_ok, self.theta, self.vmax = float(tau_s), float(w_fail), float(w_ok), float(theta), float(vmax)

    def run(self, events):
        """events: sorted [(t, ok)]. Yields (t, charge, fired) after each event."""
        v, last = 0.0, None
        for t, ok in events:
            if last is not None and self.tau > 0:
                v *= math.exp(-(t - last) / self.tau)
            v = min(self.vmax, v + self.w_fail) if not ok else max(0.0, v - self.w_ok)
            last = t
            yield t, v, v >= self.theta

    def bursts(self, events):
        """(t, charge) at each event where the neuron fires -- a cluster of failures."""
        return [(t, v) for t, v, fired in self.run(events) if fired]


def ask_events(path=None):
    """Sorted [(epoch, ok_bool)] from the model-ask ledger."""
    out = []
    try:
        with open(path or MODEL_ASKS, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                t = r.get("at")
                if isinstance(t, (int, float)):
                    out.append((float(t), bool(r.get("ok"))))
    except OSError:
        return []
    return sorted(out, key=lambda e: e[0])


def silences(times, detector, min_gap_s=None):
    """Every stretch where DETECTOR would have fired: (start_epoch, end_epoch, hours) for each gap in TIMES whose
    silence crosses the detector's threshold. DETECTOR is a callable taking a running-silence in seconds."""
    out = []
    for a, b in zip(times, times[1:]):
        if detector(b - a):
            out.append((a, b, (b - a) / 3600.0))
    return out


def covers(found, when_prefix, min_hours):
    """True if any (start, end, hours) in FOUND lasts min_hours and SPANS the given yyyy-mm-dd prefix (local) --
    the date falls on or between the silence's start and end day. A silence's start is the last check-in before the
    hole, which can be the prior day, so 'spans' is the honest test, not 'starts on'."""
    import time
    for start, end, hours in found:
        if hours < min_hours:
            continue
        if time.strftime("%Y-%m-%d", time.localtime(start)) <= when_prefix <= time.strftime("%Y-%m-%d", time.localtime(end)):
            return True
    return False


def split_tune_score(times, frac=0.5):
    """The tuning half and the scoring half of the stream, by time (Amendment 1: tune on the first, score on the
    second, never the same)."""
    if len(times) < 4:
        return times, times
    cut = times[0] + (times[-1] - times[0]) * frac
    return [t for t in times if t <= cut], [t for t in times if t > cut]


def report(path=None, fire_gaps=6.0):
    """Set both detectors from the TUNING half's cadence, score both on the WHOLE stream, and check the bar: both
    known silences found, the pacemaker finding at least what CUSUM finds. Returns a dict; acts on nothing."""
    times = checkin_times(path)
    if len(times) < 10:
        return {"state": "UNKNOWN", "why": "too few check-ins to set a cadence (%d)" % len(times)}
    tune, _score = split_tune_score(times)
    gap = median_gap(tune) or median_gap(times)
    pace, cus = Pacemaker(gap, fire_gaps), Cusum(gap)
    import time
    p_found = silences(times, pace.silent)
    c_found = silences(times, cus.alarm)
    p_starts = {round(pf[0]) for pf in p_found}
    bar = {s["name"]: {"pacemaker": covers(p_found, s["from"], s["min_hours"]),
                       "cusum": covers(c_found, s["from"], s["min_hours"])} for s in KNOWN_SILENCES}
    since_last = time.time() - times[-1]
    return {
        "state": "PRESENT" if pace.silent(since_last) else "ABSENT",
        "since_last_checkin_h": round(since_last / 3600.0, 1),
        "median_gap_min": round(gap / 60.0, 1),
        "pacemaker_fires_after_h": round(pace.fires_after_s() / 3600.0, 1),
        "pacemaker_silences": len(p_found), "cusum_silences": len(c_found),
        "bar": bar,
        "both_known_found": all(v["pacemaker"] for v in bar.values()),
        # Amendment 1's keep/retire test: the pacemaker must catch at least every silence CUSUM catches (every CUSUM
        # alarm's gap has a pacemaker alarm too). If it does not, the plain baseline wins and the neuron is retired.
        "pacemaker_covers_cusum": all(round(cf[0]) in p_starts for cf in c_found),
    }


def ask_burst_report(path=None):
    """The leaky-burst twin over the model-ask stream. Runs and reports, but is SHADOW/UNKEPT: there is no labelled
    failure-burst incident to validate it against. Measured 2026-10-19: the known Tetsu-down events (A329 10-08,
    A282 10-06) show only 1-2 FAILED asks each, because when Tetsu is down asks are not made -- that silence is
    `tetsu_cannot_answer`'s (a readiness check), not this failure stream's. So Amendment 1's keep test cannot be met
    here yet, and this never acts. It is kept in the code because the mechanism is correct and reusable (e.g. for
    the forum-strike stream, which does have labelled incidents)."""
    import time
    events = ask_events(path)
    if len(events) < 20:
        return {"state": "UNKNOWN", "why": "too few asks (%d)" % len(events), "kept": False}
    gaps = [b[0] - a[0] for a, b in zip(events, events[1:]) if b[0] > a[0]]
    tau = (statistics.median(gaps) if gaps else 60.0) * 120     # ~a 2 h clustering scale from the ask cadence
    lb = LeakyBurst(tau_s=tau)
    b = lb.bursts(events)
    return {"state": "PRESENT" if (events and lb.bursts(events[-50:]) and b and b[-1][0] == events[-1][0]) else "ABSENT",
            "asks": len(events), "failures": sum(1 for _t, ok in events if not ok),
            "bursts": [time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) for t, _v in b],
            "kept": False, "why_unkept": "no labelled failure-burst incident to validate against (rule 5)"}


def strike_events(rows=None):
    """Sorted [(epoch, solved_bool)] of Moltbook posting-challenge results from free's sends -- the same stream the
    highway's moltbook_strikes reads. A solved challenge is ok; a failed or abstained one is a miss."""
    import calendar
    if rows is None:
        try:
            import covenant_free_will as FW
            rows = FW.sends()
        except Exception:                                         # noqa: BLE001
            return []
    out = []
    for r in rows or []:
        v = r.get("verification")
        if not isinstance(v, dict) or not v.get("required"):
            continue
        at = r.get("at")
        if at is None:
            try:
                at = calendar.timegm(time.strptime(str(r.get("t", "")), "%Y-%m-%dT%H:%M:%SZ"))
            except ValueError:
                continue
        out.append((float(at), bool(v.get("solved"))))
    return sorted(out, key=lambda e: e[0])


def strike_report(rows=None):
    """The leaky-burst twin over the Moltbook strike stream. RETIRED, not kept (Amendment 2, 2026-10-19). I first
    claimed it KEPT because it "fires over the 12-unsolved run on record (a labelled incident)". Five models
    (Gemini, Meta AI, Mistral, Chat Smith, and DeepSeek) refuted that on review, unanimously and correctly:
      1. It does NOT beat the baseline. The highway's consecutive-unsolved count ALSO fires on the 12-run, so firing
         there is not an improvement over what exists (Meta AI).
      2. It reads the SAME observation path (the challenge stream), so it fails the independence rule -- it is a
         second mechanism, not a second reading (Meta AI).
      3. It restates the base rate. The account is unsolved 79 of 114, so any accumulator fires ~continuously (it
         fires on 108 of 114); that is a description, not a detection (Gemini, Mistral, Chat Smith).
      4. The keep test had no SPECIFICITY: it tested only that the twin fires on a labelled incident, never its
         false-alarm rate on incident-free periods. "The whole layer is validated only on positives" (Mistral).
    The real correction is the BAR, not this twin -- see Amendment 2 in docs/SPIKING_WITNESS.md. The code stays as a
    shadow, reusable only for a stream that has an INDEPENDENT path and where the twin beats the baseline at a fixed
    false-alarm rate. It raises nothing and acts on nothing. The claim as first written is preserved in the plan
    beside the correction."""
    events = strike_events(rows)
    if len(events) < 10:
        return {"state": "UNKNOWN", "why": "too few challenge results (%d)" % len(events), "kept": None}
    lb = LeakyBurst(tau_s=0, w_fail=1.0, w_ok=0.5, theta=5.0, vmax=20.0)   # tau_s=0: beat-space, no wall-clock leak
    # LeakyBurst.run leaks by wall-clock; here we want beat-space, so feed unit-spaced events (index as time).
    spaced = [(float(i), ok) for i, (_t, ok) in enumerate(events)]
    fired = lb.bursts(spaced)
    final_charge = list(lb.run(spaced))[-1][1] if spaced else 0.0
    # the longest consecutive unsolved run on record -- the labelled incident the twin must catch
    run = longest = 0
    for _t, ok in events:
        run = 0 if ok else run + 1
        longest = max(longest, run)
    # did the neuron fire somewhere inside that longest run?
    solved = sum(1 for _t, ok in events if ok)
    unsolved_rate = round(1 - solved / len(events), 3)
    # the twin fires on this fraction of all events -- the number that shows it restates the base rate
    fire_rate = round(len(fired) / len(events), 3)
    return {
        "state": "PRESENT" if final_charge >= lb.theta else "ABSENT", "final_charge": round(final_charge, 2),
        "challenges": len(events), "solved": solved, "unsolved_rate": unsolved_rate,
        "longest_unsolved_run": longest, "fired_events": len(fired), "fire_rate": fire_rate,
        # RETIRED (Amendment 2): it does not beat the baseline on the labelled run, reads the same path, and fires at
        # ~the base rate (fire_rate ~ unsolved_rate), with no specificity test. Never kept, whatever the data.
        "kept": False,
        "why_unkept": ("fires on %.0f%% of events while the account is %.0f%% unsolved -- it restates the base rate; "
                       "the consecutive baseline also fires on the %d-run, so it is not beaten; same path, no "
                       "specificity test (retired on review, 2026-10-19)" % (fire_rate * 100, unsolved_rate * 100, longest)),
    }


# ----------------------------------------------------------------- the foundation (Amendment 3): CUSUM + the keep test
#
# His words, 2026-10-19: "Put the foundation though its likely to be needed" / "just do it". Amendment 3 (five voices,
# unanimous): CUSUM is the sufficient statistic on these small streams; a spiking twin is added ONLY when it is
# measured to beat CUSUM at an EQUAL false-alarm rate on a held-out set of real negatives. This is the prove-or-retire
# machinery every twin must pass. Pure functions; nothing acts.

class CusumDetector:
    """A one-sided cumulative-sum change detector with reset and a recovery hold (hysteresis). Over a stream of
    values x_t: S = max(0, S + x_t - k); it fires when S >= h, then resets S to 0 and holds for `recover` events
    before it can fire again. k is the slack (drift allowed before accumulating), h the decision threshold, both in
    the stream's own units. The sufficient statistic the review says to beat before any neuron is kept."""

    def __init__(self, k, h, recover=0):
        self.k, self.h, self.recover = float(k), float(h), int(recover)

    def fires(self, values):
        """Indices (0-based into `values`) at which the detector fires. `values` is the per-event statistic -- e.g.
        the gap since the last check-in, or 1.0 for a miss and 0.0 for an ok."""
        out, s, hold = [], 0.0, 0
        for i, x in enumerate(values):
            if hold > 0:
                hold -= 1
                s = 0.0
                continue
            s = max(0.0, s + float(x) - self.k)
            if s >= self.h:
                out.append(i)
                s, hold = 0.0, self.recover
        return out


def extract_negatives(event_times, incidents, pad_s=0.0):
    """The honest negatives: the incident-free spans of a stream, as (start, end) epoch pairs. `incidents` is a list
    of (start, end) windows; a negative is any gap between the stream's first and last event that does not overlap a
    padded incident window. The review's rule: NEVER manufacture an incident -- normal operation IS the negative set
    (Mistral, Grok). Returns the spans; the caller counts false alarms that land in them."""
    if not event_times:
        return []
    t0, t1 = min(event_times), max(event_times)
    bad = sorted((float(a) - pad_s, float(b) + pad_s) for a, b in incidents)
    negs, cur = [], t0
    for a, b in bad:
        if a > cur:
            negs.append((cur, min(a, t1)))
        cur = max(cur, b)
        if cur >= t1:
            break
    if cur < t1:
        negs.append((cur, t1))
    return [(a, b) for a, b in negs if b > a]


def _in_any(t, windows):
    return any(a <= t <= b for a, b in windows)


def score_detector(fire_times, incidents, negatives):
    """The NAB PRINCIPLE (not the benchmark): a detector is scored by whether it catches each labelled incident and
    how many false alarms it raises on the held-out negatives. Returns {caught, missed, detections, false_alarms,
    fa_per_negative, fa_rate_per_day}. Only the FIRST fire inside an incident window counts as the detection; every
    fire inside a negative span is a false alarm (Mistral/Grok: FPs lower the score)."""
    inc = [(float(a), float(b)) for a, b in incidents]
    caught = sum(1 for a, b in inc if any(a <= t <= b for t in fire_times))
    fa = [t for t in fire_times if _in_any(t, negatives)]
    neg_s = sum(b - a for a, b in negatives)
    return {"caught": caught, "missed": len(inc) - caught, "incidents": len(inc),
            "detections": [a for a, b in inc if any(a <= t <= b for t in fire_times)],
            "false_alarms": len(fa), "negative_days": round(neg_s / 86400.0, 2),
            "fa_rate_per_day": round(len(fa) / (neg_s / 86400.0), 3) if neg_s > 0 else None}


def beats_baseline(twin_fires, base_fires, incidents, negatives):
    """Amendment 3's keep test. A twin is KEPT only if, at a false-alarm rate no worse than the baseline's on the
    negatives, it catches at least as many incidents AND catches at least one the baseline MISSED. Returns
    (kept_bool, why, {twin, base})."""
    tw, bs = score_detector(twin_fires, incidents, negatives), score_detector(base_fires, incidents, negatives)
    twin_only = [a for a, b in ((float(x), float(y)) for x, y in incidents)
                 if any(a <= t <= b for t in twin_fires) and not any(a <= t <= b for t in base_fires)]
    fa_ok = (tw["false_alarms"] <= bs["false_alarms"])
    kept = bool(fa_ok and tw["caught"] >= bs["caught"] and twin_only)
    if not twin_only:
        why = "catches nothing the baseline misses -- a second mechanism, not a second reading (retire)"
    elif not fa_ok:
        why = "catches a baseline miss but at a WORSE false-alarm rate (%d vs %d) -- not kept" % (tw["false_alarms"], bs["false_alarms"])
    elif tw["caught"] < bs["caught"]:
        why = "misses incidents the baseline catches -- not kept"
    else:
        why = "catches %d incident(s) the baseline missed at an equal-or-better false-alarm rate -- kept" % len(twin_only)
    return kept, why, {"twin": tw, "base": bs}


# ----------------------------------------------------------------- the negatives PIPELINE (Amendment 3, the still-to-build piece)
#
# Amendment 3's unanimous verdict (six models + Tetsu, 2026-10-19): a spiking twin can be KEPT only when it is measured
# to beat CUSUM at an equal-or-better false-alarm rate on a held-out set of REAL negatives, and "normal operation IS the
# negative set -- never manufacture an incident". That negative set does not exist until it has ACCRUED: the detectors
# run read-only over weeks, every alarm logged-but-ignored, and only time that has safely passed is sealed as a trusted
# negative. This is that accrual -- read-only, idempotent, acting on nothing. It writes one internal ledger and a
# high-water mark; it never touches the highway, the gate, the ledger of record, or any outward surface. The keep test
# (beats_baseline) above is the judge; this is the evidence it needs, accumulated honestly over time.
#
# The honesty margin (rule 9): a span is sealed only once it is OLDER than CONFIRM_LAG_S. Recent time is not yet
# trustworthy -- an incident could still be unfolding in it, and calling a span clean before it is over is exactly the
# false-negative the whole witness exists to avoid. And prove_or_retire returns UNDETERMINED until enough negative-days
# have accrued: specificity measured on a thin negative set is not specificity (the A376-strike lesson, in code).

WITNESS_STATE = os.path.join(HERE, "ops", "witness_state.json")
NEGATIVES_LEDGER = os.path.join(HERE, "ops", "witness_negatives.jsonl")
SPIKING_WITNESS = os.path.join(HERE, "ops", "spiking_witness.jsonl")   # the redundancy layer's disagreements, told once
CONFIRM_LAG_S = 2 * 86400          # time younger than two days is not yet sealed as a verified negative
PROVE_MIN_NEGATIVE_DAYS = 30.0     # below this the keep test is UNDETERMINED -- a thin negative set cannot measure specificity


def known_incident_windows(times):
    """The (start, end) epoch window of each KNOWN_SILENCE, read off the real stream: the gap that SPANS the silence's
    date (the same test as covers()) and lasts at least its min_hours. A known silence not yet present in the stream is
    simply absent -- never invented (the review's rule: do not manufacture an incident)."""
    import time
    out = []
    for s in KNOWN_SILENCES:
        for a, b in zip(times, times[1:]):
            if (b - a) / 3600.0 < s["min_hours"]:
                continue
            if time.strftime("%Y-%m-%d", time.localtime(a)) <= s["from"] <= time.strftime("%Y-%m-%d", time.localtime(b)):
                out.append((a, b))
                break
    return out


def seal_negatives(event_times, incidents, now, confirm_lag_s=CONFIRM_LAG_S, sealed_until=0.0):
    """PURE. The incident-free spans safe to trust as negatives this run: each extract_negatives span, clamped to start
    at sealed_until (never re-seal already-sealed time) and to END before the horizon now-confirm_lag_s (never seal time
    an unfolding incident could still be hiding in). Returns [(a, b)] with b > a."""
    horizon = float(now) - float(confirm_lag_s)
    out = []
    for a, b in extract_negatives(event_times, incidents):
        a2, b2 = max(float(a), float(sealed_until)), min(float(b), horizon)
        if b2 > a2:
            out.append((a2, b2))
    return out


def shadow_alarms(fire_times, spans):
    """PURE. The fires that land inside sealed negative spans -- logged, never acted on. This is the specificity
    (false-alarm) record a twin is later judged on. A fire inside a real incident is a detection, and is not counted
    here."""
    return [t for t in fire_times if _in_any(t, spans)]


def _phone_fires(times, fire_gaps=6.0):
    """The pacemaker and CUSUM alarm INSTANTS over the stream (last check-in + the detector's own latency), so each
    fire can be attributed to the span it lands in. Cadence frozen from the tuning half (Amendment 1)."""
    gap = median_gap(split_tune_score(times)[0]) or median_gap(times)
    pace, cus = Pacemaker(gap, fire_gaps), Cusum(gap)
    pace_fires = [a + pace.fires_after_s() for a, _b, _h in silences(times, pace.silent)]
    cus_fires = [a + (cus.k + cus.h) for a, _b, _h in silences(times, cus.alarm)]
    return gap, pace_fires, cus_fires


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def accrued_spans(ledger_path=None):
    """Every sealed negative span across the accrual ledger, as (a, b) epoch pairs -- the verified negative set that has
    accumulated so far. Absent ledger -> empty (no data, no claim)."""
    out = []
    try:
        with open(ledger_path or NEGATIVES_LEDGER, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                for a, b in r.get("spans", []):
                    out.append((float(a), float(b)))
    except OSError:
        return []
    return out


def accrue_once(now, checkins_path=None, state_path=None, ledger_path=None,
                confirm_lag_s=CONFIRM_LAG_S, fire_gaps=6.0):
    """Read-only accrual, idempotent. Seal the phone stream's newly-trustworthy incident-free spans, record the
    pacemaker/CUSUM false alarms inside them, and advance the high-water mark. Writes WITNESS_STATE and appends to
    NEGATIVES_LEDGER only when there is something new to seal; acts on nothing else. Re-running with no new elapsed
    time seals nothing (the mark makes it idempotent). Returns the record (or the reason it sealed nothing)."""
    state_path = state_path or WITNESS_STATE
    ledger_path = ledger_path or NEGATIVES_LEDGER
    times = checkin_times(checkins_path)
    if len(times) < 10:
        return {"sealed_spans": 0, "why": "too few check-ins to set a cadence (%d)" % len(times)}
    state = _read_json(state_path, {})
    sealed_until = float(state.get("phone_sealed_until", 0.0))
    incidents = known_incident_windows(times)
    spans = seal_negatives(times, incidents, now, confirm_lag_s, sealed_until)
    gap, pace_fires, cus_fires = _phone_fires(times, fire_gaps)
    rec = {
        "at": float(now), "stream": "phone_checkins",
        "spans": [[round(a), round(b)] for a, b in spans],
        "neg_seconds": round(sum(b - a for a, b in spans)),
        "shadow_fa": {"pacemaker": len(shadow_alarms(pace_fires, spans)),
                      "cusum": len(shadow_alarms(cus_fires, spans))},
        "median_gap_min": round(gap / 60.0, 1), "confirm_lag_h": round(confirm_lag_s / 3600.0, 1),
        "incidents_known": len(incidents),
    }
    if spans:
        with open(ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        state["phone_sealed_until"] = max(sealed_until, float(now) - float(confirm_lag_s))
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    return rec


def prove_or_retire(now, checkins_path=None, ledger_path=None, fire_gaps=6.0,
                    min_negative_days=PROVE_MIN_NEGATIVE_DAYS):
    """Amendment 3's keep test for the phone pacemaker, run against the ACCRUED negative set (not the naive whole-stream
    one). Until at least min_negative_days of verified negatives have accrued, the honest verdict is UNDETERMINED (rule
    9): the test is not run, because specificity measured on a thin negative set is not specificity. Reads only; it
    decides nothing on its own -- it reports KEEP/RETIRE for a person to act on."""
    spans = accrued_spans(ledger_path)
    neg_days = sum(b - a for a, b in spans) / 86400.0
    times = checkin_times(checkins_path)
    if len(times) < 10:
        return {"verdict": "UNDETERMINED", "why": "too few check-ins (%d)" % len(times),
                "accrued_negative_days": round(neg_days, 2)}
    if neg_days < min_negative_days:
        return {"verdict": "UNDETERMINED", "accrued_negative_days": round(neg_days, 2),
                "need_days": min_negative_days,
                "why": "not enough verified negatives yet to measure specificity -- keep accruing"}
    incidents = known_incident_windows(times)
    _gap, pace_fires, cus_fires = _phone_fires(times, fire_gaps)
    kept, why, detail = beats_baseline(pace_fires, cus_fires, incidents, spans)
    return {"verdict": "KEEP" if kept else "RETIRE", "why": why,
            "accrued_negative_days": round(neg_days, 2), "incidents": len(incidents), **detail}


# ----------------------------------------------------------------- the REDUNDANCY layer (A375 Amendment 1, his 2026-10-27)
#
# His original ask, 2026-10-19: "a redundant layer of everything we've developed and grew", and 2026-10-27, after the
# keep test RETIRED the pacemaker as a twin: "build it for redundancy." These are two different goals, and this is the
# second one, built honestly as what it is:
#   - the KEEP TEST (Amendment 3, prove_or_retire) asks "does the spiking twin add DETECTION the baseline misses?"
#     On the phone stream the answer is no -- pacemaker and CUSUM agree (RETIRE). That verdict stands; nothing here
#     overturns it or claims the twin is superior.
#   - REDUNDANCY asks a different question: run both readings in PARALLEL so that a DISAGREEMENT shows one of them has
#     gone blind (Amendment 1: "Disagreement is the output ... told once"). Two readings that AGREE is the healthy,
#     expected state; the signal is where they DIFFER.
# So agreement is not a failure here, it is the baseline condition. The value is resilience (if one detector breaks or
# drifts, the other still reads) and the disagreement alarm (a bug or drift in one shows as divergence from the other).
# HONEST LIMIT: the pacemaker and CUSUM read the SAME ledger, so this is ALGORITHMIC redundancy -- it catches a fault in
# one detector's arithmetic, not a fault in the shared observation path. INDEPENDENT-sensing redundancy (the phone's own
# view of the PC) is the path the review called for and waits on his yes for the phone branch. Reads only; acts on nothing.

def agree_disagree(spiking_keys, baseline_keys):
    """PURE. Given the two readings' fire KEYS on the same stream (e.g. rounded gap-starts), split them into: both
    fired (agree), only the spiking twin fired (twin_only), only the baseline fired (base_only). The disagreements --
    twin_only and base_only -- are redundancy's whole output: where the readings differ, one is blind."""
    sp, bs = set(spiking_keys), set(baseline_keys)
    return {"agree": sorted(sp & bs), "twin_only": sorted(sp - bs), "base_only": sorted(bs - sp)}


def redundancy(path=None, fire_gaps=6.0):
    """Read the phone stream TWICE -- the spiking pacemaker and the plain CUSUM -- and report their agreement and every
    disagreement. It does NOT claim the twin beats the baseline (the keep test settled that: they agree on real
    incidents, so the twin was RETIRED as a detector). This is the redundant LAYER his A375 asked for: a second reading
    whose job is to DIVERGE when one of the two goes blind. Returns a dict with each disagreement's time and which
    reading flagged it; acts on nothing."""
    import time
    times = checkin_times(path)
    if len(times) < 10:
        return {"state": "UNKNOWN", "why": "too few check-ins to set a cadence (%d)" % len(times)}
    gap = median_gap(split_tune_score(times)[0]) or median_gap(times)
    pace, cus = Pacemaker(gap, fire_gaps), Cusum(gap)
    p_sil, c_sil = silences(times, pace.silent), silences(times, cus.alarm)
    hours_of = {round(a): round(h, 1) for a, _b, h in p_sil}
    hours_of.update({round(a): round(h, 1) for a, _b, h in c_sil})
    ad = agree_disagree([round(a) for a, _b, _h in p_sil], [round(a) for a, _b, _h in c_sil])

    def ev(keys, who):
        return [{"stream": "phone_checkins", "at_gap_start": k, "flagged_by": who, "hours": hours_of.get(k),
                 "when": time.strftime("%Y-%m-%d %H:%M", time.localtime(k))} for k in keys]

    n = len(ad["agree"]) + len(ad["twin_only"]) + len(ad["base_only"])
    return {
        "state": "OK", "stream": "phone_checkins",
        "readings": {"spiking": "pacemaker(%.1f gaps)" % fire_gaps, "baseline": "cusum"},
        "agree": len(ad["agree"]), "twin_only": len(ad["twin_only"]), "base_only": len(ad["base_only"]),
        "agreement_rate": round(len(ad["agree"]) / n, 3) if n else 1.0,
        "disagreements": ev(ad["twin_only"], "spiking_twin_only") + ev(ad["base_only"], "baseline_only"),
        "note": ("the two readings agree -- the expected healthy state; redundancy's value is resilience and the "
                 "disagreement alarm, not added detection (the keep test RETIRED the twin as a detector)."),
    }


def redundancy_tell(now, path=None, witness_path=None, fire_gaps=6.0):
    """Append only the NEW disagreements to the spiking-witness ledger -- told once (Amendment 1). Idempotent: a
    disagreement already on record is not told again. Writes only; acts on nothing."""
    witness_path = witness_path or SPIKING_WITNESS
    rep = redundancy(path, fire_gaps)
    if rep.get("state") != "OK":
        return {"told": 0, "why": rep.get("why", rep.get("state"))}
    told = set()
    try:
        with open(witness_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                told.add((r.get("stream"), r.get("at_gap_start"), r.get("flagged_by")))
    except OSError:
        pass
    new = [d for d in rep["disagreements"] if (d["stream"], d["at_gap_start"], d["flagged_by"]) not in told]
    if new:
        with open(witness_path, "a", encoding="utf-8") as fh:
            for d in new:
                fh.write(json.dumps(dict(d, told_at=float(now))) + "\n")
    return {"told": len(new), "agreement_rate": rep["agreement_rate"],
            "agree": rep["agree"], "twin_only": rep["twin_only"], "base_only": rep["base_only"]}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    import time
    if argv and argv[0] == "redundancy":
        print(json.dumps(redundancy(), indent=1, default=str))
        return 0
    if argv and argv[0] == "tell":
        print(json.dumps(redundancy_tell(time.time()), indent=1, default=str))
        return 0
    if argv and argv[0] == "accrue":
        print(json.dumps(accrue_once(time.time()), indent=1, default=str))
        return 0
    if argv and argv[0] == "prove":
        print(json.dumps(prove_or_retire(time.time()), indent=1, default=str))
        return 0
    print(json.dumps({"phone_silence": report(), "ask_bursts": ask_burst_report(),
                      "moltbook_strikes": strike_report()}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
