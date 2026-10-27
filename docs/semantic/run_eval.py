"""Build the spaces, run the cross-register eval, print the report."""
import json, os, sys, time
import numpy as np
sys.path.insert(0, "/root/sem")
from sem_core import tokenize, build_space
from cross_register import (load_pairs, split, evaluate, summarise, wilson)

CORPUS = "/root/sem/corpus"
LANGS = [l for l in sys.argv[1:]] or ["fr", "de", "es"]
VOCAB = 20000
MIN_COUNT = 10
ANCHOR_MAX = 4000        # supervised seed: the 4k most frequent English words
TEST_MIN = 4000          # held out: strictly rarer than every anchor
TEST_CAP = 600


CACHE = "/root/sem/cache"


def load(lang):
    import pickle
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f"{lang}_{VOCAB}_{MIN_COUNT}.pkl")
    if os.path.exists(cp):
        sp = pickle.load(open(cp, "rb"))
        print(f"space {lang} {sp.sig}  vocab={len(sp.words):,} "
              f"tokens={sp.n_tokens:,}  (cached)", flush=True)
        return sp
    p = os.path.join(CORPUS, f"{lang}.txt")
    t0 = time.time()
    toks = tokenize(open(p, encoding="utf-8", errors="ignore").read())
    sp = build_space(toks, lang, vocab_size=VOCAB, min_count=MIN_COUNT)
    pickle.dump(sp, open(cp, "wb"))
    print(f"space {lang} {sp.sig}  vocab={len(sp.words):,} "
          f"tokens={sp.n_tokens:,}  ({time.time()-t0:.0f}s)", flush=True)
    return sp


def main():
    en = load("en")
    report = {"en": {"sig": en.sig, "vocab": len(en.words), "tokens": en.n_tokens},
              "langs": {}}
    for lang in LANGS:
        tg = load(lang)
        gold = load_pairs(f"/root/sem/dict_en-{lang}.txt", en, tg)
        anchors, test = split(gold, ANCHOR_MAX, TEST_MIN, TEST_CAP)
        print(f"  {lang}: {len(gold):,} usable src words -> "
              f"{len(anchors):,} anchors, {len(test):,} held-out", flush=True)
        if len(anchors) < 200 or len(test) < 50:
            print(f"  {lang}: SKIPPED, too few pairs")
            continue
        res, per_pair, perm = evaluate(en, tg, gold, anchors, test)

        block = {"sig": tg.sig, "vocab": len(tg.words), "tokens": tg.n_tokens,
                 "n_anchors": len(anchors), "n_test": len(test),
                 "scorers": {k: summarise(v) for k, v in res.items()},
                 "perm_p10_mean": float(np.mean(perm)),
                 "perm_p10_max": float(np.max(perm))}

        # cognate-free subset: no gold translation within edit-similarity 0.5
        keep = [i for i, p in enumerate(per_pair) if p["ortho_sim"] < 0.5]
        block["n_noncognate"] = len(keep)
        block["noncognate"] = {k: summarise([res[k][i] for i in keep])
                               for k in res}
        block["cognate_share"] = round(1 - len(keep) / len(per_pair), 3)
        report["langs"][lang] = block
        with open(f"/root/sem/pairs_{lang}.json", "w") as f:
            json.dump(per_pair, f, indent=1)

    with open("/root/sem/report.json", "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
