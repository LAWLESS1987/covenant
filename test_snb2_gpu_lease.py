#!/usr/bin/env python3
"""SNB2 -- A484: the spiking network respects TETSU's GPU lease. It never takes the lease; it places a pool on the
GPU only while no lease is in force; a pool already there moves to numpy, state and all, when one is taken, and its
spikes and voltages stay identical to pure Python. The lease file is read the way its writer (TETSU's
jlens/gpu_lease.py) and the start script read it. Driven both ways. Lines that need numpy or a CUDA GPU are NOT RUN,
with the reason, where those are missing."""
import json
import os
import random
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.pop("COVENANT_SNN_BACKEND", None)

import covenant_snn_backend as B    # noqa: E402
import covenant_octopus as O        # noqa: E402

fails, notrun, n = [], [], [0]


def check(name, cond, detail=""):
    n[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:220]))
    if not cond:
        fails.append(name)


def not_run(name, why):
    print("NOT RUN " + name + " -- " + why)
    notrun.append(name)


if not hasattr(B, "lease_held"):
    check("SNB2.0 the backend reads a GPU lease", False, "covenant_snn_backend has no lease_held")
    print("\nSNB2: %d/%d passed" % (n[0] - len(fails), n[0]))
    sys.exit(1)

tmp = tempfile.mkdtemp(prefix="snb2-")
lease = os.path.join(tmp, "gpu-lease.json")
os.environ[B.LEASE_ENV] = lease


def write(obj, raw=None):
    with open(lease, "w", encoding="utf-8") as fh:
        fh.write(raw if raw is not None else json.dumps(obj))


def clear():
    if os.path.exists(lease):
        os.replace(lease, lease + ".kept-%d" % time.time_ns())      # kept aside, never deleted


# ---- reading the lease as its writer does
clear()
check("SNB2.1 no lease file: free", B.lease_held() == (False, "no GPU lease"))
write({"expires": time.time() + 600, "why": "jlens fit"})
held, why = B.lease_held()
check("SNB2.2 a fresh lease is in force, with its reason", held and "jlens fit" in why, why)
write({"expires": time.time() - 5})
check("SNB2.3 an expired leftover is free (the night pause's lesson)", B.lease_held()[0] is False)
write(None, raw="{not json")
check("SNB2.4 an unreadable lease counts as held", B.lease_held()[0] is True)
write({"why": "no expiry"})
check("SNB2.5 a lease with no expiry counts as held", B.lease_held()[0] is True)
write(None, raw='{"expires": "soon"}')
check("SNB2.6 an expiry that is not a number counts as held, and does not crash", B.lease_held()[0] is True)
write(None, raw='{"expires": Infinity}')
check("SNB2.7 an infinite expiry counts as held", B.lease_held()[0] is True)
write(None, raw='["a list"]')
check("SNB2.8 a lease that is not a record counts as held", B.lease_held()[0] is True)
os.environ.pop(B.LEASE_ENV)
check("SNB2.9 the default path is training/gpu-lease.json beside the covenant folder (TETSU's layout)",
      B.lease_path() == os.path.join(os.path.dirname(HERE), "training", "gpu-lease.json"), B.lease_path())
os.environ[B.LEASE_ENV] = lease

# ---- the choice: never the GPU under a lease, never taking it
real_np = B._has_numpy
B._has_numpy = lambda: True
try:
    write({"expires": time.time() + 600, "why": "lens fit"})
    c, why = B.choose(200000)
    check("SNB2.10 a big pool under a lease goes to numpy, and says the lease is why",
          c == "numpy" and "lease" in why, (c, why))
    c, why = B.choose(200000, "cuda")
    check("SNB2.11 even COVENANT_SNN_BACKEND=cuda does not override a lease", c == "numpy" and "lease" in why, (c, why))
    before = open(lease, encoding="utf-8").read()
    B.choose(200000)
    check("SNB2.12 the network never writes the lease (it is not a holder)", open(lease, encoding="utf-8").read() == before)
finally:
    B._has_numpy = real_np


# ---- a pool on the GPU when a lease is taken mid-run
def drive(arm, seed, steps=60, at=None):
    rnd = random.Random(seed)
    out = []
    for t in range(steps):
        if at is not None and t == at:
            write({"expires": time.time() + 600, "why": "a lens fit started"})
        out.append(list(arm.sense([rnd.uniform(0.0, 0.14) for _ in range(len(arm.neurons))])))
    return out, [nu.v for nu in arm.neurons]


clear()
B.LEASE_CHECK_S = 0.0
gpu_ok, gpu_why = B._gpu_room(4096)
if gpu_ok and B._has_numpy():
    ref = drive(O.Arm(n=512, backend="python"), seed=4)
    arm = O.Arm(n=512, backend="cuda")
    was = arm.backend
    got = drive(arm, seed=4, at=30)
    check("SNB2.13 a lease taken mid-run moves the pool off the GPU to numpy, and the result is identical",
          was == "cuda" and arm.backend == "numpy" and "moved off the GPU" in arm.backend_why and got == ref,
          (was, arm.backend, arm.backend_why))
    clear()
else:
    not_run("SNB2.13 (a real GPU pool)", gpu_why if not gpu_ok else "numpy is not installed")

if B._has_numpy():
    # the same hand-over without a GPU: a numpy pool whose step reports a lease
    ref = drive(O.Arm(n=512, backend="python"), seed=9)
    arm = O.Arm(n=512, backend="numpy")
    real_step = arm.pool.step
    k = [0]

    def lease_once(sig):
        k[0] += 1
        if k[0] == 25:
            raise B.LeaseTaken("a GPU lease is in force (simulated)")
        return real_step(sig)

    arm.pool.step = lease_once
    got = drive(arm, seed=9)
    check("SNB2.14 the arm's lease hand-over keeps the exact state (simulated on numpy)",
          arm.backend == "numpy" and "moved off the GPU" in arm.backend_why and got == ref, arm.backend_why)
    # break: to_numpy that loses the voltages must turn SNB2.14 red
    real_to = B.NeuronPool.to_numpy

    def lossy(self):
        p = real_to(self)
        p.arr["v"][:] = 0.0
        return p

    B.NeuronPool.to_numpy = lossy
    try:
        arm = O.Arm(n=512, backend="numpy")
        rs = arm.pool.step
        k2 = [0]

        def lease_once2(sig):
            k2[0] += 1
            if k2[0] == 25:
                raise B.LeaseTaken("simulated")
            return rs(sig)

        arm.pool.step = lease_once2
        got2 = drive(arm, seed=9)
        check("SNB2.15 the hand-over check is seen RED when the voltages are not carried", got2 != ref)
    finally:
        B.NeuronPool.to_numpy = real_to
else:
    not_run("SNB2.14-SNB2.15", "numpy is not installed in this interpreter")

# break: a lease reader that ignores the file must turn SNB2.10 red
real_held = B.lease_held
B.lease_held = lambda path=None: (False, "ignored")
B._has_numpy = lambda: True
real_room = B._gpu_room
try:
    write({"expires": time.time() + 600, "why": "lens fit"})
    B._gpu_room = lambda k: ((not B.lease_held()[0]), "room")       # a GPU with room, if the lease allowed it
    check("SNB2.16 the choice check is seen RED when the lease is ignored", B.choose(200000)[0] == "cuda")
finally:
    B.lease_held, B._has_numpy, B._gpu_room = real_held, real_np, real_room
    clear()

print("\nSNB2: %d/%d passed%s" % (n[0] - len(fails), n[0], ("; NOT RUN: " + ", ".join(notrun)) if notrun else ""))
sys.exit(1 if fails else 0)
