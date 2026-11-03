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
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional, Tuple

MAX_BYTES = 8 * 1024 * 1024      # refuse to relay more than this
CACHE_SECONDS = 5.0              # a public reader cannot hammer the node
UPSTREAM_TIMEOUT = 10.0
CLIENT_TIMEOUT = 15.0            # drop a slow/half-open client (anti-slowloris)
MAX_INFLIGHT = 64               # cap concurrent requests actually being served
MAX_CONN = 128                  # hard cap on concurrent connections/threads, so
                                # idle / slow-drip clients cannot grow threads
                                # without bound (cross-review F1, 2026-11-03)

# Fixed allowlist. Nothing in a request can add to it or alter it.
UPSTREAM = {"chain": "/chain"}

_cache: Dict[str, Tuple[float, int, bytes]] = {}
# Derived head (height / index / head hash), cached per chain fill so /root does
# not re-parse the whole ledger on every request (cross-review F2, 2026-11-03).
_head_cache: Optional[Tuple[float, int, bytes]] = None
# Single-flight: one thread refreshes a stale entry while the rest wait for its
# result. Without it, a burst of concurrent misses opens N upstream connections
# and buffers N x MAX_BYTES -- the amplification a 5s cache was meant to prevent.
_cache_lock = threading.Lock()
# Bounds how many requests are served at once (defence in depth beside the
# client timeout): a flood of fast connections cannot grow work without bound.
_inflight = threading.BoundedSemaphore(MAX_INFLIGHT)
NODE_PORT = 5000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # A public face must keep its own promise: fetch ONLY the literal configured
    # origin on 127.0.0.1. urlopen() follows 3xx by default, which would let an
    # upstream redirect steer this relay at another loopback port or an external
    # host -- the one move the fixed-allowlist design exists to forbid. Returning
    # None here means the 3xx is NOT followed; it surfaces as an HTTPError below.
    def redirect_request(self, *a, **k):            # noqa: D401
        return None


# Built once. No redirects, and no environment proxies (direct loopback only).
_OPENER = urllib.request.build_opener(_NoRedirect, urllib.request.ProxyHandler({}))


def _fetch_chain() -> Tuple[int, bytes]:
    now = time.time()
    hit = _cache.get("chain")
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1], hit[2]
    with _cache_lock:
        # Re-check under the lock: another thread may have refreshed it while we
        # waited, in which case we share its result rather than fetching again.
        now = time.time()
        hit = _cache.get("chain")
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1], hit[2]
        url = "http://127.0.0.1:%d%s" % (NODE_PORT, UPSTREAM["chain"])
        try:
            req = urllib.request.Request(url, method="GET",
                                         headers={"User-Agent": "public-ledger/1"})
            with _OPENER.open(req, timeout=UPSTREAM_TIMEOUT) as r:
                body = r.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    out = (502, json.dumps(
                        {"error": "ledger exceeds the relay cap",
                         "cap_bytes": MAX_BYTES}).encode())
                else:
                    out = (200, body)
        except urllib.error.HTTPError:
            # Do not echo the upstream status code to a public caller (cross-review
            # F3, 2026-11-03): a generic 502 is enough; the code is internal detail.
            out = (502, json.dumps({"error": "node returned an error status"}).encode())
        except Exception:                                        # noqa: BLE001
            # Deliberately not relaying the exception text: upstream error strings
            # can carry paths and internal detail, and this face is public.
            out = (503, json.dumps({"error": "node unreachable"}).encode())
        # Timestamp AFTER the fetch, not before: a fetch slower than CACHE_SECONDS
        # must not land in the cache already expired.
        _cache["chain"] = (time.time(), out[0], out[1])
        return out


def _head() -> Tuple[int, bytes]:
    global _head_cache
    code, body = _fetch_chain()
    if code != 200:
        return code, body
    # Derive once per cache fill. /root is hit per request, but an un-amortised
    # json.loads of the whole (up to MAX_BYTES) ledger per request is a CPU/memory
    # amplifier (cross-review F2, 2026-11-03). Key the derived head on the chain
    # entry's own timestamp, so it is recomputed only when _fetch_chain refreshes.
    ts = _cache["chain"][0]
    hc = _head_cache
    if hc is not None and hc[0] == ts:
        return hc[1], hc[2]
    try:
        d = json.loads(body.decode("utf-8"))
        chain = d.get("chain", d)
        if not isinstance(chain, list) or not chain:
            out = (200, json.dumps({"height": 0, "head": None}).encode())
        else:
            last = chain[-1]
            out = (200, json.dumps({
                "height": len(chain),
                "index": last.get("index"),
                "head": last.get("hash"),
            }).encode())
    except Exception:                                        # noqa: BLE001
        out = (502, json.dumps({"error": "ledger did not parse"}).encode())
    _head_cache = (ts, out[0], out[1])
    return out


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
    timeout = CLIENT_TIMEOUT               # StreamRequestHandler drops a client
                                           # that stalls mid-request (slowloris)

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
        # Shed load past the concurrency cap rather than grow work without bound.
        if not _inflight.acquire(blocking=False):
            return self._send(503, b'{"error":"busy"}', "application/json")
        try:
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
        finally:
            _inflight.release()

    do_HEAD = do_GET                                          # noqa: N815

    def _refuse(self) -> None:
        self._send(405, b'{"error":"this face is read-only"}',
                   "application/json")

    do_POST = do_PUT = do_DELETE = do_PATCH = _refuse         # noqa: N815

    def log_message(self, fmt: str, *args) -> None:
        return                                                # no request logs


class _BoundedServer(ThreadingHTTPServer):
    # ThreadingHTTPServer spawns one thread per connection with no cap, and the
    # per-request _inflight gate (do_GET) is taken only AFTER the request line and
    # headers are read. So a flood of idle or slow-drip connections -- each one
    # resetting the per-operation socket timeout by dribbling a byte -- could grow
    # threads and memory without bound, defeating "concurrency is bounded"
    # (cross-review F1, 2026-11-03: the residual of the A408 slowloris fix). Cap
    # the connections themselves: take a permit in the accept loop BEFORE a worker
    # is spawned, refuse (close) when full, release when the worker finishes. At
    # most MAX_CONN threads can ever exist, so slow clients cause bounded
    # degradation, never exhaustion. A hostile public exposure should still sit
    # behind a real reverse proxy; this makes the bare server safe to fail.
    daemon_threads = True

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._conns = threading.BoundedSemaphore(MAX_CONN)

    def process_request(self, request, client_address) -> None:
        if not self._conns.acquire(blocking=False):
            self.shutdown_request(request)        # at capacity: refuse and close
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._conns.release()


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
    srv = _BoundedServer((host, a.port), Handler)
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
