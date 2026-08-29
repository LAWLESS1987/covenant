"""SEM1's lesson applied to SEM2's headline: score protocol C (10k random
anchors, test band src rank >= 4000, seed 0) on the cognate-free subset --
pairs where every gold translation has normalised Levenshtein similarity
< 0.5 to the source word. Embed scoring is character-blind, but the CLAIM
must hold where spelling scores nothing."""
import pickle, sys
import numpy as np
sys.path.insert(0, "/root/sem")
from cross_register import (load_pairs, procrustes, csls_scores,
                            target_hubness, ranks_of_gold, wilson)
from rapidfuzz.distance import Levenshtein

V, MC = 20000, 10
en = pickle.load(open(f"/root/sem/cache/en10_{V}_{MC}.pkl", "rb"))

for lang in ("fr", "de", "es"):
    tg = pickle.load(open(f"/root/sem/cache/{lang}10_{V}_{MC}.pkl", "rb"))
    gold = load_pairs(f"/root/sem/dict_en-{lang}.txt", en, tg)
    all_pairs = sorted(gold.items())
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(all_pairs))
    n_anch = min(10000, len(all_pairs) - 600)
    anch_set = set(idx[:n_anch].tolist())
    anchors = sorted((all_pairs[i][0], all_pairs[i][1][0]) for i in idx[:n_anch])
    test_pool = [(si, tis) for j, (si, tis) in enumerate(all_pairs)
                 if j not in anch_set and si >= 4000]
    pick = rng.choice(len(test_pool), size=min(600, len(test_pool)), replace=False)
    test = [test_pool[i] for i in sorted(pick)]

    A = np.array([a for a, _ in anchors]); B = np.array([b for _, b in anchors])
    W = procrustes(en.vecs[A], tg.vecs[B])
    src_idx = [s for s, _ in test]
    Q = en.vecs[src_idx] @ W
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-12
    r_t = target_hubness(Q, tg.vecs)
    ranks, cog = [], []
    for i, (si, tis) in enumerate(test):
        ranks.append(ranks_of_gold(csls_scores(Q[i], tg.vecs, r_t), tis))
        sim = max(Levenshtein.normalized_similarity(en.words[si], tg.words[t])
                  for t in tis)
        cog.append(sim)
    ranks = np.array(ranks); cog = np.array(cog)
    nc = cog < 0.5
    p10_all = float((ranks <= 10).mean())
    p10_nc = float((ranks[nc] <= 10).mean())
    lo, hi = wilson(p10_nc, int(nc.sum()))
    print(f"{lang}: all n={len(ranks)} P@10={p10_all:.3f} | "
          f"non-cognate n={int(nc.sum())} P@10={p10_nc:.3f} "
          f"wilson95=[{lo:.3f},{hi:.3f}] | cognate n={int((~nc).sum())} "
          f"P@10={float((ranks[~nc] <= 10).mean()):.3f}", flush=True)
