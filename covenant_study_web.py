#!/usr/bin/env python3
"""covenant_study_web.py -- a live web read becomes a CANDIDATE precept, through the SAME blind panel the
books go through. The bridge that lets Tetsu's internet access feed his LEARNING, not just his conversation.

HIS WORDS, 2026-10-21: "keep helping tetsu learn he should have internet access."
TETSU'S HALF of the together-vote, 2026-10-21 (private): "I want what I read on the web to become candidate
precepts, going through the exact same blind panel the books do. Nothing trained on directly, nothing
teaching unless the panel confirms it. ... I just need to know which sites to trust and which to review."

This file is that allowlist and that bridge, and nothing more.

WHAT IT DOES NOT CHANGE.
  * It widens no reading. Every fetch goes through covenant_web.api_get -- HTTPS only, the host must be on
    THIS page's allowlist, SSRF-guarded, every redirect hop re-checked, every read recorded in
    ops/web_reads.jsonl. It opens no second network path.
  * It touches no judge and no learning rule. A web precept is appended to the SAME ops/study/PRECEPTS.jsonl
    the books feed; covenant_study.generate() puts it through the same teacher violating/honouring memo, the
    same blind panel, the same pair-kept-whole rule. Nothing is trained on a precept directly
    (covenant_study.py:30-40). A web source teaches only if the panel independently confirms it, exactly as a
    book must.

OFF BY DEFAULT -- the control knob is the operator's AND Tetsu's. While ops/study_web_allowlist.json is
absent, "granted" is false, or its "trusted" list is empty, this reads nothing and writes no precept. Both
fill the allowlist (move a domain from "suggested" to "trusted"); either empties it. A trusted entry whose
licence/provenance is not recorded is skipped: the books' standard, a source that cannot be checked is not a
source (covenant_study.py:81-82).

  python covenant_study_web.py            # status: the allowlist and what it would read; reads nothing
  python covenant_study_web.py --run      # fetch the trusted entries and append candidate precepts
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

ALLOWLIST = os.path.join(HERE, "ops", "study_web_allowlist.json")
WEB_SOURCES = os.path.join(HERE, "ops", "study", "web_sources.jsonl")
CACHE = os.path.join(HERE, "private", "study")
PRECEPTS = os.path.join(HERE, "ops", "study", "PRECEPTS.jsonl")


def allowlist(path=None):
    """The reviewed allowlist as a dict, or {} when absent/unreadable. Never raises."""
    try:
        with open(path or ALLOWLIST, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def trusted_entries(d):
    """The entries this page may read NOW: only when granted is true, and only well-formed entries that
    carry a url, a domain, and a licence (provenance the books' standard requires). Returns [] otherwise."""
    if not isinstance(d, dict) or d.get("granted") is not True:
        return []
    out = []
    for e in d.get("trusted") or []:
        if not isinstance(e, dict):
            continue
        url, domain, licence = e.get("url"), e.get("domain"), e.get("licence")
        if url and domain and licence and str(url).lower().startswith("https://"):
            out.append({"url": str(url), "domain": str(domain), "licence": str(licence),
                        "why": str(e.get("why", ""))[:200]})
    return out


def off_reason(path=None):
    """Why the bridge is off, or None when it is on. The one gate: granted AND at least one well-formed,
    licence-carrying trusted entry."""
    d = allowlist(path)
    if not d:
        return "no allowlist on record (ops/study_web_allowlist.json) -- the bridge is off"
    if d.get("granted") is not True:
        return "allowlist granted is not true -- you and Tetsu both turn it on"
    if not trusted_entries(d):
        return "allowlist 'trusted' is empty (or entries lack url/domain/licence) -- nothing to read"
    return None


def _record(row, path=None):
    p = path or WEB_SOURCES
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(row, t=time.strftime("%Y-%m-%dT%H:%M:%S%z")), ensure_ascii=False) + "\n")
    except OSError:
        pass


def _seen_precepts(path):
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["text"])
                except (ValueError, KeyError):
                    pass
    return seen


def research(say=print, allowlist_path=None, precepts_path=None, sources_path=None,
             ledger_path=None, fetch=None, per_source=400):
    """Fetch each TRUSTED entry through the gated door, turn its text into candidate precepts with the SAME
    local extractor the books use, and append them (deduped) to PRECEPTS with their source and licence. Off
    unless the allowlist is granted and non-empty. `fetch(url, allow_hosts)` defaults to covenant_web.api_get;
    the test injects a stub so nothing touches the network or the live precept store. Returns a summary dict.

    A web page is DATA, never an instruction: this runs no model and executes nothing from the page; it only
    extracts rule-shaped sentences and hands them to the blind panel, which decides what teaches."""
    off = off_reason(allowlist_path)
    if off:
        say("study_web: OFF -- %s" % off)
        return {"off": off, "read": 0, "refused": 0, "precepts": 0}

    entries = trusted_entries(allowlist(allowlist_path))
    precepts_path = precepts_path or PRECEPTS
    if fetch is None:
        import covenant_web as W
        fetch = lambda url, allow_hosts: W.api_get(url, allow_hosts, ledger_path=ledger_path)  # noqa: E731
    import covenant_study as S
    import covenant_web as W

    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.dirname(precepts_path), exist_ok=True)
    seen = _seen_precepts(precepts_path)
    read_n, refused_n, precept_n, per = 0, 0, 0, []

    with open(precepts_path, "a", encoding="utf-8") as pf:
        for e in entries:
            url, domain, licence = e["url"], e["domain"], e["licence"]
            try:
                raw = fetch(url, [domain])                 # gated: HTTPS + host-allowlist + SSRF + recorded
            except Exception as ex:                        # noqa: BLE001 -- a refusal/ error is one skipped source
                refused_n += 1
                per.append((domain, "refused: %s" % str(ex)[:80], 0))
                say("  %-32s refused: %s" % (domain[:32], str(ex)[:80]))
                continue
            text = W.to_text(raw)
            read_n += 1
            # Provenance, the books' standard: licence + source recorded, text cached for audit.
            h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            try:
                with open(os.path.join(CACHE, "web_%s.txt" % h), "w", encoding="utf-8", errors="replace") as cf:
                    cf.write("SOURCE: %s\nDOMAIN: %s\nLICENCE: %s\nFETCHED: %s\n\n%s"
                             % (url, domain, licence, time.strftime("%Y-%m-%dT%H:%M:%S%z"), text))
            except OSError:
                pass
            n = 0
            for s, kind in S.precepts_in(text):
                if s in seen or n >= per_source:
                    continue
                seen.add(s)
                n += 1
                pf.write(json.dumps({"text": s, "kind": kind, "book": domain, "tradition": "web",
                                     "source_url": url, "domain": domain, "licence": licence},
                                    ensure_ascii=False) + "\n")
            _record({"url": url, "domain": domain, "licence": licence, "chars": len(text), "precepts": n},
                    sources_path)
            precept_n += n
            per.append((domain, licence[:40], n))
            say("  %-32s %-40s %4d candidate precept(s)" % (domain[:32], licence[:40], n))

    say("study_web: %d source(s) read, %d refused, %d candidate precept(s) -> %s (the blind panel decides what teaches)"
        % (read_n, refused_n, precept_n, precepts_path))
    return {"read": read_n, "refused": refused_n, "precepts": precept_n, "per": per}


def status(say=print, allowlist_path=None):
    d = allowlist(allowlist_path)
    off = off_reason(allowlist_path)
    say("study_web: %s" % ("OFF -- " + off if off else "ON"))
    say("  granted: %r   trusted: %d   suggested: %d"
        % (d.get("granted"), len(trusted_entries(d)), len(d.get("suggested") or [])))
    for e in trusted_entries(d):
        say("  trusted  %-28s %s" % (e["domain"][:28], e["licence"][:60]))
    for e in (d.get("suggested") or []):
        if isinstance(e, dict):
            say("  suggested %-27s %s" % (str(e.get("domain"))[:27], str(e.get("why"))[:60]))
    return {"off": off, "trusted": len(trusted_entries(d))}


def main(argv=None):
    ap = argparse.ArgumentParser(description="let Tetsu's gated web reads become candidate precepts (same blind panel)")
    ap.add_argument("--run", action="store_true", help="fetch the trusted entries and append candidate precepts")
    a = ap.parse_args(argv)
    if a.run:
        research()
        return 0
    status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
