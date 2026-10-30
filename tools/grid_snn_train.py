"""Train the grid SNN witness per the sealed prereg and score it held-out vs baselines.
Run with the spiking-lab venv. Records numbers only; the verdict goes in the prereg."""
import sys, json
sys.path.insert(0, r"C:\Users\Lawre\covenant")
sys.path.insert(0, r"C:\Users\Lawre\covenant\tools")
import numpy as np, torch, torch.nn as nn
import snntorch as snn
import grid_snn_bench as B
import covenant_grid_snn as G

CH = ("breaker", "shed", "setpoint_delta", "interval", "zones_active")

def feats(rows):
    enc = G.encode_window(rows, now=max(r["issued_utc"] for r in rows) + 1)
    f = []
    for c in CH:
        f.append(enc[c].sum(axis=1)); f.append((enc[c] > 0).sum(axis=1))
    return np.stack(f, axis=1).astype(np.float32)          # [60, 10]

class Net(nn.Module):
    def __init__(s, h=32):
        super().__init__()
        s.f1 = nn.Linear(10, h); s.l1 = snn.Leaky(beta=0.9)
        s.f2 = nn.Linear(h, 1); s.l2 = snn.Leaky(beta=0.9, output=True)
    def forward(s, x):                                     # x [B,T,10]
        m1 = s.l1.init_leaky(); m2 = s.l2.init_leaky(); acc = 0
        for t in range(x.shape[1]):
            sp1, m1 = s.l1(s.f1(x[:, t]), m1)
            sp2, m2 = s.l2(s.f2(sp1), m2)
            acc = acc + m2.squeeze(-1)
        return acc / x.shape[1]

def dataset(fam, seed, n):
    ben = [feats(B.gen("benign" + fam, seed * 1000 + i)) for i in range(n)]
    att = [feats(B.gen(fam, seed * 1000 + 500 + i)) for i in range(n)]
    X = np.stack(ben + att); y = np.array([0] * n + [1] * n, dtype=np.float32)
    return X, y

def train_eval(Xtr, ytr, Xva_b, Xte_b, Xte_a, seed):
    torch.manual_seed(seed)
    sc = Xtr.reshape(-1, 10).std(0) + 1e-6
    T = lambda a: torch.tensor(a / sc)
    net = Net(); opt = torch.optim.Adam(net.parameters(), 5e-3); lf = nn.BCEWithLogitsLoss()
    Xt, yt = T(Xtr), torch.tensor(ytr)
    for ep in range(60):
        perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 32):
            b = perm[i:i + 32]; opt.zero_grad(); loss = lf(net(Xt[b]), yt[b]); loss.backward(); opt.step()
    with torch.no_grad():
        sv = net(T(Xva_b)).numpy(); sb = net(T(Xte_b)).numpy(); sa = net(T(Xte_a)).numpy()
    thr = np.quantile(sv, 0.99)
    return float((sa > thr).mean()), float((sb > thr).mean())

res = {}
for fam in ("A", "B", "C", "D"):
    dets, fas = [], []
    for seed in (1, 2, 3, 4, 5):
        X, y = dataset(fam, seed, 80)
        n = 80; idx_b = np.arange(n); idx_a = np.arange(n, 2 * n)
        tr = np.r_[idx_b[:40], idx_a[:40]]
        d, f = train_eval(X[tr], y[tr], X[idx_b[40:60]], X[idx_b[60:]], X[idx_a[60:]], seed)
        dets.append(d); fas.append(f)
    res[fam] = (np.mean(dets), np.std(dets), np.mean(fas))
    print("SNN family %s: test detection %.2f +/- %.2f  test FA %.3f" % (fam, *res[fam]), flush=True)

# prereg bar #3: held-out family (train on A,B,C; test on D)
Xs, ys = [], []
for fam in ("A", "B", "C"):
    X, y = dataset(fam, 7, 60); Xs.append(X); ys.append(y)
Xtr = np.concatenate(Xs); ytr = np.concatenate(ys)
Xd, yd = dataset("D", 8, 60)
d, f = train_eval(Xtr, ytr, Xd[:30], Xd[30:60], Xd[60:], 9)
print("SNN held-out family D (trained on A,B,C): detection %.2f  FA %.3f" % (d, f), flush=True)
json.dump({"per_family": res, "heldout_D": [d, f]}, open(r"C:\Users\Lawre\AppData\Local\Temp\claude\C--Users-Lawre-covenant\e2a52397-a294-4dd2-8829-b5479a522d8e\scratchpad\snn_train_result.json", "w"))
