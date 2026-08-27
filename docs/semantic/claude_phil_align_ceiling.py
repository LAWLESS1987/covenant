"""Is cos 0.104 a property of DIFFERENT BOOKS, or of DISJOINT TEXT at this scale?

I reported 0.104 as a Babel finding without establishing what the instrument can
reach at its best. That is the same error as the uniform-random null on 08-24:
a number with no ceiling beside it is not a measurement.

CONTROLS
  P  positive control   align A to ITSELF -> must be ~1.0, else the harness is wrong
  R  floor              random orthogonal transform -> must be ~0.0
  S  same-source        split half A into two disjoint quarters, same register,
                        same author pool, same sampling process. Align those.
                        If S ~= the A|B number, the finding is DATA QUANTITY and
                        my Babel reading is wrong.
  X  the measurement    A vs B, different books

Then, only if the gap survives: anchor count sweep and iterative refinement
(Procrustes -> mutual nearest neighbours -> re-anchor), because I named
alignment the binding constraint and a named constraint that is never attacked
is a recommendation, not a result.

Held-out words are fixed once and excluded from anchoring in EVERY condition.
"""
from __future__ import annotations
import os, pickle, sys
import numpy as np

sys.path.insert(0, "/home/claude/phil")
from sem_core import tokenize, build_space  # noqa: E402

RNG = np.random.default_rng(20260825)
D_REMOVE = 3
VOCAB, MINC, DIM = 12000, 8, 200


def clean(sp):
    X = sp.vecs - sp.vecs.mean(axis=0)
    n = min(6000, len(X))
    _, _, Vt = np.linalg.svd(X[np.random.default_rng(0).choice(len(X), size=n, replace=False)],
                             full_matrices=False)
    T = Vt[:D_REMOVE]
    X = X - (X @ T.T) @ T
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)


def procrustes(S, T):
    U, _, Vt = np.linalg.svd(S.T @ T)
    return U @ Vt


def get_space(text, name, vocab=VOCAB, minc=MINC, dim=DIM):
    p = f"/home/claude/phil/space_{name}.pkl"
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    sp = build_space(tokenize(text), name, vocab_size=vocab, min_count=minc,
                     window=4, dim=dim)
    pickle.dump(sp, open(p, "wb"))
    return sp


def align_score(S, XS, T, XT, n_anchors, held, refine=0, verbose=False):
    """Align S->T on n_anchors shared words; report mean cos on `held`."""
    shared = [w for w in S.words if T.has(w) and w not in held]
    anc = shared[:n_anchors]
    A = np.array([XS[S.index[w]] for w in anc])
    B = np.array([XT[T.index[w]] for w in anc])
    W = procrustes(A, B)

    for r in range(refine):
        Q = XS @ W
        Q /= (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-12)
        # mutual nearest neighbours over the 6k most frequent words in each space
        k = min(6000, len(S.words), len(T.words))
        Sm = Q[:k] @ XT[:k].T
        fwd = Sm.argmax(axis=1)
        bwd = Sm.argmax(axis=0)
        pairs = [(i, int(fwd[i])) for i in range(k)
                 if int(bwd[int(fwd[i])]) == i and S.words[i] not in held]
        if len(pairs) < 200:
            break
        A = np.array([XS[i] for i, _ in pairs])
        B = np.array([XT[j] for _, j in pairs])
        W = procrustes(A, B)
        if verbose:
            print(f"      refine {r+1}: {len(pairs)} mutual NN pairs")

    Q = XS @ W
    Q /= (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-12)
    hv = [w for w in held if S.has(w) and T.has(w)]
    return float(np.mean([Q[S.index[w]] @ XT[T.index[w]] for w in hv])), len(hv), W


def main():
    ta = open("/home/claude/phil/half_A.txt", encoding="utf-8").read()
    tb = open("/home/claude/phil/half_B.txt", encoding="utf-8").read()
    A, B = get_space(ta, "A"), get_space(tb, "B")
    XA, XB = clean(A), clean(B)

    shared_ab = [w for w in A.words if B.has(w)]
    heldout = set(RNG.choice(shared_ab, size=1500, replace=False).tolist())
    print(f"held-out shared words fixed at {len(heldout)}, excluded from anchoring everywhere\n")

    print("=" * 72)
    print("CONTROLS")
    print("=" * 72)

    s, n, _ = align_score(A, XA, A, XA, 4000, heldout)
    print(f"  P positive  A -> A (self)                      cos = {s:+.3f}  n={n}")

    Wr = np.linalg.qr(np.random.default_rng(1).standard_normal((XA.shape[1], XA.shape[1])))[0]
    hv = [w for w in heldout if A.has(w) and B.has(w)]
    Qr = XA @ Wr
    Qr /= (np.linalg.norm(Qr, axis=1, keepdims=True) + 1e-12)
    sr = float(np.mean([Qr[A.index[w]] @ XB[B.index[w]] for w in hv]))
    print(f"  R floor     random orthogonal transform         cos = {sr:+.3f}  n={len(hv)}")

    # S: same source, disjoint text. Split half A's books in two.
    docs = ta.split("\n\n\n")
    if len(docs) < 4:
        cut = len(ta) // 2
        a1, a2 = ta[:cut], ta[cut:]
    else:
        a1 = "\n\n\n".join(docs[::2]); a2 = "\n\n\n".join(docs[1::2])
    A1 = get_space(a1, "A1"); A2 = get_space(a2, "A2")
    X1, X2 = clean(A1), clean(A2)
    s1, n1, _ = align_score(A1, X1, A2, X2, 4000, heldout)
    print(f"  S same-src  A1 -> A2  ({A1.n_tokens:,} / {A2.n_tokens:,} tokens)   "
          f"cos = {s1:+.3f}  n={n1}")

    sx, nx, _ = align_score(A, XA, B, XB, 4000, heldout)
    print(f"  X measured  A -> B    ({A.n_tokens:,} / {B.n_tokens:,} tokens)   "
          f"cos = {sx:+.3f}  n={nx}")

    print(f"\n  gap attributable to DIFFERENT BOOKS rather than disjoint text: "
          f"{sx - s1:+.3f}")
    print(f"  headroom to the same-source condition: {s1 - sx:+.3f}")

    print("\n" + "=" * 72)
    print("ATTACKING THE CONSTRAINT -- anchors and refinement, A -> B")
    print("=" * 72)
    print(f"  {'anchors':>8}{'plain':>10}{'+1 refine':>12}{'+3 refine':>12}")
    for na in (500, 1000, 2000, 4000, 6000):
        r0, _, _ = align_score(A, XA, B, XB, na, heldout, refine=0)
        r1, _, _ = align_score(A, XA, B, XB, na, heldout, refine=1)
        r3, _, _ = align_score(A, XA, B, XB, na, heldout, refine=3)
        print(f"  {na:>8}{r0:>10.3f}{r1:>12.3f}{r3:>12.3f}", flush=True)

    print("\n  same sweep on the SAME-SOURCE pair, for the ceiling:")
    print(f"  {'anchors':>8}{'plain':>10}{'+3 refine':>12}")
    for na in (1000, 4000):
        r0, _, _ = align_score(A1, X1, A2, X2, na, heldout, refine=0)
        r3, _, _ = align_score(A1, X1, A2, X2, na, heldout, refine=3)
        print(f"  {na:>8}{r0:>10.3f}{r3:>12.3f}", flush=True)


if __name__ == "__main__":
    main()
