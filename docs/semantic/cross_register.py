"""Cross-register (bilingual) retrieval, with the nulls the first eval lacked.

The 2026-08-24 14:05 result reported P@10=0.21 against a *uniform-random*
baseline of 0.00067 and called it above chance. Uniform-random is the wrong
null: it assumes an adversary with no knowledge at all. Two much cheaper
predictors are available to anyone holding the two vocabularies and no
semantics whatsoever --

  FREQ    a word's translation tends to sit at a similar frequency rank
  ORTHO   'gold'->'gold', 'secret'->'secret' need no space to find

-- and 2 of the 3 hits that eval printed as its best are identical strings.
This script scores the aligned space against BOTH, against their combination,
on the cognate-free subset, and against a permuted-anchor null.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

# ----------------------------------------------------------------- alignment


def procrustes(X, Y):
    """Orthogonal W minimising ||XW - Y||_F."""
    U, _, Vt = np.linalg.svd(X.T @ Y)
    return U @ Vt


def csls_scores(q, T, r_t, k=10):
    """CSLS: cosine, penalised by each candidate's mean similarity to the
    k nearest source vectors. Standard hubness correction -- without it a
    handful of target words are everyone's nearest neighbour."""
    s = T @ q
    return 2 * s - r_t


def target_hubness(Q, T, k=10, block=2048):
    """r_t: mean top-k similarity of each target word to the mapped queries."""
    out = np.zeros(T.shape[0])
    for i in range(0, T.shape[0], block):
        S = T[i:i + block] @ Q.T
        kk = min(k, S.shape[1])
        part = np.partition(S, -kk, axis=1)[:, -kk:]
        out[i:i + block] = part.mean(axis=1)
    return out


# -------------------------------------------------------------------- nulls


def freq_rank_scores(src_rank, n_tgt):
    """Score every target index by closeness in log frequency rank.
    Uses no vectors, no characters -- only the two frequency tables."""
    tr = np.arange(n_tgt, dtype=np.float64)
    return -np.abs(np.log1p(tr) - math.log1p(src_rank))


def ortho_scores(src_word, tgt_words):
    """Normalised Levenshtein similarity to every target word."""
    return process.cdist([src_word], tgt_words,
                         scorer=Levenshtein.normalized_similarity,
                         dtype=np.float32)[0].astype(np.float64)


# ------------------------------------------------------------------ scoring

def ranks_of_gold(scores, gold_idx):
    """Best (smallest) rank achieved by any gold translation."""
    order = np.argsort(-scores, kind="stable")
    pos = np.empty(scores.shape[0], dtype=np.int64)
    pos[order] = np.arange(scores.shape[0])
    return int(min(pos[g] for g in gold_idx)) + 1


def summarise(ranks, ks=(1, 5, 10)):
    r = np.array(ranks, dtype=float)
    out = {f"P@{k}": float((r <= k).mean()) for k in ks}
    out["median_rank"] = float(np.median(r))
    out["n"] = int(r.size)
    return out


def wilson(p, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# --------------------------------------------------------------------- main

def load_pairs(path, en_space, tgt_space):
    """MUSE ground-truth dictionary -> {src_idx: [tgt_idx, ...]}, in-vocab only."""
    gold = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) != 2:
                continue
            s, t = parts
            si, ti = en_space.index.get(s), tgt_space.index.get(t)
            if si is None or ti is None:
                continue
            gold.setdefault(si, [])
            if ti not in gold[si]:
                gold[si].append(ti)
    return gold


def split(gold, anchor_max_rank, test_min_rank, test_cap, seed=0):
    anchors, test = [], []
    for si, tis in gold.items():
        if si < anchor_max_rank:
            anchors.append((si, tis[0]))          # one translation per anchor
        elif si >= test_min_rank:
            test.append((si, tis))
    anchors.sort()
    test.sort()
    rng = np.random.default_rng(seed)
    if len(test) > test_cap:
        pick = rng.choice(len(test), size=test_cap, replace=False)
        test = [test[i] for i in sorted(pick)]
    return anchors, test


def evaluate(en, tg, gold, anchors, test, n_perm=20, seed=0):
    A = np.array([a for a, _ in anchors])
    B = np.array([b for _, b in anchors])
    W = procrustes(en.vecs[A], tg.vecs[B])

    src_idx = [s for s, _ in test]
    Q = en.vecs[src_idx] @ W
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-12
    r_t = target_hubness(Q, tg.vecs)

    tgt_words = tg.words
    res = {"embed": [], "freq": [], "ortho": [], "ortho+freq": [], "embed+ortho": []}
    per_pair = []
    for i, (si, tis) in enumerate(test):
        emb = csls_scores(Q[i], tg.vecs, r_t)
        frq = freq_rank_scores(si, len(tgt_words))
        ort = ortho_scores(en.words[si], tgt_words)
        combo = ort + 0.05 * frq
        eo = (emb - emb.mean()) / (emb.std() + 1e-12) + 2.0 * ort
        rr = {"embed": ranks_of_gold(emb, tis),
              "freq": ranks_of_gold(frq, tis),
              "ortho": ranks_of_gold(ort, tis),
              "ortho+freq": ranks_of_gold(combo, tis),
              "embed+ortho": ranks_of_gold(eo, tis)}
        for k, v in rr.items():
            res[k].append(v)
        best_ortho = max(ort[t] for t in tis)
        per_pair.append({"src": en.words[si], "src_rank": si,
                         "gold": [tgt_words[t] for t in tis[:4]],
                         "ortho_sim": round(float(best_ortho), 3),
                         **rr})

    # permuted-anchor null: same machinery, anchor pairing destroyed
    rng = np.random.default_rng(seed)
    perm_p10 = []
    for _ in range(n_perm):
        Bs = B.copy()
        rng.shuffle(Bs)
        Wp = procrustes(en.vecs[A], tg.vecs[Bs])
        Qp = en.vecs[src_idx] @ Wp
        Qp /= np.linalg.norm(Qp, axis=1, keepdims=True) + 1e-12
        rp = target_hubness(Qp, tg.vecs)
        hits = 0
        for i, (si, tis) in enumerate(test):
            if ranks_of_gold(csls_scores(Qp[i], tg.vecs, rp), tis) <= 10:
                hits += 1
        perm_p10.append(hits / len(test))

    return res, per_pair, perm_p10
