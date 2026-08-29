"""SEM2: does the supervision curve keep climbing at 10k anchors / 10M+ tokens?

The 08-24 prediction (IMPROVEMENT_LOG, SEM2): the anchor curve had not
flattened at 3.3k anchors / ~3M tokens (fr P@10 .010/.038/.055/.065/.078 at
250/500/1k/2k/3.3k, test band = src rank >= 4000). "If 10k anchors and 10M
tokens do not pass P@10 ~0.15, I am wrong and the method is the problem."

Three protocols, because anchors eat the test band and pretending otherwise
is contamination:

  A  TOKEN AXIS — byte-compatible with the 08-24 grid: anchors = in-vocab
     gold pairs with src rank < 4000 (lowest-rank first), test = pairs with
     src rank >= 4000, cap 600. Only the corpus changed (3M -> 11M tokens).
  B  ANCHOR AXIS, uncontaminated — anchors from src rank < 15000 (grid to
     10k), test = pairs with src rank >= 15000, cap 600. Harder band by
     construction (P@10 decays with rank — SEM1); the 08-24-style anchor set
     (rank < 4000) is also scored on this same band so the supervision gain
     is measured at fixed band.
  C  THE PREDICTION'S LETTER — 10k anchors sampled uniformly from ALL
     in-vocab gold pairs, test = 600 left-out pairs with src rank >= 4000
     (same band as protocol A/the 08-24 curve). Two seeds.

Embed-only scoring (CSLS), as in anchor_sweep.py. Permutation null (20
shuffles) at the headline points.
"""
import json, pickle, sys
import numpy as np
sys.path.insert(0, "/root/sem")
from cross_register import (load_pairs, split, procrustes, csls_scores,
                            target_hubness, ranks_of_gold, wilson)

V, MC = 20000, 10


def score(en, tg, anchors, test):
    A = np.array([a for a, _ in anchors]); B = np.array([b for _, b in anchors])
    W = procrustes(en.vecs[A], tg.vecs[B])
    src_idx = [s for s, _ in test]
    Q = en.vecs[src_idx] @ W
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-12
    r_t = target_hubness(Q, tg.vecs)
    r = np.array([ranks_of_gold(csls_scores(Q[i], tg.vecs, r_t), tis)
                  for i, (_, tis) in enumerate(test)])
    return r


def perm_null(en, tg, anchors, test, n_perm=20, seed=0):
    A = np.array([a for a, _ in anchors]); B = np.array([b for _, b in anchors])
    src_idx = [s for s, _ in test]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_perm):
        Bs = B.copy(); rng.shuffle(Bs)
        Wp = procrustes(en.vecs[A], tg.vecs[Bs])
        Qp = en.vecs[src_idx] @ Wp
        Qp /= np.linalg.norm(Qp, axis=1, keepdims=True) + 1e-12
        rp = target_hubness(Qp, tg.vecs)
        hits = sum(1 for i, (_, tis) in enumerate(test)
                   if ranks_of_gold(csls_scores(Qp[i], tg.vecs, rp), tis) <= 10)
        out.append(hits / len(test))
    return out


def row(tag, lang, n, r):
    print(f"{tag:<28}{lang:<5}{n:>7}{(r<=1).mean():>8.3f}{(r<=5).mean():>8.3f}"
          f"{(r<=10).mean():>8.3f}{np.median(r):>8.0f}  n_test={len(r)}",
          flush=True)


en = pickle.load(open(f"/root/sem/cache/en10_{V}_{MC}.pkl", "rb"))
print(f"en: {en.n_tokens:,} tokens sig={en.sig}")
print(f"{'protocol':<28}{'lang':<5}{'anch':>7}{'P@1':>8}{'P@5':>8}{'P@10':>8}{'med':>8}")

for lang in ("fr", "de", "es"):
    tg = pickle.load(open(f"/root/sem/cache/{lang}10_{V}_{MC}.pkl", "rb"))
    print(f"# {lang}: {tg.n_tokens:,} tokens sig={tg.sig}")
    gold = load_pairs(f"/root/sem/dict_en-{lang}.txt", en, tg)
    print(f"# {lang}: {len(gold)} in-vocab gold source words")

    # ---- A: token axis, 08-24 protocol verbatim -------------------------
    anchors, test = split(gold, 4000, 4000, 600)
    for n in (250, 500, 1000, 2000, 3300, len(anchors)):
        if n > len(anchors):
            continue
        r = score(en, tg, anchors[:n], test)
        row("A tokens (test>=4000)", lang, n, r)

    # ---- B: anchor axis, uncontaminated (test>=15000) -------------------
    anchors15, test15 = split(gold, 15000, 15000, 600)
    r = score(en, tg, anchors[: len(anchors)], test15)   # 08-24-style anchors, same band
    row("B fixed-band (anch<4000)", lang, len(anchors), r)
    for n in (2000, 4000, 6000, 8000, 10000, len(anchors15)):
        if n > len(anchors15):
            continue
        r = score(en, tg, anchors15[:n], test15)
        row("B anchors (test>=15000)", lang, n, r)

    # ---- C: the prediction's letter — 10k anchors, old band -------------
    all_pairs = sorted(gold.items())
    for seed in (0, 1):
        rng = np.random.default_rng(seed)
        idx = rng.permutation(len(all_pairs))
        n_anch = min(10000, len(all_pairs) - 600)
        anch_set = set(idx[:n_anch].tolist())
        anchors_c = sorted((all_pairs[i][0], all_pairs[i][1][0])
                           for i in idx[:n_anch])
        test_pool = [(si, tis) for j, (si, tis) in enumerate(all_pairs)
                     if j not in anch_set and si >= 4000]
        pick = rng.choice(len(test_pool), size=min(600, len(test_pool)),
                          replace=False)
        test_c = [test_pool[i] for i in sorted(pick)]
        r = score(en, tg, anchors_c, test_c)
        row(f"C 10k-rand s{seed} (>=4000)", lang, n_anch, r)
        p10 = float((r <= 10).mean())
        lo, hi = wilson(p10, len(r))
        print(f"    seed {seed}: P@10={p10:.3f} wilson95=[{lo:.3f},{hi:.3f}]",
              flush=True)
        if seed == 0:
            null = perm_null(en, tg, anchors_c, test_c, n_perm=20, seed=0)
            print(f"    perm null P@10: max={max(null):.4f} "
                  f"mean={np.mean(null):.4f} over 20 shuffles", flush=True)
