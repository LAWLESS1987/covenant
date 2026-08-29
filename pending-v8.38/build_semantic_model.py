"""build_semantic_model.py -- OFFLINE. Builds the model the semantic judge runs.

This is the only place numpy, scipy or a corpus is needed. The judge that ships
inside the node (covenant_semantic_judge.py) is pure stdlib and pure integer
arithmetic; it reads the JSON this writes and nothing else. The split is
deliberate: the node has to import the judge on a phone under Termux, where
`cryptography` already barely builds and scipy does not build at all.

================================================================
WHAT THIS REBUILDS, AND WHAT IS NOT RECOVERABLE
================================================================

`claude_SEMANTIC_JUDGE_TESTS.txt` records a judge `1b726f7fbe58`
(`veto_at=261 gate=[155,261)`) passing 23 checks on 2026-08-24, and
`claude_SEMANTIC_CORE_PROBE.txt` records the space it ran on, `87718a550f78`.
**Neither source survived.** A grep for the model id across the project and the
machine returns exactly one hit: the results file itself.

The space id was checked before a book was fetched, not assumed: sem_core's
signature is a hash of (lang, n_tokens, V, window, dim, alpha, min_count, seed),
so a 180-point parameter sweep was run against `87718a550f78`. No hit --
sem_core.py was written 08-24 23:15 and the probe is dated 08-24 12:33, so the
probe's builder predates the one that survived and is gone with the rest of that
run. This therefore does not restore `1b726f7fbe58`; it rebuilds the instrument
from the inputs that survived and records a new identity.

The corpus is the one thing that was pinned properly. `claude_phil_CORPUS_
MANIFEST.json` names 46 Gutenberg ids and its `approx_words: 2952375` matches
this tokenizer over those 46 books **to the digit**. (Its `corpus_sha256` does
not match any concatenation of them, so that field describes bytes that are also
gone -- recorded rather than quietly ignored.)

================================================================
THE INSTRUMENT
================================================================

From the surviving probe: whole-phrase similarity does NOT work -- topic
dominates, and 'hide the payment' scores 0.039 against a word-overlap trap at
0.623. What works is projection onto an INDUCED CONTRAST AXIS: +0.0660 'hide the
payment', +0.0661 'conceal the transfer', -0.0021 'make the payment'.

So: seed a family, induce its neighbours, build an axis, project onto it. Two
post-processing steps come from `claude_phil_align_ceiling.py`: mean-centre,
then remove the top 3 principal directions. Without that the leading components
carry frequency and register and every axis becomes a frequency detector.

**Induction sets the WEIGHTS. It does not set MEMBERSHIP, and that is a
measurement, not a preference.** Unfiltered, the top induced terms on the
appropriation axis were `sign` (530), `dream` (526), `legacy` (513),
`sweetheart` (470), `omen` (464), `foretells` (485) -- this corpus contains a
dream-interpretation dictionary, and its vocabulary sits exactly where wrongdoing
sits. Shipping that means **"sign the transfer" is rejected as theft at weight
530.** A frequency filter does not separate them either (`hide` is rank 2443,
`sweetheart` 3080, `omen` 1769).

So an induced word joins only if it is a morphological neighbour of a seed --
a shared prefix of >= PREFIX characters. That keeps precisely what induction was
advertised to find (`robbed`, `robbery`, `robbing`, `concealing`, `deceived` --
members nobody listed) and rejects the corpus artifacts. Every word in the
shipped model is then either one somebody wrote down or an inflection of one,
and every WEIGHT is still semantic: `hide` outranks `seize` 488 to 141 because
of where the space puts them, not because anyone said so.

Call it what it is: **a semantically weighted lexical detector, not a semantic
reasoner.** It is strictly stronger than MockJudge -- which is eight hardcoded
phrases with inverted logic -- it is deterministic, and it is one-way. It is not
an LLM and does not replace one.

================================================================
WHAT THIS MODEL CANNOT OBSERVE
================================================================

Four of the ten principles were built and only two are shipped, because two of
them measured badly and saying so is X4 ("principles this model cannot observe
are declared, not faked"):

  covet   the seeds are too rare here; the axis induced `kissing`, `elasticity`,
          `orthodoxy`, `seconded`. It is noise wearing a label.
  murder  in a philosophy-and-history corpus the violence axis is a WAR axis --
          `battle`, `soldiers`, `wounded`, `enemy`, `foe`. A corpus that cannot
          separate murder from a battlefield cannot judge whether a payment is
          violent, and shipping it would fire on `attack` and `danger`.

Two axes that work beat four where two are noise.

USAGE
    python build_semantic_model.py             build, self-check, write
    python build_semantic_model.py --report    print the full lexicon too
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys

import numpy as np

# -------------------------------------------------------------------------
# PATHS.  Parameterised 2026-08-29 (preflight_publish.py G5). This file named
# one machine's home directory six times, which published an account name AND
# meant the model could not be rebuilt anywhere else. A model whose build
# cannot be re-run is a set of weights nobody can check -- and this project
# already carries one of those in `supersedes`, whose source is simply gone.
# -------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
SEM = os.environ.get("COVENANT_SEMANTIC_DIR", HERE)
WORK = os.environ.get("COVENANT_SEMANTIC_WORK", HERE)
sys.path.insert(0, SEM)
try:
    from sem_core import build_space, tokenize  # noqa: E402
except ImportError:
    raise SystemExit(
        f"sem_core.py is not in {SEM}. Set COVENANT_SEMANTIC_DIR to the\n"
        f"directory holding it -- it is the space builder the shipped model\n"
        f"was fitted with, and no other implementation reproduces its ids.")

BOOKS = os.environ.get("COVENANT_CORPUS_DIR", os.path.join(WORK, "books"))
MANIFEST = os.environ.get("COVENANT_CORPUS_MANIFEST",
                          os.path.join(HERE, "CORPUS_MANIFEST.json"))
OUT = os.environ.get("COVENANT_MODEL_OUT",
                     os.path.join(HERE, "semantic_judge_model.json"))

# min_count=8 is align_ceiling's value and gives vocab 17,388 -- within 3% of the
# lost probe's 16,916, which is the closest thing to a provenance check available.
VOCAB, MINC, WINDOW, DIM, ALPHA, SEED = 30000, 8, 4, 300, 0.75, 0
D_REMOVE = 3        # align_ceiling's value
FAMILY = 40         # terms used to re-centre the axis after the first pass
PREFIX = 4          # morphological gate: shared prefix length with a seed
TOP_K = 2           # how many weights a score sums -- see the judge
SCALE = 1000

AXES = {
    "You shall not steal.": {
        "label": "appropriation",
        "seeds": ["steal", "stole", "stolen", "stealing", "theft", "thief",
                  "thieves", "rob", "robbed", "robbery", "robbing", "plunder",
                  "plundered", "seize", "seized", "seizure", "loot", "looted",
                  "usurp", "usurped", "forge", "forged", "forgery", "cheat",
                  "cheated", "dishonest", "dishonesty", "defraud", "embezzle",
                  "embezzlement", "misappropriate", "misappropriation",
                  "extort", "extortion", "pilfer", "purloin"],
    },
    "You shall not bear false witness.": {
        "label": "concealment",
        "seeds": ["lie", "lied", "lying", "falsehood", "false", "deceive",
                  "deceived", "deceiving", "deceit", "deceitful", "conceal",
                  "concealed", "concealing", "concealment", "hide", "hidden",
                  "hid", "hiding", "pretence", "pretend", "pretended",
                  "disguise", "disguised", "fraud", "fraudulent", "betray",
                  "betrayed", "perjury", "forswear", "misrepresent",
                  "falsify", "falsified"],
    },
}
NOT_OBSERVABLE = {
    "You shall have no other gods before Me.": "not evidenced by a transfer",
    "You shall not make for yourself a carved image.": "not evidenced by a transfer",
    "You shall not take the name of the Lord your God in vain.": "not evidenced by a transfer",
    "Remember the Sabbath day, to keep it holy.": "not evidenced by a transfer",
    "Honor your father and your mother.": "not evidenced by a transfer",
    "You shall not commit adultery.": "not evidenced by a transfer",
    "You shall not murder.": ("built and REJECTED: in this corpus the violence "
                              "axis is a war axis (battle, soldiers, wounded, "
                              "enemy) and would fire on 'attack' and 'danger'"),
    "You shall not covet.": ("built and REJECTED: seeds too rare here; the axis "
                             "induced kissing, elasticity, orthodoxy"),
}

# The separation set. Small, and the smallness is stated in the model file --
# eleven and eighteen is two observations, not a validation (M39).
PROBE_VIOLATING = [
    "drain all staked funds to attacker wallet, steal everything",
    "hide the payment", "conceal the transfer",
    "rob the treasury and lie about it",
    "seize the funds without authorisation",
    "forge the signature and take the balance",
    "stealing from the pool",
    "a fraudulent transfer, concealed from the ledger",
    "plunder the escrow", "a dishonest claim on the stake",
    "quietly move the balance and hide it from the ledger",
]
PROBE_BENIGN = [
    "make the payment", "gift to node B for helping with the sync",
    "send 10 to alice for the invoice", "quarterly settlement, agreed terms",
    "this will help everyone, greater good, divine unity",
    "stake 100 for 30 days", "reward distribution for block 4",
    "refund the overpayment to carol", "transfer 5 to the escrow account",
    "monthly subscription renewal", "node gift, thank you for the relay",
    "paying back the loan as agreed",
    "consensus reward, block 12, alignment 0.61",
    "operator authorised rebalance", "fee for the relay hop",
    "returning the deposit in full", "dividend payment to the pool",
    "settlement of the outstanding invoice",
    # the words the unfiltered induction would have fired on
    "sign the transfer", "a legacy payment to the estate",
    "the dream team relay bonus", "honors dividend, as declared",
]


def clean(vecs):
    X = vecs - vecs.mean(axis=0)
    pick = np.random.default_rng(0).choice(len(X), size=min(6000, len(X)),
                                           replace=False)
    _, _, Vt = np.linalg.svd(X[pick], full_matrices=False)
    T = Vt[:D_REMOVE]
    X = X - (X @ T.T) @ T
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)


def morphological(word, seeds):
    """Is `word` an inflection of one of `seeds`? Shared prefix, both ways."""
    for s in seeds:
        n = min(len(word), len(s))
        if n >= PREFIX and word[:PREFIX] == s[:PREFIX]:
            return s
    return None


def load_tokens():
    ids = json.load(open(MANIFEST))["ids"]
    cache = os.path.join(WORK, "tokens.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb")), ids
    toks = []
    for t in ids:
        toks.extend(tokenize(open(f"{BOOKS}/{t}.txt", encoding="utf-8").read()))
    pickle.dump(toks, open(cache, "wb"))
    return toks, ids


def get_space(tokens):
    cache = os.path.join(WORK, f"space_mc{MINC}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    sp = build_space(tokens, "phil", vocab_size=VOCAB, min_count=MINC,
                     window=WINDOW, dim=DIM, alpha=ALPHA, seed=SEED)
    pickle.dump(sp, open(cache, "wb"))
    return sp


def score(tokens, principles, top_k):
    """The judge's scoring, mirrored here so the bands are calibrated against
    the exact function that will run. Integer only, no division."""
    best, who, why = 0, None, []
    for p, weights in sorted(principles.items()):
        hits = sorted(((weights[t], t) for t in tokens if t in weights),
                      reverse=True)[:top_k]
        s = sum(v for v, _ in hits)
        if s > best:
            best, who, why = s, p, hits
    return best, who, why


def main():
    report = "--report" in sys.argv
    tokens, ids = load_tokens()
    sp = get_space(tokens)
    X = clean(sp.vecs)
    print(f"corpus {len(ids)} books / {len(tokens):,} tokens   "
          f"space {sp.sig} vocab={len(sp.words):,}", flush=True)

    principles, lexicons, rejected = {}, {}, {}
    for p, spec in AXES.items():
        seeds = spec["seeds"]
        have = [w for w in seeds if sp.has(w)]
        if not have:
            raise ValueError(f"no seed in vocabulary for {p}")
        c = np.mean([X[sp.index[w]] for w in have], axis=0)
        c /= np.linalg.norm(c) + 1e-12
        proj = X @ c
        fam = [sp.words[i] for i in np.argsort(-proj)[:FAMILY]
               if len(sp.words[i]) >= 3]
        c = np.mean([X[sp.index[w]] for w in sorted(set(have + fam))], axis=0)
        c /= np.linalg.norm(c) + 1e-12
        proj = X @ c

        weights = {w: int(round(SCALE * float(proj[sp.index[w]]))) for w in have}
        added, dropped = [], []
        for i in np.argsort(-proj)[:600]:
            w = sp.words[i]
            if w in weights or len(w) < PREFIX:
                continue
            v = int(round(SCALE * float(proj[i])))
            if v <= 0:
                break
            if morphological(w, seeds):
                weights[w] = v
                added.append(w)
            elif len(dropped) < 12:
                dropped.append(f"{w}({v})")
        weights = {w: v for w, v in weights.items() if v > 0}
        principles[p] = weights
        lexicons[p] = {"seeds_in_vocab": have, "induced_kept": added,
                       "induced_rejected_sample": dropped,
                       "missing_seeds": [w for w in seeds if not sp.has(w)]}
        rejected[p] = dropped
        print(f"  {spec['label']:14s} {len(weights):3d} words "
              f"({len(have)} seeds + {len(added)} morphological)  "
              f"rejected e.g. {dropped[:5]}", flush=True)

    # ------------------------------------------------------------ bands
    # Derived from the model rather than chosen: any single seed firing must at
    # least reach ABSTAIN, and the median seed weight is the veto. Both are
    # integers read off the lexicon, so they move with the model and cannot
    # drift away from it.
    seedw = sorted(principles[p][w] for p in principles
                   for w in lexicons[p]["seeds_in_vocab"] if w in principles[p])
    gate_lo = seedw[0]
    veto_at = seedw[len(seedw) // 2]
    print(f"\nseed weights: min={seedw[0]} median={veto_at} max={seedw[-1]}")
    print(f"bands: clean < {gate_lo} <= ABSTAIN < {veto_at} <= VIOLATES  "
          f"midpoint={(gate_lo + veto_at) // 2}")

    # -------------------------------------------------------- self-check
    def verdict(s):
        return "VIOLATES" if s >= veto_at else ("ABSTAIN" if s >= gate_lo
                                                else "clean")
    fp, fn = [], []
    for t in PROBE_BENIGN:
        s, _, why = score(tokenize(t), principles, TOP_K)
        if verdict(s) != "clean":
            fp.append((t, s, why))
        if report:
            print(f"  {s:5d} {verdict(s):9s} {t!r}")
    for t in PROBE_VIOLATING:
        s, p, why = score(tokenize(t), principles, TOP_K)
        if verdict(s) == "clean":
            fn.append((t, s))
        if report:
            print(f"  {s:5d} {verdict(s):9s} {str(why):28s} {t!r}")
    print(f"\nseparation: {len(PROBE_VIOLATING)} violating, "
          f"{len(PROBE_BENIGN)} benign -> "
          f"{len(fn)} false negative(s), {len(fp)} false positive(s)")
    for t, s, why in fp:
        print(f"  FALSE POSITIVE {s} {why} {t!r}")
    for t, s in fn:
        print(f"  FALSE NEGATIVE {s} {t!r}")

    model = {
        "format": "covenant-semantic-judge/1",
        "space_sig": sp.sig, "space_vocab": len(sp.words),
        "space_tokens": int(sp.n_tokens),
        "corpus_ids": ids, "corpus_manifest": os.path.basename(MANIFEST),
        "build": {"vocab": VOCAB, "min_count": MINC, "window": WINDOW,
                  "dim": DIM, "alpha": ALPHA, "seed": SEED,
                  "d_remove": D_REMOVE, "family": FAMILY, "prefix": PREFIX,
                  "scale": SCALE, "top_k": TOP_K},
        "gate_lo": gate_lo, "veto_at": veto_at, "top_k": TOP_K,
        "principles": principles, "lexicons": lexicons,
        "not_observable": NOT_OBSERVABLE,
        "separation": {"violating": len(PROBE_VIOLATING),
                       "benign": len(PROBE_BENIGN),
                       "false_negatives": len(fn), "false_positives": len(fp),
                       "caveat": "n=11 and n=22 is two observations, not a "
                                 "validation. Both sets are in the builder and "
                                 "are the author's own; no held-out data exists."},
        "supersedes": {"model": "1b726f7fbe58", "space": "87718a550f78",
                       "note": "source for both is gone; results files only"},
    }
    body = json.dumps(model, sort_keys=True, separators=(",", ":"))
    model["model_id"] = hashlib.sha256(body.encode()).hexdigest()[:12]
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(model, fh, sort_keys=True, indent=1)
        fh.write("\n")
    print(f"\nmodel {model['model_id']} -> {OUT} "
          f"({os.path.getsize(OUT):,} bytes)")
    return 1 if (fp or fn) else 0


if __name__ == "__main__":
    sys.exit(main())
