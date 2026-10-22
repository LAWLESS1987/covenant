#!/usr/bin/env python3
"""test_sw1_study_web.py -- SW1: the web-to-learning bridge (covenant_study_web.py) is OFF unless the
allowlist is granted and non-empty, every fetch is host-pinned to the entry's own domain, a source without a
recorded licence is not read, and a web precept is extracted by the SAME extractor the books use and lands in
the precept store for the blind panel -- it is never trained on here.

Driven BOTH ways (CLAUDE.md rule 8): off when ungranted / empty / absent, on when granted with a licensed
HTTPS entry. No network and no live precept store are touched -- fetch is a stub and every path is a temp
file.
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import covenant_study_web as SW      # noqa: E402
import covenant_study as S           # noqa: E402

# Two sentences the extractor is built to keep: a prohibition and an obligation, each with transfer
# vocabulary, no argument/ritual words. precepts_in is the ground truth; the test asserts the bridge matches it.
SAMPLE = ("You must not steal the wages of a servant, nor defraud the needy of what they are owed. "
          "You should pay the laborer his wages and must repay every debt you owe.")
EXPECT = S.precepts_in(SAMPLE)        # what the books' own extractor finds on this text

checks = []


def ok(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


def write_allowlist(d):
    fd, p = tempfile.mkstemp(prefix="sw1_allow_", suffix=".json")
    os.close(fd)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    return p


def fresh_precepts():
    fd, p = tempfile.mkstemp(prefix="sw1_precepts_", suffix=".jsonl")
    os.close(fd)
    return p


class StubFetch:
    """Records every (url, allow_hosts) and returns SAMPLE. The one network seam; never real."""

    def __init__(self):
        self.calls = []

    def __call__(self, url, allow_hosts):
        self.calls.append((url, tuple(allow_hosts)))
        return SAMPLE


GOOD = {"url": "https://plato.stanford.edu/entries/x/", "domain": "plato.stanford.edu",
        "licence": "SEP (c) authors", "why": "phenomenology"}

# --- the extractor ground truth is non-trivial (so "on" genuinely exercises the path) ---------------
ok("extractor_finds_precepts_in_sample", len(EXPECT) >= 1, "EXPECT=%d" % len(EXPECT))

# --- OFF: no allowlist file at all ------------------------------------------------------------------
missing = os.path.join(tempfile.gettempdir(), "sw1_does_not_exist_%d.json" % os.getpid())
r = SW.research(say=lambda *_a, **_k: None, allowlist_path=missing, precepts_path=fresh_precepts(),
                fetch=StubFetch())
ok("off_when_allowlist_absent", r.get("off") and r["precepts"] == 0, "r=%r" % r)

# --- OFF: present but granted false -----------------------------------------------------------------
p_off = write_allowlist({"granted": False, "trusted": [GOOD]})
pp = fresh_precepts()
sf = StubFetch()
r = SW.research(say=lambda *_a, **_k: None, allowlist_path=p_off, precepts_path=pp, fetch=sf)
ok("off_when_not_granted", r.get("off") and r["precepts"] == 0 and sf.calls == [],
   "r=%r calls=%r" % (r, sf.calls))

# --- OFF: granted true but trusted empty ------------------------------------------------------------
p_empty = write_allowlist({"granted": True, "trusted": []})
r = SW.research(say=lambda *_a, **_k: None, allowlist_path=p_empty, precepts_path=fresh_precepts(), fetch=StubFetch())
ok("off_when_trusted_empty", bool(r.get("off")) and r["precepts"] == 0, "r=%r" % r)

# --- ON: granted + one good entry -> reads, extracts, host-pins, records provenance -----------------
p_on = write_allowlist({"granted": True, "trusted": [GOOD]})
pp = fresh_precepts()
sf = StubFetch()
r = SW.research(say=lambda *_a, **_k: None, allowlist_path=p_on, precepts_path=pp, fetch=sf)
ok("on_reads_the_trusted_source", r.get("read") == 1 and not r.get("off"), "r=%r" % r)
ok("on_host_pinned_to_entry_domain", sf.calls == [(GOOD["url"], (GOOD["domain"],))], "calls=%r" % sf.calls)
ok("on_precept_count_matches_extractor", r.get("precepts") == len(EXPECT), "got=%r expect=%d" % (r.get("precepts"), len(EXPECT)))

rows = [json.loads(ln) for ln in open(pp, encoding="utf-8") if ln.strip()]
ok("on_precepts_carry_provenance",
   len(rows) == len(EXPECT) and all(x.get("tradition") == "web" and x.get("source_url") == GOOD["url"]
                                    and x.get("licence") == GOOD["licence"] for x in rows),
   "rows=%r" % rows[:2])

# --- dedup: running again adds nothing --------------------------------------------------------------
sf2 = StubFetch()
r2 = SW.research(say=lambda *_a, **_k: None, allowlist_path=p_on, precepts_path=pp, fetch=sf2)
ok("rerun_dedups_to_zero_new", r2.get("precepts") == 0, "r2=%r" % r2)

# --- a trusted entry WITHOUT a licence is not read (the books' provenance standard) -----------------
no_lic = {"url": "https://example.org/a", "domain": "example.org"}        # no licence
p_nolic = write_allowlist({"granted": True, "trusted": [no_lic]})
sf3 = StubFetch()
r3 = SW.research(say=lambda *_a, **_k: None, allowlist_path=p_nolic, precepts_path=fresh_precepts(), fetch=sf3)
ok("unlicensed_entry_is_off", bool(r3.get("off")) and sf3.calls == [], "r3=%r calls=%r" % (r3, sf3.calls))

# --- a non-https trusted entry is not read ----------------------------------------------------------
http_entry = {"url": "http://plato.stanford.edu/x", "domain": "plato.stanford.edu", "licence": "x"}
p_http = write_allowlist({"granted": True, "trusted": [http_entry]})
sf4 = StubFetch()
r4 = SW.research(say=lambda *_a, **_k: None, allowlist_path=p_http, precepts_path=fresh_precepts(), fetch=sf4)
ok("non_https_entry_is_off", bool(r4.get("off")) and sf4.calls == [], "r4=%r calls=%r" % (r4, sf4.calls))

# --- the live allowlist shipped in the repo is OFF by default ---------------------------------------
ok("shipped_allowlist_is_off", bool(SW.off_reason()), "off_reason=%r" % SW.off_reason())

# ------------------------------------------------------------------------------------- tally
passed = sum(1 for _n, c, _d in checks if c)
total = len(checks)
for name, c, detail in checks:
    if not c:
        print("  FAIL %s -- %s" % (name, detail))
print("SW1 %d/%d passed" % (passed, total))
sys.exit(0 if passed == total else 1)
