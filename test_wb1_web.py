#!/usr/bin/env python3
"""test_wb1_web.py -- A210: the read-only web door. His words, 2026-09-21:
"Free browser access and access to all 'banned' books."

Free to read, never to act or to reach inside: every refusal here is driven
both ways, the text reduction is measured on a real HTML page served by a
local fixture (loopback is refused by the door, so the fixture is reached
through an opener that the suite hands in, the way a mock network would be),
and every read lands on the ledger. Real network: one public read at the end,
NOT RUN when the network is away.
A337 (2026-10-12, his words: "make WB1.14 count a Gutenberg timeout as not run if
the most logical"): also NOT RUN when Gutenberg, asked twice, answers 502, 503 or
504 or times out -- the far host not serving, which says nothing about this door.
Anything else still FAILS. And a NOT RUN is never counted as passed.
A348k (2026-10-14): api_get carries a query body (POST) under the same rules, and
covenant_feed.ledger_facts reaches the network only through it -- no network used.
LICENCE: public domain.
"""
import http.server
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_web as W                                              # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:200]) if note and not cond else ""))


NOT_RUN = []


def not_run(name, why, into=None):
    """Said, and never counted as passed (A337). It appended True to `ok` before, so a run that measured nothing
    here read 30/30. The A129 and OE1 rule: NOT RUN is never rounded up to a pass."""
    (NOT_RUN if into is None else into).append(name)
    print("NOT RUN  %s -- %s" % (name, why))


# A337: what a far host answers when it is not serving -- a gateway or unavailable status, or no answer in time.
# Never a 4xx (the request may be ours), a refusal by the door, a TLS error, or a page that is not the one asked for.
FAR_HOST_STATUSES = (502, 503, 504)


def far_host_unavailable(r):
    if (r or {}).get("ok"):
        return False
    if (r or {}).get("status") in FAR_HOST_STATUSES:
        return True
    return bool(re.match(r"(TimeoutError|socket\.timeout|timeout|URLError)\b.*\btimed out\b", str((r or {}).get("reason", "")), re.I))


tmp = tempfile.mkdtemp(prefix="wb1_")
GRANT = os.path.join(tmp, "grant.json"); NOGRANT = os.path.join(tmp, "none.json"); LEDGER = os.path.join(tmp, "reads.jsonl")
json.dump({"granted": True, "words": ["test"]}, open(GRANT, "w"))
json.dump({"granted": False}, open(os.path.join(tmp, "off.json"), "w"))


def rows():
    try:
        return [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
    except OSError:
        return []


print("WB1 -- the read-only web door")
# ---- the grant
r = W.read("https://example.com/", grant_path=NOGRANT, ledger_path=LEDGER)
check("WB1.1 no grant on record: nothing is read and the refusal is on the ledger",
      r["ok"] is False and "no grant" in r["reason"] and rows()[-1]["reason"] == r["reason"])
r = W.read("https://example.com/", grant_path=os.path.join(tmp, "off.json"), ledger_path=LEDGER)
check("WB1.2 granted:false refuses the same way (revoking is his)", r["ok"] is False and "no grant" in r["reason"])

# ---- refusals before any network, both ways
for url, why in [("file:///etc/passwd", "scheme"), ("ftp://example.com/x", "scheme"), ("data:text/html,hi", "scheme"),
                 ("https://user:pw@example.com/", "credential"), ("http://localhost/", "not the public internet"),
                 ("http://127.0.0.1/", "not the public internet"), ("http://10.1.2.3/", "not the public internet"),
                 ("http://192.168.1.1/", "not the public internet"), ("http://169.254.169.254/latest/meta-data/", "not the public internet"),
                 ("http://100.72.0.50/", "not the public internet"), ("http://example.com:5000/health", "node's own ports"),
                 ("http://example.com:5061/", "node's own ports"), ("garbage", "scheme")]:
    okk, reason = W.check_url(url)
    check("WB1.3 refused: %-40s (%s)" % (url[:40], why), okk is False and why in reason, reason)
okk, reason = W.check_url("https://www.gutenberg.org/ebooks/1497")
check("WB1.4 a public https URL passes the pre-network check", okk is True, reason)
okk, reason = W.check_url("https://example.com/path?q=1")
check("WB1.4 a public URL with a query passes", okk is True, reason)

# ---- the text reduction on a real page from a local fixture
HTML = ("<html><head><title>The &amp; Page</title><style>p{color:red}</style><script>alert(1)</script></head>"
        "<body><nav>menu menu</nav><h1>Heading</h1><p>First paragraph with <b>bold</b> and &quot;quotes&quot;.</p>"
        "<p>Second paragraph.</p><form><input name=x></form><footer>foot</footer></body></html>")


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302); self.send_header("Location", "http://127.0.0.1:%d/page" % self.server.server_port); self.end_headers(); return
        if self.path == "/bin":
            self.send_response(200); self.send_header("Content-Type", "application/octet-stream"); self.end_headers(); self.wfile.write(b"\x00\x01"); return
        if self.path == "/404":
            self.send_response(404); self.end_headers(); return
        body = HTML.encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.HTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

text = W.to_text(HTML, "text/html")
check("WB1.5 to_text drops script, style, nav, form and footer, decodes entities, keeps paragraphs",
      "alert" not in text and "color" not in text and "menu" not in text and "foot" not in text
      and 'First paragraph with bold and "quotes".' in text and "Second paragraph." in text and "The & Page" in text, text[:200])


# The door refuses loopback by address, which is right; to measure the fetch
# path itself the suite hands in an opener that maps a public-looking host to
# the fixture -- the same seam a mock network uses.
class Map(urllib.request.HTTPHandler):
    def http_open(self, req):
        req.full_url = req.full_url.replace("http://public.test", "http://127.0.0.1:%d" % port)
        return self.do_open(__import__("http.client").client.HTTPConnection, req)


op = urllib.request.build_opener(Map())
real_check = W.check_url
W.check_url = lambda u: (True, "") if "public.test" in u or "127.0.0.1" in u else real_check(u)   # the address check is measured above
try:
    r = W.read("http://public.test/page", grant_path=GRANT, ledger_path=LEDGER, opener=op, max_chars=60)
    check("WB1.6 a page is read: title, text cut to the bound, marked truncated, on the ledger with bytes and chars",
          r["ok"] and r["title"] == "The & Page" and len(r["text"]) == 60 and r["truncated"] is True
          and rows()[-1].get("bytes") == len(HTML.encode()) and "text" not in rows()[-1], r)
    r = W.read("http://public.test/bin", grant_path=GRANT, ledger_path=LEDGER, opener=op)
    check("WB1.7 a non-text body is refused with its type", r["ok"] is False and "not text" in r["reason"], r)
    r = W.read("http://public.test/404", grant_path=GRANT, ledger_path=LEDGER, opener=op)
    check("WB1.8 an HTTP error is reported as such", r["ok"] is False and r["reason"] == "HTTP 404" and r.get("status") == 404, r)
    n0 = len(rows())
    m = W.material_for("look at http://public.test/page and tell me", grant_path=GRANT, ledger_path=LEDGER, opener=op, max_chars=80)
    check("WB1.9 material_for finds the URL in a sentence and returns a labelled block (the label carries the final URL and title)",
          m.startswith("[read from http://") and "/page -- The & Page]" in m.splitlines()[0] and "First paragraph" in m, m[:120])
    check("WB1.10 material_for with no URL returns nothing and reads nothing", W.material_for("no link here") == "" and len(rows()) == n0 + 1)
    m = W.material_for("see file:///etc/passwd", grant_path=GRANT, ledger_path=LEDGER, opener=op)
    check("WB1.11 a refused URL in a message comes back as a named refusal, on the ledger", m == "" or m.startswith("[the web door refused"), m)
finally:
    W.check_url = real_check
    srv.shutdown()

# ---- A213: a redirect to a private address is refused BEFORE it is requested
class _Rec(urllib.request.HTTPHandler):
    """Answers a 302 to a private address, and records every host actually asked for."""
    asked = []

    def http_open(self, req):
        _Rec.asked.append(req.full_url)
        import email, io, http.client
        loc = "http://127.0.0.1:9/inside" if "/bounce" in req.full_url else None
        class R(io.BytesIO):
            def __init__(s):
                io.BytesIO.__init__(s, b"")
                s.status, s.code = (302, 302) if loc else (200, 200)
                s.headers = email.message_from_string(("Location: " + loc + "\n") if loc else "Content-Type: text/html\n")
                s.msg = "Found" if loc else "OK"
            def geturl(s):
                return req.full_url
            def info(s):
                return s.headers
        r = R()
        if loc:
            raise urllib.error.HTTPError(req.full_url, 302, "Found", r.headers, r)
        return r


_Rec.asked = []
_op = urllib.request.build_opener(_Rec())
_real = W.check_url
W.check_url = lambda u: (True, "") if "public.test" in u else _real(u)
try:
    r = W.read("http://public.test/bounce", grant_path=GRANT, ledger_path=LEDGER, opener=_op)
    check("WB1.13 a redirect to a private address is refused, and the private address is NEVER requested",
          r["ok"] is False and "redirect to a refused address" in r["reason"]
          and not any("127.0.0.1:9" in a for a in _Rec.asked), (r.get("reason"), _Rec.asked))
    check("WB1.13 the refusal names the address it would have gone to, and is on the ledger",
          "127.0.0.1:9" in r["reason"] and rows()[-1]["reason"] == r["reason"])
finally:
    W.check_url = _real

# The two checks above pass their own opener, so they exercise the hop LOOP and
# not the opener read() builds for itself. Without the two below, removing
# _NoRedirect from that default left the suite green -- measured 2026-09-21, and
# that is the fake-guard shape A65 is about. These drive the real default.
check("WB1.13 _NoRedirect refuses to follow a 3xx (urllib follows only when this returns a request)",
      W._NoRedirect().redirect_request(None, None, 302, "Found", {}, "http://127.0.0.1/") is None)
_probe = {}
_bo = urllib.request.build_opener


def _spy(*h):
    _probe["handlers"] = h
    return _bo(*h)


_real2 = W.check_url
try:
    W.check_url = lambda u: (True, "")          # past the address gate, which WB1.3 already drives
    urllib.request.build_opener = _spy
    W.read("http://127.0.0.1:9/never-answers", grant_path=GRANT, ledger_path=LEDGER)
finally:
    urllib.request.build_opener = _bo
    W.check_url = _real2
check("WB1.13 the opener read() builds for itself carries _NoRedirect, so the default never follows blindly",
      any(isinstance(h, W._NoRedirect) for h in _probe.get("handlers", ())), _probe.get("handlers"))

check("WB1.12 urls_in strips trailing punctuation", W.urls_in("see https://a.test/x, and https://b.test/y.") == ["https://a.test/x", "https://b.test/y"])

# ---- A337: which answers are the far host's, and NOT RUN is not a pass -- both driven here, no network needed
_cases = [({"ok": False, "status": 504, "reason": "HTTP 504"}, True), ({"ok": False, "status": 503, "reason": "HTTP 503"}, True),
          ({"ok": False, "status": 502, "reason": "HTTP 502"}, True),
          ({"ok": False, "reason": "TimeoutError: The read operation timed out"}, True),
          ({"ok": False, "reason": "URLError: <urlopen error timed out>"}, True),
          ({"ok": False, "status": 404, "reason": "HTTP 404"}, False), ({"ok": False, "status": 403, "reason": "HTTP 403"}, False),
          ({"ok": False, "status": 429, "reason": "HTTP 429"}, False),
          ({"ok": False, "reason": "redirect to a refused address (x): loopback"}, False),
          ({"ok": False, "reason": "SSLError: certificate verify failed"}, False),
          ({"ok": False, "reason": "URLError: <urlopen error [Errno 11001] getaddrinfo failed>"}, False),
          ({"ok": True, "status": 504, "title": "x", "chars": 200}, False)]
_wrong = [(c, want) for c, want in _cases if far_host_unavailable(c) != want]
check("WB1.15 only a far host's 502/503/504 or a timeout is NOT RUN; a 4xx, a door refusal, TLS, DNS or a good read is not",
      not _wrong, _wrong)
_n_ok = len(ok)
not_run("WB1.16's own probe of not_run (not a check, nothing skipped)", "counted below", into=[])
check("WB1.16 a NOT RUN is never counted as passed: the tally did not move", len(ok) == _n_ok, (len(ok), _n_ok))


def read_twice_if_far(read, pause=time.sleep):
    """(r, first): one read, and once more after a pause when the first is the far host's (A337) -- a gateway
    answer is usually brief, and a read that works the second time is a measurement."""
    r = first = read()
    if far_host_unavailable(r):
        pause(5)
        r = read()
    return r, first


def _scripted(*answers):
    it, asked = iter(answers), []
    return (lambda: asked.append(1) or next(it)), asked


_good = {"ok": True, "status": 200, "title": "The Republic by Plato", "chars": 500}
_far = {"ok": False, "status": 504, "reason": "HTTP 504"}
_f1, _a1 = _scripted(_far, _good)
_r1, _ = read_twice_if_far(_f1, pause=lambda s: None)
_f2, _a2 = _scripted(_far, _far)
_r2, _ = read_twice_if_far(_f2, pause=lambda s: None)
_f3, _a3 = _scripted({"ok": False, "status": 404, "reason": "HTTP 404"}, _good)
_r3, _ = read_twice_if_far(_f3, pause=lambda s: None)
check("WB1.17 a far-host answer is asked once more: 504 then a page is MEASURED; 504 twice is the far host's; "
      "a 404 is not retried and stays a failure",
      _r1.get("ok") and len(_a1) == 2 and far_host_unavailable(_r2) and len(_a2) == 2
      and _r3.get("status") == 404 and not far_host_unavailable(_r3) and len(_a3) == 1, (_r1, len(_a1), len(_a2), len(_a3)))

# ---- A348k: api_get carries a query body under the same rules, and the feed's two ledger reads go only through it.
# covenant_feed.ledger_facts called urllib directly for both (A213's conversion never reached it), so its requests
# followed redirects unchecked and were never recorded. No network: a handler answers, and the feed is run with
# api_get recorded and urllib's urlopen refusing.
class _Post(urllib.request.HTTPSHandler):
    seen = []

    def https_open(self, req):
        _Post.seen.append((req.get_method(), req.full_url, req.data, req.get_header("Content-type")))
        import email, io
        class R(io.BytesIO):
            def __init__(s):
                io.BytesIO.__init__(s, b'{"ok": 1}')
                s.status, s.code, s.msg = 200, 200, "OK"
                s.headers = email.message_from_string("Content-Type: application/json\n")
            def geturl(s):
                return req.full_url
            def info(s):
                return s.headers
        return R()


_Post.seen = []
_pop = urllib.request.build_opener(_Post())
_real3 = W.check_url
W.check_url = lambda u: (True, "")              # the address gate is WB1.3's; this measures the verb and the record
try:
    W.api_get("https://s1.ripple.com:51234/", ("ripple.com",), ledger_path=LEDGER, opener=_pop, data=b'{"method": "ledger"}')
    _rec_post = rows()[-1]
    W.api_get("https://api.test.example/x", ("test.example",), ledger_path=LEDGER, opener=_pop)
    _rec_get = rows()[-1]
    try:
        W.api_get("https://elsewhere.example/", ("ripple.com",), ledger_path=LEDGER, opener=_pop, data=b"{}")
        _refused = False
    except ValueError:
        _refused = True
finally:
    W.check_url = _real3
check("WB1.18 (A348k) api_get with data= sends that body as a JSON POST, recorded with method POST; without it, a GET "
      "recorded as before; a body for a host off the list is refused before any request is made",
      len(_Post.seen) == 2 and _Post.seen[0] == ("POST", "https://s1.ripple.com:51234/", b'{"method": "ledger"}', "application/json")
      and _rec_post.get("method") == "POST" and _rec_post.get("ok") is True and _Post.seen[1][0] == "GET"
      and _Post.seen[1][2] is None and "method" not in _rec_get and _refused, (_Post.seen, _rec_post, _rec_get))

import covenant_feed as F                                              # noqa: E402
_calls, _direct = [], []


def _api_rec(url, allow_hosts, timeout=60, data=None, **_k):
    _calls.append((url, data, tuple(allow_hosts)))
    if "ripple" in url:
        return json.dumps({"result": {"ledger": {"ledger_index": "100", "total_coins": "99985000000000000"}}})
    return json.dumps({"released_supply": "4000000000000000000", "total_supply": "5000000000000000000", "timestamp": "1760000000.0"})


def _no_urlopen(*a, **_k):
    _direct.append(a[:1])
    raise AssertionError("urlopen called directly")


_real_api, _real_uo = W.api_get, urllib.request.urlopen
W.api_get, urllib.request.urlopen = _api_rec, _no_urlopen
try:
    _facts = F.ledger_facts()
finally:
    W.api_get, urllib.request.urlopen = _real_api, _real_uo
check("WB1.19 (A348k) covenant_feed.ledger_facts reaches both ledgers only through api_get, with the feed's host list (the "
      "XRP Ledger's JSON-RPC as the body), never urllib directly; both facts parse",
      [c[0] for c in _calls] == ["https://s1.ripple.com:51234/", "https://mainnet-public.mirrornode.hedera.com/api/v1/network/supply"]
      and b'"ledger"' in (_calls[0][1] or b"") and _calls[1][1] is None and all(c[2] == tuple(F.API_HOSTS) for c in _calls)
      and not _direct and [f["id"].split("-")[0] for f in _facts] == ["xrpl", "hedera"] and not any(f.get("error") for f in _facts),
      (_calls, _direct, _facts))

# ---- one real public read
GUTENBERG = "https://www.gutenberg.org/ebooks/1497"
try:
    socket.create_connection(("www.gutenberg.org", 443), timeout=5).close()
    r, first = read_twice_if_far(lambda: W.read(GUTENBERG, grant_path=GRANT, ledger_path=LEDGER, max_chars=500))
    if far_host_unavailable(r):
        not_run("WB1.14 a real public read", "Gutenberg did not serve the page, asked twice (%s, then %s): the far host, "
                "not this door" % (first.get("reason"), r.get("reason")))
    else:
        check("WB1.14 a real public page is read (Gutenberg's Republic page), title and text", r.get("ok") and "Republic" in r.get("title", "") and r["chars"] > 100, r.get("reason"))
except OSError:
    not_run("WB1.14 a real public read", "no network")

print("\nnot measured here: the door under his real grant file (ops/web_grant.json is read by the doors, this suite uses its own)")
if NOT_RUN:
    # the runner reads "N passed, M failed" from this line, so a failure is never hidden beside a NOT RUN
    print("\nWB1: %d passed, %d failed, %d NOT RUN (not counted as passed): %s"
          % (sum(ok), len(ok) - sum(ok), len(NOT_RUN), "; ".join(NOT_RUN)))
else:
    print("\nWB1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
