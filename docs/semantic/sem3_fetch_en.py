"""SEM3: fetch the EXACT en ids in CORPUS_MANIFEST_10M.json (no sampling —
the manifest pins them; M40). Concatenation order = sorted id order, stated
in the results doc. Gutenberg strip identical to fetch10.py."""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

OUT = "/home/claude/sem3/corpus_en.txt"
BOOKS = "/home/claude/sem3/books"
UA = {"User-Agent": "corpus-builder/1.0"}
START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)
END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)

def fetch(tid):
    dst = f"{BOOKS}/{tid}.txt"
    if os.path.exists(dst):
        return tid, True
    url = f"https://www.gutenberg.org/cache/epub/{tid}/pg{tid}.txt"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    except Exception as e:
        return tid, f"ERR {e}"
    txt = None
    for enc in ("utf-8", "latin-1"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not txt:
        return tid, "ERR decode"
    m = START.search(txt)
    if m:
        txt = txt[m.end():]
    m = END.search(txt)
    if m:
        txt = txt[:m.start()]
    with open(dst, "w", encoding="utf-8") as f:
        f.write(txt)
    return tid, True

if __name__ == "__main__":
    ids = json.load(open("/home/claude/sem3/manifest_en.json"))["en"]["ids"]
    with ThreadPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(fetch, ids))
    bad = [(t, r) for t, r in res if r is not True]
    print(f"{len(ids)} ids, {len(bad)} failed")
    for t, r in bad:
        print("  ", t, r)
    if not bad:
        with open(OUT, "w", encoding="utf-8") as out:
            for tid in sorted(ids):
                out.write(open(f"{BOOKS}/{tid}.txt", encoding="utf-8").read())
                out.write("\n")
        print("concat ->", OUT, os.path.getsize(OUT), "bytes")
