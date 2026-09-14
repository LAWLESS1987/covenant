#!/usr/bin/env python3
"""test_a115_rate_limited_is_not_down.py -- a node that answers 429 is UP, and
nothing may restart it for saying so.

THE DEFECT (2026-09-14). /health is an unlisted read endpoint, so it carries
RATE_LIMIT_DEFAULT: twenty requests per sixty seconds, keyed by source address.
127.0.0.1 is ONE source no matter which tool is asking -- the watchdog every
sixty seconds, rolling_restart once every two while it waits for a boot, and a
person running --status. Cross twenty and healthy nodes start answering 429.

urllib raises HTTPError for that, HTTPError is a SUBCLASS of URLError, and
covenant_watchdog.health caught URLError -- so a rate-limited node came back
indistinguishable from a refused connection. Three consecutive and the watchdog
restarts it. Worse: when every node trips in the same pass, `all_down` drops the
threshold from three strikes to ONE, so the answer to "I asked too often" was to
restart the entire mesh on the first pass.

This is not hypothetical and it is not old. It happened while the phone was
being peered: nodes B and C returned 429 in 1.5 milliseconds, rolling_restart
printed NOT ANSWERING for both, and the watchdog logged them unreachable and
tried to start second copies. The only thing between that and a real outage was
run_node's port preflight refusing to bind an occupied port. A monitor that
takes the chain down because it asked too many questions is worse than no
monitor.

WHAT THESE CHECKS ARE. Every one drives the REAL covenant_watchdog.health
against a REAL HTTP server over a REAL socket, and the restart decision through
the REAL one_pass. Nothing here greps source text for the string "429" -- 35 of
36 guards audited on 2026-09-09 did exactly that, and a guard that greps cannot
tell a fix from a comment about a fix.

Run:  python test_a115_rate_limited_is_not_down.py
"""
import http.server
import json
import os
import socket
import sys
import threading
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append((label, bool(ok), detail))
    print("%-6s %-52s %s" % ("ok" if ok else "FAIL", label, detail))
    return bool(ok)


class Stub(http.server.BaseHTTPRequestHandler):
    """Answers /health with whatever status the server was told to answer."""

    def do_GET(self):                                             # noqa: N802
        code = self.server.code
        body = json.dumps(self.server.body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_a):                                   # silence
        return


def serve(code, body=None):
    srv = http.server.HTTPServer(("127.0.0.1", 0), Stub)
    srv.code = code
    srv.body = body if body is not None else {"status": "error", "message": "rate limited"}
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, srv.server_address[1]


def closed_port():
    """A port with nothing on it: bind, read the number, close."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    import covenant_watchdog as W

    # ------------------------------------------------------- health() itself
    srv429, p429 = serve(429)
    srv200, p200 = serve(200, {"node_id": "STUB", "chain_height": 7, "warnings": []})
    dead = closed_port()
    try:
        h, err = W.health(p429, timeout=5)
        check("A115.1a a 429 yields no health document", h is None, repr(h)[:40])
        check("A115.1b and the error is MARKED as a rate limit",
              str(err).startswith("429"), str(err)[:70])

        h2, err2 = W.health(p200, timeout=5)
        check("A115.2 a 200 still parses into a health document",
              isinstance(h2, dict) and h2.get("chain_height") == 7 and err2 is None,
              "height %s" % (h2 or {}).get("chain_height"))

        h3, err3 = W.health(dead, timeout=5)
        check("A115.3a a refused connection yields no document", h3 is None, "")
        check("A115.3b and is NOT marked as a rate limit",
              not str(err3).startswith("429"), str(err3)[:60])

        # -------------------------------------------- the restart decision
        # Drive the real one_pass. Only the two tending helpers are stubbed --
        # they mine the pending pool and tend a service, which is not what is
        # being measured and does touch real state.
        started = []
        orig = (W.NODES, W.start_node, W.tend_seal_service, W.tend_pending,
                W.log, dict(W._fail_counts))
        try:
            tended = []
            W.start_node = lambda n: started.append(n["id"])
            W.tend_seal_service = lambda: (tended.append("seal"), "up")[1]
            W.tend_pending = lambda: (tended.append("pool"), "nothing pending")[1]
            W.log = lambda *a, **k: None

            # One node, rate-limited, probed more times than the strike count.
            W.NODES = [{"id": "RL", "port": p429, "db": "unused.db",
                        "key": "unused.db.key", "peers": ""}]
            W._fail_counts = {"RL": 0}
            for _ in range(W.FAIL_BEFORE_RESTART + 2):
                W.one_pass(strict=False)
            check("A115.4a a rate-limited node is never restarted",
                  started == [], "start_node called for %s" % (started or "nobody"))
            check("A115.4b and it accrues no strikes",
                  W._fail_counts.get("RL") == 0, "strikes=%s" % W._fail_counts.get("RL"))

            # The same loop against a node that is genuinely gone MUST still
            # restart it, or this suite would pass by breaking the watchdog
            # rather than fixing it -- and it must take the full three strikes,
            # which is only observable with a healthy node alongside it. Alone,
            # a dead node IS the whole mesh, `all_down` is true, and one strike
            # is the correct answer (that is what A115.7 measures).
            started.clear()
            W.NODES = [{"id": "UP", "port": p200, "db": "u.db", "key": "u.key", "peers": ""},
                       {"id": "DEAD", "port": dead, "db": "u.db", "key": "u.key", "peers": ""}]
            W._fail_counts = {"UP": 0, "DEAD": 0}
            for i in range(1, W.FAIL_BEFORE_RESTART + 1):
                W.one_pass(strict=False)
                if i < W.FAIL_BEFORE_RESTART:
                    check("A115.5%s strike %d of %d does not restart yet"
                          % ("abcdef"[i - 1], i, W.FAIL_BEFORE_RESTART),
                          started == [], "restarted %s" % (started or "nobody"))
            check("A115.5z the unreachable node IS restarted on the last strike",
                  started == ["DEAD"], "start_node called for %s" % (started or "nobody"))

            # THE WORST CASE. Every node answering 429 in one pass must not read
            # as "whole mesh down", because that drops the threshold to a single
            # strike and would restart all of them on the first pass.
            started.clear()
            srv429b, p429b = serve(429)
            srv429c, p429c = serve(429)
            try:
                W.NODES = [{"id": "X", "port": p429, "db": "u.db", "key": "u.key", "peers": ""},
                           {"id": "Y", "port": p429b, "db": "u.db", "key": "u.key", "peers": ""},
                           {"id": "Z", "port": p429c, "db": "u.db", "key": "u.key", "peers": ""}]
                W._fail_counts = {"X": 0, "Y": 0, "Z": 0}
                tended.clear()
                W.one_pass(strict=False)
                check("A115.6a three nodes all rate-limited is NOT 'whole mesh down'",
                      started == [], "restarted %s on the first pass" % (started or "nobody"))
                # ...and the pass must go on doing its work. `all_down` gates the
                # tending block as well as the restart threshold, so counting a
                # 429 as "down" would also have silently stopped the watchdog
                # tending the seal service and the pending pool for as long as
                # the limiter was tripped. This is the check that makes the
                # all_down fix load-bearing rather than belt-and-braces: without
                # it, reinstating the old expression changed nothing any test
                # could see.
                check("A115.6b and the pass still does its tending work",
                      sorted(set(tended)) == ["pool", "seal"], "tended %s" % (sorted(set(tended)) or "nothing"))
            finally:
                srv429b.shutdown(); srv429c.shutdown()

            # And a mesh that really IS all gone must still restart on one strike.
            started.clear()
            d2, d3 = closed_port(), closed_port()
            W.NODES = [{"id": "P", "port": dead, "db": "u.db", "key": "u.key", "peers": ""},
                       {"id": "Q", "port": d2, "db": "u.db", "key": "u.key", "peers": ""},
                       {"id": "R", "port": d3, "db": "u.db", "key": "u.key", "peers": ""}]
            W._fail_counts = {"P": 0, "Q": 0, "R": 0}
            W.one_pass(strict=False)
            check("A115.7 a really-unreachable mesh still restarts on the first strike",
                  sorted(started) == ["P", "Q", "R"], "restarted %s" % sorted(started))
        finally:
            (W.NODES, W.start_node, W.tend_seal_service, W.tend_pending,
             W.log, W._fail_counts) = orig
    finally:
        srv429.shutdown()
        srv200.shutdown()

    passed = sum(1 for _, o, _ in RESULTS if o)
    failed = sum(1 for _, o, _ in RESULTS if not o)
    print("")
    print("A115: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                             # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
