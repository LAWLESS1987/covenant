#!/usr/bin/env python3
"""covenant_feed.py -- the open sources the covenant reads every night, by
topic, and carries to its students: current science, open courseware, public
ledgers, law and medicine. All of it open-licensed or public domain; all of
it recorded; none of it a shortcut past the gate.

HIS WORDS, 2026-09-21 (evening, in order): "All ai news including j space
discovery quantum computing, mishmahowalds work and all offspring of it all
data in covenant mainly the open ended mutual benefit and growth" -- "All free
available mit and college material" -- "All research on recursive self
improvement every known math equation" -- "Imterdimensional studies" --
"Layered understanding and collective consciousness research" -- "Crypto
ledgers and burn rates" -- "Law, medical journals and research" -- "All for
growth and mutual benefit".

WHAT A TOPIC IS. One row in TOPICS: a name, his words, a SOURCE KIND and a
query or a page list. Four kinds:
  arxiv      the arXiv API (Atom, no key): the newest abstracts for a query;
  europepmc  Europe PMC (REST, no key): open-access CC BY/CC0 full texts,
             through covenant_study.fetch_oa, so they also feed the precepts;
  pages      public pages read through the web door (covenant_web, A210:
             read-only, on record) -- MIT OpenCourseWare and OpenStax are
             open-licensed (CC BY-NC-SA / CC BY); the US Code and the Supreme
             Court's opinions are US government works, public domain;
  ledgers    public ledger facts by JSON-RPC and REST, no key: the XRP
             Ledger's total supply (so its cumulative fee burn, 100 billion
             minus what remains) and Hedera's supply from its mirror node.
WHAT A PASS DOES. For each topic, a bounded number of new items (by id, kept
in ops/feed_state.json), cached under private/feed/<topic>/, and ONE digest
row per topic per night on the teacher queue (source "feed:<topic>"): titles
and first lines, cut to size, so the students read what is new and Tetsu's
brief can say what the covenant read. A source that fails is reported and
skipped; the pass never stops on one.
WHAT IS NOT HERE, said plainly. "Every known math equation" is not a corpus
anyone can fetch: what is open is arXiv's mathematics and NIST's Digital
Library of Mathematical Functions (public domain), and those are what the
topic reads. "All AI news" is what open feeds carry, not the trade press.
Misha Mahowald's published work and its line (the silicon retina,
neuromorphic engineering) is public science and is read; no person is looked
up. "Interdimensional studies" is read as the physics of extra dimensions
(hep-th, gr-qc), which is what the open literature contains.
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CACHE = os.path.join(HERE, "private", "feed")
STATE = os.path.join(HERE, "ops", "feed_state.json")
UA = {"User-Agent": "covenant-feed/1.0 (open sources only; github.com/LAWLESS1987/covenant)", "Accept": "application/atom+xml, application/json, text/html;q=0.8, */*;q=0.5"}
# A213 (2026-09-21, his words: "So encode the newest stuff the same way for
# security"). This module used urllib directly, so none of the web door's checks
# applied to it. Every fetch now goes through covenant_web.api_get: https only,
# the host must be on this list, every redirect hop checked before it is
# followed, and each call recorded in the same ledger as any other read.
API_HOSTS = ("api.openalex.org", "export.arxiv.org", "ebi.ac.uk",
             "ripple.com", "mirrornode.hedera.com")


def _api(url, timeout=60):
    import covenant_web
    return covenant_web.api_get(url, API_HOSTS, timeout=timeout)
# A211: these were 6 and 3000, the assistant's numbers. Raised, and overridable.
# What remains is only what keeps a nightly pass finishing and polite to the open
# services it reads (OpenAlex, Europe PMC and arXiv are free and shared).
PER_TOPIC = int(os.environ.get("COVENANT_FEED_PER_TOPIC") or 25)
DIGEST_CHARS = int(os.environ.get("COVENANT_FEED_DIGEST_CHARS") or 12000)

# (name, his words, kind, query-or-pages)
TOPICS = [
    ("ai-research", "All ai news", "papers",
     "artificial intelligence large language model agents alignment"),
    ("space-discovery", "j space discovery", "papers",
     "exoplanet discovery galaxy cosmology observation"),
    ("quantum-computing", "quantum computing", "papers",
     "quantum computing qubit error correction"),
    ("neuromorphic", "mishmahowalds work and all offspring of it", "papers",
     "neuromorphic engineering silicon retina spiking neural event camera"),
    ("recursive-self-improvement", "All research on recursive self improvement", "papers",
     "recursive self-improvement self-improving artificial intelligence"),
    ("mathematics", "every known math equation", "papers",
     "mathematics theorem proof equation"),
    ("extra-dimensions", "Imterdimensional studies", "papers",
     "extra dimensions Kaluza-Klein braneworld higher-dimensional spacetime"),
    ("collective-consciousness", "Layered understanding and collective consciousness research", "papers",
     "collective intelligence consciousness global workspace integrated information"),
    ("crypto-ledgers", "Crypto ledgers and burn rates", "ledgers", None),
    ("token-burn-research", "Crypto ledgers and burn rates", "papers",
     "token burn tokenomics blockchain transaction fee mechanism"),
    ("medicine", "Law, medical journals and research", "europepmc",
     '(PUB_TYPE:"systematic review" OR PUB_TYPE:review) AND (TITLE:treatment OR TITLE:therapy OR TITLE:prevention) AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND HAS_FT:Y'),
    ("law", "Law, medical journals and research", "pages", [
        "https://uscode.house.gov/browse.xhtml",
        "https://www.supremecourt.gov/opinions/slipopinion/25",
        "https://www.law.cornell.edu/constitution/overview",
    ]),
    ("courseware", "All free available mit and college material", "pages", [
        "https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/pages/syllabus/",
        "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/pages/syllabus/",
        "https://ocw.mit.edu/courses/24-00-problems-of-philosophy-fall-2019/pages/syllabus/",
        "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/pages/syllabus/",
        "https://openstax.org/books/psychology-2e/pages/1-introduction",
        "https://openstax.org/books/introduction-to-philosophy/pages/1-introduction",
        "https://openstax.org/books/biology-2e/pages/1-introduction",
        "https://openstax.org/books/college-physics-2e/pages/1-introduction",
        "https://dlmf.nist.gov/",
    ]),
]


# ------------------------------------------------------------------ sources --
def _openalex_abstract(inv):
    """OpenAlex stores an abstract as {word: [positions]}; put it back in order."""
    if not inv:
        return ""
    return " ".join(w for _p, w in sorted((p, w) for w, ps in inv.items() for p in ps))


def openalex_search(query, n, mailto="noreply@github.com"):
    """Open-access works, newest first, from OpenAlex: open metadata (CC0), no
    key, and the mailto puts the call in its polite pool."""
    u = "https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"search": query, "filter": "open_access.is_oa:true", "sort": "publication_date:desc",
         "per-page": n, "mailto": mailto})
    out = []
    for w in (json.loads(_api(u)).get("results") or []):
        out.append({"id": (w.get("id") or "").rsplit("/", 1)[-1],
                    "title": (w.get("title") or "")[:300],
                    "summary": _openalex_abstract(w.get("abstract_inverted_index"))[:1500],
                    "published": (w.get("publication_date") or "")[:10],
                    "authors": [((a.get("author") or {}).get("display_name") or "") for a in (w.get("authorships") or [])][:6],
                    "url": (w.get("open_access") or {}).get("oa_url") or w.get("id") or ""})
    return out


def arxiv_search(query, n):
    """[{"id", "title", "summary", "published", "authors", "url"}] newest first."""
    u = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": query, "start": 0, "max_results": n, "sortBy": "submittedDate", "sortOrder": "descending"})
    return parse_arxiv(_api(u))


def papers_search(query, n):
    """OpenAlex first, arXiv second. Measured 2026-09-21: the arXiv API answered
    406 to every query asking for more than one result, so it is the fallback
    and not the road. A failure of both carries both reasons."""
    try:
        got = openalex_search(query, n)
        if got:
            return got
        note = "no results"
    except Exception as e:                                        # noqa: BLE001
        note = "%s: %s" % (type(e).__name__, str(e)[:60])
    try:
        return arxiv_search("all:" + " AND all:".join(query.split()[:3]), n)
    except Exception as e:                                        # noqa: BLE001
        raise RuntimeError("OpenAlex %s; arXiv %s: %s" % (note, type(e).__name__, str(e)[:60]))


def parse_arxiv(xml):
    out = []
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        def tag(t):
            mm = re.search(r"<%s[^>]*>(.*?)</%s>" % (t, t), e, re.S)
            return re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""
        aid = tag("id").rsplit("/", 1)[-1]
        out.append({"id": aid, "title": tag("title"), "summary": tag("summary")[:1500], "published": tag("published")[:10],
                    "authors": [re.sub(r"\s+", " ", a).strip() for a in re.findall(r"<name>(.*?)</name>", e)][:6],
                    "url": "https://arxiv.org/abs/" + aid})
    return out


def ledger_facts():
    """Public numbers, each with its source; a source that fails says so."""
    facts = []
    try:
        body = json.dumps({"method": "ledger", "params": [{"ledger_index": "validated", "transactions": False, "expand": False}]}).encode()
        r = json.load(urllib.request.urlopen(urllib.request.Request("https://s1.ripple.com:51234/", data=body, headers=dict(UA, **{"Content-Type": "application/json"})), timeout=30))
        L = r["result"]["ledger"]
        total = int(L["total_coins"]) / 1e6
        facts.append({"id": "xrpl-%s" % L["ledger_index"], "title": "XRP Ledger #%s: %.6f XRP remain of 100,000,000,000; %.6f XRP destroyed as fees to date"
                      % (L["ledger_index"], total, 1e11 - total), "source": "https://s1.ripple.com:51234 (ledger, validated)", "n": {"ledger_index": L["ledger_index"], "total_coins_xrp": total, "burned_xrp": 1e11 - total}})
    except Exception as e:                                        # noqa: BLE001
        facts.append({"id": "xrpl-error-%s" % time.strftime("%Y%m%d"), "title": "XRP Ledger: not read (%s: %s)" % (type(e).__name__, str(e)[:80]), "source": "s1.ripple.com", "error": True})
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request("https://mainnet-public.mirrornode.hedera.com/api/v1/network/supply", headers=UA), timeout=30))
        rel, tot = int(r["released_supply"]) / 1e8, int(r["total_supply"]) / 1e8
        facts.append({"id": "hedera-%s" % str(r.get("timestamp", ""))[:10], "title": "Hedera: %.0f HBAR released of %.0f total (%.1f%%)" % (rel, tot, 100 * rel / tot if tot else 0),
                      "source": "https://mainnet-public.mirrornode.hedera.com/api/v1/network/supply", "n": {"released": rel, "total": tot}})
    except Exception as e:                                        # noqa: BLE001
        facts.append({"id": "hedera-error-%s" % time.strftime("%Y%m%d"), "title": "Hedera: not read (%s: %s)" % (type(e).__name__, str(e)[:80]), "source": "mirrornode.hedera.com", "error": True})
    return facts


# -------------------------------------------------------------------- state --
def load_state(path=None):
    try:
        with open(path or STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"seen": {}}


def save_state(st, path=None):
    p = path or STATE
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(dict(st, t=time.strftime("%Y-%m-%dT%H:%M:%S%z")), fh, indent=1)


def _cache(topic, item_id, text, cache=None):
    d = os.path.join(cache or CACHE, topic)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, re.sub(r"[^\w.-]", "_", item_id)[:80] + ".txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


# --------------------------------------------------------------------- pass --
def run_topic(name, words, kind, spec, seen, per_topic=PER_TOPIC, cache=None, say=print,
              papers=None, oa=None, web=None, ledgers=None):
    """New items for one topic -> cached; returns (items, note). Never raises."""
    seen_ids = set(seen.get(name, []))
    items = []
    try:
        if kind == "papers":
            for e in (papers or papers_search)(spec, per_topic * 3):
                if e["id"] in seen_ids or len(items) >= per_topic:
                    continue
                text = "Title: %s\nSource: %s\nPublished: %s\nAuthors: %s\n\n%s\n" % (
                    e["title"], e.get("url", ""), e["published"], ", ".join(e["authors"]), e["summary"])
                _cache(name, e["id"], text, cache)
                items.append({"id": e["id"], "title": e["title"], "line": e["summary"][:300], "url": e.get("url", "")})
        elif kind == "europepmc":
            if oa is None:
                import covenant_study as S
                got = []
                def _say(line):
                    got.append(line)
                new, _sk = S.fetch_oa(per_query=per_topic, say=_say, queries=[("open-access: " + name, spec)])
                for pmcid, title, trad in S.oa_sources():
                    if trad == "open-access: " + name and pmcid not in seen_ids and len(items) < per_topic:
                        items.append({"id": pmcid, "title": title, "line": "", "url": "https://europepmc.org/article/PMC/%s" % pmcid})
            else:
                items = [i for i in oa(spec, per_topic) if i["id"] not in seen_ids][:per_topic]
        elif kind == "pages":
            W = web
            if W is None:
                import covenant_web as _W
                W = _W.read
            for url in spec:
                if url in seen_ids or len(items) >= per_topic:
                    continue
                r = W(url, max_chars=8000)
                if not r.get("ok"):
                    say("  %-26s %s -> %s" % (name, url[:50], r.get("reason"))); continue
                _cache(name, url, "Title: %s\nSource: %s\n\n%s\n" % (r.get("title", ""), url, r["text"]), cache)
                items.append({"id": url, "title": r.get("title") or url, "line": r["text"][:300], "url": url})
        elif kind == "ledgers":
            for f in (ledgers or ledger_facts)():
                if f["id"] in seen_ids:
                    continue
                _cache(name, f["id"], "Title: %s\nSource: %s\n\n%s\n" % (f["title"], f["source"], json.dumps(f.get("n", {}))), cache)
                items.append({"id": f["id"], "title": f["title"], "line": "public ledger, read by JSON-RPC/REST, no key", "url": f["source"], "error": f.get("error", False)})
        else:
            return [], "unknown kind %r" % kind
    except Exception as e:                                        # noqa: BLE001
        return items, "%s: %s" % (type(e).__name__, str(e)[:120])
    return items, ""


def digest(name, words, items):
    head = "WHAT THE COVENANT READ TONIGHT -- %s (his words: %s)\n\n" % (name, words)
    body = ""
    for i in items:
        line = "- %s\n  %s\n  %s\n" % (i["title"][:200], (i.get("line") or "")[:300].replace("\n", " "), i.get("url", ""))
        if len(head) + len(body) + len(line) > DIGEST_CHARS:
            break
        body += line
    return (head + body).strip()


def run(per_topic=PER_TOPIC, topics=None, state_path=None, cache=None, queue_path=None, say=print, append=None, **sources):
    """One pass over every topic. Returns {"topics": n, "items": n, "queued": n, "failed": [names]}."""
    st = load_state(state_path)
    seen = st.setdefault("seen", {})
    rows, total, failed = [], 0, []
    for name, words, kind, spec in (topics or TOPICS):
        items, note = run_topic(name, words, kind, spec, seen, per_topic, cache, say, **sources)
        good = [i for i in items if not i.get("error")]
        if note:
            failed.append(name); say("  %-26s %-9s %d new, then: %s" % (name, kind, len(items), note))
        else:
            say("  %-26s %-9s %d new" % (name, kind, len(items)))
        if good:
            rows.append({"text": digest(name, words, good), "source": ("feed:" + name)[:80]})
        seen[name] = (seen.get(name, []) + [i["id"] for i in items])[-400:]
        total += len(items)
    kept = 0
    if rows:
        if append is None:
            from covenant_daily_plan import teacher_queue_append as append
        kept = append(rows, path=queue_path)
    st["last"] = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "items": total, "queued": kept, "failed": failed}
    save_state(st, state_path)
    say("feed: %d topic(s), %d new item(s), %d digest row(s) queued for the teacher, %d source(s) failed" % (len(topics or TOPICS), total, kept, len(failed)))
    return {"topics": len(topics or TOPICS), "items": total, "queued": kept, "failed": failed}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the open sources the covenant reads every night")
    ap.add_argument("--per-topic", type=int, default=PER_TOPIC)
    ap.add_argument("--only", nargs="*", default=None, help="topic names")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for name, words, kind, spec in TOPICS:
            print("  %-26s %-9s %s" % (name, kind, (spec if isinstance(spec, str) else "%d page(s)" % len(spec)) if spec else "-"))
        return 0
    if a.status:
        print(json.dumps(load_state().get("last", {}), indent=1)); return 0
    topics = [t for t in TOPICS if not a.only or t[0] in a.only]
    run(per_topic=a.per_topic, topics=topics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
