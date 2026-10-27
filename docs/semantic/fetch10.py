"""SEM2 corpus fetch: same deterministic sampling as fetch_corpus.py (seed
20260824, shuffle of the whole catalogue), extended from 3M to 10M words per
language. The 10M corpus is therefore (up to availability drift and thread
timing at the stop boundary) a superset of the 08-24 corpus. Ids recorded to
MANIFEST_10M.json per language as each finishes; resumable per language."""
import csv, json, os, re, sys, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor

CAT = "/root/sem/pg_catalog.csv"
OUT = "/root/sem/corpus10"
TARGET_WORDS = 11_300_000
UA = {"User-Agent": "corpus-builder/1.0"}
SEED = 20260824
csv.field_size_limit(10 ** 7)

START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)
END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)


def catalogue(lang):
    ids = []
    with open(CAT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Type"] != "Text" or row["Language"] != lang:
                continue
            try:
                ids.append(int(row["Text#"]))
            except ValueError:
                pass
    return ids


def fetch(tid):
    url = f"https://www.gutenberg.org/cache/epub/{tid}/pg{tid}.txt"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
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


def build(lang):
    import random
    ids = catalogue(lang)
    rng = random.Random(SEED)
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

    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(work, ids[:4000]))
    out.close()
    entry = {"ids": sorted(state["used"]), "approx_words": state["words"],
             "seed": SEED, "target_words": TARGET_WORDS,
             "catalogue_size": len(ids),
             "sampling": "deterministic shuffle of the whole catalogue"}
    mp = os.path.join(OUT, "MANIFEST_10M.json")
    manifest = json.load(open(mp)) if os.path.exists(mp) else {}
    manifest[lang] = entry
    json.dump(manifest, open(mp, "w"), indent=1)
    print(f"{lang}: {len(state['used'])} books ~{state['words']:,} words "
          f"(catalogue {len(ids):,})", flush=True)


if __name__ == "__main__":
    for lang in sys.argv[1:]:
        p = os.path.join(OUT, f"{lang}.txt")
        mp = os.path.join(OUT, "MANIFEST_10M.json")
        done = json.load(open(mp)) if os.path.exists(mp) else {}
        if lang in done:
            print(f"{lang}: already fetched ({done[lang]['approx_words']:,} words)")
            continue
        build(lang)
