"""How much of the ceiling is supervision? Vary the anchor count only."""
import pickle, sys, numpy as np
sys.path.insert(0, "/root/sem")
from cross_register import (load_pairs, split, procrustes, csls_scores,
                            target_hubness, ranks_of_gold, wilson)

V, MC = 20000, 10
en = pickle.load(open(f"/root/sem/cache/en_{V}_{MC}.pkl", "rb"))
print(f"{'lang':<5}{'anchors':>9}{'P@1':>8}{'P@5':>8}{'P@10':>8}{'med':>8}")
for lang in ("fr", "de", "es"):
    tg = pickle.load(open(f"/root/sem/cache/{lang}_{V}_{MC}.pkl", "rb"))
    gold = load_pairs(f"/root/sem/dict_en-{lang}.txt", en, tg)
    anchors, test = split(gold, 4000, 4000, 600)
    src_idx = [s for s, _ in test]
    for n in (250, 500, 1000, 2000, len(anchors)):
        sub = anchors[:n]
        A = np.array([a for a, _ in sub]); B = np.array([b for _, b in sub])
        W = procrustes(en.vecs[A], tg.vecs[B])
        Q = en.vecs[src_idx] @ W
        Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-12
        r_t = target_hubness(Q, tg.vecs)
        r = np.array([ranks_of_gold(csls_scores(Q[i], tg.vecs, r_t), tis)
                      for i, (_, tis) in enumerate(test)])
        print(f"{lang:<5}{n:>9}{(r<=1).mean():>8.3f}{(r<=5).mean():>8.3f}"
              f"{(r<=10).mean():>8.3f}{np.median(r):>8.0f}", flush=True)
