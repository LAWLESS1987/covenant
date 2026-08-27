"""Count-based semantic space: PPMI over a sliding window, then truncated SVD.

Deliberately not a neural embedding. Everything here is a deterministic
function of (corpus bytes, vocab_size, window, dim, seed) and the space
carries a sha256 of those inputs so two runs can prove they used the same one.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import svds

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def tokenize(text: str):
    text = unicodedata.normalize("NFC", text.lower())
    return WORD.findall(text)


@dataclass
class Space:
    lang: str
    words: list          # index -> word, ordered by descending frequency
    index: dict          # word -> index
    vecs: np.ndarray     # (V, d) unit-norm rows
    counts: np.ndarray   # (V,) raw unigram counts
    n_tokens: int
    sig: str

    def rank(self, w):
        return self.index.get(w)

    def has(self, w):
        return w in self.index


def build_space(tokens, lang, vocab_size=20000, min_count=20, window=4,
                dim=300, alpha=0.75, seed=0):
    from collections import Counter
    c = Counter(tokens)
    kept = [(w, n) for w, n in c.most_common() if n >= min_count][:vocab_size]
    words = [w for w, _ in kept]
    counts = np.array([n for _, n in kept], dtype=np.float64)
    index = {w: i for i, w in enumerate(words)}
    V = len(words)

    ids = np.fromiter((index.get(t, -1) for t in tokens), dtype=np.int64,
                      count=len(tokens))
    M = sp.csr_matrix((V, V), dtype=np.float32)
    for off in range(1, window + 1):
        a, b = ids[:-off], ids[off:]
        m = (a >= 0) & (b >= 0)
        a = a[m].astype(np.int32); b = b[m].astype(np.int32)
        w = np.float32(1.0 / off)          # harmonic weighting, both directions
        v = np.full(a.size, w, dtype=np.float32)
        M = M + sp.coo_matrix((v, (a, b)), shape=(V, V)).tocsr()
        M = M + sp.coo_matrix((v, (b, a)), shape=(V, V)).tocsr()
        del a, b, v

    # PPMI with context-distribution smoothing
    M = M.astype(np.float64)
    total = M.sum()
    rsum = np.asarray(M.sum(axis=1)).ravel()
    csum = np.asarray(M.sum(axis=0)).ravel() ** alpha
    csum_tot = csum.sum()
    M = M.tocoo()
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((M.data * total * csum_tot)
                     / (rsum[M.row] * csum[M.col] * total))
    pmi[~np.isfinite(pmi)] = 0.0
    pmi = np.maximum(pmi, 0.0)
    keep = pmi > 0
    P = sp.coo_matrix((pmi[keep], (M.row[keep], M.col[keep])),
                      shape=(V, V)).tocsr()

    k = min(dim, min(P.shape) - 1)
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(min(P.shape))
    U, S, _ = svds(P, k=k, v0=v0)
    order = np.argsort(-S)
    U, S = U[:, order], S[order]
    X = U * (S ** 0.5)                      # eigenvalue weighting p=0.5
    X /= (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)

    sig = hashlib.sha256(
        f"{lang}|{len(tokens)}|{V}|{window}|{dim}|{alpha}|{min_count}|{seed}"
        .encode()).hexdigest()[:12]
    return Space(lang, words, index, X, counts, len(tokens), sig)
