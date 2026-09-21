#!/usr/bin/env python3
"""covenant_web.py -- the PC and Tetsu can read the open web: any public page,
as text, read-only, every read on record.

HIS WORDS, 2026-09-21: "Free browser access and access to all 'banned' books."

WHAT "FREE" MEANS HERE, AND WHAT IT DOES NOT. Free to READ: any http(s) page
on the public internet, fetched with this repository's own name in the
user agent, reduced to text (scripts, styles, navigation and tags dropped),
cut to a bound, and handed to the council (A167) or to Tetsu (A165) as
material for an answer -- the gate still judges the answer. Not free to:
  * act -- no forms, no logins, no cookies, no POST: this door has one verb,
    GET, and it never sends a credential (a URL carrying user:pass@ is
    refused, not stripped);
  * reach inside -- loopback, link-local, private ranges and the tailnet
    are refused by address AFTER resolution (an SSRF door is not a browser),
    and the node's own ports are never a target;
  * read a file -- file:, ftp:, data: and every scheme but http(s) refuse;
  * hide -- every read, refused or served, is one row in ops/web_reads.jsonl
    with the URL, the bytes, the reason. "Free" is not "unrecorded".
THE GRANT is ops/web_grant.json, in his words; absent or granted:false, the
door reads nothing and says so. Revoking is his: set granted to false.

THE BANNED BOOKS (the second half of his sentence) are not here: a book is a
text, and texts go through the study pipeline (covenant_study.py, A209), where
every banned or challenged book that is PUBLIC DOMAIN is on the reading list
by discovery from Gutenberg's own banned-books shelf. Books still in copyright
are named there and not fetched -- "free" does not mean "taken".
LICENCE: public domain.
"""
from __future__ import annotations

import html
import ipaddress
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GRANT = os.path.join(HERE, "ops", "web_grant.json")
LEDGER = os.path.join(HERE, "ops", "web_reads.jsonl")
UA = "covenant-web (read-only; github.com/LAWLESS1987/covenant)"
MAX_BYTES = 2_000_000
MAX_HOPS = 10               # A213: redirects are followed by hand, each hop checked first
MAX_CHARS = 12_000
TIMEOUT_S = 30
_TAILNET = ipaddress.ip_network("100.64.0.0/10")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hands the 3xx back as an HTTPError so read() can check the next hop's
    ADDRESS before the request to it is made."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def grant(path=None):
    p = path or os.environ.get("COVENANT_WEB_GRANT") or GRANT
    try:
        with open(p, encoding="utf-8") as fh:
            g = json.load(fh)
        return g if g.get("granted") is True else None
    except (OSError, ValueError):
        return None


def _record(row, path=None):
    p = path or os.environ.get("COVENANT_WEB_LEDGER") or LEDGER
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(row, t=time.strftime("%Y-%m-%dT%H:%M:%S%z")), ensure_ascii=False) + "\n")
    except OSError:
        pass


def _refuse_address(host):
    """A reason when the host resolves anywhere that is not the public
    internet; None when every address is public."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        return "does not resolve (%s)" % e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
                or ip.is_unspecified or (ip.version == 4 and ip in _TAILNET)):
            return "resolves to %s, which is not the public internet" % ip
    return None


def check_url(url):
    """(ok, reason) before any network call."""
    try:
        u = urllib.parse.urlsplit(str(url).strip())
    except ValueError as e:
        return False, "not a URL: %s" % e
    if u.scheme not in ("http", "https"):
        return False, "scheme %r refused: this door reads http(s) only" % (u.scheme or "")
    if not u.hostname:
        return False, "no host"
    if u.username or u.password or "@" in u.netloc:
        return False, "a credential in the URL is refused, not stripped"
    if u.port and u.port in (5000, 5001, 5011, 5020, 5021, 5031, 5060, 5061, 5071, 5199):
        return False, "the node's own ports are never a target"
    why = _refuse_address(u.hostname)
    if why:
        return False, why
    return True, ""


def api_get(url, allow_hosts, timeout=60, max_bytes=MAX_BYTES, ledger_path=None, opener=None):
    """A213 (2026-09-21, his words: "So encode the newest stuff the same way for
    security"). The newest modules -- the feed and the study's open-access
    fetcher -- called urllib directly, so none of the checks above applied to
    them: no scheme test, no address test, no redirect discipline, no record.
    This is the one way in for them. HTTPS only, the host must be ON THE LIST
    (exactly, or a subdomain of a listed host), every redirect hop checked
    before it is followed, and every call recorded like any other read.

    Returns the decoded body. Raises ValueError with the reason when refused."""
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    listed = any(host == h or host.endswith("." + h) for h in allow_hosts)
    if not urllib.parse.urlsplit(url).scheme == "https" or not listed:
        why = "api_get refuses %s: %s" % (url[:120], "not https" if host and not url.startswith("https://") else "host %r is not on this caller's list" % host)
        _record({"ok": False, "url": url[:300], "reason": why, "kind": "api"}, ledger_path)
        raise ValueError(why)
    ok, why = check_url(url)
    if not ok:
        _record({"ok": False, "url": url[:300], "reason": why, "kind": "api"}, ledger_path)
        raise ValueError("api_get refuses %s: %s" % (url[:120], why))
    op = opener or urllib.request.build_opener(_NoRedirect())
    target, hops = url, 0
    while True:
        req = urllib.request.Request(target, headers={"User-Agent": UA, "Accept": "application/json, application/xml, text/plain, */*;q=0.5"})
        try:
            r = op.open(req, timeout=timeout)
            break
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location") if e.headers else None
            if e.code in (301, 302, 303, 307, 308) and loc:
                hops += 1
                target = urllib.parse.urljoin(target, loc)
                h2 = (urllib.parse.urlsplit(target).hostname or "").lower()
                ok2, why2 = check_url(target)
                if hops > MAX_HOPS or not ok2 or not any(h2 == h or h2.endswith("." + h) for h in allow_hosts):
                    why = "api_get refuses the redirect to %s: %s" % (target[:120], why2 or "off this caller's host list")
                    _record({"ok": False, "url": url[:300], "reason": why, "kind": "api"}, ledger_path)
                    raise ValueError(why)
                continue
            _record({"ok": False, "url": url[:300], "reason": "HTTP %s" % e.code, "kind": "api"}, ledger_path)
            raise
    with r:
        raw = r.read(max_bytes + 1)[:max_bytes]
    _record({"ok": True, "url": url[:300], "final_url": (r.geturl() or target)[:300], "bytes": len(raw), "kind": "api"}, ledger_path)
    m = re.search(r"charset=([\w-]+)", str(r.headers.get("Content-Type", "")))
    return raw.decode(m.group(1) if m else "utf-8", "replace")


def to_text(raw, content_type=""):
    """HTML (or plain text) to readable text: scripts, styles, nav and tags out,
    entities decoded, whitespace folded, paragraphs kept."""
    s = raw
    if "html" in content_type.lower() or re.search(r"<\s*(html|body|p|div)\b", s[:4000], re.I):
        s = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|form)\b.*?</\1\s*>", " ", s)
        s = re.sub(r"(?is)<!--.*?-->", " ", s)
        s = re.sub(r"(?i)</\s*(p|div|li|h[1-6]|tr|br|section|article|blockquote)\s*>|<br\s*/?>", "\n", s)
        s = re.sub(r"<[^>]+>", " ", s)
        s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def read(url, max_chars=MAX_CHARS, grant_path=None, ledger_path=None, opener=None):
    """{"ok": True, "url", "final_url", "status", "chars", "text", "title"} or
    {"ok": False, "url", "reason"}; every call recorded."""
    url = str(url).strip()
    g = grant(grant_path)
    if g is None:
        row = {"ok": False, "url": url, "reason": "no grant on record (ops/web_grant.json)"}
        _record(row, ledger_path); return row
    ok, why = check_url(url)
    if not ok:
        row = {"ok": False, "url": url, "reason": why}
        _record(row, ledger_path); return row
    # A213 (2026-09-21, his words: "There should be no backdoors"). The first
    # version of this let urllib follow redirects and checked the address only
    # afterwards -- so a public host that answered 302 to http://127.0.0.1/ had
    # already had the request MADE to the private address before the check ran,
    # which is the whole of what an SSRF guard exists to stop. Redirects are now
    # followed by hand, at most MAX_HOPS, and EVERY hop is checked before it is
    # fetched.
    hops, target, final, r = 0, url, url, None
    try:
        op = opener or urllib.request.build_opener(_NoRedirect())
        while True:
            req = urllib.request.Request(target, headers={"User-Agent": UA, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.5"})
            try:
                r = op.open(req, timeout=TIMEOUT_S)
            except urllib.error.HTTPError as e:
                loc = e.headers.get("Location") if e.headers else None
                if e.code in (301, 302, 303, 307, 308) and loc:
                    hops += 1
                    if hops > MAX_HOPS:
                        row = {"ok": False, "url": url, "reason": "more than %d redirects" % MAX_HOPS}
                        _record(row, ledger_path); return row
                    target = urllib.parse.urljoin(target, loc)
                    ok2, why2 = check_url(target)          # checked BEFORE the next request is made
                    if not ok2:
                        row = {"ok": False, "url": url, "reason": "redirect to a refused address (%s): %s" % (target[:200], why2)}
                        _record(row, ledger_path); return row
                    continue
                raise
            break
        with r:
            final = r.geturl() or target
            ok2, why2 = check_url(final)
            if not ok2:
                row = {"ok": False, "url": url, "reason": "landed on a refused address: %s" % why2}
                _record(row, ledger_path); return row
            ctype = str(r.headers.get("Content-Type", ""))
            raw = r.read(MAX_BYTES + 1)
            status = getattr(r, "status", 200)
    except urllib.error.HTTPError as e:
        row = {"ok": False, "url": url, "reason": "HTTP %s" % e.code, "status": e.code}
        _record(row, ledger_path); return row
    except Exception as e:                                        # noqa: BLE001
        row = {"ok": False, "url": url, "reason": "%s: %s" % (type(e).__name__, str(e)[:120])}
        _record(row, ledger_path); return row
    if len(raw) > MAX_BYTES:
        raw = raw[:MAX_BYTES]
    if not (ctype.startswith("text/") or "html" in ctype or "xml" in ctype or "json" in ctype or not ctype):
        row = {"ok": False, "url": url, "reason": "not text: %s" % ctype[:60], "status": status}
        _record(row, ledger_path); return row
    m = re.search(r"charset=([\w-]+)", ctype)
    s = raw.decode(m.group(1) if m else "utf-8", "replace")
    t = re.search(r"(?is)<title[^>]*>(.*?)</title>", s)
    title = html.unescape(re.sub(r"\s+", " ", t.group(1))).strip()[:200] if t else ""
    text = to_text(s, ctype)
    truncated = len(text) > max_chars
    text = text[:max_chars]
    row = {"ok": True, "url": url, "final_url": final, "status": status, "bytes": len(raw), "chars": len(text),
           "truncated": truncated, "title": title}
    _record(row, ledger_path)
    return dict(row, text=text)


_URL = re.compile(r"https?://[^\s<>\"']+")


def urls_in(text):
    return [u.rstrip(".,;:)") for u in _URL.findall(str(text or ""))]


def material_for(message, max_chars=6000, **kw):
    """For a door: the first URL in the message read, as a block the model can
    use, or "" when there is none or it was refused (the refusal is recorded)."""
    urls = urls_in(message)
    if not urls:
        return ""
    r = read(urls[0], max_chars=max_chars, **kw)
    if not r.get("ok"):
        return "[the web door refused %s: %s]" % (urls[0], r.get("reason"))
    return "[read from %s%s]\n%s" % (r.get("final_url") or urls[0], " -- " + r["title"] if r.get("title") else "", r["text"])


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="read a public page as text, on record")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    a = ap.parse_args(argv)
    if a.status or not a.url:
        g = grant()
        n = 0
        try:
            with open(LEDGER, encoding="utf-8") as fh:
                n = sum(1 for _ in fh)
        except OSError:
            pass
        print(json.dumps({"granted": g is not None, "words": (g or {}).get("words"), "reads_on_record": n}, indent=1))
        return 0
    r = read(a.url, max_chars=a.max_chars)
    if not r.get("ok"):
        print("refused: %s" % r.get("reason")); return 1
    print("%s (%s) %d chars%s\n" % (r["final_url"], r.get("title", ""), r["chars"], " [cut]" if r["truncated"] else ""))
    sys.stdout.write(r["text"] + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
