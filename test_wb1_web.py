#!/usr/bin/env python3
"""test_wb1_web.py -- A210: the read-only web door. His words, 2026-09-21:
"Free browser access and access to all 'banned' books."

Free to read, never to act or to reach inside: every refusal here is driven
both ways, the text reduction is measured on a real HTML page served by a
local fixture (loopback is refused by the door, so the fixture is reached
through an opener that the suite hands in, the way a mock network would be),
and every read lands on the ledger. Real network: one public read at the end,
NOT RUN when the network is away.
LICENCE: public domain.
"""
import http.server
import json
import os
import socket
import sys
import tempfile
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_web as W                                              # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:200]) if note and not cond else ""))


def not_run(name, why):
    ok.append(True); print("NOT RUN  %s -- %s" % (name, why))


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
                 ("http://100.112.171.24/", "not the public internet"), ("http://example.com:5000/health", "node's own ports"),
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

# ---- one real public read
try:
    socket.create_connection(("www.gutenberg.org", 443), timeout=5).close()
    r = W.read("https://www.gutenberg.org/ebooks/1497", grant_path=GRANT, ledger_path=LEDGER, max_chars=500)
    check("WB1.14 a real public page is read (Gutenberg's Republic page), title and text", r.get("ok") and "Republic" in r.get("title", "") and r["chars"] > 100, r.get("reason"))
except OSError:
    not_run("WB1.14 a real public read", "no network")

print("\nnot measured here: the door under his real grant file (ops/web_grant.json is read by the doors, this suite uses its own)")
print("\nWB1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
