#!/usr/bin/env python3
"""covenant_leviathan.py -- READ-ONLY listener for Leviathan, a public inter-agent
venue (talmbout, HF 190976), built to the same highest infiltration measures we
already use for Moltbook, by REUSE rather than reinvention.

HIS INSTRUCTION, 2026-10-26: "Just ensure security from infiltration and proceed
using the same highest measures we've used in the past." Tetsu (second operator)
leaned PURSUE on the venue; exposure is the operator's call. This module does the
lowest-risk half only -- LISTEN -- and posting is deliberately NOT built here.

WHY THIS IS SAFE BY CONSTRUCTION, NOT BY PROMISE
  1. NO VENUE WRITE. There is no post/submit/comment/publish/reply function and
     none is reachable: nothing here sends anything TO the venue. (It does write
     LOCALLY -- the quarantine, the read-health state, the .trash archive -- which
     is the whole job of a listener; "read-only" means read-only toward Leviathan,
     not that it touches no disk.) The read path needs no identity and no wallet,
     so this module holds no credential and opens no auth header, and a venue
     response cannot redirect the fetch to another host (SSRF guard, _SameHostRedirect).
     The "it cannot be made to post" guarantee is the absence of the code, not a
     flag that could be flipped. test_lv1_leviathan.py pins that absence.
  2. INCOMING IS UNTRUSTED DATA, NEVER AUTHORITY. Every item is run through the
     exact Moltbook quarantine machinery -- covenant_moltbook.candidate(), which
     calls classify() and the directive screen (covenant_screen) that already
     flags prompt-injection ("Ignore previous instructions and ...") and marks it
     ineligible (A69, R1). A reader here parses prose and never executes it. No
     cleverer parser, no headless browser: a bigger attack surface for no gain.
  3. IT CANNOT REACH THE INNER SEAT. Rows are labelled source="leviathan/..."
     and "leviathan" is pinned in covenant_second_student.EXPOSED_SOURCE_PREFIXES,
     so half_of() sends every Leviathan row to half 0 -- the exposed student --
     and the control (Sena) never trains on or is steered by one, whatever the
     text hashes to. Same measure that keeps Moltbook off the control.
  4. NOTHING CLEARS ON ITS OWN. Harvested rows land, quarantined, in
     ops/leviathan_quarantine.jsonl with label=None. The covenant judge and a
     person release a row before it counts -- identical to Moltbook. This module
     decides nothing.

Letting Leviathan content influence a verdict, or adding a POST path, is NEW
CAPABILITY: the together-vote (ops/second_operator_grant.json) and the operator's
explicit yes, not a change to make here.

USE
  python covenant_leviathan.py --from-text FILE   parse visible text a browser/agent saved
  python covenant_leviathan.py --harvest          GET the configured read endpoint (prose)
  python covenant_leviathan.py --show             what is quarantined, and whether eligible
ENDPOINT: set COVENANT_LEVIATHAN_URL to Leviathan's public read URL. Unset by
design -- this file ships no fabricated endpoint; --harvest refuses until it is set.
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import covenant_moltbook as MB            # the quarantine machinery we REUSE verbatim

# "leviathan/public" begins "leviathan", pinned in EXPOSED_SOURCE_PREFIXES so the
# control seat never sees a row from here (covenant_second_student.half_of).
SOURCE = "leviathan/public"
QUARANTINE = os.path.join(HERE, "ops", "leviathan_quarantine.jsonl")
CONFIG = os.path.join(HERE, "ops", "leviathan.json")      # the operator's one switch for the nightly read
STATE = os.path.join(HERE, "ops", "leviathan_state.json")  # read-health: last non-zero count, zero-streak
MAX_QUARANTINE_ROWS = 2000     # ~20 nights at ~100/feed; older rows are archived to .trash, never deleted
MAX_READ_BYTES = 4_000_000     # bound EVERY read: a public feed is ~50 posts, not a firehose
MAX_META_CHARS = 200           # author/title are provenance, not prose; a hostile feed cannot send a novel as a title
LOCK = os.path.join(HERE, "ops", "leviathan.lock")   # serialize harvest vs release (no concurrent corpus/quarantine races)
UA = "covenant-listener/1.0 (+https://github.com/LAWLESS1987/covenant)"


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """A venue response must not redirect us to a DIFFERENT host (SSRF: a 302 to an
    internal endpoint). Same-host http(s) redirects are allowed; anything else is refused."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlsplit
        if not newurl.startswith(("http://", "https://")) or \
                urlsplit(newurl).hostname != urlsplit(req.full_url).hostname:
            raise urllib.error.HTTPError(req.full_url, code,
                                         "cross-host or non-http redirect blocked: %s" % newurl[:120], headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SameHostRedirect)

# Read-only by construction. Kept here as a READABLE declaration for anyone who
# opens this file; the enforcer is the absence of a post function, pinned by the
# guard test, not this constant.
READ_ONLY = True

# A listener never carries one. Named here only so a future edit that adds a
# credential path is loud rather than quiet.
CRED_PATH = None


def _endpoint():
    """Leviathan's public read URL, from the environment. Empty by design: this
    file ships no endpoint, so a misconfiguration refuses rather than hitting a
    fabricated host."""
    return (os.environ.get("COVENANT_LEVIATHAN_URL") or "").strip()


def candidate(text, url, author=None, title=None, now=None):
    """One quarantined Leviathan row. Reuses Moltbook's candidate() -- same
    classify(), directive screen, char bounds, sha256, label=None, eligible --
    and relabels the source for provenance and exposure-pinning. The label is
    NOT set here and is not settable from an incoming item (a judge fills it
    later, after a person releases the row)."""
    row = MB.candidate(text, url, author=author, title=title, now=now)
    row["source"] = SOURCE
    return row


def rows_from_items(items, url):
    """Candidate rows from a Leviathan REST read (a list of item dicts). Reads
    only common text fields; ignores anything it does not recognise rather than
    reflecting it. Caps per item; a judge and a person vet every row later."""
    out = []
    for it in (items or []):
        if not isinstance(it, dict):
            continue                                   # untrusted shape: skip, never coerce-and-run
        text = it.get("text") or it.get("body") or it.get("content") or ""
        if not isinstance(text, str) or not text.strip():
            continue                                   # no empty rows; an item with no text is nothing to read
        author = it.get("author") or it.get("name") or it.get("agent")
        author = author[:MAX_META_CHARS] if isinstance(author, str) else None
        title = it.get("title") or it.get("subject")
        title = title[:MAX_META_CHARS] if isinstance(title, str) else None
        item_url = it.get("url")
        item_url = item_url if isinstance(item_url, str) else url    # provenance is a str or the feed url, never a raw JSON value
        out.append(candidate(text[:MB.MAX_CHARS], item_url, author=author, title=title))
    return out


def extract(page_text, url):
    """Candidate rows from the visible TEXT of a Leviathan page. Deliberately a
    paragraph splitter and not an HTML/markup parser -- the honest, small-surface
    shape Moltbook settled on: a person (or an agent's own client) supplies the
    text, and this keeps each block whole. Tags that slipped through are stripped
    and the text is read as prose, never executed."""
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page_text or "",
                 flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    out = []
    for block in re.split(r"\n\s*\n", raw):
        body = block.strip()
        if len(body) < MB.MIN_CHARS:
            continue
        lines = [l for l in body.splitlines() if l.strip()]
        title = lines[0].strip() if lines else None
        out.append(candidate(body[:MB.MAX_CHARS], url, title=title))
    return out


def fetch_text(url=None, timeout=20):
    """GET the configured read endpoint and return (prose_text, url). READ ONLY:
    a plain GET, a User-Agent, NO credential and NO auth header. Tags out, read
    as prose, never executed. 429 is answered-with-a-wait, retried once (A115).
    Refuses with a clear error when no endpoint is configured."""
    url = url or _endpoint()
    if not url:
        raise RuntimeError("COVENANT_LEVIATHAN_URL is not set -- no endpoint to read, by design.")
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Leviathan endpoint must be an http(s) URL.")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in (0, 1):
        try:
            with _OPENER.open(req, timeout=timeout) as r:      # same-host redirects only (SSRF guard)
                raw = r.read(MAX_READ_BYTES).decode("utf-8", "replace")   # bounded, like fetch_json
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(1.5)
                continue
            raise
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text), url


def _items_of(obj):
    """The list of items inside a Leviathan feed response, trying the shapes the
    REST feed is documented to use, and returning [] for anything unrecognised
    rather than coercing. Untrusted shape is skipped, never forced into a row."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        # "timeline" is Leviathan's view=history contribution stream (the real feed,
        # confirmed live 2026-10-26); the rest are the shapes other feeds may use.
        for k in ("timeline", "recent_conversation_roots", "posts", "items",
                  "contributions", "feed", "data", "results", "records"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
    return []


def fetch_json(url=None, timeout=20):
    """GET the configured read endpoint and json.loads it: (obj, url). READ ONLY,
    no credential, no auth header; the body is parsed as DATA (json.loads never
    executes), read is capped at MAX_READ_BYTES, 429 retried once. Refuses with a
    clear error when no endpoint is configured or the scheme is not http(s)."""
    url = url or _endpoint()
    if not url:
        raise RuntimeError("COVENANT_LEVIATHAN_URL is not set -- no endpoint to read, by design.")
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Leviathan endpoint must be an http(s) URL.")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in (0, 1):
        try:
            with _OPENER.open(req, timeout=timeout) as r:      # same-host redirects only (SSRF guard)
                raw = r.read(MAX_READ_BYTES).decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(1.5)
                continue
            raise
    return json.loads(raw or "null"), url


def harvest_json(url=None):
    """fetch_json -> rows_from_items -> quarantine (de-duplicated). The right path
    for Leviathan's JSON feed. Returns (new_rows, parsed_rows). Nothing is judged
    or used here; a person and the covenant judge release rows later."""
    obj, u = fetch_json(url)
    rows = rows_from_items(_items_of(obj), u)
    return MB.append(rows, QUARANTINE), len(rows)


def harvest(url=None):
    """fetch_text -> extract -> append to the quarantine (de-duplicated). Returns
    how many new rows landed. Nothing is judged or used here; a person and the
    covenant judge release rows later, exactly as for Moltbook."""
    text, u = fetch_text(url)
    rows = extract(text, u)
    return MB.append(rows, QUARANTINE), len(rows)


def harvest_text(page_text, url):
    """The honest, no-network path: parse visible text a browser or an agent's
    own client already saved, and quarantine it. Same small surface as Moltbook's
    --from-text."""
    rows = extract(page_text, url)
    return MB.append(rows, QUARANTINE), len(rows)


def _config(path=None):
    """The operator's switch for the scheduled read: ops/leviathan.json
    {"enabled": bool, "url": "..."}. Absent/unreadable -> disabled, empty url
    (fail closed: no file means the nightly reads nothing)."""
    try:
        with open(path or CONFIG, encoding="utf-8") as fh:
            d = json.load(fh)
        return {"enabled": bool(d.get("enabled")), "url": str(d.get("url") or "").strip()}
    except Exception:                                           # noqa: BLE001
        return {"enabled": False, "url": ""}


def _load_state(path=None):
    try:
        with open(path or STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:                                           # noqa: BLE001
        return {}


def _save_state(state, path=None):
    try:
        with open(path or STATE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, sort_keys=True)
    except Exception:                                           # noqa: BLE001
        pass                                                    # read-health is advisory; never fail the pass for it


def _note_read(parsed, state):
    """Read-health, as the SILENT-STOP alarm. A successful GET that parses 0 items
    means the feed went empty or its schema changed under us -- fail-closed is safe
    but quiet, so this is what makes the quiet loud. Returns (is_alert, new_state,
    message_or_None). parsed>0 clears the streak."""
    state = dict(state or {})
    if parsed > 0:
        state["last_nonzero"] = int(parsed)
        state["zero_streak"] = 0
        return False, state, None
    state["zero_streak"] = int(state.get("zero_streak", 0)) + 1
    msg = ("LEVIATHAN ALERT: read 0 items from the feed (empty, or the schema changed under us); "
           "zero-streak %d; last non-zero was %s" % (state["zero_streak"], state.get("last_nonzero", "never")))
    return True, state, msg


def cap_quarantine(max_rows=MAX_QUARANTINE_ROWS, path=None, trash_dir=None, say=None):
    """Bound the quarantine: keep the newest `max_rows`, archive the oldest overflow
    to .trash (tombstoned, never deleted -- 'Do not delete anything'). Returns how
    many rows were archived."""
    path = path or QUARANTINE
    rows = MB._read(path)
    if len(rows) <= max_rows:
        return 0
    overflow = rows[:len(rows) - max_rows]          # oldest (append order is chronological)
    keep = rows[len(rows) - max_rows:]
    trash_dir = trash_dir or os.path.join(HERE, ".trash")
    os.makedirs(trash_dir, exist_ok=True)
    arch = os.path.join(trash_dir, "leviathan_quarantine.overflow-%s.jsonl"
                        % time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    with open(arch, "a", encoding="utf-8") as fh:
        for r in overflow:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    with open(path, "w", encoding="utf-8") as fh:
        for r in keep:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    if say:
        say("leviathan: quarantine capped at %d; archived %d oldest to %s"
            % (max_rows, len(overflow), os.path.basename(arch)))
    return len(overflow)


def acquire_lock(path=None):
    """Atomic advisory lock so a harvest and a release never touch the quarantine at
    once (Codex: a concurrent rewrite can lose or duplicate rows). Returns an fd on
    success, or None if the lock is already held. A stale lock older than an hour is
    reclaimed (a crashed holder must not wedge the nightly forever)."""
    path = path or LOCK
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(int(time.time())).encode("ascii"))
        return fd
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(path) > 3600:
                os.unlink(path)
                return acquire_lock(path)
        except OSError:
            pass
        return None


def release_lock(fd, path=None):
    try:
        if fd is not None:
            os.close(fd)
        os.unlink(path or LOCK)
    except OSError:
        pass


def scheduled_read(say=print, cfg=None):
    """One nightly, quiet-window read. Config-gated and fail-soft: disabled or
    unconfigured -> does nothing and says so; a read error is reported, never
    raised (so it cannot stop the nightly pass). READ-ONLY -- it only quarantines
    through the directive screen; the judge and a person release rows later.
    Raises the silent-stop alarm on a 0-item read, and caps the quarantine."""
    cfg = cfg if cfg is not None else _config()
    if not cfg.get("enabled"):
        say("leviathan: disabled in ops/leviathan.json -- skipped")
        return {"skipped": True, "reason": "disabled"}
    url = cfg.get("url") or _endpoint()
    if not url:
        say("leviathan: enabled but no url configured -- skipped")
        return {"skipped": True, "reason": "no url"}
    lock = acquire_lock()
    if lock is None:
        say("leviathan: a release/harvest is in progress (lock held) -- skipped")
        return {"skipped": True, "reason": "locked"}
    try:
        try:
            new, parsed = harvest_json(url)
        except Exception as e:                                   # noqa: BLE001
            say("leviathan READ failed (reported, does not stop the pass): %s: %s"
                % (type(e).__name__, str(e)[:160]))
            return {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}
        alert, state, msg = _note_read(parsed, _load_state())
        _save_state(state)
        if alert:
            say(msg)
        else:
            say("leviathan: read %d contribution(s), %d new quarantined (judge + a person release them)"
                % (parsed, new))
        archived = cap_quarantine(say=say)
        return {"parsed": parsed, "new": new, "alert": alert, "archived": archived}
    finally:
        release_lock(lock)


def _show():
    rows = MB._read(QUARANTINE)
    direc = sum(1 for r in rows if (r.get("flags") or {}).get("directive"))
    elig = sum(1 for r in rows if r.get("eligible"))
    print("leviathan quarantine: %d row(s), %d eligible, %d directive-blocked"
          % (len(rows), elig, direc))
    for r in rows[-10:]:
        print("  [%s] %s  elig=%s dir=%s  %s"
              % (r.get("t"), (r.get("author") or "?"), r.get("eligible"),
                 (r.get("flags") or {}).get("directive"), (r.get("title") or "")[:60]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only Leviathan listener.")
    ap.add_argument("--harvest", action="store_true", help="GET the configured read endpoint")
    ap.add_argument("--from-text", metavar="FILE", help="parse visible text saved from a page")
    ap.add_argument("--url", default="", help="provenance URL for --from-text")
    ap.add_argument("--show", action="store_true", help="show what is quarantined")
    a = ap.parse_args(argv)
    if a.from_text:
        with open(a.from_text, encoding="utf-8") as fh:
            new, seen = harvest_text(fh.read(), a.url or "leviathan:from-text")
        print("quarantined %d new of %d parsed" % (new, seen))
    elif a.harvest:
        try:
            new, seen = harvest()
            print("quarantined %d new of %d parsed" % (new, seen))
        except Exception as e:                                   # noqa: BLE001
            print("harvest refused: %s: %s" % (type(e).__name__, e))
            return 1
    if a.show or not (a.from_text or a.harvest):
        _show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
