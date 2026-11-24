#!/usr/bin/env python3
"""SNB1 -- A483: the octopus's neurons compute on pure Python, numpy (CPU) or the GPU, chosen by size, with the SAME
spikes and voltages on every backend. Driven both ways (rule 8).

What runs everywhere: the choice rule, the phone-safe default (no backend module, numpy or torch imported for the
default arms, Tetsu's among them), and the hand-back to pure Python. What needs numpy or a CUDA GPU (equivalence,
fallback mid-run, the breaks): each is reported NOT RUN, with its reason, where the library is missing -- never
counted as passed. On TETSU run it also with an interpreter that has them (the lens venv) for the full set."""
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.pop("COVENANT_SNN_BACKEND", None)

import covenant_octopus as O        # noqa: E402
import covenant_snn_backend as B    # noqa: E402

fails, notrun, n = [], [], [0]


def check(name, cond, detail=""):
    n[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:220]))
    if not cond:
        fails.append(name)


def not_run(name, why):
    print("NOT RUN " + name + " -- " + why)
    notrun.append(name)


HAS_NP = B._has_numpy()
GPU_OK, GPU_WHY = B._gpu_room(4096)

# ---- the default path stays pure Python and imports nothing heavy (the phone's path)
probe = ("import sys; sys.path.insert(0, %r); import covenant_octopus as O; o = O.default_octopus(); "
         "[a.sense(0.3) for a in o.arms.values()]; "
         "print(sorted(m for m in ('numpy', 'torch', 'covenant_snn_backend') if m in sys.modules)); "
         "print([(k, a.backend, a.pool is None) for k, a in sorted(o.arms.items())])" % HERE)
env = dict(os.environ)
env.pop("COVENANT_SNN_BACKEND", None)
out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env, timeout=120).stdout
lines = out.strip().splitlines()
check("SNB1.1 the default octopus imports neither numpy, torch nor the backend module", lines[:1] == ["[]"], out)
check("SNB1.2 every default arm (8 neurons; Tetsu's reflex among them) stays on the pure-Python neurons",
      len(lines) > 1 and "'python', True" in lines[1] and "numpy" not in lines[1] and "cuda" not in lines[1], out)

# ---- the choice rule, as measured
real_np, real_gpu = B._has_numpy, B._gpu_room
try:
    B._has_numpy = lambda: True
    B._gpu_room = lambda k: (True, "fake room")
    check("SNB1.3 below 256 neurons pure Python is chosen even with numpy and a GPU", B.choose(24)[0] == "python")
    check("SNB1.4 from 256 numpy on the CPU", B.choose(256)[0] == "numpy" and B.choose(131071)[0] == "numpy")
    check("SNB1.5 from 131,072 the GPU, when it has room", B.choose(131072)[0] == "cuda")
    B._gpu_room = lambda k: (False, "the GPU has 900 MiB free; 1024 MiB must stay free beside its models")
    c, why = B.choose(200000)
    check("SNB1.6 a GPU without room beside its models leaves a big pool on numpy, and says why",
          c == "numpy" and "must stay free" in why, (c, why))
    B._has_numpy = lambda: False
    check("SNB1.7 without numpy everything stays pure Python", B.choose(500)[0] == "python" and B.choose(200000)[0] == "python")
    check("SNB1.8 'numpy' asked for without numpy falls back to Python, saying so",
          B.choose(500, "numpy") == ("python", "numpy asked for but not installed"))
    B._has_numpy = lambda: True
    check("SNB1.9 COVENANT_SNN_BACKEND=python keeps even a huge pool on Python", B.choose(10 ** 6, "python")[0] == "python")
finally:
    B._has_numpy, B._gpu_room = real_np, real_gpu

# ---- a backend that cannot be built leaves the arm on Python (never a new failure)
real_pool = B.NeuronPool


def broken_pool(*a, **k):
    raise RuntimeError("no device")


B.NeuronPool = broken_pool
real_choose = B.choose
B.choose = lambda k, w=None: ("numpy", "forced for the test")
try:
    arm = O.Arm(n=512)
    check("SNB1.10 a pool that cannot be built leaves the arm on pure Python, with the reason",
          arm.pool is None and arm.backend == "python" and "backend unavailable" in arm.backend_why
          and len(arm.neurons) == 512 and isinstance(arm.neurons[0], O.LIF), arm.backend_why)
finally:
    B.NeuronPool, B.choose = real_pool, real_choose


# ---- equivalence, fallback and breaks: need numpy (and a GPU for the cuda lines)
def drive(arm, seed, steps=120, thresh_change=True, ring_like=True):
    rnd = random.Random(seed)
    spikes, n_ = [], len(arm.neurons)
    for t in range(steps):
        if ring_like and t % 7 == 3:
            arm.incoming = rnd.uniform(0.0, 0.5)           # current as if from a neighbour (clamped on arrival)
        if thresh_change and t == 60:
            arm.neurons[3].thresh = 0.6                    # a threshold lowered mid-run, read live (A414)
            arm.neurons[5].v = 0.95                        # a voltage written through the per-neuron view
        sig = [rnd.uniform(0.0, 0.14) for _ in range(n_)] if t % 2 else rnd.uniform(0.0, 0.12)
        spikes.append(list(arm.sense(sig)))
    return spikes, [nu.v for nu in arm.neurons]


def same(a, b):
    return a[0] == b[0] and a[1] == b[1]


backends = []
if HAS_NP:
    backends.append("numpy")
else:
    not_run("SNB1.11-SNB1.18 (numpy)", "numpy is not installed in this interpreter")
if GPU_OK:
    backends.append("cuda")
else:
    not_run("SNB1.11-SNB1.13 (cuda)", GPU_WHY)

for b in backends:
    for size in (8, 512):
        ref = drive(O.Arm(n=size, backend="python"), seed=size)
        got_arm = O.Arm(n=size, backend=b)
        got = drive(got_arm, seed=size)
        check("SNB1.11 %s, %d neurons: spikes AND voltages bit-identical to pure Python over 120 steps (ring current "
              "and a mid-run threshold change included)" % (b, size), got_arm.backend == b and same(ref, got),
              (got_arm.backend, got_arm.backend_why))
    sp = O.Arm(n=512, backend=b)
    check("SNB1.12 %s: min_thresh is read live from the pool" % b,
          sp.min_thresh() == 1.0 and (setattr(sp.neurons[7], "thresh", 0.4) or sp.min_thresh() == 0.4))
    ring = O.Octopus(ring=O.Commissure())
    ring_py = O.Octopus(ring=O.Commissure())
    for o, bk in ((ring, b), (ring_py, "python")):
        for name in ("a", "b"):
            arm_ = O.Arm(n=512, backend=bk)
            arm_.name = name
            o.attach(arm_)
    rs, rs_py = [], []
    rnd1, rnd2 = random.Random(5), random.Random(5)
    for t in range(80):
        x1 = rnd1.uniform(0, 0.15) if t < 40 else 0.0
        x2 = rnd2.uniform(0, 0.15) if t < 40 else 0.0
        rs.append(sum(ring.arms["a"].sense(x1)) + sum(ring.arms["b"].sense(0.0)))
        rs_py.append(sum(ring_py.arms["a"].sense(x2)) + sum(ring_py.arms["b"].sense(0.0)))
    check("SNB1.13 %s: two arms on the ring fire exactly as on Python, and the ring falls quiet" % b,
          rs == rs_py and sum(rs[-20:]) == 0, (rs[-10:], rs_py[-10:]))

if HAS_NP:
    # a backend that raises mid-run: the arm hands its exact state to Python and continues identically
    ref = drive(O.Arm(n=512, backend="python"), seed=11)
    arm = O.Arm(n=512, backend="numpy")
    calls = [0]
    real_step = arm.pool.step

    def flaky(sig):
        calls[0] += 1
        if calls[0] == 50:
            raise MemoryError("simulated")
        return real_step(sig)

    arm.pool.step = flaky
    got = drive(arm, seed=11)
    check("SNB1.14 a backend that raises mid-run hands its state to Python and the result is still identical",
          arm.pool is None and "fell back" in arm.backend_why and same(ref, got), arm.backend_why)
    arm = O.Arm(n=512, backend="numpy")
    arm2 = O.Arm(n=512, backend="python")
    short = [0.5] * 100
    check("SNB1.15 a signal shorter than the arm: handed back, and stepped exactly as Python's zip does",
          arm.sense(short) == arm2.sense(short) and arm.pool is None
          and [nu.v for nu in arm.neurons] == [nu.v for nu in arm2.neurons], arm.backend_why)

    # breaks: each must turn an equivalence check red
    import numpy as np
    src = B.NeuronPool.step

    def gt_step(self, signal):                                   # break 1: > instead of >=
        a = self.arr
        x = np.asarray(signal, dtype=np.float64)
        v = a["v"] * a["decay"] + x
        fired = v > a["thresh"]
        a["v"] = np.where(fired, a["reset"], v)
        return fired.astype(np.int8).tolist()

    def noreset_step(self, signal):                              # break 2: fires but never resets
        a = self.arr
        x = np.asarray(signal, dtype=np.float64)
        v = a["v"] * a["decay"] + x
        fired = v >= a["thresh"]
        a["v"] = v
        return fired.astype(np.int8).tolist()

    def fma_like(self, signal):                                  # break 3: add before decay (a different order)
        a = self.arr
        x = np.asarray(signal, dtype=np.float64)
        v = (a["v"] + x) * a["decay"]
        fired = v >= a["thresh"]
        a["v"] = np.where(fired, a["reset"], v)
        return fired.astype(np.int8).tolist()

    for label, brk in (("> for >=", gt_step), ("no reset", noreset_step),
                       ("add before decay", fma_like)):
        B.NeuronPool.step = brk
        try:
            ref = drive(O.Arm(n=512, backend="python"), seed=21, thresh_change=False, ring_like=False)
            got = drive(O.Arm(n=512, backend="numpy"), seed=21, thresh_change=False, ring_like=False)
            # equality on exactly-at-threshold values is rare with random floats, so ">" is seen through a
            # neuron set exactly at threshold
            if label == "> for >=":
                t1, t2 = O.Arm(n=512, backend="python"), O.Arm(n=512, backend="numpy")
                t1.neurons[0].v = t2.neurons[0].v = 0.0
                sig = [0.0] * 512
                sig[0] = 1.0
                diff = t1.sense(sig) != t2.sense(sig)
            else:
                diff = not same(ref, got)
            check("SNB1.16 the equivalence check is seen RED when the pool is broken (%s)" % label, diff)
        finally:
            B.NeuronPool.step = src

    real_state = B.NeuronPool.state
    B.NeuronPool.state = lambda self: [(0.0, d, t, r) for (_v, d, t, r) in real_state(self)]   # break 4
    try:
        ref = drive(O.Arm(n=512, backend="python"), seed=31)
        arm = O.Arm(n=512, backend="numpy")
        rs_ = arm.pool.step
        k = [0]

        def raise_once(sig):
            k[0] += 1
            if k[0] == 30:
                raise RuntimeError("x")
            return rs_(sig)

        arm.pool.step = raise_once
        got = drive(arm, seed=31)
        check("SNB1.17 the hand-back check is seen RED when the voltages are not carried over", not same(ref, got))
    finally:
        B.NeuronPool.state = real_state
    try:
        B.NeuronPool(4, backend="gpu")
        refused = False
    except ValueError:
        refused = True
    check("SNB1.18 a pool can only be numpy or cuda (an unknown backend name is refused)", refused)


print("\nSNB1: %d/%d passed%s" % (n[0] - len(fails), n[0],
                                  ("; NOT RUN: " + ", ".join(notrun)) if notrun else ""))
sys.exit(1 if fails else 0)
