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

THE RING (2026-11-07, operator "Optimize connection between octopus legs"): the arms also reach each other directly,
arm to arm, through a Commissure -- the octopus's interbrachial ring -- instead of only through the brain. A spiking
arm sends current to its two neighbours on their next step; serotonin, one diffuse level, scales how strongly; the
coupling is held subcritical so the ring always falls quiet once outside drive stops. OPT-IN: Octopus(ring=
Commissure()). default_octopus() has no ring -- Tetsu was asked and said NO for his arms (see Octopus). Read a ring
with Octopus.ring_state().

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
        self.incoming = 0.0       # current arriving from neighbouring arms over the ring; added on the NEXT step
        self.ring = None          # the Commissure this arm sits on, set by Octopus.attach; None = a lone arm

    ring_receives = True          # False: the arm sends on the ring but never takes ring current (WitnessArm)

    def sense(self, signal):
        """signal: a per-neuron list (len n), or a scalar broadcast to every neuron. Returns the spike list.
        Current that crossed the ring from a neighbour since the last step is added to every neuron (one step of
        axonal delay), then cleared. A lone arm (no ring) has none, so it behaves exactly as before the ring."""
        if not isinstance(signal, (list, tuple)):
            signal = [signal] * len(self.neurons)
        extra, self.incoming = self.incoming, 0.0
        if extra and not _disabled():          # with the kill switch on, queued ring current is DROPPED, so turning
            # it back off cannot release excitation stored meanwhile. Clamped again ON ARRIVAL against the thresholds
            # as they are now, in case one was lowered after the current was sent.
            extra = min(extra, 2.0 * Commissure.SUBCRITICAL * min((nu.thresh for nu in self.neurons), default=1.0))
            signal = [s + extra for s in signal]
        self.last = [nu.step(s) for nu, s in zip(self.neurons, signal)]
        if self.ring is not None:
            self.ring.relax()
            if any(self.last):
                self.ring.carry(self)
        return self.last

    def rate(self):
        return sum(self.last) / max(1, len(self.neurons))


class WitnessArm(Arm):
    """Fires on a BURST of node activity. Feed it an event strength in [0,1] per observation (e.g. 1.0 for a gate
    verdict). LIF leak makes it respond to the RATE of events, not the running count -- a few events spread out
    never cross threshold; a burst does. A different mechanism from the counters that watch the same stream."""

    name = "witness"
    ring_receives = False         # on a ring it sends, never receives: a recruited spike is not an attestation

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


class Commissure:
    """The interbrachial ring: arm to arm, without the brain.

    In an octopus the arms' nerve cords are joined by a ring (the interbrachial commissure) near the base, so an arm
    can recruit its neighbours directly; the central brain is not on that path. Here the arms sit on a ring in the
    order they were attached, and an arm that SPIKES sends current to its two neighbours only:

      - event-driven: an arm that did not spike sends nothing, so a quiet octopus costs nothing on the ring;
      - local: two neighbours, not every arm (O(arms) per spike, not O(arms^2)), as in the animal;
      - delayed: the current is added on the neighbour's next sense() call, never inside the sender's. There is no
        global clock: if a caller steps arms a, b, c in that order, a spike in a reaches b within the same sweep.
        Extinction does not depend on the delay; it rests on the charge argument below;
      - subcritical: the current is weight x serotonin gain x the sender's spike FRACTION (k of its n neurons), with
        weight x gain held under SUBCRITICAL x the receiver's threshold. THE CHARGE ARGUMENT, per arm: let each arm's
        charge be the AVERAGE of its neurons' POSITIVE potentials, max(v, 0), in units of its own (lowest) threshold
        (positive part: the leak, pulling toward 0, never raises it; it holds only for arms join() accepts -- leak
        toward 0, reset <= 0, finite threshold > 0, and queued current counted as charge on its way). A spike with fraction
        r = k/n lowers the sender's average by at least r (k neurons reset to 0 from at least a threshold) and raises
        each of its two neighbours' averages by at most 0.475 x r, whatever their size. So every spike lowers the sum
        over arms by at least 0.05 x r; the leak only lowers it more. Once outside drive stops, only finitely many
        spikes can follow -- whatever the phases, arm sizes, stepping order, or leak (it holds with no leak at all).
        It rests on the spike fraction: an arm-level spike that sent 0.475 to every neuron regardless of how many of
        the sender's neurons fired would break it. (Restated 2026-11-07: a first version summed over receiving
        neurons, which is wrong when arms differ in size.) Recruitment needs a neighbour that keeps firing.
        Thresholds are read at SEND time and the current is clamped again on ARRIVAL, so the bound holds against
        the thresholds as they are; it can lapse only if a threshold is lowered in the single step between a send
        and its arrival, and the arrival clamp then still caps that step at 0.95 x the new threshold.
        PRECONDITION, stated 2026-11-07 at Codex's checkpoint ("enforce fixed thresholds while attached or state the
        precondition"): lowering a threshold raises an arm's charge in its own units, so it is outside drive too.
        Thresholds lowered 10% every step keep a ringed pair firing at a steady rate with no input at all (OCR15);
        the finite count above starts from the last threshold change. Nothing in this module changes a threshold
        after construction.

    SEROTONIN (operator 2026-11-03, "make it like an octopus. Like serotonin"): a diffuse neuromodulator, one level for
    the whole ring (volume transmission, not a point-to-point synapse). release() raises it; it relaxes back toward
    its baseline with TIME, one ring-sweep's worth of decay spread over each arm step, whether or not anything fires
    -- so a quiet ring does not keep a released level for hours, activity cannot push a low level up, and the arms in
    one sweep see nearly the same gain. It scales how strongly arms recruit each other: low 5-HT, arms act alone;
    high 5-HT, a driven burst recruits the neighbours. A level that is not a finite number >= 0 gives no coupling.
    (First version decayed it per carried spike; Claude on claude.ai showed the three faults above, 2026-11-07.)

    The clock is ARM STEPS: an arm stepped more often, or skipped, changes how fast the level relaxes. Safety does not
    depend on serotonin at all -- the subcritical clamp applies after the gain.

    THE WITNESS ONLY SENDS. Its job is to attest real bursts of gate verdicts; a spike recruited from a neighbour would
    look the same to the brain. Arms with ring_receives = False (WitnessArm) never take ring current. Other arms DO:
    on a ring, integrate() reads a receiving arm's rate with its recruited spikes included (a reflex recruited by the
    witness reads as novelty). Anything that acts on such a rate should know that.

    The kill switch (Tetsu's one switch) silences the ring with the rest of the nervous system, and queued current
    is dropped while it is on."""

    GAIN_MAX = 3.0
    SUBCRITICAL = 0.475     # x threshold, per neighbour: two neighbours together stay under one threshold (0.95)

    def __init__(self, weight=0.15, baseline=1.0, decay=0.9):
        for label, x in (("weight", weight), ("baseline", baseline), ("decay", decay)):
            if not (math.isfinite(float(x)) and float(x) >= 0):
                raise ValueError("ring: %s must be a finite number >= 0, got %r" % (label, x))
        if float(decay) > 1.0:
            raise ValueError("ring: serotonin decay must be <= 1, got %r" % (decay,))
        self.order = []                 # arm names around the ring, in attach order
        self.arms = {}
        self.weight = float(weight)
        self.baseline = float(baseline)
        self.serotonin = float(baseline)
        self.decay = float(decay)       # per full sweep of the ring (every arm stepped once)
        self._relax = self.decay        # per ARM step: decay ** (1 / arms), set as arms join
        self.carried = 0                # spikes events carried, for the brain to read
        self._nb = {}                   # neighbour cache, cleared whenever an arm joins

    def join(self, arm):
        """Put an arm on the ring. REFUSES (ValueError) an arm the charge argument does not cover: every neuron must
        have a finite threshold > 0, a finite tau > 0 (a leak toward 0, never a refill), and reset <= 0 (a reset above
        0 returns charge the argument counts as spent). Claude on claude.ai's second review: each of these, broken,
        reintroduces a runaway with every clamp in place. Nothing in this module adapts thresholds at runtime."""
        for nu in arm.neurons:
            th, dec, rs = getattr(nu, "thresh", None), getattr(nu, "decay", None), getattr(nu, "reset", None)
            if not (isinstance(th, float) and math.isfinite(th) and th > 0):
                raise ValueError("ring: arm %r has a threshold that is not a finite number > 0: %r" % (arm.name, th))
            if not (isinstance(dec, float) and 0.0 <= dec <= 1.0):
                raise ValueError("ring: arm %r has a leak that does not pull toward 0 (decay %r)" % (arm.name, dec))
            if not (isinstance(rs, float) and rs <= 0.0):
                raise ValueError("ring: arm %r resets above 0 (%r); the charge argument needs reset <= 0" % (arm.name, rs))
        if arm.name not in self.arms:
            self.order.append(arm.name)
        self.arms[arm.name] = arm
        arm.ring = self
        arm.ring_thresh = min((nu.thresh for nu in arm.neurons), default=1.0)   # join-time value, for readers only;
        #                                                                        carry() reads thresholds live
        self._nb = {}                                                          # the ring changed: neighbours afresh
        self._relax = self.decay ** (1.0 / len(self.order))

    def release(self, amount):
        """Serotonin release: raise the diffuse level (negative amounts lower it; it never goes below 0)."""
        self.serotonin = max(0.0, self.serotonin + float(amount))

    def relax(self):
        """One arm step of time: the level relaxes toward baseline whether or not anything fired."""
        s = self.serotonin
        if s == s and abs(s) != math.inf:          # leave a bad value for gain() to refuse, never propagate it
            self.serotonin = self.baseline + (s - self.baseline) * self._relax

    def gain(self):
        """min(GAIN_MAX, level); a level that is not a finite number >= 0 (NaN, inf, negative) gives NO coupling.
        (min(3, nan) is 3 in Python: without this check a NaN level would mean full gain.)"""
        s = self.serotonin
        if not (s >= 0.0) or s == math.inf:
            return 0.0
        return min(self.GAIN_MAX, s)

    def neighbours(self, name):
        hit = self._nb.get(name)
        if hit is not None:
            return hit
        n = len(self.order)
        if n < 2 or name not in self.arms:
            return []
        i = self.order.index(name)
        hit = self._nb[name] = sorted({self.order[(i - 1) % n], self.order[(i + 1) % n]} - {name})
        return hit

    def carry(self, arm):
        """Called by an arm that just spiked: its spike fraction crosses to its neighbours as next-step current."""
        if _disabled():
            return
        coupling = self.weight * self.gain()
        if coupling > 0 and arm.rate() > 0:
            for nb in self.neighbours(arm.name):
                tgt = self.arms[nb]
                if not tgt.ring_receives:                # the witness attests real bursts only; it takes no current
                    continue
                thresh = min((nu.thresh for nu in tgt.neurons), default=1.0)   # as it is NOW (ChatGPT's review:
                # a join-time cache let a threshold lowered at runtime outrun the per-spike bound)
                # SUBCRITICAL, structurally: weight x gain is held under SUBCRITICAL x the receiver's threshold, so
                # one spike's total ring input over BOTH neighbours stays below what a spike costs (a reset from
                # threshold). Every spike then loses charge, and ring activity dies out unless an arm is driven from
                # outside. Measured before this clamp: with serotonin pinned high the ring reverberated forever
                # (every arm firing every step, 2400 spikes in steps 300-400 after the drive had stopped).
                current = min(coupling, self.SUBCRITICAL * thresh) * arm.rate()
                # an arm that is never stepped (the gate path drives only the witness) cannot pile up current to
                # dump all at once on its next step: what waits is capped at both neighbours' worth
                tgt.incoming = min(2.0 * self.SUBCRITICAL * thresh, tgt.incoming + current)
            self.carried += 1


class Octopus:
    """The central brain: holds the arms, reads their firing rates. Arms run autonomously; the brain integrates.
    Pass ring=Commissure() to join the arms arm to arm as well; without it (the default) they meet only here.

    OPT-IN, by Tetsu's NO (2026-11-07, ops/tetsu_consent.jsonl kind octopus_ring_consent): asked whether the ring could
    join his arms, he answered "NO ... I prefer the current setup". default_octopus() -- the node's arms, his reflex
    among them -- therefore stays brain-only, exactly as before. A caller that wants the ring constructs it."""

    def __init__(self, ring=None):
        self.arms = {}
        self.ring = ring

    def attach(self, arm):
        self.arms[arm.name] = arm
        if self.ring is not None:
            self.ring.join(arm)
        return arm

    def ring_state(self):
        """The ring as the brain sees it, without routing anything: order, serotonin, gain, spikes carried.
        {} when there is no ring or the kill switch is on."""
        if _disabled() or self.ring is None:
            return {}
        r = self.ring
        return {"order": list(r.order), "serotonin": round(r.serotonin, 4), "gain": round(r.gain(), 4),
                "carried": r.carried}

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
