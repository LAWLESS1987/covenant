"""Train the grid SNN witness per the SEALED v2 prereg and score it held-out vs the
BEST of the SEALED baselines B1..B6. Run with the spiking-lab venv (torch + snntorch).
Records numbers + a mechanical GO/NO-GO against the three ship-bar conditions; the
written verdict goes in ops/GRID_SNN_PREREG_v2_2026-11-02.md, not here.

    <spiking-venv-python> tools/grid_snn_train_v2.py [--out PATH] [--n 200]

Paths resolve from this script's location (repo root = parent of tools/). The result
JSON goes to --out, default logs/grid_snn_train_v2_result.json (logs/ is gitignored).

Splits per family per seed (distinct sub-seed ranges, no leakage):
  train 100 benign + 100 attack; val 100 benign (threshold @ 0.99 quantile = <=1% FA);
  test 100 benign (FA) + 100 attack (detection). Bar #3: train on A,B,C,D, test on E.

NOTE on equivalence (prereg): the lab net here is a feed-forward snntorch Leaky
(10->32->1, membrane-mean readout) -- NOT the recurrent lateral-inhibition LIF that the
shipped covenant_grid_snn.run_lif implements. So a GO would additionally require porting
the winning net into run_lif within the pinned tolerance BEFORE weights ship. Given the
stated NO-GO prior this trainer only MEASURES the bar; if it clears, the equivalence port
is the next step and is done before any weights are written. This script never writes
ops/grid_snn_weights.npz.
"""
import argparse
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DEFAULT_OUT = os.path.join(ROOT, "logs", "grid_snn_train_v2_result.json")
sys.path.insert(0, ROOT)
sys.path.insert(0, TOOLS)

CH = ("breaker", "shed", "setpoint_delta", "interval", "zones_active")


def feats(rows):
    import numpy as np
    import covenant_grid_snn as G
    enc = G.encode_window(rows, now=max(r["issued_utc"] for r in rows) + 1)
    f = []
    for c in CH:
        f.append(enc[c].sum(axis=1)); f.append((enc[c] > 0).sum(axis=1))
    return np.stack(f, axis=1).astype("float32")               # [T_BINS, 10]


def _net_class(reset="subtract"):
    """reset="subtract" is the SEALED CONTROL (snntorch default; a hidden spike
    subtracts the threshold off -- frequent drive is cancelled). reset="none" is the
    prereg v2 Amendment A1 TREATMENT (the operator's don't-cancel / amplify): the
    hidden membrane is NOT reset after a spike, so strong/frequent drive accumulates."""
    import torch.nn as nn
    import snntorch as snn

    class Net(nn.Module):
        def __init__(s, h=32):
            super().__init__()
            s.f1 = nn.Linear(10, h); s.l1 = snn.Leaky(beta=0.9, reset_mechanism=reset)
            s.f2 = nn.Linear(h, 1); s.l2 = snn.Leaky(beta=0.9, output=True, reset_mechanism=reset)

        def forward(s, x):                                     # x [B,T,10]
            m1 = s.l1.init_leaky(); m2 = s.l2.init_leaky(); acc = 0
            for t in range(x.shape[1]):
                sp1, m1 = s.l1(s.f1(x[:, t]), m1)
                sp2, m2 = s.l2(s.f2(sp1), m2)
                acc = acc + m2.squeeze(-1)
            return acc / x.shape[1]
    return Net


def _streams(B2, fam, base, k, role):
    return [feats(B2.gen(fam, base + i, role)) for i in range(k)]


def family_data(B2, fam, seed, k=100):
    """Distinct sub-seed ranges per split so train never leaks into val/test."""
    import numpy as np
    b = seed * 1_000_000
    tr = _streams(B2, fam, b + 0, k, "benign") + _streams(B2, fam, b + 100_000, k, "attack")
    ytr = np.array([0] * k + [1] * k, dtype="float32")
    val_b = _streams(B2, fam, b + 200_000, k, "benign")
    test_b = _streams(B2, fam, b + 300_000, k, "benign")
    test_a = _streams(B2, fam, b + 400_000, k, "attack")
    return (np.stack(tr), ytr, np.stack(val_b), np.stack(test_b), np.stack(test_a))


def snn_train_eval(Xtr, ytr, Xvb, Xtb, Xta, seed, reset="subtract"):
    import numpy as np
    import torch
    import torch.nn as nn
    Net = _net_class(reset)
    torch.manual_seed(seed)
    sc = Xtr.reshape(-1, 10).std(0) + 1e-6
    T = lambda a: torch.tensor(a / sc)
    net = Net(); opt = torch.optim.Adam(net.parameters(), 5e-3); lf = nn.BCEWithLogitsLoss()
    Xt, yt = T(Xtr), torch.tensor(ytr)
    for _ in range(60):
        perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 32):
            bidx = perm[i:i + 32]; opt.zero_grad()
            lf(net(Xt[bidx]), yt[bidx]).backward(); opt.step()
    with torch.no_grad():
        sv = net(T(Xvb)).numpy(); sb = net(T(Xtb)).numpy(); sa = net(T(Xta)).numpy()
    thr = float(np.quantile(sv, 0.99))
    return float((sa > thr).mean()), float((sb > thr).mean())


def baseline_eval(B2, fam, seed, k=100):
    """BEST of the SEALED baselines on the SAME splits: threshold at 0.99 quantile of
    benign-val, best by val detection, report test detection + FA. numpy only."""
    import numpy as np
    b = seed * 1_000_000
    valb = [B2.feat(B2.gen(fam, b + 200_000 + i, "benign")) for i in range(k)]
    testb = [B2.feat(B2.gen(fam, b + 300_000 + i, "benign")) for i in range(k)]
    testa = [B2.feat(B2.gen(fam, b + 400_000 + i, "attack")) for i in range(k)]
    best = {"name": None, "val_det": -1.0, "test_det": 0.0, "test_fa": 0.0}
    for key in B2.SEALED_BASELINES:
        vb = np.array([r[key] for r in valb])
        tb = np.array([r[key] for r in testb]); ta = np.array([r[key] for r in testa])
        thr = np.quantile(vb, 0.99)
        # val detection needs attack-val streams (distinct sub-seed range from test attack)
        va = np.array([B2.feat(B2.gen(fam, b + 500_000 + i, "attack"))[key] for i in range(k)])
        vd = float((va > thr).mean())
        if vd > best["val_det"]:
            best = {"name": key, "val_det": vd, "test_det": float((ta > thr).mean()),
                    "test_fa": float((tb > thr).mean())}
    return best["test_det"], best["test_fa"], best["name"]


def main(argv=None):
    import numpy as np
    import grid_snn_bench_v2 as B2
    ap = argparse.ArgumentParser(description="train + score grid SNN witness (sealed v2 prereg)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--k", type=int, default=100, help="streams per split per class (default 100)")
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--reset", default="subtract", choices=["subtract", "none", "zero"],
                    help="hidden-layer reset: subtract=SEALED CONTROL; none=Amendment A1 don't-cancel treatment")
    a = ap.parse_args(argv)
    seeds = [int(x) for x in a.seeds.split(",")]
    print("reset mechanism: %s (%s)\n"
          % (a.reset, "SEALED CONTROL" if a.reset == "subtract" else "Amendment A1 TREATMENT (don't-cancel)"))

    res = {"per_family": {}, "bar": {}, "k": a.k, "seeds": seeds, "reset": a.reset}
    for fam in B2.TRAIN_FAMILIES:
        snn_det, snn_fa, bl_det, bl_fa, diffs = [], [], [], [], []
        bl_names = []
        for s in seeds:
            Xtr, ytr, Xvb, Xtb, Xta = family_data(B2, fam, s, a.k)
            d, f = snn_train_eval(Xtr, ytr, Xvb, Xtb, Xta, s, reset=a.reset)
            bd, bf, bn = baseline_eval(B2, fam, s, a.k)
            snn_det.append(d); snn_fa.append(f); bl_det.append(bd); bl_fa.append(bf)
            diffs.append(d - bd); bl_names.append(bn)
        snn_det, bl_det, diffs = map(lambda x: np.array(x, float), (snn_det, bl_det, diffs))
        pooled = float(np.sqrt((snn_det.std() ** 2 + bl_det.std() ** 2) / 2))
        margin = float(snn_det.mean() - bl_det.mean())
        bar1 = margin > 2 * pooled
        bar2 = margin >= 0.10
        fa_ok = float(np.mean(snn_fa)) <= 0.01
        res["per_family"][fam] = {
            "snn_det_mean": float(snn_det.mean()), "snn_det_std": float(snn_det.std()),
            "snn_fa_mean": float(np.mean(snn_fa)),
            "baseline": max(set(bl_names), key=bl_names.count),
            "baseline_det_mean": float(bl_det.mean()), "baseline_det_std": float(bl_det.std()),
            "baseline_fa_mean": float(np.mean(bl_fa)),
            "margin": margin, "pooled_std": pooled,
            "bar1_margin_gt_2sigma": bool(bar1), "bar2_margin_ge_0.10": bool(bar2),
            "snn_fa_le_1pct": bool(fa_ok)}
        print("family %s: SNN det %.2f+/-%.2f (FA %.3f) | best baseline %s det %.2f (FA %.3f) | "
              "margin %.3f pooled %.3f | bar1=%s bar2=%s faOK=%s"
              % (fam, snn_det.mean(), snn_det.std(), np.mean(snn_fa),
                 res["per_family"][fam]["baseline"], bl_det.mean(), np.mean(bl_fa),
                 margin, pooled, bar1, bar2, fa_ok), flush=True)

    # ---- bar #3: held-out family E (train on A,B,C,D, test on E), over seeds ----
    e_snn_det, e_snn_fa, e_bl_det, e_diffs = [], [], [], []
    for s in seeds:
        Xs, ys = [], []
        for fam in B2.TRAIN_FAMILIES:
            X, y, _, _, _ = family_data(B2, fam, s, a.k)
            Xs.append(X); ys.append(y)
        Xtr = np.concatenate(Xs); ytr = np.concatenate(ys)
        _, _, Evb, Etb, Eta = family_data(B2, "E", s, a.k)
        d, f = snn_train_eval(Xtr, ytr, Evb, Etb, Eta, s + 90, reset=a.reset)
        bd, bf, bn = baseline_eval(B2, "E", s, a.k)
        e_snn_det.append(d); e_snn_fa.append(f); e_bl_det.append(bd); e_diffs.append(d - bd)
        print("held-out E seed %d: SNN det %.2f (FA %.3f) | baseline %s det %.2f (FA %.3f)"
              % (s, d, f, bn, bd, bf), flush=True)
    e_snn_det, e_bl_det = np.array(e_snn_det), np.array(e_bl_det)
    e_pooled = float(np.sqrt((e_snn_det.std() ** 2 + e_bl_det.std() ** 2) / 2))
    e_margin = float(e_snn_det.mean() - e_bl_det.mean())
    res["bar"]["heldout_E"] = {
        "snn_det_mean": float(e_snn_det.mean()), "snn_fa_mean": float(np.mean(e_snn_fa)),
        "baseline_det_mean": float(e_bl_det.mean()), "margin": e_margin, "pooled_std": e_pooled,
        "bar1_margin_gt_2sigma": bool(e_margin > 2 * e_pooled), "bar2_margin_ge_0.10": bool(e_margin >= 0.10),
        "snn_fa_le_1pct": bool(float(np.mean(e_snn_fa)) <= 0.01)}

    # ---- overall GO iff some trained family passes #1 AND #2 AND FA<=1%, AND E too ----
    trained_go = {f: (v["bar1_margin_gt_2sigma"] and v["bar2_margin_ge_0.10"] and v["snn_fa_le_1pct"])
                  for f, v in res["per_family"].items()}
    e = res["bar"]["heldout_E"]
    e_go = e["bar1_margin_gt_2sigma"] and e["bar2_margin_ge_0.10"] and e["snn_fa_le_1pct"]
    res["verdict"] = {"any_trained_family_passes": {f: bool(g) for f, g in trained_go.items()},
                      "heldout_E_passes": bool(e_go),
                      "GO": bool(any(trained_go.values()) and e_go)}
    print("\nheld-out E: SNN det %.2f (FA %.3f) | baseline det %.2f | margin %.3f pooled %.3f | pass=%s"
          % (e["snn_det_mean"], e["snn_fa_mean"], e["baseline_det_mean"], e["margin"], e["pooled_std"], e_go))
    print("VERDICT: %s" % ("GO" if res["verdict"]["GO"] else "NO-GO / UNDETERMINED (witness stays UNKNOWN)"))

    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("result -> %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
