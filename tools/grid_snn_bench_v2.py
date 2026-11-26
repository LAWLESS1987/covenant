#!/usr/bin/env python3
"""
tools/grid_snn_bench_v2.py -- v2 benchmark harness for the grid SNN witness, per the
SEALED pre-registration ops/GRID_SNN_PREREG_v2_2026-11-02.md.

Why a v2 (what v1's own pre-merge review, A392, found and this fixes):
  1. CUMULATIVE-WINDOW-RESPECTING generator. Every stream keeps sum(shed_pct) <= 100
     and #breaker_ops <= 1000 BY CONSTRUCTION (shed drawn <= 2.0 each, N=40 -> <=80;
     breaker multiset is 20 open/20 close), over a horizon H = 4*WINDOW_S, so no
     trailing C5 window can exceed a cap. v1's A/D overran the window and failed the
     in-bounds premise 0/300; here the premise holds for both classes, and we MEASURE
     it through the real gateway rather than assume it.
  2. MATCHED MARGINALS EXACT BY CONSTRUCTION. For each paired (benign_i, attack_i) the
     attack stream is a re-timing / re-ordering of the SAME magnitude multiset: same
     actions, same per-zone magnitude values, only arrival times and order differ. So
     exact-multiset equality = 1.0; measured. Belt-and-braces pooled KS per zone under
     HOLM-BONFERRONI correction (v1's D read UNDETERMINED on an uncorrected 3-zone test).
  3. B1..B6 ALL SEALED. v1 sealed only B1..B4 and added B3b/B5/B6 after seeing results;
     here the SNN must beat the BEST of the full sealed set snn.ewma_baseline_score
     reports (B1,B2,B2-sustained,B3,B3b,B4,B5,B6).
  4. LARGER BENIGN SPLIT. n=200 benign/seed (100 val + 100 test) so a <=1% FA operating
     point is resolvable on the test split (v1's n=20 quantised FA at 0.05).
  5. HELD-OUT FAMILY E (setpoint staircase), premise-valid by the same construction,
     reserved for ship-bar #3 and never trained on.

The in-bounds premise replay reuses grid_snn_bench.permits() unchanged -- the real
GridEffectorGateway.submit() -> authorize() over the whole stream, signed ACTUATION
with operator+tetsu tokens, cumulative C5, fresh ledger per stream. That path needs
`cryptography` (repo Python). Baseline scoring and the generator need only numpy.

The trained-SNN run is tools/grid_snn_train_v2.py (spiking-lab venv); its numbers and
the GO/NO-GO verdict are recorded in the prereg, not computed here. No RNG at inference;
all seeds explicit. Synthetic separability only, NOT a field claim (patterns-not-proof).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import numpy as np

import covenant_grid_snn as snn

ZONES = ["Z1", "Z2", "Z3"]
N = 40                       # commands per stream
WINDOW_S = 3600
H = 4 * WINDOW_S             # 14400 s: longer than the C5 window, so streams span it
T0 = 1_700_000_000

# All six are SEALED in v2 (prereg); the SNN must beat the BEST of these. These are
# exactly the keys covenant_grid_snn.ewma_baseline_score returns.
SEALED_BASELINES = ("B1_ewma_shed", "B2_cusum_shed", "B2_sustained_breaker",
                    "B3_setpoint_slope", "B3b_shed_slope", "B4_crosszone_corr",
                    "B5_setpoint_value_slope", "B6_breaker_alternation")

TRAIN_FAMILIES = ("A", "B", "C", "D")
HELDOUT_FAMILY = "E"
SHED_FAMILIES = {"A", "D"}
SETPOINT_FAMILIES = {"C", "E"}
BREAKER_FAMILIES = {"B"}


# --------------------------------------------------------------- the v2 generator
def _payload(seq, t, action, zone, mag):
    return {"v": "COVENANT_GRIDCMD_V1", "seq": seq, "nonce": "n%d" % seq,
            "issued_utc": int(t), "expires_utc": int(t) + 300, "signer_fpr": "bench",
            "class": "ACTUATION", "action": action, "zone": zone,
            "magnitude": mag, "authz_tokens": []}


def _pool(family, seed, n=N):
    """The fixed per-stream material a benign/attack PAIR shares, so their magnitude
    multisets are identical (matched marginals exact). Returns (mags, zones) where
    `zones` is the per-command zone assignment (fixed for both roles)."""
    rng = np.random.default_rng(seed)
    if family in SHED_FAMILIES:
        mags = np.round(rng.uniform(0.5, 2.0, n), 2)          # sum <= 80 < MAX_SHED_PCT 100
        zones = [ZONES[i % len(ZONES)] for i in range(n)] if family == "D" else ["Z1"] * n
    elif family in SETPOINT_FAMILIES:
        mags = np.round(rng.uniform(42.0, 58.0, n), 2)        # inside [40,60] per-command range
        zones = ["Z1"] * n
    elif family in BREAKER_FAMILIES:
        mags = np.array([1.0] * (n // 2) + [0.0] * (n - n // 2))   # fixed multiset: 20 open / 20 close
        zones = ["Z1"] * n
    else:
        raise ValueError("unknown family %r" % family)
    return mags, zones


def gen(family, seed, role):
    """One stream of command payloads for `role` in {"benign","attack"}. Benign and
    attack at the same (family, seed) share the magnitude multiset from _pool(); only
    arrival times / order differ (the temporal structure under test). Every stream is
    in-bounds by construction; the premise is MEASURED by permits()."""
    mags, zones = _pool(family, seed)
    n = len(mags)
    rng = np.random.default_rng(seed * 7919 + (0 if role == "benign" else 1))

    def _rows_from(order, times, action_of, mag_of):
        rows = []
        for i in range(n):
            j = order[i]
            rows.append(_payload(i, T0 + times[i], action_of(i, j), zones[j], mag_of(i, j)))
        return rows

    if role == "benign":                                      # no temporal/cross structure
        if family == "D":
            # same per-zone multisets as attack, but each command jittered independently
            # (no cross-zone coincidence); zone assignment kept stable (order = arange).
            rounds = int(np.ceil(n / len(ZONES)))
            base = np.linspace(0, H, rounds)
            times = np.array([min(H, base[i // len(ZONES)] + rng.uniform(0, H / rounds))
                              for i in range(n)])
            return _rows_from(np.arange(n), times, lambda i, j: "load_shed",
                              lambda i, j: {"pct": float(mags[j])})
        order = rng.permutation(n)
        times = np.sort(rng.uniform(0, H, n))
        if family in SHED_FAMILIES:
            return _rows_from(order, times, lambda i, j: "load_shed",
                              lambda i, j: {"pct": float(mags[j])})
        if family in SETPOINT_FAMILIES:
            return _rows_from(order, times, lambda i, j: "setpoint",
                              lambda i, j: {"value": float(mags[j])})
        if family in BREAKER_FAMILIES:
            return _rows_from(order, times,
                              lambda i, j: "breaker_open" if mags[j] == 1.0 else "breaker_close",
                              lambda i, j: {})

    # ---- attack: the family's temporal / cross-channel structure, same multiset ----
    if family == "A":                                         # monotone shed ramp
        order = np.argsort(mags)
        times = np.linspace(0, H, n)
        return _rows_from(order, times, lambda i, j: "load_shed",
                          lambda i, j: {"pct": float(mags[j])})
    if family == "B":                                         # strict open/close alternation
        order = np.arange(n)
        times = np.linspace(0, H, n)
        return _rows_from(order, times,
                          lambda i, j: "breaker_open" if i % 2 == 0 else "breaker_close",
                          lambda i, j: {})
    if family == "C":                                         # monotone setpoint walk
        order = np.argsort(mags)
        times = np.linspace(0, H, n)
        return _rows_from(order, times, lambda i, j: "setpoint",
                          lambda i, j: {"value": float(mags[j])})
    if family == "D":                                         # cross-zone time-locked
        rounds = int(np.ceil(n / len(ZONES)))
        rt = np.linspace(0, H, rounds)
        times = np.array([rt[i // len(ZONES)] for i in range(n)])   # all zones in a round share the time
        order = np.arange(n)
        return _rows_from(order, times, lambda i, j: "load_shed",
                          lambda i, j: {"pct": float(mags[j])})
    if family == "E":                                         # setpoint staircase (held-out)
        order = np.argsort(mags)                              # ascending values
        steps = 5
        per = int(np.ceil(n / steps))
        step_t = np.linspace(0, H, steps)
        times = np.array([min(H, step_t[i // per] + (i % per) * (H / steps) * 0.05) for i in range(n)])
        return _rows_from(order, times, lambda i, j: "setpoint",
                          lambda i, j: {"value": float(mags[j])})
    raise ValueError("unknown family/role %r/%r" % (family, role))


# --------------------------------------------------------------- matched marginals
def _holm_ok(pvals, alpha=0.05):
    """Holm-Bonferroni: sort p ascending, reject step i iff p_(i) <= alpha/(m-i). The
    marginals MATCH (no zone rejects) iff NO hypothesis is rejected under Holm."""
    m = len(pvals)
    if m == 0:
        return True, None
    order = np.argsort(pvals)
    for i, idx in enumerate(order):
        if pvals[idx] <= alpha / (m - i):
            return False, float(pvals[idx])         # a zone rejected -> marginals differ
    return True, float(min(pvals))


def marginal_check(ben_rows, att_rows, alpha=0.05):
    """Reuse v1's per-command magnitude extraction + KS, add Holm correction over zones.
    status: MATCHED-EXACT (every paired multiset identical) | MATCHED-DISTRIBUTIONAL
    (no zone rejects under Holm) | UNDETERMINED."""
    import grid_snn_bench as B
    pairs = list(zip(ben_rows, att_rows))
    exact = float(np.mean([sorted(B._marginal_values(b)) == sorted(B._marginal_values(a))
                           for b, a in pairs])) if pairs else 0.0
    zones = sorted({r.get("zone") for rows in ben_rows + att_rows for r in rows})
    per_zone = []
    for z in zones:
        bv = [v for rows in ben_rows for v in B._marginal_values(rows, z)]
        av = [v for rows in att_rows for v in B._marginal_values(rows, z)]
        if not bv or not av:
            per_zone.append({"zone": z, "D": 1.0, "p": 0.0, "how": "missing"})
            continue
        D, p, how = B._ks_2samp(bv, av)
        per_zone.append({"zone": z, "D": D, "p": p, "how": how, "n_ben": len(bv), "n_att": len(av)})
    holm_ok, min_p = _holm_ok([z["p"] for z in per_zone], alpha)
    if exact == 1.0:
        status = "MATCHED-EXACT"
    elif holm_ok:
        status = "MATCHED-DISTRIBUTIONAL"
    else:
        status = "UNDETERMINED"
    worst = min(per_zone, key=lambda z: z["p"]) if per_zone else None
    return {"exact_pairs": exact, "n_pairs": len(pairs), "per_zone": per_zone,
            "ks_worst": worst, "holm_ok": holm_ok, "holm_min_p": min_p,
            "alpha": alpha, "status": status}


# --------------------------------------------------------------- in-bounds premise
def premise_sample(family, seeds=(1, 2, 3, 4, 5), n_per=8):
    """MEASURE the in-bounds premise through the real gateway on a pinned sample of
    streams per class (grid_snn_bench.permits replays the whole stream through
    GridEffectorGateway.submit() with the cumulative C5 window). Returns counts."""
    import grid_snn_bench as B
    out = {"benign": [], "attack": []}
    for s in seeds:
        for i in range(n_per):
            out["benign"].append(B.permits(gen(family, s * 1000 + i, "benign")))
            out["attack"].append(B.permits(gen(family, s * 1000 + i, "attack")))
    summ = {}
    for cls, vs in out.items():
        k = sum(1 for v in vs if v["all_permit"])
        fails = {}
        for v in vs:
            for ck, c in v["fail_checks"].items():
                fails[ck] = fails.get(ck, 0) + c
        summ[cls] = {"all_permit": k, "total": len(vs),
                     "mean_permitted": float(np.mean([v["n_permit"] for v in vs])),
                     "n_cmd": vs[0]["n"] if vs else 0, "fail_checks": fails}
    return summ


# --------------------------------------------------------------- baselines
def feat(rows):
    """All six SEALED baseline scores for one stream (snn.ewma_baseline_score)."""
    b = snn.ewma_baseline_score(rows, now=max(r["issued_utc"] for r in rows) + 1, window_s=WINDOW_S)
    missing = set(SEALED_BASELINES) - set(b)
    if missing:
        raise RuntimeError("baseline keys missing from ewma_baseline_score: %s" % sorted(missing))
    return b


def best_baseline(family, seeds=(1, 2, 3, 4, 5), n=200, val=100):
    """Per seed: threshold each sealed baseline at the 0.99 quantile of benign-VAL;
    report the BEST (by val detection) baseline's detection + FA on the held-out TEST
    split. Mean +/- std over seeds. Returns {per_seed, det_mean, det_std, fa_mean,
    pooled_std, name}."""
    per_seed = []
    for s in seeds:
        ben = [feat(gen(family, s * 100 + i, "benign")) for i in range(n)]
        att = [feat(gen(family, s * 100 + 5000 + i, "attack")) for i in range(n)]
        best = {"name": None, "val_det": -1.0, "test_det": 0.0, "test_fa": 0.0}
        for k in SEALED_BASELINES:
            bv = np.array([b[k] for b in ben]); av = np.array([a[k] for a in att])
            thr = np.quantile(bv[:val], 0.99)
            val_det = float((av[:val] > thr).mean())
            if val_det > best["val_det"]:
                best = {"name": k, "val_det": val_det,
                        "test_det": float((av[val:] > thr).mean()),
                        "test_fa": float((bv[val:] > thr).mean())}
        per_seed.append(best)
    det = np.array([r["test_det"] for r in per_seed])
    fa = np.array([r["test_fa"] for r in per_seed])
    names = [r["name"] for r in per_seed]
    return {"per_seed": per_seed, "name": max(set(names), key=names.count),
            "det_mean": float(det.mean()), "det_std": float(det.std()),
            "fa_mean": float(fa.mean()), "det": det.tolist()}


# --------------------------------------------------------------- report
def main(argv=None):
    ap = argparse.ArgumentParser(description="grid SNN v2 baseline benchmark (sealed prereg v2)")
    ap.add_argument("--n", type=int, default=200, help="streams per class per seed (default 200)")
    ap.add_argument("--val", type=int, default=100, help="val split size (default 100; test = n-val)")
    ap.add_argument("--premise-n", type=int, default=8, help="premise streams per class per seed (default 8)")
    ap.add_argument("--families", default="ABCDE")
    ap.add_argument("--no-premise", action="store_true", help="skip the gateway replay (needs cryptography)")
    a = ap.parse_args(argv)
    print("grid SNN v2 benchmark -- sealed prereg ops/GRID_SNN_PREREG_v2_2026-11-02.md")
    print("All of B1..B6 are SEALED; SNN must beat the BEST of them. n=%d (%d val / %d test) x 5 seeds."
          % (a.n, a.val, a.n - a.val))
    print("Trained-SNN numbers + GO/NO-GO are tools/grid_snn_train_v2.py + the prereg, not here.\n")
    for fam in a.families:
        print("family %s%s:" % (fam, "  (HELD-OUT, bar #3)" if fam == HELDOUT_FAMILY else ""))
        if not a.no_premise:
            pr = premise_sample(fam, n_per=a.premise_n)
            for cls in ("benign", "attack"):
                d = pr[cls]
                print("  in-bounds premise [%s]: all-PERMIT %d/%d; mean permitted %.1f/%d; non-PERMIT %s"
                      % (cls, d["all_permit"], d["total"], d["mean_permitted"], d["n_cmd"],
                         d["fail_checks"] or "{}"))
        else:
            print("  in-bounds premise: NOT MEASURED (--no-premise)")
        ben_all = [gen(fam, 900 + i, "benign") for i in range(60)]
        att_all = [gen(fam, 900 + i, "attack") for i in range(60)]
        m = marginal_check(ben_all, att_all)
        w = m["ks_worst"] or {}
        print("  matched marginals: exact paired multiset %d/%d; KS worst zone %s p=%.3g; Holm-ok=%s -> %s"
              % (round(m["exact_pairs"] * m["n_pairs"]), m["n_pairs"], w.get("zone"),
                 w.get("p", float("nan")), m["holm_ok"], m["status"]))
        bb = best_baseline(fam, n=a.n, val=a.val)
        print("  best SEALED baseline: %-24s test detection=%.2f+/-%.2f  test FA=%.3f\n"
              % (bb["name"], bb["det_mean"], bb["det_std"], bb["fa_mean"]))
    print("Synthetic separability only, NOT a field claim. A family whose premise or marginals")
    print("do not hold is UNDETERMINED for the prereg comparison (CLAUDE.md rule 9).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
