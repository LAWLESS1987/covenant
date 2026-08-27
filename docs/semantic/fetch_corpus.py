"""Fetch a size-matched, register-matched Gutenberg corpus for en/fr/de/es.

Two things the first attempt got wrong, and both are confounds for a
cross-lingual retrieval score:

  SIZE      English reached 3.5M words while French stalled at 1.6M. A
            smaller target corpus has a smaller, noisier vocabulary and
            retrieval degrades for reasons that have nothing to do with
            alignment.
  REGISTER  Taking the LOWEST ebook ids gives English the Bible and the US
            founding documents while giving French and Spanish 19th-century
            novels. That is a register mismatch dressed up as a language gap
            -- in an evaluation whose own name is CROSS_REGISTER.

So: a deterministic random sample across each language's whole catalogue,
downloaded in parallel, stopped at the same token target for every language.
The ids used are written to MANIFEST.json so the corpus is reproducible.
"""
import csv
import json
import os
import re
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CAT = "/root/sem/pg_catalog.csv"
OUT = "/root/sem/corpus"
TARGET_WORDS = 3_000_000
LANGS = ("en", "fr", "de", "es")
UA = {"User-Agent": "corpus-builder/1.0"}
SEED = 20260824
csv.field_size_limit(10 ** 7)

START = re.compile(
    r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    re.I | re.S)
END = re.compile(
    r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    re.I | re.S)


def catalogue():
    by = {l: [] for l in LANGS}
    with open(CAT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Type"] != "Text":
                continue
            l = row["Language"]
            if l in by:
                try:
                    by[l].append(int(row["Text#"]))
                except ValueError:
                    pass
    return by


def fetch(tid):
    url = f"https://www.gutenberg.org/cache/epub/{tid}/pg{tid}.txt"
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=40).read()
    except Exception:
        return None
    txt = None
    for enc in ("utf-8", "latin-1"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not txt or len(txt) < 20_000:
        return None
    m = START.search(txt)
    if m:
        txt = txt[m.end():]
    m = END.search(txt)
    if m:
        txt = txt[:m.start()]
    return txt if txt.count(" ") >= 5_000 else None


def build(lang, ids):
    import random
    rng = random.Random(SEED)
    ids = ids[:]
    rng.shuffle(ids)
    lock = threading.Lock()
    state = {"words": 0, "used": [], "stop": False}
    out = open(os.path.join(OUT, f"{lang}.txt"), "w", encoding="utf-8")

    def work(tid):
        if state["stop"]:
            return
        body = fetch(tid)
        if not body:
            return
        n = body.count(" ")
        with lock:
            if state["stop"]:
                return
            out.write(body)
            out.write("\n")
            state["words"] += n
            state["used"].append(tid)
            if state["words"] >= TARGET_WORDS:
                state["stop"] = True
                print(f"  {lang} target reached at {state['words']:,}",
                      flush=True)

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(work, ids[:1500]))
    out.close()
    print(f"{lang}: {len(state['used'])} books ~{state['words']:,} words",
          flush=True)
    return {"ids": sorted(state["used"]), "approx_words": state["words"],
            "seed": SEED,
            "sampling": "deterministic shuffle of the whole catalogue"}


def main():
    by = catalogue()
    manifest = {}
    for lang in LANGS:
        print(f"{lang}: catalogue has {len(by[lang]):,} texts", flush=True)
        manifest[lang] = build(lang, by[lang])
        with open(os.path.join(OUT, "MANIFEST.json"), "w") as f:
            json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
