#!/usr/bin/env python3
"""test_cx1_app_csrf.py -- CX1: the console refuses cross-site state-changing requests.

WHY THIS EXISTS (2026-11-02, the security-hunt). covenant_app binds loopback and checks the client
IP per request (_guard). That is NOT a CSRF defence: a page on any site the operator visits can POST
to http://127.0.0.1:5199 with a "simple" request; the browser still connects from loopback, so
_guard passes, and when actions are armed (COVENANT_APP_ACTIONS=1) a drive-by site could trigger
restart / sweep / aclfix. do_POST now also refuses a request carrying positive evidence of a
cross-site browser origin (a mismatched Origin, or Sec-Fetch-Site: cross-site), while leaving the
console's own same-origin page and non-browser callers (no Origin) untouched.

DRIVES THE REAL covenant_app.Handler on an EPHEMERAL loopback port -- no production ports, so this
runs anywhere, unlike test_covenant_app which needs 5000/5020/5060 free. A cross-site POST is refused
BEFORE any dispatch, so no mesh/node is needed to reach the gate. Both ways: cross-site -> 403;
same-origin and headless (no Origin) -> not 403 (the real page and curl must keep working).

Run: python3 test_cx1_app_csrf.py
"""
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def main():
    try:
        import covenant_app as app
    except Exception as e:                                           # noqa: BLE001
        print("NOT RUN: covenant_app did not import (%s) -- CX1 did not run. Not a pass." % e)
        return 2

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    try:
        srv = app.ExclusiveHTTPServer(("127.0.0.1", port), app.Handler)
    except Exception as e:                                           # noqa: BLE001
        print("NOT RUN: could not start the real console handler (%s). Not a pass." % e)
        return 2
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.3)

    def post(origin=None, sec=None, path="/api/action/gates"):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=b"{}",
                                     method="POST", headers={"Content-Type": "application/json"})
        if origin is not None:
            req.add_header("Origin", origin)
        if sec is not None:
            req.add_header("Sec-Fetch-Site", sec)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:                                       # noqa: BLE001
            return "ERR:%s" % type(e).__name__

    try:
        cross = post(origin="http://evil.example")
        check("CX1.1 a cross-site Origin on a state-changing POST is refused (403) -- CSRF cannot reach run_action",
              cross == 403, "status=%r (want 403)" % cross)
        sec = post(sec="cross-site")
        check("CX1.2 Sec-Fetch-Site: cross-site is refused too (the browser's own cross-origin signal)",
              sec == 403, "status=%r (want 403)" % sec)
        # the console's own page is served from app.PORT; its fetch POSTs carry that Origin.
        same = post(origin="http://127.0.0.1:%d" % app.PORT)
        check("CX1.3 the console's OWN same-origin page is NOT refused (passes the origin gate) -- the real page works",
              same != 403, "status=%r (must not be 403)" % same)
        none = post()
        check("CX1.4 a non-browser caller with no Origin is unaffected -- headless tools / curl still work",
              none != 403, "status=%r (must not be 403)" % none)
        # GET must stay open to the same-origin page regardless (read-only); a cross-site GET is harmless
        # and not gated, so we only assert the POST gate above.
    finally:
        srv.shutdown()

    ok = sum(1 for r in results if r)
    print("\nCX1: %d/%d passed" % (ok, len(results)))
    return 0 if results and ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
