import json, hashlib, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# PATHS.  Parameterised 2026-08-29, because preflight_publish.py's G5 found this
# file naming one machine's home directory. Two things were wrong with that, and
# only one of them is privacy: the account name was published to every reader,
# AND the script could not run anywhere else. A placeholder would have fixed the
# first and made the second permanent, so these are real settings with real
# defaults beside the script.
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
BOOKS = os.environ.get("COVENANT_CORPUS_DIR", os.path.join(HERE, "books"))
# TWO MANIFESTS LIVE IN THIS DIRECTORY AND ONLY ONE IS THIS ONE.
# `CORPUS_MANIFEST.json` is a LANGUAGE manifest (en/fr/de/es);
# `claude_phil_CORPUS_MANIFEST.json` holds the 46 Gutenberg ids the space was
# actually fitted on. The first draft of this defaulted to the shorter name and
# died on KeyError: 'ids' -- a file that EXISTS and is the WRONG FILE, which is
# worse than a missing one because `os.path.exists` says yes. So the shape is
# checked, not just the presence.
MANIFEST = os.environ.get("COVENANT_CORPUS_MANIFEST",
                          os.path.join(HERE, "claude_phil_CORPUS_MANIFEST.json"))
if not os.path.exists(MANIFEST):
    raise SystemExit(
        f"no corpus manifest at {MANIFEST}.\n"
        f"Set COVENANT_CORPUS_MANIFEST, or put claude_phil_CORPUS_MANIFEST.json\n"
        f"beside this script. It names the 46 Gutenberg ids the space was fitted\n"
        f"on, and without it this fetches nothing rather than the wrong books.")
_m = json.load(open(MANIFEST, encoding="utf-8"))
if not isinstance(_m, dict) or "ids" not in _m:
    raise SystemExit(
        f"{MANIFEST} exists but carries no 'ids' key (top-level keys: "
        f"{sorted(_m)[:6] if isinstance(_m, dict) else type(_m).__name__}).\n"
        f"That is a different manifest. This script needs the one listing the\n"
        f"46 Gutenberg ids -- a file that exists and is the wrong file is worse\n"
        f"than one that is absent, because the absence is at least obvious.")
os.makedirs(BOOKS, exist_ok=True)
IDS = _m["ids"]
UA = {"User-Agent": "corpus-builder/1.0"}
START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I|re.S)
END   = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I|re.S)
def one(tid):
    p = os.path.join(BOOKS, f"{tid}.txt")
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
