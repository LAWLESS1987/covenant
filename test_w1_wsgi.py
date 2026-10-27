#!/usr/bin/env python3
"""
test_w1_wsgi.py -- W1 (v8.29): the HTTP front door is bounded.

WHAT THIS PINS DOWN
  Every other read path in this file was bounded by the A-series: bytes (A3),
  coherent ceilings (A5), a concurrent boot probe (A14), a wall-clock exchange
  deadline (A15), and a 96-worker receive pool. The HTTP port -- the one an
  operator is actually told to expose -- was served by werkzeug's DEVELOPMENT
  server with `threaded=True`: one unbounded thread per connection, no queue,
  no idle timeout. A client that connects and says nothing costs a thread for
  as long as it likes. That is the A15 hazard on the HTTP side, and W10 below
  records it happening on the fallback path.

  The change is a resolved WSGI backend (waitress when importable, else the
  old dev server byte for byte), a bounded pool, an idle reaper, and /health
  saying which one is serving so nobody has to assume.

CHECKS
  W1a-W1e  import-time refusals: bad backend name, threads<1, connection_limit
           below threads, channel_timeout<1, WSGI body cap not above Flask's.
  W2       resolve_wsgi_server("werkzeug") -> the old dev server.
  W3       resolve_wsgi_server("waitress") -> waitress.
  W4       "auto" prefers waitress when it imports.
  W5       explicit waitress + waitress missing -> RuntimeError (not a silent
           downgrade to the dev server).
  W6       live waitress node: /health 200, wsgi=waitress, no dev-server warning.
  W7       live waitress node: an oversized POST is refused 413 AND recorded as
           http_body_too_large -- i.e. FLASK is still the enforcer. If waitress
           had refused it first, the v8.17 anomaly record would have silently
           stopped happening: a monitoring regression dressed as a tightening.
  W8       live waitress node: an idle connection is REAPED by channel_timeout.
  W9       live werkzeug node: /health says werkzeug-dev, warns about it, and
           still does W7's 413 + anomaly exactly as before.
  W10      PRE-FIX RECORD, on the fallback path: the dev server does NOT reap
           an idle connection. Same node, same test, opposite outcome.
"""
from __future__ import annotations
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_SKIP_PREFLIGHT", "1")
# Small so the oversized-body case is cheap; still > MAX_TX_BYTES (16 KiB), so
# the import-time coherence assertion is satisfied honestly rather than bypassed.
os.environ.setdefault("COVENANT_MAX_HTTP_BODY_BYTES", str(32 * 1024))
os.environ.setdefault("COVENANT_WSGI_CHANNEL_TIMEOUT", "2")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov  # noqa: E402

results = []
HERE = os.path.dirname(os.path.abspath(__file__))


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail and not ok else ""))


def import_refused(env, needle):
    """Start python -c 'import covenant_unified_v8' with env and expect death."""
    e = dict(os.environ)
    e.update(env)
    p = subprocess.run([sys.executable, "-c", "import covenant_unified_v8"],
                       cwd=HERE, env=e, capture_output=True, text=True, timeout=120)
    return p.returncode != 0 and needle in (p.stderr or "")


def fresh_master(name, port, backend):
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    old = cov.WSGI_SERVER
    cov.WSGI_SERVER = backend           # resolve_wsgi_server() reads this
    try:
        m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port,
                                      p2p_port=port + 1, db_path=tmp)
    finally:
        cov.WSGI_SERVER = old
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    threading.Thread(target=m.api.run, daemon=True).start()
    for _ in range(200):                # wait for the listener
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return m
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"{name} never bound {port}")


def get_json(port, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        c.request("GET", path)
        r = c.getresponse()
        return r.status, json.loads(r.read().decode() or "{}")
    finally:
        c.close()


def post_bytes(port, path, nbytes):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    try:
        body = b'{"pad":"' + b"x" * nbytes + b'"}'
        c.request("POST", path, body=body, headers={"Content-Type": "application/json"})
        r = c.getresponse()
        r.read()
        return r.status
    except Exception as ex:
        return f"transport:{type(ex).__name__}"
    finally:
        c.close()


def idle_socket_survives(port, seconds):
    """Open a connection, send NOTHING, and report whether the server kept it
    open for `seconds`. True  = the connection was held (a pinned worker).
    False = the server closed it (reaped)."""
    s = socket.create_connection(("127.0.0.1", port), timeout=seconds + 5)
    try:
        s.settimeout(seconds)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                if s.recv(1) == b"":
                    return False              # server closed it
            except socket.timeout:
                return True                   # still open at the deadline
            except OSError:
                return False
        return True
    finally:
        try:
            s.close()
        except OSError:
            pass


# --------------------------------------------------------------- import gates
print("\nW1  import-time refusals")
check("W1a bad backend name refused",
      import_refused({"COVENANT_WSGI": "nginx"}, "auto|waitress|werkzeug"))
check("W1b threads < 1 refused",
      import_refused({"COVENANT_WSGI_THREADS": "0"}, "COVENANT_WSGI_THREADS must be >= 1"))
check("W1c connection_limit below threads refused",
      import_refused({"COVENANT_WSGI_THREADS": "8", "COVENANT_WSGI_CONNECTION_LIMIT": "4"},
                     "could never fill"))
check("W1d channel_timeout < 1 refused",
      import_refused({"COVENANT_WSGI_CHANNEL_TIMEOUT": "0.5"},
                     "COVENANT_WSGI_CHANNEL_TIMEOUT must be >= 1"))
check("W1e WSGI body cap not above Flask's refused",
      import_refused({"COVENANT_WSGI_MAX_BODY_BYTES": str(32 * 1024)},
                     "http_body_too_large"))

# ------------------------------------------------------------------- resolver
print("\nW2-W5  resolver")
name, serve = cov.resolve_wsgi_server("werkzeug")
check("W2 werkzeug -> dev server", name == "werkzeug-dev" and callable(serve), name)
name, serve = cov.resolve_wsgi_server("waitress")
check("W3 waitress -> waitress", name == "waitress" and callable(serve), name)
name, _ = cov.resolve_wsgi_server("auto")
check("W4 auto prefers waitress when importable", name == "waitress", name)

import builtins  # noqa: E402
_real_import = builtins.__import__


def _blocked(n, *a, **k):
    if n == "waitress":
        raise ImportError("blocked for W5")
    return _real_import(n, *a, **k)


builtins.__import__ = _blocked
try:
    try:
        cov.resolve_wsgi_server("waitress")
        w5 = False
    except RuntimeError as ex:
        w5 = "pip install waitress" in str(ex)
    name_auto, _ = cov.resolve_wsgi_server("auto")
finally:
    builtins.__import__ = _real_import
check("W5 explicit waitress + missing waitress -> RuntimeError, not a downgrade", w5)
check("W5b auto + missing waitress falls back to the dev server",
      name_auto == "werkzeug-dev", name_auto)

# ------------------------------------------------------------------ live: waitress
print("\nW6-W8  live node on waitress")
WP = 17910
mw = fresh_master("w1wait", WP, "waitress")
st, h = get_json(WP, "/health")
check("W6 /health 200 on waitress", st == 200, st)
check("W6b /health reports wsgi=waitress", h.get("wsgi") == "waitress", h.get("wsgi"))
check("W6c no dev-server warning",
      not any("werkzeug" in w for w in h.get("warnings", [])), h.get("warnings"))

code = post_bytes(WP, "/transactions", 40 * 1024)
_, an = get_json(WP, "/anomalies")
kinds = an.get("per_kind", {})
check("W7 oversized POST refused 413", code == 413, code)
check("W7b Flask -- not waitress -- recorded http_body_too_large",
      "http_body_too_large" in kinds, sorted(kinds))

t0 = time.monotonic()
held = idle_socket_survives(WP, 8)
check("W8 idle connection REAPED by channel_timeout",
      not held, f"still open after {time.monotonic()-t0:.1f}s")

# ------------------------------------------------------------------ live: werkzeug
print("\nW9-W10  live node on the werkzeug dev server (the fallback path)")
KP = 17930
mk = fresh_master("w1werk", KP, "werkzeug")
st, h = get_json(KP, "/health")
check("W9 /health 200 on the dev server", st == 200, st)
check("W9b /health reports wsgi=werkzeug-dev", h.get("wsgi") == "werkzeug-dev", h.get("wsgi"))
check("W9c /health warns that the dev server is unbounded",
      any("werkzeug-dev" in w for w in h.get("warnings", [])), h.get("warnings"))
code = post_bytes(KP, "/transactions", 40 * 1024)
_, an = get_json(KP, "/anomalies")
check("W9d dev-server path still refuses 413", code == 413, code)
check("W9e dev-server path still records http_body_too_large",
      "http_body_too_large" in an.get("per_kind", {}), sorted(an.get("per_kind", {})))

held = idle_socket_survives(KP, 5)
check("W10 PRE-FIX RECORD: dev server does NOT reap an idle connection", held)

# ------------------------------------------------- preflight vs both servers
print("\nW11-W12  A2's HTTP-vs-P2P discriminator must survive the server swap")


def preflight_says_http(target_port, own_port):
    """Run preflight_port_check in a child: peer = an HTTP API port -> fatal."""
    e = dict(os.environ)
    e.pop("COVENANT_SKIP_PREFLIGHT", None)          # the whole point is to run it
    code = ("import covenant_unified_v8 as c;"
            f"c.preflight_port_check('127.0.0.1', {own_port}, '127.0.0.1:{target_port}')")
    p = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=e,
                       capture_output=True, text=True, timeout=60)
    return p.returncode == 1 and "answered like an HTTP server" in (p.stdout or "")


check("W11 preflight detects a WAITRESS-served API port as HTTP",
      preflight_says_http(WP, 17960),
      "waitress answers NOTHING to an unterminated request line -- the pre-W1 "
      "probe read that as 'P2P listener' and let the footgun through")
check("W12 preflight still detects a WERKZEUG-served API port as HTTP",
      preflight_says_http(KP, 17980))

# ----------------------------------------------------------------------- done
passed = sum(1 for _, ok in results if ok)
print(f"\n  {passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
