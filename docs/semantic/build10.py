"""Build the 10M-token spaces (V=20000, MC=10 — same knobs as the 08-24 cache
files en_20000_10.pkl etc.). One language per invocation; skips if cached."""
import os, pickle, sys, time
sys.path.insert(0, "/root/sem")
from sem_core import tokenize, build_space

V, MC = 20000, 10

for lang in sys.argv[1:]:
    dst = f"/root/sem/cache/{lang}10_{V}_{MC}.pkl"
    if os.path.exists(dst):
        print(f"{lang}: cached")
        continue
    t0 = time.time()
    text = open(f"/root/sem/corpus10/{lang}.txt", encoding="utf-8").read()
    toks = tokenize(text)
    del text
    print(f"{lang}: {len(toks):,} tokens", flush=True)
    sp = build_space(toks, lang, vocab_size=V, min_count=MC)
    pickle.dump(sp, open(dst, "wb"))
    print(f"{lang}: V={len(sp.words)} sig={sp.sig} {time.time()-t0:.0f}s",
          flush=True)
