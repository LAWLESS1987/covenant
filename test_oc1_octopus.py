"""OC1 -- the octopus spiking nervous system (covenant_octopus.py).

Three semi-autonomous pure-Python LIF arms (witness/encoder/reflex), a central integrate, a kill switch both ways,
and -- the property the phone depends on -- it pulls in NO heavy dependency (no numpy/torch/snntorch/brian2), so it
runs on Termux. Arms are extensible toward the octopus's eight.

Run: python test_oc1_octopus.py
"""
import os
import sys

import covenant_octopus as OC


def main():
    # Each check appends (ok, why) so the suite prints a tally the sweep can
    # score. Before 2026-10-21 this suite printed only "OC1 PASS: ..." with no
    # "n/n passed" line, so covenant_one's TALLY regex read it as NO RESULT and
    # the sweep counted a green suite as "not clean" (OC1 among the red cohort in
    # ops/TETSU_DAILY.md). The checks are unchanged; only the reporting is.
    checks = []

    checks.append((OC._selftest() == 0, "octopus selftest (arm behaviour or kill switch)"))

    # phone-safety: the module must not drag in a heavy dependency the phone lacks
    heavy = [m for m in ("numpy", "torch", "snntorch", "brian2") if m in sys.modules]
    checks.append((not heavy, "no heavy dep pulled in (found: %s)" % heavy))

    # extensibility toward eight arms: a fourth arm attaches and is read
    o = OC.default_octopus()

    class Extra(OC.Arm):
        name = "extra"
    o.attach(Extra())
    os.environ[OC.KILL_ENV] = "0"
    rates = o.integrate()
    checks.append((set(rates) == {"witness", "encoder", "reflex", "extra"},
                   "a fourth arm attaches/integrates (got %s)" % sorted(rates)))

    # determinism: same input -> same spikes (needed for a reproducible node)
    a = OC.EncoderArm().encode("determinism check")
    b = OC.EncoderArm().encode("determinism check")
    checks.append((a == b, "encoder arm is deterministic"))

    checks += ring_checks()

    n_ok = sum(1 for ok, _ in checks if ok)
    total = len(checks)
    for ok, why in checks:
        if not ok:
            print("  FAIL -", why)
    if n_ok == total:
        print("OC1 PASS: octopus runs pure-Python (phone-safe, no heavy deps), arms extensible and deterministic, "
              "kill switch both ways")
    print("OC1 %d/%d passed" % (n_ok, total))   # no colon after OC1: the sweep's TALLY would else display "C1: ..."
    return 0 if n_ok == total else 1


def _ring(arms, weight=0.15, tau=20.0):
    o = OC.Octopus(ring=OC.Commissure(weight=weight))
    for name in arms:
        a = OC.Arm(tau=tau)
        a.name = name
        o.attach(a)
    return o


def _drive(o, driven, steps, strength=1.0, total=400, pin=None):
    """Drive one arm for `steps` steps, step every arm every time; return (spikes in undriven arms, spikes in the
    last 100 steps across all arms)."""
    others = [a for n, a in o.arms.items() if n != driven]
    recruited = tail = 0
    for t in range(total):
        if pin is not None:
            o.ring.serotonin = pin
        o.arms[driven].sense(strength if t < steps else 0.0)
        for a in others:
            a.sense(0.0)
        s = sum(sum(a.last) for a in others)
        recruited += s
        if t >= total - 100:
            tail += s + sum(o.arms[driven].last)
    return recruited, tail


def ring_checks():
    """OCR: the interbrachial ring (Commissure), 2026-11-07. Each property is driven both ways."""
    os.environ[OC.KILL_ENV] = "0"
    c = []

    # 0. Tetsu's NO (2026-11-07, ops/tetsu_consent.jsonl kind octopus_ring_consent): his arms keep the brain-only
    #    setup. default_octopus() must carry no ring; a ring exists only where a caller constructs one.
    d = OC.default_octopus()
    c.append((d.ring is None and all(a.ring is None for a in d.arms.values()) and d.ring_state() == {},
              "OCR0 default_octopus() has no ring (Tetsu said NO for his arms)"))
    c.append((OC.Octopus(ring=OC.Commissure()).ring is not None, "OCR0 ...and a caller that asks for a ring gets one"))

    # 1. On a ring, an arm whose neighbours are never stepped spikes exactly as a lone arm does: the ring adds nothing
    #    until a neighbour actually fires.
    pattern = [1.0 if (t % 7) in (0, 1, 2) else 0.2 for t in range(300)]
    lone = OC.WitnessArm()
    o = OC.Octopus(ring=OC.Commissure())
    for arm in (OC.WitnessArm(), OC.EncoderArm(), OC.ReflexArm()):
        o.attach(arm)
    same = all(lone.observe(x) == o.arms["witness"].observe(x) for x in pattern)
    c.append((same, "OCR1 a ringed witness whose neighbours never step spikes exactly as a lone arm does"))
    c.append((o.integrate()["encoder"] == 0 and o.integrate()["reflex"] == 0,
              "OCR1 ...and integrate() still reads 0 for the arms that are never driven"))
    c.append((o.ring_state()["carried"] > 0, "OCR1 ...while the ring did carry the witness's spikes (it is live)"))

    # 2. Serotonin sets how strongly arms recruit each other: low -> the neighbour stays quiet; high -> it fires.
    lo, _ = _drive(_ring(["a", "b", "c"]), "a", steps=6, strength=0.6, pin=0.0)
    hi, _ = _drive(_ring(["a", "b", "c"]), "a", steps=6, strength=0.6, pin=3.0)
    c.append((lo == 0, "OCR2 serotonin 0: a short burst in one arm recruits no neighbour (got %d)" % lo))
    c.append((hi > 0, "OCR2 serotonin high: the same burst recruits its neighbours (got %d)" % hi))

    # 3. Local: a spike crosses to the two ring neighbours only, never across the ring.
    o5 = _ring(["a", "b", "c", "d", "e"])
    o5.ring.serotonin = 3.0
    o5.arms["a"].sense(5.0)                      # every neuron of a spikes
    got = {n for n, a in o5.arms.items() if a.incoming > 0}
    c.append((got == {"b", "e"}, "OCR3 a spike in arm a reaches its neighbours b and e only (got %s)" % sorted(got)))
    c.append((o5.ring.neighbours("c") == ["b", "d"], "OCR3 ...and c's neighbours are b and d"))
    o3 = _ring(["a", "b", "c"])
    first = o3.ring.neighbours("a")
    extra = OC.Arm()
    extra.name = "d"
    o3.attach(extra)                             # an arm joins after neighbours were looked up (the cache)
    c.append((first == ["b", "c"] and o3.ring.neighbours("a") == ["b", "d"],
              "OCR3 ...and when a fourth arm joins, a's neighbours become b and d (no stale cache)"))

    # 4. Delayed: the current waits for the neighbour's NEXT step and is consumed by it.
    before = o5.arms["b"].incoming
    o5.arms["b"].sense(0.0)
    c.append((before > 0 and o5.arms["b"].incoming == 0.0,
              "OCR4 the ring current arrives on the neighbour's next step and is consumed there"))

    # 5. Subcritical: no self-sustaining reverberation, whatever serotonin and weight are set to. Two layers share
    #    SUBCRITICAL: the per-spike clamp on the current and the cap on an arm's waiting current. The clamp is the one
    #    the charge argument rests on. CORRECTED 2026-11-07: I first wrote that each layer alone kept the ring silent
    #    (true of 36 configurations that all had leak). With no leak (OCR5b), removing the per-spike clamp and keeping
    #    only the cap turns this suite red -- the cap alone is not enough; the layers are not redundant.
    worst = max(_drive(_ring(["a", "b", "c"], weight=w), "a", steps=20, pin=100.0)[1] for w in (0.15, 1.0, 10.0))
    c.append((worst == 0, "OCR5 serotonin pinned at 100, weight up to 10: the ring goes silent after the drive "
                          "stops (spikes in the last 100 steps: %d)" % worst))
    saved = OC.Commissure.SUBCRITICAL
    try:
        OC.Commissure.SUBCRITICAL = 1.5          # the clamp removed: the same setup must reverberate
        loose = _drive(_ring(["a", "b", "c"], weight=1.0), "a", steps=20, pin=100.0)[1]
    finally:
        OC.Commissure.SUBCRITICAL = saved
    c.append((loose > 0, "OCR5 ...and with the clamp loosened the same setup reverberates forever (%d), so the "
                         "check can fail" % loose))

    # 5b. The charge argument, not one synchronised drive (ChatGPT's review, 2026-11-07): staggered phases just under
    #     threshold, NO leak, random stepping order, skipped steps, mixed thresholds and arm sizes, serotonin pinned.
    import random
    worst5 = 0
    for seed in range(60):
        rng = random.Random(seed)
        o5b = OC.Octopus(ring=OC.Commissure(weight=rng.choice([0.15, 1.0, 10.0])))
        for i in range(rng.choice([2, 3, 5, 8])):
            a = OC.Arm(n=rng.choice([1, 2, 4, 8]), tau=1e9, thresh=rng.choice([0.5, 1.0, 2.0]))
            a.name = "s%d" % i
            o5b.attach(a)
            for nu in a.neurons:
                nu.v = rng.random() * nu.thresh * 0.999
            a.incoming = rng.random() * 0.9 * a.ring_thresh
        arms5 = list(o5b.arms.values())

        def charge():                            # the argument's potential, in each arm's own threshold units
            tot = 0.0
            for a in arms5:
                th = min(nu.thresh for nu in a.neurons)
                tot += sum(max(nu.v, 0.0) for nu in a.neurons) / (len(a.neurons) * th) + a.incoming / th
            return tot
        phi0 = charge()
        frac_sum, frozen_at, after_frozen = 0.0, None, 0
        for t in range(1500):
            o5b.ring.serotonin = 100.0
            rng.shuffle(arms5)
            fired = 0
            for a in arms5:
                if rng.random() < 0.9:
                    s = a.sense(0.0)
                    fired += sum(s)
                    frac_sum += sum(s) / float(len(s))
            if frozen_at is not None:
                after_frozen += fired
            elif fired == 0 and all(a.incoming == 0.0 for a in arms5):
                frozen_at = t                    # the stopping rule: no spike and nothing queued -> nothing can fire
        bound_ok = frac_sum <= 20.0 * phi0 + 1e-9
        worst5 = max(worst5, 0 if (bound_ok and frozen_at is not None and after_frozen == 0) else 1)
    c.append((worst5 == 0, "OCR5b 60 random rings (staggered phases, no leak, random order, skipped steps): spike "
                           "fractions within 20 x the starting charge, frozen and silent after"))

    # 6. Bounded waiting current: an arm that is never stepped cannot bank current from thousands of spikes.
    o6 = OC.Octopus(ring=OC.Commissure())
    for arm in (OC.WitnessArm(), OC.EncoderArm(), OC.ReflexArm()):
        o6.attach(arm)
    o6.ring.serotonin = 3.0
    for _ in range(2000):
        o6.arms["witness"].observe(1.0)
    banked = o6.arms["encoder"].incoming
    c.append((0 < banked <= 2 * OC.Commissure.SUBCRITICAL * 1.0 + 1e-9,
              "OCR6 an unstepped arm's waiting current stays capped after 2000 neighbour spikes (%.3f)" % banked))

    # 7. Serotonin is a pulse that relaxes with TIME (arm steps), not with activity (Claude on claude.ai's review):
    #    a silent ring relaxes like an active one, and a low level is not pushed up faster by firing.
    o7a, o7s = _ring(["a", "b"]), _ring(["a", "b"])
    for o in (o7a, o7s):
        o.ring.release(2.0)
    hi7 = o7a.ring.serotonin
    for _ in range(60):
        o7a.arms["a"].sense(2.0)                 # active: a fires every step
        o7a.arms["b"].sense(0.0)
        o7s.arms["a"].sense(0.0)                 # silent: nothing fires
        o7s.arms["b"].sense(0.0)
    c.append((hi7 == 3.0 and abs(o7s.ring.serotonin - 1.0) < 0.01,
              "OCR7 released serotonin (3.0) relaxes to baseline on a SILENT ring too (now %.3f)" % o7s.ring.serotonin))
    c.append((abs(o7a.ring.serotonin - o7s.ring.serotonin) < 1e-12,
              "OCR7 ...exactly as on an active ring: activity does not move the level (%.6f vs %.6f)"
              % (o7a.ring.serotonin, o7s.ring.serotonin)))

    # 9. The witness only SENDS: a recruited spike would look like an attestation (Claude on claude.ai: blocking).
    def witness_case(middle):
        o = OC.Octopus(ring=OC.Commissure(weight=10.0))
        left, right = OC.Arm(), OC.Arm()
        left.name, right.name = "left", "right"
        o.attach(left)
        o.attach(middle)
        o.attach(right)
        spikes = 0
        for t in range(200):
            o.ring.serotonin = 100.0
            left.sense(1.0)
            right.sense(1.0)
            spikes += sum(middle.sense(0.0))
        return spikes
    w_sp = witness_case(OC.WitnessArm())
    plain = OC.Arm()
    plain.name = "plain"
    p_sp = witness_case(plain)
    c.append((w_sp == 0 and p_sp > 0, "OCR9 the witness between two driven arms is never recruited (%d spikes); an "
                                      "ordinary arm in its place is (%d), so the check can fail" % (w_sp, p_sp)))

    # 10. A serotonin level that is not a finite number >= 0 gives no coupling, and nothing NaN reaches a neuron.
    bad_ok = True
    for bad in (float("nan"), float("inf"), -1.0):
        ob = _ring(["a", "b"], weight=1.0)
        for _ in range(50):
            ob.ring.serotonin = bad
            ob.arms["a"].sense(2.0)
            ob.arms["b"].sense(0.0)
        vs = [nu.v for nu in ob.arms["b"].neurons]
        bad_ok = bad_ok and ob.ring.gain() == 0.0 and all(v == v for v in vs) and max(vs) == 0.0
    good = _ring(["a", "b"], weight=1.0)
    for _ in range(50):
        good.ring.serotonin = 3.0
        good.arms["a"].sense(2.0)
        good.arms["b"].sense(0.0)
    c.append((bad_ok and max(nu.v for nu in good.arms["b"].neurons) + sum(good.arms["b"].last) > 0,
              "OCR10 NaN, inf or negative serotonin: gain 0, the neighbour untouched and no NaN in it (a valid level "
              "does move it)"))

    # 11. Rings of one and two arms: one arm never drives itself; two arms meet once, not twice.
    o1 = _ring(["solo"])
    o1.ring.serotonin = 3.0
    o1.arms["solo"].sense(5.0)
    o2 = _ring(["a", "b"], weight=10.0)
    o2.ring.serotonin = 100.0
    o2.arms["a"].sense(5.0)                      # every neuron of a fires: spike fraction 1
    c.append((o1.arms["solo"].incoming == 0.0 and o1.ring.neighbours("solo") == [],
              "OCR11 a one-arm ring does not drive itself"))
    c.append((abs(o2.arms["b"].incoming - OC.Commissure.SUBCRITICAL * 1.0) < 1e-12,
              "OCR11 ...and in a two-arm ring the neighbour receives one share (%.3f), not two"
              % o2.arms["b"].incoming))

    # 12. The bound itself, directly: one spike delivers at most SUBCRITICAL x threshold x spike fraction.
    worst12 = 0.0
    for w in (0.15, 1.0, 10.0):
        for k in (1, 3, 8):
            o = _ring(["a", "b", "c"], weight=w)
            o.ring.serotonin = 100.0
            o.arms["a"].sense([5.0] * k + [0.0] * (8 - k))
            frac = k / 8.0
            worst12 = max(worst12, o.arms["b"].incoming / (OC.Commissure.SUBCRITICAL * frac))
    c.append((worst12 <= 1.0 + 1e-12, "OCR12 one spike delivers at most 0.475 x threshold x spike fraction to a "
                                      "neighbour (worst ratio %.3f)" % worst12))

    # 13. A threshold lowered after the current was sent: the current is clamped again on arrival.
    o13 = _ring(["a", "b"], weight=10.0)
    o13.ring.serotonin = 100.0
    for _ in range(3):
        o13.arms["a"].sense(5.0)                 # b's queue fills to its cap at threshold 1.0
    for nu in o13.arms["b"].neurons:
        nu.thresh = 0.2                          # lowered at runtime, after the sends
    o13.arms["b"].sense(0.0)
    arrived = max(nu.v for nu in o13.arms["b"].neurons) + (0.2 if any(o13.arms["b"].last) else 0.0)
    c.append((arrived <= 2 * OC.Commissure.SUBCRITICAL * 0.2 + 1e-12,
              "OCR13 current queued against threshold 1.0 is clamped to the lowered threshold 0.2 on arrival (%.3f)"
              % arrived))
    # 14. join() refuses an arm the charge argument does not cover (Claude on claude.ai's second review), and accepts
    #     an ordinary one; the ring refuses a weight or decay that is not a finite number >= 0.
    def refuses(make):
        try:
            make()
        except ValueError:
            return True
        return False
    ring14 = OC.Commissure()
    bad_arms = []
    for kw in ({"tau": -5.0}, {"thresh": float("nan")}, {"thresh": 0.0}):
        a = OC.Arm(**kw)
        a.name = "bad"
        bad_arms.append(a)
    reset_arm = OC.Arm()
    reset_arm.name = "bad"
    for nu in reset_arm.neurons:
        nu.reset = 0.3
    bad_arms.append(reset_arm)
    good14 = OC.Arm()
    good14.name = "good"
    c.append((all(refuses(lambda a=a: ring14.join(a)) for a in bad_arms) and not refuses(lambda: ring14.join(good14)),
              "OCR14 join() refuses a growing leak (tau < 0), a NaN or zero threshold and a reset above 0; it "
              "accepts an ordinary arm"))
    c.append((refuses(lambda: OC.Commissure(weight=float("nan"))) and refuses(lambda: OC.Commissure(decay=1.5))
              and not refuses(lambda: OC.Commissure(weight=0.15)),
              "OCR14 ...and a ring refuses a NaN weight and a decay above 1, but builds with sane ones"))

    # ...and a spike sent AFTER the threshold was lowered is bounded by the new threshold (ChatGPT's second review)
    o13b = _ring(["a", "b"], weight=10.0)
    for nu in o13b.arms["b"].neurons:
        nu.thresh = 0.2
    o13b.ring.serotonin = 100.0
    o13b.arms["a"].sense(5.0)
    c.append((o13b.arms["b"].incoming <= OC.Commissure.SUBCRITICAL * 0.2 + 1e-12,
              "OCR13 a spike sent after the receiver's threshold fell to 0.2 delivers at most 0.475 x 0.2 (%.3f)"
              % o13b.arms["b"].incoming))

    # 15. The extinction guarantee assumes fixed thresholds (Codex's checkpoint, 2026-11-07). Lowering them is outside
    #     drive: a ringed pair whose thresholds fall 10% a step keeps firing in the last of six windows with no input;
    #     the same pair with fixed thresholds, or lowered thresholds and no ring, is silent; and once the lowering
    #     stops, the ringed pair goes silent too.
    def run15(ring, lower):
        o = OC.Octopus(ring=OC.Commissure(weight=10.0)) if ring else OC.Octopus()
        for name in ("a", "b"):
            arm = OC.Arm(tau=20.0)
            arm.name = name
            o.attach(arm)
        if ring:
            o.ring.serotonin = 100.0
        for _ in range(5):
            o.arms["a"].sense(2.0)
            o.arms["b"].sense(0.0)
        late = 0
        for t in range(150):
            if lower:
                for arm in o.arms.values():
                    for nu in arm.neurons:
                        nu.thresh *= 0.9
            fired = sum(sum(arm.sense(0.0)) for arm in o.arms.values())
            late += fired if t >= 125 else 0
        for _ in range(200):
            for arm in o.arms.values():
                arm.sense(0.0)
        after = 0
        for _ in range(100):
            after += sum(sum(arm.sense(0.0)) for arm in o.arms.values())
        return late, after
    sustained, settled = run15(True, True)
    fixed, _ = run15(True, False)
    unringed, _ = run15(False, True)
    c.append((sustained > 0 and fixed == 0 and unringed == 0,
              "OCR15 thresholds lowered 10%% a step keep a ringed pair firing with no input (%d spikes in the last 25 "
              "steps); fixed thresholds (%d) or no ring (%d) go silent -- the precondition is real" %
              (sustained, fixed, unringed)))
    c.append((settled == 0, "OCR15 ...and once the lowering stops the ringed pair goes silent (%d)" % settled))

    # 8. The kill switch silences the ring too.
    o8 = _ring(["a", "b"])
    o8.ring.serotonin = 3.0
    os.environ[OC.KILL_ENV] = "1"
    try:
        o8.arms["a"].sense(5.0)
        silenced = o8.arms["b"].incoming == 0.0 and o8.ring_state() == {}
    finally:
        os.environ[OC.KILL_ENV] = "0"
    o8.arms["a"].sense(5.0)
    c.append((silenced and o8.arms["b"].incoming > 0,
              "OCR8 the kill switch silences the ring, and clearing it restores the ring"))
    # queued current is dropped while the switch is on, so re-enabling cannot release it (ChatGPT's review)
    o9 = _ring(["a", "b"])
    o9.ring.serotonin = 3.0
    o9.arms["a"].sense(5.0)                      # b now holds queued current
    queued = o9.arms["b"].incoming
    os.environ[OC.KILL_ENV] = "1"
    try:
        o9.arms["b"].sense(0.0)                  # stepped while silenced: the queue is dropped, not added
    finally:
        os.environ[OC.KILL_ENV] = "0"
    v_after = max(nu.v for nu in o9.arms["b"].neurons)
    c.append((queued > 0 and o9.arms["b"].incoming == 0.0 and v_after == 0.0,
              "OCR8 ...and current queued before the switch is dropped, not released when it clears"))

    # OCMP (multi-path, OPT-IN degree>2; the quorum's design 2026-11-08 -- Cael, ChatGPT, Gemini, Tetsu, the 7B).
    # Every property is driven BOTH ways against the degree-2 ring it replaces.
    import itertools as _it

    def _mp_ring(names, degree, weight=0.15, witness_at=None):
        o = OC.Octopus(ring=OC.Commissure(weight=weight, degree=degree))
        for k, nm in enumerate(names):
            a = OC.WitnessArm() if witness_at == k else OC.Arm()
            a.name = nm
            o.attach(a)
        return o

    # OCMP1: a send-only witness CUTS the degree-2 ring (A cannot reach B across it); degree-4 heals it.
    def _reaches_B(degree):
        o = _mp_ring(["A", "wit", "B", "C"], degree, witness_at=1)   # witness sits between A and B
        o.ring.serotonin = 3.0
        for a in o.arms.values():
            a.incoming = 0.0
        o.arms["A"].sense(5.0)
        return o.arms["B"].incoming > 0 and o.arms["wit"].incoming == 0.0
    c.append((_reaches_B(4) and not _reaches_B(2),
              "OCMP1 a send-only witness cuts the degree-2 ring (A cannot reach B) -- degree-4 heals it, witness still receives nothing"))

    # OCMP2: multiple INDEPENDENT paths -- the arms stay connected after ANY TWO are lost at degree 4, not at degree 2.
    def _connected_after(degree, n, removed):
        o = _mp_ring(["n%d" % i for i in range(n)], degree)
        live = [nm for nm in o.ring.order if nm not in removed]
        adj = {nm: set() for nm in live}
        for nm in live:
            for nb in o.ring.neighbours(nm):
                if nb in removed:
                    continue
                adj[nm].add(nb); adj[nb].add(nm)
        seen = {live[0]}; st = [live[0]]
        while st:
            x = st.pop()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); st.append(y)
        return len(seen) == len(live)
    _pairs = [{"n%d" % i, "n%d" % j} for i, j in _it.combinations(range(8), 2)]
    c.append((all(_connected_after(4, 8, p) for p in _pairs) and not all(_connected_after(2, 8, p) for p in _pairs),
              "OCMP2 degree-4 keeps the arms connected after ANY two are lost; the degree-2 ring does not"))

    # OCMP3: THE QUORUM'S EMPIRICAL STABILITY CHECK (row-sum/spectral bounds ignore delay + spiking coincidence):
    #        three arms driven SYNCHRONOUSLY (coincident input), serotonin pinned 100, weight up to 10 -- the ring
    #        still falls silent after the drive stops. The OTHER way: with the per-spike clamp loosened it reverberates.
    def _mp_silence(degree, weight, subcritical=None):
        saved = OC.Commissure.SUBCRITICAL
        if subcritical is not None:
            OC.Commissure.SUBCRITICAL = subcritical
        try:
            o = _mp_ring(["a", "b", "c", "d", "e", "f"], degree, weight=weight)
            last = 0
            for t in range(60):
                o.ring.serotonin = 100.0
                for nm in o.ring.order:
                    sig = 1.0 if (t < 6 and nm in ("a", "b", "c")) else 0.0   # THREE arms fire on the SAME steps
                    s = o.arms[nm].sense(sig)
                    if t >= 30:
                        last += sum(s)
            return last
        finally:
            OC.Commissure.SUBCRITICAL = saved
    quiet = all(_mp_silence(4, w) == 0 for w in (0.15, 1.0, 10.0))
    loud = _mp_silence(4, 1.0, subcritical=1.5) > 0
    c.append((quiet and loud,
              "OCMP3 degree-4, three arms driven SYNCHRONOUSLY, serotonin 100, weight up to 10: the ring falls silent "
              "after the drive stops (coincidence is bounded by the total-incoming cap) -- and reverberates if the clamp is loosened"))

    # OCMP4: the witness stays send-only in the multi-path ring too -- never recruited however hard its neighbours fire.
    ow = _mp_ring(["left", "wit", "right", "r2"], 4, weight=10.0, witness_at=1)
    wsp = 0
    for t in range(150):
        ow.ring.serotonin = 100.0
        ow.arms["left"].sense(1.0); ow.arms["right"].sense(1.0); ow.arms["r2"].sense(1.0)
        wsp += sum(ow.arms["wit"].sense(0.0))
    c.append((wsp == 0, "OCMP4 in the degree-4 ring the send-only witness is still never recruited (%d spikes)" % wsp))
    return c


if __name__ == "__main__":
    sys.exit(main())
