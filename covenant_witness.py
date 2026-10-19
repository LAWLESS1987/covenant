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


def main(argv=None):
    print(json.dumps({"phone_silence": report(), "ask_bursts": ask_burst_report()}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
