#!/usr/bin/env python3
"""test_oa1_open_access.py -- A208/A209: the study pipeline's open-access
source (Europe PMC, Creative Commons full texts) and the banned-books shelf.
Fixtures only: a fake search and a fake full text drive fetch_oa; extract()
runs on a temp cache and a temp precept file. The real reading list is
counted, and the shelf's presence measured by tradition, read-only.
LICENCE: public domain.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_study as S                                            # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:200]) if note and not cond else ""))


print("OA1 -- open access into the study")
tmp = tempfile.mkdtemp(prefix="oa1_")
cache, reg = os.path.join(tmp, "cache"), os.path.join(tmp, "oa_sources.jsonl")
ARTICLE = ("Thou shalt not take from a child what the child has earned by effort. " * 30 +
           "Teachers must never conceal a child's progress from the parents who pay for it. " * 30 +
           "It is well known that the sky is blue. " * 60)


def fake_search(query, n):
    return 4, [{"pmcid": "PMC1", "license": "cc by", "journalTitle": "J", "pubYear": "2020", "citedByCount": 9},
               {"pmcid": "PMC2", "license": "cc by-nc-nd", "journalTitle": "J", "pubYear": "2020", "citedByCount": 8},
               {"pmcid": "PMC3", "license": "cc0", "journalTitle": "J", "pubYear": "2021", "citedByCount": 7},
               {"pmcid": "PMC4", "license": "cc by", "journalTitle": "J", "pubYear": "2021", "citedByCount": 1}]


def fake_text(pmcid):
    if pmcid == "PMC4":
        return "Short", "too short to keep"
    # each article's sentences differ (the extractor keeps a sentence once, wherever it first appears)
    return "Article %s" % pmcid, ARTICLE.replace("a child", "a child of %s" % pmcid)


said = []
new, skipped = S.fetch_oa(cache=cache, registry=reg, per_query=2, say=said.append, queries=[("open-access: test", "q")],
                          search=fake_search, get_text=fake_text)
srcs = S.oa_sources(reg)
check("OA1.1 two CC BY/CC0 articles cached, the NC-ND one and the short one skipped",
      new == 2 and [p for p, _t, _d in srcs] == ["PMC1", "PMC3"] and skipped >= 1, (new, skipped, srcs))
head = open(os.path.join(cache, "oa_PMC1.txt"), encoding="utf-8").read(400)
check("OA1.2 a cached article carries Title, Source URL and Licence lines before its text",
      head.startswith("Title: Article PMC1\nSource: https://europepmc.org/article/PMC/PMC1\nLicence: cc by\n"), head[:120])
new2, _ = S.fetch_oa(cache=cache, registry=reg, per_query=2, say=said.append, queries=[("open-access: test", "q")],
                     search=fake_search, get_text=fake_text)
check("OA1.3 a second pass caches nothing new (the registry remembers)", new2 == 0 and len(S.oa_sources(reg)) == 2)
check("OA1.4 the bound holds: per_query=2 took the two best-cited that qualified, not the third", "PMC4" not in [p for p, _t, _d in srcs])

# extraction over the cached articles, on temp paths
real = (S.CACHE, S.OA_REGISTRY, S.PRECEPTS, S.OUT)
S.CACHE, S.OA_REGISTRY, S.PRECEPTS, S.OUT = cache, reg, os.path.join(tmp, "P.jsonl"), tmp
try:
    total, per = S.extract(say=lambda *_a: None)
    rows = [json.loads(l) for l in open(S.PRECEPTS, encoding="utf-8")]
    oa_rows = [r for r in rows if r.get("pmcid")]
    check("OA1.5 extract() reads the cached articles and records precepts with the pmcid, title and tradition",
          len(oa_rows) >= 2 and {r["pmcid"] for r in oa_rows} == {"PMC1", "PMC3"} and oa_rows[0]["book"].startswith("Article") and oa_rows[0]["tradition"] == "open-access: test",
          (total, oa_rows[:1]))
    check("OA1.6 only the sentences that state a rule about value between people are kept (the sky is not a precept)",
          all("sky" not in r["text"] for r in oa_rows) and any("take from a child" in r["text"] or "conceal" in r["text"] for r in oa_rows))
finally:
    S.CACHE, S.OA_REGISTRY, S.PRECEPTS, S.OUT = real

# the reading list itself, read-only
trads = {}
for gid, title, trad in S.BOOKS:
    trads[trad] = trads.get(trad, 0) + 1
ids = [gid for gid, _t, _d in S.BOOKS]
check("OA1.7 the reading list has no duplicate ids", len(ids) == len(set(ids)), len(ids) - len(set(ids)))
check("OA1.8 the banned-books shelf is on the list by discovery (100 or more titles under its tradition)", trads.get("banned-books-shelf", 0) >= 100, trads.get("banned-books-shelf"))
check("OA1.9 child development, psychology and the philosophers are on the list", trads.get("child-development", 0) >= 8 and trads.get("psychology", 0) >= 5 and trads.get("humean", 0) >= 1, trads)
check("OA1.10 four open-access topics are declared, each a Europe PMC query for CC BY or CC0 full text",
      len(S.OA_QUERIES) == 4 and all('LICENSE:"cc by"' in q and "HAS_FT:Y" in q for _t, q in S.OA_QUERIES))

print("\nnot measured here: the live Europe PMC search and download (network); measured by hand 2026-09-21: 13,392 hits, one 217,000-character review fetched")
print("\nOA1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
