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
import time
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


class Truncating(http.server.BaseHTTPRequestHandler):
    """Promises more body than it sends, then hangs up.

    urllib raises http.client.IncompleteRead for this, and IncompleteRead is an
    HTTPException, which is NEITHER an OSError NOR a URLError. So it used to
    escape covenant_watchdog.health entirely and abort the whole pass: every
    node after the bad one went unchecked, and the branch that restarts a dead
    node never ran. A node killed mid-response is the realistic way to produce
    it -- which is precisely the moment a watchdog is most needed."""

    def do_GET(self):                                             # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "4096")
        self.end_headers()
        self.wfile.write(b'{"node_id": "TRUNC"')
        self.close_connection = True

    def log_message(self, *_a):
        return


class Slow(http.server.BaseHTTPRequestHandler):
    """Accepts the connection, then takes far too long to answer.

    A node mid-boot building its judges looks exactly like this. The connection
    is ACCEPTED, so something is listening; it just does not answer inside the
    probe's timeout. Reporting that as an empty port is how a rolling restart
    starts a second node on an occupied one."""

    def do_GET(self):                                             # noqa: N802
        time.sleep(12)
        try:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")
        except Exception:                                         # noqa: BLE001
            pass

    def log_message(self, *_a):
        return


def serve(code, body=None, handler=Stub):
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler)
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

        # A truncated response raises http.client.IncompleteRead, which is an
        # HTTPException -- neither an OSError nor a URLError. It used to escape
        # health() and abort the whole pass, leaving every later node unchecked
        # and the restart branch unreached.
        srvT, pT = serve(200, handler=Truncating)
        try:
            raised = ""
            try:
                h4, err4 = W.health(pT, timeout=5)
            except Exception as exc:                              # noqa: BLE001
                h4, err4, raised = None, "", "%s: %s" % (type(exc).__name__, exc)
            check("A115.10a a truncated response does not escape health()",
                  raised == "", raised or "returned an error instead of raising")
            check("A115.10b it yields no document and is not a rate limit",
                  h4 is None and not str(err4).startswith("429"), str(err4)[:60])
        finally:
            srvT.shutdown()

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

            # A115.8: THE ALERT, not just the restart. one_pass says "NO node
            # is reachable -- the chain is not running", the loudest sentence
            # this file can produce, from `states` -- where a 429 lands as None
            # like any other failure. The restart path was taught the
            # difference and this was not, so a fully healthy mesh answering
            # 429 still reported the chain down. Measured by an adversarial
            # review, not by this suite, which stayed green through it.
            started.clear()
            srv8a, p8a = serve(429)
            srv8b, p8b = serve(429)
            try:
                W.NODES = [{"id": "R1", "port": p429, "db": "u.db", "key": "u.key", "peers": ""},
                           {"id": "R2", "port": p8a, "db": "u.db", "key": "u.key", "peers": ""},
                           {"id": "R3", "port": p8b, "db": "u.db", "key": "u.key", "peers": ""}]
                W._fail_counts = {"R1": 0, "R2": 0, "R3": 0}
                alerts = W.one_pass(strict=False) or []
                bad = [a for a in alerts if "chain is not running" in a]
                check("A115.8a an all-429 mesh is NOT reported as 'the chain is not running'",
                      bad == [], "; ".join(bad) or "no such alert")
                check("A115.8b and nothing is restarted over it",
                      started == [], "restarted %s" % (started or "nobody"))
            finally:
                srv8a.shutdown(); srv8b.shutdown()

            # A115.9: a genuinely dead mesh MUST still say it out loud, or
            # A115.8 would be satisfied by deleting the alert.
            started.clear()
            d9a, d9b, d9c = closed_port(), closed_port(), closed_port()
            W.NODES = [{"id": "D1", "port": d9a, "db": "u.db", "key": "u.key", "peers": ""},
                       {"id": "D2", "port": d9b, "db": "u.db", "key": "u.key", "peers": ""},
                       {"id": "D3", "port": d9c, "db": "u.db", "key": "u.key", "peers": ""}]
            W._fail_counts = {"D1": 0, "D2": 0, "D3": 0}
            alerts9 = W.one_pass(strict=False) or []
            check("A115.9 a really-dead mesh still reports the chain not running",
                  any("chain is not running" in a for a in alerts9),
                  "; ".join(a for a in alerts9 if "chain" in a)[:90] or "NO SUCH ALERT")

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

    # ------------------------------------- the tool that caused the incident
    # rolling_restart.py polled /health hard enough to trip the limiter and
    # then reported the healthy nodes it had silenced as NOT ANSWERING. Until
    # now nothing tested it at all. These drive its real probe/port_free.
    import rolling_restart as RR

    srvR, pR = serve(429)
    srvS, pS = serve(200, handler=Slow)
    deadR = closed_port()
    try:
        st, _d = RR.probe(pR, timeout=5)
        check("A115.11a rolling_restart calls a 429 'rate_limited', not 'down'",
              st == "rate_limited", "got %r" % st)
        st2, _d2 = RR.probe(deadR, timeout=5)
        check("A115.11b and a refused connection 'down'", st2 == "down", "got %r" % st2)
        st3, d3 = RR.probe(pS, timeout=3)
        check("A115.11c and a listener too slow to answer 'slow', NOT 'down'",
              st3 == "slow", "got %r (%s)" % (st3, d3))

        # port_free decides whether it is safe to start a node on that port.
        # It must say NO for anything that is listening, however it answers.
        check("A115.12a port_free refuses a port that is merely slow",
              RR.port_free(pS, time.time() + 6, lambda *_a: None) is False, "")
        check("A115.12b port_free refuses a port that is rate-limiting",
              RR.port_free(pR, time.time() + 6, lambda *_a: None) is False, "")
        check("A115.12c port_free allows a port with nothing on it",
              RR.port_free(deadR, time.time() + 6, lambda *_a: None) is True, "")
    finally:
        srvR.shutdown()
        srvS.shutdown()

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
