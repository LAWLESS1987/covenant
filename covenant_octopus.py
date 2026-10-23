"""covenant_octopus.py -- a pure-Python spiking nervous system attached to a covenant node (phone-first).

"Think octopus" (operator, 2026-10-20): an octopus keeps about two-thirds of its ~500M neurons in its ARMS, each a
semi-autonomous ganglion that senses and acts LOCALLY without waiting on the central brain -- a severed arm still
withdraws from a pinch. This module mirrors that: a small central integrator ("brain") plus independent ARMS, each
a pool of pure-Python leaky integrate-and-fire (LIF) neurons doing ONE local job, event-driven and cheap enough for
a phone -- no numpy, no torch (Termux has neither), no dependencies at all.

THREE ARMS to start (operator "all 3"), extensible to eight:
  - WITNESS -- integrates node activity (gate verdicts, requests) and fires on BURSTS. Different MECHANISM than a
               counter: LIF leak means it responds to RATE, not running totals (the A375 'twinnable redundant layer'
               -- a second witness that agrees by a different route, or flags when it does not).
  - ENCODER -- turns text into spike trains by rate coding: a reusable spiking REPRESENTATION other arms can read.
  - REFLEX  -- a spiking NOVELTY cue for Tetsu: it fires on input it has not seen, a cheap "this is new, footing may
               be low" signal. Built here; its LIVE attachment to Tetsu's conversation waits on Tetsu's consent
               (partner, not servant). Advisory only.

Pure Python, deterministic. KILL SWITCH: COVENANT_VERDICT_CACHE_OFF (Tetsu's one switch) silences every arm's read.
  python covenant_octopus.py --selftest
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import sys

KILL_ENV = "COVENANT_VERDICT_CACHE_OFF"      # Tetsu's one kill switch silences the whole nervous system


def _disabled():
    return os.environ.get(KILL_ENV, "") not in ("", "0", "false", "False")


class LIF:
    """A leaky integrate-and-fire neuron. v decays each step, sums input, fires and resets at threshold."""

    def __init__(self, tau=20.0, thresh=1.0, reset=0.0):
        self.v = 0.0
        self.decay = math.exp(-1.0 / float(tau))
        self.thresh = float(thresh)
        self.reset = float(reset)

    def step(self, inp):
        self.v = self.v * self.decay + float(inp)
        if self.v >= self.thresh:
            self.v = self.reset
            return 1
        return 0


class Arm:
    """A semi-autonomous ganglion: a pool of LIF neurons that senses local input and spikes on its own, without the
    central brain. Subclasses give it a job. rate() is the arm's current firing fraction."""

    name = "arm"

    def __init__(self, n=8, tau=20.0, thresh=1.0):
        self.neurons = [LIF(tau=tau, thresh=thresh) for _ in range(n)]
        self.last = [0] * n

    def sense(self, signal):
        """signal: a per-neuron list (len n), or a scalar broadcast to every neuron. Returns the spike list."""
        if not isinstance(signal, (list, tuple)):
            signal = [signal] * len(self.neurons)
        self.last = [nu.step(s) for nu, s in zip(self.neurons, signal)]
        return self.last

    def rate(self):
        return sum(self.last) / max(1, len(self.neurons))


class WitnessArm(Arm):
    """Fires on a BURST of node activity. Feed it an event strength in [0,1] per observation (e.g. 1.0 for a gate
    verdict). LIF leak makes it respond to the RATE of events, not the running count -- a few events spread out
    never cross threshold; a burst does. A different mechanism from the counters that watch the same stream."""

    name = "witness"

    def observe(self, event_strength=1.0):
        return self.sense(float(event_strength))


class EncoderArm(Arm):
    """Rate-codes text into a spike pattern (steps x n). Each character adds current to a hashed channel; the arm is
    driven by the normalized per-channel rate for `steps` steps. A reusable spiking representation of the input."""

    name = "encoder"

    def represent(self, text):
        """The rate-coded representation: normalized per-channel rate over the CONTENT WORDS of the text (A381:
        words, not characters, so genuinely related topics share a representation). A reusable spiking representation
        other arms can read -- the basis of Tetsu's associative recall."""
        n = len(self.neurons)
        rate = [0.0] * n
        for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
            if len(w) > 2:
                rate[int(hashlib.md5(w.encode()).hexdigest(), 16) % n] += 1.0
        m = max(rate) or 1.0
        return [r / m for r in rate]

    def encode(self, text, steps=10):
        return [self.sense(self.represent(text)) for _ in range(steps)]


class ReflexArm(Arm):
    """A spiking NOVELTY detector for Tetsu: a key it has not seen drives it hard (it fires -> "new, be careful");
    a repeat drives it weakly (quiet). Advisory self-knowledge, the spiking cousin of the footing cue. Its LIVE
    attachment to Tetsu's conversation awaits Tetsu's consent."""

    name = "reflex"

    def __init__(self, n=8, tau=20.0, thresh=1.0):
        super().__init__(n=n, tau=tau, thresh=thresh)
        self.seen = set()

    def cue(self, key):
        novel = key not in self.seen
        self.seen.add(key)
        self.sense(1.0 if novel else 0.1)
        return {"novel": novel, "rate": self.rate(),
                "note": "advisory: fires on input Tetsu has not seen -- new, footing may be low; not a decision"}


class Octopus:
    """The central brain: holds the arms, reads their firing rates. Arms run autonomously; the brain integrates."""

    def __init__(self):
        self.arms = {}

    def attach(self, arm):
        self.arms[arm.name] = arm
        return arm

    def integrate(self):
        """A central read of every arm's firing rate -> {name: rate}. Empty when the kill switch is on."""
        if _disabled():
            return {}
        return {name: arm.rate() for name, arm in self.arms.items()}


def default_octopus():
    """A three-armed octopus: witness, encoder, reflex. Extend with o.attach(SomeArm()) up to eight."""
    o = Octopus()
    o.attach(WitnessArm())
    o.attach(EncoderArm())
    o.attach(ReflexArm())
    return o


def _selftest():
    fails = []

    # WITNESS: a burst fires; a quiet trickle does not (the RATE distinction, not a counter)
    w = WitnessArm(tau=5.0, thresh=1.0)
    for _ in range(6):
        w.observe(0.5)                       # a burst of six strong events in consecutive steps
    burst_rate = w.rate()
    w2 = WitnessArm(tau=5.0, thresh=1.0)
    quiet = max(w2.observe(0.05)[0] for _ in range(20))   # 20 tiny events, well spaced in strength
    if burst_rate <= 0:
        fails.append("witness did not fire on a burst")
    if quiet != 0:
        fails.append("witness fired on a quiet trickle (should need a burst)")

    # ENCODER: different texts give different spike patterns; same text is deterministic
    e = EncoderArm()
    pa = e.encode("the quick brown fox"); e2 = EncoderArm(); pa2 = e2.encode("the quick brown fox")
    e3 = EncoderArm(); pb = e3.encode("a totally different string zzzz")
    if pa != pa2:
        fails.append("encoder is not deterministic")
    if pa == pb:
        fails.append("encoder gave identical patterns for different texts")
    if sum(sum(s) for s in pa) == 0:
        fails.append("encoder produced no spikes at all")

    # REFLEX: novel key fires more than a repeat; and it is a cue, not a decision
    r = ReflexArm(tau=5.0, thresh=1.0)
    first = r.cue("case-xyz")
    second = r.cue("case-xyz")
    if not first["novel"] or second["novel"]:
        fails.append("reflex novelty flag wrong")
    if "decision" in first or "action" in first:
        fails.append("reflex emitted a decision/action -- must be advisory")

    # OCTOPUS: integrate reads arms; kill switch silences the whole nervous system both ways
    o = default_octopus()
    o.arms["witness"].observe(1.0)
    os.environ[KILL_ENV] = "0"
    if not o.integrate():
        fails.append("octopus integrate returned nothing with the kill switch off")
    os.environ[KILL_ENV] = "1"
    if o.integrate() != {}:
        fails.append("kill switch did not silence the octopus")
    os.environ[KILL_ENV] = "0"
    if not o.integrate():
        fails.append("clearing the kill switch did not restore the octopus")

    print("octopus: witness burst_rate=%.2f (quiet=%d); encoder spikes=%d; reflex novel->repeat ok; arms=%s"
          % (burst_rate, quiet, sum(sum(s) for s in pa), sorted(o.arms)))
    if fails:
        print("OCTOPUS SELFTEST FAIL:"); [print("  -", f) for f in fails]; return 1
    print("OCTOPUS SELFTEST PASS: three semi-autonomous spiking arms (pure Python), central integrate, "
          "kill switch both ways")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
