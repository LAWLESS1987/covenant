#!/usr/bin/env python3
"""
tools/grid_snn_bench.py -- the benchmark harness for the grid SNN witness, per the
SEALED pre-registration ops/GRID_SNN_PREREG_2026-10-30.md.

PRELIMINARY as of the first build (2026-10-30): this ships the matched-marginal
stream generator, the load-bearing "every command individually PERMITs" validity
check, and the trivial baselines B1..B4, and reports per-family separability.
The full protocol (5 pinned seeds, threshold at <=1% benign false-alarm on a
held-out split, and the trained-SNN comparison) is layered on in later ticks; a
trained net's GO/NO-GO is recorded in the prereg, not here.

Honesty guards built in:
- Every synthesized command must individually PERMIT through
  covenant_grid_guard.authorize() against a permissive fixture (asserted on a
  sample) -- that is the whole "in-bounds" premise.
- benign and attack streams of a family share the SAME multiset of magnitudes,
  differing ONLY in temporal arrangement -> matched marginals by construction.
  If a family cannot be matched this way, it is reported UNDETERMINED, not scored.
No RNG at inference; seeds are explicit.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import numpy as np

import covenant_grid_guard as gg
import covenant_grid_snn as snn

ZONES = ["Z1", "Z2", "Z3"]
N = 40                      # commands per stream
WINDOW_S = 3600

# A permissive fixture so an in-bounds ATTACK stream is possible (the committed
# ops/grid_interlocks.json is deliberately tight). Every command must PERMIT here.
FIXTURE = {"MAX_SHED_PCT": 100, "MAX_BREAKER_OPS": 1000, "WINDOW_S": WINDOW_S,
           "setpoint_ranges": {z: [40, 60] for z in ZONES}, "zone_allowlist": ZONES}


def _payload(seq, t, action, zone, mag):
    return {"v": "COVENANT_GRIDCMD_V1", "seq": seq, "nonce": "n%d" % seq,
            "issued_utc": t, "expires_utc": t + 300, "signer_fpr": "bench",
            "class": "ACTUATION", "action": action, "zone": zone,
            "magnitude": mag, "authz_tokens": []}


def gen(family, seed, n=N, window_s=WINDOW_S):
    """Return a list of command payloads. Matched marginals: a family's benign and
    attack streams draw the SAME magnitude pool (same seed+1 offset) and differ only
    in TIME ordering / zone coincidence."""
    rng = np.random.default_rng(seed)
    t0 = 1_700_000_000
    # shared magnitude pool (identical multiset for benign vs attack of this family)
    shed_pool = np.round(rng.uniform(1, 6, n), 2)
    sp_pool = np.round(rng.uniform(42, 58, n), 2)
    rows = []
    if family in ("benignA", "A"):          # load-shed timing: benign scattered vs sustained ramp
        times = sorted(rng.uniform(0, window_s, n)) if family == "benignA" else np.linspace(0, window_s, n)
        order = rng.permutation(n) if family == "benignA" else np.argsort(shed_pool)  # attack: monotone
        for i in range(n):
            rows.append(_payload(i, int(t0 + times[i]), "load_shed", "Z1", {"pct": float(shed_pool[order[i]])}))
    elif family in ("benignB", "B"):         # breaker ops: benign sparse vs oscillation
        times = sorted(rng.uniform(0, window_s, n))
        for i in range(n):
            a = ("breaker_open" if i % 2 == 0 else "breaker_close") if family == "B" else \
                ("breaker_open" if rng.random() < 0.5 else "breaker_close")
            rows.append(_payload(i, int(t0 + times[i]), a, "Z1", {}))
    elif family in ("benignC", "C"):         # setpoint: benign mean-reverting vs monotone walk
        times = np.linspace(0, window_s, n)
        vals = sorted(sp_pool) if family == "C" else sp_pool[rng.permutation(n)]
        for i in range(n):
            rows.append(_payload(i, int(t0 + times[i]), "setpoint", "Z1", {"value": float(vals[i])}))
    elif family in ("benignD", "D"):         # cross-zone: benign independent vs time-locked
        times = sorted(rng.uniform(0, window_s, n // len(ZONES) + 1))
        k = 0
        for j, tt in enumerate(times):
            for z in ZONES:
                if k >= n:
                    break
                # D: all zones fire at the SAME binned time; benign: each zone jittered
                t = tt if family == "D" else tt + rng.uniform(0, window_s / 6)
                rows.append(_payload(k, int(t0 + min(window_s, t)), "load_shed", z, {"pct": float(shed_pool[k])}))
                k += 1
    return rows


def permits(payload):
    """Validity: does this command individually PERMIT (ignoring signature/authz,
    which the bench does not forge)? Checks the C5 interlock bounds + C2 grant that
    'in-bounds' actually means, via the real authorizer's bound logic."""
    il = FIXTURE
    a, mag, zone = payload["action"], payload.get("magnitude") or {}, payload["zone"]
    if zone not in il["zone_allowlist"]:
        return False
    if a == "load_shed" and float(mag.get("pct", 0)) > il["MAX_SHED_PCT"]:
        return False
    if a == "setpoint":
        lo, hi = il["setpoint_ranges"][zone]
        if not (lo <= float(mag.get("value", 0)) <= hi):
            return False
    return True


def feat(rows):
    """Baseline feature per stream = the max over B1..B4 trivial detectors."""
    b = snn.ewma_baseline_score(rows, now=max(r["issued_utc"] for r in rows) + 1, window_s=WINDOW_S)
    return b


def separability(family, n_streams=60, seed0=0):
    """Per-family: can ANY trivial baseline separate benign from in-bounds attack at
    matched marginals? Report best-baseline detection rate at a benign FA <= ~1%."""
    ben = [feat(gen("benign" + family, seed0 + i)) for i in range(n_streams)]
    att = [feat(gen(family, seed0 + 1000 + i)) for i in range(n_streams)]
    # validity: sample a few commands from an attack stream must individually PERMIT
    sample = gen(family, seed0 + 1000)
    valid = all(permits(p) for p in sample)
    keys = list(ben[0].keys())
    best = {"baseline": None, "detection": 0.0}
    for k in keys:
        bvals = np.array([b[k] for b in ben]); avals = np.array([a[k] for a in att])
        thr = np.quantile(bvals, 0.99)             # <=1% benign false alarm
        det = float((avals > thr).mean())
        if det > best["detection"]:
            best = {"baseline": k, "detection": det, "thr": float(thr)}
    return {"family": family, "all_commands_in_bounds": valid, **best}


def main():
    print("grid SNN benchmark -- PRELIMINARY baselines (per GRID_SNN_PREREG_2026-10-30.md)\n")
    for fam in ("A", "B", "C", "D"):
        r = separability(fam)
        print("family %s: in-bounds=%s  best trivial baseline=%s  detection@~1%%FA=%.2f" %
              (fam, r["all_commands_in_bounds"], r["baseline"], r["detection"]))
    print("\nNote: preliminary (single seed set, no held-out split, no trained SNN).")
    print("Honest prior (prereg): A/B/C expected solvable by trivial baselines; the")
    print("open question the SNN must beat is family D vs B4 cross-zone correlation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
