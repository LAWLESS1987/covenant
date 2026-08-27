import json, hashlib, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor
IDS = json.load(open("/mnt/project/claude_phil_CORPUS_MANIFEST.json"))["ids"]
UA = {"User-Agent": "corpus-builder/1.0"}
START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I|re.S)
END   = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I|re.S)
def one(tid):
    p = f"/home/claude/jlens/books/{tid}.txt"
    if os.path.exists(p): return tid, True
    try:
        raw = urllib.request.urlopen(urllib.request.Request(
            f"https://www.gutenberg.org/cache/epub/{tid}/pg{tid}.txt", headers=UA), timeout=60).read()
    except Exception as e:
        return tid, f"ERR {e}"
    txt = None
    for enc in ("utf-8","latin-1"):
        try: txt = raw.decode(enc); break
        except UnicodeDecodeError: continue
    if not txt: return tid, "DECODE"
    m = START.search(txt)
    if m: txt = txt[m.end():]
    m = END.search(txt)
    if m: txt = txt[:m.start()]
    open(p,"w",encoding="utf-8").write(txt)
    return tid, True
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(one, IDS))
bad = [r for r in res if r[1] is not True]
print("fetched", len(res)-len(bad), "of", len(IDS), "failures:", bad, flush=True)
