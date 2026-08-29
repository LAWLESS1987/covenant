"""SEM3: the contrast-axis instrument (SEMANTIC_CORE_PROBE test C) at real n.

The 08-24 probe's test C was three phrases and no null. This runs the same
instrument — projection onto an induced contrast axis, built with the exact
recipe build_semantic_model.py ships (mean-centre, top-3 PC removal, seed
centroid, FAMILY=40 re-centre) — over a combinatorial battery of ~600 triples
on the 10M-token en space, with three nulls:

  N1  label permutation over phrases  (does the axis separate covert from
      innocent better than chance labelling)
  N2  binomial sign test on the triple statistic (paraphrase-closer-than-trap)
  N3  random axes from frequency-matched random seed sets (is the SEED CHOICE
      doing the work, or would any axis of this construction separate)

Three phrase classes per axis:
  covert      verb from the axis's seed family (pool A anchors, pool B
              paraphrases — vocabulary-disjoint from pool A)
  covert_oov  verb with covert meaning but OUTSIDE the seed families and
              their 4-char morphological neighbourhoods — the space must
              generalise for these to score; the shipped lexicon cannot
  innocent    innocent verb, SAME noun as the anchor (the word-overlap trap)

Everything is deterministic given SEED; run it twice and diff.
"""
import hashlib
import json
import pickle
import sys

import numpy as np

sys.path.insert(0, "/home/claude/sem3")

SEED = 20260829
D_REMOVE = 3          # build_semantic_model.py values, verbatim
FAMILY = 40
PREFIX = 4
N_RANDOM_AXES = 200
N_PERM = 2000
TRIPLE_CAP_PER_AXIS = 300

AXES = {
    "concealment": {
        "seeds": ["lie", "lied", "lying", "falsehood", "false", "deceive",
                  "deceived", "deceiving", "deceit", "deceitful", "conceal",
                  "concealed", "concealing", "concealment", "hide", "hidden",
                  "hid", "hiding", "pretence", "pretend", "pretended",
                  "disguise", "disguised", "fraud", "fraudulent", "betray",
                  "betrayed", "perjury", "forswear", "misrepresent",
                  "falsify", "falsified"],
        "pool_a": ["hide", "hidden", "concealing", "deceive", "falsified"],
        "pool_b": ["conceal", "hid", "disguised", "deceiving", "misrepresent"],
        "oov":    ["smuggle", "smuggled", "suppress", "obscure", "mask",
                   "veil", "cloak", "bury", "withhold", "camouflage"],
    },
    "appropriation": {
        "seeds": ["steal", "stole", "stolen", "stealing", "theft", "thief",
                  "thieves", "rob", "robbed", "robbery", "robbing", "plunder",
                  "plundered", "seize", "seized", "seizure", "loot", "looted",
                  "usurp", "usurped", "forge", "forged", "forgery", "cheat",
                  "cheated", "dishonest", "dishonesty", "defraud", "embezzle",
                  "embezzlement", "misappropriate", "misappropriation",
                  "extort", "extortion", "pilfer", "purloin"],
        "pool_a": ["steal", "stole", "robbed", "plundered", "embezzle"],
        "pool_b": ["rob", "stolen", "seize", "looted", "pilfer"],
        "oov":    ["pocket", "swipe", "snatch", "abscond", "appropriate",
                   "confiscate", "ransack", "despoil", "filch", "swindle"],
    },
}

INNOCENT_VERBS = ["make", "send", "record", "announce", "declare", "deliver",
                  "receive", "count", "return", "accept", "share", "present",
                  "bring", "collect", "complete"]

NOUN_PAIRS = [("payment", "transfer"), ("money", "cash"), ("gold", "silver"),
              ("letter", "papers"), ("jewels", "treasure"),
              ("fortune", "wealth"), ("inheritance", "estate"),
              ("wages", "earnings"), ("deed", "documents"),
              ("goods", "merchandise"), ("purse", "wallet"),
              ("debt", "loan"), ("accounts", "ledger"), ("rent", "dues"),
              ("profits", "proceeds"), ("savings", "deposit")]


def clean(vecs, rng_seed=0):
    X = vecs - vecs.mean(axis=0)
    pick = np.random.default_rng(rng_seed).choice(len(X), size=min(6000, len(X)),
                                                  replace=False)
    _, _, Vt = np.linalg.svd(X[pick], full_matrices=False)
    T = Vt[:D_REMOVE]
    X = X - (X @ T.T) @ T
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)


def build_axis(space, X, seeds):
    have = [w for w in seeds if space.has(w)]
    c = np.mean([X[space.index[w]] for w in have], axis=0)
    c /= np.linalg.norm(c) + 1e-12
    proj = X @ c
    fam = [space.words[i] for i in np.argsort(-proj)[:FAMILY]
           if len(space.words[i]) >= 3]
    c = np.mean([X[space.index[w]] for w in sorted(set(have + fam))], axis=0)
    c /= np.linalg.norm(c) + 1e-12
    return c, have


def phrase_vec(space, X, phrase):
    toks = [t for t in phrase.split() if space.has(t)]
    if not toks:
        return None
    return np.mean([X[space.index[t]] for t in toks], axis=0)


def morphologically_related(word, seeds):
    for s in seeds:
        if min(len(word), len(s)) >= PREFIX and word[:PREFIX] == s[:PREFIX]:
            return True
    return False


def auc(pos, neg):
    """Mann-Whitney AUC, ties counted half."""
    pos, neg = np.asarray(pos), np.asarray(neg)
    wins = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def main():
    space = pickle.load(open("/home/claude/sem3/cache/en10_20000_10.pkl", "rb"))
    print(f"space {space.sig} V={len(space.words):,} tokens={space.n_tokens:,}")
    X = clean(space.vecs)

    all_seeds = AXES["concealment"]["seeds"] + AXES["appropriation"]["seeds"]
    rng = np.random.default_rng(SEED)
    report = {"space_sig": space.sig, "seed": SEED}

    for axis_name, spec in AXES.items():
        c, have = build_axis(space, X, spec["seeds"])
        pa = [v for v in spec["pool_a"] if space.has(v)]
        pb = [v for v in spec["pool_b"] if space.has(v)]
        oov = [v for v in spec["oov"] if space.has(v)
               and not morphologically_related(v, all_seeds)]
        inn = [v for v in INNOCENT_VERBS if space.has(v)]
        pairs = [(a, b) for a, b in NOUN_PAIRS if space.has(a) and space.has(b)]
        dropped = {
            "pool_a": [v for v in spec["pool_a"] if not space.has(v)],
            "pool_b": [v for v in spec["pool_b"] if not space.has(v)],
            "oov_dropped": [v for v in spec["oov"] if v not in oov],
            "noun_pairs": [p for p in NOUN_PAIRS if p not in pairs],
        }

        triples, k = [], 0
        for n1, n2 in pairs:
            for va in pa:
                for vb in pb:
                    if len(triples) >= TRIPLE_CAP_PER_AXIS:
                        break
                    vi = inn[k % len(inn)]; k += 1
                    triples.append((f"{va} the {n1}", f"{vb} the {n2}",
                                    f"{vi} the {n1}"))
        oov_phrases = [f"{v} the {n1}" for n1, _ in pairs for v in oov]

        pv = {p: phrase_vec(space, X, p)
              for t in triples for p in t}
        pv.update({p: phrase_vec(space, X, p) for p in oov_phrases})
        proj = {p: float(v @ c) for p, v in pv.items() if v is not None}

        cov = [proj[a] for a, _, _ in triples] + [proj[b] for _, b, _ in triples]
        trp = [proj[t] for _, _, t in triples]
        ov = [proj[p] for p in oov_phrases if p in proj]

        # --- S1: separation + N1 label permutation --------------------
        a_real = auc(cov, trp)
        pool = np.array(cov + trp)
        lab = np.array([1] * len(cov) + [0] * len(trp))
        worse = 0
        for s in range(2):
            r = np.random.default_rng(SEED + s)
            for _ in range(N_PERM):
                sh = r.permutation(lab)
                if auc(pool[sh == 1], pool[sh == 0]) >= a_real:
                    worse += 1
        p_perm = (worse + 1) / (2 * N_PERM + 1)

        a_oov = auc(ov, trp) if ov else None

        # --- S2: the triple statistic + similarity control ------------
        ax_wins = sim_trap_wins = 0
        for a, b, t in triples:
            if abs(proj[a] - proj[b]) < abs(proj[a] - proj[t]):
                ax_wins += 1
            va, vb, vt = pv[a], pv[b], pv[t]
            cos_ab = float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb)))
            cos_at = float(va @ vt / (np.linalg.norm(va) * np.linalg.norm(vt)))
            if cos_at > cos_ab:
                sim_trap_wins += 1
        n = len(triples)
        # exact binomial upper tail under p=.5, via log to stay stable
        from math import lgamma, exp
        def binom_p_ge(kk, nn):
            tot = 0.0
            for i in range(kk, nn + 1):
                tot += exp(lgamma(nn + 1) - lgamma(i + 1) - lgamma(nn - i + 1)
                           - nn * np.log(2.0))
            return tot
        p_triple = binom_p_ge(ax_wins, n)

        # --- N3: random frequency-matched axes ------------------------
        ranks = np.array([space.index[w] for w in have])
        a_null = []
        for _ in range(N_RANDOM_AXES):
            fake = []
            for rk in ranks:
                lo, hi = max(0, rk // 2), min(len(space.words) - 1, rk * 2)
                fake.append(space.words[int(rng.integers(lo, hi + 1))])
            fc, _ = build_axis(space, X, fake)
            fp = {p: float(v @ fc) for p, v in pv.items() if v is not None}
            a_null.append(auc(
                [fp[a] for a, _, _ in triples] + [fp[b] for _, b, _ in triples],
                [fp[t] for _, _, t in triples]))
        a_null = np.array(a_null)
        p_axis = (int((a_null >= a_real).sum()) + 1) / (N_RANDOM_AXES + 1)

        report[axis_name] = {
            "n_triples": n, "n_oov_phrases": len(ov), "dropped": dropped,
            "mean_proj": {"covert": round(float(np.mean(cov)), 4),
                          "covert_oov": round(float(np.mean(ov)), 4) if ov else None,
                          "innocent_trap": round(float(np.mean(trp)), 4)},
            "S1_auc_covert_vs_trap": round(float(a_real), 4),
            "N1_perm_p": round(p_perm, 6),
            "S1b_auc_oov_vs_trap": round(float(a_oov), 4) if a_oov else None,
            "S2_axis_paraphrase_closer": f"{ax_wins}/{n}",
            "S2_p_binomial": f"{p_triple:.3g}",
            "S2_similarity_trap_wins": f"{sim_trap_wins}/{n}",
            "N3_random_axis_auc": {"mean": round(float(a_null.mean()), 4),
                                   "max": round(float(a_null.max()), 4),
                                   "p": round(p_axis, 6)},
        }
        r = report[axis_name]
        print(f"\n== {axis_name} ==  triples={n} oov={len(ov)}")
        print(f"  mean proj  covert {r['mean_proj']['covert']:+.4f}  "
              f"oov {r['mean_proj']['covert_oov']:+.4f}  "
              f"trap {r['mean_proj']['innocent_trap']:+.4f}")
        print(f"  S1  AUC covert-vs-trap {r['S1_auc_covert_vs_trap']}  "
              f"perm p={r['N1_perm_p']}")
        print(f"  S1b AUC oov-vs-trap    {r['S1b_auc_oov_vs_trap']}")
        print(f"  S2  axis: paraphrase closer than trap {r['S2_axis_paraphrase_closer']} "
              f"(p={r['S2_p_binomial']});  similarity: trap wins "
              f"{r['S2_similarity_trap_wins']}")
        print(f"  N3  random axes AUC mean {r['N3_random_axis_auc']['mean']} "
              f"max {r['N3_random_axis_auc']['max']}  p={r['N3_random_axis_auc']['p']}")

    body = json.dumps(report, sort_keys=True)
    print(f"\nreport sha256 {hashlib.sha256(body.encode()).hexdigest()[:16]}")
    json.dump(report, open("/home/claude/sem3/SEM3_AXIS_REPORT.json", "w"),
              indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
