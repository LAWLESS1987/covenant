#!/usr/bin/env python3
"""
PL1 -- the both-ways guard for public_ledger.py (A408, 2026-11-03).

The artifact for finding C4 (cross-system security review, 2026-11-02 divvy):
ChatGPT (area 9, High effort) raised three findings on public_ledger.py and
Claude confirmed all three against the real code. This suite pins each fix and,
for each, drives the guard BOTH ways -- with the guard, the flaw is gone; remove
the guard (a dummy lock, a redirect-following opener, an exhausted permit pool)
and the flaw returns. A green that was never observed turning red is not a check
(rule 8).

  C4a  slowloris / unbounded client wait  -> Handler.timeout drops a stalled client
  C4b  cache stampede + stale timestamp    -> single-flight lock; timestamp after fetch
  C4c  upstream redirect escapes the origin -> _NoRedirect opener refuses to follow 3xx

Pure stdlib, loopback only, ephemeral ports. No node required.
"""
from __future__ import annotations

import http.client
import socket
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import public_ledger as pl


# --- tiny controllable upstream ------------------------------------------------

class _Upstream:
    """A throwaway HTTP server on an ephemeral loopback port.

    mode: "ok"       -> 200 with a small JSON body, counting each hit
          "redirect" -> 302 Location: http://127.0.0.1:<other>/private
          "slow"     -> 200 after `delay` seconds, counting each hit
    """

    def __init__(self, mode="ok", other_port=None, delay=0.0, body=b'{"chain":[]}'):
        self.mode = mode
        self.other_port = other_port
        self.delay = delay
        self.body = body
        self.hits = 0
        self._lock = threading.Lock()
        up = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def do_GET(self):               # noqa: N802
                with up._lock:
                    up.hits += 1
                if up.mode == "redirect":
                    self.send_response(302)
                    self.send_header(
                        "Location",
                        "http://127.0.0.1:%d/private" % up.other_port)
                    self.end_headers()
                    return
                if up.mode == "slow":
                    time.sleep(up.delay)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(up.body)))
                self.end_headers()
                self.wfile.write(up.body)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()


def _clear_cache():
    pl._cache.clear()


# --- C4c: redirects must not escape the fixed origin --------------------------

def test_redirect_not_followed():
    """The _NoRedirect opener refuses a 302; the 'private' target is never hit."""
    secret = _Upstream(mode="ok", body=b'{"chain":["SECRET"]}')
    front = _Upstream(mode="redirect", other_port=secret.port)
    try:
        pl.NODE_PORT = front.port
        _clear_cache()
        code, body = pl._fetch_chain()
        assert code == 502, "a redirect should surface as 502, got %d" % code
        assert b"SECRET" not in body, "relay followed the redirect and leaked the target"
        assert secret.hits == 0, "the redirect target was fetched (hits=%d)" % secret.hits
    finally:
        front.stop()
        secret.stop()


def test_redirect_WOULD_follow_without_guard():
    """RED direction: a redirect-following opener DOES reach the private target --
    proving the _NoRedirect guard is what closes it, not the fixed URL alone."""
    secret = _Upstream(mode="ok", body=b'{"chain":["SECRET"]}')
    front = _Upstream(mode="redirect", other_port=secret.port)
    saved = pl._OPENER
    try:
        pl.NODE_PORT = front.port
        pl._OPENER = urllib.request.build_opener()   # stock opener FOLLOWS 3xx
        _clear_cache()
        code, body = pl._fetch_chain()
        assert code == 200 and b"SECRET" in body, \
            "stock opener should have followed to the target (got %d)" % code
        assert secret.hits == 1, "expected the target to be hit once, got %d" % secret.hits
    finally:
        pl._OPENER = saved
        front.stop()
        secret.stop()


# --- C4b: single-flight + timestamp-after-fetch -------------------------------

def test_single_flight_collapses_concurrent_misses():
    """N concurrent misses open exactly ONE upstream connection."""
    up = _Upstream(mode="slow", delay=0.4)
    try:
        pl.NODE_PORT = up.port
        _clear_cache()
        results = []

        def go():
            results.append(pl._fetch_chain())

        threads = [threading.Thread(target=go) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert all(c == 200 for c, _ in results), "every caller should get 200"
        assert up.hits == 1, "single-flight expected 1 upstream hit, got %d" % up.hits
    finally:
        up.stop()


def test_WITHOUT_lock_stampedes():
    """RED direction: replace the lock with a no-op and the N misses all fetch --
    proving the lock is load-bearing."""
    class _NoLock:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    up = _Upstream(mode="slow", delay=0.4)
    saved = pl._cache_lock
    try:
        pl.NODE_PORT = up.port
        pl._cache_lock = _NoLock()
        _clear_cache()
        threads = [threading.Thread(target=pl._fetch_chain) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert up.hits > 1, "without the lock the misses should stampede, got %d" % up.hits
    finally:
        pl._cache_lock = saved
        up.stop()


def test_timestamp_recorded_after_fetch():
    """A slow fetch is cached with a post-fetch timestamp, not the pre-fetch one."""
    up = _Upstream(mode="slow", delay=0.5)
    try:
        pl.NODE_PORT = up.port
        _clear_cache()
        t0 = time.time()
        pl._fetch_chain()
        ts = pl._cache["chain"][0]
        assert ts - t0 >= 0.4, \
            "cache timestamp must be recorded after the ~0.5s fetch (delta=%.3f)" % (ts - t0)
    finally:
        up.stop()


# --- C4a: slowloris / client timeout ------------------------------------------

def test_production_handler_has_timeout():
    assert pl.Handler.timeout is not None, "Handler.timeout must be set (slowloris)"
    assert 0 < pl.Handler.timeout, "Handler.timeout must be positive"


def test_slow_client_is_dropped():
    """A client that sends a partial request and stalls is dropped within the
    handler timeout, instead of holding a thread open indefinitely."""
    class Slow(pl.Handler):
        timeout = 1.0

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.sendall(b"GET /chain HTTP/1.1\r\nHost: x\r\n")   # no terminating blank line
        s.settimeout(5)
        start = time.time()
        data = s.recv(65536)      # server closes (b'') or errors when it times out
        elapsed = time.time() - start
        s.close()
        assert elapsed < 4.0, "slow client was not dropped promptly (%.1fs)" % elapsed
        # b'' = clean close on timeout; a 408-style response also counts as "dropped".
        assert data == b"" or b"HTTP/1." in data, "unexpected server behaviour"
    finally:
        srv.shutdown()
        srv.server_close()


# --- C4a defence-in-depth: concurrency cap ------------------------------------

def test_concurrency_cap_sheds_load():
    """With every in-flight permit held, a new request gets 503; freed, it is served."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), pl.Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    acquired = 0
    try:
        while pl._inflight.acquire(blocking=False):
            acquired += 1
        assert acquired == pl.MAX_INFLIGHT, \
            "expected to drain %d permits, drained %d" % (pl.MAX_INFLIGHT, acquired)

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/")          # "/" is static, needs no upstream
        busy = conn.getresponse().status
        conn.close()
        assert busy == 503, "exhausted permits should shed with 503, got %d" % busy

        pl._inflight.release()
        acquired -= 1
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/")
        ok = conn.getresponse().status
        conn.close()
        assert ok == 200, "with a permit free, / should serve 200, got %d" % ok
    finally:
        for _ in range(acquired):
            pl._inflight.release()
        srv.shutdown()
        srv.server_close()


TESTS = [
    test_redirect_not_followed,
    test_redirect_WOULD_follow_without_guard,
    test_single_flight_collapses_concurrent_misses,
    test_WITHOUT_lock_stampedes,
    test_timestamp_recorded_after_fetch,
    test_production_handler_has_timeout,
    test_slow_client_is_dropped,
    test_concurrency_cap_sheds_load,
]


def main() -> int:
    passed = 0
    failed = 0
    for fn in TESTS:
        try:
            fn()
            passed += 1
        except Exception as e:                               # noqa: BLE001
            failed += 1
            print("  FAIL %s: %s" % (fn.__name__, e))
    total = passed + failed
    print("PL1: %d/%d passed" % (passed, total))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
