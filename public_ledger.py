#!/usr/bin/env python3
"""
public_ledger.py -- publish the ledger on purpose, instead of by default.

THE ARGUMENT FOR IT

  The ledger is meant to be readable. The repository is public, the findings
  are public, the anchors are published deliberately. Someone reading the chain
  has obtained something you would hand them, and defending it would be theatre.

  But right now they read it by reaching the NODE, which was never written to
  face strangers. `0.0.0.0` was not a decision; it is a default. The node also
  serves /health (node state, anomaly kinds, judge configuration) and /peers
  (network topology), which are operational detail about a machine rather than
  published content, and every POST handler on it is reachable code.

  So: expose the ledger through something built for the purpose, and let the
  node go back to listening only on loopback. Openness becomes a choice, and
  the code written assuming a trusted network stays on one.

WHAT IT SERVES, AND NOTHING ELSE

    GET /            a one-page description of what this is
    GET /chain       the ledger
    GET /root        chain height and the hash of the head block
    GET /health      up/down and height. NOT the node's /health.

  Every other path is 404. Every method except GET and HEAD is 405. There is
  no path passed through to the node, so this cannot be steered at an upstream
  endpoint it does not already know about.

DESIGN RULES, EACH THERE FOR A REASON

  * Upstream paths are a fixed allowlist in code. Nothing in a request can
    influence which upstream URL is fetched. Without that, a public reader
    could aim this at the node's own private routes.
  * Read-only in the strongest sense available: only GET is ever issued
    upstream, and only to 127.0.0.1.
  * Responses are cached briefly, so a public reader cannot use this to hammer
    a node that is trying to mine.
  * Response size is capped. An unbounded proxy is a memory exhaustion tool.
  * Binds LOOPBACK by default. Facing the public requires --public, typed by a
    person who meant it. That is the whole point of the file.
  * No node internals are relayed. /health here reports only reachability and
    height, not the node's own health document.

USE
  python public_ledger.py                       # loopback, port 8080
  python public_ledger.py --public --port 8080  # deliberately public
  python public_ledger.py --node-port 5000

  Then close the raw node ports at the firewall and, when convenient, change
  the node's bind default from 0.0.0.0 to 127.0.0.1.

LICENCE: Apache-2.0.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional, Tuple

MAX_BYTES = 8 * 1024 * 1024      # refuse to relay more than this
CACHE_SECONDS = 5.0              # a public reader cannot hammer the node
UPSTREAM_TIMEOUT = 10.0

# Fixed allowlist. Nothing in a request can add to it or alter it.
UPSTREAM = {"chain": "/chain"}

_cache: Dict[str, Tuple[float, int, bytes]] = {}
NODE_PORT = 5000


def _fetch_chain() -> Tuple[int, bytes]:
    hit = _cache.get("chain")
    now = time.time()
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1], hit[2]
    url = "http://127.0.0.1:%d%s" % (NODE_PORT, UPSTREAM["chain"])
    try:
        req = urllib.request.Request(url, method="GET",
                                     headers={"User-Agent": "public-ledger/1"})
        with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as r:
            body = r.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                out = (502, json.dumps(
                    {"error": "ledger exceeds the relay cap",
                     "cap_bytes": MAX_BYTES}).encode())
            else:
                out = (200, body)
    except urllib.error.HTTPError as e:
        out = (502, json.dumps({"error": "node returned %s" % e.code}).encode())
    except Exception:                                        # noqa: BLE001
        # Deliberately not relaying the exception text: upstream error strings
        # can carry paths and internal detail, and this face is public.
        out = (503, json.dumps({"error": "node unreachable"}).encode())
    _cache["chain"] = (now, out[0], out[1])
    return out


def _head() -> Tuple[int, bytes]:
    code, body = _fetch_chain()
    if code != 200:
        return code, body
    try:
        d = json.loads(body.decode("utf-8"))
        chain = d.get("chain", d)
        if not isinstance(chain, list) or not chain:
            return 200, json.dumps({"height": 0, "head": None}).encode()
        last = chain[-1]
        return 200, json.dumps({
            "height": len(chain),
            "index": last.get("index"),
            "head": last.get("hash"),
        }).encode()
    except Exception:                                        # noqa: BLE001
        return 502, json.dumps({"error": "ledger did not parse"}).encode()


INDEX = b"""<!doctype html><meta charset=utf-8>
<title>Covenant ledger, public read</title>
<style>body{font:16px/1.55 system-ui,sans-serif;max-width:44rem;margin:3rem auto;padding:0 1rem}
code{background:#eee;padding:.1rem .3rem;border-radius:3px}</style>
<h1>Covenant ledger</h1>
<p>A deliberately public, read-only view of one node's ledger. Published
because the ledger is meant to be readable, and served through this rather
than by exposing the node itself.</p>
<ul>
<li><code>GET /chain</code> - the ledger</li>
<li><code>GET /root</code> - height and head hash</li>
<li><code>GET /health</code> - whether this relay can reach its node</li>
</ul>
<p>Nothing here accepts writes. Every other path is 404 and every method other
than GET is 405. This relay never forwards a path supplied in a request.</p>
<p>Source, and what it will and will not do:
<code>public_ledger.py</code> at github.com/LAWLESS1987/covenant</p>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "public-ledger/1"
    sys_version = ""                       # do not advertise the Python version

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=5")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Access-Control-Allow-Origin", "*")   # read-only data
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:                                # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == "/":
            return self._send(200, INDEX, "text/html; charset=utf-8")
        if path == "/chain":
            code, body = _fetch_chain()
            return self._send(code, body, "application/json")
        if path == "/root":
            code, body = _head()
            return self._send(code, body, "application/json")
        if path == "/health":
            code, _ = _fetch_chain()
            body = json.dumps({"relay": "ok",
                               "node_reachable": code == 200}).encode()
            return self._send(200, body, "application/json")
        self._send(404, b'{"error":"not found"}', "application/json")

    do_HEAD = do_GET                                          # noqa: N815

    def _refuse(self) -> None:
        self._send(405, b'{"error":"this face is read-only"}',
                   "application/json")

    do_POST = do_PUT = do_DELETE = do_PATCH = _refuse         # noqa: N815

    def log_message(self, fmt: str, *args) -> None:
        return                                                # no request logs


def main() -> int:
    global NODE_PORT
    p = argparse.ArgumentParser(description="Read-only public view of a node's ledger.")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--node-port", type=int, default=5000)
    p.add_argument("--public", action="store_true",
                   help="bind 0.0.0.0. Without this it is loopback only.")
    a = p.parse_args()
    NODE_PORT = a.node_port

    host = "0.0.0.0" if a.public else "127.0.0.1"
    srv = ThreadingHTTPServer((host, a.port), Handler)
    print("  serving %s:%d  ->  node on 127.0.0.1:%d"
          % (host, a.port, a.node_port))
    if a.public:
        print("  PUBLIC. Anyone who can reach this host can read the ledger.")
        print("  That is the intended state of this file and nothing else")
        print("  about the node should be reachable. Check with:")
        print("      python exposure_check.py")
    else:
        print("  loopback only. Pass --public when you mean it.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
