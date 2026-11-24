#!/usr/bin/env python3
"""covenant_snn_backend.py -- where the octopus's neurons compute: the CPU in pure Python, the CPU in numpy, or the
GPU, chosen per arm by its size, with the same result on every one (A483).

HIS WORDS, 2026-11-23: "gpu and cpu should be intergrated in the snn".

MEASURED FIRST (TETSU, RTX 5060 Ti, the same leaky integrate-and-fire step as covenant_octopus.LIF, float64; the
spikes AND the voltages were bit-identical to the pure-Python reference on every backend at every size):
    neurons      pure Python    numpy (CPU)    GPU (torch, CUDA)
    8            1.1 us/step    3.4            67.5
    24           2.5            2.5            65.9      <- today's three arms of 8: Python is fastest, the GPU 26x slower
    256          21.7           3.3            69.5
    4,096        362            9.6            79.3
    65,536       5,540          107            149
    98,304       -              140            146       <- the GPU's crossover
    131,072      -              514            153
    1,048,576    -              3,939          748
So the rule is by size, not by preference: below NUMPY_MIN the pure-Python path (the phone's, and the reference);
from NUMPY_MIN numpy on the CPU; from GPU_MIN the GPU, but only when the GPU has room beside the models that live on
it (free memory after this pool must stay above GPU_HEADROOM_MIB) -- otherwise numpy. Launching work on a GPU costs
more than a small pool's arithmetic, which is why the GPU loses below the crossover.

SAME RESULT, BY CONSTRUCTION AND BY TEST. Every backend does what LIF.step does, in the same order, in float64:
v = v * decay; v = v + input (two separately rounded operations, never a fused multiply-add); fire where v >= thresh;
reset there. IEEE-754 rounds each of those exactly, so the spikes and voltages match the reference bit for bit (SNB1
checks it on every backend it can reach, and names any it cannot as NOT RUN).

NEVER A NEW FAILURE. numpy and torch are imported lazily, only when a pool is large enough to want them; a missing
library or a GPU without room simply leaves the pool on a slower backend, and a backend that raises mid-run hands
its exact state back to the pure-Python neurons (covenant_octopus.Arm does that). COVENANT_SNN_BACKEND=python|numpy|
cuda|auto overrides the choice (auto is the default). The kill switch and everything the arms decide are untouched.
LICENCE: public domain.
"""
from __future__ import annotations

import math
import os

NUMPY_MIN = 256              # measured: numpy 3.3 us vs Python 21.7 us at 256 neurons (tied at 24)
GPU_MIN = 131072             # measured: GPU 153 us vs numpy 514 us at 131,072 (tied at 98,304)
GPU_HEADROOM_MIB = 1024      # free GPU memory that must remain after a pool is placed there
ENV = "COVENANT_SNN_BACKEND"

# THE GPU LEASE (A484, his "GPU respects the lease"). On TETSU the GPU is shared through a lease file: while a lease
# is in force a training or lens job holds the GPU and the 27B is paused; with none, the 27B holds it. The spiking
# network never TAKES the lease (that would stop the 27B for a few small arms); it uses the GPU only while NO lease is
# in force, and a pool already on the GPU moves to numpy, state and all, when one is taken. The file is read the way
# the lease's own writer and TETSU's start script read it: missing = free; unreadable, or an expiry that is missing,
# not a number or not finite = in force; an expiry in the past = free. The path: COVENANT_GPU_LEASE, else
# training/gpu-lease.json beside this covenant folder (where it sits on TETSU); elsewhere that path does not exist.
LEASE_ENV = "COVENANT_GPU_LEASE"
LEASE_CHECK_S = 1.0          # a pool on the GPU looks at the lease at most this often while it steps
HERE = os.path.dirname(os.path.abspath(__file__))


class LeaseTaken(RuntimeError):
    """Raised by a GPU pool's step when a lease came into force; nothing was committed for that step."""


def lease_path():
    return os.environ.get(LEASE_ENV) or os.path.join(os.path.dirname(HERE), "training", "gpu-lease.json")


def lease_held(path=None):
    """(True, why) while a GPU lease is in force."""
    import json
    import time
    path = path or lease_path()
    try:
        with open(path, encoding="utf-8-sig") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return False, "no GPU lease"
    except (OSError, ValueError):
        return True, "the GPU lease file cannot be read, so it counts as held"
    if not isinstance(d, dict):
        return True, "the GPU lease file is not a record, so it counts as held"
    try:
        exp = float(d.get("expires"))
    except (TypeError, ValueError):
        return True, "the GPU lease has no usable expiry, so it counts as held"
    if exp != exp or exp in (float("inf"), float("-inf")):
        return True, "the GPU lease's expiry is not finite, so it counts as held"
    if exp > time.time():
        return True, "a GPU lease is in force (%s)" % str(d.get("why", "no reason given"))[:80]
    return False, "the GPU lease has expired"


def _has_numpy():
    try:
        import numpy  # noqa: F401
        return True
    except Exception:                                        # noqa: BLE001
        return False


def _gpu_room(n):
    """(True, why) when no GPU lease is in force and torch sees a CUDA GPU with room for n neurons and
    GPU_HEADROOM_MIB left over. The lease is read first, so a held lease never even loads torch."""
    held, why = lease_held()
    if held:
        return False, why
    try:
        import torch
    except Exception as e:                                   # noqa: BLE001
        return False, "no torch (%s)" % type(e).__name__
    try:
        if not torch.cuda.is_available():
            return False, "torch sees no CUDA GPU"
        free, _total = torch.cuda.mem_get_info()
    except Exception as e:                                   # noqa: BLE001
        return False, "the GPU could not be read (%s)" % type(e).__name__
    need = n * 8 * 6 + (64 << 20)                            # v, decay, thresh, reset, input, mask; plus a margin
    if free - need < GPU_HEADROOM_MIB * (1 << 20):
        return False, "the GPU has %d MiB free; %d MiB must stay free beside its models" % (free >> 20, GPU_HEADROOM_MIB)
    return True, "%d MiB free" % (free >> 20)


def choose(n, want=None):
    """(backend, why) for a pool of n neurons. want, else COVENANT_SNN_BACKEND, else 'auto'."""
    want = (want or os.environ.get(ENV) or "auto").strip().lower()
    if want == "python":
        return "python", "asked for"
    if want == "numpy":
        return ("numpy", "asked for") if _has_numpy() else ("python", "numpy asked for but not installed")
    if want == "cuda":
        ok, why = _gpu_room(n)
        if ok:
            return "cuda", "asked for; " + why
        return ("numpy", "cuda asked for but " + why) if _has_numpy() else ("python", "cuda asked for but " + why)
    if n < NUMPY_MIN:
        return "python", "%d neurons < %d: pure Python is fastest here" % (n, NUMPY_MIN)
    if n >= GPU_MIN:
        ok, why = _gpu_room(n)
        if ok:
            return "cuda", "%d neurons >= %d and %s" % (n, GPU_MIN, why)
        if _has_numpy():
            return "numpy", "%d neurons >= %d but %s" % (n, GPU_MIN, why)
        return "python", "no numpy, and " + why
    if _has_numpy():
        return "numpy", "%d neurons, between %d and %d" % (n, NUMPY_MIN, GPU_MIN)
    return "python", "numpy is not installed"


class NeuronView:
    """One neuron of a pool, read and written like covenant_octopus.LIF (v, decay, thresh, reset), so the ring and
    the tests that look at single neurons work unchanged. Writes go into the pool's arrays."""

    __slots__ = ("_p", "_i")

    def __init__(self, pool, i):
        self._p, self._i = pool, i

    v = property(lambda s: s._p.get("v", s._i), lambda s, x: s._p.set("v", s._i, x))
    decay = property(lambda s: s._p.get("decay", s._i), lambda s, x: s._p.set("decay", s._i, x))
    thresh = property(lambda s: s._p.get("thresh", s._i), lambda s, x: s._p.set("thresh", s._i, x))
    reset = property(lambda s: s._p.get("reset", s._i), lambda s, x: s._p.set("reset", s._i, x))


class NeuronPool:
    """n leaky integrate-and-fire neurons on one backend ('numpy' or 'cuda'). step(signal) -> list of 0/1, the same
    as [LIF.step(s) for ...]. The new voltages are committed only after the whole step succeeds, so a backend that
    raises leaves the state as it was before the step (Arm then replays that step in pure Python)."""

    def __init__(self, n, tau=20.0, thresh=1.0, reset=0.0, backend="numpy"):
        if backend not in ("numpy", "cuda"):
            raise ValueError("NeuronPool backend must be numpy or cuda, not %r" % (backend,))
        self.n, self.backend = int(n), backend
        decay = math.exp(-1.0 / float(tau))
        if backend == "numpy":
            import numpy as np
            self._np = np
            mk = lambda x: np.full(self.n, float(x), dtype=np.float64)   # noqa: E731
        else:
            import torch
            self._t = torch
            mk = lambda x: torch.full((self.n,), float(x), dtype=torch.float64, device="cuda")   # noqa: E731
        self.arr = {"v": mk(0.0), "decay": mk(decay), "thresh": mk(thresh), "reset": mk(reset)}

    def views(self):
        return [NeuronView(self, i) for i in range(self.n)]

    def get(self, name, i):
        return float(self.arr[name][i])

    def set(self, name, i, x):
        self.arr[name][i] = float(x)

    def state(self):
        """Every neuron's (v, decay, thresh, reset) as Python floats, for a hand-back to pure Python."""
        cols = {k: (a.tolist() if self.backend == "numpy" else a.cpu().tolist()) for k, a in self.arr.items()}
        return [(cols["v"][i], cols["decay"][i], cols["thresh"][i], cols["reset"][i]) for i in range(self.n)]

    def to_numpy(self):
        """The same neurons, state and all, as a numpy pool (A484: off the GPU when a lease is taken). Bit-identical
        afterwards, because the two backends compute the same step the same way."""
        import numpy as np
        other = NeuronPool.__new__(NeuronPool)
        other.n, other.backend, other._np = self.n, "numpy", np
        other.arr = {k: (np.array(a, dtype=np.float64) if self.backend == "numpy"
                         else a.cpu().numpy().astype(np.float64, copy=True)) for k, a in self.arr.items()}
        return other

    def min_thresh(self):
        return float(self.arr["thresh"].min()) if self.n else 1.0

    def step(self, signal):
        a = self.arr
        if self.backend == "numpy":
            np = self._np
            x = np.asarray(signal, dtype=np.float64)
            v = a["v"] * a["decay"]                     # rounded once, as LIF does
            v = v + x                                   # rounded again: never fused with the multiply
            fired = v >= a["thresh"]
            v = np.where(fired, a["reset"], v)
            a["v"] = v                                  # committed only now
            return fired.astype(np.int8).tolist()
        import time
        now = time.monotonic()
        if now - getattr(self, "_lease_seen", -1e9) >= LEASE_CHECK_S:
            self._lease_seen = now
            held, why = lease_held()
            if held:
                raise LeaseTaken(why)                   # before anything is computed: nothing committed
        t = self._t
        x = t.as_tensor(signal, dtype=t.float64, device="cuda")
        v = t.mul(a["v"], a["decay"])
        v = t.add(v, x)
        fired = v >= a["thresh"]
        v = t.where(fired, a["reset"], v)
        out = fired.to(t.int8).cpu().tolist()           # the copy back is also the wait for the GPU
        a["v"] = v
        return out
